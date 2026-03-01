"""
Analytics repository.
Stores and queries structured analytics events.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from pymongo.errors import PyMongoError

from app.core.exceptions import DatabaseError
from app.db.mongodb import get_db
from app.models.analytics import AnalyticsEvent

logger = logging.getLogger(__name__)

COLLECTION = "analytics"


async def record_event(event: AnalyticsEvent) -> None:
    """Persist a single analytics event. Errors are logged but not re-raised
    so analytics failures never interrupt user-facing flows."""
    try:
        db = get_db()
        await db[COLLECTION].insert_one(
            event.model_dump(exclude_none=True)
        )
        logger.debug(
            "Analytics event recorded",
            extra={"event_type": event.event_type, "telegram_id": event.telegram_id},
        )
    except PyMongoError as exc:
        logger.warning("Analytics event failed to persist", exc_info=exc)


async def get_summary() -> dict[str, Any]:
    """Aggregate summary stats for the admin endpoint."""
    try:
        db = get_db()
        pipeline = [
            {
                "$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1},
                    "unique_users": {"$addToSet": "$telegram_id"},
                }
            },
            {"$project": {"event_type": "$_id", "count": 1, "unique_users": {"$size": "$unique_users"}}},
            {"$sort": {"count": -1}},
        ]
        cursor = db[COLLECTION].aggregate(pipeline)
        results = await cursor.to_list(length=100)

        total_events = sum(r["count"] for r in results)

        return {
            "total_events": total_events,
            "breakdown": [
                {
                    "event_type": r["event_type"],
                    "count": r["count"],
                    "unique_users": r["unique_users"],
                }
                for r in results
            ],
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
    except PyMongoError as exc:
        raise DatabaseError("Failed to aggregate analytics") from exc
