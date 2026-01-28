"""
Referral System (NOW-144)

Manages worker referrals and bonus payouts for Chamba.

Features:
- Referral code generation with customizable formats
- $1-2 per referral that completes 5 tasks
- Automatic tracking and attribution
- Payout management via x402
- Fraud prevention (self-referral, abuse detection)
- Expiration handling

Example:
    >>> manager = ReferralManager()
    >>> # Existing worker generates referral code
    >>> code = await manager.generate_code("worker_123")
    >>> print(f"Share this code: {code.code}")

    >>> # New user applies referral during signup
    >>> referral = await manager.apply_code(code.code, "new_worker_456")
    >>> print(f"Referral created: {referral.id}")

    >>> # After each task completion, check for bonus
    >>> result = await manager.record_task_completion("new_worker_456")
    >>> if result and result.status == ReferralStatus.COMPLETED:
    ...     print(f"Bonus ${result.bonus_amount} earned!")
"""

import logging
import secrets
import string
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ReferralStatus(str, Enum):
    """Status of a referral in the system."""
    PENDING = "pending"           # Referred user signed up but hasn't started
    QUALIFYING = "qualifying"     # Working on required tasks
    COMPLETED = "completed"       # Required tasks done, bonus paid
    EXPIRED = "expired"           # Didn't complete in time
    REJECTED = "rejected"         # Fraud detected or invalid referral


@dataclass
class ReferralConfig:
    """
    Configuration for the referral program.

    Attributes:
        tasks_required: Number of tasks referee must complete
        bonus_amount_min: Minimum bonus in USD
        bonus_amount_max: Maximum bonus in USD
        bonus_amount_default: Default bonus amount
        expiry_days: Days until referral expires
        code_length: Length of generated referral codes
        code_prefix: Prefix for generated codes
        max_referrals_per_code: Maximum uses per code (None = unlimited)
        min_referrer_tasks: Minimum tasks referrer must have completed
        cooldown_hours: Hours between generating new codes
        max_active_codes: Maximum active codes per referrer
        fraud_check_enabled: Enable fraud detection
    """
    tasks_required: int = 5
    bonus_amount_min: float = 1.00
    bonus_amount_max: float = 2.00
    bonus_amount_default: float = 2.00
    expiry_days: int = 30
    code_length: int = 8
    code_prefix: str = "CHAMBA"
    max_referrals_per_code: Optional[int] = None
    min_referrer_tasks: int = 1
    cooldown_hours: int = 0
    max_active_codes: int = 5
    fraud_check_enabled: bool = True


@dataclass
class ReferralCode:
    """
    A referral code that can be shared to invite new workers.

    Attributes:
        code: The actual referral code string
        referrer_id: ID of the worker who owns this code
        created_at: When the code was created
        uses: Number of times this code has been used
        max_uses: Maximum allowed uses (None = unlimited)
        expires_at: When this code expires
        is_active: Whether the code is currently active
        bonus_amount: Bonus amount for this specific code
        metadata: Additional metadata
    """
    code: str
    referrer_id: str
    created_at: datetime
    uses: int = 0
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    bonus_amount: float = 2.00
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Check if code is still valid for use."""
        if not self.is_active:
            return False
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @property
    def remaining_uses(self) -> Optional[int]:
        """Get remaining uses, or None if unlimited."""
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.uses)


@dataclass
class Referral:
    """
    A referral relationship between two workers.

    Tracks the progress of a referred user toward completing
    the required tasks for the referrer to earn the bonus.

    Attributes:
        id: Unique referral ID
        code: The referral code used
        referrer_id: ID of the worker who referred
        referee_id: ID of the new worker who was referred
        status: Current status of the referral
        tasks_completed: Number of qualifying tasks completed
        tasks_required: Total tasks needed to qualify
        bonus_amount: Bonus amount to be paid
        bonus_paid: Whether bonus has been paid
        created_at: When referral was created
        completed_at: When required tasks were completed
        paid_at: When bonus was paid
        expires_at: When referral expires
        tx_hash: Payment transaction hash
        metadata: Additional tracking data
    """
    id: str
    code: str
    referrer_id: str
    referee_id: str
    status: ReferralStatus
    tasks_completed: int
    tasks_required: int
    bonus_amount: float
    bonus_paid: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    tx_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def tasks_remaining(self) -> int:
        """Tasks remaining until qualification."""
        return max(0, self.tasks_required - self.tasks_completed)

    @property
    def progress_percent(self) -> float:
        """Progress percentage toward completion."""
        if self.tasks_required == 0:
            return 100.0
        return min(100.0, (self.tasks_completed / self.tasks_required) * 100)

    @property
    def is_expired(self) -> bool:
        """Check if referral has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class ReferralStats:
    """
    Statistics for a referrer's referral activity.

    Attributes:
        referrer_id: Worker ID
        total_referrals: Total referrals created
        completed_referrals: Referrals that completed tasks
        pending_referrals: Active referrals in progress
        expired_referrals: Referrals that expired
        total_earned: Total bonus amount earned
        total_pending: Potential bonus for pending referrals
        active_codes: Number of active referral codes
        avg_completion_days: Average days to completion
        conversion_rate: Percentage that complete requirements
    """
    referrer_id: str
    total_referrals: int = 0
    completed_referrals: int = 0
    pending_referrals: int = 0
    expired_referrals: int = 0
    total_earned: float = 0.0
    total_pending: float = 0.0
    active_codes: int = 0
    avg_completion_days: Optional[float] = None
    conversion_rate: float = 0.0


