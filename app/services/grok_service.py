"""
AI service via OpenRouter.
Uses httpx async client to call OpenRouter's OpenAI-compatible /v1/chat/completions endpoint.
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import GrokAPIError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Sakhi, a warm and caring menstrual health assistant.

MOOD DETECTION RULE:
If the user expresses any mood or emotion (sad, anxious, irritable, tired, stressed, angry, low, overwhelmed, happy, bloated, crampy, mood swings, etc.) — respond EXACTLY in this format:

💭 [One empathetic sentence acknowledging their mood]

🥗 *Food Tips*
• [Food tip 1]
• [Food tip 2]
• [Food tip 3]

🧘 *Yoga & Movement*
• [Pose name] — [one line benefit]
• [Pose name] — [one line benefit]

💡 *Quick Tip*
[One concise practical tip]

⚠️ _Disclaimer: This is general wellness advice. Consult a doctor if symptoms are severe._

---

FOR ALL OTHER HEALTH QUESTIONS (non-mood):
- Short paragraphs, max 2-3 sentences each
- Use bullet points (•) for lists
- Under 150 words total
- End with one short follow-up question
- Always add a one-line disclaimer at the end

RULES:
1. NEVER diagnose medical conditions
2. NEVER recommend prescription medications
3. Always suggest consulting a doctor for severe symptoms
4. Match user language exactly:
   - Hindi → respond fully in Hindi (Devanagari)
   - Tamil → respond fully in Tamil script
   - Telugu → respond fully in Telugu script
   - English → respond in English
5. Keep tone warm, sisterly, supportive

You are NOT a replacement for professional medical care."""


# Yoga poses with YouTube search links for period/mood relief
YOGA_LINKS = [
    {
        "name": "Child's Pose (Balasana)",
        "benefit": "Releases pelvic tension & calms the mind",
        "url": "https://www.youtube.com/results?search_query=balasana+for+period+pain",
    },
    {
        "name": "Legs Up the Wall (Viparita Karani)",
        "benefit": "Reduces fatigue & eases cramps",
        "url": "https://www.youtube.com/results?search_query=viparita+karani+menstrual+relief",
    },
    {
        "name": "Supine Twist (Supta Matsyendrasana)",
        "benefit": "Relieves lower back pain & bloating",
        "url": "https://www.youtube.com/results?search_query=supine+twist+period+cramps",
    },
    {
        "name": "Cat-Cow Stretch (Marjaryasana)",
        "benefit": "Eases cramps & improves circulation",
        "url": "https://www.youtube.com/results?search_query=cat+cow+stretch+period+pain",
    },
    {
        "name": "Butterfly Pose (Baddha Konasana)",
        "benefit": "Opens hips & reduces PMS discomfort",
        "url": "https://www.youtube.com/results?search_query=butterfly+pose+PMS+relief",
    },
]

MOOD_KEYWORDS = {
    "en": [
        "sad", "angry", "irritable", "tired", "exhausted", "stressed", "anxious",
        "depressed", "overwhelmed", "moody", "low", "upset", "crying", "emotional",
        "bloated", "crampy", "cramps", "pain", "uncomfortable", "nauseous", "dizzy",
        "headache", "fatigue", "mood swing", "not feeling well", "feeling bad",
        "feeling down", "cant sleep", "can't sleep", "no energy", "restless",
        "heavy", "irritated", "hopeless", "lonely", "panic", "worried",
    ],
    "hi": [
        "उदास", "थकान", "दर्द", "चिड़चिड़ा", "तनाव", "घबराहट", "मूड",
        "रो", "नींद", "थका", "सिरदर्द", "मतली", "भारी", "अकेला",
        "परेशान", "दर्द", "बेचैन", "थकी", "कमज़ोर",
    ],
    "ta": [
        "சோர்வு", "வலி", "கோபம்", "மன அழுத்தம்", "தலைவலி", "குமட்டல்",
        "தூக்கமின்மை", "மனநிலை", "அழுகை", "கஷ்டம்", "பயம்", "கவலை",
    ],
    "te": [
        "విచారం", "అలసట", "నొప్పి", "కోపం", "ఒత్తిడి", "ఆందోళన",
        "తలనొప్పి", "వికారం", "నిద్రలేమి", "మూడ్", "భారంగా", "ఒంటరిగా",
        "అలసిన", "బాధగా", "నీరసం", "కడుపునొప్పి", "ఏడుపు", "భయం",
    ],
}


