"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logging import setup_logging

# Configure logging with file output
settings = get_settings()
setup_logging(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info(f"Starting application in {settings.environment} mode")
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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
