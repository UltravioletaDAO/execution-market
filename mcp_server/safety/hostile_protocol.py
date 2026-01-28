"""
Hostile Meatspace Protocol (NOW-113)

Handles situations where physical task completion faces obstacles.

This module provides:
- Obstacle reporting and verification
- Proof of attempt validation
- Compensation for legitimate obstacles
- Safety-first approach to hostile environments

Philosophy:
Workers should never feel pressured to complete tasks in unsafe conditions.
If a legitimate obstacle prevents completion, workers receive fair compensation
for their time and effort in attempting the task.
"""

import logging
import uuid
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class ObstacleType(str, Enum):
    """Types of obstacles that can prevent task completion."""
    ACCESS_DENIED = "access_denied"           # Couldn't access location
    LOCATION_CLOSED = "location_closed"       # Business/location closed
    HOSTILE_ENVIRONMENT = "hostile_environment"  # Unsafe/threatening situation
    WEATHER_BLOCKED = "weather_blocked"       # Weather prevents completion
    UNSAFE_CONDITIONS = "unsafe_conditions"   # Physical hazards
    TARGET_NOT_FOUND = "target_not_found"     # Subject of task not present
    EQUIPMENT_FAILURE = "equipment_failure"   # Camera/phone issues
    MEDICAL_EMERGENCY = "medical_emergency"   # Worker health issue
    LEGAL_RESTRICTION = "legal_restriction"   # Police/security intervention
    TRANSPORTATION_ISSUE = "transportation_issue"  # Couldn't reach location


class CompensationTier(str, Enum):
    """Tiers of compensation for obstacles."""
    NONE = "none"           # No compensation (e.g., worker didn't attempt)
    MINIMAL = "minimal"     # Token compensation (e.g., target not found)
    PARTIAL = "partial"     # Partial compensation (e.g., access denied)
    SUBSTANTIAL = "substantial"  # Higher compensation (e.g., hostile environment)
    FULL = "full"           # Full bounty (e.g., task impossible by design)


