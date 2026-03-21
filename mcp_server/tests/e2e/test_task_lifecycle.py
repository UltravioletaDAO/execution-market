"""
E2E Tests for Complete Task Lifecycle.

Tests the full flow:
1. Agent publishes task -> escrow created
2. Worker sees task (get_tasks)
3. Worker applies (apply_to_task)
4. Agent assigns worker (assign_task)
5. Worker submits evidence (submit_work) -> 30% partial release
6. Agent approves (approve_submission) -> 70% final release
7. Task marked completed

Also tests:
- test_lifecycle_with_rejection: Agent rejects, worker can resubmit
- test_lifecycle_with_timeout: Task expires, agent gets refund
- test_lifecycle_with_dispute: Dispute raised and resolved
"""

import pytest

pytestmark = pytest.mark.core
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..e2e.conftest import (
    MockAgent,
    MockWorker,
    MockEscrowManager,
    MockSupabaseClient,
)


# ============== HAPPY PATH: COMPLETE LIFECYCLE ==============


@pytest.mark.asyncio
async def test_complete_task_lifecycle(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    test_worker: MockWorker,
    sample_task_input: dict,
    sample_evidence: dict,
):
    """
    Test the complete happy path task lifecycle:

    1. Agent publishes task -> escrow created
    2. Worker sees task (get_tasks)
    3. Worker applies (apply_to_task)
    4. Agent assigns worker (assign_task)
    5. Worker submits evidence (submit_work) -> 30% partial release
    6. Agent approves (approve_submission) -> 70% final release
    7. Task marked completed
    """
    # Register worker in the system
    mock_supabase.register_worker(test_worker)

    # ========== STEP 1: Agent publishes task ==========
    deadline = datetime.now(timezone.utc) + timedelta(
        hours=sample_task_input["deadline_hours"]
    )
    task = await mock_supabase.create_task(
        agent_id=sample_task_input["agent_id"],
        title=sample_task_input["title"],
        instructions=sample_task_input["instructions"],
        category=sample_task_input["category"],
        bounty_usd=sample_task_input["bounty_usd"],
        deadline=deadline,
        evidence_required=sample_task_input["evidence_required"],
        evidence_optional=sample_task_input.get("evidence_optional"),
        location_hint=sample_task_input.get("location_hint"),
        min_reputation=sample_task_input.get("min_reputation", 0),
    )

    assert task["status"] == "published"
    assert task["id"] is not None
    task_id = task["id"]

    # Create escrow for the task
    escrow = await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal(str(sample_task_input["bounty_usd"])),
        agent_wallet=test_agent.wallet.address,
    )

    assert escrow.status == "deposited"
    assert escrow.total_amount == Decimal("10.00")
    assert escrow.escrow_id is not None

    # ========== STEP 2: Worker sees available tasks ==========
    available_tasks = await mock_supabase.get_tasks(status="published")

    assert available_tasks["count"] > 0
    task_found = any(t["id"] == task_id for t in available_tasks["tasks"])
    assert task_found, "Published task should be visible to workers"

    # ========== STEP 3: Worker applies to task ==========
    application_result = await mock_supabase.apply_to_task(
        task_id=task_id,
        executor_id=test_worker.executor_id,
        message="I can verify this location today",
    )

    assert application_result["application"]["status"] == "pending"
    assert application_result["task"]["id"] == task_id

    # ========== STEP 4: Agent assigns worker ==========
    assign_result = await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
        notes="Worker has good reputation",
    )

    assert assign_result["task"]["status"] == "accepted"
    assert assign_result["task"]["executor_id"] == test_worker.executor_id

    # ========== STEP 5: Worker submits evidence -> 30% partial release ==========
    submit_result = await mock_supabase.submit_work(
        task_id=task_id,
        executor_id=test_worker.executor_id,
        evidence=sample_evidence,
        notes="Work completed as requested",
    )

    assert submit_result["task"]["status"] == "submitted"
    assert submit_result["submission"]["agent_verdict"] == "pending"

    # Partial release on submission (30%)
    partial_result = await mock_escrow_manager.release_partial_on_submission(
        task_id=task_id,
        worker_wallet=test_worker.wallet.address,
    )

    assert partial_result["success"] is True
    assert partial_result["percent_released"] == 30.0

    # Verify escrow state
    escrow_state = mock_escrow_manager.get_escrow(task_id)
    assert escrow_state.status == "partial_released"

    # Net bounty = $10 * (1 - 13% fee) = $8.70
    # 30% of $8.70 = $2.61
    expected_partial = Decimal("10.00") * Decimal("0.87") * Decimal("0.30")
    assert escrow_state.released_amount == expected_partial.quantize(Decimal("0.01"))

    # ========== STEP 6: Agent approves -> 70% final release ==========
    submission_id = submit_result["submission"]["id"]

    approve_result = await mock_supabase.update_submission(
        submission_id=submission_id,
        agent_id=test_agent.agent_id,
        verdict="accepted",
        notes="Good work, evidence verified",
    )

    assert approve_result["agent_verdict"] == "accepted"

    # Final release (remaining 70% + platform fee)
    final_result = await mock_escrow_manager.release_on_approval(
        task_id=task_id,
        worker_wallet=test_worker.wallet.address,
    )

    assert final_result["success"] is True
    assert final_result["type"] == "final"

    # Verify escrow fully released
    escrow_state = mock_escrow_manager.get_escrow(task_id)
    assert escrow_state.status == "released"

    # Worker should receive full net amount: $10 * 0.87 = $8.70
    assert final_result["worker_payment"] == 8.70

    # Platform fee: $10 * 0.13 = $1.30
    assert final_result["platform_fee"] == 1.30

    # ========== STEP 7: Verify task is completed ==========
    final_task = await mock_supabase.get_task(task_id)
    assert final_task["status"] == "completed"
    assert final_task["completed_at"] is not None

    # Verify worker's reputation increased
    worker_stats = await mock_supabase.get_executor_stats(test_worker.executor_id)
    assert worker_stats["reputation_score"] > test_worker.reputation_score


