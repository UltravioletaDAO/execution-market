"""
Execution Market Task Bundles (NOW-136, NOW-137)

Implements task bundling for efficiency:
- Group 5-10 similar tasks in a zone
- Bundle completion bonus (10% extra)
- Optimized routing
- Shared deadlines

Benefits:
- Workers: Higher earnings per hour
- Agents: Bulk pricing discounts
- Platform: Better task completion rates
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import math


class BundleStatus(str, Enum):
    """Status of a task bundle."""
    DRAFT = "draft"              # Being assembled
    PUBLISHED = "published"      # Available for workers
    ASSIGNED = "assigned"        # Worker accepted
    IN_PROGRESS = "in_progress"  # Worker started
    COMPLETED = "completed"      # All tasks done
    PARTIAL = "partial"          # Some tasks done, timed out
    CANCELLED = "cancelled"


class BundleType(str, Enum):
    """Types of task bundles."""
    ZONE_RECON = "zone_recon"      # Multiple observations in area
    PRICE_SWEEP = "price_sweep"    # Price checks at multiple stores
    DELIVERY_ROUTE = "delivery_route"  # Multi-stop deliveries
    TRIAL_BATCH = "trial_batch"    # Multiple mystery shops
    MIXED = "mixed"                # Mixed task types in zone


@dataclass
class GeoZone:
    """
    Geographic zone for bundling.

    Attributes:
        zone_id: Unique zone identifier
        name: Human-readable name
        center_lat: Center latitude
        center_lon: Center longitude
        radius_km: Radius in kilometers
        polygon: Optional polygon coordinates for irregular zones
    """
    zone_id: str
    name: str
    center_lat: float
    center_lon: float
    radius_km: float
    polygon: Optional[List[Tuple[float, float]]] = None

    def contains_point(self, lat: float, lon: float) -> bool:
        """Check if a point is within this zone."""
        # Simple circle check
        distance = self._haversine_distance(
            self.center_lat, self.center_lon, lat, lon
        )
        return distance <= self.radius_km

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        R = 6371  # Earth's radius in km
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "center": {"lat": self.center_lat, "lon": self.center_lon},
            "radius_km": self.radius_km,
            "polygon": self.polygon,
        }


@dataclass
class BundleTask:
    """
    A task within a bundle.

    Attributes:
        task_id: Original task ID
        sequence: Suggested order in bundle
        latitude: Task location latitude
        longitude: Task location longitude
        task_type: Type of task
        bounty_usd: Individual task bounty
        status: Task status
        completed_at: When completed
        distance_from_prev_km: Distance from previous task
    """
    task_id: str
    sequence: int
    latitude: float
    longitude: float
    task_type: str
    bounty_usd: Decimal
    status: str = "pending"
    completed_at: Optional[datetime] = None
    distance_from_prev_km: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "sequence": self.sequence,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "task_type": self.task_type,
            "bounty_usd": str(self.bounty_usd),
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "distance_from_prev_km": round(self.distance_from_prev_km, 2),
        }


@dataclass
class BundleBonus:
    """
    Bonus configuration for bundle completion.

    Attributes:
        completion_threshold: Minimum % tasks to complete for bonus
        bonus_percentage: Bonus as % of total bounty
        time_bonus_percentage: Extra bonus for early completion
        time_bonus_threshold_hours: Hours early for time bonus
    """
    completion_threshold: float = 100.0  # Must complete all for bonus
    bonus_percentage: float = 10.0       # 10% bonus
    time_bonus_percentage: float = 5.0   # Extra 5% for early
    time_bonus_threshold_hours: float = 2.0  # 2 hours early

    def calculate_bonus(
        self,
        base_total: Decimal,
        tasks_completed: int,
        total_tasks: int,
        hours_early: float = 0.0,
    ) -> Decimal:
        """
        Calculate bonus earned.

        Args:
            base_total: Total bounty of all tasks
            tasks_completed: Number of tasks completed
            total_tasks: Total tasks in bundle
            hours_early: Hours completed before deadline

        Returns:
            Bonus amount in USD
        """
        completion_rate = (tasks_completed / total_tasks) * 100 if total_tasks > 0 else 0

        if completion_rate < self.completion_threshold:
            return Decimal("0")

        # Base completion bonus
        bonus = base_total * (Decimal(str(self.bonus_percentage)) / 100)

        # Time bonus if completed early
        if hours_early >= self.time_bonus_threshold_hours:
            time_bonus = base_total * (Decimal(str(self.time_bonus_percentage)) / 100)
            bonus += time_bonus

        return bonus.quantize(Decimal("0.01"))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "completion_threshold": self.completion_threshold,
            "bonus_percentage": self.bonus_percentage,
            "time_bonus_percentage": self.time_bonus_percentage,
            "time_bonus_threshold_hours": self.time_bonus_threshold_hours,
        }


@dataclass
class TaskBundle:
    """
    A bundle of related tasks.

    Attributes:
        id: Unique bundle identifier
        bundle_type: Type of bundle
        zone: Geographic zone
        tasks: List of tasks in bundle
        status: Bundle status
        bonus_config: Bonus configuration
        total_bounty_usd: Sum of all task bounties
        bonus_usd: Earned bonus amount
        estimated_duration_minutes: Estimated completion time
        deadline: When bundle must be completed
        assigned_worker: Assigned worker ID
        created_at: When bundle was created
        started_at: When worker started
        completed_at: When bundle was completed
        metadata: Additional bundle data
    """
    id: str
    bundle_type: BundleType
    zone: GeoZone
    tasks: List[BundleTask]
    status: BundleStatus = BundleStatus.DRAFT
    bonus_config: BundleBonus = field(default_factory=BundleBonus)
    total_bounty_usd: Decimal = Decimal("0")
    bonus_usd: Decimal = Decimal("0")
    estimated_duration_minutes: int = 0
    deadline: Optional[datetime] = None
    assigned_worker: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate totals after initialization."""
        if self.total_bounty_usd == Decimal("0"):
            self._calculate_totals()

    def _calculate_totals(self):
        """Calculate total bounty and estimated duration."""
        self.total_bounty_usd = sum(t.bounty_usd for t in self.tasks)

        # Estimate duration: 15 min per task + travel time
        travel_time = sum(t.distance_from_prev_km for t in self.tasks) * 3  # 3 min/km
        task_time = len(self.tasks) * 15
        self.estimated_duration_minutes = int(task_time + travel_time)

    @property
    def total_with_bonus(self) -> Decimal:
        """Total payment including potential bonus."""
        max_bonus = self.bonus_config.calculate_bonus(
            self.total_bounty_usd,
            len(self.tasks),
            len(self.tasks),
            self.bonus_config.time_bonus_threshold_hours,  # Max bonus
        )
        return self.total_bounty_usd + max_bonus

    @property
    def tasks_completed(self) -> int:
        """Count of completed tasks."""
        return sum(1 for t in self.tasks if t.status == "completed")

    @property
    def completion_progress(self) -> float:
        """Completion percentage."""
        if not self.tasks:
            return 0.0
        return (self.tasks_completed / len(self.tasks)) * 100

    def get_next_task(self) -> Optional[BundleTask]:
        """Get next incomplete task in sequence."""
        for task in sorted(self.tasks, key=lambda t: t.sequence):
            if task.status != "completed":
                return task
        return None

    def mark_task_completed(self, task_id: str) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task to mark complete

        Returns:
            True if task was found and marked
        """
        for task in self.tasks:
            if task.task_id == task_id:
                task.status = "completed"
                task.completed_at = datetime.now(UTC)

                # Check if bundle is complete
                if self.tasks_completed == len(self.tasks):
                    self._complete_bundle()

                return True
        return False

    def _complete_bundle(self):
        """Mark bundle as completed and calculate bonus."""
        self.status = BundleStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

        # Calculate time bonus eligibility
        hours_early = 0.0
        if self.deadline and self.started_at:
            time_remaining = self.deadline - self.completed_at
            hours_early = max(0, time_remaining.total_seconds() / 3600)

        self.bonus_usd = self.bonus_config.calculate_bonus(
            self.total_bounty_usd,
            self.tasks_completed,
            len(self.tasks),
            hours_early,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "bundle_type": self.bundle_type.value,
            "zone": self.zone.to_dict(),
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status.value,
            "bonus_config": self.bonus_config.to_dict(),
            "total_bounty_usd": str(self.total_bounty_usd),
            "bonus_usd": str(self.bonus_usd),
            "total_with_bonus": str(self.total_with_bonus),
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "assigned_worker": self.assigned_worker,
            "tasks_completed": self.tasks_completed,
            "completion_progress": round(self.completion_progress, 1),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class BundleOptimizer:
    """
    Optimizes task bundles for efficient completion.
    """

    @staticmethod
    def calculate_distances(tasks: List[BundleTask]) -> List[BundleTask]:
        """
        Calculate distances between sequential tasks.

        Args:
            tasks: List of tasks to calculate distances for

        Returns:
            Tasks with distance_from_prev_km populated
        """
        if not tasks:
            return tasks

        # Sort by sequence
        sorted_tasks = sorted(tasks, key=lambda t: t.sequence)

        for i, task in enumerate(sorted_tasks):
            if i == 0:
                task.distance_from_prev_km = 0.0
            else:
                prev = sorted_tasks[i - 1]
                task.distance_from_prev_km = GeoZone._haversine_distance(
                    prev.latitude, prev.longitude,
                    task.latitude, task.longitude,
                )

        return sorted_tasks

    @staticmethod
    def optimize_sequence(tasks: List[BundleTask]) -> List[BundleTask]:
        """
        Optimize task sequence to minimize travel distance.
        Uses a simple nearest-neighbor heuristic.

        Args:
            tasks: List of tasks to optimize

        Returns:
            Tasks with optimized sequence numbers
        """
        if len(tasks) <= 2:
            return tasks

        # Start from first task
        remaining = tasks.copy()
        optimized = [remaining.pop(0)]

        while remaining:
            current = optimized[-1]
            # Find nearest task
            nearest_idx = 0
            nearest_dist = float('inf')

            for i, task in enumerate(remaining):
                dist = GeoZone._haversine_distance(
                    current.latitude, current.longitude,
                    task.latitude, task.longitude,
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            optimized.append(remaining.pop(nearest_idx))

        # Update sequence numbers
        for i, task in enumerate(optimized):
            task.sequence = i + 1

        return BundleOptimizer.calculate_distances(optimized)

    @staticmethod
    def estimate_route_time(tasks: List[BundleTask], avg_speed_kmh: float = 20.0) -> int:
        """
        Estimate total time to complete a route.

        Args:
            tasks: List of tasks
            avg_speed_kmh: Average travel speed (default 20 km/h for urban)

        Returns:
            Estimated minutes to complete
        """
        if not tasks:
            return 0

        # Calculate total distance
        total_distance = sum(t.distance_from_prev_km for t in tasks)

        # Travel time in minutes
        travel_minutes = (total_distance / avg_speed_kmh) * 60

        # Add task time (15 min per task average)
        task_minutes = len(tasks) * 15

        return int(travel_minutes + task_minutes)


class BundleFactory:
    """
    Factory for creating task bundles.
    """

    # Default bundle size limits
    MIN_TASKS = 3
    MAX_TASKS = 10
    DEFAULT_BONUS_PCT = 10.0

    @classmethod
    def create_zone_recon_bundle(
        cls,
        zone: GeoZone,
        tasks: List[Dict[str, Any]],
        deadline_hours: int = 4,
        bonus_percentage: float = DEFAULT_BONUS_PCT,
    ) -> TaskBundle:
        """
        Create a zone reconnaissance bundle.

        Args:
            zone: Geographic zone
            tasks: List of task dicts with id, lat, lon, type, bounty
            deadline_hours: Hours to complete
            bonus_percentage: Completion bonus percentage

        Returns:
            Configured TaskBundle
        """
        if len(tasks) < cls.MIN_TASKS:
            raise ValueError(f"Bundle requires at least {cls.MIN_TASKS} tasks")
        if len(tasks) > cls.MAX_TASKS:
            raise ValueError(f"Bundle cannot exceed {cls.MAX_TASKS} tasks")

        bundle_tasks = []
        for i, task in enumerate(tasks):
            bundle_tasks.append(BundleTask(
                task_id=task.get("id", str(uuid4())),
                sequence=i + 1,
                latitude=task["latitude"],
                longitude=task["longitude"],
                task_type=task.get("type", "recon"),
                bounty_usd=Decimal(str(task.get("bounty", "2.00"))),
            ))

        # Optimize route
        optimized_tasks = BundleOptimizer.optimize_sequence(bundle_tasks)
        estimated_time = BundleOptimizer.estimate_route_time(optimized_tasks)

        bonus_config = BundleBonus(
            completion_threshold=100.0,
            bonus_percentage=bonus_percentage,
        )

        return TaskBundle(
            id=str(uuid4()),
            bundle_type=BundleType.ZONE_RECON,
            zone=zone,
            tasks=optimized_tasks,
            bonus_config=bonus_config,
            estimated_duration_minutes=estimated_time,
            deadline=datetime.now(UTC) + timedelta(hours=deadline_hours),
            metadata={
                "original_task_count": len(tasks),
                "optimized_route": True,
            }
        )

    @classmethod
    def create_price_sweep_bundle(
        cls,
        zone: GeoZone,
        stores: List[Dict[str, Any]],
        items_to_check: List[str],
        deadline_hours: int = 6,
        bonus_percentage: float = DEFAULT_BONUS_PCT,
    ) -> TaskBundle:
        """
        Create a price sweep bundle (check prices at multiple stores).

        Args:
            zone: Geographic zone
            stores: List of store dicts with name, lat, lon
            items_to_check: Items to price check at each store
            deadline_hours: Hours to complete
            bonus_percentage: Completion bonus percentage

        Returns:
            Configured TaskBundle
        """
        if len(stores) < cls.MIN_TASKS:
            raise ValueError(f"Bundle requires at least {cls.MIN_TASKS} stores")

        bundle_tasks = []
        base_bounty = Decimal("2.50") + Decimal("0.50") * (len(items_to_check) - 1)

        for i, store in enumerate(stores):
            bundle_tasks.append(BundleTask(
                task_id=str(uuid4()),
                sequence=i + 1,
                latitude=store["latitude"],
                longitude=store["longitude"],
                task_type="price_check",
                bounty_usd=base_bounty,
            ))

        optimized_tasks = BundleOptimizer.optimize_sequence(bundle_tasks)
        estimated_time = BundleOptimizer.estimate_route_time(optimized_tasks)

        bonus_config = BundleBonus(
            completion_threshold=100.0,
            bonus_percentage=bonus_percentage,
        )

        return TaskBundle(
            id=str(uuid4()),
            bundle_type=BundleType.PRICE_SWEEP,
            zone=zone,
            tasks=optimized_tasks,
            bonus_config=bonus_config,
            estimated_duration_minutes=estimated_time,
            deadline=datetime.now(UTC) + timedelta(hours=deadline_hours),
            metadata={
                "items_to_check": items_to_check,
                "store_count": len(stores),
            }
        )

    @classmethod
    def auto_bundle_tasks(
        cls,
        tasks: List[Dict[str, Any]],
        max_radius_km: float = 5.0,
        min_bundle_size: int = 3,
        max_bundle_size: int = 10,
    ) -> List[TaskBundle]:
        """
        Automatically group tasks into bundles based on location.

        Args:
            tasks: List of task dicts with id, lat, lon, type, bounty
            max_radius_km: Maximum zone radius
            min_bundle_size: Minimum tasks per bundle
            max_bundle_size: Maximum tasks per bundle

        Returns:
            List of TaskBundles
        """
        if not tasks:
            return []

        bundles = []
        remaining = tasks.copy()

        while len(remaining) >= min_bundle_size:
            # Start with first remaining task as center
            seed = remaining[0]
            zone_tasks = [seed]
            remaining.remove(seed)

            # Find nearby tasks
            for task in remaining.copy():
                distance = GeoZone._haversine_distance(
                    seed["latitude"], seed["longitude"],
                    task["latitude"], task["longitude"],
                )
                if distance <= max_radius_km and len(zone_tasks) < max_bundle_size:
                    zone_tasks.append(task)
                    remaining.remove(task)

            # Only create bundle if we have enough tasks
            if len(zone_tasks) >= min_bundle_size:
                # Calculate zone center
                avg_lat = sum(t["latitude"] for t in zone_tasks) / len(zone_tasks)
                avg_lon = sum(t["longitude"] for t in zone_tasks) / len(zone_tasks)

                zone = GeoZone(
                    zone_id=str(uuid4()),
                    name=f"Auto-zone {len(bundles) + 1}",
                    center_lat=avg_lat,
                    center_lon=avg_lon,
                    radius_km=max_radius_km,
                )

                bundle = cls.create_zone_recon_bundle(zone, zone_tasks)
                bundles.append(bundle)

        return bundles


# Convenience functions
def create_bundle(
    zone: GeoZone,
    tasks: List[Dict[str, Any]],
    bundle_type: BundleType = BundleType.ZONE_RECON,
    **kwargs,
) -> TaskBundle:
    """
    Create a bundle using appropriate factory method.

    Args:
        zone: Geographic zone
        tasks: List of tasks
        bundle_type: Type of bundle
        **kwargs: Additional arguments

    Returns:
        Configured TaskBundle
    """
    if bundle_type == BundleType.PRICE_SWEEP:
        return BundleFactory.create_price_sweep_bundle(
            zone, tasks,
            items_to_check=kwargs.get("items_to_check", ["item"]),
            **{k: v for k, v in kwargs.items() if k != "items_to_check"}
        )
    else:
        return BundleFactory.create_zone_recon_bundle(zone, tasks, **kwargs)


def calculate_bundle_bonus(
    total_bounty: float,
    tasks_completed: int,
    total_tasks: int,
    bonus_percentage: float = 10.0,
) -> float:
    """
    Quick calculation of bundle bonus.

    Args:
        total_bounty: Total bounty of all tasks
        tasks_completed: Number completed
        total_tasks: Total tasks
        bonus_percentage: Bonus percentage

    Returns:
        Bonus amount in USD
    """
    config = BundleBonus(bonus_percentage=bonus_percentage)
    return float(config.calculate_bonus(
        Decimal(str(total_bounty)),
        tasks_completed,
        total_tasks,
    ))
