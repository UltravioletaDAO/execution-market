"""
TaskValidator — Pre-Routing Task Validation Pipeline
=====================================================

Module #58 in the KK V2 Swarm.

Validates tasks before they enter the routing pipeline. Catches
malformed, uneconomic, or unroutable tasks early — saving signal
evaluation, chain routing, and fleet querying cycles for tasks
that would inevitably fail.

Architecture:

    ┌────────────────────────────────────────────────────────┐
    │                   TaskValidator                         │
    │                                                         │
    │  Task ──► [Rule 1] ──► [Rule 2] ──► ... ──► [Rule N]  │
    │               │             │                    │      │
    │               ▼             ▼                    ▼      │
    │          ValidationResult (pass/warn/reject)            │
    │               │                                         │
    │               ▼                                         │
    │          ValidationReport (batch summary)               │
    └────────────────────────────────────────────────────────┘

Validation Rules (built-in):
    1. REQUIRED_FIELDS — title, description, bounty present
    2. BOUNTY_MINIMUM — bounty above economic floor ($0.01)
    3. BOUNTY_MAXIMUM — bounty below sanity ceiling ($10,000)
    4. DESCRIPTION_LENGTH — description not empty, < 10K chars
    5. EVIDENCE_TYPES — only valid evidence type enums
    6. DEADLINE_FUTURE — deadline is in the future
    7. DEADLINE_REASONABLE — deadline not absurdly far (< 1 year)
    8. NETWORK_SUPPORTED — requested network is in enabled list
    9. SKILL_PARSEABLE — required skills are parseable strings
    10. DUPLICATE_DETECTION — task isn't near-duplicate of recent

Custom rules can be added via add_rule().

Usage:
    from mcp_server.swarm.task_validator import TaskValidator

    validator = TaskValidator()
    result = validator.validate(task_dict)

    if result.passed:
        # Route the task
        pipeline.process(task)
    else:
        # Handle rejection
        print(result.reasons)

    # Batch validation
    report = validator.validate_batch(tasks)
    routable = report.passed_tasks
"""

import hashlib
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("em.swarm.task_validator")


# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

VALID_EVIDENCE_TYPES = frozenset(
    {
        "photo",
        "photo_geo",
        "video",
        "document",
        "receipt",
        "signature",
        "notarized",
        "timestamp_proof",
        "text_response",
        "measurement",
        "screenshot",
    }
)

DEFAULT_ENABLED_NETWORKS = frozenset(
    {
        "base",
        "ethereum",
        "polygon",
        "arbitrum",
        "celo",
        "monad",
        "avalanche",
        "optimism",
    }
)

# Reasonable defaults
DEFAULT_MIN_BOUNTY = 0.01  # $0.01 minimum
DEFAULT_MAX_BOUNTY = 10_000.0  # $10K sanity ceiling
DEFAULT_MAX_DESCRIPTION_LENGTH = 10_000  # 10K chars
DEFAULT_MAX_DEADLINE_DAYS = 365  # 1 year
DEFAULT_DUPLICATE_WINDOW = 100  # Check last 100 tasks
DEFAULT_DUPLICATE_THRESHOLD = 0.85  # 85% similarity = duplicate


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────


class ValidationSeverity(str, Enum):
    """Severity level for validation findings."""

    PASS = "pass"  # Task is valid
    WARNING = "warning"  # Task is valid but suspicious
    REJECT = "reject"  # Task should not be routed


class ValidationRuleId(str, Enum):
    """Built-in validation rule identifiers."""

    REQUIRED_FIELDS = "required_fields"
    BOUNTY_MINIMUM = "bounty_minimum"
    BOUNTY_MAXIMUM = "bounty_maximum"
    DESCRIPTION_LENGTH = "description_length"
    EVIDENCE_TYPES = "evidence_types"
    DEADLINE_FUTURE = "deadline_future"
    DEADLINE_REASONABLE = "deadline_reasonable"
    NETWORK_SUPPORTED = "network_supported"
    SKILL_PARSEABLE = "skill_parseable"
    DUPLICATE_DETECTION = "duplicate_detection"


