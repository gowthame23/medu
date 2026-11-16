import time
from collections import OrderedDict
from typing import Dict, List
from fastapi import Request, HTTPException, status
from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Extract client IP, validating X-Forwarded-For against TRUSTED_PROXIES."""
    remote_host = request.client.host if request.client else "unknown"
    trusted = getattr(settings, "TRUSTED_PROXIES", ["127.0.0.1", "::1"])
    if remote_host in trusted:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                return parts[-1]
    return remote_host


class InMemoryRateLimiter:
    """Sliding-window bounded in-memory rate limiter with trusted proxy validation."""
    def __init__(self, requests_per_minute: int, key_prefix: str = "", max_tracked_keys: int = 10000):
        self.requests_per_minute = requests_per_minute
        self.key_prefix = key_prefix
        self.window_seconds = 60.0
        self.max_tracked_keys = max_tracked_keys
        self._requests: OrderedDict[str, List[float]] = OrderedDict()

    def _resolve_client_ip(self, request: Request) -> str:
        return get_client_ip(request)

    async def __call__(self, request: Request):
        # Allow disabling rate limiter during standard unit test suites unless explicitly tested
        if getattr(request.app.state, "disable_rate_limiting", False):
            return

        client_ip = self._resolve_client_ip(request)
        key = f"{self.key_prefix}:{client_ip}"
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Memory capping & eviction
        if len(self._requests) >= self.max_tracked_keys:
            # Evict expired keys
            expired_keys = [k for k, v in self._requests.items() if not v or v[-1] <= cutoff]
            for k in expired_keys:
                self._requests.pop(k, None)
            # If still over limit, evict the oldest key (FIFO)
            while len(self._requests) >= self.max_tracked_keys:
                self._requests.popitem(last=False)

        history = [ts for ts in self._requests.get(key, []) if ts > cutoff]
        if len(history) >= self.requests_per_minute:
            retry_after = int(self.window_seconds - (now - history[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
                headers={"Retry-After": str(max(1, retry_after))}
            )

        history.append(now)
        self._requests[key] = history
        self._requests.move_to_end(key)


login_rate_limiter = InMemoryRateLimiter(settings.RATE_LIMIT_LOGIN_PER_MIN, "auth:login", settings.RATE_LIMIT_MAX_TRACKED_IPS)
register_rate_limiter = InMemoryRateLimiter(settings.RATE_LIMIT_REGISTER_PER_MIN, "auth:register", settings.RATE_LIMIT_MAX_TRACKED_IPS)
refresh_rate_limiter = InMemoryRateLimiter(settings.RATE_LIMIT_REFRESH_PER_MIN, "auth:refresh", settings.RATE_LIMIT_MAX_TRACKED_IPS)
invitation_accept_rate_limiter = InMemoryRateLimiter(settings.RATE_LIMIT_INVITE_ACCEPT_PER_MIN, "invites:accept", settings.RATE_LIMIT_MAX_TRACKED_IPS)
verification_rate_limiter = InMemoryRateLimiter(30, "verification", settings.RATE_LIMIT_MAX_TRACKED_IPS)
