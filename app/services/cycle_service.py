"""
Deterministic menstrual cycle prediction service.
Pure functions — no I/O, fully testable.
"""

from datetime import date, timedelta

from app.core.config import settings


def predict_next_period(last_period_date: date, cycle_length_days: int | None = None) -> date:
    """Return the predicted start date of the next period."""
    length = cycle_length_days or settings.DEFAULT_CYCLE_LENGTH_DAYS
    return last_period_date + timedelta(days=length)


def days_until_next_period(next_period_date: date) -> int:
    """Return days remaining until next period. Negative if overdue."""
    return (next_period_date - date.today()).days


def is_cycle_related_query(text: str) -> bool:
    """
    Heuristic classifier: decide whether a message is about cycle prediction
    vs a general health/AI question.

    Returns True  → handle with deterministic logic
    Returns False → delegate to Grok AI
    """
    text_lower = text.lower().strip()

    # Commands we handle deterministically
    deterministic_triggers = [
        "next period", "when is my", "days left", "cycle", "period date",
        "predict", "my period", "days until", "period tracker",
        "अगला मासिक", "मासिक कब", "cycle prediction", "period prediction",
        "அடுத்த மாதவிடாய்", "மாதவிடாய் எப்போது",
    ]

    return any(trigger in text_lower for trigger in deterministic_triggers)


def format_date(d: date) -> str:
    """Return date in a human-friendly format."""
    return d.strftime("%d %B %Y")
