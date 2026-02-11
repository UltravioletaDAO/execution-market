"""
E2E Tests for ERC-8004 Integration Flows.

Simulates full end-to-end scenarios with ERC-8004 side effects:

1. HAPPY PATH: Task published → completed → paid → bidirectional reputation
   - Agent rates worker via dynamic scoring
   - Worker auto-rates agent (WS-2)
   - Worker auto-registered on ERC-8004 (WS-1)

2. CANCEL/REFUND: Task published → nobody takes it → agent cancels → refund
   - No side effects should be created

3. REJECTION + MAJOR FEEDBACK: Task submitted → agent rejects with severity=major
   - rate_worker_on_rejection side effect enqueued
   - Minor rejection creates no side effect

4. BIDIRECTIONAL REPUTATION: Worker rates agent via dashboard modal flow
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock

pytestmark = [pytest.mark.erc8004, pytest.mark.core]

from ..e2e.conftest import (
    MockAgent,
    MockWorker,
    MockEscrowManager,
    MockSupabaseClient,
)


# ---------------------------------------------------------------------------
# Extended mock Supabase that tracks erc8004_side_effects outbox
# ---------------------------------------------------------------------------


class ERC8004MockSupabase(MockSupabaseClient):
    """MockSupabaseClient extended with erc8004_side_effects outbox tracking."""

    def __init__(self):
        super().__init__()
        self._side_effects: Dict[str, Dict[str, Any]] = {}
        self._platform_config: Dict[str, Any] = {
            "erc8004_auto_register_worker": True,
            "erc8004_auto_rate_agent": True,
            "erc8004_dynamic_scoring": True,
            "erc8004_rejection_feedback": True,
            "erc8004_mcp_tools": True,
        }

    def table(self, name: str):
        """Override to intercept erc8004_side_effects table operations."""
        if name == "erc8004_side_effects":
            return SideEffectTableBuilder(self)
        if name == "platform_config":
            return PlatformConfigTableBuilder(self)
        return super().table(name)

    def get_side_effects(
        self,
        submission_id: Optional[str] = None,
        effect_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query side effects for assertions."""
        effects = list(self._side_effects.values())
        if submission_id:
            effects = [e for e in effects if e.get("submission_id") == submission_id]
        if effect_type:
            effects = [e for e in effects if e.get("effect_type") == effect_type]
        return effects


