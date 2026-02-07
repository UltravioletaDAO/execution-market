"""
E2E Tests for Escrow Flows through MCP Tools.

Tests the two primary escrow flows that MUST work in production:

Flow 1 (Release): AUTHORIZE → task in DB → worker submits → RELEASE to worker
Flow 2 (Refund): AUTHORIZE → task in DB → task cancelled → REFUND to agent

Also validates:
- $100 deposit limit enforcement (commit 0ee2cf4)
- Arbiter escrow dispute resolution (AUTHORIZE → review → RELEASE or REFUND)
- em_escrow_dispute returns non-functional message
- Strategy recommendation respects deposit limit warnings

These tests exercise the MCP tool layer (escrow_tools.py) with a mocked
AdvancedEscrowClient so we validate the full tool → integration → SDK stack
without requiring on-chain transactions.
"""

import sys
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Mock the mcp module before any tools import triggers it
if "mcp" not in sys.modules:
    _mock_mcp = MagicMock()
    sys.modules["mcp"] = _mock_mcp
    sys.modules["mcp.server"] = _mock_mcp.server
    sys.modules["mcp.server.fastmcp"] = _mock_mcp.server.fastmcp
    sys.modules["mcp.server.fastmcp"].FastMCP = MagicMock

from ..e2e.conftest import (
    MockAgent,
    MockWorker,
    MockSupabaseClient,
)


# =============================================================================
# Mock SDK types for testing the tool layer
# =============================================================================


@dataclass
class MockPaymentInfo:
    """Simulates uvd_x402_sdk PaymentInfo."""

    receiver: str = ""
    amount: int = 0
    tier: str = "standard"
    max_fee_bps: int = 800


@dataclass
class MockAuthorizationResult:
    """Simulates uvd_x402_sdk AuthorizationResult."""

    success: bool = True
    transaction_hash: str = "0xAUTH_TX_MOCK_1234567890abcdef"
    error: Optional[str] = None


@dataclass
class MockTransactionResult:
    """Simulates uvd_x402_sdk TransactionResult."""

    success: bool = True
    transaction_hash: str = "0xTX_MOCK_1234567890abcdef"
    gas_used: int = 85000
    error: Optional[str] = None


class MockAdvancedEscrowClient:
    """
    Simulates the uvd_x402_sdk AdvancedEscrowClient.
    Tracks state in memory to validate flow sequences.
    """

    def __init__(self):
        self.payer = "0xMOCK_PAYER_ADDRESS_1234567890abcdef1234"
        self.facilitator_url = "https://facilitator.test.local"
        self._escrows: Dict[str, dict] = {}
        self._tx_counter = 0

    def _next_tx(self, prefix: str = "TX") -> str:
        self._tx_counter += 1
        return f"0x{prefix}_{self._tx_counter:06d}_{'a' * 40}"

    def build_payment_info(self, receiver, amount, tier, max_fee_bps=800):
        return MockPaymentInfo(
            receiver=receiver,
            amount=amount,
            tier=tier.value if hasattr(tier, "value") else tier,
            max_fee_bps=max_fee_bps,
        )

    def authorize(self, payment_info: MockPaymentInfo) -> MockAuthorizationResult:
        key = f"auth_{payment_info.receiver}_{payment_info.amount}"
        self._escrows[key] = {
            "payment_info": payment_info,
            "status": "authorized",
            "released": False,
            "refunded": False,
        }
        return MockAuthorizationResult(
            success=True,
            transaction_hash=self._next_tx("AUTH"),
        )

    def release(
        self, payment_info: MockPaymentInfo, amount=None
    ) -> MockTransactionResult:
        return MockTransactionResult(
            success=True,
            transaction_hash=self._next_tx("RELEASE"),
            gas_used=92000,
        )

    def refund_in_escrow(
        self, payment_info: MockPaymentInfo, amount=None
    ) -> MockTransactionResult:
        return MockTransactionResult(
            success=True,
            transaction_hash=self._next_tx("REFUND"),
            gas_used=78000,
        )

    def charge(self, payment_info: MockPaymentInfo) -> MockTransactionResult:
        return MockTransactionResult(
            success=True,
            transaction_hash=self._next_tx("CHARGE"),
            gas_used=65000,
        )


# =============================================================================
# Mock EMAdvancedEscrow that wraps MockAdvancedEscrowClient
# =============================================================================


