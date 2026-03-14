"""
Fraud Detector - Main Entry Point

Unified fraud detection for Execution Market submissions that combines:
- GPS spoofing detection
- Image manipulation detection
- Timing anomaly detection
- Behavioral analysis

This module orchestrates all fraud detection checks and returns
a unified FraudScore for each submission.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from .gps_antispoofing import GPSAntiSpoofing, GPSData, DeviceInfo, SensorData
from .image_analysis import ImageAnalyzer, ImageAnalysisResult
from .behavioral import BehavioralAnalyzer

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk levels for fraud detection."""

    LOW = "low"  # Normal submission, no concerns
    MEDIUM = "medium"  # Some anomalies, flag for review
    HIGH = "high"  # Multiple red flags, hold payment
    CRITICAL = "critical"  # Clear fraud, reject submission


@dataclass
class FraudCheckResult:
    """Result from a single fraud check."""

    check_name: str
    passed: bool
    risk_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FraudScore:
    """
    Unified fraud score for a submission.

    Combines results from all fraud detection methods into
    a single actionable score.
    """

    submission_id: str
    executor_id: str
    task_id: str

    # Overall assessment
    overall_score: float  # 0.0 (clean) to 1.0 (definitely fraud)
    risk_level: RiskLevel
    is_fraudulent: bool

    # Individual check results
    checks: List[FraudCheckResult] = field(default_factory=list)

    # Recommendations
    action: str = "approve"  # approve, review, hold, reject
    reasons: List[str] = field(default_factory=list)

    # Metadata
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    analysis_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API."""
        return {
            "submission_id": self.submission_id,
            "executor_id": self.executor_id,
            "task_id": self.task_id,
            "overall_score": round(self.overall_score, 4),
            "risk_level": self.risk_level.value,
            "is_fraudulent": self.is_fraudulent,
            "action": self.action,
            "reasons": self.reasons,
            "checks": [
                {
                    "name": c.check_name,
                    "passed": c.passed,
                    "risk_score": round(c.risk_score, 4),
                    "risk_level": c.risk_level.value,
                    "reason": c.reason,
                }
                for c in self.checks
            ],
            "analyzed_at": self.analyzed_at.isoformat(),
            "analysis_time_ms": round(self.analysis_time_ms, 2),
        }


@dataclass
class SubmissionData:
    """Data for a submission to be analyzed for fraud."""

    submission_id: str
    executor_id: str
    task_id: str
    agent_id: str

    # GPS data
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy_meters: Optional[float] = None
    gps_altitude: Optional[float] = None
    gps_timestamp: Optional[datetime] = None

    # Device info
    device_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    platform: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    timezone: Optional[str] = None

    # Sensor data
    accelerometer: Optional[Tuple[float, float, float]] = None
    gyroscope: Optional[Tuple[float, float, float]] = None

    # Image evidence
    image_paths: List[str] = field(default_factory=list)
    image_bytes: List[bytes] = field(default_factory=list)
    reference_image_path: Optional[str] = None  # For comparison

    # Timing
    task_assigned_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None

    # Task context
    task_bounty_usd: Optional[float] = None
    task_category: Optional[str] = None
    expected_location_lat: Optional[float] = None
    expected_location_lon: Optional[float] = None
    expected_location_radius_m: Optional[float] = None


@dataclass
class FraudDetectorConfig:
    """Configuration for fraud detection thresholds."""

    # Overall thresholds
    low_risk_threshold: float = 0.25
    medium_risk_threshold: float = 0.5
    high_risk_threshold: float = 0.75

    # Action thresholds
    review_threshold: float = 0.4
    hold_threshold: float = 0.6
    reject_threshold: float = 0.8

    # Check weights for final score
    weight_gps: float = 0.25
    weight_image: float = 0.30
    weight_timing: float = 0.15
    weight_behavioral: float = 0.20
    weight_location_match: float = 0.10

    # Enable/disable checks
    enable_gps_check: bool = True
    enable_image_check: bool = True
    enable_timing_check: bool = True
    enable_behavioral_check: bool = True
    enable_location_match_check: bool = True

    # Timing thresholds
    min_task_duration_seconds: float = 60.0  # At least 1 minute
    suspicious_duration_seconds: float = 120.0  # Less than 2 minutes is suspicious

    # Location matching
    default_location_radius_m: float = 500.0  # 500m tolerance


class FraudDetector:
    """
    Main fraud detection orchestrator.

    Analyzes submissions using multiple detection methods and
    produces a unified fraud score with actionable recommendations.

    Example:
        >>> detector = FraudDetector()
        >>> submission = SubmissionData(
        ...     submission_id="sub_123",
        ...     executor_id="exec_456",
        ...     task_id="task_789",
        ...     agent_id="agent_abc",
        ...     latitude=19.4326,
        ...     longitude=-99.1332,
        ...     image_paths=["/path/to/evidence.jpg"],
        ... )
        >>> score = await detector.analyze_submission(submission)
        >>> if score.is_fraudulent:
        ...     print(f"FRAUD: {score.reasons}")
    """

    def __init__(self, config: Optional[FraudDetectorConfig] = None):
        """
        Initialize fraud detector.

        Args:
            config: Optional configuration for thresholds
        """
        self.config = config or FraudDetectorConfig()
        self._gps_detector = GPSAntiSpoofing()
        self._image_analyzer = ImageAnalyzer()
        self._behavioral_analyzer = BehavioralAnalyzer()

        logger.info("FraudDetector initialized")

    async def analyze_submission(self, submission: SubmissionData) -> FraudScore:
        """
        Analyze a submission for fraud.

        Runs all enabled fraud checks in parallel and combines
        results into a unified score.

        Args:
            submission: Submission data to analyze

        Returns:
            FraudScore with overall assessment and check details
        """
        start_time = datetime.now(timezone.utc)
        checks: List[FraudCheckResult] = []

        # Run checks in parallel
        tasks = []

        if self.config.enable_gps_check and submission.latitude is not None:
            tasks.append(("gps", self._check_gps(submission)))

        if self.config.enable_image_check and (
            submission.image_paths or submission.image_bytes
        ):
            tasks.append(("image", self._check_images(submission)))

        if self.config.enable_timing_check:
            tasks.append(("timing", self._check_timing(submission)))

        if self.config.enable_behavioral_check:
            tasks.append(("behavioral", self._check_behavioral(submission)))

        if (
            self.config.enable_location_match_check
            and submission.expected_location_lat is not None
        ):
            tasks.append(("location_match", self._check_location_match(submission)))

        # Execute all checks
        if tasks:
            results = await asyncio.gather(
                *[task for _, task in tasks], return_exceptions=True
            )

            for (name, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Fraud check {name} failed: {result}")
                    checks.append(
                        FraudCheckResult(
                            check_name=name,
                            passed=True,  # Don't penalize for check failure
                            risk_score=0.0,
                            risk_level=RiskLevel.LOW,
                            reason=f"Check failed: {str(result)}",
                            details={"error": str(result)},
                        )
                    )
                else:
                    checks.append(result)

        # Calculate overall score
        overall_score = self._calculate_overall_score(checks)
        risk_level = self._score_to_risk_level(overall_score)
        action = self._determine_action(overall_score, checks)
        reasons = self._collect_reasons(checks)

        # Determine if fraudulent
        is_fraudulent = overall_score >= self.config.reject_threshold

        end_time = datetime.now(timezone.utc)
        analysis_time_ms = (end_time - start_time).total_seconds() * 1000

        score = FraudScore(
            submission_id=submission.submission_id,
            executor_id=submission.executor_id,
            task_id=submission.task_id,
            overall_score=overall_score,
            risk_level=risk_level,
            is_fraudulent=is_fraudulent,
            checks=checks,
            action=action,
            reasons=reasons,
            analyzed_at=start_time,
            analysis_time_ms=analysis_time_ms,
        )

        logger.info(
            f"Submission {submission.submission_id} analyzed: "
            f"score={overall_score:.3f}, level={risk_level.value}, action={action}"
        )

        return score

    async def _check_gps(self, submission: SubmissionData) -> FraudCheckResult:
        """Check for GPS spoofing."""
        gps_data = GPSData(
            latitude=submission.latitude,
            longitude=submission.longitude,
            accuracy_meters=submission.gps_accuracy_meters,
            altitude=submission.gps_altitude,
            timestamp=submission.gps_timestamp or datetime.now(timezone.utc),
        )

        device_info = DeviceInfo(
            device_id=submission.device_id,
            user_agent=submission.user_agent,
            platform=submission.platform,
            screen_width=submission.screen_width,
            screen_height=submission.screen_height,
            timezone=submission.timezone,
        )

        sensor_data = None
        if submission.accelerometer or submission.gyroscope:
            sensor_data = SensorData(
                accelerometer=submission.accelerometer,
                gyroscope=submission.gyroscope,
                timestamp=datetime.now(timezone.utc),
            )

        result = await self._gps_detector.detect_spoofing(
            gps_data=gps_data,
            device_info=device_info,
            executor_id=submission.executor_id,
            ip_address=submission.ip_address,
            sensor_data=sensor_data,
        )

        risk_level = self._score_to_risk_level(result.risk_score)

        return FraudCheckResult(
            check_name="gps_spoofing",
            passed=not result.is_spoofed,
            risk_score=result.risk_score,
            risk_level=risk_level,
            reason="; ".join(result.reasons) if result.reasons else None,
            details={
                "checks_performed": result.checks_performed,
                "confidence": result.confidence,
                **result.details,
            },
        )

    async def _check_images(self, submission: SubmissionData) -> FraudCheckResult:
        """Check images for manipulation or AI generation."""
        all_results: List[ImageAnalysisResult] = []

        # Analyze images by path
        for path in submission.image_paths:
            result = await self._image_analyzer.analyze_image(path)
            all_results.append(result)

        # Analyze images by bytes
        for image_bytes in submission.image_bytes:
            result = await self._image_analyzer.analyze_image_bytes(image_bytes)
            all_results.append(result)

        if not all_results:
            return FraudCheckResult(
                check_name="image_analysis",
                passed=True,
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                reason="No images to analyze",
            )

        # Aggregate results - use highest risk
        max_risk = max(r.risk_score for r in all_results)
        failed_count = sum(1 for r in all_results if r.is_suspicious)

        reasons = []
        for i, r in enumerate(all_results):
            if r.is_suspicious and r.reason:
                reasons.append(f"Image {i + 1}: {r.reason}")

        risk_level = self._score_to_risk_level(max_risk)

        return FraudCheckResult(
            check_name="image_analysis",
            passed=failed_count == 0,
            risk_score=max_risk,
            risk_level=risk_level,
            reason="; ".join(reasons) if reasons else None,
            details={
                "images_analyzed": len(all_results),
                "suspicious_images": failed_count,
                "results": [r.to_dict() for r in all_results],
            },
        )

    async def _check_timing(self, submission: SubmissionData) -> FraudCheckResult:
        """Check for timing anomalies."""
        if not submission.task_assigned_at or not submission.submitted_at:
            return FraudCheckResult(
                check_name="timing_analysis",
                passed=True,
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                reason="No timing data available",
            )

        duration = (
            submission.submitted_at - submission.task_assigned_at
        ).total_seconds()

        # Check for impossibly fast completion
        if duration < self.config.min_task_duration_seconds:
            return FraudCheckResult(
                check_name="timing_analysis",
                passed=False,
                risk_score=0.9,
                risk_level=RiskLevel.CRITICAL,
                reason=f"Task completed in {duration:.0f}s (minimum: {self.config.min_task_duration_seconds:.0f}s)",
                details={
                    "duration_seconds": duration,
                    "min_required": self.config.min_task_duration_seconds,
                },
            )

        # Check for suspiciously fast completion
        if duration < self.config.suspicious_duration_seconds:
            risk_score = 1.0 - (duration / self.config.suspicious_duration_seconds)
            return FraudCheckResult(
                check_name="timing_analysis",
                passed=True,  # Not automatic fail, just suspicious
                risk_score=min(0.6, risk_score),
                risk_level=RiskLevel.MEDIUM,
                reason=f"Task completed quickly ({duration:.0f}s)",
                details={
                    "duration_seconds": duration,
                    "suspicious_threshold": self.config.suspicious_duration_seconds,
                },
            )

        return FraudCheckResult(
            check_name="timing_analysis",
            passed=True,
            risk_score=0.0,
            risk_level=RiskLevel.LOW,
            details={"duration_seconds": duration},
        )

    async def _check_behavioral(self, submission: SubmissionData) -> FraudCheckResult:
        """Check for behavioral anomalies."""
        result = await self._behavioral_analyzer.analyze_submission(
            executor_id=submission.executor_id,
            agent_id=submission.agent_id,
            task_id=submission.task_id,
            bounty_usd=submission.task_bounty_usd,
            device_id=submission.device_id,
            ip_address=submission.ip_address,
        )

        risk_level = self._score_to_risk_level(result.risk_score)

        reasons = []
        if result.velocity_abuse:
            reasons.append("Velocity abuse detected")
        if result.collusion_suspected:
            reasons.append("Collusion pattern detected")
        if result.multi_account_suspected:
            reasons.append("Multiple accounts suspected")

        return FraudCheckResult(
            check_name="behavioral_analysis",
            passed=result.risk_score < 0.5,
            risk_score=result.risk_score,
            risk_level=risk_level,
            reason="; ".join(reasons) if reasons else None,
            details=result.to_dict(),
        )

    async def _check_location_match(
        self, submission: SubmissionData
    ) -> FraudCheckResult:
        """Check if submission location matches expected task location."""
        if submission.latitude is None or submission.longitude is None:
            return FraudCheckResult(
                check_name="location_match",
                passed=True,
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                reason="No GPS data to verify",
            )

        expected_lat = submission.expected_location_lat
        expected_lon = submission.expected_location_lon
        radius = (
            submission.expected_location_radius_m
            or self.config.default_location_radius_m
        )

        # Calculate distance using haversine
        import math

        lat1, lon1 = (
            math.radians(submission.latitude),
            math.radians(submission.longitude),
        )
        lat2, lon2 = math.radians(expected_lat), math.radians(expected_lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_m = 6_371_000 * c

        if distance_m <= radius:
            return FraudCheckResult(
                check_name="location_match",
                passed=True,
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                details={
                    "distance_m": distance_m,
                    "allowed_radius_m": radius,
                },
            )

        # Calculate risk based on distance
        excess_distance = distance_m - radius
        risk_score = min(1.0, excess_distance / 5000)  # Max risk at 5km+ from expected

        risk_level = self._score_to_risk_level(risk_score)

        return FraudCheckResult(
            check_name="location_match",
            passed=False,
            risk_score=risk_score,
            risk_level=risk_level,
            reason=f"Location {distance_m:.0f}m from expected (max: {radius:.0f}m)",
            details={
                "distance_m": distance_m,
                "allowed_radius_m": radius,
                "submission_coords": (submission.latitude, submission.longitude),
                "expected_coords": (expected_lat, expected_lon),
            },
        )

    def _calculate_overall_score(self, checks: List[FraudCheckResult]) -> float:
        """Calculate weighted overall fraud score."""
        if not checks:
            return 0.0

        weights = {
            "gps_spoofing": self.config.weight_gps,
            "image_analysis": self.config.weight_image,
            "timing_analysis": self.config.weight_timing,
            "behavioral_analysis": self.config.weight_behavioral,
            "location_match": self.config.weight_location_match,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for check in checks:
            weight = weights.get(check.check_name, 0.1)
            weighted_sum += check.risk_score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return min(1.0, weighted_sum / total_weight)

    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score >= self.config.high_risk_threshold:
            return RiskLevel.CRITICAL
        elif score >= self.config.medium_risk_threshold:
            return RiskLevel.HIGH
        elif score >= self.config.low_risk_threshold:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _determine_action(
        self, overall_score: float, checks: List[FraudCheckResult]
    ) -> str:
        """Determine recommended action based on score and checks."""
        # Critical check failures always reject
        critical_failures = [
            c for c in checks if c.risk_level == RiskLevel.CRITICAL and not c.passed
        ]
        if critical_failures:
            return "reject"

        # Score-based action
        if overall_score >= self.config.reject_threshold:
            return "reject"
        elif overall_score >= self.config.hold_threshold:
            return "hold"
        elif overall_score >= self.config.review_threshold:
            return "review"

        return "approve"

    def _collect_reasons(self, checks: List[FraudCheckResult]) -> List[str]:
        """Collect all reasons from failed or suspicious checks."""
        reasons = []
        for check in checks:
            if not check.passed and check.reason:
                reasons.append(f"[{check.check_name}] {check.reason}")
            elif check.risk_score >= 0.3 and check.reason:
                reasons.append(f"[{check.check_name}] {check.reason}")
        return reasons


# Convenience function for quick analysis
async def analyze_submission_fraud(
    submission_id: str,
    executor_id: str,
    task_id: str,
    agent_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    image_paths: Optional[List[str]] = None,
    device_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> FraudScore:
    """
    Quick fraud analysis for a submission.

    Args:
        submission_id: Unique submission identifier
        executor_id: Worker's ID
        task_id: Task ID
        agent_id: Agent's ID
        latitude: GPS latitude
        longitude: GPS longitude
        image_paths: List of evidence image paths
        device_id: Device identifier
        ip_address: Client IP

    Returns:
        FraudScore with analysis results
    """
    detector = FraudDetector()

    submission = SubmissionData(
        submission_id=submission_id,
        executor_id=executor_id,
        task_id=task_id,
        agent_id=agent_id,
        latitude=latitude,
        longitude=longitude,
        image_paths=image_paths or [],
        device_id=device_id,
        ip_address=ip_address,
    )

    return await detector.analyze_submission(submission)
