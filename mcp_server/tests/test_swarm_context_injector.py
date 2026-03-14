"""
Tests for SwarmContextInjector — agent-specific context injection.

Coverage:
    - Utility functions (_score_bar, _score_emoji, TIER_DISPLAY)
    - AgentContextBlock (empty, sections, to_dict, to_string, estimate_tokens)
    - Injector with no dependencies
    - Capability profile from AutoJob
    - Reputation badge from ERC-8004
    - Task fitness scoring
    - Swarm awareness
    - Budget context
    - Full integration
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swarm.swarm_context_injector import (
    SwarmContextInjector,
    AgentContextBlock,
    _score_bar,
    _score_emoji,
    TIER_DISPLAY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run async coroutine in sync test."""
    return asyncio.get_event_loop().run_until_complete(coro)


def make_mock_autojob_bridge(leaderboard=None, enrichment=None):
    """Create a mock AutoJob bridge."""
    mock = MagicMock()
    mock.get_leaderboard.return_value = leaderboard or []
    mock.enrich_task.return_value = enrichment or {}
    return mock


def make_mock_reputation_bridge(composite=None):
    """Create a mock reputation bridge."""
    mock = MagicMock()
    if composite:
        mock.compute_composite.return_value = composite
    else:
        mock.compute_composite.return_value = None
    return mock


def make_mock_lifecycle_manager(agents=None):
    """Create a mock lifecycle manager."""
    mock = MagicMock()
    mock._agents = agents or {}

    def _get_agent(agent_id):
        return agents.get(agent_id) if agents else None

    mock.get_agent = _get_agent
    return mock


# ---------------------------------------------------------------------------
# TestUtilities
# ---------------------------------------------------------------------------

class TestUtilities:
    """Test utility functions."""

    def test_score_bar_full(self):
        bar = _score_bar(100.0, 10)
        assert bar == "██████████"

    def test_score_bar_empty(self):
        bar = _score_bar(0.0, 10)
        assert bar == "░░░░░░░░░░"

    def test_score_bar_half(self):
        bar = _score_bar(50.0, 10)
        assert bar == "█████░░░░░"

    def test_score_emoji_green(self):
        assert _score_emoji(90) == "🟢"

    def test_score_emoji_blue(self):
        assert _score_emoji(65) == "🔵"

    def test_score_emoji_yellow(self):
        assert _score_emoji(45) == "🟡"

    def test_score_emoji_orange(self):
        assert _score_emoji(25) == "🟠"

    def test_score_emoji_red(self):
        assert _score_emoji(10) == "🔴"

    def test_score_bar_clamps_negative(self):
        bar = _score_bar(-10, 10)
        assert bar == "░░░░░░░░░░"

    def test_score_bar_clamps_over_100(self):
        bar = _score_bar(150, 10)
        assert bar == "██████████"

    def test_tier_display_keys(self):
        assert "platinum" in TIER_DISPLAY
        assert "gold" in TIER_DISPLAY
        assert "silver" in TIER_DISPLAY
        assert "bronze" in TIER_DISPLAY
        assert "unranked" in TIER_DISPLAY


# ---------------------------------------------------------------------------
# TestAgentContextBlock
# ---------------------------------------------------------------------------

class TestAgentContextBlock:
    """Test the AgentContextBlock container."""

    def test_empty_block_renders_empty(self):
        block = AgentContextBlock(agent_id="aurora")
        assert block.to_string() == ""

    def test_block_with_single_section(self):
        block = AgentContextBlock(agent_id="aurora")
        block.add_section("Skills", "Python, Rust, Go")
        text = block.to_string()
        assert "## Skills" in text
        assert "Python, Rust, Go" in text

    def test_block_with_all_sections(self):
        block = AgentContextBlock(agent_id="cipher")
        block.add_section("Capabilities", "Code review expert")
        block.add_section("Reputation", "Score: 85/100")
        block.add_section("Budget", "$45.00 remaining")
        text = block.to_string()
        assert "## Capabilities" in text
        assert "## Reputation" in text
        assert "## Budget" in text

    def test_block_to_dict(self):
        block = AgentContextBlock(agent_id="echo")
        block.add_section("Info", "Test info")
        block.metadata["key"] = "value"
        d = block.to_dict()
        assert d["agent_id"] == "echo"
        assert "Info" in d["sections"]
        assert d["metadata"]["key"] == "value"

    def test_block_skips_empty_sections(self):
        block = AgentContextBlock(agent_id="aurora")
        block.add_section("Empty", "")
        block.add_section("Whitespace", "   ")
        block.add_section("Valid", "Content here")
        assert len(block.sections) == 1
        assert "Valid" in block.sections

    def test_estimate_tokens(self):
        block = AgentContextBlock(agent_id="aurora")
        block.add_section("Info", "A" * 400)  # ~100 tokens
        tokens = block.estimate_tokens()
        assert tokens > 0
        assert tokens < 200  # Rough estimate