class MockEMAdvancedEscrow:
    """
    Simulates EMAdvancedEscrow from advanced_escrow_integration.py.
    Uses MockAdvancedEscrowClient internally.
    """

    DEPOSIT_LIMIT_USDC = Decimal("100")

    def __init__(self):
        self.client = MockAdvancedEscrowClient()
        self.payer = self.client.payer
        self._task_payments: Dict[str, Any] = {}

    def _amount_to_atomic(self, amount_usdc: Decimal) -> int:
        return int(amount_usdc * Decimal(10**6))

    def _get_tier_value(self, amount_usdc: Decimal) -> str:
        if amount_usdc < 5:
            return "micro"
        elif amount_usdc < 50:
            return "standard"
        elif amount_usdc < 200:
            return "premium"
        else:
            return "enterprise"

    def recommend_strategy(
        self,
        amount_usdc,
        worker_reputation=0.0,
        external_dependency=False,
        requires_quality_review=False,
        erc8004_score=None,
    ):
        from integrations.x402.advanced_escrow_integration import PaymentStrategy

        effective_rep = (
            erc8004_score if erc8004_score is not None else worker_reputation
        )

        if effective_rep >= 0.90 and amount_usdc < 5:
            return PaymentStrategy.INSTANT_PAYMENT
        if external_dependency:
            return PaymentStrategy.ESCROW_CANCEL
        if requires_quality_review and amount_usdc >= 50:
            return PaymentStrategy.DISPUTE_RESOLUTION
        if effective_rep < 0.50 and amount_usdc >= 50:
            return PaymentStrategy.DISPUTE_RESOLUTION
        return PaymentStrategy.ESCROW_CAPTURE

    def authorize_task(self, task_id, receiver, amount_usdc, strategy=None, tier=None):
        """Lock bounty in escrow."""
        amount_atomic = self._amount_to_atomic(amount_usdc)
        task_tier = tier or self._get_tier_value(amount_usdc)

        pi = self.client.build_payment_info(
            receiver=receiver,
            amount=amount_atomic,
            tier=MagicMock(value=task_tier),
            max_fee_bps=800,
        )

        result = self.client.authorize(pi)

        payment = MagicMock()
        payment.task_id = task_id
        payment.strategy = strategy or MagicMock(value="escrow_capture")
        payment.payment_info = pi
        payment.authorization = result
        payment.amount_usdc = amount_usdc
        payment.released_usdc = Decimal("0")
        payment.refunded_usdc = Decimal("0")
        payment.status = "authorized" if result.success else "failed"
        payment.tx_hashes = [result.transaction_hash] if result.success else []

        self._task_payments[task_id] = payment
        return payment

    def release_to_worker(self, task_id, amount_usdc=None):
        """Release escrowed funds to worker."""
        payment = self._task_payments.get(task_id)
        if not payment or not payment.payment_info:
            raise ValueError(f"Task {task_id} not found or not authorized")

        result = self.client.release(payment.payment_info, amount_usdc)

        if result.success:
            released = amount_usdc or payment.amount_usdc
            payment.released_usdc = released
            payment.status = "released"
            payment.tx_hashes.append(result.transaction_hash)

        return result

    def refund_to_agent(self, task_id, amount_usdc=None):
        """Refund escrowed funds to agent."""
        payment = self._task_payments.get(task_id)
        if not payment or not payment.payment_info:
            raise ValueError(f"Task {task_id} not found or not authorized")

        result = self.client.refund_in_escrow(payment.payment_info, amount_usdc)

        if result.success:
            refunded = amount_usdc or payment.amount_usdc
            payment.refunded_usdc = refunded
            payment.status = "refunded"
            payment.tx_hashes.append(result.transaction_hash)

        return result

    def charge_instant(self, task_id, receiver, amount_usdc, tier=None):
        """Instant payment, no escrow."""
        amount_atomic = self._amount_to_atomic(amount_usdc)
        task_tier = tier or self._get_tier_value(amount_usdc)

        pi = self.client.build_payment_info(
            receiver=receiver,
            amount=amount_atomic,
            tier=MagicMock(value=task_tier),
            max_fee_bps=800,
        )

        result = self.client.charge(pi)

        payment = MagicMock()
        payment.task_id = task_id
        payment.strategy = MagicMock(value="instant_payment")
        payment.payment_info = pi
        payment.amount_usdc = amount_usdc
        payment.released_usdc = amount_usdc if result.success else Decimal("0")
        payment.refunded_usdc = Decimal("0")
        payment.status = "charged" if result.success else "failed"
        payment.tx_hashes = [result.transaction_hash] if result.success else []

        self._task_payments[task_id] = payment
        return payment

    def get_task_payment(self, task_id):
        return self._task_payments.get(task_id)

    def partial_release_and_refund(self, task_id, release_percent):
        payment = self._task_payments.get(task_id)
        if not payment or not payment.payment_info:
            raise ValueError(f"Task {task_id} not found or not authorized")

        release_frac = Decimal(str(release_percent)) / Decimal("100")
        release_amount = payment.amount_usdc * release_frac
        refund_amount = payment.amount_usdc - release_amount

        release_result = self.client.release(
            payment.payment_info, self._amount_to_atomic(release_amount)
        )
        refund_result = self.client.refund_in_escrow(
            payment.payment_info, self._amount_to_atomic(refund_amount)
        )

        payment.released_usdc = release_amount
        payment.refunded_usdc = refund_amount
        payment.status = "partial_released"

        return {
            "success": True,
            "released_usdc": float(release_amount),
            "refunded_usdc": float(refund_amount),
            "release_result": release_result,
            "refund_result": refund_result,
        }


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_advanced_escrow():
    """Create a mock EMAdvancedEscrow instance."""
    return MockEMAdvancedEscrow()


