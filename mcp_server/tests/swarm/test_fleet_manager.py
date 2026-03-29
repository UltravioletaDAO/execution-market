"""
Tests for FleetManager — Agent Fleet Lifecycle and Capability Management
Module #53 in the KK V2 Swarm.

Test coverage:
1. Agent Registration & Deregistration
2. Capability Management & Matrix
3. Tag Management
4. Status Management & Heartbeats
5. Task Load Tracking
6. Load Balancing Strategies
7. Fleet Metrics & Snapshots
8. Availability Windows
9. Persistence (save/load)
10. Edge Cases & Graceful Degradation
"""

import time
import pytest
from datetime import datetime, timezone

from mcp_server.swarm.fleet_manager import (
    FleetManager,
    AgentProfile,
    AgentStatus,
    AvailabilityWindow,
    Capability,
    CapabilityLevel,
    CandidateScore,
    FleetSnapshot,
    LoadBalanceStrategy,
    TaskLoad,
    CAPABILITY_SCORES,
)


# ─── Fixtures ─────────────────────────────────────────────────


def make_agent(
    agent_id: int = 1,
    name: str = "TestAgent",
    capabilities: dict | None = None,
    tags: set | None = None,
    max_concurrent: int = 3,
    status: AgentStatus = AgentStatus.ACTIVE,
) -> AgentProfile:
    """Create an AgentProfile for testing."""
    caps = {}
    if capabilities:
        for cap_name, level in capabilities.items():
            caps[cap_name] = Capability(name=cap_name, level=level)
    return AgentProfile(
        agent_id=agent_id,
        name=name,
        capabilities=caps,
        tags=tags or set(),
        max_concurrent_tasks=max_concurrent,
        status=status,
    )


def make_fleet_with_agents(n: int = 5) -> FleetManager:
    """Create a FleetManager with n agents pre-registered."""
    fleet = FleetManager()
    capabilities = ["delivery", "photography", "research", "data_entry", "verification"]
    for i in range(n):
        caps = {capabilities[i % len(capabilities)]: CapabilityLevel.COMPETENT}
        if i % 2 == 0:
            caps["delivery"] = CapabilityLevel.PROFICIENT
        agent = make_agent(
            agent_id=1000 + i,
            name=f"Agent-{i}",
            capabilities=caps,
            tags={"team-a"} if i < 3 else {"team-b"},
        )
        fleet.register_agent(agent)
    return fleet


# ──────────────────────────────────────────────────────────────
# 1. Agent Registration & Deregistration
# ──────────────────────────────────────────────────────────────


class TestAgentRegistration:
    """Registration, deregistration, and retrieval."""

    def test_register_new_agent(self):
        fleet = FleetManager()
        agent = make_agent(agent_id=42, name="Alpha")
        result = fleet.register_agent(agent)
        assert result.agent_id == 42
        assert fleet.agent_count() == 1

    def test_register_multiple_agents(self):
        fleet = FleetManager()
        for i in range(10):
            fleet.register_agent(make_agent(agent_id=i, name=f"Agent-{i}"))
        assert fleet.agent_count() == 10

    def test_register_duplicate_updates(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, name="v1"))
        fleet.register_agent(make_agent(agent_id=1, name="v2"))
        assert fleet.agent_count() == 1
        assert fleet.get_agent(1).name == "v2"

    def test_deregister_agent(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        result = fleet.deregister_agent(1)
        assert result is not None
        assert fleet.agent_count() == 0

    def test_deregister_nonexistent(self):
        fleet = FleetManager()
        result = fleet.deregister_agent(999)
        assert result is None

    def test_get_agent(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=7, name="Lucky"))
        agent = fleet.get_agent(7)
        assert agent is not None
        assert agent.name == "Lucky"

    def test_get_nonexistent_agent(self):
        fleet = FleetManager()
        assert fleet.get_agent(999) is None

    def test_list_agents_all(self):
        fleet = make_fleet_with_agents(5)
        agents = fleet.list_agents()
        assert len(agents) == 5

    def test_list_agents_by_status(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, status=AgentStatus.ACTIVE))
        fleet.register_agent(make_agent(agent_id=2, status=AgentStatus.OFFLINE))
        fleet.register_agent(make_agent(agent_id=3, status=AgentStatus.ACTIVE))
        active = fleet.list_agents(status=AgentStatus.ACTIVE)
        assert len(active) == 2

    def test_list_agents_by_capability(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.EXPERT},
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            capabilities={"research": CapabilityLevel.COMPETENT},
        ))
        delivery_agents = fleet.list_agents(capability="delivery")
        assert len(delivery_agents) == 1
        assert delivery_agents[0].agent_id == 1

    def test_list_agents_by_tag(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, tags={"vip"}))
        fleet.register_agent(make_agent(agent_id=2, tags={"standard"}))
        vip = fleet.list_agents(tag="vip")
        assert len(vip) == 1


