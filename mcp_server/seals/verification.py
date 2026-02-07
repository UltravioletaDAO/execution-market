"""
Seal Verification

Handles verification of seals for various use cases:
- Verify a worker has required seals for a task
- Verify seal authenticity (on-chain validation)
- Gate access to premium tasks based on seals
- Generate verification proofs for external systems

Verification Contexts:
1. TASK_ACCEPTANCE: Worker applying for task needs specific seals
2. PROFILE_VIEW: Displaying verified seals on profile
3. EXTERNAL_API: Third-party verification requests
4. PAYMENT_ROUTING: Seals affecting payment terms
"""

import logging
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, UTC
from dataclasses import dataclass

from .types import (
    SealStatus,
    get_requirement,
)
from .registry import SealRegistry, MockSealRegistry

logger = logging.getLogger(__name__)


@dataclass
class VerificationContext:
    """Context for seal verification request."""

    purpose: str  # e.g., "task_acceptance", "profile_view"
    requester_id: Optional[str] = None
    task_id: Optional[str] = None
    additional_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


@dataclass
class SealVerificationResult:
    """Result of verifying a single seal."""

    seal_type: str
    is_valid: bool
    status: SealStatus
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    verification_details: Dict[str, Any] = None

    def __post_init__(self):
        if self.verification_details is None:
            self.verification_details = {}


@dataclass
class TaskSealRequirement:
    """Seal requirements for a task."""

    required_seals: List[str]  # Must have all of these
    preferred_seals: List[str]  # Nice to have (affects ranking)
    any_of_seals: List[str]  # Must have at least one of these


@dataclass
class TaskEligibilityResult:
    """Result of checking worker eligibility for a task."""

    is_eligible: bool
    missing_required: List[str]
    has_preferred: List[str]
    missing_preferred: List[str]
    satisfied_any_of: bool
    eligibility_score: float  # 0-100, for ranking