@pytest.fixture
def patch_escrow_tools(mock_advanced_escrow):
    """
    Patch the escrow_tools module so tools use MockEMAdvancedEscrow
    instead of requiring the real uvd-x402-sdk.
    """
    with (
        patch("tools.escrow_tools.ADVANCED_ESCROW_AVAILABLE", True),
        patch("tools.escrow_tools._get_escrow", return_value=mock_advanced_escrow),
        patch("tools.escrow_tools.DEPOSIT_LIMIT_USDC", Decimal("100")),
    ):
        yield mock_advanced_escrow


@pytest.fixture
def escrow_tools(patch_escrow_tools):
    """Import escrow tool functions after patching."""
    from tools.escrow_tools import (
        EscrowAuthorizeInput,
        EscrowReleaseInput,
        EscrowRefundInput,
        EscrowChargeInput,
        EscrowDisputeInput,
        EscrowStatusInput,
        EscrowRecommendInput,
        EscrowPartialReleaseInput,
    )

    return {
        "EscrowAuthorizeInput": EscrowAuthorizeInput,
        "EscrowReleaseInput": EscrowReleaseInput,
        "EscrowRefundInput": EscrowRefundInput,
        "EscrowChargeInput": EscrowChargeInput,
        "EscrowDisputeInput": EscrowDisputeInput,
        "EscrowStatusInput": EscrowStatusInput,
        "EscrowRecommendInput": EscrowRecommendInput,
        "EscrowPartialReleaseInput": EscrowPartialReleaseInput,
    }


@pytest.fixture
def registered_tools(patch_escrow_tools):
    """
    Register escrow tools on a mock MCP server and return the tool functions.
    """
    tool_registry = {}

    class MockMCP:
        def tool(self, name=None, annotations=None):
            def decorator(func):
                tool_registry[name] = func
                return func

            return decorator

    mock_mcp = MockMCP()

    from tools.escrow_tools import register_escrow_tools

    register_escrow_tools(mock_mcp)

    return tool_registry


# =============================================================================
# FLOW 1: AUTHORIZE → RELEASE (Happy Path - Worker Gets Paid)
# =============================================================================