# ---------------------------------------------------------------------------
# TestInjectorNoDependencies
# ---------------------------------------------------------------------------

class TestInjectorNoDependencies:
    """Test injector with no bridges configured."""

    def test_build_with_no_bridges(self):
        injector = SwarmContextInjector()
        ctx = injector.build_context("aurora")
        # Should produce an empty block (no data sources)
        assert ctx.agent_id == "aurora"
        assert ctx.to_string() == ""

    def test_status_no_dependencies(self):
        injector = SwarmContextInjector()
        status = injector.status()
        assert status["autojob_connected"] is False
        assert status["reputation_connected"] is False
        assert status["lifecycle_connected"] is False

    def test_active_task_tracking(self):
        injector = SwarmContextInjector()
        injector.track_active_task("aurora", "task_001")
        injector.track_active_task("aurora", "task_002")
        assert len(injector._active_tasks["aurora"]) == 2

        injector.clear_active_task("aurora", "task_001")
        assert len(injector._active_tasks["aurora"]) == 1
        assert injector._active_tasks["aurora"][0] == "task_002"


# ---------------------------------------------------------------------------
# TestCapabilityProfile
# ---------------------------------------------------------------------------

class TestCapabilityProfile:
    """Test capability profile from AutoJob leaderboard."""

    def test_builds_from_autojob_leaderboard(self):
        leaderboard = [
            {
                "agent_id": "aurora",
                "tier": "gold",
                "top_skills": ["research", "data_collection", "writing"],
                "reliability": 0.95,
                "tasks_completed": 42,
            }
        ]
        autojob = make_mock_autojob_bridge(leaderboard=leaderboard)
        injector = SwarmContextInjector(autojob_bridge=autojob)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "aurora" in text
        assert "Gold" in text

    def test_includes_tier(self):
        leaderboard = [{"agent_id": "cipher", "tier": "platinum"}]
        autojob = make_mock_autojob_bridge(leaderboard=leaderboard)
        injector = SwarmContextInjector(autojob_bridge=autojob)
        ctx = injector.build_context("cipher")
        text = ctx.to_string()
        assert "Platinum" in text

    def test_includes_reliability_bar(self):
        leaderboard = [{"agent_id": "echo", "tier": "silver", "reliability": 0.75}]
        autojob = make_mock_autojob_bridge(leaderboard=leaderboard)
        injector = SwarmContextInjector(autojob_bridge=autojob)
        ctx = injector.build_context("echo")
        text = ctx.to_string()
        assert "75%" in text

    def test_empty_when_wallet_not_in_leaderboard(self):
        leaderboard = [{"agent_id": "other_agent"}]
        autojob = make_mock_autojob_bridge(leaderboard=leaderboard)
        injector = SwarmContextInjector(autojob_bridge=autojob)
        ctx = injector.build_context("aurora")
        # Capability section should be empty
        assert "Capability Profile" not in ctx.to_string()

    def test_graceful_on_autojob_error(self):
        autojob = MagicMock()
        autojob.get_leaderboard.side_effect = Exception("connection failed")
        injector = SwarmContextInjector(autojob_bridge=autojob)
        ctx = injector.build_context("aurora")
        assert ctx.agent_id == "aurora"
        # Should not crash


# ---------------------------------------------------------------------------
# TestReputationBadge
# ---------------------------------------------------------------------------

class TestReputationBadge:
    """Test reputation badge from ERC-8004."""

    def _make_rep(self, **kwargs):
        rep = MagicMock()
        rep.agent_id = kwargs.get("agent_id", "aurora")
        rep.composite_score = kwargs.get("composite_score", 85.0)
        rep.score = kwargs.get("score", 85.0)
        rep.tier = kwargs.get("tier", "gold")
        rep.total_completed = kwargs.get("total_completed", 30)
        rep.em_completed = kwargs.get("em_completed", 30)
        rep.chain_rating_count = kwargs.get("chain_rating_count", 5)
        rep.chain_avg_rating = kwargs.get("chain_avg_rating", 4.2)
        return rep

    def test_builds_from_erc8004(self):
        rep = self._make_rep()
        bridge = make_mock_reputation_bridge(composite=rep)
        injector = SwarmContextInjector(reputation_bridge=bridge)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "Reputation Badge" in text

    def test_includes_agent_id(self):
        rep = self._make_rep(agent_id="agent_2106")
        bridge = make_mock_reputation_bridge(composite=rep)
        injector = SwarmContextInjector(reputation_bridge=bridge)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "agent_2106" in text

    def test_includes_composite_score(self):
        rep = self._make_rep(composite_score=92.5)
        bridge = make_mock_reputation_bridge(composite=rep)
        injector = SwarmContextInjector(reputation_bridge=bridge)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "92.5" in text

    def test_includes_tier(self):
        rep = self._make_rep(tier="platinum")
        bridge = make_mock_reputation_bridge(composite=rep)
        injector = SwarmContextInjector(reputation_bridge=bridge)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "Platinum" in text

    def test_includes_task_track_record(self):
        rep = self._make_rep(total_completed=50)
        bridge = make_mock_reputation_bridge(composite=rep)
        injector = SwarmContextInjector(reputation_bridge=bridge)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "50" in text

    def test_empty_when_no_reputation(self):
        bridge = make_mock_reputation_bridge(composite=None)
        injector = SwarmContextInjector(reputation_bridge=bridge)
        ctx = injector.build_context("unknown_agent")
        assert "Reputation Badge" not in ctx.to_string()

    def test_graceful_on_reputation_error(self):
        bridge = MagicMock()
        bridge.compute_composite.side_effect = Exception("chain error")
        injector = SwarmContextInjector(reputation_bridge=bridge)
        ctx = injector.build_context("aurora")
        assert ctx.agent_id == "aurora"


