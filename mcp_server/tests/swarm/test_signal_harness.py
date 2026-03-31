"""
Tests for SignalHarness — Signal bootstrap and telemetry layer
===============================================================

Covers: connection, disconnection, instrumented scoring,
telemetry (call count, errors, latency), diagnostics,
health summary, graceful degradation, and custom signals.
"""

import pytest

from mcp_server.swarm.signal_harness import SignalHarness
from mcp_server.swarm.decision_synthesizer import (
    SignalType,
    DecisionOutcome,
    DEFAULT_WEIGHTS,
)
from mcp_server.swarm.verification_adapter import VerificationAdapter


# ── Mock Sources ──────────────────────────────────────────────


class MockReputationBridge:
    """Mock ReputationBridge with configurable scores."""

    def __init__(self, scores=None):
        self._scores = scores or {}

    def get_composite_score(self, wallet: str) -> float:
        return self._scores.get(wallet, 0.5)


class MockAvailabilityBridge:
    """Mock AvailabilityBridge."""

    def __init__(self, probs=None):
        self._probs = probs or {}

    def predict_availability(self, agent_id: str) -> float:
        return self._probs.get(agent_id, 0.5)


class MockSkillMatcher:
    """Mock skill matching."""

    def __init__(self, scores=None):
        self._scores = scores or {}

    def match_score(self, task: dict, candidate: dict) -> float:
        cid = candidate.get("id", "")
        return self._scores.get(cid, 0.5)


class MockReliabilitySource:
    def get_reliability_score(self, agent_id: str) -> float:
        return 75.0


class MockSpeedSource:
    def get_speed_score(self, agent_id: str) -> float:
        return 80.0


class BrokenSource:
    """A source that always raises."""

    def score(self, *args, **kwargs):
        raise RuntimeError("Source unavailable")

    def get_composite_score(self, wallet):
        raise RuntimeError("Source unavailable")


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def harness():
    return SignalHarness()


@pytest.fixture
def task():
    return {"id": "t1", "category": "physical_verification", "bounty_usd": 5.0}


@pytest.fixture
def candidates():
    return [
        {"id": "agent_1", "wallet": "0xAAA", "skills": ["photography"]},
        {"id": "agent_2", "wallet": "0xBBB", "skills": ["research"]},
        {"id": "agent_3", "wallet": "0xCCC", "skills": ["photography", "geo"]},
    ]


# ── 1. Connection Tests ──────────────────────────────────────


class TestConnection:
    """Signal connection and registration."""

    def test_connect_reputation(self, harness):
        bridge = MockReputationBridge()
        result = harness.connect_reputation(bridge)
        assert result is harness  # Fluent API
        assert harness.connected_count == 1
        assert SignalType.REPUTATION in harness._connections

    def test_connect_availability(self, harness):
        bridge = MockAvailabilityBridge()
        harness.connect_availability(bridge)
        assert SignalType.AVAILABILITY in harness._connections

    def test_connect_verification(self, harness):
        adapter = VerificationAdapter()
        harness.connect_verification(adapter)
        assert SignalType.VERIFICATION_QUALITY in harness._connections

    def test_connect_skill_match(self, harness):
        matcher = MockSkillMatcher()
        harness.connect_skill_match(matcher)
        assert SignalType.SKILL_MATCH in harness._connections

    def test_connect_reliability(self, harness):
        source = MockReliabilitySource()
        harness.connect_reliability(source)
        assert SignalType.RELIABILITY in harness._connections

    def test_connect_speed(self, harness):
        source = MockSpeedSource()
        harness.connect_speed(source)
        assert SignalType.SPEED in harness._connections

    def test_connect_custom(self, harness):
        harness.connect_custom(
            SignalType.CAPACITY,
            "CustomCapacity",
            lambda t, c: 60.0,
        )
        assert SignalType.CAPACITY in harness._connections
        assert harness._connections[SignalType.CAPACITY].source_name == "CustomCapacity"

    def test_connect_multiple(self, harness):
        harness.connect_reputation(MockReputationBridge())
        harness.connect_availability(MockAvailabilityBridge())
        harness.connect_verification(VerificationAdapter())
        assert harness.connected_count == 3

    def test_fluent_chaining(self, harness):
        result = (
            harness.connect_reputation(MockReputationBridge())
            .connect_availability(MockAvailabilityBridge())
            .connect_verification(VerificationAdapter())
        )
        assert result is harness
        assert harness.connected_count == 3

    def test_signals_registered_in_synthesizer(self, harness):
        harness.connect_reputation(MockReputationBridge())
        assert SignalType.REPUTATION in harness.synthesizer._providers