@pytest.mark.asyncio
async def test_flow_release_happy_path(
    registered_tools,
    mock_supabase: MockSupabaseClient,
    test_agent: MockAgent,
    test_worker: MockWorker,
    sample_task_input: dict,
    sample_evidence: dict,
    patch_escrow_tools,
):
    """
    E2E: Full release flow through MCP tools.

    1. Recommend strategy -> escrow_capture
    2. Authorize escrow (lock $10 USDC) -> get auth tx
    3. Task posted in Supabase
    4. Worker applies, gets assigned, submits evidence
    5. Agent approves -> Release escrow to worker
    6. Verify: task completed, payment released, tx hashes present
    """
    mock_supabase.register_worker(test_worker)
    task_id = str(uuid.uuid4())
    worker_wallet = test_worker.wallet.address

    # --- Step 1: Recommend strategy ---
    from tools.escrow_tools import EscrowRecommendInput

    recommend = registered_tools["em_escrow_recommend_strategy"]
    rec_result = await recommend(
        EscrowRecommendInput(
            amount_usdc=10.00,
            worker_reputation=0.75,
            external_dependency=False,
            requires_quality_review=False,
        )
    )

    assert "escrow_capture" in rec_result
    assert "recommended" in rec_result.lower()

    # --- Step 2: Authorize escrow ---
    from tools.escrow_tools import EscrowAuthorizeInput

    authorize = registered_tools["em_escrow_authorize"]
    auth_result = await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=10.00,
            strategy="escrow_capture",
        )
    )

    assert "Escrow Authorized" in auth_result
    assert "AUTH" in auth_result  # tx hash prefix
    assert "em_escrow_release" in auth_result  # next step hint

    # --- Step 3: Task posted in DB ---
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title=sample_task_input["title"],
        instructions=sample_task_input["instructions"],
        category=sample_task_input["category"],
        bounty_usd=10.00,
        deadline=deadline,
        evidence_required=sample_task_input["evidence_required"],
    )
    # Link escrow to task
    await mock_supabase.update_task(task["id"], {"escrow_task_id": task_id})

    assert task["status"] == "published"

    # --- Step 4: Worker applies, gets assigned, submits ---
    await mock_supabase.apply_to_task(
        task_id=task["id"],
        executor_id=test_worker.executor_id,
        message="I can verify this location",
    )

    await mock_supabase.assign_task(
        task_id=task["id"],
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    submit_result = await mock_supabase.submit_work(
        task_id=task["id"],
        executor_id=test_worker.executor_id,
        evidence=sample_evidence,
        notes="Completed as requested",
    )
    assert submit_result["task"]["status"] == "submitted"

    # Agent approves submission
    await mock_supabase.update_submission(
        submission_id=submit_result["submission"]["id"],
        agent_id=test_agent.agent_id,
        verdict="accepted",
        notes="Evidence verified",
    )

    # --- Step 5: Release escrow to worker ---
    from tools.escrow_tools import EscrowReleaseInput

    release = registered_tools["em_escrow_release"]
    release_result = await release(
        EscrowReleaseInput(
            task_id=task_id,
        )
    )

    assert "Payment Released to Worker" in release_result
    assert "RELEASE" in release_result  # tx hash
    assert "$10.00 USDC" in release_result

    # --- Step 6: Verify final state ---
    final_task = await mock_supabase.get_task(task["id"])
    assert final_task["status"] == "completed"

    # Verify escrow state via status tool
    from tools.escrow_tools import EscrowStatusInput

    status = registered_tools["em_escrow_status"]
    status_result = await status(EscrowStatusInput(task_id=task_id))

    assert "released" in status_result.lower()
    assert "Payment has been released" in status_result


@pytest.mark.asyncio
async def test_flow_release_with_amount(
    registered_tools,
    patch_escrow_tools,
):
    """Test release with explicit amount specified."""
    task_id = str(uuid.uuid4())
    worker_wallet = "0x" + "B" * 40

    # Authorize
    from tools.escrow_tools import EscrowAuthorizeInput, EscrowReleaseInput

    authorize = registered_tools["em_escrow_authorize"]
    await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=50.00,
            strategy="escrow_capture",
        )
    )

    # Release with explicit amount
    release = registered_tools["em_escrow_release"]
    result = await release(
        EscrowReleaseInput(
            task_id=task_id,
            amount_usdc=50.00,
        )
    )

    assert "Payment Released to Worker" in result
    assert "$50.00 USDC" in result


# =============================================================================
# FLOW 2: AUTHORIZE → REFUND (Task Cancelled - Agent Gets Money Back)
# =============================================================================


