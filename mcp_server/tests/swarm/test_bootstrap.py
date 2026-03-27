"""
Tests for SwarmBootstrap — Initialize the coordinator from production data.

Covers:
    - DEFAULT_AGENTS registry and KNOWN_AGENTS alias
    - BootstrapResult dataclass and serialization
    - SwarmBootstrap initialization and configuration
    - create_coordinator() full pipeline (no live fetch)
    - Profile caching (save/load)
    - Agent registration
    - Reputation data building
    - Coordinator wiring with all components
    - quick_start() factory method
    - Error handling and warnings
"""

import json
import os
import tempfile

import pytest

from mcp_server.swarm.bootstrap import (
    DEFAULT_AGENTS,
    KNOWN_AGENTS,
    BootstrapResult,
    SwarmBootstrap,
)
from mcp_server.swarm.coordinator import SwarmCoordinator
from mcp_server.swarm.orchestrator import RoutingStrategy


# ─── DEFAULT_AGENTS Registry ─────────────────────────────────────


class TestDefaultAgents:
    def test_agent_count(self):
        assert len(DEFAULT_AGENTS) == 24

    def test_known_agents_alias(self):
        assert KNOWN_AGENTS is DEFAULT_AGENTS

    def test_agent_structure(self):
        for agent in DEFAULT_AGENTS:
            assert "agent_id" in agent
            assert "name" in agent
            assert "personality" in agent
            assert "tags" in agent
            assert isinstance(agent["tags"], list)

    def test_agent_ids_unique(self):
        ids = [a["agent_id"] for a in DEFAULT_AGENTS]
        assert len(ids) == len(set(ids))

    def test_agent_ids_in_2100_range(self):
        for agent in DEFAULT_AGENTS:
            assert 2100 <= agent["agent_id"] <= 2200

    def test_ultravioleta_is_present(self):
        uv = [a for a in DEFAULT_AGENTS if a["name"] == "UltraVioleta"]
        assert len(uv) == 1
        assert uv[0]["agent_id"] == 2106
        assert uv[0]["personality"] == "orchestrator"

    def test_personalities_are_valid(self):
        valid = {"explorer", "strategist", "executor", "analyst", "specialist", "orchestrator"}
        for agent in DEFAULT_AGENTS:
            assert agent["personality"] in valid, f"Invalid personality: {agent['personality']}"

    def test_all_agents_have_at_least_two_tags(self):
        for agent in DEFAULT_AGENTS:
            assert len(agent["tags"]) >= 2, f"Agent {agent['name']} has too few tags"


# ─── BootstrapResult ─────────────────────────────────────────────


class TestBootstrapResult:
    def test_basic_creation(self):
        result = BootstrapResult(
            agents_registered=24,
            tasks_ingested=100,
            profiles_built=5,
            chains_active=["base", "ethereum"],
            total_bounty_usd=150.50,
            bootstrap_ms=250.3,
        )
        assert result.agents_registered == 24
        assert result.chains_active == ["base", "ethereum"]
        assert result.warnings == []

    def test_to_dict(self):
        result = BootstrapResult(
            agents_registered=10,
            tasks_ingested=50,
            profiles_built=3,
            chains_active=["base"],
            total_bounty_usd=99.999,
            bootstrap_ms=100.123,
            warnings=["No cached profiles"],
        )
        d = result.to_dict()
        assert d["agents_registered"] == 10
        assert d["total_bounty_usd"] == 100.0  # rounded
        assert d["bootstrap_ms"] == 100.1
        assert d["warnings"] == ["No cached profiles"]

    def test_empty_chains(self):
        result = BootstrapResult(
            agents_registered=0,
            tasks_ingested=0,
            profiles_built=0,
            chains_active=[],
            total_bounty_usd=0.0,
            bootstrap_ms=5.0,
        )
        assert result.chains_active == []


# ─── SwarmBootstrap Init ─────────────────────────────────────────


