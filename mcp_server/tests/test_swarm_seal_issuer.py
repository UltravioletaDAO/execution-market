"""
Tests for SealIssuer — Automated describe-net seal issuance.

Coverage:
- Milestone threshold checking (6 default milestones)
- Category-specific seals (SPECIALIST)
- Cooldown enforcement
- Duplicate prevention
- Dry-run mode
- On-chain callback integration
- State persistence (save/load)
- Batch processing
- Edge cases (zero tasks, perfect scores, boundary values)
- Evidence hash determinism
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Fix import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from swarm.seal_issuer import (
    SealIssuer,
    SealIssuance,
    SealType,
    Quadrant,
    MilestoneThreshold,
    WorkerPerformance,
    DEFAULT_MILESTONES,
)


PLATFORM_WALLET = "0xD3868E1eD738CED6945A574a7c769433BeD5d474"
WORKER_WALLET = "0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def issuer():
    """Basic dry-run issuer."""
    return SealIssuer(platform_wallet=PLATFORM_WALLET, dry_run=True)


@pytest.fixture
def worker_newcomer():
    """Worker who qualifies for NEWCOMER seal."""
    return WorkerPerformance(
        wallet=WORKER_WALLET,
        total_tasks=6,
        successful_tasks=4,
        failed_tasks=2,
        avg_rating=3.0,
    )


@pytest.fixture
def worker_reliable():
    """Worker who qualifies for NEWCOMER + RELIABLE seals."""
    return WorkerPerformance(
        wallet=WORKER_WALLET,
        total_tasks=25,
        successful_tasks=22,
        failed_tasks=3,
        avg_rating=3.8,
    )


@pytest.fixture
def worker_skillful():
    """Worker who qualifies for NEWCOMER + RELIABLE + SKILLFUL."""
    return WorkerPerformance(
        wallet=WORKER_WALLET,
        total_tasks=55,
        successful_tasks=51,
        failed_tasks=4,
        avg_rating=4.2,
    )


@pytest.fixture
def worker_exceptional():
    """Worker who qualifies for all tier seals."""
    return WorkerPerformance(
        wallet=WORKER_WALLET,
        total_tasks=110,
        successful_tasks=106,
        failed_tasks=4,
        avg_rating=4.7,
    )


@pytest.fixture
def worker_zero():
    """Worker with no tasks."""
    return WorkerPerformance(wallet=WORKER_WALLET)


@pytest.fixture
def worker_specialist():
    """Worker with deep category-specific expertise."""
    return WorkerPerformance(
        wallet=WORKER_WALLET,
        total_tasks=30,
        successful_tasks=27,
        failed_tasks=3,
        avg_rating=4.0,
        categories={"physical_verification": 20, "data_collection": 10},
        category_success_rates={"physical_verification": 0.90, "data_collection": 0.70},
    )


# ---------------------------------------------------------------------------
# Test: Milestone Checking
# ---------------------------------------------------------------------------

class TestMilestoneChecking:
    """Test basic milestone threshold evaluation."""

    def test_newcomer_eligible(self, issuer, worker_newcomer):
        """Worker with 6 tasks and 67% success qualifies for NEWCOMER."""
        eligible = issuer.check_milestones(worker_newcomer)
        types = [e.seal_type for e in eligible]
        assert SealType.NEWCOMER in types

    def test_newcomer_not_eligible_few_tasks(self, issuer):
        """Worker with only 3 tasks doesn't qualify."""
        worker = WorkerPerformance(wallet=WORKER_WALLET, total_tasks=3, successful_tasks=3)
        eligible = issuer.check_milestones(worker)
        types = [e.seal_type for e in eligible]
        assert SealType.NEWCOMER not in types

    def test_newcomer_not_eligible_low_success(self, issuer):
        """Worker with 5 tasks but 40% success doesn't qualify."""
        worker = WorkerPerformance(
            wallet=WORKER_WALLET, total_tasks=5, successful_tasks=2, failed_tasks=3
        )
        eligible = issuer.check_milestones(worker)
        types = [e.seal_type for e in eligible]
        assert SealType.NEWCOMER not in types

    def test_reliable_eligible(self, issuer, worker_reliable):
        """Worker with 25 tasks, 88% success, 3.8 rating qualifies for RELIABLE."""
        eligible = issuer.check_milestones(worker_reliable)
        types = [e.seal_type for e in eligible]
        assert SealType.RELIABLE in types
        assert SealType.NEWCOMER in types  # Should also get NEWCOMER

    def test_reliable_not_eligible_low_rating(self, issuer):
        """Worker meets task/success thresholds but rating too low."""
        worker = WorkerPerformance(
            wallet=WORKER_WALLET,
            total_tasks=25,
            successful_tasks=22,
            avg_rating=3.0,  # Below 3.5 threshold
        )
        eligible = issuer.check_milestones(worker)
        types = [e.seal_type for e in eligible]
        assert SealType.RELIABLE not in types

    def test_skillful_eligible(self, issuer, worker_skillful):
        """Worker with 55 tasks, 93% success, 4.2 rating qualifies for SKILLFUL."""
        eligible = issuer.check_milestones(worker_skillful)
        types = [e.seal_type for e in eligible]
        assert SealType.SKILLFUL in types
        assert SealType.RELIABLE in types
        assert SealType.NEWCOMER in types

    def test_exceptional_eligible(self, issuer, worker_exceptional):
        """Worker with 110 tasks, 96% success, 4.7 rating qualifies for all."""
        eligible = issuer.check_milestones(worker_exceptional)
        types = [e.seal_type for e in eligible]
        assert SealType.EXCEPTIONAL in types
        assert SealType.SKILLFUL in types
        assert SealType.RELIABLE in types
        assert SealType.NEWCOMER in types

    def test_zero_tasks_no_seals(self, issuer, worker_zero):
        """Worker with no tasks gets no seals."""
        eligible = issuer.check_milestones(worker_zero)
        assert len(eligible) == 0

    def test_perfect_boundary_values(self, issuer):
        """Test exact boundary values for each threshold."""
        # Exactly at NEWCOMER boundary
        worker = WorkerPerformance(
            wallet=WORKER_WALLET, total_tasks=5, successful_tasks=3, failed_tasks=2
        )
        eligible = issuer.check_milestones(worker)
        types = [e.seal_type for e in eligible]
        assert SealType.NEWCOMER in types  # 3/5 = 0.60, exactly at threshold