@pytest.mark.asyncio
async def test_flow_refund_happy_path(
    registered_tools,
    mock_supabase: MockSupabaseClient,
    test_agent: MockAgent,
    sample_task_input: dict,
    patch_escrow_tools,
):
    """
    E2E: Full refund flow through MCP tools.

    1. Authorize escrow (lock $25 USDC)
    2. Task posted in Supabase
    3. No worker takes it / agent cancels
    4. Refund escrow to agent
    5. Verify: task cancelled, refund tx present
    """
    task_id = str(uuid.uuid4())
    worker_wallet = "0x" + "C" * 40  # Placeholder receiver for auth

    # --- Step 1: Authorize escrow ---
    from tools.escrow_tools import EscrowAuthorizeInput

    authorize = registered_tools["em_escrow_authorize"]
    auth_result = await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=25.00,
            strategy="escrow_cancel",
        )
    )

    assert "Escrow Authorized" in auth_result
    assert "em_escrow_refund" in auth_result  # next step for cancel strategy

    # --- Step 2: Task posted in DB ---
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Task to be cancelled",
        instructions="This will be cancelled",
        category="physical_presence",
        bounty_usd=25.00,
        deadline=deadline,
        evidence_required=["photo_geo"],
    )

    assert task["status"] == "published"

    # --- Step 3: Agent cancels task ---
    cancelled = await mock_supabase.cancel_task(
        task_id=task["id"],
        agent_id=test_agent.agent_id,
    )
    assert cancelled["status"] == "cancelled"

    # --- Step 4: Refund escrow to agent ---
    from tools.escrow_tools import EscrowRefundInput

    refund = registered_tools["em_escrow_refund"]
    refund_result = await refund(
        EscrowRefundInput(
            task_id=task_id,
        )
    )

    assert "Escrow Refunded to Agent" in refund_result
    assert "REFUND" in refund_result  # tx hash
    assert "bounty has been returned" in refund_result

    # --- Step 5: Verify status shows refunded ---
    from tools.escrow_tools import EscrowStatusInput

    status = registered_tools["em_escrow_status"]
    status_result = await status(EscrowStatusInput(task_id=task_id))

    assert "refunded" in status_result.lower()


@pytest.mark.asyncio
async def test_flow_refund_with_amount(
    registered_tools,
    patch_escrow_tools,
):
    """Test refund with explicit amount specified."""
    task_id = str(uuid.uuid4())
    worker_wallet = "0x" + "D" * 40

    from tools.escrow_tools import EscrowAuthorizeInput, EscrowRefundInput

    authorize = registered_tools["em_escrow_authorize"]
    await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=75.00,
            strategy="escrow_cancel",
        )
    )

    refund = registered_tools["em_escrow_refund"]
    result = await refund(
        EscrowRefundInput(
            task_id=task_id,
            amount_usdc=75.00,
        )
    )

    assert "Escrow Refunded to Agent" in result
    assert "$75.00 USDC" in result


# =============================================================================
# DEPOSIT LIMIT ENFORCEMENT ($100 max - commit 0ee2cf4)
# =============================================================================


@pytest.mark.asyncio
async def test_authorize_rejects_over_100(
    registered_tools,
    patch_escrow_tools,
):
    """Amounts > $100 are rejected by authorize tool BEFORE reaching on-chain."""
    from tools.escrow_tools import EscrowAuthorizeInput

    authorize = registered_tools["em_escrow_authorize"]

    result = await authorize(
        EscrowAuthorizeInput(
            task_id=str(uuid.uuid4()),
            receiver="0x" + "A" * 40,
            amount_usdc=150.00,
            strategy="escrow_capture",
        )
    )

    assert "Exceeds Contract Deposit Limit" in result
    assert "$100" in result
    assert "Reduce the bounty" in result


@pytest.mark.asyncio
async def test_charge_rejects_over_100(
    registered_tools,
    patch_escrow_tools,
):
    """Amounts > $100 are rejected by charge tool BEFORE reaching on-chain."""
    from tools.escrow_tools import EscrowChargeInput

    charge = registered_tools["em_escrow_charge"]

    result = await charge(
        EscrowChargeInput(
            task_id=str(uuid.uuid4()),
            receiver="0x" + "B" * 40,
            amount_usdc=200.00,
        )
    )

    assert "Exceeds Contract Deposit Limit" in result
    assert "$100" in result


@pytest.mark.asyncio
async def test_authorize_at_exact_limit(
    registered_tools,
    patch_escrow_tools,
):
    """$100 exactly should be accepted (not rejected)."""
    from tools.escrow_tools import EscrowAuthorizeInput

    authorize = registered_tools["em_escrow_authorize"]

    result = await authorize(
        EscrowAuthorizeInput(
            task_id=str(uuid.uuid4()),
            receiver="0x" + "E" * 40,
            amount_usdc=100.00,
            strategy="escrow_capture",
        )
    )

    assert "Escrow Authorized" in result
    assert "Exceeds" not in result


@pytest.mark.asyncio
async def test_authorize_under_limit(
    registered_tools,
    patch_escrow_tools,
):
    """$99.99 should be accepted."""
    from tools.escrow_tools import EscrowAuthorizeInput

    authorize = registered_tools["em_escrow_authorize"]

    result = await authorize(
        EscrowAuthorizeInput(
            task_id=str(uuid.uuid4()),
            receiver="0x" + "F" * 40,
            amount_usdc=99.99,
            strategy="escrow_capture",
        )
    )

    assert "Escrow Authorized" in result