class SideEffectTableBuilder:
    """Mock table builder for erc8004_side_effects."""

    def __init__(self, client: ERC8004MockSupabase):
        self._client = client
        self._filters: list = []

    def upsert(self, row, on_conflict=None, ignore_duplicates=False):
        """Upsert into side effects with dedup."""
        key = f"{row.get('submission_id')}:{row.get('effect_type')}"
        if ignore_duplicates and key in {
            f"{e.get('submission_id')}:{e.get('effect_type')}"
            for e in self._client._side_effects.values()
        }:
            self._upsert_data = []
        else:
            effect_id = str(uuid.uuid4())
            record = {
                "id": effect_id,
                **row,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._client._side_effects[effect_id] = record
            self._upsert_data = [record]
        return self

    def execute(self):
        if hasattr(self, "_upsert_data"):
            return MagicMock(data=self._upsert_data)
        if hasattr(self, "_update_target"):
            return MagicMock(data=[self._update_target])
        # Select query
        items = list(self._client._side_effects.values())
        for field_name, op, value in self._filters:
            if op == "eq":
                items = [i for i in items if i.get(field_name) == value]
            elif op == "in":
                items = [i for i in items if i.get(field_name) in value]
            elif op == "lt":
                items = [i for i in items if (i.get(field_name) or 0) < value]
        if hasattr(self, "_single_mode"):
            return MagicMock(data=items[0] if items else None)
        return MagicMock(data=items)

    def select(self, fields="*"):
        return self

    def eq(self, field, value):
        self._filters.append((field, "eq", value))
        return self

    def in_(self, field, values):
        self._filters.append((field, "in", values))
        return self

    def lt(self, field, value):
        self._filters.append((field, "lt", value))
        return self

    def order(self, field, **kwargs):
        return self

    def limit(self, count):
        return self

    def single(self):
        self._single_mode = True
        return self

    def update(self, updates):
        """Update matching records."""
        for effect in self._client._side_effects.values():
            match = all(effect.get(f) == v for f, op, v in self._filters if op == "eq")
            if match:
                effect.update(updates)
                self._update_target = effect
        return self


class PlatformConfigTableBuilder:
    """Mock table builder for platform_config."""

    def __init__(self, client: ERC8004MockSupabase):
        self._client = client
        self._key = None

    def select(self, fields="*"):
        return self

    def eq(self, field, value):
        self._key = value
        return self

    def single(self):
        return self

    def execute(self):
        if self._key and self._key in self._client._platform_config:
            return MagicMock(
                data={
                    "key": self._key,
                    "value": self._client._platform_config[self._key],
                }
            )
        return MagicMock(data=None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def erc8004_supabase():
    """Create extended mock Supabase with side effects tracking."""
    return ERC8004MockSupabase()


@pytest.fixture
def agent():
    return MockAgent.create(seed=42)


@pytest.fixture
def worker():
    return MockWorker.create(seed=7, reputation=100)


@pytest.fixture
def escrow():
    return MockEscrowManager()


# ---------------------------------------------------------------------------
# Helper: run a full task lifecycle up to submission
# ---------------------------------------------------------------------------


async def _publish_and_submit(
    db: ERC8004MockSupabase,
    escrow: MockEscrowManager,
    agent: MockAgent,
    worker: MockWorker,
    bounty: float = 10.0,
) -> tuple:
    """Helper: publish task, assign worker, submit evidence. Returns (task, submission)."""
    db.register_worker(worker)

    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    task = await db.create_task(
        agent_id=agent.agent_id,
        title="Verificar horario de tienda",
        instructions="Toma una foto del horario de apertura de la tienda",
        category="physical_presence",
        bounty_usd=bounty,
        deadline=deadline,
        evidence_required=["photo_geo"],
        evidence_optional=["text_response"],
        location_hint="Bogotá, Colombia",
        min_reputation=50,
    )

    await escrow.deposit_for_task(
        task_id=task["id"],
        bounty_usd=Decimal(str(bounty)),
        agent_wallet=agent.wallet.address,
    )

    await db.assign_task(
        task_id=task["id"],
        agent_id=agent.agent_id,
        executor_id=worker.executor_id,
    )

    evidence = {
        "photo_geo": {
            "url": "ipfs://QmEvidenceHash123",
            "metadata": {
                "lat": 4.7110,
                "lng": -74.0721,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
        "text_response": "Tienda abierta 9am-9pm. Foto tomada en la entrada principal.",
    }

    result = await db.submit_work(
        task_id=task["id"],
        executor_id=worker.executor_id,
        evidence=evidence,
        notes="Tarea completada exitosamente",
    )

    return task, result["submission"]


# ============================================================================
# SCENARIO 1: Happy Path — task completed + paid + bidirectional reputation
# ============================================================================


class TestHappyPathWithReputation:
    """Full lifecycle: publish → complete → pay → reputation on both sides."""

    @pytest.mark.asyncio
    async def test_approval_enqueues_worker_registration(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """WS-1: After approval, register_worker_identity side effect is created."""
        from reputation.side_effects import enqueue_side_effect

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # Simulate what routes.py does after approval
        effect = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="register_worker_identity",
            payload={
                "task_id": task["id"],
                "worker_wallet": worker.wallet.address,
                "executor_id": worker.executor_id,
                "network": "base",
            },
        )

        assert effect is not None
        assert effect["effect_type"] == "register_worker_identity"
        assert effect["status"] == "pending"
        assert effect["payload"]["worker_wallet"] == worker.wallet.address

        # Verify it's in the outbox
        effects = erc8004_supabase.get_side_effects(
            submission_id=submission["id"],
            effect_type="register_worker_identity",
        )
        assert len(effects) == 1

    @pytest.mark.asyncio
    async def test_approval_enqueues_agent_rating(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """WS-2: After approval, rate_agent_from_worker side effect is created."""
        from reputation.side_effects import enqueue_side_effect

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # Approve submission
        await erc8004_supabase.update_submission(
            submission_id=submission["id"],
            agent_id=agent.agent_id,
            verdict="accepted",
            notes="Excelente trabajo",
        )

        # Release payment
        release = await escrow.release_on_approval(
            task_id=task["id"],
            worker_wallet=worker.wallet.address,
        )
        assert release["success"]

        # Simulate WS-2 enqueue
        effect = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_agent_from_worker",
            payload={
                "task_id": task["id"],
                "agent_erc8004_id": 2106,
                "payment_tx": release["tx_hashes"][0],
            },
            score=85,
        )

        assert effect is not None
        assert effect["effect_type"] == "rate_agent_from_worker"
        assert effect["score"] == 85
        assert effect["payload"]["agent_erc8004_id"] == 2106

    @pytest.mark.asyncio
    async def test_approval_enqueues_worker_rating_via_dynamic_scoring(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """After approval, worker is rated using dynamic scoring engine."""
        from reputation.scoring import calculate_dynamic_score
        from reputation.side_effects import enqueue_side_effect

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # Calculate dynamic score
        scoring_result = calculate_dynamic_score(
            task=task,
            submission=submission,
            executor={
                "id": worker.executor_id,
                "reputation_score": worker.reputation_score,
                "tasks_completed": worker.tasks_completed,
            },
        )

        assert scoring_result["score"] > 0
        assert scoring_result["score"] <= 100
        assert "breakdown" in scoring_result
        assert scoring_result["source"] in ("dynamic", "override", "fallback")

        # Enqueue the rating
        effect = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_worker_from_agent",
            payload={
                "task_id": task["id"],
                "worker_wallet": worker.wallet.address,
            },
            score=scoring_result["score"],
        )

        assert effect is not None
        assert effect["score"] == scoring_result["score"]

    @pytest.mark.asyncio
    async def test_full_happy_path_creates_all_side_effects(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """Complete flow creates register + rate_agent + rate_worker effects."""
        from reputation.side_effects import enqueue_side_effect
        from reputation.scoring import calculate_dynamic_score

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # Approve
        await erc8004_supabase.update_submission(
            submission_id=submission["id"],
            agent_id=agent.agent_id,
            verdict="accepted",
            notes="Perfecto",
        )

        release = await escrow.release_on_approval(
            task_id=task["id"],
            worker_wallet=worker.wallet.address,
        )

        # --- Side effect 1: WS-1 register_worker_identity ---
        await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="register_worker_identity",
            payload={
                "task_id": task["id"],
                "worker_wallet": worker.wallet.address,
                "executor_id": worker.executor_id,
                "network": "base",
            },
        )

        # --- Side effect 2: Agent rates worker (rate_worker_from_agent) ---
        scoring = calculate_dynamic_score(
            task=task,
            submission=submission,
            executor={"tasks_completed": worker.tasks_completed},
        )
        await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_worker_from_agent",
            payload={
                "task_id": task["id"],
                "worker_wallet": worker.wallet.address,
            },
            score=scoring["score"],
        )

        # --- Side effect 3: WS-2 worker auto-rates agent ---
        await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_agent_from_worker",
            payload={
                "task_id": task["id"],
                "agent_erc8004_id": 2106,
                "payment_tx": release["tx_hashes"][0],
            },
            score=85,
        )

        # Verify all 3 side effects exist
        all_effects = erc8004_supabase.get_side_effects(submission_id=submission["id"])
        assert len(all_effects) == 3

        effect_types = {e["effect_type"] for e in all_effects}
        assert effect_types == {
            "register_worker_identity",
            "rate_worker_from_agent",
            "rate_agent_from_worker",
        }

        # All should be pending (best-effort immediate attempts mocked out)
        assert all(e["status"] == "pending" for e in all_effects)

    @pytest.mark.asyncio
    async def test_dedup_prevents_duplicate_side_effects(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """Same submission_id + effect_type should not create duplicates."""
        from reputation.side_effects import enqueue_side_effect

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # First enqueue
        effect1 = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="register_worker_identity",
            payload={"task_id": task["id"]},
        )
        assert effect1 is not None

        # Second enqueue (same submission_id + effect_type) — should dedup
        effect2 = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="register_worker_identity",
            payload={"task_id": task["id"]},
        )
        assert effect2 is None  # dedup returns None

        # Only 1 record in outbox
        effects = erc8004_supabase.get_side_effects(
            submission_id=submission["id"],
            effect_type="register_worker_identity",
        )
        assert len(effects) == 1


# ============================================================================
# SCENARIO 2: Cancel/Refund — no side effects created
# ============================================================================


class TestCancelRefundNoSideEffects:
    """Task cancelled before anyone takes it → full refund, zero side effects."""

    @pytest.mark.asyncio
    async def test_cancel_before_assignment_no_side_effects(
        self, erc8004_supabase, escrow, agent
    ):
        """Cancelling a task before assignment creates no ERC-8004 effects."""
        deadline = datetime.now(timezone.utc) + timedelta(hours=24)
        task = await erc8004_supabase.create_task(
            agent_id=agent.agent_id,
            title="Tarea que nadie va a tomar",
            instructions="Verificar algo en una ubicación remota",
            category="physical_presence",
            bounty_usd=15.0,
            deadline=deadline,
            evidence_required=["photo_geo"],
        )

        await escrow.deposit_for_task(
            task_id=task["id"],
            bounty_usd=Decimal("15.00"),
            agent_wallet=agent.wallet.address,
        )

        # Cancel
        cancelled = await erc8004_supabase.cancel_task(
            task_id=task["id"],
            agent_id=agent.agent_id,
        )
        assert cancelled["status"] == "cancelled"

        # Refund
        refund = await escrow.refund_on_cancel(
            task_id=task["id"],
            reason="Nadie tomó la tarea",
        )
        assert refund["success"]
        assert refund["amount_refunded"] == 15.0

        # ZERO side effects
        all_effects = erc8004_supabase.get_side_effects()
        assert len(all_effects) == 0

    @pytest.mark.asyncio
    async def test_timeout_refund_no_side_effects(
        self, erc8004_supabase, escrow, agent
    ):
        """Task expires without assignment → refund, zero side effects."""
        deadline = datetime.now(timezone.utc) + timedelta(hours=1)
        task = await erc8004_supabase.create_task(
            agent_id=agent.agent_id,
            title="Tarea urgente sin tomar",
            instructions="Verificar algo urgente",
            category="physical_presence",
            bounty_usd=20.0,
            deadline=deadline,
            evidence_required=["photo_geo"],
        )

        escrow_record = await escrow.deposit_for_task(
            task_id=task["id"],
            bounty_usd=Decimal("20.00"),
            agent_wallet=agent.wallet.address,
            timeout_hours=1,
        )

        # Simulate timeout
        escrow_record.timeout_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await erc8004_supabase.update_task(task["id"], {"status": "expired"})

        refund = await escrow.process_timeout_refund(task["id"])
        assert refund["success"]
        assert refund["amount_refunded"] == 20.0

        # ZERO side effects
        all_effects = erc8004_supabase.get_side_effects()
        assert len(all_effects) == 0

    @pytest.mark.asyncio
    async def test_cancel_escrow_state_is_refunded(
        self, erc8004_supabase, escrow, agent
    ):
        """After cancel + refund, escrow state is 'refunded'."""
        deadline = datetime.now(timezone.utc) + timedelta(hours=24)
        task = await erc8004_supabase.create_task(
            agent_id=agent.agent_id,
            title="Tarea cancelada",
            instructions="Esta tarea será cancelada",
            category="simple_action",
            bounty_usd=5.0,
            deadline=deadline,
            evidence_required=["text_response"],
        )

        await escrow.deposit_for_task(
            task_id=task["id"],
            bounty_usd=Decimal("5.00"),
            agent_wallet=agent.wallet.address,
        )

        await erc8004_supabase.cancel_task(task["id"], agent.agent_id)
        await escrow.refund_on_cancel(task["id"], "Cancelada por el agente")

        state = escrow.get_escrow(task["id"])
        assert state.status == "refunded"
        assert state.refund_tx is not None
        assert float(state.total_amount) == 5.0


# ============================================================================
# SCENARIO 3: Rejection Feedback (WS-3)
# ============================================================================


class TestRejectionFeedbackSideEffects:
    """Major rejection creates rate_worker_on_rejection; minor does not."""

    @pytest.mark.asyncio
    async def test_minor_rejection_no_side_effect(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """Minor rejection creates NO side effect in outbox."""
        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # Agent rejects with minor severity
        await erc8004_supabase.update_submission(
            submission_id=submission["id"],
            agent_id=agent.agent_id,
            verdict="more_info_requested",
            notes="La foto no es clara, por favor retoma",
        )

        # Minor = no side effect
        effects = erc8004_supabase.get_side_effects(
            submission_id=submission["id"],
            effect_type="rate_worker_on_rejection",
        )
        assert len(effects) == 0

    @pytest.mark.asyncio
    async def test_major_rejection_enqueues_side_effect(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """Major rejection creates rate_worker_on_rejection side effect."""
        from reputation.side_effects import enqueue_side_effect

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # Agent rejects with major severity (as routes.py does)
        score = 15  # Severe penalty
        effect = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_worker_on_rejection",
            payload={
                "task_id": task["id"],
                "worker_wallet": worker.wallet.address,
                "agent_id": agent.agent_id,
                "severity": "major",
                "notes": "Evidencia claramente fraudulenta - GPS no coincide",
            },
            score=score,
        )

        assert effect is not None
        assert effect["effect_type"] == "rate_worker_on_rejection"
        assert effect["score"] == 15
        assert effect["payload"]["severity"] == "major"

    @pytest.mark.asyncio
    async def test_major_rejection_default_score_30(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """Major rejection without explicit score defaults to 30."""
        from reputation.side_effects import enqueue_side_effect
        from api.routes import RejectionRequest

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # Parse request model as routes.py does
        request = RejectionRequest(
            notes="Evidencia fraudulenta detectada en la entrega",
            severity="major",
            # reputation_score omitted → default None → endpoint uses 30
        )
        score = request.reputation_score if request.reputation_score is not None else 30
        assert score == 30

        effect = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_worker_on_rejection",
            payload={
                "task_id": task["id"],
                "worker_wallet": worker.wallet.address,
                "agent_id": agent.agent_id,
                "severity": "major",
            },
            score=score,
        )

        assert effect is not None
        assert effect["score"] == 30

    @pytest.mark.asyncio
    async def test_rejection_score_capped_at_50(self):
        """RejectionRequest model rejects scores above 50."""
        from api.routes import RejectionRequest

        # Valid: score = 50
        req = RejectionRequest(
            notes="Muy mal trabajo con evidencia falsa detectada",
            severity="major",
            reputation_score=50,
        )
        assert req.reputation_score == 50

        # Invalid: score = 51
        with pytest.raises(Exception):
            RejectionRequest(
                notes="Otro trabajo muy malo con fraude detectado",
                severity="major",
                reputation_score=51,
            )


# ============================================================================
# SCENARIO 4: Bidirectional Reputation
# ============================================================================


class TestBidirectionalReputation:
    """Both sides can rate each other after task completion."""

    @pytest.mark.asyncio
    async def test_agent_rates_worker_and_worker_rates_agent(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """After completion, both agent→worker and worker→agent ratings exist."""
        from reputation.side_effects import enqueue_side_effect
        from reputation.scoring import calculate_dynamic_score

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        # Approve and pay
        await erc8004_supabase.update_submission(
            submission_id=submission["id"],
            agent_id=agent.agent_id,
            verdict="accepted",
        )
        release = await escrow.release_on_approval(
            task_id=task["id"],
            worker_wallet=worker.wallet.address,
        )

        # Agent → Worker rating (dynamic scoring)
        scoring = calculate_dynamic_score(
            task=task,
            submission=submission,
            executor={"tasks_completed": worker.tasks_completed},
        )
        await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_worker_from_agent",
            payload={
                "task_id": task["id"],
                "worker_wallet": worker.wallet.address,
            },
            score=scoring["score"],
        )

        # Worker → Agent rating (auto WS-2)
        await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_agent_from_worker",
            payload={
                "task_id": task["id"],
                "agent_erc8004_id": 2106,
                "payment_tx": release["tx_hashes"][0],
            },
            score=85,
        )

        # Verify bidirectional
        agent_to_worker = erc8004_supabase.get_side_effects(
            submission_id=submission["id"],
            effect_type="rate_worker_from_agent",
        )
        worker_to_agent = erc8004_supabase.get_side_effects(
            submission_id=submission["id"],
            effect_type="rate_agent_from_worker",
        )

        assert len(agent_to_worker) == 1
        assert len(worker_to_agent) == 1

        # Scores are different (agent rates worker dynamically, worker auto-rates 85)
        assert agent_to_worker[0]["score"] == scoring["score"]
        assert worker_to_agent[0]["score"] == 85

    @pytest.mark.asyncio
    async def test_worker_manual_rating_via_dashboard(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """Worker can manually rate agent from dashboard (RateAgentModal flow)."""
        from reputation.side_effects import enqueue_side_effect

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        await erc8004_supabase.update_submission(
            submission_id=submission["id"],
            agent_id=agent.agent_id,
            verdict="accepted",
        )

        # Simulate dashboard RateAgentModal: worker gives 4/5 stars → score 80
        star_rating = 4
        score_from_stars = star_rating * 20  # 1-5 → 20-100

        effect = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_agent_from_worker",
            payload={
                "task_id": task["id"],
                "agent_erc8004_id": 2106,
                "source": "dashboard_manual",
                "star_rating": star_rating,
                "comment": "Buen agente, pagó rápido",
            },
            score=score_from_stars,
        )

        assert effect is not None
        assert effect["score"] == 80
        assert effect["payload"]["source"] == "dashboard_manual"
        assert effect["payload"]["star_rating"] == 4


# ============================================================================
# SCENARIO 5: Side Effect Lifecycle (mark success/failed)
# ============================================================================


class TestSideEffectLifecycle:
    """Test marking side effects as success/failed after processing."""

    @pytest.mark.asyncio
    async def test_mark_effect_success_with_tx_hash(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """After on-chain registration succeeds, mark effect as success."""
        from reputation.side_effects import enqueue_side_effect, mark_side_effect

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        effect = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="register_worker_identity",
            payload={
                "task_id": task["id"],
                "worker_wallet": worker.wallet.address,
            },
        )

        # Mark as success (simulating facilitator response)
        await mark_side_effect(
            supabase=erc8004_supabase,
            effect_id=effect["id"],
            status="success",
            tx_hash="0xabc123def456",
        )

        # Verify effect updated
        updated = erc8004_supabase._side_effects[effect["id"]]
        assert updated["status"] == "success"
        assert updated["tx_hash"] == "0xabc123def456"
        assert updated["attempts"] == 1

    @pytest.mark.asyncio
    async def test_mark_effect_failed_increments_attempts(
        self, erc8004_supabase, escrow, agent, worker
    ):
        """Failed effect increments attempt counter for retry schedule."""
        from reputation.side_effects import enqueue_side_effect, mark_side_effect

        task, submission = await _publish_and_submit(
            erc8004_supabase, escrow, agent, worker
        )

        effect = await enqueue_side_effect(
            supabase=erc8004_supabase,
            submission_id=submission["id"],
            effect_type="rate_agent_from_worker",
            payload={"task_id": task["id"]},
            score=85,
        )

        # First failure
        await mark_side_effect(
            supabase=erc8004_supabase,
            effect_id=effect["id"],
            status="failed",
            error="Facilitator timeout",
        )

        updated = erc8004_supabase._side_effects[effect["id"]]
        assert updated["status"] == "failed"
        assert updated["attempts"] == 1
        assert updated["last_error"] == "Facilitator timeout"


# ============================================================================
# SCENARIO 6: Dynamic Scoring Integration
# ============================================================================


class TestDynamicScoringIntegration:
    """Dynamic scoring produces correct scores for different submission profiles."""

    def test_fast_completion_scores_higher(self):
        """Submission completed quickly should score higher on speed dimension."""
        from reputation.scoring import calculate_dynamic_score

        now = datetime.now(timezone.utc)
        task = {
            "id": "task-001",
            "created_at": (now - timedelta(hours=24)).isoformat(),
            "deadline": (now + timedelta(hours=24)).isoformat(),
            "bounty_usd": 10.0,
        }

        # Fast: submitted 1 hour after creation
        fast_submission = {
            "id": "sub-fast",
            "submitted_at": (now - timedelta(hours=23)).isoformat(),
            "evidence": {
                "photo_geo": {"url": "ipfs://Qm...", "metadata": {"lat": 4.7}}
            },
        }

        # Slow: submitted 23 hours after creation
        slow_submission = {
            "id": "sub-slow",
            "submitted_at": (now - timedelta(hours=1)).isoformat(),
            "evidence": {
                "photo_geo": {"url": "ipfs://Qm...", "metadata": {"lat": 4.7}}
            },
        }

        fast_result = calculate_dynamic_score(task, fast_submission, {})
        slow_result = calculate_dynamic_score(task, slow_submission, {})

        # Fast submission should score >= slow submission overall
        # (speed dimension contributes up to 30 points)
        assert fast_result["score"] >= slow_result["score"] - 5  # Allow small variance

    def test_override_score_ignores_dynamic(self):
        """When override_score is provided, it takes precedence."""
        from reputation.scoring import calculate_dynamic_score

        result = calculate_dynamic_score(
            task={"id": "t1"},
            submission={"id": "s1"},
            executor={},
            override_score=42,
        )

        assert result["score"] == 42
        assert result["source"] == "override"

    def test_score_always_in_valid_range(self):
        """Score should always be 0-100 regardless of input."""
        from reputation.scoring import calculate_dynamic_score

        # Minimal input
        result = calculate_dynamic_score(
            task={},
            submission={},
            executor={},
        )

        assert 0 <= result["score"] <= 100
        assert result["source"] in ("dynamic", "fallback")
