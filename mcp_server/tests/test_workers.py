"""
Tests for Worker Experience Module

Tests covering:
- Probation system (NOW-174)
- Recovery paths (NOW-175)
- Time-based premiums (NOW-176)
- Worker categorization (NOW-177, NOW-178, NOW-179)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from workers.probation import (
    WorkerTier,
    ProbationStatus,
    ProbationConfig,
    ProbationManager,
)
from workers.recovery import (
    RecoveryStatus,
    RecoveryPath,
    RecoveryConfig,
    RecoveryManager,
)
from workers.premiums import (
    PremiumType,
    PremiumConfig,
    PremiumCalculator,
    calculate_task_premium,
)
from workers.categories import (
    ExpertiseLevel,
    Modality,
    EquipmentType,
    WorkerProfile,
    GeoLocation,
    CategoryFilter,
    CategoryManager,
)


# ==================== PROBATION TESTS ====================


class TestProbationManager:
    """Tests for ProbationManager."""

    @pytest.fixture
    def manager(self):
        """Create a manager with default config."""
        return ProbationManager()

    @pytest.fixture
    def custom_manager(self):
        """Create a manager with custom config."""
        config = ProbationConfig(
            probation_task_count=5,
            probation_max_value=10.00,
        )
        return ProbationManager(config)

    @pytest.mark.asyncio
    async def test_new_worker_is_probation(self, manager):
        """New workers should start in probation."""
        status = await manager.get_status("new_worker_123")

        assert status.tier == WorkerTier.PROBATION
        assert status.tasks_completed == 0
        assert status.max_task_value == 5.00
        assert status.extra_verification_required is True

    @pytest.mark.asyncio
    async def test_probation_task_value_limit(self, manager):
        """Probation workers cannot accept high-value tasks."""
        # Should be eligible for low-value task
        eligibility = await manager.check_task_eligibility(
            "probation_worker",
            task_value=3.00
        )
        assert eligibility.eligible is True

        # Should not be eligible for high-value task
        eligibility = await manager.check_task_eligibility(
            "probation_worker",
            task_value=50.00
        )
        assert eligibility.eligible is False
        assert "Maximum task value" in eligibility.reason

    @pytest.mark.asyncio
    async def test_probation_extra_verification(self, manager):
        """Probation workers should have extra verification requirements."""
        eligibility = await manager.check_task_eligibility(
            "probation_worker",
            task_value=3.00
        )

        assert eligibility.eligible is True
        assert "photo_selfie" in eligibility.extra_verification
        assert "realtime_timestamp" in eligibility.extra_verification

    @pytest.mark.asyncio
    async def test_task_completion_updates_status(self, manager):
        """Completing tasks should update probation status."""
        worker_id = "progress_worker"

        # Complete a task
        status = await manager.record_task_completion(
            worker_id=worker_id,
            task_id="task_1",
            rating=4.5,
            task_value=3.00
        )

        assert status.tasks_completed == 1
        assert status.average_rating == 4.5

        # Complete more tasks
        for i in range(9):
            status = await manager.record_task_completion(
                worker_id=worker_id,
                task_id=f"task_{i+2}",
                rating=4.0,
                task_value=4.00
            )

        # Should now have 10 tasks
        assert status.tasks_completed == 10

    @pytest.mark.asyncio
    async def test_graduation_requires_identity_verification(self, manager):
        """Workers need identity verification to graduate."""
        worker_id = "graduate_worker"

        # Complete 10 tasks with good ratings
        for i in range(10):
            await manager.record_task_completion(
                worker_id=worker_id,
                task_id=f"task_{i}",
                rating=4.5,
                task_value=4.00
            )

        status = await manager.get_status(worker_id)

        # Should still be probation without identity verification
        assert status.tier == WorkerTier.PROBATION
        assert status.can_graduate is False

        # Verify identity
        status = await manager.record_identity_verification(
            worker_id=worker_id,
            verified=True,
            verification_method="passport"
        )

        # Should now graduate to standard
        assert status.tier == WorkerTier.STANDARD
        assert status.graduated_at is not None

    @pytest.mark.asyncio
    async def test_suspension_on_low_rating(self, manager):
        """Workers with very low ratings should be suspended."""
        worker_id = "bad_worker"

        # Complete 5 tasks with terrible ratings
        for i in range(5):
            await manager.record_task_completion(
                worker_id=worker_id,
                task_id=f"task_{i}",
                rating=1.5,
                task_value=3.00
            )

        status = await manager.get_status(worker_id)

        # Should be suspended
        assert status.tier == WorkerTier.SUSPENDED
        assert "rating" in status.suspension_reason.lower()

    @pytest.mark.asyncio
    async def test_tier_benefits(self, manager):
        """Verify tier benefits are correct."""
        probation_benefits = manager.get_tier_benefits(WorkerTier.PROBATION)
        assert probation_benefits["max_task_value"] == 5.00
        assert probation_benefits["max_concurrent_tasks"] == 1
        assert probation_benefits["instant_payout"] is False

        trusted_benefits = manager.get_tier_benefits(WorkerTier.TRUSTED)
        assert trusted_benefits["max_task_value"] == 5000.0
        assert trusted_benefits["priority_access"] is True
        assert trusted_benefits["instant_payout"] is True


# ==================== RECOVERY TESTS ====================


class TestRecoveryManager:
    """Tests for RecoveryManager."""

    @pytest.fixture
    def manager(self):
        """Create a manager with default config."""
        return RecoveryManager()

    @pytest.fixture
    def fast_manager(self):
        """Create a manager with shorter cooloff for testing."""
        config = RecoveryConfig(cooloff_days=1)
        return RecoveryManager(config)

    @pytest.mark.asyncio
    async def test_check_eligibility_for_suspended_worker(self, manager):
        """Suspended workers should be eligible for recovery."""
        eligibility = await manager.check_eligibility("suspended_worker")

        assert eligibility.eligible is True
        assert len(eligibility.requirements) > 0
        assert any("cooloff" in r.lower() for r in eligibility.requirements)

    @pytest.mark.asyncio
    async def test_initiate_recovery(self, manager):
        """Should be able to initiate recovery for eligible worker."""
        path = await manager.initiate_recovery(
            worker_id="suspended_worker",
            suspension_reason="Too many disputes",
            suspension_date=datetime.now(timezone.utc) - timedelta(days=7)
        )

        assert path.status == RecoveryStatus.COOLOFF
        assert path.cooloff_remaining_days > 0
        assert path.worker_id == "suspended_worker"

    @pytest.mark.asyncio
    async def test_cannot_initiate_recovery_twice(self, manager):
        """Cannot have two active recoveries."""
        # First recovery
        await manager.initiate_recovery(
            worker_id="double_recovery",
            suspension_reason="Test",
            suspension_date=datetime.now(timezone.utc)
        )

        # Second attempt should check eligibility and fail
        eligibility = await manager.check_eligibility("double_recovery")
        assert eligibility.eligible is False
        assert "already in progress" in eligibility.reason.lower()

    @pytest.mark.asyncio
    async def test_cooloff_progress(self, fast_manager):
        """Cooloff status should progress correctly."""
        path = await fast_manager.initiate_recovery(
            worker_id="cooloff_worker",
            suspension_reason="Test",
            suspension_date=datetime.now(timezone.utc)
        )

        # Initially in cooloff
        assert path.status == RecoveryStatus.COOLOFF
        assert not path.is_cooloff_complete

        # Simulate cooloff completion by adjusting the end date
        path.cooloff_ends_at = datetime.now(timezone.utc) - timedelta(hours=1)

        # Check status should advance to verification
        updated = await fast_manager.check_cooloff_status("cooloff_worker")
        assert updated.status == RecoveryStatus.VERIFICATION

    @pytest.mark.asyncio
    async def test_identity_reverification(self, manager):
        """Should require identity re-verification during recovery."""
        # Start recovery
        path = await manager.initiate_recovery(
            worker_id="verify_worker",
            suspension_reason="Test",
            suspension_date=datetime.now(timezone.utc)
        )

        # Advance past cooloff
        path.cooloff_ends_at = datetime.now(timezone.utc) - timedelta(hours=1)
        path.status = RecoveryStatus.VERIFICATION

        # Record verification
        updated = await manager.record_identity_verification(
            worker_id="verify_worker",
            verified=True,
            verification_method="drivers_license"
        )

        assert updated.identity_reverified is True

    @pytest.mark.asyncio
    async def test_recovery_rejection(self, manager):
        """Recovery can be rejected by admin."""
        # Start recovery
        await manager.initiate_recovery(
            worker_id="reject_worker",
            suspension_reason="Fraud",
            suspension_date=datetime.now(timezone.utc)
        )

        # Reject
        path = await manager.reject_recovery(
            worker_id="reject_worker",
            rejected_by="admin_1",
            reason="Evidence of repeated fraud"
        )

        assert path.status == RecoveryStatus.REJECTED
        assert "fraud" in path.resolution_notes.lower()


# ==================== PREMIUM TESTS ====================


class TestPremiumCalculator:
    """Tests for PremiumCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create a calculator with default config."""
        return PremiumCalculator()

    def test_no_premium_weekday_daytime(self, calculator):
        """No premium for regular weekday daytime."""
        # Tuesday at 2pm
        work_time = datetime(2026, 1, 27, 14, 0, tzinfo=timezone.utc)

        premium = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="UTC"
        )

        assert premium.premium_percentage == 0
        assert premium.total_amount == 100.0

    def test_weekend_premium(self, calculator):
        """Weekend should add 15% premium."""
        # Saturday at 2pm
        work_time = datetime(2026, 1, 24, 14, 0, tzinfo=timezone.utc)

        premium = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="UTC"
        )

        assert premium.premium_percentage == 15.0
        assert premium.total_amount == 115.0
        assert any(p["type"] == "weekend" for p in premium.applied_premiums)

    def test_night_premium(self, calculator):
        """Night hours should add 25% premium."""
        # Wednesday at 10pm
        work_time = datetime(2026, 1, 28, 22, 0, tzinfo=timezone.utc)

        premium = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="UTC"
        )

        assert premium.premium_percentage == 25.0
        assert premium.total_amount == 125.0
        assert any(p["type"] == "night" for p in premium.applied_premiums)

    def test_stacked_premiums(self, calculator):
        """Weekend + night should stack."""
        # Saturday at 10pm
        work_time = datetime(2026, 1, 24, 22, 0, tzinfo=timezone.utc)

        premium = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="UTC"
        )

        # 15% weekend + 25% night = 40%
        assert premium.premium_percentage == 40.0
        assert premium.total_amount == 140.0

    def test_holiday_premium(self, calculator):
        """Holidays should add 50% premium."""
        # Christmas
        work_time = datetime(2026, 12, 25, 14, 0, tzinfo=timezone.utc)

        premium = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="UTC"
        )

        assert premium.premium_percentage >= 50.0
        assert any(p["type"] == "holiday" for p in premium.applied_premiums)

    def test_country_specific_holiday(self, calculator):
        """Country-specific holidays should apply."""
        # Mexican Independence Day
        work_time = datetime(2026, 9, 16, 14, 0, tzinfo=timezone.utc)

        # For Mexican worker
        premium_mx = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="America/Mexico_City",
            worker_country="MX"
        )

        # For US worker (not a holiday)
        premium_us = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="America/New_York",
            worker_country="US"
        )

        assert premium_mx.premium_percentage > premium_us.premium_percentage

    def test_urgent_premium(self, calculator):
        """Urgent tasks (short deadline) should add premium."""
        premium = calculator.calculate_premium(
            base_amount=100.0,
            deadline_hours=2  # Very urgent
        )

        assert premium.premium_percentage >= 20.0
        assert any(p["type"] == "urgent" for p in premium.applied_premiums)

    def test_premium_cap(self, calculator):
        """Total premium should be capped."""
        # Try to stack everything: weekend + night + holiday + urgent
        work_time = datetime(2026, 12, 25, 22, 0, tzinfo=timezone.utc)

        premium = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            deadline_hours=2,
            demand_multiplier=3.0  # High surge
        )

        # Should be capped at 100%
        assert premium.premium_percentage <= 100.0
        assert premium.total_amount <= 200.0

    def test_timezone_aware_night(self, calculator):
        """Night hours should be calculated in worker's timezone."""
        # 10pm UTC = 4pm Mexico City (not night there)
        work_time = datetime(2026, 1, 28, 22, 0, tzinfo=timezone.utc)

        premium_mexico = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="America/Mexico_City"
        )

        premium_utc = calculator.calculate_premium(
            base_amount=100.0,
            work_time=work_time,
            worker_timezone="UTC"
        )

        # UTC should have night premium, Mexico should not
        assert premium_utc.premium_percentage > premium_mexico.premium_percentage

    def test_convenience_function(self):
        """Test the convenience function."""
        premium = calculate_task_premium(
            base_amount=50.0,
            worker_timezone="America/Los_Angeles",
        )

        assert premium.base_amount == 50.0
        assert premium.total_amount >= 50.0


