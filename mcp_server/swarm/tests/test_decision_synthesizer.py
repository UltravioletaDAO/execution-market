from __future__ import annotations
"""
Tests for DecisionSynthesizer — Unified Multi-Signal Routing Engine
====================================================================

The DecisionSynthesizer is the brain of the swarm routing system.
These tests cover:
    1. Signal registration and lifecycle
    2. Basic synthesis (single signal, multi-signal)
    3. Candidate ranking and scoring
    4. Confidence levels and determination
    5. Outcome classification (ROUTED, HELD, etc.)
    6. Explanation generation
    7. Degradation tolerance (signal failures)
    8. Weight management and updates
    9. Audit trail and decision history
    10. Statistics aggregation
    11. Candidate comparison (head-to-head)
    12. What-if analysis
    13. Edge cases (empty candidates, zero scores, etc.)
    14. Quick synthesis shortcut
    15. Normalization
"""

import importlib.util
import sys
import os

import pytest

# Direct-load decision_synthesizer without triggering __init__.py import chain
# (other swarm modules use Python 3.10+ union syntax that fails on 3.9).
_swarm_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_mod_path = os.path.join(_swarm_dir, "decision_synthesizer.py")

# Temporarily shadow the package entry if needed, then restore.
_had_pkg = "mcp_server.swarm" in sys.modules
_old_pkg = sys.modules.get("mcp_server.swarm")
if not _had_pkg:
    import types as _t
    sys.modules["mcp_server.swarm"] = _t.ModuleType("mcp_server.swarm")