class ReferralManager:
    """
    Manages the complete referral program lifecycle.

    Features:
    - Generate unique, human-readable referral codes
    - Track referral attribution and progress
    - Automatically trigger bonus payments when tasks complete
    - Fraud prevention and abuse detection
    - Statistics and reporting

    Example:
        >>> manager = ReferralManager()

        >>> # Worker generates a referral code
        >>> code = await manager.generate_code("worker_123")
        >>> print(f"Your code: {code.code}")  # e.g., "CHAMBA-ABC123"

        >>> # New user signs up with the code
        >>> referral = await manager.apply_code("CHAMBA-ABC123", "new_user_456")

        >>> # After each task completion, manager checks progress
        >>> for task in completed_tasks:
        ...     result = await manager.record_task_completion("new_user_456")
        ...     if result and result.status == ReferralStatus.COMPLETED:
        ...         print(f"Referrer earned ${result.bonus_amount}!")
    """

    def __init__(
        self,
        config: Optional[ReferralConfig] = None,
        db_client: Optional[Any] = None,
        x402_client: Optional[Any] = None,
    ):
        """
        Initialize the referral manager.

        Args:
            config: Configuration for referral program parameters
            db_client: Database client for persistence (Supabase)
            x402_client: x402 payment client for bonus payouts
        """
        self.config = config or ReferralConfig()
        self.db_client = db_client
        self.x402_client = x402_client

        # In-memory storage for development/testing
        # Production uses database
        self._codes: Dict[str, ReferralCode] = {}
        self._referrals: Dict[str, Referral] = {}
        self._referee_to_referral: Dict[str, str] = {}  # referee_id -> referral_id

    def _generate_code_string(self) -> str:
        """
        Generate a unique, human-readable referral code.

        Format: PREFIX-XXXXXX (e.g., CHAMBA-A3B7C9)
        Uses only uppercase letters and digits, avoiding ambiguous chars (0, O, I, L, 1).
        """
        # Exclude ambiguous characters
        alphabet = ''.join(
            c for c in string.ascii_uppercase + string.digits
            if c not in '0O1IL'
        )

        # Generate random part
        random_part = ''.join(
            secrets.choice(alphabet)
            for _ in range(self.config.code_length)
        )

        # Combine with prefix
        if self.config.code_prefix:
            return f"{self.config.code_prefix}-{random_part}"
        return random_part

    async def _check_referrer_eligibility(
        self,
        referrer_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a worker is eligible to generate referral codes.

        Args:
            referrer_id: Worker ID to check

        Returns:
            Tuple of (is_eligible, error_message)
        """
        # Check minimum tasks completed
        if self.db_client:
            result = self.db_client.table("workers").select(
                "tasks_completed, created_at"
            ).eq("id", referrer_id).single().execute()

            if not result.data:
                return False, "Worker not found"

            tasks_completed = result.data.get("tasks_completed", 0)
            if tasks_completed < self.config.min_referrer_tasks:
                return False, (
                    f"Must complete at least {self.config.min_referrer_tasks} tasks "
                    f"to generate referral codes. You have: {tasks_completed}"
                )

        # Check active codes limit
        active_codes = sum(
            1 for code in self._codes.values()
            if code.referrer_id == referrer_id and code.is_valid
        )
        if active_codes >= self.config.max_active_codes:
            return False, (
                f"Maximum {self.config.max_active_codes} active codes allowed. "
                "Deactivate an existing code first."
            )

        # Check cooldown
        if self.config.cooldown_hours > 0:
            recent_codes = [
                code for code in self._codes.values()
                if code.referrer_id == referrer_id
            ]
            if recent_codes:
                latest = max(recent_codes, key=lambda c: c.created_at)
                cooldown_end = latest.created_at + timedelta(hours=self.config.cooldown_hours)
                if datetime.now(timezone.utc) < cooldown_end:
                    remaining = cooldown_end - datetime.now(timezone.utc)
                    return False, (
                        f"Please wait {remaining.total_seconds() / 3600:.1f} hours "
                        "before generating another code."
                    )

        return True, None

    async def _check_fraud(
        self,
        code: str,
        referee_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for potential fraud in referral application.

        Args:
            code: Referral code being used
            referee_id: New user's ID

        Returns:
            Tuple of (is_valid, fraud_reason)
        """
        if not self.config.fraud_check_enabled:
            return True, None

        referral_code = self._codes.get(code)
        if not referral_code:
            return False, "Invalid code"

        # Self-referral check
        if referral_code.referrer_id == referee_id:
            logger.warning(f"Self-referral attempt: {referee_id}")
            return False, "Cannot use your own referral code"

        # Check if referee already has a referral
        if referee_id in self._referee_to_referral:
            return False, "You have already been referred"

        # Additional fraud checks with database
        if self.db_client:
            # Check for shared IP/device patterns
            referrer_data = self.db_client.table("workers").select(
                "signup_ip, device_fingerprint"
            ).eq("id", referral_code.referrer_id).single().execute()

            referee_data = self.db_client.table("workers").select(
                "signup_ip, device_fingerprint"
            ).eq("id", referee_id).single().execute()

            if referrer_data.data and referee_data.data:
                # Same IP check
                if (referrer_data.data.get("signup_ip") ==
                    referee_data.data.get("signup_ip")):
                    logger.warning(
                        f"Same IP referral: referrer={referral_code.referrer_id}, "
                        f"referee={referee_id}"
                    )
                    # Allow but flag for review
                    return True, "FLAGGED: Same IP address"

                # Same device check
                if (referrer_data.data.get("device_fingerprint") ==
                    referee_data.data.get("device_fingerprint")):
                    logger.warning(
                        f"Same device referral: referrer={referral_code.referrer_id}, "
                        f"referee={referee_id}"
                    )
                    return False, "Suspicious activity detected"

        return True, None

    async def generate_code(
        self,
        referrer_id: str,
        bonus_amount: Optional[float] = None,
        max_uses: Optional[int] = None,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReferralCode:
        """
        Generate a new referral code for a worker.

        Args:
            referrer_id: Worker's ID who will receive the bonus
            bonus_amount: Custom bonus amount (uses default if not specified)
            max_uses: Maximum uses for this code
            expires_in_days: Days until code expires
            metadata: Additional metadata to store

        Returns:
            ReferralCode object with the generated code

        Raises:
            ValueError: If worker is not eligible to generate codes
        """
        # Check eligibility
        eligible, error = await self._check_referrer_eligibility(referrer_id)
        if not eligible:
            raise ValueError(error)

        # Generate unique code
        code_str = self._generate_code_string()
        while code_str in self._codes:  # Ensure uniqueness
            code_str = self._generate_code_string()

        # Determine bonus amount
        bonus = bonus_amount or self.config.bonus_amount_default
        bonus = max(self.config.bonus_amount_min,
                   min(self.config.bonus_amount_max, bonus))

        # Calculate expiration
        now = datetime.now(timezone.utc)
        expires_days = expires_in_days or self.config.expiry_days
        expires_at = now + timedelta(days=expires_days) if expires_days > 0 else None

        # Create code object
        referral_code = ReferralCode(
            code=code_str,
            referrer_id=referrer_id,
            created_at=now,
            uses=0,
            max_uses=max_uses or self.config.max_referrals_per_code,
            expires_at=expires_at,
            is_active=True,
            bonus_amount=bonus,
            metadata=metadata or {},
        )

        # Store in memory
        self._codes[code_str] = referral_code

        # Persist to database
        if self.db_client:
            self.db_client.table("referral_codes").insert({
                "code": code_str,
                "referrer_id": referrer_id,
                "created_at": now.isoformat(),
                "max_uses": referral_code.max_uses,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "bonus_amount": bonus,
                "metadata": metadata or {},
            }).execute()

        logger.info(
            f"Referral code generated: {code_str} by {referrer_id}, "
            f"bonus=${bonus:.2f}"
        )

        return referral_code

    async def apply_code(
        self,
        code: str,
        referee_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Referral]:
        """
        Apply a referral code for a new user during signup.

        Args:
            code: The referral code to apply
            referee_id: The new user's worker ID
            metadata: Additional metadata (e.g., signup source)

        Returns:
            Referral object if successful, None if code is invalid

        Raises:
            ValueError: If code is invalid or fraud detected
        """
        # Normalize code (uppercase, trim)
        code = code.strip().upper()

        # Look up code
        referral_code = self._codes.get(code)

        # Try database if not in memory
        if not referral_code and self.db_client:
            result = self.db_client.table("referral_codes").select(
                "*"
            ).eq("code", code).single().execute()

            if result.data:
                referral_code = ReferralCode(
                    code=result.data["code"],
                    referrer_id=result.data["referrer_id"],
                    created_at=datetime.fromisoformat(result.data["created_at"]),
                    uses=result.data.get("uses", 0),
                    max_uses=result.data.get("max_uses"),
                    expires_at=(datetime.fromisoformat(result.data["expires_at"])
                               if result.data.get("expires_at") else None),
                    is_active=result.data.get("is_active", True),
                    bonus_amount=result.data.get("bonus_amount", self.config.bonus_amount_default),
                    metadata=result.data.get("metadata", {}),
                )
                self._codes[code] = referral_code

        if not referral_code:
            raise ValueError("Invalid referral code")

        if not referral_code.is_valid:
            if referral_code.max_uses and referral_code.uses >= referral_code.max_uses:
                raise ValueError("This referral code has reached its usage limit")
            if referral_code.expires_at and datetime.now(timezone.utc) > referral_code.expires_at:
                raise ValueError("This referral code has expired")
            raise ValueError("This referral code is no longer active")

        # Fraud check
        is_valid, fraud_reason = await self._check_fraud(code, referee_id)
        if not is_valid:
            raise ValueError(fraud_reason)

        # Create referral
        now = datetime.now(timezone.utc)
        referral_id = str(uuid.uuid4())

        referral = Referral(
            id=referral_id,
            code=code,
            referrer_id=referral_code.referrer_id,
            referee_id=referee_id,
            status=ReferralStatus.PENDING,
            tasks_completed=0,
            tasks_required=self.config.tasks_required,
            bonus_amount=referral_code.bonus_amount,
            bonus_paid=False,
            created_at=now,
            expires_at=now + timedelta(days=self.config.expiry_days),
            metadata={
                **(metadata or {}),
                "fraud_flag": fraud_reason if fraud_reason else None,
            },
        )

        # Update code usage
        referral_code.uses += 1

        # Store
        self._referrals[referral_id] = referral
        self._referee_to_referral[referee_id] = referral_id

        # Persist to database
        if self.db_client:
            self.db_client.table("referrals").insert({
                "id": referral_id,
                "code": code,
                "referrer_id": referral_code.referrer_id,
                "referee_id": referee_id,
                "status": ReferralStatus.PENDING.value,
                "tasks_completed": 0,
                "tasks_required": self.config.tasks_required,
                "bonus_amount": referral_code.bonus_amount,
                "bonus_paid": False,
                "created_at": now.isoformat(),
                "expires_at": referral.expires_at.isoformat(),
                "metadata": referral.metadata,
            }).execute()

            # Update code uses
            self.db_client.table("referral_codes").update({
                "uses": referral_code.uses,
            }).eq("code", code).execute()

        logger.info(
            f"Referral applied: {code} -> {referee_id}, "
            f"referrer={referral_code.referrer_id}"
        )

        return referral

    async def record_task_completion(
        self,
        worker_id: str,
        task_id: Optional[str] = None,
        task_rating: Optional[float] = None,
    ) -> Optional[Referral]:
        """
        Record a task completion and check if referral bonus is earned.

        Called after a worker completes a task. Checks if the worker
        is a referee and updates their referral progress.

        Args:
            worker_id: The worker who completed the task
            task_id: The completed task ID (for tracking)
            task_rating: Rating received for the task

        Returns:
            Updated Referral if worker is a referee, None otherwise
        """
        # Check if worker is a referee
        referral_id = self._referee_to_referral.get(worker_id)

        # Try database if not in memory
        if not referral_id and self.db_client:
            result = self.db_client.table("referrals").select(
                "id"
            ).eq("referee_id", worker_id).eq(
                "status", ReferralStatus.PENDING.value
            ).single().execute()

            if result.data:
                referral_id = result.data["id"]
                # Load full referral
                await self._load_referral(referral_id)

        if not referral_id:
            return None

        referral = self._referrals.get(referral_id)
        if not referral:
            return None

        # Skip if already completed or expired
        if referral.status in [ReferralStatus.COMPLETED, ReferralStatus.EXPIRED,
                               ReferralStatus.REJECTED]:
            return referral

        # Check for expiration
        if referral.is_expired:
            referral.status = ReferralStatus.EXPIRED
            await self._persist_referral(referral)
            logger.info(f"Referral {referral.id} expired")
            return referral

        # Update progress
        referral.tasks_completed += 1

        # Track task in metadata
        if task_id:
            if "completed_tasks" not in referral.metadata:
                referral.metadata["completed_tasks"] = []
            referral.metadata["completed_tasks"].append({
                "task_id": task_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "rating": task_rating,
            })

        # Update status
        if referral.tasks_completed > 0:
            referral.status = ReferralStatus.QUALIFYING

        # Check if qualification complete
        if referral.tasks_completed >= referral.tasks_required:
            referral.completed_at = datetime.now(timezone.utc)
            # Process bonus payment
            success = await self._process_bonus(referral)
            if success:
                referral.status = ReferralStatus.COMPLETED
                referral.bonus_paid = True
                referral.paid_at = datetime.now(timezone.utc)
                logger.info(
                    f"Referral completed: {referral.id}, "
                    f"bonus ${referral.bonus_amount:.2f} to {referral.referrer_id}"
                )
            else:
                # Payment failed, keep as qualifying for retry
                logger.error(f"Bonus payment failed for referral {referral.id}")

        await self._persist_referral(referral)

        return referral

    async def _process_bonus(self, referral: Referral) -> bool:
        """
        Process bonus payment for a completed referral.

        Args:
            referral: The completed referral

        Returns:
            True if payment succeeded, False otherwise
        """
        try:
            if self.x402_client:
                # Get referrer's wallet address
                if self.db_client:
                    result = self.db_client.table("workers").select(
                        "wallet_address"
                    ).eq("id", referral.referrer_id).single().execute()

                    if not result.data or not result.data.get("wallet_address"):
                        logger.error(
                            f"No wallet address for referrer {referral.referrer_id}"
                        )
                        return False

                    wallet_address = result.data["wallet_address"]
                else:
                    # Fallback for testing
                    wallet_address = referral.metadata.get("referrer_wallet")
                    if not wallet_address:
                        logger.error("No wallet address available for payment")
                        return False

                # Execute payment via x402
                payment_result = await self.x402_client.send_payment(
                    recipient=wallet_address,
                    amount_usdc=referral.bonus_amount,
                    memo=f"Referral bonus for {referral.referee_id}",
                )

                if payment_result.success:
                    referral.tx_hash = payment_result.tx_hash
                    logger.info(
                        f"Bonus paid: ${referral.bonus_amount:.2f} to {wallet_address}, "
                        f"tx={payment_result.tx_hash}"
                    )
                    return True
                else:
                    logger.error(f"Payment failed: {payment_result.error}")
                    return False
            else:
                # No x402 client - mark as successful for testing
                logger.warning("No x402 client - simulating payment success")
                referral.tx_hash = f"sim_{uuid.uuid4().hex[:16]}"
                return True

        except Exception as e:
            logger.exception(f"Error processing bonus payment: {e}")
            return False

    async def _persist_referral(self, referral: Referral) -> None:
        """Persist referral state to database."""
        if self.db_client:
            self.db_client.table("referrals").update({
                "status": referral.status.value,
                "tasks_completed": referral.tasks_completed,
                "bonus_paid": referral.bonus_paid,
                "completed_at": referral.completed_at.isoformat() if referral.completed_at else None,
                "paid_at": referral.paid_at.isoformat() if referral.paid_at else None,
                "tx_hash": referral.tx_hash,
                "metadata": referral.metadata,
            }).eq("id", referral.id).execute()

    async def _load_referral(self, referral_id: str) -> Optional[Referral]:
        """Load a referral from database."""
        if not self.db_client:
            return None

        result = self.db_client.table("referrals").select(
            "*"
        ).eq("id", referral_id).single().execute()

        if not result.data:
            return None

        data = result.data
        referral = Referral(
            id=data["id"],
            code=data["code"],
            referrer_id=data["referrer_id"],
            referee_id=data["referee_id"],
            status=ReferralStatus(data["status"]),
            tasks_completed=data["tasks_completed"],
            tasks_required=data["tasks_required"],
            bonus_amount=data["bonus_amount"],
            bonus_paid=data["bonus_paid"],
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=(datetime.fromisoformat(data["completed_at"])
                         if data.get("completed_at") else None),
            paid_at=(datetime.fromisoformat(data["paid_at"])
                    if data.get("paid_at") else None),
            expires_at=(datetime.fromisoformat(data["expires_at"])
                       if data.get("expires_at") else None),
            tx_hash=data.get("tx_hash"),
            metadata=data.get("metadata", {}),
        )

        self._referrals[referral_id] = referral
        self._referee_to_referral[referral.referee_id] = referral_id

        return referral

    async def get_referral(self, referral_id: str) -> Optional[Referral]:
        """
        Get a referral by ID.

        Args:
            referral_id: The referral ID

        Returns:
            Referral object or None if not found
        """
        if referral_id in self._referrals:
            return self._referrals[referral_id]
        return await self._load_referral(referral_id)

    async def get_referral_by_referee(self, referee_id: str) -> Optional[Referral]:
        """
        Get a referral by referee ID.

        Args:
            referee_id: The referee's worker ID

        Returns:
            Referral object or None if not found
        """
        referral_id = self._referee_to_referral.get(referee_id)
        if referral_id:
            return self._referrals.get(referral_id)

        # Try database
        if self.db_client:
            result = self.db_client.table("referrals").select(
                "id"
            ).eq("referee_id", referee_id).single().execute()

            if result.data:
                return await self._load_referral(result.data["id"])

        return None

    async def get_referrer_stats(self, referrer_id: str) -> ReferralStats:
        """
        Get comprehensive referral statistics for a worker.

        Args:
            referrer_id: The referrer's worker ID

        Returns:
            ReferralStats with all metrics
        """
        stats = ReferralStats(referrer_id=referrer_id)

        # Get all referrals for this referrer
        referrals: List[Referral] = []

        if self.db_client:
            result = self.db_client.table("referrals").select(
                "*"
            ).eq("referrer_id", referrer_id).execute()

            if result.data:
                for data in result.data:
                    referrals.append(Referral(
                        id=data["id"],
                        code=data["code"],
                        referrer_id=data["referrer_id"],
                        referee_id=data["referee_id"],
                        status=ReferralStatus(data["status"]),
                        tasks_completed=data["tasks_completed"],
                        tasks_required=data["tasks_required"],
                        bonus_amount=data["bonus_amount"],
                        bonus_paid=data["bonus_paid"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        completed_at=(datetime.fromisoformat(data["completed_at"])
                                     if data.get("completed_at") else None),
                        paid_at=(datetime.fromisoformat(data["paid_at"])
                                if data.get("paid_at") else None),
                        expires_at=(datetime.fromisoformat(data["expires_at"])
                                   if data.get("expires_at") else None),
                        tx_hash=data.get("tx_hash"),
                        metadata=data.get("metadata", {}),
                    ))
        else:
            # Use in-memory data
            referrals = [
                r for r in self._referrals.values()
                if r.referrer_id == referrer_id
            ]

        # Calculate statistics
        stats.total_referrals = len(referrals)

        completion_days: List[float] = []

        for referral in referrals:
            if referral.status == ReferralStatus.COMPLETED:
                stats.completed_referrals += 1
                stats.total_earned += referral.bonus_amount

                # Calculate completion time
                if referral.completed_at and referral.created_at:
                    days = (referral.completed_at - referral.created_at).total_seconds() / 86400
                    completion_days.append(days)

            elif referral.status in [ReferralStatus.PENDING, ReferralStatus.QUALIFYING]:
                stats.pending_referrals += 1
                stats.total_pending += referral.bonus_amount

            elif referral.status == ReferralStatus.EXPIRED:
                stats.expired_referrals += 1

        # Calculate averages
        if completion_days:
            stats.avg_completion_days = sum(completion_days) / len(completion_days)

        if stats.total_referrals > 0:
            stats.conversion_rate = (stats.completed_referrals / stats.total_referrals) * 100

        # Count active codes
        if self.db_client:
            codes_result = self.db_client.table("referral_codes").select(
                "code", count="exact"
            ).eq("referrer_id", referrer_id).eq("is_active", True).execute()
            stats.active_codes = codes_result.count or 0
        else:
            stats.active_codes = sum(
                1 for code in self._codes.values()
                if code.referrer_id == referrer_id and code.is_valid
            )

        return stats

    async def get_referrer_referrals(
        self,
        referrer_id: str,
        status: Optional[ReferralStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Referral]:
        """
        Get all referrals for a referrer.

        Args:
            referrer_id: The referrer's worker ID
            status: Filter by status (optional)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of Referral objects
        """
        if self.db_client:
            query = self.db_client.table("referrals").select(
                "*"
            ).eq("referrer_id", referrer_id)

            if status:
                query = query.eq("status", status.value)

            result = query.order(
                "created_at", desc=True
            ).range(offset, offset + limit - 1).execute()

            referrals = []
            for data in (result.data or []):
                referrals.append(Referral(
                    id=data["id"],
                    code=data["code"],
                    referrer_id=data["referrer_id"],
                    referee_id=data["referee_id"],
                    status=ReferralStatus(data["status"]),
                    tasks_completed=data["tasks_completed"],
                    tasks_required=data["tasks_required"],
                    bonus_amount=data["bonus_amount"],
                    bonus_paid=data["bonus_paid"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    completed_at=(datetime.fromisoformat(data["completed_at"])
                                 if data.get("completed_at") else None),
                    paid_at=(datetime.fromisoformat(data["paid_at"])
                            if data.get("paid_at") else None),
                    expires_at=(datetime.fromisoformat(data["expires_at"])
                               if data.get("expires_at") else None),
                    tx_hash=data.get("tx_hash"),
                    metadata=data.get("metadata", {}),
                ))
            return referrals
        else:
            # In-memory
            referrals = [
                r for r in self._referrals.values()
                if r.referrer_id == referrer_id
                and (status is None or r.status == status)
            ]
            referrals.sort(key=lambda r: r.created_at, reverse=True)
            return referrals[offset:offset + limit]

    async def get_referrer_codes(
        self,
        referrer_id: str,
        active_only: bool = True,
    ) -> List[ReferralCode]:
        """
        Get all referral codes for a referrer.

        Args:
            referrer_id: The referrer's worker ID
            active_only: Only return active/valid codes

        Returns:
            List of ReferralCode objects
        """
        if self.db_client:
            query = self.db_client.table("referral_codes").select("*").eq(
                "referrer_id", referrer_id
            )

            if active_only:
                query = query.eq("is_active", True)

            result = query.order("created_at", desc=True).execute()

            codes = []
            for data in (result.data or []):
                code = ReferralCode(
                    code=data["code"],
                    referrer_id=data["referrer_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    uses=data.get("uses", 0),
                    max_uses=data.get("max_uses"),
                    expires_at=(datetime.fromisoformat(data["expires_at"])
                               if data.get("expires_at") else None),
                    is_active=data.get("is_active", True),
                    bonus_amount=data.get("bonus_amount", self.config.bonus_amount_default),
                    metadata=data.get("metadata", {}),
                )
                if not active_only or code.is_valid:
                    codes.append(code)
            return codes
        else:
            codes = [
                c for c in self._codes.values()
                if c.referrer_id == referrer_id
                and (not active_only or c.is_valid)
            ]
            codes.sort(key=lambda c: c.created_at, reverse=True)
            return codes

    async def deactivate_code(
        self,
        code: str,
        referrer_id: str,
    ) -> bool:
        """
        Deactivate a referral code.

        Args:
            code: The code to deactivate
            referrer_id: Must match the code owner

        Returns:
            True if deactivated, False if not found or unauthorized
        """
        code = code.strip().upper()
        referral_code = self._codes.get(code)

        if not referral_code:
            if self.db_client:
                result = self.db_client.table("referral_codes").select(
                    "*"
                ).eq("code", code).single().execute()
                if result.data:
                    referral_code = ReferralCode(
                        code=result.data["code"],
                        referrer_id=result.data["referrer_id"],
                        created_at=datetime.fromisoformat(result.data["created_at"]),
                        is_active=result.data.get("is_active", True),
                    )
                    self._codes[code] = referral_code

        if not referral_code:
            return False

        if referral_code.referrer_id != referrer_id:
            logger.warning(
                f"Unauthorized deactivation attempt: {code} by {referrer_id}"
            )
            return False

        referral_code.is_active = False

        if self.db_client:
            self.db_client.table("referral_codes").update({
                "is_active": False,
            }).eq("code", code).execute()

        logger.info(f"Referral code deactivated: {code}")
        return True

    async def expire_old_referrals(self) -> int:
        """
        Expire referrals that have passed their expiration date.

        Called periodically by a background job.

        Returns:
            Number of referrals expired
        """
        now = datetime.now(timezone.utc)
        expired_count = 0

        if self.db_client:
            # Update all expired referrals in database
            result = self.db_client.table("referrals").update({
                "status": ReferralStatus.EXPIRED.value,
            }).lt("expires_at", now.isoformat()).in_(
                "status", [ReferralStatus.PENDING.value, ReferralStatus.QUALIFYING.value]
            ).execute()

            expired_count = len(result.data) if result.data else 0
        else:
            # Update in-memory
            for referral in self._referrals.values():
                if (referral.status in [ReferralStatus.PENDING, ReferralStatus.QUALIFYING]
                    and referral.is_expired):
                    referral.status = ReferralStatus.EXPIRED
                    expired_count += 1

        if expired_count > 0:
            logger.info(f"Expired {expired_count} referrals")

        return expired_count

    async def get_program_stats(self) -> Dict[str, Any]:
        """
        Get overall referral program statistics.

        Returns:
            Dict with program-wide metrics
        """
        if self.db_client:
            # Get counts by status
            total_result = self.db_client.table("referrals").select(
                "id", count="exact"
            ).execute()

            completed_result = self.db_client.table("referrals").select(
                "id", count="exact"
            ).eq("status", ReferralStatus.COMPLETED.value).execute()

            pending_result = self.db_client.table("referrals").select(
                "id", count="exact"
            ).in_("status", [
                ReferralStatus.PENDING.value,
                ReferralStatus.QUALIFYING.value
            ]).execute()

            # Get total bonuses paid
            paid_result = self.db_client.table("referrals").select(
                "bonus_amount"
            ).eq("bonus_paid", True).execute()

            total_paid = sum(
                r.get("bonus_amount", 0) for r in (paid_result.data or [])
            )

            # Get active codes count
            codes_result = self.db_client.table("referral_codes").select(
                "code", count="exact"
            ).eq("is_active", True).execute()

            return {
                "total_referrals": total_result.count or 0,
                "completed_referrals": completed_result.count or 0,
                "pending_referrals": pending_result.count or 0,
                "total_bonuses_paid": total_paid,
                "active_codes": codes_result.count or 0,
                "conversion_rate": (
                    ((completed_result.count or 0) / (total_result.count or 1)) * 100
                ),
                "config": {
                    "tasks_required": self.config.tasks_required,
                    "bonus_range": f"${self.config.bonus_amount_min:.2f}-${self.config.bonus_amount_max:.2f}",
                    "expiry_days": self.config.expiry_days,
                },
            }
        else:
            # In-memory stats
            referrals = list(self._referrals.values())
            codes = list(self._codes.values())

            completed = [r for r in referrals if r.status == ReferralStatus.COMPLETED]
            pending = [r for r in referrals if r.status in [
                ReferralStatus.PENDING, ReferralStatus.QUALIFYING
            ]]

            return {
                "total_referrals": len(referrals),
                "completed_referrals": len(completed),
                "pending_referrals": len(pending),
                "total_bonuses_paid": sum(r.bonus_amount for r in completed if r.bonus_paid),
                "active_codes": sum(1 for c in codes if c.is_valid),
                "conversion_rate": (
                    (len(completed) / len(referrals)) * 100 if referrals else 0
                ),
                "config": {
                    "tasks_required": self.config.tasks_required,
                    "bonus_range": f"${self.config.bonus_amount_min:.2f}-${self.config.bonus_amount_max:.2f}",
                    "expiry_days": self.config.expiry_days,
                },
            }


# Convenience functions

async def create_referral_code(
    referrer_id: str,
    bonus_amount: float = 2.00,
) -> ReferralCode:
    """
    Create a referral code for a worker.

    Args:
        referrer_id: Worker ID
        bonus_amount: Bonus amount in USD

    Returns:
        ReferralCode object
    """
    manager = ReferralManager()
    return await manager.generate_code(referrer_id, bonus_amount=bonus_amount)


async def apply_referral_code(
    code: str,
    referee_id: str,
) -> Optional[Referral]:
    """
    Apply a referral code during signup.

    Args:
        code: Referral code
        referee_id: New worker's ID

    Returns:
        Referral object or None
    """
    manager = ReferralManager()
    return await manager.apply_code(code, referee_id)


async def check_referral_bonus(worker_id: str) -> Optional[Referral]:
    """
    Check and process referral bonus after task completion.

    Args:
        worker_id: Worker who completed a task

    Returns:
        Updated Referral if applicable
    """
    manager = ReferralManager()
    return await manager.record_task_completion(worker_id)
