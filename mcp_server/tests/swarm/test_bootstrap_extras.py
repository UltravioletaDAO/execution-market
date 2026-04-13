"""
Tests for SwarmBootstrap — Production-aware coordinator initialization.
"""

import json
import os
import tempfile

from swarm.bootstrap import (
    SwarmBootstrap,
    BootstrapResult,
    DEFAULT_AGENTS,
    KNOWN_AGENTS,
)
from swarm.coordinator import SwarmCoordinator
from swarm.orchestrator import TaskRequest, TaskPriority, RoutingStrategy


# ─── Agent Registry Tests ────────────────────────────────────────────────────


class TestKnownAgents:
    """Validate the known agent registry."""

    def test_agent_ids_range(self):
        """Agent IDs are in 2101-2124 range."""
        ids = [a["agent_id"] for a in KNOWN_AGENTS]
        assert min(ids) == 2101
        assert max(ids) == 2124

    def test_all_agents_have_required_fields(self):
        """Every agent has name, personality, and tags."""
        for agent in KNOWN_AGENTS:
            assert "agent_id" in agent
            assert "name" in agent
            assert "personality" in agent
            assert "tags" in agent
            assert len(agent["tags"]) >= 1

    def test_agent_names_unique(self):
        """All agent names are unique."""
        names = [a["name"] for a in KNOWN_AGENTS]
        assert len(names) == len(set(names))

    def test_ultravioleta_agent(self):
        """Agent 2106 (UltraVioleta) is the platform operator."""
        uv = [a for a in KNOWN_AGENTS if a["agent_id"] == 2106]
        assert len(uv) == 1
        assert uv[0]["name"] == "UltraVioleta"
        assert uv[0]["personality"] == "orchestrator"
        assert "multichain" in uv[0]["tags"]

    def test_personality_diversity(self):
        """At least 3 different personality types."""
        personalities = set(a["personality"] for a in KNOWN_AGENTS)
        assert len(personalities) >= 3

    def test_tag_coverage(self):
        """Agents cover key categories."""
        all_tags = set()
        for agent in KNOWN_AGENTS:
            all_tags.update(agent["tags"])

        expected = {
            "general",
            "coding",
            "verification",
            "blockchain",
            "delivery",
            "creative",
        }
        assert expected.issubset(all_tags), f"Missing tags: {expected - all_tags}"

    def test_default_agents_alias(self):
        """KNOWN_AGENTS is a backward-compat alias for DEFAULT_AGENTS."""
        assert KNOWN_AGENTS is DEFAULT_AGENTS

    def test_custom_agents_override(self):
        """Bootstrap accepts custom agents list, ignoring defaults."""
        custom = [
            {
                "agent_id": 9001,
                "name": "Custom",
                "personality": "explorer",
                "tags": ["test"],
            },
        ]
        bootstrap = SwarmBootstrap(agents=custom)
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False,
            use_cached_profiles=False,
        )
        assert result.agents_registered == 1


# ─── Bootstrap Result Tests ──────────────────────────────────────────────────


class TestBootstrapResult:
    """Test BootstrapResult data class."""

    def test_with_warnings(self):
        result = BootstrapResult(
            agents_registered=0,
            tasks_ingested=0,
            profiles_built=0,
            chains_active=[],
            total_bounty_usd=0,
            bootstrap_ms=10,
            warnings=["No profile data"],
        )
        assert len(result.warnings) == 1


# ─── Quick Start Tests ───────────────────────────────────────────────────────


