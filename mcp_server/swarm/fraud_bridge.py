from __future__ import annotations
"""
FraudBridge — Server-Side Behavioral Fraud Intelligence

Module #74 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's FraudDetector (Signal #27).
Detects fraudulent worker behavior through multi-dimensional anomaly
analysis:

  1. GPS spoofing — Impossible velocity between evidence submissions
  2. Evidence recycling — Duplicate evidence hashes (self and cross-worker)
  3. Velocity anomalies — Tasks completed faster than physically possible
  4. Submission rate spikes — Burst patterns exceeding human capacity
  5. Sybil detection — IP hash clustering across wallets
  6. Reputation gaming — Oscillation patterns in reputation scores
  7. Wallet networks — Fund-connected or timing-correlated wallets

Design principle: INNOCENT UNTIL PROVEN GUILTY.
Single anomalies produce warnings. Routing penalties ONLY apply when
multiple independent fraud dimensions converge (noisy-OR model).

Key capabilities:
    1. record_evidence() — Feed evidence events from EM task lifecycle
    2. record_reputation() — Feed reputation changes for oscillation detection
    3. record_wallet_relation() — Feed sybil signals from chain analysis
    4. signal() — Get fraud risk score for a worker
    5. fleet_summary() — Fleet-wide fraud risk assessment
    6. worker_timeline() — Detailed risk event timeline
    7. health() — Status endpoint
    8. save/load — JSON persistence

Integration with SwarmCoordinator:
    coordinator.fraud_bridge.record_evidence(...)
    sig = coordinator.fraud_bridge.signal(worker_id)
    if sig.recommendation == "block":
        reject_worker(worker_id)

Author: Clawd (1 AM Dream Session, April 4 2026)
"""

import json
import hashlib
import logging
import math
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("swarm.fraud_bridge")

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class FraudBridgeConfig:
    """Configuration for the server-side FraudBridge."""

    # Overall penalty scaling
    max_penalty: float = 0.15

    # GPS spoofing thresholds
    gps_velocity_threshold_kmh: float = 900.0
    gps_impossible_velocity_kmh: float = 2000.0
    gps_min_interval_seconds: float = 60.0

    # Evidence recycling
    evidence_hash_window: int = 1000

    # Velocity anomalies
    task_completion_min_seconds: float = 30.0
    submissions_per_hour_threshold: int = 20

    # Sybil detection
    sybil_ip_overlap_threshold: int = 3

    # Convergence
    min_signals_for_penalty: int = 2
    convergence_decay_days: float = 30.0

    # Risk thresholds
    warning_threshold: float = 0.3
    flag_threshold: float = 0.6
    block_threshold: float = 0.85

    # Cold start
    min_events_for_scoring: int = 3


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclass
class EvidenceEvent:
    """Record of a worker's evidence submission."""
    task_id: str
    worker_id: str
    timestamp: float
    evidence_type: str = "photo"
    evidence_hash: str = ""
    gps_lat: float | None = None
    gps_lng: float | None = None
    gps_accuracy_m: float | None = None
    completion_time_seconds: float | None = None
    ip_hash: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ReputationEvent:
    """Record of a reputation change."""
    worker_id: str
    timestamp: float
    old_score: float
    new_score: float
    reason: str = ""


@dataclass
class WalletRelation:
    """Record of wallet relationship signal."""
    wallet_a: str
    wallet_b: str
    relation_type: str
    confidence: float
    timestamp: float
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class RiskFactor:
    """A single detected risk indicator."""
    dimension: str
    severity: float
    description: str
    evidence_count: int
    last_seen: float
    metadata: dict = field(default_factory=dict)