class TestSpecialistSeals:
    """Test category-specific seal issuance."""

    def test_specialist_single_category(self, issuer, worker_specialist):
        """Worker qualifies for SPECIALIST in physical_verification only."""
        eligible = issuer.check_milestones(worker_specialist)
        specialist_seals = [e for e in eligible if e.seal_type == SealType.SPECIALIST]
        assert len(specialist_seals) == 1
        assert specialist_seals[0].category == "physical_verification"

    def test_specialist_both_categories(self, issuer):
        """Worker qualifies for SPECIALIST in two categories."""
        worker = WorkerPerformance(
            wallet=WORKER_WALLET,
            total_tasks=40,
            successful_tasks=36,
            categories={"physical_verification": 20, "data_collection": 20},
            category_success_rates={"physical_verification": 0.90, "data_collection": 0.90},
        )
        eligible = issuer.check_milestones(worker)
        specialist_seals = [e for e in eligible if e.seal_type == SealType.SPECIALIST]
        categories = {s.category for s in specialist_seals}
        assert "physical_verification" in categories
        assert "data_collection" in categories

    def test_specialist_not_enough_category_tasks(self, issuer):
        """Worker has enough total tasks but not enough in any category."""
        worker = WorkerPerformance(
            wallet=WORKER_WALLET,
            total_tasks=30,
            successful_tasks=27,
            categories={"a": 5, "b": 5, "c": 5, "d": 5, "e": 5, "f": 5},
            category_success_rates={k: 0.90 for k in "abcdef"},
        )
        eligible = issuer.check_milestones(worker)
        specialist_seals = [e for e in eligible if e.seal_type == SealType.SPECIALIST]
        assert len(specialist_seals) == 0


