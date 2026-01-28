"""
Tests for Seals & Credentials Module

Tests cover:
- Seal types and requirements
- Mock registry operations
- Issuance eligibility and logic
- Verification service
- Display formatting
"""

import pytest
from datetime import datetime, timedelta, UTC

from ..seals import (
    # Types
    SealCategory,
    SealStatus,
    VerificationMethod,
    SkillSealType,
    WorkSealType,
    BehaviorSealType,
    Seal,
    SealBundle,
    get_requirement,
    get_automatic_seals,
    SEAL_REQUIREMENTS,
    # Registry
    MockSealRegistry,
    get_seal_type_id,
    get_seal_type_from_id,
    # Issuance
    SealIssuanceService,
    WorkerStats,
    # Verification
    SealVerificationService,
    TaskSealRequirement,
    # Display
    SealDisplayFormatter,
    DisplayConfig,
    format_seals_for_profile,
    format_seals_for_card,
    get_seal_display_name,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_registry():
    """Create a mock registry for testing."""
    return MockSealRegistry()


@pytest.fixture
def issuance_service(mock_registry):
    """Create issuance service with mock registry."""
    return SealIssuanceService(mock_registry)


@pytest.fixture
def verification_service(mock_registry):
    """Create verification service with mock registry."""
    return SealVerificationService(mock_registry)


@pytest.fixture
def display_formatter():
    """Create display formatter with Spanish locale."""
    return SealDisplayFormatter(DisplayConfig(locale="es"))


@pytest.fixture
def sample_worker_stats():
    """Create sample worker stats for testing."""
    return WorkerStats(
        wallet_address="0x1234567890123456789012345678901234567890",
        total_tasks_completed=105,
        total_earnings_usd=1250.00,
        average_rating=88.5,
        active_days=95,
        cancellation_count=0,
        avg_response_time_minutes=45.0,
        tasks_by_category={
            "delivery": 50,
            "photography": 30,
        },
    )


@pytest.fixture
def sample_seal():
    """Create a sample seal for testing."""
    now = datetime.now(UTC)
    return Seal(
        id=Seal.generate_id("0x1234...", "tasks_100_completed", now),
        category=SealCategory.WORK,
        seal_type=WorkSealType.TASKS_100.value,
        holder_id="0x1234567890123456789012345678901234567890",
        issued_at=now,
        expires_at=None,
        tx_hash="0xabcd1234",
        block_number=1000000,
    )


@pytest.fixture
async def populated_registry(mock_registry):
    """Create registry with some seals already issued."""
    address = "0x1234567890123456789012345678901234567890"

    await mock_registry.issue_seal(address, WorkSealType.TASKS_10.value)
    await mock_registry.issue_seal(address, WorkSealType.TASKS_50.value)
    await mock_registry.issue_seal(address, WorkSealType.TASKS_100.value)
    await mock_registry.issue_seal(address, SkillSealType.DELIVERY_CERTIFIED.value)

    # Add expiring seal
    await mock_registry.issue_seal(
        address,
        BehaviorSealType.FAST_RESPONDER.value,
        expires_at=datetime.now(UTC) + timedelta(days=10)
    )

    return mock_registry


# =============================================================================
# TYPE TESTS
# =============================================================================

class TestSealTypes:
    """Tests for seal type definitions."""

    def test_seal_categories_exist(self):
        """Verify all seal categories are defined."""
        assert SealCategory.SKILL.value == "skill"
        assert SealCategory.WORK.value == "work"
        assert SealCategory.BEHAVIOR.value == "behavior"

    def test_skill_seal_types_exist(self):
        """Verify key skill seal types are defined."""
        assert SkillSealType.PHOTOGRAPHY_VERIFIED.value == "photography_verified"
        assert SkillSealType.DELIVERY_CERTIFIED.value == "delivery_certified"
        assert SkillSealType.DOCUMENT_HANDLING.value == "document_handling_verified"

    def test_work_seal_types_exist(self):
        """Verify key work seal types are defined."""
        assert WorkSealType.TASKS_10.value == "tasks_10_completed"
        assert WorkSealType.TASKS_100.value == "tasks_100_completed"
        assert WorkSealType.EARNED_1000_USD.value == "earned_1000_usd"

    def test_behavior_seal_types_exist(self):
        """Verify key behavior seal types are defined."""
        assert BehaviorSealType.FAST_RESPONDER.value == "fast_responder"
        assert BehaviorSealType.HIGH_QUALITY.value == "high_quality"
        assert BehaviorSealType.NEVER_CANCELLED.value == "never_cancelled"

    def test_seal_requirements_defined(self):
        """Verify seal requirements are defined for key types."""
        assert len(SEAL_REQUIREMENTS) > 10

        # Check a specific requirement
        req = get_requirement(WorkSealType.TASKS_100.value)
        assert req is not None
        assert req.min_tasks == 100
        assert req.category == SealCategory.WORK
        assert req.verification_method == VerificationMethod.AUTOMATIC

    def test_get_automatic_seals(self):
        """Verify automatic seals can be retrieved."""
        auto_seals = get_automatic_seals()
        assert len(auto_seals) > 5

        # All should be AUTOMATIC verification
        for seal in auto_seals:
            assert seal.verification_method == VerificationMethod.AUTOMATIC


class TestSealModel:
    """Tests for Seal dataclass."""

    def test_seal_creation(self, sample_seal):
        """Verify seal can be created."""
        assert sample_seal.seal_type == WorkSealType.TASKS_100.value
        assert sample_seal.category == SealCategory.WORK
        assert sample_seal.is_valid is True
        assert sample_seal.status == SealStatus.ACTIVE

    def test_seal_id_generation(self):
        """Verify seal ID is deterministic."""
        now = datetime.now(UTC)
        id1 = Seal.generate_id("holder1", "type1", now)
        id2 = Seal.generate_id("holder1", "type1", now)
        id3 = Seal.generate_id("holder2", "type1", now)

        assert id1 == id2  # Same inputs = same ID
        assert id1 != id3  # Different holder = different ID

    def test_seal_status_expired(self):
        """Verify expired seal status."""
        seal = Seal(
            id="test",
            category=SealCategory.BEHAVIOR,
            seal_type="fast_responder",
            holder_id="0x1234",
            issued_at=datetime.now(UTC) - timedelta(days=60),
            expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired yesterday
        )
        assert seal.status == SealStatus.EXPIRED
        assert seal.is_valid is False

    def test_seal_status_revoked(self):
        """Verify revoked seal status."""
        seal = Seal(
            id="test",
            category=SealCategory.SKILL,
            seal_type="photography_verified",
            holder_id="0x1234",
            issued_at=datetime.now(UTC) - timedelta(days=30),
            revoked_at=datetime.now(UTC) - timedelta(days=5),
        )
        assert seal.status == SealStatus.REVOKED
        assert seal.is_valid is False

    def test_seal_to_dict(self, sample_seal):
        """Verify seal serialization."""
        data = sample_seal.to_dict()

        assert data["seal_type"] == WorkSealType.TASKS_100.value
        assert data["status"] == "active"
        assert data["is_valid"] is True
        assert "issued_at" in data


# =============================================================================
# REGISTRY TESTS
# =============================================================================

class TestSealTypeIds:
    """Tests for seal type ID mapping."""

    def test_skill_seal_ids_in_range(self):
        """Verify skill seal IDs are in 1-99 range."""
        for seal_type in SkillSealType:
            seal_id = get_seal_type_id(seal_type.value)
            assert seal_id is not None
            assert 1 <= seal_id < 100

    def test_work_seal_ids_in_range(self):
        """Verify work seal IDs are in 100-199 range."""
        for seal_type in WorkSealType:
            seal_id = get_seal_type_id(seal_type.value)
            assert seal_id is not None
            assert 100 <= seal_id < 200

    def test_behavior_seal_ids_in_range(self):
        """Verify behavior seal IDs are in 200-299 range."""
        for seal_type in BehaviorSealType:
            seal_id = get_seal_type_id(seal_type.value)
            assert seal_id is not None
            assert 200 <= seal_id < 300

    def test_reverse_mapping(self):
        """Verify reverse mapping works."""
        for seal_type in WorkSealType:
            seal_id = get_seal_type_id(seal_type.value)
            reverse = get_seal_type_from_id(seal_id)
            assert reverse == seal_type.value


class TestMockRegistry:
    """Tests for mock registry operations."""

    @pytest.mark.asyncio
    async def test_issue_seal(self, mock_registry):
        """Test issuing a seal."""
        address = "0x1234567890123456789012345678901234567890"
        seal_type = WorkSealType.TASKS_10.value

        tx_hash = await mock_registry.issue_seal(address, seal_type)

        assert tx_hash is not None
        assert await mock_registry.has_seal(address, seal_type) is True

    @pytest.mark.asyncio
    async def test_duplicate_seal_fails(self, mock_registry):
        """Test that duplicate seals are rejected."""
        address = "0x1234567890123456789012345678901234567890"
        seal_type = WorkSealType.TASKS_10.value

        # First issuance succeeds
        tx1 = await mock_registry.issue_seal(address, seal_type)
        assert tx1 is not None

        # Second issuance fails
        tx2 = await mock_registry.issue_seal(address, seal_type)
        assert tx2 is None

    @pytest.mark.asyncio
    async def test_get_seals(self, populated_registry):
        """Test retrieving all seals for a holder."""
        address = "0x1234567890123456789012345678901234567890"
        seals = await populated_registry.get_seals(address)

        assert len(seals) == 5
        seal_types = {s.seal_type for s in seals}
        assert WorkSealType.TASKS_100.value in seal_types
        assert SkillSealType.DELIVERY_CERTIFIED.value in seal_types

    @pytest.mark.asyncio
    async def test_get_seal_bundle(self, populated_registry):
        """Test retrieving seal bundle."""
        address = "0x1234567890123456789012345678901234567890"
        bundle = await populated_registry.get_seal_bundle(address)

        assert bundle.total_count == 5
        assert len(bundle.work_seals) == 3
        assert len(bundle.skill_seals) == 1
        assert len(bundle.behavior_seals) == 1

    @pytest.mark.asyncio
    async def test_revoke_seal(self, populated_registry):
        """Test revoking a seal."""
        address = "0x1234567890123456789012345678901234567890"
        seal_type = WorkSealType.TASKS_10.value

        # Verify seal exists
        assert await populated_registry.has_seal(address, seal_type) is True

        # Revoke
        tx = await populated_registry.revoke_seal(address, seal_type, "Testing")
        assert tx is not None

        # Seal should no longer be valid
        assert await populated_registry.has_seal(address, seal_type) is False


# =============================================================================
# ISSUANCE TESTS
# =============================================================================

class TestEligibilityChecking:
    """Tests for eligibility checking."""

    def test_check_tasks_100_eligible(self, issuance_service, sample_worker_stats):
        """Test worker eligible for 100 tasks seal."""
        req = get_requirement(WorkSealType.TASKS_100.value)
        result = issuance_service.check_eligibility(sample_worker_stats, req)

        assert result.is_eligible is True
        assert len(result.missing_requirements) == 0

    def test_check_tasks_500_not_eligible(self, issuance_service, sample_worker_stats):
        """Test worker not eligible for 500 tasks seal."""
        req = get_requirement(WorkSealType.TASKS_500.value)
        result = issuance_service.check_eligibility(sample_worker_stats, req)

        assert result.is_eligible is False
        assert len(result.missing_requirements) > 0
        assert "500" in result.missing_requirements[0]

    def test_check_earnings_eligible(self, issuance_service, sample_worker_stats):
        """Test worker eligible for $1000 earnings seal."""
        req = get_requirement(WorkSealType.EARNED_1000_USD.value)
        result = issuance_service.check_eligibility(sample_worker_stats, req)

        assert result.is_eligible is True

    def test_check_fast_responder_eligible(self, issuance_service, sample_worker_stats):
        """Test worker eligible for fast responder seal."""
        req = get_requirement(BehaviorSealType.FAST_RESPONDER.value)
        result = issuance_service.check_eligibility(sample_worker_stats, req)

        assert result.is_eligible is True

    def test_check_all_eligibility(self, issuance_service, sample_worker_stats):
        """Test checking all automatic seal eligibility."""
        results = issuance_service.check_all_eligibility(sample_worker_stats)

        # Should check multiple seals
        assert len(results) > 5

        # Some should be eligible, some not
        eligible = [r for r in results if r.is_eligible]
        not_eligible = [r for r in results if not r.is_eligible]

        assert len(eligible) > 0
        assert len(not_eligible) > 0


class TestSealIssuance:
    """Tests for seal issuance."""

    @pytest.mark.asyncio
    async def test_issue_seal(self, issuance_service):
        """Test issuing a single seal."""
        address = "0x1234567890123456789012345678901234567890"

        result = await issuance_service.issue_seal(
            address,
            WorkSealType.TASKS_10.value
        )

        assert result.success is True
        assert result.tx_hash is not None
        assert result.error is None

    @pytest.mark.asyncio
    async def test_issue_duplicate_fails(self, issuance_service):
        """Test that duplicate issuance fails."""
        address = "0x1234567890123456789012345678901234567890"
        seal_type = WorkSealType.TASKS_10.value

        # First succeeds
        result1 = await issuance_service.issue_seal(address, seal_type)
        assert result1.success is True

        # Second fails
        result2 = await issuance_service.issue_seal(address, seal_type)
        assert result2.success is False
        assert "already has" in result2.error

    @pytest.mark.asyncio
    async def test_check_and_issue_automatic(self, issuance_service, sample_worker_stats):
        """Test automatic seal issuance based on stats."""
        results = await issuance_service.check_and_issue_automatic(sample_worker_stats)

        # Should issue some seals
        successful = [r for r in results if r.success]
        assert len(successful) > 0

        # Check expected seals were issued
        issued_types = {r.seal_type for r in successful}
        assert WorkSealType.TASKS_100.value in issued_types
        assert WorkSealType.EARNED_1000_USD.value in issued_types

    @pytest.mark.asyncio
    async def test_dry_run_no_issuance(self, issuance_service, sample_worker_stats):
        """Test dry run mode doesn't actually issue."""
        results = await issuance_service.check_and_issue_automatic(
            sample_worker_stats,
            dry_run=True
        )

        # Should have results
        assert len(results) > 0

        # But no actual transactions
        for result in results:
            assert result.tx_hash is None
            assert result.error == "DRY_RUN"


# =============================================================================
# VERIFICATION TESTS
# =============================================================================

class TestSealVerification:
    """Tests for seal verification."""

    @pytest.mark.asyncio
    async def test_verify_existing_seal(self, verification_service, populated_registry):
        """Test verifying an existing seal."""
        address = "0x1234567890123456789012345678901234567890"

        result = await verification_service.verify_seal(
            address,
            WorkSealType.TASKS_100.value
        )

        assert result.is_valid is True
        assert result.status == SealStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_verify_nonexistent_seal(self, verification_service, mock_registry):
        """Test verifying a seal that doesn't exist."""
        address = "0x1234567890123456789012345678901234567890"

        result = await verification_service.verify_seal(
            address,
            WorkSealType.TASKS_1000.value
        )

        assert result.is_valid is False
        assert "not found" in result.verification_details.get("reason", "")

    @pytest.mark.asyncio
    async def test_task_eligibility_met(self, verification_service, populated_registry):
        """Test task eligibility when requirements are met."""
        address = "0x1234567890123456789012345678901234567890"

        requirements = TaskSealRequirement(
            required_seals=[SkillSealType.DELIVERY_CERTIFIED.value],
            preferred_seals=[WorkSealType.TASKS_100.value],
            any_of_seals=[]
        )

        result = await verification_service.check_task_eligibility(
            address, requirements
        )

        assert result.is_eligible is True
        assert len(result.missing_required) == 0
        assert WorkSealType.TASKS_100.value in result.has_preferred

    @pytest.mark.asyncio
    async def test_task_eligibility_not_met(self, verification_service, mock_registry):
        """Test task eligibility when requirements are not met."""
        address = "0x1234567890123456789012345678901234567890"

        requirements = TaskSealRequirement(
            required_seals=[SkillSealType.PHOTOGRAPHY_PROFESSIONAL.value],
            preferred_seals=[],
            any_of_seals=[]
        )

        result = await verification_service.check_task_eligibility(
            address, requirements
        )

        assert result.is_eligible is False
        assert SkillSealType.PHOTOGRAPHY_PROFESSIONAL.value in result.missing_required

    @pytest.mark.asyncio
    async def test_seal_gate_check(self, verification_service, populated_registry):
        """Test seal gate checking."""
        address = "0x1234567890123456789012345678901234567890"

        gate_config = {
            "all": [WorkSealType.TASKS_100.value],
            "any": [SkillSealType.DELIVERY_CERTIFIED.value, SkillSealType.PHOTOGRAPHY_VERIFIED.value],
        }

        result = await verification_service.check_seal_gate(address, gate_config)

        assert result["passed"] is True


# =============================================================================
# DISPLAY TESTS
# =============================================================================

class TestSealDisplay:
    """Tests for seal display formatting."""

    @pytest.mark.asyncio
    async def test_format_profile(self, display_formatter, populated_registry):
        """Test formatting seals for profile display."""
        address = "0x1234567890123456789012345678901234567890"
        bundle = await populated_registry.get_seal_bundle(address)

        profile = display_formatter.format_profile(bundle)

        assert profile["summary"]["total_seals"] == 5
        assert len(profile["skill_seals"]) == 1
        assert len(profile["work_seals"]) == 3
        assert profile["category_names"]["skill"] == "Habilidades"

    @pytest.mark.asyncio
    async def test_format_card(self, display_formatter, populated_registry):
        """Test formatting seals for card display."""
        address = "0x1234567890123456789012345678901234567890"
        bundle = await populated_registry.get_seal_bundle(address)

        card = display_formatter.format_card(bundle, max_display=3)

        assert card["total_seals"] == 5
        assert len(card["seals"]) <= 3
        assert card["more_count"] >= 2
        assert "sellos verificados" in card["summary_text"]

    def test_format_single_seal(self, display_formatter, sample_seal):
        """Test formatting a single seal."""
        formatted = display_formatter.format_seal(sample_seal, "profile")

        assert formatted["seal_type"] == WorkSealType.TASKS_100.value
        assert formatted["is_valid"] is True
        assert "display_name" in formatted
        assert "tier" in formatted

    def test_format_badge(self, display_formatter, sample_seal):
        """Test formatting a seal as a badge."""
        badge = display_formatter.format_badge(sample_seal, size="medium")

        assert badge["size"] == "medium"
        assert badge["show_text"] is True
        assert "icon" in badge
        assert "color" in badge

    def test_get_display_name_spanish(self):
        """Test getting Spanish display name."""
        name = get_seal_display_name(WorkSealType.TASKS_100.value, "es")
        assert "100" in name
        assert "Completadas" in name

    def test_get_display_name_english(self):
        """Test getting English display name."""
        name = get_seal_display_name(WorkSealType.TASKS_100.value, "en")
        assert "100" in name
        assert "Completed" in name

    def test_format_notification(self, display_formatter, sample_seal):
        """Test formatting seal notification."""
        notif = display_formatter.format_seal_notification(sample_seal, "issued")

        assert "Nuevo sello" in notif["title"]
        assert "obtenido" in notif["body"]
        assert "icon" in notif


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests across modules."""

    @pytest.mark.asyncio
    async def test_full_issuance_and_verification_flow(self, mock_registry):
        """Test complete flow from stats to verification."""
        address = "0xabcdef1234567890abcdef1234567890abcdef12"

        # Setup services
        issuance = SealIssuanceService(mock_registry)
        verification = SealVerificationService(mock_registry)
        display = SealDisplayFormatter(DisplayConfig(locale="es"))

        # Create worker stats
        stats = WorkerStats(
            wallet_address=address,
            total_tasks_completed=150,
            total_earnings_usd=2000.0,
            average_rating=92.0,
            active_days=100,
        )

        # Issue automatic seals
        results = await issuance.check_and_issue_automatic(stats)
        assert len([r for r in results if r.success]) > 0

        # Verify issued seals
        bundle = await mock_registry.get_seal_bundle(address)
        assert bundle.total_count > 0

        # Check task eligibility
        requirements = TaskSealRequirement(
            required_seals=[WorkSealType.TASKS_100.value],
            preferred_seals=[WorkSealType.EARNED_1000_USD.value],
            any_of_seals=[]
        )
        eligibility = await verification.check_task_eligibility(address, requirements)
        assert eligibility.is_eligible is True

        # Format for display
        profile = display.format_profile(bundle)
        assert profile["summary"]["active_seals"] > 0

    @pytest.mark.asyncio
    async def test_expiring_seal_handling(self, mock_registry):
        """Test handling of expiring seals."""
        address = "0xabcdef1234567890abcdef1234567890abcdef12"

        # Issue seal that expires soon
        await mock_registry.issue_seal(
            address,
            BehaviorSealType.FAST_RESPONDER.value,
            expires_at=datetime.now(UTC) + timedelta(days=5)
        )

        # Get statistics
        verification = SealVerificationService(mock_registry)
        stats = await verification.get_seal_statistics(address)

        # Should show expiring seal
        assert len(stats["expiring_soon"]) == 1
        assert stats["expiring_soon"][0]["seal_type"] == BehaviorSealType.FAST_RESPONDER.value
