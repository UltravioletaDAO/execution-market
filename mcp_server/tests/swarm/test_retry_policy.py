"""
Tests for RetryPolicy — Configurable retry logic with circuit breaking.

Covers:
- Exponential backoff with jitter
- Linear and immediate retry strategies
- Max retry exhaustion → dead-letter queue
- Time-based task expiry
- Force dead-letter
- Circuit breaker state machine (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Circuit breaker recovery timeout
- Escalating routing strategy suggestions
- Record introspection and cleanup
- Dead-letter queue management
- Aggregate statistics
- Edge cases (zero retries, zero delay, concurrent records)
"""

import time
from datetime import datetime, timezone, timedelta

import pytest

from mcp_server.swarm.retry_policy import (
    RetryPolicy,
    RetryDecision,
    RetryRecord,
    RetryStrategy,
    DeadLetterReason,
    CircuitBreaker,
    CircuitState,
    ESCALATION_SEQUENCE,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def policy():
    """Standard retry policy."""
    return RetryPolicy(
        max_retries=5,
        base_delay=2.0,
        max_delay=60.0,
        jitter_factor=0.0,  # No jitter for deterministic tests
        strategy=RetryStrategy.EXPONENTIAL,
    )


@pytest.fixture
def linear_policy():
    """Linear retry policy."""
    return RetryPolicy(
        max_retries=3,
        base_delay=5.0,
        max_delay=60.0,
        jitter_factor=0.0,
        strategy=RetryStrategy.LINEAR,
    )


@pytest.fixture
def immediate_policy():
    """Immediate retry policy (no delay)."""
    return RetryPolicy(
        max_retries=3,
        base_delay=0.0,
        strategy=RetryStrategy.IMMEDIATE,
    )


@pytest.fixture
def circuit():
    """Fresh circuit breaker."""
    return CircuitBreaker(
        name="test_service",
        failure_threshold=3,
        recovery_timeout_seconds=5.0,
    )


# ─── Exponential Backoff ──────────────────────────────────────────────────────


class TestExponentialBackoff:
    def test_first_retry_uses_base_delay(self, policy):
        decision = policy.should_retry("t1", error="fail")
        assert decision.retry is True
        assert decision.delay_seconds == 2.0  # base_delay * 2^0

    def test_second_retry_doubles_delay(self, policy):
        policy.should_retry("t1", error="fail")
        decision = policy.should_retry("t1", error="fail again")
        assert decision.retry is True
        assert decision.delay_seconds == 4.0  # base_delay * 2^1

    def test_third_retry_quadruples_delay(self, policy):
        for _ in range(2):
            policy.should_retry("t1", error="fail")
        decision = policy.should_retry("t1", error="fail 3")
        assert decision.delay_seconds == 8.0  # base_delay * 2^2

    def test_delay_capped_at_max(self, policy):
        for _ in range(10):
            decision = policy.should_retry("t1", error="fail")
        # Delay should never exceed max_delay
        assert decision.delay_seconds <= policy.max_delay

    def test_jitter_applied_when_enabled(self):
        policy = RetryPolicy(
            max_retries=10,
            base_delay=10.0,
            jitter_factor=0.25,
            strategy=RetryStrategy.EXPONENTIAL,
        )
        delays = set()
        for i in range(20):
            decision = policy.should_retry(f"jitter-{i}", error="fail")
            delays.add(round(decision.delay_seconds, 4))

        # With jitter, delays should not all be identical
        assert len(delays) > 1

    def test_delay_never_negative(self):
        policy = RetryPolicy(
            max_retries=10,
            base_delay=1.0,
            jitter_factor=0.5,  # Large jitter
        )
        for i in range(50):
            decision = policy.should_retry(f"neg-{i}", error="fail")
            assert decision.delay_seconds >= 0


# ─── Linear Retry ─────────────────────────────────────────────────────────────


class TestLinearRetry:
    def test_linear_delay_grows_linearly(self, linear_policy):
        d1 = linear_policy.should_retry("t1", error="fail")
        assert d1.delay_seconds == 5.0  # base * 1

        d2 = linear_policy.should_retry("t1", error="fail")
        assert d2.delay_seconds == 10.0  # base * 2

        d3 = linear_policy.should_retry("t1", error="fail")
        assert d3.delay_seconds == 15.0  # base * 3


# ─── Immediate Retry ──────────────────────────────────────────────────────────


class TestImmediateRetry:
    def test_no_delay(self, immediate_policy):
        decision = immediate_policy.should_retry("t1", error="fail")
        assert decision.retry is True
        assert decision.delay_seconds == 0.0


# ─── Max Retries & Dead Letter ─────────────────────────────────────────────────


class TestMaxRetriesDeadLetter:
    def test_dead_letter_after_max_retries(self, policy):
        # 5 retries → all should succeed
        for i in range(5):
            decision = policy.should_retry("t1", error=f"fail {i}")
            assert decision.retry is True

        # 6th attempt → dead letter
        decision = policy.should_retry("t1", error="final fail")
        assert decision.retry is False
        assert decision.dead_letter is True
        assert decision.dead_letter_reason == DeadLetterReason.MAX_RETRIES_EXHAUSTED

    def test_dead_letter_preserves_error_info(self, policy):
        for _ in range(6):
            policy.should_retry("t1", error="persistent error")

        dead = policy.get_dead_letters()
        assert len(dead) == 1
        assert dead[0]["task_id"] == "t1"
        assert dead[0]["last_error"] == "persistent error"

    def test_zero_max_retries(self):
        policy = RetryPolicy(max_retries=0)
        decision = policy.should_retry("t1", error="no retries")
        # First attempt counts as attempt 1 which exceeds 0 max retries
        assert decision.retry is False
        assert decision.dead_letter is True

    def test_dead_letter_count(self, policy):
        for i in range(3):
            for _ in range(6):
                policy.should_retry(f"dl-{i}", error="fail")

        dead = policy.get_dead_letters()
        assert len(dead) == 3


# ─── Time-Based Expiry ────────────────────────────────────────────────────────


class TestTimeBasedExpiry:
    def test_task_expires_after_lifetime(self):
        policy = RetryPolicy(
            max_retries=100,
            dead_letter_after_seconds=10.0,
        )
        record = policy._get_or_create_record("t1")
        record.record_attempt("initial")
        # Backdate the first failure
        record.first_failure_at = datetime.now(timezone.utc) - timedelta(seconds=15)

        decision = policy.should_retry("t1", error="expired")
        assert decision.retry is False
        assert decision.dead_letter is True
        assert decision.dead_letter_reason == DeadLetterReason.TASK_EXPIRED


# ─── Force Dead Letter ────────────────────────────────────────────────────────


class TestForceDeadLetter:
    def test_force_dead_letter_on_first_attempt(self, policy):
        decision = policy.should_retry("t1", error="blocked", force_dead_letter=True)
        assert decision.retry is False
        assert decision.dead_letter is True
        assert decision.dead_letter_reason == DeadLetterReason.MANUAL_REJECT

    def test_force_dead_letter_preserves_error(self, policy):
        policy.should_retry("t1", error="first fail")
        decision = policy.should_retry(
            "t1", error="budget blocked", force_dead_letter=True
        )
        assert decision.retry is False
        assert decision.dead_letter is True
        assert "budget blocked" in decision.reason


# ─── Escalating Strategy ──────────────────────────────────────────────────────


class TestEscalatingStrategy:
    def test_first_attempt_no_escalation(self, policy):
        decision = policy.should_retry("t1", error="fail")
        # First attempt doesn't suggest a different strategy
        assert decision.suggested_routing_strategy is None

    def test_second_attempt_escalates(self, policy):
        policy.should_retry("t1", error="fail")
        decision = policy.should_retry("t1", error="fail again")
        assert decision.suggested_routing_strategy == ESCALATION_SEQUENCE[1]

    def test_escalation_follows_sequence(self, policy):
        strategies_seen = []
        for i in range(5):
            decision = policy.should_retry("t1", error=f"fail {i}")
            if decision.suggested_routing_strategy:
                strategies_seen.append(decision.suggested_routing_strategy)

        # Should follow the escalation sequence
        assert len(strategies_seen) >= 1

    def test_escalation_disabled(self):
        policy = RetryPolicy(
            max_retries=5,
            escalate_on_retry=False,
            jitter_factor=0.0,
        )
        for _ in range(3):
            decision = policy.should_retry("t1", error="fail")

        assert decision.suggested_routing_strategy is None


# ─── Circuit Breaker ──────────────────────────────────────────────────────────


class TestCircuitBreaker:
    def test_starts_closed(self, circuit):
        assert circuit.state == CircuitState.CLOSED
        assert circuit.is_open() is False

    def test_opens_after_threshold(self, circuit):
        for _ in range(3):
            circuit.record_failure()
        assert circuit.state == CircuitState.OPEN
        assert circuit.is_open() is True

    def test_stays_closed_below_threshold(self, circuit):
        circuit.record_failure()
        circuit.record_failure()
        assert circuit.state == CircuitState.CLOSED

    def test_blocks_calls_when_open(self, circuit):
        for _ in range(3):
            circuit.record_failure()
        assert circuit.allow_call() is False

    def test_allows_calls_when_closed(self, circuit):
        assert circuit.allow_call() is True
        circuit.record_failure()
        assert circuit.allow_call() is True

    def test_half_open_after_timeout(self):
        circuit = CircuitBreaker(
            name="fast",
            failure_threshold=2,
            recovery_timeout_seconds=0.1,
        )
        circuit.record_failure()
        circuit.record_failure()
        assert circuit.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)
        assert circuit.is_open() is False  # Should transition to HALF_OPEN
        assert circuit.state == CircuitState.HALF_OPEN

    def test_half_open_closes_on_success(self):
        circuit = CircuitBreaker(
            name="recover",
            failure_threshold=2,
            recovery_timeout_seconds=0.05,
        )
        circuit.record_failure()
        circuit.record_failure()
        time.sleep(0.1)
        circuit.is_open()  # Trigger transition to half-open

        circuit.record_success()
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    def test_half_open_reopens_on_failure(self):
        circuit = CircuitBreaker(
            name="relapse",
            failure_threshold=2,
            recovery_timeout_seconds=0.05,
        )
        circuit.record_failure()
        circuit.record_failure()
        time.sleep(0.1)
        circuit.is_open()  # Trigger half-open

        circuit.record_failure()
        assert circuit.state == CircuitState.OPEN

    def test_success_decays_failure_count(self, circuit):
        circuit.record_failure()
        circuit.record_failure()
        assert circuit.failure_count == 2

        circuit.record_success()
        assert circuit.failure_count == 1

    def test_half_open_limits_calls(self):
        circuit = CircuitBreaker(
            name="limited",
            failure_threshold=1,
            recovery_timeout_seconds=0.05,
            half_open_max_calls=1,
        )
        circuit.record_failure()
        time.sleep(0.1)

        # First call in half-open should be allowed
        assert circuit.allow_call() is True
        # Second call should be blocked
        assert circuit.allow_call() is False

    def test_status_dict(self, circuit):
        status = circuit.get_status()
        assert status["name"] == "test_service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0

    def test_status_after_failures(self, circuit):
        for _ in range(3):
            circuit.record_failure()
        status = circuit.get_status()
        assert status["state"] == "open"
        assert status["failure_count"] == 3
        assert status["last_failure_at"] is not None


