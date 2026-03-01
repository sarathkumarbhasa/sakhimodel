"""
Admin analytics endpoints.
No authentication — deploy behind internal network or add your own auth later.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import DatabaseError
from app.db.analytics_repository import get_summary
from app.db.user_repository import count_users

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/analytics",
    summary="Admin: analytics summary",
)
async def analytics_summary() -> dict:
    """Return aggregated analytics across all users."""
    try:
        summary = await get_summary()
        total_users = await count_users()
        return {
            "total_users": total_users,
            **summary,
        }
    except DatabaseError as exc:
        logger.error("Analytics query failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve analytics",
        )