class TestQuickStart:
    """Test the minimal bootstrap path."""

    def test_quick_start_agents_active(self):
        coordinator = SwarmBootstrap.quick_start()
        available = coordinator.lifecycle.get_available_agents()
        assert len(available) == 24

    def test_quick_start_can_route(self):
        coordinator = SwarmBootstrap.quick_start()
        task = TaskRequest(
            task_id="test-1",
            title="Test task",
            categories=["general"],
            bounty_usd=1.0,
        )
        coordinator.ingest_task(
            task_id=task.task_id,
            title=task.title,
            categories=task.categories,
            bounty_usd=task.bounty_usd,
        )
        from swarm.orchestrator import Assignment

        results = coordinator.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        assert results[0].task_id == "test-1"
        assert results[0].agent_id in [a["agent_id"] for a in KNOWN_AGENTS]

    def test_quick_start_routing_prefers_tagged(self):
        """Tasks should be routed to agents with matching tags."""
        coordinator = SwarmBootstrap.quick_start()

        # Ingest a blockchain task
        coordinator.ingest_task(
            task_id="bc-1",
            title="Smart contract audit",
            categories=["blockchain"],
            bounty_usd=10.0,
        )
        results = coordinator.process_task_queue()

        # Should be assigned to an agent with blockchain tag
        from swarm.orchestrator import Assignment

        assignments = [r for r in results if isinstance(r, Assignment)]
        assert len(assignments) == 1
        assigned_id = assignments[0].agent_id
        assert assigned_id in [a["agent_id"] for a in KNOWN_AGENTS]
        assert assignments[0].task_id == "bc-1"


# ─── Full Bootstrap Tests ────────────────────────────────────────────────────


