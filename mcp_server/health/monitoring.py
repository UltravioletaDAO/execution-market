"""
Monitoring Utilities for Chamba

Provides:
- Structured logging setup
- Error tracking (Sentry compatible)
- Performance tracing
- Request correlation IDs
"""

import asyncio
import functools
import json
import logging
import os
import sys
import time
import traceback
import uuid
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

# Context variable for request correlation
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
trace_context_var: ContextVar[Optional["TracingContext"]] = ContextVar("trace_context", default=None)


# =============================================================================
# Structured Logging
# =============================================================================


class StructuredFormatter(logging.Formatter):
    """
    JSON-structured log formatter.

    Outputs logs in JSON format suitable for:
    - CloudWatch Logs Insights
    - Elasticsearch/OpenSearch
    - Datadog Log Management
    - Splunk
    """

    def __init__(self, service_name: str = "chamba"):
        super().__init__()
        self.service_name = service_name
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.version = os.getenv("APP_VERSION", "unknown")

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
            "version": self.version,
        }

        # Add correlation ID if available
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id

        # Add tracing context if available
        trace_ctx = trace_context_var.get()
        if trace_ctx:
            log_entry["trace_id"] = trace_ctx.trace_id
            log_entry["span_id"] = trace_ctx.span_id
            if trace_ctx.parent_span_id:
                log_entry["parent_span_id"] = trace_ctx.parent_span_id

        # Add source location for errors
        if record.levelno >= logging.WARNING:
            log_entry["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in logging.LogRecord(
                "", 0, "", 0, "", (), None
            ).__dict__ and not k.startswith("_")
        }
        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable log formatter for development.

    Includes colors for terminal output.
    """

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human readability."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        level = record.levelname

        # Color the level
        if self.use_colors:
            color = self.COLORS.get(level, "")
            level = f"{color}{level:8}{self.RESET}"
        else:
            level = f"{level:8}"

        # Add request ID if available
        request_id = request_id_var.get()
        rid_str = f" [{request_id[:8]}]" if request_id else ""

        # Base message
        message = f"{timestamp} {level} {record.name}:{record.lineno}{rid_str} - {record.getMessage()}"

        # Add exception if present
        if record.exc_info:
            message += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return message


def setup_logging(
    level: str = "INFO",
    structured: bool = None,
    service_name: str = "chamba",
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Use JSON format (auto-detected based on environment)
        service_name: Service name for structured logs
    """
    # Auto-detect structured logging based on environment
    if structured is None:
        environment = os.getenv("ENVIRONMENT", "development")
        structured = environment in ("production", "staging")

    # Create formatter
    if structured:
        formatter = StructuredFormatter(service_name=service_name)
    else:
        formatter = HumanReadableFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.info(
        "Logging configured: level=%s, structured=%s, service=%s",
        level, structured, service_name
    )


# =============================================================================
# Error Tracking (Sentry Compatible)
# =============================================================================


_error_tracking_initialized = False
_sentry_sdk = None


def setup_error_tracking(
    dsn: str = None,
    environment: str = None,
    release: str = None,
    sample_rate: float = 1.0,
    traces_sample_rate: float = 0.1,
) -> bool:
    """
    Set up error tracking with Sentry.

    Args:
        dsn: Sentry DSN (or from SENTRY_DSN env var)
        environment: Environment name (or from ENVIRONMENT env var)
        release: Release version (or from APP_VERSION env var)
        sample_rate: Error sample rate (0.0 to 1.0)
        traces_sample_rate: Performance monitoring sample rate

    Returns:
        True if successfully initialized, False otherwise
    """
    global _error_tracking_initialized, _sentry_sdk

    dsn = dsn or os.getenv("SENTRY_DSN")
    if not dsn:
        logging.info("Sentry DSN not configured, error tracking disabled")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        environment = environment or os.getenv("ENVIRONMENT", "development")
        release = release or os.getenv("APP_VERSION", "unknown")

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            sample_rate=sample_rate,
            traces_sample_rate=traces_sample_rate,
            integrations=[
                AsyncioIntegration(),
                LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
            ],
            # Don't send PII
            send_default_pii=False,
            # Attach request data
            request_bodies="small",
        )

        _error_tracking_initialized = True
        _sentry_sdk = sentry_sdk

        logging.info(
            "Sentry initialized: environment=%s, release=%s",
            environment, release
        )
        return True

    except ImportError:
        logging.warning("sentry-sdk not installed, error tracking disabled")
        return False
    except Exception as e:
        logging.error("Failed to initialize Sentry: %s", str(e))
        return False


