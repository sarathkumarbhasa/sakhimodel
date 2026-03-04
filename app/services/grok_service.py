"""
AI service via OpenRouter.
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import GrokAPIError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Sakhi, a menstrual health assistant. Be brief, warm, and helpful.

MOOD RESPONSE FORMAT (when user feels sad/tired/stressed/crampy/pain):
💭 [1 empathetic line]

🥗 *Food:* item1 • item2 • item3
🧘 *Yoga:* pose1 • pose2
💡 [1 quick tip]
⚠️ _Consult a doctor if severe._

HEALTH QUESTION FORMAT (all other questions):
[Answer in 2-3 short sentences max]
⚠️ _Consult a doctor if needed._

STRICT RULES:
- Max 80 words total per response
- No long paragraphs
- No repeating the disclaimer twice
- Never diagnose or prescribe
- Match user language (Telugu/Hindi/Tamil/English)"""

MOOD_KEYWORDS = {
    "en": [
        "sad", "angry", "irritable", "tired", "exhausted", "stressed", "anxious",
        "depressed", "overwhelmed", "moody", "low", "upset", "crying", "emotional",
        "bloated", "crampy", "cramps", "pain", "nauseous", "dizzy", "headache",
        "fatigue", "mood swing", "not feeling well", "feeling bad", "feeling down",
        "cant sleep", "can't sleep", "no energy", "restless", "heavy", "worried",
    ],
    "hi": [
        "उदास", "थकान", "दर्द", "चिड़चिड़ा", "तनाव", "घबराहट",
        "रो", "नींद", "थका", "सिरदर्द", "मतली", "भारी", "परेशान", "बेचैन",
    ],
    "ta": [
        "சோர்வு", "வலி", "கோபம்", "மன அழுத்தம்", "தலைவலி", "குமட்டல்",
        "தூக்கமின்மை", "அழுகை", "கவலை",
    ],
    "te": [
        "విచారం", "అలసట", "నొప్పి", "కోపం", "ఒత్తిడి", "ఆందోళన",
        "తలనొప్పి", "వికారం", "నిద్రలేమి", "భారంగా", "అలసిన",
        "బాధగా", "నీరసం", "కడుపునొప్పి", "ఏడుపు", "భయం",
    ],
}

YOGA_LINKS = [
    ("Child's Pose", "https://www.youtube.com/results?search_query=balasana+period+pain"),
    ("Legs Up Wall", "https://www.youtube.com/results?search_query=viparita+karani+menstrual"),
    ("Cat-Cow Stretch", "https://www.youtube.com/results?search_query=cat+cow+stretch+period"),
]

YOGA_TITLE = {
    "en": "🎥 *Yoga Videos*",
    "hi": "🎥 *योग वीडियो*",
    "ta": "🎥 *யோகா வீடியோ*",
    "te": "🎥 *యోగా వీడియోలు*",
}


def detect_mood(text: str, language: str = "en") -> bool:
    text_lower = text.lower()
    keywords = MOOD_KEYWORDS.get(language, []) + MOOD_KEYWORDS["en"]
    return any(k in text_lower for k in keywords)


def build_yoga_links(language: str = "en") -> str:
    title = YOGA_TITLE.get(language, YOGA_TITLE["en"])
    lines = [title]
    for name, url in YOGA_LINKS:
        lines.append(f"• [{name}]({url})")
    return "\n".join(lines)


async def ask_grok(user_message: str, language: str = "en") -> str:
    lang_instruction = {
        "hi": "Reply in Hindi.",
        "ta": "Reply in Tamil.",
        "te": "Reply in Telugu.",
    }.get(language, "Reply in English.")

    is_mood = detect_mood(user_message, language)
    mood_hint = "\n[MOOD DETECTED — use mood format]" if is_mood else ""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{lang_instruction}{mood_hint}\n\n{user_message}"},
    ]

    headers = {
        "Authorization": f"Bearer {settings.GROK_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://sakhimodel.onrender.com",
        "X-Title": "Sakhi Health Assistant",
    }

    payload = {
        "model": settings.GROK_MODEL,
        "messages": messages,
        "max_tokens": 180,
        "temperature": 0.5,
    }

    try:
        async with httpx.AsyncClient(
            base_url=settings.GROK_BASE_URL,
            timeout=httpx.Timeout(connect=5.0, read=settings.GROK_TIMEOUT_SECONDS, write=5.0, pool=2.0),
        ) as client:
            response = await client.post("/chat/completions", headers=headers, json=payload)

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error("OpenRouter non-200", extra={"status": response.status_code, "detail": error_detail})
            raise GrokAPIError(f"OpenRouter returned {response.status_code}: {error_detail}")

        data = response.json()
        content: Optional[str] = (
            data.get("choices", [{}])[0].get("message", {}).get("content")
        )

        if not content:
            raise GrokAPIError("Empty response from OpenRouter")

        if is_mood:
            content = f"{content.strip()}\n\n{build_yoga_links(language)}"

        logger.info("OpenRouter success", extra={"tokens": data.get("usage", {}).get("total_tokens"), "mood": is_mood})
        return content.strip()

    except httpx.TimeoutException as exc:
        raise GrokAPIError("OpenRouter timed out") from exc
    except httpx.RequestError as exc:
        raise GrokAPIError("Network error contacting OpenRouter") from exc
