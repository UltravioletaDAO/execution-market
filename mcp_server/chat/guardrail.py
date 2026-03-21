"""
GuardrailFilter — Enhanced message filtering for the chat relay.

Two layers of protection:
1. **Slash commands**: Exact prefix match (``/approve``, ``/cancel``, etc.)
2. **NLP patterns**: Regex patterns catching natural-language action requests
   in English and Spanish (``cancel my task``, ``aprueba esto``, etc.)

Blocked attempts are returned as ``ChatError`` and logged for audit.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of a guardrail check."""

    allowed: bool
    reason: str = ""
    matched_pattern: str = ""


# ---------------------------------------------------------------------------
# Slash commands — always blocked
# ---------------------------------------------------------------------------

BLOCKED_COMMANDS: set[str] = {
    "/approve",
    "/reject",
    "/cancel",
    "/pay",
    "/release",
    "/refund",
    "/dispute",
    "/assign",
    "/claim",
    "/close",
}

# ---------------------------------------------------------------------------
# NLP patterns — natural language action requests (EN + ES)
# ---------------------------------------------------------------------------

_NLP_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Cancel
    (
        re.compile(
            r"\b(cancel|cancelar|cancela)\s+(my|mi|this|esta|the|la|el)\s+(task|tarea)\b",
            re.IGNORECASE,
        ),
        "cancel_task",
    ),
    # Pay me
    (
        re.compile(
            r"\b(pay|pagar|pagame|paga)\s+(me|now|ahora)\b",
            re.IGNORECASE,
        ),
        "pay_request",
    ),
    # Approve
    (
        re.compile(
            r"\b(approve|aprobar|aprueba)\s+(this|esto|the|la|my|mi|it)\b",
            re.IGNORECASE,
        ),
        "approve_request",
    ),
    # Release payment
    (
        re.compile(
            r"\b(release|liberar|libera)\s+(payment|pago|funds|fondos|the|el|los)\b",
            re.IGNORECASE,
        ),
        "release_request",
    ),
    # Reject
    (
        re.compile(
            r"\b(reject|rechazar|rechaza)\s+(this|esto|the|la|my|mi|it)\b",
            re.IGNORECASE,
        ),
        "reject_request",
    ),
    # Dispute
    (
        re.compile(
            r"\b(dispute|disputar|disputa)\s+(this|esto|the|la|my|mi|it)\b",
            re.IGNORECASE,
        ),
        "dispute_request",
    ),
    # Refund
    (
        re.compile(
            r"\b(refund|reembolsar|reembolsa|devolver|devuelve)\s+(my|mi|this|esto|the|el)\b",
            re.IGNORECASE,
        ),
        "refund_request",
    ),
]


class GuardrailFilter:
    """
    Checks outgoing chat messages for action commands and NLP action patterns.

    Usage::

        gf = GuardrailFilter()
        result = gf.check("cancel my task")
        if not result.allowed:
            send_error(result.reason)
    """

    def __init__(
        self,
        *,
        extra_commands: Optional[set[str]] = None,
        enable_nlp: bool = True,
    ):
        self._commands = BLOCKED_COMMANDS | (extra_commands or set())
        self._enable_nlp = enable_nlp
        self._stats: dict[str, int] = {
            "checked": 0,
            "blocked_command": 0,
            "blocked_nlp": 0,
            "allowed": 0,
        }

    def check(self, text: str) -> FilterResult:
        """Check a message against all guardrail layers.

        Returns ``FilterResult(allowed=True)`` if the message is safe,
        or ``FilterResult(allowed=False, reason=..., matched_pattern=...)``
        if it should be blocked.
        """
        self._stats["checked"] += 1
        stripped = text.strip()

        if not stripped:
            self._stats["allowed"] += 1
            return FilterResult(allowed=True)

        # Layer 1: Slash command prefix
        lower = stripped.lower()
        for cmd in self._commands:
            if lower.startswith(cmd):
                self._stats["blocked_command"] += 1
                return FilterResult(
                    allowed=False,
                    reason=(
                        f"Action commands ({cmd}) are not allowed in chat. "
                        "Use the app or API to perform task actions."
                    ),
                    matched_pattern=cmd,
                )

        # Layer 2: NLP patterns
        if self._enable_nlp:
            for pattern, label in _NLP_PATTERNS:
                if pattern.search(stripped):
                    self._stats["blocked_nlp"] += 1
                    return FilterResult(
                        allowed=False,
                        reason=(
                            "It looks like you're trying to perform a task action. "
                            "Use the app or API to approve, cancel, or manage tasks — "
                            "chat is for coordination only."
                        ),
                        matched_pattern=label,
                    )

        self._stats["allowed"] += 1
        return FilterResult(allowed=True)

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
