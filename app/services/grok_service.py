"""
AI service via OpenRouter.
Includes mood detection, yoga links, mudra links, and frequency music links.
"""

import logging
import random
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import GrokAPIError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Sakhi, a menstrual health assistant. Be brief, warm, helpful.

MOOD RESPONSE FORMAT (sad/tired/stressed/crampy/pain/anxious):
💭 [1 empathetic line]

🥗 *Food:* item1 • item2 • item3
🧘 *Yoga:* pose1 • pose2
💡 [1 quick tip]
⚠️ _Consult a doctor if severe._

HEALTH QUESTION FORMAT:
[Answer in 2-3 short sentences max]
⚠️ _Consult a doctor if needed._

RULES:
- Max 70 words total
- No long paragraphs, no repeating disclaimer
- Never diagnose or prescribe
- Match user language (Telugu/Hindi/Tamil/English)"""

# ---------------------------------------------------------------------------
# Mood keyword detection
# ---------------------------------------------------------------------------
MOOD_KEYWORDS = {
    "en": [
        "sad", "angry", "irritable", "tired", "exhausted", "stressed", "anxious",
        "depressed", "overwhelmed", "moody", "low", "upset", "crying", "emotional",
        "bloated", "crampy", "cramps", "pain", "nauseous", "dizzy", "headache",
        "fatigue", "mood swing", "not feeling well", "feeling bad", "feeling down",
        "cant sleep", "can't sleep", "no energy", "restless", "heavy", "worried",
        "scared", "lonely", "hopeless", "panic", "irritated",
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

# ---------------------------------------------------------------------------
# Mood → category mapping
# ---------------------------------------------------------------------------
def classify_mood(text: str) -> str:
    """Map message to a mood category for targeted recommendations."""
    t = text.lower()
    if any(w in t for w in ["pain", "cramp", "నొప్పి", "కడుపునొప్పి", "दर्द", "வலி"]):
        return "pain"
    if any(w in t for w in ["stress", "anxious", "panic", "worried", "తనాव", "ఒత్తిడి", "तनाव", "மன அழுத்தம்"]):
        return "stress"
    if any(w in t for w in ["sad", "cry", "depress", "lonely", "hopeless", "విచారం", "ఏడుపు", "उदास", "சோகம்"]):
        return "sadness"
    if any(w in t for w in ["tired", "exhaust", "fatigue", "no energy", "అలసట", "నీరసం", "थकान", "சோர்வு"]):
        return "fatigue"
    if any(w in t for w in ["angry", "irritab", "కోపం", "चिड़चिड़ा", "கோபம்"]):
        return "anger"
    if any(w in t for w in ["sleep", "నిద్రలేమి", "नींद", "தூக்கமின்மை"]):
        return "insomnia"
    return "general"

# ---------------------------------------------------------------------------
# Yoga links by mood
# ---------------------------------------------------------------------------
YOGA_BY_MOOD: dict[str, list[tuple]] = {
    "pain": [
        ("Child's Pose", "https://www.youtube.com/results?search_query=balasana+period+cramp+relief"),
        ("Supine Twist", "https://www.youtube.com/results?search_query=supine+twist+period+pain"),
        ("Cat-Cow", "https://www.youtube.com/results?search_query=cat+cow+stretch+menstrual+pain"),
    ],
    "stress": [
        ("Child's Pose", "https://www.youtube.com/results?search_query=childs+pose+stress+relief"),
        ("Legs Up Wall", "https://www.youtube.com/results?search_query=viparita+karani+anxiety+relief"),
        ("Forward Fold", "https://www.youtube.com/results?search_query=standing+forward+fold+stress"),
    ],
    "sadness": [
        ("Heart Opener", "https://www.youtube.com/results?search_query=heart+opening+yoga+sadness"),
        ("Butterfly Pose", "https://www.youtube.com/results?search_query=baddha+konasana+mood+lift"),
        ("Sun Salutation", "https://www.youtube.com/results?search_query=surya+namaskar+depression+yoga"),
    ],
    "fatigue": [
        ("Legs Up Wall", "https://www.youtube.com/results?search_query=viparita+karani+fatigue+energy"),
        ("Corpse Pose", "https://www.youtube.com/results?search_query=savasana+restore+energy"),
        ("Restorative Yoga", "https://www.youtube.com/results?search_query=restorative+yoga+tiredness"),
    ],
    "anger": [
        ("Lion's Breath", "https://www.youtube.com/results?search_query=lion+breath+pranayama+anger"),
        ("Seated Twist", "https://www.youtube.com/results?search_query=seated+spinal+twist+anger+release"),
        ("Child's Pose", "https://www.youtube.com/results?search_query=childs+pose+calm+anger"),
    ],
    "insomnia": [
        ("Legs Up Wall", "https://www.youtube.com/results?search_query=yoga+for+sleep+legs+up+wall"),
        ("Body Scan", "https://www.youtube.com/results?search_query=yoga+nidra+insomnia+sleep"),
        ("Forward Fold", "https://www.youtube.com/results?search_query=forward+fold+bedtime+yoga"),
    ],
    "general": [
        ("Child's Pose", "https://www.youtube.com/results?search_query=balasana+period+pain"),
        ("Legs Up Wall", "https://www.youtube.com/results?search_query=viparita+karani+menstrual"),
        ("Cat-Cow", "https://www.youtube.com/results?search_query=cat+cow+stretch+period"),
    ],
}

# ---------------------------------------------------------------------------
# Mudras by mood
# ---------------------------------------------------------------------------
MUDRAS_BY_MOOD: dict[str, list[tuple]] = {
    "pain": [
        ("Apana Mudra 🤲", "https://www.youtube.com/results?search_query=apana+mudra+menstrual+pain"),
        ("Shakti Mudra 🤲", "https://www.youtube.com/results?search_query=shakti+mudra+period+cramps"),
    ],
    "stress": [
        ("Gyan Mudra 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+stress+anxiety+relief"),
        ("Prana Mudra 🤲", "https://www.youtube.com/results?search_query=prana+mudra+calm+stress"),
    ],
    "sadness": [
        ("Ahamkara Mudra 🤲", "https://www.youtube.com/results?search_query=ahamkara+mudra+confidence+sadness"),
        ("Surya Mudra 🤲", "https://www.youtube.com/results?search_query=surya+mudra+energy+mood"),
    ],
    "fatigue": [
        ("Prana Mudra 🤲", "https://www.youtube.com/results?search_query=prana+mudra+energy+fatigue"),
        ("Surya Mudra 🤲", "https://www.youtube.com/results?search_query=surya+mudra+vitality+tiredness"),
    ],
    "anger": [
        ("Shunya Mudra 🤲", "https://www.youtube.com/results?search_query=shunya+mudra+anger+calm"),
        ("Vayu Mudra 🤲", "https://www.youtube.com/results?search_query=vayu+mudra+anger+relief"),
    ],
    "insomnia": [
        ("Gyan Mudra 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+sleep+insomnia"),
        ("Yoni Mudra 🤲", "https://www.youtube.com/results?search_query=yoni+mudra+deep+sleep"),
    ],
    "general": [
        ("Gyan Mudra 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+menstrual+health"),
        ("Apana Mudra 🤲", "https://www.youtube.com/results?search_query=apana+mudra+women+health"),
    ],
}

# ---------------------------------------------------------------------------
# Healing frequency music by mood
# ---------------------------------------------------------------------------
MUSIC_BY_MOOD: dict[str, tuple] = {
    "pain":     ("174 Hz – Pain Relief 🎵", "https://www.youtube.com/results?search_query=174hz+pain+relief+solfeggio"),
    "stress":   ("432 Hz – Deep Calm 🎵",   "https://www.youtube.com/results?search_query=432hz+stress+relief+calm+music"),
    "sadness":  ("528 Hz – Heart Heal 🎵",  "https://www.youtube.com/results?search_query=528hz+emotional+healing+music"),
    "fatigue":  ("285 Hz – Energy Boost 🎵","https://www.youtube.com/results?search_query=285hz+energy+healing+frequency"),
    "anger":    ("396 Hz – Release Fear 🎵","https://www.youtube.com/results?search_query=396hz+release+anger+solfeggio"),
    "insomnia": ("Delta 1-4 Hz – Sleep 🎵", "https://www.youtube.com/results?search_query=delta+waves+deep+sleep+music"),
    "general":  ("432 Hz – Balance 🎵",     "https://www.youtube.com/results?search_query=432hz+menstrual+cycle+healing"),
}

# ---------------------------------------------------------------------------
# Section titles by language
# ---------------------------------------------------------------------------
SECTION_TITLES = {
    "en": {"yoga": "🧘 *Yoga*", "mudra": "🤲 *Mudras*", "music": "🎵 *Healing Music*"},
    "hi": {"yoga": "🧘 *योग*",  "mudra": "🤲 *मुद्राएं*", "music": "🎵 *उपचार संगीत*"},
    "ta": {"yoga": "🧘 *யோகா*", "mudra": "🤲 *முத்திரைகள்*", "music": "🎵 *குணமளிக்கும் இசை*"},
    "te": {"yoga": "🧘 *యోగా*", "mudra": "🤲 *ముద్రలు*",    "music": "🎵 *హీలింగ్ మ్యూజిక్*"},
}


def detect_mood(text: str, language: str = "en") -> bool:
    text_lower = text.lower()
    keywords = MOOD_KEYWORDS.get(language, []) + MOOD_KEYWORDS["en"]
    return any(k in text_lower for k in keywords)


def build_wellness_links(mood_category: str, language: str = "en") -> str:
    """Build yoga + mudra + music links section."""
    titles = SECTION_TITLES.get(language, SECTION_TITLES["en"])
    yoga_poses = YOGA_BY_MOOD.get(mood_category, YOGA_BY_MOOD["general"])
    mudras = MUDRAS_BY_MOOD.get(mood_category, MUDRAS_BY_MOOD["general"])
    music_name, music_url = MUSIC_BY_MOOD.get(mood_category, MUSIC_BY_MOOD["general"])

    lines = []

    # Yoga
    lines.append(titles["yoga"])
    for name, url in yoga_poses:
        lines.append(f"• [{name}]({url})")

    lines.append("")

    # Mudras
    lines.append(titles["mudra"])
    for name, url in mudras:
        lines.append(f"• [{name}]({url})")

    lines.append("")

    # Frequency music
    lines.append(titles["music"])
    lines.append(f"• [{music_name}]({music_url})")

    return "\n".join(lines)


async def ask_grok(user_message: str, language: str = "en") -> str:
    lang_instruction = {
        "hi": "Reply in Hindi.",
        "ta": "Reply in Tamil.",
        "te": "Reply in Telugu.",
    }.get(language, "Reply in English.")

    is_mood = detect_mood(user_message, language)
    mood_category = classify_mood(user_message) if is_mood else "general"
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

        # Append wellness links for mood responses
        if is_mood:
            wellness = build_wellness_links(mood_category, language)
            content = f"{content.strip()}\n\n{wellness}"

        logger.info("OpenRouter success", extra={
            "tokens": data.get("usage", {}).get("total_tokens"),
            "mood": is_mood,
            "mood_category": mood_category,
        })
        return content.strip()

    except httpx.TimeoutException as exc:
        raise GrokAPIError("OpenRouter timed out") from exc
    except httpx.RequestError as exc:
        raise GrokAPIError("Network error contacting OpenRouter") from exc
