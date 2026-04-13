"""
Tests for DecisionSynthesizer
==============================

Covers: signal registration, composite scoring, ranking, outcome
determination, confidence levels, explanations, audit trail,
weight management, candidate comparison, and what-if analysis.
"""

import pytest

from mcp_server.swarm.decision_synthesizer import (
    DecisionSynthesizer,
    SignalType,
    SignalValue,
    SignalVector,
    DecisionOutcome,
    ConfidenceLevel,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def synth():
    """Basic synthesizer with no signals registered."""
    return DecisionSynthesizer()


@pytest.fixture
def task():
    """Sample task for testing."""
    return {
        "id": "task_001",
        "title": "Verify storefront in downtown",
        "category": "physical_verification",
        "bounty_usd": 5.0,
    }


@pytest.fixture
def candidates():
    """Three sample candidates."""
    return [
        {"id": "agent_1", "wallet": "0xAAA", "skills": ["photography", "field_work"]},
        {"id": "agent_2", "wallet": "0xBBB", "skills": ["data_entry", "research"]},
        {
            "id": "agent_3",
            "wallet": "0xCCC",
            "skills": ["photography", "geo_verification"],
        },
    ]


def make_scorer(score_map: dict):
    """Create a scorer function from a score map {candidate_id: score}."""

    def scorer(task, candidate):
        cid = str(candidate.get("id", candidate.get("agent_id", "")))
        return score_map.get(cid, 50.0)

    return scorer


@pytest.fixture
def loaded_synth():
    """Synthesizer with multiple signals registered."""
    s = DecisionSynthesizer()
    s.register_signal(
        SignalType.SKILL_MATCH,
        make_scorer({"agent_1": 90, "agent_2": 40, "agent_3": 85}),
        weight=0.30,
        description="Skill matching",
    )
    s.register_signal(
        SignalType.REPUTATION,
        make_scorer({"agent_1": 70, "agent_2": 80, "agent_3": 60}),
        weight=0.20,
        description="Reputation scoring",
    )
    s.register_signal(
        SignalType.AVAILABILITY,
        make_scorer({"agent_1": 95, "agent_2": 30, "agent_3": 75}),
        weight=0.10,
        description="Availability prediction",
    )
    s.register_signal(
        SignalType.RELIABILITY,
        make_scorer({"agent_1": 85, "agent_2": 90, "agent_3": 70}),
        weight=0.15,
        description="Reliability scoring",
    )
    s.register_signal(
        SignalType.SPEED,
        make_scorer({"agent_1": 60, "agent_2": 50, "agent_3": 80}),
        weight=0.08,
        description="Response speed",
    )
    return s


# ── Basic Synthesis ───────────────────────────────────────────


class TestBasicSynthesis:
    def test_empty_candidates_returns_held(self, synth, task):
        decision = synth.synthesize(task, [])
        assert decision.outcome == DecisionOutcome.HELD
        assert decision.best_candidate is None

    def test_no_signals_returns_held(self, synth, task, candidates):
        decision = synth.synthesize(task, candidates)
        assert decision.outcome == DecisionOutcome.HELD

    def test_single_signal_routes(self, synth, task, candidates):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            make_scorer({"agent_1": 80, "agent_2": 40, "agent_3": 60}),
        )
        decision = synth.synthesize(task, candidates)
        assert decision.outcome == DecisionOutcome.ROUTED
        assert decision.best_candidate == "agent_1"

    def test_multi_signal_routes(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert decision.outcome == DecisionOutcome.ROUTED
        assert decision.best_candidate == "agent_1"
        assert decision.best_score > 0

    def test_decision_has_rankings(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert len(decision.rankings) == 3
        assert decision.rankings[0].rank == 1
        assert decision.rankings[1].rank == 2
        assert decision.rankings[2].rank == 3

    def test_rankings_sorted_descending(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        scores = [r.composite_score for r in decision.rankings]
        assert scores == sorted(scores, reverse=True)


# ── Signal Registration ───────────────────────────────────────


class TestSignalRegistration:
    def test_register_signal(self, synth):
        synth.register_signal(
            SignalType.REPUTATION,
            lambda t, c: 50.0,
            description="Test",
        )
        assert "reputation" in synth.registered_signals

    def test_unregister_signal(self, synth):
        synth.register_signal(SignalType.SPEED, lambda t, c: 50.0)
        assert "speed" in synth.registered_signals
        synth.unregister_signal(SignalType.SPEED)
        assert "speed" not in synth.registered_signals

    def test_multiple_signals(self, loaded_synth):
        signals = loaded_synth.registered_signals
        assert len(signals) == 5
        assert "skill_match" in signals
        assert "reputation" in signals

    def test_register_override_weight(self, synth):
        synth.register_signal(
            SignalType.COST,
            lambda t, c: 50.0,
            weight=0.99,
        )
        # Verify through synthesis
        decision = synth.synthesize(
            {"id": "t1"},
            [{"id": "a1"}],
        )
        assert decision.outcome == DecisionOutcome.ROUTED


# ── Composite Scoring ─────────────────────────────────────────


class TestCompositeScoring:
    def test_perfect_scores(self, synth, task):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 100.0,
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert decision.best_score > 0.9

    def test_zero_scores(self, synth, task):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 0.0,
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert decision.best_score < 0.01

    def test_mixed_signals_average(self, synth, task):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 100.0,
            weight=0.5,
        )
        synth.register_signal(
            SignalType.REPUTATION,
            lambda t, c: 0.0,
            weight=0.5,
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        # Should be roughly 0.5 (weighted average)
        assert 0.3 < decision.best_score < 0.7

    def test_weight_affects_score(self, synth, task):
        # High weight on skill_match
        synth.register_signal(
            SignalType.SKILL_MATCH,
            make_scorer({"a1": 90, "a2": 30}),
            weight=0.9,
        )
        synth.register_signal(
            SignalType.REPUTATION,
            make_scorer({"a1": 30, "a2": 90}),
            weight=0.1,
        )
        decision = synth.synthesize(task, [{"id": "a1"}, {"id": "a2"}])
        assert decision.best_candidate == "a1"

    def test_signal_values_normalized(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        for vec in decision.rankings:
            for sig in vec.signals:
                assert 0.0 <= sig.normalized <= 1.0


# ── Outcome Determination ─────────────────────────────────────


class TestOutcomeDetermination:
    def test_below_threshold_held(self, synth, task):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 1.0,  # Very low score
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert decision.outcome == DecisionOutcome.HELD

    def test_above_threshold_routed(self, synth, task):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 80.0,
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert decision.outcome == DecisionOutcome.ROUTED

    def test_custom_threshold(self, task):
        synth = DecisionSynthesizer(min_threshold=0.9)
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 80.0,  # 0.8 normalized, below 0.9 threshold
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert decision.outcome == DecisionOutcome.HELD


# ── Confidence Levels ─────────────────────────────────────────


class TestConfidence:
    def test_single_signal_low_confidence(self, synth, task):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 80.0,
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert decision.confidence_level in (
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
        )

    def test_many_signals_higher_confidence(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert decision.confidence_level in (
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        )
        assert decision.confidence_score > 0.3

    def test_confidence_score_in_range(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert 0.0 <= decision.confidence_score <= 1.0


# ── Explanations ──────────────────────────────────────────────


class TestExplanations:
    def test_has_explanation(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert decision.explanation
        assert len(decision.explanation) > 20

    def test_explanation_mentions_candidates(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert (
            "agent_1" in decision.explanation
            or "candidate" in decision.explanation.lower()
        )

    def test_held_explanation(self, synth, task):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 1.0,
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert (
            "held" in decision.explanation.lower()
            or "threshold" in decision.explanation.lower()
        )


# ── Signal Vector ─────────────────────────────────────────────


class TestSignalVector:
    def test_signal_count(self):
        vec = SignalVector(
            candidate_id="a1",
            signals=[
                SignalValue(SignalType.SKILL_MATCH, 80.0, 0.8, 0.3, 0.9),
                SignalValue(SignalType.REPUTATION, 70.0, 0.7, 0.2, 0.8),
            ],
        )
        assert vec.signal_count == 2

    def test_total_confidence(self):
        vec = SignalVector(
            candidate_id="a1",
            signals=[
                SignalValue(SignalType.SKILL_MATCH, 80.0, 0.8, 0.3, 0.9),
                SignalValue(SignalType.REPUTATION, 70.0, 0.7, 0.2, 0.7),
            ],
        )
        assert abs(vec.total_confidence - 0.8) < 0.01

    def test_signal_by_type(self):
        vec = SignalVector(
            candidate_id="a1",
            signals=[
                SignalValue(SignalType.SKILL_MATCH, 80.0, 0.8),
                SignalValue(SignalType.REPUTATION, 70.0, 0.7),
            ],
        )
        sig = vec.signal_by_type(SignalType.SKILL_MATCH)
        assert sig is not None
        assert sig.raw_value == 80.0

    def test_signal_by_type_missing(self):
        vec = SignalVector(candidate_id="a1", signals=[])
        assert vec.signal_by_type(SignalType.COST) is None

    def test_to_dict(self):
        vec = SignalVector(
            candidate_id="a1",
            wallet="0xAAA",
            signals=[
                SignalValue(SignalType.SKILL_MATCH, 80.0, 0.8, 0.3, 0.9),
            ],
            composite_score=0.72,
            rank=1,
        )
        d = vec.to_dict()
        assert d["candidate_id"] == "a1"
        assert "skill_match" in d["signals"]
        assert d["composite_score"] == 0.72


# ── Weighted Score ────────────────────────────────────────────


class TestWeightedScore:
    def test_signal_value_weighted_score(self):
        sv = SignalValue(
            signal_type=SignalType.SKILL_MATCH,
            raw_value=80.0,
            normalized=0.8,
            weight=0.3,
            confidence=0.9,
        )
        expected = 0.8 * 0.3 * 0.9
        assert abs(sv.weighted_score - expected) < 0.001

    def test_zero_weight_zero_contribution(self):
        sv = SignalValue(
            signal_type=SignalType.COST,
            raw_value=100.0,
            normalized=1.0,
            weight=0.0,
            confidence=1.0,
        )
        assert sv.weighted_score == 0.0

    def test_zero_confidence_zero_contribution(self):
        sv = SignalValue(
            signal_type=SignalType.COST,
            raw_value=100.0,
            normalized=1.0,
            weight=0.5,
            confidence=0.0,
        )
        assert sv.weighted_score == 0.0


# ── Audit Trail ───────────────────────────────────────────────


class TestAuditTrail:
    def test_logs_decisions(self, loaded_synth, task, candidates):
        loaded_synth.synthesize(task, candidates)
        assert len(loaded_synth.decision_history) == 1

    def test_log_accumulates(self, loaded_synth, task, candidates):
        loaded_synth.synthesize(task, candidates)
        loaded_synth.synthesize(task, candidates)
        loaded_synth.synthesize(task, candidates)
        assert len(loaded_synth.decision_history) == 3

    def test_log_entry_has_fields(self, loaded_synth, task, candidates):
        loaded_synth.synthesize(task, candidates)
        entry = loaded_synth.decision_history[0]
        assert "task_id" in entry
        assert "outcome" in entry
        assert "best" in entry
        assert "ts" in entry

    def test_stats(self, loaded_synth, task, candidates):
        loaded_synth.synthesize(task, candidates)
        loaded_synth.synthesize(task, candidates)
        stats = loaded_synth.stats
        assert stats["total_decisions"] == 2
        assert stats["providers_registered"] == 5
        assert "outcomes" in stats

    def test_stats_empty(self, synth):
        stats = synth.stats
        assert stats["total_decisions"] == 0


# ── Weight Management ─────────────────────────────────────────


class TestWeightManagement:
    def test_get_weights(self, synth):
        weights = synth.get_weights()
        assert "skill_match" in weights
        assert "reputation" in weights

    def test_update_weights(self, synth):
        synth.update_weights({SignalType.SKILL_MATCH: 0.99})
        weights = synth.get_weights()
        assert weights["skill_match"] == 0.99

    def test_updated_weights_affect_scoring(self, task):
        s = DecisionSynthesizer()
        s.register_signal(
            SignalType.SKILL_MATCH,
            make_scorer({"a1": 90, "a2": 30}),
        )
        s.register_signal(
            SignalType.REPUTATION,
            make_scorer({"a1": 30, "a2": 90}),
        )

        # Default: skill_match has higher weight
        s.synthesize(task, [{"id": "a1"}, {"id": "a2"}])

        # Flip weights
        s.update_weights(
            {
                SignalType.SKILL_MATCH: 0.01,
                SignalType.REPUTATION: 0.99,
            }
        )
        d2 = s.synthesize(task, [{"id": "a1"}, {"id": "a2"}])

        # With reputation weighted heavily, a2 should win
        assert d2.best_candidate == "a2"


# ── Candidate Comparison ──────────────────────────────────────


class TestCandidateComparison:
    def test_compare_returns_winner(self, loaded_synth, task):
        a = {"id": "agent_1", "wallet": "0xAAA"}
        b = {"id": "agent_2", "wallet": "0xBBB"}
        result = loaded_synth.compare_candidates(task, a, b)
        assert "winner" in result
        assert "loser" in result
        assert result["winner"] != result["loser"]

    def test_compare_has_signal_breakdown(self, loaded_synth, task):
        a = {"id": "agent_1", "wallet": "0xAAA"}
        b = {"id": "agent_2", "wallet": "0xBBB"}
        result = loaded_synth.compare_candidates(task, a, b)
        assert "signal_comparison" in result
        assert len(result["signal_comparison"]) > 0

    def test_compare_shows_advantages(self, loaded_synth, task):
        a = {"id": "agent_1", "wallet": "0xAAA"}
        b = {"id": "agent_2", "wallet": "0xBBB"}
        result = loaded_synth.compare_candidates(task, a, b)
        for signal, data in result["signal_comparison"].items():
            assert "advantage" in data
            assert data["advantage"] in ("agent_1", "agent_2", "tie")


# ── What-If Analysis ─────────────────────────────────────────


class TestWhatIf:
    def test_what_if_returns_comparison(self, loaded_synth, task, candidates):
        result = loaded_synth.what_if(
            task,
            candidates,
            {SignalType.SKILL_MATCH: 0.01, SignalType.REPUTATION: 0.99},
        )
        assert "current_best" in result
        assert "modified_best" in result
        assert "ranking_changed" in result

    def test_what_if_can_change_ranking(self, task):
        s = DecisionSynthesizer()
        s.register_signal(
            SignalType.SKILL_MATCH,
            make_scorer({"a1": 90, "a2": 30}),
            weight=0.9,
        )
        s.register_signal(
            SignalType.REPUTATION,
            make_scorer({"a1": 30, "a2": 90}),
            weight=0.1,
        )
        result = s.what_if(
            task,
            [{"id": "a1"}, {"id": "a2"}],
            {SignalType.SKILL_MATCH: 0.1, SignalType.REPUTATION: 0.9},
        )
        assert result["current_best"] == "a1"
        assert result["modified_best"] == "a2"
        assert result["ranking_changed"] is True


# ── Quick Synthesis ───────────────────────────────────────────


class TestQuickSynthesis:
    def test_quick_returns_id(self, loaded_synth, task, candidates):
        result = loaded_synth.synthesize_quick(task, candidates)
        assert result is not None
        assert result == "agent_1"

    def test_quick_returns_none_when_held(self, synth, task):
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 1.0,  # Below threshold
        )
        result = synth.synthesize_quick(task, [{"id": "a1"}])
        assert result is None


# ── Serialization ─────────────────────────────────────────────


class TestSerialization:
    def test_decision_to_dict(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        d = decision.to_dict()
        assert d["task_id"] == "task_001"
        assert d["outcome"] == "routed"
        assert "confidence" in d
        assert "top_candidates" in d
        assert len(d["top_candidates"]) <= 5

    def test_decision_dict_json_serializable(self, loaded_synth, task, candidates):
        import json

        decision = loaded_synth.synthesize(task, candidates)
        d = decision.to_dict()
        serialized = json.dumps(d)
        parsed = json.loads(serialized)
        assert parsed["task_id"] == "task_001"


# ── Degradation Tolerance ────────────────────────────────────


class TestDegradation:
    def test_failing_signal_skipped(self, synth, task):
        """Signal that throws an exception should be skipped."""

        def bad_scorer(t, c):
            raise ValueError("Signal source unavailable")

        synth.register_signal(
            SignalType.REPUTATION,
            bad_scorer,
        )
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 80.0,
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        # Should still route based on the working signal
        assert decision.outcome == DecisionOutcome.ROUTED
        assert "skill_match" in decision.signal_types_used
        assert "reputation" not in decision.signal_types_used

    def test_none_signal_skipped(self, synth, task):
        """Signal returning None should be skipped."""
        synth.register_signal(
            SignalType.SPEED,
            lambda t, c: None,
        )
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 80.0,
        )
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert "speed" not in decision.signal_types_used

    def test_all_signals_fail_gracefully(self, synth, task):
        """If all signals fail, should return HELD, not crash."""

        def bad_scorer(t, c):
            raise RuntimeError("everything is broken")

        synth.register_signal(SignalType.SKILL_MATCH, bad_scorer)
        synth.register_signal(SignalType.REPUTATION, bad_scorer)
        decision = synth.synthesize(task, [{"id": "a1"}])
        assert decision.outcome == DecisionOutcome.HELD


# ── Performance ───────────────────────────────────────────────


class TestPerformance:
    def test_decision_time_tracked(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert decision.decision_time_ms >= 0
        assert decision.decision_time_ms < 1000  # Should be fast

    def test_timestamp_set(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert decision.timestamp
        assert "T" in decision.timestamp  # ISO format


# ── Top-N Property ────────────────────────────────────────────


class TestTopN:
    def test_top_n_returns_3(self, loaded_synth, task, candidates):
        decision = loaded_synth.synthesize(task, candidates)
        assert len(decision.top_n) == 3

    def test_top_n_with_fewer_candidates(self, loaded_synth, task):
        decision = loaded_synth.synthesize(task, [{"id": "a1"}, {"id": "a2"}])
        assert len(decision.top_n) == 2