@dataclass
class ValidationFinding:
    """A single finding from a validation rule."""

    rule_id: str
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    value: Any = None

    def to_dict(self) -> dict:
        d = {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.field:
            d["field"] = self.field
        if self.value is not None:
            d["value"] = str(self.value)[:200]
        return d


@dataclass
class ValidationResult:
    """Result of validating a single task."""

    task_id: Optional[str] = None
    findings: list[ValidationFinding] = field(default_factory=list)
    validated_at: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        """Task passed if no REJECT findings."""
        return not any(f.severity == ValidationSeverity.REJECT for f in self.findings)

    @property
    def warnings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == ValidationSeverity.WARNING]

    @property
    def rejections(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == ValidationSeverity.REJECT]

    @property
    def reasons(self) -> list[str]:
        """Human-readable rejection reasons."""
        return [f.message for f in self.rejections]

    @property
    def warning_messages(self) -> list[str]:
        """Human-readable warning messages."""
        return [f.message for f in self.warnings]

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "passed": self.passed,
            "rejection_count": len(self.rejections),
            "warning_count": len(self.warnings),
            "findings": [f.to_dict() for f in self.findings],
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class ValidationReport:
    """Result of validating a batch of tasks."""

    results: list[ValidationResult] = field(default_factory=list)
    validated_at: float = field(default_factory=time.time)
    total_duration_ms: float = 0.0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def rejected_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.passed_count / len(self.results)

    @property
    def passed_tasks(self) -> list[ValidationResult]:
        return [r for r in self.results if r.passed]

    @property
    def rejected_tasks(self) -> list[ValidationResult]:
        return [r for r in self.results if not r.passed]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed_count,
            "rejected": self.rejected_count,
            "pass_rate": round(self.pass_rate, 3),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "results": [r.to_dict() for r in self.results],
        }

    def summary(self) -> str:
        return (
            f"Validated {self.total} tasks: "
            f"{self.passed_count} passed, "
            f"{self.rejected_count} rejected "
            f"({self.pass_rate:.0%} pass rate) "
            f"in {self.total_duration_ms:.0f}ms"
        )


@dataclass
class ValidationRule:
    """A pluggable validation rule."""

    rule_id: str
    name: str
    description: str
    check: Callable[["TaskValidator", dict], list[ValidationFinding]]
    enabled: bool = True
    order: int = 100  # Lower = runs first

    def __repr__(self) -> str:
        state = "enabled" if self.enabled else "disabled"
        return f"ValidationRule({self.rule_id}, {state}, order={self.order})"


# ──────────────────────────────────────────────────────────────
# Built-in Rule Implementations
# ──────────────────────────────────────────────────────────────


def _check_required_fields(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure required fields are present and non-empty."""
    findings = []
    required = ["title", "description", "bounty"]

    for field_name in required:
        value = task.get(field_name)
        if value is None:
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.REQUIRED_FIELDS.value,
                    severity=ValidationSeverity.REJECT,
                    message=f"Missing required field: {field_name}",
                    field=field_name,
                )
            )
        elif isinstance(value, str) and not value.strip():
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.REQUIRED_FIELDS.value,
                    severity=ValidationSeverity.REJECT,
                    message=f"Required field is empty: {field_name}",
                    field=field_name,
                )
            )

    return findings


def _check_bounty_minimum(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure bounty meets minimum threshold."""
    findings = []
    bounty = task.get("bounty")

    if bounty is None:
        return findings  # Caught by required_fields

    try:
        bounty_val = float(bounty)
    except (TypeError, ValueError):
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.BOUNTY_MINIMUM.value,
                severity=ValidationSeverity.REJECT,
                message=f"Bounty is not a valid number: {bounty}",
                field="bounty",
                value=bounty,
            )
        )
        return findings

    if bounty_val <= 0:
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.BOUNTY_MINIMUM.value,
                severity=ValidationSeverity.REJECT,
                message=f"Bounty must be positive, got {bounty_val}",
                field="bounty",
                value=bounty_val,
            )
        )
    elif bounty_val < validator.min_bounty:
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.BOUNTY_MINIMUM.value,
                severity=ValidationSeverity.REJECT,
                message=(
                    f"Bounty ${bounty_val:.2f} below minimum "
                    f"${validator.min_bounty:.2f}"
                ),
                field="bounty",
                value=bounty_val,
            )
        )

    return findings


