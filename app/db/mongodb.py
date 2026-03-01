"""
Async MongoDB connection management via Motor.
Provides a single shared client and database instance.
"""

import logging
from typing import Optional

import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import settings
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    """Initialise Motor client and verify connectivity."""
    global _client, _db

    _client = motor.motor_asyncio.AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        tls=True,
        tlsAllowInvalidCertificates=False,
        retryWrites=True,
        w="majority",
    )
    _db = _client[settings.MONGODB_DB_NAME]

    try:
        await _client.admin.command("ping")
        logger.info("MongoDB ping successful", extra={"db": settings.MONGODB_DB_NAME})
    except ServerSelectionTimeoutError as exc:
        logger.critical("MongoDB connection failed", exc_info=exc)
        raise DatabaseError("Cannot reach MongoDB Atlas") from exc

    await _ensure_indexes()


async def disconnect_db() -> None:
    """Close the Motor client on shutdown."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database handle."""
    if _db is None:
        raise DatabaseError("Database not initialised. Call connect_db() first.")
    return _db


async def _ensure_indexes() -> None:
    """Create necessary indexes idempotently."""
    db = get_db()

    await db.users.create_indexes([
        IndexModel([("telegram_id", ASCENDING)], unique=True, name="uq_telegram_id"),
        IndexModel([("updated_at", ASCENDING)], name="idx_updated_at"),
    ])

    await db.analytics.create_indexes([
        IndexModel([("telegram_id", ASCENDING)], name="idx_analytics_user"),
        IndexModel([("event_type", ASCENDING)], name="idx_event_type"),
        IndexModel([("created_at", ASCENDING)], name="idx_created_at"),
    ])

    logger.info("MongoDB indexes ensured")
