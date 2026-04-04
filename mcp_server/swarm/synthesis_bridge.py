from __future__ import annotations
"""
SynthesisBridge — Server-Side On-Chain/Off-Chain Reputation Convergence

Module #79 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's ReputationSynthesizer (Signal #32).
Bridges on-chain ERC-8004 reputation with off-chain behavioral signals
from Signals #1-31, producing a unified convergence score.

The Island Problem (Reputation Edition)
========================================

Before Signal #32, the routing system had TWO reputation systems
operating in parallel, never talking to each other:

  ON-CHAIN (ERC-8004):
  - Worker 0xAAA: 4.8/5.0 (20 tasks on Base)
  - Immutable, cross-platform, verifiable
  - But: can be gamed (friendly ratings, sybil reviews)

  OFF-CHAIN (Signals #1-31):
  - Worker 0xAAA: fraud_risk=0.73, quality=0.42
  - Behavioral, nuanced, hard to fake
  - But: platform-specific, no portability

Signal #32 bridges these worlds:
  - When both agree → HIGH CONVERGENCE → trust the combined score
  - When they disagree → DIVERGENCE ALERT → investigate
  - When only one exists → BOOTSTRAP → use available data

The Architecture
================

SynthesisBridge wraps AutoJob's ReputationSynthesizer and adds:
1. Supabase integration for ERC-8004 reputation data
2. Signal ingestion from other bridges (quality, fraud, comm, etc.)
3. Coordinator lifecycle hooks
4. Fleet-wide convergence analytics

Integration with SwarmCoordinator:
    result = coordinator.synthesis_bridge.signal(wallet="0xABC")
    # result.bonus → routing adjustment
    # result.convergence → on-chain/off-chain agreement
    # result.divergence_alert → True if suspicious

Author: Clawd (Dream Session, April 4 2026 — 5AM)
"""

import json
import logging
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("swarm.synthesis_bridge")


# ===========================================================================
# Configuration
# ===========================================================================

@dataclass
class SynthesisConfig:
    """Configuration for the SynthesisBridge."""
    
    # Signal output range
    max_bonus: float = 0.10
    max_penalty: float = -0.08
    
    # Weight balance
    onchain_base_weight: float = 0.40
    offchain_base_weight: float = 0.60
    
    # Convergence thresholds
    strong_convergence: float = 0.85
    moderate_convergence: float = 0.60
    divergence_threshold: float = 0.35
    
    # Velocity detection
    velocity_window_days: int = 30
    velocity_alert_threshold: float = 0.3
    
    # Cold-start handling
    min_onchain_tasks: int = 3
    min_offchain_signals: int = 5
    
    # Time decay
    half_life_days: float = 60.0
    
    # Multi-platform bonus
    multi_platform_bonus: float = 0.03
    
    # Full confidence threshold
    full_confidence_observations: int = 20


# ===========================================================================
# Data Types
# ===========================================================================

@dataclass
class OnChainScore:
    """A single on-chain reputation observation."""
    chain: str
    score: float
    max_score: float
    task_count: int
    timestamp: float = 0.0
    contract: str = ""
    
    @property
    def normalized(self) -> float:
        if self.max_score <= 0:
            return 0.5
        return max(0.0, min(1.0, self.score / self.max_score))


@dataclass
class OffChainSignal:
    """A single off-chain signal observation."""
    signal_name: str
    value: float
    confidence: float
    timestamp: float = 0.0
    category: str = ""
    
    @property
    def weighted_value(self) -> float:
        return self.value * self.confidence


@dataclass
class SynthesisResult:
    """Result of reputation synthesis for one worker."""
    bonus: float
    convergence: float
    onchain_aggregate: float
    offchain_aggregate: float
    confidence: float
    velocity: float
    portability: float
    divergence_alert: bool
    dominant_source: str
    details: dict = field(default_factory=dict)


