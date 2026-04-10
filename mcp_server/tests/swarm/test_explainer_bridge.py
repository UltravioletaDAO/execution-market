"""
Tests for ExplainerBridge — Module #72: Decision Transparency
==============================================================

Validates server-side routing decision decomposition.

Test categories:
1. SignalContribution data class
2. Live recording: begin → record → finalize
3. Explanation generation (physical/digital/general)
4. Comparison API
5. Counterfactual analysis
6. Ranking explanation
7. Audit summary
8. Persistence (save/load)
9. Health endpoint
10. Edge cases
"""

import json
import os
import tempfile
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "swarm"))

from explainer_bridge import (
    ExplainerBridge,
    SignalContribution,
    Decision,
    Comparison,
    BRIDGE_LABELS,
    _short_id,
    _infer_task_type,
    _get_phrases,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bridge():
    return ExplainerBridge()


@pytest.fixture
def physical_task():
    return {
        "id": "task_phy_001",
        "category": "physical_verification",
        "title": "Verify storefront",
        "evidence_type": "photo_geo",
    }


@pytest.fixture
def digital_task():
    return {
        "id": "task_dig_001",
        "category": "digital_task",
        "title": "Research pricing",
        "evidence_type": "text_response",
    }


def _make_decision(bridge, task_id, worker_id, base, signals_data, final, task=None):
    bridge.begin_decision(task_id, worker_id, base_score=base, task=task)
    for s in signals_data:
        bridge.record_signal(
            s["name"], s["bonus"],
            weight=s.get("weight", 1.0),
            confidence=s.get("confidence", 1.0),
            detail=s.get("detail"),
        )
    return bridge.finalize_decision(final_score=final)


# ---------------------------------------------------------------------------
# SignalContribution
# ---------------------------------------------------------------------------

class TestSignalContribution:
    def test_basic(self):
        sc = SignalContribution(bridge_name="geo", bonus=0.08, weight=0.12)
        assert sc.bridge_name == "geo"
        assert sc.bonus == 0.08

    def test_human_label(self):
        sc = SignalContribution(bridge_name="geo", bonus=0.05, weight=1.0)
        assert sc.human_label == "Geographic Proximity"

    def test_unknown_label(self):
        sc = SignalContribution(bridge_name="custom_xyz", bonus=0.01, weight=1.0)
        assert sc.human_label == "custom_xyz"

    def test_to_dict(self):
        sc = SignalContribution(bridge_name="quality", bonus=0.06, weight=0.10, confidence=0.9)
        d = sc.to_dict()
        assert d["bridge_name"] == "quality"
        assert d["label"] == "Evidence Quality"
        assert d["bonus"] == 0.06

    def test_negative_bonus(self):
        sc = SignalContribution(bridge_name="comm", bonus=-0.03, weight=0.07)
        assert sc.bonus < 0


# ---------------------------------------------------------------------------
# Task Type Inference
# ---------------------------------------------------------------------------

class TestTaskType:
    def test_physical(self):
        assert _infer_task_type({"category": "physical_verification"}) == "physical"

    def test_digital(self):
        assert _infer_task_type({"category": "digital_task"}) == "digital"

    def test_general(self):
        assert _infer_task_type({"category": "custom"}) == "general"

    def test_empty(self):
        assert _infer_task_type({}) == "general"

    def test_physical_phrases(self):
        p = _get_phrases("physical")
        assert "near" in p["geo"]

    def test_digital_phrases(self):
        p = _get_phrases("digital")
        assert "timezone" in p["geo"]


# ---------------------------------------------------------------------------
# Short ID
# ---------------------------------------------------------------------------

class TestShortId:
    def test_wallet(self):
        assert _short_id("0xABCDEF1234567890") == "0xABCD...7890"

    def test_short(self):
        assert _short_id("worker_1") == "worker_1"


# ---------------------------------------------------------------------------
# Live Recording
# ---------------------------------------------------------------------------

class TestLiveRecording:
    def test_basic_flow(self, bridge):
        bridge.begin_decision("t1", "0xAAA", base_score=0.65)
        bridge.record_signal("geo", 0.08, weight=0.12)
        bridge.record_signal("quality", 0.06, weight=0.10)
        d = bridge.finalize_decision(final_score=0.79)

        assert d.task_id == "t1"
        assert d.worker_id == "0xAAA"
        assert d.final_score == 0.79
        assert len(d.signals) == 2

    def test_deciding_signals(self, bridge):
        bridge.begin_decision("t", "w")
        bridge.record_signal("geo", 0.10)
        bridge.record_signal("quality", 0.08)
        bridge.record_signal("fpq", 0.06)
        bridge.record_signal("comm", 0.02)
        d = bridge.finalize_decision(final_score=0.76)
        assert len(d.deciding_signals) == 3
        assert d.deciding_signals[0] == "geo"

    def test_negative_signals(self, bridge):
        bridge.begin_decision("t", "w")
        bridge.record_signal("geo", -0.05)
        bridge.record_signal("fpq", 0.04)
        d = bridge.finalize_decision(final_score=0.49)
        assert len(d.negative_signals) == 1
        assert len(d.positive_signals) == 1

    def test_total_bonus(self, bridge):
        d = _make_decision(bridge, "t", "w", 0.5, [
            {"name": "geo", "bonus": 0.05},
            {"name": "quality", "bonus": 0.03},
        ], 0.58)
        assert abs(d.total_bonus - 0.08) < 1e-9

    def test_timestamp(self, bridge):
        bridge.begin_decision("t", "w")
        d = bridge.finalize_decision(final_score=0.5)
        assert "T" in d.timestamp

    def test_finalize_without_begin_raises(self, bridge):
        with pytest.raises(ValueError):
            bridge.finalize_decision(final_score=0.5)

    def test_record_without_begin_warns(self, bridge):
        bridge.record_signal("test", 0.05)  # Should not crash

    def test_state_resets(self, bridge):
        _make_decision(bridge, "t1", "w1", 0.5, [{"name": "a", "bonus": 0.1}], 0.6)
        bridge.begin_decision("t2", "w2")
        d = bridge.finalize_decision(final_score=0.5)
        assert d.task_id == "t2"
        assert len(d.signals) == 0

    def test_decision_count(self, bridge):
        _make_decision(bridge, "t1", "w1", 0.5, [], 0.5)
        _make_decision(bridge, "t2", "w2", 0.5, [], 0.5)
        assert bridge.decision_count == 2


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------

class TestExplanation:
    def test_physical_explanation(self, bridge, physical_task):
        bridge.begin_decision("phy_1", "0xAABBCCDD11223344", base_score=0.65, task=physical_task)
        bridge.record_signal("geo", 0.08)
        d = bridge.finalize_decision(final_score=0.73)
        assert "0xAABB...3344" in d.explanation
        assert d.task_type == "physical"

    def test_digital_explanation(self, bridge, digital_task):
        bridge.begin_decision("dig_1", "0xDDEEFF", base_score=0.7, task=digital_task)
        bridge.record_signal("comm", 0.05)
        d = bridge.finalize_decision(final_score=0.75)
        assert d.task_type == "digital"

    def test_includes_base_score(self, bridge):
        bridge.begin_decision("t", "w", base_score=0.72)
        d = bridge.finalize_decision(final_score=0.72)
        assert "72%" in d.explanation

    def test_no_signals(self, bridge):
        bridge.begin_decision("t", "w", base_score=0.50)
        d = bridge.finalize_decision(final_score=0.50)
        assert "50%" in d.explanation

    def test_includes_advantages(self, bridge):
        bridge.begin_decision("t", "w")
        bridge.record_signal("geo", 0.10)
        d = bridge.finalize_decision(final_score=0.60)
        assert "Advantage" in d.explanation or "+" in d.explanation

    def test_includes_concerns(self, bridge):
        bridge.begin_decision("t", "w")
        bridge.record_signal("comm", -0.05)
        d = bridge.finalize_decision(final_score=0.45)
        assert "Concern" in d.explanation or "Communication" in d.explanation


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

class TestComparison:
    def test_basic(self, bridge):
        d_a = _make_decision(bridge, "t", "A", 0.7, [{"name": "geo", "bonus": 0.1}], 0.8)
        d_b = _make_decision(bridge, "t", "B", 0.5, [{"name": "geo", "bonus": 0.01}], 0.51)
        comp = bridge.compare(d_a, d_b)
        assert comp.winner.worker_id == "A"
        assert comp.loser.worker_id == "B"
        assert comp.score_gap == pytest.approx(0.29)

    def test_auto_swap(self, bridge):
        d_low = _make_decision(bridge, "t", "low", 0.3, [], 0.3)
        d_high = _make_decision(bridge, "t", "high", 0.8, [], 0.8)
        comp = bridge.compare(d_low, d_high)
        assert comp.winner.worker_id == "high"

    def test_advantages_and_disadvantages(self, bridge):
        d_a = _make_decision(bridge, "t", "A", 0.5, [
            {"name": "geo", "bonus": 0.15},
            {"name": "comm", "bonus": -0.02},
        ], 0.63)
        d_b = _make_decision(bridge, "t", "B", 0.5, [
            {"name": "geo", "bonus": 0.01},
            {"name": "comm", "bonus": 0.05},
        ], 0.56)
        comp = bridge.compare(d_a, d_b)
        assert "geo" in comp.decisive_advantages
        assert "comm" in comp.decisive_disadvantages

    def test_identical_scores(self, bridge):
        d_a = _make_decision(bridge, "t", "A", 0.5, [], 0.5)
        d_b = _make_decision(bridge, "t", "B", 0.5, [], 0.5)
        comp = bridge.compare(d_a, d_b)
        assert comp.score_gap == pytest.approx(0.0)

    def test_to_dict(self, bridge):
        d_a = _make_decision(bridge, "t", "A", 0.8, [], 0.8)
        d_b = _make_decision(bridge, "t", "B", 0.6, [], 0.6)
        comp = bridge.compare(d_a, d_b)
        d = comp.to_dict()
        assert "winner_id" in d
        assert "score_gap" in d

    def test_summary_text(self, bridge):
        d_a = _make_decision(bridge, "t", "A", 0.7, [{"name": "a", "bonus": 0.1}], 0.8)
        d_b = _make_decision(bridge, "t", "B", 0.5, [], 0.5)
        comp = bridge.compare(d_a, d_b)
        assert "beat" in comp.summary.lower()


# ---------------------------------------------------------------------------
# Counterfactual
# ---------------------------------------------------------------------------

class TestCounterfactual:
    def test_signal_flip(self, bridge):
        d_a = _make_decision(bridge, "t", "A", 0.5, [{"name": "geo", "bonus": 0.20}], 0.70)
        d_b = _make_decision(bridge, "t", "B", 0.5, [{"name": "geo", "bonus": 0.01}], 0.51)
        comp = bridge.compare(d_a, d_b)
        assert "would have won" in comp.counterfactual

    def test_no_flip(self, bridge):
        d_a = _make_decision(bridge, "t", "A", 0.5, [
            {"name": "geo", "bonus": 0.03},
            {"name": "fpq", "bonus": 0.03},
            {"name": "comm", "bonus": 0.03},
        ], 0.59)
        d_b = _make_decision(bridge, "t", "B", 0.5, [], 0.50)
        comp = bridge.compare(d_a, d_b)
        assert "No single signal" in comp.counterfactual

    def test_disabled(self):
        bridge = ExplainerBridge(enable_counterfactual=False)
        d_a = _make_decision(bridge, "t", "A", 0.5, [{"name": "geo", "bonus": 0.5}], 1.0)
        d_b = _make_decision(bridge, "t", "B", 0.5, [], 0.5)
        comp = bridge.compare(d_a, d_b)
        assert comp.counterfactual == ""


# ---------------------------------------------------------------------------
# Ranking Explanation
# ---------------------------------------------------------------------------

class TestRankingExplanation:
    def test_basic(self, bridge):
        decisions = [
            _make_decision(bridge, "t", "A", 0.8, [{"name": "geo", "bonus": 0.1}], 0.90),
            _make_decision(bridge, "t", "B", 0.6, [{"name": "geo", "bonus": 0.05}], 0.65),
            _make_decision(bridge, "t", "C", 0.4, [], 0.40),
        ]
        result = bridge.explain_ranking(decisions, task_id="t")
        assert result["total_candidates"] == 3
        assert len(result["pairs"]) == 2

    def test_single_candidate(self, bridge):
        d = [_make_decision(bridge, "t", "A", 0.8, [], 0.8)]
        result = bridge.explain_ranking(d)
        assert result["total_candidates"] == 1
        assert len(result["pairs"]) == 0

    def test_empty(self, bridge):
        result = bridge.explain_ranking([])
        assert "No candidates" in result["explanation"]

    def test_sorts_by_score(self, bridge):
        decisions = [
            _make_decision(bridge, "t", "C", 0.3, [], 0.3),
            _make_decision(bridge, "t", "A", 0.9, [], 0.9),
            _make_decision(bridge, "t", "B", 0.6, [], 0.6),
        ]
        result = bridge.explain_ranking(decisions)
        assert result["pairs"][0]["worker_a"] == "A"


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class TestAudit:
    def test_empty(self, bridge):
        a = bridge.audit_summary()
        assert a["total_decisions"] == 0

    def test_tracks(self, bridge):
        _make_decision(bridge, "t1", "w1", 0.5, [{"name": "geo", "bonus": 0.1}], 0.6)
        _make_decision(bridge, "t2", "w2", 0.4, [{"name": "fpq", "bonus": 0.2}], 0.6)
        a = bridge.audit_summary()
        assert a["total_decisions"] == 2
        assert a["avg_score"] == pytest.approx(0.6)

    def test_signal_frequency(self, bridge):
        for i in range(5):
            _make_decision(bridge, f"t{i}", f"w{i}", 0.5, [{"name": "geo", "bonus": 0.1}], 0.6)
        a = bridge.audit_summary()
        assert a["signal_frequency"]["geo"] == 5

    def test_reset(self, bridge):
        _make_decision(bridge, "t1", "w1", 0.5, [], 0.5)
        bridge.reset()
        assert bridge.decision_count == 0

    def test_trimming(self):
        bridge = ExplainerBridge(max_decisions=10)
        for i in range(20):
            _make_decision(bridge, f"t{i}", f"w{i}", 0.5, [], 0.5)
        assert bridge.decision_count == 20
        a = bridge.audit_summary()
        assert len(a["decisions"]) <= 10


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_load(self, bridge):
        _make_decision(bridge, "t1", "0xAAA", 0.65, [
            {"name": "geo", "bonus": 0.08, "weight": 0.12},
        ], 0.73)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            loaded = ExplainerBridge.load(path)
            assert loaded.decision_count == 1
            a = loaded.audit_summary()
            assert a["decisions"][0]["task_id"] == "t1"
        finally:
            os.unlink(path)

    def test_save_empty(self, bridge):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            with open(path) as f:
                data = json.load(f)
            assert data["total_decisions"] == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_empty(self, bridge):
        h = bridge.health()
        assert h["status"] == "healthy"
        assert h["module_number"] == 72
        assert h["total_decisions"] == 0

    def test_with_data(self, bridge):
        _make_decision(bridge, "t", "w", 0.5, [{"name": "geo", "bonus": 0.1}], 0.6)
        h = bridge.health()
        assert h["total_decisions"] == 1
        assert h["most_decisive_signal"] == "geo"


# ---------------------------------------------------------------------------
# Decision Data Class
# ---------------------------------------------------------------------------

class TestDecision:
    def test_to_dict(self, bridge):
        d = _make_decision(bridge, "t1", "w1", 0.65, [{"name": "geo", "bonus": 0.08}], 0.73)
        dd = d.to_dict()
        assert dd["task_id"] == "t1"
        assert dd["final_score"] == 0.73
        assert len(dd["signals"]) == 1

    def test_positive_negative(self, bridge):
        d = _make_decision(bridge, "t", "w", 0.5, [
            {"name": "pos", "bonus": 0.05},
            {"name": "neg", "bonus": -0.03},
        ], 0.52)
        assert len(d.positive_signals) == 1
        assert len(d.negative_signals) == 1


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_many_signals(self, bridge):
        bridge.begin_decision("t", "w")
        for i in range(50):
            bridge.record_signal(f"s{i}", 0.01 * i)
        d = bridge.finalize_decision(final_score=12.0)
        assert len(d.signals) == 50
        assert len(d.deciding_signals) == 3

    def test_all_negative(self, bridge):
        d = _make_decision(bridge, "t", "w", 0.8, [
            {"name": "a", "bonus": -0.10},
            {"name": "b", "bonus": -0.05},
        ], 0.65)
        assert d.total_bonus == pytest.approx(-0.15)

    def test_zero_bonus(self, bridge):
        d = _make_decision(bridge, "t", "w", 0.5, [{"name": "a", "bonus": 0.0}], 0.5)
        assert len(d.deciding_signals) == 0

    def test_custom_top_n(self):
        bridge = ExplainerBridge(top_n_deciding=5)
        bridge.begin_decision("t", "w")
        for i in range(10):
            bridge.record_signal(f"s{i}", 0.05 + i * 0.01)
        d = bridge.finalize_decision(final_score=1.0)
        assert len(d.deciding_signals) == 5