@pytest.mark.asyncio
async def test_lifecycle_worker_reputation_check(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    low_reputation_worker: MockWorker,
    sample_task_input: dict,
):
    """Test that workers with insufficient reputation cannot apply."""
    # Register low reputation worker
    mock_supabase.register_worker(low_reputation_worker)

    # Create task with min_reputation = 50
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="High reputation task",
        instructions="This task requires experienced workers",
        category="physical_presence",
        bounty_usd=20.00,
        deadline=deadline,
        evidence_required=["photo"],
        min_reputation=50,
    )

    # Low reputation worker (10) tries to apply to task requiring 50
    with pytest.raises(ValueError, match="Insufficient reputation"):
        await mock_supabase.apply_to_task(
            task_id=task["id"],
            executor_id=low_reputation_worker.executor_id,
            message="I can do this",
        )


# ============== REJECTION AND RESUBMISSION ==============


@pytest.mark.asyncio
async def test_lifecycle_with_rejection(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    test_worker: MockWorker,
    sample_task_input: dict,
):
    """
    Test lifecycle with rejection and resubmission:

    1. Agent publishes task
    2. Worker assigned and submits
    3. Agent rejects with feedback
    4. Worker resubmits improved evidence
    5. Agent approves second submission
    """
    mock_supabase.register_worker(test_worker)

    # Create and assign task
    deadline = datetime.now(timezone.utc) + timedelta(hours=48)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Document verification task",
        instructions="Take a clear photo of the document",
        category="knowledge_access",
        bounty_usd=15.00,
        deadline=deadline,
        evidence_required=["photo", "text_response"],
    )
    task_id = task["id"]

    # Create escrow
    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("15.00"),
        agent_wallet=test_agent.wallet.address,
    )

    # Assign worker
    await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    # ========== First submission - will be rejected ==========
    bad_evidence = {
        "photo": "ipfs://QmBadPhoto123",
        "text_response": "Here's the document",  # Vague, not detailed
    }

    first_submit = await mock_supabase.submit_work(
        task_id=task_id,
        executor_id=test_worker.executor_id,
        evidence=bad_evidence,
        notes="First attempt",
    )

    # Agent rejects asking for more detail
    reject_result = await mock_supabase.update_submission(
        submission_id=first_submit["submission"]["id"],
        agent_id=test_agent.agent_id,
        verdict="more_info_requested",
        notes="Photo is blurry. Please provide a clearer image with the document number visible.",
    )

    assert reject_result["agent_verdict"] == "more_info_requested"

    # Task goes back to in_progress for resubmission
    await mock_supabase.update_task(task_id, {"status": "in_progress"})

    # ========== Second submission - will be approved ==========
    good_evidence = {
        "photo": "ipfs://QmClearPhoto456",
        "text_response": "Document #12345, dated 2026-01-25. All fields clearly visible.",
    }

    second_submit = await mock_supabase.submit_work(
        task_id=task_id,
        executor_id=test_worker.executor_id,
        evidence=good_evidence,
        notes="Resubmission with clearer photo",
    )

    # Release partial on resubmission
    partial_result = await mock_escrow_manager.release_partial_on_submission(
        task_id=task_id,
        worker_wallet=test_worker.wallet.address,
    )

    assert partial_result["success"] is True

    # Agent approves
    approve_result = await mock_supabase.update_submission(
        submission_id=second_submit["submission"]["id"],
        agent_id=test_agent.agent_id,
        verdict="accepted",
        notes="Much better! Document is clearly visible.",
    )

    assert approve_result["agent_verdict"] == "accepted"

    # Final release
    final_result = await mock_escrow_manager.release_on_approval(
        task_id=task_id,
        worker_wallet=test_worker.wallet.address,
    )

    assert final_result["success"] is True

    # Verify task completed
    final_task = await mock_supabase.get_task(task_id)
    assert final_task["status"] == "completed"


