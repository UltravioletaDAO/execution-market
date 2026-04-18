"""
Tests for structured JSON logging config.

Phase 2.3 — MASTER_PLAN_SAAS_PRODUCTION_HARDENING.

Verifies:
  - configure_logging() produces valid JSON per log record
  - Context fields (request_id, agent_id, task_id) propagate via ``extra``
  - EM_JSON_LOGS=false falls back to plain text
  - Standard metadata fields (time, level, service, env, git_sha) are always present
  - Missing context fields are omitted (no "None" string leakage)
  - Idempotent: calling twice does not double log handlers

Each test isolates the root logger state so ordering cannot leak between
cases. Production code (``mcp_server/main.py``) only calls
``configure_logging()`` once at module import, so these tests are the
only place where repeated reconfiguration is exercised.
"""

from __future__ import annotations

import io
import json
import logging
from typing import Iterator
from unittest.mock import patch

import pytest

from logging_config import (
    ContextFilter,
    EMJsonFormatter,
    configure_logging,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_root_logger() -> Iterator[None]:
    """Snapshot + restore root logger state around each test.

    configure_logging() mutates the root logger (level + handlers). Without
    restoration a failing assertion in one test could cascade into noise
    elsewhere. We snapshot both ``handlers`` and ``level`` so the original
    pytest-provided state is preserved.
    """
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    original_filters = list(root.filters)
    try:
        yield
    finally:
        # Strip anything the test added.
        for h in list(root.handlers):
            root.removeHandler(h)
        for f in list(root.filters):
            root.removeFilter(f)
        # Reattach originals.
        for h in original_handlers:
            root.addHandler(h)
        for f in original_filters:
            root.addFilter(f)
        root.setLevel(original_level)


def _capture_single_log_record(
    level: str = "INFO",
    env: dict | None = None,
    logger_name: str = "em.test",
    message: str = "hello",
    extra: dict | None = None,
) -> str:
    """Configure logging with optional env overrides, emit one record, return stdout.

    We swap sys.stdout for a StringIO temporarily because configure_logging()
    attaches a StreamHandler(sys.stdout). Then we re-run configure_logging()
    so the handler binds to our captured stream.
    """
    env = env or {}
    buf = io.StringIO()
    with patch.dict("os.environ", env, clear=False), patch("sys.stdout", buf):
        configure_logging(level=level)
        logger = logging.getLogger(logger_name)
        logger.log(getattr(logging, level.upper()), message, extra=extra or {})

        # Ensure handler flushes to our captured buffer.
        for h in logging.getLogger().handlers:
            h.flush()

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_json_format_produces_valid_json(clean_root_logger: None) -> None:
    """With EM_JSON_LOGS=true (default), every line must be parseable JSON."""
    output = _capture_single_log_record(
        env={"EM_JSON_LOGS": "true"},
        message="payment settled",
    )

    lines = [ln for ln in output.splitlines() if ln.strip()]
    assert lines, "configure_logging emitted no output"

    for line in lines:
        # json.loads raises on anything non-JSON — if this passes, the line is valid.
        payload = json.loads(line)
        assert isinstance(payload, dict), f"expected JSON object, got {type(payload)}"

    final = json.loads(lines[-1])
    assert final["message"] == "payment settled"


def test_context_fields_propagate_via_extra(clean_root_logger: None) -> None:
    """``extra={"request_id": ...}`` must surface in the JSON payload."""
    output = _capture_single_log_record(
        env={"EM_JSON_LOGS": "true"},
        message="request handled",
        extra={
            "request_id": "rid-abc123",
            "agent_id": "agent-2106",
            "task_id": "task-deadbeef",
        },
    )
    payload = json.loads(output.strip().splitlines()[-1])

    assert payload["request_id"] == "rid-abc123"
    assert payload["agent_id"] == "agent-2106"
    assert payload["task_id"] == "task-deadbeef"


def test_env_disable_falls_back_to_text(clean_root_logger: None) -> None:
    """EM_JSON_LOGS=false must produce non-JSON human-readable output."""
    output = _capture_single_log_record(
        env={"EM_JSON_LOGS": "false"},
        message="local dev line",
    )
    line = output.strip().splitlines()[-1]

    # The text formatter is ``%(asctime)s [%(levelname)s] %(name)s: %(message)s``.
    # We should NOT be able to parse it as JSON.
    with pytest.raises(json.JSONDecodeError):
        json.loads(line)

    assert "[INFO]" in line
    assert "local dev line" in line
    assert "em.test" in line


def test_level_metadata_included(clean_root_logger: None) -> None:
    """time / level / logger / service / env / git_sha appear on every record."""
    output = _capture_single_log_record(
        env={
            "EM_JSON_LOGS": "true",
            "ENVIRONMENT": "staging",
            "GIT_SHA": "abc1234",
        },
        message="metadata check",
    )
    payload = json.loads(output.strip().splitlines()[-1])

    # Numeric epoch time — BaseJsonFormatter's separate ``timestamp`` key
    # is ISO-8601; our ``time`` key is the raw float for numeric sorting.
    assert isinstance(payload["time"], (int, float))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "em.test"
    assert payload["service"] == "em-mcp-server"
    assert payload["env"] == "staging"
    assert payload["git_sha"] == "abc1234"

    # python-json-logger injects "timestamp" as ISO string when timestamp=True.
    assert "timestamp" in payload


def test_missing_context_fields_default_to_none(clean_root_logger: None) -> None:
    """Records without ``extra`` must NOT leak ``"request_id": null`` into JSON.

    ContextFilter sets missing fields to Python ``None``, and the formatter
    explicitly skips ``None``-valued correlation fields so CloudWatch
    doesn't get polluted with empty slots.
    """
    output = _capture_single_log_record(
        env={"EM_JSON_LOGS": "true"},
        message="no context",
    )
    line = output.strip().splitlines()[-1]
    payload = json.loads(line)

    # Raw JSON must not contain the literal string "None" from a mis-cast.
    assert '"None"' not in line

    for field in ("request_id", "agent_id", "task_id", "path", "method", "status"):
        assert field not in payload, (
            f"unset context field {field!r} leaked into JSON payload: {payload}"
        )


def test_idempotent_no_duplicate_handlers(clean_root_logger: None) -> None:
    """Calling configure_logging twice must not stack handlers (Uvicorn reload)."""
    with patch.dict("os.environ", {"EM_JSON_LOGS": "true"}, clear=False):
        configure_logging()
        first_count = len(logging.getLogger().handlers)
        configure_logging()
        second_count = len(logging.getLogger().handlers)

    assert first_count == 1
    assert second_count == 1


def test_context_filter_defaults_missing_fields() -> None:
    """Unit test: ContextFilter injects None for any of the 6 context fields."""
    f = ContextFilter()
    record = logging.LogRecord(
        name="em.unit",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="x",
        args=(),
        exc_info=None,
    )

    assert f.filter(record) is True
    for field in ("request_id", "agent_id", "task_id", "path", "method", "status"):
        assert hasattr(record, field)
        assert getattr(record, field) is None


def test_emjsonformatter_uses_service_name(clean_root_logger: None) -> None:
    """Unit test: EMJsonFormatter.add_fields must emit service='em-mcp-server'."""
    formatter = EMJsonFormatter("%(message)s", timestamp=True)
    record = logging.LogRecord(
        name="em.unit",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="direct formatter check",
        args=(),
        exc_info=None,
    )
    rendered = formatter.format(record)
    payload = json.loads(rendered)
    assert payload["service"] == "em-mcp-server"
    assert payload["logger"] == "em.unit"
    assert payload["level"] == "INFO"
