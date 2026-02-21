"""Usage quota enforcement and concurrent generation limiting."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import get_settings
from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class QuotaStatus:
    """Current quota status for a user."""

    used: int
    limit: int
    is_admin: bool
    resets_at: str  # ISO date string for next month start

    @property
    def remaining(self) -> int:
        if self.is_admin:
            return 999
        return max(0, self.limit - self.used)

    @property
    def exceeded(self) -> bool:
        if self.is_admin:
            return False
        return self.used >= self.limit


def get_quota_status(user_id: str, monthly_limit: int, is_admin: bool) -> QuotaStatus:
    """Check how many reports a user has generated this month.

    Args:
        user_id: The user's ID
        monthly_limit: Their configured monthly limit
        is_admin: Whether they have the admin role

    Returns:
        QuotaStatus with usage details
    """
    supabase = get_supabase_client()

    # Count non-failed reports created this calendar month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = supabase.table("reports").select(
        "id", count="exact"
    ).eq(
        "created_by", user_id
    ).neq(
        "status", "failed"
    ).gte(
        "created_at", month_start.isoformat()
    ).execute()

    used = result.count or 0

    # Calculate next reset date (first day of next month)
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

    return QuotaStatus(
        used=used,
        limit=monthly_limit,
        is_admin=is_admin,
        resets_at=next_month.isoformat(),
    )


# ---------------------------------------------------------------------------
# Concurrent generation limiter (in-memory, single-instance)
# ---------------------------------------------------------------------------

class GenerationLimiter:
    """Limits concurrent report generations to protect $5 Railway instance.

    Uses an asyncio.Semaphore — safe for single-process FastAPI with
    BackgroundTasks (which run in the same event loop).
    """

    def __init__(self, max_concurrent: int | None = None):
        self._max = max_concurrent or settings.max_concurrent_generations
        self._semaphore = asyncio.Semaphore(self._max)
        self._active_count = 0
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return self._active_count

    @property
    def slots_available(self) -> int:
        return self._max - self._active_count

    async def acquire(self) -> bool:
        """Try to acquire a generation slot. Returns False if full."""
        async with self._lock:
            if self._active_count >= self._max:
                return False
            self._active_count += 1
            return True

    async def release(self) -> None:
        """Release a generation slot."""
        async with self._lock:
            self._active_count = max(0, self._active_count - 1)


# Singleton instance
_generation_limiter: GenerationLimiter | None = None


def get_generation_limiter() -> GenerationLimiter:
    """Get the global generation limiter instance."""
    global _generation_limiter
    if _generation_limiter is None:
        _generation_limiter = GenerationLimiter()
    return _generation_limiter
