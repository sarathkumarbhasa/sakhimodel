"""
Health check endpoint.
Used by Render, load balancers, and uptime monitors.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.mongodb import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    summary="Service health check",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> JSONResponse:
    """Return service status including DB connectivity."""
    db_status = "ok"
    db_latency_ms: float | None = None

    try:
        import time
        t0 = time.monotonic()
        await get_db().command("ping")
        db_latency_ms = round((time.monotonic() - t0) * 1000, 2)
    except Exception as exc:
        logger.warning("Health check DB ping failed", exc_info=exc)
        db_status = "error"

    overall = "healthy" if db_status == "ok" else "degraded"
    http_status = status.HTTP_200_OK if overall == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall,
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "checks": {
                "database": {
                    "status": db_status,
                    "latency_ms": db_latency_ms,
                }
            },
        },
    )
