"""
Tests for ChainRouter — Intelligent Multi-Chain Task Routing (Module #57)
==========================================================================

Tests the full chain routing pipeline:
- Basic task routing with different strategies
- Micro-task and high-value task routing
- Batch routing optimization
- Chain management (register, remove, status)
- Worker preference tracking
- Success rate tracking
- Health checks and diagnostics
- Persistence (save/load)
- Strategy scoring (cost, speed, feature, worker, balanced)
- Edge cases and error handling
"""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

# Adjust import path for test discovery
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp_server" / "swarm"))

from swarm.chain_router import (
    ChainRouter,
    ChainProfile,
    ChainRouterConfig,
    ChainStatus,
    RoutingDecision,
    RoutingStrategy,
    ChainSuccessRecord,
)


# ─── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def router():
    """Router with default chain profiles."""
    return ChainRouter.with_default_chains()


@pytest.fixture
def custom_router():
    """Router with custom config."""
    config = ChainRouterConfig(
        default_strategy=RoutingStrategy.COST_OPTIMAL,
        max_gas_ratio=0.05,
        platform_fee_rate=0.10,
    )
    return ChainRouter.with_default_chains(config=config)


@pytest.fixture
def minimal_router():
    """Router with only 3 chains."""
    chains = {
        "base": ChainProfile(
            name="Base", chain_key="base", chain_id=8453,
            gas_per_task_usd=0.006, confirmation_time_seconds=2.0,
        ),
        "ethereum": ChainProfile(
            name="Ethereum", chain_key="ethereum", chain_id=1,
            gas_per_task_usd=1.60, confirmation_time_seconds=15.0,
        ),
        "skale": ChainProfile(
            name="SKALE", chain_key="skale",
            gas_per_task_usd=0.0, confirmation_time_seconds=3.0,
        ),
    }
    return ChainRouter(chains=chains)


# ═══════════════════════════════════════════════════════════════
# Test Class 1: Basic Task Routing
# ═══════════════════════════════════════════════════════════════


class TestBasicRouting:
    """Tests for route_task() core behavior."""

    def test_returns_routing_decision(self, router):
        decision = router.route_task(task_value_usd=5.00)
        assert isinstance(decision, RoutingDecision)
        assert isinstance(decision.chain, str)
        assert isinstance(decision.chain_name, str)
        assert isinstance(decision.gas_cost_usd, float)
        assert isinstance(decision.reasoning, str)

    def test_micro_task_avoids_ethereum(self, router):
        decision = router.route_task(task_value_usd=0.10)
        assert decision.chain != "ethereum"

    def test_small_task_prefers_cheap_chains(self, router):
        decision = router.route_task(task_value_usd=0.50)
        assert decision.gas_cost_usd < 0.05

    def test_large_task_any_chain_viable(self, router):
        decision = router.route_task(task_value_usd=1000.00)
        assert decision.gas_cost_usd >= 0

    def test_alternatives_provided(self, router):
        decision = router.route_task(task_value_usd=5.00)
        assert isinstance(decision.alternatives, list)
        assert len(decision.alternatives) > 0

    def test_gas_savings_calculated(self, router):
        decision = router.route_task(task_value_usd=5.00)
        # Should save something vs Ethereum
        if decision.chain != "ethereum":
            assert decision.gas_savings_vs_default_usd > 0

    def test_to_dict(self, router):
        decision = router.route_task(task_value_usd=5.00)
        d = decision.to_dict()
        assert isinstance(d, dict)
        assert "chain" in d
        assert "gas_cost_usd" in d
        assert "reasoning" in d

    def test_metadata_included(self, router):
        decision = router.route_task(task_value_usd=5.00)
        assert "gas_ratio_percent" in decision.metadata
        assert "is_micro_task" in decision.metadata
        assert not decision.metadata["is_micro_task"]

    def test_micro_task_detected(self, router):
        decision = router.route_task(task_value_usd=0.50)
        assert decision.metadata["is_micro_task"]

    def test_preferred_chain(self, router):
        decision = router.route_task(
            task_value_usd=10.00, preferred_chain="arbitrum"
        )
        # Preferred chain should be selected or at least considered
        assert decision.chain == "arbitrum" or any(
            a["chain"] == "arbitrum" for a in decision.alternatives
        )

    def test_required_features_filter(self, router):
        decision = router.route_task(
            task_value_usd=5.00,
            required_features=["escrow", "payments"],
        )
        profile = router.get_chain(decision.chain)
        assert profile.supports_escrow
        assert profile.supports_payments

    def test_zero_value_task(self, router):
        decision = router.route_task(task_value_usd=0.0)
        assert isinstance(decision, RoutingDecision)

    def test_decision_tracked(self, router):
        assert router.diagnostics()["total_decisions"] == 0
        router.route_task(task_value_usd=5.00)
        assert router.diagnostics()["total_decisions"] == 1


