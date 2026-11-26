import ipaddress
import time
from collections import OrderedDict, deque

from fastapi import Depends, HTTPException, Request, status

from backend.app.core.config import Settings, get_app_settings

_DEFAULT_MAX_TRACKED_KEYS = 10_000


class InMemoryRateLimiter:
    """Process-local sliding-window rate limiter with O(1) LRU eviction.

    Note: In-memory counters are local to a single Python process. Use Cloud Armor or an
    edge/shared store for global multi-instance enforcement across Cloud Run instances.
    """

    def __init__(self, max_keys: int = _DEFAULT_MAX_TRACKED_KEYS) -> None:
        self._max_keys = max_keys
        self._buckets: OrderedDict[str, deque[float]] = OrderedDict()

    def _get_or_create_bucket(self, key: str) -> deque[float]:
        bucket = self._buckets.get(key)
        if bucket is not None:
            self._buckets.move_to_end(key)
            return bucket
        if len(self._buckets) >= self._max_keys:
            self._buckets.popitem(last=False)
        bucket = deque()
        self._buckets[key] = bucket
        return bucket

    def check_and_record(self, key: str, *, max_requests: int, window_seconds: int) -> bool:
        """Check whether *key* is within budget and record the current attempt."""
        now = time.monotonic()
        cutoff = now - window_seconds
        bucket = self._get_or_create_bucket(key)
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        return True

    def is_allowed(self, key: str, *, max_requests: int, window_seconds: int) -> bool:
        """Check whether *key* is currently below *max_requests* without recording."""
        bucket = self._buckets.get(key)
        if bucket is None:
            return True
        now = time.monotonic()
        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        return len(bucket) < max_requests

    def record(self, key: str, *, window_seconds: int) -> None:
        """Record an event timestamp for *key* (e.g. a failed login attempt)."""
        now = time.monotonic()
        cutoff = now - window_seconds
        bucket = self._get_or_create_bucket(key)
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        bucket.append(now)

    def clear(self, key: str) -> None:
        """Remove tracked state for *key* (e.g. after successful login)."""
        self._buckets.pop(key, None)

    @property
    def tracked_key_count(self) -> int:
        """Expose current bucket count for observability and testing."""
        return len(self._buckets)

    def reset(self) -> None:
        """Clear all recorded buckets (primarily for test isolation)."""
        self._buckets.clear()


_auth_ip_rate_limiter = InMemoryRateLimiter()
_auth_username_rate_limiter = InMemoryRateLimiter()
_public_rate_limiter = InMemoryRateLimiter()


def get_auth_ip_rate_limiter() -> InMemoryRateLimiter:
    return _auth_ip_rate_limiter


def get_auth_username_rate_limiter() -> InMemoryRateLimiter:
    return _auth_username_rate_limiter


def get_public_rate_limiter() -> InMemoryRateLimiter:
    return _public_rate_limiter


def get_auth_rate_limiter() -> InMemoryRateLimiter:
    """Alias for auth IP rate limiter."""
    return _auth_ip_rate_limiter


def reset_all_rate_limiters() -> None:
    """Reset all process-local rate limiters (primarily for test isolation)."""
    _auth_ip_rate_limiter.reset()
    _auth_username_rate_limiter.reset()
    _public_rate_limiter.reset()


def _is_ip_trusted(ip_str: str, trusted_entries: list[str]) -> bool:
    if not trusted_entries:
        return False
    if ip_str in trusted_entries:
        return True
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    for entry in trusted_entries:
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        if addr in network:
            return True
    return False


def extract_client_ip(
    request: Request,
    trusted_proxy_ips: list[str],
    trusted_proxy_hops: int = 0,
) -> str:
    """Resolve client IP safely from trusted proxy IPs/CIDRs or trusted hop count."""
    peer_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]

    if hops and _is_ip_trusted(peer_ip, trusted_proxy_ips):
        for hop in reversed(hops):
            if not _is_ip_trusted(hop, trusted_proxy_ips):
                return hop
        return hops[-1]

    if hops and trusted_proxy_hops > 0:
        if len(hops) >= trusted_proxy_hops:
            return hops[-trusted_proxy_hops]
        return hops[0]

    return peer_ip


def enforce_auth_rate_limit(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    limiter: InMemoryRateLimiter = Depends(get_auth_ip_rate_limiter),
) -> None:
    """Reject excessive authentication attempts from a single client IP."""
    client_ip = extract_client_ip(
        request,
        settings.TRUSTED_PROXY_IPS,
        settings.TRUSTED_PROXY_HOPS,
    )
    allowed = limiter.check_and_record(
        f"auth:{client_ip}:{request.url.path}",
        max_requests=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
        )


def enforce_public_rate_limit(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    limiter: InMemoryRateLimiter = Depends(get_public_rate_limiter),
) -> None:
    """Reject excessive requests to public catalog/recommender/trends endpoints."""
    client_ip = extract_client_ip(
        request,
        settings.TRUSTED_PROXY_IPS,
        settings.TRUSTED_PROXY_HOPS,
    )
    allowed = limiter.check_and_record(
        f"public:{client_ip}:{request.url.path}",
        max_requests=settings.PUBLIC_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