class TestFastSeal:
    """Test FAST seal based on completion time."""

    def test_fast_eligible(self, issuer):
        """Worker with fast completion times qualifies."""
        worker = WorkerPerformance(
            wallet=WORKER_WALLET,
            total_tasks=12,
            successful_tasks=10,
            avg_completion_time_hours=1.5,
            p20_completion_time_hours=2.0,
        )
        eligible = issuer.check_milestones(worker)
        types = [e.seal_type for e in eligible]
        assert SealType.FAST in types

    def test_fast_not_eligible_slow(self, issuer):
        """Worker with slow completion times doesn't qualify."""
        worker = WorkerPerformance(
            wallet=WORKER_WALLET,
            total_tasks=12,
            successful_tasks=10,
            avg_completion_time_hours=5.0,
            p20_completion_time_hours=2.0,
        )
        eligible = issuer.check_milestones(worker)
        types = [e.seal_type for e in eligible]
        assert SealType.FAST not in types

    def test_fast_no_baseline(self, issuer):
        """Worker with no p20 baseline can't qualify."""
        worker = WorkerPerformance(
            wallet=WORKER_WALLET,
            total_tasks=12,
            successful_tasks=10,
            avg_completion_time_hours=1.5,
            p20_completion_time_hours=0,  # No baseline
        )
        eligible = issuer.check_milestones(worker)
        types = [e.seal_type for e in eligible]
        assert SealType.FAST not in types


# ---------------------------------------------------------------------------
# Test: Duplicate Prevention
# ---------------------------------------------------------------------------

class TestDuplicatePrevention:
    """Test that seals aren't issued twice."""

    def test_no_duplicate_after_issuance(self, issuer, worker_newcomer):
        """Once NEWCOMER is issued, don't issue again."""
        # First check: eligible
        eligible = issuer.check_milestones(worker_newcomer)
        assert any(e.seal_type == SealType.NEWCOMER for e in eligible)

        # Submit the seal
        for e in eligible:
            issuer.submit(e)

        # Second check: no longer eligible
        eligible2 = issuer.check_milestones(worker_newcomer)
        assert not any(e.seal_type == SealType.NEWCOMER for e in eligible2)

    def test_different_seals_independent(self, issuer, worker_reliable):
        """Issuing NEWCOMER doesn't prevent RELIABLE."""
        eligible = issuer.check_milestones(worker_reliable)

        # Submit only NEWCOMER
        for e in eligible:
            if e.seal_type == SealType.NEWCOMER:
                issuer.submit(e)

        # Check again: RELIABLE still eligible, NEWCOMER not
        eligible2 = issuer.check_milestones(worker_reliable)
        types2 = [e.seal_type for e in eligible2]
        assert SealType.RELIABLE in types2
        assert SealType.NEWCOMER not in types2

    def test_specialist_category_independent(self, issuer):
        """SPECIALIST in one category doesn't block another."""
        worker = WorkerPerformance(
            wallet=WORKER_WALLET,
            total_tasks=40,
            successful_tasks=36,
            categories={"photo": 20, "data": 20},
            category_success_rates={"photo": 0.90, "data": 0.90},
        )

        eligible = issuer.check_milestones(worker)
        # Submit only photo SPECIALIST
        for e in eligible:
            if e.seal_type == SealType.SPECIALIST and e.category == "photo":
                issuer.submit(e)

        # Check again: data SPECIALIST still eligible
        eligible2 = issuer.check_milestones(worker)
        data_specialist = [e for e in eligible2 if e.seal_type == SealType.SPECIALIST and e.category == "data"]
        assert len(data_specialist) == 1


# ---------------------------------------------------------------------------
# Test: Cooldown Enforcement
# ---------------------------------------------------------------------------

class TestCooldown:
    """Test cooldown period between same seal type issuances."""

    def test_within_cooldown(self, issuer, worker_newcomer):
        """Recently issued seal can't be re-issued within cooldown."""
        eligible = issuer.check_milestones(worker_newcomer)
        for e in eligible:
            if e.seal_type == SealType.NEWCOMER:
                issuer.submit(e)

        # Within cooldown: should be blocked
        eligible2 = issuer.check_milestones(worker_newcomer)
        assert not any(e.seal_type == SealType.NEWCOMER for e in eligible2)


