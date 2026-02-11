"""
Tests for Worker Protection Fund (DORMANT — not wired into active endpoints)

(NOW-100, NOW-101)
"""

import pytest
from decimal import Decimal

pytestmark = pytest.mark.dormant

from ..protection.fund import (
    ProtectionFund,
    FundConfig,
    ClaimType,
    ClaimStatus,
    ContributionSource,
    FundError,
    InsufficientFundsError,
    ClaimLimitExceededError,
    ClaimNotFoundError,
    InvalidClaimStateError,
    get_fund,
    reset_fund,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fund():
    """Create a fresh ProtectionFund for each test."""
    return ProtectionFund(initial_balance=Decimal("1000.00"))


@pytest.fixture
def empty_fund():
    """Create an empty fund."""
    return ProtectionFund()


@pytest.fixture
def custom_config():
    """Custom configuration for testing limits."""
    return FundConfig(
        contribution_rate=Decimal("0.02"),  # 2% for testing different rate
        max_claim_amount=Decimal("100.00"),
        max_monthly_per_worker=Decimal("300.00"),
        min_claim_amount=Decimal("1.00"),
    )


# =============================================================================
# Contribution Tests (NOW-100)
# =============================================================================


class TestContributions:
    """Tests for fund contributions."""

    def test_contribute_from_fee_basic(self, fund):
        """Test basic fee contribution (1% of bounty)."""
        contrib = fund.contribute_from_fee("task123", Decimal("10.00"))

        assert contrib.amount == Decimal("0.10")  # 1% of $10
        assert contrib.source == ContributionSource.PLATFORM_FEE
        assert contrib.task_id == "task123"
        assert contrib.original_amount == Decimal("10.00")

    def test_contribute_from_fee_updates_balance(self, empty_fund):
        """Test that fee contributions update balance."""
        assert empty_fund.balance == Decimal("0")

        empty_fund.contribute_from_fee("task1", Decimal("100.00"))
        assert empty_fund.balance == Decimal("1.00")  # 1% of $100

        empty_fund.contribute_from_fee("task2", Decimal("100.00"))
        assert empty_fund.balance == Decimal("2.00")  # 1% of $200 total

    def test_contribute_from_fee_very_small(self, empty_fund):
        """Test very small fee contribution."""
        contrib = empty_fund.contribute_from_fee("task_tiny", Decimal("0.10"))
        # 1% of $0.10 = $0.001, rounded
        assert contrib.amount == Decimal("0.0010")

    def test_contribute_from_slash(self, fund):
        """Test contribution from slashed bond."""
        initial_balance = fund.balance
        contrib = fund.contribute_from_slash(
            amount=Decimal("25.00"),
            reason="Unfair rejection",
            task_id="task456",
            agent_id="agent789",
        )

        assert contrib.amount == Decimal("25.00")
        assert contrib.source == ContributionSource.SLASHED_BOND
        assert fund.balance == initial_balance + Decimal("25.00")

    def test_contribute_manual(self, fund):
        """Test manual treasury contribution."""
        initial_balance = fund.balance
        contrib = fund.contribute_manual(
            amount=Decimal("500.00"),
            description="Q1 top-up",
            contributor_id="treasury_admin",
        )

        assert contrib.amount == Decimal("500.00")
        assert contrib.source == ContributionSource.MANUAL_DEPOSIT
        assert fund.balance == initial_balance + Decimal("500.00")


# =============================================================================
# Claim Submission Tests (NOW-101)
# =============================================================================


class TestClaimSubmission:
    """Tests for claim submission."""

    @pytest.mark.asyncio
    async def test_submit_claim_basic(self, fund):
        """Test basic claim submission."""
        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.AGENT_DISAPPEARED,
            amount=Decimal("30.00"),
            reason="Agent stopped responding",
            evidence={"task_id": "task456"},
        )

        assert claim.status == ClaimStatus.PENDING
        assert claim.amount_requested == Decimal("30.00")
        assert claim.worker_id == "worker123"
        assert claim.claim_type == ClaimType.AGENT_DISAPPEARED

    @pytest.mark.asyncio
    async def test_submit_claim_max_amount(self, fund):
        """Test claim at maximum amount ($50)."""
        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.PAYMENT_FAILURE,
            amount=Decimal("50.00"),
            reason="Payment system failure",
            evidence={},
        )

        assert claim.amount_requested == Decimal("50.00")
        assert claim.status == ClaimStatus.PENDING

    @pytest.mark.asyncio
    async def test_submit_claim_exceeds_max_per_claim(self, fund):
        """Test claim exceeding $50 max is rejected."""
        with pytest.raises(FundError) as exc_info:
            await fund.submit_claim(
                worker_id="worker123",
                claim_type=ClaimType.AGENT_DISAPPEARED,
                amount=Decimal("51.00"),
                reason="Test",
                evidence={},
            )

        assert "exceeds maximum" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_submit_claim_below_minimum(self, fund):
        """Test claim below minimum is rejected."""
        with pytest.raises(FundError) as exc_info:
            await fund.submit_claim(
                worker_id="worker123",
                claim_type=ClaimType.AGENT_DISAPPEARED,
                amount=Decimal("0.25"),
                reason="Test",
                evidence={},
            )

        assert "below minimum" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_monthly_limit_enforcement(self, fund):
        """Test $200/month limit per worker."""
        # Submit 4 claims of $50 = $200 (at the limit)
        for i in range(4):
            claim = await fund.submit_claim(
                worker_id="worker_monthly",
                claim_type=ClaimType.PAYMENT_FAILURE,
                amount=Decimal("50.00"),
                reason=f"Claim {i + 1}",
                evidence={},
            )
            # Approve and pay each claim
            await fund.approve_claim(
                claim.id,
                "admin",
                Decimal("50.00"),
            )

        # 5th claim should fail (would exceed $200)
        with pytest.raises(ClaimLimitExceededError) as exc_info:
            await fund.submit_claim(
                worker_id="worker_monthly",
                claim_type=ClaimType.PAYMENT_FAILURE,
                amount=Decimal("50.00"),
                reason="Claim 5",
                evidence={},
            )

        assert "monthly limit" in str(exc_info.value).lower()