def _check_bounty_maximum(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure bounty doesn't exceed sanity ceiling."""
    findings = []
    bounty = task.get("bounty")

    if bounty is None:
        return findings

    try:
        bounty_val = float(bounty)
    except (TypeError, ValueError):
        return findings  # Caught by bounty_minimum

    if bounty_val > validator.max_bounty:
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.BOUNTY_MAXIMUM.value,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"Bounty ${bounty_val:.2f} exceeds ceiling "
                    f"${validator.max_bounty:.2f} — verify intentional"
                ),
                field="bounty",
                value=bounty_val,
            )
        )

    return findings


def _check_description_length(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure description is within reasonable bounds."""
    findings = []
    desc = task.get("description")

    if desc is None:
        return findings  # Caught by required_fields

    if not isinstance(desc, str):
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.DESCRIPTION_LENGTH.value,
                severity=ValidationSeverity.REJECT,
                message="Description must be a string",
                field="description",
            )
        )
        return findings

    stripped = desc.strip()

    if len(stripped) < 10:
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.DESCRIPTION_LENGTH.value,
                severity=ValidationSeverity.WARNING,
                message=f"Description very short ({len(stripped)} chars) — may be hard to fulfill",
                field="description",
                value=len(stripped),
            )
        )

    if len(stripped) > validator.max_description_length:
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.DESCRIPTION_LENGTH.value,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"Description very long ({len(stripped)} chars) — "
                    f"max recommended is {validator.max_description_length}"
                ),
                field="description",
                value=len(stripped),
            )
        )

    return findings


def _check_evidence_types(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure evidence types are valid enum values."""
    findings = []
    evidence_types = task.get("evidence_types") or task.get("evidence_required")

    if not evidence_types:
        return findings  # Optional field

    if isinstance(evidence_types, str):
        evidence_types = [evidence_types]

    if not isinstance(evidence_types, (list, tuple)):
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.EVIDENCE_TYPES.value,
                severity=ValidationSeverity.REJECT,
                message="evidence_types must be a list",
                field="evidence_types",
            )
        )
        return findings

    for et in evidence_types:
        if not isinstance(et, str):
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.EVIDENCE_TYPES.value,
                    severity=ValidationSeverity.REJECT,
                    message=f"Evidence type must be a string, got {type(et).__name__}",
                    field="evidence_types",
                    value=et,
                )
            )
        elif et not in VALID_EVIDENCE_TYPES:
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.EVIDENCE_TYPES.value,
                    severity=ValidationSeverity.REJECT,
                    message=f"Unknown evidence type: '{et}'. Valid: {sorted(VALID_EVIDENCE_TYPES)}",
                    field="evidence_types",
                    value=et,
                )
            )

    return findings


