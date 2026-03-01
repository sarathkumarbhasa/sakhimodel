"""
Pydantic models for Telegram Bot API webhook payloads.
Only includes fields Sakhi needs — ignores the rest.
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


class TelegramMessage(BaseModel):
    message_id: int
    from_: Optional[TelegramUser] = Field(None, alias="from")
    chat: TelegramChat
    text: Optional[str] = None
    date: int = 0

    model_config = {"populate_by_name": True}


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
