"""
SealIssuer — Automated describe-net seal issuance based on reputation milestones.

Closes the evidence flywheel loop:
  Task Completed → reputation_bridge.update() → threshold check →
  IF milestone crossed → describe-net SealRegistry.issueSeal() on-chain

This module monitors agent/worker reputation scores and automatically
issues on-chain seals when they cross tier thresholds:
  - BRONCE: 5+ tasks, 60%+ success → "NEWCOMER" seal
  - PLATA:  20+ tasks, 80%+ success → "RELIABLE" seal
  - ORO:    50+ tasks, 90%+ success → "SKILLFUL" seal
  - DIAMANTE: 100+ tasks, 95%+ success → "EXCEPTIONAL" seal

Each seal is an on-chain attestation that becomes a portable credential
via the ERC-8004 identity system.

Architecture:
    ┌─────────────┐     check      ┌──────────────────┐
    │ reputation   │───────────────►│  SealIssuer       │
    │ _bridge.py   │  thresholds   │                    │
    └─────────────┘               │  1. Check scores   │
                                  │  2. Find eligible   │
    ┌─────────────┐               │  3. Issue seals     │
    │ lifecycle    │  agent state  │  4. Record issuance │
    │ _manager.py  │──────────────►│  5. Emit events     │
    └─────────────┘               └──────────────────┘
                                           │
                                           │ on-chain TX
                                           ▼
                                  ┌──────────────────┐
                                  │ describe-net      │
                                  │ SealRegistry.sol  │
                                  │ (Base / Sepolia)  │
                                  └──────────────────┘

Dependencies:
    Python stdlib only (no web3.py required — uses raw JSON-RPC).
    For production, integrate with web3signer or Vault for key management.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger("em.swarm.seal_issuer")


# ---------------------------------------------------------------------------
# Seal Types (matching describe-net SealRegistry.sol)
# ---------------------------------------------------------------------------

class SealType(str, Enum):
    """Seal type identifiers — keccak256 of the label on-chain."""
    NEWCOMER = "NEWCOMER"
    RELIABLE = "RELIABLE"
    SKILLFUL = "SKILLFUL"
    EXCEPTIONAL = "EXCEPTIONAL"
    FAST = "FAST"
    THOROUGH = "THOROUGH"
    SPECIALIST = "SPECIALIST"


class Quadrant(str, Enum):
    """Evaluation direction quadrants from SealRegistry.sol."""
    H2H = "H2H"  # Human to Human
    H2A = "H2A"  # Human to Agent
    A2H = "A2H"  # Agent to Human
    A2A = "A2A"  # Agent to Agent


# ---------------------------------------------------------------------------
# Milestone Thresholds
# ---------------------------------------------------------------------------

@dataclass
class MilestoneThreshold:
    """Defines when a seal should be issued."""
    seal_type: SealType
    min_tasks: int
    min_success_rate: float  # 0.0-1.0
    min_avg_rating: float = 0.0  # 0-5 scale, 0 = no minimum
    quadrant: Quadrant = Quadrant.A2H  # Default: agent evaluating human worker
    cooldown_days: int = 7  # Don't re-issue same seal type within this window
    category_specific: bool = False  # If True, issue per-category
    description: str = ""


# Default milestones (can be overridden via config)
DEFAULT_MILESTONES = [
    MilestoneThreshold(
        seal_type=SealType.NEWCOMER,
        min_tasks=5,
        min_success_rate=0.60,
        description="Completed first tasks with acceptable quality",
    ),
    MilestoneThreshold(
        seal_type=SealType.RELIABLE,
        min_tasks=20,
        min_success_rate=0.80,
        min_avg_rating=3.5,
        description="Consistently reliable task completion",
    ),
    MilestoneThreshold(
        seal_type=SealType.SKILLFUL,
        min_tasks=50,
        min_success_rate=0.90,
        min_avg_rating=4.0,
        description="High skill demonstrated across many tasks",
    ),
    MilestoneThreshold(
        seal_type=SealType.EXCEPTIONAL,
        min_tasks=100,
        min_success_rate=0.95,
        min_avg_rating=4.5,
        description="Elite-level performance over sustained period",
    ),
    MilestoneThreshold(
        seal_type=SealType.FAST,
        min_tasks=10,
        min_success_rate=0.80,
        description="Consistently fast completion times (top 20%)",
    ),
    MilestoneThreshold(
        seal_type=SealType.SPECIALIST,
        min_tasks=15,
        min_success_rate=0.85,
        category_specific=True,
        description="Deep expertise in a specific task category",
    ),
]


# ---------------------------------------------------------------------------
# Issuance Record
# ---------------------------------------------------------------------------

@dataclass
class SealIssuance:
    """Record of a seal issuance (pending or confirmed)."""
    seal_type: SealType
    subject_wallet: str
    evaluator_wallet: str
    quadrant: Quadrant
    category: Optional[str] = None
    evidence_hash: str = ""
    tx_hash: Optional[str] = None
    status: str = "pending"  # pending, submitted, confirmed, failed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    error: Optional[str] = None
    milestone: Optional[str] = None  # Which milestone triggered this

    def to_dict(self) -> dict:
        return {
            "seal_type": self.seal_type.value,
            "subject": self.subject_wallet,
            "evaluator": self.evaluator_wallet,
            "quadrant": self.quadrant.value,
            "category": self.category,
            "evidence_hash": self.evidence_hash,
            "tx_hash": self.tx_hash,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "error": self.error,
            "milestone": self.milestone,
        }


# ---------------------------------------------------------------------------
# Worker Performance Data
# ---------------------------------------------------------------------------

@dataclass
class WorkerPerformance:
    """Aggregated performance data for milestone evaluation."""
    wallet: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_rating: float = 0.0
    avg_completion_time_hours: float = 0.0
    median_completion_time_hours: float = 0.0
    p20_completion_time_hours: float = 0.0  # Top 20% threshold
    categories: dict[str, int] = field(default_factory=dict)  # category → count
    category_success_rates: dict[str, float] = field(default_factory=dict)
    existing_seals: set[str] = field(default_factory=set)  # Already issued seal types
    last_seal_at: dict[str, datetime] = field(default_factory=dict)  # seal_type → when

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def is_fast(self) -> bool:
        """Worker is in top 20% completion time."""
        if self.p20_completion_time_hours <= 0:
            return False
        return self.avg_completion_time_hours <= self.p20_completion_time_hours


# ---------------------------------------------------------------------------
# SealIssuer Engine
# ---------------------------------------------------------------------------

class SealIssuer:
    """
    Monitors reputation and issues describe-net seals when milestones are reached.

    Designed to be called periodically (e.g., after each task completion or
    during the daemon's analytics phase). Uses callbacks for on-chain
    submission to keep the module independent of any specific web3 library.

    Usage:
        issuer = SealIssuer(
            platform_wallet="0xD386...",
            on_issue=my_chain_callback,  # or None for dry-run mode
        )

        # After processing a task completion:
        eligible = issuer.check_milestones(worker_performance)
        for issuance in eligible:
            issuer.submit(issuance)

        # Or auto-process:
        results = issuer.process_worker(worker_performance)
    """

    def __init__(
        self,
        platform_wallet: str = "",
        milestones: list[MilestoneThreshold] | None = None,
        on_issue: Callable[[SealIssuance], Optional[str]] | None = None,
        dry_run: bool = False,
        state_file: str | None = None,
    ):
        """
        Args:
            platform_wallet: Wallet that signs seal issuance TXs
            milestones: Custom milestone thresholds (defaults to DEFAULT_MILESTONES)
            on_issue: Callback for on-chain submission. Takes SealIssuance,
                      returns tx_hash or None. If None, runs in dry-run mode.
            dry_run: If True, never actually submit on-chain
            state_file: Path to persist issuance history (JSON)
        """
        self.platform_wallet = platform_wallet
        self.milestones = milestones if milestones is not None else DEFAULT_MILESTONES
        self.on_issue = on_issue
        self.dry_run = dry_run or (on_issue is None)
        self.state_file = state_file

        # Issuance history: wallet → list of SealIssuance
        self._history: dict[str, list[SealIssuance]] = {}
        # Pending issuances not yet confirmed
        self._pending: list[SealIssuance] = []

        # Stats
        self._total_checks = 0
        self._total_issued = 0
        self._total_skipped = 0

        # Load state if file exists
        if state_file:
            self._load_state()

    def check_milestones(
        self,
        worker: WorkerPerformance,
    ) -> list[SealIssuance]:
        """Check if a worker has crossed any milestone thresholds.

        Returns list of SealIssuance objects for newly eligible milestones.
        Skips milestones that have already been issued or are in cooldown.
        """
        self._total_checks += 1
        eligible: list[SealIssuance] = []

        for milestone in self.milestones:
            # Skip if already issued (non-category-specific)
            if not milestone.category_specific:
                if self._already_issued(worker.wallet, milestone.seal_type):
                    continue

                # Check basic thresholds
                if worker.total_tasks < milestone.min_tasks:
                    continue
                if worker.success_rate < milestone.min_success_rate:
                    continue
                if milestone.min_avg_rating > 0 and worker.avg_rating < milestone.min_avg_rating:
                    continue

                # Special check for FAST seal
                if milestone.seal_type == SealType.FAST and not worker.is_fast:
                    continue

                # Check cooldown
                if self._in_cooldown(worker.wallet, milestone.seal_type, milestone.cooldown_days):
                    continue

                # Eligible!
                evidence = self._compute_evidence_hash(worker, milestone)
                issuance = SealIssuance(
                    seal_type=milestone.seal_type,
                    subject_wallet=worker.wallet,
                    evaluator_wallet=self.platform_wallet,
                    quadrant=milestone.quadrant,
                    evidence_hash=evidence,
                    milestone=f"{milestone.seal_type.value}: {milestone.description}",
                )
                eligible.append(issuance)
            else:
                # Category-specific: check each category independently
                for category, count in worker.categories.items():
                    seal_key = f"{milestone.seal_type.value}:{category}"
                    if self._already_issued(worker.wallet, milestone.seal_type, category):
                        continue

                    if count < milestone.min_tasks:
                        continue

                    cat_success = worker.category_success_rates.get(category, 0.0)
                    if cat_success < milestone.min_success_rate:
                        continue

                    if self._in_cooldown(worker.wallet, milestone.seal_type, milestone.cooldown_days, category):
                        continue

                    evidence = self._compute_evidence_hash(worker, milestone, category)
                    issuance = SealIssuance(
                        seal_type=milestone.seal_type,
                        subject_wallet=worker.wallet,
                        evaluator_wallet=self.platform_wallet,
                        quadrant=milestone.quadrant,
                        category=category,
                        evidence_hash=evidence,
                        milestone=f"{milestone.seal_type.value} [{category}]: {milestone.description}",
                    )
                    eligible.append(issuance)

        return eligible

    def submit(self, issuance: SealIssuance) -> SealIssuance:
        """Submit a seal issuance on-chain.

        If dry_run, logs but doesn't submit. If on_issue callback is set,
        calls it and records the tx_hash.
        """
        if self.dry_run:
            issuance.status = "dry_run"
            logger.info(
                f"[DRY RUN] Would issue {issuance.seal_type.value} seal "
                f"to {issuance.subject_wallet[:10]}... "
                f"(category={issuance.category}, evidence={issuance.evidence_hash[:16]}...)"
            )
            self._record_issuance(issuance)
            self._total_issued += 1
            return issuance

        try:
            issuance.status = "submitted"
            tx_hash = self.on_issue(issuance)
            if tx_hash:
                issuance.tx_hash = tx_hash
                issuance.status = "confirmed"
                issuance.confirmed_at = datetime.now(timezone.utc)
                logger.info(
                    f"✅ Issued {issuance.seal_type.value} seal to "
                    f"{issuance.subject_wallet[:10]}... — tx: {tx_hash[:16]}..."
                )
            else:
                issuance.status = "submitted_no_hash"
                logger.warning(
                    f"⚠️ Seal submitted but no tx hash returned for "
                    f"{issuance.seal_type.value} → {issuance.subject_wallet[:10]}..."
                )
        except Exception as e:
            issuance.status = "failed"
            issuance.error = str(e)
            logger.error(
                f"❌ Failed to issue {issuance.seal_type.value} seal: {e}"
            )

        self._record_issuance(issuance)
        self._total_issued += 1 if issuance.status in ("confirmed", "submitted_no_hash", "dry_run") else 0
        return issuance

    def process_worker(self, worker: WorkerPerformance) -> list[SealIssuance]:
        """One-shot: check milestones and submit any eligible seals.

        Convenience method that combines check + submit.
        """
        eligible = self.check_milestones(worker)
        results = []
        for issuance in eligible:
            result = self.submit(issuance)
            results.append(result)
        return results

    def process_batch(self, workers: list[WorkerPerformance]) -> dict:
        """Process multiple workers in one pass.

        Returns summary dict with counts and details.
        """
        all_results: list[SealIssuance] = []
        for worker in workers:
            results = self.process_worker(worker)
            all_results.extend(results)

        return {
            "workers_checked": len(workers),
            "seals_issued": len([r for r in all_results if r.status in ("confirmed", "dry_run", "submitted_no_hash")]),
            "seals_failed": len([r for r in all_results if r.status == "failed"]),
            "issuances": [r.to_dict() for r in all_results],
        }

    # ---- State Management ----

    def _already_issued(
        self,
        wallet: str,
        seal_type: SealType,
        category: str | None = None,
    ) -> bool:
        """Check if this seal has already been issued to this wallet."""
        history = self._history.get(wallet, [])
        for record in history:
            if record.seal_type == seal_type and record.category == category:
                if record.status in ("confirmed", "dry_run", "submitted_no_hash"):
                    return True
        return False

    def _in_cooldown(
        self,
        wallet: str,
        seal_type: SealType,
        cooldown_days: int,
        category: str | None = None,
    ) -> bool:
        """Check if this seal type is in cooldown for this wallet."""
        history = self._history.get(wallet, [])
        now = datetime.now(timezone.utc)
        for record in reversed(history):
            if record.seal_type == seal_type and record.category == category:
                if record.created_at and (now - record.created_at).days < cooldown_days:
                    return True
        return False

    def _record_issuance(self, issuance: SealIssuance):
        """Record an issuance in history."""
        wallet = issuance.subject_wallet
        if wallet not in self._history:
            self._history[wallet] = []
        self._history[wallet].append(issuance)

        if self.state_file:
            self._save_state()

    def _compute_evidence_hash(
        self,
        worker: WorkerPerformance,
        milestone: MilestoneThreshold,
        category: str | None = None,
    ) -> str:
        """Compute a deterministic evidence hash for the seal.

        Includes: wallet, milestone type, task counts, success rate, timestamp.
        This hash can be stored on-chain as evidence of what triggered the seal.
        """
        data = {
            "wallet": worker.wallet,
            "seal_type": milestone.seal_type.value,
            "total_tasks": worker.total_tasks,
            "success_rate": round(worker.success_rate, 4),
            "avg_rating": round(worker.avg_rating, 2),
            "category": category,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        raw = json.dumps(data, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _load_state(self):
        """Load issuance history from state file."""
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            for wallet, records in data.get("history", {}).items():
                self._history[wallet] = []
                for r in records:
                    self._history[wallet].append(SealIssuance(
                        seal_type=SealType(r["seal_type"]),
                        subject_wallet=r["subject"],
                        evaluator_wallet=r["evaluator"],
                        quadrant=Quadrant(r["quadrant"]),
                        category=r.get("category"),
                        evidence_hash=r.get("evidence_hash", ""),
                        tx_hash=r.get("tx_hash"),
                        status=r.get("status", "unknown"),
                        created_at=datetime.fromisoformat(r["created_at"]) if r.get("created_at") else datetime.now(timezone.utc),
                        confirmed_at=datetime.fromisoformat(r["confirmed_at"]) if r.get("confirmed_at") else None,
                        error=r.get("error"),
                        milestone=r.get("milestone"),
                    ))
            logger.info(f"Loaded seal issuer state: {sum(len(v) for v in self._history.values())} records")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Failed to load seal issuer state: {e}")

    def _save_state(self):
        """Persist issuance history to state file."""
        try:
            data = {
                "history": {
                    wallet: [r.to_dict() for r in records]
                    for wallet, records in self._history.items()
                },
                "stats": {
                    "total_checks": self._total_checks,
                    "total_issued": self._total_issued,
                    "total_skipped": self._total_skipped,
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save seal issuer state: {e}")

    def get_stats(self) -> dict:
        """Get issuer statistics."""
        total_records = sum(len(v) for v in self._history.values())
        confirmed = sum(
            1 for records in self._history.values()
            for r in records
            if r.status in ("confirmed", "dry_run")
        )
        return {
            "total_checks": self._total_checks,
            "total_issued": self._total_issued,
            "total_skipped": self._total_skipped,
            "history_records": total_records,
            "confirmed_seals": confirmed,
            "unique_wallets": len(self._history),
            "dry_run": self.dry_run,
        }

    def get_worker_seals(self, wallet: str) -> list[dict]:
        """Get all seals issued to a specific wallet."""
        return [r.to_dict() for r in self._history.get(wallet, [])]