# ─── Circuit Breakers in Policy ───────────────────────────────────────────────


class TestCircuitBreakersInPolicy:
    def test_create_circuit(self, policy):
        cb = policy.get_or_create_circuit("em_api", failure_threshold=3)
        assert cb.name == "em_api"
        assert cb.failure_threshold == 3

    def test_circuit_allows_initially(self, policy):
        policy.get_or_create_circuit("em_api")
        assert policy.circuit_allows("em_api") is True

    def test_circuit_blocks_after_failures(self, policy):
        policy.get_or_create_circuit("em_api", failure_threshold=2)
        policy.record_circuit_failure("em_api")
        policy.record_circuit_failure("em_api")
        assert policy.circuit_open("em_api") is True

    def test_circuit_recovers_after_success(self, policy):
        cb = policy.get_or_create_circuit(
            "em_api", failure_threshold=2, recovery_timeout=0.05
        )
        policy.record_circuit_failure("em_api")
        policy.record_circuit_failure("em_api")
        time.sleep(0.1)

        # Check allows (triggers half-open transition)
        assert policy.circuit_allows("em_api") is True
        policy.record_circuit_success("em_api")
        assert policy.circuit_open("em_api") is False

    def test_nonexistent_circuit_allows(self, policy):
        assert policy.circuit_allows("unknown") is True
        assert policy.circuit_open("unknown") is False

    def test_circuit_status_all(self, policy):
        policy.get_or_create_circuit("service_a")
        policy.get_or_create_circuit("service_b")
        policy.record_circuit_failure("service_a")

        status = policy.get_circuit_status()
        assert "service_a" in status
        assert "service_b" in status
        assert status["service_a"]["failure_count"] == 1


