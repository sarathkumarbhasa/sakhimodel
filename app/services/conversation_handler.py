"""
Conversation handler — the brain of Sakhi.

State machine:
  NEW / AWAITING_LANGUAGE      → ask language
  AWAITING_LAST_PERIOD         → parse date, run cycle prediction
  ACTIVE                       → route messages
    - casual                   → warm reply
    - serious symptom          → ask for location
    - location shared          → find nearest hospital
    - cycle query              → deterministic prediction
    - health question          → Grok AI
"""

import logging
from datetime import date

from app.core.constants import ConversationState, SUPPORTED_LANGUAGES, get_message
from app.core.exceptions import DatabaseError, GrokAPIError
from app.db import user_repository
from app.models.analytics import EventType
from app.models.telegram import TelegramMessage
from app.models.user import UserDocument
from app.services import analytics_service, grok_service, telegram_service
from app.services.cycle_service import (
    predict_next_period, days_until_next_period,
    is_cycle_related_query, format_date,
)
from app.services.hospital_service import find_hospitals
from app.services.symptom_service import (
    is_serious_symptom, get_location_request, get_searching_msg,
)
from app.utils.validators import (
    parse_date_input, validate_period_date, sanitize_text,
    is_casual_message, get_casual_response,
)

logger = logging.getLogger(__name__)


async def handle_message(message: TelegramMessage) -> None:
    """Entry point for all incoming messages."""
    if not message.from_:
        logger.warning("Received message without sender info")
        return

    telegram_id = message.from_.id
    chat_id = message.chat.id
    raw_text = message.text or ""
    text = sanitize_text(raw_text)

    logger.info("Incoming message", extra={
        "telegram_id": telegram_id,
        "has_location": message.location is not None,
        "text_length": len(text),
    })

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
        return

    # /start resets state
    if text.lower() in {"/start", "/start@sakhibot"}:
        await _handle_start(user, chat_id)
        return

    # Location message — user shared their location
    if message.location:
        await _handle_location(user, chat_id, message.location.latitude, message.location.longitude)
        return

    # Route by state
    if user.state in (ConversationState.NEW, ConversationState.AWAITING_LANGUAGE):
        await _handle_language_selection(user, chat_id, text)
    elif user.state == ConversationState.AWAITING_LAST_PERIOD:
        await _handle_period_date(user, chat_id, text)
    elif user.state == ConversationState.ACTIVE:
        await _handle_active(user, chat_id, text)
    else:
        await _handle_start(user, chat_id)


# ---------------------------------------------------------------------------
# State handlers
# ---------------------------------------------------------------------------

async def _handle_start(user: UserDocument, chat_id: int) -> None:
    user.state = ConversationState.AWAITING_LANGUAGE
    user.last_period_date = None
    user.awaiting_location_for_hospital = False
    await _save_user(user)
    await _send_safe(chat_id, get_message("en", "welcome"))
    await analytics_service.track(user.telegram_id, EventType.USER_START)


async def _handle_language_selection(user: UserDocument, chat_id: int, text: str) -> None:
    lang_code = SUPPORTED_LANGUAGES.get(text.lower().strip())
    if not lang_code:
        await _send_safe(chat_id, get_message(user.language, "language_unknown"))
        return

    user.language = lang_code
    user.state = ConversationState.AWAITING_LAST_PERIOD
    await _save_user(user)
    await _send_safe(chat_id, get_message(lang_code, "language_set"))
    await _send_safe(chat_id, get_message(lang_code, "ask_last_period"))


async def _handle_period_date(user: UserDocument, chat_id: int, text: str) -> None:
    lang = user.language
    parsed = parse_date_input(text)

    if parsed is None:
        await _send_safe(chat_id, get_message(lang, "invalid_date"))
        return

    error_key = validate_period_date(parsed)
    if error_key:
        await _send_safe(chat_id, get_message(lang, error_key))
        return

    user.last_period_date = parsed
    user.state = ConversationState.ACTIVE
    await _save_user(user)
    await _send_cycle_prediction(user, chat_id)