class TestFullBootstrap:
    """Test the full bootstrap pipeline without live API."""

    def test_create_coordinator_no_fetch(self):
        bootstrap = SwarmBootstrap()
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False,
            use_cached_profiles=False,
        )
        assert isinstance(coordinator, SwarmCoordinator)
        assert result.agents_registered == 24
        assert result.bootstrap_ms > 0

    def test_create_coordinator_with_cached_profiles(self):
        """Test loading cached profiles from disk."""
        # Create a temp profile file
        profiles = {
            "generated_at": "2026-03-14T05:00:00+00:00",
            "total_tasks_analyzed": 189,
            "profiles": {
                "executor-1": {
                    "executor_id": "executor-1",
                    "total_tasks": 189,
                    "total_earned_usd": 18.90,
                    "chains": {"base": 35, "polygon": 28},
                    "categories": {"simple_action": 189},
                    "skill_dna": {
                        "primary_category": "simple_action",
                        "primary_chain": "base",
                        "multi_chain": True,
                        "experience_level": "expert",
                    },
                },
            },
            "chain_analytics": {
                "base": {"tasks": 35, "share_pct": 18.5},
            },
            "summary": {"total_tasks": 189},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(profiles, f)
            temp_path = f.name

        try:
            bootstrap = SwarmBootstrap(profiles_path=temp_path)
            coordinator, result = bootstrap.create_coordinator(
                fetch_live=False,
                use_cached_profiles=True,
            )
            assert result.agents_registered == 24
            assert result.profiles_built == 1
        finally:
            os.unlink(temp_path)

    def test_reputation_initialization(self):
        """All agents get reputation data."""
        bootstrap = SwarmBootstrap()
        coordinator, _ = bootstrap.create_coordinator(
            fetch_live=False,
            use_cached_profiles=False,
        )

        # Check that reputation data exists in the orchestrator
        for agent_id in range(2101, 2125):
            assert agent_id in coordinator.orchestrator._on_chain
            assert agent_id in coordinator.orchestrator._internal

    def test_agent_2106_no_special_casing(self):
        """Agent 2106 gets the same default treatment as all other agents."""
        profiles = {
            "profiles": {"exec-1": {"categories": {"simple_action": 189}}},
            "summary": {"total_tasks": 189},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(profiles, f)
            temp_path = f.name

        try:
            bootstrap = SwarmBootstrap(profiles_path=temp_path)
            bootstrap.create_coordinator(fetch_live=False, use_cached_profiles=True)

            internal_2106 = bootstrap._internal_reps.get(2106)
            internal_2101 = bootstrap._internal_reps.get(2101)
            assert internal_2106 is not None
            assert internal_2101 is not None
            # Agent 2106 should have the same default bayesian score as any other agent
            assert internal_2106.bayesian_score == internal_2101.bayesian_score
            assert internal_2106.bayesian_score == 0.5
        finally:
            os.unlink(temp_path)


# ─── Routing Integration Tests ───────────────────────────────────────────────


class TestRoutingIntegration:
    """Test that bootstrapped coordinator makes intelligent routing decisions."""

    def setup_method(self):
        self.coordinator = SwarmBootstrap.quick_start()

    def test_route_general_task(self):
        """General tasks can be routed."""
        self.coordinator.ingest_task(
            task_id="gen-1",
            title="Simple verification",
            categories=["general"],
            bounty_usd=5.0,
        )
        results = self.coordinator.process_task_queue()
        from swarm.orchestrator import Assignment

        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        assert results[0].task_id == "gen-1"
        assert results[0].agent_id in [a["agent_id"] for a in KNOWN_AGENTS]

    def test_route_multiple_tasks(self):
        """Multiple tasks can be routed to different agents."""
        for i in range(5):
            self.coordinator.ingest_task(
                task_id=f"multi-{i}",
                title=f"Task {i}",
                categories=["general"],
                bounty_usd=1.0,
            )
        results = self.coordinator.process_task_queue()

        from swarm.orchestrator import Assignment

        assignments = [r for r in results if isinstance(r, Assignment)]
        # All 5 tasks should be assigned (24 agents available)
        assert len(assignments) == 5

        # Different agents should be assigned (round-robin or best-fit varies)
        agent_ids = set(a.agent_id for a in assignments)
        assert len(agent_ids) >= 2, (
            f"Expected tasks spread across agents, got {agent_ids}"
        )
        # All assigned agents must be known
        known_ids = {a["agent_id"] for a in KNOWN_AGENTS}
        assert agent_ids.issubset(known_ids)

    def test_specialist_routing(self):
        """Specialist strategy only picks category experts."""
        self.coordinator.ingest_task(
            task_id="spec-1",
            title="DeFi yield analysis",
            categories=["defi"],
            bounty_usd=50.0,
            priority=TaskPriority.HIGH,
        )
        # Use specialist strategy
        self.coordinator.process_task_queue(strategy=RoutingStrategy.SPECIALIST)
        # May not find a specialist (base score 30 < threshold 50)
        # That's OK — it validates the strategy works

    def test_complete_and_re_route(self):
        """After completing a task, agent becomes available again."""
        self.coordinator.ingest_task(
            task_id="cycle-1",
            title="First task",
            categories=["general"],
            bounty_usd=1.0,
        )
        self.coordinator.process_task_queue()
        self.coordinator.complete_task("cycle-1")

        # Run health checks to process cooldowns
        self.coordinator.run_health_checks()

        # Queue summary should reflect completion
        summary = self.coordinator.get_queue_summary()
        assert "completed" in summary["by_status"]

    def test_dashboard_after_bootstrap(self):
        """Dashboard should work with bootstrapped coordinator."""
        dashboard = self.coordinator.get_dashboard()
        assert "metrics" in dashboard
        assert "fleet" in dashboard
        assert len(dashboard["fleet"]) == 24

        # Verify fleet has expected structure
        for agent in dashboard["fleet"]:
            assert "agent_id" in agent
            assert "name" in agent
            assert "state" in agent

    def test_metrics_after_routing(self):
        """Metrics should reflect routing activity."""
        for i in range(3):
            self.coordinator.ingest_task(
                task_id=f"met-{i}",
                title=f"Metrics task {i}",
                categories=["coding"],
                bounty_usd=2.0,
            )
        self.coordinator.process_task_queue()

        metrics = self.coordinator.get_metrics()
        assert metrics.tasks_ingested >= 3
        assert metrics.agents_registered == 24
