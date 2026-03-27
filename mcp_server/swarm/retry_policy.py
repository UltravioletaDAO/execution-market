"""
RetryPolicy — Configurable retry logic for failed task routing and agent errors.

Implements exponential backoff, jitter, circuit breaking, and dead-letter
queue semantics. Works with the SwarmCoordinator to handle:

1. Routing failures (no agents available → backoff → retry)
2. Task execution failures (agent error → escalate strategy → retry)
3. API failures (EM API unreachable → circuit breaker → fallback)
4. Agent degradation (heartbeat timeout → retry with healthy agent)

Usage:
    policy = RetryPolicy()

    # Check if a task should be retried
    decision = policy.should_retry("task-123", error="timeout")
    if decision.retry:
        await asyncio.sleep(decision.delay_seconds)
        coordinator.process_task_queue()
    elif decision.dead_letter:
        notify_human(decision.reason)

    # Circuit breaker for external APIs
    if policy.circuit_open("em_api"):
        use_cached_data()
    else:
        try:
            result = em_client.list_tasks()
            policy.record_success("em_api")
        except Exception:
            policy.record_failure("em_api")
"""

import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RetryStrategy(str, Enum):
    """How to retry a failed operation."""

    IMMEDIATE = "immediate"  # Retry right away
    LINEAR = "linear"  # Fixed delay between retries
    EXPONENTIAL = "exponential"  # Exponential backoff
    ESCALATING = "escalating"  # Change routing strategy on each retry


class DeadLetterReason(str, Enum):
    """Why a task was sent to the dead-letter queue."""

    MAX_RETRIES_EXHAUSTED = "max_retries_exhausted"
    CIRCUIT_OPEN = "circuit_open"
    BUDGET_BLOCKED = "budget_blocked"
    NO_ELIGIBLE_AGENTS = "no_eligible_agents"
    TASK_EXPIRED = "task_expired"
    MANUAL_REJECT = "manual_reject"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, no requests allowed
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryDecision:
    """The policy's decision about whether to retry."""

    retry: bool
    delay_seconds: float = 0.0
    attempt: int = 0
    max_attempts: int = 0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    suggested_routing_strategy: Optional[str] = None  # For escalating strategy
    dead_letter: bool = False
    dead_letter_reason: Optional[DeadLetterReason] = None
    reason: str = ""

    def to_dict(self) -> dict:
        d = {
            "retry": self.retry,
            "delay_seconds": round(self.delay_seconds, 2),
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "strategy": self.strategy.value,
        }
        if self.suggested_routing_strategy:
            d["suggested_routing_strategy"] = self.suggested_routing_strategy
        if self.dead_letter:
            d["dead_letter"] = True
            d["dead_letter_reason"] = (
                self.dead_letter_reason.value if self.dead_letter_reason else None
            )
            d["reason"] = self.reason
        return d


@dataclass
class RetryRecord:
    """Tracks retry state for a single task."""

    task_id: str
    attempts: int = 0
    first_failure_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_error: str = ""
    errors: list[str] = field(default_factory=list)
    dead_lettered: bool = False
    dead_letter_reason: Optional[DeadLetterReason] = None

    def record_attempt(self, error: str = "") -> None:
        now = datetime.now(timezone.utc)
        self.attempts += 1
        self.last_failure_at = now
        self.last_error = error
        if self.first_failure_at is None:
            self.first_failure_at = now
        if error:
            # Keep last 10 errors
            self.errors = (self.errors + [error])[-10:]