def detect_mood(text: str, language: str = "en") -> bool:
    """Return True if message contains mood/feeling indicators."""
    text_lower = text.lower()
    keywords = MOOD_KEYWORDS.get(language, MOOD_KEYWORDS["en"])
    all_keywords = list(set(keywords + MOOD_KEYWORDS["en"]))
    return any(keyword in text_lower for keyword in all_keywords)


def build_yoga_links_text(language: str = "en") -> str:
    """Build a formatted yoga links section based on language."""
    labels = {
        "en": ("🧘 *Yoga Videos for You*", "Watch"),
        "hi": ("🧘 *आपके लिए योग वीडियो*", "देखें"),
        "ta": ("🧘 *உங்களுக்கான யோகா வீடியோக்கள்*", "பாருங்கள்"),
        "te": ("🧘 *మీకోసం యోగా వీడియోలు*", "చూడండి"),
    }
    title, watch_word = labels.get(language, labels["en"])

    lines = [title]
    for pose in YOGA_LINKS[:3]:
        lines.append(f"• [{pose['name']}]({pose['url']}) — {pose['benefit']}")

    return "\n".join(lines)


async def ask_grok(user_message: str, language: str = "en") -> str:
    """
    Send a message to OpenRouter and return the assistant's reply.
    Raises GrokAPIError on network failure, timeout, or API error.
    """
    lang_instruction = {
        "hi": "Respond fully in Hindi (Devanagari script).",
        "ta": "Respond fully in Tamil script.",
        "te": "Respond fully in Telugu script.",
    }.get(language, "Respond in English.")

    is_mood = detect_mood(user_message, language)
    mood_hint = ""
    if is_mood:
        mood_hint = "\n[MOOD DETECTED — use the mood response format with Food Tips, Yoga & Movement, and Quick Tip sections. Do NOT include yoga links — they will be appended separately.]"

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
        "max_tokens": settings.GROK_MAX_TOKENS,
        "temperature": 0.65,
    }

    logger.info(
        "Calling OpenRouter API",
        extra={
            "model": settings.GROK_MODEL,
            "language": language,
            "mood_detected": is_mood,
        },
    )

    try:
        async with httpx.AsyncClient(
            base_url=settings.GROK_BASE_URL,
            timeout=httpx.Timeout(
                connect=5.0,
                read=settings.GROK_TIMEOUT_SECONDS,
                write=5.0,
                pool=2.0,
            ),
        ) as client:
            response = await client.post("/chat/completions", headers=headers, json=payload)

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(
                "OpenRouter API non-200 response",
                extra={
                    "status_code": response.status_code,
                    "detail": error_detail,
                    "model": settings.GROK_MODEL,
                },
            )
            raise GrokAPIError(f"OpenRouter API returned {response.status_code}: {error_detail}")

        data = response.json()
        content: Optional[str] = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )

        if not content:
            raise GrokAPIError("Empty response from OpenRouter")

        # Append yoga video links for mood responses
        if is_mood:
            yoga_section = build_yoga_links_text(language)
            content = f"{content.strip()}\n\n{yoga_section}"

        logger.info(
            "OpenRouter API success",
            extra={
                "tokens_used": data.get("usage", {}).get("total_tokens"),
                "language": language,
                "mood_detected": is_mood,
            },
        )
        return content.strip()

    except httpx.TimeoutException as exc:
        logger.warning("OpenRouter API timeout", exc_info=exc)
        raise GrokAPIError("OpenRouter request timed out") from exc
    except httpx.RequestError as exc:
        logger.error("OpenRouter API network error", exc_info=exc)
        raise GrokAPIError("Network error contacting OpenRouter") from exc
