"""
Tests for SynthesisBridge — Module #79: On-Chain/Off-Chain Reputation Convergence
==================================================================================
"""

import json
import math
import tempfile
import time
from pathlib import Path

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from synthesis_bridge import (
    SynthesisBridge,
    SynthesisConfig,
    SynthesisResult,
    OnChainScore,
    OffChainSignal,
    WorkerReputation,
    SIGNAL_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bridge():
    return SynthesisBridge()

@pytest.fixture
def rich_bridge():
    """Bridge with rich data for one worker."""
    b = SynthesisBridge()
    wallet = "0xRICH"
    now = time.time()
    b.record_onchain_score(wallet, "base", 4.5, 5.0, task_count=20, timestamp=now - 86400)
    b.record_onchain_score(wallet, "ethereum", 4.2, 5.0, task_count=10, timestamp=now - 3600)
    for name, val, conf in [
        ("quality", 0.88, 0.95), ("communication", 0.82, 0.90),
        ("first_pass_rate", 0.91, 0.85), ("reliability", 0.75, 0.80),
        ("trajectory", 0.60, 0.70), ("social_trust", 0.55, 0.65),
        ("geo_proximity", 0.70, 0.80), ("load_balance", 0.65, 0.75),
    ]:
        b.record_offchain_signal(wallet, name, val, conf, timestamp=now - 7200)
    return b, wallet


# ---------------------------------------------------------------------------
# Data Type Tests
# ---------------------------------------------------------------------------

class TestOnChainScore:
    def test_normalized(self):
        s = OnChainScore(chain="base", score=4.0, max_score=5.0, task_count=10)
        assert s.normalized == 0.8

    def test_normalized_clamp(self):
        s = OnChainScore(chain="base", score=6.0, max_score=5.0, task_count=10)
        assert s.normalized == 1.0

    def test_normalized_zero_max(self):
        s = OnChainScore(chain="base", score=3.0, max_score=0.0, task_count=10)
        assert s.normalized == 0.5


class TestOffChainSignal:
    def test_weighted_value(self):
        s = OffChainSignal(signal_name="quality", value=0.8, confidence=0.9)
        assert abs(s.weighted_value - 0.72) < 0.001


class TestWorkerReputation:
    def test_roundtrip(self):
        rep = WorkerReputation(wallet="0xABC")
        rep.onchain_scores.append(
            OnChainScore(chain="base", score=4.0, max_score=5.0, task_count=10, timestamp=1000.0)
        )
        rep.offchain_signals.append(
            OffChainSignal(signal_name="quality", value=0.8, confidence=0.9, timestamp=2000.0)
        )
        rep.platforms = {"onchain:base"}
        d = rep.to_dict()
        restored = WorkerReputation.from_dict(d)
        assert restored.wallet == "0xABC"
        assert len(restored.onchain_scores) == 1
        assert len(restored.offchain_signals) == 1


# ---------------------------------------------------------------------------
# Cold Start Tests
# ---------------------------------------------------------------------------

class TestColdStart:
    def test_unknown_worker(self, bridge):
        r = bridge.signal("0xUNKNOWN")
        assert r.bonus == 0.0
        assert r.confidence == 0.0
        assert r.details.get("cold_start") is True

    def test_onchain_only(self, bridge):
        bridge.record_onchain_score("0xON", "base", 4.5, 5.0, task_count=15)
        r = bridge.signal("0xON")
        assert r.dominant_source == "onchain"

    def test_offchain_only(self, bridge):
        for name in ["quality", "communication", "reliability"]:
            bridge.record_offchain_signal("0xOFF", name, 0.85, 0.9)
        r = bridge.signal("0xOFF")
        assert r.dominant_source == "offchain"


# ---------------------------------------------------------------------------
# Convergence Tests
# ---------------------------------------------------------------------------

class TestConvergence:
    def test_high_convergence(self, bridge):
        w = "0xGOOD"
        now = time.time()
        bridge.record_onchain_score(w, "base", 4.5, 5.0, task_count=20, timestamp=now)
        for name in ["quality", "communication", "reliability", "first_pass_rate"]:
            bridge.record_offchain_signal(w, name, 0.85, 0.9, timestamp=now)
        r = bridge.signal(w)
        assert r.convergence > 0.6
        assert r.bonus > 0

    def test_low_convergence(self, bridge):
        w = "0xSUS"
        now = time.time()
        bridge.record_onchain_score(w, "base", 4.8, 5.0, task_count=15, timestamp=now)
        for name in ["quality", "communication", "reliability", "first_pass_rate"]:
            bridge.record_offchain_signal(w, name, 0.15, 0.9, timestamp=now)
        r = bridge.signal(w)
        assert r.convergence < 0.6


# ---------------------------------------------------------------------------
# Bonus Tests
# ---------------------------------------------------------------------------

class TestBonus:
    def test_positive_good_worker(self, rich_bridge):
        b, w = rich_bridge
        r = b.signal(w)
        assert r.bonus > 0
        assert r.bonus <= b.config.max_bonus

    def test_negative_bad_worker(self, bridge):
        now = time.time()
        bridge.record_onchain_score("0xBAD", "base", 1.0, 5.0, task_count=15, timestamp=now)
        for name in ["quality", "communication", "reliability", "first_pass_rate"]:
            bridge.record_offchain_signal("0xBAD", name, 0.1, 0.9, timestamp=now)
        r = bridge.signal("0xBAD")
        assert r.bonus < 0
        assert r.bonus >= bridge.config.max_penalty

    def test_bounded(self, bridge):
        now = time.time()
        bridge.record_onchain_score("0xS", "base", 5.0, 5.0, task_count=50, timestamp=now)
        for name in ["quality", "communication", "reliability", "first_pass_rate",
                      "trajectory", "social_trust", "load_balance", "geo_proximity"]:
            bridge.record_offchain_signal("0xS", name, 0.99, 1.0, timestamp=now)
        r = bridge.signal("0xS")
        assert r.bonus <= bridge.config.max_bonus


# ---------------------------------------------------------------------------
# Bridge Ingestion Tests
# ---------------------------------------------------------------------------

class TestBridgeIngestion:
    def test_ingest_quality(self, bridge):
        bridge.ingest_from_quality_bridge("0xA", 0.85)
        w = bridge._workers.get("0xA")
        assert w is not None
        assert any(s.signal_name == "quality" for s in w.offchain_signals)

    def test_ingest_fraud(self, bridge):
        bridge.ingest_from_fraud_bridge("0xA", 0.7)
        w = bridge._workers.get("0xA")
        assert any(s.signal_name == "fraud_risk" for s in w.offchain_signals)

    def test_ingest_comm(self, bridge):
        bridge.ingest_from_comm_bridge("0xA", 0.8)
        w = bridge._workers.get("0xA")
        assert any(s.signal_name == "communication" for s in w.offchain_signals)

    def test_ingest_fpq(self, bridge):
        bridge.ingest_from_fpq_bridge("0xA", 0.9)
        w = bridge._workers.get("0xA")
        assert any(s.signal_name == "first_pass_rate" for s in w.offchain_signals)

    def test_ingest_trajectory(self, bridge):
        bridge.ingest_from_trajectory_bridge("0xA", 0.6)
        w = bridge._workers.get("0xA")
        assert any(s.signal_name == "trajectory" for s in w.offchain_signals)

    def test_ingest_erc8004(self, bridge):
        bridge.ingest_from_erc8004("0xA", "base", 4.5, 5.0, 20)
        w = bridge._workers.get("0xA")
        assert len(w.onchain_scores) == 1
        assert w.onchain_scores[0].chain == "base"


# ---------------------------------------------------------------------------
# Portability Tests
# ---------------------------------------------------------------------------

class TestPortability:
    def test_multi_platform(self, rich_bridge):
        b, w = rich_bridge
        r = b.signal(w)
        assert r.portability > 0.3

    def test_cross_type_bonus(self, bridge):
        now = time.time()
        bridge.record_onchain_score("0xX", "base", 4.0, 5.0, task_count=10, timestamp=now)
        bridge.record_offchain_signal("0xX", "quality", 0.8, 0.9, category="behavioral", timestamp=now)
        r = bridge.signal("0xX")
        assert r.portability > 0.3


# ---------------------------------------------------------------------------
# Fleet Analytics Tests
# ---------------------------------------------------------------------------

class TestFleetAnalytics:
    def test_empty_fleet(self, bridge):
        report = bridge.fleet_convergence_report()
        assert report["worker_count"] == 0

    def test_fleet_report_structure(self, rich_bridge):
        b, _ = rich_bridge
        report = b.fleet_convergence_report()
        assert report["worker_count"] == 1
        assert "avg_convergence" in report
        assert "velocity_distribution" in report

    def test_worker_card(self, rich_bridge):
        b, w = rich_bridge
        card = b.worker_reputation_card(w)
        assert card["has_data"] is True
        assert "base" in card["onchain_chains"]

    def test_unknown_card(self, bridge):
        card = bridge.worker_reputation_card("0xNONE")
        assert card["has_data"] is False


# ---------------------------------------------------------------------------
# Health & Persistence Tests
# ---------------------------------------------------------------------------

class TestHealth:
    def test_healthy(self, bridge):
        h = bridge.health()
        assert h["status"] == "healthy"

    def test_with_data(self, rich_bridge):
        b, _ = rich_bridge
        h = b.health()
        assert h["worker_count"] == 1
        assert h["total_onchain_observations"] == 2


class TestPersistence:
    def test_save_load(self, rich_bridge):
        b, w = rich_bridge
        r1 = b.signal(w)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "synth.json"
            b.save(p)
            b2 = SynthesisBridge()
            b2.load(p)
            r2 = b2.signal(w)
        assert r2.dominant_source == r1.dominant_source
        assert abs(r2.onchain_aggregate - r1.onchain_aggregate) < 0.01

    def test_load_missing(self, bridge):
        bridge.load("/nonexistent/path.json")
        assert len(bridge._workers) == 0


# ---------------------------------------------------------------------------
# Coordinator Integration Tests
# ---------------------------------------------------------------------------

class TestCoordinatorIntegration:
    def test_full_synthesis_flow(self, bridge):
        """Simulate coordinator feeding data from all bridges."""
        now = time.time()
        wallet = "0xFULL"
        
        # ERC-8004 on-chain (from registry sync)
        bridge.ingest_from_erc8004(wallet, "base", 4.3, 5.0, 18)
        bridge.ingest_from_erc8004(wallet, "ethereum", 4.1, 5.0, 12)
        
        # Off-chain signals (from various bridges)
        bridge.ingest_from_quality_bridge(wallet, 0.82, 0.9)
        bridge.ingest_from_fraud_bridge(wallet, 0.12, 0.95)
        bridge.ingest_from_comm_bridge(wallet, 0.78, 0.85)
        bridge.ingest_from_fpq_bridge(wallet, 0.88, 0.9)
        bridge.ingest_from_trajectory_bridge(wallet, 0.65, 0.75)
        
        # Compute synthesis
        r = bridge.signal(wallet)
        
        assert r.confidence > 0.3
        assert r.bonus > 0  # Should be positive (good worker)
        assert not r.divergence_alert
        assert len(r.details["onchain_chains"]) == 2

    def test_fraud_divergence_detection(self, bridge):
        """Worker with great on-chain but fraud detected off-chain."""
        wallet = "0xGAMER"
        
        bridge.ingest_from_erc8004(wallet, "base", 4.9, 5.0, 25)
        bridge.ingest_from_fraud_bridge(wallet, 0.85, 0.95)
        bridge.ingest_from_quality_bridge(wallet, 0.20, 0.9)
        bridge.ingest_from_comm_bridge(wallet, 0.15, 0.85)
        bridge.ingest_from_fpq_bridge(wallet, 0.10, 0.9)
        
        r = bridge.signal(wallet)
        assert r.convergence < 0.7
        assert r.bonus < 0.05  # Suppressed despite great on-chain


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_repr(self, bridge):
        assert "SynthesisBridge" in repr(bridge)

    def test_signal_weights_sum(self):
        total = sum(sw["weight"] for sw in SIGNAL_WEIGHTS.values())
        assert 0.9 < total < 1.1

    def test_massive_workers(self, bridge):
        now = time.time()
        for i in range(100):
            w = "0x%04x" % i
            bridge.record_onchain_score(w, "base", 3.0 + i * 0.01, 5.0, i + 1, timestamp=now)
            bridge.record_offchain_signal(w, "quality", 0.5 + i * 0.003, 0.9, timestamp=now)
        h = bridge.health()
        assert h["worker_count"] == 100

    def test_custom_config(self):
        cfg = SynthesisConfig(max_bonus=0.20, max_penalty=-0.15)
        b = SynthesisBridge(config=cfg)
        assert b.config.max_bonus == 0.20
