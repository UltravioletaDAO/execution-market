"""
Structured JSON logging config for CloudWatch Insights queryability.

Enables queries like:
  fields @timestamp, level, request_id, agent_id, message
  | filter level='ERROR'
  | sort @timestamp desc

Phase 2.3 — MASTER_PLAN_SAAS_PRODUCTION_HARDENING.

Usage
-----
Call ``configure_logging()`` exactly once at application startup, BEFORE any
module acquires a logger at import time. ``mcp_server/main.py`` wires it in
right after the Sentry SDK block (itself the first substantive work in the
module) so the rest of the application inherits the JSON handler.

.. code-block:: python

    from logging_config import configure_logging
    configure_logging()

    import logging
    logger = logging.getLogger(__name__)

    # Minimal call — emits JSON with standard fields only
    logger.info("Payment settled")

    # With correlation context — propagates via ``extra``
    logger.info(
        "Payment settled",
        extra={"request_id": rid, "agent_id": aid, "task_id": tid},
    )

Environment variables
---------------------
``EM_JSON_LOGS`` (default ``true``)
    Set to ``false`` to fall back to the classic human-readable formatter.
    Useful for local dev / tailing logs in a terminal.

``ENVIRONMENT`` (default ``production``)
    Embedded into every record as ``env``.

``GIT_SHA`` (default ``unknown``)
    Embedded into every record as ``git_sha``. Populated by CI/CD.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Union

# python-json-logger moved ``JsonFormatter`` from ``pythonjsonlogger.jsonlogger``
# to ``pythonjsonlogger.json`` in v3.x. We try the new path first and fall
# back to the old one so the requirements.txt pin (``>=2.0.7``) stays broad.
try:
    from pythonjsonlogger.json import JsonFormatter as _BaseJsonFormatter  # type: ignore
except ImportError:  # pragma: no cover - v2.x fallback path
    from pythonjsonlogger.jsonlogger import JsonFormatter as _BaseJsonFormatter  # type: ignore


# Fields we expect to see on records when callers pass them via ``extra={}``.
# ContextFilter ensures they ALWAYS exist on the record (defaulting to None)
# so JsonFormatter can't accidentally render missing keys as string "None".
_CONTEXT_FIELDS = ("request_id", "agent_id", "task_id", "path", "method", "status")


class ContextFilter(logging.Filter):
    """Injects request context into log records if available.

    Without this filter, a record that was NOT emitted with
    ``extra={"request_id": ...}`` would lack the attribute entirely, and
    downstream code (e.g. formatters that copy context fields) would need
    defensive ``getattr(record, "request_id", None)`` everywhere.

    We default missing fields to ``None`` here so the formatter can use a
    single ``is not None`` check to decide whether to emit them.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        for field in _CONTEXT_FIELDS:
            if not hasattr(record, field):
                setattr(record, field, None)
        return True


class EMJsonFormatter(_BaseJsonFormatter):
    """Adds standard fields + environment metadata to every record.

    Every record ends up with at minimum:
        time, level, logger, service, env, git_sha, message

    Plus any of the correlation fields (``request_id``, ``agent_id``,
    ``task_id``, ``path``, ``method``, ``status``) that were populated via
    ``extra={}`` on the ``logger.*`` call. Missing correlation fields are
    omitted — we never emit ``"request_id": null`` just to prove the slot
    exists.
    """

    def add_fields(self, log_record, record, message_dict):  # type: ignore[override]
        super().add_fields(log_record, record, message_dict)

        # Deterministic top-level fields. Using ``record.created`` (float
        # seconds since epoch) keeps ingestion tools happy regardless of
        # whether python-json-logger's built-in ``timestamp`` ISO string is
        # also rendered (it is, under key "timestamp" — see __init__).
        log_record["time"] = record.created
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = "em-mcp-server"
        log_record["env"] = os.getenv("ENVIRONMENT", "production")
        log_record["git_sha"] = os.getenv("GIT_SHA", "unknown")

        # python-json-logger v3/v4 auto-extracts ALL non-reserved record
        # attributes (including our ContextFilter-injected defaults). Strip
        # correlation fields that were left at None so CloudWatch searches
        # aren't flooded with "request_id: null" slots. Callers opt-in by
        # passing ``extra={"request_id": rid}`` on the log call.
        for field in _CONTEXT_FIELDS:
            if log_record.get(field) is None:
                log_record.pop(field, None)


def configure_logging(level: Union[str, int] = "INFO") -> None:
    """Idempotent JSON logging setup. Call once at app startup.

    Set ``EM_JSON_LOGS=false`` to disable JSON formatting (useful for local
    dev where a human-readable stream is nicer to tail).

    Subsequent calls are safe — existing handlers on the root logger are
    removed before new ones are attached, so Uvicorn's ``--reload`` loop
    won't produce duplicate log lines.
    """
    json_enabled = os.getenv("EM_JSON_LOGS", "true").lower() != "false"

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid double-logs in Uvicorn reload.
    # Walking a copy of the list because we mutate ``root.handlers``.
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)

    if json_enabled:
        # ``timestamp=True`` -> python-json-logger adds an ISO-8601 UTC
        # "timestamp" field automatically. We also emit ``time`` as an
        # epoch float in add_fields for tools that prefer numeric sorting.
        formatter: logging.Formatter = EMJsonFormatter(
            "%(time)s %(level)s %(logger)s %(message)s",
            timestamp=True,
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())
    root.addHandler(handler)

    # Silence overly noisy loggers. These are fine at INFO in dev but
    # drown out CloudWatch in production. Keeping them at WARNING mirrors
    # the existing policy in health/monitoring.py (the legacy path that
    # this module replaces at the main.py entry point).
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("h2").setLevel(logging.WARNING)
