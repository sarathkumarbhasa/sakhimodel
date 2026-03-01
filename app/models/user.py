"""
Pydantic models for User documents stored in MongoDB.
"""

from datetime import date, datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class UserDocument(BaseModel):
    """Mirrors the MongoDB user document schema."""

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}

    id: Optional[str] = Field(default=None, alias="_id")
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language: str = "en"
    state: str = "NEW"
    last_period_date: Optional[date] = None
    cycle_length_days: int = 28
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        # Convert date to datetime for MongoDB compatibility
        if data.get("last_period_date") and isinstance(data["last_period_date"], date):
            data["last_period_date"] = datetime(
                data["last_period_date"].year,
                data["last_period_date"].month,
                data["last_period_date"].day,
            )
        # Remove None _id to avoid inserting null
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        return data