# ── 2. Disconnection Tests ───────────────────────────────────


class TestDisconnection:
    """Signal disconnection."""

    def test_disconnect_existing(self, harness):
        harness.connect_reputation(MockReputationBridge())
        assert harness.disconnect(SignalType.REPUTATION)
        assert harness.connected_count == 0

    def test_disconnect_nonexistent(self, harness):
        assert not harness.disconnect(SignalType.REPUTATION)

    def test_disconnect_all(self, harness):
        harness.connect_reputation(MockReputationBridge())
        harness.connect_availability(MockAvailabilityBridge())
        harness.connect_verification(VerificationAdapter())
        count = harness.disconnect_all()
        assert count == 3
        assert harness.connected_count == 0

    def test_disconnect_removes_from_synthesizer(self, harness):
        harness.connect_reputation(MockReputationBridge())
        harness.disconnect(SignalType.REPUTATION)
        assert SignalType.REPUTATION not in harness.synthesizer._providers


# ── 3. Scoring Through Harness ────────────────────────────────


class TestScoring:
    """Instrumented scoring flow."""

    def test_scores_flow_through_synthesizer(self, harness, task, candidates):
        harness.connect_reputation(
            MockReputationBridge({"0xAAA": 0.9, "0xBBB": 0.5, "0xCCC": 0.7})
        )

        decision = harness.synthesizer.synthesize(task, candidates)
        assert decision is not None
        assert len(decision.rankings) == 3
        # Agent_1 (0xAAA, score 0.9) should rank first
        assert decision.rankings[0].candidate_id == "agent_1"

    def test_multi_signal_scoring(self, harness, task, candidates):
        harness.connect_skill_match(
            MockSkillMatcher({"agent_1": 0.8, "agent_2": 0.3, "agent_3": 0.9})
        )
        harness.connect_reputation(
            MockReputationBridge({"0xAAA": 0.6, "0xBBB": 0.9, "0xCCC": 0.7})
        )

        decision = harness.synthesizer.synthesize(task, candidates)
        assert decision.outcome == DecisionOutcome.ROUTED
        # Agent_3 has high skill + decent rep, should rank well
        top_3_ids = [r.candidate_id for r in decision.rankings[:3]]
        assert "agent_3" in top_3_ids

    def test_verification_in_multi_signal(self, harness, task, candidates):
        adapter = VerificationAdapter(min_inferences_for_signal=1)
        # Give agent_3 great verification history
        for i in range(5):
            adapter.ingest_inference(
                "agent_3",
                {
                    "score": 0.95,
                    "decision": "approved",
                    "category": "physical_verification",
                    "has_exif": True,
                    "has_gps": True,
                    "photo_source": "camera",
                },
            )

        harness.connect_skill_match(
            MockSkillMatcher({"agent_1": 0.7, "agent_2": 0.7, "agent_3": 0.7})
        )
        harness.connect_verification(adapter)

        decision = harness.synthesizer.synthesize(task, candidates)
        # Agent_3 should be boosted by verification quality
        assert decision.rankings[0].candidate_id == "agent_3"


# ── 4. Telemetry ─────────────────────────────────────────────


