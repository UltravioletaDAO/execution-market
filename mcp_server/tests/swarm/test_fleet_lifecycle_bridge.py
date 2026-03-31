"""
Tests for FleetLifecycleBridge — Module #54
============================================

Validates bidirectional sync between FleetManager and LifecycleManager.

10 test classes covering:
1. Initialization and component wiring
2. Lifecycle → Fleet state sync
3. Fleet → Lifecycle state sync
4. Task assignment sync
5. Task completion sync
6. Heartbeat sync
7. Cooldown sync
8. Agent registration sync
9. Unified view and conflict detection
10. Reconciliation
"""

from unittest.mock import MagicMock, patch, PropertyMock

from mcp_server.swarm.fleet_lifecycle_bridge import (
    FleetLifecycleBridge,
    SyncDirection,
    SyncEventType,
    SyncEvent,
    UnifiedAgentView,
    ReconciliationReport,
    LIFECYCLE_TO_FLEET_STATUS,
    FLEET_TO_LIFECYCLE_STATE,
)


# ─── Fixtures ─────────────────────────────────────────────────


def make_lifecycle_mock(agents=None):
    """Create a mock LifecycleManager with configurable agents."""
    lm = MagicMock()
    lm._agents = agents or {}
    agents_prop = PropertyMock(return_value=lm._agents)
    type(lm).agents = agents_prop

    def _get_agent(agent_id):
        if agent_id not in lm._agents:
            raise Exception(f"Agent {agent_id} not found")
        return lm._agents[agent_id]

    lm._get_agent = _get_agent
    lm.get_swarm_status.return_value = {
        "total_agents": len(lm._agents),
        "state_counts": {},
        "available_count": 0,
    }
    return lm


def make_fleet_mock(agents=None):
    """Create a mock FleetManager."""
    fm = MagicMock()
    fm._agents = agents or {}

    def get_agent(agent_id):
        return fm._agents.get(agent_id)

    fm.get_agent = get_agent

    def list_agents(**kwargs):
        result = []
        for a in fm._agents.values():
            result.append(a)
        return result

    fm.list_agents = list_agents
    fm.health.return_value = {"healthy": True, "agent_count": len(fm._agents)}
    return fm


def make_agent_record(agent_id=2106, state="idle", task_id=None, budget_daily=0.0):
    """Create a mock LifecycleManager AgentRecord."""
    record = MagicMock()
    # State as an enum-like mock
    state_mock = MagicMock()
    state_mock.value = state
    record.state = state_mock
    record.agent_id = agent_id
    record.current_task_id = task_id
    record.cooldown_until = None

    # Budget
    record.budget_state = MagicMock()
    record.budget_state.daily_spent_usd = budget_daily
    record.budget_state.monthly_spent_usd = budget_daily * 20
    record.budget_config = MagicMock()
    record.budget_config.daily_limit_usd = 5.0

    # Health
    record.health = MagicMock()
    record.health.is_healthy = True
    record.health.consecutive_missed = 0
    record.health.error_count = 0

    return record


def make_fleet_agent(agent_id=2106, status="active", load=0, max_concurrent=3):
    """Create a mock FleetManager AgentProfile."""
    agent = MagicMock()
    agent.agent_id = agent_id
    status_mock = MagicMock()
    status_mock.value = status
    agent.status = status_mock
    agent.current_load = load
    agent.max_concurrent_tasks = max_concurrent
    agent.utilization = load / max_concurrent if max_concurrent > 0 else 0
    agent.total_completed = 10
    agent.total_failed = 1
    agent.tags = ["tier1"]
    agent.capabilities = []
    return agent


# ─── 1. Initialization ───────────────────────────────────────


