from __future__ import annotations
"""
TrajectoryBridge — Server-Side Worker Growth Intelligence

Module #77 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's SkillTrajectoryPredictor (Signal #30).
Tracks worker performance trajectories over time and produces routing
signals that favor growing workers and match tasks to their Zone of
Proximal Development (ZPD).

The Static Snapshot Problem
===========================

Signals #1-29 treat workers as frozen snapshots. A worker's current
score is all that matters. But workers aren't static:

  - A newcomer improving 12%/week will surpass veterans in weeks
  - A veteran declining 5%/week will become unreliable within a month
  - A plateaued worker needs novel task types to break through
  - A growing worker benefits most from stretch tasks just above ability

Without trajectory intelligence, the routing system can't distinguish
between "scored 0.7 and improving" vs "scored 0.7 and declining." Both
get identical routing treatment. One is your best future worker; the
other is about to churn.

The Architecture
================

TrajectoryBridge analyzes performance observations over three time
windows (7d, 30d, 90d) using weighted linear regression, then produces:

1. **Trajectory Classification** — improving, stable, declining, plateau, unknown
2. **Growth Rate** — Normalized % change per week
3. **ZPD Range** — Task difficulty range that maximizes learning
4. **Investment Score** — How much to invest in routing tasks to this worker
5. **Fleet Analytics** — Distribution, top growers, at-risk, plateaued

Integration with SwarmCoordinator:
    signal = coordinator.trajectory_bridge.signal(
        worker_id="0xABC",
        task_category="physical_verification",
        task_difficulty=0.75,
    )
    # signal.trajectory_bonus → routing adjustment
    # signal.trajectory → "improving" | "stable" | "declining" | "plateau"
    # signal.zpd_range → (0.72, 0.92) optimal difficulty range
    # signal.investment_score → 0.85

Author: Clawd (Dream Session, April 4 2026)
"""

import json
import logging
import math
import os
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, Tuple, List, Dict

logger = logging.getLogger("swarm.trajectory_bridge")

UTC = timezone.utc


# ===========================================================================
# Configuration
# ===========================================================================

@dataclass
class TrajectoryBridgeConfig:
    """Configuration for the TrajectoryBridge."""

    # Trajectory detection windows (days)
    short_window_days: float = 7.0
    medium_window_days: float = 30.0
    long_window_days: float = 90.0

    # Minimum observations per window
    min_observations_short: int = 3
    min_observations_medium: int = 8
    min_observations_long: int = 15

    # Trajectory thresholds (growth rate per week)
    improving_threshold: float = 0.02   # 2%/week = improving
    declining_threshold: float = -0.02  # -2%/week = declining

    # Plateau detection
    plateau_weeks: float = 4.0
    plateau_variance_max: float = 0.03

    # Zone of Proximal Development
    zpd_lower_pct: float = 0.05
    zpd_upper_pct: float = 0.25
    zpd_growth_expansion: float = 0.5

    # Routing bonuses
    max_growth_bonus: float = 0.08
    max_stretch_bonus: float = 0.04
    max_decline_penalty: float = -0.06
    plateau_break_bonus: float = 0.03

    # Investment scoring weights
    investment_trajectory_weight: float = 0.4
    investment_engagement_weight: float = 0.3
    investment_potential_weight: float = 0.3

    # Decay
    observation_half_life_days: float = 60.0
    max_observations_per_worker: int = 200


# ===========================================================================
# Data Types
# ===========================================================================

@dataclass
class PerformanceObservation:
    """A single performance data point for a worker."""
    score: float
    task_difficulty: float
    category: str
    timestamp: float
    task_id: str = ""
    was_stretch: bool = False
    revision_count: int = 0

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "task_difficulty": self.task_difficulty,
            "category": self.category,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "was_stretch": self.was_stretch,
            "revision_count": self.revision_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PerformanceObservation":
        return cls(
            score=d["score"],
            task_difficulty=d["task_difficulty"],
            category=d["category"],
            timestamp=d["timestamp"],
            task_id=d.get("task_id", ""),
            was_stretch=d.get("was_stretch", False),
            revision_count=d.get("revision_count", 0),
        )