_spec = importlib.util.spec_from_file_location(
    "_ds_standalone", _mod_path
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Restore the package entry so other tests aren't polluted.
if not _had_pkg:
    del sys.modules["mcp_server.swarm"]
else:
    sys.modules["mcp_server.swarm"] = _old_pkg

DecisionSynthesizer = _mod.DecisionSynthesizer
SignalType = _mod.SignalType
SignalValue = _mod.SignalValue
SignalVector = _mod.SignalVector
RankedDecision = _mod.RankedDecision
DecisionOutcome = _mod.DecisionOutcome
ConfidenceLevel = _mod.ConfidenceLevel
DEFAULT_WEIGHTS = _mod.DEFAULT_WEIGHTS
MINIMUM_ROUTE_THRESHOLD = _mod.MINIMUM_ROUTE_THRESHOLD


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_task(task_id="task-1", category="simple_action", title="Test task", bounty=0.15):
    return {
        "id": task_id,
        "category": category,
        "title": title,
        "bounty_usd": bounty,
    }


def make_candidate(cid="agent-1", wallet="0xAAA", skills=None):
    return {
        "id": cid,
        "wallet": wallet,
        "skills": skills or ["photo", "delivery"],
    }


def fixed_scorer(score):
    """Return a scorer that always returns the given score."""
    def scorer(task, candidate):
        return score
    return scorer


def candidate_id_scorer(scores_map):
    """Return a scorer that returns different scores per candidate ID."""
    def scorer(task, candidate):
        cid = str(candidate.get("id", ""))
        return scores_map.get(cid, 50)
    return scorer


def failing_scorer(task, candidate):
    """A scorer that raises an exception."""
    raise RuntimeError("Signal computation failed!")


# ===========================================================================
# 1. Signal Registration
# ===========================================================================

class TestSignalRegistration:
    def test_register_signal(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        assert "reputation" in ds.registered_signals

    def test_register_multiple(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.register_signal(SignalType.SKILL_MATCH, fixed_scorer(90))
        ds.register_signal(SignalType.AVAILABILITY, fixed_scorer(70))
        assert len(ds.registered_signals) == 3

    def test_unregister_signal(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.unregister_signal(SignalType.REPUTATION)
        assert "reputation" not in ds.registered_signals

    def test_unregister_nonexistent(self):
        ds = DecisionSynthesizer()
        ds.unregister_signal(SignalType.REPUTATION)  # No error
        assert ds.registered_signals == []

    def test_register_with_custom_weight(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80), weight=0.5)
        assert ds._providers[SignalType.REPUTATION].weight == 0.5

    def test_register_with_description(self):
        ds = DecisionSynthesizer()
        ds.register_signal(
            SignalType.REPUTATION, fixed_scorer(80),
            description="On-chain rep from ERC-8004"
        )
        assert ds._providers[SignalType.REPUTATION].description == "On-chain rep from ERC-8004"


# ===========================================================================
# 2. Basic Synthesis
# ===========================================================================

class TestBasicSynthesis:
    def test_single_signal_single_candidate(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.ROUTED
        assert decision.best_candidate == "agent-1"
        assert decision.best_score > 0

    def test_multi_signal(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.register_signal(SignalType.SKILL_MATCH, fixed_scorer(90))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.ROUTED
        assert len(decision.signal_types_used) == 2

    def test_multi_candidate(self):
        ds = DecisionSynthesizer()
        ds.register_signal(
            SignalType.REPUTATION,
            candidate_id_scorer({"agent-1": 80, "agent-2": 60, "agent-3": 90})
        )
        candidates = [
            make_candidate("agent-1"),
            make_candidate("agent-2"),
            make_candidate("agent-3"),
        ]
        decision = ds.synthesize(make_task(), candidates)
        assert decision.best_candidate == "agent-3"
        assert len(decision.rankings) == 3

    def test_no_candidates_returns_held(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [])
        assert decision.outcome == DecisionOutcome.HELD


# ===========================================================================
# 3. Ranking and Scoring
# ===========================================================================

class TestRanking:
    def test_candidates_ranked_by_score(self):
        ds = DecisionSynthesizer()
        ds.register_signal(
            SignalType.REPUTATION,
            candidate_id_scorer({"a1": 90, "a2": 70, "a3": 80})
        )
        candidates = [make_candidate("a1"), make_candidate("a2"), make_candidate("a3")]
        decision = ds.synthesize(make_task(), candidates)
        ranks = [r.candidate_id for r in decision.rankings]
        assert ranks == ["a1", "a3", "a2"]

    def test_rank_numbers_assigned(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, candidate_id_scorer({"a": 80, "b": 60}))
        decision = ds.synthesize(make_task(), [make_candidate("a"), make_candidate("b")])
        assert decision.rankings[0].rank == 1
        assert decision.rankings[1].rank == 2

    def test_composite_score_reasonable(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate()])
        score = decision.best_score
        assert 0.0 <= score <= 1.0

    def test_top_n_property(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, candidate_id_scorer(
            {"a": 90, "b": 80, "c": 70, "d": 60}
        ))
        candidates = [make_candidate(c) for c in "abcd"]
        decision = ds.synthesize(make_task(), candidates)
        assert len(decision.top_n) == 3
        assert decision.top_n[0] == "a"


# ===========================================================================
# 4. Confidence Levels
# ===========================================================================

class TestConfidence:
    def test_high_confidence_many_signals(self):
        ds = DecisionSynthesizer()
        for st in [SignalType.REPUTATION, SignalType.SKILL_MATCH, SignalType.AVAILABILITY,
                    SignalType.SPEED, SignalType.RELIABILITY]:
            ds.register_signal(st, fixed_scorer(80), confidence=0.9)
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.confidence_level == ConfidenceLevel.HIGH

    def test_low_confidence_single_signal(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80), confidence=0.3)
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.confidence_level in (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM)

    def test_confidence_score_bounded(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert 0.0 <= decision.confidence_score <= 1.0

    def test_signal_vector_total_confidence(self):
        sv = SignalVector(
            candidate_id="test",
            signals=[
                SignalValue(SignalType.REPUTATION, 80, 0.8, 1.0, 0.9),
                SignalValue(SignalType.SKILL_MATCH, 90, 0.9, 1.0, 0.7),
            ],
        )
        assert abs(sv.total_confidence - 0.8) < 0.01


# ===========================================================================
# 5. Outcome Classification
# ===========================================================================

class TestOutcomes:
    def test_routed_above_threshold(self):
        ds = DecisionSynthesizer(min_threshold=0.1)
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.ROUTED

    def test_held_below_threshold(self):
        ds = DecisionSynthesizer(min_threshold=0.99)
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(10))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.HELD

    def test_held_no_signals(self):
        ds = DecisionSynthesizer()
        # No signals registered
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.HELD

    def test_held_zero_scores(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(0))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.HELD


# ===========================================================================
# 6. Explanations
# ===========================================================================

class TestExplanations:
    def test_routed_explanation_has_task_info(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(
            make_task(title="Interior photo of store"),
            [make_candidate()]
        )
        assert "Interior photo" in decision.explanation

    def test_held_explanation(self):
        ds = DecisionSynthesizer()
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert "held" in decision.explanation.lower() or "No candidate" in decision.explanation

    def test_explanation_mentions_candidate_count(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate("a"), make_candidate("b")])
        assert "2 candidate" in decision.explanation

    def test_clear_winner_mentioned(self):
        ds = DecisionSynthesizer()
        ds.register_signal(
            SignalType.REPUTATION,
            candidate_id_scorer({"a": 95, "b": 20})
        )
        decision = ds.synthesize(make_task(), [make_candidate("a"), make_candidate("b")])
        assert "clear winner" in decision.explanation.lower() or "gap" in decision.explanation.lower()


# ===========================================================================
# 7. Degradation Tolerance
# ===========================================================================

class TestDegradation:
    def test_one_signal_fails_others_work(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.register_signal(SignalType.SKILL_MATCH, failing_scorer)
        decision = ds.synthesize(make_task(), [make_candidate()])
        # Should still route using the surviving signal
        assert decision.outcome == DecisionOutcome.ROUTED
        assert "reputation" in decision.signal_types_used
        assert "skill_match" not in decision.signal_types_used

    def test_all_signals_fail(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, failing_scorer)
        ds.register_signal(SignalType.SKILL_MATCH, failing_scorer)
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.HELD

    def test_scorer_returns_none(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, lambda t, c: None)
        ds.register_signal(SignalType.SKILL_MATCH, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert "skill_match" in decision.signal_types_used


# ===========================================================================
# 8. Weight Management
# ===========================================================================

class TestWeights:
    def test_update_weights(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.update_weights({SignalType.REPUTATION: 0.5})
        assert ds.get_weights()["reputation"] == 0.5

    def test_update_weights_string_keys(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.update_weights({"reputation": 0.3})
        assert ds.get_weights()["reputation"] == 0.3

    def test_override_weights_in_synthesize(self):
        ds = DecisionSynthesizer()
        ds.register_signal(
            SignalType.REPUTATION,
            candidate_id_scorer({"a": 90, "b": 80})
        )
        ds.register_signal(
            SignalType.SKILL_MATCH,
            candidate_id_scorer({"a": 30, "b": 95})
        )
        
        # With default weights, depends on balance
        # With skill_match overweighted, b should win
        decision_skill_heavy = ds.synthesize(
            make_task(),
            [make_candidate("a"), make_candidate("b")],
            override_weights={
                SignalType.REPUTATION: 0.01,
                SignalType.SKILL_MATCH: 0.99,
            },
        )
        assert decision_skill_heavy.best_candidate == "b"

    def test_get_weights(self):
        ds = DecisionSynthesizer()
        weights = ds.get_weights()
        assert "skill_match" in weights
        assert "reputation" in weights

    def test_default_weights_sum_to_one(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01


# ===========================================================================
# 9. Audit Trail
# ===========================================================================

class TestAuditTrail:
    def test_decision_logged(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.synthesize(make_task(), [make_candidate()])
        assert len(ds.decision_history) == 1

    def test_multiple_decisions_logged(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        for i in range(5):
            ds.synthesize(make_task(task_id=f"t-{i}"), [make_candidate()])
        assert len(ds.decision_history) == 5

    def test_log_entry_fields(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.synthesize(make_task(task_id="t-abc"), [make_candidate()])
        entry = ds.decision_history[0]
        assert entry["task_id"] == "t-abc"
        assert "outcome" in entry
        assert "score" in entry
        assert "ts" in entry

    def test_log_circular_buffer(self):
        ds = DecisionSynthesizer()
        ds._max_log_size = 5
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        for i in range(10):
            ds.synthesize(make_task(task_id=f"t-{i}"), [make_candidate()])
        assert len(ds.decision_history) == 5
        # Should keep the last 5
        assert ds.decision_history[0]["task_id"] == "t-5"


# ===========================================================================
# 10. Statistics
# ===========================================================================

class TestStatistics:
    def test_empty_stats(self):
        ds = DecisionSynthesizer()
        stats = ds.stats
        assert stats["total_decisions"] == 0

    def test_stats_after_decisions(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        for i in range(3):
            ds.synthesize(make_task(task_id=f"t-{i}"), [make_candidate()])
        stats = ds.stats
        assert stats["total_decisions"] == 3
        assert stats["route_rate"] > 0
        assert stats["avg_decision_time_ms"] >= 0

    def test_stats_outcomes_counted(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        ds.synthesize(make_task(), [make_candidate()])
        # Use zero-score candidate to get HELD (empty candidates returns early without logging)
        ds.register_signal(SignalType.SKILL_MATCH, fixed_scorer(0))
        ds_held = DecisionSynthesizer(min_threshold=0.99)
        ds_held.register_signal(SignalType.REPUTATION, fixed_scorer(10))
        ds_held.synthesize(make_task(), [make_candidate()])
        stats = ds.stats
        assert "routed" in stats["outcomes"]
        held_stats = ds_held.stats
        assert "held" in held_stats["outcomes"]


# ===========================================================================
# 11. Candidate Comparison
# ===========================================================================

class TestComparison:
    def test_compare_two_candidates(self):
        ds = DecisionSynthesizer()
        ds.register_signal(
            SignalType.REPUTATION,
            candidate_id_scorer({"a": 90, "b": 60})
        )
        result = ds.compare_candidates(
            make_task(),
            make_candidate("a"),
            make_candidate("b"),
        )
        assert result["winner"] == "a"
        assert result["score_gap"] > 0
        assert "signal_comparison" in result

    def test_comparison_signal_breakdown(self):
        ds = DecisionSynthesizer()
        ds.register_signal(
            SignalType.REPUTATION,
            candidate_id_scorer({"a": 90, "b": 60})
        )
        result = ds.compare_candidates(
            make_task(),
            make_candidate("a"),
            make_candidate("b"),
        )
        assert "reputation" in result["signal_comparison"]
        rep = result["signal_comparison"]["reputation"]
        assert rep["a"] > rep["b"]
        assert rep["advantage"] == "a"


# ===========================================================================
# 12. What-If Analysis
# ===========================================================================

class TestWhatIf:
    def test_what_if_same_weights(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        result = ds.what_if(
            make_task(),
            [make_candidate()],
            modified_weights=dict(DEFAULT_WEIGHTS),
        )
        assert result["ranking_changed"] is False

    def test_what_if_different_winner(self):
        ds = DecisionSynthesizer()
        ds.register_signal(
            SignalType.REPUTATION,
            candidate_id_scorer({"a": 90, "b": 30}),
            weight=0.5,
        )
        ds.register_signal(
            SignalType.SKILL_MATCH,
            candidate_id_scorer({"a": 30, "b": 90}),
            weight=0.5,
        )
        
        candidates = [make_candidate("a"), make_candidate("b")]
        
        result = ds.what_if(
            make_task(), candidates,
            modified_weights={
                SignalType.REPUTATION: 0.01,
                SignalType.SKILL_MATCH: 0.99,
            },
        )
        # With skill_match heavily weighted, b should win
        assert result["modified_best"] == "b"


# ===========================================================================
# 13. Edge Cases
# ===========================================================================

class TestEdgeCases:
    def test_single_candidate_always_best(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(50))
        decision = ds.synthesize(make_task(), [make_candidate("solo")])
        assert decision.best_candidate == "solo"

    def test_all_zero_scores(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(0))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.HELD

    def test_all_perfect_scores(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(100))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.outcome == DecisionOutcome.ROUTED
        assert decision.best_score > 0.9

    def test_negative_scores_normalized(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(-10))
        decision = ds.synthesize(make_task(), [make_candidate()])
        # Negative should normalize to 0
        assert decision.best_score == 0.0

    def test_over_100_scores_capped(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(200))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.best_score <= 1.0

    def test_decision_has_timestamp(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.timestamp != ""
        assert "202" in decision.timestamp  # Year prefix

    def test_decision_time_tracked(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate()])
        assert decision.decision_time_ms >= 0

    def test_task_id_from_task_id_key(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize({"task_id": "fallback-id"}, [make_candidate()])
        assert decision.task_id == "fallback-id"


# ===========================================================================
# 14. Quick Synthesis
# ===========================================================================

class TestQuickSynthesis:
    def test_quick_returns_id(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        result = ds.synthesize_quick(make_task(), [make_candidate("winner")])
        assert result == "winner"

    def test_quick_returns_none_when_held(self):
        ds = DecisionSynthesizer()
        result = ds.synthesize_quick(make_task(), [make_candidate()])
        assert result is None

    def test_quick_returns_none_no_candidates(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        result = ds.synthesize_quick(make_task(), [])
        assert result is None


# ===========================================================================
# 15. Normalization
# ===========================================================================

class TestNormalization:
    def test_default_normalize_zero(self):
        assert DecisionSynthesizer._default_normalize(0) == 0.0

    def test_default_normalize_100(self):
        assert DecisionSynthesizer._default_normalize(100) == 1.0

    def test_default_normalize_50(self):
        assert DecisionSynthesizer._default_normalize(50) == 0.5

    def test_default_normalize_negative(self):
        assert DecisionSynthesizer._default_normalize(-10) == 0.0

    def test_default_normalize_over_100(self):
        assert DecisionSynthesizer._default_normalize(150) == 1.0


# ===========================================================================
# 16. Data Type Serialization
# ===========================================================================

class TestDataTypes:
    def test_signal_vector_to_dict(self):
        sv = SignalVector(
            candidate_id="agent-1",
            wallet="0xAAA",
            signals=[
                SignalValue(SignalType.REPUTATION, 80, 0.8, 0.18, 0.9, "rep"),
            ],
            composite_score=0.72,
            rank=1,
        )
        d = sv.to_dict()
        assert d["candidate_id"] == "agent-1"
        assert "reputation" in d["signals"]

    def test_signal_vector_signal_by_type(self):
        sv = SignalVector(
            candidate_id="test",
            signals=[
                SignalValue(SignalType.REPUTATION, 80, 0.8, 1.0, 0.9),
                SignalValue(SignalType.SKILL_MATCH, 90, 0.9, 1.0, 0.8),
            ],
        )
        rep = sv.signal_by_type(SignalType.REPUTATION)
        assert rep is not None
        assert rep.raw_value == 80
        
        missing = sv.signal_by_type(SignalType.SPEED)
        assert missing is None

    def test_signal_value_weighted_score(self):
        sv = SignalValue(SignalType.REPUTATION, 80, 0.8, 0.5, 0.9)
        expected = 0.8 * 0.5 * 0.9
        assert abs(sv.weighted_score - expected) < 0.001

    def test_ranked_decision_to_dict(self):
        ds = DecisionSynthesizer()
        ds.register_signal(SignalType.REPUTATION, fixed_scorer(80))
        decision = ds.synthesize(make_task(), [make_candidate()])
        d = decision.to_dict()
        assert "task_id" in d
        assert "outcome" in d
        assert "confidence" in d
        assert "top_candidates" in d

    def test_signal_count_property(self):
        sv = SignalVector(
            candidate_id="test",
            signals=[
                SignalValue(SignalType.REPUTATION, 80, 0.8, 1.0, 0.9),
                SignalValue(SignalType.SKILL_MATCH, 90, 0.9, 1.0, 0.8),
            ],
        )
        assert sv.signal_count == 2
