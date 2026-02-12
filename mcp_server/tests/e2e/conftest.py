"""
Shared fixtures for E2E task lifecycle tests.

Provides mocked Supabase client, x402 escrow manager, and test entities
(agents, workers) for testing the complete task lifecycle.
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from unittest.mock import MagicMock


# ============== MOCK DATA CLASSES ==============


@dataclass
class MockWallet:
    """Mock wallet for testing."""

    address: str
    balance_usdc: float = 1000.0


@dataclass
class MockAgent:
    """Test agent with API key and wallet."""

    agent_id: str
    api_key: str
    wallet: MockWallet
    display_name: str = "Test Agent"

    @classmethod
    def create(cls, seed: int = 1) -> "MockAgent":
        """Create a test agent with unique ID."""
        return cls(
            agent_id=f"agent-{uuid.uuid4().hex[:8]}-{seed}",
            api_key=f"test-api-key-{seed}",
            wallet=MockWallet(
                address=f"0x{'A' * 38}{seed:02d}",
                balance_usdc=10000.0,
            ),
            display_name=f"Test Agent {seed}",
        )


@dataclass
class MockWorker:
    """Test worker with executor_id and wallet."""

    executor_id: str
    wallet: MockWallet
    display_name: str = "Test Worker"
    reputation_score: int = 100
    tasks_completed: int = 10
    status: str = "active"

    @classmethod
    def create(cls, seed: int = 1, reputation: int = 100) -> "MockWorker":
        """Create a test worker with unique ID."""
        return cls(
            executor_id=str(uuid.uuid4()),
            wallet=MockWallet(
                address=f"0x{'B' * 38}{seed:02d}",
                balance_usdc=100.0,
            ),
            display_name=f"Test Worker {seed}",
            reputation_score=reputation,
            tasks_completed=10 + seed,
            status="active",
        )


@dataclass
class MockEscrowRecord:
    """Track escrow state for a task."""

    escrow_id: str
    task_id: str
    total_amount: Decimal
    released_amount: Decimal = Decimal("0")
    status: str = "deposited"
    depositor_wallet: str = ""
    beneficiary_wallet: Optional[str] = None
    deposit_tx: str = ""
    release_txs: List[Dict[str, Any]] = field(default_factory=list)
    refund_tx: Optional[str] = None
    timeout_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=48)
    )

    @property
    def remaining_amount(self) -> Decimal:
        return self.total_amount - self.released_amount


# ============== MOCK ESCROW MANAGER ==============


class MockEscrowManager:
    """
    Mock escrow manager that tracks payment state in memory.

    Tracks:
    - Deposits when tasks are published
    - Partial releases (30%) when work is submitted
    - Final releases (70%) when approved
    - Refunds when cancelled
    - Dispute locks
    """

    PLATFORM_FEE_PERCENT = Decimal("0.13")  # 13%
    PARTIAL_RELEASE_PERCENT = Decimal("0.30")  # 30%

    def __init__(self):
        self._escrows: Dict[str, MockEscrowRecord] = {}
        self._tx_counter = 0

    def _generate_tx_hash(self) -> str:
        """Generate mock transaction hash."""
        self._tx_counter += 1
        return f"0x{'T' * 60}{self._tx_counter:04d}"

    def _generate_escrow_id(self) -> str:
        """Generate mock escrow ID."""
        return f"escrow-{uuid.uuid4().hex[:12]}"

    async def deposit_for_task(
        self,
        task_id: str,
        bounty_usd: Decimal,
        agent_wallet: str,
        timeout_hours: int = 48,
    ) -> MockEscrowRecord:
        """Create escrow deposit for a task."""
        if task_id in self._escrows:
            raise ValueError(f"Escrow already exists for task {task_id}")

        escrow = MockEscrowRecord(
            escrow_id=self._generate_escrow_id(),
            task_id=task_id,
            total_amount=bounty_usd,
            depositor_wallet=agent_wallet,
            deposit_tx=self._generate_tx_hash(),
            timeout_at=datetime.now(timezone.utc) + timedelta(hours=timeout_hours),
        )
        self._escrows[task_id] = escrow
        return escrow

    async def release_partial_on_submission(
        self,
        task_id: str,
        worker_wallet: str,
    ) -> Dict[str, Any]:
        """Release 30% partial payment when worker submits."""
        escrow = self._get_escrow(task_id)

        if escrow.status not in ("deposited",):
            raise ValueError(
                f"Cannot release partial: escrow status is {escrow.status}"
            )

        # Calculate 30% of net (after fees)
        net_bounty = escrow.total_amount * (1 - self.PLATFORM_FEE_PERCENT)
        partial_amount = (net_bounty * self.PARTIAL_RELEASE_PERCENT).quantize(
            Decimal("0.01")
        )

        tx_hash = self._generate_tx_hash()
        escrow.beneficiary_wallet = worker_wallet
        escrow.released_amount += partial_amount
        escrow.status = "partial_released"
        escrow.release_txs.append(
            {
                "tx_hash": tx_hash,
                "amount": float(partial_amount),
                "recipient": worker_wallet,
                "type": "partial",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "amount_released": float(partial_amount),
            "percent_released": float(self.PARTIAL_RELEASE_PERCENT * 100),
            "remaining": float(escrow.remaining_amount),
            "type": "partial",
        }

    async def release_on_approval(
        self,
        task_id: str,
        worker_wallet: str,
    ) -> Dict[str, Any]:
        """Release remaining payment when agent approves."""
        escrow = self._get_escrow(task_id)

        if escrow.status not in ("deposited", "partial_released"):
            raise ValueError(f"Cannot release: escrow status is {escrow.status}")

        # Calculate amounts
        net_bounty = escrow.total_amount * (1 - self.PLATFORM_FEE_PERCENT)
        platform_fee = escrow.total_amount * self.PLATFORM_FEE_PERCENT

        # Worker gets remaining net (after partial)
        worker_remaining = (net_bounty - escrow.released_amount).quantize(
            Decimal("0.01")
        )

        tx_hashes = []

        # Release to worker
        if worker_remaining > 0:
            worker_tx = self._generate_tx_hash()
            escrow.release_txs.append(
                {
                    "tx_hash": worker_tx,
                    "amount": float(worker_remaining),
                    "recipient": worker_wallet,
                    "type": "final",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            escrow.released_amount += worker_remaining
            tx_hashes.append(worker_tx)

        # Record platform fee (would go to treasury)
        fee_tx = self._generate_tx_hash()
        escrow.release_txs.append(
            {
                "tx_hash": fee_tx,
                "amount": float(platform_fee),
                "recipient": "treasury",
                "type": "fee",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        escrow.released_amount += platform_fee
        tx_hashes.append(fee_tx)

        escrow.status = "released"

        return {
            "success": True,
            "tx_hashes": tx_hashes,
            "worker_payment": float(net_bounty),
            "platform_fee": float(platform_fee),
            "total_released": float(escrow.released_amount),
            "type": "final",
        }

    async def refund_on_cancel(
        self,
        task_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Refund escrow when task is cancelled."""
        escrow = self._get_escrow(task_id)

        if escrow.status not in ("deposited",):
            raise ValueError(
                f"Cannot refund: escrow status is {escrow.status}. "
                f"Only 'deposited' escrows can be fully refunded."
            )

        if escrow.released_amount > 0:
            raise ValueError(
                f"Cannot fully refund: ${float(escrow.released_amount):.2f} already released."
            )

        tx_hash = self._generate_tx_hash()
        escrow.refund_tx = tx_hash
        escrow.status = "refunded"

        return {
            "success": True,
            "tx_hash": tx_hash,
            "amount_refunded": float(escrow.total_amount),
            "type": "refund",
        }

    async def handle_dispute(
        self,
        task_id: str,
        dispute_reason: Optional[str] = None,
    ) -> None:
        """Lock escrow for dispute resolution."""
        escrow = self._get_escrow(task_id)

        if escrow.status not in ("deposited", "partial_released"):
            raise ValueError(f"Cannot dispute: escrow status is {escrow.status}")

        escrow.status = "disputed"

    async def resolve_dispute(
        self,
        task_id: str,
        winner: str,
        worker_wallet: Optional[str] = None,
        worker_pct: float = 1.0,
    ) -> Dict[str, Any]:
        """Resolve dispute and release funds accordingly."""
        escrow = self._get_escrow(task_id)

        if escrow.status != "disputed":
            raise ValueError(f"Cannot resolve: escrow status is {escrow.status}")

        if winner == "worker":
            if not worker_wallet:
                raise ValueError("worker_wallet required when worker wins")

            escrow.status = "partial_released"  # Allow release
            return await self.release_on_approval(task_id, worker_wallet)

        elif winner == "agent":
            # Reset to deposited state for refund
            escrow.status = "deposited"
            escrow.released_amount = Decimal("0")
            return await self.refund_on_cancel(
                task_id, "Dispute resolved in favor of agent"
            )

        else:
            raise ValueError(f"Invalid winner: {winner}")

    async def process_timeout_refund(
        self,
        task_id: str,
    ) -> Dict[str, Any]:
        """Process refund for expired task."""
        escrow = self._get_escrow(task_id)

        if datetime.now(timezone.utc) < escrow.timeout_at:
            raise ValueError("Escrow has not timed out yet")

        if escrow.released_amount > 0:
            # Partial refund: only unreleased amount goes back to agent
            refund_amount = escrow.remaining_amount
            tx_hash = self._generate_tx_hash()
            escrow.refund_tx = tx_hash
            escrow.status = "refunded"

            return {
                "success": True,
                "tx_hash": tx_hash,
                "amount_refunded": float(refund_amount),
                "partial_released_to_worker": float(escrow.released_amount),
                "type": "timeout_partial_refund",
            }
        else:
            return await self.refund_on_cancel(
                task_id, "Task expired without assignment"
            )

    def get_escrow(self, task_id: str) -> Optional[MockEscrowRecord]:
        """Get escrow state for a task."""
        return self._escrows.get(task_id)

    def _get_escrow(self, task_id: str) -> MockEscrowRecord:
        """Get escrow, raising error if not found."""
        escrow = self._escrows.get(task_id)
        if not escrow:
            raise ValueError(f"No escrow found for task {task_id}")
        return escrow