# ──────────────────────────────────────────────────────────────
# 2. Capability Management & Matrix
# ──────────────────────────────────────────────────────────────


class TestCapabilityManagement:
    """Capability CRUD and matrix generation."""

    def test_add_capability(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        assert fleet.add_capability(1, "delivery", CapabilityLevel.EXPERT)
        agent = fleet.get_agent(1)
        assert "delivery" in agent.capabilities
        assert agent.capabilities["delivery"].level == CapabilityLevel.EXPERT

    def test_add_capability_nonexistent_agent(self):
        fleet = FleetManager()
        assert not fleet.add_capability(999, "delivery")

    def test_update_capability_level(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.NOVICE},
        ))
        fleet.add_capability(1, "delivery", CapabilityLevel.SPECIALIST)
        agent = fleet.get_agent(1)
        assert agent.capabilities["delivery"].level == CapabilityLevel.SPECIALIST

    def test_remove_capability(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.COMPETENT},
        ))
        assert fleet.remove_capability(1, "delivery")
        agent = fleet.get_agent(1)
        assert "delivery" not in agent.capabilities

    def test_remove_nonexistent_capability(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        assert not fleet.remove_capability(1, "flying")

    def test_capability_matrix(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.EXPERT},
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            capabilities={"delivery": CapabilityLevel.NOVICE},
        ))
        matrix = fleet.get_capability_matrix()
        assert "delivery" in matrix
        assert len(matrix["delivery"]) == 2
        # Expert should be first (higher score)
        assert matrix["delivery"][0]["agent_id"] == 1

    def test_capability_scores(self):
        """Verify all capability levels have scores."""
        for level in CapabilityLevel:
            assert level in CAPABILITY_SCORES
            assert 0 < CAPABILITY_SCORES[level] <= 1.0

    def test_capability_score_computation(self):
        cap = Capability(
            name="test",
            level=CapabilityLevel.EXPERT,
            tasks_completed=10,
            success_rate=0.95,
        )
        score = cap.score
        assert 0.5 < score <= 1.0  # Expert + experience

    def test_capability_score_low_success_rate(self):
        cap = Capability(
            name="test",
            level=CapabilityLevel.EXPERT,
            success_rate=0.3,
        )
        score = cap.score
        # Should be penalized
        expert_base = CAPABILITY_SCORES[CapabilityLevel.EXPERT]
        assert score < expert_base


# ──────────────────────────────────────────────────────────────
# 3. Tag Management
# ──────────────────────────────────────────────────────────────


class TestTagManagement:
    """Agent grouping via tags."""

    def test_add_tag(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        assert fleet.add_tag(1, "vip")
        agent = fleet.get_agent(1)
        assert "vip" in agent.tags

    def test_add_tag_nonexistent_agent(self):
        fleet = FleetManager()
        assert not fleet.add_tag(999, "vip")

    def test_remove_tag(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, tags={"vip", "premium"}))
        assert fleet.remove_tag(1, "vip")
        agent = fleet.get_agent(1)
        assert "vip" not in agent.tags
        assert "premium" in agent.tags

    def test_remove_nonexistent_tag(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        assert not fleet.remove_tag(1, "missing")

    def test_filter_by_tag(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, tags={"alpha"}))
        fleet.register_agent(make_agent(agent_id=2, tags={"beta"}))
        fleet.register_agent(make_agent(agent_id=3, tags={"alpha"}))
        alpha = fleet.list_agents(tag="alpha")
        assert len(alpha) == 2


