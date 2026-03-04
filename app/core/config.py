from typing import Optional
"""
Environment-based configuration for Sakhi.
All secrets loaded from environment variables — no hardcoded values.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App ---
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = Field(..., description="Telegram bot token from BotFather")
    TELEGRAM_API_BASE: str = "https://api.telegram.org/bot"

    # --- MongoDB Atlas ---
    MONGODB_URI: str = Field(..., description="MongoDB Atlas connection URI with TLS")
    MONGODB_DB_NAME: str = "sakhi"

    # --- Grok / xAI ---
    GROK_API_KEY: str = Field(..., description="xAI API key for Grok")
    GROK_BASE_URL: str = "https://openrouter.ai/api/v1"
    GROK_MODEL: str = "meta-llama/llama-3.3-70b-instruct"
    GROK_TIMEOUT_SECONDS: float = 15.0
    GROK_MAX_TOKENS: int = 512

    # --- Cycle defaults ---
    DEFAULT_CYCLE_LENGTH_DAYS: int = 28

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return upper


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
