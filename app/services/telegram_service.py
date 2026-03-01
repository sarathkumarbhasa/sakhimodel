"""
Telegram messaging service.
Wraps the Telegram Bot API for sending messages.
Channel-agnostic interface — swap this file to support WhatsApp, SMS, etc.
"""

import logging

import httpx

from app.core.config import settings
from app.core.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

_BASE_URL = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}"


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "Markdown",
    disable_web_page_preview: bool = True,
) -> None:
    """
    Send a text message to a Telegram chat.

    Raises TelegramAPIError if delivery fails.
    """
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{_BASE_URL}/sendMessage",
                json=payload,
            )

        if response.status_code != 200:
            logger.error(
                "Telegram sendMessage failed",
                extra={"chat_id": chat_id, "status": response.status_code, "body": response.text[:300]},
            )
            raise TelegramAPIError(f"Telegram API returned {response.status_code}")

        logger.debug("Message sent", extra={"chat_id": chat_id})

    except httpx.RequestError as exc:
        logger.error("Telegram network error", exc_info=exc)
        raise TelegramAPIError("Network error sending Telegram message") from exc


async def send_typing_action(chat_id: int) -> None:
    """Send 'typing…' indicator — best-effort, errors are suppressed."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{_BASE_URL}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
            )
    except Exception:
        pass  # Cosmetic — never block on this