# ============== TIMEOUT AND EXPIRATION ==============


@pytest.mark.asyncio
async def test_lifecycle_with_timeout_before_assignment(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    sample_task_input: dict,
):
    """
    Test timeout when task expires without being assigned:

    1. Agent publishes task
    2. No worker takes it
    3. Deadline passes
    4. Agent requests refund
    5. Full escrow returned to agent
    """
    # Create task with short deadline (for simulation)
    deadline = datetime.now(timezone.utc) + timedelta(hours=1)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Urgent verification needed",
        instructions="Please verify ASAP",
        category="physical_presence",
        bounty_usd=25.00,
        deadline=deadline,
        evidence_required=["photo_geo"],
    )
    task_id = task["id"]

    # Create escrow with short timeout for test
    escrow = await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("25.00"),
        agent_wallet=test_agent.wallet.address,
        timeout_hours=1,  # Short timeout
    )

    # Verify escrow created
    assert escrow.status == "deposited"
    assert float(escrow.total_amount) == 25.00

    # Simulate timeout by manipulating the escrow timeout
    escrow_record = mock_escrow_manager.get_escrow(task_id)
    escrow_record.timeout_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Update task status to expired
    await mock_supabase.update_task(task_id, {"status": "expired"})

    # Process timeout refund
    refund_result = await mock_escrow_manager.process_timeout_refund(task_id)

    assert refund_result["success"] is True
    assert refund_result["amount_refunded"] == 25.00

    # Verify escrow state
    escrow_state = mock_escrow_manager.get_escrow(task_id)
    assert escrow_state.status == "refunded"
    assert escrow_state.refund_tx is not None


@pytest.mark.asyncio
async def test_lifecycle_with_timeout_after_assignment(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    test_worker: MockWorker,
):
    """
    Test timeout when task expires after assignment but before submission:

    1. Task assigned to worker
    2. Worker doesn't submit before deadline
    3. Partial funds returned to agent
    """
    mock_supabase.register_worker(test_worker)

    # Create and assign task
    deadline = datetime.now(timezone.utc) + timedelta(hours=2)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Time-sensitive task",
        instructions="Must be done within 2 hours",
        category="simple_action",
        bounty_usd=30.00,
        deadline=deadline,
        evidence_required=["photo"],
    )
    task_id = task["id"]

    # Create escrow
    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("30.00"),
        agent_wallet=test_agent.wallet.address,
        timeout_hours=2,
    )

    # Assign worker
    await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    # Simulate timeout
    escrow_record = mock_escrow_manager.get_escrow(task_id)
    escrow_record.timeout_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Mark task as expired
    await mock_supabase.update_task(task_id, {"status": "expired"})

    # Process timeout - full refund since no work submitted
    refund_result = await mock_escrow_manager.process_timeout_refund(task_id)

    assert refund_result["success"] is True
    assert refund_result["amount_refunded"] == 30.00

    final_task = await mock_supabase.get_task(task_id)
    assert final_task["status"] == "expired"