@dataclass
class FraudSignal:
    """Complete fraud assessment for a worker."""
    worker_id: str
    fraud_risk: float
    fraud_penalty: float
    risk_level: str
    risk_factors: list[RiskFactor]
    total_events: int
    confidence: float
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "fraud_risk": round(self.fraud_risk, 4),
            "fraud_penalty": round(self.fraud_penalty, 4),
            "risk_level": self.risk_level,
            "risk_factors": [asdict(rf) for rf in self.risk_factors],
            "total_events": self.total_events,
            "confidence": round(self.confidence, 4),
            "recommendation": self.recommendation,
        }


# ---------------------------------------------------------------------------
# Internal profile
# ---------------------------------------------------------------------------

@dataclass
class _WorkerProfile:
    """Internal accumulator for per-worker fraud signals."""
    worker_id: str
    evidence_events: list[dict] = field(default_factory=list)
    reputation_events: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)

    gps_velocities: list[dict] = field(default_factory=list)
    gps_impossible_count: int = 0
    gps_suspicious_count: int = 0

    evidence_hashes: list[str] = field(default_factory=list)
    duplicate_count: int = 0
    unique_evidence_count: int = 0

    rapid_completions: int = 0
    hourly_bursts: list[dict] = field(default_factory=list)

    oscillation_count: int = 0
    oscillation_magnitude: float = 0.0

    ip_hashes: list[str] = field(default_factory=list)
    related_wallets: list[str] = field(default_factory=list)

    first_seen: float = 0.0
    last_seen: float = 0.0
    total_events: int = 0


# ---------------------------------------------------------------------------
# FraudBridge
# ---------------------------------------------------------------------------

