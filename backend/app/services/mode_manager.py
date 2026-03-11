"""Runtime mode manager for switching between production and dev models.

Controls whether the application uses Sonnet (production) or Haiku (dev) models.
The initial state is determined by the DEV_MODE environment variable.
When DEV_MODE is not set (i.e., in production deployment), defaults to production mode.
"""

import logging
from threading import Lock

logger = logging.getLogger(__name__)

_lock = Lock()
_production_mode: bool = True  # Default: production mode


def init_mode() -> None:
    """Initialize mode from application settings. Call once at startup."""
    global _production_mode
    from app.config import get_settings

    settings = get_settings()
    # If dev_mode is True in config, start in dev (non-production) mode
    _production_mode = not settings.dev_mode
    logger.info(
        f"Mode initialized: {'PRODUCTION (Sonnet)' if _production_mode else 'DEVELOPMENT (Haiku)'}"
    )


def is_production_mode() -> bool:
    """Check if currently in production mode."""
    return _production_mode


def set_production_mode(enabled: bool) -> None:
    """Toggle production mode at runtime.

    Args:
        enabled: True for production (Sonnet), False for dev (Haiku)
    """
    global _production_mode
    with _lock:
        _production_mode = enabled
    logger.info(
        f"Mode switched to: {'PRODUCTION (Sonnet)' if enabled else 'DEVELOPMENT (Haiku)'}"
    )


def is_dev_mode_allowed() -> bool:
    """Check if dev mode toggle is allowed (only when DEV_MODE env var is set)."""
    from app.config import get_settings

    return get_settings().dev_mode