class SealVerificationService:
    """
    Service for verifying seals.

    Handles all seal verification operations including:
    - Single seal verification
    - Task eligibility checking
    - Batch verification
    - Proof generation

    Example:
        >>> service = SealVerificationService(registry)
        >>> result = await service.verify_seal(
        ...     "0x1234...",
        ...     "photography_verified"
        ... )
        >>> if result.is_valid:
        ...     print("Seal verified!")
    """

    def __init__(self, registry: SealRegistry | MockSealRegistry):
        """
        Initialize verification service.

        Args:
            registry: SealRegistry instance for on-chain queries
        """
        self.registry = registry

    # =========================================================================
    # SINGLE SEAL VERIFICATION
    # =========================================================================

    async def verify_seal(
        self,
        holder_address: str,
        seal_type: str,
        context: Optional[VerificationContext] = None,
    ) -> SealVerificationResult:
        """
        Verify that a holder has a valid seal of the specified type.

        Args:
            holder_address: Worker's wallet address
            seal_type: Seal type to verify
            context: Optional verification context

        Returns:
            SealVerificationResult with validity and details
        """
        try:
            # Quick check first
            has_seal = await self.registry.has_seal(holder_address, seal_type)

            if not has_seal:
                return SealVerificationResult(
                    seal_type=seal_type,
                    is_valid=False,
                    status=SealStatus.PENDING,  # Never issued
                    verification_details={
                        "reason": "Seal not found",
                        "checked_at": datetime.now(UTC).isoformat(),
                    },
                )

            # Get full details
            details = await self.registry.get_seal_details(holder_address, seal_type)

            if not details:
                return SealVerificationResult(
                    seal_type=seal_type,
                    is_valid=False,
                    status=SealStatus.PENDING,
                    verification_details={"reason": "Could not retrieve details"},
                )

            # Determine status
            if not details["is_active"]:
                status = SealStatus.REVOKED
                is_valid = False
            elif details["expires_at"]:
                expires_at = datetime.fromisoformat(details["expires_at"])
                if datetime.now(UTC) > expires_at:
                    status = SealStatus.EXPIRED
                    is_valid = False
                else:
                    status = SealStatus.ACTIVE
                    is_valid = True
            else:
                status = SealStatus.ACTIVE
                is_valid = True

            return SealVerificationResult(
                seal_type=seal_type,
                is_valid=is_valid,
                status=status,
                issued_at=datetime.fromisoformat(details["issued_at"])
                if details.get("issued_at")
                else None,
                expires_at=datetime.fromisoformat(details["expires_at"])
                if details.get("expires_at")
                else None,
                verification_details={
                    "issuer": details.get("issuer"),
                    "metadata_hash": details.get("metadata_hash"),
                    "checked_at": datetime.now(UTC).isoformat(),
                    "context": context.purpose if context else None,
                },
            )

        except Exception as e:
            logger.error(f"Error verifying seal: {e}")
            return SealVerificationResult(
                seal_type=seal_type,
                is_valid=False,
                status=SealStatus.PENDING,
                verification_details={"error": str(e)},
            )

    async def verify_multiple_seals(
        self,
        holder_address: str,
        seal_types: List[str],
        context: Optional[VerificationContext] = None,
    ) -> Dict[str, SealVerificationResult]:
        """
        Verify multiple seals at once.

        Args:
            holder_address: Worker's wallet address
            seal_types: List of seal types to verify
            context: Optional verification context

        Returns:
            Dict mapping seal type to verification result
        """
        results = {}

        for seal_type in seal_types:
            result = await self.verify_seal(holder_address, seal_type, context)
            results[seal_type] = result

        return results

    # =========================================================================
    # TASK ELIGIBILITY
    # =========================================================================

    async def check_task_eligibility(
        self,
        holder_address: str,
        requirements: TaskSealRequirement,
    ) -> TaskEligibilityResult:
        """
        Check if a worker is eligible for a task based on seal requirements.

        Args:
            holder_address: Worker's wallet address
            requirements: Task's seal requirements

        Returns:
            TaskEligibilityResult with eligibility details
        """
        # Get all worker's seals
        bundle = await self.registry.get_seal_bundle(holder_address)
        worker_seals: Set[str] = {
            seal.seal_type for seal in bundle.all_seals if seal.is_valid
        }

        # Check required seals
        required_set = set(requirements.required_seals)
        missing_required = list(required_set - worker_seals)

        # Check preferred seals
        preferred_set = set(requirements.preferred_seals)
        has_preferred = list(preferred_set & worker_seals)
        missing_preferred = list(preferred_set - worker_seals)

        # Check any_of seals
        any_of_set = set(requirements.any_of_seals)
        satisfied_any_of = (
            len(any_of_set) == 0  # No any_of requirement
            or len(any_of_set & worker_seals) > 0
        )

        # Determine overall eligibility
        is_eligible = len(missing_required) == 0 and satisfied_any_of

        # Calculate eligibility score for ranking
        score = 0.0
        if is_eligible:
            # Base score for meeting requirements
            score = 50.0

            # Bonus for preferred seals
            if len(requirements.preferred_seals) > 0:
                preferred_ratio = len(has_preferred) / len(requirements.preferred_seals)
                score += preferred_ratio * 50.0

        return TaskEligibilityResult(
            is_eligible=is_eligible,
            missing_required=missing_required,
            has_preferred=has_preferred,
            missing_preferred=missing_preferred,
            satisfied_any_of=satisfied_any_of,
            eligibility_score=score,
        )

    async def filter_eligible_workers(
        self,
        worker_addresses: List[str],
        requirements: TaskSealRequirement,
    ) -> List[Dict[str, Any]]:
        """
        Filter a list of workers to only those eligible for a task.

        Returns workers sorted by eligibility score.

        Args:
            worker_addresses: List of worker wallet addresses
            requirements: Task's seal requirements

        Returns:
            List of dicts with 'address', 'eligibility', sorted by score
        """
        results = []

        for address in worker_addresses:
            eligibility = await self.check_task_eligibility(address, requirements)

            if eligibility.is_eligible:
                results.append(
                    {
                        "address": address,
                        "eligibility": eligibility,
                    }
                )

        # Sort by score descending
        results.sort(key=lambda x: x["eligibility"].eligibility_score, reverse=True)

        return results

    # =========================================================================
    # PROOF GENERATION
    # =========================================================================

    async def generate_verification_proof(
        self,
        holder_address: str,
        seal_types: List[str],
        purpose: str,
    ) -> Dict[str, Any]:
        """
        Generate a verification proof for external systems.

        Creates a signed attestation that can be verified
        by third parties without direct blockchain access.

        Args:
            holder_address: Worker's wallet address
            seal_types: Seals to include in proof
            purpose: Purpose of the proof (for audit trail)

        Returns:
            Dict with proof data
        """
        verifications = await self.verify_multiple_seals(
            holder_address, seal_types, VerificationContext(purpose=purpose)
        )

        # Build proof
        proof = {
            "version": "1.0",
            "holder": holder_address,
            "purpose": purpose,
            "generated_at": datetime.now(UTC).isoformat(),
            "seals": [],
            "summary": {
                "total_requested": len(seal_types),
                "total_valid": 0,
                "total_invalid": 0,
            },
        }

        for seal_type, result in verifications.items():
            seal_data = {
                "type": seal_type,
                "valid": result.is_valid,
                "status": result.status.value,
            }

            if result.is_valid:
                proof["summary"]["total_valid"] += 1
                seal_data["issued_at"] = (
                    result.issued_at.isoformat() if result.issued_at else None
                )
                seal_data["expires_at"] = (
                    result.expires_at.isoformat() if result.expires_at else None
                )
            else:
                proof["summary"]["total_invalid"] += 1

            proof["seals"].append(seal_data)

        # Add overall validity
        proof["all_valid"] = proof["summary"]["total_invalid"] == 0

        return proof

    # =========================================================================
    # SEAL GATING
    # =========================================================================

    async def check_seal_gate(
        self,
        holder_address: str,
        gate_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check if holder passes a seal gate.

        Gates can be used for:
        - Premium task access
        - Higher payment tiers
        - Special features

        Gate config format:
        {
            "all": ["seal1", "seal2"],  # Must have all
            "any": ["seal3", "seal4"],   # Must have at least one
            "none": ["seal5"],           # Must not have
        }

        Args:
            holder_address: Worker's wallet address
            gate_config: Gate configuration

        Returns:
            Dict with pass status and details
        """
        bundle = await self.registry.get_seal_bundle(holder_address)
        worker_seals: Set[str] = {
            seal.seal_type for seal in bundle.all_seals if seal.is_valid
        }

        result = {"passed": True, "checks": []}

        # Check "all" condition
        if "all" in gate_config:
            required = set(gate_config["all"])
            missing = required - worker_seals
            passed = len(missing) == 0

            result["checks"].append(
                {
                    "type": "all",
                    "required": list(required),
                    "missing": list(missing),
                    "passed": passed,
                }
            )

            if not passed:
                result["passed"] = False

        # Check "any" condition
        if "any" in gate_config:
            any_of = set(gate_config["any"])
            has_any = len(any_of & worker_seals) > 0
            matched = list(any_of & worker_seals)

            result["checks"].append(
                {
                    "type": "any",
                    "required": list(any_of),
                    "matched": matched,
                    "passed": has_any,
                }
            )

            if not has_any:
                result["passed"] = False

        # Check "none" condition (must NOT have these)
        if "none" in gate_config:
            forbidden = set(gate_config["none"])
            has_forbidden = forbidden & worker_seals
            passed = len(has_forbidden) == 0

            result["checks"].append(
                {
                    "type": "none",
                    "forbidden": list(forbidden),
                    "has_forbidden": list(has_forbidden),
                    "passed": passed,
                }
            )

            if not passed:
                result["passed"] = False

        return result

    # =========================================================================
    # BATCH VERIFICATION
    # =========================================================================

    async def batch_verify_workers(
        self,
        verifications: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Batch verify multiple workers' seals.

        More efficient for bulk operations.

        Args:
            verifications: List of dicts with 'address' and 'seal_types'

        Returns:
            List of verification results
        """
        results = []

        for verification in verifications:
            address = verification["address"]
            seal_types = verification.get("seal_types", [])

            worker_results = await self.verify_multiple_seals(address, seal_types)

            results.append(
                {
                    "address": address,
                    "verifications": {
                        st: result.is_valid for st, result in worker_results.items()
                    },
                    "all_valid": all(r.is_valid for r in worker_results.values()),
                }
            )

        return results

    # =========================================================================
    # ANALYTICS
    # =========================================================================

    async def get_seal_statistics(
        self,
        holder_address: str,
    ) -> Dict[str, Any]:
        """
        Get statistics about a worker's seals.

        Args:
            holder_address: Worker's wallet address

        Returns:
            Dict with seal statistics
        """
        bundle = await self.registry.get_seal_bundle(holder_address)

        stats = {
            "holder": holder_address,
            "total_seals": bundle.total_count,
            "active_seals": bundle.active_count,
            "by_category": {
                "skill": {
                    "total": len(bundle.skill_seals),
                    "active": sum(1 for s in bundle.skill_seals if s.is_valid),
                },
                "work": {
                    "total": len(bundle.work_seals),
                    "active": sum(1 for s in bundle.work_seals if s.is_valid),
                },
                "behavior": {
                    "total": len(bundle.behavior_seals),
                    "active": sum(1 for s in bundle.behavior_seals if s.is_valid),
                },
            },
            "expiring_soon": [],
            "seal_list": [],
        }

        # Find expiring seals (within 30 days)
        for seal in bundle.all_seals:
            if seal.expires_at and seal.is_valid:
                days_until = (seal.expires_at - datetime.now(UTC)).days
                if 0 < days_until <= 30:
                    stats["expiring_soon"].append(
                        {
                            "seal_type": seal.seal_type,
                            "expires_in_days": days_until,
                        }
                    )

            # Add to seal list
            req = get_requirement(seal.seal_type)
            stats["seal_list"].append(
                {
                    "type": seal.seal_type,
                    "category": seal.category.value,
                    "display_name": req.display_name if req else seal.seal_type,
                    "status": seal.status.value,
                    "tier": req.tier if req else 1,
                }
            )

        return stats
