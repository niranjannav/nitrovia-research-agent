"""Configuration API endpoints for runtime mode toggling."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.mode_manager import (
    is_dev_mode_allowed,
    is_production_mode,
    set_production_mode,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ModeResponse(BaseModel):
    """Response for current mode status."""

    production_mode: bool
    dev_toggle_available: bool
    model_tier: str  # "sonnet" or "haiku"


class ModeUpdateRequest(BaseModel):
    """Request to update mode."""

    production_mode: bool


@router.get("/config/mode", response_model=ModeResponse)
async def get_mode():
    """Get the current LLM mode (production vs dev)."""
    prod = is_production_mode()
    return ModeResponse(
        production_mode=prod,
        dev_toggle_available=is_dev_mode_allowed(),
        model_tier="sonnet" if prod else "haiku",
    )


@router.put("/config/mode", response_model=ModeResponse)
async def set_mode(request: ModeUpdateRequest):
    """Toggle between production (Sonnet) and dev (Haiku) mode.

    Only available when DEV_MODE=true is set in the environment.
    In production deployments (no DEV_MODE), this endpoint returns 403.
    """
    if not is_dev_mode_allowed():
        raise HTTPException(
            status_code=403,
            detail="Mode toggle is not available in production deployments. "
            "Set DEV_MODE=true in .env to enable.",
        )

    set_production_mode(request.production_mode)
    prod = is_production_mode()
    logger.info(f"Mode toggled to: {'production' if prod else 'development'}")

    return ModeResponse(
        production_mode=prod,
        dev_toggle_available=True,
        model_tier="sonnet" if prod else "haiku",
    )