@dataclass
class WorkerReputation:
    """Complete reputation state for a worker."""
    wallet: str
    onchain_scores: list = field(default_factory=list)
    offchain_signals: list = field(default_factory=list)
    platforms: set = field(default_factory=set)
    score_history: list = field(default_factory=list)
    last_updated: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "wallet": self.wallet,
            "onchain_scores": [asdict(s) for s in self.onchain_scores],
            "offchain_signals": [asdict(s) for s in self.offchain_signals],
            "platforms": sorted(self.platforms),
            "score_history": self.score_history[-50:],
            "last_updated": self.last_updated,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "WorkerReputation":
        rep = cls(wallet=d["wallet"])
        rep.onchain_scores = [OnChainScore(**s) for s in d.get("onchain_scores", [])]
        rep.offchain_signals = [OffChainSignal(**s) for s in d.get("offchain_signals", [])]
        rep.platforms = set(d.get("platforms", []))
        rep.score_history = [tuple(h) for h in d.get("score_history", [])]
        rep.last_updated = d.get("last_updated", 0.0)
        return rep


# ===========================================================================
# Signal Weights
# ===========================================================================

SIGNAL_WEIGHTS = {
    "fraud_risk": {"weight": 0.15, "invert": True},
    "quality": {"weight": 0.14, "invert": False},
    "first_pass_rate": {"weight": 0.12, "invert": False},
    "communication": {"weight": 0.10, "invert": False},
    "trajectory": {"weight": 0.09, "invert": False},
    "reliability": {"weight": 0.09, "invert": False},
    "load_balance": {"weight": 0.08, "invert": False},
    "social_trust": {"weight": 0.07, "invert": False},
    "affinity": {"weight": 0.06, "invert": False},
    "exploration": {"weight": 0.05, "invert": False},
    "geo_proximity": {"weight": 0.05, "invert": False},
}


# ===========================================================================
# Core Engine
# ===========================================================================

