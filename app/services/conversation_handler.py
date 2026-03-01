"""
Conversation handler — the brain of Sakhi.

Implements the state machine:
  NEW / AWAITING_LANGUAGE → ask language
  AWAITING_LAST_PERIOD    → parse date, run cycle prediction
  ACTIVE                  → route to Grok AI or cycle query handler
"""

import logging
from datetime import date

from app.core.constants import (
    ConversationState,
    SUPPORTED_LANGUAGES,
    get_message,
)
from app.core.config import settings
from app.core.exceptions import DatabaseError, GrokAPIError
from app.db import user_repository
from app.models.analytics import EventType
from app.models.telegram import TelegramMessage
from app.models.user import UserDocument
from app.services import analytics_service, grok_service, telegram_service
from app.services.cycle_service import (
    predict_next_period,
    days_until_next_period,
    is_cycle_related_query,
    format_date,
)
from app.utils.validators import parse_date_input, validate_period_date, sanitize_text

logger = logging.getLogger(__name__)


async def handle_message(message: TelegramMessage) -> None:
    """
    Entry point for all incoming messages.
    Loads user state, routes to correct handler, persists changes.
    """
    if not message.from_:
        logger.warning("Received message without sender info")
        return

    telegram_id = message.from_.id
    chat_id = message.chat.id
    raw_text = message.text or ""
    text = sanitize_text(raw_text)

    logger.info(
        "Incoming message",
        extra={
            "telegram_id": telegram_id,
            "text_length": len(text),
            "chat_id": chat_id,
        },
    )

    # Load or bootstrap user
    try:
        user = await user_repository.get_user(telegram_id)
        if user is None:
            user = UserDocument(
                telegram_id=telegram_id,
                username=message.from_.username,
                first_name=message.from_.first_name,
                language=message.from_.language_code or "en",
            )
    except DatabaseError as exc:
        logger.error("Failed to load user", exc_info=exc)
        await _send_safe(chat_id, get_message("en", "db_error"))
        await analytics_service.track(telegram_id, EventType.DB_ERROR)
        return

    # /start command resets state regardless
    if text.lower() in {"/start", "/start@sakhibot"}:
        await _handle_start(user, chat_id)
        return

    # Route by current state
    if user.state in (ConversationState.NEW, ConversationState.AWAITING_LANGUAGE):
        await _handle_language_selection(user, chat_id, text)
    elif user.state == ConversationState.AWAITING_LAST_PERIOD:
        await _handle_period_date(user, chat_id, text)
    elif user.state == ConversationState.ACTIVE:
        await _handle_active(user, chat_id, text)
    else:
        logger.warning("Unknown state encountered", extra={"state": user.state})
        await _handle_start(user, chat_id)


# ---------------------------------------------------------------------------
# State handlers
# ---------------------------------------------------------------------------

async def _handle_start(user: UserDocument, chat_id: int) -> None:
    """Reset user and show welcome message."""
    user.state = ConversationState.AWAITING_LANGUAGE
    user.last_period_date = None

    await _save_user(user)
    await _send_safe(chat_id, get_message("en", "welcome"))
    await analytics_service.track(user.telegram_id, EventType.USER_START)


async def _handle_language_selection(user: UserDocument, chat_id: int, text: str) -> None:
    """Map user input to a supported language code."""
    lang_code = SUPPORTED_LANGUAGES.get(text.lower().strip())

    if not lang_code:
        await _send_safe(chat_id, get_message(user.language, "language_unknown"))
        await analytics_service.track(user.telegram_id, EventType.INVALID_INPUT, payload={"text": text[:50]})
        return

    user.language = lang_code
    user.state = ConversationState.AWAITING_LAST_PERIOD

    await _save_user(user)
    await _send_safe(chat_id, get_message(lang_code, "language_set"))
    await _send_safe(chat_id, get_message(lang_code, "ask_last_period"))
    await analytics_service.track(user.telegram_id, EventType.LANGUAGE_SET, language=lang_code)


async def _handle_period_date(user: UserDocument, chat_id: int, text: str) -> None:
    """Parse last period date and run cycle prediction."""
    lang = user.language
    parsed = parse_date_input(text)

    if parsed is None:
        await _send_safe(chat_id, get_message(lang, "invalid_date"))
        await analytics_service.track(user.telegram_id, EventType.INVALID_INPUT, payload={"text": text[:50]})
        return

    error_key = validate_period_date(parsed)
    if error_key:
        await _send_safe(chat_id, get_message(lang, error_key))
        await analytics_service.track(user.telegram_id, EventType.INVALID_INPUT, payload={"error": error_key})
        return

    # Save date and transition to ACTIVE
    user.last_period_date = parsed
    user.state = ConversationState.ACTIVE
    await _save_user(user)

    await analytics_service.track(
        user.telegram_id,
        EventType.PERIOD_DATE_SET,
        language=lang,
        payload={"date": parsed.isoformat()},
    )

    # Generate and send prediction
    await _send_cycle_prediction(user, chat_id)


async def _handle_active(user: UserDocument, chat_id: int, text: str) -> None:
    """
    Route active-state messages:
    - Cycle prediction queries → deterministic handler
    - Everything else → Grok AI
    """
    if is_cycle_related_query(text):
        if user.last_period_date:
            await _send_cycle_prediction(user, chat_id)
        else:
            # Edge case: user asks about cycle but date was never set
            user.state = ConversationState.AWAITING_LAST_PERIOD
            await _save_user(user)
            await _send_safe(chat_id, get_message(user.language, "ask_last_period"))
        return

    # Delegate to Grok
    await telegram_service.send_typing_action(chat_id)
    await analytics_service.track(user.telegram_id, EventType.AI_QUERY, language=user.language)

    try:
        reply = await grok_service.ask_grok(text, language=user.language)
        disclaimer = get_message(user.language, "disclaimer")
        await _send_safe(chat_id, f"{reply}\n\n{disclaimer}")

    except GrokAPIError as exc:
        logger.warning("Grok AI failed", exc_info=exc)
        await analytics_service.track(
            user.telegram_id,
            EventType.AI_ERROR,
            payload={"error": str(exc)[:200]},
        )
        await _send_safe(chat_id, get_message(user.language, "ai_error"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _send_cycle_prediction(user: UserDocument, chat_id: int) -> None:
    """Compute and send the next period prediction message."""
    last_period: date = user.last_period_date  # type: ignore[assignment]
    next_period = predict_next_period(last_period, user.cycle_length_days)
    days_remaining = days_until_next_period(next_period)

    msg = get_message(
        user.language,
        "prediction",
        last_period=format_date(last_period),
        next_period=format_date(next_period),
        days_remaining=str(max(days_remaining, 0)),
        cycle_length=str(user.cycle_length_days),
    )

    await _send_safe(chat_id, msg)
    await analytics_service.track(
        user.telegram_id,
        EventType.CYCLE_PREDICTED,
        language=user.language,
        payload={
            "next_period": next_period.isoformat(),
            "days_remaining": days_remaining,
        },
    )


async def _save_user(user: UserDocument) -> None:
    """Persist user with error handling."""
    try:
        await user_repository.upsert_user(user)
    except DatabaseError as exc:
        logger.error("Failed to persist user", exc_info=exc)
        raise


async def _send_safe(chat_id: int, text: str) -> None:
    """Send a Telegram message, logging but not re-raising delivery errors."""
    try:
        await telegram_service.send_message(chat_id, text)
    except Exception as exc:
        logger.error(
            "Failed to send message",
            extra={"chat_id": chat_id},
            exc_info=exc,
        )