class TestSwarmBootstrapInit:
    def test_default_initialization(self):
        bootstrap = SwarmBootstrap()
        assert bootstrap.em_api_url == "https://api.execution.market"
        assert bootstrap.em_api_key is None
        assert bootstrap.autojob_url == "http://localhost:8765"
        assert bootstrap.default_strategy == RoutingStrategy.BEST_FIT

    def test_custom_initialization(self):
        bootstrap = SwarmBootstrap(
            em_api_url="https://custom.api.com",
            em_api_key="test-key",
            autojob_url="http://autojob:9999",
            default_strategy=RoutingStrategy.ROUND_ROBIN,
        )
        assert bootstrap.em_api_url == "https://custom.api.com"
        assert bootstrap.em_api_key == "test-key"
        assert bootstrap.autojob_url == "http://autojob:9999"

    def test_custom_agents(self):
        custom = [
            {"agent_id": 9001, "name": "TestAgent", "personality": "explorer", "tags": ["test"]},
        ]
        bootstrap = SwarmBootstrap(agents=custom)
        assert bootstrap._custom_agents == custom

    def test_profiles_path_default(self):
        bootstrap = SwarmBootstrap()
        assert "em-production-profiles.json" in bootstrap.profiles_path


# ─── create_coordinator() ────────────────────────────────────────


