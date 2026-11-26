import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from backend.app.core.config import Settings, get_settings

_PRUNE_INTERVAL_SECONDS = 60.0
_MAX_TRACKED_KEYS = 10_000


class InMemoryRateLimiter:
    """Process-local per-IP sliding-window rate limiter for authentication endpoints.

    Note: In-memory counters are local to a single Python process and cannot enforce a
    global limit across multiple Uvicorn workers or horizontally scaled Cloud Run
    instances. Use an edge/load-balancer rate limit or shared store for multi-instance
    global enforcement.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._last_prune_at: float = time.monotonic()

    def _prune_expired_buckets(self, now: float, window_seconds: int) -> None:
        if (
            now - self._last_prune_at < _PRUNE_INTERVAL_SECONDS
            and len(self._buckets) < _MAX_TRACKED_KEYS
        ):
            return
        cutoff = now - window_seconds
        stale_keys = [
            key for key, bucket in self._buckets.items() if not bucket or bucket[-1] <= cutoff
        ]
        for key in stale_keys:
            del self._buckets[key]
        self._last_prune_at = now

    def check_and_record(self, key: str, *, max_requests: int, window_seconds: int) -> bool:
        now = time.monotonic()
        self._prune_expired_buckets(now, window_seconds)
        cutoff = now - window_seconds
        bucket = self._buckets[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        return True

    @property
    def tracked_key_count(self) -> int:
        """Expose current bucket count for observability and testing."""
        return len(self._buckets)

    def reset(self) -> None:
        """Clear all recorded buckets (primarily for test isolation)."""
        self._buckets.clear()
        self._last_prune_at = time.monotonic()


_auth_rate_limiter = InMemoryRateLimiter()


def get_auth_rate_limiter() -> InMemoryRateLimiter:
    return _auth_rate_limiter


def extract_client_ip(request: Request, trusted_proxy_ips: list[str]) -> str:
    """Resolve client IP safely, only reading X-Forwarded-For from trusted proxies."""
    peer_ip = request.client.host if request.client else "unknown"
    if peer_ip in trusted_proxy_ips:
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
        if hops:
            # Rightmost non-trusted hop (or rightmost hop) prevents client-header spoofing.
            for hop in reversed(hops):
                if hop not in trusted_proxy_ips:
                    return hop
            return hops[-1]
    return peer_ip


def enforce_auth_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
    limiter: InMemoryRateLimiter = Depends(get_auth_rate_limiter),
) -> None:
    """Reject excessive authentication attempts from a single client IP."""
    client_ip = extract_client_ip(request, settings.TRUSTED_PROXY_IPS)
    allowed = limiter.check_and_record(
        f"{client_ip}:{request.url.path}",
        max_requests=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
        )
