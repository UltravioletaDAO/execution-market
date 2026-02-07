"""
Bounty Escalation Job

Automatically increases bounties for unclaimed tasks based on time.
Implements dynamic pricing to ensure tasks get completed.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class EscalationConfig:
    """Configuration for bounty escalation."""

    # Base escalation rate (15% default)
    rate: float = 0.15
    # Interval between escalations (2 hours default)
    interval_hours: int = 2
    # Maximum multiplier (3x default)
    max_multiplier: float = 3.0
    # Minimum bounty before escalation kicks in
    min_bounty_usd: float = 1.0
    # Enable/disable escalation
    enabled: bool = True


@dataclass
class UrgencyConfig:
    """Configuration for urgency multipliers."""

    # Multiplier for <2hr deadline
    urgent_2hr: float = 1.5
    # Multiplier for <30min deadline
    urgent_30min: float = 2.0
    # Extra multiplier for remote/rural locations
    rural_premium: float = 1.3
    # Surge multiplier during peak hours
    peak_surge: float = 1.25


@dataclass
class EscalationResult:
    """Result of bounty escalation."""

    task_id: str
    original_bounty: float
    new_bounty: float
    multiplier: float
    escalation_count: int
    reason: str
    next_escalation_at: Optional[datetime] = None


class BountyEscalator:
    """
    Manages automatic bounty escalation for unclaimed tasks.

    Features:
    - Time-based escalation
    - Urgency multipliers
    - Location premiums
    - Surge pricing
    - Maximum caps
    """

    # Peak hours (UTC)
    PEAK_HOURS = [(9, 12), (14, 17), (19, 22)]

    def __init__(
        self,
        escalation_config: Optional[EscalationConfig] = None,
        urgency_config: Optional[UrgencyConfig] = None,
    ):
        """
        Initialize bounty escalator.

        Args:
            escalation_config: Escalation settings
            urgency_config: Urgency multiplier settings
        """
        self.escalation = escalation_config or EscalationConfig()
        self.urgency = urgency_config or UrgencyConfig()

    async def check_and_escalate(
        self, tasks: List[Dict[str, Any]]
    ) -> List[EscalationResult]:
        """
        Check all unclaimed tasks and escalate bounties if needed.

        Args:
            tasks: List of task dicts with id, bounty_usd, created_at,
                   deadline, location_hint, last_escalation

        Returns:
            List of escalation results
        """
        results = []
        now = datetime.utcnow()

        for task in tasks:
            # Skip if escalation disabled
            if not self.escalation.enabled:
                continue

            # Skip if below minimum
            if task.get("bounty_usd", 0) < self.escalation.min_bounty_usd:
                continue

            # Check if needs escalation
            result = self._check_task_escalation(task, now)
            if result:
                results.append(result)

        return results

    async def calculate_suggested_bounty(
        self,
        base_bounty: float,
        deadline: datetime,
        location_hint: Optional[str] = None,
        task_type: str = "simple_action",
    ) -> Dict[str, Any]:
        """
        Calculate suggested bounty with all multipliers.

        Args:
            base_bounty: Base bounty amount
            deadline: Task deadline
            location_hint: Location hint for task
            task_type: Type of task

        Returns:
            Dict with suggested bounty and breakdown
        """
        multipliers = {}
        now = datetime.utcnow()

        # Urgency multiplier
        time_to_deadline = (deadline - now).total_seconds()
        if time_to_deadline < 1800:  # <30 min
            multipliers["urgency"] = self.urgency.urgent_30min
        elif time_to_deadline < 7200:  # <2 hr
            multipliers["urgency"] = self.urgency.urgent_2hr
        else:
            multipliers["urgency"] = 1.0

        # Location premium
        if location_hint and self._is_rural_location(location_hint):
            multipliers["location"] = self.urgency.rural_premium
        else:
            multipliers["location"] = 1.0

        # Peak hours surge
        if self._is_peak_hour(now):
            multipliers["surge"] = self.urgency.peak_surge
        else:
            multipliers["surge"] = 1.0

        # Task type minimum
        type_minimums = {
            "simple_action": 0.50,
            "physical_presence": 1.00,
            "knowledge_access": 2.00,
            "human_authority": 5.00,
            "digital_physical": 3.00,
        }
        min_bounty = type_minimums.get(task_type, 0.50)

        # Calculate final
        total_multiplier = 1.0
        for mult in multipliers.values():
            total_multiplier *= mult

        suggested = max(base_bounty * total_multiplier, min_bounty)

        return {
            "base_bounty": base_bounty,
            "suggested_bounty": round(suggested, 2),
            "total_multiplier": round(total_multiplier, 2),
            "multipliers": multipliers,
            "minimum_for_type": min_bounty,
        }

    async def run_escalation_job(self) -> Dict[str, Any]:
        """
        Run the escalation job (for scheduler).

        Returns:
            Job execution summary
        """
        start = datetime.utcnow()
        logger.info("Starting bounty escalation job")

        # Would fetch unclaimed tasks from database
        # For now, return empty results
        results = []

        end = datetime.utcnow()
        duration = (end - start).total_seconds()

        summary = {
            "job": "escalate_bounties",
            "started_at": start.isoformat(),
            "completed_at": end.isoformat(),
            "duration_seconds": duration,
            "tasks_checked": 0,
            "tasks_escalated": len(results),
            "results": [r.__dict__ for r in results],
        }

        logger.info(f"Escalation job completed: {len(results)} tasks escalated")
        return summary

    # Private methods

    def _check_task_escalation(
        self, task: Dict[str, Any], now: datetime
    ) -> Optional[EscalationResult]:
        """Check if a task needs escalation."""
        task_id = task["id"]
        current_bounty = task["bounty_usd"]
        original_bounty = task.get("original_bounty_usd", current_bounty)
        created_at = task.get("created_at", now)
        last_escalation = task.get("last_escalation")

        # Parse dates if strings
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(last_escalation, str):
            last_escalation = datetime.fromisoformat(
                last_escalation.replace("Z", "+00:00")
            )

        # Calculate current multiplier
        current_multiplier = (
            current_bounty / original_bounty if original_bounty > 0 else 1.0
        )

        # Check if at max
        if current_multiplier >= self.escalation.max_multiplier:
            return None

        # Check if enough time has passed
        check_time = last_escalation or created_at
        hours_since = (now - check_time).total_seconds() / 3600

        if hours_since < self.escalation.interval_hours:
            return None

        # Calculate new bounty
        new_multiplier = min(
            current_multiplier * (1 + self.escalation.rate),
            self.escalation.max_multiplier,
        )
        new_bounty = original_bounty * new_multiplier

        # Count escalations
        escalation_count = task.get("escalation_count", 0) + 1

        return EscalationResult(
            task_id=task_id,
            original_bounty=original_bounty,
            new_bounty=round(new_bounty, 2),
            multiplier=round(new_multiplier, 2),
            escalation_count=escalation_count,
            reason=f"Auto-escalation after {hours_since:.1f}h unclaimed",
            next_escalation_at=now + timedelta(hours=self.escalation.interval_hours)
            if new_multiplier < self.escalation.max_multiplier
            else None,
        )

    def _is_rural_location(self, location_hint: str) -> bool:
        """Check if location appears rural."""
        rural_keywords = [
            "rural",
            "remote",
            "countryside",
            "pueblo",
            "village",
            "farm",
            "ranch",
            "mountain",
            "forest",
            "desert",
        ]
        return any(kw in location_hint.lower() for kw in rural_keywords)

    def _is_peak_hour(self, dt: datetime) -> bool:
        """Check if time is during peak hours."""
        hour = dt.hour
        return any(start <= hour < end for start, end in self.PEAK_HOURS)


# Job scheduler helper


async def schedule_escalation_job(interval_minutes: int = 30):
    """
    Schedule the escalation job to run periodically.

    Args:
        interval_minutes: Run interval in minutes
    """
    import asyncio

    escalator = BountyEscalator()

    while True:
        try:
            result = await escalator.run_escalation_job()
            logger.info(f"Job result: {result['tasks_escalated']} escalated")
        except Exception as e:
            logger.error(f"Escalation job error: {e}")

        await asyncio.sleep(interval_minutes * 60)