# ==================== CATEGORY TESTS ====================


class TestCategoryManager:
    """Tests for CategoryManager."""

    @pytest.fixture
    def manager(self):
        """Create a manager."""
        return CategoryManager()

    @pytest.mark.asyncio
    async def test_create_profile(self, manager):
        """Should create worker profile."""
        location = GeoLocation(
            country_code="MX",
            city="Mexico City",
            latitude=19.4326,
            longitude=-99.1332
        )

        profile = await manager.create_profile(
            worker_id="new_worker",
            display_name="Juan Perez",
            primary_location=location
        )

        assert profile.worker_id == "new_worker"
        assert profile.display_name == "Juan Perez"
        assert profile.primary_location.city == "Mexico City"

    @pytest.mark.asyncio
    async def test_add_expertise(self, manager):
        """Should add expertise to profile."""
        # Create profile first
        await manager.create_profile(
            worker_id="expert_worker",
            display_name="Expert"
        )

        # Add expertise
        profile = await manager.add_expertise(
            worker_id="expert_worker",
            expertise_code="content_photo",
            level=ExpertiseLevel.ADVANCED,
            verified=True,
            verified_by="admin"
        )

        assert len(profile.expertise) == 1
        assert profile.expertise[0].category_code == "content_photo"
        assert profile.expertise[0].level == ExpertiseLevel.ADVANCED
        assert profile.expertise[0].verified is True

    @pytest.mark.asyncio
    async def test_set_equipment(self, manager):
        """Should set worker equipment."""
        await manager.create_profile("equip_worker", "Equipment Worker")

        profile = await manager.set_equipment(
            worker_id="equip_worker",
            equipment=[
                EquipmentType.SMARTPHONE,
                EquipmentType.CAMERA_DSLR,
                EquipmentType.VEHICLE_CAR
            ]
        )

        assert len(profile.equipment) == 3
        assert EquipmentType.CAMERA_DSLR in profile.equipment

    @pytest.mark.asyncio
    async def test_set_modalities(self, manager):
        """Should set work modalities."""
        await manager.create_profile("modal_worker", "Modal Worker")

        profile = await manager.set_modalities(
            worker_id="modal_worker",
            modalities=[Modality.HYBRID, Modality.MOBILE]
        )

        assert Modality.HYBRID in profile.modalities
        assert Modality.MOBILE in profile.modalities

    @pytest.mark.asyncio
    async def test_find_workers_by_expertise(self, manager):
        """Should find workers by expertise."""
        # Create workers with different expertise
        await manager.create_profile("photo_worker", "Photographer")
        await manager.add_expertise(
            "photo_worker",
            "content_photo",
            ExpertiseLevel.ADVANCED
        )

        await manager.create_profile("writer_worker", "Writer")
        await manager.add_expertise(
            "writer_worker",
            "content_writing",
            ExpertiseLevel.INTERMEDIATE
        )

        # Search for photographers
        matches = await manager.find_workers(CategoryFilter(
            required_expertise=["content_photo"],
            min_expertise_level=ExpertiseLevel.INTERMEDIATE
        ))

        assert len(matches) >= 1
        assert any(m.worker_id == "photo_worker" for m in matches)
        assert not any(m.worker_id == "writer_worker" for m in matches)

    @pytest.mark.asyncio
    async def test_find_workers_by_location(self, manager):
        """Should find workers by location."""
        # Create workers in different locations
        await manager.create_profile("mx_worker", "Mexico Worker")
        await manager.update_location(
            "mx_worker",
            GeoLocation(country_code="MX", city="Guadalajara")
        )

        await manager.create_profile("us_worker", "US Worker")
        await manager.update_location(
            "us_worker",
            GeoLocation(country_code="US", city="Los Angeles")
        )

        # Search for Mexican workers
        matches = await manager.find_workers(CategoryFilter(
            country_codes=["MX"]
        ))

        assert len(matches) >= 1
        assert any(m.worker_id == "mx_worker" for m in matches)

    @pytest.mark.asyncio
    async def test_find_workers_by_equipment(self, manager):
        """Should find workers with required equipment."""
        await manager.create_profile("car_worker", "Driver")
        await manager.set_equipment("car_worker", [
            EquipmentType.VEHICLE_CAR,
            EquipmentType.SMARTPHONE
        ])

        await manager.create_profile("bike_worker", "Cyclist")
        await manager.set_equipment("bike_worker", [
            EquipmentType.VEHICLE_BICYCLE,
            EquipmentType.SMARTPHONE
        ])

        # Search for workers with cars
        matches = await manager.find_workers(CategoryFilter(
            required_equipment=[EquipmentType.VEHICLE_CAR]
        ))

        assert any(m.worker_id == "car_worker" for m in matches)
        assert not any(m.worker_id == "bike_worker" for m in matches)

    @pytest.mark.asyncio
    async def test_match_score_calculation(self, manager):
        """Match score should reflect how well worker matches criteria."""
        # Create a worker with many qualifications
        await manager.create_profile("perfect_worker", "Perfect Match")
        await manager.update_location(
            "perfect_worker",
            GeoLocation(country_code="MX", city="Mexico City")
        )
        await manager.add_expertise(
            "perfect_worker",
            "content_photo",
            ExpertiseLevel.ADVANCED
        )
        await manager.set_equipment("perfect_worker", [
            EquipmentType.CAMERA_DSLR,
            EquipmentType.SMARTPHONE
        ])

        # Create a partial match
        await manager.create_profile("partial_worker", "Partial Match")
        await manager.update_location(
            "partial_worker",
            GeoLocation(country_code="MX", city="Monterrey")
        )
        await manager.add_expertise(
            "partial_worker",
            "content_photo",
            ExpertiseLevel.NOVICE  # Lower level
        )

        # Search with specific criteria
        matches = await manager.find_workers(CategoryFilter(
            country_codes=["MX"],
            cities=["Mexico City"],
            required_expertise=["content_photo"],
            min_expertise_level=ExpertiseLevel.INTERMEDIATE,
            required_equipment=[EquipmentType.CAMERA_DSLR]
        ))

        # Perfect worker should score higher
        perfect = next((m for m in matches if m.worker_id == "perfect_worker"), None)
        partial = next((m for m in matches if m.worker_id == "partial_worker"), None)

        assert perfect is not None
        assert perfect.match_score > 0.5
        if partial:
            assert perfect.match_score > partial.match_score

    @pytest.mark.asyncio
    async def test_language_matching(self, manager):
        """Should match workers by language."""
        await manager.create_profile("spanish_worker", "Spanish Speaker")
        await manager.add_language("spanish_worker", "es", "native")
        await manager.add_language("spanish_worker", "en", "conversational")

        await manager.create_profile("english_worker", "English Speaker")
        await manager.add_language("english_worker", "en", "native")

        # Search for Spanish speakers
        matches = await manager.find_workers(CategoryFilter(
            required_languages=["es"]
        ))

        assert any(m.worker_id == "spanish_worker" for m in matches)

    def test_expertise_tree(self, manager):
        """Should return hierarchical expertise tree."""
        tree = manager.get_expertise_tree()

        assert "tech" in tree
        assert "content" in tree
        assert "field" in tree

        # Check children
        assert "children" in tree["tech"]
        assert len(tree["tech"]["children"]) > 0

    @pytest.mark.asyncio
    async def test_profile_completeness(self, manager):
        """Profile completeness should update with each addition."""
        profile = await manager.create_profile("complete_worker", "Complete")

        initial_completeness = profile.profile_completeness

        # Add location
        await manager.update_location(
            "complete_worker",
            GeoLocation(country_code="MX", city="Mexico City")
        )

        # Add expertise
        await manager.add_expertise(
            "complete_worker",
            "content_photo",
            ExpertiseLevel.INTERMEDIATE
        )

        # Add language
        await manager.add_language("complete_worker", "es", "native")

        profile = await manager.get_profile("complete_worker")
        assert profile.profile_completeness > initial_completeness