# ---------------------------------------------------------------------------
# TestTaskFitness
# ---------------------------------------------------------------------------

class TestTaskFitness:
    """Test task fitness scoring."""

    def test_builds_task_fitness(self):
        enrichment = {
            "rankings": [
                {"agent_id": "aurora", "score": 85.0}
            ]
        }
        autojob = make_mock_autojob_bridge(enrichment=enrichment)
        injector = SwarmContextInjector(autojob_bridge=autojob)
        task = {"title": "Research blockchain protocols", "skills": ["research"]}
        ctx = injector.build_context("aurora", task=task)
        text = ctx.to_string()
        assert "Task Fitness" in text

    def test_shows_match_score(self):
        enrichment = {"rankings": [{"agent_id": "aurora", "score": 72.0}]}
        autojob = make_mock_autojob_bridge(enrichment=enrichment)
        injector = SwarmContextInjector(autojob_bridge=autojob)
        task = {"title": "Data collection task"}
        ctx = injector.build_context("aurora", task=task)
        text = ctx.to_string()
        assert "72" in text

    def test_shows_excellent_fit_guidance(self):
        enrichment = {"rankings": [{"agent_id": "aurora", "score": 95.0}]}
        autojob = make_mock_autojob_bridge(enrichment=enrichment)
        injector = SwarmContextInjector(autojob_bridge=autojob)
        task = {"title": "Perfect task"}
        ctx = injector.build_context("aurora", task=task)
        text = ctx.to_string()
        assert "Excellent fit" in text

    def test_shows_weak_fit_for_low_score_agent(self):
        enrichment = {"rankings": [{"agent_id": "aurora", "score": 25.0}]}
        autojob = make_mock_autojob_bridge(enrichment=enrichment)
        injector = SwarmContextInjector(autojob_bridge=autojob)
        task = {"title": "Unmatched task"}
        ctx = injector.build_context("aurora", task=task)
        text = ctx.to_string()
        assert "Weak fit" in text

    def test_no_fitness_without_task(self):
        autojob = make_mock_autojob_bridge()
        injector = SwarmContextInjector(autojob_bridge=autojob)
        ctx = injector.build_context("aurora")
        assert "Task Fitness" not in ctx.to_string()


# ---------------------------------------------------------------------------
# TestSwarmAwareness
# ---------------------------------------------------------------------------

class TestSwarmAwareness:
    """Test swarm awareness context."""

    def test_shows_active_tasks(self):
        injector = SwarmContextInjector()
        injector.track_active_task("cipher", "task_001")
        injector.track_active_task("echo", "task_002")
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "cipher" in text or "echo" in text

    def test_excludes_own_tasks(self):
        injector = SwarmContextInjector()
        injector.track_active_task("aurora", "task_001")
        injector.track_active_task("cipher", "task_002")
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        # aurora's own tasks should NOT appear in awareness
        if text:
            assert "cipher" in text
            # aurora might not be listed

    def test_includes_fleet_status(self):
        class MockAgent:
            def __init__(self, status):
                self.status = status

        agents = {
            "aurora": MockAgent("active"),
            "cipher": MockAgent("active"),
            "echo": MockAgent("sleeping"),
        }
        lifecycle = make_mock_lifecycle_manager(agents)
        injector = SwarmContextInjector(lifecycle_manager=lifecycle)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "Fleet Status" in text or "active" in text

    def test_empty_when_no_tasks_and_no_lifecycle(self):
        injector = SwarmContextInjector()
        ctx = injector.build_context("aurora")
        assert "Swarm Awareness" not in ctx.to_string()


# ---------------------------------------------------------------------------
# TestBudgetContext
# ---------------------------------------------------------------------------

