"""
User repository.
All MongoDB CRUD operations for user documents.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo.errors import PyMongoError

from app.core.exceptions import DatabaseError
from app.db.mongodb import get_db
from app.models.user import UserDocument

logger = logging.getLogger(__name__)

COLLECTION = "users"


async def get_user(telegram_id: int) -> Optional[UserDocument]:
    """Fetch a user document by Telegram ID."""
    try:
        db = get_db()
        doc = await db[COLLECTION].find_one({"telegram_id": telegram_id})
        if doc:
            return UserDocument(**doc)
        return None
    except PyMongoError as exc:
        logger.error("get_user failed", extra={"telegram_id": telegram_id}, exc_info=exc)
        raise DatabaseError("Failed to retrieve user") from exc


async def upsert_user(user: UserDocument) -> None:
    """Insert or update a user document."""
    try:
        db = get_db()
        now = datetime.now(tz=timezone.utc)
        update = {
            "$set": {
                **user.model_dump(exclude={"id"}, exclude_none=True),
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        }
        await db[COLLECTION].update_one(
            {"telegram_id": user.telegram_id},
            update,
            upsert=True,
        )
        logger.debug("User upserted", extra={"telegram_id": user.telegram_id})
    except PyMongoError as exc:
        logger.error("upsert_user failed", extra={"telegram_id": user.telegram_id}, exc_info=exc)
        raise DatabaseError("Failed to save user") from exc


async def update_user_fields(telegram_id: int, **fields) -> None:
    """Partial update of user fields."""
    try:
        db = get_db()
        fields["updated_at"] = datetime.now(tz=timezone.utc)
        await db[COLLECTION].update_one(
            {"telegram_id": telegram_id},
            {"$set": fields},
        )
    except PyMongoError as exc:
        logger.error("update_user_fields failed", extra={"telegram_id": telegram_id}, exc_info=exc)
        raise DatabaseError("Failed to update user") from exc


async def count_users() -> int:
    """Return total registered users."""
    try:
        return await get_db()[COLLECTION].count_documents({})
    except PyMongoError as exc:
        raise DatabaseError("Failed to count users") from exc