# =============================================================================
# Claim Review Tests
# =============================================================================


class TestClaimReview:
    """Tests for claim approval and rejection."""

    @pytest.mark.asyncio
    async def test_approve_claim_full_amount(self, fund):
        """Test approving claim for full requested amount."""
        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.AGENT_DISAPPEARED,
            amount=Decimal("30.00"),
            reason="Test claim",
            evidence={},
        )

        approved = await fund.approve_claim(
            claim.id,
            reviewer_id="admin456",
            amount=Decimal("30.00"),
        )

        assert approved.status == ClaimStatus.PAID  # Auto-pays
        assert approved.amount_approved == Decimal("30.00")
        assert approved.reviewer_id == "admin456"
        assert approved.tx_hash is not None

    @pytest.mark.asyncio
    async def test_approve_claim_partial_amount(self, fund):
        """Test approving claim for less than requested."""
        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.UNJUST_REJECTION,
            amount=Decimal("50.00"),
            reason="Test",
            evidence={},
        )

        approved = await fund.approve_claim(
            claim.id,
            reviewer_id="admin",
            amount=Decimal("25.00"),  # Half of requested
            notes="Partial approval due to limited evidence",
        )

        assert approved.amount_approved == Decimal("25.00")
        assert approved.reviewer_notes == "Partial approval due to limited evidence"

    @pytest.mark.asyncio
    async def test_approve_claim_updates_balance(self, fund):
        """Test that approving claim deducts from balance."""
        initial_balance = fund.balance

        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.PAYMENT_FAILURE,
            amount=Decimal("40.00"),
            reason="Test",
            evidence={},
        )

        await fund.approve_claim(claim.id, "admin", Decimal("40.00"))

        assert fund.balance == initial_balance - Decimal("40.00")

    @pytest.mark.asyncio
    async def test_reject_claim(self, fund):
        """Test rejecting a claim."""
        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.EMERGENCY_HARDSHIP,
            amount=Decimal("50.00"),
            reason="Emergency",
            evidence={},
        )

        rejected = await fund.reject_claim(
            claim.id,
            reviewer_id="admin",
            reason="Insufficient evidence",
        )

        assert rejected.status == ClaimStatus.REJECTED
        assert rejected.reviewer_notes == "Insufficient evidence"

    @pytest.mark.asyncio
    async def test_cannot_approve_rejected_claim(self, fund):
        """Test that rejected claims cannot be approved."""
        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.PAYMENT_FAILURE,
            amount=Decimal("20.00"),
            reason="Test",
            evidence={},
        )

        await fund.reject_claim(claim.id, "admin", "No evidence")

        with pytest.raises(InvalidClaimStateError):
            await fund.approve_claim(claim.id, "admin2", Decimal("20.00"))

    @pytest.mark.asyncio
    async def test_cannot_approve_more_than_requested(self, fund):
        """Test that approval cannot exceed requested amount."""
        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.AGENT_DISAPPEARED,
            amount=Decimal("30.00"),
            reason="Test",
            evidence={},
        )

        with pytest.raises(FundError) as exc_info:
            await fund.approve_claim(claim.id, "admin", Decimal("35.00"))

        assert "exceeds requested" in str(exc_info.value)