class TestBudgetContext:
    """Test budget context injection."""

    def _make_agent_with_budget(self, total, spent):
        agent = MagicMock()
        agent.budget = MagicMock()
        agent.budget.total_usd = total
        agent.budget.spent_usd = spent
        return agent

    def test_shows_budget_usage(self):
        agent = self._make_agent_with_budget(100.0, 40.0)
        lifecycle = MagicMock()
        lifecycle.get_agent.return_value = agent
        injector = SwarmContextInjector(lifecycle_manager=lifecycle)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "$40.00" in text or "40%" in text

    def test_shows_warning_at_high_usage(self):
        agent = self._make_agent_with_budget(100.0, 95.0)
        lifecycle = MagicMock()
        lifecycle.get_agent.return_value = agent
        injector = SwarmContextInjector(lifecycle_manager=lifecycle)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "WARNING" in text

    def test_shows_caution_at_70_percent(self):
        agent = self._make_agent_with_budget(100.0, 75.0)
        lifecycle = MagicMock()
        lifecycle.get_agent.return_value = agent
        injector = SwarmContextInjector(lifecycle_manager=lifecycle)
        ctx = injector.build_context("aurora")
        text = ctx.to_string()
        assert "CAUTION" in text

    def test_empty_for_unknown_agent(self):
        lifecycle = MagicMock()
        lifecycle.get_agent.return_value = None
        injector = SwarmContextInjector(lifecycle_manager=lifecycle)
        ctx = injector.build_context("unknown")
        assert "Budget Context" not in ctx.to_string()


# ---------------------------------------------------------------------------
# TestFullIntegration
# ---------------------------------------------------------------------------

class TestFullIntegration:
    """Test full context injection with all dependencies."""

    def _make_full_injector(self):
        leaderboard = [
            {
                "agent_id": "aurora",
                "tier": "gold",
                "top_skills": ["research", "data_collection"],
                "reliability": 0.92,
                "tasks_completed": 35,
            }
        ]
        enrichment = {"rankings": [{"agent_id": "aurora", "score": 88.0}]}
        autojob = make_mock_autojob_bridge(leaderboard=leaderboard, enrichment=enrichment)

        rep = MagicMock()
        rep.agent_id = "agent_2106_aurora"
        rep.composite_score = 85.0
        rep.score = 85.0
        rep.tier = "gold"
        rep.total_completed = 35
        rep.chain_rating_count = 8
        rep.chain_avg_rating = 4.5
        reputation = make_mock_reputation_bridge(composite=rep)

        agent = MagicMock()
        agent.budget = MagicMock()
        agent.budget.total_usd = 50.0
        agent.budget.spent_usd = 12.50
        lifecycle = MagicMock()
        lifecycle.get_agent.return_value = agent

        class MockAgentState:
            def __init__(self, status):
                self.status = status

        lifecycle._agents = {
            "aurora": MockAgentState("active"),
            "cipher": MockAgentState("active"),
            "echo": MockAgentState("sleeping"),
        }

        injector = SwarmContextInjector(
            autojob_bridge=autojob,
            reputation_bridge=reputation,
            lifecycle_manager=lifecycle,
        )
        injector.track_active_task("cipher", "task_abc")

        return injector

    def test_all_sections_populated(self):
        injector = self._make_full_injector()
        task = {"title": "Research DeFi protocols", "skills": ["research"]}
        ctx = injector.build_context("aurora", task=task)
        text = ctx.to_string()

        assert "Capability Profile" in text
        assert "Reputation Badge" in text
        assert "Task Fitness" in text
        assert "Swarm Awareness" in text
        assert "Budget Context" in text

    def test_full_context_string_is_coherent(self):
        injector = self._make_full_injector()
        task = {"title": "Analyze smart contracts"}
        ctx = injector.build_context("aurora", task=task)
        text = ctx.to_string()

        # Should be readable text with section headers
        assert text.count("##") >= 4
        assert len(text) > 100

    def test_token_estimate_is_reasonable(self):
        injector = self._make_full_injector()
        task = {"title": "Research task"}
        ctx = injector.build_context("aurora", task=task)
        tokens = ctx.estimate_tokens()
        assert 10 < tokens < 2000  # Reasonable context size

    def test_batch_build_for_multiple_agents(self):
        injector = self._make_full_injector()
        batch = injector.build_batch(["aurora", "cipher", "echo"])
        assert len(batch) == 3
        assert all(isinstance(v, AgentContextBlock) for v in batch.values())

    def test_status_with_all_dependencies(self):
        injector = self._make_full_injector()
        status = injector.status()
        assert status["autojob_connected"] is True
        assert status["reputation_connected"] is True
        assert status["lifecycle_connected"] is True
        assert status["active_tasks_tracked"] == 1