@pytest.mark.asyncio
async def test_lifecycle_with_timeout_after_partial_release(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    test_worker: MockWorker,
    sample_evidence: dict,
):
    """
    Test timeout when task expires after worker submitted (partial released):

    1. Worker submits, gets 30%
    2. Agent doesn't respond before timeout
    3. Worker keeps 30%, agent gets 70% back
    """
    mock_supabase.register_worker(test_worker)

    # Create and assign task
    deadline = datetime.now(timezone.utc) + timedelta(hours=4)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Verification task",
        instructions="Standard verification",
        category="physical_presence",
        bounty_usd=50.00,
        deadline=deadline,
        evidence_required=["photo_geo"],
        evidence_optional=["text_response"],
    )
    task_id = task["id"]

    # Create escrow
    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("50.00"),
        agent_wallet=test_agent.wallet.address,
        timeout_hours=4,
    )

    # Assign and submit
    await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    await mock_supabase.submit_work(
        task_id=task_id,
        executor_id=test_worker.executor_id,
        evidence=sample_evidence,
    )

    # Release partial (30%)
    partial_result = await mock_escrow_manager.release_partial_on_submission(
        task_id=task_id,
        worker_wallet=test_worker.wallet.address,
    )

    # Net bounty = $50 * 0.87 = $43.50
    # Partial = $43.50 * 0.30 = $13.05
    assert partial_result["success"] is True
    assert partial_result["amount_released"] == 13.05

    # Simulate timeout
    escrow_record = mock_escrow_manager.get_escrow(task_id)
    escrow_record.timeout_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Process timeout - partial refund
    refund_result = await mock_escrow_manager.process_timeout_refund(task_id)

    assert refund_result["success"] is True
    assert refund_result["type"] == "timeout_partial_refund"
    assert refund_result["partial_released_to_worker"] == 13.05

    # Remaining goes back to agent: $50 - $13.05 = $36.95
    # (This includes the platform fee since task wasn't completed)
    remaining = Decimal("50.00") - Decimal("13.05")
    assert Decimal(str(refund_result["amount_refunded"])) == remaining.quantize(
        Decimal("0.01")
    )


# ============== DISPUTE HANDLING ==============


@pytest.mark.asyncio
async def test_lifecycle_with_dispute_worker_wins(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    test_worker: MockWorker,
    sample_evidence: dict,
):
    """
    Test dispute lifecycle where worker wins:

    1. Worker submits valid evidence
    2. Agent unfairly disputes
    3. Arbitration finds in worker's favor
    4. Worker receives full payment
    """
    mock_supabase.register_worker(test_worker)

    # Create, assign, and submit task
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Store verification",
        instructions="Verify store is open",
        category="physical_presence",
        bounty_usd=20.00,
        deadline=deadline,
        evidence_required=["photo_geo"],
    )
    task_id = task["id"]

    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("20.00"),
        agent_wallet=test_agent.wallet.address,
    )

    await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    submit_result = await mock_supabase.submit_work(
        task_id=task_id,
        executor_id=test_worker.executor_id,
        evidence=sample_evidence,
    )

    # Release partial
    await mock_escrow_manager.release_partial_on_submission(
        task_id=task_id,
        worker_wallet=test_worker.wallet.address,
    )

    # Agent disputes
    await mock_supabase.update_submission(
        submission_id=submit_result["submission"]["id"],
        agent_id=test_agent.agent_id,
        verdict="disputed",
        notes="Photo doesn't show store hours",
    )

    # Create formal dispute
    dispute = await mock_supabase.create_dispute(
        task_id=task_id,
        submission_id=submit_result["submission"]["id"],
        opened_by="agent",
        opener_id=test_agent.agent_id,
        dispute_type="quality",
        description="Photo doesn't show required information",
    )

    # Lock escrow
    await mock_escrow_manager.handle_dispute(task_id)

    escrow_state = mock_escrow_manager.get_escrow(task_id)
    assert escrow_state.status == "disputed"

    # Arbitration resolves in worker's favor
    resolution = await mock_supabase.resolve_dispute(
        dispute_id=dispute["id"],
        outcome="worker_wins",
        resolution_notes="Photo clearly shows store hours. Worker fulfilled requirements.",
        worker_payout_pct=1.0,
    )

    assert resolution["outcome"] == "worker_wins"

    # Release remaining funds to worker
    release_result = await mock_escrow_manager.resolve_dispute(
        task_id=task_id,
        winner="worker",
        worker_wallet=test_worker.wallet.address,
    )

    assert release_result["success"] is True

    # Worker should receive full net payment
    # $20 * 0.87 = $17.40
    assert release_result["worker_payment"] == 17.40

    # Verify task completed
    final_task = await mock_supabase.get_task(task_id)
    assert final_task["status"] == "completed"


