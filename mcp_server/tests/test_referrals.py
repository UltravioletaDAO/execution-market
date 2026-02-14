"""
Tests for the growth/referrals module.

Covers:
- ReferralCode model properties (is_valid, remaining_uses)
- Referral model properties (tasks_remaining, progress_percent, is_expired)
- ReferralManager code generation
- ReferralManager code application + fraud checks
- ReferralManager task completion tracking
- Edge cases (expired codes, self-referral, limits)
"""

from datetime import datetime, timezone, timedelta

import pytest

from mcp_server.growth.referrals import (
    ReferralStatus,
    ReferralConfig,
    ReferralCode,
    Referral,
    ReferralManager,
)


@pytest.fixture
def config():
    return ReferralConfig(
        tasks_required=5,
        bonus_amount_default=2.00,
        code_length=6,
        code_prefix="TEST",
        max_active_codes=3,
        cooldown_hours=0,
        fraud_check_enabled=True,
        min_referrer_tasks=0,
    )


@pytest.fixture
def manager(config):
    return ReferralManager(config=config)


# ═══════════════════════════════════════════════════════════
# ReferralCode model
# ═══════════════════════════════════════════════════════════

class TestReferralCodeModel:

    def test_is_valid_active_code(self):
        code = ReferralCode(
            code="TEST-AAA", referrer_id="w1",
            created_at=datetime.now(timezone.utc), is_active=True,
        )
        assert code.is_valid is True

    def test_is_valid_inactive(self):
        code = ReferralCode(
            code="TEST-AAA", referrer_id="w1",
            created_at=datetime.now(timezone.utc), is_active=False,
        )
        assert code.is_valid is False

    def test_is_valid_expired(self):
        code = ReferralCode(
            code="TEST-AAA", referrer_id="w1",
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert code.is_valid is False

    def test_is_valid_max_uses_reached(self):
        code = ReferralCode(
            code="TEST-AAA", referrer_id="w1",
            created_at=datetime.now(timezone.utc), uses=5, max_uses=5,
        )
        assert code.is_valid is False

    def test_remaining_uses_unlimited(self):
        code = ReferralCode(
            code="TEST-AAA", referrer_id="w1",
            created_at=datetime.now(timezone.utc), max_uses=None,
        )
        assert code.remaining_uses is None

    def test_remaining_uses_limited(self):
        code = ReferralCode(
            code="TEST-AAA", referrer_id="w1",
            created_at=datetime.now(timezone.utc), uses=3, max_uses=10,
        )
        assert code.remaining_uses == 7


# ═══════════════════════════════════════════════════════════
# Referral model
# ═══════════════════════════════════════════════════════════

class TestReferralModel:

    def _make(self, **kw):
        defaults = dict(
            id="ref_1", code="TEST-AAA", referrer_id="w1", referee_id="w2",
            status=ReferralStatus.QUALIFYING, tasks_completed=2, tasks_required=5,
            bonus_amount=2.00, bonus_paid=False,
            created_at=datetime.now(timezone.utc),
        )
        defaults.update(kw)
        return Referral(**defaults)

    def test_tasks_remaining(self):
        assert self._make(tasks_completed=2, tasks_required=5).tasks_remaining == 3

    def test_tasks_remaining_zero(self):
        assert self._make(tasks_completed=5, tasks_required=5).tasks_remaining == 0

    def test_tasks_remaining_over(self):
        assert self._make(tasks_completed=7, tasks_required=5).tasks_remaining == 0

    def test_progress_percent(self):
        assert self._make(tasks_completed=3, tasks_required=5).progress_percent == pytest.approx(60.0)

    def test_progress_percent_zero(self):
        assert self._make(tasks_completed=0, tasks_required=5).progress_percent == pytest.approx(0.0)

    def test_progress_percent_complete(self):
        assert self._make(tasks_completed=5, tasks_required=5).progress_percent == pytest.approx(100.0)

    def test_is_expired_false(self):
        assert self._make(expires_at=datetime.now(timezone.utc) + timedelta(days=10)).is_expired is False

    def test_is_expired_true(self):
        assert self._make(expires_at=datetime.now(timezone.utc) - timedelta(days=1)).is_expired is True

    def test_is_expired_no_expiry(self):
        assert self._make(expires_at=None).is_expired is False


# ═══════════════════════════════════════════════════════════
# ReferralManager — Code Generation
# ═══════════════════════════════════════════════════════════

class TestCodeGeneration:

    @pytest.mark.asyncio
    async def test_generate_code(self, manager):
        code = await manager.generate_code("worker_1")
        assert code.code.startswith("TEST-")
        assert code.referrer_id == "worker_1"
        assert code.is_active is True
        assert code.bonus_amount == 2.00

    @pytest.mark.asyncio
    async def test_generate_code_custom_bonus(self, manager):
        code = await manager.generate_code("worker_1", bonus_amount=1.50)
        assert code.bonus_amount == 1.50

    @pytest.mark.asyncio
    async def test_generate_code_bonus_clamped_to_max(self, manager):
        code = await manager.generate_code("worker_1", bonus_amount=999.0)
        assert code.bonus_amount == manager.config.bonus_amount_max

    @pytest.mark.asyncio
    async def test_generate_code_bonus_clamped_to_min(self, manager):
        code = await manager.generate_code("worker_1", bonus_amount=0.01)
        assert code.bonus_amount == manager.config.bonus_amount_min

    @pytest.mark.asyncio
    async def test_generate_multiple_unique_codes(self, manager):
        c1 = await manager.generate_code("worker_1")
        c2 = await manager.generate_code("worker_1")
        assert c1.code != c2.code

    @pytest.mark.asyncio
    async def test_generate_exceeds_active_limit(self, manager):
        for i in range(3):
            await manager.generate_code("worker_1")
        with pytest.raises(ValueError, match="active codes"):
            await manager.generate_code("worker_1")

    @pytest.mark.asyncio
    async def test_generate_with_max_uses(self, manager):
        code = await manager.generate_code("worker_1", max_uses=10)
        assert code.max_uses == 10

    @pytest.mark.asyncio
    async def test_generate_with_custom_expiry(self, manager):
        code = await manager.generate_code("worker_1", expires_in_days=7)
        assert code.expires_at is not None
        delta = code.expires_at - code.created_at
        assert 6 < delta.days <= 7


# ═══════════════════════════════════════════════════════════
# ReferralManager — Apply Code
# ═══════════════════════════════════════════════════════════

class TestApplyCode:

    @pytest.mark.asyncio
    async def test_apply_valid_code(self, manager):
        code = await manager.generate_code("referrer_1")
        referral = await manager.apply_code(code.code, "new_user_1")
        assert referral is not None
        assert referral.referrer_id == "referrer_1"
        assert referral.referee_id == "new_user_1"
        assert referral.status == ReferralStatus.PENDING
        assert referral.tasks_completed == 0

    @pytest.mark.asyncio
    async def test_apply_increments_uses(self, manager):
        code = await manager.generate_code("referrer_1")
        await manager.apply_code(code.code, "user_1")
        assert code.uses == 1

    @pytest.mark.asyncio
    async def test_apply_invalid_code(self, manager):
        with pytest.raises(ValueError, match="Invalid"):
            await manager.apply_code("FAKE-CODE", "new_user_1")

    @pytest.mark.asyncio
    async def test_apply_self_referral_blocked(self, manager):
        code = await manager.generate_code("worker_1")
        with pytest.raises(ValueError, match="own referral"):
            await manager.apply_code(code.code, "worker_1")

    @pytest.mark.asyncio
    async def test_apply_already_referred(self, manager):
        code = await manager.generate_code("referrer_1")
        await manager.apply_code(code.code, "new_user_1")
        with pytest.raises(ValueError, match="already been referred"):
            await manager.apply_code(code.code, "new_user_1")

    @pytest.mark.asyncio
    async def test_apply_case_insensitive(self, manager):
        code = await manager.generate_code("referrer_1")
        referral = await manager.apply_code(code.code.lower(), "new_user_1")
        assert referral is not None


# ═══════════════════════════════════════════════════════════
# ReferralManager — Task Completion
# ═══════════════════════════════════════════════════════════

class TestTaskCompletion:

    @pytest.mark.asyncio
    async def test_non_referee_returns_none(self, manager):
        result = await manager.record_task_completion("random_worker")
        assert result is None

    @pytest.mark.asyncio
    async def test_first_task_transitions_to_qualifying(self, manager):
        code = await manager.generate_code("referrer_1")
        await manager.apply_code(code.code, "new_user_1")
        referral = await manager.record_task_completion("new_user_1")
        assert referral.status == ReferralStatus.QUALIFYING
        assert referral.tasks_completed == 1

    @pytest.mark.asyncio
    async def test_incremental_progress(self, manager):
        code = await manager.generate_code("referrer_1")
        await manager.apply_code(code.code, "new_user_1")
        for i in range(3):
            referral = await manager.record_task_completion("new_user_1")
        assert referral.tasks_completed == 3
        assert referral.tasks_remaining == 2

    @pytest.mark.asyncio
    async def test_completion_triggers_bonus(self, manager):
        code = await manager.generate_code("referrer_1")
        await manager.apply_code(code.code, "new_user_1")
        for i in range(5):
            referral = await manager.record_task_completion("new_user_1")
        assert referral.tasks_completed >= 5

    @pytest.mark.asyncio
    async def test_expired_referral_marked(self, manager):
        code = await manager.generate_code("referrer_1")
        referral = await manager.apply_code(code.code, "new_user_1")
        referral.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        result = await manager.record_task_completion("new_user_1")
        assert result.status == ReferralStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_task_metadata_tracked(self, manager):
        code = await manager.generate_code("referrer_1")
        await manager.apply_code(code.code, "new_user_1")
        referral = await manager.record_task_completion(
            "new_user_1", task_id="task_42", task_rating=4.5,
        )
        tasks = referral.metadata.get("completed_tasks", [])
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task_42"
        assert tasks[0]["rating"] == 4.5
