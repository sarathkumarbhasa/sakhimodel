"""
Voice-to-text service for Sakhi.

Flow:
  1. Telegram sends a voice message → we get a file_id
  2. We call getFile to get the file_path on Telegram servers
  3. We download the .oga / .ogg file (Telegram voice is always OGG/Opus)
  4. We run OpenAI Whisper locally to transcribe it
  5. Transcribed text is returned and handled exactly like a typed message

Language → Whisper language code mapping:
  en → "english"
  hi → "hindi"
  ta → "tamil"
  te → "telugu"

Whisper "small" model is used — good balance of speed vs. accuracy for Indian
languages on a CPU server. If Render gives you enough RAM you can upgrade to
"medium" by changing WHISPER_MODEL below.
"""

import logging
import os
import tempfile

import httpx
import whisper  # openai-whisper

from app.core.config import settings
from app.core.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

_BASE_URL = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}"

# Load model once at import time (cached in memory for the process lifetime).
# "small" supports all Indian languages and runs on CPU in ~5–8 seconds.
# Change to "medium" for better accuracy if your server has more RAM.
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")

_model = None  # lazy-loaded on first voice message


def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        logger.info("Loading Whisper model '%s' (first voice message)…", WHISPER_MODEL_SIZE)
        _model = whisper.load_model(WHISPER_MODEL_SIZE)
        logger.info("Whisper model loaded.")
    return _model


# Sakhi language code → Whisper language hint
_LANG_TO_WHISPER = {
    "en": "english",
    "hi": "hindi",
    "ta": "tamil",
    "te": "telugu",
}


async def transcribe_voice(file_id: str, language: str = "en") -> str:
    """
    Download a Telegram voice file and transcribe it with Whisper.

    Args:
        file_id:  Telegram file_id from the voice message object.
        language: Sakhi language code ("en" | "hi" | "ta" | "te").

    Returns:
        Transcribed text string (stripped).

    Raises:
        TelegramAPIError: if the file cannot be downloaded.
        RuntimeError:     if Whisper transcription fails.
    """
    whisper_lang = _LANG_TO_WHISPER.get(language, "english")

    # ── Step 1: resolve file_id → download URL ────────────────────────────────
    file_path = await _get_telegram_file_path(file_id)
    download_url = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"

    # ── Step 2: download audio bytes ─────────────────────────────────────────
    audio_bytes = await _download_file(download_url)

    # ── Step 3: write to temp file and transcribe ─────────────────────────────
    # Whisper needs a file path, not bytes.
    # We use .ogg extension — Whisper (via ffmpeg) handles OGG/Opus natively.
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = _get_model()
        logger.info(
            "Transcribing voice message",
            extra={"language": whisper_lang, "file_size_kb": len(audio_bytes) // 1024},
        )
        result = model.transcribe(
            tmp_path,
            language=whisper_lang,
            fp16=False,          # fp16 needs a GPU; CPU servers must use fp32
            task="transcribe",   # "transcribe" keeps original language; use "translate" for English
        )
        text = result.get("text", "").strip()
        logger.info("Transcription done", extra={"text_preview": text[:80]})
        return text

    except Exception as exc:
        logger.error("Whisper transcription failed", exc_info=exc)
        raise RuntimeError("Could not transcribe voice message") from exc

    finally:
        # Always clean up the temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ── Private helpers ───────────────────────────────────────────────────────────

async def _get_telegram_file_path(file_id: str) -> str:
    """Call Telegram getFile API to resolve file_id → server path."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_BASE_URL}/getFile",
                params={"file_id": file_id},
            )
        if resp.status_code != 200:
            raise TelegramAPIError(f"getFile returned {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if not data.get("ok"):
            raise TelegramAPIError(f"getFile not ok: {data}")
        return data["result"]["file_path"]
    except httpx.RequestError as exc:
        raise TelegramAPIError("Network error calling getFile") from exc


async def _download_file(url: str) -> bytes:
    """Download file bytes from Telegram CDN."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            raise TelegramAPIError(f"Download failed {resp.status_code}")
        return resp.content
    except httpx.RequestError as exc:
        raise TelegramAPIError("Network error downloading voice file") from exc
