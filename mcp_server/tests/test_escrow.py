"""
Tests for x402 Escrow Integration Module (NOW-021 to NOW-023)

Tests the EscrowManager class and related functionality for:
- Deposit operations (escrow creation)
- Release operations (full and partial)
- Refund operations (cancellation)
- Dispute handling and resolution
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from ..integrations.x402.escrow import (
    EscrowManager,
    EscrowStatus,
    PaymentToken,
    TaskEscrow,
    FeeBreakdown,
    ReleaseRecord,
    EscrowStateError,
    PLATFORM_FEE_PERCENT,
    MINIMUM_PAYOUT,
    PARTIAL_RELEASE_PERCENT,
)
from ..integrations.x402.client import (
    X402Client,
    X402Error,
    PaymentResult as ClientPaymentResult,
    EscrowDeposit as ClientEscrowDeposit,
    EscrowInfo,
    EscrowStatus as ClientEscrowStatus,
    PaymentToken as ClientPaymentToken,
    InsufficientFundsError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_x402_client():
    """Create a mock X402Client for testing."""
    client = MagicMock(spec=X402Client)
    client.default_token = ClientPaymentToken.USDC
    return client


@pytest.fixture
def escrow_manager(mock_x402_client):
    """Create an EscrowManager with mocked X402Client."""
    return EscrowManager(
        x402_client=mock_x402_client,
        treasury_address="0xTREASURY1234567890123456789012345678901234",
    )


@pytest.fixture
def sample_agent_wallet():
    """Sample agent wallet address."""
    return "0xAGENT123456789012345678901234567890123456"


@pytest.fixture
def sample_worker_wallet():
    """Sample worker wallet address."""
    return "0xWORKER12345678901234567890123456789012345"


@pytest.fixture
def sample_task_id():
    """Sample task ID."""
    return f"task-{uuid.uuid4().hex[:8]}"


# =============================================================================
# Deposit Tests
# =============================================================================

class TestDepositCreatesEscrow:
    """Test that deposit operations create escrow records correctly."""

    @pytest.mark.asyncio
    async def test_deposit_creates_escrow(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Deposit creates escrow record with correct initial state."""
        # Setup mock response
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc12345",
                task_id=sample_task_id,
                amount=Decimal("10.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xTX123456789",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
                status=ClientEscrowStatus.ACTIVE,
                network="base",
            )
        )

        # Execute
        escrow = await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("10.00"),
            agent_wallet=sample_agent_wallet,
        )

        # Verify
        assert escrow is not None
        assert escrow.task_id == sample_task_id
        assert escrow.total_amount == Decimal("10.00")
        assert escrow.status == EscrowStatus.DEPOSITED
        assert escrow.depositor_wallet == sample_agent_wallet
        assert escrow.released_amount == Decimal("0")
        assert escrow.remaining_amount == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_deposit_stores_in_cache(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Deposit stores escrow in internal cache for retrieval."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("10.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xTX123",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("10.00"),
            agent_wallet=sample_agent_wallet,
        )

        # Verify retrieval
        retrieved = escrow_manager.get_escrow(sample_task_id)
        assert retrieved is not None
        assert retrieved.task_id == sample_task_id

    @pytest.mark.asyncio
    async def test_deposit_prevents_duplicate(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Cannot create duplicate escrow for same task."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("10.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xTX123",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        # First deposit succeeds
        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("10.00"),
            agent_wallet=sample_agent_wallet,
        )

        # Second deposit should fail
        with pytest.raises(EscrowStateError, match="already exists"):
            await escrow_manager.deposit_for_task(
                task_id=sample_task_id,
                bounty_usd=Decimal("10.00"),
                agent_wallet=sample_agent_wallet,
            )


