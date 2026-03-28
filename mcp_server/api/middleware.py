"""
API Middleware Module

Rate limiting, logging, and request tracking middleware.
"""

import logging
import time
import uuid
from typing import Callable, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from security.rate_limits import RateLimiter, check_all_limits, RateLimitTier

logger = logging.getLogger(__name__)

# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None

# A2A-specific rate limit (in-memory sliding window)
_a2a_requests: dict = {}  # ip -> list of timestamps


def _check_a2a_limit(ip: str, limit: int = 5, window: int = 60) -> tuple:
    """Check A2A-specific rate limit. Returns (is_limited, retry_after_seconds)."""
    now = time.time()
    timestamps = _a2a_requests.setdefault(ip, [])
    cutoff = now - window
    timestamps[:] = [t for t in timestamps if t > cutoff]
    if len(timestamps) >= limit:
        return True, int(window - (now - timestamps[0])) if timestamps else window
    timestamps.append(now)
    return False, 0


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        client_ip = _get_client_ip(request)

        logger.info(
            "[%s] %s %s - IP: %s",
            request_id,
            request.method,
            request.url.path,
            client_ip,
        )

        # Process request
        try:
            response = await call_next(request)

            # Log response
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "[%s] %s %s - %d (%.2fms)",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "[%s] %s %s - ERROR: %s (%.2fms)",
                request_id,
                request.method,
                request.url.path,
                str(e),
                duration_ms,
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests."""

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/.well-known/agent.json",
        "/.well-known/x402",
    }

    # Path prefixes exempt from rate limiting (have their own auth)
    EXEMPT_PREFIXES = (
        "/api/v1/admin/",
        "/api/v1/reputation/info",
        "/api/v1/reputation/networks",
        "/api/v1/escrow/config",
        "/api/v1/config",
        "/health/",
    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip rate limiting for exempt prefixes (admin endpoints have their own auth)
        if request.url.path.startswith(self.EXEMPT_PREFIXES):
            return await call_next(request)

        # Skip for WebSocket upgrades
        if request.headers.get("upgrade") == "websocket":
            return await call_next(request)

        # Get client IP early (needed for ban check + rate limiting)
        client_ip = _get_client_ip(request)

        # Check IP ban FIRST (cheapest check, no processing for banned IPs)
        try:
            from security.ip_ban import is_banned, record_429

            if is_banned(client_ip):
                return JSONResponse(
                    status_code=403,
                    content={"error": "Temporarily banned due to excessive requests"},
                )
        except ImportError:
            record_429 = None  # type: ignore[assignment]

        # Reject oversized request bodies (1 MB max)
        content_length = int(request.headers.get("content-length", 0))
        if content_length > 1_048_576:
            return JSONResponse(
                status_code=413,
                content={"error": "Request body too large", "max_bytes": 1_048_576},
            )

        # A2A-specific rate limits (stricter: 5 req/min per IP)
        if request.url.path.startswith("/a2a/"):
            is_limited, retry_after = _check_a2a_limit(client_ip, limit=5, window=60)
            if is_limited:
                if record_429:
                    record_429(client_ip)
                return JSONResponse(
                    status_code=429,
                    content={
                        "jsonrpc": "2.0",
                        "error": {"code": -32005, "message": "A2A rate limit exceeded"},
                        "id": None,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Type": "a2a",
                    },
                )

        # Get remaining client identifiers
        device_id = request.headers.get("X-Device-ID")
        api_key = _extract_api_key(request)

        # Check for ERC-8128 wallet as rate limit identifier
        if not api_key:
            erc8128_wallet = _extract_erc8128_wallet(request)
            if erc8128_wallet:
                # Use wallet address as the rate limit key (default STARTER tier)
                api_key = f"erc8128:{erc8128_wallet}"

        # Determine tier from API key
        tier = RateLimitTier.FREE
        if api_key:
            if api_key.startswith("erc8128:"):
                tier = RateLimitTier.STARTER  # Default tier for wallet auth
            else:
                tier = _get_tier_from_key(api_key)

        # Check rate limits
        limiter = get_rate_limiter()
        allowed, limit_type, retry_after = check_all_limits(
            limiter=limiter,
            ip=client_ip,
            device_id=device_id,
            api_key=api_key,
            api_tier=tier,
        )

        if not allowed:
            logger.warning(
                "Rate limited: ip=%s, type=%s, retry_after=%s",
                client_ip,
                limit_type,
                retry_after,
            )
            if record_429:
                record_429(client_ip)

            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit type: {limit_type}",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Type": limit_type,
                },
            )

        # Add rate limit info to request state
        request.state.rate_limit_tier = tier.value
        request.state.client_ip = client_ip

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        remaining = limiter.get_remaining(
            api_key or client_ip, "api" if api_key else "ip"
        )
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Tier"] = tier.value

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent error handling."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)

        except ValueError as e:
            logger.warning("Validation error: %s", str(e))
            return JSONResponse(
                status_code=400,
                content={
                    "error": "validation_error",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        except PermissionError as e:
            logger.warning("Permission denied: %s", str(e))
            return JSONResponse(
                status_code=403,
                content={
                    "error": "forbidden",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        except Exception as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.exception("[%s] Unhandled error: %s", request_id, str(e))
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )


def add_api_middleware(app: FastAPI) -> None:
    """
    Add all API middleware to the FastAPI app.

    Order matters - middleware is executed in reverse order of addition.
    """
    # Error handling (outermost)
    app.add_middleware(ErrorHandlingMiddleware)

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Request logging (innermost, runs first)
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("API middleware configured")


def _get_client_ip(request: Request) -> str:
    """
    Extract real client IP from request.

    Handles common proxy headers (X-Forwarded-For, X-Real-IP).
    """
    # Check X-Forwarded-For (from load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP (from nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client
    if request.client:
        return request.client.host

    return "unknown"


def _extract_api_key(request: Request) -> Optional[str]:
    """Extract API key from request headers."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    x_api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if x_api_key:
        return x_api_key.strip()
    return None


def _extract_erc8128_wallet(request: Request) -> Optional[str]:
    """
    Extract wallet address from ERC-8128 Signature-Input keyid for rate limiting.

    This is a pre-auth heuristic — the actual signature is verified later
    in the auth dependency. A fake keyid gets higher rate limits but will
    still fail signature verification.
    """
    import re

    sig_input = request.headers.get("signature-input") or request.headers.get(
        "Signature-Input", ""
    )
    if "erc8128:" in sig_input:
        match = re.search(r'keyid="erc8128:\d+:(0x[a-fA-F0-9]{40})"', sig_input)
        if match:
            return match.group(1).lower()
    return None


def _get_tier_from_key(api_key: str) -> RateLimitTier:
    """
    Estimate rate limit tier from API key prefix.

    NOTE: This is a pre-auth heuristic for rate limiting only.
    A fake key with "enterprise" prefix gets higher rate limits but
    will still fail authentication in the endpoint handler (auth.py).
    The actual tier is validated against the DB during auth.
    """
    if api_key.startswith("em_enterprise_"):
        return RateLimitTier.ENTERPRISE
    elif api_key.startswith("em_growth_"):
        return RateLimitTier.GROWTH
    elif api_key.startswith("em_starter_") or api_key.startswith("em_bot_"):
        return RateLimitTier.STARTER
    return RateLimitTier.FREE