@dataclass
class CircuitBreaker:
    """Circuit breaker for external service calls."""

    name: str
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout_seconds: float = 60.0  # Time before half-open
    half_open_max_calls: int = 1  # Calls allowed in half-open

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: Optional[datetime] = None
    last_state_change: Optional[datetime] = None
    half_open_calls: int = 0

    def _transition(self, new_state: CircuitState) -> None:
        self.state = new_state
        self.last_state_change = datetime.now(timezone.utc)

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            # Recovered — close the circuit
            self._transition(CircuitState.CLOSED)
            self.failure_count = 0
            self.half_open_calls = 0
        elif self.state == CircuitState.CLOSED:
            self.success_count += 1
            # Decay failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        now = datetime.now(timezone.utc)
        self.failure_count += 1
        self.last_failure_at = now

        if self.state == CircuitState.HALF_OPEN:
            # Failed during probe — reopen
            self._transition(CircuitState.OPEN)
            self.half_open_calls = 0
        elif (
            self.state == CircuitState.CLOSED
            and self.failure_count >= self.failure_threshold
        ):
            self._transition(CircuitState.OPEN)

    def is_open(self) -> bool:
        """Check if the circuit is open (blocking calls)."""
        if self.state == CircuitState.CLOSED:
            return False

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_at:
                elapsed = (
                    datetime.now(timezone.utc) - self.last_failure_at
                ).total_seconds()
                if elapsed >= self.recovery_timeout_seconds:
                    self._transition(CircuitState.HALF_OPEN)
                    self.half_open_calls = 0
                    return False
            return True

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls >= self.half_open_max_calls

        return False

    def allow_call(self) -> bool:
        """Check if a call is allowed. Increments half-open counter."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if not self.is_open():
                # Transitioned to half-open
                self.half_open_calls += 1
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        return False

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_at": (
                self.last_failure_at.isoformat() if self.last_failure_at else None
            ),
        }


# Escalating strategy sequence: retry with increasingly aggressive strategies
ESCALATION_SEQUENCE = [
    "best_fit",
    "round_robin",
    "budget_aware",
    "best_fit",  # Final attempt: back to best_fit with lower threshold
]


class RetryPolicy:
    """
    Configurable retry policy for the swarm coordinator.

    Handles retry decisions with backoff, jitter, circuit breaking,
    and dead-letter queue semantics.

    Usage:
        policy = RetryPolicy(max_retries=5, base_delay=2.0)

        # Task-level retries
        decision = policy.should_retry("task-123", error="no agents")
        if decision.retry:
            time.sleep(decision.delay_seconds)

        # Circuit breakers for external services
        if policy.circuit_allows("em_api"):
            try:
                result = call_api()
                policy.record_circuit_success("em_api")
            except:
                policy.record_circuit_failure("em_api")
    """

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 2.0,
        max_delay: float = 120.0,
        jitter_factor: float = 0.25,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        escalate_on_retry: bool = True,
        dead_letter_after_seconds: float = 3600.0,  # 1 hour max lifetime
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor
        self.strategy = strategy
        self.escalate_on_retry = escalate_on_retry
        self.dead_letter_after_seconds = dead_letter_after_seconds

        # Track retry state per task
        self._records: dict[str, RetryRecord] = {}
        self._dead_letters: deque[RetryRecord] = deque(maxlen=500)

        # Circuit breakers by service name
        self._circuits: dict[str, CircuitBreaker] = {}

    def should_retry(
        self,
        task_id: str,
        error: str = "",
        force_dead_letter: bool = False,
    ) -> RetryDecision:
        """
        Determine whether a task should be retried.

        Records the failure attempt and returns a decision with:
        - Whether to retry
        - How long to wait
        - Suggested routing strategy (if escalating)
        - Dead-letter info if max retries exceeded
        """
        record = self._get_or_create_record(task_id)
        record.record_attempt(error)

        # Force dead-letter (manual rejection, budget blocked, etc.)
        if force_dead_letter:
            return self._dead_letter(
                record, DeadLetterReason.MANUAL_REJECT, f"Force dead-lettered: {error}"
            )

        # Check time-based expiry
        if record.first_failure_at:
            elapsed = (
                datetime.now(timezone.utc) - record.first_failure_at
            ).total_seconds()
            if elapsed >= self.dead_letter_after_seconds:
                return self._dead_letter(
                    record,
                    DeadLetterReason.TASK_EXPIRED,
                    f"Exceeded max retry lifetime ({self.dead_letter_after_seconds}s)",
                )

        # Check attempt count
        if record.attempts > self.max_retries:
            return self._dead_letter(
                record,
                DeadLetterReason.MAX_RETRIES_EXHAUSTED,
                f"Exhausted {self.max_retries} retries. Last error: {error}",
            )

        # Compute delay
        delay = self._compute_delay(record.attempts)

        # Determine routing strategy suggestion
        suggested_strategy = None
        if self.escalate_on_retry and record.attempts > 1:
            idx = min(record.attempts - 1, len(ESCALATION_SEQUENCE) - 1)
            suggested_strategy = ESCALATION_SEQUENCE[idx]

        return RetryDecision(
            retry=True,
            delay_seconds=delay,
            attempt=record.attempts,
            max_attempts=self.max_retries,
            strategy=self.strategy,
            suggested_routing_strategy=suggested_strategy,
            reason=f"Retry {record.attempts}/{self.max_retries}: {error}",
        )

    def _compute_delay(self, attempt: int) -> float:
        """Compute delay with jitter."""
        if self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0

        if self.strategy == RetryStrategy.LINEAR:
            raw_delay = self.base_delay * attempt
        elif self.strategy in (RetryStrategy.EXPONENTIAL, RetryStrategy.ESCALATING):
            raw_delay = self.base_delay * (2 ** (attempt - 1))
        else:
            raw_delay = self.base_delay

        # Apply max cap
        raw_delay = min(raw_delay, self.max_delay)

        # Apply jitter (±jitter_factor)
        if self.jitter_factor > 0:
            jitter = raw_delay * self.jitter_factor
            raw_delay += random.uniform(-jitter, jitter)

        return max(0, raw_delay)

    def _dead_letter(
        self,
        record: RetryRecord,
        reason: DeadLetterReason,
        message: str,
    ) -> RetryDecision:
        """Send a task to the dead-letter queue."""
        record.dead_lettered = True
        record.dead_letter_reason = reason
        self._dead_letters.append(record)

        return RetryDecision(
            retry=False,
            attempt=record.attempts,
            max_attempts=self.max_retries,
            strategy=self.strategy,
            dead_letter=True,
            dead_letter_reason=reason,
            reason=message,
        )

    def _get_or_create_record(self, task_id: str) -> RetryRecord:
        if task_id not in self._records:
            self._records[task_id] = RetryRecord(task_id=task_id)
        return self._records[task_id]

    # ─── Circuit Breakers ─────────────────────────────────────────────────

    def get_or_create_circuit(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout_seconds=recovery_timeout,
            )
        return self._circuits[name]

    def circuit_allows(self, name: str) -> bool:
        """Check if a circuit breaker allows a call."""
        circuit = self._circuits.get(name)
        if circuit is None:
            return True  # No circuit → always allow
        return circuit.allow_call()

    def record_circuit_success(self, name: str) -> None:
        """Record a successful call for a circuit breaker."""
        circuit = self._circuits.get(name)
        if circuit:
            circuit.record_success()

    def record_circuit_failure(self, name: str) -> None:
        """Record a failed call for a circuit breaker."""
        circuit = self._circuits.get(name)
        if circuit:
            circuit.record_failure()

    def circuit_open(self, name: str) -> bool:
        """Check if a circuit is currently open (blocking calls)."""
        circuit = self._circuits.get(name)
        if circuit is None:
            return False
        return circuit.is_open()

    # ─── Introspection ────────────────────────────────────────────────────

    def get_retry_record(self, task_id: str) -> Optional[dict]:
        """Get retry state for a task."""
        record = self._records.get(task_id)
        if record is None:
            return None
        return {
            "task_id": record.task_id,
            "attempts": record.attempts,
            "first_failure_at": (
                record.first_failure_at.isoformat() if record.first_failure_at else None
            ),
            "last_failure_at": (
                record.last_failure_at.isoformat() if record.last_failure_at else None
            ),
            "last_error": record.last_error,
            "dead_lettered": record.dead_lettered,
        }

    def get_dead_letters(self, limit: int = 50) -> list[dict]:
        """Get tasks in the dead-letter queue."""
        return [
            {
                "task_id": r.task_id,
                "attempts": r.attempts,
                "reason": r.dead_letter_reason.value if r.dead_letter_reason else None,
                "last_error": r.last_error,
                "first_failure_at": (
                    r.first_failure_at.isoformat() if r.first_failure_at else None
                ),
            }
            for r in list(self._dead_letters)[-limit:]
        ]

    def get_circuit_status(self) -> dict:
        """Get status of all circuit breakers."""
        return {name: cb.get_status() for name, cb in self._circuits.items()}

    def clear_record(self, task_id: str) -> bool:
        """Clear retry state for a task (e.g., on successful completion)."""
        if task_id in self._records:
            del self._records[task_id]
            return True
        return False

    def get_stats(self) -> dict:
        """Get aggregate retry statistics."""
        active = [r for r in self._records.values() if not r.dead_lettered]
        return {
            "active_retries": len(active),
            "dead_letters": len(self._dead_letters),
            "total_tracked": len(self._records),
            "circuits": {name: cb.state.value for name, cb in self._circuits.items()},
            "avg_attempts": (
                sum(r.attempts for r in active) / len(active) if active else 0
            ),
        }