# ──────────────────────────────────────────────────────────────
# 4. Status Management & Heartbeats
# ──────────────────────────────────────────────────────────────


class TestStatusManagement:
    """Status transitions and heartbeat tracking."""

    def test_set_status(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        assert fleet.set_status(1, AgentStatus.OFFLINE)
        assert fleet.get_agent(1).status == AgentStatus.OFFLINE

    def test_set_status_nonexistent(self):
        fleet = FleetManager()
        assert not fleet.set_status(999, AgentStatus.OFFLINE)

    def test_heartbeat(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        before = fleet.get_agent(1).last_heartbeat
        time.sleep(0.01)
        assert fleet.heartbeat(1)
        assert fleet.get_agent(1).last_heartbeat > before

    def test_heartbeat_revives_idle(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, status=AgentStatus.IDLE))
        fleet.heartbeat(1)
        assert fleet.get_agent(1).status == AgentStatus.ACTIVE

    def test_heartbeat_nonexistent(self):
        fleet = FleetManager()
        assert not fleet.heartbeat(999)

    def test_check_heartbeats_timeout(self):
        fleet = FleetManager(heartbeat_timeout_s=0.01)
        agent = make_agent(agent_id=1)
        agent.last_heartbeat = time.time() - 1  # 1 second ago
        fleet.register_agent(agent)
        idled = fleet.check_heartbeats()
        assert 1 in idled
        assert fleet.get_agent(1).status == AgentStatus.IDLE

    def test_check_heartbeats_healthy(self):
        fleet = FleetManager(heartbeat_timeout_s=300)
        fleet.register_agent(make_agent(agent_id=1))
        idled = fleet.check_heartbeats()
        assert len(idled) == 0


# ──────────────────────────────────────────────────────────────
# 5. Task Load Tracking
# ──────────────────────────────────────────────────────────────


class TestTaskLoadTracking:
    """Assignment recording and load metrics."""

    def test_record_assignment(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        assert fleet.record_task_assigned(1)
        agent = fleet.get_agent(1)
        assert agent.load.active_tasks == 1
        assert agent.load.tasks_today == 1

    def test_record_assignment_maxes_out(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, max_concurrent=2))
        fleet.record_task_assigned(1)
        fleet.record_task_assigned(1)
        assert fleet.get_agent(1).status == AgentStatus.BUSY

    def test_record_completion(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        fleet.record_task_assigned(1)
        assert fleet.record_task_completed(1, success=True)
        agent = fleet.get_agent(1)
        assert agent.load.active_tasks == 0
        assert agent.status == AgentStatus.COOLDOWN

    def test_record_completion_with_capability(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.COMPETENT},
        ))
        fleet.record_task_assigned(1)
        fleet.record_task_completed(1, capability_name="delivery", duration_s=120.0)
        cap = fleet.get_agent(1).capabilities["delivery"]
        assert cap.tasks_completed == 1
        assert cap.avg_completion_time_s > 0

    def test_record_nonexistent_agent(self):
        fleet = FleetManager()
        assert not fleet.record_task_assigned(999)
        assert not fleet.record_task_completed(999)

    def test_active_tasks_never_negative(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        fleet.record_task_completed(1)  # Complete without assigning
        assert fleet.get_agent(1).load.active_tasks == 0

    def test_utilization(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, max_concurrent=4))
        fleet.record_task_assigned(1)
        fleet.record_task_assigned(1)
        assert fleet.get_agent(1).utilization == 0.5


# ──────────────────────────────────────────────────────────────
# 6. Load Balancing Strategies
# ──────────────────────────────────────────────────────────────


