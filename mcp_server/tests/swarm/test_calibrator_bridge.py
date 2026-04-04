"""
Tests for CalibratorBridge — Module #73: Outcome-Driven Calibration
=====================================================================
"""

import json
import os
import tempfile
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "swarm"))

from calibrator_bridge import (
    CalibratorBridge,
    DecisionRecord,
    OutcomeRecord,
    SignalAccuracy,
    CalibrationReport,
    DriftAlert,
)


@pytest.fixture
def bridge():
    return CalibratorBridge(min_observations=5)


def _seed_correlated(bridge, n=10):
    """Geo correlates with success, fpq neutral."""
    for i in range(n):
        bridge.record_decision(f"t_good_{i}", "0xG", 0.85,
                               {"geo": 0.08, "fpq": 0.04})
        bridge.record_outcome(f"t_good_{i}", "0xG", success=True, quality_score=0.9)
    for i in range(n):
        bridge.record_decision(f"t_bad_{i}", "0xB", 0.55,
                               {"geo": -0.02, "fpq": 0.04})
        bridge.record_outcome(f"t_bad_{i}", "0xB", success=False, quality_score=0.3)


class TestRecording:
    def test_record_decision(self, bridge):
        bridge.record_decision("t1", "w1", 0.8, {"geo": 0.05})
        assert bridge.decision_count == 1

    def test_record_outcome(self, bridge):
        bridge.record_outcome("t1", "w1", success=True)
        assert bridge.outcome_count == 1

    def test_matched_count(self, bridge):
        bridge.record_decision("t1", "w1", 0.8, {"geo": 0.05})
        bridge.record_outcome("t1", "w1", success=True)
        assert bridge.matched_count == 1

    def test_unmatched(self, bridge):
        bridge.record_decision("t1", "w1", 0.8, {"a": 0.05})
        assert bridge.matched_count == 0

    def test_from_explainer(self, bridge):
        bridge.record_decision_from_explainer({
            "task_id": "t1", "worker_id": "w1", "final_score": 0.8,
            "signals": [{"bridge_name": "geo", "bonus": 0.06}],
        })
        assert bridge.decision_count == 1

    def test_quality_clamped(self, bridge):
        bridge.record_outcome("t1", "w1", success=True, quality_score=1.5)
        bridge.record_decision("t1", "w1", 0.8, {"a": 0.05})
        assert bridge.matched_count == 1


class TestSignalAccuracy:
    def test_no_data(self, bridge):
        a = bridge.signal_accuracy("geo")
        assert a.sample_size == 0

    def test_positive_correlation(self, bridge):
        _seed_correlated(bridge)
        a = bridge.signal_accuracy("geo")
        assert a.correlation > 0
        assert a.avg_bonus_success > a.avg_bonus_failure

    def test_neutral_signal(self, bridge):
        _seed_correlated(bridge)
        a = bridge.signal_accuracy("fpq")
        assert abs(a.correlation) < 0.1

    def test_significance(self, bridge):
        _seed_correlated(bridge)
        a = bridge.signal_accuracy("geo")
        assert a.is_significant

    def test_to_dict(self, bridge):
        _seed_correlated(bridge, n=5)
        a = bridge.signal_accuracy("geo")
        d = a.to_dict()
        assert "bridge_name" in d
        assert "correlation" in d


class TestRecommendations:
    def test_increase(self, bridge):
        _seed_correlated(bridge)
        recs = bridge.recommend_adjustments()
        assert "geo" in recs
        assert recs["geo"] > 0

    def test_empty(self, bridge):
        assert len(bridge.recommend_adjustments()) == 0

    def test_capped(self, bridge):
        _seed_correlated(bridge, n=50)
        for _, v in bridge.recommend_adjustments().items():
            assert abs(v) <= bridge._max_adj


class TestAllAccuracies:
    def test_returns_all(self, bridge):
        _seed_correlated(bridge, n=5)
        accs = bridge.all_signal_accuracies()
        names = [a.bridge_name for a in accs]
        assert "geo" in names
        assert "fpq" in names

    def test_sorted(self, bridge):
        _seed_correlated(bridge, n=5)
        accs = bridge.all_signal_accuracies()
        names = [a.bridge_name for a in accs]
        assert names == sorted(names)


class TestDrift:
    def test_insufficient_data(self, bridge):
        _seed_correlated(bridge, n=5)
        assert bridge.drift_detection() == []


class TestReport:
    def test_empty(self, bridge):
        r = bridge.calibration_report()
        assert r.total_decisions == 0
        assert r.matched_pairs == 0

    def test_full(self, bridge):
        _seed_correlated(bridge)
        r = bridge.calibration_report()
        assert r.total_decisions == 20
        assert r.matched_pairs == 20
        assert r.success_rate == pytest.approx(0.5)

    def test_to_dict(self, bridge):
        _seed_correlated(bridge, n=5)
        d = bridge.calibration_report().to_dict()
        assert "signal_accuracies" in d
        assert "recommendations" in d

    def test_has_drift(self, bridge):
        assert not bridge.calibration_report().has_drift

    def test_needs_recalibration(self, bridge):
        assert not bridge.calibration_report().needs_recalibration

    def test_avg_quality(self, bridge):
        bridge.record_decision("t1", "w1", 0.8, {"a": 0.05})
        bridge.record_outcome("t1", "w1", success=True, quality_score=0.8)
        bridge.record_decision("t2", "w2", 0.6, {"a": 0.01})
        bridge.record_outcome("t2", "w2", success=True, quality_score=0.6)
        assert bridge.calibration_report().avg_quality == pytest.approx(0.7)


class TestPersistence:
    def test_save_load(self, bridge):
        _seed_correlated(bridge, n=5)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            loaded = CalibratorBridge.load(path)
            assert loaded.decision_count == 10
            assert loaded.outcome_count == 10
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


class TestHealth:
    def test_empty(self, bridge):
        h = bridge.health()
        assert h["status"] == "healthy"
        assert h["module_number"] == 73
        assert not h["ready_for_calibration"]

    def test_ready(self, bridge):
        _seed_correlated(bridge)
        h = bridge.health()
        assert h["ready_for_calibration"]


class TestEdgeCases:
    def test_all_success(self, bridge):
        for i in range(10):
            bridge.record_decision(f"t{i}", "w", 0.8, {"geo": 0.05 + i * 0.01})
            bridge.record_outcome(f"t{i}", "w", success=True)
        assert bridge.signal_accuracy("geo").correlation == 0.0

    def test_all_failure(self, bridge):
        for i in range(10):
            bridge.record_decision(f"t{i}", "w", 0.5, {"geo": 0.01})
            bridge.record_outcome(f"t{i}", "w", success=False)
        assert bridge.signal_accuracy("geo").correlation == 0.0

    def test_identical_bonuses(self, bridge):
        for i in range(10):
            bridge.record_decision(f"t{i}", f"w{i}", 0.7, {"geo": 0.05})
            bridge.record_outcome(f"t{i}", f"w{i}", success=(i < 5))
        assert abs(bridge.signal_accuracy("geo").correlation) < 0.001

    def test_empty_signals(self, bridge):
        bridge.record_decision("t1", "w1", 0.5, {})
        bridge.record_outcome("t1", "w1", success=True)
        r = bridge.calibration_report()
        assert r.matched_pairs == 1
        assert len(r.signal_accuracies) == 0