class TestInitialization:
    """Test bridge creation and component wiring."""

    def test_create_empty(self):
        bridge = FleetLifecycleBridge()
        assert bridge._lifecycle is None
        assert bridge._fleet is None

    def test_create_with_components(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        assert bridge._lifecycle is lm
        assert bridge._fleet is fm

    def test_fluent_setters(self):
        bridge = FleetLifecycleBridge()
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        result = bridge.set_lifecycle_manager(lm).set_fleet_manager(fm)
        assert result is bridge
        assert bridge._lifecycle is lm
        assert bridge._fleet is fm

    def test_initial_counters(self):
        bridge = FleetLifecycleBridge()
        assert bridge._sync_count == 0
        assert bridge._error_count == 0
        assert bridge._conflict_count == 0

    def test_custom_history_size(self):
        bridge = FleetLifecycleBridge(max_history=50)
        assert bridge._history.maxlen == 50

    def test_auto_resolve_default(self):
        bridge = FleetLifecycleBridge()
        assert bridge._auto_resolve is True

    def test_auto_resolve_disabled(self):
        bridge = FleetLifecycleBridge(auto_resolve_conflicts=False)
        assert bridge._auto_resolve is False


# ─── 2. Lifecycle → Fleet State Sync ─────────────────────────


class TestLifecycleToFleetSync:
    """Test state propagation from LifecycleManager to FleetManager."""

    def test_idle_maps_to_active(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        event = bridge.sync_state_change(2106, "idle")
        assert event.success
        assert event.details["fleet_status"] == "active"
        fm.set_status.assert_called_once()

    def test_working_maps_to_busy(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        event = bridge.sync_state_change(2106, "working")
        assert event.success
        assert event.details["fleet_status"] == "busy"

    def test_suspended_maps_to_suspended(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        event = bridge.sync_state_change(2106, "suspended")
        assert event.success
        assert event.details["fleet_status"] == "suspended"

    def test_cooldown_maps_to_cooldown(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        event = bridge.sync_state_change(2106, "cooldown")
        assert event.success
        assert event.details["fleet_status"] == "cooldown"

    def test_degraded_maps_to_idle(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        event = bridge.sync_state_change(2106, "degraded")
        assert event.success
        assert event.details["fleet_status"] == "idle"

    def test_enum_state_extracted(self):
        """State can be passed as an enum with .value."""
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        state_enum = MagicMock()
        state_enum.value = "working"
        event = bridge.sync_state_change(2106, state_enum)
        assert event.success
        assert event.details["fleet_status"] == "busy"

    def test_unknown_state_fails(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        event = bridge.sync_state_change(2106, "nonexistent")
        assert not event.success
        assert "No fleet status mapping" in event.error

    def test_no_fleet_manager_fails(self):
        bridge = FleetLifecycleBridge()
        event = bridge.sync_state_change(2106, "idle")
        assert not event.success
        assert "FleetManager not connected" in event.error

    def test_fleet_exception_captured(self):
        fm = make_fleet_mock()
        fm.set_status.side_effect = Exception("fleet down")
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        event = bridge.sync_state_change(2106, "idle")
        assert not event.success
        assert "fleet down" in event.error

    def test_all_mappings_covered(self):
        """Every lifecycle state has a fleet mapping."""
        expected_states = {
            "initializing",
            "idle",
            "active",
            "working",
            "cooldown",
            "degraded",
            "suspended",
        }
        assert set(LIFECYCLE_TO_FLEET_STATUS.keys()) == expected_states


# ─── 3. Fleet → Lifecycle State Sync ─────────────────────────


class TestFleetToLifecycleSync:
    """Test state propagation from FleetManager to LifecycleManager."""

    def test_heartbeat_timeout_triggers_degraded(self):
        record = make_agent_record(state="active")
        lm = make_lifecycle_mock({2106: record})

        # Patch VALID_TRANSITIONS in lifecycle_manager module (where it's imported from)
        from mcp_server.swarm.lifecycle_manager import AgentState as LCState

        with patch(
            "mcp_server.swarm.lifecycle_manager.VALID_TRANSITIONS",
            {
                record.state: {LCState.DEGRADED},
            },
        ):
            bridge = FleetLifecycleBridge(lifecycle_manager=lm)
            event = bridge.sync_heartbeat_timeout(2106)
            # It will attempt the transition
            assert event.event_type == SyncEventType.HEARTBEAT_TIMEOUT
            lm.transition.assert_called_once()

    def test_heartbeat_timeout_no_lifecycle(self):
        bridge = FleetLifecycleBridge()
        event = bridge.sync_heartbeat_timeout(2106)
        assert not event.success
        assert "LifecycleManager not connected" in event.error

    def test_budget_exceeded_propagates(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        event = bridge.sync_budget_exceeded(2106)
        assert event.event_type == SyncEventType.BUDGET_EXCEEDED
        assert event.direction == SyncDirection.LIFECYCLE_TO_FLEET

    def test_budget_exceeded_no_fleet(self):
        bridge = FleetLifecycleBridge()
        event = bridge.sync_budget_exceeded(2106)
        assert not event.success
        assert "FleetManager not connected" in event.error

    def test_reverse_mapping_complete(self):
        """Every fleet status has a lifecycle mapping."""
        expected_statuses = {
            "active",
            "busy",
            "idle",
            "offline",
            "suspended",
            "cooldown",
        }
        assert set(FLEET_TO_LIFECYCLE_STATE.keys()) == expected_statuses


# ─── 4. Task Assignment Sync ─────────────────────────────────


class TestTaskAssignment:
    """Test bidirectional task assignment propagation."""

    def test_assign_both_systems(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_task_assigned(2106, "task-001")
        assert event.success
        assert event.direction == SyncDirection.BIDIRECTIONAL
        lm.assign_task.assert_called_once_with(2106, "task-001")
        fm.record_task_assigned.assert_called_once_with(2106)

    def test_assign_lifecycle_error_partial(self):
        lm = make_lifecycle_mock()
        lm.assign_task.side_effect = Exception("budget exceeded")
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_task_assigned(2106, "task-002")
        assert not event.success
        assert "lifecycle: budget exceeded" in event.error
        # Fleet should still be called
        fm.record_task_assigned.assert_called_once()

    def test_assign_fleet_error_partial(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        fm.record_task_assigned.side_effect = Exception("agent not found")
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_task_assigned(2106, "task-003")
        assert not event.success
        assert "fleet: agent not found" in event.error
        # Lifecycle should still be called
        lm.assign_task.assert_called_once()

    def test_assign_both_errors(self):
        lm = make_lifecycle_mock()
        lm.assign_task.side_effect = Exception("lm error")
        fm = make_fleet_mock()
        fm.record_task_assigned.side_effect = Exception("fm error")
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_task_assigned(2106, "task-004")
        assert not event.success
        assert "lm error" in event.error
        assert "fm error" in event.error

    def test_assign_no_systems(self):
        bridge = FleetLifecycleBridge()
        event = bridge.sync_task_assigned(2106, "task-005")
        assert event.success  # No error if nothing to call

    def test_assign_records_event(self):
        bridge = FleetLifecycleBridge()
        bridge.sync_task_assigned(2106, "task-006")
        assert len(bridge._history) == 1
        assert bridge._sync_count == 1


# ─── 5. Task Completion Sync ─────────────────────────────────


class TestTaskCompletion:
    """Test bidirectional task completion propagation."""

    def test_complete_both_systems(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_task_completed(
            2106, "task-001", success=True, cost_usd=0.50
        )
        assert event.success
        lm.complete_task.assert_called_once_with(2106, "task-001", cost_usd=0.50)
        fm.record_task_completed.assert_called_once_with(2106, success=True)

    def test_complete_failure(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_task_completed(2106, "task-002", success=False)
        assert event.success
        assert event.details["success"] is False
        fm.record_task_completed.assert_called_once_with(2106, success=False)

    def test_complete_with_cost(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_task_completed(2106, "task-003", cost_usd=1.25)
        assert event.details["cost_usd"] == 1.25

    def test_complete_lifecycle_error(self):
        lm = make_lifecycle_mock()
        lm.complete_task.side_effect = Exception("invalid transition")
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_task_completed(2106, "task-004")
        assert not event.success
        # Fleet should still be called
        fm.record_task_completed.assert_called_once()

    def test_complete_error_increments_counter(self):
        lm = make_lifecycle_mock()
        lm.complete_task.side_effect = Exception("fail")
        bridge = FleetLifecycleBridge(lifecycle_manager=lm)
        bridge.sync_task_completed(2106, "task-005")
        assert bridge._error_count == 1


# ─── 6. Heartbeat Sync ───────────────────────────────────────


class TestHeartbeatSync:
    """Test heartbeat propagation to both systems."""

    def test_heartbeat_both_systems(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_heartbeat(2106)
        assert event.success
        lm.record_heartbeat.assert_called_once_with(2106)
        fm.heartbeat.assert_called_once_with(2106)

    def test_heartbeat_lifecycle_error(self):
        lm = make_lifecycle_mock()
        lm.record_heartbeat.side_effect = Exception("not found")
        bridge = FleetLifecycleBridge(lifecycle_manager=lm)

        event = bridge.sync_heartbeat(2106)
        assert not event.success

    def test_heartbeat_fleet_error(self):
        fm = make_fleet_mock()
        fm.heartbeat.side_effect = Exception("not found")
        bridge = FleetLifecycleBridge(fleet_manager=fm)

        event = bridge.sync_heartbeat(2106)
        assert not event.success

    def test_heartbeat_recovery_type(self):
        bridge = FleetLifecycleBridge()
        event = bridge.sync_heartbeat(2106)
        assert event.event_type == SyncEventType.HEARTBEAT_RECOVERY


# ─── 7. Cooldown Sync ────────────────────────────────────────


class TestCooldownSync:
    """Test cooldown start/stop synchronization."""

    def test_cooldown_started(self):
        agent = make_fleet_agent()
        fm = make_fleet_mock({2106: agent})
        bridge = FleetLifecycleBridge(fleet_manager=fm)

        event = bridge.sync_cooldown_started(2106, duration_seconds=120.0)
        assert event.success
        agent.enter_cooldown.assert_called_once_with(120.0)

    def test_cooldown_started_no_agent(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)

        event = bridge.sync_cooldown_started(2106)
        assert not event.success
        assert "not in fleet" in event.error

    def test_cooldown_started_no_fleet(self):
        bridge = FleetLifecycleBridge()
        event = bridge.sync_cooldown_started(2106)
        assert not event.success

    def test_cooldown_expired(self):
        agent = make_fleet_agent()
        fm = make_fleet_mock({2106: agent})
        lm = make_lifecycle_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_cooldown_expired(2106)
        assert event.event_type == SyncEventType.COOLDOWN_EXPIRED
        agent.exit_cooldown.assert_called_once()
        lm.check_cooldown_expiry.assert_called_once_with(2106)

    def test_cooldown_expired_fleet_error(self):
        fm = make_fleet_mock()  # No agent registered
        lm = make_lifecycle_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_cooldown_expired(2106)
        # Should still try lifecycle
        lm.check_cooldown_expiry.assert_called_once()

    def test_cooldown_default_duration(self):
        agent = make_fleet_agent()
        fm = make_fleet_mock({2106: agent})
        bridge = FleetLifecycleBridge(fleet_manager=fm)

        event = bridge.sync_cooldown_started(2106)
        assert event.details["duration_seconds"] == 300.0


# ─── 8. Agent Registration Sync ──────────────────────────────


class TestAgentRegistration:
    """Test synchronized agent registration across both systems."""

    def test_register_both_systems(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_agent_registered(
            agent_id=2107,
            name="TestAgent",
            wallet_address="0xabc",
            capabilities=["delivery", "research"],
            tags=["tier1"],
        )
        assert event.success
        assert event.event_type == SyncEventType.AGENT_REGISTERED
        lm.register_agent.assert_called_once_with(
            agent_id=2107, name="TestAgent", wallet_address="0xabc"
        )
        fm.register_agent.assert_called_once()

    def test_register_lifecycle_error(self):
        lm = make_lifecycle_mock()
        lm.register_agent.side_effect = Exception("duplicate")
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_agent_registered(2107, "TestAgent")
        assert not event.success
        assert "lifecycle: duplicate" in event.error
        # Fleet should still be called
        fm.register_agent.assert_called_once()

    def test_register_fleet_error(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        fm.register_agent.side_effect = Exception("duplicate")
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_agent_registered(2107, "TestAgent")
        assert not event.success
        assert "fleet: duplicate" in event.error
        lm.register_agent.assert_called_once()

    def test_register_no_capabilities(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        event = bridge.sync_agent_registered(2107, "TestAgent")
        assert event.success
        assert event.details["capabilities"] == []

    def test_register_no_systems(self):
        bridge = FleetLifecycleBridge()
        event = bridge.sync_agent_registered(2107, "TestAgent")
        assert event.success  # No error if nothing to call


# ─── 9. Unified View and Conflict Detection ──────────────────


class TestUnifiedView:
    """Test combined agent view and conflict detection."""

    def test_full_view(self):
        record = make_agent_record(state="idle")
        lm = make_lifecycle_mock({2106: record})
        lm.get_budget_status.return_value = {"at_warning": False, "at_limit": False}

        agent = make_fleet_agent(status="active")
        fm = make_fleet_mock({2106: agent})

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        view = bridge.get_unified_view(2106)

        assert view.agent_id == 2106
        assert view.lifecycle_state == "idle"
        assert view.fleet_status == "active"
        assert view.in_sync  # idle → active is correct mapping

    def test_conflict_detection(self):
        record = make_agent_record(state="working")
        lm = make_lifecycle_mock({2106: record})
        lm.get_budget_status.return_value = {"at_warning": False, "at_limit": False}

        agent = make_fleet_agent(status="active")  # Should be "busy"
        fm = make_fleet_mock({2106: agent})

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        view = bridge.get_unified_view(2106)

        assert not view.in_sync
        assert any("state_mismatch" in c for c in view.conflicts)

    def test_lifecycle_only(self):
        record = make_agent_record(state="idle")
        lm = make_lifecycle_mock({2106: record})
        lm.get_budget_status.return_value = {"at_warning": False, "at_limit": False}
        fm = make_fleet_mock()  # No agent

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        view = bridge.get_unified_view(2106)

        assert view.lifecycle_state == "idle"
        assert view.fleet_status is None
        assert any("fleet: agent not registered" in c for c in view.conflicts)

    def test_fleet_only(self):
        lm = make_lifecycle_mock()  # No agent — will raise on _get_agent
        agent = make_fleet_agent(status="active")
        fm = make_fleet_mock({2106: agent})

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        view = bridge.get_unified_view(2106)

        assert view.lifecycle_state is None
        assert view.fleet_status == "active"

    def test_view_to_dict(self):
        view = UnifiedAgentView(
            agent_id=2106,
            lifecycle_state="idle",
            fleet_status="active",
        )
        d = view.to_dict()
        assert d["agent_id"] == 2106
        assert d["lifecycle"]["state"] == "idle"
        assert d["fleet"]["status"] == "active"
        assert d["sync"]["in_sync"] is True

    def test_view_budget_info(self):
        record = make_agent_record(state="active", budget_daily=3.5)
        lm = make_lifecycle_mock({2106: record})
        lm.get_budget_status.return_value = {"at_warning": True, "at_limit": False}

        bridge = FleetLifecycleBridge(lifecycle_manager=lm)
        view = bridge.get_unified_view(2106)

        assert view.budget_daily_spent == 3.5
        assert view.budget_at_warning is True
        assert view.budget_at_limit is False

    def test_fleet_overview(self):
        lm = make_lifecycle_mock()
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)

        overview = bridge.get_fleet_overview()
        assert overview["lifecycle"] is not None
        assert overview["fleet"] is not None
        assert "sync_status" in overview

    def test_fleet_overview_no_systems(self):
        bridge = FleetLifecycleBridge()
        overview = bridge.get_fleet_overview()
        assert overview["lifecycle"] is None
        assert overview["fleet"] is None


# ─── 10. Reconciliation ──────────────────────────────────────


class TestReconciliation:
    """Test full fleet reconciliation between both systems."""

    def test_all_in_sync(self):
        record = make_agent_record(state="idle")
        lm = make_lifecycle_mock({2106: record})
        lm.get_budget_status.return_value = {"at_warning": False, "at_limit": False}

        agent = make_fleet_agent(status="active")
        fm = make_fleet_mock({2106: agent})

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        report = bridge.reconcile()

        assert report.agents_checked >= 1
        assert report.agents_in_sync == 1
        assert report.agents_out_of_sync == 0
        assert report.all_in_sync

    def test_conflict_detected(self):
        record = make_agent_record(state="working")
        lm = make_lifecycle_mock({2106: record})
        lm.get_budget_status.return_value = {"at_warning": False, "at_limit": False}

        agent = make_fleet_agent(status="active")  # Should be "busy"
        fm = make_fleet_mock({2106: agent})

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        report = bridge.reconcile(fix=True)

        assert not report.all_in_sync or report.conflicts_resolved > 0
        assert report.agents_checked >= 1

    def test_lifecycle_only_agents(self):
        record = make_agent_record(agent_id=2107, state="idle")
        lm = make_lifecycle_mock({2107: record})
        fm = make_fleet_mock()

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        report = bridge.reconcile()

        assert 2107 in report.lifecycle_only

    def test_fleet_only_agents(self):
        lm = make_lifecycle_mock()
        agent = make_fleet_agent(agent_id=2108)
        fm = make_fleet_mock({2108: agent})

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        report = bridge.reconcile()

        assert 2108 in report.fleet_only

    def test_reconcile_no_fix(self):
        record = make_agent_record(state="working")
        lm = make_lifecycle_mock({2106: record})
        lm.get_budget_status.return_value = {"at_warning": False, "at_limit": False}

        agent = make_fleet_agent(status="active")
        fm = make_fleet_mock({2106: agent})

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        report = bridge.reconcile(fix=False)

        assert report.conflicts_resolved == 0

    def test_reconcile_updates_timestamp(self):
        bridge = FleetLifecycleBridge(
            lifecycle_manager=make_lifecycle_mock(),
            fleet_manager=make_fleet_mock(),
        )
        assert bridge._last_reconciliation is None
        bridge.reconcile()
        assert bridge._last_reconciliation is not None

    def test_reconciliation_report_to_dict(self):
        report = ReconciliationReport(
            agents_checked=5,
            agents_in_sync=3,
            agents_out_of_sync=2,
            conflicts_found=2,
            conflicts_resolved=1,
        )
        d = report.to_dict()
        assert d["agents_checked"] == 5
        assert d["all_in_sync"] is False

    def test_empty_reconciliation(self):
        bridge = FleetLifecycleBridge(
            lifecycle_manager=make_lifecycle_mock(),
            fleet_manager=make_fleet_mock(),
        )
        report = bridge.reconcile()
        assert report.agents_checked == 0
        assert report.all_in_sync

    def test_multiple_agents_reconciliation(self):
        agents_lc = {}
        agents_fm = {}
        for i in range(5):
            aid = 2100 + i
            agents_lc[aid] = make_agent_record(agent_id=aid, state="idle")
            agents_fm[aid] = make_fleet_agent(agent_id=aid, status="active")

        lm = make_lifecycle_mock(agents_lc)
        lm.get_budget_status.return_value = {"at_warning": False, "at_limit": False}
        fm = make_fleet_mock(agents_fm)

        bridge = FleetLifecycleBridge(lifecycle_manager=lm, fleet_manager=fm)
        report = bridge.reconcile()

        assert report.agents_checked == 5
        assert report.agents_in_sync == 5


# ─── 11. Health & Diagnostics ────────────────────────────────


class TestHealthDiagnostics:
    """Test health reporting and event tracking."""

    def test_health_initial(self):
        bridge = FleetLifecycleBridge()
        h = bridge.health()
        assert h["sync_count"] == 0
        assert h["error_count"] == 0
        assert h["lifecycle_connected"] is False
        assert h["fleet_connected"] is False

    def test_health_connected(self):
        bridge = FleetLifecycleBridge(
            lifecycle_manager=make_lifecycle_mock(),
            fleet_manager=make_fleet_mock(),
        )
        h = bridge.health()
        assert h["lifecycle_connected"] is True
        assert h["fleet_connected"] is True

    def test_health_after_syncs(self):
        bridge = FleetLifecycleBridge()
        bridge.sync_task_assigned(2106, "t1")
        bridge.sync_task_assigned(2107, "t2")
        h = bridge.health()
        assert h["sync_count"] == 2

    def test_health_after_errors(self):
        lm = make_lifecycle_mock()
        lm.assign_task.side_effect = Exception("fail")
        bridge = FleetLifecycleBridge(lifecycle_manager=lm)
        bridge.sync_task_assigned(2106, "t1")
        h = bridge.health()
        assert h["error_count"] == 1
        # Health degrades when error rate > 10%
        assert not h["healthy"]

    def test_healthy_with_low_error_rate(self):
        fm = make_fleet_mock()
        bridge = FleetLifecycleBridge(fleet_manager=fm)
        # 20 successes, 1 error
        for i in range(20):
            bridge.sync_state_change(2106, "idle")
        fm.set_status.side_effect = Exception("fail")
        bridge.sync_state_change(2106, "idle")
        h = bridge.health()
        assert h["healthy"]  # 1/21 < 10%

    def test_recent_events(self):
        bridge = FleetLifecycleBridge()
        bridge.sync_task_assigned(2106, "t1")
        bridge.sync_task_assigned(2107, "t2")
        events = bridge.get_recent_events(limit=1)
        assert len(events) == 1
        assert events[0]["agent_id"] == 2107

    def test_sync_stats(self):
        bridge = FleetLifecycleBridge()
        bridge.sync_task_assigned(2106, "t1")
        bridge.sync_task_completed(2106, "t1")
        bridge.sync_heartbeat(2106)

        stats = bridge.get_sync_stats()
        assert "task_assigned" in stats
        assert "task_completed" in stats
        assert "heartbeat_recovery" in stats

    def test_summary(self):
        bridge = FleetLifecycleBridge()
        s = bridge.summary()
        assert s["bridge"] == "fleet_lifecycle"
        assert "healthy" in s
        assert "syncs" in s

    def test_event_to_dict(self):
        event = SyncEvent(
            event_type=SyncEventType.TASK_ASSIGNED,
            direction=SyncDirection.BIDIRECTIONAL,
            agent_id=2106,
            details={"task_id": "t1"},
        )
        d = event.to_dict()
        assert d["event_type"] == "task_assigned"
        assert d["direction"] == "bidirectional"
        assert d["agent_id"] == 2106

    def test_history_bounded(self):
        bridge = FleetLifecycleBridge(max_history=5)
        for i in range(10):
            bridge.sync_heartbeat(2106)
        assert len(bridge._history) == 5
        assert bridge._sync_count == 10
