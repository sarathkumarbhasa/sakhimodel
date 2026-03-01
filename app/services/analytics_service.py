"""
Analytics service.
Thin facade over the analytics repository.
Errors are always swallowed to prevent analytics from degrading UX.
"""

import logging
from typing import Any, Optional

from app.db.analytics_repository import record_event
from app.models.analytics import AnalyticsEvent

logger = logging.getLogger(__name__)


async def track(
    telegram_id: int,
    event_type: str,
    language: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    """Fire-and-forget analytics event tracking."""
    try:
        event = AnalyticsEvent(
            telegram_id=telegram_id,
            event_type=event_type,
            language=language,
            payload=payload,
        )
        await record_event(event)
    except Exception as exc:
        logger.warning(
            "Analytics tracking failed (non-fatal)",
            extra={"event_type": event_type, "telegram_id": telegram_id},
            exc_info=exc,
        )