@pytest.mark.asyncio
async def test_recommend_strategy_warns_over_limit(
    registered_tools,
    patch_escrow_tools,
):
    """Strategy recommendation warns when amount > $100."""
    from tools.escrow_tools import EscrowRecommendInput

    recommend = registered_tools["em_escrow_recommend_strategy"]

    result = await recommend(
        EscrowRecommendInput(
            amount_usdc=250.00,
            worker_reputation=0.5,
        )
    )

    assert "Deposit Limit Warning" in result
    assert "$100" in result


# =============================================================================
# DISPUTE RESOLUTION (Arbiter Escrow - commit 0ee2cf4)
# =============================================================================


@pytest.mark.asyncio
async def test_dispute_tool_returns_not_available(
    registered_tools,
    patch_escrow_tools,
):
    """
    em_escrow_dispute returns informational message, NOT a transaction.
    Per commit 0ee2cf4: tokenCollector not implemented.
    """
    from tools.escrow_tools import EscrowDisputeInput

    dispute = registered_tools["em_escrow_dispute"]

    result = await dispute(
        EscrowDisputeInput(
            task_id=str(uuid.uuid4()),
        )
    )

    assert "Not Available" in result
    assert "tokenCollector" in result
    assert "em_escrow_refund" in result  # recommends alternative
    assert "in-escrow" in result.lower()


