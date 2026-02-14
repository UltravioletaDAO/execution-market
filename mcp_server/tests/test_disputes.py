"""
Tests for the disputes module (manager, evidence, resolution).

Covers:
- DisputeManager lifecycle (create, respond, resolve, escalate, withdraw)
- Evidence management (attach, verify, remove, limits)
- Resolution logic (refund splits, auto-resolution, recommendations)
- Edge cases (invalid states, non-party responses, limits)
"""

import hashlib
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.dormant

from mcp_server.disputes.models import (
    Dispute,
    DisputeStatus,
    DisputeReason,
    DisputeParty,
    DisputeResponse,
    DisputeEvidence,
    ResolutionType,
    DisputeConfig,
)
from mcp_server.disputes.manager import (
    DisputeManager,
    DisputeError,
    DisputeNotFoundError,
    InvalidDisputeStateError,
    reset_manager as reset_dispute_manager,
)
from mcp_server.disputes.evidence import (
    EvidenceManager,
    EvidenceError,
    EvidenceNotFoundError,
    EvidenceIntegrityError,
    reset_manager as reset_evidence_manager,
)
from mcp_server.disputes.resolution import (
    calculate_refund_split,
    determine_auto_resolution,
    get_resolution_recommendations,
)


# ─── Helpers ───


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset module singletons between tests."""
    reset_dispute_manager()
    reset_evidence_manager()
    yield


@pytest.fixture
def manager():
    return DisputeManager()


@pytest.fixture
def evidence_mgr():
    return EvidenceManager(max_per_party=5, max_file_size_mb=10)


async def _create_basic_dispute(mgr, **overrides):
    """Create a basic dispute with sensible defaults."""
    defaults = dict(
        task_id="task_001",
        initiator_id="worker_001",
        initiator_party=DisputeParty.WORKER,
        respondent_id="agent_001",
        reason=DisputeReason.QUALITY,
        description="Work quality does not match requirements.",
        amount=Decimal("50.00"),
    )
    defaults.update(overrides)
    return await mgr.create_dispute(**defaults)


def _make_dispute(**kw):
    """Create a minimal Dispute for resolution tests."""
    defaults = dict(
        id="disp_test",
        task_id="t1",
        submission_id=None,
        escrow_id=None,
        initiator_id="w1",
        initiator_party=DisputeParty.WORKER,
        respondent_id="a1",
        respondent_party=DisputeParty.AGENT,
        reason=DisputeReason.QUALITY,
        description="test",
        amount_disputed=Decimal("100.00"),
    )
    defaults.update(kw)
    return Dispute(**defaults)


# ═══════════════════════════════════════════════════════════
# DisputeManager — Creation
# ═══════════════════════════════════════════════════════════


class TestDisputeCreation:
    """Tests for creating disputes."""

    @pytest.mark.asyncio
    async def test_create_dispute_basic(self, manager):
        d = await _create_basic_dispute(manager)
        assert d.id.startswith("disp_")
        assert d.status == DisputeStatus.OPEN
        assert d.task_id == "task_001"
        assert d.initiator_party == DisputeParty.WORKER
        assert d.respondent_party == DisputeParty.AGENT
        assert d.amount_disputed == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_create_dispute_with_evidence(self, manager):
        d = await _create_basic_dispute(
            manager,
            evidence=[
                {"file_url": "s3://proof.jpg", "description": "Screenshot"},
                {"file_url": "s3://receipt.pdf", "file_type": "application/pdf"},
            ],
        )
        assert len(d.evidence) == 2
        assert d.evidence[0].party == DisputeParty.WORKER

    @pytest.mark.asyncio
    async def test_create_dispute_indexes_by_task(self, manager):
        await _create_basic_dispute(manager, task_id="task_aaa")
        await _create_basic_dispute(manager, task_id="task_aaa")
        disputes = manager.get_disputes_by_task("task_aaa")
        assert len(disputes) == 2

    @pytest.mark.asyncio
    async def test_create_dispute_indexes_by_party(self, manager):
        await _create_basic_dispute(manager, initiator_id="w1", respondent_id="a1")
        await _create_basic_dispute(manager, initiator_id="w2", respondent_id="a1")
        party_disputes = manager.get_disputes_by_party("a1")
        assert len(party_disputes) == 2

    @pytest.mark.asyncio
    async def test_create_dispute_description_too_long(self):
        cfg = DisputeConfig(max_response_length=10)
        mgr = DisputeManager(config=cfg)
        with pytest.raises(DisputeError, match="maximum length"):
            await _create_basic_dispute(mgr, description="x" * 20)

    @pytest.mark.asyncio
    async def test_create_dispute_agent_initiator(self, manager):
        d = await _create_basic_dispute(
            manager,
            initiator_party=DisputeParty.AGENT,
        )
        assert d.initiator_party == DisputeParty.AGENT
        assert d.respondent_party == DisputeParty.WORKER

    @pytest.mark.asyncio
    async def test_create_dispute_with_escrow_lock(self):
        mock_escrow = AsyncMock()
        mgr = DisputeManager(escrow_manager=mock_escrow)
        await _create_basic_dispute(mgr, escrow_id="escrow_123")
        mock_escrow.handle_dispute.assert_called_once()


# ═══════════════════════════════════════════════════════════
# DisputeManager — Response
# ═══════════════════════════════════════════════════════════


class TestDisputeResponse:
    """Tests for responding to disputes."""

    @pytest.mark.asyncio
    async def test_add_response_from_respondent(self, manager):
        d = await _create_basic_dispute(manager)
        d = await manager.add_response(d.id, "agent_001", "We disagree.")
        assert len(d.responses) == 1
        assert d.responses[0].responder_party == DisputeParty.AGENT

    @pytest.mark.asyncio
    async def test_add_response_with_evidence(self, manager):
        d = await _create_basic_dispute(manager)
        d = await manager.add_response(
            d.id,
            "agent_001",
            "Here is proof.",
            evidence=[{"file_url": "s3://rebuttal.jpg"}],
        )
        assert len(d.evidence) == 1

    @pytest.mark.asyncio
    async def test_both_respond_transitions_to_review(self, manager):
        d = await _create_basic_dispute(manager)
        await manager.add_response(d.id, "worker_001", "My side.")
        d = await manager.add_response(d.id, "agent_001", "My side.")
        assert d.status == DisputeStatus.UNDER_REVIEW

    @pytest.mark.asyncio
    async def test_respond_non_party_rejected(self, manager):
        d = await _create_basic_dispute(manager)
        with pytest.raises(DisputeError, match="not a party"):
            await manager.add_response(d.id, "stranger", "I want in.")

    @pytest.mark.asyncio
    async def test_respond_to_resolved_dispute_rejected(self, manager):
        d = await _create_basic_dispute(manager)
        await manager.resolve_dispute(d.id, DisputeParty.WORKER, "Worker wins")
        with pytest.raises(InvalidDisputeStateError):
            await manager.add_response(d.id, "agent_001", "Too late.")

    @pytest.mark.asyncio
    async def test_response_message_too_long(self):
        cfg = DisputeConfig(max_response_length=5)
        mgr = DisputeManager(config=cfg)
        d = await _create_basic_dispute(mgr, description="ok")
        with pytest.raises(DisputeError, match="maximum length"):
            await mgr.add_response(d.id, "agent_001", "x" * 10)

    @pytest.mark.asyncio
    async def test_evidence_limit_per_party(self):
        cfg = DisputeConfig(max_evidence_per_party=2)
        mgr = DisputeManager(config=cfg)
        d = await _create_basic_dispute(mgr)
        await mgr.add_response(
            d.id,
            "agent_001",
            "ev1",
            evidence=[
                {"file_url": "a.jpg"},
                {"file_url": "b.jpg"},
            ],
        )
        with pytest.raises(DisputeError, match="Evidence limit"):
            await mgr.add_response(
                d.id,
                "agent_001",
                "ev2",
                evidence=[
                    {"file_url": "c.jpg"},
                ],
            )


# ═══════════════════════════════════════════════════════════
# DisputeManager — Resolution, Escalation, Withdrawal
# ═══════════════════════════════════════════════════════════


class TestDisputeResolution:
    """Tests for resolving/escalating/withdrawing disputes."""

    @pytest.mark.asyncio
    async def test_resolve_full_worker(self, manager):
        d = await _create_basic_dispute(manager)
        d = await manager.resolve_dispute(d.id, DisputeParty.WORKER, "Worker wins", 1.0)
        assert d.status == DisputeStatus.RESOLVED
        assert d.resolution.resolution_type == ResolutionType.FULL_WORKER

    @pytest.mark.asyncio
    async def test_resolve_full_agent(self, manager):
        d = await _create_basic_dispute(manager)
        d = await manager.resolve_dispute(d.id, DisputeParty.AGENT, "Agent wins", 0.0)
        assert d.resolution.resolution_type == ResolutionType.FULL_AGENT

    @pytest.mark.asyncio
    async def test_resolve_split(self, manager):
        d = await _create_basic_dispute(manager)
        d = await manager.resolve_dispute(d.id, DisputeParty.WORKER, "Shared", 0.6)
        assert d.resolution.resolution_type == ResolutionType.SPLIT

    @pytest.mark.asyncio
    async def test_resolve_dismissed(self, manager):
        d = await _create_basic_dispute(manager)
        d = await manager.resolve_dispute(d.id, None, "No merit")
        assert d.resolution.resolution_type == ResolutionType.DISMISSED

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_fails(self, manager):
        d = await _create_basic_dispute(manager)
        await manager.resolve_dispute(d.id, None, "Done")
        with pytest.raises(InvalidDisputeStateError):
            await manager.resolve_dispute(d.id, None, "Again")

    @pytest.mark.asyncio
    async def test_escalate_from_open(self, manager):
        d = await _create_basic_dispute(manager)
        d = await manager.escalate_dispute(d.id, "Complex case")
        assert d.status == DisputeStatus.ESCALATED
        assert d.metadata["escalation_reason"] == "Complex case"

    @pytest.mark.asyncio
    async def test_escalate_from_under_review(self, manager):
        d = await _create_basic_dispute(manager)
        await manager.add_response(d.id, "worker_001", "ok")
        await manager.add_response(d.id, "agent_001", "ok")
        d = await manager.escalate_dispute(d.id)
        assert d.status == DisputeStatus.ESCALATED

    @pytest.mark.asyncio
    async def test_escalate_resolved_fails(self, manager):
        d = await _create_basic_dispute(manager)
        await manager.resolve_dispute(d.id, None, "Done")
        with pytest.raises(InvalidDisputeStateError):
            await manager.escalate_dispute(d.id)

    @pytest.mark.asyncio
    async def test_withdraw_by_initiator(self, manager):
        d = await _create_basic_dispute(manager)
        d = await manager.withdraw_dispute(d.id, "worker_001", "Changed my mind")
        assert d.status == DisputeStatus.WITHDRAWN
        assert d.metadata["withdrawal_reason"] == "Changed my mind"

    @pytest.mark.asyncio
    async def test_withdraw_by_non_initiator_fails(self, manager):
        d = await _create_basic_dispute(manager)
        with pytest.raises(DisputeError, match="Only the initiator"):
            await manager.withdraw_dispute(d.id, "agent_001", "nope")

    @pytest.mark.asyncio
    async def test_withdraw_resolved_fails(self, manager):
        d = await _create_basic_dispute(manager)
        await manager.resolve_dispute(d.id, None, "done")
        with pytest.raises(InvalidDisputeStateError):
            await manager.withdraw_dispute(d.id, "worker_001", "late")


# ═══════════════════════════════════════════════════════════
# DisputeManager — Queries & Statistics
# ═══════════════════════════════════════════════════════════


class TestDisputeQueries:
    """Tests for dispute queries and statistics."""

    def test_get_dispute_not_found(self, manager):
        assert manager.get_dispute("nonexistent") is None

    def test_get_dispute_not_found_raises(self, manager):
        with pytest.raises(DisputeNotFoundError):
            manager._get_dispute("nonexistent")

    @pytest.mark.asyncio
    async def test_get_open_disputes(self, manager):
        await _create_basic_dispute(manager, task_id="t1")
        await _create_basic_dispute(manager, task_id="t2")
        d3 = await _create_basic_dispute(manager, task_id="t3")
        await manager.resolve_dispute(d3.id, None, "Done")
        assert len(manager.get_open_disputes()) == 2

    def test_statistics_empty(self, manager):
        stats = manager.get_statistics()
        assert stats["total"] == 0
        assert stats["open"] == 0

    @pytest.mark.asyncio
    async def test_statistics_comprehensive(self, manager):
        d1 = await _create_basic_dispute(manager, task_id="t1")
        await _create_basic_dispute(manager, task_id="t2", reason=DisputeReason.FRAUD)
        await manager.resolve_dispute(d1.id, DisputeParty.WORKER, "Worker wins")
        stats = manager.get_statistics()
        assert stats["total"] == 2
        assert stats["open"] == 1
        assert stats["resolved"] == 1
        assert stats["outcomes"]["worker_wins"] == 1
        assert stats["by_reason"]["quality"] == 1
        assert stats["by_reason"]["fraud"] == 1


# ═══════════════════════════════════════════════════════════
# Evidence Manager
# ═══════════════════════════════════════════════════════════


class TestEvidenceManager:
    """Tests for evidence attachment and verification."""

    @pytest.mark.asyncio
    async def test_attach_evidence_basic(self, evidence_mgr):
        ev = await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="s3://photo.jpg",
            file_type="image/jpeg",
            description="Photo of work done",
        )
        assert ev.id.startswith("ev_")
        assert ev.party == DisputeParty.WORKER

    @pytest.mark.asyncio
    async def test_attach_with_hash(self, evidence_mgr):
        content = b"fake image data"
        ev = await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="s3://photo.jpg",
            file_type="image/jpeg",
            description="test",
            file_content=content,
        )
        assert ev.hash == hashlib.sha256(content).hexdigest()
        assert ev.verified is True

    @pytest.mark.asyncio
    async def test_attach_invalid_type(self, evidence_mgr):
        with pytest.raises(EvidenceError, match="not allowed"):
            await evidence_mgr.attach_evidence(
                dispute_id="d1",
                submitter_id="w1",
                party=DisputeParty.WORKER,
                file_url="s3://x.exe",
                file_type="application/x-executable",
                description="bad file",
            )

    @pytest.mark.asyncio
    async def test_attach_file_too_large(self):
        mgr = EvidenceManager(max_file_size_mb=1)
        huge = b"x" * (2 * 1024 * 1024)  # 2MB
        with pytest.raises(EvidenceError, match="exceeds"):
            await mgr.attach_evidence(
                dispute_id="d1",
                submitter_id="w1",
                party=DisputeParty.WORKER,
                file_url="s3://big.jpg",
                file_type="image/jpeg",
                description="too big",
                file_content=huge,
            )

    @pytest.mark.asyncio
    async def test_verify_integrity_pass(self, evidence_mgr):
        content = b"original data"
        ev = await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="s3://x.jpg",
            file_type="image/jpeg",
            description="t",
            file_content=content,
        )
        result = await evidence_mgr.verify_evidence_integrity(ev.id, content)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_integrity_fail(self, evidence_mgr):
        ev = await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="s3://x.jpg",
            file_type="image/jpeg",
            description="t",
            file_content=b"original",
        )
        result = await evidence_mgr.verify_evidence_integrity(ev.id, b"tampered")
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_no_hash_raises(self, evidence_mgr):
        ev = await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="s3://x.jpg",
            file_type="image/jpeg",
            description="no hash provided",
        )
        with pytest.raises(EvidenceIntegrityError):
            await evidence_mgr.verify_evidence_integrity(ev.id, b"data")

    @pytest.mark.asyncio
    async def test_verify_not_found(self, evidence_mgr):
        with pytest.raises(EvidenceNotFoundError):
            await evidence_mgr.verify_evidence_integrity("ev_fake", b"data")

    def test_remove_evidence(self, evidence_mgr):
        # Use sync method directly
        assert evidence_mgr.remove_evidence("ev_nope") is False

    @pytest.mark.asyncio
    async def test_remove_evidence_exists(self, evidence_mgr):
        ev = await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="s3://x.jpg",
            file_type="image/jpeg",
            description="t",
        )
        assert evidence_mgr.remove_evidence(ev.id) is True
        assert evidence_mgr.get_evidence(ev.id) is None

    @pytest.mark.asyncio
    async def test_get_by_dispute(self, evidence_mgr):
        await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="a.jpg",
            file_type="image/jpeg",
            description="a",
        )
        await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="a1",
            party=DisputeParty.AGENT,
            file_url="b.jpg",
            file_type="image/jpeg",
            description="b",
        )
        assert len(evidence_mgr.get_evidence_by_dispute("d1")) == 2

    @pytest.mark.asyncio
    async def test_get_by_party(self, evidence_mgr):
        await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="a.jpg",
            file_type="image/jpeg",
            description="a",
        )
        await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="a1",
            party=DisputeParty.AGENT,
            file_url="b.jpg",
            file_type="image/jpeg",
            description="b",
        )
        worker_ev = evidence_mgr.get_evidence_by_party("d1", DisputeParty.WORKER)
        assert len(worker_ev) == 1

    @pytest.mark.asyncio
    async def test_statistics(self, evidence_mgr):
        await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="a.jpg",
            file_type="image/jpeg",
            description="a",
            file_content=b"data",
        )
        await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="a1",
            party=DisputeParty.AGENT,
            file_url="b.pdf",
            file_type="application/pdf",
            description="b",
        )
        stats = evidence_mgr.get_statistics("d1")
        assert stats["total"] == 2
        assert stats["by_party"]["worker"] == 1
        assert stats["verified"] == 1
        assert "image/jpeg" in stats["by_type"]

    @pytest.mark.asyncio
    async def test_update_hash(self, evidence_mgr):
        ev = await evidence_mgr.attach_evidence(
            dispute_id="d1",
            submitter_id="w1",
            party=DisputeParty.WORKER,
            file_url="a.jpg",
            file_type="image/jpeg",
            description="a",
        )
        assert ev.hash is None
        updated = await evidence_mgr.update_evidence_hash(ev.id, b"new content")
        assert updated.hash is not None
        assert updated.verified is True


# ═══════════════════════════════════════════════════════════
# Resolution Logic
# ═══════════════════════════════════════════════════════════


class TestResolutionLogic:
    """Tests for refund split calculation and auto-resolution."""

    def test_explicit_split(self):
        d = _make_dispute()
        result = calculate_refund_split(d, worker_payout_pct=0.7)
        assert result["worker_pct"] == 0.7
        assert result["agent_pct"] == pytest.approx(0.3)
        assert result["worker_amount"] == pytest.approx(70.0)
        assert result["calculation_details"]["method"] == "explicit"

    def test_calculated_split_50_50_no_evidence(self):
        d = _make_dispute()
        result = calculate_refund_split(d)
        assert result["worker_pct"] == pytest.approx(0.5, abs=0.15)

    def test_evidence_affects_split(self):
        d = _make_dispute()
        for i in range(3):
            d.evidence.append(
                DisputeEvidence(
                    id=f"ev_{i}",
                    dispute_id="disp_test",
                    submitted_by="w1",
                    party=DisputeParty.WORKER,
                    file_url=f"f{i}.jpg",
                    file_type="image/jpeg",
                    description="proof",
                )
            )
        result = calculate_refund_split(d)
        assert result["worker_pct"] > 0.5

    def test_non_responsive_party_penalized(self):
        d = _make_dispute()
        d.responses.append(
            DisputeResponse(
                id="r1",
                dispute_id="disp_test",
                responder_id="w1",
                responder_party=DisputeParty.WORKER,
                message="I responded",
            )
        )
        result = calculate_refund_split(d)
        assert result["worker_pct"] > 0.5

    def test_auto_resolve_small_dispute(self):
        d = _make_dispute(amount_disputed=Decimal("5.00"))
        for i in range(3):
            d.evidence.append(
                DisputeEvidence(
                    id=f"ev_{i}",
                    dispute_id="disp_test",
                    submitted_by="w1",
                    party=DisputeParty.WORKER,
                    file_url=f"f{i}.jpg",
                    file_type="image/jpeg",
                    description="proof",
                )
            )
        result = determine_auto_resolution(d)
        assert result is not None
        assert result["can_auto_resolve"] is True

    def test_auto_resolve_non_responsive_respondent(self):
        d = _make_dispute(initiator_party=DisputeParty.WORKER)
        d.responses.append(
            DisputeResponse(
                id="r1",
                dispute_id="disp_test",
                responder_id="w1",
                responder_party=DisputeParty.WORKER,
                message="help",
            )
        )
        result = determine_auto_resolution(d)
        assert result is not None
        assert result["winner"] == DisputeParty.WORKER

    def test_auto_resolve_large_dispute_no_evidence_no_responses(self):
        """Large dispute with no evidence and no responses → no auto-resolve."""
        d = _make_dispute(amount_disputed=Decimal("500.00"))
        # Both parties responded → no non-response auto-resolve path
        d.responses.append(
            DisputeResponse(
                id="r1",
                dispute_id="disp_test",
                responder_id="w1",
                responder_party=DisputeParty.WORKER,
                message="help",
            )
        )
        d.responses.append(
            DisputeResponse(
                id="r2",
                dispute_id="disp_test",
                responder_id="a1",
                responder_party=DisputeParty.AGENT,
                message="nope",
            )
        )
        result = determine_auto_resolution(d)
        assert result is None

    def test_recommendations_include_escalate_for_high_value(self):
        d = _make_dispute(amount_disputed=Decimal("200.00"))
        recs = get_resolution_recommendations(d)
        actions = [r["action"] for r in recs]
        assert "escalate" in actions

    def test_recommendations_sorted_by_confidence(self):
        d = _make_dispute(amount_disputed=Decimal("5.00"))
        recs = get_resolution_recommendations(d)
        confidences = [r["confidence"] for r in recs]
        assert confidences == sorted(confidences, reverse=True)
