"""
Availability Bridge — AutoJob ↔ Swarm Time-Aware Routing
==========================================================

Bridges the AutoJob AvailabilityPredictor into the EM swarm's routing
decisions. Instead of routing tasks blindly, the swarm can now ask:
"Is this worker likely online right now?" and "When is the best time
to assign this task?"

This completes the intelligence pipeline:
    AutoJob AvailabilityPredictor → AvailabilityBridge → Swarm Coordinator
    (timezone inference + patterns) → (time-weighted rankings) → (routing)

Usage:
    from swarm.availability_bridge import AvailabilityBridge

    bridge = AvailabilityBridge()
    ranked = bridge.time_weighted_ranking(wallets, task)
    schedule = bridge.schedule_task(task, wallets)
    coverage = bridge.pool_coverage(wallets)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Weight for availability in combined scoring (rest goes to skill match)
DEFAULT_AVAILABILITY_WEIGHT = 0.25

# Maximum delay (hours) before we route anyway regardless of availability
MAX_DELAY_HOURS = 4

# Minimum confidence to trust availability prediction
MIN_PREDICTION_CONFIDENCE = 0.3

# Response time thresholds (minutes)
FAST_RESPONSE_THRESHOLD = 20
SLOW_RESPONSE_THRESHOLD = 120


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

@dataclass
class TimeWeightedCandidate:
    """A worker candidate with time-aware scoring."""
    wallet: str
    skill_score: float  # From reputation matcher (0-100)
    availability_score: float  # From availability predictor (0-1)
    combined_score: float  # Weighted blend
    available_now: bool
    estimated_response_minutes: float
    timezone_offset: float
    prediction_confidence: float
    recommendation: str  # "route_now", "delay", "route_anyway"


@dataclass
class ScheduleRecommendation:
    """When and to whom to route a task."""
    route_immediately: bool
    best_worker: Optional[str] = None
    best_time_utc: Optional[int] = None  # Hour (0-23)
    delay_minutes: Optional[float] = None
    alternatives: list = field(default_factory=list)
    reason: str = ""
    coverage_at_optimal_time: int = 0  # Available workers at best time


@dataclass
class PoolCoverage:
    """24-hour availability coverage of the worker pool."""
    total_workers: int
    hours_with_coverage: int  # Hours where >= 1 worker available
    coverage_ratio: float  # hours_with_coverage / 24
    dead_zones: list = field(default_factory=list)  # Hours with 0 workers
    peak_hour_utc: int = 12
    peak_workers: int = 0
    avg_workers_per_hour: float = 0.0


# ---------------------------------------------------------------------------
# Availability Bridge
# ---------------------------------------------------------------------------

class AvailabilityBridge:
    """Bridges AutoJob availability predictions into swarm routing.

    The bridge wraps raw availability data into swarm-friendly formats:
    - Time-weighted candidate rankings
    - Task scheduling recommendations
    - Pool coverage analysis
    - Deadline-aware routing decisions

    All methods are synchronous and work with dicts/primitives (no
    external dependencies required).
    """

    def __init__(
        self,
        availability_weight: float = DEFAULT_AVAILABILITY_WEIGHT,
        max_delay_hours: float = MAX_DELAY_HOURS,
    ):
        self.availability_weight = availability_weight
        self.max_delay_hours = max_delay_hours
        # In-memory availability data cache
        self._availability_data: dict = {}

    def register_availability(
        self,
        wallet: str,
        data: dict,
    ):
        """Register availability data for a worker.

        Expected data format (from AutoJob AvailabilityPredictor):
        {
            "timezone_offset_hours": -5.0,
            "hourly_distribution": [0.01, 0.01, ..., 0.15, ...],
            "active_windows": [...],
            "avg_response_minutes": 25.0,
            "peak_hour": 14,
            "reliability_score": 0.8,
            "total_data_points": 15,
        }
        """
        self._availability_data[wallet] = data

    def register_batch(self, profiles: dict):
        """Register multiple availability profiles at once.

        Args:
            profiles: {wallet: availability_data_dict, ...}
        """
        self._availability_data.update(profiles)

    # -------------------------------------------------------------------
    # Time-Weighted Ranking
    # -------------------------------------------------------------------

    def time_weighted_ranking(
        self,
        candidates: list,
        now: Optional[datetime] = None,
    ) -> list:
        """Rank candidates with availability weighting.

        Args:
            candidates: List of dicts with at minimum:
                {wallet: str, score: float}
                Optionally includes skill_score, match_score, etc.
            now: Current time (for testing)

        Returns:
            List of TimeWeightedCandidate dicts, sorted by combined score
        """
        now = now or datetime.now(UTC)
        results = []

        for candidate in candidates:
            wallet = candidate.get("wallet", "")
            skill_score = candidate.get("score", candidate.get("skill_score", 50.0))

            avail_data = self._availability_data.get(wallet)
            if avail_data:
                avail_score, est_response, available, confidence = (
                    self._compute_availability_score(avail_data, now)
                )
                tz_offset = avail_data.get("timezone_offset_hours", 0.0)
            else:
                # No availability data → neutral score
                avail_score = 0.5
                est_response = 60.0
                available = True  # Assume available when unknown
                confidence = 0.0
                tz_offset = 0.0

            # Combined score
            if confidence >= MIN_PREDICTION_CONFIDENCE:
                combined = (
                    skill_score * (1 - self.availability_weight) +
                    (skill_score * avail_score) * self.availability_weight
                )
            else:
                combined = skill_score  # Don't penalize when data is poor

            # Recommendation
            if available and est_response <= FAST_RESPONSE_THRESHOLD:
                recommendation = "route_now"
            elif available:
                recommendation = "route_now"
            elif est_response <= SLOW_RESPONSE_THRESHOLD:
                recommendation = "route_anyway"
            else:
                recommendation = "delay"

            results.append(TimeWeightedCandidate(
                wallet=wallet,
                skill_score=round(skill_score, 2),
                availability_score=round(avail_score, 3),
                combined_score=round(combined, 2),
                available_now=available,
                estimated_response_minutes=round(est_response, 1),
                timezone_offset=tz_offset,
                prediction_confidence=round(confidence, 3),
                recommendation=recommendation,
            ))

        results.sort(key=lambda r: (-r.combined_score, r.estimated_response_minutes))
        return [asdict(r) for r in results]

    # -------------------------------------------------------------------
    # Task Scheduling
    # -------------------------------------------------------------------

    def schedule_task(
        self,
        task: dict,
        candidate_wallets: list,
        now: Optional[datetime] = None,
    ) -> ScheduleRecommendation:
        """Determine the optimal time to route a task.

        Considers:
        - Worker availability patterns
        - Task deadline (if any)
        - Maximum acceptable delay
        - Number of available workers at each hour
        """
        now = now or datetime.now(UTC)
        current_hour = now.hour

        # Check who's available now
        available_now = []
        for wallet in candidate_wallets:
            avail_data = self._availability_data.get(wallet)
            if avail_data:
                _, est_response, available, confidence = (
                    self._compute_availability_score(avail_data, now)
                )
                if available:
                    available_now.append({
                        "wallet": wallet,
                        "est_response": est_response,
                    })
            else:
                # Unknown availability → assume available
                available_now.append({
                    "wallet": wallet,
                    "est_response": 60.0,
                })

        if available_now:
            # Route to best available worker now
            available_now.sort(key=lambda w: w["est_response"])
            return ScheduleRecommendation(
                route_immediately=True,
                best_worker=available_now[0]["wallet"],
                reason="workers_available_now",
                coverage_at_optimal_time=len(available_now),
                alternatives=[w["wallet"] for w in available_now[1:3]],
            )

        # No one available now — find best future time
        best_hour = None
        best_count = 0

        for offset in range(1, 25):
            check_hour = (current_hour + offset) % 24
            check_time = now + timedelta(hours=offset)

            count = 0
            for wallet in candidate_wallets:
                avail_data = self._availability_data.get(wallet)
                if avail_data:
                    _, _, available, _ = self._compute_availability_score(
                        avail_data, check_time
                    )
                    if available:
                        count += 1

            if count > best_count:
                best_count = count
                best_hour = check_hour

            # Respect max delay
            if offset >= self.max_delay_hours and best_count > 0:
                break

        if best_hour is not None and best_count > 0:
            # Calculate delay
            hours_until = (best_hour - current_hour) % 24
            if hours_until == 0:
                hours_until = 24
            delay_minutes = hours_until * 60

            # If delay exceeds max, route anyway
            if delay_minutes > self.max_delay_hours * 60:
                return ScheduleRecommendation(
                    route_immediately=True,
                    best_worker=candidate_wallets[0] if candidate_wallets else None,
                    best_time_utc=best_hour,
                    delay_minutes=delay_minutes,
                    reason="max_delay_exceeded_routing_anyway",
                    coverage_at_optimal_time=best_count,
                )

            return ScheduleRecommendation(
                route_immediately=False,
                best_time_utc=best_hour,
                delay_minutes=round(delay_minutes, 0),
                reason="delay_for_better_availability",
                coverage_at_optimal_time=best_count,
            )

        # No good time found — route immediately anyway
        return ScheduleRecommendation(
            route_immediately=True,
            best_worker=candidate_wallets[0] if candidate_wallets else None,
            reason="no_availability_data_routing_immediately",
        )

    # -------------------------------------------------------------------
    # Pool Coverage
    # -------------------------------------------------------------------

    def pool_coverage(
        self,
        wallets: list,
        now: Optional[datetime] = None,
    ) -> PoolCoverage:
        """Analyze 24-hour availability coverage of worker pool.

        Returns hourly breakdown of how many workers are expected
        to be online, identifying dead zones and peak times.
        """
        now = now or datetime.now(UTC)
        hourly_counts = []

        for hour in range(24):
            check_time = now.replace(hour=hour, minute=0, second=0)
            count = 0
            for wallet in wallets:
                avail_data = self._availability_data.get(wallet)
                if avail_data:
                    _, _, available, _ = self._compute_availability_score(
                        avail_data, check_time
                    )
                    if available:
                        count += 1
            hourly_counts.append(count)

        dead_zones = [h for h, c in enumerate(hourly_counts) if c == 0]
        hours_covered = sum(1 for c in hourly_counts if c > 0)
        peak_hour = hourly_counts.index(max(hourly_counts))
        peak_count = max(hourly_counts)
        avg_workers = sum(hourly_counts) / 24

        return PoolCoverage(
            total_workers=len(wallets),
            hours_with_coverage=hours_covered,
            coverage_ratio=round(hours_covered / 24, 3),
            dead_zones=dead_zones,
            peak_hour_utc=peak_hour,
            peak_workers=peak_count,
            avg_workers_per_hour=round(avg_workers, 2),
        )

    # -------------------------------------------------------------------
    # Deadline-Aware Routing
    # -------------------------------------------------------------------

    def deadline_aware_route(
        self,
        task: dict,
        candidates: list,
        now: Optional[datetime] = None,
    ) -> dict:
        """Route with deadline awareness.

        If the task has a tight deadline, prioritize available-now workers
        even if their skill match is lower. If deadline is far, optimize
        for the best skill+availability combination.
        """
        now = now or datetime.now(UTC)
        deadline_str = task.get("deadline") or task.get("expires_at")
        hours_remaining = None

        if deadline_str:
            try:
                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                            "%Y-%m-%dT%H:%M:%S+00:00"]:
                    try:
                        dl = datetime.strptime(deadline_str, fmt).replace(tzinfo=UTC)
                        hours_remaining = (dl - now).total_seconds() / 3600
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Get time-weighted rankings
        ranked = self.time_weighted_ranking(candidates, now)

        if hours_remaining is not None and hours_remaining < 2:
            # Urgent: prioritize available-now workers
            urgency = "critical"
            available = [c for c in ranked if c["available_now"]]
            if available:
                return {
                    "urgency": urgency,
                    "hours_remaining": round(hours_remaining, 1),
                    "selected": available[0],
                    "strategy": "fastest_available",
                    "alternatives": available[1:3],
                }
            # No one available but deadline is soon — route to best skill match
            return {
                "urgency": urgency,
                "hours_remaining": round(hours_remaining, 1),
                "selected": ranked[0] if ranked else None,
                "strategy": "best_skill_despite_unavailability",
                "alternatives": ranked[1:3] if ranked else [],
            }
        elif hours_remaining is not None and hours_remaining < 8:
            urgency = "moderate"
        else:
            urgency = "low"

        # Normal routing: use combined score
        return {
            "urgency": urgency,
            "hours_remaining": round(hours_remaining, 1) if hours_remaining else None,
            "selected": ranked[0] if ranked else None,
            "strategy": "optimal_combined_score",
            "alternatives": ranked[1:3] if ranked else [],
        }

    # -------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------

    def _compute_availability_score(
        self,
        avail_data: dict,
        now: datetime,
    ) -> tuple:
        """Compute availability score from stored profile data.

        Returns: (score: float, est_response_min: float, available: bool, confidence: float)
        """
        hourly = avail_data.get("hourly_distribution", [])
        tz_offset = avail_data.get("timezone_offset_hours", 0.0)
        reliability = avail_data.get("reliability_score", 0.5)
        data_points = avail_data.get("total_data_points", 0)

        if not hourly or len(hourly) != 24:
            return (0.5, 60.0, True, 0.0)

        # Current local hour
        local_hour = int((now.hour + tz_offset) % 24)
        activity = hourly[local_hour]
        peak = max(hourly) if hourly else 0

        if peak <= 0:
            return (0.5, 60.0, True, 0.0)

        ratio = activity / peak

        # Score: 0-1 based on how active this hour is
        score = min(1.0, ratio)

        # Estimated response time
        if ratio >= 0.6:
            est_response = 15.0
        elif ratio >= 0.3:
            t = (ratio - 0.3) / 0.3
            est_response = 45.0 + t * (15.0 - 45.0)
        elif ratio >= 0.1:
            est_response = 45.0
        else:
            est_response = 180.0

        # Available if score is reasonable
        available = ratio >= 0.3

        # Confidence from data points and reliability
        data_confidence = min(1.0, data_points / 15)
        confidence = data_confidence * 0.5 + reliability * 0.5

        return (score, est_response, available, confidence)

    # -------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------

    def get_registered_count(self) -> int:
        return len(self._availability_data)

    def get_registered_wallets(self) -> list:
        return list(self._availability_data.keys())

    def to_dict(self) -> dict:
        return {
            "registered_workers": len(self._availability_data),
            "availability_weight": self.availability_weight,
            "max_delay_hours": self.max_delay_hours,
        }