@pytest.mark.asyncio
async def test_arbiter_escrow_release_path(
    registered_tools,
    mock_supabase: MockSupabaseClient,
    test_agent: MockAgent,
    test_worker: MockWorker,
    sample_evidence: dict,
    patch_escrow_tools,
):
    """
    Arbiter escrow: AUTHORIZE → arbiter reviews → RELEASE.
    Dispute resolution strategy where funds stay in escrow until quality verified.
    """
    mock_supabase.register_worker(test_worker)
    task_id = str(uuid.uuid4())
    worker_wallet = test_worker.wallet.address

    # --- Authorize with dispute_resolution strategy ---
    from tools.escrow_tools import EscrowAuthorizeInput

    authorize = registered_tools["em_escrow_authorize"]
    auth_result = await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=75.00,
            strategy="dispute_resolution",
        )
    )

    assert "Escrow Authorized" in auth_result
    assert "Arbiter reviews" in auth_result
    assert "em_escrow_release" in auth_result  # if approved
    assert "em_escrow_refund" in auth_result  # if rejected

    # --- Task posted and worker submits ---
    deadline = datetime.now(timezone.utc) + timedelta(hours=48)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Quality-sensitive task",
        instructions="Requires arbiter review",
        category="knowledge_access",
        bounty_usd=75.00,
        deadline=deadline,
        evidence_required=["photo", "text_response"],
    )

    await mock_supabase.assign_task(
        task_id=task["id"],
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    # Evidence must match the required fields in the task
    arbiter_evidence = {
        "photo": "ipfs://QmArbiterPhoto123",
        "text_response": "Detailed document scan with all fields visible.",
    }

    submit_result = await mock_supabase.submit_work(
        task_id=task["id"],
        executor_id=test_worker.executor_id,
        evidence=arbiter_evidence,
    )

    # --- Arbiter approves → RELEASE ---
    await mock_supabase.update_submission(
        submission_id=submit_result["submission"]["id"],
        agent_id=test_agent.agent_id,
        verdict="accepted",
        notes="Quality verified by arbiter",
    )

    from tools.escrow_tools import EscrowReleaseInput

    release = registered_tools["em_escrow_release"]
    release_result = await release(EscrowReleaseInput(task_id=task_id))

    assert "Payment Released to Worker" in release_result

    # Task should be completed
    final_task = await mock_supabase.get_task(task["id"])
    assert final_task["status"] == "completed"


@pytest.mark.asyncio
async def test_arbiter_escrow_refund_path(
    registered_tools,
    mock_supabase: MockSupabaseClient,
    test_agent: MockAgent,
    test_worker: MockWorker,
    patch_escrow_tools,
):
    """
    Arbiter escrow: AUTHORIZE → arbiter reviews → REFUND.
    Quality is unacceptable, funds returned to agent while still in escrow.
    """
    mock_supabase.register_worker(test_worker)
    task_id = str(uuid.uuid4())
    worker_wallet = test_worker.wallet.address

    # --- Authorize with dispute_resolution strategy ---
    from tools.escrow_tools import EscrowAuthorizeInput

    authorize = registered_tools["em_escrow_authorize"]
    await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=60.00,
            strategy="dispute_resolution",
        )
    )

    # --- Task posted, worker submits bad work ---
    deadline = datetime.now(timezone.utc) + timedelta(hours=48)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Quality check task",
        instructions="Take clear photo",
        category="knowledge_access",
        bounty_usd=60.00,
        deadline=deadline,
        evidence_required=["photo"],
    )

    await mock_supabase.assign_task(
        task_id=task["id"],
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    bad_evidence = {"photo": "ipfs://QmBlurryBadPhoto"}
    submit_result = await mock_supabase.submit_work(
        task_id=task["id"],
        executor_id=test_worker.executor_id,
        evidence=bad_evidence,
    )

    # --- Arbiter rejects → REFUND (in-escrow, not post-escrow) ---
    await mock_supabase.update_submission(
        submission_id=submit_result["submission"]["id"],
        agent_id=test_agent.agent_id,
        verdict="disputed",
        notes="Photo is blurry, doesn't meet requirements",
    )

    from tools.escrow_tools import EscrowRefundInput

    refund = registered_tools["em_escrow_refund"]
    refund_result = await refund(EscrowRefundInput(task_id=task_id))

    assert "Escrow Refunded to Agent" in refund_result
    assert "REFUND" in refund_result

    # Verify status
    from tools.escrow_tools import EscrowStatusInput

    status = registered_tools["em_escrow_status"]
    status_result = await status(EscrowStatusInput(task_id=task_id))
    assert "refunded" in status_result.lower()


@pytest.mark.asyncio
async def test_recommend_dispute_resolution_for_high_value_low_rep(
    registered_tools,
    patch_escrow_tools,
):
    """
    Strategy recommendation returns dispute_resolution for
    high-value tasks with low-reputation workers.
    """
    from tools.escrow_tools import EscrowRecommendInput

    recommend = registered_tools["em_escrow_recommend_strategy"]

    result = await recommend(
        EscrowRecommendInput(
            amount_usdc=75.00,
            worker_reputation=0.30,
            requires_quality_review=False,
        )
    )

    assert "dispute_resolution" in result
    assert "recommended" in result.lower()


@pytest.mark.asyncio
async def test_recommend_dispute_resolution_for_quality_review(
    registered_tools,
    patch_escrow_tools,
):
    """
    Strategy recommendation returns dispute_resolution when
    quality review is required and amount >= $50.
    """
    from tools.escrow_tools import EscrowRecommendInput

    recommend = registered_tools["em_escrow_recommend_strategy"]

    result = await recommend(
        EscrowRecommendInput(
            amount_usdc=80.00,
            worker_reputation=0.80,
            requires_quality_review=True,
        )
    )

    assert "dispute_resolution" in result
    assert "Dispute Resolution Note" in result
    assert "in escrow" in result.lower()


# =============================================================================
# EDGE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_release_nonexistent_task(
    registered_tools,
    patch_escrow_tools,
):
    """Releasing a task that was never authorized returns error."""
    from tools.escrow_tools import EscrowReleaseInput

    release = registered_tools["em_escrow_release"]

    result = await release(
        EscrowReleaseInput(
            task_id="nonexistent-task-id",
        )
    )

    assert "Error" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_refund_nonexistent_task(
    registered_tools,
    patch_escrow_tools,
):
    """Refunding a task that was never authorized returns error."""
    from tools.escrow_tools import EscrowRefundInput

    refund = registered_tools["em_escrow_refund"]

    result = await refund(
        EscrowRefundInput(
            task_id="nonexistent-task-id",
        )
    )

    assert "Error" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_status_nonexistent_task(
    registered_tools,
    patch_escrow_tools,
):
    """Status for a task without escrow returns informative message."""
    from tools.escrow_tools import EscrowStatusInput

    status = registered_tools["em_escrow_status"]

    result = await status(
        EscrowStatusInput(
            task_id="no-such-task",
        )
    )

    assert "No Escrow Found" in result


@pytest.mark.asyncio
async def test_instant_payment_flow(
    registered_tools,
    patch_escrow_tools,
):
    """Test instant payment (CHARGE) flow for trusted micro-tasks."""
    task_id = str(uuid.uuid4())
    worker_wallet = "0x" + "A" * 40

    # Recommend should suggest instant for high-rep micro task
    from tools.escrow_tools import EscrowRecommendInput

    recommend = registered_tools["em_escrow_recommend_strategy"]
    rec_result = await recommend(
        EscrowRecommendInput(
            amount_usdc=3.00,
            worker_reputation=0.95,
        )
    )
    assert "instant_payment" in rec_result

    # Charge directly
    from tools.escrow_tools import EscrowChargeInput

    charge = registered_tools["em_escrow_charge"]
    charge_result = await charge(
        EscrowChargeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=3.00,
        )
    )

    assert "Instant Payment Sent" in charge_result
    assert "CHARGE" in charge_result


