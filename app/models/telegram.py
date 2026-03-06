"""
Pydantic models for Telegram Bot API webhook payloads.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    id: int
    is_bot: bool = False
    first_name: str = ""
    username: Optional[str] = None
    language_code: Optional[str] = None


class TelegramChat(BaseModel):
    id: int
    type: str


class TelegramLocation(BaseModel):
    latitude: float
    longitude: float


class TelegramVoice(BaseModel):
    """
    Telegram voice message object.
    Sent when a user records and sends a voice note in the chat.
    Audio is always OGG format encoded with OPUS codec.
    """
    file_id: str                     # Use this to download via getFile
    file_unique_id: str              # Stable unique id (not for downloading)
    duration: int                    # Length in seconds
    mime_type: Optional[str] = None  # "audio/ogg"
    file_size: Optional[int] = None  # bytes


class TelegramMessage(BaseModel):
    message_id: int
    from_: Optional[TelegramUser] = Field(None, alias="from")
    chat: TelegramChat
    text: Optional[str] = None
    location: Optional[TelegramLocation] = None
    voice: Optional[TelegramVoice] = None   # ← voice message support
    date: int = 0

    model_config = {"populate_by_name": True}


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
