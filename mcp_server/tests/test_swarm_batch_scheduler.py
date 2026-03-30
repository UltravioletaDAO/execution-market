"""
Tests for BatchScheduler — Module #59
=======================================

Comprehensive tests covering all batching strategies, priority
computation, persistence, metrics, and edge cases.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from mcp_server.swarm.batch_scheduler import (
    Batch,
    BatchPlan,
    BatchPriority,
    BatchScheduler,
    BatchStrategy,
    BatchTask,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


def _task(
    task_id="t1",
    title="Test Task",
    bounty=5.0,
    chain="base",
    skills=None,
    deadline=None,
    evidence_types=None,
):
    """Create a minimal task dict."""
    d = {
        "task_id": task_id,
        "title": title,
        "description": f"Description for {title}",
        "bounty": bounty,
        "chain": chain,
        "skills": skills or [],
        "evidence_types": evidence_types or ["photo"],
    }
    if deadline:
        d["deadline"] = deadline.isoformat()
    return d


def _future(hours=24):
    """Return a datetime N hours from now."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def _past(hours=1):
    """Return a datetime N hours ago."""
    return datetime.now(timezone.utc) - timedelta(hours=hours)


# ──────────────────────────────────────────────────────────────
# 1. BatchTask Parsing
# ──────────────────────────────────────────────────────────────


class TestBatchTaskParsing:
    def test_basic_parsing(self):
        bt = BatchTask.from_dict(_task())
        assert bt.task_id == "t1"
        assert bt.title == "Test Task"
        assert bt.bounty == 5.0
        assert bt.chain == "base"

    def test_alternative_field_names(self):
        d = {"id": "x1", "bounty_amount": 3.0, "network": "polygon"}
        bt = BatchTask.from_dict(d)
        assert bt.task_id == "x1"
        assert bt.bounty == 3.0
        assert bt.chain == "polygon"

    def test_skills_from_string(self):
        d = {"task_id": "t1", "skills": "photography, delivery, data entry"}
        bt = BatchTask.from_dict(d)
        assert bt.skills == ["photography", "delivery", "data entry"]

    def test_skills_from_list(self):
        d = {"task_id": "t1", "skills": ["coding", "testing"]}
        bt = BatchTask.from_dict(d)
        assert bt.skills == ["coding", "testing"]

    def test_deadline_iso_string(self):
        dl = "2026-04-01T12:00:00Z"
        bt = BatchTask.from_dict({"task_id": "t1", "deadline": dl})
        assert bt.deadline is not None
        assert bt.deadline.year == 2026

    def test_deadline_datetime_object(self):
        dl = datetime(2026, 5, 1, tzinfo=timezone.utc)
        bt = BatchTask.from_dict({"task_id": "t1", "deadline": dl})
        assert bt.deadline == dl

    def test_deadline_timestamp(self):
        ts = 1750000000.0
        bt = BatchTask.from_dict({"task_id": "t1", "deadline": ts})
        assert bt.deadline is not None

    def test_invalid_deadline_ignored(self):
        bt = BatchTask.from_dict({"task_id": "t1", "deadline": "not-a-date"})
        assert bt.deadline is None

    def test_raw_dict_preserved(self):
        d = _task(task_id="raw1")
        bt = BatchTask.from_dict(d)
        assert bt.raw == d

    def test_chain_lowercase(self):
        bt = BatchTask.from_dict({"task_id": "t1", "chain": "ETHEREUM"})
        assert bt.chain == "ethereum"


# ──────────────────────────────────────────────────────────────
# 2. Chain Strategy
# ──────────────────────────────────────────────────────────────