def _check_deadline_future(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure deadline is in the future."""
    findings = []
    deadline = task.get("deadline") or task.get("expires_at")

    if not deadline:
        return findings  # Optional field

    try:
        if isinstance(deadline, str):
            # Parse ISO 8601
            dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        elif isinstance(deadline, (int, float)):
            # Unix timestamp
            dt = datetime.fromtimestamp(deadline, tz=timezone.utc)
        else:
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.DEADLINE_FUTURE.value,
                    severity=ValidationSeverity.REJECT,
                    message=f"Deadline must be ISO string or timestamp, got {type(deadline).__name__}",
                    field="deadline",
                )
            )
            return findings

        now = datetime.now(timezone.utc)

        if dt <= now:
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.DEADLINE_FUTURE.value,
                    severity=ValidationSeverity.REJECT,
                    message=f"Deadline is in the past: {dt.isoformat()}",
                    field="deadline",
                    value=deadline,
                )
            )

    except (ValueError, OSError) as e:
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.DEADLINE_FUTURE.value,
                severity=ValidationSeverity.REJECT,
                message=f"Cannot parse deadline: {e}",
                field="deadline",
                value=deadline,
            )
        )

    return findings


def _check_deadline_reasonable(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure deadline is within reasonable bounds."""
    findings = []
    deadline = task.get("deadline") or task.get("expires_at")

    if not deadline:
        return findings

    try:
        if isinstance(deadline, str):
            dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        elif isinstance(deadline, (int, float)):
            dt = datetime.fromtimestamp(deadline, tz=timezone.utc)
        else:
            return findings  # Caught by deadline_future

        now = datetime.now(timezone.utc)
        days_away = (dt - now).total_seconds() / 86400

        if days_away > validator.max_deadline_days:
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.DEADLINE_REASONABLE.value,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Deadline is {days_away:.0f} days away — "
                        f"max recommended is {validator.max_deadline_days} days"
                    ),
                    field="deadline",
                    value=days_away,
                )
            )

    except (ValueError, OSError):
        pass  # Caught by deadline_future

    return findings


def _check_network_supported(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure requested network is in the supported set."""
    findings = []
    network = task.get("network") or task.get("chain")

    if not network:
        return findings  # Will default to base

    if isinstance(network, str):
        network_lower = network.lower().strip()
        if network_lower not in validator.enabled_networks:
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.NETWORK_SUPPORTED.value,
                    severity=ValidationSeverity.REJECT,
                    message=(
                        f"Unsupported network: '{network}'. "
                        f"Supported: {sorted(validator.enabled_networks)}"
                    ),
                    field="network",
                    value=network,
                )
            )
    else:
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.NETWORK_SUPPORTED.value,
                severity=ValidationSeverity.REJECT,
                message=f"Network must be a string, got {type(network).__name__}",
                field="network",
            )
        )

    return findings


def _check_skill_parseable(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Ensure required skills are parseable."""
    findings = []
    skills = task.get("required_skills") or task.get("skills")

    if not skills:
        return findings  # Optional

    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    if not isinstance(skills, (list, tuple)):
        findings.append(
            ValidationFinding(
                rule_id=ValidationRuleId.SKILL_PARSEABLE.value,
                severity=ValidationSeverity.REJECT,
                message="Skills must be a list or comma-separated string",
                field="skills",
            )
        )
        return findings

    for skill in skills:
        if not isinstance(skill, str):
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.SKILL_PARSEABLE.value,
                    severity=ValidationSeverity.REJECT,
                    message=f"Skill must be a string, got {type(skill).__name__}",
                    field="skills",
                    value=skill,
                )
            )
        elif len(skill.strip()) == 0:
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.SKILL_PARSEABLE.value,
                    severity=ValidationSeverity.WARNING,
                    message="Empty skill tag in list",
                    field="skills",
                )
            )
        elif not re.match(r"^[a-zA-Z0-9_\-\s/.]+$", skill):
            findings.append(
                ValidationFinding(
                    rule_id=ValidationRuleId.SKILL_PARSEABLE.value,
                    severity=ValidationSeverity.WARNING,
                    message=f"Skill '{skill}' contains unusual characters",
                    field="skills",
                    value=skill,
                )
            )

    return findings


