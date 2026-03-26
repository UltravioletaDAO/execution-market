"""
ReplayEngine Test Suite
=======================

Comprehensive tests for the historical task decision replay & simulation engine.

Coverage:
- Data types (TaskSnapshot, AgentProfile, RoutingDecision, etc.)
- Agent management (add, remove, reset loads)
- Task routing (scoring, filtering, best-match selection)
- Routing config validation (weights, thresholds)
- Replay pipeline (single task replay, outcome simulation)
- Scenario execution (batch replay, reports, metrics)
- Agent diversity calculation (entropy-based)
- What-if analysis (config comparison)
- I/O helpers (load/save/export)
- Edge cases (no agents, no skills, capacity exhaustion)
"""

import json
import math
import tempfile
import pytest

from mcp_server.swarm.replay_engine import (
    TaskOutcome,
    TaskSnapshot,
    AgentProfile,
    RoutingDecision,
    ReplayResult,
    ScenarioReport,
    RoutingConfig,
    ReplayEngine,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def agents():
    """Standard agent pool."""
    return [
        AgentProfile(
            agent_id="alice", skills=["delivery", "photo", "verification"],
            success_rate=0.95, avg_completion_hours=2.0, capacity=5,
            reputation_score=0.9,
        ),
        AgentProfile(
            agent_id="bob", skills=["delivery", "manual_labor"],
            success_rate=0.80, avg_completion_hours=4.0, capacity=3,
            reputation_score=0.7,
        ),
        AgentProfile(
            agent_id="carol", skills=["photo", "creative", "data_entry"],
            success_rate=0.70, avg_completion_hours=3.0, capacity=4,
            reputation_score=0.5,
        ),
    ]


@pytest.fixture
def engine(agents):
    """Engine with standard agent pool."""
    return ReplayEngine(agents=agents)


@pytest.fixture
def tasks():
    """Batch of task snapshots for scenario testing."""
    return [
        TaskSnapshot(
            task_id="t1", title="Deliver package",
            category="delivery", bounty_usd=5.0, deadline_hours=4.0,
            required_skills=["delivery"],
            actual_worker_id="alice", actual_outcome="completed",
        ),
        TaskSnapshot(
            task_id="t2", title="Take photo of store",
            category="verification", bounty_usd=3.0, deadline_hours=2.0,
            required_skills=["photo", "verification"],
        ),
        TaskSnapshot(
            task_id="t3", title="Data entry task",
            category="data_entry", bounty_usd=2.0, deadline_hours=8.0,
            required_skills=["data_entry"],
        ),
        TaskSnapshot(
            task_id="t4", title="Creative writing",
            category="creative", bounty_usd=10.0, deadline_hours=24.0,
            required_skills=["creative"],
            actual_worker_id="carol", actual_outcome="completed",
        ),
        TaskSnapshot(
            task_id="t5", title="Heavy lifting",
            category="manual_labor", bounty_usd=15.0, deadline_hours=6.0,
            required_skills=["manual_labor"],
            actual_worker_id="bob", actual_outcome="expired",
        ),
    ]


# ──────────────────────────────────────────────────────────────
# Section 1: Data Types (10 tests)
# ──────────────────────────────────────────────────────────────


class TestDataTypes:
    """Task snapshots, agent profiles, and supporting types."""

    def test_task_snapshot_defaults(self):
        t = TaskSnapshot(task_id="t1", title="Test")
        assert t.category == "general"
        assert t.bounty_usd == 0.0
        assert t.deadline_hours == 24.0
        assert t.required_skills == []
        assert t.actual_outcome is None

    def test_task_snapshot_roundtrip(self):
        original = TaskSnapshot(
            task_id="t1", title="Test", category="delivery",
            bounty_usd=5.0, required_skills=["photo"],
            actual_outcome="completed",
        )
        d = original.to_dict()
        restored = TaskSnapshot.from_dict(d)
        assert restored.task_id == original.task_id
        assert restored.category == original.category
        assert restored.bounty_usd == original.bounty_usd
        assert restored.required_skills == original.required_skills

    def test_task_snapshot_from_dict_extra_keys(self):
        d = {"task_id": "t1", "title": "Test", "extra": "ignored"}
        t = TaskSnapshot.from_dict(d)
        assert t.task_id == "t1"

    def test_agent_profile_available(self):
        a = AgentProfile(agent_id="a1", capacity=3, active_tasks=1)
        assert a.available() is True

    def test_agent_profile_unavailable(self):
        a = AgentProfile(agent_id="a1", capacity=3, active_tasks=3)
        assert a.available() is False

    def test_agent_skill_overlap_full(self):
        a = AgentProfile(agent_id="a1", skills=["photo", "delivery"])
        assert a.skill_overlap(["photo", "delivery"]) == 1.0

    def test_agent_skill_overlap_partial(self):
        a = AgentProfile(agent_id="a1", skills=["photo"])
        assert a.skill_overlap(["photo", "delivery"]) == 0.5

    def test_agent_skill_overlap_none(self):
        a = AgentProfile(agent_id="a1", skills=["cooking"])
        assert a.skill_overlap(["photo", "delivery"]) == 0.0

    def test_agent_skill_overlap_empty_required(self):
        a = AgentProfile(agent_id="a1", skills=["photo"])
        assert a.skill_overlap([]) == 1.0

    def test_task_outcome_enum(self):
        assert TaskOutcome.COMPLETED.value == "completed"
        assert TaskOutcome.EXPIRED.value == "expired"
        assert TaskOutcome.DISPUTED.value == "disputed"


# ──────────────────────────────────────────────────────────────
# Section 2: Agent Management (5 tests)
# ──────────────────────────────────────────────────────────────


class TestAgentManagement:
    """Adding, removing, and managing agents."""

    def test_add_agent(self):
        engine = ReplayEngine()
        engine.add_agent(AgentProfile(agent_id="new"))
        assert "new" in engine.agents

    def test_remove_agent(self, engine):
        assert engine.remove_agent("alice") is True
        assert "alice" not in engine.agents

    def test_remove_nonexistent(self, engine):
        assert engine.remove_agent("nonexistent") is False

    def test_reset_loads(self, engine):
        engine.agents["alice"].active_tasks = 5
        engine.agents["bob"].active_tasks = 3
        engine.reset_agent_loads()
        assert all(a.active_tasks == 0 for a in engine.agents.values())

    def test_agents_from_constructor(self, agents):
        engine = ReplayEngine(agents=agents)
        assert len(engine.agents) == 3
        assert "alice" in engine.agents


# ──────────────────────────────────────────────────────────────
# Section 3: Routing Config (6 tests)
# ──────────────────────────────────────────────────────────────


class TestRoutingConfig:
    """Configuration validation and weight management."""

    def test_default_weights_sum_to_one(self):
        cfg = RoutingConfig()
        total = (cfg.skill_weight + cfg.capacity_weight + cfg.reputation_weight
                 + cfg.speed_weight + cfg.cost_weight)
        assert abs(total - 1.0) < 0.001

    def test_valid_config(self):
        cfg = RoutingConfig()
        errors = cfg.validate()
        assert errors == []

    def test_invalid_weight_sum(self):
        cfg = RoutingConfig(skill_weight=0.5, capacity_weight=0.5,
                            reputation_weight=0.5, speed_weight=0.5, cost_weight=0.5)
        errors = cfg.validate()
        assert len(errors) > 0
        assert "sum" in errors[0].lower() or "1.0" in errors[0]

    def test_negative_weight(self):
        cfg = RoutingConfig(skill_weight=-0.1, capacity_weight=0.25,
                            reputation_weight=0.35, speed_weight=0.25, cost_weight=0.25)
        errors = cfg.validate()
        assert any("negative" in e.lower() for e in errors)

    def test_custom_thresholds(self):
        cfg = RoutingConfig(min_skill_overlap=0.5, min_reputation=0.3)
        assert cfg.min_skill_overlap == 0.5
        assert cfg.min_reputation == 0.3

    def test_max_load_ratio(self):
        cfg = RoutingConfig(max_load_ratio=0.8)
        assert cfg.max_load_ratio == 0.8


# ──────────────────────────────────────────────────────────────
# Section 4: Task Routing (14 tests)
# ──────────────────────────────────────────────────────────────


class TestTaskRouting:
    """Core routing logic — scoring and selection."""

    def test_route_delivery_task(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver package",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is not None
        assert decision.confidence > 0

    def test_route_prefers_best_skill_match(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Take photo",
            required_skills=["photo", "verification"],
            bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        # Alice has both photo + verification skills
        assert decision.recommended_agent_id == "alice"

    def test_route_no_agents(self):
        engine = ReplayEngine()
        task = TaskSnapshot(task_id="t1", title="Test")
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is None
        assert "no agents" in decision.reasoning.lower()

    def test_route_no_eligible_agents(self, engine):
        """All agents filtered out by skill requirement."""
        task = TaskSnapshot(
            task_id="t1", title="Brain surgery",
            required_skills=["neurosurgery"],
            bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is None

    def test_route_capacity_filter(self, engine):
        """Agent at capacity is excluded."""
        engine.agents["alice"].active_tasks = 5  # At max
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        assert decision.recommended_agent_id != "alice"

    def test_route_reputation_filter(self):
        engine = ReplayEngine(
            agents=[AgentProfile(agent_id="low_rep", reputation_score=0.05,
                                 skills=["delivery"])],
            config=RoutingConfig(min_reputation=0.1),
        )
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is None

    def test_route_alternatives_included(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        # Both alice and bob have delivery skill
        assert len(decision.alternatives) >= 1

    def test_route_reasoning_string(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        assert len(decision.reasoning) > 0

    def test_route_matches_actual(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
            actual_worker_id="alice",
        )
        decision = engine.route_task(task)
        if decision.recommended_agent_id == "alice":
            assert decision.matches_actual is True
        else:
            assert decision.matches_actual is False

    def test_route_actual_was_better_check(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery", "manual_labor"], bounty_usd=5.0,
            actual_worker_id="bob", actual_outcome="completed",
        )
        decision = engine.route_task(task)
        # actual_was_better is set when actual differs from recommended
        if not decision.matches_actual:
            assert decision.actual_was_better is not None

    def test_route_no_skills_required(self, engine):
        """Task with no skill requirements — all agents eligible."""
        task = TaskSnapshot(task_id="t1", title="Simple task", bounty_usd=5.0)
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is not None

    def test_route_composite_score_populated(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        assert decision.composite_score > 0
        assert decision.skill_match > 0
        assert decision.reputation_score > 0

    def test_speed_score_considers_deadline(self):
        """Agent that's slow relative to deadline gets lower speed score."""
        slow = AgentProfile(agent_id="slow", skills=["delivery"],
                            avg_completion_hours=20.0, reputation_score=0.8)
        fast = AgentProfile(agent_id="fast", skills=["delivery"],
                            avg_completion_hours=1.0, reputation_score=0.8)
        engine = ReplayEngine(agents=[slow, fast])
        task = TaskSnapshot(
            task_id="t1", title="Urgent delivery",
            required_skills=["delivery"], deadline_hours=4.0, bounty_usd=5.0,
        )
        decision = engine.route_task(task)
        assert decision.recommended_agent_id == "fast"

    def test_cost_score_with_hourly_rate(self):
        """Agent with lower cost gets better cost score."""
        cheap = AgentProfile(agent_id="cheap", skills=["delivery"],
                             hourly_rate=5.0, avg_completion_hours=2.0,
                             reputation_score=0.5)
        expensive = AgentProfile(agent_id="expensive", skills=["delivery"],
                                 hourly_rate=50.0, avg_completion_hours=2.0,
                                 reputation_score=0.5)
        engine = ReplayEngine(agents=[cheap, expensive])
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=20.0,
        )
        decision = engine.route_task(task)
        assert decision.recommended_agent_id == "cheap"


# ──────────────────────────────────────────────────────────────
# Section 5: Replay Pipeline (8 tests)
# ──────────────────────────────────────────────────────────────


class TestReplayPipeline:
    """Single task replay including outcome simulation."""

    def test_replay_basic(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        result = engine.replay_task(task)
        assert isinstance(result, ReplayResult)
        assert result.decision.recommended_agent_id is not None
        assert result.cost_estimate == 5.0

    def test_replay_increments_count(self, engine):
        assert engine.replay_count == 0
        task = TaskSnapshot(task_id="t1", title="Test")
        engine.replay_task(task)
        assert engine.replay_count == 1

    def test_replay_increments_agent_load(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        result = engine.replay_task(task)
        agent_id = result.decision.recommended_agent_id
        assert engine.agents[agent_id].active_tasks >= 1

    def test_replay_high_confidence_completed(self, engine):
        """High confidence + high success rate → simulated completed."""
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        result = engine.replay_task(task)
        # Alice has 0.95 success rate, should get high confidence
        if result.decision.confidence > 0.7:
            assert result.simulated_outcome == "completed"

    def test_replay_unroutable(self):
        engine = ReplayEngine()
        task = TaskSnapshot(task_id="t1", title="Test")
        result = engine.replay_task(task)
        assert result.simulated_outcome == "unroutable"

    def test_replay_estimated_hours(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
        )
        result = engine.replay_task(task)
        assert result.estimated_completion_hours > 0

    def test_accuracy_signal_completed(self, engine):
        task = TaskSnapshot(
            task_id="t1", title="Deliver",
            required_skills=["delivery"], bounty_usd=5.0,
            actual_outcome="completed",
        )
        result = engine.replay_task(task)
        signal = result.accuracy_signal()
        assert signal is not None
        assert isinstance(signal, bool)

    def test_accuracy_signal_no_actual(self, engine):
        task = TaskSnapshot(task_id="t1", title="Test")
        result = engine.replay_task(task)
        assert result.accuracy_signal() is None


# ──────────────────────────────────────────────────────────────
# Section 6: Scenario Execution (12 tests)
# ──────────────────────────────────────────────────────────────


class TestScenarioExecution:
    """Full scenario replay and report generation."""

    def test_scenario_basic(self, engine, tasks):
        report = engine.run_scenario("test_run", tasks)
        assert isinstance(report, ScenarioReport)
        assert report.scenario_name == "test_run"
        assert report.task_count == 5

    def test_scenario_counts(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        assert report.routed_count + report.unroutable_count == report.task_count

    def test_scenario_avg_confidence(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        if report.routed_count > 0:
            assert 0 <= report.avg_confidence <= 1.0

    def test_scenario_avg_skill_match(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        if report.routed_count > 0:
            assert 0 <= report.avg_skill_match <= 1.0

    def test_scenario_agent_load(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        assert isinstance(report.agent_load, dict)
        total_assigned = sum(report.agent_load.values())
        assert total_assigned == report.routed_count

    def test_scenario_agent_diversity(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        # Multiple agents should give diversity > 0
        if len(report.agent_load) > 1:
            assert report.agent_diversity > 0

    def test_scenario_single_agent_diversity(self):
        """All tasks to one agent → diversity = 0."""
        engine = ReplayEngine(agents=[
            AgentProfile(agent_id="solo", skills=["everything"],
                         capacity=100, reputation_score=0.8),
        ])
        tasks = [TaskSnapshot(task_id=f"t{i}", title="Test",
                              required_skills=["everything"], bounty_usd=5.0)
                 for i in range(5)]
        report = engine.run_scenario("solo_test", tasks)
        assert report.agent_diversity == 0.0

    def test_scenario_cost_tracking(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        assert report.total_estimated_cost > 0
        if report.routed_count > 0:
            assert report.avg_cost_per_task > 0

    def test_scenario_match_rate(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        # Some tasks have actual_worker_id
        assert isinstance(report.match_rate, float)

    def test_scenario_results_list(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        assert len(report.results) == 5
        for r in report.results:
            assert isinstance(r, ReplayResult)

    def test_scenario_reset_loads(self, engine, tasks):
        """Loads should reset between scenarios."""
        engine.run_scenario("first", tasks)
        # Run again — agents should start fresh
        report = engine.run_scenario("second", tasks, reset_loads=True)
        assert report.routed_count > 0

    def test_scenario_no_reset_loads(self, engine, tasks):
        """Without reset, agents accumulate load."""
        engine.run_scenario("first", tasks, reset_loads=False)
        # Agents now have load from first run
        total_load = sum(a.active_tasks for a in engine.agents.values())
        assert total_load > 0

    def test_scenario_to_dict(self, engine, tasks):
        report = engine.run_scenario("test", tasks)
        d = report.to_dict()
        assert d["scenario_name"] == "test"
        assert d["task_count"] == 5
        assert isinstance(d["results"], list)


# ──────────────────────────────────────────────────────────────
# Section 7: What-If Analysis (4 tests)
# ──────────────────────────────────────────────────────────────


class TestWhatIfAnalysis:
    """Config comparison for what-if scenarios."""

    def test_compare_two_configs(self, engine, tasks):
        config_a = RoutingConfig(skill_weight=0.5, capacity_weight=0.1,
                                  reputation_weight=0.2, speed_weight=0.1,
                                  cost_weight=0.1)
        config_b = RoutingConfig(skill_weight=0.1, capacity_weight=0.1,
                                  reputation_weight=0.5, speed_weight=0.2,
                                  cost_weight=0.1)
        comparisons = engine.compare_configs(tasks, [config_a, config_b])
        assert len(comparisons) == 2
        for name, metrics in comparisons.items():
            assert "avg_confidence" in metrics
            assert "avg_skill_match" in metrics
            assert "routed_pct" in metrics
            assert "agent_diversity" in metrics

    def test_compare_configs_different_results(self, engine, tasks):
        """Different weights should produce different outcomes."""
        skill_heavy = RoutingConfig(skill_weight=0.8, capacity_weight=0.05,
                                     reputation_weight=0.05, speed_weight=0.05,
                                     cost_weight=0.05)
        reputation_heavy = RoutingConfig(skill_weight=0.05, capacity_weight=0.05,
                                          reputation_weight=0.8, speed_weight=0.05,
                                          cost_weight=0.05)
        comparisons = engine.compare_configs(tasks, [skill_heavy, reputation_heavy])
        configs = list(comparisons.values())
        # At least one metric should differ
        differs = any(configs[0][k] != configs[1][k] for k in configs[0])
        assert differs

    def test_compare_single_config(self, engine, tasks):
        comparisons = engine.compare_configs(tasks, [RoutingConfig()])
        assert len(comparisons) == 1

    def test_compare_empty_tasks(self, engine):
        comparisons = engine.compare_configs([], [RoutingConfig()])
        for metrics in comparisons.values():
            assert metrics["routed_pct"] == 0.0


# ──────────────────────────────────────────────────────────────
# Section 8: I/O Helpers (5 tests)
# ──────────────────────────────────────────────────────────────


class TestIOHelpers:
    """Load, save, and export operations."""

    def test_load_tasks_from_list(self, engine):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([
                {"task_id": "t1", "title": "Test 1"},
                {"task_id": "t2", "title": "Test 2"},
            ], f)
            f.flush()
            tasks = engine.load_tasks(f.name)
        assert len(tasks) == 2
        assert tasks[0].task_id == "t1"

    def test_load_tasks_from_dict(self, engine):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"tasks": [
                {"task_id": "t1", "title": "Test 1"},
            ]}, f)
            f.flush()
            tasks = engine.load_tasks(f.name)
        assert len(tasks) == 1

    def test_save_report(self, engine, tasks):
        report = engine.run_scenario("save_test", tasks)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            engine.save_report(report, f.name)
            saved = json.loads(open(f.name).read())
        assert saved["scenario_name"] == "save_test"
        assert saved["task_count"] == 5

    def test_export_decisions(self, engine, tasks):
        results = [engine.replay_task(t) for t in tasks]
        exported = engine.export_decisions(results)
        assert len(exported) == 5
        for d in exported:
            assert "task_id" in d
            assert "recommended_agent" in d
            assert "confidence" in d
            assert "simulated_outcome" in d

    def test_export_includes_alternatives(self, engine, tasks):
        results = [engine.replay_task(t) for t in tasks]
        exported = engine.export_decisions(results)
        # At least one task should have alternatives
        has_alternatives = any(len(d["alternatives"]) > 0 for d in exported)
        assert has_alternatives


# ──────────────────────────────────────────────────────────────
# Section 9: Edge Cases (8 tests)
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_empty_engine(self):
        engine = ReplayEngine()
        task = TaskSnapshot(task_id="t1", title="Test")
        result = engine.replay_task(task)
        assert result.simulated_outcome == "unroutable"

    def test_single_agent_gets_all(self):
        engine = ReplayEngine(agents=[
            AgentProfile(agent_id="only", skills=["all"],
                         capacity=100, reputation_score=0.8),
        ])
        tasks = [TaskSnapshot(task_id=f"t{i}", title=f"Task {i}",
                              required_skills=["all"], bounty_usd=5.0)
                 for i in range(10)]
        report = engine.run_scenario("solo", tasks)
        assert report.agent_load == {"only": 10}

    def test_capacity_exhaustion(self):
        """Agent runs out of capacity during scenario."""
        engine = ReplayEngine(agents=[
            AgentProfile(agent_id="limited", skills=["work"],
                         capacity=2, reputation_score=0.8),
        ])
        tasks = [TaskSnapshot(task_id=f"t{i}", title=f"Task {i}",
                              required_skills=["work"], bounty_usd=5.0)
                 for i in range(5)]
        report = engine.run_scenario("exhaust", tasks, reset_loads=False)
        # Only 2 tasks should be routed (capacity = 2, max_load_ratio = 0.9)
        assert report.unroutable_count > 0

    def test_zero_bounty_task(self, engine):
        task = TaskSnapshot(task_id="t1", title="Free task",
                            required_skills=["delivery"], bounty_usd=0.0)
        result = engine.replay_task(task)
        assert result.cost_estimate == 0.0

    def test_zero_deadline(self, engine):
        task = TaskSnapshot(task_id="t1", title="Urgent",
                            required_skills=["delivery"], deadline_hours=0,
                            bounty_usd=5.0)
        result = engine.replay_task(task)
        # Should not crash — deadline_hours=0 is handled
        assert result is not None

    def test_pearson_no_pairs(self):
        assert ReplayEngine._pearson([]) == 0.0

    def test_pearson_one_pair(self):
        assert ReplayEngine._pearson([(1.0, 1.0)]) == 0.0

    def test_pearson_perfect_correlation(self):
        pairs = [(1, 1), (2, 2), (3, 3), (4, 4)]
        r = ReplayEngine._pearson(pairs)
        assert abs(r - 1.0) < 0.001

    def test_pearson_negative_correlation(self):
        pairs = [(1, 4), (2, 3), (3, 2), (4, 1)]
        r = ReplayEngine._pearson(pairs)
        assert abs(r - (-1.0)) < 0.001

    def test_outcome_correlation_in_scenario(self, engine, tasks):
        report = engine.run_scenario("corr_test", tasks)
        # outcome_correlation may be 0 if not enough data, but shouldn't crash
        assert isinstance(report.outcome_correlation, float)
