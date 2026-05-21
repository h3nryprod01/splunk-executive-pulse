# orchestration/retry_policy.py
from __future__ import annotations
import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Callable, Awaitable, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    # Exceptions that should NOT be retried (terminal errors)
    no_retry_on: tuple = ()


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    node_name: str,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await fn()
        except policy.no_retry_on as e:
            logger.error(f"[{node_name}] terminal error (no retry): {e}")
            raise
        except Exception as e:
            last_exc = e
            if attempt == policy.max_attempts:
                logger.error(f"[{node_name}] failed after {attempt} attempts: {e}")
                raise
            delay = min(
                policy.base_delay_s * (policy.exponential_base ** (attempt - 1)),
                policy.max_delay_s,
            )
            if policy.jitter:
                delay *= 0.5 + random.random()
            logger.warning(
                f"[{node_name}] attempt {attempt}/{policy.max_attempts} failed "
                f"({type(e).__name__}: {e}); retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore
