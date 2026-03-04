"""
Input validation and message classification utilities for Sakhi.
"""

import re
from datetime import date, timedelta
from typing import Optional


DATE_PATTERNS = [
    r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$",
    r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$",
]

MAX_PAST_DAYS = 180  # 6 months

# ---------------------------------------------------------------------------
# Casual / small-talk phrases — bot should respond warmly, not with health tips
# ---------------------------------------------------------------------------
CASUAL_PHRASES: dict[str, list[str]] = {
    "en": [
        "ok", "okay", "thanks", "thank you", "bye", "goodbye", "see you",
        "hello", "hi", "hey", "good morning", "good night", "good evening",
        "how are you", "nice", "great", "cool", "sure", "alright", "got it",
        "i am here", "i will be here", "i'll stay", "still here", "i'm here",
    ],
    "hi": [
        "ठीक है", "धन्यवाद", "शुक्रिया", "नमस्ते", "हाँ", "हां", "अच्छा",
        "ओके", "बाय", "अलविदा", "मैं यहाँ हूँ", "मैं रहूँगी",
    ],
    "ta": [
        "சரி", "நன்றி", "வணக்கம்", "ஆம்", "நான் இங்கே இருக்கிறேன்",
        "பை", "சந்திப்போம்",
    ],
    "te": [
        "సరే", "ధన్యవాదాలు", "నమస్కారం", "అవును", "బాగుంది", "ఓకే",
        "నేను ఇంకా వుంటాను", "నేను ఇక్కడ ఉన్నాను", "నేను వుంటాను",
        "ఇంకా వుంటాను", "వుంటాను", "బై", "మళ్ళీ కలుద్దాం", "థాంక్యూ",
        "నేను ఇంకా వుంటే", "నేను ఉంటాను",
    ],
}

CASUAL_RESPONSES: dict[str, str] = {
    "en": "😊 I'm always here for you! Feel free to ask me anything about your health or cycle anytime.",
    "hi": "😊 मैं हमेशा आपके लिए यहाँ हूँ! अपने स्वास्थ्य या चक्र के बारे में कभी भी पूछें।",
    "ta": "😊 நான் எப்போதும் உங்களுக்காக இங்கே இருக்கிறேன்! உங்கள் ஆரோக்கியம் பற்றி எப்போதும் கேளுங்கள்.",
    "te": "😊 నేను ఎప్పుడూ మీకోసం ఇక్కడ ఉన్నాను! మీ ఆరోగ్యం లేదా చక్రం గురించి ఎప్పుడైనా అడగండి।",
}


def is_casual_message(text: str, language: str = "en") -> bool:
    """Return True if the message is casual small-talk, not a health query."""
    text_clean = text.lower().strip()

    # Very short messages (1-2 words) that are not health related
    if len(text_clean.split()) <= 2:
        casual = CASUAL_PHRASES.get(language, []) + CASUAL_PHRASES["en"]
        if any(phrase in text_clean for phrase in casual):
            return True

    # Check full phrase match
    casual_all = CASUAL_PHRASES.get(language, []) + CASUAL_PHRASES["en"]
    if any(phrase in text_clean for phrase in casual_all):
        return True

    return False


def get_casual_response(language: str = "en") -> str:
    """Return a warm casual reply in the user's language."""
    return CASUAL_RESPONSES.get(language, CASUAL_RESPONSES["en"])


def parse_date_input(text: str) -> Optional[date]:
    """Parse a date string from user input. Returns date or None."""
    text = text.strip()

    # DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})$", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    # YYYY-MM-DD
    m = re.match(r"^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None


def validate_period_date(d: date) -> Optional[str]:
    """Returns an error key string if invalid, else None."""
    today = date.today()
    if d > today:
        return "future_date"
    if d < today - timedelta(days=MAX_PAST_DAYS):
        return "date_too_old"
    return None


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Remove leading/trailing whitespace and truncate."""
    return text.strip()[:max_length]
