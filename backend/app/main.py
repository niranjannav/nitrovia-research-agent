"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.utils.logging import setup_logging

# Configure logging with file output
settings = get_settings()
setup_logging(level=settings.log_level)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter (in-memory store — fine for single Railway instance)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


def _configure_api_keys() -> None:
    """Set LLM API keys in environment so litellm can find them."""
    import os

    if settings.anthropic_api_key:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    _configure_api_keys()
    logger.info(f"Starting application in {settings.environment} mode")
    logger.info(f"Max concurrent generations: {settings.max_concurrent_generations}")
    logger.info(f"Default monthly report limit: {settings.default_monthly_report_limit}")
    yield
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title="Research Report Generator API",
    description="API for generating research reports and presentations from documents",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Import and include routers
from app.api import auth, files, health, reports  # noqa: E402

app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(files.router, prefix="/files", tags=["Files"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Research Report Generator API",
        "version": "1.0.0",
        "docs": "/docs" if not settings.is_production else None,
    }
