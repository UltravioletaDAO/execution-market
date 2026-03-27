"""
Tests for DecisionSynthesizer — Unified Multi-Signal Routing Decisions
=======================================================================

Validates that the decision engine correctly:
- Aggregates signals from multiple providers
- Ranks candidates by composite score
- Determines appropriate outcomes
- Handles graceful degradation
- Produces explainable decisions
"""

import pytest

from mcp_server.swarm.decision_synthesizer import (
    DecisionSynthesizer,
    SignalType,
    SignalValue,
    SignalVector,
    RankedDecision,
    DecisionOutcome,
    ConfidenceLevel,
    DEFAULT_WEIGHTS,
    MINIMUM_ROUTE_THRESHOLD,
    HIGH_CONFIDENCE_SIGNALS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_task(
    task_id="t1", category="physical_verification", title="Verify store", bounty=5.0
):
    return {
        "id": task_id,
        "category": category,
        "title": title,
        "bounty_usd": bounty,
    }


def make_candidate(cid="c1", wallet="0xABC", skills=None):
    return {
        "id": cid,
        "wallet": wallet,
        "skills": skills or ["photography", "field_work"],
    }


def constant_scorer(value):
    """Returns a scorer that always returns `value`."""

    def scorer(task, candidate):
        return value

    return scorer


def candidate_based_scorer(scores_map):
    """Returns a scorer that returns different scores per candidate."""

    def scorer(task, candidate):
        cid = candidate.get("id", "")
        return scores_map.get(cid, 50)

    return scorer


@pytest.fixture
def synth():
    return DecisionSynthesizer()


@pytest.fixture
def synth_with_signals():
    s = DecisionSynthesizer()
    s.register_signal(
        SignalType.SKILL_MATCH,
        candidate_based_scorer({"c1": 90, "c2": 60, "c3": 40}),
        description="Skill matching",
    )
    s.register_signal(
        SignalType.REPUTATION,
        candidate_based_scorer({"c1": 80, "c2": 85, "c3": 70}),
        description="On-chain reputation",
    )
    s.register_signal(
        SignalType.RELIABILITY,
        candidate_based_scorer({"c1": 95, "c2": 75, "c3": 50}),
        description="Completion reliability",
    )
    return s


# ---------------------------------------------------------------------------
# SignalValue Tests
# ---------------------------------------------------------------------------


class TestSignalValue:
    def test_weighted_score(self):
        sv = SignalValue(
            signal_type=SignalType.REPUTATION,
            raw_value=80,
            normalized=0.8,
            weight=0.2,
            confidence=0.9,
        )
        assert sv.weighted_score == pytest.approx(0.8 * 0.2 * 0.9, abs=0.001)

    def test_zero_confidence(self):
        sv = SignalValue(
            signal_type=SignalType.SKILL_MATCH,
            raw_value=100,
            normalized=1.0,
            weight=0.3,
            confidence=0.0,
        )
        assert sv.weighted_score == 0.0

    def test_zero_weight(self):
        sv = SignalValue(
            signal_type=SignalType.COST,
            raw_value=50,
            normalized=0.5,
            weight=0.0,
            confidence=1.0,
        )
        assert sv.weighted_score == 0.0


# ---------------------------------------------------------------------------
# SignalVector Tests
# ---------------------------------------------------------------------------


class TestSignalVector:
    def test_empty_vector(self):
        v = SignalVector(candidate_id="c1")
        assert v.signal_count == 0
        assert v.total_confidence == 0.0

    def test_signal_count(self):
        v = SignalVector(
            candidate_id="c1",
            signals=[
                SignalValue(SignalType.REPUTATION, 80, 0.8, 0.2, 0.9),
                SignalValue(SignalType.SKILL_MATCH, 90, 0.9, 0.3, 0.85),
            ],
        )
        assert v.signal_count == 2

    def test_total_confidence(self):
        v = SignalVector(
            candidate_id="c1",
            signals=[
                SignalValue(SignalType.REPUTATION, 80, 0.8, 0.2, 0.9),
                SignalValue(SignalType.SKILL_MATCH, 90, 0.9, 0.3, 0.7),
            ],
        )
        assert v.total_confidence == pytest.approx(0.8, abs=0.01)

    def test_signal_by_type(self):
        rep = SignalValue(SignalType.REPUTATION, 80, 0.8, 0.2, 0.9)
        skill = SignalValue(SignalType.SKILL_MATCH, 90, 0.9, 0.3, 0.85)
        v = SignalVector(candidate_id="c1", signals=[rep, skill])
        assert v.signal_by_type(SignalType.REPUTATION) is rep
        assert v.signal_by_type(SignalType.COST) is None

    def test_to_dict(self):
        v = SignalVector(
            candidate_id="c1",
            wallet="0xABC",
            composite_score=0.75,
            rank=1,
            signals=[
                SignalValue(SignalType.REPUTATION, 80, 0.8, 0.2, 0.9),
            ],
        )
        d = v.to_dict()
        assert d["candidate_id"] == "c1"
        assert d["composite_score"] == 0.75
        assert "reputation" in d["signals"]


# ---------------------------------------------------------------------------
# RankedDecision Tests
# ---------------------------------------------------------------------------


class TestRankedDecision:
    def test_top_n_empty(self):
        d = RankedDecision(task_id="t1", outcome=DecisionOutcome.HELD)
        assert d.top_n == []

    def test_top_n(self):
        d = RankedDecision(
            task_id="t1",
            outcome=DecisionOutcome.ROUTED,
            rankings=[
                SignalVector(candidate_id="c1"),
                SignalVector(candidate_id="c2"),
                SignalVector(candidate_id="c3"),
                SignalVector(candidate_id="c4"),
            ],
        )
        assert d.top_n == ["c1", "c2", "c3"]

    def test_to_dict(self):
        d = RankedDecision(
            task_id="t1",
            outcome=DecisionOutcome.ROUTED,
            best_candidate="c1",
            best_score=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            confidence_score=0.9,
        )
        dd = d.to_dict()
        assert dd["task_id"] == "t1"
        assert dd["outcome"] == "routed"
        assert dd["confidence"]["level"] == "high"


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_signal(self, synth):
        synth.register_signal(
            SignalType.REPUTATION,
            constant_scorer(80),
            description="Test reputation",
        )
        assert "reputation" in synth.registered_signals

    def test_register_multiple(self, synth):
        synth.register_signal(SignalType.REPUTATION, constant_scorer(80))
        synth.register_signal(SignalType.SKILL_MATCH, constant_scorer(90))
        assert len(synth.registered_signals) == 2

    def test_unregister(self, synth):
        synth.register_signal(SignalType.REPUTATION, constant_scorer(80))
        synth.unregister_signal(SignalType.REPUTATION)
        assert "reputation" not in synth.registered_signals

    def test_custom_weight(self, synth):
        synth.register_signal(SignalType.REPUTATION, constant_scorer(80), weight=0.5)
        assert synth._providers[SignalType.REPUTATION].weight == 0.5

    def test_default_weight_from_config(self, synth):
        synth.register_signal(SignalType.REPUTATION, constant_scorer(80))
        expected = DEFAULT_WEIGHTS.get(SignalType.REPUTATION, 0.1)
        assert synth._providers[SignalType.REPUTATION].weight == expected


# ---------------------------------------------------------------------------
# Core Synthesis Tests
# ---------------------------------------------------------------------------


class TestSynthesize:
    def test_no_candidates(self, synth_with_signals):
        task = make_task()
        decision = synth_with_signals.synthesize(task, [])
        assert decision.outcome == DecisionOutcome.HELD
        assert "No candidates" in decision.explanation

    def test_single_candidate(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth_with_signals.synthesize(task, candidates)
        assert decision.best_candidate == "c1"
        assert decision.best_score > 0

    def test_ranking_order(self, synth_with_signals):
        task = make_task()
        candidates = [
            make_candidate("c1"),
            make_candidate("c2"),
            make_candidate("c3"),
        ]
        decision = synth_with_signals.synthesize(task, candidates)
        # c1 has highest skill (90) + high reputation (80) + high reliability (95)
        assert decision.rankings[0].candidate_id == "c1"
        assert decision.rankings[0].rank == 1
        assert decision.rankings[1].rank == 2
        assert decision.rankings[2].rank == 3

    def test_scores_decrease_in_order(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1"), make_candidate("c2"), make_candidate("c3")]
        decision = synth_with_signals.synthesize(task, candidates)
        scores = [r.composite_score for r in decision.rankings]
        assert scores == sorted(scores, reverse=True)

    def test_routed_outcome(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth_with_signals.synthesize(task, candidates)
        assert decision.outcome == DecisionOutcome.ROUTED

    def test_signal_types_used(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth_with_signals.synthesize(task, candidates)
        assert "skill_match" in decision.signal_types_used
        assert "reputation" in decision.signal_types_used
        assert "reliability" in decision.signal_types_used

    def test_decision_time_tracked(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth_with_signals.synthesize(task, candidates)
        assert decision.decision_time_ms >= 0

    def test_timestamp_present(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth_with_signals.synthesize(task, candidates)
        assert decision.timestamp != ""

    def test_synthesize_quick(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1")]
        result = synth_with_signals.synthesize_quick(task, candidates)
        assert result == "c1"

    def test_synthesize_quick_no_candidate(self, synth):
        task = make_task()
        result = synth.synthesize_quick(task, [make_candidate("c1")])
        # No signals registered → held → returns None
        assert result is None


# ---------------------------------------------------------------------------
# Normalization Tests
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_default_normalize_zero(self):
        assert DecisionSynthesizer._default_normalize(0) == 0.0

    def test_default_normalize_hundred(self):
        assert DecisionSynthesizer._default_normalize(100) == 1.0

    def test_default_normalize_fifty(self):
        assert DecisionSynthesizer._default_normalize(50) == 0.5

    def test_default_normalize_negative(self):
        assert DecisionSynthesizer._default_normalize(-10) == 0.0

    def test_default_normalize_over_hundred(self):
        assert DecisionSynthesizer._default_normalize(150) == 1.0


# ---------------------------------------------------------------------------
# Composite Score Tests
# ---------------------------------------------------------------------------


class TestCompositeScore:
    def test_single_signal(self, synth):
        signals = [
            SignalValue(
                signal_type=SignalType.REPUTATION,
                raw_value=80,
                normalized=0.8,
                weight=1.0,
                confidence=1.0,
            ),
        ]
        score = synth._compute_composite(signals)
        assert score == pytest.approx(0.8, abs=0.01)

    def test_empty_signals(self, synth):
        assert synth._compute_composite([]) == 0.0

    def test_weighted_average(self, synth):
        signals = [
            SignalValue(SignalType.REPUTATION, 100, 1.0, 0.5, 1.0),
            SignalValue(SignalType.SKILL_MATCH, 0, 0.0, 0.5, 1.0),
        ]
        score = synth._compute_composite(signals)
        # (1.0 * 0.5 * 1.0 + 0.0 * 0.5 * 1.0) / (0.5 + 0.5) = 0.5
        assert score == pytest.approx(0.5, abs=0.01)

    def test_confidence_weighting(self, synth):
        # High confidence high score + low confidence low score
        signals = [
            SignalValue(SignalType.REPUTATION, 80, 0.8, 0.5, 0.9),
            SignalValue(SignalType.SKILL_MATCH, 20, 0.2, 0.5, 0.1),
        ]
        score = synth._compute_composite(signals)
        # The high-confidence signal should dominate
        assert score > 0.5


# ---------------------------------------------------------------------------
# Outcome Determination Tests
# ---------------------------------------------------------------------------


class TestOutcomeDetermination:
    def test_held_when_below_threshold(self, synth):
        vectors = [
            SignalVector(candidate_id="c1", composite_score=0.01, signals=[]),
        ]
        outcome, level, score = synth._determine_outcome(vectors, set())
        assert outcome == DecisionOutcome.HELD

    def test_routed_when_above_threshold(self, synth):
        vectors = [
            SignalVector(
                candidate_id="c1",
                composite_score=0.5,
                signals=[
                    SignalValue(SignalType.REPUTATION, 80, 0.8, 0.2, 0.9),
                ],
            ),
        ]
        outcome, level, score = synth._determine_outcome(vectors, {"reputation"})
        assert outcome == DecisionOutcome.ROUTED

    def test_empty_vectors_held(self, synth):
        outcome, level, score = synth._determine_outcome([], set())
        assert outcome == DecisionOutcome.HELD
        assert level == ConfidenceLevel.GUESS

    def test_high_confidence_many_signals(self, synth):
        signals = [
            SignalValue(SignalType.REPUTATION, 80, 0.8, 0.2, 0.9),
            SignalValue(SignalType.SKILL_MATCH, 90, 0.9, 0.3, 0.85),
            SignalValue(SignalType.RELIABILITY, 85, 0.85, 0.15, 0.8),
            SignalValue(SignalType.AVAILABILITY, 70, 0.7, 0.1, 0.75),
            SignalValue(SignalType.SPEED, 60, 0.6, 0.08, 0.7),
        ]
        vectors = [
            SignalVector(candidate_id="c1", composite_score=0.8, signals=signals),
        ]
        used = {"reputation", "skill_match", "reliability", "availability", "speed"}
        outcome, level, score = synth._determine_outcome(vectors, used)
        assert level == ConfidenceLevel.HIGH

    def test_low_confidence_single_signal(self, synth):
        vectors = [
            SignalVector(
                candidate_id="c1",
                composite_score=0.5,
                signals=[
                    SignalValue(SignalType.REPUTATION, 80, 0.8, 0.2, 0.5),
                ],
            ),
        ]
        outcome, level, score = synth._determine_outcome(vectors, {"reputation"})
        assert level == ConfidenceLevel.LOW


# ---------------------------------------------------------------------------
# Explanation Builder Tests
# ---------------------------------------------------------------------------


class TestExplanation:
    def test_held_explanation(self, synth):
        vectors = [SignalVector(candidate_id="c1", composite_score=0.01)]
        explanation = synth._build_explanation(
            make_task(), vectors, DecisionOutcome.HELD, set()
        )
        assert "held" in explanation.lower() or "held" in explanation

    def test_routed_explanation_includes_best(self, synth):
        vectors = [
            SignalVector(
                candidate_id="c1",
                composite_score=0.85,
                signals=[
                    SignalValue(
                        SignalType.REPUTATION, 80, 0.8, 0.2, 0.9, detail="High rep"
                    ),
                ],
            ),
        ]
        explanation = synth._build_explanation(
            make_task(), vectors, DecisionOutcome.ROUTED, {"reputation"}
        )
        assert "c1" in explanation
        assert "0.85" in explanation

    def test_close_race_noted(self, synth):
        vectors = [
            SignalVector(candidate_id="c1", composite_score=0.80, signals=[]),
            SignalVector(candidate_id="c2", composite_score=0.79, signals=[]),
        ]
        explanation = synth._build_explanation(
            make_task(), vectors, DecisionOutcome.ROUTED, {"reputation"}
        )
        assert "close" in explanation.lower() or "race" in explanation.lower()

    def test_clear_winner_noted(self, synth):
        vectors = [
            SignalVector(candidate_id="c1", composite_score=0.85, signals=[]),
            SignalVector(candidate_id="c2", composite_score=0.50, signals=[]),
        ]
        explanation = synth._build_explanation(
            make_task(), vectors, DecisionOutcome.ROUTED, {"reputation"}
        )
        assert "clear" in explanation.lower() or "winner" in explanation.lower()


# ---------------------------------------------------------------------------
# Graceful Degradation Tests
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_failing_scorer(self, synth):
        """A failing signal scorer shouldn't crash the synthesis."""

        def failing_scorer(task, candidate):
            raise ValueError("Signal source unavailable")

        synth.register_signal(SignalType.REPUTATION, failing_scorer)
        synth.register_signal(SignalType.SKILL_MATCH, constant_scorer(80))

        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth.synthesize(task, candidates)
        # Should still work with the remaining signal
        assert decision.best_candidate == "c1"
        assert "skill_match" in decision.signal_types_used

    def test_none_return_scorer(self, synth):
        """A scorer returning None should be skipped gracefully."""

        def none_scorer(task, candidate):
            return None

        synth.register_signal(SignalType.REPUTATION, none_scorer)
        synth.register_signal(SignalType.SKILL_MATCH, constant_scorer(80))

        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth.synthesize(task, candidates)
        assert "reputation" not in decision.signal_types_used
        assert "skill_match" in decision.signal_types_used

    def test_no_signals_registered(self, synth):
        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth.synthesize(task, candidates)
        assert decision.outcome == DecisionOutcome.HELD
        assert decision.confidence_level == ConfidenceLevel.GUESS

    def test_all_scorers_fail(self, synth):
        def boom(task, candidate):
            raise RuntimeError("Kaboom")

        synth.register_signal(SignalType.REPUTATION, boom)
        synth.register_signal(SignalType.SKILL_MATCH, boom)

        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth.synthesize(task, candidates)
        assert decision.outcome == DecisionOutcome.HELD


# ---------------------------------------------------------------------------
# Audit Trail Tests
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_decision_logged(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1")]
        synth_with_signals.synthesize(task, candidates)
        assert len(synth_with_signals.decision_history) == 1
        entry = synth_with_signals.decision_history[0]
        assert entry["task_id"] == "t1"
        assert entry["outcome"] == "routed"

    def test_multiple_decisions_logged(self, synth_with_signals):
        for i in range(5):
            task = make_task(task_id=f"t{i}")
            synth_with_signals.synthesize(task, [make_candidate("c1")])
        assert len(synth_with_signals.decision_history) == 5

    def test_stats(self, synth_with_signals):
        for i in range(3):
            task = make_task(task_id=f"t{i}")
            synth_with_signals.synthesize(task, [make_candidate("c1")])
        stats = synth_with_signals.stats
        assert stats["total_decisions"] == 3
        assert stats["providers_registered"] == 3

    def test_stats_empty(self, synth):
        stats = synth.stats
        assert stats["total_decisions"] == 0


# ---------------------------------------------------------------------------
# Weight Override Tests
# ---------------------------------------------------------------------------


class TestWeightOverrides:
    def test_override_weights(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1"), make_candidate("c2")]

        # Default: c1 wins (higher skill + reliability)
        d1 = synth_with_signals.synthesize(task, candidates)
        assert d1.best_candidate == "c1"

        # Override: boost reputation to dominate (c2 has higher reputation)
        d2 = synth_with_signals.synthesize(
            task,
            candidates,
            override_weights={
                SignalType.REPUTATION: 0.95,
                SignalType.SKILL_MATCH: 0.03,
                SignalType.RELIABILITY: 0.02,
            },
        )
        # c2 has reputation=85 vs c1's 80, should win with reputation dominant
        assert d2.best_candidate == "c2"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_duplicate_candidates(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate("c1"), make_candidate("c1")]
        decision = synth_with_signals.synthesize(task, candidates)
        assert len(decision.rankings) == 2

    def test_task_id_from_task_id_field(self, synth_with_signals):
        task = {"task_id": "custom_id", "title": "Test"}
        decision = synth_with_signals.synthesize(task, [make_candidate("c1")])
        assert decision.task_id == "custom_id"

    def test_candidate_without_id(self, synth_with_signals):
        task = make_task()
        candidates = [{"wallet": "0xABC", "skills": []}]
        decision = synth_with_signals.synthesize(task, candidates)
        assert decision.rankings[0].candidate_id == ""

    def test_many_candidates(self, synth_with_signals):
        task = make_task()
        candidates = [make_candidate(f"c{i}") for i in range(50)]
        decision = synth_with_signals.synthesize(task, candidates)
        assert len(decision.rankings) == 50
        assert decision.rankings[0].rank == 1
        assert decision.rankings[-1].rank == 50

    def test_custom_min_threshold(self):
        synth = DecisionSynthesizer(min_threshold=0.99)
        synth.register_signal(SignalType.SKILL_MATCH, constant_scorer(80))
        task = make_task()
        candidates = [make_candidate("c1")]
        decision = synth.synthesize(task, candidates)
        # 0.8 normalized < 0.99 threshold → held
        assert decision.outcome == DecisionOutcome.HELD


# ---------------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------------


class TestConfiguration:
    def test_default_weights_sum_approximately_one(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_all_weight_types_defined(self):
        """Key signal types should have default weights."""
        key_types = [
            SignalType.SKILL_MATCH,
            SignalType.REPUTATION,
            SignalType.RELIABILITY,
            SignalType.AVAILABILITY,
        ]
        for st in key_types:
            assert st in DEFAULT_WEIGHTS, f"Missing weight for {st}"

    def test_minimum_threshold_positive(self):
        assert MINIMUM_ROUTE_THRESHOLD > 0

    def test_high_confidence_signals_reasonable(self):
        assert HIGH_CONFIDENCE_SIGNALS >= 3
        assert HIGH_CONFIDENCE_SIGNALS <= 10