@pytest.mark.asyncio
async def test_lifecycle_with_dispute_agent_wins(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    test_worker: MockWorker,
):
    """
    Test dispute lifecycle where agent wins:

    1. Worker submits fraudulent evidence
    2. Agent disputes
    3. Arbitration finds in agent's favor
    4. Agent receives refund (minus any partial already released)
    """
    mock_supabase.register_worker(test_worker)

    # Create and assign task
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Document delivery verification",
        instructions="Confirm document was delivered to address",
        category="physical_presence",
        bounty_usd=35.00,
        deadline=deadline,
        evidence_required=["photo_geo", "timestamp_proof"],
    )
    task_id = task["id"]

    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("35.00"),
        agent_wallet=test_agent.wallet.address,
    )

    await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    # Worker submits fake evidence (GPS doesn't match)
    fake_evidence = {
        "photo_geo": {
            "url": "ipfs://QmFakePhoto",
            "metadata": {
                "lat": 0.0,  # Wrong location
                "lng": 0.0,
            },
        },
        "timestamp_proof": datetime.now(timezone.utc).isoformat(),
    }

    submit_result = await mock_supabase.submit_work(
        task_id=task_id,
        executor_id=test_worker.executor_id,
        evidence=fake_evidence,
    )

    # No partial release yet - agent immediately disputes

    # Agent disputes
    await mock_supabase.update_submission(
        submission_id=submit_result["submission"]["id"],
        agent_id=test_agent.agent_id,
        verdict="disputed",
        notes="GPS coordinates are 0,0 - clearly fake",
    )

    # Create dispute
    dispute = await mock_supabase.create_dispute(
        task_id=task_id,
        submission_id=submit_result["submission"]["id"],
        opened_by="agent",
        opener_id=test_agent.agent_id,
        dispute_type="fraud",
        description="Worker submitted fake GPS coordinates (0,0)",
    )

    # Lock escrow
    await mock_escrow_manager.handle_dispute(task_id)

    # Arbitration finds for agent
    resolution = await mock_supabase.resolve_dispute(
        dispute_id=dispute["id"],
        outcome="agent_wins",
        resolution_notes="GPS coordinates are clearly fake. Evidence of fraud.",
        worker_payout_pct=0.0,
    )

    assert resolution["outcome"] == "agent_wins"

    # Agent gets full refund
    refund_result = await mock_escrow_manager.resolve_dispute(
        task_id=task_id,
        winner="agent",
    )

    assert refund_result["success"] is True
    assert refund_result["amount_refunded"] == 35.00

    # Verify task cancelled
    final_task = await mock_supabase.get_task(task_id)
    assert final_task["status"] == "cancelled"


