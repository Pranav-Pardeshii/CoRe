import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from backend.app.core.config import Settings, get_settings


class InMemoryRateLimiter:
    """Simple per-IP sliding-window rate limiter for authentication endpoints."""

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check_and_record(self, key: str, *, max_requests: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        bucket = self._buckets[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        return True

    def reset(self) -> None:
        """Clear all recorded buckets (primarily for test isolation)."""
        self._buckets.clear()


_auth_rate_limiter = InMemoryRateLimiter()


def get_auth_rate_limiter() -> InMemoryRateLimiter:
    return _auth_rate_limiter


def enforce_auth_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
    limiter: InMemoryRateLimiter = Depends(get_auth_rate_limiter),
) -> None:
    """Reject excessive authentication attempts from a single client IP."""
    client_host = request.client.host if request.client else "unknown"
    allowed = limiter.check_and_record(
        f"{client_host}:{request.url.path}",
        max_requests=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
        )