class TestChainStrategy:
    def test_single_chain_single_batch(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}", chain="base") for i in range(5)])
        plan = scheduler.plan()
        assert plan.batch_count == 1
        assert plan.batches[0].chain == "base"
        assert plan.batches[0].size == 5

    def test_multiple_chains_multiple_batches(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([
            _task("t1", chain="base"),
            _task("t2", chain="base"),
            _task("t3", chain="polygon"),
            _task("t4", chain="ethereum"),
            _task("t5", chain="polygon"),
        ])
        plan = scheduler.plan()
        assert plan.batch_count == 3
        chains = {b.chain for b in plan.batches}
        assert chains == {"base", "polygon", "ethereum"}

    def test_chain_batch_sizes(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}", chain="base") for i in range(3)])
        scheduler.add_tasks([_task(f"t{i+3}", chain="polygon") for i in range(7)])
        plan = scheduler.plan()
        sizes = {b.chain: b.size for b in plan.batches}
        assert sizes["base"] == 3
        assert sizes["polygon"] == 7

    def test_max_batch_size_splitting(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN, max_batch_size=3)
        scheduler.add_tasks([_task(f"t{i}", chain="base") for i in range(8)])
        plan = scheduler.plan()
        assert plan.batch_count == 3  # 3 + 3 + 2
        assert all(b.chain == "base" for b in plan.batches)
        sizes = sorted([b.size for b in plan.batches], reverse=True)
        assert sizes == [3, 3, 2]


# ──────────────────────────────────────────────────────────────
# 3. Skill Strategy
# ──────────────────────────────────────────────────────────────


class TestSkillStrategy:
    def test_skill_grouping(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.SKILL)
        scheduler.add_tasks([
            _task("t1", skills=["photography"]),
            _task("t2", skills=["photography"]),
            _task("t3", skills=["delivery"]),
            _task("t4", skills=["coding"]),
        ])
        plan = scheduler.plan()
        clusters = {b.skill_cluster for b in plan.batches}
        assert "photography" in clusters
        assert "delivery" in clusters
        assert "coding" in clusters

    def test_no_skills_grouped_as_unspecified(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.SKILL)
        scheduler.add_tasks([
            _task("t1", skills=[]),
            _task("t2", skills=[]),
        ])
        plan = scheduler.plan()
        assert plan.batch_count == 1
        assert plan.batches[0].skill_cluster == "unspecified"

    def test_primary_skill_used(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.SKILL)
        scheduler.add_tasks([
            _task("t1", skills=["photography", "editing"]),
            _task("t2", skills=["photography", "writing"]),
        ])
        plan = scheduler.plan()
        assert plan.batch_count == 1
        assert plan.batches[0].skill_cluster == "photography"

    def test_case_insensitive_skills(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.SKILL)
        scheduler.add_tasks([
            _task("t1", skills=["Photography"]),
            _task("t2", skills=["PHOTOGRAPHY"]),
        ])
        plan = scheduler.plan()
        assert plan.batch_count == 1


# ──────────────────────────────────────────────────────────────
# 4. Deadline Strategy
# ──────────────────────────────────────────────────────────────


class TestDeadlineStrategy:
    def test_overdue_tasks(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([
            _task("t1", deadline=_past(2)),
            _task("t2", deadline=_past(1)),
        ])
        plan = scheduler.plan()
        assert plan.batch_count == 1
        assert plan.batches[0].deadline_tier == "overdue"

    def test_critical_tier(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([
            _task("t1", deadline=_future(0.5)),  # 30 min from now
        ])
        plan = scheduler.plan()
        assert plan.batches[0].deadline_tier == "critical"

    def test_urgent_tier(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([
            _task("t1", deadline=_future(3)),  # 3h from now
        ])
        plan = scheduler.plan()
        assert plan.batches[0].deadline_tier == "urgent"

    def test_standard_tier(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([
            _task("t1", deadline=_future(12)),
        ])
        plan = scheduler.plan()
        assert plan.batches[0].deadline_tier == "standard"

    def test_relaxed_tier(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([
            _task("t1", deadline=_future(48)),
        ])
        plan = scheduler.plan()
        assert plan.batches[0].deadline_tier == "relaxed"

    def test_no_deadline_tasks(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([
            _task("t1"),
            _task("t2"),
        ])
        plan = scheduler.plan()
        assert plan.batches[0].deadline_tier == "none"

    def test_mixed_deadline_tiers(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([
            _task("t1", deadline=_past(1)),
            _task("t2", deadline=_future(0.5)),
            _task("t3", deadline=_future(12)),
            _task("t4"),
        ])
        plan = scheduler.plan()
        tiers = [b.deadline_tier for b in plan.batches]
        assert "overdue" in tiers
        assert "critical" in tiers

    def test_overdue_first_in_ordering(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([
            _task("t1", deadline=_future(48)),
            _task("t2", deadline=_past(1)),
        ])
        plan = scheduler.plan()
        # After priority computation, overdue should rank higher
        assert plan.batches[0].deadline_tier == "overdue"


# ──────────────────────────────────────────────────────────────
# 5. Bounty Strategy
# ──────────────────────────────────────────────────────────────


class TestBountyStrategy:
    def test_bounty_tiers(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        scheduler.add_tasks([
            _task("t1", bounty=0.50),   # micro
            _task("t2", bounty=5.00),   # small
            _task("t3", bounty=50.00),  # medium
            _task("t4", bounty=500.00), # large
        ])
        plan = scheduler.plan()
        tiers = {b.bounty_tier for b in plan.batches}
        assert tiers == {"micro", "small", "medium", "large"}

    def test_large_first_ordering(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        scheduler.add_tasks([
            _task("t1", bounty=0.50),
            _task("t2", bounty=500.00),
        ])
        plan = scheduler.plan()
        # Large bounty should have higher priority
        assert plan.batches[0].bounty_tier == "large"

    def test_custom_bounty_tiers(self):
        custom_tiers = {
            "tiny": (0, 5),
            "big": (5, float("inf")),
        }
        scheduler = BatchScheduler(
            strategy=BatchStrategy.BOUNTY, bounty_tiers=custom_tiers
        )
        scheduler.add_tasks([
            _task("t1", bounty=2.0),
            _task("t2", bounty=10.0),
        ])
        plan = scheduler.plan()
        tiers = {b.bounty_tier for b in plan.batches}
        assert tiers == {"tiny", "big"}


# ──────────────────────────────────────────────────────────────
# 6. Hybrid Strategy
# ──────────────────────────────────────────────────────────────


class TestHybridStrategy:
    def test_chain_then_skill_grouping(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.HYBRID)
        scheduler.add_tasks([
            _task("t1", chain="base", skills=["photography"]),
            _task("t2", chain="base", skills=["photography"]),
            _task("t3", chain="base", skills=["delivery"]),
            _task("t4", chain="polygon", skills=["photography"]),
        ])
        plan = scheduler.plan()
        # Should create separate batches for base/photography, base/delivery, polygon/photography
        assert plan.batch_count >= 3

    def test_urgent_separated_from_normal(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.HYBRID)
        scheduler.add_tasks([
            _task("t1", chain="base", skills=["photo"], deadline=_future(0.5)),
            _task("t2", chain="base", skills=["photo"], deadline=_future(48)),
        ])
        plan = scheduler.plan()
        # Urgent and normal should be in separate batches
        assert plan.batch_count == 2

    def test_single_task_handled(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.HYBRID)
        scheduler.add_task(_task("t1"))
        plan = scheduler.plan()
        assert plan.batch_count == 1
        assert plan.batches[0].size == 1

    def test_empty_tasks(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.HYBRID)
        plan = scheduler.plan()
        assert plan.batch_count == 0
        assert plan.rationale == "No tasks to batch."

    def test_mixed_batch_created_for_singles(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.HYBRID, min_batch_size=2)
        scheduler.add_tasks([
            _task("t1", chain="base"),
            _task("t2", chain="polygon"),
            _task("t3", chain="ethereum"),
        ])
        plan = scheduler.plan()
        # Single-chain tasks may be grouped into mixed batch
        assert plan.batched_tasks + len(plan.unbatched) == 3


# ──────────────────────────────────────────────────────────────
# 7. Priority Computation
# ──────────────────────────────────────────────────────────────


class TestPriorityComputation:
    def test_overdue_is_critical(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([_task("t1", deadline=_past(2))])
        plan = scheduler.plan()
        assert plan.batches[0].priority == BatchPriority.CRITICAL

    def test_high_bounty_is_high(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        scheduler.add_tasks([_task("t1", bounty=150.0)])
        plan = scheduler.plan()
        assert plan.batches[0].priority == BatchPriority.HIGH

    def test_critical_plus_high_bounty_is_critical(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.DEADLINE)
        scheduler.add_tasks([_task("t1", bounty=200.0, deadline=_future(0.5))])
        plan = scheduler.plan()
        assert plan.batches[0].priority == BatchPriority.CRITICAL

    def test_low_bounty_small_batch_is_deferred(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        scheduler.add_tasks([_task("t1", bounty=0.10)])
        plan = scheduler.plan()
        assert plan.batches[0].priority == BatchPriority.DEFERRED

    def test_priority_ordering(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([
            _task("t1", chain="base", bounty=0.10),
            _task("t2", chain="polygon", bounty=200.0),
        ])
        plan = scheduler.plan()
        # High bounty batch should come first
        assert plan.batches[0].total_bounty > plan.batches[1].total_bounty


# ──────────────────────────────────────────────────────────────
# 8. BatchPlan Properties
# ──────────────────────────────────────────────────────────────


class TestBatchPlanProperties:
    def test_efficiency_perfect(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}") for i in range(10)])
        plan = scheduler.plan()
        assert plan.efficiency == 1.0

    def test_to_dict(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task("t1"), _task("t2")])
        plan = scheduler.plan()
        d = plan.to_dict()
        assert "strategy" in d
        assert "batch_count" in d
        assert "total_tasks" in d
        assert "efficiency" in d
        assert "batches" in d
        assert len(d["batches"]) == plan.batch_count

    def test_batch_to_dict(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task("t1", bounty=5.0), _task("t2", bounty=3.0)])
        plan = scheduler.plan()
        bd = plan.batches[0].to_dict()
        assert bd["size"] == 2
        assert bd["total_bounty"] == 8.0
        assert bd["avg_bounty"] == 4.0
        assert "task_ids" in bd

    def test_planning_time_recorded(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}") for i in range(100)])
        plan = scheduler.plan()
        assert plan.planning_time_ms >= 0

    def test_rationale_not_empty(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task("t1")])
        plan = scheduler.plan()
        assert len(plan.rationale) > 0


# ──────────────────────────────────────────────────────────────
# 9. Task Ingestion
# ──────────────────────────────────────────────────────────────


class TestTaskIngestion:
    def test_add_single_task(self):
        scheduler = BatchScheduler()
        bt = scheduler.add_task(_task("t1"))
        assert scheduler.pending_count == 1
        assert bt.task_id == "t1"

    def test_add_multiple_tasks(self):
        scheduler = BatchScheduler()
        tasks = scheduler.add_tasks([_task(f"t{i}") for i in range(5)])
        assert scheduler.pending_count == 5
        assert len(tasks) == 5

    def test_clear_tasks(self):
        scheduler = BatchScheduler()
        scheduler.add_tasks([_task("t1"), _task("t2")])
        assert scheduler.pending_count == 2
        scheduler.clear_tasks()
        assert scheduler.pending_count == 0


# ──────────────────────────────────────────────────────────────
# 10. Metrics & Diagnostics
# ──────────────────────────────────────────────────────────────


class TestMetrics:
    def test_initial_metrics(self):
        scheduler = BatchScheduler()
        m = scheduler.metrics()
        assert m["plans_generated"] == 0
        assert m["total_tasks_batched"] == 0

    def test_metrics_after_plan(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}") for i in range(5)])
        scheduler.plan()
        m = scheduler.metrics()
        assert m["plans_generated"] == 1
        assert m["total_tasks_batched"] == 5

    def test_avg_batch_size(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([
            _task("t1", chain="base"),
            _task("t2", chain="base"),
            _task("t3", chain="polygon"),
        ])
        scheduler.plan()
        m = scheduler.metrics()
        assert m["avg_batch_size"] == pytest.approx(1.5, abs=0.01)

    def test_strategy_usage_tracked(self):
        scheduler = BatchScheduler()
        scheduler.add_tasks([_task("t1")])
        scheduler.plan(strategy=BatchStrategy.CHAIN)
        scheduler.clear_tasks()
        scheduler.add_tasks([_task("t2")])
        scheduler.plan(strategy=BatchStrategy.SKILL)
        m = scheduler.metrics()
        assert m["strategy_usage"]["chain"] == 1
        assert m["strategy_usage"]["skill"] == 1

    def test_diagnostics(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.HYBRID)
        d = scheduler.diagnostics()
        assert "config" in d
        assert "metrics" in d
        assert "recent_plans" in d
        assert d["config"]["strategy"] == "hybrid"


# ──────────────────────────────────────────────────────────────
# 11. Persistence
# ──────────────────────────────────────────────────────────────


class TestPersistence:
    def test_save_and_load(self):
        s1 = BatchScheduler(strategy=BatchStrategy.CHAIN, max_batch_size=25)
        s1.add_tasks([_task(f"t{i}") for i in range(3)])
        s1.plan()

        state = s1.save_state()
        assert state["version"] == 1
        assert state["strategy"] == "chain"

        s2 = BatchScheduler()
        s2.load_state(state)
        assert s2.strategy == BatchStrategy.CHAIN
        assert s2._max_batch_size == 25
        m = s2.metrics()
        assert m["plans_generated"] == 1

    def test_load_invalid_version(self):
        scheduler = BatchScheduler()
        scheduler.load_state({"version": 99})
        assert scheduler.strategy == BatchStrategy.HYBRID  # unchanged default

    def test_load_empty_state(self):
        scheduler = BatchScheduler()
        scheduler.load_state({})
        assert scheduler.pending_count == 0

    def test_load_none(self):
        scheduler = BatchScheduler()
        scheduler.load_state(None)
        assert scheduler.strategy == BatchStrategy.HYBRID

    def test_batch_counter_preserved(self):
        s1 = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s1.add_tasks([_task(f"t{i}") for i in range(3)])
        s1.plan()
        state = s1.save_state()

        s2 = BatchScheduler()
        s2.load_state(state)
        assert s2._batch_counter == s1._batch_counter

    def test_plan_history_preserved(self):
        s1 = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s1.add_tasks([_task("t1")])
        s1.plan()
        state = s1.save_state()
        assert len(state["plan_history"]) == 1


# ──────────────────────────────────────────────────────────────
# 12. Strategy Suggestion
# ──────────────────────────────────────────────────────────────


class TestStrategySuggestion:
    def test_suggest_with_no_tasks(self):
        scheduler = BatchScheduler()
        assert scheduler.suggest_strategy() == scheduler.strategy

    def test_suggest_chain_for_diverse_chains(self):
        scheduler = BatchScheduler()
        scheduler.add_tasks([
            _task("t1", chain="base"),
            _task("t2", chain="polygon"),
            _task("t3", chain="ethereum"),
        ])
        suggestion = scheduler.suggest_strategy()
        assert suggestion in (BatchStrategy.CHAIN, BatchStrategy.HYBRID)

    def test_suggest_skill_for_same_chain_diverse_skills(self):
        scheduler = BatchScheduler()
        # All same chain (base), diverse skills → should suggest SKILL
        # Need > 4 tasks so chain_diversity = 1/N <= 0.25
        scheduler.add_tasks([
            _task("t1", chain="base", skills=["photography"]),
            _task("t2", chain="base", skills=["delivery"]),
            _task("t3", chain="base", skills=["coding"]),
            _task("t4", chain="base", skills=["writing"]),
            _task("t5", chain="base", skills=["testing"]),
        ])
        suggestion = scheduler.suggest_strategy()
        assert suggestion == BatchStrategy.SKILL

    def test_suggest_deadline_when_many_have_deadlines(self):
        scheduler = BatchScheduler()
        # All same chain, no skills, but all have deadlines → DEADLINE
        scheduler.add_tasks([
            _task("t1", chain="base", deadline=_future(1)),
            _task("t2", chain="base", deadline=_future(2)),
            _task("t3", chain="base", deadline=_future(6)),
            _task("t4", chain="base", deadline=_future(12)),
            _task("t5", chain="base", deadline=_future(24)),
        ])
        suggestion = scheduler.suggest_strategy()
        assert suggestion == BatchStrategy.DEADLINE


# ──────────────────────────────────────────────────────────────
# 13. Savings Estimation
# ──────────────────────────────────────────────────────────────


class TestSavingsEstimation:
    def test_savings_with_batching(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}", chain="base") for i in range(10)])
        plan = scheduler.plan()
        savings = scheduler.estimate_savings(plan)
        assert savings["individual_routing_ms"] == 500.0  # 10 * 50ms
        assert savings["batched_routing_ms"] < 500.0
        assert savings["saved_ms"] > 0
        assert savings["pct_saved"] > 0

    def test_savings_without_plan(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}") for i in range(5)])
        savings = scheduler.estimate_savings()
        assert "saved_ms" in savings
        assert "pct_saved" in savings

    def test_chain_switches_saved(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([
            _task("t1", chain="base"),
            _task("t2", chain="base"),
            _task("t3", chain="polygon"),
        ])
        plan = scheduler.plan()
        savings = scheduler.estimate_savings(plan)
        assert savings["chain_switches_saved"] >= 0


# ──────────────────────────────────────────────────────────────
# 14. Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_plan(self):
        scheduler = BatchScheduler()
        plan = scheduler.plan()
        assert plan.batch_count == 0
        assert plan.total_tasks == 0
        assert plan.efficiency == 0

    def test_single_task_all_strategies(self):
        for strategy in BatchStrategy:
            scheduler = BatchScheduler(strategy=strategy)
            scheduler.add_task(_task("t1"))
            plan = scheduler.plan()
            assert plan.total_tasks == 1
            assert plan.batched_tasks >= 0  # May be 0 if min_batch_size > 1
            scheduler.clear_tasks()

    def test_min_batch_size_filter(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN, min_batch_size=3)
        scheduler.add_tasks([
            _task("t1", chain="base"),
            _task("t2", chain="polygon"),
        ])
        plan = scheduler.plan()
        # Both tasks are in single-element chain groups, below min_batch_size
        assert plan.batched_tasks == 0
        assert len(plan.unbatched) == 2

    def test_zero_bounty_tasks(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        scheduler.add_tasks([_task("t1", bounty=0.0)])
        plan = scheduler.plan()
        assert plan.batch_count == 1
        assert plan.batches[0].bounty_tier == "micro"

    def test_very_large_bounty(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.BOUNTY)
        scheduler.add_tasks([_task("t1", bounty=1_000_000.0)])
        plan = scheduler.plan()
        assert plan.batches[0].bounty_tier == "large"

    def test_plan_strategy_override(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task("t1", skills=["photo"]), _task("t2", skills=["photo"])])
        plan = scheduler.plan(strategy=BatchStrategy.SKILL)
        assert plan.strategy == BatchStrategy.SKILL

    def test_multiple_plans_same_tasks(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}") for i in range(5)])
        p1 = scheduler.plan()
        p2 = scheduler.plan()
        assert p1.total_tasks == p2.total_tasks

    def test_large_task_volume(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN, max_batch_size=100)
        scheduler.add_tasks([
            _task(f"t{i}", chain=["base", "polygon", "ethereum"][i % 3])
            for i in range(300)
        ])
        plan = scheduler.plan()
        assert plan.total_tasks == 300
        assert plan.batched_tasks == 300


# ──────────────────────────────────────────────────────────────
# 15. Strategy Setter
# ──────────────────────────────────────────────────────────────


class TestStrategyConfig:
    def test_strategy_getter(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        assert scheduler.strategy == BatchStrategy.CHAIN

    def test_strategy_setter(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.strategy = BatchStrategy.HYBRID
        assert scheduler.strategy == BatchStrategy.HYBRID

    def test_custom_hybrid_weights(self):
        weights = {"chain": 0.6, "skill": 0.2, "deadline": 0.1, "bounty": 0.1}
        scheduler = BatchScheduler(
            strategy=BatchStrategy.HYBRID, hybrid_weights=weights
        )
        assert scheduler._hybrid_weights["chain"] == 0.6

    def test_custom_urgency_hours(self):
        scheduler = BatchScheduler(urgency_hours=[2, 12, 48, 336])
        assert scheduler._urgency_hours == [2, 12, 48, 336]


# ──────────────────────────────────────────────────────────────
# 16. Batch Properties
# ──────────────────────────────────────────────────────────────


class TestBatchProperties:
    def test_total_bounty(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task("t1", bounty=5.0), _task("t2", bounty=3.0)])
        plan = scheduler.plan()
        assert plan.batches[0].total_bounty == 8.0

    def test_avg_bounty(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task("t1", bounty=6.0), _task("t2", bounty=4.0)])
        plan = scheduler.plan()
        assert plan.batches[0].avg_bounty == 5.0

    def test_avg_bounty_empty_batch(self):
        batch = Batch(
            batch_id="b-test",
            label="empty",
            strategy="test",
            tasks=[],
        )
        assert batch.avg_bounty == 0

    def test_batch_size_property(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task(f"t{i}") for i in range(7)])
        plan = scheduler.plan()
        assert plan.batches[0].size == 7


# ──────────────────────────────────────────────────────────────
# 17. Plan History
# ──────────────────────────────────────────────────────────────


class TestPlanHistory:
    def test_history_recorded(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        scheduler.add_tasks([_task("t1")])
        scheduler.plan()
        assert len(scheduler._plan_history) == 1
        entry = scheduler._plan_history[0]
        assert "timestamp" in entry
        assert entry["strategy"] == "chain"
        assert entry["tasks"] == 1

    def test_history_bounded(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        for i in range(110):
            scheduler.add_tasks([_task(f"t{i}")])
            scheduler.plan()
            scheduler.clear_tasks()
        assert len(scheduler._plan_history) <= 100
