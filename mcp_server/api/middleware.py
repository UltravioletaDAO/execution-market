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
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from security.rate_limits import RateLimiter, check_all_limits, RateLimitTier
from utils.net import get_client_ip as _trusted_get_client_ip

logger = logging.getLogger(__name__)

# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None

# A2A-specific rate limit (in-memory sliding window, bounded)
_a2a_requests: dict = {}  # ip -> list of timestamps
_a2a_check_count = 0
_A2A_MAX_IPS = 5000


def _check_a2a_limit(ip: str, limit: int = 5, window: int = 150) -> tuple:
    """Check A2A-specific rate limit. Returns (is_limited, retry_after_seconds)."""
    global _a2a_check_count
    now = time.time()

    # Periodic cleanup: evict stale IPs every 1000 checks
    _a2a_check_count += 1
    if _a2a_check_count % 1000 == 0:
        cutoff_global = now - window
        stale = [k for k, v in _a2a_requests.items() if not v or v[-1] < cutoff_global]
        for k in stale:
            del _a2a_requests[k]
        # Hard cap
        if len(_a2a_requests) > _A2A_MAX_IPS:
            _a2a_requests.clear()

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
        record_429_fn = None
        record_unauth_fn = None
        try:
            from security.ip_ban import is_banned, record_429, record_unauthorized

            if is_banned(client_ip):
                return JSONResponse(
                    status_code=403,
                    content={"error": "Temporarily banned due to excessive requests"},
                )
            record_429_fn = record_429
            record_unauth_fn = record_unauthorized
        except ImportError:
            pass

        # Reject oversized request bodies (1 MB max)
        content_length = int(request.headers.get("content-length", 0))
        if content_length > 1_048_576:
            return JSONResponse(
                status_code=413,
                content={"error": "Request body too large", "max_bytes": 1_048_576},
            )

        # A2A early-reject: if no auth headers at all, return 401 immediately
        # without invoking the full A2A JSON-RPC dispatch. Saves CPU on junk
        # traffic from bots that don't even attempt authentication.
        if request.url.path.startswith("/a2a/"):
            has_auth = (
                request.headers.get("signature-input")
                or request.headers.get("Signature-Input")
                or request.headers.get("authorization")
                or request.headers.get("Authorization")
                or request.headers.get("x-api-key")
                or request.headers.get("X-API-Key")
            )
            if not has_auth:
                if record_unauth_fn:
                    record_unauth_fn(client_ip)
                return JSONResponse(
                    status_code=401,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32000,
                            "message": "Authentication required",
                        },
                        "id": None,
                    },
                )

        # A2A-specific rate limits (per IP, for authenticated requests that passed
        # the early-reject above). 15 req/5min is generous for legitimate A2A
        # discovery but catches repeat abuse from authenticated bots.
        # Raised from 5/150s after review — agents polling task status is normal.
        if request.url.path.startswith("/a2a/"):
            is_limited, retry_after = _check_a2a_limit(client_ip, limit=15, window=300)
            if is_limited:
                if record_429_fn:
                    record_429_fn(client_ip)
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
            if record_429_fn:
                record_429_fn(client_ip)

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


class SecurityHeadersMiddleware:
    """
    Inject defense-in-depth security response headers on every HTTP response.

    Rationale (Phase 1.1 SAAS_PRODUCTION_HARDENING):
      If a client bypasses CloudFront / the ALB edge (e.g. hitting the raw
      origin URL), the backend must still enforce browser-level protections.

    Implementation:
      Pure ASGI middleware (NOT BaseHTTPMiddleware). We intercept the raw
      ``http.response.start`` message and mutate the headers list before it
      is flushed to the client. This guarantees headers land on EVERY
      response, including:
        * responses generated by Starlette's internal ``ServerErrorMiddleware``
          when a handler raises (before any ``@app.exception_handler(Exception)``
          runs);
        * short-circuit responses from inner middleware (429, 413, 403);
        * handler-set responses (200, 404, 418, etc.).
      A ``BaseHTTPMiddleware`` subclass would miss the first case because
      ``ServerErrorMiddleware`` sits outside of it in the Starlette stack.

    Headers injected:
      - Strict-Transport-Security: force HTTPS for 2 years, include subdomains
        and request preload-list inclusion.
      - X-Content-Type-Options: prevent MIME sniffing.
      - X-Frame-Options: disallow framing (clickjacking defense).
      - Referrer-Policy: leak only the origin on cross-origin navigations.
      - Permissions-Policy: deny geolocation / camera / microphone / payment
        by default. The dashboard captures camera/geo from the browser via
        the user's device APIs, which are frontend-only and are not gated by
        these API responses; this policy only affects documents served from
        the API itself (swagger UI, error pages, etc.), where those APIs
        should be off.

    If any endpoint later needs to enable camera/geolocation for its own
    rendered HTML, scope the policy at the endpoint level — do not relax
    the default here.
    """

    # Exposed as class attributes so tests can assert exact values.
    HEADERS = {
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": ("geolocation=(), camera=(), microphone=(), payment=()"),
    }

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for header_name, header_value in self.HEADERS.items():
                    # setdefault semantics: never override a handler-set value.
                    if header_name not in headers:
                        headers[header_name] = header_value
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


def add_api_middleware(app: FastAPI) -> None:
    """
    Add all API middleware to the FastAPI app.

    Order matters - middleware is executed in reverse order of addition.
    The last-added middleware is the OUTERMOST (runs first on request, last
    on response), so SecurityHeadersMiddleware is added last to guarantee
    its headers land on every response, including error responses emitted
    by inner middleware.
    """
    # Error handling (outermost among request-path middleware)
    app.add_middleware(ErrorHandlingMiddleware)

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Request logging (innermost, runs first)
    app.add_middleware(RequestLoggingMiddleware)

    # Security headers — added last so it sits OUTERMOST in the middleware
    # stack. This guarantees headers are set on responses that short-circuit
    # (e.g. 429 from RateLimitMiddleware, 500 from ErrorHandlingMiddleware).
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("API middleware configured")


def _get_client_ip(request: Request) -> str:
    """Extract real client IP from request, respecting trusted-proxy boundary.

    This is a thin wrapper around :func:`utils.net.get_client_ip` so that
    existing callsites (``RequestLoggingMiddleware``, ``RateLimitMiddleware``)
    keep working. The trusted-proxy logic lives in ``utils.net`` — see the
    docstring there for the spoofing-resistance rules.

    TL;DR: XFF is only honored when the TCP peer is inside
    ``TRUSTED_PROXY_CIDRS``. For direct (untrusted) callers, the TCP peer
    IP is returned and XFF is ignored.
    """
    return _trusted_get_client_ip(request)


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