def _check_duplicate_detection(
    validator: "TaskValidator", task: dict
) -> list[ValidationFinding]:
    """Detect near-duplicate tasks using content fingerprinting."""
    findings = []

    title = str(task.get("title", "")).strip().lower()
    desc = str(task.get("description", "")).strip().lower()

    if not title and not desc:
        return findings  # Nothing to compare

    # Create content fingerprint
    content = f"{title}|{desc}"
    fingerprint = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Check against recent fingerprints
    for recent_fp, recent_id, recent_time in validator._recent_fingerprints:
        if recent_fp == fingerprint:
            age_seconds = time.time() - recent_time
            if age_seconds < 3600:  # Within last hour = exact duplicate
                findings.append(
                    ValidationFinding(
                        rule_id=ValidationRuleId.DUPLICATE_DETECTION.value,
                        severity=ValidationSeverity.REJECT,
                        message=(
                            f"Exact duplicate of task {recent_id} "
                            f"submitted {age_seconds:.0f}s ago"
                        ),
                        field="content",
                        value=recent_id,
                    )
                )
            else:
                findings.append(
                    ValidationFinding(
                        rule_id=ValidationRuleId.DUPLICATE_DETECTION.value,
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Similar to task {recent_id} "
                            f"submitted {age_seconds / 3600:.1f}h ago"
                        ),
                        field="content",
                        value=recent_id,
                    )
                )

    # Fuzzy matching: simple token overlap
    if not findings:
        content_tokens = set(content.split())
        if len(content_tokens) >= 3:
            for recent_fp, recent_id, recent_time in validator._recent_fingerprints:
                recent_content = validator._fingerprint_content.get(recent_fp, "")
                recent_tokens = set(recent_content.split())
                if not recent_tokens:
                    continue

                intersection = content_tokens & recent_tokens
                union = content_tokens | recent_tokens
                similarity = len(intersection) / len(union) if union else 0

                if similarity >= validator.duplicate_threshold:
                    findings.append(
                        ValidationFinding(
                            rule_id=ValidationRuleId.DUPLICATE_DETECTION.value,
                            severity=ValidationSeverity.WARNING,
                            message=(
                                f"Task is {similarity:.0%} similar to {recent_id} — "
                                f"possible duplicate"
                            ),
                            field="content",
                            value=recent_id,
                        )
                    )
                    break  # One duplicate warning is enough

    # Register this task's fingerprint
    task_id = task.get("id") or task.get("task_id") or fingerprint
    validator._recent_fingerprints.append((fingerprint, task_id, time.time()))
    validator._fingerprint_content[fingerprint] = content

    # Prune old fingerprint content
    active_fps = {fp for fp, _, _ in validator._recent_fingerprints}
    stale = [k for k in validator._fingerprint_content if k not in active_fps]
    for k in stale:
        del validator._fingerprint_content[k]

    return findings


# ──────────────────────────────────────────────────────────────
# Default Rule Registry
# ──────────────────────────────────────────────────────────────

_DEFAULT_RULES = [
    ValidationRule(
        rule_id=ValidationRuleId.REQUIRED_FIELDS.value,
        name="Required Fields",
        description="Ensures title, description, and bounty are present",
        check=_check_required_fields,
        order=10,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.BOUNTY_MINIMUM.value,
        name="Bounty Minimum",
        description="Bounty meets economic floor",
        check=_check_bounty_minimum,
        order=20,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.BOUNTY_MAXIMUM.value,
        name="Bounty Maximum",
        description="Bounty below sanity ceiling",
        check=_check_bounty_maximum,
        order=21,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.DESCRIPTION_LENGTH.value,
        name="Description Length",
        description="Description within reasonable bounds",
        check=_check_description_length,
        order=30,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.EVIDENCE_TYPES.value,
        name="Evidence Types",
        description="Only valid evidence type enums",
        check=_check_evidence_types,
        order=40,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.DEADLINE_FUTURE.value,
        name="Deadline Future",
        description="Deadline is in the future",
        check=_check_deadline_future,
        order=50,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.DEADLINE_REASONABLE.value,
        name="Deadline Reasonable",
        description="Deadline within 1 year",
        check=_check_deadline_reasonable,
        order=51,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.NETWORK_SUPPORTED.value,
        name="Network Supported",
        description="Network is in enabled set",
        check=_check_network_supported,
        order=60,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.SKILL_PARSEABLE.value,
        name="Skill Parseable",
        description="Skills are valid strings",
        check=_check_skill_parseable,
        order=70,
    ),
    ValidationRule(
        rule_id=ValidationRuleId.DUPLICATE_DETECTION.value,
        name="Duplicate Detection",
        description="Detects near-duplicate tasks",
        check=_check_duplicate_detection,
        order=80,
    ),
]


