"""
Sakhi - Menstrual Health Assistant
Main FastAPI application entry point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.webhook import router as webhook_router
from app.api.health import router as health_router
from app.api.analytics import router as analytics_router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.mongodb import connect_db, disconnect_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""
    configure_logging()
    logger.info("Starting Sakhi backend", extra={"env": settings.ENVIRONMENT})
    await connect_db()
    logger.info("MongoDB connection established")
    yield
    logger.info("Shutting down Sakhi backend")
    await disconnect_db()


app = FastAPI(
    title="Sakhi - Menstrual Health Assistant",
    description="Webhook-based menstrual health assistant with cycle prediction and AI conversations.",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-Telegram-Bot-Api-Secret-Token"],
)

app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(analytics_router, prefix="/admin", tags=["Analytics"])