class TestDepositRequiresValidAmount:
    """Test that deposit validates minimum bounty amount."""

    @pytest.mark.asyncio
    async def test_deposit_requires_minimum_bounty(
        self, escrow_manager, sample_task_id, sample_agent_wallet
    ):
        """Deposit fails if net payout would be below minimum."""
        # Bounty too small: $0.50 * 0.92 (after 8% fee) = $0.46 < MINIMUM_PAYOUT
        with pytest.raises(X402Error, match="below minimum"):
            await escrow_manager.deposit_for_task(
                task_id=sample_task_id,
                bounty_usd=Decimal("0.50"),
                agent_wallet=sample_agent_wallet,
            )

    @pytest.mark.asyncio
    async def test_deposit_accepts_minimum_valid_bounty(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Deposit accepts bounty that results in exactly minimum payout."""
        # Minimum bounty = 0.50 / 0.92 = ~0.5435, rounded up to 0.55
        min_bounty = Decimal("0.55")

        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=min_bounty,
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xTX123",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        escrow = await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=min_bounty,
            agent_wallet=sample_agent_wallet,
        )

        assert escrow.fees.net_to_worker >= MINIMUM_PAYOUT


class TestDepositCalculatesFees:
    """Test that deposit calculates fee breakdown correctly."""

    def test_calculate_fees_8_percent(self, escrow_manager):
        """Fee breakdown correctly applies 8% platform fee."""
        fees = escrow_manager.calculate_fees(Decimal("100.00"))

        assert fees.gross_amount == Decimal("100.00")
        assert fees.platform_fee == Decimal("8.00")
        assert fees.net_to_worker == Decimal("92.00")
        assert fees.fee_percent == Decimal("8")  # 8%

    def test_calculate_fees_rounds_to_cents(self, escrow_manager):
        """Fee amounts are rounded to 2 decimal places."""
        fees = escrow_manager.calculate_fees(Decimal("15.50"))

        # 15.50 * 0.08 = 1.24
        assert fees.platform_fee == Decimal("1.24")
        assert fees.net_to_worker == Decimal("14.26")

    def test_calculate_fees_small_amount(self, escrow_manager):
        """Fee calculation works for small amounts."""
        fees = escrow_manager.calculate_fees(Decimal("5.00"))

        # 5.00 * 0.08 = 0.40
        assert fees.platform_fee == Decimal("0.40")
        assert fees.net_to_worker == Decimal("4.60")

    @pytest.mark.asyncio
    async def test_deposit_stores_fee_breakdown(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Deposit stores fee breakdown in escrow record."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xTX123",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        escrow = await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        assert escrow.fees is not None
        assert escrow.fees.gross_amount == Decimal("100.00")
        assert escrow.fees.platform_fee == Decimal("8.00")
        assert escrow.fees.net_to_worker == Decimal("92.00")


class TestDepositWithInsufficientBalance:
    """Test deposit behavior when client has insufficient balance."""

    @pytest.mark.asyncio
    async def test_deposit_raises_on_insufficient_balance(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Deposit raises InsufficientFundsError when balance is too low."""
        mock_x402_client.create_escrow = AsyncMock(
            side_effect=InsufficientFundsError(
                required=Decimal("100.00"),
                available=Decimal("50.00"),
                token=ClientPaymentToken.USDC,
            )
        )

        with pytest.raises(InsufficientFundsError) as exc_info:
            await escrow_manager.deposit_for_task(
                task_id=sample_task_id,
                bounty_usd=Decimal("100.00"),
                agent_wallet=sample_agent_wallet,
            )

        assert "Insufficient" in str(exc_info.value)
        assert exc_info.value.details["required"] == "100.00"
        assert exc_info.value.details["available"] == "50.00"

    @pytest.mark.asyncio
    async def test_deposit_marks_failed_on_error(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Escrow status is FAILED when deposit transaction fails."""
        mock_x402_client.create_escrow = AsyncMock(
            side_effect=X402Error("Transaction reverted")
        )

        with pytest.raises(X402Error):
            await escrow_manager.deposit_for_task(
                task_id=sample_task_id,
                bounty_usd=Decimal("100.00"),
                agent_wallet=sample_agent_wallet,
            )

        # Escrow should be cached with FAILED status
        escrow = escrow_manager.get_escrow(sample_task_id)
        assert escrow is not None
        assert escrow.status == EscrowStatus.FAILED


# =============================================================================
# Release Tests
# =============================================================================

class TestReleaseFullAmount:
    """Test full release of escrow to worker."""

    @pytest.mark.asyncio
    async def test_release_full_amount(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Release full amount to worker on approval."""
        # Setup: Create escrow first
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        # Setup release mock
        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xRELEASE123",
                amount=Decimal("92.00"),
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        # Execute release
        tx_hash = await escrow_manager.release_on_approval(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        # Verify
        assert tx_hash == "0xRELEASE123"

        escrow = escrow_manager.get_escrow(sample_task_id)
        assert escrow.status == EscrowStatus.RELEASED
        assert escrow.beneficiary_wallet == sample_worker_wallet


class TestReleaseWithPlatformFee:
    """Test that release deducts platform fee correctly."""

    @pytest.mark.asyncio
    async def test_release_deducts_8_percent_fee(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Release deducts 8% platform fee and sends to treasury."""
        # Setup escrow
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        # Track release calls
        release_calls = []

        async def capture_release(*args, **kwargs):
            release_calls.append(kwargs)
            return ClientPaymentResult(
                success=True,
                tx_hash=f"0xRELEASE{len(release_calls)}",
                amount=kwargs.get("amount", Decimal("0")),
                token=ClientPaymentToken.USDC,
                recipient=kwargs.get("recipient", ""),
                timestamp=datetime.now(timezone.utc),
            )

        mock_x402_client.release_escrow = AsyncMock(side_effect=capture_release)

        # Execute release
        await escrow_manager.release_on_approval(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        # Verify calls
        # First call: worker payment ($92)
        # Second call: fee to treasury ($8)
        assert len(release_calls) == 2

        worker_call = release_calls[0]
        assert worker_call["recipient"] == sample_worker_wallet
        assert worker_call["amount"] == Decimal("92.00")

        fee_call = release_calls[1]
        assert fee_call["recipient"] == escrow_manager.treasury_address
        assert fee_call["amount"] == Decimal("8.00")


class TestReleaseRequiresValidStatus:
    """Test that release only works from valid states."""

    @pytest.mark.asyncio
    async def test_release_from_deposited_succeeds(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Release succeeds when escrow is in DEPOSITED status."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xRELEASE",
                amount=Decimal("92.00"),
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        # Should succeed
        tx_hash = await escrow_manager.release_on_approval(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )
        assert tx_hash is not None

    @pytest.mark.asyncio
    async def test_release_from_refunded_fails(
        self, escrow_manager, sample_task_id, sample_worker_wallet
    ):
        """Release fails when escrow is already REFUNDED."""
        # Manually create an escrow in REFUNDED state
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.REFUNDED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(EscrowStateError, match="Cannot release"):
            await escrow_manager.release_on_approval(
                task_id=sample_task_id,
                worker_wallet=sample_worker_wallet,
            )

    @pytest.mark.asyncio
    async def test_release_from_released_fails(
        self, escrow_manager, sample_task_id, sample_worker_wallet
    ):
        """Release fails when escrow is already RELEASED."""
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("100.00"),
            status=EscrowStatus.RELEASED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet="0xWORKER",
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(EscrowStateError, match="Cannot release"):
            await escrow_manager.release_on_approval(
                task_id=sample_task_id,
                worker_wallet=sample_worker_wallet,
            )


class TestReleaseUpdatesStatus:
    """Test that release updates escrow status correctly."""

    @pytest.mark.asyncio
    async def test_full_release_sets_released_status(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Full release changes status to RELEASED."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xRELEASE",
                amount=Decimal("92.00"),
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        await escrow_manager.release_on_approval(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        escrow = escrow_manager.get_escrow(sample_task_id)
        assert escrow.status == EscrowStatus.RELEASED

    @pytest.mark.asyncio
    async def test_release_records_transaction(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Release records transaction in release_txs list."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xWORKER_RELEASE",
                amount=Decimal("92.00"),
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        await escrow_manager.release_on_approval(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        escrow = escrow_manager.get_escrow(sample_task_id)
        assert len(escrow.release_txs) >= 1

        worker_release = next(
            (r for r in escrow.release_txs if r.release_type == "final"),
            None
        )
        assert worker_release is not None
        assert worker_release.tx_hash == "0xWORKER_RELEASE"
        assert worker_release.amount == Decimal("92.00")
        assert worker_release.recipient == sample_worker_wallet


# =============================================================================
# Partial Release Tests
# =============================================================================

class TestPartialReleaseOnSubmission:
    """Test partial release (30%) on worker submission."""

    @pytest.mark.asyncio
    async def test_partial_release_30_percent(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Partial release sends 30% of net amount to worker."""
        # Setup escrow
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        # Setup partial release mock
        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xPARTIAL",
                amount=Decimal("27.60"),  # 30% of $92 = $27.60
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        escrow = await escrow_manager.release_partial_on_submission(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        # Verify 30% of net ($92) = $27.60
        assert escrow.released_amount == Decimal("27.60")
        assert escrow.status == EscrowStatus.PARTIAL_RELEASED


class TestPartialReleaseTracking:
    """Test tracking of partial releases."""

    @pytest.mark.asyncio
    async def test_partial_release_tracks_amount(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Partial release updates released_amount correctly."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xPARTIAL",
                amount=Decimal("27.60"),
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        escrow = await escrow_manager.release_partial_on_submission(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        # Verify tracking
        assert escrow.released_amount == Decimal("27.60")
        assert escrow.remaining_amount == Decimal("100.00") - Decimal("27.60")

        # Verify release record
        partial_release = next(
            (r for r in escrow.release_txs if r.release_type == "partial"),
            None
        )
        assert partial_release is not None
        assert partial_release.amount == Decimal("27.60")

    @pytest.mark.asyncio
    async def test_partial_release_sets_beneficiary(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Partial release sets beneficiary wallet."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xPARTIAL",
                amount=Decimal("27.60"),
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        escrow = await escrow_manager.release_partial_on_submission(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        assert escrow.beneficiary_wallet == sample_worker_wallet


class TestFinalReleaseAfterPartial:
    """Test final release after partial release."""

    @pytest.mark.asyncio
    async def test_final_release_completes_remaining_70(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Final release after partial sends remaining 70%."""
        # Setup escrow
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        # Execute partial release first
        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xPARTIAL",
                amount=Decimal("27.60"),  # 30% of $92
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        await escrow_manager.release_partial_on_submission(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        # Track final release calls
        release_calls = []

        async def capture_release(*args, **kwargs):
            release_calls.append(kwargs)
            return ClientPaymentResult(
                success=True,
                tx_hash=f"0xFINAL{len(release_calls)}",
                amount=kwargs.get("amount", Decimal("0")),
                token=ClientPaymentToken.USDC,
                recipient=kwargs.get("recipient", ""),
                timestamp=datetime.now(timezone.utc),
            )

        mock_x402_client.release_escrow = AsyncMock(side_effect=capture_release)

        # Execute final release
        await escrow_manager.release_on_approval(
            task_id=sample_task_id,
            worker_wallet=sample_worker_wallet,
        )

        # First call should be remaining worker payment
        # $92 total - $27.60 already released = $64.40
        worker_call = release_calls[0]
        assert worker_call["recipient"] == sample_worker_wallet
        assert worker_call["amount"] == Decimal("64.40")

        # Second call should be fee to treasury
        fee_call = release_calls[1]
        assert fee_call["recipient"] == escrow_manager.treasury_address
        assert fee_call["amount"] == Decimal("8.00")


# =============================================================================
# Refund Tests
# =============================================================================

class TestRefundOnCancel:
    """Test refund when task is cancelled."""

    @pytest.mark.asyncio
    async def test_refund_returns_full_amount(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Refund returns full amount to agent."""
        # Setup escrow
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        # Setup refund mock
        mock_x402_client.refund_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xREFUND123",
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                recipient=sample_agent_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        tx_hash = await escrow_manager.refund_on_cancel(
            task_id=sample_task_id,
            reason="Task cancelled by agent",
        )

        assert tx_hash == "0xREFUND123"

        escrow = escrow_manager.get_escrow(sample_task_id)
        assert escrow.status == EscrowStatus.REFUNDED
        assert escrow.refund_tx == "0xREFUND123"


class TestRefundRequiresDepositedStatus:
    """Test that refund only works from DEPOSITED status."""

    @pytest.mark.asyncio
    async def test_refund_from_deposited_succeeds(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Refund succeeds when escrow is in DEPOSITED status."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        mock_x402_client.refund_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xREFUND",
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                recipient=sample_agent_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        tx_hash = await escrow_manager.refund_on_cancel(
            task_id=sample_task_id,
            reason="Cancelled",
        )

        assert tx_hash == "0xREFUND"

    @pytest.mark.asyncio
    async def test_refund_from_released_fails(self, escrow_manager, sample_task_id):
        """Refund fails when escrow is already RELEASED."""
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("100.00"),
            status=EscrowStatus.RELEASED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet="0xWORKER",
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(EscrowStateError, match="Cannot refund"):
            await escrow_manager.refund_on_cancel(
                task_id=sample_task_id,
                reason="Too late",
            )


class TestRefundBlockedIfPartialReleased:
    """Test that full refund is blocked after partial release."""

    @pytest.mark.asyncio
    async def test_full_refund_blocked_after_partial(
        self, escrow_manager, sample_task_id
    ):
        """Cannot fully refund after partial release has been made."""
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("27.60"),  # 30% released
            status=EscrowStatus.PARTIAL_RELEASED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet="0xWORKER",
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(EscrowStateError, match="Cannot refund"):
            await escrow_manager.refund_on_cancel(
                task_id=sample_task_id,
                reason="Trying to refund after partial",
            )

    @pytest.mark.asyncio
    async def test_refund_blocked_with_any_released_amount(
        self, escrow_manager, mock_x402_client, sample_task_id,
        sample_agent_wallet, sample_worker_wallet
    ):
        """Cannot refund if any amount has been released."""
        # Create escrow in DEPOSITED state but with some released amount
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("10.00"),  # Some released
            status=EscrowStatus.DEPOSITED,  # Still shows deposited
            token=PaymentToken.USDC,
            depositor_wallet=sample_agent_wallet,
            beneficiary_wallet=sample_worker_wallet,
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(EscrowStateError, match="already released"):
            await escrow_manager.refund_on_cancel(
                task_id=sample_task_id,
                reason="Cannot refund",
            )


# =============================================================================
# Dispute Tests
# =============================================================================

class TestDisputeLocksEscrow:
    """Test that dispute locks escrow."""

    @pytest.mark.asyncio
    async def test_dispute_changes_status_to_disputed(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_agent_wallet
    ):
        """Dispute changes escrow status to DISPUTED."""
        mock_x402_client.create_escrow = AsyncMock(
            return_value=ClientEscrowDeposit(
                escrow_id=f"escrow_{sample_task_id}_abc",
                task_id=sample_task_id,
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                depositor=sample_agent_wallet,
                beneficiary=sample_agent_wallet,
                tx_hash="0xDEPOSIT",
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
        )

        await escrow_manager.deposit_for_task(
            task_id=sample_task_id,
            bounty_usd=Decimal("100.00"),
            agent_wallet=sample_agent_wallet,
        )

        await escrow_manager.handle_dispute(
            task_id=sample_task_id,
            dispute_reason="Worker claims work was done",
        )

        escrow = escrow_manager.get_escrow(sample_task_id)
        assert escrow.status == EscrowStatus.DISPUTED
        assert escrow.dispute_reason == "Worker claims work was done"

    @pytest.mark.asyncio
    async def test_dispute_blocks_release(
        self, escrow_manager, sample_task_id, sample_worker_wallet
    ):
        """Cannot release escrow while disputed."""
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.DISPUTED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(EscrowStateError, match="Cannot release"):
            await escrow_manager.release_on_approval(
                task_id=sample_task_id,
                worker_wallet=sample_worker_wallet,
            )

    @pytest.mark.asyncio
    async def test_dispute_blocks_refund(self, escrow_manager, sample_task_id):
        """Cannot refund escrow while disputed."""
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.DISPUTED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(EscrowStateError, match="Cannot refund"):
            await escrow_manager.refund_on_cancel(
                task_id=sample_task_id,
                reason="Trying to refund during dispute",
            )


class TestResolveDisputeWorkerWins:
    """Test dispute resolution in favor of worker."""

    @pytest.mark.asyncio
    async def test_worker_wins_gets_payment(
        self, escrow_manager, mock_x402_client, sample_task_id, sample_worker_wallet
    ):
        """When worker wins dispute, they receive payment."""
        # Setup disputed escrow
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.DISPUTED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
            fees=FeeBreakdown(
                gross_amount=Decimal("100.00"),
                platform_fee=Decimal("8.00"),
                net_to_worker=Decimal("92.00"),
                fee_percent=Decimal("8"),
            ),
        )

        mock_x402_client.release_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xWORKER_WINS",
                amount=Decimal("92.00"),
                token=ClientPaymentToken.USDC,
                recipient=sample_worker_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        tx_hash = await escrow_manager.resolve_dispute(
            task_id=sample_task_id,
            winner="worker",
            worker_wallet=sample_worker_wallet,
        )

        assert tx_hash == "0xWORKER_WINS"

        escrow = escrow_manager.get_escrow(sample_task_id)
        assert escrow.status == EscrowStatus.RELEASED


class TestResolveDisputeAgentWins:
    """Test dispute resolution in favor of agent."""

    @pytest.mark.asyncio
    async def test_agent_wins_gets_refund(
        self, escrow_manager, mock_x402_client, sample_task_id
    ):
        """When agent wins dispute, they receive refund."""
        agent_wallet = "0xAGENT123456789012345678901234567890123456"

        # Setup disputed escrow
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.DISPUTED,
            token=PaymentToken.USDC,
            depositor_wallet=agent_wallet,
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
        )

        mock_x402_client.refund_escrow = AsyncMock(
            return_value=ClientPaymentResult(
                success=True,
                tx_hash="0xAGENT_WINS",
                amount=Decimal("100.00"),
                token=ClientPaymentToken.USDC,
                recipient=agent_wallet,
                timestamp=datetime.now(timezone.utc),
            )
        )

        tx_hash = await escrow_manager.resolve_dispute(
            task_id=sample_task_id,
            winner="agent",
        )

        assert tx_hash == "0xAGENT_WINS"

        escrow = escrow_manager.get_escrow(sample_task_id)
        assert escrow.status == EscrowStatus.REFUNDED

    @pytest.mark.asyncio
    async def test_resolve_requires_disputed_status(
        self, escrow_manager, sample_task_id, sample_worker_wallet
    ):
        """Cannot resolve dispute if escrow is not disputed."""
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.DEPOSITED,  # Not disputed
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(EscrowStateError, match="Cannot resolve"):
            await escrow_manager.resolve_dispute(
                task_id=sample_task_id,
                winner="worker",
                worker_wallet=sample_worker_wallet,
            )

    @pytest.mark.asyncio
    async def test_resolve_invalid_winner_raises(
        self, escrow_manager, sample_task_id
    ):
        """Invalid winner value raises ValueError."""
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.DISPUTED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
        )

        with pytest.raises(ValueError, match="Invalid winner"):
            await escrow_manager.resolve_dispute(
                task_id=sample_task_id,
                winner="nobody",  # Invalid
            )


# =============================================================================
# Edge Cases and Utilities
# =============================================================================

class TestEscrowRetrieval:
    """Test escrow retrieval methods."""

    def test_get_escrow_returns_none_for_missing(self, escrow_manager):
        """get_escrow returns None for non-existent task."""
        result = escrow_manager.get_escrow("nonexistent-task")
        assert result is None

    def test_get_escrow_status_raises_for_missing(self, escrow_manager):
        """get_escrow_status raises error for non-existent task."""
        with pytest.raises(EscrowStateError, match="No escrow found"):
            escrow_manager.get_escrow_status("nonexistent-task")

    def test_get_escrow_status_returns_dict(self, escrow_manager, sample_task_id):
        """get_escrow_status returns serialized dict."""
        escrow_manager._escrows[sample_task_id] = TaskEscrow(
            task_id=sample_task_id,
            escrow_id="escrow_123",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.DEPOSITED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
        )

        status = escrow_manager.get_escrow_status(sample_task_id)

        assert isinstance(status, dict)
        assert status["task_id"] == sample_task_id
        assert status["total_amount"] == 100.0
        assert status["status"] == "deposited"


class TestTaskEscrowProperties:
    """Test TaskEscrow dataclass properties."""

    def test_remaining_amount_calculation(self):
        """remaining_amount correctly calculates unreleased funds."""
        escrow = TaskEscrow(
            task_id="task-123",
            escrow_id="escrow-456",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("30.00"),
            status=EscrowStatus.PARTIAL_RELEASED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet="0xWORKER",
            deposit_tx="0xDEPOSIT",
        )

        assert escrow.remaining_amount == Decimal("70.00")

    def test_is_active_for_deposited(self):
        """is_active returns True for DEPOSITED status."""
        escrow = TaskEscrow(
            task_id="task-123",
            escrow_id="escrow-456",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("0"),
            status=EscrowStatus.DEPOSITED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet=None,
            deposit_tx="0xDEPOSIT",
        )

        assert escrow.is_active is True

    def test_is_active_for_released(self):
        """is_active returns False for RELEASED status."""
        escrow = TaskEscrow(
            task_id="task-123",
            escrow_id="escrow-456",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("100.00"),
            status=EscrowStatus.RELEASED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet="0xWORKER",
            deposit_tx="0xDEPOSIT",
        )

        assert escrow.is_active is False

    def test_to_dict_serialization(self):
        """to_dict correctly serializes escrow."""
        escrow = TaskEscrow(
            task_id="task-123",
            escrow_id="escrow-456",
            total_amount=Decimal("100.00"),
            released_amount=Decimal("27.60"),
            status=EscrowStatus.PARTIAL_RELEASED,
            token=PaymentToken.USDC,
            depositor_wallet="0xAGENT",
            beneficiary_wallet="0xWORKER",
            deposit_tx="0xDEPOSIT",
            fees=FeeBreakdown(
                gross_amount=Decimal("100.00"),
                platform_fee=Decimal("8.00"),
                net_to_worker=Decimal("92.00"),
                fee_percent=Decimal("8"),
            ),
        )

        result = escrow.to_dict()

        assert result["task_id"] == "task-123"
        assert result["total_amount"] == 100.0
        assert result["released_amount"] == 27.6
        assert result["remaining_amount"] == 72.4
        assert result["status"] == "partial_released"
        assert result["token"] == "USDC"
        assert result["fees"]["platform_fee"] == 8.0


class TestFeeBreakdownSerialization:
    """Test FeeBreakdown serialization."""

    def test_to_dict(self):
        """FeeBreakdown.to_dict() correctly serializes."""
        fees = FeeBreakdown(
            gross_amount=Decimal("100.00"),
            platform_fee=Decimal("8.00"),
            net_to_worker=Decimal("92.00"),
            fee_percent=Decimal("8"),
        )

        result = fees.to_dict()

        assert result["gross_amount"] == 100.0
        assert result["platform_fee"] == 8.0
        assert result["net_to_worker"] == 92.0
        assert result["fee_percent"] == 8.0
