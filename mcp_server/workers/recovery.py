"""
Reputation Recovery System (NOW-175)

Provides paths for workers to recover from suspension or low reputation.

Recovery process:
1. 30-day cooloff period (no task access)
2. Re-verification of identity
3. Return to probation tier
4. Must re-graduate through normal process

This allows:
- Second chances for workers who had legitimate issues
- Deterrence (recovery is painful but possible)
- Protection against permanent punishment for fixable problems

Anti-abuse measures:
- Only one recovery attempt per 365 days
- Must complete cooloff period
- Payment of recovery fee (optional, covers verification cost)
- Agent consent for previous dispute partners
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class RecoveryStatus(str, Enum):
    """Status of a recovery request."""
    PENDING = "pending"           # Request submitted
    COOLOFF = "cooloff"           # In cooloff period
    VERIFICATION = "verification" # Awaiting re-verification
    APPROVED = "approved"         # Recovery approved, back to probation
    REJECTED = "rejected"         # Recovery denied
    EXPIRED = "expired"           # Cooloff not completed


@dataclass
class RecoveryConfig:
    """Configuration for recovery system."""
    # Cooloff period
    cooloff_days: int = 30

    # Attempt limits
    max_recovery_attempts_per_year: int = 1
    min_days_between_attempts: int = 365

    # Fees
    recovery_fee_usd: float = 10.0  # Covers verification cost
    fee_required: bool = False

    # Verification
    require_new_identity_verification: bool = True
    require_agent_consent_for_disputes: bool = True

    # Automatic eligibility
    auto_eligible_after_days: int = 180  # 6 months of good behavior post-recovery


@dataclass
class RecoveryPath:
    """A recovery attempt record."""
    id: str
    worker_id: str
    status: RecoveryStatus
    initiated_at: datetime
    cooloff_ends_at: datetime

    # Reason for suspension
    suspension_reason: str
    suspension_date: datetime

    # Progress tracking
    identity_reverified: bool = False
    fee_paid: bool = False
    agent_consents: Dict[str, bool] = field(default_factory=dict)  # agent_id -> consent

    # Resolution
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    approved_by: Optional[str] = None

    @property
    def cooloff_remaining_days(self) -> int:
        """Days remaining in cooloff period."""
        if self.status != RecoveryStatus.COOLOFF:
            return 0
        now = datetime.now(timezone.utc)
        if now >= self.cooloff_ends_at:
            return 0
        return (self.cooloff_ends_at - now).days

    @property
    def is_cooloff_complete(self) -> bool:
        """Check if cooloff period is complete."""
        return datetime.now(timezone.utc) >= self.cooloff_ends_at

    @property
    def can_proceed_to_verification(self) -> bool:
        """Check if can move to verification stage."""
        return self.is_cooloff_complete and self.status == RecoveryStatus.COOLOFF


@dataclass
class RecoveryEligibility:
    """Eligibility check result for recovery."""
    eligible: bool
    reason: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    estimated_return_date: Optional[datetime] = None


class RecoveryManager:
    """
    Manages worker reputation recovery paths.

    Features:
    - Initiate recovery requests
    - Track cooloff periods
    - Handle re-verification
    - Process agent consents for disputed workers

    Example:
        >>> manager = RecoveryManager()
        >>> eligibility = await manager.check_eligibility("worker_123")
        >>> if eligibility.eligible:
        ...     path = await manager.initiate_recovery("worker_123")
        ...     # Worker now in 30-day cooloff
    """

    def __init__(self, config: Optional[RecoveryConfig] = None):
        """Initialize with optional custom config."""
        self.config = config or RecoveryConfig()
        self._active_recoveries: Dict[str, RecoveryPath] = {}

    async def check_eligibility(
        self,
        worker_id: str,
        db_client: Optional[Any] = None
    ) -> RecoveryEligibility:
        """
        Check if worker is eligible to start recovery.

        Args:
            worker_id: Worker's unique identifier
            db_client: Optional database client

        Returns:
            RecoveryEligibility with detailed requirements
        """
        requirements: List[str] = []

        # Check if already in recovery
        if worker_id in self._active_recoveries:
            active = self._active_recoveries[worker_id]
            if active.status in [RecoveryStatus.COOLOFF, RecoveryStatus.VERIFICATION]:
                return RecoveryEligibility(
                    eligible=False,
                    reason=f"Recovery already in progress (status: {active.status.value})",
                    estimated_return_date=active.cooloff_ends_at + timedelta(days=7),
                )

        # Check previous attempts
        previous_attempts = await self._get_previous_attempts(worker_id, db_client)
        recent_attempts = [
            a for a in previous_attempts
            if a.initiated_at > datetime.now(timezone.utc) - timedelta(days=365)
        ]

        if len(recent_attempts) >= self.config.max_recovery_attempts_per_year:
            last_attempt = max(recent_attempts, key=lambda a: a.initiated_at)
            next_eligible = last_attempt.initiated_at + timedelta(
                days=self.config.min_days_between_attempts
            )
            return RecoveryEligibility(
                eligible=False,
                reason=f"Maximum recovery attempts ({self.config.max_recovery_attempts_per_year}) "
                       "reached this year",
                estimated_return_date=next_eligible,
            )

        # Check if worker is actually suspended
        worker_status = await self._get_worker_status(worker_id, db_client)
        if worker_status.get("tier") != "suspended":
            return RecoveryEligibility(
                eligible=False,
                reason="Worker is not suspended - no recovery needed",
            )

        # Build requirements list
        requirements.append(
            f"Complete {self.config.cooloff_days}-day cooloff period"
        )

        if self.config.require_new_identity_verification:
            requirements.append("Submit new identity verification")

        if self.config.fee_required:
            requirements.append(
                f"Pay recovery fee: ${self.config.recovery_fee_usd:.2f}"
            )

        # Check if there are disputed agents requiring consent
        disputed_agents = await self._get_disputed_agents(worker_id, db_client)
        if disputed_agents and self.config.require_agent_consent_for_disputes:
            requirements.append(
                f"Obtain consent from {len(disputed_agents)} previously disputed agent(s)"
            )

        estimated_return = (
            datetime.now(timezone.utc)
            + timedelta(days=self.config.cooloff_days)
            + timedelta(days=7)  # Verification processing
        )

        return RecoveryEligibility(
            eligible=True,
            requirements=requirements,
            estimated_return_date=estimated_return,
        )

    async def initiate_recovery(
        self,
        worker_id: str,
        suspension_reason: str,
        suspension_date: datetime,
        db_client: Optional[Any] = None
    ) -> RecoveryPath:
        """
        Initiate a recovery process.

        Args:
            worker_id: Worker's unique identifier
            suspension_reason: Why the worker was suspended
            suspension_date: When suspension occurred
            db_client: Optional database client

        Returns:
            RecoveryPath tracking the recovery process
        """
        # Verify eligibility
        eligibility = await self.check_eligibility(worker_id, db_client)
        if not eligibility.eligible:
            raise ValueError(f"Not eligible for recovery: {eligibility.reason}")

        import uuid
        now = datetime.now(timezone.utc)

        path = RecoveryPath(
            id=str(uuid.uuid4()),
            worker_id=worker_id,
            status=RecoveryStatus.COOLOFF,
            initiated_at=now,
            cooloff_ends_at=now + timedelta(days=self.config.cooloff_days),
            suspension_reason=suspension_reason,
            suspension_date=suspension_date,
        )

        # Get disputed agents for consent tracking
        disputed_agents = await self._get_disputed_agents(worker_id, db_client)
        if disputed_agents:
            path.agent_consents = {agent_id: False for agent_id in disputed_agents}

        self._active_recoveries[worker_id] = path

        logger.info(
            f"Recovery initiated for {worker_id}: "
            f"cooloff ends {path.cooloff_ends_at.isoformat()}"
        )

        # Persist to database
        if db_client:
            await self._save_recovery(path, db_client)

        return path

    async def check_cooloff_status(
        self,
        worker_id: str,
        db_client: Optional[Any] = None
    ) -> Optional[RecoveryPath]:
        """
        Check current cooloff status.

        Args:
            worker_id: Worker's unique identifier
            db_client: Optional database client

        Returns:
            RecoveryPath if in recovery, None otherwise
        """
        if worker_id in self._active_recoveries:
            path = self._active_recoveries[worker_id]

            # Auto-advance from COOLOFF to VERIFICATION if cooloff complete
            if path.status == RecoveryStatus.COOLOFF and path.is_cooloff_complete:
                path.status = RecoveryStatus.VERIFICATION
                logger.info(
                    f"Worker {worker_id} completed cooloff, "
                    "now awaiting verification"
                )

                if db_client:
                    await self._save_recovery(path, db_client)

            return path

        # Try loading from database
        if db_client:
            return await self._load_active_recovery(worker_id, db_client)

        return None

    async def record_identity_verification(
        self,
        worker_id: str,
        verified: bool,
        verification_method: str,
        db_client: Optional[Any] = None
    ) -> RecoveryPath:
        """
        Record identity re-verification result.

        Args:
            worker_id: Worker's unique identifier
            verified: Verification result
            verification_method: Method used
            db_client: Optional database client

        Returns:
            Updated RecoveryPath
        """
        path = await self.check_cooloff_status(worker_id, db_client)
        if not path:
            raise ValueError(f"No active recovery for worker {worker_id}")

        if path.status != RecoveryStatus.VERIFICATION:
            raise ValueError(
                f"Recovery not in verification stage (current: {path.status.value})"
            )

        path.identity_reverified = verified

        if verified:
            logger.info(f"Identity re-verified for {worker_id} via {verification_method}")
            # Check if can complete recovery
            await self._check_recovery_completion(path, db_client)
        else:
            logger.warning(f"Identity re-verification failed for {worker_id}")
            path.status = RecoveryStatus.REJECTED
            path.resolution_notes = "Identity verification failed"
            path.resolved_at = datetime.now(timezone.utc)

        if db_client:
            await self._save_recovery(path, db_client)

        return path

    async def record_fee_payment(
        self,
        worker_id: str,
        amount_paid: float,
        payment_reference: str,
        db_client: Optional[Any] = None
    ) -> RecoveryPath:
        """
        Record recovery fee payment.

        Args:
            worker_id: Worker's unique identifier
            amount_paid: Amount paid in USD
            payment_reference: Payment transaction reference
            db_client: Optional database client

        Returns:
            Updated RecoveryPath
        """
        path = await self.check_cooloff_status(worker_id, db_client)
        if not path:
            raise ValueError(f"No active recovery for worker {worker_id}")

        if amount_paid >= self.config.recovery_fee_usd:
            path.fee_paid = True
            logger.info(
                f"Recovery fee paid for {worker_id}: "
                f"${amount_paid:.2f} (ref: {payment_reference})"
            )
        else:
            logger.warning(
                f"Insufficient fee payment for {worker_id}: "
                f"${amount_paid:.2f} < ${self.config.recovery_fee_usd:.2f}"
            )

        if db_client:
            await self._save_recovery(path, db_client)

        return path

    async def record_agent_consent(
        self,
        worker_id: str,
        agent_id: str,
        consents: bool,
        notes: Optional[str] = None,
        db_client: Optional[Any] = None
    ) -> RecoveryPath:
        """
        Record agent consent for worker recovery.

        Args:
            worker_id: Worker's unique identifier
            agent_id: Agent who had dispute
            consents: Whether agent consents to recovery
            notes: Optional notes from agent
            db_client: Optional database client

        Returns:
            Updated RecoveryPath
        """
        path = await self.check_cooloff_status(worker_id, db_client)
        if not path:
            raise ValueError(f"No active recovery for worker {worker_id}")

        if agent_id not in path.agent_consents:
            raise ValueError(f"Agent {agent_id} not in consent list")

        path.agent_consents[agent_id] = consents

        if consents:
            logger.info(f"Agent {agent_id} consented to recovery for {worker_id}")
        else:
            logger.info(
                f"Agent {agent_id} denied consent for {worker_id} recovery"
                + (f": {notes}" if notes else "")
            )
            # One denial is enough to reject (configurable)
            path.status = RecoveryStatus.REJECTED
            path.resolution_notes = f"Agent {agent_id} denied consent: {notes or 'No reason given'}"
            path.resolved_at = datetime.now(timezone.utc)

        # Check if all consents received
        if consents:
            await self._check_recovery_completion(path, db_client)

        if db_client:
            await self._save_recovery(path, db_client)

        return path

    async def complete_recovery(
        self,
        worker_id: str,
        approved_by: str,
        notes: Optional[str] = None,
        db_client: Optional[Any] = None
    ) -> RecoveryPath:
        """
        Manually complete/approve a recovery (admin action).

        Args:
            worker_id: Worker's unique identifier
            approved_by: Admin/system identifier
            notes: Resolution notes
            db_client: Optional database client

        Returns:
            Completed RecoveryPath
        """
        path = await self.check_cooloff_status(worker_id, db_client)
        if not path:
            raise ValueError(f"No active recovery for worker {worker_id}")

        path.status = RecoveryStatus.APPROVED
        path.resolved_at = datetime.now(timezone.utc)
        path.approved_by = approved_by
        path.resolution_notes = notes

        logger.info(
            f"Recovery approved for {worker_id} by {approved_by}"
            + (f": {notes}" if notes else "")
        )

        # Worker returns to probation - handled by ProbationManager
        if db_client:
            await self._save_recovery(path, db_client)
            # Reset worker to probation
            await self._reset_worker_to_probation(worker_id, db_client)

        # Remove from active
        self._active_recoveries.pop(worker_id, None)

        return path

    async def reject_recovery(
        self,
        worker_id: str,
        rejected_by: str,
        reason: str,
        db_client: Optional[Any] = None
    ) -> RecoveryPath:
        """
        Reject a recovery request (admin action).

        Args:
            worker_id: Worker's unique identifier
            rejected_by: Admin/system identifier
            reason: Rejection reason
            db_client: Optional database client

        Returns:
            Rejected RecoveryPath
        """
        path = await self.check_cooloff_status(worker_id, db_client)
        if not path:
            raise ValueError(f"No active recovery for worker {worker_id}")

        path.status = RecoveryStatus.REJECTED
        path.resolved_at = datetime.now(timezone.utc)
        path.resolution_notes = f"Rejected by {rejected_by}: {reason}"

        logger.info(f"Recovery rejected for {worker_id}: {reason}")

        if db_client:
            await self._save_recovery(path, db_client)

        # Remove from active
        self._active_recoveries.pop(worker_id, None)

        return path

    async def _check_recovery_completion(
        self,
        path: RecoveryPath,
        db_client: Optional[Any] = None
    ):
        """Check if recovery requirements are met and auto-complete."""
        if path.status != RecoveryStatus.VERIFICATION:
            return

        # Check all requirements
        all_met = True
        missing = []

        if self.config.require_new_identity_verification and not path.identity_reverified:
            all_met = False
            missing.append("identity verification")

        if self.config.fee_required and not path.fee_paid:
            all_met = False
            missing.append("fee payment")

        if self.config.require_agent_consent_for_disputes:
            if not all(path.agent_consents.values()):
                all_met = False
                pending = [k for k, v in path.agent_consents.items() if not v]
                missing.append(f"agent consent from {len(pending)} agent(s)")

        if all_met:
            path.status = RecoveryStatus.APPROVED
            path.resolved_at = datetime.now(timezone.utc)
            path.approved_by = "system"
            path.resolution_notes = "All requirements met - auto-approved"

            logger.info(f"Recovery auto-approved for {path.worker_id}")

            if db_client:
                await self._reset_worker_to_probation(path.worker_id, db_client)

            # Remove from active
            self._active_recoveries.pop(path.worker_id, None)

    async def _get_previous_attempts(
        self,
        worker_id: str,
        db_client: Optional[Any]
    ) -> List[RecoveryPath]:
        """Get previous recovery attempts from database."""
        if not db_client:
            return []

        result = db_client.table("recovery_attempts").select("*").eq(
            "worker_id", worker_id
        ).execute()

        if not result.data:
            return []

        return [
            RecoveryPath(
                id=r["id"],
                worker_id=r["worker_id"],
                status=RecoveryStatus(r["status"]),
                initiated_at=datetime.fromisoformat(r["initiated_at"]),
                cooloff_ends_at=datetime.fromisoformat(r["cooloff_ends_at"]),
                suspension_reason=r.get("suspension_reason", ""),
                suspension_date=datetime.fromisoformat(r["suspension_date"]),
            )
            for r in result.data
        ]

    async def _get_worker_status(
        self,
        worker_id: str,
        db_client: Optional[Any]
    ) -> Dict[str, Any]:
        """Get worker status from database."""
        if not db_client:
            return {"tier": "suspended"}  # Assume suspended for testing

        result = db_client.table("workers").select(
            "tier, suspension_reason"
        ).eq("id", worker_id).single().execute()

        return result.data or {"tier": "suspended"}

    async def _get_disputed_agents(
        self,
        worker_id: str,
        db_client: Optional[Any]
    ) -> List[str]:
        """Get list of agents who had disputes with this worker."""
        if not db_client:
            return []

        result = db_client.table("disputes").select(
            "agent_id"
        ).eq("worker_id", worker_id).eq(
            "outcome", "worker_fault"
        ).execute()

        if not result.data:
            return []

        return list(set(d["agent_id"] for d in result.data))

    async def _save_recovery(
        self,
        path: RecoveryPath,
        db_client: Any
    ):
        """Save recovery path to database."""
        data = {
            "id": path.id,
            "worker_id": path.worker_id,
            "status": path.status.value,
            "initiated_at": path.initiated_at.isoformat(),
            "cooloff_ends_at": path.cooloff_ends_at.isoformat(),
            "suspension_reason": path.suspension_reason,
            "suspension_date": path.suspension_date.isoformat(),
            "identity_reverified": path.identity_reverified,
            "fee_paid": path.fee_paid,
            "agent_consents": path.agent_consents,
            "resolved_at": path.resolved_at.isoformat() if path.resolved_at else None,
            "resolution_notes": path.resolution_notes,
            "approved_by": path.approved_by,
        }

        db_client.table("recovery_attempts").upsert(data).execute()

    async def _load_active_recovery(
        self,
        worker_id: str,
        db_client: Any
    ) -> Optional[RecoveryPath]:
        """Load active recovery from database."""
        result = db_client.table("recovery_attempts").select("*").eq(
            "worker_id", worker_id
        ).in_(
            "status", [RecoveryStatus.COOLOFF.value, RecoveryStatus.VERIFICATION.value]
        ).single().execute()

        if not result.data:
            return None

        r = result.data
        path = RecoveryPath(
            id=r["id"],
            worker_id=r["worker_id"],
            status=RecoveryStatus(r["status"]),
            initiated_at=datetime.fromisoformat(r["initiated_at"]),
            cooloff_ends_at=datetime.fromisoformat(r["cooloff_ends_at"]),
            suspension_reason=r.get("suspension_reason", ""),
            suspension_date=datetime.fromisoformat(r["suspension_date"]),
            identity_reverified=r.get("identity_reverified", False),
            fee_paid=r.get("fee_paid", False),
            agent_consents=r.get("agent_consents", {}),
        )

        self._active_recoveries[worker_id] = path
        return path

    async def _reset_worker_to_probation(
        self,
        worker_id: str,
        db_client: Any
    ):
        """Reset worker to probation tier after approved recovery."""
        db_client.table("workers").update({
            "tier": "probation",
            "tasks_completed": 0,
            "average_rating": 0.0,
            "total_disputes": 0,
            "identity_verified": True,  # Already re-verified
            "suspension_reason": None,
            "recovered_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", worker_id).execute()

        logger.info(f"Worker {worker_id} reset to probation tier")