@dataclass
class TrajectoryResult:
    """Full trajectory analysis for a worker in a category."""
    trajectory: str
    growth_rate: float
    confidence: float
    current_level: float
    predicted_score_7d: float
    predicted_score_30d: float
    zpd_range: Tuple[float, float]
    investment_score: float
    plateau_duration_weeks: float
    observation_count: int
    short_trend: float
    medium_trend: float
    long_trend: float

    def to_dict(self) -> dict:
        return {
            "trajectory": self.trajectory,
            "growth_rate": self.growth_rate,
            "confidence": self.confidence,
            "current_level": self.current_level,
            "predicted_score_7d": self.predicted_score_7d,
            "predicted_score_30d": self.predicted_score_30d,
            "zpd_range": list(self.zpd_range),
            "investment_score": self.investment_score,
            "plateau_duration_weeks": self.plateau_duration_weeks,
            "observation_count": self.observation_count,
            "short_trend": self.short_trend,
            "medium_trend": self.medium_trend,
            "long_trend": self.long_trend,
        }


@dataclass
class TrajectorySignal:
    """Routing signal from trajectory analysis."""
    trajectory_bonus: float
    trajectory: str
    growth_rate: float
    confidence: float
    current_level: float
    predicted_score_7d: float
    zpd_range: Tuple[float, float]
    investment_score: float
    is_stretch_task: bool
    stretch_fit: float
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "trajectory_bonus": self.trajectory_bonus,
            "trajectory": self.trajectory,
            "growth_rate": self.growth_rate,
            "confidence": self.confidence,
            "current_level": self.current_level,
            "predicted_score_7d": self.predicted_score_7d,
            "zpd_range": list(self.zpd_range),
            "investment_score": self.investment_score,
            "is_stretch_task": self.is_stretch_task,
            "stretch_fit": self.stretch_fit,
            "recommendation": self.recommendation,
        }


# ===========================================================================
# TrajectoryBridge
# ===========================================================================