class VerificationStatus(str, Enum):
    """Status of obstacle verification."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    REQUIRES_ESCALATION = "requires_escalation"


class EvidenceType(str, Enum):
    """Types of evidence for proof of attempt."""
    PHOTO = "photo"
    VIDEO = "video"
    GPS_TRACK = "gps_track"
    TIMESTAMP = "timestamp"
    SCREENSHOT = "screenshot"
    AUDIO = "audio"
    WITNESS = "witness"
    RECEIPT = "receipt"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ProofOfAttempt:
    """Evidence that worker genuinely attempted the task."""
    worker_id: str
    task_id: str
    evidence_type: EvidenceType
    evidence_url: Optional[str]
    evidence_data: Dict[str, Any]
    gps_coordinates: Optional[Tuple[float, float]]
    timestamp: datetime
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "worker_id": self.worker_id,
            "task_id": self.task_id,
            "evidence_type": self.evidence_type.value,
            "evidence_url": self.evidence_url,
            "evidence_data": self.evidence_data,
            "gps_coordinates": self.gps_coordinates,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
        }


@dataclass
class ObstacleReport:
    """Report of an obstacle preventing task completion."""
    id: str
    task_id: str
    worker_id: str
    obstacle_type: ObstacleType
    description: str
    evidence: List[ProofOfAttempt]
    reported_at: datetime
    location: Optional[Tuple[float, float]] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verified: bool = False
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    compensation_awarded: float = 0.0
    compensation_tier: CompensationTier = CompensationTier.NONE
    rejection_reason: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "obstacle_type": self.obstacle_type.value,
            "description": self.description,
            "evidence": [e.to_dict() for e in self.evidence],
            "location": self.location,
            "reported_at": self.reported_at.isoformat(),
            "verification_status": self.verification_status.value,
            "verified": self.verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_by": self.verified_by,
            "compensation_awarded": self.compensation_awarded,
            "compensation_tier": self.compensation_tier.value,
            "rejection_reason": self.rejection_reason,
            "notes": self.notes,
            "metadata": self.metadata,
        }


@dataclass
class CompensationDecision:
    """Decision on compensation for an obstacle report."""
    report_id: str
    approved: bool
    compensation_tier: CompensationTier
    compensation_amount: float
    compensation_percentage: float
    reason: str
    decided_at: datetime
    decided_by: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "approved": self.approved,
            "compensation_tier": self.compensation_tier.value,
            "compensation_amount": self.compensation_amount,
            "compensation_percentage": self.compensation_percentage,
            "reason": self.reason,
            "decided_at": self.decided_at.isoformat(),
            "decided_by": self.decided_by,
        }


@dataclass
class SafetyScore:
    """Safety score for a task/location combination."""
    task_id: str
    score: float  # 0.0 (unsafe) to 1.0 (safe)
    factors: Dict[str, float]
    warnings: List[str]
    recommendations: List[str]
    calculated_at: datetime


# =============================================================================
# CONSTANTS
# =============================================================================


# Compensation percentages by obstacle type (% of bounty)
OBSTACLE_COMPENSATION: Dict[ObstacleType, float] = {
    ObstacleType.ACCESS_DENIED: 0.20,           # Worker went there but couldn't enter
    ObstacleType.LOCATION_CLOSED: 0.15,         # Business unexpectedly closed
    ObstacleType.HOSTILE_ENVIRONMENT: 0.30,     # Unsafe situation, higher compensation
    ObstacleType.WEATHER_BLOCKED: 0.10,         # Weather is often predictable
    ObstacleType.UNSAFE_CONDITIONS: 0.30,       # Physical hazards = higher compensation
    ObstacleType.TARGET_NOT_FOUND: 0.10,        # Subject not present
    ObstacleType.EQUIPMENT_FAILURE: 0.05,       # Worker's equipment issue
    ObstacleType.MEDICAL_EMERGENCY: 0.25,       # Health issues
    ObstacleType.LEGAL_RESTRICTION: 0.25,       # Police/security stopped them
    ObstacleType.TRANSPORTATION_ISSUE: 0.05,   # Couldn't get there
}

# Minimum evidence required by obstacle type
REQUIRED_EVIDENCE: Dict[ObstacleType, List[EvidenceType]] = {
    ObstacleType.ACCESS_DENIED: [EvidenceType.PHOTO, EvidenceType.GPS_TRACK],
    ObstacleType.LOCATION_CLOSED: [EvidenceType.PHOTO, EvidenceType.TIMESTAMP],
    ObstacleType.HOSTILE_ENVIRONMENT: [EvidenceType.GPS_TRACK],  # Don't require photos in hostile situations
    ObstacleType.WEATHER_BLOCKED: [EvidenceType.PHOTO],
    ObstacleType.UNSAFE_CONDITIONS: [EvidenceType.PHOTO, EvidenceType.GPS_TRACK],
    ObstacleType.TARGET_NOT_FOUND: [EvidenceType.PHOTO, EvidenceType.GPS_TRACK],
    ObstacleType.EQUIPMENT_FAILURE: [EvidenceType.SCREENSHOT],
    ObstacleType.MEDICAL_EMERGENCY: [],  # No evidence required for medical
    ObstacleType.LEGAL_RESTRICTION: [EvidenceType.GPS_TRACK],
    ObstacleType.TRANSPORTATION_ISSUE: [EvidenceType.GPS_TRACK],
}

# Automatic verification thresholds
AUTO_VERIFY_THRESHOLD = 0.85  # Confidence threshold for auto-verification
MAX_REPORTS_PER_WORKER_PER_DAY = 5  # Anti-abuse limit
ESCALATION_BOUNTY_THRESHOLD = 100.0  # High-value tasks require manual review


# =============================================================================
# HOSTILE PROTOCOL MANAGER
# =============================================================================


class HostileProtocolManager:
    """
    Manages hostile environment situations and obstacle compensation.

    This class handles:
    - Receiving and validating obstacle reports
    - Verifying proof of attempt
    - Calculating fair compensation
    - Tracking patterns for fraud detection
    - Protecting workers in unsafe situations

    Philosophy:
    Workers should NEVER feel pressured to complete tasks in unsafe conditions.
    The protocol is designed to:
    1. Make it easy to report legitimate obstacles
    2. Provide fair compensation for genuine attempts
    3. Prevent abuse through evidence requirements and pattern detection
    4. Prioritize worker safety over task completion

    Usage:
        manager = HostileProtocolManager()

        # Worker reports obstacle
        report = await manager.report_obstacle(
            task_id="task-123",
            worker_id="worker-456",
            obstacle_type=ObstacleType.ACCESS_DENIED,
            description="Gate was locked, no answer at intercom",
            evidence=[
                ProofOfAttempt(
                    worker_id="worker-456",
                    task_id="task-123",
                    evidence_type=EvidenceType.PHOTO,
                    evidence_url="https://...",
                    evidence_data={"shows": "locked_gate"},
                    gps_coordinates=(40.7128, -74.0060),
                    timestamp=datetime.now(UTC),
                    description="Photo of locked gate"
                )
            ]
        )

        # System verifies and awards compensation
        if report.verified:
            compensation = report.compensation_awarded
    """

    def __init__(
        self,
        task_service: Optional[Any] = None,
        payment_service: Optional[Any] = None,
        ai_verification_service: Optional[Any] = None,
    ):
        """
        Initialize hostile protocol manager.

        Args:
            task_service: Service to get task details.
                Should implement: async get_task(task_id) -> Dict
            payment_service: Service to process payments.
                Should implement: async release_partial(task_id, worker_id, amount) -> bool
            ai_verification_service: Optional AI service for evidence verification.
                Should implement: async verify_evidence(evidence, obstacle_type) -> float
        """
        self.task_service = task_service
        self.payment_service = payment_service
        self.ai_verification_service = ai_verification_service

        # In-memory storage (use database in production)
        self._reports: Dict[str, ObstacleReport] = {}
        self._worker_reports_today: Dict[str, List[datetime]] = {}

    async def report_obstacle(
        self,
        task_id: str,
        worker_id: str,
        obstacle_type: ObstacleType,
        description: str,
        evidence: List[ProofOfAttempt],
        location: Optional[Tuple[float, float]] = None,
    ) -> ObstacleReport:
        """
        Report an obstacle preventing task completion.

        Args:
            task_id: ID of the task
            worker_id: ID of the worker reporting
            obstacle_type: Type of obstacle encountered
            description: Detailed description of the situation
            evidence: List of proof of attempt evidence
            location: GPS coordinates where obstacle was encountered

        Returns:
            ObstacleReport with initial status

        Raises:
            ValueError: If validation fails
        """
        # Validate report
        validation_errors = await self._validate_report(
            task_id, worker_id, obstacle_type, evidence
        )
        if validation_errors:
            raise ValueError(f"Invalid obstacle report: {'; '.join(validation_errors)}")

        # Check rate limits
        if not self._check_rate_limit(worker_id):
            raise ValueError(
                f"Rate limit exceeded. Maximum {MAX_REPORTS_PER_WORKER_PER_DAY} "
                "obstacle reports per day."
            )

        # Create report
        report_id = f"obst_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)

        report = ObstacleReport(
            id=report_id,
            task_id=task_id,
            worker_id=worker_id,
            obstacle_type=obstacle_type,
            description=description,
            evidence=evidence,
            reported_at=now,
            location=location,
            verification_status=VerificationStatus.PENDING,
        )

        # Store report
        self._reports[report_id] = report

        # Record for rate limiting
        self._record_report(worker_id)

        logger.info(
            f"Obstacle report created: {report_id} for task {task_id} "
            f"(type: {obstacle_type.value})"
        )

        # Attempt automatic verification for simple cases
        await self._attempt_auto_verification(report)

        return report

    async def verify_obstacle(
        self,
        report_id: str,
        verifier_id: Optional[str] = None,
    ) -> bool:
        """
        Verify an obstacle claim.

        Combines automated checks with optional manual review.

        Args:
            report_id: ID of the obstacle report
            verifier_id: Optional ID of manual verifier

        Returns:
            True if obstacle is verified
        """
        report = self._reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        # Calculate verification confidence
        confidence = await self._calculate_verification_confidence(report)

        # High confidence = auto-verify
        if confidence >= AUTO_VERIFY_THRESHOLD:
            report.verified = True
            report.verification_status = VerificationStatus.VERIFIED
            report.verified_at = datetime.now(UTC)
            report.verified_by = "system_auto"
            report.notes.append(
                f"Auto-verified with {confidence:.2%} confidence"
            )
            logger.info(f"Report {report_id} auto-verified (confidence: {confidence:.2%})")

        # Low confidence + high bounty = escalate
        elif confidence < 0.5:
            report.verification_status = VerificationStatus.REQUIRES_ESCALATION
            report.notes.append(
                f"Escalated for manual review (confidence: {confidence:.2%})"
            )
            logger.info(f"Report {report_id} escalated for review")

        # Manual verification
        elif verifier_id:
            report.verified = True
            report.verification_status = VerificationStatus.VERIFIED
            report.verified_at = datetime.now(UTC)
            report.verified_by = verifier_id
            report.notes.append(f"Manually verified by {verifier_id}")
            logger.info(f"Report {report_id} manually verified by {verifier_id}")

        else:
            report.verification_status = VerificationStatus.UNDER_REVIEW
            report.notes.append("Awaiting manual review")

        return report.verified

    async def reject_obstacle(
        self,
        report_id: str,
        reason: str,
        rejector_id: str,
    ) -> ObstacleReport:
        """
        Reject an obstacle claim.

        Args:
            report_id: ID of the obstacle report
            reason: Reason for rejection
            rejector_id: ID of the person rejecting

        Returns:
            Updated ObstacleReport
        """
        report = self._reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        report.verified = False
        report.verification_status = VerificationStatus.REJECTED
        report.rejection_reason = reason
        report.verified_at = datetime.now(UTC)
        report.verified_by = rejector_id
        report.notes.append(f"Rejected by {rejector_id}: {reason}")

        logger.info(f"Report {report_id} rejected: {reason}")

        return report

    async def award_compensation(
        self,
        report_id: str,
        bounty_amount: Optional[float] = None,
    ) -> CompensationDecision:
        """
        Award compensation for a verified obstacle.

        Args:
            report_id: ID of the obstacle report
            bounty_amount: Optional override for task bounty amount

        Returns:
            CompensationDecision with details
        """
        report = self._reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        if not report.verified:
            raise ValueError("Cannot award compensation for unverified obstacle")

        # Get task bounty
        if bounty_amount is None:
            task = await self._get_task(report.task_id)
            bounty_amount = task.get("bounty_usd", 0)

        # Calculate compensation
        base_percentage = OBSTACLE_COMPENSATION.get(report.obstacle_type, 0.10)

        # Adjust percentage based on evidence quality
        evidence_quality = await self._assess_evidence_quality(report.evidence)
        adjusted_percentage = base_percentage * (0.5 + 0.5 * evidence_quality)

        # Calculate amount
        compensation_amount = bounty_amount * adjusted_percentage

        # Determine tier
        compensation_tier = self._determine_compensation_tier(adjusted_percentage)

        # Create decision
        decision = CompensationDecision(
            report_id=report_id,
            approved=True,
            compensation_tier=compensation_tier,
            compensation_amount=round(compensation_amount, 2),
            compensation_percentage=round(adjusted_percentage * 100, 1),
            reason=f"Obstacle type: {report.obstacle_type.value}, "
                   f"evidence quality: {evidence_quality:.2%}",
            decided_at=datetime.now(UTC),
            decided_by="system",
        )

        # Update report
        report.compensation_awarded = decision.compensation_amount
        report.compensation_tier = compensation_tier

        # Process payment if service available
        if self.payment_service and compensation_amount > 0:
            try:
                await self.payment_service.release_partial(
                    task_id=report.task_id,
                    worker_id=report.worker_id,
                    amount=compensation_amount,
                )
                report.notes.append(
                    f"Compensation of ${compensation_amount:.2f} released"
                )
            except Exception as e:
                logger.error(f"Failed to release compensation: {e}")
                report.notes.append(f"Payment failed: {e}")

        logger.info(
            f"Compensation awarded for report {report_id}: "
            f"${compensation_amount:.2f} ({adjusted_percentage:.1%} of bounty)"
        )

        return decision

    async def get_report(self, report_id: str) -> Optional[ObstacleReport]:
        """Get an obstacle report by ID."""
        return self._reports.get(report_id)

    async def get_reports_for_task(self, task_id: str) -> List[ObstacleReport]:
        """Get all obstacle reports for a task."""
        return [r for r in self._reports.values() if r.task_id == task_id]

    async def get_reports_for_worker(
        self,
        worker_id: str,
        include_rejected: bool = False,
    ) -> List[ObstacleReport]:
        """Get all obstacle reports for a worker."""
        reports = [r for r in self._reports.values() if r.worker_id == worker_id]

        if not include_rejected:
            reports = [
                r for r in reports
                if r.verification_status != VerificationStatus.REJECTED
            ]

        return reports

    def calculate_safety_score(
        self,
        task_id: str,
        location: Tuple[float, float],
        task_time: datetime,
    ) -> SafetyScore:
        """
        Calculate safety score for a task.

        Uses historical obstacle reports and other factors.

        Args:
            task_id: Task ID
            location: Task location
            task_time: Planned execution time

        Returns:
            SafetyScore with assessment
        """
        factors: Dict[str, float] = {}
        warnings: List[str] = []
        recommendations: List[str] = []

        # Check obstacle history at this location
        location_reports = self._get_reports_near_location(location)
        if location_reports:
            # Calculate factor based on report types
            hostile_count = sum(
                1 for r in location_reports
                if r.obstacle_type in [
                    ObstacleType.HOSTILE_ENVIRONMENT,
                    ObstacleType.UNSAFE_CONDITIONS,
                ]
            )
            access_issues = sum(
                1 for r in location_reports
                if r.obstacle_type == ObstacleType.ACCESS_DENIED
            )

            if hostile_count > 0:
                factors["historical_hostility"] = min(1.0, hostile_count * 0.3)
                warnings.append(
                    f"{hostile_count} hostile environment reports at this location."
                )
                recommendations.append("Consider buddy system for this location.")

            if access_issues > 2:
                factors["access_history"] = min(1.0, access_issues * 0.2)
                warnings.append(f"Frequent access issues ({access_issues} reports).")

        # Time-based factors
        hour = task_time.hour
        if hour < 6 or hour >= 22:
            factors["night_risk"] = 0.4
            warnings.append("Task scheduled during night hours.")
            recommendations.append("Consider rescheduling to daylight hours.")

        # Calculate overall score (higher = safer)
        risk_sum = sum(factors.values())
        safety_score = max(0.0, 1.0 - (risk_sum / max(len(factors), 1)))

        return SafetyScore(
            task_id=task_id,
            score=safety_score,
            factors=factors,
            warnings=warnings,
            recommendations=recommendations,
            calculated_at=datetime.now(UTC),
        )

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    async def _validate_report(
        self,
        task_id: str,
        worker_id: str,
        obstacle_type: ObstacleType,
        evidence: List[ProofOfAttempt],
    ) -> List[str]:
        """Validate an obstacle report."""
        errors: List[str] = []

        # Check required evidence
        required = REQUIRED_EVIDENCE.get(obstacle_type, [])
        provided = {e.evidence_type for e in evidence}

        missing = set(required) - provided
        if missing:
            errors.append(
                f"Missing required evidence: {[e.value for e in missing]}"
            )

        # Validate evidence timestamps
        now = datetime.now(UTC)
        for e in evidence:
            if e.timestamp.tzinfo is None:
                e.timestamp = e.timestamp.replace(tzinfo=UTC)
            age = (now - e.timestamp).total_seconds()
            if age > 3600:  # 1 hour old
                errors.append(f"Evidence too old: {e.evidence_type.value}")

        return errors

    def _check_rate_limit(self, worker_id: str) -> bool:
        """Check if worker has exceeded daily report limit."""
        today_reports = self._worker_reports_today.get(worker_id, [])

        # Clean old entries
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_reports = [t for t in today_reports if t >= today_start]
        self._worker_reports_today[worker_id] = today_reports

        return len(today_reports) < MAX_REPORTS_PER_WORKER_PER_DAY

    def _record_report(self, worker_id: str) -> None:
        """Record report for rate limiting."""
        if worker_id not in self._worker_reports_today:
            self._worker_reports_today[worker_id] = []
        self._worker_reports_today[worker_id].append(datetime.now(UTC))

    async def _attempt_auto_verification(self, report: ObstacleReport) -> None:
        """Attempt automatic verification for simple cases."""
        confidence = await self._calculate_verification_confidence(report)

        if confidence >= AUTO_VERIFY_THRESHOLD:
            await self.verify_obstacle(report.id)

            # Get bounty and award compensation
            task = await self._get_task(report.task_id)
            bounty = task.get("bounty_usd", 0) if task else 0

            if bounty > 0:
                await self.award_compensation(report.id, bounty)

    async def _calculate_verification_confidence(
        self,
        report: ObstacleReport,
    ) -> float:
        """Calculate confidence in obstacle claim."""
        scores: List[float] = []

        # 1. Evidence completeness
        required = REQUIRED_EVIDENCE.get(report.obstacle_type, [])
        if not required:
            scores.append(0.8)  # No evidence required = high base confidence
        else:
            provided = {e.evidence_type for e in report.evidence}
            completeness = len(provided & set(required)) / len(required)
            scores.append(completeness)

        # 2. GPS verification (if GPS evidence provided)
        gps_evidence = [e for e in report.evidence if e.gps_coordinates]
        if gps_evidence:
            # Check if GPS is near reported location
            if report.location:
                for e in gps_evidence:
                    distance = self._haversine_distance(
                        report.location[0], report.location[1],
                        e.gps_coordinates[0], e.gps_coordinates[1]
                    )
                    if distance < 100:  # Within 100 meters
                        scores.append(0.9)
                    elif distance < 500:
                        scores.append(0.7)
                    else:
                        scores.append(0.3)

        # 3. Timestamp freshness
        now = datetime.now(UTC)
        ages = [(now - e.timestamp).total_seconds() / 60 for e in report.evidence]
        if ages:
            avg_age_minutes = sum(ages) / len(ages)
            if avg_age_minutes < 5:
                scores.append(0.95)
            elif avg_age_minutes < 15:
                scores.append(0.85)
            elif avg_age_minutes < 60:
                scores.append(0.7)
            else:
                scores.append(0.4)

        # 4. AI verification (if available)
        if self.ai_verification_service and report.evidence:
            try:
                ai_score = await self.ai_verification_service.verify_evidence(
                    report.evidence, report.obstacle_type
                )
                scores.append(ai_score)
            except Exception as e:
                logger.warning(f"AI verification failed: {e}")

        # 5. Worker history factor
        worker_reports = await self.get_reports_for_worker(report.worker_id)
        verified_count = sum(1 for r in worker_reports if r.verified)
        rejected_count = sum(
            1 for r in worker_reports
            if r.verification_status == VerificationStatus.REJECTED
        )

        if verified_count + rejected_count > 0:
            history_score = verified_count / (verified_count + rejected_count)
            scores.append(0.5 + 0.5 * history_score)

        # Calculate weighted average
        if not scores:
            return 0.5

        return sum(scores) / len(scores)

    async def _assess_evidence_quality(
        self,
        evidence: List[ProofOfAttempt],
    ) -> float:
        """Assess the quality of provided evidence."""
        if not evidence:
            return 0.0

        quality_scores: List[float] = []

        for e in evidence:
            score = 0.5  # Base score

            # GPS evidence is valuable
            if e.gps_coordinates:
                score += 0.2

            # Photo/video evidence
            if e.evidence_type in [EvidenceType.PHOTO, EvidenceType.VIDEO]:
                score += 0.2

            # Fresh timestamp
            if e.timestamp.tzinfo is None:
                e.timestamp = e.timestamp.replace(tzinfo=UTC)
            age_minutes = (datetime.now(UTC) - e.timestamp).total_seconds() / 60
            if age_minutes < 10:
                score += 0.1

            quality_scores.append(min(1.0, score))

        return sum(quality_scores) / len(quality_scores)

    def _determine_compensation_tier(self, percentage: float) -> CompensationTier:
        """Determine compensation tier from percentage."""
        if percentage >= 0.5:
            return CompensationTier.FULL
        elif percentage >= 0.25:
            return CompensationTier.SUBSTANTIAL
        elif percentage >= 0.10:
            return CompensationTier.PARTIAL
        elif percentage > 0:
            return CompensationTier.MINIMAL
        else:
            return CompensationTier.NONE

    async def _get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details."""
        if self.task_service:
            try:
                return await self.task_service.get_task(task_id) or {}
            except Exception as e:
                logger.error(f"Failed to get task {task_id}: {e}")
        return {}

    def _get_reports_near_location(
        self,
        location: Tuple[float, float],
        radius_meters: float = 500,
    ) -> List[ObstacleReport]:
        """Get obstacle reports near a location."""
        nearby: List[ObstacleReport] = []

        for report in self._reports.values():
            if report.location:
                distance = self._haversine_distance(
                    location[0], location[1],
                    report.location[0], report.location[1]
                )
                if distance <= radius_meters:
                    nearby.append(report)

        return nearby

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
    ) -> float:
        """Calculate distance in meters between two coordinates."""
        import math

        R = 6371000  # Earth radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    # =========================================================================
    # ADMIN METHODS
    # =========================================================================

    def clear_reports(self) -> None:
        """Clear all reports (admin/testing only)."""
        self._reports.clear()
        self._worker_reports_today.clear()

    def get_all_pending_reports(self) -> List[ObstacleReport]:
        """Get all reports pending review (admin)."""
        return [
            r for r in self._reports.values()
            if r.verification_status in [
                VerificationStatus.PENDING,
                VerificationStatus.UNDER_REVIEW,
                VerificationStatus.REQUIRES_ESCALATION,
            ]
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get obstacle report statistics (admin)."""
        reports = list(self._reports.values())

        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        total_compensation = 0.0

        for r in reports:
            by_type[r.obstacle_type.value] = by_type.get(r.obstacle_type.value, 0) + 1
            by_status[r.verification_status.value] = by_status.get(r.verification_status.value, 0) + 1
            total_compensation += r.compensation_awarded

        verified_count = sum(1 for r in reports if r.verified)
        verification_rate = verified_count / len(reports) if reports else 0

        return {
            "total_reports": len(reports),
            "by_type": by_type,
            "by_status": by_status,
            "verification_rate": verification_rate,
            "total_compensation_awarded": total_compensation,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def report_obstacle_quick(
    task_id: str,
    worker_id: str,
    obstacle_type: str,
    description: str,
    photo_url: Optional[str] = None,
    gps: Optional[Tuple[float, float]] = None,
) -> ObstacleReport:
    """
    Quick obstacle reporting with minimal parameters.

    Convenience function for simple cases.

    Args:
        task_id: Task ID
        worker_id: Worker ID
        obstacle_type: Obstacle type string
        description: Description of obstacle
        photo_url: Optional photo URL
        gps: Optional GPS coordinates

    Returns:
        ObstacleReport
    """
    manager = HostileProtocolManager()

    # Parse obstacle type
    try:
        obs_type = ObstacleType(obstacle_type)
    except ValueError:
        obs_type = ObstacleType.ACCESS_DENIED

    # Build evidence
    evidence: List[ProofOfAttempt] = []

    if gps:
        evidence.append(ProofOfAttempt(
            worker_id=worker_id,
            task_id=task_id,
            evidence_type=EvidenceType.GPS_TRACK,
            evidence_url=None,
            evidence_data={"coordinates": gps},
            gps_coordinates=gps,
            timestamp=datetime.now(UTC),
            description="GPS location at obstacle",
        ))

    if photo_url:
        evidence.append(ProofOfAttempt(
            worker_id=worker_id,
            task_id=task_id,
            evidence_type=EvidenceType.PHOTO,
            evidence_url=photo_url,
            evidence_data={},
            gps_coordinates=gps,
            timestamp=datetime.now(UTC),
            description="Photo evidence",
        ))

    return await manager.report_obstacle(
        task_id=task_id,
        worker_id=worker_id,
        obstacle_type=obs_type,
        description=description,
        evidence=evidence,
        location=gps,
    )