class TestTelemetry:
    """Call counting, error tracking, latency measurement."""

    def test_call_count_increments(self, harness, task, candidates):
        harness.connect_reputation(MockReputationBridge())
        harness.synthesizer.synthesize(task, candidates)

        conn = harness._connections[SignalType.REPUTATION]
        assert conn.call_count == len(candidates)  # Called once per candidate

    def test_error_tracking(self, harness, task, candidates):
        """Broken sources track errors without crashing."""
        harness.connect_custom(
            SignalType.REPUTATION,
            "BrokenSource",
            lambda t, c: (_ for _ in ()).throw(RuntimeError("fail")),
        )

        # Actually, we need a function that raises, not a generator
        harness.disconnect(SignalType.REPUTATION)

        def broken_scorer(t, c):
            raise RuntimeError("Source down")

        harness.connect_custom(SignalType.REPUTATION, "BrokenSource", broken_scorer)

        # Should not crash
        decision = harness.synthesizer.synthesize(task, candidates)
        assert decision is not None

        conn = harness._connections[SignalType.REPUTATION]
        assert conn.error_count == len(candidates)
        assert "Source down" in conn.last_error

    def test_latency_tracking(self, harness, task, candidates):
        harness.connect_reputation(MockReputationBridge())
        harness.synthesizer.synthesize(task, candidates)

        conn = harness._connections[SignalType.REPUTATION]
        assert conn.avg_latency_ms >= 0  # Should be very small but positive

    def test_multiple_calls_average_latency(self, harness, task, candidates):
        harness.connect_reputation(MockReputationBridge())
        # Synthesize twice
        harness.synthesizer.synthesize(task, candidates)
        harness.synthesizer.synthesize(task, candidates)

        conn = harness._connections[SignalType.REPUTATION]
        assert conn.call_count == len(candidates) * 2
        assert conn.avg_latency_ms >= 0


# ── 5. Diagnostics ────────────────────────────────────────────


class TestDiagnostics:
    """Status and health reporting."""

    def test_status_empty(self, harness):
        status = harness.status()
        assert status["connected"] == 0
        assert status["available"] > 0
        assert status["total_calls"] == 0

    def test_status_with_signals(self, harness, task, candidates):
        harness.connect_reputation(MockReputationBridge())
        harness.connect_verification(VerificationAdapter())
        harness.synthesizer.synthesize(task, candidates)

        status = harness.status()
        assert status["connected"] == 2
        assert "reputation" in status["signals"]
        assert "verification_quality" in status["signals"]
        assert status["total_calls"] > 0

    def test_status_includes_weight(self, harness):
        harness.connect_reputation(MockReputationBridge())
        status = harness.status()
        rep_signal = status["signals"]["reputation"]
        assert rep_signal["weight"] == DEFAULT_WEIGHTS[SignalType.REPUTATION]

    def test_health_summary_all_healthy(self, harness, task, candidates):
        harness.connect_reputation(MockReputationBridge())
        harness.synthesizer.synthesize(task, candidates)

        health = harness.health_summary()
        assert health["healthy"]
        assert health["connected"] == 1
        assert health["degraded_signals"] == 0

    def test_health_summary_with_errors(self, harness, task, candidates):
        def broken(t, c):
            raise RuntimeError("fail")

        harness.connect_custom(SignalType.REPUTATION, "Broken", broken)
        harness.synthesizer.synthesize(task, candidates)

        health = harness.health_summary()
        assert not health["healthy"]
        assert health["degraded_signals"] == 1

    def test_get_signal_stats(self, harness, task, candidates):
        harness.connect_reputation(MockReputationBridge())
        harness.synthesizer.synthesize(task, candidates)

        stats = harness.get_signal_stats(SignalType.REPUTATION)
        assert stats is not None
        assert stats["calls"] == len(candidates)
        assert stats["source"] == "ReputationBridge"

    def test_get_signal_stats_nonexistent(self, harness):
        assert harness.get_signal_stats(SignalType.REPUTATION) is None

    def test_connected_count_property(self, harness):
        assert harness.connected_count == 0
        harness.connect_reputation(MockReputationBridge())
        assert harness.connected_count == 1

    def test_total_available_property(self, harness):
        # Should be at least 13 (all signal types)
        assert harness.total_available >= 13

    def test_coverage_metric(self, harness):
        harness.connect_reputation(MockReputationBridge())
        status = harness.status()
        assert 0 < status["coverage"] < 1.0

    def test_uptime_tracking(self, harness):
        status = harness.status()
        assert status["uptime_seconds"] >= 0