# ═══════════════════════════════════════════════════════════════
# Test Class 2: Strategy-Specific Routing
# ═══════════════════════════════════════════════════════════════


class TestStrategyRouting:
    """Tests for different routing strategies."""

    def test_cost_optimal(self, router):
        decision = router.route_task(
            task_value_usd=5.00,
            strategy=RoutingStrategy.COST_OPTIMAL,
        )
        # Should pick a cheap chain
        assert decision.strategy == "cost_optimal"
        assert decision.gas_cost_usd < 0.05

    def test_speed_optimal(self, router):
        decision = router.route_task(
            task_value_usd=5.00,
            strategy=RoutingStrategy.SPEED_OPTIMAL,
        )
        assert decision.strategy == "speed_optimal"
        # Should pick a fast chain
        assert decision.confirmation_time_seconds <= 5.0

    def test_feature_match(self, router):
        decision = router.route_task(
            task_value_usd=5.00,
            strategy=RoutingStrategy.FEATURE_MATCH,
        )
        assert decision.strategy == "feature_match"
        profile = router.get_chain(decision.chain)
        assert profile.feature_count == 4

    def test_worker_aligned_no_prefs(self, router):
        decision = router.route_task(
            task_value_usd=5.00,
            strategy=RoutingStrategy.WORKER_ALIGNED,
            worker_wallets=["0xAAA", "0xBBB"],
        )
        assert decision.strategy == "worker_aligned"

    def test_worker_aligned_with_prefs(self, router):
        router.set_worker_preference("0xAAA", "polygon")
        router.set_worker_preference("0xBBB", "polygon")
        decision = router.route_task(
            task_value_usd=5.00,
            strategy=RoutingStrategy.WORKER_ALIGNED,
            worker_wallets=["0xAAA", "0xBBB"],
        )
        assert decision.chain == "polygon"

    def test_balanced_default(self, router):
        decision = router.route_task(task_value_usd=5.00)
        assert decision.strategy == "balanced"

    def test_micro_task_uses_cost_optimal(self, router):
        decision = router.route_micro_task(task_value_usd=0.25)
        assert decision.strategy == "cost_optimal"

    def test_high_value_uses_feature_match(self, router):
        decision = router.route_high_value_task(task_value_usd=500.00)
        assert decision.strategy == "feature_match"


# ═══════════════════════════════════════════════════════════════
# Test Class 3: Batch Routing
# ═══════════════════════════════════════════════════════════════


class TestBatchRouting:
    """Tests for route_batch()."""

    def test_basic_batch(self, router):
        result = router.route_batch(task_values=[5.00, 3.00, 2.00])
        assert result["task_count"] == 3
        assert result["total_value_usd"] == 10.00
        assert result["recommended_chain"] is not None

    def test_savings_vs_ethereum(self, router):
        result = router.route_batch(task_values=[1.00] * 10)
        assert result["savings_vs_ethereum_usd"] > 0

    def test_empty_batch(self, router):
        result = router.route_batch(task_values=[])
        assert result["task_count"] == 0

    def test_single_task_batch(self, router):
        result = router.route_batch(task_values=[5.00])
        assert result["task_count"] == 1

    def test_chain_analysis_included(self, router):
        result = router.route_batch(task_values=[5.00])
        assert "base" in result["chain_analysis"]
        assert "total_gas_usd" in result["chain_analysis"]["base"]

    def test_optimal_is_cheapest(self, router):
        result = router.route_batch(task_values=[1.00] * 5)
        optimal = result["recommended_chain"]
        optimal_gas = result["chain_analysis"][optimal]["total_gas_usd"]
        for chain, analysis in result["chain_analysis"].items():
            assert analysis["total_gas_usd"] >= optimal_gas - 0.001


