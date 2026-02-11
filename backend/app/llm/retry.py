"""Retry strategy with exponential backoff for LLM calls.

Provides robust retry logic for transient failures with automatic
fallback to alternative providers.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# Common retryable exceptions
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True

    # Additional exception types to retry on
    retry_on: tuple[type[Exception], ...] = field(default_factory=lambda: ())

    def get_retryable_exceptions(self) -> tuple[type[Exception], ...]:
        """Get all exceptions that should trigger a retry."""
        return RETRYABLE_EXCEPTIONS + self.retry_on


class RetryStrategy:
    """Handles retry logic with exponential backoff and fallbacks."""

    def __init__(self, config: RetryConfig):
        """Initialize retry strategy.

        Args:
            config: Retry configuration
        """
        self.config = config

    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        fallback_func: Optional[Callable[..., T]] = None,
        on_retry: Optional[Callable[[Exception, int], None]] = None,
        **kwargs: Any,
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            fallback_func: Optional fallback function if all retries fail
            on_retry: Optional callback for retry events (exception, attempt_number)
            **kwargs: Keyword arguments for func

        Returns:
            Result from func or fallback_func

        Raises:
            Exception: If all retries and fallback fail
        """
        last_exception: Optional[Exception] = None
        attempt = 0

        try:
            async for attempt_state in AsyncRetrying(
                stop=stop_after_attempt(self.config.max_retries),
                wait=wait_exponential_jitter(
                    initial=self.config.initial_delay,
                    max=self.config.max_delay,
                    jitter=self.config.max_delay / 4 if self.config.jitter else 0,
                ),
                retry=retry_if_exception_type(self.config.get_retryable_exceptions()),
                reraise=True,
            ):
                with attempt_state:
                    attempt = attempt_state.retry_state.attempt_number
                    if attempt > 1:
                        logger.info(
                            f"Retry attempt {attempt}/{self.config.max_retries}"
                        )
                        if on_retry and last_exception:
                            on_retry(last_exception, attempt)

                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        raise

        except RetryError as retry_error:
            last_exception = retry_error.last_attempt.exception()
            logger.warning(
                f"All {self.config.max_retries} retries exhausted. "
                f"Last error: {last_exception}"
            )

            # Try fallback if available
            if fallback_func:
                logger.info("Attempting fallback function")
                try:
                    return await fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise fallback_error from last_exception

            # Re-raise the last exception
            if last_exception:
                raise last_exception
            raise

        except Exception as e:
            # Non-retryable exception
            logger.error(f"Non-retryable exception: {type(e).__name__}: {e}")
            raise

        # Should not reach here, but type checker needs this
        raise RuntimeError("Unexpected state in retry loop")

    def execute_sync_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        fallback_func: Optional[Callable[..., T]] = None,
        on_retry: Optional[Callable[[Exception, int], None]] = None,
        **kwargs: Any,
    ) -> T:
        """Execute a synchronous function with retry logic.

        Args:
            func: Sync function to execute
            *args: Positional arguments for func
            fallback_func: Optional fallback function if all retries fail
            on_retry: Optional callback for retry events
            **kwargs: Keyword arguments for func

        Returns:
            Result from func or fallback_func
        """
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)

            except self.config.get_retryable_exceptions() as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.info(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    if on_retry:
                        on_retry(e, attempt)
                    import time

                    time.sleep(delay)
                else:
                    logger.warning(
                        f"All {self.config.max_retries} retries exhausted. "
                        f"Last error: {e}"
                    )

            except Exception as e:
                # Non-retryable exception
                logger.error(f"Non-retryable exception: {type(e).__name__}: {e}")
                raise

        # All retries exhausted, try fallback
        if fallback_func:
            logger.info("Attempting fallback function")
            try:
                return fallback_func(*args, **kwargs)
            except Exception as fallback_error:
                if last_exception:
                    raise fallback_error from last_exception
                raise

        if last_exception:
            raise last_exception

        raise RuntimeError("Unexpected state in retry loop")

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.config.initial_delay * (self.config.backoff_factor ** (attempt - 1))
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            # Add jitter: +/- 25% of the delay
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


def is_rate_limit_error(exception: Exception) -> bool:
    """Check if an exception is a rate limit error.

    Args:
        exception: Exception to check

    Returns:
        True if this is a rate limit error
    """
    error_str = str(exception).lower()
    rate_limit_indicators = [
        "rate limit",
        "rate_limit",
        "ratelimit",
        "too many requests",
        "429",
        "quota exceeded",
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)


def is_transient_error(exception: Exception) -> bool:
    """Check if an exception is a transient error that should be retried.

    Args:
        exception: Exception to check

    Returns:
        True if this is a transient error
    """
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True

    error_str = str(exception).lower()
    transient_indicators = [
        "timeout",
        "connection",
        "temporary",
        "unavailable",
        "503",
        "502",
        "500",
        "overloaded",
    ]
    return any(indicator in error_str for indicator in transient_indicators)