# ---------------------------------------------------------------------------
# Test: Dry Run & Callbacks
# ---------------------------------------------------------------------------

class TestDryRunAndCallbacks:
    """Test dry-run mode and on-chain callback integration."""

    def test_dry_run_no_callback(self, worker_newcomer):
        """Dry run mode works without callback."""
        issuer = SealIssuer(platform_wallet=PLATFORM_WALLET, dry_run=True)
        results = issuer.process_worker(worker_newcomer)
        assert len(results) > 0
        for r in results:
            assert r.status == "dry_run"
            assert r.tx_hash is None

    def test_callback_returns_hash(self, worker_newcomer):
        """Callback mode returns tx hash."""
        mock_callback = MagicMock(return_value="0xabcdef1234567890")
        issuer = SealIssuer(
            platform_wallet=PLATFORM_WALLET,
            on_issue=mock_callback,
            dry_run=False,
        )
        results = issuer.process_worker(worker_newcomer)
        assert len(results) > 0
        assert mock_callback.called
        for r in results:
            assert r.status == "confirmed"
            assert r.tx_hash == "0xabcdef1234567890"

    def test_callback_returns_none(self, worker_newcomer):
        """Callback returns None (submitted but no hash)."""
        mock_callback = MagicMock(return_value=None)
        issuer = SealIssuer(
            platform_wallet=PLATFORM_WALLET,
            on_issue=mock_callback,
            dry_run=False,
        )
        results = issuer.process_worker(worker_newcomer)
        assert len(results) > 0
        for r in results:
            assert r.status == "submitted_no_hash"

    def test_callback_raises_exception(self, worker_newcomer):
        """Callback exception is caught and recorded."""
        mock_callback = MagicMock(side_effect=RuntimeError("RPC timeout"))
        issuer = SealIssuer(
            platform_wallet=PLATFORM_WALLET,
            on_issue=mock_callback,
            dry_run=False,
        )
        results = issuer.process_worker(worker_newcomer)
        assert len(results) > 0
        for r in results:
            assert r.status == "failed"
            assert "RPC timeout" in r.error

    def test_no_callback_implies_dry_run(self, worker_newcomer):
        """If on_issue is None, automatically dry_run."""
        issuer = SealIssuer(platform_wallet=PLATFORM_WALLET, on_issue=None)
        assert issuer.dry_run is True
        results = issuer.process_worker(worker_newcomer)
        for r in results:
            assert r.status == "dry_run"


# ---------------------------------------------------------------------------
# Test: State Persistence
# ---------------------------------------------------------------------------

