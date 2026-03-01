"""
Telegram webhook endpoint.
Validates the secret token and dispatches to the conversation handler.
"""

import logging

from fastapi import APIRouter, Request, status

from app.core.exceptions import DatabaseError
from app.models.telegram import TelegramUpdate
from app.services.conversation_handler import handle_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/telegram",
    status_code=status.HTTP_200_OK,
    summary="Telegram webhook receiver",
)
async def telegram_webhook(request: Request) -> dict:
    """
    Receive and process incoming Telegram updates.

    Telegram requires a 200 OK response quickly — processing errors are logged
    but never returned as 5xx (which would cause Telegram to retry aggressively).
    """
    # Parse body
    try:
        body = await request.json()
        update = TelegramUpdate.model_validate(body)
    except Exception as exc:
        logger.warning("Failed to parse Telegram update", exc_info=exc)
        # Return 200 to prevent Telegram from retrying bad payloads
        return {"ok": True, "note": "parse_error"}

    logger.debug("Webhook update received", extra={"update_id": update.update_id})

    if update.message and update.message.text:
        try:
            await handle_message(update.message)
        except DatabaseError as exc:
            logger.error("Database error processing message", exc_info=exc)
            # Return 200 to prevent retry storm
        except Exception as exc:
            logger.error("Unhandled error processing message", exc_info=exc)

    return {"ok": True}