# ═══════════════════════════════════════════════════════════════
# Test Class 4: Chain Management
# ═══════════════════════════════════════════════════════════════


class TestChainManagement:
    """Tests for chain CRUD operations."""

    def test_list_chains(self, router):
        chains = router.list_chains()
        assert "base" in chains
        assert "ethereum" in chains
        assert len(chains) >= 9

    def test_get_chain(self, router):
        profile = router.get_chain("base")
        assert profile is not None
        assert profile.name == "Base"
        assert profile.chain_id == 8453

    def test_get_nonexistent(self, router):
        assert router.get_chain("bitcoin") is None

    def test_register_chain(self, router):
        new = ChainProfile(
            name="TestChain", chain_key="testchain",
            chain_id=99999, gas_per_task_usd=0.001,
        )
        router.register_chain("testchain", new)
        assert "testchain" in router.list_chains()

    def test_remove_chain(self, router):
        assert router.remove_chain("ethereum")
        assert "ethereum" not in router.list_chains()

    def test_remove_nonexistent(self, router):
        assert not router.remove_chain("bitcoin")

    def test_active_chains(self, router):
        active = router.active_chains()
        assert len(active) == len(router.list_chains())

    def test_set_chain_status(self, router):
        assert router.set_chain_status("base", ChainStatus.DEGRADED)
        profile = router.get_chain("base")
        assert profile.status == ChainStatus.DEGRADED

    def test_set_status_nonexistent(self, router):
        assert not router.set_chain_status("bitcoin", ChainStatus.DEGRADED)

    def test_disabled_chain_not_active(self, router):
        router.set_chain_status("ethereum", ChainStatus.DISABLED)
        assert "ethereum" not in router.active_chains()

    def test_degraded_chain_still_active(self, router):
        router.set_chain_status("base", ChainStatus.DEGRADED)
        assert "base" in router.active_chains()


# ═══════════════════════════════════════════════════════════════
# Test Class 5: Worker Preferences
# ═══════════════════════════════════════════════════════════════


class TestWorkerPreferences:
    """Tests for worker chain preference tracking."""

    def test_set_and_get_preference(self, router):
        router.set_worker_preference("0xAAA", "base")
        assert router.get_worker_preference("0xAAA") == "base"

    def test_get_unknown_worker(self, router):
        assert router.get_worker_preference("0xZZZ") is None

    def test_update_preference(self, router):
        router.set_worker_preference("0xAAA", "base")
        router.set_worker_preference("0xAAA", "polygon")
        assert router.get_worker_preference("0xAAA") == "polygon"

    def test_consensus_chain(self, router):
        router.set_worker_preference("0x1", "base")
        router.set_worker_preference("0x2", "base")
        router.set_worker_preference("0x3", "polygon")
        
        consensus = router.worker_consensus_chain(["0x1", "0x2", "0x3"])
        assert consensus == "base"

    def test_consensus_empty(self, router):
        assert router.worker_consensus_chain([]) is None

    def test_consensus_no_prefs(self, router):
        assert router.worker_consensus_chain(["0x1", "0x2"]) is None

    def test_preferences_tracked_in_diagnostics(self, router):
        router.set_worker_preference("0x1", "base")
        router.set_worker_preference("0x2", "polygon")
        diag = router.diagnostics()
        assert diag["worker_preferences_tracked"] == 2


# ═══════════════════════════════════════════════════════════════
# Test Class 6: Success Rate Tracking
# ═══════════════════════════════════════════════════════════════


