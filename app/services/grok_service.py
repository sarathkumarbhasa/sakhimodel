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

SYSTEM_PROMPT = """You are Sakhi, a compassionate menstrual health assistant. You help users understand:
- Menstrual cycle patterns and irregularities
- PMS symptoms and management
- Period pain relief (non-prescription)
- General reproductive health awareness
- Hygiene and self-care during periods

STRICT RULES:
1. NEVER diagnose medical conditions.
2. NEVER recommend specific prescription medications or dosages.
3. ALWAYS recommend consulting a qualified gynaecologist or doctor for:
   - Severe pain, abnormal bleeding, or irregular cycles
   - Any symptoms that cause significant distress
4. Respond with warmth, empathy, and cultural sensitivity.
5. Keep responses concise (under 250 words) and easy to understand.
6. If the question is outside menstrual/reproductive health, politely redirect.
7. Add a brief disclaimer when discussing health-related advice.

You are NOT a replacement for professional medical care."""


async def ask_grok(user_message: str, language: str = "en") -> str:
    """
    Send a message to OpenRouter and return the assistant's reply.
    Raises GrokAPIError on network failure, timeout, or API error.
    """
    lang_instruction = {
        "hi": "Respond in Hindi (Devanagari script).",
        "ta": "Respond in Tamil script.",
    }.get(language, "Respond in English.")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{lang_instruction}\n\n{user_message}"},
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
        "temperature": 0.6,
    }

    logger.info(
        "Calling OpenRouter API",
        extra={"model": settings.GROK_MODEL, "language": language},
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

        logger.info(
            "OpenRouter API success",
            extra={
                "tokens_used": data.get("usage", {}).get("total_tokens"),
                "language": language,
                "model": settings.GROK_MODEL,
            },
        )
        return content.strip()

    except httpx.TimeoutException as exc:
        logger.warning("OpenRouter API timeout", exc_info=exc)
        raise GrokAPIError("OpenRouter request timed out") from exc
    except httpx.RequestError as exc:
        logger.error("OpenRouter API network error", exc_info=exc)
        raise GrokAPIError("Network error contacting OpenRouter") from exc