async def _handle_active(user: UserDocument, chat_id: int, text: str) -> None:
    lang = user.language

    # 1. Casual message
    if is_casual_message(text, lang):
        await _send_safe(chat_id, get_casual_response(lang))
        return

    # 2. Serious symptom → ask for location
    if is_serious_symptom(text, lang):
        await telegram_service.send_typing_action(chat_id)
        # Get AI response first
        try:
            ai_reply = await grok_service.ask_grok(text, language=lang)
            await _send_safe(chat_id, ai_reply)
        except GrokAPIError:
            pass  # still show location request even if AI fails

        # Ask for location
        user.awaiting_location_for_hospital = True
        await _save_user(user)
        await _send_safe(chat_id, get_location_request(lang))
        return

    # 3. If user was asked for location but sent text instead
    if user.awaiting_location_for_hospital:
        # If they type their city name, do a text-based fallback
        if len(text.split()) <= 4:
            await _handle_city_text_fallback(user, chat_id, text)
        else:
            # They ignored location request, reset flag
            user.awaiting_location_for_hospital = False
            await _save_user(user)

    # 4. Cycle query
    if is_cycle_related_query(text):
        if user.last_period_date:
            await _send_cycle_prediction(user, chat_id)
        else:
            user.state = ConversationState.AWAITING_LAST_PERIOD
            await _save_user(user)
            await _send_safe(chat_id, get_message(lang, "ask_last_period"))
        return

    # 5. General AI health question
    await telegram_service.send_typing_action(chat_id)
    await analytics_service.track(user.telegram_id, EventType.AI_QUERY, language=lang)

    try:
        reply = await grok_service.ask_grok(text, language=lang)
        await _send_safe(chat_id, reply)
    except GrokAPIError as exc:
        logger.warning("Grok AI failed", exc_info=exc)
        await _send_safe(chat_id, get_message(lang, "ai_error"))


async def _handle_location(user: UserDocument, chat_id: int, lat: float, lon: float) -> None:
    """User shared their location — find nearest hospitals."""
    lang = user.language

    # Save location for future use
    user.latitude = lat
    user.longitude = lon
    user.awaiting_location_for_hospital = False
    await _save_user(user)

    await _send_safe(chat_id, get_searching_msg(lang))
    await telegram_service.send_typing_action(chat_id)

    try:
        result = await find_hospitals(lat, lon, language=lang)
        await _send_safe(chat_id, result)
    except Exception as exc:
        logger.error("Hospital finder failed", exc_info=exc)
        await _send_safe(chat_id, "🚨 *Emergency:* 108  |  🏥 *Health Helpline:* 104")


async def _handle_city_text_fallback(user: UserDocument, chat_id: int, city: str) -> None:
    """User typed city name instead of sharing location — show Google Maps link."""
    lang = user.language
    maps_url = f"https://www.google.com/maps/search/government+hospital+near+{city.replace(' ', '+')}"
    fallback = {
        "en": f"📍 [Find govt hospitals near {city}]({maps_url})\n\n🚨 *Emergency:* 108  |  🏥 *Helpline:* 104",
        "hi": f"📍 [{city} के पास सरकारी अस्पताल]({maps_url})\n\n🚨 *आपातकाल:* 108  |  🏥 *हेल्पलाइन:* 104",
        "ta": f"📍 [{city} அருகில் அரசு மருத்துவமனை]({maps_url})\n\n🚨 *அவசரம்:* 108  |  🏥 *உதவி:* 104",
        "te": f"📍 [{city} దగ్గర ప్రభుత్వ ఆసుపత్రి]({maps_url})\n\n🚨 *అత్యవసర:* 108  |  🏥 *హెల్ప్‌లైన్:* 104",
    }
    user.awaiting_location_for_hospital = False
    await _save_user(user)
    await _send_safe(chat_id, fallback.get(lang, fallback["en"]))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _send_cycle_prediction(user: UserDocument, chat_id: int) -> None:
    last_period: date = user.last_period_date
    next_period = predict_next_period(last_period, user.cycle_length_days)
    days_remaining = days_until_next_period(next_period)
    msg = get_message(
        user.language, "prediction",
        last_period=format_date(last_period),
        next_period=format_date(next_period),
        days_remaining=str(max(days_remaining, 0)),
        cycle_length=str(user.cycle_length_days),
    )
    await _send_safe(chat_id, msg)


async def _save_user(user: UserDocument) -> None:
    try:
        await user_repository.upsert_user(user)
    except DatabaseError as exc:
        logger.error("Failed to persist user", exc_info=exc)
        raise


async def _send_safe(chat_id: int, text: str) -> None:
    try:
        await telegram_service.send_message(chat_id, text)
    except Exception as exc:
        logger.error("Failed to send message", extra={"chat_id": chat_id}, exc_info=exc)
