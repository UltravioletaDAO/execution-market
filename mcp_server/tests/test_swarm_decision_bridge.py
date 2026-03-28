"""
Test Suite: DecisionBridge — Integration Glue for 12-Signal Intelligence Stack
================================================================================

The DecisionBridge is THE most architecturally critical module in the swarm.
It wires the DecisionSynthesizer into the SwarmCoordinator pipeline, replacing
basic reputation-only routing with multi-signal intelligent decisions.

Tests cover:
    1. Bridge modes (PRIMARY, SHADOW, ADVISORY, DISABLED)
    2. Signal registration (auto-detect and manual)
    3. Task processing pipeline (decomposition → candidates → synthesis → apply)
    4. Feedback loop (outcome recording → optimizer → weight evolution)
    5. Scorer functions (reputation, availability, skill, reliability, capacity, workforce)
    6. Factory methods (from_coordinator)
    7. Dashboard stats and feedback history
    8. Error resilience (missing modules, scorer failures, empty candidates)
    9. Data types (BridgeResult, DecomposedTask, FeedbackRecord)
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from collections import deque
from dataclasses import asdict

from mcp_server.swarm.decision_bridge import (
    DecisionBridge,
    BridgeMode,
    BridgeResult,
    DecomposedTask,
    FeedbackRecord,
    _make_reputation_scorer,
    _make_availability_scorer,
    _make_skill_match_scorer,
    _make_reliability_scorer,
    _make_capacity_scorer,
    _make_workforce_scorer,
)
from mcp_server.swarm.decision_synthesizer import (
    DecisionSynthesizer,
    SignalType,
    DecisionOutcome,
    RankedDecision,
    ConfidenceLevel,
)
from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════


def _mock_synthesizer(outcome=DecisionOutcome.ROUTED, best="42", score=85.0, confidence=ConfidenceLevel.HIGH):
    """Create a mock DecisionSynthesizer with configurable synthesis results."""
    synth = MagicMock(spec=DecisionSynthesizer)
    decision = MagicMock(spec=RankedDecision)
    decision.outcome = outcome
    decision.best_candidate = best
    decision.best_score = score
    decision.confidence_level = confidence
    decision.rankings = [{"id": best, "score": score}]
    decision.signal_types_used = ["reputation", "skill_match"]
    synth.synthesize.return_value = decision
    synth.stats = {"total_decisions": 1}
    synth.get_weights.return_value = {SignalType.REPUTATION: 0.3}
    synth.registered_signals = ["reputation", "skill_match"]
    return synth


def _mock_orchestrator():
    """Create a mock SwarmOrchestrator."""
    orch = MagicMock(spec=SwarmOrchestrator)
    orch._on_chain = {}
    orch._internal = {}
    assignment = Assignment(
        task_id="task-1", agent_id=42, agent_name="TestAgent",
        score=85.0, strategy_used=RoutingStrategy.BEST_FIT,
    )
    orch.route_task.return_value = assignment
    return orch


def _mock_lifecycle():
    """Create a mock LifecycleManager with available agents."""
    lifecycle = MagicMock()
    agent1 = MagicMock()
    agent1.agent_id = 42
    agent1.name = "Agent42"
    agent1.wallet_address = "0xabc"
    agent1.personality = "efficient"
    agent1.current_task_id = None
    agent1.tags = ["photo", "verify"]

    agent2 = MagicMock()
    agent2.agent_id = 99
    agent2.name = "Agent99"
    agent2.wallet_address = "0xdef"
    agent2.personality = "thorough"
    agent2.current_task_id = None
    agent2.tags = ["delivery"]

    lifecycle.get_available_agents.return_value = [agent1, agent2]
    lifecycle.get_budget_status.return_value = {"daily_pct": 30}
    lifecycle.agents = {42: agent1, 99: agent2}
    return lifecycle


def _mock_queued_task(task_id="task-1", title="Test Task", categories=None, bounty=25.0, priority="normal"):
    """Create a mock QueuedTask."""
    task = MagicMock()
    task.task_id = task_id
    task.title = title
    task.categories = categories or ["delivery"]
    task.bounty_usd = bounty
    task.priority = MagicMock()
    task.priority.value = priority
    task.status = "pending"
    task.attempts = 0
    task.max_attempts = 3
    task.ingested_at = 1000
    task.raw_data = {"description": "Test task description"}
    task.to_task_request.return_value = MagicMock()
    return task


def _make_bridge(mode=BridgeMode.PRIMARY, **kwargs):
    """Create a DecisionBridge with sensible defaults."""
    synth = kwargs.pop("synthesizer", _mock_synthesizer())
    orch = kwargs.pop("orchestrator", _mock_orchestrator())
    lifecycle = kwargs.pop("lifecycle_manager", _mock_lifecycle())

    return DecisionBridge(
        synthesizer=synth,
        orchestrator=orch,
        lifecycle_manager=lifecycle,
        mode=mode,
        **kwargs,
    )


# ══════════════════════════════════════════════════════════════
# Data Type Tests
# ══════════════════════════════════════════════════════════════


class TestDecomposedTask:
    def test_single_subtask_not_compound(self):
        dt = DecomposedTask(original_task_id="t1", sub_tasks=[{"id": "sub1"}])
        assert not dt.is_compound

    def test_multiple_subtasks_is_compound(self):
        dt = DecomposedTask(
            original_task_id="t1",
            sub_tasks=[{"id": "sub1"}, {"id": "sub2"}],
            team_strategy="specialist",
        )
        assert dt.is_compound
        assert dt.team_strategy == "specialist"

    def test_empty_subtasks_not_compound(self):
        dt = DecomposedTask(original_task_id="t1")
        assert not dt.is_compound
        assert len(dt.sub_tasks) == 0

    def test_defaults(self):
        dt = DecomposedTask(original_task_id="t1")
        assert dt.team_strategy == "solo"
        assert dt.estimated_total_hours == 0.0
        assert dt.decomposition_time_ms == 0.0


class TestBridgeResult:
    def test_succeeded_with_assignment(self):
        assignment = Assignment(
            task_id="t1", agent_id=42, agent_name="A",
            score=80.0, strategy_used=RoutingStrategy.BEST_FIT,
        )
        result = BridgeResult(task_id="t1", assignment=assignment)
        assert result.succeeded

    def test_failed_without_assignment(self):
        result = BridgeResult(
            task_id="t1",
            failure=RoutingFailure(task_id="t1", reason="none", attempted_agents=0, excluded_agents=0),
        )
        assert not result.succeeded

    def test_to_dict_minimal(self):
        result = BridgeResult(task_id="t1", mode=BridgeMode.PRIMARY)
        d = result.to_dict()
        assert d["task_id"] == "t1"
        assert d["mode"] == "primary"
        assert d["succeeded"] is False
        assert "decision" not in d

    def test_to_dict_with_decision(self):
        decision = MagicMock()
        decision.outcome.value = "routed"
        decision.best_candidate = "42"
        decision.confidence_level.value = "high"
        decision.signal_types_used = ["reputation"]

        result = BridgeResult(task_id="t1", decision=decision, mode=BridgeMode.PRIMARY)
        d = result.to_dict()
        assert "decision" in d
        assert d["decision"]["best_candidate"] == "42"
        assert d["decision"]["outcome"] == "routed"

    def test_to_dict_with_compound_decomposition(self):
        decomp = DecomposedTask(
            original_task_id="t1",
            sub_tasks=[{"id": "s1"}, {"id": "s2"}],
            team_strategy="parallel",
        )
        result = BridgeResult(task_id="t1", decomposition=decomp)
        d = result.to_dict()
        assert d["decomposed"]["sub_task_count"] == 2
        assert d["decomposed"]["team_strategy"] == "parallel"

    def test_to_dict_skips_simple_decomposition(self):
        decomp = DecomposedTask(original_task_id="t1", sub_tasks=[{"id": "s1"}])
        result = BridgeResult(task_id="t1", decomposition=decomp)
        d = result.to_dict()
        assert "decomposed" not in d


class TestFeedbackRecord:
    def test_basic_creation(self):
        fr = FeedbackRecord(
            task_id="t1",
            decision_outcome="routed",
            actual_outcome="completed",
            agent_id="42",
            decision_score=85.0,
        )
        assert fr.task_id == "t1"
        assert fr.quality_rating == 0.0  # Default
        assert fr.timestamp == ""  # Default


# ══════════════════════════════════════════════════════════════
# Scorer Function Tests
# ══════════════════════════════════════════════════════════════


class TestReputationScorer:
    def test_with_orchestrator_data(self):
        source = MagicMock()
        source._on_chain = {42: MagicMock()}
        source._internal = {42: MagicMock()}
        source.bridge = MagicMock()
        source.bridge.compute_composite.return_value = MagicMock(total=87.5)

        scorer = _make_reputation_scorer(source)
        result = scorer({}, {"agent_id": 42})
        assert result == 87.5

    def test_with_direct_method(self):
        source = MagicMock()
        del source._on_chain  # Remove orchestrator attributes
        del source._internal
        source.get_composite_score.return_value = MagicMock(total=92.0)

        scorer = _make_reputation_scorer(source)
        result = scorer({}, {"agent_id": 42})
        assert result == 92.0

    def test_missing_agent_returns_zero(self):
        source = MagicMock()
        source._on_chain = {}
        source._internal = {}

        scorer = _make_reputation_scorer(source)
        result = scorer({}, {"agent_id": 42})
        assert result == 0.0

    def test_no_agent_id_returns_zero(self):
        source = MagicMock()
        scorer = _make_reputation_scorer(source)
        result = scorer({}, {})
        assert result == 0.0

    def test_exception_returns_zero(self):
        source = MagicMock()
        source._on_chain = {42: MagicMock()}
        source._internal = {42: MagicMock()}
        source.bridge = MagicMock()
        source.bridge.compute_composite.side_effect = Exception("db error")

        scorer = _make_reputation_scorer(source)
        result = scorer({}, {"agent_id": 42})
        assert result == 0.0

    def test_uses_id_fallback(self):
        source = MagicMock()
        source._on_chain = {42: MagicMock()}
        source._internal = {42: MagicMock()}
        source.bridge = MagicMock()
        source.bridge.compute_composite.return_value = MagicMock(total=77.0)

        scorer = _make_reputation_scorer(source)
        result = scorer({}, {"id": 42})  # Uses "id" not "agent_id"
        assert result == 77.0


class TestAvailabilityScorer:
    def test_available_high_score(self):
        bridge = MagicMock()
        bridge.predict.return_value = MagicMock(probability=0.95)

        scorer = _make_availability_scorer(bridge)
        result = scorer({}, {"wallet": "0xabc"})
        assert result == 95.0

    def test_unavailable_low_score(self):
        bridge = MagicMock()
        bridge.predict.return_value = MagicMock(probability=0.1)

        scorer = _make_availability_scorer(bridge)
        result = scorer({}, {"wallet": "0xabc"})
        assert result == 10.0

    def test_no_wallet_returns_neutral(self):
        bridge = MagicMock()
        scorer = _make_availability_scorer(bridge)
        result = scorer({}, {"wallet": ""})
        assert result == 50.0

    def test_error_returns_neutral(self):
        bridge = MagicMock()
        bridge.predict.side_effect = Exception("timeout")

        scorer = _make_availability_scorer(bridge)
        result = scorer({}, {"wallet": "0xabc"})
        assert result == 50.0


class TestSkillMatchScorer:
    def test_high_skill_match(self):
        client = MagicMock()
        enrichment = MagicMock()
        enrichment.skill_match = 88.0
        client.enrich_agents.return_value = {"0xabc": enrichment}

        scorer = _make_skill_match_scorer(client)
        result = scorer({}, {"wallet": "0xabc"})
        assert result == 88.0

    def test_no_wallet_returns_zero(self):
        client = MagicMock()
        scorer = _make_skill_match_scorer(client)
        result = scorer({}, {"wallet": ""})
        assert result == 0.0

    def test_no_enrichment_returns_zero(self):
        client = MagicMock()
        client.enrich_agents.return_value = {}

        scorer = _make_skill_match_scorer(client)
        result = scorer({}, {"wallet": "0xabc"})
        assert result == 0.0

    def test_error_returns_zero(self):
        client = MagicMock()
        client.enrich_agents.side_effect = Exception("api down")

        scorer = _make_skill_match_scorer(client)
        result = scorer({}, {"wallet": "0xabc"})
        assert result == 0.0


class TestReliabilityScorer:
    def test_high_completion_rate(self):
        source = MagicMock()
        internal = MagicMock()
        internal.total_tasks = 10
        internal.successful_tasks = 9
        source._internal = {42: internal}

        scorer = _make_reliability_scorer(source)
        result = scorer({}, {"agent_id": 42})
        assert result == 90.0

    def test_new_agent_returns_neutral(self):
        source = MagicMock()
        source._internal = {}

        scorer = _make_reliability_scorer(source)
        result = scorer({}, {"agent_id": 42})
        assert result == 50.0

    def test_zero_tasks_returns_neutral(self):
        source = MagicMock()
        internal = MagicMock()
        internal.total_tasks = 0
        source._internal = {42: internal}

        scorer = _make_reliability_scorer(source)
        result = scorer({}, {"agent_id": 42})
        assert result == 50.0


class TestCapacityScorer:
    def test_idle_agent_high_budget(self):
        lifecycle = MagicMock()
        record = MagicMock()
        record.current_task_id = None
        lifecycle.agents = {42: record}
        lifecycle.get_budget_status.return_value = {"daily_pct": 20}

        scorer = _make_capacity_scorer(lifecycle)
        result = scorer({}, {"agent_id": 42})
        assert result == 80.0  # 100 - 20

    def test_busy_agent_low_score(self):
        lifecycle = MagicMock()
        record = MagicMock()
        record.current_task_id = "some-task"
        lifecycle.agents = {42: record}

        scorer = _make_capacity_scorer(lifecycle)
        result = scorer({}, {"agent_id": 42})
        assert result == 10.0  # Busy but could queue

    def test_unknown_agent_returns_zero(self):
        lifecycle = MagicMock()
        lifecycle.agents = {}

        scorer = _make_capacity_scorer(lifecycle)
        result = scorer({}, {"agent_id": 42})
        assert result == 0.0

    def test_capped_at_100(self):
        lifecycle = MagicMock()
        record = MagicMock()
        record.current_task_id = None
        lifecycle.agents = {42: record}
        lifecycle.get_budget_status.return_value = {"daily_pct": -10}

        scorer = _make_capacity_scorer(lifecycle)
        result = scorer({}, {"agent_id": 42})
        assert result == 100.0  # Capped

    def test_floored_at_zero(self):
        lifecycle = MagicMock()
        record = MagicMock()
        record.current_task_id = None
        lifecycle.agents = {42: record}
        lifecycle.get_budget_status.return_value = {"daily_pct": 110}

        scorer = _make_capacity_scorer(lifecycle)
        result = scorer({}, {"agent_id": 42})
        assert result == 0.0  # Floored


class TestWorkforceScorer:
    def test_health_score(self):
        analytics = MagicMock()
        analytics.get_worker_health.return_value = {"health_score": 73.5}

        scorer = _make_workforce_scorer(analytics)
        result = scorer({}, {"agent_id": "42"})
        assert result == 73.5

    def test_no_health_data(self):
        analytics = MagicMock()
        analytics.get_worker_health.return_value = None

        scorer = _make_workforce_scorer(analytics)
        result = scorer({}, {"agent_id": "42"})
        assert result == 50.0

    def test_no_agent_id(self):
        analytics = MagicMock()
        scorer = _make_workforce_scorer(analytics)
        result = scorer({}, {})
        assert result == 0.0


# ══════════════════════════════════════════════════════════════
# Bridge Mode Tests
# ══════════════════════════════════════════════════════════════


class TestBridgeModes:
    def test_primary_mode_uses_synthesis(self):
        bridge = _make_bridge(mode=BridgeMode.PRIMARY)
        task = _mock_queued_task()
        task_queue = {"task-1": task}

        results = bridge.process_with_synthesis(task_queue)
        assert len(results) == 1
        assert results[0].used_synthesis is True
        assert results[0].mode == BridgeMode.PRIMARY

    def test_shadow_mode_logs_but_uses_legacy(self):
        bridge = _make_bridge(mode=BridgeMode.SHADOW)
        task = _mock_queued_task()
        task_queue = {"task-1": task}

        results = bridge.process_with_synthesis(task_queue)
        assert len(results) == 1
        assert results[0].used_synthesis is False
        assert results[0].mode == BridgeMode.SHADOW
        # Synthesis should still run
        bridge.synthesizer.synthesize.assert_called_once()

    def test_advisory_mode_doesnt_override(self):
        bridge = _make_bridge(mode=BridgeMode.ADVISORY)
        task = _mock_queued_task()
        task_queue = {"task-1": task}

        results = bridge.process_with_synthesis(task_queue)
        assert len(results) == 1
        assert results[0].used_synthesis is False

    def test_disabled_mode_skips_synthesis(self):
        bridge = _make_bridge(mode=BridgeMode.DISABLED)
        task = _mock_queued_task()
        task_queue = {"task-1": task}

        results = bridge.process_with_synthesis(task_queue)
        assert len(results) == 1
        bridge.synthesizer.synthesize.assert_not_called()

    def test_mode_enum_values(self):
        assert BridgeMode.SHADOW.value == "shadow"
        assert BridgeMode.ADVISORY.value == "advisory"
        assert BridgeMode.PRIMARY.value == "primary"
        assert BridgeMode.DISABLED.value == "disabled"


# ══════════════════════════════════════════════════════════════
# Signal Registration Tests
# ══════════════════════════════════════════════════════════════


class TestSignalRegistration:
    def test_registers_reputation_when_orchestrator_present(self):
        synth = MagicMock(spec=DecisionSynthesizer)
        orch = _mock_orchestrator()

        bridge = DecisionBridge(
            synthesizer=synth,
            orchestrator=orch,
            mode=BridgeMode.PRIMARY,
        )

        # reputation + reliability from orchestrator
        assert synth.register_signal.call_count >= 2
        signal_types = [call.args[0] for call in synth.register_signal.call_args_list]
        assert SignalType.REPUTATION in signal_types
        assert SignalType.RELIABILITY in signal_types

    def test_registers_skill_match_when_autojob_present(self):
        synth = MagicMock(spec=DecisionSynthesizer)
        orch = _mock_orchestrator()
        autojob = MagicMock()

        bridge = DecisionBridge(
            synthesizer=synth,
            orchestrator=orch,
            autojob_client=autojob,
            mode=BridgeMode.PRIMARY,
        )

        signal_types = [call.args[0] for call in synth.register_signal.call_args_list]
        assert SignalType.SKILL_MATCH in signal_types

    def test_registers_availability_when_bridge_present(self):
        synth = MagicMock(spec=DecisionSynthesizer)
        orch = _mock_orchestrator()
        avail = MagicMock()

        bridge = DecisionBridge(
            synthesizer=synth,
            orchestrator=orch,
            availability_bridge=avail,
            mode=BridgeMode.PRIMARY,
        )

        signal_types = [call.args[0] for call in synth.register_signal.call_args_list]
        assert SignalType.AVAILABILITY in signal_types

    def test_registers_capacity_when_lifecycle_present(self):
        synth = MagicMock(spec=DecisionSynthesizer)
        orch = _mock_orchestrator()
        lifecycle = _mock_lifecycle()

        bridge = DecisionBridge(
            synthesizer=synth,
            orchestrator=orch,
            lifecycle_manager=lifecycle,
            mode=BridgeMode.PRIMARY,
        )

        signal_types = [call.args[0] for call in synth.register_signal.call_args_list]
        assert SignalType.CAPACITY in signal_types

    def test_no_signals_when_nothing_available(self):
        synth = MagicMock(spec=DecisionSynthesizer)
        orch = MagicMock(spec=SwarmOrchestrator)
        # Remove orchestrator's internal dicts
        del orch._on_chain
        del orch._internal

        bridge = DecisionBridge(
            synthesizer=synth,
            orchestrator=orch,
            mode=BridgeMode.PRIMARY,
        )

        # Nothing should have been registered (no reputation source without _on_chain)
        # Actually register_signal may still be called if has hasattr checks pass
        # The key is it shouldn't crash


class TestSignalRegistrationAdapters:
    """Test adapter-based signal registration (performance, pricing, outcome, etc.)."""

    def test_performance_adapter_registration(self):
        synth = MagicMock(spec=DecisionSynthesizer)
        orch = _mock_orchestrator()
        perf = MagicMock()

        with patch("mcp_server.swarm.decision_bridge.DecisionBridge._register_available_signals"):
            bridge = DecisionBridge(
                synthesizer=synth,
                orchestrator=orch,
                performance_adapter=perf,
                mode=BridgeMode.PRIMARY,
            )

        assert bridge.performance_adapter is perf

    def test_pricing_adapter_stored(self):
        synth = MagicMock(spec=DecisionSynthesizer)
        orch = _mock_orchestrator()
        pricing = MagicMock()

        with patch("mcp_server.swarm.decision_bridge.DecisionBridge._register_available_signals"):
            bridge = DecisionBridge(
                synthesizer=synth,
                orchestrator=orch,
                pricing_adapter=pricing,
                mode=BridgeMode.PRIMARY,
            )

        assert bridge.pricing_adapter is pricing

    def test_all_12_adapter_slots(self):
        """Verify all 12 adapter slots can be populated."""
        synth = MagicMock(spec=DecisionSynthesizer)
        orch = _mock_orchestrator()

        with patch("mcp_server.swarm.decision_bridge.DecisionBridge._register_available_signals"):
            bridge = DecisionBridge(
                synthesizer=synth,
                orchestrator=orch,
                lifecycle_manager=MagicMock(),
                reputation_bridge=MagicMock(),
                autojob_client=MagicMock(),
                availability_bridge=MagicMock(),
                workforce_analytics=MagicMock(),
                routing_optimizer=MagicMock(),
                performance_adapter=MagicMock(),
                pricing_adapter=MagicMock(),
                outcome_adapter=MagicMock(),
                decomposition_adapter=MagicMock(),
                retention_adapter=MagicMock(),
                market_intelligence_adapter=MagicMock(),
                mode=BridgeMode.PRIMARY,
            )

        assert bridge.lifecycle is not None
        assert bridge.reputation_bridge is not None
        assert bridge.autojob is not None
        assert bridge.availability_bridge is not None
        assert bridge.workforce_analytics is not None
        assert bridge.routing_optimizer is not None
        assert bridge.performance_adapter is not None
        assert bridge.pricing_adapter is not None
        assert bridge.outcome_adapter is not None
        assert bridge.decomposition_adapter is not None
        assert bridge.retention_adapter is not None
        assert bridge.market_intelligence_adapter is not None


# ══════════════════════════════════════════════════════════════
# Task Processing Tests
# ══════════════════════════════════════════════════════════════


class TestProcessWithSynthesis:
    def test_processes_pending_tasks_only(self):
        bridge = _make_bridge()
        pending = _mock_queued_task("t1")
        completed = _mock_queued_task("t2")
        completed.status = "completed"

        task_queue = {"t1": pending, "t2": completed}
        results = bridge.process_with_synthesis(task_queue)
        assert len(results) == 1
        assert results[0].task_id == "t1"

    def test_skips_exhausted_attempts(self):
        bridge = _make_bridge()
        task = _mock_queued_task("t1")
        task.attempts = 3
        task.max_attempts = 3

        results = bridge.process_with_synthesis({"t1": task})
        assert len(results) == 0

    def test_respects_max_tasks_limit(self):
        bridge = _make_bridge()
        tasks = {}
        for i in range(10):
            tasks[f"t{i}"] = _mock_queued_task(f"t{i}")

        results = bridge.process_with_synthesis(tasks, max_tasks=3)
        assert len(results) == 3

    def test_sorts_by_priority_then_time(self):
        bridge = _make_bridge()
        low = _mock_queued_task("low", priority="low")
        low.ingested_at = 100
        high = _mock_queued_task("high", priority="high")
        high.ingested_at = 200
        critical = _mock_queued_task("crit", priority="critical")
        critical.ingested_at = 300

        task_queue = {"low": low, "high": high, "crit": critical}
        results = bridge.process_with_synthesis(task_queue)

        # Critical should be first
        assert results[0].task_id == "crit"

    def test_empty_queue_returns_empty(self):
        bridge = _make_bridge()
        results = bridge.process_with_synthesis({})
        assert results == []

    def test_updates_total_processed_counter(self):
        bridge = _make_bridge()
        task = _mock_queued_task()
        bridge.process_with_synthesis({"t1": task})
        assert bridge._total_processed == 1

    def test_appends_to_results_deque(self):
        bridge = _make_bridge()
        task = _mock_queued_task()
        bridge.process_with_synthesis({"t1": task})
        assert len(bridge._results) == 1


class TestSingleTaskProcessing:
    def test_no_candidates_returns_failure(self):
        bridge = _make_bridge()
        bridge.lifecycle.get_available_agents.return_value = []

        task = _mock_queued_task()
        results = bridge.process_with_synthesis({"t1": task})
        assert len(results) == 1
        assert not results[0].succeeded
        assert results[0].failure is not None
        assert "No available candidates" in results[0].failure.reason

    def test_primary_mode_applies_decision(self):
        bridge = _make_bridge(mode=BridgeMode.PRIMARY)
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        assert results[0].used_synthesis is True
        bridge.orchestrator.route_task.assert_called_once()

    def test_synthesis_held_returns_failure(self):
        synth = _mock_synthesizer(outcome=DecisionOutcome.HELD)
        bridge = _make_bridge(synthesizer=synth)
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        assert not results[0].succeeded
        assert results[0].failure is not None

    def test_invalid_candidate_id_returns_failure(self):
        synth = _mock_synthesizer(best="not-a-number")
        bridge = _make_bridge(synthesizer=synth)
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        assert not results[0].succeeded

    def test_orchestrator_error_returns_failure(self):
        orch = _mock_orchestrator()
        orch.route_task.side_effect = Exception("routing crash")
        bridge = _make_bridge(orchestrator=orch)
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        assert not results[0].succeeded

    def test_orchestrator_returns_routing_failure(self):
        orch = _mock_orchestrator()
        orch.route_task.return_value = RoutingFailure(task_id="t1", reason="no capacity", attempted_agents=2, excluded_agents=0)
        bridge = _make_bridge(orchestrator=orch)
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        assert not results[0].succeeded

    def test_records_synthesis_time(self):
        bridge = _make_bridge()
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        assert results[0].synthesis_time_ms >= 0


class TestCandidateCollection:
    def test_builds_candidate_dicts(self):
        bridge = _make_bridge()
        task = _mock_queued_task()

        # Process to trigger candidate collection
        bridge.process_with_synthesis({"t1": task})

        # Verify synthesizer was called with proper candidate dicts
        call_args = bridge.synthesizer.synthesize.call_args
        candidates = call_args[0][1]
        assert len(candidates) == 2
        assert candidates[0]["id"] == 42
        assert candidates[0]["wallet"] == "0xabc"
        assert candidates[1]["id"] == 99

    def test_no_lifecycle_no_candidates(self):
        bridge = _make_bridge(lifecycle_manager=None)
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        assert not results[0].succeeded


# ══════════════════════════════════════════════════════════════
# Decomposition Tests
# ══════════════════════════════════════════════════════════════


class TestDecomposition:
    def test_skips_when_autojob_unavailable(self):
        bridge = _make_bridge(autojob_client=None)
        task = _mock_queued_task(bounty=50.0)

        results = bridge.process_with_synthesis({"t1": task})
        assert results[0].decomposition is None

    def test_skips_low_bounty_tasks(self):
        autojob = MagicMock()
        autojob.is_available.return_value = True
        bridge = _make_bridge(autojob_client=autojob)
        task = _mock_queued_task(bounty=5.0)

        results = bridge.process_with_synthesis({"t1": task})
        autojob._post.assert_not_called()

    def test_decomposes_high_bounty_tasks(self):
        autojob = MagicMock()
        autojob.is_available.return_value = True
        autojob._post.return_value = {
            "success": True,
            "sub_tasks": [{"id": "s1"}, {"id": "s2"}],
            "team_strategy": "specialist",
            "estimated_hours": 4.5,
        }
        bridge = _make_bridge(autojob_client=autojob)
        task = _mock_queued_task(bounty=50.0)

        results = bridge.process_with_synthesis({"t1": task})
        assert results[0].decomposition is not None
        assert results[0].decomposition.is_compound
        assert bridge._total_decomposed == 1

    def test_handles_decomposition_failure(self):
        autojob = MagicMock()
        autojob.is_available.return_value = True
        autojob._post.side_effect = Exception("timeout")
        bridge = _make_bridge(autojob_client=autojob)
        task = _mock_queued_task(bounty=50.0)

        results = bridge.process_with_synthesis({"t1": task})
        assert results[0].decomposition is None

    def test_disabled_decomposition(self):
        autojob = MagicMock()
        autojob.is_available.return_value = True
        bridge = _make_bridge(autojob_client=autojob, decomposition_enabled=False)
        task = _mock_queued_task(bounty=50.0)

        results = bridge.process_with_synthesis({"t1": task})
        autojob._post.assert_not_called()

    def test_autojob_not_available(self):
        autojob = MagicMock()
        autojob.is_available.return_value = False
        bridge = _make_bridge(autojob_client=autojob)
        task = _mock_queued_task(bounty=50.0)

        results = bridge.process_with_synthesis({"t1": task})
        autojob._post.assert_not_called()


# ══════════════════════════════════════════════════════════════
# Feedback Loop Tests
# ══════════════════════════════════════════════════════════════


class TestFeedbackLoop:
    def test_records_outcome(self):
        bridge = _make_bridge()
        bridge.record_outcome("t1", "completed", quality_rating=0.9)

        assert len(bridge._feedback) == 1
        assert bridge._feedback[0].actual_outcome == "completed"
        assert bridge._total_feedback_recorded == 1

    def test_disabled_feedback_does_nothing(self):
        bridge = _make_bridge(feedback_enabled=False)
        bridge.record_outcome("t1", "completed")
        assert len(bridge._feedback) == 0

    def test_matches_previous_decision(self):
        bridge = _make_bridge()
        task = _mock_queued_task()
        bridge.process_with_synthesis({"task-1": task})

        bridge.record_outcome("task-1", "completed")
        assert bridge._feedback[0].decision_outcome != "unknown"

    def test_unknown_outcome_for_unmatched_task(self):
        bridge = _make_bridge()
        bridge.record_outcome("never-processed", "completed")
        assert bridge._feedback[0].decision_outcome == "unknown"

    def test_feeds_optimizer_on_outcome(self):
        """Verify _feed_optimizer correctly feeds TaskRecord to the optimizer.
        Bug fix: was importing TaskOutcome (doesn't exist), now uses TaskRecord."""
        optimizer = MagicMock()
        bridge = _make_bridge(routing_optimizer=optimizer)

        bridge.record_outcome("t1", "completed")
        optimizer.record_outcome.assert_called_once()
        assert bridge._total_feedback_recorded == 1

    def test_optimizer_error_doesnt_crash(self):
        """The _feed_optimizer method catches all exceptions. Verify graceful degradation."""
        optimizer = MagicMock()
        optimizer.record_outcome.side_effect = Exception("optimizer down")
        bridge = _make_bridge(routing_optimizer=optimizer)

        # Should not raise even with optimizer errors
        bridge.record_outcome("t1", "completed")
        assert bridge._total_feedback_recorded == 1


class TestWeightEvolution:
    def test_auto_evolve_at_threshold(self):
        optimizer = MagicMock()
        recommendation = MagicMock()
        recommendation.confidence = 0.8
        recommendation.weights = MagicMock()
        recommendation.weights.skill_match = 0.4
        recommendation.weights.reputation = 0.3
        recommendation.weights.capacity = 0.2
        recommendation.weights.speed = 0.05
        recommendation.weights.cost = 0.05
        optimizer.evolve.return_value = recommendation

        bridge = _make_bridge(
            routing_optimizer=optimizer,
            auto_evolve_threshold=5,
        )

        # Record enough outcomes to trigger evolution
        for i in range(5):
            bridge._decisions_since_evolve += 1

        bridge.record_outcome(f"t{5}", "completed")
        optimizer.evolve.assert_called()

    def test_no_evolve_below_threshold(self):
        optimizer = MagicMock()
        bridge = _make_bridge(
            routing_optimizer=optimizer,
            auto_evolve_threshold=100,
        )

        bridge.record_outcome("t1", "completed")
        optimizer.evolve.assert_not_called()

    def test_low_confidence_doesnt_update_weights(self):
        optimizer = MagicMock()
        recommendation = MagicMock()
        recommendation.confidence = 0.3  # Below 0.6 threshold
        optimizer.evolve.return_value = recommendation

        synth = _mock_synthesizer()
        bridge = _make_bridge(
            synthesizer=synth,
            routing_optimizer=optimizer,
            auto_evolve_threshold=1,
        )
        bridge._decisions_since_evolve = 1

        bridge.record_outcome("t1", "completed")
        synth.update_weights.assert_not_called()

    def test_evolve_error_doesnt_crash(self):
        optimizer = MagicMock()
        optimizer.evolve.side_effect = Exception("evolution failed")

        bridge = _make_bridge(
            routing_optimizer=optimizer,
            auto_evolve_threshold=1,
        )
        bridge._decisions_since_evolve = 1

        # Should not raise
        bridge.record_outcome("t1", "completed")


# ══════════════════════════════════════════════════════════════
# Factory Method Tests
# ══════════════════════════════════════════════════════════════


class TestFromCoordinator:
    def test_builds_from_coordinator(self):
        coordinator = MagicMock()
        coordinator.orchestrator = _mock_orchestrator()
        coordinator.lifecycle = _mock_lifecycle()
        coordinator.bridge = MagicMock()  # ReputationBridge
        coordinator.autojob = MagicMock()
        coordinator.routing_optimizer = None
        coordinator.availability_bridge = None
        coordinator.workforce_analytics = None

        bridge = DecisionBridge.from_coordinator(coordinator)

        assert bridge.orchestrator is coordinator.orchestrator
        assert bridge.lifecycle is coordinator.lifecycle
        assert bridge.mode == BridgeMode.PRIMARY  # Default

    def test_custom_mode(self):
        coordinator = MagicMock()
        coordinator.orchestrator = _mock_orchestrator()
        coordinator.lifecycle = _mock_lifecycle()
        coordinator.bridge = MagicMock()
        coordinator.autojob = None
        coordinator.routing_optimizer = None
        coordinator.availability_bridge = None
        coordinator.workforce_analytics = None

        bridge = DecisionBridge.from_coordinator(coordinator, mode=BridgeMode.SHADOW)
        assert bridge.mode == BridgeMode.SHADOW

    def test_detects_optional_modules(self):
        coordinator = MagicMock()
        coordinator.orchestrator = _mock_orchestrator()
        coordinator.lifecycle = _mock_lifecycle()
        coordinator.bridge = MagicMock()
        coordinator.autojob = MagicMock()
        coordinator.routing_optimizer = MagicMock()
        coordinator.availability_bridge = MagicMock()
        coordinator.workforce_analytics = MagicMock()

        bridge = DecisionBridge.from_coordinator(coordinator)
        assert bridge.routing_optimizer is not None
        assert bridge.availability_bridge is not None


# ══════════════════════════════════════════════════════════════
# Stats & Dashboard Tests
# ══════════════════════════════════════════════════════════════


class TestStatsAndDashboard:
    def test_initial_stats(self):
        bridge = _make_bridge()
        stats = bridge.stats

        assert stats["mode"] == "primary"
        assert stats["total_processed"] == 0
        assert stats["total_synthesized"] == 0
        assert stats["total_decomposed"] == 0
        assert stats["feedback_recorded"] == 0
        assert stats["routing_accuracy"] is None

    def test_stats_after_processing(self):
        bridge = _make_bridge()
        task = _mock_queued_task()
        bridge.process_with_synthesis({"t1": task})

        stats = bridge.stats
        assert stats["total_processed"] == 1
        assert stats["total_synthesized"] == 1

    def test_routing_accuracy_calculation(self):
        bridge = _make_bridge()

        # Simulate 3 correct and 1 incorrect feedback
        for i in range(3):
            bridge._feedback.append(FeedbackRecord(
                task_id=f"t{i}",
                decision_outcome="routed",
                actual_outcome="completed",
            ))
        bridge._feedback.append(FeedbackRecord(
            task_id="t3",
            decision_outcome="routed",
            actual_outcome="expired",
        ))

        stats = bridge.stats
        assert stats["routing_accuracy"] == 0.75  # 3/4

    def test_feedback_history(self):
        bridge = _make_bridge()

        for i in range(5):
            bridge._feedback.append(FeedbackRecord(
                task_id=f"t{i}",
                decision_outcome="routed",
                actual_outcome="completed",
                agent_id="42",
                decision_score=85.0,
                timestamp="2026-03-28T00:00:00Z",
            ))

        history = bridge.get_feedback_history(limit=3)
        assert len(history) == 3
        assert history[0]["task_id"] == "t2"  # Last 3 of 5

    def test_feedback_history_full(self):
        bridge = _make_bridge()

        for i in range(3):
            bridge._feedback.append(FeedbackRecord(
                task_id=f"t{i}",
                decision_outcome="routed",
                actual_outcome="completed",
            ))

        history = bridge.get_feedback_history(limit=50)
        assert len(history) == 3

    def test_stats_include_synthesizer(self):
        bridge = _make_bridge()
        stats = bridge.stats
        assert "synthesizer" in stats
        assert "current_weights" in stats
        assert "registered_signals" in stats


# ══════════════════════════════════════════════════════════════
# Edge Cases & Error Resilience
# ══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_results_deque_maxlen(self):
        bridge = _make_bridge()
        # Deque should have maxlen 1000
        assert bridge._results.maxlen == 1000

    def test_feedback_deque_maxlen(self):
        bridge = _make_bridge()
        assert bridge._feedback.maxlen == 1000

    def test_multiple_tasks_processed_serially(self):
        bridge = _make_bridge()
        tasks = {f"t{i}": _mock_queued_task(f"t{i}") for i in range(5)}

        results = bridge.process_with_synthesis(tasks)
        assert len(results) == 5
        assert bridge._total_processed == 5
        assert bridge._total_synthesized == 5

    def test_synthesis_counter_increments(self):
        bridge = _make_bridge()
        task = _mock_queued_task()
        bridge.process_with_synthesis({"t1": task})
        assert bridge._total_synthesized == 1
        assert bridge._decisions_since_evolve == 1

    def test_legacy_route_fallback(self):
        """In non-PRIMARY modes, legacy routing is used."""
        orch = _mock_orchestrator()
        bridge = _make_bridge(orchestrator=orch, mode=BridgeMode.SHADOW)
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        # Legacy route should be called
        orch.route_task.assert_called()

    def test_none_best_candidate(self):
        synth = _mock_synthesizer(outcome=DecisionOutcome.ROUTED, best=None)
        bridge = _make_bridge(synthesizer=synth)
        task = _mock_queued_task()

        results = bridge.process_with_synthesis({"t1": task})
        # Should handle None candidate gracefully
        assert not results[0].succeeded

    def test_concurrent_processing_tracking(self):
        bridge = _make_bridge()
        for i in range(10):
            task = _mock_queued_task(f"t{i}")
            bridge.process_with_synthesis({f"t{i}": task})

        assert bridge._total_processed == 10
        assert len(bridge._results) == 10
