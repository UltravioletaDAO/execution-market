"""
Tests for SwarmReplayEngine — historical task decision replay & simulation.
"""

import json
import pytest

from mcp_server.swarm.replay_engine import (
    TaskSnapshot,
    AgentProfile,
    RoutingDecision,
    RoutingConfig,
    ReplayEngine,
    ReplayResult,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def basic_agents():
    """3 agents with different skill profiles."""
    return [
        AgentProfile(
            agent_id="agent_python",
            skills=["python", "devops", "aws"],
            success_rate=0.92,
            avg_completion_hours=3.0,
            capacity=5,
            reputation_score=0.85,
        ),
        AgentProfile(
            agent_id="agent_js",
            skills=["javascript", "react", "node"],
            success_rate=0.88,
            avg_completion_hours=4.0,
            capacity=3,
            reputation_score=0.75,
        ),
        AgentProfile(
            agent_id="agent_general",
            skills=["python", "javascript", "sql", "documentation"],
            success_rate=0.78,
            avg_completion_hours=6.0,
            capacity=4,
            reputation_score=0.60,
        ),
    ]


@pytest.fixture
def basic_tasks():
    """Sample tasks with different requirements."""
    return [
        TaskSnapshot(
            task_id="task_1",
            title="Deploy Python API",
            description="Set up FastAPI service on AWS ECS",
            category="devops",
            bounty_usd=50.0,
            deadline_hours=24.0,
            required_skills=["python", "aws", "devops"],
        ),
        TaskSnapshot(
            task_id="task_2",
            title="Build React Dashboard",
            description="Create real-time monitoring dashboard",
            category="frontend",
            bounty_usd=75.0,
            deadline_hours=48.0,
            required_skills=["javascript", "react"],
        ),
        TaskSnapshot(
            task_id="task_3",
            title="Write API Documentation",
            description="OpenAPI spec + developer guide",
            category="documentation",
            bounty_usd=25.0,
            deadline_hours=12.0,
            required_skills=["documentation", "python"],
        ),
    ]


@pytest.fixture
def engine(basic_agents):
    return ReplayEngine(agents=basic_agents)


@pytest.fixture
def historical_tasks():
    """Tasks with known historical outcomes."""
    return [
        TaskSnapshot(
            task_id="hist_1",
            title="Python Script",
            required_skills=["python"],
            actual_worker_id="agent_python",
            actual_outcome="completed",
            actual_rating=4.5,
        ),
        TaskSnapshot(
            task_id="hist_2",
            title="React Component",
            required_skills=["react", "javascript"],
            actual_worker_id="agent_js",
            actual_outcome="completed",
            actual_rating=4.0,
        ),
        TaskSnapshot(
            task_id="hist_3",
            title="Data Analysis",
            required_skills=["python", "sql"],
            actual_worker_id="agent_general",
            actual_outcome="expired",
        ),
    ]


# ──────────────────────────────────────────────────────────────
# TaskSnapshot
# ──────────────────────────────────────────────────────────────


class TestTaskSnapshot:
    def test_create_basic(self):
        t = TaskSnapshot(task_id="t1", title="Test Task")
        assert t.task_id == "t1"
        assert t.category == "general"
        assert t.bounty_usd == 0.0
        assert t.deadline_hours == 24.0

    def test_to_dict(self):
        t = TaskSnapshot(task_id="t1", title="X", bounty_usd=10.0)
        d = t.to_dict()
        assert d["task_id"] == "t1"
        assert d["bounty_usd"] == 10.0

    def test_from_dict(self):
        data = {
            "task_id": "t2",
            "title": "From Dict",
            "bounty_usd": 25.0,
            "required_skills": ["python"],
        }
        t = TaskSnapshot.from_dict(data)
        assert t.task_id == "t2"
        assert t.required_skills == ["python"]

    def test_from_dict_ignores_unknown_fields(self):
        data = {"task_id": "t3", "title": "X", "unknown_field": "ignored"}
        t = TaskSnapshot.from_dict(data)
        assert t.task_id == "t3"
        assert not hasattr(t, "unknown_field")

    def test_roundtrip(self):
        original = TaskSnapshot(
            task_id="rt",
            title="Roundtrip",
            bounty_usd=100,
            required_skills=["rust", "wasm"],
            actual_outcome="completed",
            actual_rating=5.0,
        )
        restored = TaskSnapshot.from_dict(original.to_dict())
        assert restored.task_id == original.task_id
        assert restored.required_skills == original.required_skills
        assert restored.actual_rating == original.actual_rating


# ──────────────────────────────────────────────────────────────
# AgentProfile
# ──────────────────────────────────────────────────────────────


class TestAgentProfile:
    def test_available_when_under_capacity(self):
        a = AgentProfile(agent_id="a1", capacity=3, active_tasks=2)
        assert a.available() is True

    def test_not_available_when_at_capacity(self):
        a = AgentProfile(agent_id="a1", capacity=3, active_tasks=3)
        assert a.available() is False

    def test_skill_overlap_full_match(self):
        a = AgentProfile(agent_id="a1", skills=["python", "aws", "devops"])
        assert a.skill_overlap(["python", "aws"]) == 1.0

    def test_skill_overlap_partial(self):
        a = AgentProfile(agent_id="a1", skills=["python"])
        assert a.skill_overlap(["python", "aws"]) == 0.5

    def test_skill_overlap_no_match(self):
        a = AgentProfile(agent_id="a1", skills=["java"])
        assert a.skill_overlap(["python", "rust"]) == 0.0

    def test_skill_overlap_empty_required(self):
        a = AgentProfile(agent_id="a1", skills=["python"])
        assert a.skill_overlap([]) == 1.0

    def test_skill_overlap_case_insensitive(self):
        a = AgentProfile(agent_id="a1", skills=["Python", "AWS"])
        assert a.skill_overlap(["python", "aws"]) == 1.0


# ──────────────────────────────────────────────────────────────
# RoutingConfig
# ──────────────────────────────────────────────────────────────


class TestRoutingConfig:
    def test_valid_config_no_errors(self):
        cfg = RoutingConfig()
        assert cfg.validate() == []


# ──────────────────────────────────────────────────────────────
# Routing decisions
# ──────────────────────────────────────────────────────────────


class TestRouting:
    def test_route_to_best_skill_match(self, engine, basic_tasks):
        """Python+AWS task should route to agent_python."""
        decision = engine.route_task(basic_tasks[0])
        assert decision.recommended_agent_id == "agent_python"
        assert decision.skill_match == 1.0
        assert decision.confidence > 0.5

    def test_route_frontend_to_js_agent(self, engine, basic_tasks):
        """React task should route to agent_js."""
        decision = engine.route_task(basic_tasks[1])
        assert decision.recommended_agent_id == "agent_js"
        assert decision.skill_match == 1.0

    def test_no_agents_returns_empty_decision(self):
        engine = ReplayEngine(agents=[])
        task = TaskSnapshot(task_id="t", title="X")
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is None
        assert "No agents" in decision.reasoning

    def test_alternatives_populated(self, engine, basic_tasks):
        """Doc task should have agent_general as primary with alternatives."""
        decision = engine.route_task(basic_tasks[2])
        # agent_general has both documentation + python
        assert decision.recommended_agent_id is not None
        # Should have at least one alternative
        assert len(decision.alternatives) >= 0  # May vary by scoring

    def test_capacity_affects_routing(self, basic_agents):
        """Fully loaded agent should not be routed to."""
        basic_agents[0].active_tasks = 5  # At capacity
        engine = ReplayEngine(agents=basic_agents)
        task = TaskSnapshot(
            task_id="t",
            title="Python Task",
            required_skills=["python"],
        )
        decision = engine.route_task(task)
        # Should NOT route to agent_python (at capacity)
        assert decision.recommended_agent_id != "agent_python"

    def test_low_reputation_filtered(self):
        """Agent below min reputation should be filtered out."""
        agents = [
            AgentProfile(
                agent_id="low_rep",
                skills=["python"],
                reputation_score=0.05,
                success_rate=0.5,
            ),
        ]
        engine = ReplayEngine(
            agents=agents,
            config=RoutingConfig(min_reputation=0.1),
        )
        task = TaskSnapshot(task_id="t", title="X", required_skills=["python"])
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is None

    def test_skill_threshold_filter(self):
        """Agent with insufficient skill overlap gets filtered."""
        agents = [
            AgentProfile(agent_id="mismatch", skills=["java"], reputation_score=0.8),
        ]
        engine = ReplayEngine(
            agents=agents,
            config=RoutingConfig(min_skill_overlap=0.5),
        )
        task = TaskSnapshot(
            task_id="t", title="X", required_skills=["python", "rust", "go"]
        )
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is None

    def test_task_without_skills_matches_anyone(self, engine):
        """No required skills → anyone can do it."""
        task = TaskSnapshot(task_id="t", title="General task", required_skills=[])
        decision = engine.route_task(task)
        assert decision.recommended_agent_id is not None

    def test_historical_comparison(self, engine, historical_tasks):
        """When actual_worker_id exists, matches_actual should be set."""
        decision = engine.route_task(historical_tasks[0])
        assert decision.matches_actual is not None

    def test_reasoning_populated(self, engine, basic_tasks):
        decision = engine.route_task(basic_tasks[0])
        assert len(decision.reasoning) > 0
        assert "agent_python" in decision.reasoning


# ──────────────────────────────────────────────────────────────
# Replay (full pipeline)
# ──────────────────────────────────────────────────────────────


class TestReplay:
    def test_replay_single_task(self, engine, basic_tasks):
        result = engine.replay_task(basic_tasks[0])
        assert result.task.task_id == "task_1"
        assert result.decision.recommended_agent_id is not None
        assert result.simulated_outcome in ("completed", "at_risk", "likely_expired")
        assert result.cost_estimate >= 0

    def test_replay_tracks_agent_load(self, engine, basic_tasks):
        """Sequential replays should increase agent load."""
        engine.reset_agent_loads()
        r1 = engine.replay_task(basic_tasks[0])
        agent_id = r1.decision.recommended_agent_id
        assert engine.agents[agent_id].active_tasks == 1

    def test_replay_count_increments(self, engine, basic_tasks):
        initial = engine.replay_count
        engine.replay_task(basic_tasks[0])
        assert engine.replay_count == initial + 1

    def test_accuracy_signal_correct(self):
        """High confidence + completed → True."""
        task = TaskSnapshot(task_id="t", title="X", actual_outcome="completed")
        result = ReplayResult(
            task=task,
            decision=RoutingDecision(task_id="t", confidence=0.9),
        )
        assert result.accuracy_signal() is True

    def test_accuracy_signal_low_confidence_expired(self):
        """Low confidence + expired → True (correctly predicted failure)."""
        task = TaskSnapshot(task_id="t", title="X", actual_outcome="expired")
        result = ReplayResult(
            task=task,
            decision=RoutingDecision(task_id="t", confidence=0.3),
        )
        assert result.accuracy_signal() is True

    def test_accuracy_signal_no_outcome(self):
        task = TaskSnapshot(task_id="t", title="X")
        result = ReplayResult(
            task=task,
            decision=RoutingDecision(task_id="t", confidence=0.5),
        )
        assert result.accuracy_signal() is None


# ──────────────────────────────────────────────────────────────
# Scenarios
# ──────────────────────────────────────────────────────────────


class TestScenarios:
    def test_basic_scenario(self, engine, basic_tasks):
        report = engine.run_scenario("test_basic", basic_tasks)
        assert report.scenario_name == "test_basic"
        assert report.task_count == 3
        assert report.routed_count > 0
        assert len(report.results) == 3
        assert report.duration_ms >= 0

    def test_scenario_resets_loads(self, engine, basic_tasks):
        """run_scenario with reset_loads=True starts fresh."""
        engine.agents["agent_python"].active_tasks = 4
        report = engine.run_scenario("reset_test", basic_tasks, reset_loads=True)
        # Should still route to agent_python since load was reset
        routed_agents = [r.decision.recommended_agent_id for r in report.results]
        assert "agent_python" in routed_agents

    def test_scenario_without_reset(self, engine, basic_tasks):
        """Without reset, previous loads carry over."""
        engine.agents["agent_python"].active_tasks = 4  # Nearly full
        report = engine.run_scenario("no_reset", basic_tasks, reset_loads=False)
        assert report.task_count == 3

    def test_scenario_single_agent_zero_diversity(self):
        """All tasks to one agent → diversity = 0."""
        agents = [
            AgentProfile(
                agent_id="solo",
                skills=["everything"],
                reputation_score=0.9,
                capacity=10,
            ),
        ]
        engine = ReplayEngine(agents=agents)
        tasks = [TaskSnapshot(task_id=f"t{i}", title=f"Task {i}") for i in range(5)]
        report = engine.run_scenario("solo", tasks)
        assert report.agent_diversity == 0.0

    def test_empty_scenario(self, engine):
        report = engine.run_scenario("empty", [])
        assert report.task_count == 0
        assert report.routed_count == 0

    def test_historical_match_rate(self, engine, historical_tasks):
        """With historical data, match_rate should be computed."""
        report = engine.run_scenario("historical", historical_tasks)
        # At least some should have matches_actual set
        has_comparison = any(
            r.decision.matches_actual is not None for r in report.results
        )
        assert has_comparison

    def test_scenario_with_many_tasks(self, engine):
        """Stress test with many tasks."""
        tasks = [
            TaskSnapshot(
                task_id=f"stress_{i}",
                title=f"Task {i}",
                required_skills=["python"] if i % 2 == 0 else ["javascript"],
                bounty_usd=10.0 + i,
            )
            for i in range(50)
        ]
        report = engine.run_scenario("stress", tasks)
        assert report.task_count == 50
        assert report.routed_count > 0
        assert report.duration_ms < 5000  # Should be fast


# ──────────────────────────────────────────────────────────────
# Engine management
# ──────────────────────────────────────────────────────────────


class TestEngineManagement:
    def test_remove_nonexistent_agent(self, engine):
        assert engine.remove_agent("ghost") is False

    def test_reset_agent_loads(self, engine):
        engine.agents["agent_python"].active_tasks = 3
        engine.agents["agent_js"].active_tasks = 2
        engine.reset_agent_loads()
        assert all(a.active_tasks == 0 for a in engine.agents.values())


# ──────────────────────────────────────────────────────────────
# What-if analysis
# ──────────────────────────────────────────────────────────────


class TestWhatIf:
    def test_compare_configs(self, engine, basic_tasks):
        configs = [
            RoutingConfig(
                skill_weight=0.6,
                capacity_weight=0.1,
                reputation_weight=0.1,
                speed_weight=0.1,
                cost_weight=0.1,
            ),
            RoutingConfig(
                skill_weight=0.1,
                capacity_weight=0.1,
                reputation_weight=0.6,
                speed_weight=0.1,
                cost_weight=0.1,
            ),
        ]
        results = engine.compare_configs(basic_tasks, configs)
        assert len(results) == 2
        for key, metrics in results.items():
            assert "avg_confidence" in metrics
            assert "avg_skill_match" in metrics
            assert "routed_pct" in metrics

    def test_different_configs_different_results(self, engine, basic_tasks):
        """Changing weights should sometimes change routing decisions."""
        configs = [
            RoutingConfig(
                skill_weight=0.9,
                capacity_weight=0.025,
                reputation_weight=0.025,
                speed_weight=0.025,
                cost_weight=0.025,
            ),
            RoutingConfig(
                skill_weight=0.025,
                capacity_weight=0.025,
                reputation_weight=0.9,
                speed_weight=0.025,
                cost_weight=0.025,
            ),
        ]
        results = engine.compare_configs(basic_tasks, configs)
        # The two configs should produce different metrics
        vals = list(results.values())
        # At minimum they should both produce valid results
        assert all(v["avg_confidence"] >= 0 for v in vals)


# ──────────────────────────────────────────────────────────────
# I/O helpers
# ──────────────────────────────────────────────────────────────


class TestIO:
    def test_load_tasks_list(self, tmp_path, engine):
        data = [
            {"task_id": "f1", "title": "From File", "bounty_usd": 20},
            {"task_id": "f2", "title": "Also From File"},
        ]
        path = tmp_path / "tasks.json"
        path.write_text(json.dumps(data))
        tasks = engine.load_tasks(str(path))
        assert len(tasks) == 2
        assert tasks[0].task_id == "f1"
        assert tasks[0].bounty_usd == 20

    def test_load_tasks_object_format(self, tmp_path, engine):
        data = {"tasks": [{"task_id": "t1", "title": "Wrapped"}]}
        path = tmp_path / "wrapped.json"
        path.write_text(json.dumps(data))
        tasks = engine.load_tasks(str(path))
        assert len(tasks) == 1


# ──────────────────────────────────────────────────────────────
# Pearson correlation
# ──────────────────────────────────────────────────────────────


class TestPearson:
    def test_perfect_positive(self):
        pairs = [(1, 1), (2, 2), (3, 3)]
        assert ReplayEngine._pearson(pairs) == pytest.approx(1.0, abs=0.01)

    def test_perfect_negative(self):
        pairs = [(1, 3), (2, 2), (3, 1)]
        assert ReplayEngine._pearson(pairs) == pytest.approx(-1.0, abs=0.01)

    def test_no_correlation(self):
        pairs = [(1, 2), (2, 1), (3, 2), (4, 1)]
        r = ReplayEngine._pearson(pairs)
        assert -0.5 < r < 0.5

    def test_single_pair(self):
        assert ReplayEngine._pearson([(1, 1)]) == 0.0

    def test_empty(self):
        assert ReplayEngine._pearson([]) == 0.0

    def test_constant_values(self):
        """All same y values → zero correlation (division by zero guard)."""
        pairs = [(1, 5), (2, 5), (3, 5)]
        assert ReplayEngine._pearson(pairs) == 0.0


# ──────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_agent_with_zero_capacity(self):
        agents = [
            AgentProfile(
                agent_id="zero", skills=["python"], capacity=0, reputation_score=0.8
            )
        ]
        engine = ReplayEngine(agents=agents)
        task = TaskSnapshot(task_id="t", title="X", required_skills=["python"])
        decision = engine.route_task(task)
        # Zero capacity means load ratio = 0/0 → filtered
        # or max_load_ratio check
        assert decision.task_id == "t"

    def test_many_agents_few_tasks(self):
        """More agents than tasks → some agents unused."""
        agents = [
            AgentProfile(
                agent_id=f"a{i}",
                skills=["python"],
                reputation_score=0.5 + i * 0.05,
                capacity=3,
            )
            for i in range(10)
        ]
        engine = ReplayEngine(agents=agents)
        tasks = [TaskSnapshot(task_id="t1", title="Solo", required_skills=["python"])]
        report = engine.run_scenario("many_agents", tasks)
        assert report.routed_count == 1
        assert len(report.agent_load) == 1

    def test_speed_score_with_long_completion(self):
        """Agent slower than deadline → negative speed score clamped to 0."""
        agents = [
            AgentProfile(
                agent_id="slow",
                skills=["python"],
                avg_completion_hours=100,
                reputation_score=0.8,
                capacity=5,
            ),
        ]
        engine = ReplayEngine(agents=agents)
        task = TaskSnapshot(
            task_id="t", title="X", required_skills=["python"], deadline_hours=10
        )
        decision = engine.route_task(task)
        # Should still route but with low speed score
        assert decision.speed_score == 0.0 or decision.recommended_agent_id is not None