# ============== MOCK SUPABASE CLIENT ==============


class MockSupabaseClient:
    """
    Mock Supabase client that stores data in memory.

    Implements the same interface as the real supabase_client module.
    """

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._executors: Dict[str, Dict[str, Any]] = {}
        self._submissions: Dict[str, Dict[str, Any]] = {}
        self._applications: Dict[str, Dict[str, Any]] = {}
        self._payments: Dict[str, Dict[str, Any]] = {}
        self._disputes: Dict[str, Dict[str, Any]] = {}

    def register_worker(self, worker: MockWorker) -> None:
        """Register a test worker."""
        self._executors[worker.executor_id] = {
            "id": worker.executor_id,
            "display_name": worker.display_name,
            "wallet_address": worker.wallet.address,
            "reputation_score": worker.reputation_score,
            "tasks_completed": worker.tasks_completed,
            "tasks_disputed": 0,
            "status": worker.status,
            "active_tasks_count": 0,
        }

    async def create_task(
        self,
        agent_id: str,
        title: str,
        instructions: str,
        category: str,
        bounty_usd: float,
        deadline: datetime,
        evidence_required: List[str],
        evidence_optional: Optional[List[str]] = None,
        location_hint: Optional[str] = None,
        min_reputation: int = 0,
        payment_token: str = "USDC",
    ) -> Dict[str, Any]:
        """Create a new task."""
        task_id = str(uuid.uuid4())

        task = {
            "id": task_id,
            "agent_id": agent_id,
            "title": title,
            "instructions": instructions,
            "category": category,
            "bounty_usd": bounty_usd,
            "deadline": deadline.isoformat(),
            "evidence_schema": {
                "required": evidence_required,
                "optional": evidence_optional or [],
            },
            "location_hint": location_hint,
            "min_reputation": min_reputation,
            "payment_token": payment_token,
            "status": "published",
            "executor_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "assigned_at": None,
            "completed_at": None,
            "escrow_id": None,
        }

        self._tasks[task_id] = task
        return task

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        task = self._tasks.get(task_id)
        if task and task.get("executor_id"):
            executor = self._executors.get(task["executor_id"])
            if executor:
                task["executor"] = executor
        return task

    async def get_tasks(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get tasks with filters."""
        tasks = list(self._tasks.values())

        if agent_id:
            tasks = [t for t in tasks if t["agent_id"] == agent_id]
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        if category:
            tasks = [t for t in tasks if t["category"] == category]

        total = len(tasks)
        tasks = tasks[offset : offset + limit]

        return {
            "total": total,
            "count": len(tasks),
            "offset": offset,
            "tasks": tasks,
            "has_more": total > offset + len(tasks),
        }

    async def update_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a task."""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")

        self._tasks[task_id].update(updates)
        return self._tasks[task_id]

    async def apply_to_task(
        self,
        task_id: str,
        executor_id: str,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Worker applies to a task."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task["status"] != "published":
            raise ValueError(f"Task is not available (status: {task['status']})")

        executor = self._executors.get(executor_id)
        if not executor:
            raise ValueError(f"Executor {executor_id} not found")

        min_rep = task.get("min_reputation", 0)
        if executor.get("reputation_score", 0) < min_rep:
            raise ValueError(f"Insufficient reputation. Required: {min_rep}")

        # Check existing application
        for app in self._applications.values():
            if app["task_id"] == task_id and app["executor_id"] == executor_id:
                raise ValueError("Already applied to this task")

        app_id = str(uuid.uuid4())
        application = {
            "id": app_id,
            "task_id": task_id,
            "executor_id": executor_id,
            "message": message,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._applications[app_id] = application

        return {
            "application": application,
            "task": task,
            "executor": executor,
        }

    async def assign_task(
        self,
        task_id: str,
        agent_id: str,
        executor_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Agent assigns task to a worker."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task["agent_id"] != agent_id:
            raise ValueError("Not authorized to assign this task")
        if task["status"] != "published":
            raise ValueError(f"Task cannot be assigned (status: {task['status']})")

        executor = self._executors.get(executor_id)
        if not executor:
            raise ValueError(f"Executor {executor_id} not found")

        # Update task
        updates = {
            "executor_id": executor_id,
            "status": "accepted",
            "assignment_notes": notes,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }
        task = await self.update_task(task_id, updates)

        # Update worker's active tasks
        executor["active_tasks_count"] = executor.get("active_tasks_count", 0) + 1

        # Update applications
        for app in self._applications.values():
            if app["task_id"] == task_id:
                if app["executor_id"] == executor_id:
                    app["status"] = "accepted"
                else:
                    app["status"] = "rejected"

        return {"task": task, "executor": executor}

    async def submit_work(
        self,
        task_id: str,
        executor_id: str,
        evidence: Dict[str, Any],
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Worker submits completed work."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task.get("executor_id") != executor_id:
            raise ValueError("You are not assigned to this task")
        if task["status"] not in ("accepted", "in_progress"):
            raise ValueError(f"Task is not submittable (status: {task['status']})")

        # Validate required evidence
        required = task.get("evidence_schema", {}).get("required", [])
        missing = [r for r in required if r not in evidence]
        if missing:
            raise ValueError(f"Missing required evidence: {', '.join(missing)}")

        submission_id = str(uuid.uuid4())
        submission = {
            "id": submission_id,
            "task_id": task_id,
            "executor_id": executor_id,
            "evidence": evidence,
            "notes": notes,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "agent_verdict": "pending",
            "agent_notes": None,
            "verified_at": None,
        }
        self._submissions[submission_id] = submission

        # Update task status
        task = await self.update_task(task_id, {"status": "submitted"})

        return {"submission": submission, "task": task}

    async def get_submissions_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all submissions for a task."""
        submissions = [s for s in self._submissions.values() if s["task_id"] == task_id]
        for sub in submissions:
            executor = self._executors.get(sub["executor_id"])
            if executor:
                sub["executor"] = executor
        return submissions

    async def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Get a submission by ID."""
        sub = self._submissions.get(submission_id)
        if sub:
            sub["task"] = await self.get_task(sub["task_id"])
            executor = self._executors.get(sub["executor_id"])
            if executor:
                sub["executor"] = executor
        return sub

    async def update_submission(
        self,
        submission_id: str,
        agent_id: str,
        verdict: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update submission with agent's verdict."""
        sub = await self.get_submission(submission_id)
        if not sub:
            raise ValueError(f"Submission {submission_id} not found")

        task = sub.get("task")
        if not task or task["agent_id"] != agent_id:
            raise ValueError("Not authorized to update this submission")

        sub["agent_verdict"] = verdict
        sub["agent_notes"] = notes

        if verdict == "accepted":
            sub["verified_at"] = datetime.now(timezone.utc).isoformat()
            # Update task status
            await self.update_task(
                task["id"],
                {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            # Update worker reputation
            executor = self._executors.get(sub["executor_id"])
            if executor:
                executor["reputation_score"] = executor.get("reputation_score", 0) + 10
                executor["tasks_completed"] = executor.get("tasks_completed", 0) + 1
                executor["active_tasks_count"] = max(
                    0, executor.get("active_tasks_count", 1) - 1
                )

        elif verdict == "disputed":
            await self.update_task(task["id"], {"status": "disputed"})

        return sub

    async def get_executor_stats(self, executor_id: str) -> Optional[Dict[str, Any]]:
        """Get executor statistics."""
        return self._executors.get(executor_id)

    async def get_executor_earnings(self, executor_id: str) -> Dict[str, Any]:
        """Get earnings summary for an executor."""
        payments = [
            p for p in self._payments.values() if p.get("executor_id") == executor_id
        ]

        completed = [p for p in payments if p.get("status") == "completed"]
        pending = [p for p in payments if p.get("status") == "pending"]
        available = [p for p in payments if p.get("status") == "available"]

        return {
            "total_earned": sum(float(p.get("amount_usdc", 0)) for p in completed),
            "pending": sum(float(p.get("amount_usdc", 0)) for p in pending),
            "available": sum(float(p.get("amount_usdc", 0)) for p in available),
            "payments": payments[-10:],
        }

    async def cancel_task(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        """Cancel a task."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task["agent_id"] != agent_id:
            raise ValueError("Not authorized to cancel this task")
        if task["status"] != "published":
            raise ValueError(f"Cannot cancel task with status: {task['status']}")

        return await self.update_task(task_id, {"status": "cancelled"})

    async def create_dispute(
        self,
        task_id: str,
        submission_id: str,
        opened_by: str,
        opener_id: str,
        dispute_type: str,
        description: str,
        evidence_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a dispute."""
        dispute_id = str(uuid.uuid4())
        dispute = {
            "id": dispute_id,
            "task_id": task_id,
            "submission_id": submission_id,
            "opened_by": opened_by,
            "opener_id": opener_id,
            "dispute_type": dispute_type,
            "description": description,
            "evidence_urls": evidence_urls or [],
            "status": "opened",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": None,
            "outcome": None,
            "resolution_notes": None,
        }
        self._disputes[dispute_id] = dispute

        # Update task status
        await self.update_task(task_id, {"status": "disputed"})

        return dispute

    async def resolve_dispute(
        self,
        dispute_id: str,
        outcome: str,
        resolution_notes: str,
        worker_payout_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """Resolve a dispute."""
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute {dispute_id} not found")

        dispute["status"] = "resolved"
        dispute["outcome"] = outcome
        dispute["resolution_notes"] = resolution_notes
        dispute["resolved_at"] = datetime.now(timezone.utc).isoformat()
        dispute["worker_payout_pct"] = worker_payout_pct

        # Update task based on outcome
        task_id = dispute["task_id"]
        if outcome == "worker_wins":
            await self.update_task(
                task_id,
                {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        elif outcome == "agent_wins":
            await self.update_task(task_id, {"status": "cancelled"})

        return dispute

    def get_client(self):
        """Return self for compatibility with db.get_client() pattern."""
        return self

    def table(self, name: str):
        """Return mock table builder."""
        return MockTableBuilder(self, name)


class MockTableBuilder:
    """Mock Supabase table query builder."""

    def __init__(self, client: MockSupabaseClient, table_name: str):
        self._client = client
        self._table_name = table_name
        self._data = self._get_table_data()
        self._filters = []
        self._select_fields = "*"
        self._order_by = None
        self._limit_val = None
        self._offset_val = 0

    def _get_table_data(self) -> Dict[str, Dict]:
        """Get data dictionary for table."""
        mapping = {
            "tasks": self._client._tasks,
            "executors": self._client._executors,
            "submissions": self._client._submissions,
            "applications": self._client._applications,
            "payments": self._client._payments,
            "disputes": self._client._disputes,
        }
        return mapping.get(self._table_name, {})

    def select(self, fields: str = "*", count: str = None):
        self._select_fields = fields
        return self

    def eq(self, field: str, value: Any):
        self._filters.append((field, "eq", value))
        return self

    def neq(self, field: str, value: Any):
        self._filters.append((field, "neq", value))
        return self

    def in_(self, field: str, values: List[Any]):
        self._filters.append((field, "in", values))
        return self

    def gte(self, field: str, value: Any):
        self._filters.append((field, "gte", value))
        return self

    def order(self, field: str, desc: bool = False):
        self._order_by = (field, desc)
        return self

    def limit(self, count: int):
        self._limit_val = count
        return self

    def range(self, start: int, end: int):
        self._offset_val = start
        self._limit_val = end - start + 1
        return self

    def single(self):
        return self

    def execute(self):
        """Execute query and return mock result."""
        items = list(self._data.values())

        # Apply filters
        for field_name, op, value in self._filters:
            if op == "eq":
                items = [i for i in items if i.get(field_name) == value]
            elif op == "neq":
                items = [i for i in items if i.get(field_name) != value]
            elif op == "in":
                items = [i for i in items if i.get(field_name) in value]
            elif op == "gte":
                items = [i for i in items if i.get(field_name) >= value]

        # Apply ordering
        if self._order_by:
            field_name, desc = self._order_by
            items.sort(key=lambda x: x.get(field_name, ""), reverse=desc)

        # Apply pagination
        if self._offset_val:
            items = items[self._offset_val :]
        if self._limit_val:
            items = items[: self._limit_val]

        return MagicMock(
            data=items[0] if hasattr(self, "_single") else items, count=len(items)
        )

    def insert(self, data: Dict[str, Any]):
        """Insert data."""
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        self._data[data["id"]] = data
        return self

    def update(self, updates: Dict[str, Any]):
        """Update matching records."""
        for item in self._data.values():
            match = all(item.get(f) == v for f, op, v in self._filters if op == "eq")
            if match:
                item.update(updates)
        return self


# ============== PYTEST FIXTURES ==============


@pytest.fixture
def mock_escrow_manager():
    """Create mock escrow manager for payment tracking."""
    return MockEscrowManager()


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client."""
    return MockSupabaseClient()


@pytest.fixture
def test_agent():
    """Create test agent with API key and wallet."""
    return MockAgent.create(seed=1)


@pytest.fixture
def test_worker():
    """Create test worker with executor_id and wallet."""
    return MockWorker.create(seed=1, reputation=100)


@pytest.fixture
def low_reputation_worker():
    """Create test worker with low reputation."""
    return MockWorker.create(seed=2, reputation=10)


@pytest.fixture
def sample_task_input(test_agent):
    """Sample input for creating a task."""
    return {
        "agent_id": test_agent.agent_id,
        "title": "Verify store hours at Main Street location",
        "instructions": "Take a photo of the store entrance showing the posted hours. Include the store name in the photo.",
        "category": "physical_presence",
        "bounty_usd": 10.00,
        "deadline_hours": 24,
        "evidence_required": ["photo_geo"],
        "evidence_optional": ["text_response"],
        "location_hint": "Downtown Miami",
        "min_reputation": 50,
    }


@pytest.fixture
def sample_evidence():
    """Sample evidence for task completion."""
    return {
        "photo_geo": {
            "url": "ipfs://QmTestHash123456789",
            "metadata": {
                "lat": 25.7617,
                "lng": -80.1918,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
        "text_response": "Store is open 9am-9pm daily. Photo shows entrance with hours posted.",
    }


@pytest.fixture
def miami_location():
    """Miami GPS coordinates."""
    return {"lat": 25.7617, "lng": -80.1918}


@pytest.fixture
async def published_task(
    mock_supabase, mock_escrow_manager, test_agent, sample_task_input
):
    """Create a published task with escrow."""
    # Create task in database
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

    # Create escrow
    escrow = await mock_escrow_manager.deposit_for_task(
        task_id=task["id"],
        bounty_usd=Decimal(str(sample_task_input["bounty_usd"])),
        agent_wallet=test_agent.wallet.address,
    )

    task["escrow_id"] = escrow.escrow_id

    return task


@pytest.fixture
async def assigned_task(published_task, mock_supabase, test_agent, test_worker):
    """Create an assigned task."""
    # Register worker
    mock_supabase.register_worker(test_worker)

    # Assign task
    result = await mock_supabase.assign_task(
        task_id=published_task["id"],
        agent_id=test_agent.agent_id,
        executor_id=test_worker.executor_id,
    )

    return result["task"]


@pytest.fixture
async def submitted_task(
    assigned_task, mock_supabase, mock_escrow_manager, test_worker, sample_evidence
):
    """Create a task with submitted work."""
    # Submit work
    result = await mock_supabase.submit_work(
        task_id=assigned_task["id"],
        executor_id=test_worker.executor_id,
        evidence=sample_evidence,
        notes="Work completed as requested",
    )

    # Release partial payment
    await mock_escrow_manager.release_partial_on_submission(
        task_id=assigned_task["id"],
        worker_wallet=test_worker.wallet.address,
    )

    return result["task"], result["submission"]
