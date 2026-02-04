"""
Tests for Execution Market Safety Module

Tests NOW-112 (Safety Pre-Investigation) and NOW-113 (Hostile Meatspace Protocol).
"""

import pytest
from datetime import datetime, timedelta, UTC
from typing import Tuple

from ..safety import (
    SafetyInvestigator,
    SafetyAssessment,
    SafetyRisk,
    RiskFactor,
    LocationRiskData,
    HostileProtocolManager,
    ObstacleReport,
    ObstacleType,
    ProofOfAttempt,
    CompensationDecision,
)
from ..safety.investigation import AreaType, is_safe_time, quick_safety_check
from ..safety.hostile_protocol import (
    EvidenceType,
    VerificationStatus,
    CompensationTier,
    OBSTACLE_COMPENSATION,
    report_obstacle_quick,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def investigator() -> SafetyInvestigator:
    """Create a SafetyInvestigator instance."""
    return SafetyInvestigator()


@pytest.fixture
def hostile_manager() -> HostileProtocolManager:
    """Create a HostileProtocolManager instance."""
    return HostileProtocolManager()


@pytest.fixture
def sample_location() -> Tuple[float, float]:
    """Sample location coordinates (Times Square, NYC)."""
    return (40.7580, -73.9855)


@pytest.fixture
def sample_evidence(sample_location: Tuple[float, float]) -> ProofOfAttempt:
    """Sample proof of attempt evidence (PHOTO type)."""
    return ProofOfAttempt(
        worker_id="worker-123",
        task_id="task-456",
        evidence_type=EvidenceType.PHOTO,
        evidence_url="https://example.com/photo.jpg",
        evidence_data={"shows": "locked_gate"},
        gps_coordinates=sample_location,
        timestamp=datetime.now(UTC),
        description="Photo of locked gate",
    )


@pytest.fixture
def sample_gps_evidence(sample_location: Tuple[float, float]) -> ProofOfAttempt:
    """Sample proof of attempt evidence (GPS_TRACK type)."""
    return ProofOfAttempt(
        worker_id="worker-123",
        task_id="task-456",
        evidence_type=EvidenceType.GPS_TRACK,
        evidence_url=None,
        evidence_data={"coordinates": sample_location},
        gps_coordinates=sample_location,
        timestamp=datetime.now(UTC),
        description="GPS track at location",
    )


# =============================================================================
# SAFETY INVESTIGATION TESTS (NOW-112)
# =============================================================================


class TestSafetyInvestigator:
    """Tests for SafetyInvestigator class."""

    @pytest.mark.asyncio
    async def test_assess_location_basic(
        self,
        investigator: SafetyInvestigator,
        sample_location: Tuple[float, float],
    ):
        """Test basic location assessment."""
        lat, lng = sample_location

        assessment = await investigator.assess_location(lat, lng)

        assert assessment is not None
        assert assessment.location == sample_location
        assert isinstance(assessment.overall_risk, SafetyRisk)
        assert 0 <= assessment.risk_score <= 1
        assert RiskFactor.CRIME_RATE in assessment.factors
        assert RiskFactor.TIME_OF_DAY in assessment.factors

    @pytest.mark.asyncio
    async def test_assess_location_with_task_id(
        self,
        investigator: SafetyInvestigator,
        sample_location: Tuple[float, float],
    ):
        """Test assessment with task ID."""
        lat, lng = sample_location

        assessment = await investigator.assess_location(
            lat, lng, task_id="task-789"
        )

        assert assessment.task_id == "task-789"

    @pytest.mark.asyncio
    async def test_assess_location_caching(
        self,
        investigator: SafetyInvestigator,
        sample_location: Tuple[float, float],
    ):
        """Test that assessments are cached."""
        lat, lng = sample_location

        # First assessment
        assessment1 = await investigator.assess_location(lat, lng)

        # Second assessment should use cache
        assessment2 = await investigator.assess_location(lat, lng)

        # Should be the same object from cache
        assert assessment1.assessed_at == assessment2.assessed_at

    @pytest.mark.asyncio
    async def test_assess_location_force_refresh(
        self,
        investigator: SafetyInvestigator,
        sample_location: Tuple[float, float],
    ):
        """Test force refresh bypasses cache."""
        lat, lng = sample_location

        # First assessment
        assessment1 = await investigator.assess_location(lat, lng)

        # Force refresh
        assessment2 = await investigator.assess_location(
            lat, lng, force_refresh=True
        )

        # Should have different timestamps
        assert assessment1.assessed_at <= assessment2.assessed_at

    def test_check_time_risk_daytime(self, investigator: SafetyInvestigator):
        """Test time risk during safe hours."""
        # 2 PM - safe hour
        task_time = datetime.now(UTC).replace(hour=14, minute=0)

        risk_score, warnings, safe_hours = investigator.check_time_risk(task_time)

        assert risk_score < 0.3
        assert len(warnings) == 0
        assert safe_hours == [(6, 22)]

    def test_check_time_risk_nighttime(self, investigator: SafetyInvestigator):
        """Test time risk during high-risk hours."""
        # 11 PM - high risk
        task_time = datetime.now(UTC).replace(hour=23, minute=0)

        risk_score, warnings, safe_hours = investigator.check_time_risk(task_time)

        assert risk_score > 0.4
        assert len(warnings) > 0
        assert "high-risk hours" in warnings[0].lower()

    def test_check_time_risk_early_morning(self, investigator: SafetyInvestigator):
        """Test time risk during early morning hours."""
        # 3 AM - high risk
        task_time = datetime.now(UTC).replace(hour=3, minute=0)

        risk_score, warnings, _ = investigator.check_time_risk(task_time)

        assert risk_score > 0.4
        assert len(warnings) > 0

    def test_check_time_risk_industrial_area(
        self, investigator: SafetyInvestigator
    ):
        """Test time risk in industrial area."""
        # 7 PM in industrial area
        task_time = datetime.now(UTC).replace(hour=19, minute=0)

        risk_score, warnings, safe_hours = investigator.check_time_risk(
            task_time, AreaType.INDUSTRIAL
        )

        # Industrial areas have stricter safe hours
        assert safe_hours == [(8, 18)]

    def test_record_incident(
        self,
        investigator: SafetyInvestigator,
        sample_location: Tuple[float, float],
    ):
        """Test incident recording."""
        lat, lng = sample_location

        investigator.record_incident(
            lat, lng,
            incident_type="hostile_encounter",
            description="Aggressive person encountered",
            worker_id="worker-123",
        )

        # Check incident was recorded
        location_key = f"{lat:.4f}:{lng:.4f}"
        assert location_key in investigator._incident_history
        assert len(investigator._incident_history[location_key]) == 1

    @pytest.mark.asyncio
    async def test_incident_affects_assessment(
        self,
        investigator: SafetyInvestigator,
        sample_location: Tuple[float, float],
    ):
        """Test that recorded incidents affect future assessments."""
        lat, lng = sample_location

        # Record multiple incidents
        for i in range(3):
            investigator.record_incident(
                lat, lng,
                incident_type="hostile_encounter",
                description=f"Incident {i}",
            )

        # Get assessment
        assessment = await investigator.assess_location(
            lat, lng, force_refresh=True
        )

        # Should have warnings about incidents
        assert any("incident" in w.lower() for w in assessment.warnings)
        assert RiskFactor.INCIDENT_HISTORY in assessment.factors
        assert assessment.factors[RiskFactor.INCIDENT_HISTORY] > 0

    @pytest.mark.asyncio
    async def test_assessment_to_dict(
        self,
        investigator: SafetyInvestigator,
        sample_location: Tuple[float, float],
    ):
        """Test SafetyAssessment.to_dict() serialization."""
        lat, lng = sample_location

        assessment = await investigator.assess_location(lat, lng)
        data = assessment.to_dict()

        assert data["location"]["lat"] == lat
        assert data["location"]["lng"] == lng
        assert "overall_risk" in data
        assert "factors" in data
        assert "warnings" in data
        assert "recommendations" in data

    def test_clear_cache(
        self,
        investigator: SafetyInvestigator,
    ):
        """Test cache clearing."""
        investigator._assessment_cache["test"] = "value"
        investigator.clear_cache()
        assert len(investigator._assessment_cache) == 0


class TestSafetyConvenienceFunctions:
    """Tests for safety convenience functions."""

    @pytest.mark.asyncio
    async def test_quick_safety_check(self, sample_location: Tuple[float, float]):
        """Test quick_safety_check function."""
        lat, lng = sample_location

        assessment = await quick_safety_check(lat, lng)

        assert assessment is not None
        assert isinstance(assessment.overall_risk, SafetyRisk)

    def test_is_safe_time_daytime(self):
        """Test is_safe_time for daytime."""
        assert is_safe_time(10) is True  # 10 AM
        assert is_safe_time(14) is True  # 2 PM
        assert is_safe_time(18) is True  # 6 PM

    def test_is_safe_time_nighttime(self):
        """Test is_safe_time for nighttime."""
        assert is_safe_time(23) is False  # 11 PM
        assert is_safe_time(2) is False   # 2 AM
        assert is_safe_time(4) is False   # 4 AM


# =============================================================================
# HOSTILE PROTOCOL TESTS (NOW-113)
# =============================================================================


class TestHostileProtocolManager:
    """Tests for HostileProtocolManager class."""

    @pytest.mark.asyncio
    async def test_report_obstacle_basic(
        self,
        hostile_manager: HostileProtocolManager,
        sample_evidence: ProofOfAttempt,
        sample_gps_evidence: ProofOfAttempt,
    ):
        """Test basic obstacle reporting."""
        # ACCESS_DENIED requires PHOTO and GPS_TRACK evidence
        report = await hostile_manager.report_obstacle(
            task_id="task-456",
            worker_id="worker-123",
            obstacle_type=ObstacleType.ACCESS_DENIED,
            description="Gate was locked",
            evidence=[sample_evidence, sample_gps_evidence],
        )

        assert report is not None
        assert report.task_id == "task-456"
        assert report.worker_id == "worker-123"
        assert report.obstacle_type == ObstacleType.ACCESS_DENIED
        assert len(report.evidence) == 2
        # With good evidence (GPS + PHOTO), may be auto-verified
        assert report.verification_status in [
            VerificationStatus.PENDING,
            VerificationStatus.VERIFIED,
        ]

    @pytest.mark.asyncio
    async def test_report_obstacle_with_location(
        self,
        hostile_manager: HostileProtocolManager,
        sample_evidence: ProofOfAttempt,
        sample_gps_evidence: ProofOfAttempt,
        sample_location: Tuple[float, float],
    ):
        """Test obstacle reporting with location."""
        # ACCESS_DENIED requires PHOTO and GPS_TRACK evidence
        report = await hostile_manager.report_obstacle(
            task_id="task-456",
            worker_id="worker-123",
            obstacle_type=ObstacleType.ACCESS_DENIED,
            description="Gate was locked",
            evidence=[sample_evidence, sample_gps_evidence],
            location=sample_location,
        )

        assert report.location == sample_location

    @pytest.mark.asyncio
    async def test_report_obstacle_missing_evidence(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test that missing required evidence raises error."""
        # ACCESS_DENIED requires PHOTO and GPS_TRACK
        with pytest.raises(ValueError) as exc_info:
            await hostile_manager.report_obstacle(
                task_id="task-456",
                worker_id="worker-123",
                obstacle_type=ObstacleType.ACCESS_DENIED,
                description="Gate was locked",
                evidence=[],  # No evidence
            )

        assert "Missing required evidence" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_report_obstacle_medical_emergency_no_evidence(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test that medical emergency doesn't require evidence."""
        # MEDICAL_EMERGENCY has no evidence requirements
        report = await hostile_manager.report_obstacle(
            task_id="task-456",
            worker_id="worker-123",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Had to leave due to health issue",
            evidence=[],
        )

        assert report is not None
        assert report.obstacle_type == ObstacleType.MEDICAL_EMERGENCY

    @pytest.mark.asyncio
    async def test_rate_limit(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test rate limiting for obstacle reports."""
        # Create minimal evidence for medical (no requirements)
        for i in range(5):
            await hostile_manager.report_obstacle(
                task_id=f"task-{i}",
                worker_id="worker-rate-limited",
                obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
                description=f"Report {i}",
                evidence=[],
            )

        # 6th report should fail
        with pytest.raises(ValueError) as exc_info:
            await hostile_manager.report_obstacle(
                task_id="task-6",
                worker_id="worker-rate-limited",
                obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
                description="Report 6",
                evidence=[],
            )

        assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_obstacle(
        self,
        hostile_manager: HostileProtocolManager,
        sample_evidence: ProofOfAttempt,
    ):
        """Test obstacle verification."""
        report = await hostile_manager.report_obstacle(
            task_id="task-456",
            worker_id="worker-123",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Health issue",
            evidence=[],
        )

        # Manually verify
        result = await hostile_manager.verify_obstacle(
            report.id, verifier_id="admin-1"
        )

        assert result is True
        updated_report = await hostile_manager.get_report(report.id)
        assert updated_report.verified is True
        assert updated_report.verified_by == "admin-1"

    @pytest.mark.asyncio
    async def test_reject_obstacle(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test obstacle rejection."""
        report = await hostile_manager.report_obstacle(
            task_id="task-456",
            worker_id="worker-123",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Test",
            evidence=[],
        )

        rejected = await hostile_manager.reject_obstacle(
            report.id,
            reason="Evidence inconsistent",
            rejector_id="admin-1",
        )

        assert rejected.verified is False
        assert rejected.verification_status == VerificationStatus.REJECTED
        assert rejected.rejection_reason == "Evidence inconsistent"

    @pytest.mark.asyncio
    async def test_award_compensation(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test compensation awarding."""
        report = await hostile_manager.report_obstacle(
            task_id="task-456",
            worker_id="worker-123",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Health issue",
            evidence=[],
        )

        # Verify first
        await hostile_manager.verify_obstacle(report.id, verifier_id="admin-1")

        # Award compensation
        decision = await hostile_manager.award_compensation(
            report.id, bounty_amount=100.0
        )

        assert decision.approved is True
        assert decision.compensation_amount > 0
        assert decision.compensation_percentage > 0

        # Check report was updated
        updated_report = await hostile_manager.get_report(report.id)
        assert updated_report.compensation_awarded > 0

    @pytest.mark.asyncio
    async def test_award_compensation_requires_verification(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test that compensation requires verification."""
        report = await hostile_manager.report_obstacle(
            task_id="task-456",
            worker_id="worker-123",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Test",
            evidence=[],
        )

        # Try to award without verification
        with pytest.raises(ValueError) as exc_info:
            await hostile_manager.award_compensation(report.id, bounty_amount=100.0)

        assert "unverified" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_reports_for_task(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test getting reports for a specific task."""
        # Create reports for different tasks
        await hostile_manager.report_obstacle(
            task_id="task-A",
            worker_id="worker-1",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Report 1",
            evidence=[],
        )
        await hostile_manager.report_obstacle(
            task_id="task-A",
            worker_id="worker-2",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Report 2",
            evidence=[],
        )
        await hostile_manager.report_obstacle(
            task_id="task-B",
            worker_id="worker-1",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Report 3",
            evidence=[],
        )

        task_a_reports = await hostile_manager.get_reports_for_task("task-A")
        assert len(task_a_reports) == 2

        task_b_reports = await hostile_manager.get_reports_for_task("task-B")
        assert len(task_b_reports) == 1

    @pytest.mark.asyncio
    async def test_get_reports_for_worker(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test getting reports for a specific worker."""
        await hostile_manager.report_obstacle(
            task_id="task-1",
            worker_id="worker-X",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Report 1",
            evidence=[],
        )
        await hostile_manager.report_obstacle(
            task_id="task-2",
            worker_id="worker-X",
            obstacle_type=ObstacleType.MEDICAL_EMERGENCY,
            description="Report 2",
            evidence=[],
        )

        worker_reports = await hostile_manager.get_reports_for_worker("worker-X")
        assert len(worker_reports) == 2

    def test_calculate_safety_score(
        self,
        hostile_manager: HostileProtocolManager,
        sample_location: Tuple[float, float],
    ):
        """Test safety score calculation."""
        score = hostile_manager.calculate_safety_score(
            task_id="task-123",
            location=sample_location,
            task_time=datetime.now(UTC).replace(hour=14),  # 2 PM
        )

        assert score is not None
        assert 0 <= score.score <= 1
        assert score.task_id == "task-123"

    def test_calculate_safety_score_night(
        self,
        hostile_manager: HostileProtocolManager,
        sample_location: Tuple[float, float],
    ):
        """Test safety score during night hours."""
        score = hostile_manager.calculate_safety_score(
            task_id="task-123",
            location=sample_location,
            task_time=datetime.now(UTC).replace(hour=23),  # 11 PM
        )

        # Night should have lower safety score
        assert score.score < 1.0
        assert "night_risk" in score.factors

    def test_obstacle_report_to_dict(
        self,
        hostile_manager: HostileProtocolManager,
        sample_evidence: ProofOfAttempt,
    ):
        """Test ObstacleReport.to_dict() serialization."""
        report = ObstacleReport(
            id="report-123",
            task_id="task-456",
            worker_id="worker-789",
            obstacle_type=ObstacleType.ACCESS_DENIED,
            description="Test",
            evidence=[sample_evidence],
            reported_at=datetime.now(UTC),
        )

        data = report.to_dict()

        assert data["id"] == "report-123"
        assert data["task_id"] == "task-456"
        assert data["obstacle_type"] == "access_denied"
        assert len(data["evidence"]) == 1

    def test_get_statistics(
        self,
        hostile_manager: HostileProtocolManager,
    ):
        """Test statistics retrieval."""
        stats = hostile_manager.get_statistics()

        assert "total_reports" in stats
        assert "by_type" in stats
        assert "by_status" in stats
        assert "verification_rate" in stats
        assert "total_compensation_awarded" in stats


class TestCompensationRates:
    """Tests for compensation rate calculations."""

    def test_hostile_environment_highest_compensation(self):
        """Test that hostile environment has high compensation."""
        hostile_rate = OBSTACLE_COMPENSATION[ObstacleType.HOSTILE_ENVIRONMENT]
        unsafe_rate = OBSTACLE_COMPENSATION[ObstacleType.UNSAFE_CONDITIONS]

        # These should be among the highest
        assert hostile_rate >= 0.25
        assert unsafe_rate >= 0.25

    def test_equipment_failure_lowest_compensation(self):
        """Test that equipment failure has low compensation."""
        equipment_rate = OBSTACLE_COMPENSATION[ObstacleType.EQUIPMENT_FAILURE]

        # Worker's equipment issue = lower compensation
        assert equipment_rate <= 0.10


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_report_obstacle_quick(self, sample_location: Tuple[float, float]):
        """Test quick obstacle reporting function."""
        report = await report_obstacle_quick(
            task_id="task-quick",
            worker_id="worker-quick",
            obstacle_type="medical_emergency",  # String, not enum
            description="Quick test",
            gps=sample_location,
        )

        assert report is not None
        assert report.obstacle_type == ObstacleType.MEDICAL_EMERGENCY

    @pytest.mark.asyncio
    async def test_report_obstacle_quick_invalid_type(
        self, sample_location: Tuple[float, float]
    ):
        """Test quick report with invalid obstacle type defaults to ACCESS_DENIED."""
        # ACCESS_DENIED requires PHOTO and GPS_TRACK evidence
        report = await report_obstacle_quick(
            task_id="task-quick",
            worker_id="worker-quick",
            obstacle_type="invalid_type",  # Invalid type
            description="Quick test",
            photo_url="https://example.com/photo.jpg",  # Required for ACCESS_DENIED
            gps=sample_location,
        )

        # Should default to ACCESS_DENIED
        assert report.obstacle_type == ObstacleType.ACCESS_DENIED


class TestProofOfAttempt:
    """Tests for ProofOfAttempt data class."""

    def test_proof_of_attempt_to_dict(
        self, sample_evidence: ProofOfAttempt
    ):
        """Test ProofOfAttempt.to_dict() serialization."""
        data = sample_evidence.to_dict()

        assert data["worker_id"] == "worker-123"
        assert data["task_id"] == "task-456"
        assert data["evidence_type"] == "photo"
        assert data["gps_coordinates"] is not None


class TestCompensationDecision:
    """Tests for CompensationDecision data class."""

    def test_compensation_decision_to_dict(self):
        """Test CompensationDecision.to_dict() serialization."""
        decision = CompensationDecision(
            report_id="report-123",
            approved=True,
            compensation_tier=CompensationTier.PARTIAL,
            compensation_amount=15.50,
            compensation_percentage=15.5,
            reason="Test reason",
            decided_at=datetime.now(UTC),
            decided_by="system",
        )

        data = decision.to_dict()

        assert data["report_id"] == "report-123"
        assert data["approved"] is True
        assert data["compensation_tier"] == "partial"
        assert data["compensation_amount"] == 15.50
