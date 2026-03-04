"""
Pydantic models for User documents stored in MongoDB.
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class UserDocument(BaseModel):
    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}

    id: Optional[str] = Field(default=None, alias="_id")
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language: str = "en"
    state: str = "NEW"
    last_period_date: Optional[date] = None
    cycle_length_days: int = 28

    # Location — saved after user shares once, reused for future queries
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Pending state — waiting for location after serious symptom
    awaiting_location_for_hospital: bool = False

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("id", mode="before")
    @classmethod
    def coerce_object_id(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    @field_validator("last_period_date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> Optional[date]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        return v

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if data.get("last_period_date") and isinstance(data["last_period_date"], date):
            data["last_period_date"] = datetime(
                data["last_period_date"].year,
                data["last_period_date"].month,
                data["last_period_date"].day,
            )
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        return data