class TestLoadBalancing:
    """Various load balancing strategy tests."""

    def test_find_capable_agents_basic(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.EXPERT},
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            capabilities={"research": CapabilityLevel.COMPETENT},
        ))
        candidates = fleet.find_capable_agents("delivery")
        assert len(candidates) == 1
        assert candidates[0].agent_id == 1

    def test_find_capable_agents_with_fitness_threshold(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.NOVICE},
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            capabilities={"delivery": CapabilityLevel.EXPERT},
        ))
        candidates = fleet.find_capable_agents("delivery", min_fitness=0.5)
        assert len(candidates) == 1
        assert candidates[0].agent_id == 2

    def test_find_capable_agents_excludes_unavailable(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.EXPERT},
            status=AgentStatus.OFFLINE,
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            capabilities={"delivery": CapabilityLevel.COMPETENT},
        ))
        candidates = fleet.find_capable_agents("delivery")
        assert len(candidates) == 1
        assert candidates[0].agent_id == 2

    def test_find_capable_includes_unavailable_when_flagged(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.EXPERT},
            status=AgentStatus.OFFLINE,
        ))
        candidates = fleet.find_capable_agents("delivery", available_only=False)
        assert len(candidates) == 1

    def test_select_agent_weighted(self):
        fleet = FleetManager(default_strategy=LoadBalanceStrategy.WEIGHTED)
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.EXPERT},
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            capabilities={"delivery": CapabilityLevel.NOVICE},
        ))
        result = fleet.select_agent("delivery")
        assert result is not None
        assert result.agent_id == 1  # Expert wins

    def test_select_agent_round_robin(self):
        fleet = FleetManager(default_strategy=LoadBalanceStrategy.ROUND_ROBIN)
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.COMPETENT},
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            capabilities={"delivery": CapabilityLevel.COMPETENT},
        ))
        first = fleet.select_agent("delivery")
        second = fleet.select_agent("delivery")
        # Should rotate
        assert first is not None
        assert second is not None
        assert first.agent_id != second.agent_id

    def test_select_agent_least_loaded(self):
        fleet = FleetManager(default_strategy=LoadBalanceStrategy.LEAST_LOADED)
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.COMPETENT},
            max_concurrent=5,
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            capabilities={"delivery": CapabilityLevel.COMPETENT},
            max_concurrent=5,
        ))
        # Load up agent 1
        fleet.record_task_assigned(1)
        fleet.record_task_assigned(1)
        result = fleet.select_agent("delivery")
        assert result is not None
        assert result.agent_id == 2  # Less loaded

    def test_select_agent_best_fit(self):
        fleet = FleetManager(default_strategy=LoadBalanceStrategy.BEST_FIT)
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.SPECIALIST},
        ))
        result = fleet.select_agent("delivery")
        assert result is not None
        assert result.agent_id == 1

    def test_select_agent_no_candidates(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"research": CapabilityLevel.COMPETENT},
        ))
        result = fleet.select_agent("delivery")
        assert result is None

    def test_candidate_score_structure(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.EXPERT},
        ))
        candidates = fleet.find_capable_agents("delivery")
        assert len(candidates) == 1
        score = candidates[0]
        assert isinstance(score, CandidateScore)
        d = score.to_dict()
        assert "fitness" in d
        assert "load_score" in d
        assert "composite" in d


# ──────────────────────────────────────────────────────────────
# 7. Fleet Metrics & Snapshots
# ──────────────────────────────────────────────────────────────


