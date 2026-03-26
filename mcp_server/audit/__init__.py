"""Structured audit logging for observability."""

import json
import logging
import time

audit_logger = logging.getLogger("em.audit")


def audit_log(event: str, **kwargs):
    """Emit a structured JSON audit log entry."""
    entry = {
        "event": event,
        "ts": time.time(),
        **kwargs,
    }
    audit_logger.info(json.dumps(entry, default=str))