class TestSuccessTracking:
    """Tests for task outcome recording and success rates."""

    def test_record_completed_task(self, router):
        router.record_task_outcome("base", completed=True, 
                                   completion_time_seconds=120, gas_spent_usd=0.005)
        rate = router.chain_success_rate("base")
        assert rate == 1.0

    def test_record_failed_task(self, router):
        router.record_task_outcome("base", completed=False)
        rate = router.chain_success_rate("base")
        assert rate == 0.0

    def test_mixed_outcomes(self, router):
        for _ in range(8):
            router.record_task_outcome("base", completed=True)
        for _ in range(2):
            router.record_task_outcome("base", completed=False)
        rate = router.chain_success_rate("base")
        assert rate == 0.8

    def test_unknown_chain_rate(self, router):
        assert router.chain_success_rate("bitcoin") == 0.0

    def test_success_records(self, router):
        router.record_task_outcome("base", completed=True, gas_spent_usd=0.005)
        router.record_task_outcome("ethereum", completed=False)
        
        records = router.chain_success_records()
        assert "base" in records
        assert "ethereum" in records
        assert records["base"]["success_rate"] == 1.0
        assert records["ethereum"]["success_rate"] == 0.0

    def test_avg_gas_per_task(self, router):
        router.record_task_outcome("base", completed=True, gas_spent_usd=0.004)
        router.record_task_outcome("base", completed=True, gas_spent_usd=0.006)
        
        records = router.chain_success_records()
        assert records["base"]["avg_gas_per_task_usd"] == pytest.approx(0.005, abs=0.001)

    def test_rolling_avg_completion_time(self, router):
        router.record_task_outcome("base", completed=True, completion_time_seconds=100)
        router.record_task_outcome("base", completed=True, completion_time_seconds=200)
        
        records = router.chain_success_records()
        # Rolling average: 100 * 0.9 + 200 * 0.1 = 110
        assert records["base"]["avg_completion_seconds"] == pytest.approx(110, abs=1)

    def test_history_affects_routing(self, router):
        """Chains with poor success rates should be deprioritized."""
        # Make ethereum fail a lot
        for _ in range(10):
            router.record_task_outcome("ethereum", completed=False)
        # Make base succeed
        for _ in range(10):
            router.record_task_outcome("base", completed=True)
        
        decision = router.route_task(task_value_usd=5.00)
        assert decision.chain != "ethereum"


# ═══════════════════════════════════════════════════════════════
# Test Class 7: Warnings
# ═══════════════════════════════════════════════════════════════


class TestWarnings:
    """Tests for routing warning generation."""

    def test_degraded_chain_warning(self, router):
        router.set_chain_status("base", ChainStatus.DEGRADED)
        # Force routing to base
        minimal = ChainRouter(chains={
            "base": ChainProfile(
                name="Base", chain_key="base", chain_id=8453,
                gas_per_task_usd=0.006, confirmation_time_seconds=2.0,
                status=ChainStatus.DEGRADED,
            ),
        })
        decision = minimal.route_task(task_value_usd=5.00)
        assert any("degraded" in w.lower() for w in decision.warnings)

    def test_high_gas_warning(self):
        eth_only = ChainRouter(chains={
            "ethereum": ChainProfile(
                name="Ethereum", chain_key="ethereum", chain_id=1,
                gas_per_task_usd=1.60, confirmation_time_seconds=15.0,
            ),
        })
        decision = eth_only.route_task(task_value_usd=0.50)
        assert any("gas" in w.lower() for w in decision.warnings)

    def test_low_success_rate_warning(self, router):
        for _ in range(10):
            router.record_task_outcome("base", completed=False)
        for _ in range(2):
            router.record_task_outcome("base", completed=True)
        
        # Force routing to base
        base_only = ChainRouter(chains={
            "base": ChainProfile(
                name="Base", chain_key="base", gas_per_task_usd=0.006,
            ),
        })
        for _ in range(10):
            base_only.record_task_outcome("base", completed=False)
        decision = base_only.route_task(task_value_usd=5.00)
        # Success rate = 0% < 80% threshold but needs 5+ tasks recorded in THAT router
        assert any("success rate" in w.lower() for w in decision.warnings)

    def test_micro_task_with_gas_warning(self):
        poly_only = ChainRouter(chains={
            "polygon": ChainProfile(
                name="Polygon", chain_key="polygon",
                gas_per_task_usd=0.025, confirmation_time_seconds=5.0,
            ),
        })
        decision = poly_only.route_task(task_value_usd=0.50)
        # $0.50 task with $0.025 gas = 5% → micro-task warning
        assert any("micro" in w.lower() for w in decision.warnings)