class TestCreateCoordinator:
    def test_create_without_fetch(self):
        """Create coordinator without live API calls."""
        bootstrap = SwarmBootstrap()
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )

        assert isinstance(coordinator, SwarmCoordinator)
        assert isinstance(result, BootstrapResult)
        assert result.agents_registered == 24
        assert result.tasks_ingested == 0
        assert result.bootstrap_ms > 0
        assert any("No profile data" in w for w in result.warnings)

    def test_create_registers_all_default_agents(self):
        bootstrap = SwarmBootstrap()
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        assert result.agents_registered == 24

    def test_create_with_custom_agents(self):
        custom = [
            {"agent_id": 9001, "name": "Alpha", "personality": "explorer", "tags": ["general"]},
            {"agent_id": 9002, "name": "Beta", "personality": "analyst", "tags": ["research"]},
        ]
        bootstrap = SwarmBootstrap(agents=custom)
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        assert result.agents_registered == 2

    def test_create_with_cached_profiles(self):
        """Test loading cached profiles from disk."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_data = {
                "profiles": {
                    "worker1": {
                        "executor_id": "worker1",
                        "total_tasks": 10,
                        "total_earned_usd": 50.0,
                    }
                },
                "chain_analytics": {"base": {"tasks": 10}},
                "summary": {"total_tasks": 10},
            }
            json.dump(cache_data, f)
            cache_path = f.name

        try:
            bootstrap = SwarmBootstrap(profiles_path=cache_path)
            coordinator, result = bootstrap.create_coordinator(
                fetch_live=False, use_cached_profiles=True
            )
            assert result.agents_registered == 24
            assert len(bootstrap._profiles) == 1
        finally:
            os.unlink(cache_path)

    def test_create_with_invalid_cache_file(self):
        """Test graceful handling of corrupted cache file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{{{")
            cache_path = f.name

        try:
            bootstrap = SwarmBootstrap(profiles_path=cache_path)
            # Should not raise, just warn
            coordinator, result = bootstrap.create_coordinator(
                fetch_live=False, use_cached_profiles=True
            )
            assert isinstance(coordinator, SwarmCoordinator)
        finally:
            os.unlink(cache_path)

    def test_result_chains_default_to_base(self):
        """When no tasks, chains should default to ['base']."""
        bootstrap = SwarmBootstrap()
        _, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        assert result.chains_active == ["base"]


# ─── Reputation Building ────────────────────────────────────────


class TestReputationBuilding:
    def test_reputation_built_for_all_agents(self):
        bootstrap = SwarmBootstrap()
        bootstrap._agents = list(DEFAULT_AGENTS)
        bootstrap._build_reputation_data()

        assert len(bootstrap._on_chain_reps) == 24
        assert len(bootstrap._internal_reps) == 24

    def test_on_chain_reputation_structure(self):
        bootstrap = SwarmBootstrap()
        bootstrap._agents = list(DEFAULT_AGENTS)
        bootstrap._build_reputation_data()

        rep = bootstrap._on_chain_reps[2101]
        assert rep.agent_id == 2101
        assert rep.wallet_address.startswith("0x")
        assert rep.chains_active == ["base"]

    def test_internal_reputation_structure(self):
        bootstrap = SwarmBootstrap()
        bootstrap._agents = list(DEFAULT_AGENTS)
        bootstrap._build_reputation_data()

        rep = bootstrap._internal_reps[2101]
        assert rep.agent_id == 2101
        assert rep.bayesian_score == 0.5
        # Should have category scores from agent tags
        assert len(rep.category_scores) >= 2

    def test_tag_based_category_scores(self):
        """Agent tags should become base category scores."""
        custom = [
            {"agent_id": 9999, "name": "Test", "personality": "explorer",
             "tags": ["coding", "blockchain", "defi"]},
        ]
        bootstrap = SwarmBootstrap(agents=custom)
        bootstrap._agents = custom
        bootstrap._build_reputation_data()

        rep = bootstrap._internal_reps[9999]
        assert "coding" in rep.category_scores
        assert "blockchain" in rep.category_scores
        assert "defi" in rep.category_scores
        assert rep.category_scores["coding"] == 30  # base competence


# ─── Profile Building from History ───────────────────────────────


class TestProfileBuilding:
    def test_build_profiles_from_empty_history(self):
        bootstrap = SwarmBootstrap()
        bootstrap._completed_tasks = []
        bootstrap._build_profiles_from_history()
        assert len(bootstrap._profiles) == 0

    def test_build_profiles_from_tasks(self):
        tasks = [
            {
                "executor_id": "worker_a",
                "payment_network": "base",
                "category": "delivery",
                "bounty_usd": 5.0,
            },
            {
                "executor_id": "worker_a",
                "payment_network": "ethereum",
                "category": "coding",
                "bounty_usd": 20.0,
            },
            {
                "executor_id": "worker_b",
                "payment_network": "base",
                "category": "delivery",
                "bounty_usd": 3.0,
            },
        ]

        bootstrap = SwarmBootstrap()
        bootstrap._completed_tasks = tasks
        bootstrap._build_profiles_from_history()

        assert len(bootstrap._profiles) == 2
        assert bootstrap._profiles["worker_a"]["total_tasks"] == 2
        assert bootstrap._profiles["worker_a"]["total_earned_usd"] == 25.0
        assert bootstrap._profiles["worker_b"]["total_tasks"] == 1

    def test_profile_skill_dna(self):
        tasks = [
            {"executor_id": "w1", "payment_network": "base", "category": "coding", "bounty_usd": 10},
        ] * 25  # 25 tasks → intermediate

        bootstrap = SwarmBootstrap()
        bootstrap._completed_tasks = tasks
        bootstrap._build_profiles_from_history()

        profile = bootstrap._profiles["w1"]
        assert profile["skill_dna"]["primary_category"] == "coding"
        assert profile["skill_dna"]["primary_chain"] == "base"
        assert profile["skill_dna"]["multi_chain"] is False
        assert profile["skill_dna"]["experience_level"] == "intermediate"

    def test_experience_levels(self):
        """Test all experience level thresholds."""
        levels = [
            (5, "beginner"),
            (20, "intermediate"),
            (50, "advanced"),
            (100, "expert"),
        ]
        for count, expected_level in levels:
            tasks = [
                {"executor_id": "w", "payment_network": "base", "category": "general", "bounty_usd": 1}
            ] * count
            bootstrap = SwarmBootstrap()
            bootstrap._completed_tasks = tasks
            bootstrap._build_profiles_from_history()
            assert bootstrap._profiles["w"]["skill_dna"]["experience_level"] == expected_level, \
                f"Count {count} should be {expected_level}"

    def test_multi_chain_detection(self):
        tasks = [
            {"executor_id": "w", "payment_network": "base", "category": "general", "bounty_usd": 1},
            {"executor_id": "w", "payment_network": "ethereum", "category": "general", "bounty_usd": 1},
        ]
        bootstrap = SwarmBootstrap()
        bootstrap._completed_tasks = tasks
        bootstrap._build_profiles_from_history()
        assert bootstrap._profiles["w"]["skill_dna"]["multi_chain"] is True

    def test_tasks_without_executor_id_skipped(self):
        tasks = [
            {"payment_network": "base", "category": "general", "bounty_usd": 1},
            {"executor_id": "", "payment_network": "base", "category": "general", "bounty_usd": 1},
        ]
        bootstrap = SwarmBootstrap()
        bootstrap._completed_tasks = tasks
        bootstrap._build_profiles_from_history()
        assert len(bootstrap._profiles) == 0

    def test_missing_bounty_usd(self):
        tasks = [
            {"executor_id": "w", "payment_network": "base", "category": "general"},
        ]
        bootstrap = SwarmBootstrap()
        bootstrap._completed_tasks = tasks
        bootstrap._build_profiles_from_history()
        assert bootstrap._profiles["w"]["total_earned_usd"] == 0.0


# ─── Coordinator Wiring ──────────────────────────────────────────


class TestCoordinatorWiring:
    def test_coordinator_has_components(self):
        bootstrap = SwarmBootstrap()
        coordinator, _ = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        assert coordinator.bridge is not None
        assert coordinator.lifecycle is not None
        assert coordinator.orchestrator is not None
        assert coordinator.em_client is not None

    def test_coordinator_has_autojob_client(self):
        bootstrap = SwarmBootstrap()
        coordinator, _ = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        # SwarmCoordinator stores autojob_client as self.autojob
        assert coordinator.autojob is not None


# ─── quick_start() ───────────────────────────────────────────────


class TestQuickStart:
    def test_quick_start_returns_coordinator(self):
        coordinator = SwarmBootstrap.quick_start()
        assert isinstance(coordinator, SwarmCoordinator)

    def test_quick_start_has_agents(self):
        coordinator = SwarmBootstrap.quick_start()
        # Agents are tracked via the lifecycle manager
        assert len(coordinator.lifecycle.agents) == 24

    def test_quick_start_no_live_data(self):
        """quick_start should work completely offline."""
        coordinator = SwarmBootstrap.quick_start()
        assert coordinator is not None


# ─── Cache Persistence ───────────────────────────────────────────


class TestCachePersistence:
    def test_load_nonexistent_cache(self):
        bootstrap = SwarmBootstrap(profiles_path="/nonexistent/path.json")
        bootstrap._load_cached_profiles()
        assert len(bootstrap._profiles) == 0

    def test_load_valid_cache(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "profiles": {"w1": {"total_tasks": 5}},
                "chain_analytics": {},
                "summary": {"total_tasks": 5},
            }, f)
            path = f.name

        try:
            bootstrap = SwarmBootstrap(profiles_path=path)
            bootstrap._load_cached_profiles()
            assert "w1" in bootstrap._profiles
            assert len(bootstrap._completed_tasks) == 5
        finally:
            os.unlink(path)

    def test_load_corrupt_cache(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{corrupt json]]]")
            path = f.name

        try:
            bootstrap = SwarmBootstrap(profiles_path=path)
            bootstrap._load_cached_profiles()  # should not raise
            assert len(bootstrap._profiles) == 0
        finally:
            os.unlink(path)


# ─── Edge Cases ──────────────────────────────────────────────────


class TestBootstrapEdgeCases:
    def test_empty_agents_falls_back_to_defaults(self):
        """When custom agents list is empty, falls back to DEFAULT_AGENTS (empty list is falsy)."""
        bootstrap = SwarmBootstrap(agents=[])
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        # Empty list is falsy → `[] or DEFAULT_AGENTS` → uses defaults
        assert result.agents_registered == 24

    def test_none_agents_uses_defaults(self):
        """When agents=None (default), uses DEFAULT_AGENTS."""
        bootstrap = SwarmBootstrap(agents=None)
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        assert result.agents_registered == 24

    def test_single_agent(self):
        custom = [
            {"agent_id": 1, "name": "Solo", "personality": "explorer", "tags": ["general"]},
        ]
        bootstrap = SwarmBootstrap(agents=custom)
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        assert result.agents_registered == 1

    def test_duplicate_agent_ids_handled(self):
        """Duplicate agent IDs should be handled gracefully."""
        custom = [
            {"agent_id": 1, "name": "Alpha", "personality": "explorer", "tags": ["general"]},
            {"agent_id": 1, "name": "Beta", "personality": "analyst", "tags": ["research"]},
        ]
        bootstrap = SwarmBootstrap(agents=custom)
        # Second registration might overwrite or fail gracefully
        coordinator, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        # At least one should register
        assert result.agents_registered >= 1

    def test_bootstrap_result_serializable(self):
        bootstrap = SwarmBootstrap()
        _, result = bootstrap.create_coordinator(
            fetch_live=False, use_cached_profiles=False
        )
        d = result.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["agents_registered"] == 24