class SynthesisBridge:
    """
    Server-side on-chain/off-chain reputation convergence.
    
    Module #79 in the KK V2 Swarm ecosystem.
    Mirrors AutoJob's ReputationSynthesizer (Signal #32).
    """
    
    def __init__(self, config: Optional[SynthesisConfig] = None):
        self.config = config or SynthesisConfig()
        self._workers: dict = {}
        self._signal_weights = dict(SIGNAL_WEIGHTS)
        logger.info(
            "SynthesisBridge initialized (max_bonus=%.2f, max_penalty=%.2f)",
            self.config.max_bonus, self.config.max_penalty,
        )
    
    # --- Recording API ---
    
    def record_onchain_score(
        self,
        wallet: str,
        chain: str,
        score: float,
        max_score: float = 5.0,
        task_count: int = 1,
        contract: str = "",
        timestamp: Optional[float] = None,
    ) -> None:
        """Record an on-chain reputation observation."""
        worker = self._get_or_create(wallet)
        ts = timestamp or time.time()
        obs = OnChainScore(
            chain=chain, score=score, max_score=max_score,
            task_count=task_count, timestamp=ts, contract=contract,
        )
        worker.onchain_scores.append(obs)
        worker.platforms.add("onchain:%s" % chain)
        worker.last_updated = ts
    
    def record_offchain_signal(
        self,
        wallet: str,
        signal_name: str,
        value: float,
        confidence: float = 1.0,
        category: str = "",
        timestamp: Optional[float] = None,
    ) -> None:
        """Record an off-chain signal observation."""
        worker = self._get_or_create(wallet)
        ts = timestamp or time.time()
        obs = OffChainSignal(
            signal_name=signal_name,
            value=max(-1.0, min(1.0, value)),
            confidence=max(0.0, min(1.0, confidence)),
            timestamp=ts, category=category,
        )
        worker.offchain_signals.append(obs)
        if category:
            worker.platforms.add("offchain:%s" % category)
        worker.last_updated = ts
    
    def record_platform(self, wallet: str, platform: str) -> None:
        """Record that a worker is active on a platform."""
        worker = self._get_or_create(wallet)
        worker.platforms.add(platform)
    
    # --- Ingest from other bridges ---
    
    def ingest_from_quality_bridge(self, wallet: str, quality_score: float, confidence: float = 0.9) -> None:
        """Ingest quality signal from QualityBridge."""
        self.record_offchain_signal(wallet, "quality", quality_score, confidence, category="bridge")
    
    def ingest_from_fraud_bridge(self, wallet: str, fraud_risk: float, confidence: float = 0.9) -> None:
        """Ingest fraud risk from FraudBridge."""
        self.record_offchain_signal(wallet, "fraud_risk", fraud_risk, confidence, category="bridge")
    
    def ingest_from_comm_bridge(self, wallet: str, comm_score: float, confidence: float = 0.9) -> None:
        """Ingest communication quality from CommBridge."""
        self.record_offchain_signal(wallet, "communication", comm_score, confidence, category="bridge")
    
    def ingest_from_fpq_bridge(self, wallet: str, fpq_score: float, confidence: float = 0.9) -> None:
        """Ingest first-pass quality from FPQBridge."""
        self.record_offchain_signal(wallet, "first_pass_rate", fpq_score, confidence, category="bridge")
    
    def ingest_from_trajectory_bridge(self, wallet: str, trajectory_score: float, confidence: float = 0.9) -> None:
        """Ingest trajectory from TrajectoryBridge."""
        self.record_offchain_signal(wallet, "trajectory", trajectory_score, confidence, category="bridge")
    
    def ingest_from_erc8004(self, wallet: str, chain: str, score: float,
                             max_score: float = 5.0, task_count: int = 1) -> None:
        """Ingest on-chain reputation from ERC-8004 registry."""
        self.record_onchain_score(wallet, chain, score, max_score, task_count)
    
    # --- Signal API ---
    
    def signal(self, wallet: str) -> SynthesisResult:
        """Compute the reputation convergence signal."""
        worker = self._workers.get(wallet)
        if not worker:
            return self._cold_start_result()
        
        now = time.time()
        
        # Aggregate sources
        onchain_agg = self._aggregate_onchain(worker, now)
        offchain_agg = self._aggregate_offchain(worker, now)
        
        # Confidence
        onchain_conf = self._onchain_confidence(worker)
        offchain_conf = self._offchain_confidence(worker)
        
        # Adaptive weights
        on_w, off_w = self._adaptive_weights(onchain_conf, offchain_conf)
        
        # Convergence
        convergence = self._compute_convergence(onchain_agg, offchain_agg, onchain_conf, offchain_conf)
        
        # Velocity
        velocity = self._compute_velocity(worker, now)
        
        # Portability
        portability = self._compute_portability(worker)
        
        # Unified score
        unified = onchain_agg * on_w + offchain_agg * off_w
        
        # Convergence modifier
        conv_mod = 0.5 + 0.5 * convergence
        modified = 0.5 + (unified - 0.5) * conv_mod
        
        # Portability bonus
        port_bonus = portability * self.config.multi_platform_bonus
        
        # Final bonus
        if modified >= 0.5:
            raw_bonus = (modified - 0.5) * 2.0 * self.config.max_bonus
        else:
            raw_bonus = (modified - 0.5) * 2.0 * abs(self.config.max_penalty)
        
        raw_bonus += port_bonus
        
        # Overall confidence
        overall_conf = max(onchain_conf, offchain_conf) * 0.7 + min(onchain_conf, offchain_conf) * 0.3
        
        final_bonus = raw_bonus * overall_conf
        final_bonus = max(self.config.max_penalty, min(self.config.max_bonus, final_bonus))
        
        # Divergence alert
        div_alert = convergence < self.config.divergence_threshold and overall_conf > 0.5
        
        # Dominant source
        if onchain_conf > offchain_conf + 0.3:
            dominant = "onchain"
        elif offchain_conf > onchain_conf + 0.3:
            dominant = "offchain"
        else:
            dominant = "balanced"
        
        # Record history
        worker.score_history.append((now, unified))
        if len(worker.score_history) > 100:
            worker.score_history = worker.score_history[-50:]
        
        return SynthesisResult(
            bonus=round(final_bonus, 6),
            convergence=round(convergence, 4),
            onchain_aggregate=round(onchain_agg, 4),
            offchain_aggregate=round(offchain_agg, 4),
            confidence=round(overall_conf, 4),
            velocity=round(velocity, 4),
            portability=round(portability, 4),
            divergence_alert=div_alert,
            dominant_source=dominant,
            details={
                "onchain_weight": round(on_w, 3),
                "offchain_weight": round(off_w, 3),
                "onchain_confidence": round(onchain_conf, 3),
                "offchain_confidence": round(offchain_conf, 3),
                "convergence_modifier": round(conv_mod, 3),
                "unified_score": round(unified, 4),
                "modified_score": round(modified, 4),
                "raw_bonus": round(raw_bonus, 6),
                "portability_bonus": round(port_bonus, 6),
                "velocity_alert": abs(velocity) > self.config.velocity_alert_threshold,
                "platforms_count": len(worker.platforms),
                "onchain_chains": list({s.chain for s in worker.onchain_scores}),
                "offchain_signals_count": len(worker.offchain_signals),
            },
        )
    
    # --- Aggregation ---
    
    def _aggregate_onchain(self, worker: WorkerReputation, now: float) -> float:
        if not worker.onchain_scores:
            return 0.5
        
        hl = self.config.half_life_days * 86400
        total_w = 0.0
        w_sum = 0.0
        
        for obs in worker.onchain_scores:
            age = max(0, now - obs.timestamp)
            decay = math.exp(-0.693 * age / hl) if hl > 0 else 1.0
            tw = decay * math.log1p(obs.task_count)
            w_sum += obs.normalized * tw
            total_w += tw
        
        return w_sum / total_w if total_w > 0 else 0.5
    
    def _aggregate_offchain(self, worker: WorkerReputation, now: float) -> float:
        if not worker.offchain_signals:
            return 0.5
        
        hl = self.config.half_life_days * 86400
        
        # Most recent per signal
        latest = {}
        for obs in worker.offchain_signals:
            ex = latest.get(obs.signal_name)
            if not ex or obs.timestamp > ex.timestamp:
                latest[obs.signal_name] = obs
        
        total_w = 0.0
        w_sum = 0.0
        
        for sig_name, obs in latest.items():
            sw = self._signal_weights.get(sig_name, {"weight": 0.05, "invert": False})
            age = max(0, now - obs.timestamp)
            decay = math.exp(-0.693 * age / hl) if hl > 0 else 1.0
            
            value = obs.value
            if sw.get("invert", False):
                value = 1.0 - value
            if value < 0:
                value = (value + 1.0) / 2.0
            
            w = sw["weight"] * decay * obs.confidence
            w_sum += value * w
            total_w += w
        
        return w_sum / total_w if total_w > 0 else 0.5
    
    # --- Confidence ---
    
    def _onchain_confidence(self, worker: WorkerReputation) -> float:
        if not worker.onchain_scores:
            return 0.0
        total = sum(s.task_count for s in worker.onchain_scores)
        chains = len({s.chain for s in worker.onchain_scores})
        task_c = min(1.0, total / self.config.full_confidence_observations)
        chain_b = min(0.2, (chains - 1) * 0.1)
        return min(1.0, task_c + chain_b)
    
    def _offchain_confidence(self, worker: WorkerReputation) -> float:
        if not worker.offchain_signals:
            return 0.0
        unique = len({s.signal_name for s in worker.offchain_signals})
        total = len(worker.offchain_signals)
        diversity = min(1.0, unique / 8)
        volume = min(1.0, total / self.config.full_confidence_observations)
        avg_c = sum(s.confidence for s in worker.offchain_signals) / len(worker.offchain_signals)
        return min(1.0, diversity * 0.4 + volume * 0.3 + avg_c * 0.3)
    
    # --- Weight Adaptation ---
    
    def _adaptive_weights(self, on_c: float, off_c: float):
        if on_c == 0 and off_c == 0:
            return 0.5, 0.5
        if on_c == 0:
            return 0.0, 1.0
        if off_c == 0:
            return 1.0, 0.0
        
        total_b = self.config.onchain_base_weight + self.config.offchain_base_weight
        on_b = self.config.onchain_base_weight / total_b
        off_b = self.config.offchain_base_weight / total_b
        on_a = on_b * on_c
        off_a = off_b * off_c
        t = on_a + off_a
        return (on_a / t, off_a / t) if t else (0.5, 0.5)
    
    # --- Convergence ---
    
    def _compute_convergence(self, on_agg, off_agg, on_c, off_c):
        if on_c == 0 or off_c == 0:
            return 0.5
        dist = abs(on_agg - off_agg)
        conv = math.exp(-3.0 * dist)
        min_c = min(on_c, off_c)
        return max(0.0, min(1.0, conv * min_c + 0.5 * (1.0 - min_c)))
    
    # --- Velocity ---
    
    def _compute_velocity(self, worker: WorkerReputation, now: float) -> float:
        if len(worker.score_history) < 2:
            return 0.0
        cutoff = now - self.config.velocity_window_days * 86400
        recent = [(ts, sc) for ts, sc in worker.score_history if ts >= cutoff]
        if len(recent) < 2:
            return 0.0
        first_ts, first_sc = recent[0]
        last_ts, last_sc = recent[-1]
        dt = last_ts - first_ts
        if dt < 3600:
            return 0.0
        v = (last_sc - first_sc) / (dt / (30 * 86400))
        return max(-1.0, min(1.0, v))
    
    # --- Portability ---
    
    def _compute_portability(self, worker: WorkerReputation) -> float:
        if not worker.platforms:
            return 0.0
        n = len(worker.platforms)
        port = 1.0 - math.exp(-0.35 * n)
        has_on = any(p.startswith("onchain:") for p in worker.platforms)
        has_off = any(p.startswith("offchain:") for p in worker.platforms)
        if has_on and has_off:
            port = min(1.0, port + 0.15)
        return min(1.0, port)
    
    def _cold_start_result(self) -> SynthesisResult:
        return SynthesisResult(
            bonus=0.0, convergence=0.5, onchain_aggregate=0.5,
            offchain_aggregate=0.5, confidence=0.0, velocity=0.0,
            portability=0.0, divergence_alert=False, dominant_source="balanced",
            details={"cold_start": True},
        )
    
    def _get_or_create(self, wallet: str) -> WorkerReputation:
        if wallet not in self._workers:
            self._workers[wallet] = WorkerReputation(wallet=wallet)
        return self._workers[wallet]
    
    # --- Fleet Analytics ---
    
    def fleet_convergence_report(self) -> dict:
        """Fleet-wide convergence analytics."""
        if not self._workers:
            return {
                "worker_count": 0, "avg_convergence": 0.0, "avg_confidence": 0.0,
                "divergence_alerts": 0, "dominant_distribution": {},
                "velocity_distribution": {"improving": 0, "stable": 0, "declining": 0},
            }
        
        results = {w: self.signal(w) for w in self._workers}
        convs = [r.convergence for r in results.values()]
        confs = [r.confidence for r in results.values()]
        dom_dist = {}
        for r in results.values():
            dom_dist[r.dominant_source] = dom_dist.get(r.dominant_source, 0) + 1
        vel_dist = {"improving": 0, "stable": 0, "declining": 0}
        for r in results.values():
            if r.velocity > 0.05:
                vel_dist["improving"] += 1
            elif r.velocity < -0.05:
                vel_dist["declining"] += 1
            else:
                vel_dist["stable"] += 1
        
        return {
            "worker_count": len(self._workers),
            "avg_convergence": sum(convs) / len(convs),
            "avg_confidence": sum(confs) / len(confs),
            "divergence_alerts": sum(1 for r in results.values() if r.divergence_alert),
            "dominant_distribution": dom_dist,
            "velocity_distribution": vel_dist,
            "avg_portability": sum(r.portability for r in results.values()) / len(results),
        }
    
    def worker_reputation_card(self, wallet: str) -> dict:
        """Detailed reputation card for a worker."""
        result = self.signal(wallet)
        worker = self._workers.get(wallet)
        card = {"wallet": wallet, "synthesis": asdict(result), "has_data": worker is not None}
        if worker:
            card.update({
                "onchain_chains": list({s.chain for s in worker.onchain_scores}),
                "total_onchain_tasks": sum(s.task_count for s in worker.onchain_scores),
                "offchain_signal_types": list({s.signal_name for s in worker.offchain_signals}),
                "total_offchain_observations": len(worker.offchain_signals),
                "platforms": sorted(worker.platforms),
            })
        return card
    
    # --- Health ---
    
    def health(self) -> dict:
        """Health check."""
        total_on = sum(len(w.onchain_scores) for w in self._workers.values())
        total_off = sum(len(w.offchain_signals) for w in self._workers.values())
        return {
            "status": "healthy",
            "worker_count": len(self._workers),
            "total_onchain_observations": total_on,
            "total_offchain_observations": total_off,
            "config": {
                "max_bonus": self.config.max_bonus,
                "max_penalty": self.config.max_penalty,
            },
        }
    
    # --- Persistence ---
    
    def save(self, path) -> None:
        path = Path(path)
        data = {
            "version": "1.0",
            "workers": {w: r.to_dict() for w, r in self._workers.items()},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str))
    
    def load(self, path) -> None:
        path = Path(path)
        if not path.exists():
            return
        data = json.loads(path.read_text())
        for w, rd in data.get("workers", {}).items():
            self._workers[w] = WorkerReputation.from_dict(rd)
    
    def __repr__(self) -> str:
        return "SynthesisBridge(workers=%d, max_bonus=%.2f)" % (
            len(self._workers), self.config.max_bonus)
