"""
Pydantic models for analytics events.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class AnalyticsEvent(BaseModel):
    telegram_id: int
    event_type: str
    payload: Optional[dict[str, Any]] = None
    language: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class EventType:
    USER_START = "user_start"
    LANGUAGE_SET = "language_set"
    PERIOD_DATE_SET = "period_date_set"
    CYCLE_PREDICTED = "cycle_predicted"
    AI_QUERY = "ai_query"
    AI_ERROR = "ai_error"
    DB_ERROR = "db_error"
    INVALID_INPUT = "invalid_input"
