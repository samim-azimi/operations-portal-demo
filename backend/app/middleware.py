from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class SlidingWindowLimiter:
    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


request_limiter = SlidingWindowLimiter()


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        is_login = path == "/api/auth/login"
        is_public_brand_image = (
            path.startswith("/api/organization-settings/")
            and path.endswith("/file")
        )
        limit = (
            settings.login_attempts_per_minute
            if is_login
            else settings.rate_limit_per_minute
        )
        bucket = "login" if is_login else "api"

        if not request_limiter.allow(f"{client_ip}:{bucket}", limit):
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again shortly."},
                headers={"Retry-After": "60"},
            )
        else:
            content_length = request.headers.get("content-length")
            max_request_bytes = settings.max_upload_bytes + 1_048_576
            try:
                request_size = int(content_length) if content_length else 0
            except ValueError:
                request_size = max_request_bytes + 1
            if request_size > max_request_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large."},
                )
            else:
                response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cross-Origin-Resource-Policy"] = (
            "cross-origin" if is_public_brand_image else "same-site"
        )
        response.headers["Cache-Control"] = (
            "no-store"
            if path.startswith("/api")
            else "no-cache"
        )
        if path.startswith("/api") and not is_public_brand_image:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )
        if settings.environment.lower() == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
