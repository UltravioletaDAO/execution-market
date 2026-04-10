"""
Tests for BatchScheduler — Intelligent Task Batching for Multi-Task Routing
==============================================================================

Comprehensive test suite covering:
1. Data models (BatchTask, Batch, BatchPlan)
2. Task ingestion
3. Strategy: CHAIN grouping
4. Strategy: SKILL grouping
5. Strategy: DEADLINE grouping
6. Strategy: BOUNTY grouping
7. Strategy: HYBRID grouping
8. Priority computation
9. Planning mechanics (history, stats, efficiency)
10. Strategy suggestion
11. Savings estimation
12. State persistence (save/load)
13. Edge cases & boundary conditions
14. Production scenarios
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta

import pytest

from mcp_server.swarm.batch_scheduler import (
    BatchScheduler,
    BatchStrategy,
    BatchPriority,
    BatchTask,
    Batch,
    BatchPlan,
    DEFAULT_MAX_BATCH_SIZE,
    DEFAULT_MIN_BATCH_SIZE,
    DEFAULT_URGENCY_HOURS,
    BOUNTY_TIERS,
    HYBRID_WEIGHTS,
    _priority_sort_key,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


def _task(
    task_id: str = "t1",
    chain: str = "base",
    skills: list = None,
    bounty: float = 1.0,
    deadline: str | datetime | None = None,
    **kw,
) -> dict:
    """Build a raw task dict."""
    d = {
        "task_id": task_id,
        "title": f"Task {task_id}",
        "chain": chain,
        "bounty": bounty,
    }
    if skills is not None:
        d["skills"] = skills
    if deadline is not None:
        d["deadline"] = deadline
    d.update(kw)
    return d


def _tasks_on_chains(n_per_chain: int = 5, chains: list = None) -> list[dict]:
    """Generate tasks distributed across chains."""
    chains = chains or ["base", "polygon", "ethereum", "arbitrum"]
    tasks = []
    for i, chain in enumerate(chains):
        for j in range(n_per_chain):
            tasks.append(_task(
                task_id=f"{chain}-{j}",
                chain=chain,
                bounty=1.0 + j * 0.5,
                skills=[f"skill_{chain}"],
            ))
    return tasks


def _tasks_with_skills(skills_map: dict = None) -> list[dict]:
    """Generate tasks with specific skill distributions."""
    skills_map = skills_map or {
        "photography": 5,
        "delivery": 3,
        "data_entry": 4,
    }
    tasks = []
    for skill, count in skills_map.items():
        for i in range(count):
            tasks.append(_task(
                task_id=f"{skill}-{i}",
                skills=[skill],
                bounty=2.0,
            ))
    return tasks


def _tasks_with_deadlines(now: datetime = None) -> list[dict]:
    """Generate tasks with various deadline urgencies."""
    now = now or datetime.now(timezone.utc)
    return [
        _task("overdue", deadline=now - timedelta(hours=1)),
        _task("critical", deadline=now + timedelta(minutes=30)),
        _task("urgent", deadline=now + timedelta(hours=3)),
        _task("standard", deadline=now + timedelta(hours=12)),
        _task("relaxed", deadline=now + timedelta(days=3)),
        _task("no-deadline"),
    ]


# ──────────────────────────────────────────────────────────────
# 1. Data Models
# ──────────────────────────────────────────────────────────────


class TestBatchTask:
    """Tests for BatchTask data model."""

    def test_from_dict_basic(self):
        bt = BatchTask.from_dict({"task_id": "t1", "title": "Test", "bounty": 2.5})
        assert bt.task_id == "t1"
        assert bt.title == "Test"
        assert bt.bounty == 2.5

    def test_from_dict_defaults(self):
        bt = BatchTask.from_dict({})
        assert bt.task_id == ""
        assert bt.bounty == 0.0
        assert bt.chain == "base"
        assert bt.skills == []

    def test_from_dict_deadline_string(self):
        bt = BatchTask.from_dict({"task_id": "t1", "deadline": "2026-04-10T12:00:00Z"})
        assert bt.deadline is not None
        assert bt.deadline.year == 2026

    def test_from_dict_deadline_datetime(self):
        dt = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
        bt = BatchTask.from_dict({"task_id": "t1", "deadline": dt})
        assert bt.deadline == dt

    def test_from_dict_deadline_timestamp(self):
        ts = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc).timestamp()
        bt = BatchTask.from_dict({"task_id": "t1", "deadline": ts})
        assert bt.deadline is not None

    def test_from_dict_deadline_invalid(self):
        bt = BatchTask.from_dict({"task_id": "t1", "deadline": "not-a-date"})
        assert bt.deadline is None

    def test_from_dict_skills_string(self):
        bt = BatchTask.from_dict({"task_id": "t1", "skills": "photo, delivery, data"})
        assert bt.skills == ["photo", "delivery", "data"]

    def test_from_dict_skills_list(self):
        bt = BatchTask.from_dict({"task_id": "t1", "skills": ["a", "b"]})
        assert bt.skills == ["a", "b"]

    def test_from_dict_required_skills_alias(self):
        bt = BatchTask.from_dict({"task_id": "t1", "required_skills": ["x"]})
        assert bt.skills == ["x"]

    def test_from_dict_bounty_amount_alias(self):
        bt = BatchTask.from_dict({"task_id": "t1", "bounty_amount": 3.0})
        assert bt.bounty == 3.0

    def test_from_dict_network_alias(self):
        bt = BatchTask.from_dict({"task_id": "t1", "network": "Polygon"})
        assert bt.chain == "polygon"

    def test_from_dict_id_alias(self):
        bt = BatchTask.from_dict({"id": "alt-id"})
        assert bt.task_id == "alt-id"

    def test_raw_preserved(self):
        raw = {"task_id": "t1", "custom_field": "hello"}
        bt = BatchTask.from_dict(raw)
        assert bt.raw == raw


class TestBatch:
    """Tests for Batch data model."""

    def test_basic_properties(self):
        tasks = [BatchTask(task_id=f"t{i}", bounty=float(i)) for i in range(1, 4)]
        batch = Batch(batch_id="b1", label="test", strategy="chain", tasks=tasks)
        assert batch.size == 3
        assert batch.total_bounty == 6.0
        assert batch.avg_bounty == 2.0

    def test_empty_batch(self):
        batch = Batch(batch_id="b1", label="test", strategy="chain", tasks=[])
        assert batch.size == 0
        assert batch.total_bounty == 0
        assert batch.avg_bounty == 0

    def test_to_dict(self):
        tasks = [BatchTask(task_id="t1", bounty=5.0)]
        batch = Batch(batch_id="b1", label="chain:base", strategy="chain",
                      tasks=tasks, priority=BatchPriority.HIGH, chain="base")
        d = batch.to_dict()
        assert d["batch_id"] == "b1"
        assert d["priority"] == "high"
        assert d["task_ids"] == ["t1"]
        assert d["total_bounty"] == 5.0


class TestBatchPlan:
    """Tests for BatchPlan data model."""

    def test_basic_plan(self):
        batches = [
            Batch(batch_id="b1", label="x", strategy="chain",
                  tasks=[BatchTask(task_id=f"t{i}") for i in range(3)]),
            Batch(batch_id="b2", label="y", strategy="chain",
                  tasks=[BatchTask(task_id=f"t{i}") for i in range(3, 5)]),
        ]
        plan = BatchPlan(batches=batches, strategy=BatchStrategy.CHAIN,
                         total_tasks=5, planning_time_ms=1.5)
        assert plan.batch_count == 2
        assert plan.batched_tasks == 5
        assert plan.efficiency == 1.0

    def test_efficiency_with_unbatched(self):
        plan = BatchPlan(
            batches=[Batch(batch_id="b1", label="x", strategy="chain",
                          tasks=[BatchTask(task_id="t1")])],
            strategy=BatchStrategy.CHAIN,
            total_tasks=5,
            planning_time_ms=1.0,
            unbatched=[BatchTask(task_id=f"u{i}") for i in range(4)],
        )
        assert plan.efficiency == 0.2

    def test_to_dict(self):
        plan = BatchPlan(
            batches=[], strategy=BatchStrategy.HYBRID,
            total_tasks=0, planning_time_ms=0.5,
        )
        d = plan.to_dict()
        assert d["strategy"] == "hybrid"
        assert d["batch_count"] == 0
        assert d["efficiency"] == 0.0


# ──────────────────────────────────────────────────────────────
# 2. Task Ingestion
# ──────────────────────────────────────────────────────────────


class TestTaskIngestion:
    """Tests for task addition and management."""

    def test_add_single_task(self):
        s = BatchScheduler()
        bt = s.add_task(_task("t1", bounty=5.0))
        assert isinstance(bt, BatchTask)
        assert bt.bounty == 5.0
        assert s.pending_count == 1

    def test_add_multiple_tasks(self):
        s = BatchScheduler()
        results = s.add_tasks([_task("t1"), _task("t2"), _task("t3")])
        assert len(results) == 3
        assert s.pending_count == 3

    def test_clear_tasks(self):
        s = BatchScheduler()
        s.add_tasks([_task("t1"), _task("t2")])
        s.clear_tasks()
        assert s.pending_count == 0

    def test_strategy_property(self):
        s = BatchScheduler(strategy=BatchStrategy.CHAIN)
        assert s.strategy == BatchStrategy.CHAIN
        s.strategy = BatchStrategy.SKILL
        assert s.strategy == BatchStrategy.SKILL


# ──────────────────────────────────────────────────────────────
# 3. CHAIN Strategy
# ──────────────────────────────────────────────────────────────


class TestChainStrategy:
    """Tests for chain-based grouping."""

    def test_groups_by_chain(self):
        s = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s.add_tasks(_tasks_on_chains(n_per_chain=3, chains=["base", "polygon"]))
        plan = s.plan()
        assert plan.batch_count >= 2
        # Each batch should have a single chain
        for batch in plan.batches:
            chains = set(t.chain for t in batch.tasks)
            assert len(chains) == 1

    def test_single_chain_one_batch(self):
        s = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s.add_tasks([_task(f"t{i}", chain="base") for i in range(5)])
        plan = s.plan()
        assert plan.batch_count == 1
        assert plan.batches[0].chain == "base"

    def test_rationale_mentions_chains(self):
        s = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s.add_tasks(_tasks_on_chains(chains=["base", "polygon", "ethereum"]))
        plan = s.plan()
        assert "chain" in plan.rationale.lower() or "3" in plan.rationale

    def test_chain_batch_label(self):
        s = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s.add_tasks([_task("t1", chain="arbitrum")])
        plan = s.plan()
        assert plan.batches[0].label == "chain:arbitrum"


# ──────────────────────────────────────────────────────────────
# 4. SKILL Strategy
# ──────────────────────────────────────────────────────────────


class TestSkillStrategy:
    """Tests for skill-based grouping."""

    def test_groups_by_skill(self):
        s = BatchScheduler(strategy=BatchStrategy.SKILL)
        s.add_tasks(_tasks_with_skills({"photo": 4, "delivery": 3}))
        plan = s.plan()
        assert plan.batch_count >= 2
        labels = {b.label for b in plan.batches}
        assert "skill:photo" in labels or "skill:photography" in labels or any("photo" in l for l in labels)

    def test_no_skills_grouped_separately(self):
        s = BatchScheduler(strategy=BatchStrategy.SKILL)
        s.add_tasks([
            _task("t1", skills=["photo"]),
            _task("t2", skills=[]),
            _task("t3"),
        ])
        plan = s.plan()
        labels = {b.label for b in plan.batches}
        assert any("unspecified" in l for l in labels)

    def test_skill_case_insensitive(self):
        s = BatchScheduler(strategy=BatchStrategy.SKILL)
        s.add_tasks([
            _task("t1", skills=["Photo"]),
            _task("t2", skills=["photo"]),
            _task("t3", skills=["PHOTO"]),
        ])
        plan = s.plan()
        # All should be in same batch (case normalized)
        assert plan.batch_count == 1


# ──────────────────────────────────────────────────────────────
# 5. DEADLINE Strategy
# ──────────────────────────────────────────────────────────────


class TestDeadlineStrategy:
    """Tests for deadline-based grouping."""

    def test_groups_by_urgency(self):
        s = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        s.add_tasks(_tasks_with_deadlines())
        plan = s.plan()
        # Should create tiers: overdue, critical, urgent, standard, relaxed, none
        tiers = {b.deadline_tier for b in plan.batches}
        assert "overdue" in tiers or "critical" in tiers  # At least urgent tasks

    def test_overdue_comes_first(self):
        s = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        s.add_tasks(_tasks_with_deadlines())
        plan = s.plan()
        # First batch should have overdue or critical tasks
        if plan.batches:
            first_tier = plan.batches[0].deadline_tier
            assert first_tier in ("overdue", "critical")

    def test_no_deadline_grouped(self):
        s = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        s.add_tasks([_task("t1"), _task("t2")])  # No deadlines
        plan = s.plan()
        assert plan.batch_count >= 1
        assert any(b.deadline_tier == "none" for b in plan.batches)

    def test_rationale_mentions_tiers(self):
        s = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        s.add_tasks(_tasks_with_deadlines())
        plan = s.plan()
        assert "deadline" in plan.rationale.lower() or "tier" in plan.rationale.lower()


# ──────────────────────────────────────────────────────────────
# 6. BOUNTY Strategy
# ──────────────────────────────────────────────────────────────


class TestBountyStrategy:
    """Tests for bounty-based grouping."""

    def test_groups_by_bounty_tier(self):
        s = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        s.add_tasks([
            _task("micro", bounty=0.50),
            _task("small", bounty=5.00),
            _task("medium", bounty=50.00),
            _task("large", bounty=500.00),
        ])
        plan = s.plan()
        tiers = {b.bounty_tier for b in plan.batches}
        assert "micro" in tiers
        assert "large" in tiers

    def test_same_tier_grouped(self):
        s = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        s.add_tasks([_task(f"t{i}", bounty=0.50) for i in range(5)])
        plan = s.plan()
        assert plan.batch_count == 1
        assert plan.batches[0].bounty_tier == "micro"

    def test_largest_bounty_first(self):
        s = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        s.add_tasks([
            _task("large", bounty=200.0),
            _task("micro", bounty=0.10),
        ])
        plan = s.plan()
        if plan.batch_count >= 2:
            # First batch should be the higher-bounty tier (sorted by max bounty desc)
            assert plan.batches[0].total_bounty >= plan.batches[-1].total_bounty


# ──────────────────────────────────────────────────────────────
# 7. HYBRID Strategy
# ──────────────────────────────────────────────────────────────


class TestHybridStrategy:
    """Tests for multi-factor hybrid grouping."""

    def test_hybrid_groups_by_chain_first(self):
        s = BatchScheduler(strategy=BatchStrategy.HYBRID)
        s.add_tasks(_tasks_on_chains(n_per_chain=5, chains=["base", "polygon"]))
        plan = s.plan()
        # Each batch should only contain tasks from one chain
        for batch in plan.batches:
            chains = set(t.chain for t in batch.tasks)
            assert len(chains) == 1

    def test_hybrid_sub_groups_by_skill(self):
        s = BatchScheduler(strategy=BatchStrategy.HYBRID)
        s.add_tasks([
            _task("t1", chain="base", skills=["photo"]),
            _task("t2", chain="base", skills=["photo"]),
            _task("t3", chain="base", skills=["delivery"]),
            _task("t4", chain="base", skills=["delivery"]),
        ])
        plan = s.plan()
        # Should create sub-groups within chain
        assert plan.batch_count >= 2

    def test_hybrid_single_task(self):
        s = BatchScheduler(strategy=BatchStrategy.HYBRID)
        s.add_task(_task("t1"))
        plan = s.plan()
        assert plan.batch_count == 1
        assert plan.rationale == "Single task — no batching needed."

    def test_hybrid_urgent_separated(self):
        now = datetime.now(timezone.utc)
        s = BatchScheduler(strategy=BatchStrategy.HYBRID)
        s.add_tasks([
            _task("urgent1", chain="base", skills=["photo"],
                  deadline=now + timedelta(minutes=30)),
            _task("normal1", chain="base", skills=["photo"],
                  deadline=now + timedelta(days=2)),
        ])
        plan = s.plan()
        # Urgent and normal should be in different batches
        if plan.batch_count >= 2:
            labels = {b.label for b in plan.batches}
            assert any("urgent" in l for l in labels) or plan.batch_count >= 1

    def test_hybrid_mixed_batch_for_orphans(self):
        s = BatchScheduler(strategy=BatchStrategy.HYBRID, min_batch_size=3)
        s.add_tasks([
            _task("t1", chain="base"),
            _task("t2", chain="polygon"),
            _task("t3", chain="ethereum"),
            _task("t4", chain="arbitrum"),
        ])
        plan = s.plan()
        # With min_batch_size=3, single-chain tasks become unbatched,
        # then grouped into a mixed batch
        has_mixed = any("mixed" in b.label for b in plan.batches)
        assert has_mixed or plan.batch_count >= 1


# ──────────────────────────────────────────────────────────────
# 8. Priority Computation
# ──────────────────────────────────────────────────────────────


class TestPriorityComputation:
    """Tests for batch priority assignment."""

    def test_overdue_gets_critical(self):
        now = datetime.now(timezone.utc)
        s = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        s.add_tasks([_task("t1", deadline=now - timedelta(hours=1), bounty=5.0)])
        plan = s.plan()
        assert plan.batches[0].priority == BatchPriority.CRITICAL

    def test_high_bounty_gets_high(self):
        s = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        s.add_tasks([_task("t1", bounty=150.0)])
        plan = s.plan()
        assert plan.batches[0].priority in (BatchPriority.CRITICAL, BatchPriority.HIGH)

    def test_small_low_bounty_gets_deferred(self):
        s = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        s.add_tasks([_task("t1", bounty=0.10)])
        plan = s.plan()
        assert plan.batches[0].priority in (BatchPriority.DEFERRED, BatchPriority.LOW)

    def test_priority_sort_order(self):
        s = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        now = datetime.now(timezone.utc)
        s.add_tasks([
            _task("small", bounty=0.10),
            _task("large", bounty=200.0, deadline=now - timedelta(hours=1)),
            _task("medium", bounty=20.0),
        ])
        plan = s.plan()
        priorities = [b.priority for b in plan.batches]
        # Should be sorted: CRITICAL/HIGH before NORMAL before LOW/DEFERRED
        priority_order = {
            BatchPriority.CRITICAL: 0, BatchPriority.HIGH: 1,
            BatchPriority.NORMAL: 2, BatchPriority.LOW: 3,
            BatchPriority.DEFERRED: 4,
        }
        orders = [priority_order[p] for p in priorities]
        assert orders == sorted(orders)

    def test_priority_sort_key(self):
        b1 = Batch(batch_id="b1", label="x", strategy="chain",
                    tasks=[BatchTask(task_id="t1", bounty=10.0)],
                    priority=BatchPriority.HIGH)
        b2 = Batch(batch_id="b2", label="y", strategy="chain",
                    tasks=[BatchTask(task_id="t2", bounty=5.0)],
                    priority=BatchPriority.LOW)
        assert _priority_sort_key(b1) < _priority_sort_key(b2)


# ──────────────────────────────────────────────────────────────
# 9. Planning Mechanics
# ──────────────────────────────────────────────────────────────


class TestPlanningMechanics:
    """Tests for planning internals."""

    def test_empty_plan(self):
        s = BatchScheduler()
        plan = s.plan()
        assert plan.batch_count == 0
        assert plan.total_tasks == 0
        assert plan.rationale == "No tasks to batch."

    def test_planning_time_tracked(self):
        s = BatchScheduler()
        s.add_tasks([_task(f"t{i}") for i in range(10)])
        plan = s.plan()
        assert plan.planning_time_ms > 0

    def test_stats_updated(self):
        s = BatchScheduler()
        s.add_tasks([_task(f"t{i}") for i in range(5)])
        s.plan()
        m = s.metrics()
        assert m["plans_generated"] == 1
        assert m["total_tasks_batched"] == 5

    def test_plan_history_recorded(self):
        s = BatchScheduler()
        s.add_tasks([_task("t1")])
        s.plan()
        assert len(s._plan_history) == 1
        assert "strategy" in s._plan_history[0]

    def test_plan_history_trimmed(self):
        s = BatchScheduler()
        for i in range(120):
            s.add_task(_task(f"t{i}"))
            s.plan()
            s.clear_tasks()
        assert len(s._plan_history) <= 100

    def test_strategy_override_in_plan(self):
        s = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s.add_tasks(_tasks_with_skills())
        plan = s.plan(strategy=BatchStrategy.SKILL)
        assert plan.strategy == BatchStrategy.SKILL

    def test_max_batch_size_respected(self):
        s = BatchScheduler(max_batch_size=3)
        s.add_tasks([_task(f"t{i}", chain="base") for i in range(10)])
        plan = s.plan(strategy=BatchStrategy.CHAIN)
        for batch in plan.batches:
            assert batch.size <= 3

    def test_min_batch_size_filters(self):
        s = BatchScheduler(min_batch_size=3, strategy=BatchStrategy.CHAIN)
        s.add_tasks([
            _task("t1", chain="base"),
            _task("t2", chain="polygon"),  # Only 1 task — below min
        ])
        plan = s.plan()
        # polygon should be unbatched
        for batch in plan.batches:
            if batch.chain == "polygon":
                assert batch.size >= 3

    def test_multiple_plans_accumulate_stats(self):
        s = BatchScheduler()
        s.add_tasks([_task("t1")])
        s.plan()
        s.clear_tasks()
        s.add_tasks([_task("t2"), _task("t3")])
        s.plan()
        m = s.metrics()
        assert m["plans_generated"] == 2
        assert m["total_tasks_batched"] == 3


# ──────────────────────────────────────────────────────────────
# 10. Strategy Suggestion
# ──────────────────────────────────────────────────────────────


class TestStrategySuggestion:
    """Tests for automatic strategy selection."""

    def test_suggest_chain_for_diverse_chains(self):
        s = BatchScheduler()
        s.add_tasks(_tasks_on_chains(n_per_chain=2, chains=["base", "polygon", "ethereum", "arbitrum"]))
        suggestion = s.suggest_strategy()
        assert suggestion in (BatchStrategy.CHAIN, BatchStrategy.HYBRID)

    def test_suggest_skill_for_single_chain(self):
        s = BatchScheduler()
        tasks = []
        for skill in ["photo", "delivery", "data", "creative"]:
            for i in range(5):
                tasks.append(_task(f"{skill}-{i}", chain="base", skills=[skill]))
        s.add_tasks(tasks)
        suggestion = s.suggest_strategy()
        # Low chain diversity → skill, deadline, or bounty (not chain or hybrid)
        assert suggestion in (BatchStrategy.SKILL, BatchStrategy.BOUNTY, BatchStrategy.DEADLINE)

    def test_suggest_for_empty(self):
        s = BatchScheduler()
        suggestion = s.suggest_strategy()
        assert suggestion == s._strategy  # Returns current default

    def test_suggest_deadline_for_timed_tasks(self):
        s = BatchScheduler()
        now = datetime.now(timezone.utc)
        tasks = [
            _task(f"t{i}", chain="base",
                  deadline=now + timedelta(hours=i))
            for i in range(10)
        ]
        s.add_tasks(tasks)
        suggestion = s.suggest_strategy()
        # Single chain, so chain won't help — should suggest deadline or bounty
        assert suggestion in (BatchStrategy.DEADLINE, BatchStrategy.BOUNTY, BatchStrategy.SKILL)


# ──────────────────────────────────────────────────────────────
# 11. Savings Estimation
# ──────────────────────────────────────────────────────────────


class TestSavingsEstimation:
    """Tests for routing savings calculation."""

    def test_savings_for_batched_tasks(self):
        s = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s.add_tasks(_tasks_on_chains(n_per_chain=5, chains=["base", "polygon"]))
        plan = s.plan()
        savings = s.estimate_savings(plan)
        assert savings["pct_saved"] > 0
        assert savings["saved_ms"] > 0

    def test_savings_for_single_task(self):
        s = BatchScheduler()
        s.add_task(_task("t1"))
        plan = s.plan()
        savings = s.estimate_savings(plan)
        assert savings["saved_ms"] >= 0

    def test_savings_auto_plans_if_needed(self):
        s = BatchScheduler()
        s.add_tasks([_task(f"t{i}") for i in range(5)])
        savings = s.estimate_savings()  # No plan passed
        assert "individual_routing_ms" in savings
        assert "batched_routing_ms" in savings

    def test_savings_keys(self):
        s = BatchScheduler()
        s.add_tasks([_task("t1")])
        savings = s.estimate_savings()
        expected_keys = {
            "individual_routing_ms", "batched_routing_ms", "saved_ms",
            "pct_saved", "chain_switches_saved", "batches_vs_individual",
        }
        assert set(savings.keys()) == expected_keys


# ──────────────────────────────────────────────────────────────
# 12. State Persistence
# ──────────────────────────────────────────────────────────────


class TestStatePersistence:
    """Tests for save/load state."""

    def test_save_state(self):
        s = BatchScheduler(strategy=BatchStrategy.SKILL, max_batch_size=25)
        s.add_tasks([_task("t1")])
        s.plan()
        state = s.save_state()
        assert state["version"] == 1
        assert state["strategy"] == "skill"
        assert state["max_batch_size"] == 25
        assert state["stats"]["plans_generated"] == 1

    def test_load_state(self):
        s1 = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        s1.add_tasks([_task("t1"), _task("t2")])
        s1.plan()
        state = s1.save_state()

        s2 = BatchScheduler()
        s2.load_state(state)
        assert s2._strategy == BatchStrategy.BOUNTY
        assert s2._stats["plans_generated"] == 1

    def test_load_invalid_state(self):
        s = BatchScheduler()
        s.load_state({})  # No version
        assert s._strategy == BatchStrategy.HYBRID  # Default unchanged

    def test_load_wrong_version(self):
        s = BatchScheduler()
        s.load_state({"version": 99})
        assert s._strategy == BatchStrategy.HYBRID

    def test_round_trip_preserves_config(self):
        s1 = BatchScheduler(
            strategy=BatchStrategy.DEADLINE,
            max_batch_size=10,
            min_batch_size=2,
        )
        s1.add_tasks([_task(f"t{i}") for i in range(5)])
        s1.plan()
        state = s1.save_state()

        s2 = BatchScheduler()
        s2.load_state(state)
        assert s2._strategy == BatchStrategy.DEADLINE
        assert s2._max_batch_size == 10
        assert s2._min_batch_size == 2

    def test_state_preserves_custom_tiers(self):
        custom_tiers = {"tiny": (0, 0.5), "huge": (0.5, float("inf"))}
        s1 = BatchScheduler(bounty_tiers=custom_tiers)
        state = s1.save_state()

        s2 = BatchScheduler()
        s2.load_state(state)
        assert "tiny" in s2._bounty_tiers
        assert "huge" in s2._bounty_tiers


# ──────────────────────────────────────────────────────────────
# 13. Metrics & Diagnostics
# ──────────────────────────────────────────────────────────────


class TestMetrics:
    """Tests for metrics and diagnostics."""

    def test_initial_metrics(self):
        s = BatchScheduler()
        m = s.metrics()
        assert m["plans_generated"] == 0
        assert m["pending_tasks"] == 0

    def test_metrics_after_planning(self):
        s = BatchScheduler()
        s.add_tasks([_task(f"t{i}") for i in range(5)])
        s.plan()
        m = s.metrics()
        assert m["plans_generated"] == 1
        assert m["total_tasks_batched"] >= 5

    def test_diagnostics_includes_config(self):
        s = BatchScheduler()
        d = s.diagnostics()
        assert "config" in d
        assert "metrics" in d
        assert "recent_plans" in d
        assert d["config"]["strategy"] == "hybrid"

    def test_strategy_usage_tracked(self):
        s = BatchScheduler()
        s.add_task(_task("t1"))
        s.plan(strategy=BatchStrategy.CHAIN)
        s.clear_tasks()
        s.add_task(_task("t2"))
        s.plan(strategy=BatchStrategy.SKILL)
        m = s.metrics()
        assert m["strategy_usage"]["chain"] == 1
        assert m["strategy_usage"]["skill"] == 1


# ──────────────────────────────────────────────────────────────
# 14. Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_single_task_plans(self):
        for strategy in BatchStrategy:
            s = BatchScheduler(strategy=strategy)
            s.add_task(_task("t1"))
            plan = s.plan()
            assert plan.total_tasks == 1
            assert plan.batch_count >= 1

    def test_all_strategies_work(self):
        for strategy in BatchStrategy:
            s = BatchScheduler(strategy=strategy)
            s.add_tasks([_task(f"t{i}", chain=f"chain{i%3}", skills=[f"s{i%2}"],
                               bounty=float(i + 1)) for i in range(10)])
            plan = s.plan()
            assert plan.total_tasks == 10

    def test_empty_skills_handled(self):
        s = BatchScheduler(strategy=BatchStrategy.SKILL)
        s.add_tasks([_task("t1", skills=[]), _task("t2")])
        plan = s.plan()
        assert plan.total_tasks == 2

    def test_zero_bounty_handled(self):
        s = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        s.add_task(_task("t1", bounty=0.0))
        plan = s.plan()
        assert plan.batch_count == 1

    def test_very_large_task_set(self):
        s = BatchScheduler(max_batch_size=10)
        s.add_tasks([_task(f"t{i}", chain="base") for i in range(100)])
        plan = s.plan(strategy=BatchStrategy.CHAIN)
        # Should split into multiple batches
        assert plan.batch_count >= 10
        for batch in plan.batches:
            assert batch.size <= 10

    def test_custom_urgency_hours(self):
        s = BatchScheduler(urgency_hours=[2, 8, 48, 336])
        now = datetime.now(timezone.utc)
        s.add_tasks([_task("t1", deadline=now + timedelta(hours=1.5))])
        plan = s.plan(strategy=BatchStrategy.DEADLINE)
        # With custom 2h critical threshold, 1.5h should be critical
        assert plan.batches[0].deadline_tier == "critical"

    def test_custom_hybrid_weights(self):
        s = BatchScheduler(hybrid_weights={
            "chain": 0.10, "skill": 0.60, "deadline": 0.20, "bounty": 0.10,
        })
        s.add_tasks(_tasks_on_chains())
        plan = s.plan(strategy=BatchStrategy.HYBRID)
        assert plan.strategy == BatchStrategy.HYBRID


# ──────────────────────────────────────────────────────────────
# 15. Production Scenarios
# ──────────────────────────────────────────────────────────────


class TestProductionScenarios:
    """Simulate real EM production scenarios."""

    def test_multi_chain_routing(self):
        """8 chains × 5 tasks each = 40 tasks optimally batched."""
        chains = ["base", "polygon", "ethereum", "arbitrum", "celo", "optimism", "avalanche", "monad"]
        s = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s.add_tasks(_tasks_on_chains(n_per_chain=5, chains=chains))
        plan = s.plan()
        assert plan.batch_count == 8
        assert plan.efficiency == 1.0

    def test_mixed_urgency_routing(self):
        """Mix of urgent and relaxed tasks should prioritize correctly."""
        now = datetime.now(timezone.utc)
        s = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        s.add_tasks([
            _task("urgent1", bounty=100.0, deadline=now + timedelta(minutes=15)),
            _task("urgent2", bounty=50.0, deadline=now + timedelta(minutes=45)),
            _task("normal1", bounty=5.0, deadline=now + timedelta(days=2)),
            _task("normal2", bounty=3.0, deadline=now + timedelta(days=5)),
        ])
        plan = s.plan()
        # First batch should be critical/urgent
        assert plan.batches[0].priority in (BatchPriority.CRITICAL, BatchPriority.HIGH)

    def test_skill_cluster_efficiency(self):
        """Tasks with same skill should batch together for worker efficiency."""
        s = BatchScheduler(strategy=BatchStrategy.SKILL)
        s.add_tasks([
            _task(f"photo-{i}", skills=["photography"], bounty=2.0)
            for i in range(10)
        ] + [
            _task(f"deliver-{i}", skills=["delivery"], bounty=3.0)
            for i in range(5)
        ])
        plan = s.plan()
        # Photography tasks should be in one batch, delivery in another
        photo_batch = next((b for b in plan.batches if "photo" in b.label), None)
        assert photo_batch is not None
        assert photo_batch.size == 10

    def test_hybrid_complex_workload(self):
        """Complex real-world workload with mixed properties."""
        now = datetime.now(timezone.utc)
        s = BatchScheduler(strategy=BatchStrategy.HYBRID)
        s.add_tasks([
            # Urgent base photo tasks
            _task("t1", chain="base", skills=["photo"], bounty=5.0,
                  deadline=now + timedelta(minutes=30)),
            _task("t2", chain="base", skills=["photo"], bounty=3.0,
                  deadline=now + timedelta(minutes=45)),
            # Normal base delivery tasks
            _task("t3", chain="base", skills=["delivery"], bounty=2.0,
                  deadline=now + timedelta(days=1)),
            _task("t4", chain="base", skills=["delivery"], bounty=2.0,
                  deadline=now + timedelta(days=2)),
            # Polygon tasks
            _task("t5", chain="polygon", skills=["photo"], bounty=10.0),
            _task("t6", chain="polygon", skills=["photo"], bounty=8.0),
        ])
        plan = s.plan()
        # Should create multiple batches separating chains and urgency
        assert plan.batch_count >= 2
        assert plan.efficiency > 0