class FraudBridge:
    """
    Server-side behavioral fraud intelligence bridge — Module #74.

    Tracks per-worker behavioral patterns across multiple fraud dimensions
    and produces aggregate risk scores for the SwarmCoordinator.
    """

    def __init__(self, config: FraudBridgeConfig | None = None):
        self.config = config or FraudBridgeConfig()
        self._profiles: dict[str, _WorkerProfile] = {}
        self._global_evidence_index: dict[str, list[str]] = defaultdict(list)
        self._global_ip_index: dict[str, list[str]] = defaultdict(list)

        logger.info(
            f"FraudBridge initialized: max_penalty={self.config.max_penalty}, "
            f"convergence_decay={self.config.convergence_decay_days}d"
        )

    def _get_profile(self, worker_id: str) -> _WorkerProfile:
        if worker_id not in self._profiles:
            self._profiles[worker_id] = _WorkerProfile(worker_id=worker_id)
        return self._profiles[worker_id]

    def _time_decay(self, event_timestamp: float, now: float | None = None) -> float:
        if now is None:
            now = time.time()
        age_days = max(0, (now - event_timestamp)) / 86400.0
        half_life = self.config.convergence_decay_days
        return math.exp(-0.693 * age_days / half_life) if half_life > 0 else 1.0

    # ----- Event recording -----

    def record_evidence(self, event: EvidenceEvent) -> list[RiskFactor]:
        """Record an evidence submission and return newly detected risk factors."""
        profile = self._get_profile(event.worker_id)
        now = event.timestamp or time.time()

        if profile.first_seen == 0:
            profile.first_seen = now
        profile.last_seen = max(profile.last_seen, now)
        profile.total_events += 1

        new_risks: list[RiskFactor] = []
        event_dict = asdict(event)
        profile.evidence_events.append(event_dict)

        if event.gps_lat is not None and event.gps_lng is not None:
            new_risks.extend(self._analyze_gps(profile, event, now))

        if event.evidence_hash:
            new_risks.extend(self._analyze_evidence_hash(profile, event, now))

        if event.completion_time_seconds is not None:
            new_risks.extend(self._analyze_completion_velocity(profile, event, now))

        new_risks.extend(self._analyze_submission_rate(profile, event, now))

        if event.ip_hash:
            new_risks.extend(self._analyze_sybil_signals(profile, event, now))

        return new_risks

    def record_reputation(self, event: ReputationEvent) -> list[RiskFactor]:
        """Record a reputation change and check for oscillation patterns."""
        profile = self._get_profile(event.worker_id)
        now = event.timestamp or time.time()

        if profile.first_seen == 0:
            profile.first_seen = now
        profile.last_seen = max(profile.last_seen, now)

        new_risks: list[RiskFactor] = []
        profile.reputation_events.append(asdict(event))

        if len(profile.reputation_events) >= 3:
            new_risks.extend(self._analyze_reputation_oscillation(profile, now))

        return new_risks

    def record_wallet_relation(self, relation: WalletRelation) -> list[RiskFactor]:
        """Record a wallet relationship signal."""
        new_risks: list[RiskFactor] = []

        for wallet in [relation.wallet_a, relation.wallet_b]:
            profile = self._get_profile(wallet)
            profile.relations.append(asdict(relation))
            other = relation.wallet_b if wallet == relation.wallet_a else relation.wallet_a
            if other not in profile.related_wallets:
                profile.related_wallets.append(other)

        profile_a = self._get_profile(relation.wallet_a)
        if len(profile_a.related_wallets) >= 3:
            new_risks.append(RiskFactor(
                dimension="sybil_network",
                severity=min(1.0, len(profile_a.related_wallets) / 6.0),
                description=(
                    f"Worker {relation.wallet_a[:10]}... connected to "
                    f"{len(profile_a.related_wallets)} wallets via {relation.relation_type}"
                ),
                evidence_count=len(profile_a.relations),
                last_seen=relation.timestamp,
            ))

        return new_risks

    # ----- Analysis dimensions -----

    def _analyze_gps(self, profile: _WorkerProfile, event: EvidenceEvent, now: float) -> list[RiskFactor]:
        risks: list[RiskFactor] = []
        prev_gps = [
            e for e in profile.evidence_events[:-1]
            if e.get("gps_lat") is not None and e.get("gps_lng") is not None
        ]
        if not prev_gps:
            return risks

        prev = prev_gps[-1]
        time_diff = abs(event.timestamp - prev["timestamp"])
        if time_diff < self.config.gps_min_interval_seconds:
            return risks

        distance_km = self._haversine(prev["gps_lat"], prev["gps_lng"], event.gps_lat, event.gps_lng)
        velocity_kmh = (distance_km / time_diff) * 3600.0 if time_diff > 0 else float("inf")

        vel_record = {
            "kmh": velocity_kmh, "distance_km": distance_km,
            "time_diff_s": time_diff, "timestamp": now,
            "from_task": prev.get("task_id", ""), "to_task": event.task_id,
        }
        profile.gps_velocities.append(vel_record)

        if velocity_kmh > self.config.gps_impossible_velocity_kmh:
            profile.gps_impossible_count += 1
            risks.append(RiskFactor(
                dimension="gps_spoofing",
                severity=min(1.0, 0.6 + (profile.gps_impossible_count - 1) * 0.15),
                description=f"Impossible velocity: {velocity_kmh:.0f} km/h ({distance_km:.1f}km in {time_diff:.0f}s)",
                evidence_count=profile.gps_impossible_count, last_seen=now, metadata=vel_record,
            ))
        elif velocity_kmh > self.config.gps_velocity_threshold_kmh:
            profile.gps_suspicious_count += 1
            if profile.gps_suspicious_count >= 2:
                risks.append(RiskFactor(
                    dimension="gps_velocity_anomaly",
                    severity=min(1.0, 0.3 + (profile.gps_suspicious_count - 1) * 0.1),
                    description=f"Suspicious velocity: {velocity_kmh:.0f} km/h (pattern: {profile.gps_suspicious_count})",
                    evidence_count=profile.gps_suspicious_count, last_seen=now, metadata=vel_record,
                ))

        return risks

    def _analyze_evidence_hash(self, profile: _WorkerProfile, event: EvidenceEvent, now: float) -> list[RiskFactor]:
        risks: list[RiskFactor] = []
        h = event.evidence_hash
        if not h:
            return risks

        if h not in profile.evidence_hashes:
            profile.evidence_hashes.append(h)
            profile.unique_evidence_count += 1
        else:
            profile.duplicate_count += 1
            risks.append(RiskFactor(
                dimension="evidence_recycling",
                severity=min(1.0, 0.4 + profile.duplicate_count * 0.15),
                description=f"Reused evidence hash {h[:16]}... ({profile.duplicate_count} duplicates)",
                evidence_count=profile.duplicate_count, last_seen=now,
            ))

        if h in self._global_evidence_index:
            others = [w for w in self._global_evidence_index[h] if w != event.worker_id]
            if others:
                risks.append(RiskFactor(
                    dimension="evidence_cross_recycling",
                    severity=min(1.0, 0.5 + len(others) * 0.2),
                    description=f"Evidence {h[:16]}... also submitted by {len(others)} other worker(s)",
                    evidence_count=len(others) + 1, last_seen=now,
                    metadata={"other_workers": others[:5]},
                ))

        if event.worker_id not in self._global_evidence_index[h]:
            self._global_evidence_index[h].append(event.worker_id)

        return risks

    def _analyze_completion_velocity(self, profile: _WorkerProfile, event: EvidenceEvent, now: float) -> list[RiskFactor]:
        risks: list[RiskFactor] = []
        ct = event.completion_time_seconds
        if ct is None or ct < 0:
            return risks

        if ct < self.config.task_completion_min_seconds:
            profile.rapid_completions += 1
            if profile.rapid_completions >= 2:
                risks.append(RiskFactor(
                    dimension="velocity_anomaly",
                    severity=min(1.0, 0.3 + (profile.rapid_completions - 1) * 0.15),
                    description=f"Task in {ct:.0f}s (threshold: {self.config.task_completion_min_seconds}s). Pattern: {profile.rapid_completions}",
                    evidence_count=profile.rapid_completions, last_seen=now,
                ))

        return risks

    def _analyze_submission_rate(self, profile: _WorkerProfile, event: EvidenceEvent, now: float) -> list[RiskFactor]:
        risks: list[RiskFactor] = []
        one_hour_ago = now - 3600.0
        recent = [e for e in profile.evidence_events if e.get("timestamp", 0) > one_hour_ago]
        count = len(recent)

        if count > self.config.submissions_per_hour_threshold:
            profile.hourly_bursts.append({"hour_start": one_hour_ago, "count": count, "timestamp": now})
            severity = max(0.0, min(1.0, (count / self.config.submissions_per_hour_threshold) - 0.8))
            if severity > 0:
                risks.append(RiskFactor(
                    dimension="rate_anomaly", severity=severity,
                    description=f"{count} submissions/hour (threshold: {self.config.submissions_per_hour_threshold})",
                    evidence_count=count, last_seen=now,
                ))

        return risks

    def _analyze_sybil_signals(self, profile: _WorkerProfile, event: EvidenceEvent, now: float) -> list[RiskFactor]:
        risks: list[RiskFactor] = []
        ip = event.ip_hash
        if not ip:
            return risks

        if ip not in profile.ip_hashes:
            profile.ip_hashes.append(ip)
        if event.worker_id not in self._global_ip_index[ip]:
            self._global_ip_index[ip].append(event.worker_id)

        wallets = self._global_ip_index[ip]
        if len(wallets) >= self.config.sybil_ip_overlap_threshold:
            risks.append(RiskFactor(
                dimension="sybil_ip_cluster",
                severity=min(1.0, (len(wallets) - 2) / 4.0),
                description=f"{len(wallets)} wallets share IP hash {ip[:12]}...",
                evidence_count=len(wallets), last_seen=now,
            ))

        return risks

    def _analyze_reputation_oscillation(self, profile: _WorkerProfile, now: float) -> list[RiskFactor]:
        risks: list[RiskFactor] = []
        events = profile.reputation_events
        if len(events) < 3:
            return risks

        directions = []
        for i in range(1, len(events)):
            delta = events[i]["new_score"] - events[i]["old_score"]
            if abs(delta) > 0.01:
                directions.append(1 if delta > 0 else -1)

        if len(directions) < 2:
            return risks

        changes = 0
        magnitudes = []
        for i in range(1, len(directions)):
            if directions[i] != directions[i - 1]:
                changes += 1
                if i < len(events):
                    magnitudes.append(abs(events[i]["new_score"] - events[i]["old_score"]))

        profile.oscillation_count = changes
        osc_ratio = changes / max(1, len(directions))
        avg_mag = sum(magnitudes) / len(magnitudes) if magnitudes else 0.0
        profile.oscillation_magnitude = avg_mag

        if osc_ratio > 0.6 and avg_mag > 0.05 and changes >= 3:
            severity = min(1.0, osc_ratio * (avg_mag / 0.1))
            risks.append(RiskFactor(
                dimension="reputation_oscillation", severity=severity,
                description=f"Oscillation: {changes} reversals in {len(directions)} updates (avg swing: {avg_mag:.2%})",
                evidence_count=changes, last_seen=now,
            ))

        return risks

    # ----- Primary signal output -----

    def signal(self, worker_id: str) -> FraudSignal:
        """Compute aggregate fraud risk signal for a worker."""
        if worker_id not in self._profiles:
            return FraudSignal(
                worker_id=worker_id, fraud_risk=0.0, fraud_penalty=0.0,
                risk_level="clean", risk_factors=[], total_events=0,
                confidence=0.0, recommendation="route_normally",
            )

        profile = self._profiles[worker_id]
        now = time.time()

        if profile.total_events < self.config.min_events_for_scoring:
            return FraudSignal(
                worker_id=worker_id, fraud_risk=0.0, fraud_penalty=0.0,
                risk_level="clean", risk_factors=[], total_events=profile.total_events,
                confidence=0.0, recommendation="route_normally",
            )

        risk_factors = self._collect_risk_factors(profile, now)

        if not risk_factors:
            confidence = min(1.0, profile.total_events / 20.0)
            return FraudSignal(
                worker_id=worker_id, fraud_risk=0.0, fraud_penalty=0.0,
                risk_level="clean", risk_factors=[], total_events=profile.total_events,
                confidence=confidence, recommendation="route_normally",
            )

        fraud_risk = self._compute_aggregate_risk(risk_factors)
        risk_level = self._risk_level(fraud_risk)
        fraud_penalty = self._compute_penalty(fraud_risk, risk_factors)
        recommendation = self._recommendation(fraud_risk)
        confidence = min(1.0, profile.total_events / 15.0)

        return FraudSignal(
            worker_id=worker_id,
            fraud_risk=round(fraud_risk, 4),
            fraud_penalty=round(fraud_penalty, 4),
            risk_level=risk_level,
            risk_factors=risk_factors,
            total_events=profile.total_events,
            confidence=confidence,
            recommendation=recommendation,
        )

    def _collect_risk_factors(self, profile: _WorkerProfile, now: float) -> list[RiskFactor]:
        factors: list[RiskFactor] = []

        if profile.gps_impossible_count > 0:
            decay = self._time_decay(profile.last_seen, now)
            factors.append(RiskFactor(
                dimension="gps_spoofing",
                severity=min(1.0, 0.6 + (profile.gps_impossible_count - 1) * 0.15) * decay,
                description=f"{profile.gps_impossible_count} impossible GPS velocities",
                evidence_count=profile.gps_impossible_count, last_seen=profile.last_seen,
            ))

        if profile.gps_suspicious_count >= 2:
            decay = self._time_decay(profile.last_seen, now)
            factors.append(RiskFactor(
                dimension="gps_velocity_anomaly",
                severity=min(1.0, 0.3 + (profile.gps_suspicious_count - 1) * 0.1) * decay,
                description=f"{profile.gps_suspicious_count} suspicious GPS velocities",
                evidence_count=profile.gps_suspicious_count, last_seen=profile.last_seen,
            ))

        if profile.duplicate_count > 0:
            decay = self._time_decay(profile.last_seen, now)
            factors.append(RiskFactor(
                dimension="evidence_recycling",
                severity=min(1.0, 0.4 + profile.duplicate_count * 0.15) * decay,
                description=f"{profile.duplicate_count} duplicate evidence submissions",
                evidence_count=profile.duplicate_count, last_seen=profile.last_seen,
            ))

        if profile.rapid_completions >= 2:
            decay = self._time_decay(profile.last_seen, now)
            factors.append(RiskFactor(
                dimension="velocity_anomaly",
                severity=min(1.0, 0.3 + (profile.rapid_completions - 1) * 0.15) * decay,
                description=f"{profile.rapid_completions} impossibly fast completions",
                evidence_count=profile.rapid_completions, last_seen=profile.last_seen,
            ))

        recent_bursts = [b for b in profile.hourly_bursts if self._time_decay(b["timestamp"], now) > 0.3]
        if recent_bursts:
            max_burst = max(b["count"] for b in recent_bursts)
            decay = self._time_decay(recent_bursts[-1]["timestamp"], now)
            sev = min(1.0, (max_burst / self.config.submissions_per_hour_threshold) - 0.8) * decay
            if sev > 0:
                factors.append(RiskFactor(
                    dimension="rate_anomaly", severity=sev,
                    description=f"{len(recent_bursts)} hourly bursts (peak: {max_burst})",
                    evidence_count=len(recent_bursts), last_seen=recent_bursts[-1]["timestamp"],
                ))

        if len(profile.related_wallets) >= 3:
            decay = self._time_decay(profile.last_seen, now)
            factors.append(RiskFactor(
                dimension="sybil_network",
                severity=min(1.0, len(profile.related_wallets) / 6.0) * decay,
                description=f"Connected to {len(profile.related_wallets)} related wallets",
                evidence_count=len(profile.related_wallets), last_seen=profile.last_seen,
            ))

        if profile.oscillation_count >= 3 and profile.oscillation_magnitude > 0.05:
            decay = self._time_decay(profile.last_seen, now)
            osc_ratio = profile.oscillation_count / max(1, len(profile.reputation_events) - 1)
            sev = min(1.0, osc_ratio * (profile.oscillation_magnitude / 0.1)) * decay
            if sev > 0.05:
                factors.append(RiskFactor(
                    dimension="reputation_oscillation", severity=sev,
                    description=f"{profile.oscillation_count} oscillations, avg {profile.oscillation_magnitude:.2%}",
                    evidence_count=profile.oscillation_count, last_seen=profile.last_seen,
                ))

        return [f for f in factors if f.severity >= 0.05]

    def _compute_aggregate_risk(self, factors: list[RiskFactor]) -> float:
        """Noisy-OR: P(fraud) = 1 - ∏(1 - severity_i)"""
        if not factors:
            return 0.0
        p_clean = 1.0
        for f in factors:
            p_clean *= (1.0 - f.severity)
        return min(1.0, max(0.0, 1.0 - p_clean))

    def _compute_penalty(self, fraud_risk: float, factors: list[RiskFactor]) -> float:
        """Penalty requires multi-dimension convergence."""
        dimensions = set(f.dimension for f in factors)
        if len(dimensions) < self.config.min_signals_for_penalty:
            return 0.0
        penalty = -self.config.max_penalty * (fraud_risk ** 1.5)
        return max(-self.config.max_penalty, penalty)

    def _risk_level(self, fraud_risk: float) -> str:
        if fraud_risk < 0.1:
            return "clean"
        elif fraud_risk < self.config.warning_threshold:
            return "low"
        elif fraud_risk < self.config.flag_threshold:
            return "elevated"
        elif fraud_risk < self.config.block_threshold:
            return "high"
        else:
            return "critical"

    def _recommendation(self, fraud_risk: float) -> str:
        if fraud_risk < self.config.warning_threshold:
            return "route_normally"
        elif fraud_risk < self.config.flag_threshold:
            return "monitor"
        elif fraud_risk < self.config.block_threshold:
            return "flag_review"
        else:
            return "block"

    # ----- Fleet operations -----

    def fleet_summary(self) -> dict:
        if not self._profiles:
            return {"total_workers": 0, "risk_distribution": {}, "flagged_workers": [], "top_risks": []}

        risk_dist = {"clean": 0, "low": 0, "elevated": 0, "high": 0, "critical": 0}
        flagged = []
        all_factors: dict[str, int] = defaultdict(int)

        for wid in self._profiles:
            sig = self.signal(wid)
            risk_dist[sig.risk_level] = risk_dist.get(sig.risk_level, 0) + 1
            if sig.fraud_risk >= self.config.warning_threshold:
                flagged.append(sig.to_dict())
            for rf in sig.risk_factors:
                all_factors[rf.dimension] += 1

        flagged.sort(key=lambda x: x["fraud_risk"], reverse=True)
        top_risks = sorted(all_factors.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_workers": len(self._profiles),
            "risk_distribution": risk_dist,
            "flagged_workers": flagged[:20],
            "top_risks": [{"dimension": d, "worker_count": c} for d, c in top_risks],
        }

    def worker_timeline(self, worker_id: str) -> list[dict]:
        if worker_id not in self._profiles:
            return []
        profile = self._profiles[worker_id]
        timeline = []
        for vel in profile.gps_velocities:
            timeline.append({"type": "gps_velocity", "timestamp": vel["timestamp"], "detail": f"{vel['kmh']:.0f} km/h"})
        for burst in profile.hourly_bursts:
            timeline.append({"type": "rate_burst", "timestamp": burst["timestamp"], "detail": f"{burst['count']} submissions/hr"})
        timeline.sort(key=lambda x: x["timestamp"])
        return timeline

    # ----- Health -----

    def health(self) -> dict:
        total_events = sum(p.total_events for p in self._profiles.values())
        flagged = sum(1 for w in self._profiles if self.signal(w).fraud_risk >= self.config.warning_threshold)
        return {
            "status": "operational",
            "total_workers_tracked": len(self._profiles),
            "total_events_processed": total_events,
            "flagged_workers": flagged,
            "global_evidence_hashes": len(self._global_evidence_index),
            "global_ip_clusters": sum(1 for ips in self._global_ip_index.values() if len(ips) >= 2),
            "config": {"max_penalty": self.config.max_penalty, "convergence_decay_days": self.config.convergence_decay_days},
        }

    # ----- Persistence -----

    def save(self, path: str) -> None:
        data = {
            "version": 1, "saved_at": datetime.now(UTC).isoformat(),
            "config": asdict(self.config),
            "profiles": {wid: asdict(p) for wid, p in self._profiles.items()},
            "global_evidence_index": dict(self._global_evidence_index),
            "global_ip_index": dict(self._global_ip_index),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @classmethod
    def load(cls, path: str) -> "FraudBridge":
        with open(path, "r") as f:
            data = json.load(f)
        config = FraudBridgeConfig(**data.get("config", {}))
        bridge = cls(config=config)
        for wid, pdata in data.get("profiles", {}).items():
            bridge._profiles[wid] = _WorkerProfile(**pdata)
        bridge._global_evidence_index = defaultdict(list, data.get("global_evidence_index", {}))
        bridge._global_ip_index = defaultdict(list, data.get("global_ip_index", {}))
        return bridge

    # ----- Utility -----

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
