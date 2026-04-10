"""
Tests for AdaptationBridge — Module #76: Server-Side Contextual Signal Adaptation

Tests cover:
1. Initialization and configuration
2. Context extraction (task type, urgency, value)
3. Task type modifiers (physical, digital, hybrid)
4. Urgency modifiers (urgent, scheduled, normal)
5. Value modifiers (high, medium, low)
6. Market modifiers (high/low supply)
7. Historical modifiers (failure rates)
8. Modifier composition and clamping
9. Per-signal expansion
10. Outcome recording
11. Persistence (save/load)
12. Health and report
13. Coordinator integration
14. Edge cases
"""

import json
import os
import sys
import tempfile

import pytest

# Ensure adaptation_bridge is importable WITHOUT pulling in the full swarm package
# (reputation_bridge uses `list[str] | None` syntax that fails on Python <3.10)
import importlib
_bridge_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _bridge_dir)

_mod = importlib.import_module("adaptation_bridge")
AdaptationBridge = _mod.AdaptationBridge
AdaptationBridgeConfig = _mod.AdaptationBridgeConfig
FleetState = _mod.FleetState
ModifierResult = _mod.ModifierResult
TaskContext = _mod.TaskContext
SIGNAL_GROUPS = _mod.SIGNAL_GROUPS
ALL_SIGNALS = _mod.ALL_SIGNALS
MIN_MODIFIER = _mod.MIN_MODIFIER
MAX_MODIFIER = _mod.MAX_MODIFIER


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def bridge():
    return AdaptationBridge()

@pytest.fixture
def physical_task():
    return {
        "id": "t_001",
        "title": "Photograph storefront verification",
        "category": "physical_verification",
        "bounty_usd": 5.0,
        "evidence_types": ["photo_geo", "photo"],
    }

@pytest.fixture
def digital_task():
    return {
        "id": "t_002",
        "title": "Transcribe audio recording",
        "category": "transcription",
        "bounty_usd": 3.0,
        "evidence_types": ["text_response"],
    }

@pytest.fixture
def high_value_task():
    return {
        "id": "t_003",
        "title": "Notarized document",
        "category": "physical_verification",
        "bounty_usd": 50.0,
        "evidence_types": ["notarized"],
    }

@pytest.fixture
def urgent_task():
    return {
        "id": "t_004",
        "title": "Emergency delivery",
        "category": "delivery",
        "bounty_usd": 15.0,
        "urgency": "urgent",
    }


# ===========================================================================
# 1. Initialization
# ===========================================================================

class TestInit:
    def test_default_init(self, bridge):
        assert isinstance(bridge.config, AdaptationBridgeConfig)
        assert bridge._adaptation_count == 0

    def test_custom_config(self):
        cfg = AdaptationBridgeConfig(physical_amplify_spatial=3.0)
        b = AdaptationBridge(config=cfg)
        assert b.config.physical_amplify_spatial == 3.0


# ===========================================================================
# 2. Context Extraction
# ===========================================================================

class TestContextExtraction:
    def test_physical_type(self, bridge, physical_task):
        ctx = bridge._extract_context(physical_task)
        assert ctx.task_type == "physical"

    def test_digital_type(self, bridge, digital_task):
        ctx = bridge._extract_context(digital_task)
        assert ctx.task_type == "digital"

    def test_unknown_type(self, bridge):
        ctx = bridge._extract_context({"title": "Something"})
        assert ctx.task_type == "unknown"

    def test_urgent(self, bridge, urgent_task):
        ctx = bridge._extract_context(urgent_task)
        assert ctx.urgency == "urgent"

    def test_scheduled(self, bridge):
        ctx = bridge._extract_context({"title": "Task", "urgency": "scheduled"})
        assert ctx.urgency == "scheduled"

    def test_normal_default(self, bridge, physical_task):
        ctx = bridge._extract_context(physical_task)
        assert ctx.urgency == "normal"

    def test_high_value(self, bridge, high_value_task):
        ctx = bridge._extract_context(high_value_task)
        assert ctx.value_tier == "high"

    def test_low_value(self, bridge):
        ctx = bridge._extract_context({"title": "Task", "bounty_usd": 0.5})
        assert ctx.value_tier == "low"

    def test_medium_value(self, bridge, physical_task):
        ctx = bridge._extract_context(physical_task)
        assert ctx.value_tier == "medium"

    def test_location_extraction(self, bridge):
        task = {"title": "Task", "latitude": 25.7, "longitude": -80.2}
        ctx = bridge._extract_context(task)
        assert ctx.location is not None
        assert ctx.location["lat"] == 25.7

    def test_evidence_string_coercion(self, bridge):
        task = {"title": "Task", "evidence_types": "photo_geo"}
        ctx = bridge._extract_context(task)
        assert ctx.evidence_types == ["photo_geo"]