@pytest.mark.asyncio
async def test_lifecycle_with_dispute_split_resolution(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    test_worker: MockWorker,
    sample_evidence: dict,
):
    """
    Test dispute with split resolution (partial payment to both parties):

    1. Worker completes task partially
    2. Agent disputes quality
    3. Arbitration awards 50% to worker, 50% to agent
    """
    mock_supabase.register_worker(test_worker)

    # Create and assign task
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Multi-item inventory check",
        instructions="Check inventory of 10 items",
        category="physical_presence",
        bounty_usd=40.00,
        deadline=deadline,
        evidence_required=["photo", "text_response"],
    )
    task_id = task["id"]

    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("40.00"),
        agent_wallet=test_agent.wallet.address,
    )

    await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    # Worker submits partial work (only 5 of 10 items)
    partial_evidence = {
        "photo": "ipfs://QmPartialWork",
        "text_response": "Checked items 1-5. Couldn't access items 6-10.",
    }

    submit_result = await mock_supabase.submit_work(
        task_id=task_id,
        executor_id=test_worker.executor_id,
        evidence=partial_evidence,
    )

    # Partial release
    await mock_escrow_manager.release_partial_on_submission(
        task_id=task_id,
        worker_wallet=test_worker.wallet.address,
    )

    # Agent disputes - wants full refund for incomplete work
    await mock_supabase.update_submission(
        submission_id=submit_result["submission"]["id"],
        agent_id=test_agent.agent_id,
        verdict="disputed",
        notes="Only half the items were checked",
    )

    dispute = await mock_supabase.create_dispute(
        task_id=task_id,
        submission_id=submit_result["submission"]["id"],
        opened_by="agent",
        opener_id=test_agent.agent_id,
        dispute_type="incomplete",
        description="Worker only completed 50% of the work",
    )

    await mock_escrow_manager.handle_dispute(task_id)

    # Arbitration awards 50% to worker (they did half the work)
    resolution = await mock_supabase.resolve_dispute(
        dispute_id=dispute["id"],
        outcome="split",
        resolution_notes="Worker completed 50% of work. Awarding proportional payment.",
        worker_payout_pct=0.5,
    )

    assert resolution["outcome"] == "split"
    assert resolution["worker_payout_pct"] == 0.5

    # For split resolution, worker keeps what was released (partial)
    # and agent gets remaining refund
    # This would require custom handling in production


# ============== EDGE CASES ==============


@pytest.mark.asyncio
async def test_cancel_task_before_assignment(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
):
    """Test cancelling a task before any worker is assigned."""
    # Create task
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Task to cancel",
        instructions="This will be cancelled",
        category="simple_action",
        bounty_usd=10.00,
        deadline=deadline,
        evidence_required=["text_response"],
    )
    task_id = task["id"]

    # Create escrow
    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("10.00"),
        agent_wallet=test_agent.wallet.address,
    )

    # Cancel task
    cancelled_task = await mock_supabase.cancel_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
    )

    assert cancelled_task["status"] == "cancelled"

    # Refund escrow
    refund_result = await mock_escrow_manager.refund_on_cancel(
        task_id=task_id,
        reason="Agent cancelled before assignment",
    )

    assert refund_result["success"] is True
    assert refund_result["amount_refunded"] == 10.00

    # Verify escrow state
    escrow_state = mock_escrow_manager.get_escrow(task_id)
    assert escrow_state.status == "refunded"


@pytest.mark.asyncio
async def test_cannot_cancel_after_assignment(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
    test_worker: MockWorker,
):
    """Test that task cannot be cancelled after worker is assigned."""
    mock_supabase.register_worker(test_worker)

    # Create and assign task
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Assigned task",
        instructions="Worker is already working on this",
        category="simple_action",
        bounty_usd=15.00,
        deadline=deadline,
        evidence_required=["text_response"],
    )
    task_id = task["id"]

    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("15.00"),
        agent_wallet=test_agent.wallet.address,
    )

    await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    # Try to cancel - should fail
    with pytest.raises(ValueError, match="Cannot cancel"):
        await mock_supabase.cancel_task(
            task_id=task_id,
            agent_id=test_agent.agent_id,
        )


