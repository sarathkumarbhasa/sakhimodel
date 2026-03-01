"""
Pydantic models for Telegram Bot API webhook payloads.
Only includes fields Sakhi needs — ignores the rest.
"""

from typing import Optional

from pydantic import BaseModel


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
    from_: Optional[TelegramUser] = None
    chat: TelegramChat
    text: Optional[str] = None
    date: int = 0

    model_config = {"populate_by_name": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if isinstance(obj, dict) and "from" in obj:
            obj = dict(obj)
            obj["from_"] = obj.pop("from")
        return super().model_validate(obj, **kwargs)


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
