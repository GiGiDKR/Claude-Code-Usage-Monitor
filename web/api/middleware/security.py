"""
Security middleware for API protection.

This module provides security headers and basic protection measures.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers and basic protection."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.

        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Content Security Policy for API endpoints
        if request.url.path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'none'; object-src 'none'"
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self, app, calls_per_minute: int = 60):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI application
            calls_per_minute: Maximum calls per minute per IP
        """
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.request_counts = {}  # In production, use Redis or similar

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limits and process request.

        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain

        Returns:
            Response or rate limit error
        """
        import time

        from fastapi import HTTPException

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old entries (older than 1 minute)
        self.request_counts = {
            ip: [
                (timestamp, count)
                for timestamp, count in requests
                if current_time - timestamp < 60
            ]
            for ip, requests in self.request_counts.items()
            if any(current_time - timestamp < 60 for timestamp, _ in requests)
        }

        # Count requests for this IP in the last minute
        ip_requests = self.request_counts.get(client_ip, [])
        recent_requests = sum(
            count for timestamp, count in ip_requests if current_time - timestamp < 60
        )

        if recent_requests >= self.calls_per_minute:
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded. Please try again later."
            )

        # Add this request
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        self.request_counts[client_ip].append((current_time, 1))

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.calls_per_minute - recent_requests - 1)
        )

        return response