# ──────────────────────────────────────────────────────────────
# TaskValidator
# ──────────────────────────────────────────────────────────────


class TaskValidator:
    """
    Pre-routing task validation pipeline.

    Runs tasks through a configurable set of validation rules
    before they enter the routing pipeline. Rejects invalid tasks
    early, saving compute on signal evaluation and chain routing.
    """

    def __init__(
        self,
        min_bounty: float = DEFAULT_MIN_BOUNTY,
        max_bounty: float = DEFAULT_MAX_BOUNTY,
        max_description_length: int = DEFAULT_MAX_DESCRIPTION_LENGTH,
        max_deadline_days: int = DEFAULT_MAX_DEADLINE_DAYS,
        enabled_networks: Optional[set[str]] = None,
        duplicate_window: int = DEFAULT_DUPLICATE_WINDOW,
        duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
        fail_fast: bool = False,
    ):
        """
        Args:
            min_bounty: Minimum bounty in USD
            max_bounty: Maximum bounty ceiling in USD
            max_description_length: Max description chars
            max_deadline_days: Max days into the future for deadlines
            enabled_networks: Set of supported network names
            duplicate_window: Number of recent tasks to check for duplicates
            duplicate_threshold: Jaccard similarity threshold for fuzzy duplicates
            fail_fast: Stop on first REJECT finding
        """
        self.min_bounty = min_bounty
        self.max_bounty = max_bounty
        self.max_description_length = max_description_length
        self.max_deadline_days = max_deadline_days
        self.enabled_networks = enabled_networks or set(DEFAULT_ENABLED_NETWORKS)
        self.duplicate_threshold = duplicate_threshold
        self.fail_fast = fail_fast

        # Rules registry
        self._rules: list[ValidationRule] = []
        for rule in _DEFAULT_RULES:
            self._rules.append(
                ValidationRule(
                    rule_id=rule.rule_id,
                    name=rule.name,
                    description=rule.description,
                    check=rule.check,
                    enabled=rule.enabled,
                    order=rule.order,
                )
            )

        # Duplicate detection state
        self._recent_fingerprints: deque[tuple[str, str, float]] = deque(
            maxlen=duplicate_window
        )
        self._fingerprint_content: dict[str, str] = {}

        # Metrics
        self._total_validated = 0
        self._total_passed = 0
        self._total_rejected = 0
        self._total_warnings = 0
        self._rule_hit_counts: dict[str, int] = {}
        self._validation_times: deque[float] = deque(maxlen=200)
        self._created_at = time.time()

    # ─── Rule Management ─────────────────────────────────────

    def add_rule(self, rule: ValidationRule) -> "TaskValidator":
        """Add a custom validation rule."""
        # Check for duplicate rule_id
        existing = {r.rule_id for r in self._rules}
        if rule.rule_id in existing:
            raise ValueError(f"Rule '{rule.rule_id}' already registered")
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.order)
        logger.info(
            f"TaskValidator: Added custom rule '{rule.rule_id}' (order={rule.order})"
        )
        return self

    def remove_rule(self, rule_id: str) -> "TaskValidator":
        """Remove a rule by id."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.rule_id != rule_id]
        if len(self._rules) < before:
            logger.info(f"TaskValidator: Removed rule '{rule_id}'")
        return self

    def enable_rule(self, rule_id: str) -> "TaskValidator":
        """Enable a specific rule."""
        for rule in self._rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                return self
        return self

    def disable_rule(self, rule_id: str) -> "TaskValidator":
        """Disable a specific rule."""
        for rule in self._rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                return self
        return self

    @property
    def rules(self) -> list[ValidationRule]:
        """All registered rules, sorted by order."""
        return sorted(self._rules, key=lambda r: r.order)

    @property
    def enabled_rules(self) -> list[ValidationRule]:
        """Only enabled rules, sorted by order."""
        return [r for r in self.rules if r.enabled]

    # ─── Core Validation ─────────────────────────────────────

    def validate(self, task: dict) -> ValidationResult:
        """
        Validate a single task against all enabled rules.

        Args:
            task: Task dictionary with fields like title, description, bounty, etc.

        Returns:
            ValidationResult with all findings.
        """
        start = time.time()
        result = ValidationResult(
            task_id=task.get("id") or task.get("task_id"),
        )

        for rule in self.enabled_rules:
            try:
                findings = rule.check(self, task)
                if findings:
                    result.findings.extend(findings)

                    # Track rule hits
                    for f in findings:
                        self._rule_hit_counts[f.rule_id] = (
                            self._rule_hit_counts.get(f.rule_id, 0) + 1
                        )

                    # Fail fast on first rejection
                    if self.fail_fast and any(
                        f.severity == ValidationSeverity.REJECT for f in findings
                    ):
                        break

            except Exception as e:
                logger.warning(
                    f"TaskValidator: Rule '{rule.rule_id}' raised exception: {e}"
                )
                result.findings.append(
                    ValidationFinding(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.WARNING,
                        message=f"Validation rule error: {e}",
                    )
                )

        elapsed_ms = (time.time() - start) * 1000
        result.duration_ms = elapsed_ms

        # Update metrics
        self._total_validated += 1
        if result.passed:
            self._total_passed += 1
        else:
            self._total_rejected += 1
        self._total_warnings += len(result.warnings)
        self._validation_times.append(elapsed_ms)

        return result

    def validate_batch(self, tasks: list[dict]) -> ValidationReport:
        """
        Validate a batch of tasks.

        Args:
            tasks: List of task dictionaries

        Returns:
            ValidationReport with all results.
        """
        start = time.time()
        report = ValidationReport()

        for task in tasks:
            result = self.validate(task)
            report.results.append(result)

        report.total_duration_ms = (time.time() - start) * 1000
        return report

    def is_valid(self, task: dict) -> bool:
        """Quick check: does this task pass validation?"""
        return self.validate(task).passed

    # ─── Metrics & Diagnostics ───────────────────────────────

    def metrics(self) -> dict:
        """Validation metrics snapshot."""
        uptime = time.time() - self._created_at
        avg_time = (
            sum(self._validation_times) / len(self._validation_times)
            if self._validation_times
            else 0
        )
        p99_time = (
            sorted(self._validation_times)[int(len(self._validation_times) * 0.99)]
            if len(self._validation_times) > 10
            else avg_time
        )

        return {
            "total_validated": self._total_validated,
            "total_passed": self._total_passed,
            "total_rejected": self._total_rejected,
            "total_warnings": self._total_warnings,
            "pass_rate": (
                self._total_passed / self._total_validated
                if self._total_validated > 0
                else 0.0
            ),
            "avg_validation_ms": round(avg_time, 2),
            "p99_validation_ms": round(p99_time, 2),
            "uptime_seconds": round(uptime, 0),
            "rules_enabled": len(self.enabled_rules),
            "rules_total": len(self._rules),
            "rule_hit_counts": dict(self._rule_hit_counts),
        }

    def top_rejection_reasons(self, limit: int = 5) -> list[tuple[str, int]]:
        """Top N most frequently triggered rules."""
        sorted_rules = sorted(
            self._rule_hit_counts.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_rules[:limit]

    def status(self) -> dict:
        """Full status for diagnostics."""
        return {
            "component": "TaskValidator",
            "module": "#58",
            "healthy": True,
            "fail_fast": self.fail_fast,
            "config": {
                "min_bounty": self.min_bounty,
                "max_bounty": self.max_bounty,
                "max_description_length": self.max_description_length,
                "max_deadline_days": self.max_deadline_days,
                "enabled_networks": sorted(self.enabled_networks),
                "duplicate_threshold": self.duplicate_threshold,
            },
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "enabled": r.enabled,
                    "order": r.order,
                    "hits": self._rule_hit_counts.get(r.rule_id, 0),
                }
                for r in self.rules
            ],
            "metrics": self.metrics(),
        }

    def health_check(self) -> dict:
        """Quick health check."""
        return {
            "component": "TaskValidator",
            "healthy": True,
            "rules_enabled": len(self.enabled_rules),
            "total_validated": self._total_validated,
            "pass_rate": (
                round(self._total_passed / self._total_validated, 3)
                if self._total_validated > 0
                else None
            ),
        }

    def reset_metrics(self) -> None:
        """Reset all accumulated metrics."""
        self._total_validated = 0
        self._total_passed = 0
        self._total_rejected = 0
        self._total_warnings = 0
        self._rule_hit_counts.clear()
        self._validation_times.clear()
        logger.info("TaskValidator: Metrics reset")

    def clear_duplicates(self) -> None:
        """Clear duplicate detection history."""
        self._recent_fingerprints.clear()
        self._fingerprint_content.clear()
        logger.info("TaskValidator: Duplicate detection history cleared")

    # ─── Persistence ─────────────────────────────────────────

    def save(self) -> dict:
        """Export validator state for persistence."""
        return {
            "version": 1,
            "config": {
                "min_bounty": self.min_bounty,
                "max_bounty": self.max_bounty,
                "max_description_length": self.max_description_length,
                "max_deadline_days": self.max_deadline_days,
                "enabled_networks": sorted(self.enabled_networks),
                "duplicate_threshold": self.duplicate_threshold,
                "fail_fast": self.fail_fast,
            },
            "disabled_rules": [r.rule_id for r in self._rules if not r.enabled],
            "metrics": {
                "total_validated": self._total_validated,
                "total_passed": self._total_passed,
                "total_rejected": self._total_rejected,
                "total_warnings": self._total_warnings,
                "rule_hit_counts": dict(self._rule_hit_counts),
            },
            "saved_at": time.time(),
        }

    @classmethod
    def load(cls, data: dict) -> "TaskValidator":
        """Create a TaskValidator from saved state."""
        config = data.get("config", {})
        validator = cls(
            min_bounty=config.get("min_bounty", DEFAULT_MIN_BOUNTY),
            max_bounty=config.get("max_bounty", DEFAULT_MAX_BOUNTY),
            max_description_length=config.get(
                "max_description_length", DEFAULT_MAX_DESCRIPTION_LENGTH
            ),
            max_deadline_days=config.get(
                "max_deadline_days", DEFAULT_MAX_DEADLINE_DAYS
            ),
            enabled_networks=set(
                config.get("enabled_networks", DEFAULT_ENABLED_NETWORKS)
            ),
            duplicate_threshold=config.get(
                "duplicate_threshold", DEFAULT_DUPLICATE_THRESHOLD
            ),
            fail_fast=config.get("fail_fast", False),
        )

        # Restore disabled rules
        for rule_id in data.get("disabled_rules", []):
            validator.disable_rule(rule_id)

        # Restore metrics
        metrics = data.get("metrics", {})
        validator._total_validated = metrics.get("total_validated", 0)
        validator._total_passed = metrics.get("total_passed", 0)
        validator._total_rejected = metrics.get("total_rejected", 0)
        validator._total_warnings = metrics.get("total_warnings", 0)
        validator._rule_hit_counts = dict(metrics.get("rule_hit_counts", {}))

        return validator

    # ─── Dunder ───────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"TaskValidator("
            f"rules={len(self.enabled_rules)}/{len(self._rules)}, "
            f"validated={self._total_validated}, "
            f"pass_rate={self._total_passed}/{self._total_validated}"
            f")"
        )