# ─── Record Introspection ────────────────────────────────────────────────────


class TestRecordIntrospection:
    def test_get_retry_record(self, policy):
        policy.should_retry("t1", error="initial fail")
        record = policy.get_retry_record("t1")
        assert record is not None
        assert record["task_id"] == "t1"
        assert record["attempts"] == 1
        assert record["last_error"] == "initial fail"

    def test_get_nonexistent_record(self, policy):
        assert policy.get_retry_record("nope") is None

    def test_clear_record(self, policy):
        policy.should_retry("t1", error="fail")
        assert policy.clear_record("t1") is True
        assert policy.get_retry_record("t1") is None

    def test_clear_nonexistent_record(self, policy):
        assert policy.clear_record("nope") is False


# ─── Dead Letter Queue ───────────────────────────────────────────────────────


class TestDeadLetterQueue:
    def test_dead_letters_limited(self, policy):
        for i in range(10):
            for _ in range(6):
                policy.should_retry(f"dl-{i}", error="fail")

        dead = policy.get_dead_letters(limit=5)
        assert len(dead) == 5

    def test_dead_letter_has_reason(self, policy):
        for _ in range(6):
            policy.should_retry("t1", error="persistent")

        dead = policy.get_dead_letters()
        assert dead[0]["reason"] == "max_retries_exhausted"