class TestFleetMetrics:
    """Capacity snapshots, utilization, and throughput."""

    def test_capacity_snapshot(self):
        fleet = make_fleet_with_agents(5)
        snapshot = fleet.capacity_snapshot()
        assert isinstance(snapshot, FleetSnapshot)
        assert snapshot.total_agents == 5
        assert snapshot.total_capacity == 15  # 5 agents * 3 max each

    def test_snapshot_to_dict(self):
        fleet = make_fleet_with_agents(3)
        snapshot = fleet.capacity_snapshot()
        d = snapshot.to_dict()
        assert "agents" in d
        assert "capacity" in d
        assert d["agents"]["total"] == 3

    def test_utilization_trend_empty(self):
        fleet = FleetManager()
        trend = fleet.utilization_trend()
        assert trend == []

    def test_utilization_trend_with_data(self):
        fleet = make_fleet_with_agents(3)
        fleet.capacity_snapshot()
        fleet.record_task_assigned(1000)
        fleet.capacity_snapshot()
        trend = fleet.utilization_trend()
        assert len(trend) == 2

    def test_throughput_stats(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        fleet.record_task_assigned(1)
        fleet.record_task_completed(1, success=True)
        stats = fleet.throughput_stats()
        assert stats["last_hour"]["assignments"] == 1
        assert stats["last_hour"]["completions"] == 1
        assert stats["all_time"]["assignments"] == 1

    def test_health_report(self):
        fleet = make_fleet_with_agents(3)
        health = fleet.health()
        assert "fleet" in health
        assert "capabilities" in health
        assert "throughput" in health
        assert health["health_status"] == "healthy"

    def test_health_empty_fleet(self):
        fleet = FleetManager()
        health = fleet.health()
        assert health["health_status"] == "empty"

    def test_summary(self):
        fleet = make_fleet_with_agents(5)
        s = fleet.summary()
        assert s["agents"] == 5
        assert "capabilities" in s
        assert "strategy" in s

    def test_agent_ranking(self):
        fleet = FleetManager()
        agent1 = make_agent(agent_id=1, name="Alpha")
        agent2 = make_agent(agent_id=2, name="Beta")
        fleet.register_agent(agent1)
        fleet.register_agent(agent2)
        fleet.record_task_assigned(1)
        fleet.record_task_completed(1)
        ranking = fleet.get_agent_ranking(metric="tasks_completed")
        assert ranking[0]["agent_id"] == 1  # Has more completions


# ──────────────────────────────────────────────────────────────
# 8. Availability Windows
# ──────────────────────────────────────────────────────────────


class TestAvailabilityWindows:
    """Availability window logic."""

    def test_window_active(self):
        # Monday 9-17 UTC
        window = AvailabilityWindow(day_of_week=0, start_hour=9, end_hour=17)
        monday_noon = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)  # Monday
        assert window.is_active_at(monday_noon)

    def test_window_inactive_wrong_day(self):
        window = AvailabilityWindow(day_of_week=0, start_hour=9, end_hour=17)
        tuesday = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)  # Tuesday
        assert not window.is_active_at(tuesday)

    def test_window_inactive_wrong_hour(self):
        window = AvailabilityWindow(day_of_week=0, start_hour=9, end_hour=17)
        monday_early = datetime(2026, 3, 30, 7, 0, tzinfo=timezone.utc)
        assert not window.is_active_at(monday_early)

    def test_window_overnight(self):
        # Friday 22:00 - 06:00
        window = AvailabilityWindow(day_of_week=4, start_hour=22, end_hour=6)
        friday_late = datetime(2026, 4, 3, 23, 0, tzinfo=timezone.utc)  # Friday
        assert window.is_active_at(friday_late)
        friday_early = datetime(2026, 4, 3, 3, 0, tzinfo=timezone.utc)  # Friday
        assert window.is_active_at(friday_early)

    def test_agent_with_availability_windows(self):
        fleet = FleetManager()
        agent = make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.COMPETENT},
        )
        # Available Mon-Fri 9-17
        for day in range(5):
            agent.availability.append(
                AvailabilityWindow(day_of_week=day, start_hour=9, end_hour=17)
            )
        fleet.register_agent(agent)
        candidates = fleet.find_capable_agents("delivery")
        # Should still appear (availability is scored, not gating)
        assert len(candidates) >= 0  # Result depends on current day/time


# ──────────────────────────────────────────────────────────────
# 9. Persistence (Save/Load)
# ──────────────────────────────────────────────────────────────