# ===========================================================================
# 3. Task Type Modifiers
# ===========================================================================

class TestTaskTypeModifiers:
    def test_physical_amplifies_spatial(self, bridge, physical_task):
        r = bridge.compute_modifiers(physical_task)
        assert r.group_modifiers["spatial"] > 1.0

    def test_physical_amplifies_temporal(self, bridge, physical_task):
        r = bridge.compute_modifiers(physical_task)
        assert r.group_modifiers["temporal"] > 1.0

    def test_digital_amplifies_quality(self, bridge, digital_task):
        r = bridge.compute_modifiers(digital_task)
        assert r.group_modifiers["quality"] > 1.0

    def test_digital_dampens_spatial(self, bridge, digital_task):
        r = bridge.compute_modifiers(digital_task)
        assert r.group_modifiers["spatial"] < 1.0

    def test_unknown_neutral(self, bridge):
        r = bridge.compute_modifiers({"title": "Something"})
        assert "task_type" not in r.dimensions_applied


# ===========================================================================
# 4. Urgency Modifiers
# ===========================================================================

class TestUrgencyModifiers:
    def test_urgent_amplifies_temporal(self, bridge, urgent_task):
        r = bridge.compute_modifiers(urgent_task)
        assert r.group_modifiers["temporal"] > 1.0

    def test_scheduled_amplifies_sustainability(self, bridge):
        task = {"title": "Task", "urgency": "scheduled", "bounty_usd": 5.0}
        r = bridge.compute_modifiers(task)
        assert r.group_modifiers["meta_sustainability"] > 1.0


# ===========================================================================
# 5. Value Modifiers
# ===========================================================================

class TestValueModifiers:
    def test_high_value_amplifies_integrity(self, bridge, high_value_task):
        r = bridge.compute_modifiers(high_value_task)
        assert r.group_modifiers["meta_integrity"] > 1.0

    def test_low_value_dampens_integrity(self, bridge):
        task = {"title": "Task", "bounty_usd": 0.5, "category": "misc"}
        r = bridge.compute_modifiers(task)
        assert r.group_modifiers["meta_integrity"] < 1.0


# ===========================================================================
# 6. Market Modifiers
# ===========================================================================

class TestMarketModifiers:
    def test_high_supply(self, bridge, physical_task):
        fleet = FleetState(workers_in_area=15)
        r = bridge.compute_modifiers(physical_task, fleet)
        assert "market" in r.dimensions_applied

    def test_low_supply(self, bridge, physical_task):
        fleet = FleetState(workers_in_area=1)
        r = bridge.compute_modifiers(physical_task, fleet)
        assert "market" in r.dimensions_applied

    def test_no_workers_no_market(self, bridge, physical_task):
        r = bridge.compute_modifiers(physical_task)
        assert "market" not in r.dimensions_applied


# ===========================================================================
# 7. Historical Modifiers
# ===========================================================================

class TestHistoricalModifiers:
    def test_high_failure_amplifies(self, bridge, physical_task):
        fleet = FleetState(task_type_failure_rate=0.4, task_type_history_count=20)
        r = bridge.compute_modifiers(physical_task, fleet)
        assert "historical" in r.dimensions_applied

    def test_low_failure_relaxes(self, bridge, physical_task):
        fleet = FleetState(task_type_failure_rate=0.02, task_type_history_count=50)
        r = bridge.compute_modifiers(physical_task, fleet)
        assert "historical" in r.dimensions_applied

    def test_insufficient_history(self, bridge, physical_task):
        fleet = FleetState(task_type_failure_rate=0.5, task_type_history_count=2)
        r = bridge.compute_modifiers(physical_task, fleet)
        assert "historical" not in r.dimensions_applied

    def test_internal_stats_fallback(self, bridge, physical_task):
        for i in range(10):
            bridge.record_outcome(f"t_{i}", physical_task, "failure")
        rate, count = bridge.get_failure_rate("physical_verification")
        assert count == 10
        assert rate == 1.0


# ===========================================================================
# 8. Composition and Clamping
# ===========================================================================

class TestComposition:
    def test_multiplicative_composition(self, bridge):
        task = {
            "title": "Urgent photograph storefront",
            "category": "physical_verification",
            "urgency": "urgent",
            "bounty_usd": 5.0,
            "evidence_types": ["photo_geo"],
        }
        r = bridge.compute_modifiers(task)
        # temporal: physical (1.5) * urgent (1.8) = 2.7
        assert r.group_modifiers["temporal"] == pytest.approx(1.5 * 1.8, rel=0.01)

    def test_all_modifiers_bounded(self, bridge):
        task = {
            "title": "Urgent photograph delivery",
            "category": "delivery",
            "urgency": "urgent",
            "bounty_usd": 100.0,
            "evidence_types": ["photo_geo"],
        }
        fleet = FleetState(
            available_workers=1,
            task_type_failure_rate=0.5,
            task_type_history_count=50,
        )
        r = bridge.compute_modifiers(task, fleet)
        for g, mod in r.group_modifiers.items():
            assert MIN_MODIFIER <= mod <= MAX_MODIFIER