# ─── Statistics ───────────────────────────────────────────────────────────────


class TestStatistics:
    def test_stats_empty(self, policy):
        stats = policy.get_stats()
        assert stats["active_retries"] == 0
        assert stats["dead_letters"] == 0
        assert stats["total_tracked"] == 0

    def test_stats_after_retries(self, policy):
        policy.should_retry("t1", error="fail")
        policy.should_retry("t2", error="fail")

        stats = policy.get_stats()
        assert stats["active_retries"] == 2
        assert stats["total_tracked"] == 2
        assert stats["avg_attempts"] == 1.0

    def test_stats_with_dead_letters(self, policy):
        for _ in range(6):
            policy.should_retry("dead", error="fail")

        policy.should_retry("alive", error="fail")

        stats = policy.get_stats()
        assert stats["active_retries"] == 1  # "alive" still active
        assert stats["dead_letters"] == 1
        assert stats["total_tracked"] == 2

    def test_stats_includes_circuits(self, policy):
        policy.get_or_create_circuit("svc_a")
        stats = policy.get_stats()
        assert "svc_a" in stats["circuits"]
        assert stats["circuits"]["svc_a"] == "closed"


# ─── RetryDecision ────────────────────────────────────────────────────────────


class TestRetryDecision:
    def test_to_dict_retry(self):
        d = RetryDecision(
            retry=True,
            delay_seconds=4.0,
            attempt=2,
            max_attempts=5,
            strategy=RetryStrategy.EXPONENTIAL,
            suggested_routing_strategy="round_robin",
        )
        result = d.to_dict()
        assert result["retry"] is True
        assert result["delay_seconds"] == 4.0
        assert result["suggested_routing_strategy"] == "round_robin"
        assert "dead_letter" not in result

    def test_to_dict_dead_letter(self):
        d = RetryDecision(
            retry=False,
            dead_letter=True,
            dead_letter_reason=DeadLetterReason.MAX_RETRIES_EXHAUSTED,
            reason="All retries used",
            attempt=6,
            max_attempts=5,
        )
        result = d.to_dict()
        assert result["retry"] is False
        assert result["dead_letter"] is True
        assert result["dead_letter_reason"] == "max_retries_exhausted"


# ─── RetryRecord ──────────────────────────────────────────────────────────────


class TestRetryRecord:
    def test_record_attempt_increments(self):
        r = RetryRecord(task_id="t1")
        r.record_attempt("err1")
        assert r.attempts == 1
        assert r.first_failure_at is not None
        assert r.last_error == "err1"

    def test_record_keeps_last_10_errors(self):
        r = RetryRecord(task_id="t1")
        for i in range(15):
            r.record_attempt(f"error-{i}")
        assert len(r.errors) == 10
        assert r.errors[0] == "error-5"  # Oldest kept
        assert r.errors[-1] == "error-14"  # Most recent

    def test_first_failure_set_once(self):
        r = RetryRecord(task_id="t1")
        r.record_attempt("first")
        first_time = r.first_failure_at
        r.record_attempt("second")
        assert r.first_failure_at == first_time  # Should not change


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_same_task_multiple_policies(self):
        """Two policies tracking the same task ID independently."""
        p1 = RetryPolicy(max_retries=3, jitter_factor=0.0)
        p2 = RetryPolicy(max_retries=5, jitter_factor=0.0)

        p1.should_retry("t1", error="fail")
        d2 = p2.should_retry("t1", error="fail")

        # Each policy has its own state
        assert p1.get_retry_record("t1")["attempts"] == 1
        assert p2.get_retry_record("t1")["attempts"] == 1

    def test_many_concurrent_tasks(self, policy):
        """Many tasks tracked simultaneously."""
        for i in range(100):
            policy.should_retry(f"concurrent-{i}", error="fail")

        stats = policy.get_stats()
        assert stats["active_retries"] == 100

    def test_retry_then_clear_then_retry(self, policy):
        """Clearing a record should allow fresh retries."""
        for _ in range(3):
            policy.should_retry("t1", error="fail")
        assert policy.get_retry_record("t1")["attempts"] == 3

        policy.clear_record("t1")
        decision = policy.should_retry("t1", error="fresh fail")
        assert decision.retry is True
        assert decision.attempt == 1

    def test_empty_error_string(self, policy):
        decision = policy.should_retry("t1", error="")
        assert decision.retry is True

    def test_very_long_error_string(self, policy):
        long_error = "x" * 10000
        decision = policy.should_retry("t1", error=long_error)
        assert decision.retry is True
        assert policy.get_retry_record("t1")["last_error"] == long_error