def capture_exception(
    exception: Exception,
    extra: Dict[str, Any] = None,
    tags: Dict[str, str] = None,
) -> Optional[str]:
    """
    Capture an exception for error tracking.

    Args:
        exception: The exception to capture
        extra: Additional context data
        tags: Tags for categorization

    Returns:
        Event ID if captured, None otherwise
    """
    if not _error_tracking_initialized or not _sentry_sdk:
        logging.error(
            "Exception captured (Sentry not available): %s",
            str(exception),
            exc_info=exception
        )
        return None

    with _sentry_sdk.push_scope() as scope:
        # Add extra data
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        # Add tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            scope.set_tag("request_id", request_id)

        # Add trace context if available
        trace_ctx = trace_context_var.get()
        if trace_ctx:
            scope.set_tag("trace_id", trace_ctx.trace_id)

        return _sentry_sdk.capture_exception(exception)


def capture_message(
    message: str,
    level: str = "info",
    extra: Dict[str, Any] = None,
    tags: Dict[str, str] = None,
) -> Optional[str]:
    """
    Capture a message for error tracking.

    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        extra: Additional context data
        tags: Tags for categorization

    Returns:
        Event ID if captured, None otherwise
    """
    if not _error_tracking_initialized or not _sentry_sdk:
        logging.log(
            getattr(logging, level.upper(), logging.INFO),
            "Message captured (Sentry not available): %s", message
        )
        return None

    with _sentry_sdk.push_scope() as scope:
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        return _sentry_sdk.capture_message(message, level=level)


# =============================================================================
# Performance Tracing
# =============================================================================


@dataclass
class Span:
    """Represents a single span in a trace."""
    span_id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    parent_span_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> Optional[float]:
        """Get span duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def set_tag(self, key: str, value: str) -> None:
        """Set a tag on the span."""
        self.tags[key] = value

    def finish(self) -> None:
        """Mark span as finished."""
        self.end_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "span_id": self.span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "parent_span_id": self.parent_span_id,
            "tags": self.tags,
            "events": self.events,
        }


@dataclass
class TracingContext:
    """Context for distributed tracing."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    spans: List[Span] = field(default_factory=list)
    _current_span: Optional[Span] = field(default=None, repr=False)

    @classmethod
    def create(cls, parent_trace_id: str = None) -> "TracingContext":
        """Create a new tracing context."""
        return cls(
            trace_id=parent_trace_id or str(uuid.uuid4()),
            span_id=str(uuid.uuid4())[:16],
        )

    @contextmanager
    def span(self, name: str, tags: Dict[str, str] = None):
        """
        Create a new span within this trace.

        Usage:
            with ctx.span("database_query", tags={"table": "tasks"}):
                result = await db.query()
        """
        span = Span(
            span_id=str(uuid.uuid4())[:16],
            name=name,
            start_time=time.time(),
            parent_span_id=self._current_span.span_id if self._current_span else self.span_id,
            tags=tags or {},
        )

        previous_span = self._current_span
        self._current_span = span
        self.spans.append(span)

        try:
            yield span
        except Exception as e:
            span.set_tag("error", "true")
            span.add_event("exception", {"type": type(e).__name__, "message": str(e)})
            raise
        finally:
            span.finish()
            self._current_span = previous_span

    @asynccontextmanager
    async def async_span(self, name: str, tags: Dict[str, str] = None):
        """Async version of span context manager."""
        with self.span(name, tags) as span:
            yield span

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "spans": [s.to_dict() for s in self.spans],
        }


@contextmanager
def trace_operation(
    name: str,
    tags: Dict[str, str] = None,
    create_new: bool = False,
):
    """
    Context manager for tracing an operation.

    Usage:
        with trace_operation("process_task", tags={"task_id": task_id}):
            await process_task()
    """
    # Get or create trace context
    ctx = trace_context_var.get()
    if ctx is None or create_new:
        ctx = TracingContext.create()
        token = trace_context_var.set(ctx)
    else:
        token = None

    with ctx.span(name, tags) as span:
        try:
            yield span
        finally:
            if token:
                trace_context_var.reset(token)


@asynccontextmanager
async def async_trace_operation(
    name: str,
    tags: Dict[str, str] = None,
    create_new: bool = False,
):
    """Async version of trace_operation."""
    with trace_operation(name, tags, create_new) as span:
        yield span


T = TypeVar("T")


def traced(name: str = None, tags: Dict[str, str] = None):
    """
    Decorator to trace a function.

    Usage:
        @traced("fetch_user_data")
        async def fetch_user(user_id: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        operation_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with async_trace_operation(operation_name, tags):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with trace_operation(operation_name, tags):
                    return func(*args, **kwargs)
            return sync_wrapper

    return decorator


# =============================================================================
# Request Correlation
# =============================================================================


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the current request ID."""
    request_id_var.set(request_id)


@contextmanager
def request_context(request_id: str = None):
    """
    Context manager for request correlation.

    Usage:
        with request_context() as rid:
            logger.info("Processing request")  # Will include request_id
    """
    rid = request_id or generate_request_id()
    token = request_id_var.set(rid)
    try:
        yield rid
    finally:
        request_id_var.reset(token)


@asynccontextmanager
async def async_request_context(request_id: str = None):
    """Async version of request_context."""
    with request_context(request_id) as rid:
        yield rid