@pytest.mark.asyncio
async def test_partial_release_flow(
    registered_tools,
    patch_escrow_tools,
):
    """Test partial release + refund for proof-of-attempt."""
    task_id = str(uuid.uuid4())
    worker_wallet = "0x" + "C" * 40

    # Authorize first
    from tools.escrow_tools import EscrowAuthorizeInput, EscrowPartialReleaseInput

    authorize = registered_tools["em_escrow_authorize"]
    await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=50.00,
            strategy="partial_payment",
        )
    )

    # Partial release (20% to worker, 80% refund)
    partial = registered_tools["em_escrow_partial_release"]
    result = await partial(
        EscrowPartialReleaseInput(
            task_id=task_id,
            release_percent=20,
        )
    )

    assert "Partial Release Complete" in result
    assert "20%" in result
    assert "80%" in result


@pytest.mark.asyncio
async def test_status_after_authorize(
    registered_tools,
    patch_escrow_tools,
):
    """Status shows authorized state with available actions."""
    task_id = str(uuid.uuid4())
    worker_wallet = "0x" + "D" * 40

    from tools.escrow_tools import EscrowAuthorizeInput, EscrowStatusInput

    authorize = registered_tools["em_escrow_authorize"]
    await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=20.00,
            strategy="escrow_capture",
        )
    )

    status = registered_tools["em_escrow_status"]
    result = await status(EscrowStatusInput(task_id=task_id))

    assert "Escrow Payment Status" in result
    assert "authorized" in result.lower()
    assert "em_escrow_release" in result
    assert "em_escrow_refund" in result


@pytest.mark.asyncio
async def test_status_after_release_no_dispute_suggestion(
    registered_tools,
    patch_escrow_tools,
):
    """
    After release, status should NOT suggest dispute as an action.
    Per commit 0ee2cf4: post-release dispute not available.
    """
    task_id = str(uuid.uuid4())
    worker_wallet = "0x" + "E" * 40

    from tools.escrow_tools import (
        EscrowAuthorizeInput,
        EscrowReleaseInput,
        EscrowStatusInput,
    )

    authorize = registered_tools["em_escrow_authorize"]
    await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=30.00,
            strategy="escrow_capture",
        )
    )

    release = registered_tools["em_escrow_release"]
    await release(EscrowReleaseInput(task_id=task_id))

    status = registered_tools["em_escrow_status"]
    result = await status(EscrowStatusInput(task_id=task_id))

    assert "released" in result.lower()
    assert "em_escrow_dispute" not in result
    assert (
        "not available" in result.lower()
        or "not implemented" in result.lower()
        or "Post-release dispute" in result
    )


@pytest.mark.asyncio
async def test_escrow_cancel_strategy_flow(
    registered_tools,
    patch_escrow_tools,
):
    """
    escrow_cancel strategy: AUTHORIZE → conditions fail → REFUND.
    For weather/event-dependent tasks.
    """
    from tools.escrow_tools import EscrowRecommendInput

    recommend = registered_tools["em_escrow_recommend_strategy"]
    rec_result = await recommend(
        EscrowRecommendInput(
            amount_usdc=30.00,
            worker_reputation=0.70,
            external_dependency=True,
        )
    )
    assert "escrow_cancel" in rec_result

    task_id = str(uuid.uuid4())
    worker_wallet = "0x" + "F" * 40

    from tools.escrow_tools import EscrowAuthorizeInput, EscrowRefundInput

    authorize = registered_tools["em_escrow_authorize"]
    auth_result = await authorize(
        EscrowAuthorizeInput(
            task_id=task_id,
            receiver=worker_wallet,
            amount_usdc=30.00,
            strategy="escrow_cancel",
        )
    )

    assert "Escrow Authorized" in auth_result
    assert "em_escrow_refund" in auth_result

    # External condition fails → refund
    refund = registered_tools["em_escrow_refund"]
    refund_result = await refund(EscrowRefundInput(task_id=task_id))

    assert "Escrow Refunded to Agent" in refund_result