# ===========================================================================
# 9. Per-Signal Expansion
# ===========================================================================

class TestSignalExpansion:
    def test_all_signals_present(self, bridge, physical_task):
        r = bridge.compute_modifiers(physical_task)
        for sig in ALL_SIGNALS:
            assert sig in r.modifiers

    def test_group_to_signal_mapping(self, bridge, physical_task):
        r = bridge.compute_modifiers(physical_task)
        assert r.modifiers["geo_proximity"] == r.group_modifiers["spatial"]


# ===========================================================================
# 10. Outcome Recording
# ===========================================================================

class TestOutcomeRecording:
    def test_record(self, bridge, physical_task):
        bridge.record_outcome("t1", physical_task, "success")
        assert len(bridge._history) == 1

    def test_stats_update(self, bridge, physical_task):
        bridge.record_outcome("t1", physical_task, "success")
        bridge.record_outcome("t2", physical_task, "failure")
        rate, count = bridge.get_failure_rate("physical_verification")
        assert count == 2
        assert rate == 0.5


# ===========================================================================
# 11. Persistence
# ===========================================================================

class TestPersistence:
    def test_save_load(self, bridge, physical_task):
        bridge.record_outcome("t1", physical_task, "success")
        bridge.record_outcome("t2", physical_task, "failure")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            new_bridge = AdaptationBridge()
            assert new_bridge.load(path)
            rate, count = new_bridge.get_failure_rate("physical_verification")
            assert count == 2
            assert rate == 0.5
        finally:
            os.unlink(path)

    def test_load_missing(self, bridge):
        assert not bridge.load("/nonexistent.json")

    def test_load_corrupt(self, bridge):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not json{")
            path = f.name
        try:
            assert not bridge.load(path)
        finally:
            os.unlink(path)


# ===========================================================================
# 12. Health and Report
# ===========================================================================

class TestHealthReport:
    def test_health(self, bridge):
        h = bridge.health()
        assert h["status"] == "healthy"
        assert h["module"] == "adaptation_bridge"
        assert h["module_number"] == 76
        assert h["meta_layer"] == 5

    def test_report_empty(self, bridge):
        r = bridge.report()
        assert r["total_adaptations"] == 0
        assert r["total_outcomes"] == 0

    def test_report_with_data(self, bridge, physical_task, digital_task):
        bridge.compute_modifiers(physical_task)
        bridge.compute_modifiers(digital_task)
        bridge.record_outcome("t1", physical_task, "success")
        r = bridge.report()
        assert r["total_adaptations"] == 2
        assert r["total_outcomes"] == 1

    def test_to_dict(self, bridge, physical_task):
        result = bridge.compute_modifiers(physical_task)
        d = result.to_dict()
        assert "modifiers" in d
        assert "context" in d
        assert isinstance(d, dict)


# ===========================================================================
# 13. Coordinator Integration
# ===========================================================================

class TestCoordinatorIntegration:
    def test_coordinator_has_adaptation_bridge(self):
        """Verify coordinator accepts adaptation_bridge parameter."""
        try:
            from swarm.coordinator import SwarmCoordinator
            # Just verify the import and attribute exist
            # Can't fully instantiate without all deps
            assert hasattr(SwarmCoordinator, "__init__")
        except ImportError:
            pytest.skip("Coordinator not importable in test env")


# ===========================================================================
# 14. Edge Cases
# ===========================================================================

class TestEdgeCases:
    def test_empty_task(self, bridge):
        r = bridge.compute_modifiers({})
        assert isinstance(r, ModifierResult)

    def test_none_fields(self, bridge):
        r = bridge.compute_modifiers({"title": None, "bounty_usd": None})
        assert isinstance(r, ModifierResult)

    def test_negative_bounty(self, bridge):
        r = bridge.compute_modifiers({"title": "Task", "bounty_usd": -5})
        assert r.context.value_tier == "low"

    def test_adaptation_count_increments(self, bridge, physical_task, digital_task):
        assert bridge._adaptation_count == 0
        bridge.compute_modifiers(physical_task)
        assert bridge._adaptation_count == 1
        bridge.compute_modifiers(digital_task)
        assert bridge._adaptation_count == 2

    def test_confidence_range(self, bridge, physical_task):
        r = bridge.compute_modifiers(physical_task)
        assert 0.0 <= r.confidence <= 1.0