# =============================================================================
# Insufficient Funds Tests
# =============================================================================


class TestInsufficientFunds:
    """Tests for handling insufficient fund balance."""

    @pytest.mark.asyncio
    async def test_approve_with_insufficient_balance(self, empty_fund):
        """Test that approving when balance is insufficient raises error."""
        # Add minimal balance
        empty_fund.contribute_manual(
            Decimal("10.00"),
            "Small top-up",
            "admin",
        )

        claim = await empty_fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.PAYMENT_FAILURE,
            amount=Decimal("50.00"),
            reason="Test",
            evidence={},
        )

        with pytest.raises(InsufficientFundsError) as exc_info:
            await empty_fund.approve_claim(claim.id, "admin", Decimal("50.00"))

        assert "insufficient" in str(exc_info.value).lower()


# =============================================================================
# Worker Eligibility Tests
# =============================================================================


class TestWorkerEligibility:
    """Tests for worker eligibility checking."""

    def test_check_eligibility_new_worker(self, fund):
        """Test eligibility for new worker."""
        eligible, message = fund.check_worker_eligibility(
            "new_worker",
            Decimal("50.00"),
        )

        assert eligible is True
        assert "Eligible" in message

    def test_check_eligibility_exceeds_per_claim(self, fund):
        """Test eligibility when amount exceeds per-claim limit."""
        eligible, message = fund.check_worker_eligibility(
            "worker",
            Decimal("100.00"),  # Exceeds $50 limit
        )

        assert eligible is False
        assert "per-claim limit" in message

    @pytest.mark.asyncio
    async def test_check_eligibility_at_monthly_limit(self, fund):
        """Test eligibility when at monthly limit."""
        # Pay worker up to $200 limit
        for i in range(4):
            claim = await fund.submit_claim(
                worker_id="heavy_user",
                claim_type=ClaimType.PAYMENT_FAILURE,
                amount=Decimal("50.00"),
                reason=f"Claim {i + 1}",
                evidence={},
            )
            await fund.approve_claim(claim.id, "admin", Decimal("50.00"))

        # Check eligibility for more
        eligible, message = fund.check_worker_eligibility(
            "heavy_user",
            Decimal("10.00"),
        )

        assert eligible is False
        assert "monthly limit" in message.lower()


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for fund statistics."""

    @pytest.mark.asyncio
    async def test_get_fund_stats_basic(self, fund):
        """Test basic statistics."""
        # Add some activity
        fund.contribute_from_fee("task1", Decimal("100.00"))
        fund.contribute_from_slash(
            Decimal("20.00"),
            "Test slash",
        )

        claim = await fund.submit_claim(
            worker_id="worker1",
            claim_type=ClaimType.AGENT_DISAPPEARED,
            amount=Decimal("25.00"),
            reason="Test",
            evidence={},
        )
        await fund.approve_claim(claim.id, "admin", Decimal("25.00"))

        stats = fund.get_fund_stats()

        assert "balance" in stats
        assert stats["contributions"]["from_fees"] > 0
        assert stats["contributions"]["from_slashes"] == 20.0
        assert stats["claims"]["paid_count"] == 1
        assert stats["claims"]["total_paid"] == 25.0

    def test_get_pending_claims(self, fund):
        """Test getting pending claims."""
        initial_pending = fund.get_pending_claims()
        assert len(initial_pending) == 0

    @pytest.mark.asyncio
    async def test_get_worker_claims(self, fund):
        """Test getting claims for a specific worker."""
        # Submit 3 claims for same worker
        for i in range(3):
            await fund.submit_claim(
                worker_id="multi_claimer",
                claim_type=ClaimType.PAYMENT_FAILURE,
                amount=Decimal("10.00"),
                reason=f"Claim {i + 1}",
                evidence={},
            )

        claims = fund.get_worker_claims("multi_claimer")
        assert len(claims) == 3


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Tests for module-level singleton."""

    def test_get_fund_returns_singleton(self):
        """Test that get_fund returns same instance."""
        reset_fund()  # Clear any existing

        fund1 = get_fund()
        fund2 = get_fund()

        assert fund1 is fund2

    def test_reset_fund_clears_singleton(self):
        """Test that reset_fund creates new instance."""
        fund1 = get_fund()
        reset_fund()
        fund2 = get_fund()

        assert fund1 is not fund2


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_claim_with_all_evidence_types(self, fund):
        """Test claim with comprehensive evidence."""
        claim = await fund.submit_claim(
            worker_id="worker123",
            claim_type=ClaimType.UNJUST_REJECTION,
            amount=Decimal("45.00"),
            reason="Complete documentation provided",
            evidence={
                "task_id": "task789",
                "screenshots": ["url1", "url2"],
                "chat_logs": ["log1", "log2"],
                "timestamps": {
                    "submitted": "2026-01-20T10:00:00Z",
                    "rejected": "2026-01-21T10:00:00Z",
                },
                "arbitration_result": "worker_wins",
            },
            task_id="task789",
        )

        assert claim.evidence["arbitration_result"] == "worker_wins"
        assert claim.task_id == "task789"

    @pytest.mark.asyncio
    async def test_claim_not_found(self, fund):
        """Test accessing non-existent claim."""
        result = fund.get_claim("nonexistent_claim_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_approve_nonexistent_claim(self, fund):
        """Test approving non-existent claim raises error."""
        with pytest.raises(ClaimNotFoundError):
            await fund.approve_claim(
                "nonexistent",
                "admin",
                Decimal("10.00"),
            )

    def test_custom_config(self, custom_config):
        """Test fund with custom configuration."""
        fund = ProtectionFund(config=custom_config)

        # Test higher contribution rate (2% instead of default 1%)
        contrib = fund.contribute_from_fee("task1", Decimal("100.00"))
        assert contrib.amount == Decimal("2.00")  # 2% of $100

    @pytest.mark.asyncio
    async def test_all_claim_types(self, fund):
        """Test all claim types can be submitted."""
        claim_types = [
            ClaimType.AGENT_DISAPPEARED,
            ClaimType.PAYMENT_FAILURE,
            ClaimType.UNJUST_REJECTION,
            ClaimType.EMERGENCY_HARDSHIP,
        ]

        for i, claim_type in enumerate(claim_types):
            claim = await fund.submit_claim(
                worker_id=f"worker_{i}",
                claim_type=claim_type,
                amount=Decimal("10.00"),
                reason=f"Testing {claim_type.value}",
                evidence={},
            )
            assert claim.claim_type == claim_type
