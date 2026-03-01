"""
Custom exception hierarchy for Sakhi.
Keeps error handling explicit and structured.
"""


class SakhiBaseException(Exception):
    """Root exception for all Sakhi errors."""


class DatabaseError(SakhiBaseException):
    """Raised when a MongoDB operation fails."""


class GrokAPIError(SakhiBaseException):
    """Raised when the Grok/xAI API returns an error or times out."""


class TelegramAPIError(SakhiBaseException):
    """Raised when sending a Telegram message fails."""


class ValidationError(SakhiBaseException):
    """Raised when user-supplied input fails validation."""