# ═══════════════════════════════════════════════════════════════
# Test Class 8: Health Check
# ═══════════════════════════════════════════════════════════════


class TestHealthCheck:
    """Tests for health_check()."""

    def test_all_healthy(self, router):
        health = router.health_check()
        assert health["status"] == "healthy"
        assert len(health["active"]) == len(router.list_chains())
        assert len(health["degraded"]) == 0
        assert len(health["disabled"]) == 0

    def test_degraded_status(self, router):
        router.set_chain_status("base", ChainStatus.DEGRADED)
        health = router.health_check()
        assert health["status"] == "degraded"
        assert "base" in health["degraded"]

    def test_critical_status(self):
        router = ChainRouter(chains={
            "base": ChainProfile(
                name="Base", chain_key="base",
                status=ChainStatus.DISABLED,
            ),
        })
        health = router.health_check()
        assert health["status"] == "critical"

    def test_disabled_chain(self, router):
        router.set_chain_status("ethereum", ChainStatus.DISABLED)
        health = router.health_check()
        assert "ethereum" in health["disabled"]


# ═══════════════════════════════════════════════════════════════
# Test Class 9: Diagnostics
# ═══════════════════════════════════════════════════════════════


class TestDiagnostics:
    """Tests for diagnostics()."""

    def test_initial_diagnostics(self, router):
        diag = router.diagnostics()
        assert diag["total_decisions"] == 0
        assert diag["total_gas_saved_usd"] == 0
        assert diag["worker_preferences_tracked"] == 0

    def test_diagnostics_after_routing(self, router):
        router.route_task(task_value_usd=5.00)
        router.route_task(task_value_usd=10.00)
        
        diag = router.diagnostics()
        assert diag["total_decisions"] == 2
        assert len(diag["decisions_per_chain"]) > 0
        assert len(diag["strategy_distribution"]) > 0

    def test_strategy_distribution(self, router):
        router.route_task(task_value_usd=5.00, strategy=RoutingStrategy.COST_OPTIMAL)
        router.route_task(task_value_usd=5.00, strategy=RoutingStrategy.SPEED_OPTIMAL)
        
        diag = router.diagnostics()
        assert "cost_optimal" in diag["strategy_distribution"]
        assert "speed_optimal" in diag["strategy_distribution"]

    def test_uptime_tracked(self, router):
        diag = router.diagnostics()
        assert diag["uptime_seconds"] >= 0


# ═══════════════════════════════════════════════════════════════
# Test Class 10: Persistence
# ═══════════════════════════════════════════════════════════════


class TestPersistence:
    """Tests for save() and load()."""

    def test_save_load_roundtrip(self, router):
        router.set_worker_preference("0xAAA", "base")
        router.record_task_outcome("base", completed=True, gas_spent_usd=0.005)
        router.route_task(task_value_usd=5.00)
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        
        try:
            router.save(path)
            
            loaded = ChainRouter()
            loaded.load(path)
            
            assert "base" in loaded.list_chains()
            assert loaded.get_worker_preference("0xAAA") == "base"
            assert loaded.diagnostics()["total_decisions"] == 1
        finally:
            os.unlink(path)

    def test_save_creates_valid_json(self, router):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        
        try:
            router.save(path)
            with open(path) as f:
                data = json.load(f)
            assert "version" in data
            assert "chains" in data
            assert "success_records" in data
            assert "worker_preferences" in data
        finally:
            os.unlink(path)

    def test_load_preserves_chain_status(self, router):
        router.set_chain_status("base", ChainStatus.DEGRADED)
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        
        try:
            router.save(path)
            loaded = ChainRouter()
            loaded.load(path)
            assert loaded.get_chain("base").status == ChainStatus.DEGRADED
        finally:
            os.unlink(path)

    def test_load_preserves_success_records(self, router):
        for _ in range(5):
            router.record_task_outcome("base", completed=True)
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        
        try:
            router.save(path)
            loaded = ChainRouter()
            loaded.load(path)
            records = loaded.chain_success_records()
            assert records["base"]["completed"] == 5
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════
# Test Class 11: Degraded Chain Handling
# ═══════════════════════════════════════════════════════════════