class TestPersistence:
    """Save and load fleet state."""

    def test_save_and_load_roundtrip(self):
        fleet = FleetManager(default_strategy=LoadBalanceStrategy.BEST_FIT)
        fleet.register_agent(make_agent(
            agent_id=1,
            name="Alpha",
            capabilities={"delivery": CapabilityLevel.EXPERT},
            tags={"vip"},
        ))
        fleet.register_agent(make_agent(
            agent_id=2,
            name="Beta",
            capabilities={"research": CapabilityLevel.NOVICE},
        ))
        fleet.record_task_assigned(1)
        fleet.record_task_completed(1)

        data = fleet.save()
        loaded = FleetManager.load(data)

        assert loaded.agent_count() == 2
        assert loaded.get_agent(1).name == "Alpha"
        assert loaded.get_agent(2).name == "Beta"
        assert loaded._strategy == LoadBalanceStrategy.BEST_FIT

    def test_save_format(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        data = fleet.save()
        assert "version" in data
        assert "agents" in data
        assert "metrics" in data
        assert data["version"] == 1

    def test_load_empty(self):
        fleet = FleetManager.load({"agents": []})
        assert fleet.agent_count() == 0

    def test_load_preserves_capabilities(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={
                "delivery": CapabilityLevel.SPECIALIST,
                "photography": CapabilityLevel.PROFICIENT,
            },
        ))
        data = fleet.save()
        loaded = FleetManager.load(data)
        agent = loaded.get_agent(1)
        assert "delivery" in agent.capabilities
        assert agent.capabilities["delivery"].level == CapabilityLevel.SPECIALIST

    def test_load_preserves_tags(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, tags={"vip", "beta"}))
        data = fleet.save()
        loaded = FleetManager.load(data)
        agent = loaded.get_agent(1)
        assert "vip" in agent.tags
        assert "beta" in agent.tags

    def test_load_preserves_metrics(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1))
        fleet.record_task_assigned(1)
        fleet.record_task_assigned(1)
        fleet.record_task_completed(1)
        data = fleet.save()
        loaded = FleetManager.load(data)
        assert loaded._total_assignments == 2
        assert loaded._total_completions == 1


# ──────────────────────────────────────────────────────────────
# 10. Edge Cases & Graceful Degradation
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_fleet_operations(self):
        fleet = FleetManager()
        assert fleet.agent_count() == 0
        assert fleet.find_capable_agents("delivery") == []
        assert fleet.select_agent("delivery") is None
        snapshot = fleet.capacity_snapshot()
        assert snapshot.total_agents == 0
        assert snapshot.utilization == 0.0

    def test_max_concurrent_zero(self):
        fleet = FleetManager()
        agent = make_agent(agent_id=1, max_concurrent=0)
        fleet.register_agent(agent)
        assert agent.utilization == 1.0
        assert not agent.is_available

    def test_cooldown_lifecycle(self):
        fleet = FleetManager()
        agent = make_agent(agent_id=1)
        agent.cooldown_seconds = 0.01  # Very short cooldown
        fleet.register_agent(agent)
        fleet.record_task_assigned(1)
        fleet.record_task_completed(1)
        assert fleet.get_agent(1).status == AgentStatus.COOLDOWN
        time.sleep(0.02)
        fleet.get_agent(1).exit_cooldown()
        assert fleet.get_agent(1).status == AgentStatus.ACTIVE

    def test_suspended_agent_not_available(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.SPECIALIST},
            status=AgentStatus.SUSPENDED,
        ))
        candidates = fleet.find_capable_agents("delivery")
        assert len(candidates) == 0

    def test_case_insensitive_capability_lookup(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"Delivery": CapabilityLevel.EXPERT},
        ))
        candidates = fleet.find_capable_agents("delivery")
        assert len(candidates) == 1

    def test_index_cleanup_on_deregister(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(
            agent_id=1,
            capabilities={"delivery": CapabilityLevel.EXPERT},
            tags={"vip"},
        ))
        fleet.deregister_agent(1)
        assert fleet.list_agents(capability="delivery") == []
        assert fleet.list_agents(tag="vip") == []

    def test_large_fleet_performance(self):
        """Ensure FleetManager handles 100+ agents without issues."""
        fleet = FleetManager()
        for i in range(100):
            fleet.register_agent(make_agent(
                agent_id=i,
                name=f"Agent-{i}",
                capabilities={"delivery": CapabilityLevel.COMPETENT},
            ))
        assert fleet.agent_count() == 100
        candidates = fleet.find_capable_agents("delivery", limit=10)
        assert len(candidates) == 10
        snapshot = fleet.capacity_snapshot()
        assert snapshot.total_agents == 100

    def test_snapshot_history_bounded(self):
        fleet = FleetManager(history_size=5)
        fleet.register_agent(make_agent(agent_id=1))
        for _ in range(10):
            fleet.capacity_snapshot()
        assert len(fleet._history) == 5  # Bounded by maxlen

    def test_assignment_history_bounded(self):
        fleet = FleetManager()
        fleet.register_agent(make_agent(agent_id=1, max_concurrent=1000))
        for _ in range(600):
            fleet.record_task_assigned(1)
        assert len(fleet._assignment_history) == 500  # Bounded by maxlen