# ── 6. Graceful Degradation ──────────────────────────────────


class TestGracefulDegradation:
    """System continues to function with broken/missing signals."""

    def test_broken_signal_doesnt_crash(self, harness, task, candidates):
        def broken(t, c):
            raise RuntimeError("network error")

        harness.connect_custom(SignalType.REPUTATION, "BrokenNet", broken)
        harness.connect_custom(
            SignalType.SKILL_MATCH, "WorkingSkill", lambda t, c: 70.0
        )

        decision = harness.synthesizer.synthesize(task, candidates)
        assert decision is not None
        assert decision.outcome == DecisionOutcome.ROUTED

    def test_all_signals_broken_still_decides(self, harness, task, candidates):
        def broken(t, c):
            raise RuntimeError("all down")

        harness.connect_custom(SignalType.REPUTATION, "Down1", broken)
        harness.connect_custom(SignalType.SKILL_MATCH, "Down2", broken)

        # Even with all signals failing, synthesizer should produce a result
        decision = harness.synthesizer.synthesize(task, candidates)
        assert decision is not None

    def test_intermittent_failures(self, harness, task, candidates):
        call_count = {"n": 0}

        def flaky(t, c):
            call_count["n"] += 1
            if call_count["n"] % 2 == 0:
                raise RuntimeError("flaky")
            return 70.0

        harness.connect_custom(SignalType.SKILL_MATCH, "Flaky", flaky)
        decision = harness.synthesizer.synthesize(task, candidates)
        assert decision is not None

        conn = harness._connections[SignalType.SKILL_MATCH]
        assert conn.call_count == len(candidates)
        assert conn.error_count > 0


# ── 7. Custom Signal ─────────────────────────────────────────


class TestCustomSignal:
    """Custom signal registration and use."""

    def test_custom_signal_affects_routing(self, harness, task, candidates):
        # Custom signal: agent_2 is the best
        scores = {"agent_1": 30.0, "agent_2": 95.0, "agent_3": 50.0}
        harness.connect_custom(
            SignalType.SPECIALIZATION,
            "CustomSpec",
            lambda t, c: scores.get(c.get("id", ""), 50.0),
        )

        decision = harness.synthesizer.synthesize(task, candidates)
        assert decision.rankings[0].candidate_id == "agent_2"

    def test_custom_signal_appears_in_status(self, harness):
        harness.connect_custom(
            SignalType.CAPACITY,
            "MyCapacityTracker",
            lambda t, c: 60.0,
        )

        status = harness.status()
        assert "capacity" in status["signals"]
        assert status["signals"]["capacity"]["source"] == "MyCapacityTracker"


# ── 8. Integration with VerificationAdapter ───────────────────


class TestVerificationIntegration:
    """Full VerificationAdapter integration through harness."""

    def test_verification_scores_flow(self, harness, task, candidates):
        adapter = VerificationAdapter(min_inferences_for_signal=2)

        # Agent_3 has excellent verification history
        for i in range(5):
            adapter.ingest_inference(
                "agent_3",
                {
                    "score": 0.95,
                    "decision": "approved",
                    "category": "physical_verification",
                    "has_exif": True,
                    "has_gps": True,
                    "photo_source": "camera",
                },
            )

        harness.connect_verification(adapter)

        # With only verification signal, agent_3 should rank first
        decision = harness.synthesizer.synthesize(task, candidates)
        assert decision.rankings[0].candidate_id == "agent_3"

    def test_verification_telemetry(self, harness, task, candidates):
        adapter = VerificationAdapter()
        harness.connect_verification(adapter)
        harness.synthesizer.synthesize(task, candidates)

        stats = harness.get_signal_stats(SignalType.VERIFICATION_QUALITY)
        assert stats["calls"] == len(candidates)
        assert stats["source"] == "VerificationAdapter"
        assert stats["errors"] == 0