@pytest.mark.asyncio
async def test_multiple_workers_apply(
    mock_supabase: MockSupabaseClient,
    mock_escrow_manager: MockEscrowManager,
    test_agent: MockAgent,
):
    """Test multiple workers applying to the same task."""
    # Create multiple workers
    worker1 = MockWorker.create(seed=1, reputation=100)
    worker2 = MockWorker.create(seed=2, reputation=150)
    worker3 = MockWorker.create(seed=3, reputation=80)

    mock_supabase.register_worker(worker1)
    mock_supabase.register_worker(worker2)
    mock_supabase.register_worker(worker3)

    # Create task
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Popular task",
        instructions="Multiple workers want this",
        category="simple_action",
        bounty_usd=50.00,
        deadline=deadline,
        evidence_required=["text_response"],
        min_reputation=50,
    )
    task_id = task["id"]

    await mock_escrow_manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal("50.00"),
        agent_wallet=test_agent.wallet.address,
    )

    # All workers apply
    for worker in [worker1, worker2, worker3]:
        await mock_supabase.apply_to_task(
            task_id=task_id,
            executor_id=worker.executor_id,
            message=f"I can do this! - {worker.display_name}",
        )

    # Agent assigns worker2 (highest reputation)
    result = await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=worker2.executor_id,
        notes="Selected due to high reputation",
    )

    assert result["task"]["executor_id"] == worker2.executor_id

    # Verify other applications are rejected
    for app_id, app in mock_supabase._applications.items():
        if app["task_id"] == task_id:
            if app["executor_id"] == worker2.executor_id:
                assert app["status"] == "accepted"
            else:
                assert app["status"] == "rejected"


@pytest.mark.asyncio
async def test_worker_cannot_submit_unassigned_task(
    mock_supabase: MockSupabaseClient,
    test_agent: MockAgent,
    test_worker: MockWorker,
    sample_evidence: dict,
):
    """Test that a worker cannot submit to a task they're not assigned to."""
    mock_supabase.register_worker(test_worker)

    # Create task but don't assign
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Unassigned task",
        instructions="No one is assigned yet",
        category="simple_action",
        bounty_usd=10.00,
        deadline=deadline,
        evidence_required=["text_response"],
    )

    # Try to submit without being assigned
    with pytest.raises(ValueError, match="not assigned"):
        await mock_supabase.submit_work(
            task_id=task["id"],
            executor_id=test_worker.executor_id,
            evidence=sample_evidence,
        )


@pytest.mark.asyncio
async def test_duplicate_application_rejected(
    mock_supabase: MockSupabaseClient,
    test_agent: MockAgent,
    test_worker: MockWorker,
):
    """Test that a worker cannot apply twice to the same task."""
    mock_supabase.register_worker(test_worker)

    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Test task",
        instructions="Testing duplicate applications",
        category="simple_action",
        bounty_usd=10.00,
        deadline=deadline,
        evidence_required=["text_response"],
    )

    # First application succeeds
    await mock_supabase.apply_to_task(
        task_id=task["id"],
        executor_id=test_worker.executor_id,
        message="First application",
    )

    # Second application fails
    with pytest.raises(ValueError, match="Already applied"):
        await mock_supabase.apply_to_task(
            task_id=task["id"],
            executor_id=test_worker.executor_id,
            message="Duplicate application",
        )


@pytest.mark.asyncio
async def test_missing_required_evidence(
    mock_supabase: MockSupabaseClient,
    test_agent: MockAgent,
    test_worker: MockWorker,
):
    """Test that submission fails if required evidence is missing."""
    mock_supabase.register_worker(test_worker)

    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await mock_supabase.create_task(
        agent_id=test_agent.agent_id,
        title="Multi-evidence task",
        instructions="Requires multiple evidence types",
        category="physical_presence",
        bounty_usd=20.00,
        deadline=deadline,
        evidence_required=["photo_geo", "timestamp_proof", "text_response"],
    )
    task_id = task["id"]

    await mock_supabase.assign_task(
        task_id=task_id,
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    # Submit with missing evidence
    incomplete_evidence = {
        "photo_geo": "ipfs://QmTest",
        # Missing: timestamp_proof, text_response
    }

    with pytest.raises(ValueError, match="Missing required evidence"):
        await mock_supabase.submit_work(
            task_id=task_id,
            executor_id=test_worker.executor_id,
            evidence=incomplete_evidence,
        )