class TrajectoryBridge:
    """
    Server-side worker growth intelligence engine.

    Module #77 — counterpart to AutoJob's SkillTrajectoryPredictor (Signal #30).
    """

    def __init__(self, config: Optional[TrajectoryBridgeConfig] = None):
        self.config = config or TrajectoryBridgeConfig()
        self._observations: Dict[str, Dict[str, List[PerformanceObservation]]] = {}
        self._cache: Dict[str, Dict[str, Tuple[TrajectoryResult, float]]] = {}
        self._cache_ttl: float = 300.0

    # -----------------------------------------------------------------------
    # Recording
    # -----------------------------------------------------------------------

    def record_performance(
        self,
        worker_id: str,
        category: str,
        score: float,
        task_difficulty: float = 0.5,
        timestamp: Optional[float] = None,
        task_id: str = "",
        was_stretch: bool = False,
        revision_count: int = 0,
    ) -> None:
        """Record a performance observation."""
        ts = timestamp if timestamp is not None else time.time()
        if isinstance(ts, datetime):
            ts = ts.timestamp()

        obs = PerformanceObservation(
            score=max(0.0, min(1.0, score)),
            task_difficulty=max(0.0, min(1.0, task_difficulty)),
            category=category,
            timestamp=float(ts),
            task_id=task_id,
            was_stretch=was_stretch,
            revision_count=revision_count,
        )

        if worker_id not in self._observations:
            self._observations[worker_id] = {}
        if category not in self._observations[worker_id]:
            self._observations[worker_id][category] = []

        self._observations[worker_id][category].append(obs)

        max_obs = self.config.max_observations_per_worker
        if len(self._observations[worker_id][category]) > max_obs:
            self._observations[worker_id][category] = sorted(
                self._observations[worker_id][category],
                key=lambda o: o.timestamp,
            )[-max_obs:]

        if worker_id in self._cache:
            self._cache[worker_id].pop(category, None)

    # -----------------------------------------------------------------------
    # Trajectory Analysis
    # -----------------------------------------------------------------------

    def analyze_trajectory(
        self,
        worker_id: str,
        category: str = "general",
        now: Optional[float] = None,
    ) -> TrajectoryResult:
        """Analyze a worker's performance trajectory."""
        now = now or time.time()

        if worker_id in self._cache and category in self._cache.get(worker_id, {}):
            cached, cache_time = self._cache[worker_id][category]
            if now - cache_time < self._cache_ttl:
                return cached

        obs_list = self._get_observations(worker_id, category)

        if not obs_list:
            result = self._empty_trajectory()
            self._set_cache(worker_id, category, result, now)
            return result

        obs_list = sorted(obs_list, key=lambda o: o.timestamp)

        # Time-decayed current level
        half_life_s = self.config.observation_half_life_days * 86400
        weighted_sum = 0.0
        weight_sum = 0.0
        for obs in obs_list:
            age = now - obs.timestamp
            decay = math.exp(-0.693 * age / half_life_s) if half_life_s > 0 else 1.0
            weighted_sum += obs.score * decay
            weight_sum += decay

        current_level = weighted_sum / weight_sum if weight_sum > 0 else 0.5

        # Compute trends
        short_trend = self._compute_trend(obs_list, now, self.config.short_window_days)
        medium_trend = self._compute_trend(obs_list, now, self.config.medium_window_days)
        long_trend = self._compute_trend(obs_list, now, self.config.long_window_days)

        growth_rate = self._select_growth_rate(short_trend, medium_trend, long_trend, obs_list, now)
        trajectory, plateau_weeks = self._classify_trajectory(growth_rate, obs_list, now, current_level)
        confidence = self._compute_confidence(obs_list, now)

        predicted_7d = min(1.0, max(0.0, current_level + growth_rate * 1.0))
        predicted_30d = min(1.0, max(0.0, current_level + growth_rate * 4.286))

        zpd = self._compute_zpd(current_level, growth_rate, trajectory)
        investment = self._compute_investment(trajectory, growth_rate, confidence, obs_list, now)

        result = TrajectoryResult(
            trajectory=trajectory,
            growth_rate=growth_rate,
            confidence=confidence,
            current_level=current_level,
            predicted_score_7d=predicted_7d,
            predicted_score_30d=predicted_30d,
            zpd_range=zpd,
            investment_score=investment,
            plateau_duration_weeks=plateau_weeks,
            observation_count=len(obs_list),
            short_trend=short_trend,
            medium_trend=medium_trend,
            long_trend=long_trend,
        )

        self._set_cache(worker_id, category, result, now)
        return result

    # -----------------------------------------------------------------------
    # Routing Signal
    # -----------------------------------------------------------------------

    def signal(
        self,
        worker_id: str,
        task_category: str = "general",
        task_difficulty: float = 0.5,
        now: Optional[float] = None,
    ) -> TrajectorySignal:
        """Produce routing signal for a worker-task pair."""
        now = now or time.time()
        traj = self.analyze_trajectory(worker_id, task_category, now)

        zpd_lower, zpd_upper = traj.zpd_range
        is_stretch = zpd_lower <= task_difficulty <= zpd_upper

        if zpd_upper > zpd_lower:
            zpd_center = (zpd_lower + zpd_upper) / 2
            zpd_width = zpd_upper - zpd_lower
            distance = abs(task_difficulty - zpd_center) / (zpd_width / 2)
            stretch_fit = max(0.0, 1.0 - distance) if is_stretch else 0.0
        else:
            stretch_fit = 0.0

        bonus = self._compute_bonus(traj, is_stretch, stretch_fit, task_difficulty)
        bonus *= traj.confidence

        recommendation = self._generate_recommendation(traj, is_stretch, stretch_fit, task_difficulty)

        return TrajectorySignal(
            trajectory_bonus=bonus,
            trajectory=traj.trajectory,
            growth_rate=traj.growth_rate,
            confidence=traj.confidence,
            current_level=traj.current_level,
            predicted_score_7d=traj.predicted_score_7d,
            zpd_range=traj.zpd_range,
            investment_score=traj.investment_score,
            is_stretch_task=is_stretch,
            stretch_fit=stretch_fit,
            recommendation=recommendation,
        )

    # -----------------------------------------------------------------------
    # Fleet Analytics
    # -----------------------------------------------------------------------

    def fleet_trajectories(
        self,
        category: str = "general",
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Analyze trajectories across the entire fleet."""
        now = now or time.time()

        trajectories = {}
        for worker_id in self._observations:
            traj = self.analyze_trajectory(worker_id, category, now)
            trajectories[worker_id] = traj

        if not trajectories:
            return {
                "total_workers": 0,
                "trajectory_distribution": {},
                "avg_growth_rate": 0.0,
                "top_growers": [],
                "at_risk": [],
                "plateaued": [],
                "fleet_investment_score": 0.0,
            }

        dist: Dict[str, int] = {"improving": 0, "stable": 0, "declining": 0, "plateau": 0, "unknown": 0}
        for t in trajectories.values():
            dist[t.trajectory] = dist.get(t.trajectory, 0) + 1

        known = [t for t in trajectories.values() if t.trajectory != "unknown"]
        avg_growth = statistics.mean(t.growth_rate for t in known) if known else 0.0

        growers = sorted(
            [(wid, t) for wid, t in trajectories.items() if t.trajectory == "improving"],
            key=lambda x: x[1].growth_rate,
            reverse=True,
        )
        top_growers = [
            {"worker_id": wid, "growth_rate": t.growth_rate, "current_level": t.current_level}
            for wid, t in growers[:5]
        ]

        at_risk = [
            {"worker_id": wid, "growth_rate": t.growth_rate, "current_level": t.current_level}
            for wid, t in trajectories.items()
            if t.trajectory == "declining"
        ]

        plateaued = [
            {"worker_id": wid, "current_level": t.current_level, "plateau_weeks": t.plateau_duration_weeks}
            for wid, t in trajectories.items()
            if t.trajectory == "plateau"
        ]

        inv_scores = [t.investment_score for t in trajectories.values()]
        fleet_investment = statistics.mean(inv_scores) if inv_scores else 0.0

        return {
            "total_workers": len(trajectories),
            "trajectory_distribution": dist,
            "avg_growth_rate": avg_growth,
            "top_growers": top_growers,
            "at_risk": at_risk,
            "plateaued": plateaued,
            "fleet_investment_score": fleet_investment,
        }

    def worker_growth_report(
        self,
        worker_id: str,
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive growth report for a single worker."""
        now = now or time.time()

        categories = list(self._observations.get(worker_id, {}).keys())
        if not categories:
            return {
                "worker_id": worker_id,
                "categories": [],
                "overall_trajectory": "unknown",
                "overall_growth_rate": 0.0,
                "total_observations": 0,
                "recommendation": "No performance data available",
            }

        cat_results = {}
        for cat in categories:
            cat_results[cat] = self.analyze_trajectory(worker_id, cat, now).to_dict()

        total_obs = sum(r["observation_count"] for r in cat_results.values())
        if total_obs > 0:
            weighted_growth = sum(
                r["growth_rate"] * r["observation_count"]
                for r in cat_results.values()
            ) / total_obs
        else:
            weighted_growth = 0.0

        if weighted_growth >= self.config.improving_threshold:
            overall = "improving"
        elif weighted_growth <= self.config.declining_threshold:
            overall = "declining"
        else:
            overall = "stable"

        sorted_cats = sorted(cat_results.items(), key=lambda x: x[1]["current_level"], reverse=True)

        return {
            "worker_id": worker_id,
            "categories": cat_results,
            "overall_trajectory": overall,
            "overall_growth_rate": weighted_growth,
            "total_observations": total_obs,
            "strongest_category": sorted_cats[0][0] if sorted_cats else None,
            "weakest_category": sorted_cats[-1][0] if len(sorted_cats) > 1 else None,
            "recommendation": self._growth_recommendation(overall, weighted_growth, cat_results),
        }

    # -----------------------------------------------------------------------
    # Health & Persistence
    # -----------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return health status."""
        total_workers = len(self._observations)
        total_obs = sum(len(obs) for cats in self._observations.values() for obs in cats.values())
        categories = set()
        for cats in self._observations.values():
            categories.update(cats.keys())

        return {
            "status": "healthy",
            "module": "trajectory_bridge",
            "module_number": 77,
            "signal_number": 30,
            "total_workers": total_workers,
            "total_observations": total_obs,
            "categories_tracked": len(categories),
            "cache_entries": sum(len(v) for v in self._cache.values()),
            "config": {
                "short_window_days": self.config.short_window_days,
                "medium_window_days": self.config.medium_window_days,
                "long_window_days": self.config.long_window_days,
                "improving_threshold": self.config.improving_threshold,
                "declining_threshold": self.config.declining_threshold,
            },
        }

    def save(self, path: str) -> None:
        """Save trajectory data to JSON."""
        data = {
            "version": 1,
            "module": "trajectory_bridge",
            "module_number": 77,
            "observations": {},
        }
        for wid, cats in self._observations.items():
            data["observations"][wid] = {}
            for cat, obs_list in cats.items():
                data["observations"][wid][cat] = [o.to_dict() for o in obs_list]

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved trajectory data: %d workers to %s", len(self._observations), path)

    @classmethod
    def load(cls, path: str, config: Optional[TrajectoryBridgeConfig] = None) -> "TrajectoryBridge":
        """Load trajectory data from JSON."""
        with open(path) as f:
            data = json.load(f)

        bridge = cls(config=config)
        for wid, cats in data.get("observations", {}).items():
            bridge._observations[wid] = {}
            for cat, obs_list in cats.items():
                bridge._observations[wid][cat] = [
                    PerformanceObservation.from_dict(o) for o in obs_list
                ]
        logger.info("Loaded trajectory data: %d workers from %s", len(bridge._observations), path)
        return bridge

    # -----------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------

    def _get_observations(self, worker_id: str, category: str) -> List[PerformanceObservation]:
        direct = self._observations.get(worker_id, {}).get(category, [])
        if direct:
            return list(direct)
        if category != "general":
            general = self._observations.get(worker_id, {}).get("general", [])
            if general:
                return list(general)
        all_obs: List[PerformanceObservation] = []
        for cat, obs_list in self._observations.get(worker_id, {}).items():
            all_obs.extend(obs_list)
        return all_obs

    def _compute_trend(
        self, obs_list: List[PerformanceObservation], now: float, window_days: float,
    ) -> float:
        cutoff = now - window_days * 86400
        window_obs = [o for o in obs_list if o.timestamp >= cutoff]
        if len(window_obs) < 2:
            return 0.0

        half_life_s = self.config.observation_half_life_days * 86400
        sum_w = sum_wx = sum_wy = sum_wxx = sum_wxy = 0.0

        for obs in window_obs:
            x = (obs.timestamp - window_obs[0].timestamp) / (7 * 86400)
            y = obs.score
            age = now - obs.timestamp
            w = math.exp(-0.693 * age / half_life_s) if half_life_s > 0 else 1.0
            sum_w += w
            sum_wx += w * x
            sum_wy += w * y
            sum_wxx += w * x * x
            sum_wxy += w * x * y

        denom = sum_w * sum_wxx - sum_wx * sum_wx
        if abs(denom) < 1e-10:
            return 0.0
        return (sum_w * sum_wxy - sum_wx * sum_wy) / denom

    def _select_growth_rate(
        self, short: float, medium: float, long_: float,
        obs_list: List[PerformanceObservation], now: float,
    ) -> float:
        sc = now - self.config.short_window_days * 86400
        mc = now - self.config.medium_window_days * 86400
        lc = now - self.config.long_window_days * 86400

        short_n = sum(1 for o in obs_list if o.timestamp >= sc)
        medium_n = sum(1 for o in obs_list if o.timestamp >= mc)
        long_n = sum(1 for o in obs_list if o.timestamp >= lc)

        if medium_n >= self.config.min_observations_medium:
            return medium
        if short_n >= self.config.min_observations_short:
            return short
        if long_n >= self.config.min_observations_long:
            return long_
        if medium_n >= 2:
            return medium
        if short_n >= 2:
            return short
        return 0.0

    def _classify_trajectory(
        self, growth_rate: float,
        obs_list: List[PerformanceObservation], now: float, current_level: float,
    ) -> Tuple[str, float]:
        if len(obs_list) < 2:
            return "unknown", 0.0

        plateau_weeks = 0.0
        if abs(growth_rate) < self.config.improving_threshold:
            plateau_cutoff = now - self.config.plateau_weeks * 7 * 86400
            plateau_obs = [o for o in obs_list if o.timestamp >= plateau_cutoff]
            if len(plateau_obs) >= 3:
                scores = [o.score for o in plateau_obs]
                variance = statistics.variance(scores) if len(scores) > 1 else 0.0
                if variance <= self.config.plateau_variance_max:
                    oldest_stable = self._find_plateau_start(obs_list, current_level, now)
                    plateau_weeks = (now - oldest_stable) / (7 * 86400)
                    if plateau_weeks >= self.config.plateau_weeks:
                        return "plateau", plateau_weeks

        if growth_rate >= self.config.improving_threshold:
            return "improving", 0.0
        elif growth_rate <= self.config.declining_threshold:
            return "declining", 0.0
        return "stable", 0.0

    def _find_plateau_start(
        self, obs_list: List[PerformanceObservation], current_level: float, now: float,
    ) -> float:
        tolerance = self.config.plateau_variance_max ** 0.5 * 2
        sorted_obs = sorted(obs_list, key=lambda o: o.timestamp, reverse=True)
        plateau_start = now
        for obs in sorted_obs:
            if abs(obs.score - current_level) <= tolerance:
                plateau_start = obs.timestamp
            else:
                break
        return plateau_start

    def _compute_confidence(self, obs_list: List[PerformanceObservation], now: float) -> float:
        if not obs_list:
            return 0.0
        count_factor = min(1.0, math.log(1 + len(obs_list)) / math.log(21))
        latest = max(o.timestamp for o in obs_list)
        recency_factor = math.exp(-0.693 * (now - latest) / (14 * 86400))
        oldest = min(o.timestamp for o in obs_list)
        span_days = (latest - oldest) / 86400
        span_factor = min(1.0, span_days / 30.0)
        return min(1.0, max(0.0, count_factor * 0.4 + recency_factor * 0.35 + span_factor * 0.25))

    def _compute_zpd(
        self, current_level: float, growth_rate: float, trajectory: str,
    ) -> Tuple[float, float]:
        lower_pct = self.config.zpd_lower_pct
        upper_pct = self.config.zpd_upper_pct

        if trajectory == "improving" and growth_rate > 0:
            expansion = min(self.config.zpd_growth_expansion, growth_rate * 10)
            upper_pct += expansion * upper_pct
        if trajectory == "declining":
            upper_pct *= 0.6
            lower_pct = 0.0

        zpd_lower = max(0.0, min(1.0, current_level + lower_pct))
        zpd_upper = max(zpd_lower, min(1.0, current_level + upper_pct))
        return (zpd_lower, zpd_upper)

    def _compute_investment(
        self, trajectory: str, growth_rate: float, confidence: float,
        obs_list: List[PerformanceObservation], now: float,
    ) -> float:
        traj_map = {"improving": 0.9, "stable": 0.5, "plateau": 0.4, "declining": 0.2, "unknown": 0.5}
        traj_score = traj_map.get(trajectory, 0.5)
        if growth_rate > 0:
            traj_score = min(1.0, traj_score + growth_rate * 2)

        engagement = 0.5
        if len(obs_list) >= 2:
            recent_30d = [o for o in obs_list if o.timestamp >= now - 30 * 86400]
            if recent_30d:
                tasks_per_week = len(recent_30d) / 4.286
                engagement = min(1.0, tasks_per_week / 5.0)

        current_scores = [o.score for o in obs_list[-10:]] if obs_list else [0.5]
        avg_score = statistics.mean(current_scores)
        room = 1.0 - avg_score
        potential = room * 0.6 + (0.4 if trajectory == "improving" else 0.0)

        inv = (
            traj_score * self.config.investment_trajectory_weight
            + engagement * self.config.investment_engagement_weight
            + potential * self.config.investment_potential_weight
        )
        return min(1.0, max(0.0, inv * confidence + 0.1 * (1 - confidence)))

    def _compute_bonus(
        self, traj: TrajectoryResult, is_stretch: bool, stretch_fit: float, task_difficulty: float,
    ) -> float:
        cfg = self.config
        if traj.trajectory == "improving":
            base = cfg.max_growth_bonus * 0.5
            return base + (cfg.max_stretch_bonus * stretch_fit if is_stretch else 0.0)
        elif traj.trajectory == "stable":
            return cfg.max_stretch_bonus * stretch_fit * 0.3 if is_stretch else 0.0
        elif traj.trajectory == "plateau":
            return cfg.plateau_break_bonus if (is_stretch or task_difficulty > traj.current_level) else 0.0
        elif traj.trajectory == "declining":
            severity = min(1.0, abs(traj.growth_rate) / 0.10)
            return cfg.max_decline_penalty * severity
        return 0.0

    def _generate_recommendation(
        self, traj: TrajectoryResult, is_stretch: bool, stretch_fit: float, task_difficulty: float,
    ) -> str:
        t = traj.trajectory
        if t == "improving":
            rate = f"+{traj.growth_rate*100:.1f}%/week"
            if is_stretch:
                return f"Growing worker ({rate}), excellent stretch task fit ({stretch_fit:.0%})"
            return f"Growing worker ({rate}), regular task (not in ZPD)"
        elif t == "stable":
            return f"Stable performer at {traj.current_level:.0%} level"
        elif t == "plateau":
            msg = f"Plateaued at {traj.current_level:.0%} for {traj.plateau_duration_weeks:.1f} weeks"
            return msg + (", stretch task may break plateau" if is_stretch else "")
        elif t == "declining":
            return f"Declining worker ({traj.growth_rate*100:.1f}%/week), reduced routing recommended"
        return "Insufficient data for trajectory assessment"

    def _growth_recommendation(
        self, trajectory: str, growth_rate: float, cat_results: dict,
    ) -> str:
        if trajectory == "improving":
            return f"Worker growing at {growth_rate*100:.1f}%/week. Continue routing stretch tasks."
        elif trajectory == "declining":
            return f"Worker declining at {growth_rate*100:.1f}%/week. Route easier tasks or investigate."
        elif trajectory == "stable":
            plateaued = [c for c, r in cat_results.items() if r["trajectory"] == "plateau"]
            if plateaued:
                return f"Plateaued in {', '.join(plateaued)}. Route diverse task types to break through."
            return "Consistent performer. Good for reliability-focused tasks."
        return "Insufficient data for growth recommendation."

    def _empty_trajectory(self) -> TrajectoryResult:
        return TrajectoryResult(
            trajectory="unknown", growth_rate=0.0, confidence=0.0,
            current_level=0.5, predicted_score_7d=0.5, predicted_score_30d=0.5,
            zpd_range=(0.5, 0.75), investment_score=0.5,
            plateau_duration_weeks=0.0, observation_count=0,
            short_trend=0.0, medium_trend=0.0, long_trend=0.0,
        )

    def _set_cache(
        self, worker_id: str, category: str, result: TrajectoryResult, now: float,
    ) -> None:
        if worker_id not in self._cache:
            self._cache[worker_id] = {}
        self._cache[worker_id][category] = (result, now)