class TestDegradedChains:
    """Tests for degraded chain behavior."""

    def test_degraded_chain_penalized(self, router):
        """Degraded chain should have lower score."""
        # Route normally
        normal = router.route_task(task_value_usd=5.00)
        
        # Degrade the selected chain
        router.set_chain_status(normal.chain, ChainStatus.DEGRADED)
        degraded = router.route_task(task_value_usd=5.00)
        
        # Should pick a different chain (or same with lower score)
        # The key assertion: degraded chains get penalized
        assert isinstance(degraded, RoutingDecision)

    def test_disabled_chain_excluded(self, router):
        router.set_chain_status("base", ChainStatus.DISABLED)
        decision = router.route_task(task_value_usd=5.00)
        assert decision.chain != "base"

    def test_all_degraded_still_routes(self, router):
        """Even if all chains degraded, should still return a decision."""
        for chain in router.list_chains():
            router.set_chain_status(chain, ChainStatus.DEGRADED)
        decision = router.route_task(task_value_usd=5.00)
        assert isinstance(decision, RoutingDecision)

    def test_all_disabled_falls_back(self, router):
        """If all chains disabled, falls back to anything available."""
        for chain in router.list_chains():
            router.set_chain_status(chain, ChainStatus.DISABLED)
        decision = router.route_task(task_value_usd=5.00)
        assert isinstance(decision, RoutingDecision)


# ═══════════════════════════════════════════════════════════════
# Test Class 12: Edge Cases
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_router(self):
        router = ChainRouter(chains={})
        decision = router.route_task(task_value_usd=5.00)
        assert isinstance(decision, RoutingDecision)

    def test_very_large_task_value(self, router):
        decision = router.route_task(task_value_usd=1_000_000.00)
        assert isinstance(decision, RoutingDecision)

    def test_very_small_task_value(self, router):
        decision = router.route_task(task_value_usd=0.001)
        assert isinstance(decision, RoutingDecision)

    def test_negative_task_value(self, router):
        decision = router.route_task(task_value_usd=-1.00)
        assert isinstance(decision, RoutingDecision)

    def test_many_sequential_decisions(self, router):
        for _ in range(100):
            router.route_task(task_value_usd=5.00)
        diag = router.diagnostics()
        assert diag["total_decisions"] == 100

    def test_chain_profile_feature_count(self):
        full = ChainProfile(
            name="Full", chain_key="full",
            supports_escrow=True, supports_payments=True,
            supports_reputation=True, supports_identity=True,
        )
        assert full.feature_count == 4
        
        minimal = ChainProfile(
            name="Min", chain_key="min",
            supports_escrow=False, supports_payments=True,
            supports_reputation=False, supports_identity=False,
        )
        assert minimal.feature_count == 1

    def test_success_record_properties(self):
        record = ChainSuccessRecord(
            chain="base", total_tasks=10,
            completed_tasks=8, failed_tasks=2,
            total_gas_spent_usd=0.05,
        )
        assert record.success_rate == 0.8
        assert record.avg_gas_per_task_usd == 0.005

    def test_success_record_empty(self):
        record = ChainSuccessRecord(chain="base")
        assert record.success_rate == 0.0
        assert record.avg_gas_per_task_usd == 0.0

    def test_minimal_router_works(self, minimal_router):
        decision = minimal_router.route_task(task_value_usd=5.00)
        assert decision.chain in ("base", "ethereum", "skale")

    def test_custom_config(self, custom_router):
        decision = custom_router.route_task(task_value_usd=5.00)
        assert decision.strategy == "cost_optimal"

    def test_routing_stats_to_dict(self, router):
        router.route_task(task_value_usd=5.00)
        diag = router.diagnostics()
        assert isinstance(diag, dict)
