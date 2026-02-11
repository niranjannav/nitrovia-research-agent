"""Supabase client wrapper with retry logic."""

import logging
import time
from functools import wraps
from typing import Callable, TypeVar

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Store client instance for potential refresh
_supabase_client: Client | None = None

# Longer timeout for storage operations (120 seconds)
STORAGE_TIMEOUT = httpx.Timeout(
    connect=30.0,
    read=120.0,
    write=60.0,
    pool=30.0,
)


def _create_supabase_client() -> Client:
    """Create a new Supabase client with custom timeout settings."""
    settings = get_settings()
    options = SyncClientOptions(
        postgrest_client_timeout=60,
        storage_client_timeout=120,
    )
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key,
        options=options,
    )


def get_supabase_client() -> Client:
    """Get Supabase client instance, creating new one if needed."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = _create_supabase_client()
    return _supabase_client


def refresh_supabase_client() -> Client:
    """Force refresh the Supabase client connection."""
    global _supabase_client
    _supabase_client = _create_supabase_client()
    logger.info("Supabase client connection refreshed")
    return _supabase_client


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retry_on: tuple = (Exception,),
) -> Callable:
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        retry_on: Tuple of exception types to retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    if attempt < max_retries:
                        # Check if it's a connection error that might need client refresh
                        error_str = str(e).lower()
                        if "ssl" in error_str or "connection" in error_str or "eof" in error_str:
                            logger.warning(f"Connection error on attempt {attempt + 1}, refreshing client...")
                            refresh_supabase_client()

                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed: {e}")

            raise last_exception
        return wrapper
    return decorator


def get_supabase_anon_client() -> Client:
    """Get Supabase client with anon key (for RLS-enabled operations)."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )
