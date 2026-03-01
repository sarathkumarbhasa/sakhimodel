"""
Input validation utilities for Sakhi.
"""

import re
from datetime import date, timedelta
from typing import Optional


DATE_PATTERNS = [
    r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$",   # DD-MM-YYYY or DD/MM/YYYY
    r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$",   # YYYY-MM-DD
]

MAX_PAST_DAYS = 180  # 6 months


def parse_date_input(text: str) -> Optional[date]:
    """
    Parse a date string from user input.
    Returns a date object or None if parsing fails.
    """
    text = text.strip()

    # Try DD-MM-YYYY / DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})$", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    # Try YYYY-MM-DD
    m = re.match(r"^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None


def validate_period_date(d: date) -> Optional[str]:
    """
    Validate a parsed period date.
    Returns an error key string if invalid, else None.
    """
    today = date.today()

    if d > today:
        return "future_date"

    if d < today - timedelta(days=MAX_PAST_DAYS):
        return "date_too_old"

    return None


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Remove leading/trailing whitespace and truncate."""
    return text.strip()[:max_length]