class TestStatePersistence:
    """Test saving/loading issuance history."""

    def test_save_and_load(self, worker_newcomer):
        """Issuance history persists across instances."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            state_file = f.name

        try:
            # Issue seals
            issuer1 = SealIssuer(
                platform_wallet=PLATFORM_WALLET,
                dry_run=True,
                state_file=state_file,
            )
            issuer1.process_worker(worker_newcomer)

            # Verify state file exists and has data
            with open(state_file) as f:
                data = json.load(f)
            assert WORKER_WALLET in data["history"]

            # Load in new instance
            issuer2 = SealIssuer(
                platform_wallet=PLATFORM_WALLET,
                dry_run=True,
                state_file=state_file,
            )

            # Previously issued seals should be blocked
            eligible = issuer2.check_milestones(worker_newcomer)
            assert not any(e.seal_type == SealType.NEWCOMER for e in eligible)

        finally:
            os.unlink(state_file)

    def test_missing_state_file(self):
        """Non-existent state file is handled gracefully."""
        issuer = SealIssuer(
            platform_wallet=PLATFORM_WALLET,
            state_file="/tmp/nonexistent_seal_state_12345.json",
        )
        assert len(issuer._history) == 0


# ---------------------------------------------------------------------------
# Test: Batch Processing
# ---------------------------------------------------------------------------

class TestBatchProcessing:
    """Test processing multiple workers at once."""

    def test_batch_multiple_workers(self, issuer):
        """Batch processes multiple workers correctly."""
        workers = [
            WorkerPerformance(
                wallet="0xAAA", total_tasks=6, successful_tasks=4,
            ),
            WorkerPerformance(
                wallet="0xBBB", total_tasks=25, successful_tasks=22, avg_rating=3.8,
            ),
            WorkerPerformance(
                wallet="0xCCC", total_tasks=2, successful_tasks=2,
            ),
        ]
        result = issuer.process_batch(workers)
        assert result["workers_checked"] == 3
        assert result["seals_issued"] >= 2  # At least 0xAAA and 0xBBB get seals
        assert isinstance(result["issuances"], list)

    def test_batch_empty(self, issuer):
        """Empty batch returns zero counts."""
        result = issuer.process_batch([])
        assert result["workers_checked"] == 0
        assert result["seals_issued"] == 0


# ---------------------------------------------------------------------------
# Test: Evidence Hash
# ---------------------------------------------------------------------------

class TestEvidenceHash:
    """Test evidence hash computation."""

    def test_deterministic(self, issuer, worker_newcomer):
        """Same inputs produce same hash."""
        milestone = DEFAULT_MILESTONES[0]
        hash1 = issuer._compute_evidence_hash(worker_newcomer, milestone)
        hash2 = issuer._compute_evidence_hash(worker_newcomer, milestone)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_different_workers_different_hash(self, issuer):
        """Different wallets produce different hashes."""
        milestone = DEFAULT_MILESTONES[0]
        w1 = WorkerPerformance(wallet="0xAAA", total_tasks=6, successful_tasks=4)
        w2 = WorkerPerformance(wallet="0xBBB", total_tasks=6, successful_tasks=4)
        hash1 = issuer._compute_evidence_hash(w1, milestone)
        hash2 = issuer._compute_evidence_hash(w2, milestone)
        assert hash1 != hash2

    def test_category_in_hash(self, issuer, worker_specialist):
        """Category-specific hashes differ from generic ones."""
        milestone = DEFAULT_MILESTONES[0]
        hash_generic = issuer._compute_evidence_hash(worker_specialist, milestone, None)
        hash_photo = issuer._compute_evidence_hash(worker_specialist, milestone, "photo")
        assert hash_generic != hash_photo


# ---------------------------------------------------------------------------
# Test: Issuance Details
# ---------------------------------------------------------------------------

class TestIssuanceDetails:
    """Test issuance record structure."""

    def test_issuance_fields(self, issuer, worker_newcomer):
        """Issuance records have all required fields."""
        eligible = issuer.check_milestones(worker_newcomer)
        assert len(eligible) > 0

        seal = eligible[0]
        assert seal.subject_wallet == WORKER_WALLET
        assert seal.evaluator_wallet == PLATFORM_WALLET
        assert seal.quadrant == Quadrant.A2H
        assert seal.status == "pending"
        assert seal.evidence_hash  # Non-empty
        assert seal.milestone  # Contains description

    def test_issuance_to_dict(self, issuer, worker_newcomer):
        """to_dict produces valid JSON-serializable output."""
        eligible = issuer.check_milestones(worker_newcomer)
        seal = eligible[0]
        d = seal.to_dict()
        assert "seal_type" in d
        assert "subject" in d
        assert "evaluator" in d
        json.dumps(d)  # Must be serializable

    def test_stats_after_processing(self, worker_newcomer):
        """Stats reflect processing activity."""
        issuer = SealIssuer(platform_wallet=PLATFORM_WALLET, dry_run=True)
        issuer.process_worker(worker_newcomer)
        stats = issuer.get_stats()
        assert stats["total_checks"] >= 1
        assert stats["total_issued"] >= 1
        assert stats["unique_wallets"] >= 1
        assert stats["dry_run"] is True

    def test_get_worker_seals(self, worker_newcomer):
        """Can retrieve seals for a specific wallet."""
        issuer = SealIssuer(platform_wallet=PLATFORM_WALLET, dry_run=True)
        issuer.process_worker(worker_newcomer)
        seals = issuer.get_worker_seals(WORKER_WALLET)
        assert len(seals) >= 1
        assert seals[0]["subject"] == WORKER_WALLET

    def test_get_worker_seals_unknown_wallet(self, issuer):
        """Unknown wallet returns empty list."""
        seals = issuer.get_worker_seals("0xUNKNOWN")
        assert seals == []


# ---------------------------------------------------------------------------
# Test: Custom Milestones
# ---------------------------------------------------------------------------

class TestCustomMilestones:
    """Test with custom milestone configurations."""

    def test_custom_thresholds(self):
        """Custom milestones override defaults."""
        custom = [
            MilestoneThreshold(
                seal_type=SealType.NEWCOMER,
                min_tasks=1,
                min_success_rate=0.0,
                description="Ultra-easy newcomer",
            ),
        ]
        issuer = SealIssuer(
            platform_wallet=PLATFORM_WALLET,
            milestones=custom,
            dry_run=True,
        )
        worker = WorkerPerformance(wallet=WORKER_WALLET, total_tasks=1, successful_tasks=1)
        eligible = issuer.check_milestones(worker)
        assert len(eligible) == 1
        assert eligible[0].seal_type == SealType.NEWCOMER

    def test_empty_milestones(self):
        """Empty milestone list means no seals ever issued."""
        issuer = SealIssuer(
            platform_wallet=PLATFORM_WALLET,
            milestones=[],
            dry_run=True,
        )
        worker = WorkerPerformance(
            wallet=WORKER_WALLET, total_tasks=200, successful_tasks=200, avg_rating=5.0
        )
        eligible = issuer.check_milestones(worker)
        assert len(eligible) == 0


# ---------------------------------------------------------------------------
# Test: Default Milestones
# ---------------------------------------------------------------------------

class TestDefaultMilestones:
    """Verify the default milestone configuration."""

    def test_six_defaults(self):
        """There are 6 default milestones."""
        assert len(DEFAULT_MILESTONES) == 6

    def test_progression(self):
        """Milestones have increasing difficulty."""
        tiers = [m for m in DEFAULT_MILESTONES if not m.category_specific and m.seal_type != SealType.FAST]
        for i in range(len(tiers) - 1):
            assert tiers[i].min_tasks <= tiers[i + 1].min_tasks
            assert tiers[i].min_success_rate <= tiers[i + 1].min_success_rate

    def test_all_are_a2h_by_default(self):
        """All defaults use A2H quadrant (agent evaluating human worker)."""
        for m in DEFAULT_MILESTONES:
            assert m.quadrant == Quadrant.A2H


# ---------------------------------------------------------------------------
# Test: Integration with ReputationBridge
# ---------------------------------------------------------------------------

class TestIntegrationPatterns:
    """Test patterns that connect with the broader swarm system."""

    def test_process_after_task_completion_pattern(self, issuer):
        """Simulate the pattern: task completes → check milestones → issue seal."""
        # Simulate worker accumulating tasks over time
        worker = WorkerPerformance(
            wallet=WORKER_WALLET,
            total_tasks=4,
            successful_tasks=3,
        )

        # Not yet eligible
        results = issuer.process_worker(worker)
        newcomer_results = [r for r in results if r.seal_type == SealType.NEWCOMER]
        assert len(newcomer_results) == 0

        # Complete one more task → crosses threshold
        worker.total_tasks = 5
        worker.successful_tasks = 3
        results = issuer.process_worker(worker)
        newcomer_results = [r for r in results if r.seal_type == SealType.NEWCOMER]
        assert len(newcomer_results) == 1
        assert newcomer_results[0].status == "dry_run"

    def test_worker_performance_success_rate(self):
        """WorkerPerformance.success_rate computes correctly."""
        w = WorkerPerformance(wallet="0x1", total_tasks=10, successful_tasks=9)
        assert w.success_rate == 0.9

        w0 = WorkerPerformance(wallet="0x2", total_tasks=0)
        assert w0.success_rate == 0.0

    def test_worker_performance_is_fast(self):
        """WorkerPerformance.is_fast works correctly."""
        fast = WorkerPerformance(
            wallet="0x1",
            avg_completion_time_hours=1.0,
            p20_completion_time_hours=2.0,
        )
        assert fast.is_fast is True

        slow = WorkerPerformance(
            wallet="0x2",
            avg_completion_time_hours=3.0,
            p20_completion_time_hours=2.0,
        )
        assert slow.is_fast is False
