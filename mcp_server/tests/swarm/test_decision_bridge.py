"""
Tests for DecisionBridge — wiring DecisionSynthesizer into SwarmCoordinator.
"""

import time
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from mcp_server.swarm.decision_bridge import (
    DecisionBridge,
    BridgeMode,
    BridgeResult,
    _make_reputation_scorer,
    _make_reliability_scorer,
    _make_capacity_scorer,
    _make_skill_match_scorer,
    _make_availability_scorer,
    _make_workforce_scorer,
)
from mcp_server.swarm.decision_synthesizer import (
    DecisionSynthesizer,
    SignalType,
    DecisionOutcome,
)
from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
)
from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
)
from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def bridge_and_lifecycle():
    """Create ReputationBridge + LifecycleManager + Orchestrator with test agents."""
    rep_bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(rep_bridge, lifecycle)

    # Register 3 test agents
    for i, (name, wallet, personality) in enumerate(
        [
            ("Agent Alpha", "0xAAA1111", "explorer"),
            ("Agent Beta", "0xBBB2222", "specialist"),
            ("Agent Gamma", "0xCCC3333", "generalist"),
        ],
        start=1,
    ):
        lifecycle.register_agent(
            agent_id=i,
            name=name,
            wallet_address=wallet,
            personality=personality,
        )
        lifecycle.transition(i, AgentState.IDLE, "test setup")
        lifecycle.transition(i, AgentState.ACTIVE, "test setup")

        on_chain = OnChainReputation(agent_id=i, wallet_address=wallet)
        internal = InternalReputation(
            agent_id=i,
            total_tasks=10 * i,
            successful_tasks=8 * i,
        )
        orchestrator.register_reputation(i, on_chain, internal)

    return rep_bridge, lifecycle, orchestrator


@pytest.fixture
def orchestrator(bridge_and_lifecycle):
    _, _, orch = bridge_and_lifecycle
    return orch


@pytest.fixture
def mock_autojob():
    client = MagicMock()
    client.is_available.return_value = True
    client._post.return_value = {"success": False}  # default no decomposition

    enrichment = MagicMock()
    enrichment.skill_match = 75.0
    enrichment.match_score = 0.8
    enrichment.predicted_quality = 0.7
    enrichment.tier = "Silver"
    enrichment.category_experience = 0.6

    client.enrich_agents.return_value = {
        "0xAAA1111": enrichment,
        "0xBBB2222": enrichment,
        "0xCCC3333": enrichment,
    }
    return client


@pytest.fixture
def decision_bridge(bridge_and_lifecycle, orchestrator, mock_autojob):
    rep_bridge, lifecycle, _ = bridge_and_lifecycle
    synthesizer = DecisionSynthesizer()
    return DecisionBridge(
        synthesizer=synthesizer,
        orchestrator=orchestrator,
        lifecycle_manager=lifecycle,
        reputation_bridge=rep_bridge,
        autojob_client=mock_autojob,
        mode=BridgeMode.PRIMARY,
    )


@pytest.fixture
def queued_task():
    """Create a mock QueuedTask."""
    task = MagicMock()
    task.task_id = "t-001"
    task.title = "Verify storefront photo"
    task.categories = ["physical_verification"]
    task.bounty_usd = 5.0
    task.priority = TaskPriority.NORMAL
    task.status = "pending"
    task.attempts = 0
    task.max_attempts = 3
    task.ingested_at = datetime.now(timezone.utc)
    task.raw_data = {"description": "Take a photo of the store at 123 Main St"}

    task.to_task_request.return_value = TaskRequest(
        task_id="t-001",
        title="Verify storefront photo",
        categories=["physical_verification"],
        bounty_usd=5.0,
    )
    return task


# ──────────────────────────────────────────────────────────────
# Signal Adapter Tests
# ──────────────────────────────────────────────────────────────


class TestSignalAdapters:
    """Test individual signal scorer functions."""

    def test_reputation_scorer(self, bridge_and_lifecycle):
        rep_bridge, _, orchestrator = bridge_and_lifecycle
        # _make_reputation_scorer uses bridge.get_composite_score which needs
        # the orchestrator's stored data. We adapt to use compute_composite directly.
        scorer = _make_reputation_scorer(orchestrator)
        task = {"id": "t1"}

        score = scorer(task, {"agent_id": 1})
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_reputation_scorer_unknown_agent(self, bridge_and_lifecycle):
        _, _, orchestrator = bridge_and_lifecycle
        scorer = _make_reputation_scorer(orchestrator)
        score = scorer({"id": "t1"}, {"agent_id": 999})
        assert score == 0.0

    def test_reputation_scorer_no_id(self, bridge_and_lifecycle):
        _, _, orchestrator = bridge_and_lifecycle
        scorer = _make_reputation_scorer(orchestrator)
        score = scorer({"id": "t1"}, {})
        assert score == 0.0

    def test_reliability_scorer(self, bridge_and_lifecycle):
        _, _, orchestrator = bridge_and_lifecycle
        scorer = _make_reliability_scorer(orchestrator)
        task = {"id": "t1"}

        # Agent 1: 10 total, 8 successful = 80%
        score = scorer(task, {"agent_id": 1})
        assert score == pytest.approx(80.0)

    def test_reliability_scorer_new_agent(self, bridge_and_lifecycle):
        _, _, orchestrator = bridge_and_lifecycle
        scorer = _make_reliability_scorer(orchestrator)
        # Unknown agent defaults to 50 (neutral)
        score = scorer({"id": "t1"}, {"agent_id": 999})
        assert score == 50.0

    def test_capacity_scorer_idle_agent(self, bridge_and_lifecycle):
        _, lifecycle, _ = bridge_and_lifecycle
        scorer = _make_capacity_scorer(lifecycle)
        # Agent with no current task = high capacity
        score = scorer({"id": "t1"}, {"agent_id": 1})
        assert score > 50

    def test_capacity_scorer_busy_agent(self, bridge_and_lifecycle):
        _, lifecycle, _ = bridge_and_lifecycle
        record = lifecycle.agents[1]
        record.current_task_id = "busy-task"
        scorer = _make_capacity_scorer(lifecycle)
        score = scorer({"id": "t1"}, {"agent_id": 1})
        assert score == 10.0  # Busy

    def test_capacity_scorer_unknown_agent(self, bridge_and_lifecycle):
        _, lifecycle, _ = bridge_and_lifecycle
        scorer = _make_capacity_scorer(lifecycle)
        score = scorer({"id": "t1"}, {"agent_id": 999})
        assert score == 0.0

    def test_skill_match_scorer(self, mock_autojob):
        scorer = _make_skill_match_scorer(mock_autojob)
        task = {"id": "t1", "category": "tech"}
        score = scorer(task, {"wallet": "0xAAA1111"})
        assert score == 75.0

    def test_skill_match_scorer_no_wallet(self, mock_autojob):
        scorer = _make_skill_match_scorer(mock_autojob)
        score = scorer({"id": "t1"}, {})
        assert score == 0.0

    def test_availability_scorer(self):
        avail_bridge = MagicMock()
        prediction = MagicMock()
        prediction.probability = 0.85
        avail_bridge.predict.return_value = prediction

        scorer = _make_availability_scorer(avail_bridge)
        score = scorer({"id": "t1"}, {"wallet": "0xAAA"})
        assert score == pytest.approx(85.0)

    def test_availability_scorer_no_wallet(self):
        avail_bridge = MagicMock()
        scorer = _make_availability_scorer(avail_bridge)
        score = scorer({"id": "t1"}, {})
        assert score == 50.0  # Neutral

    def test_workforce_scorer(self):
        analytics = MagicMock()
        analytics.get_worker_health.return_value = {"health_score": 92.0}

        scorer = _make_workforce_scorer(analytics)
        score = scorer({"id": "t1"}, {"agent_id": 1})
        assert score == 92.0

    def test_workforce_scorer_unknown(self):
        analytics = MagicMock()
        analytics.get_worker_health.return_value = None

        scorer = _make_workforce_scorer(analytics)
        score = scorer({"id": "t1"}, {"agent_id": 1})
        assert score == 50.0  # Neutral


# ──────────────────────────────────────────────────────────────
# DecisionBridge Core Tests
# ──────────────────────────────────────────────────────────────


class TestDecisionBridge:
    """Test the DecisionBridge integration layer."""

    def test_init(self, decision_bridge):
        assert decision_bridge.mode == BridgeMode.PRIMARY
        assert decision_bridge.synthesizer is not None
        assert decision_bridge.orchestrator is not None
        assert len(decision_bridge.synthesizer.registered_signals) > 0

    def test_signal_auto_registration(self, decision_bridge):
        signals = decision_bridge.synthesizer.registered_signals
        assert "reputation" in signals
        assert "reliability" in signals
        assert "skill_match" in signals
        assert "capacity" in signals

    def test_collect_candidates(self, decision_bridge, queued_task):
        candidates = decision_bridge._collect_candidates(queued_task)
        assert len(candidates) == 3
        assert all("agent_id" in c for c in candidates)
        assert all("wallet" in c for c in candidates)

    def test_process_single_task_primary_mode(self, decision_bridge, queued_task):
        result = decision_bridge._process_single_task(queued_task)
        assert isinstance(result, BridgeResult)
        assert result.task_id == "t-001"
        assert result.mode == BridgeMode.PRIMARY
        assert result.used_synthesis is True
        assert result.decision is not None

    def test_process_single_task_shadow_mode(self, decision_bridge, queued_task):
        decision_bridge.mode = BridgeMode.SHADOW
        result = decision_bridge._process_single_task(queued_task)
        assert result.used_synthesis is False
        assert result.decision is not None  # Still computed for logging
        assert result.mode == BridgeMode.SHADOW

    def test_process_single_task_disabled_mode(self, decision_bridge, queued_task):
        decision_bridge.mode = BridgeMode.DISABLED
        result = decision_bridge._process_single_task(queued_task)
        assert result.decision is None
        assert result.used_synthesis is False

    def test_process_with_synthesis(self, decision_bridge, queued_task):
        task_queue = {"t-001": queued_task}
        results = decision_bridge.process_with_synthesis(task_queue, max_tasks=5)
        assert len(results) == 1
        assert results[0].task_id == "t-001"
        assert decision_bridge._total_processed == 1

    def test_process_skips_non_pending(self, decision_bridge, queued_task):
        queued_task.status = "assigned"
        task_queue = {"t-001": queued_task}
        results = decision_bridge.process_with_synthesis(task_queue)
        assert len(results) == 0

    def test_process_skips_exhausted_attempts(self, decision_bridge, queued_task):
        queued_task.attempts = 5
        task_queue = {"t-001": queued_task}
        results = decision_bridge.process_with_synthesis(task_queue)
        assert len(results) == 0

    def test_no_candidates_returns_failure(self, queued_task):
        """Test that no candidates produces a failure result."""
        # Create a bridge with empty lifecycle (no agents at all)
        rep_bridge = ReputationBridge()
        lifecycle = LifecycleManager()
        orchestrator = SwarmOrchestrator(rep_bridge, lifecycle)
        synthesizer = DecisionSynthesizer()

        bridge = DecisionBridge(
            synthesizer=synthesizer,
            orchestrator=orchestrator,
            lifecycle_manager=lifecycle,
            reputation_bridge=rep_bridge,
            autojob_client=None,
            mode=BridgeMode.PRIMARY,
        )
        result = bridge._process_single_task(queued_task)
        assert result.failure is not None
        assert "No available candidates" in result.failure.reason

    def test_synthesis_time_tracked(self, decision_bridge, queued_task):
        result = decision_bridge._process_single_task(queued_task)
        assert result.synthesis_time_ms >= 0


# ──────────────────────────────────────────────────────────────
# Decomposition Tests
# ──────────────────────────────────────────────────────────────


class TestDecomposition:
    """Test task decomposition via AutoJob."""

    def test_no_decompose_low_bounty(self, decision_bridge, queued_task):
        queued_task.bounty_usd = 3.0
        decomp = decision_bridge._try_decompose(queued_task)
        assert decomp is None

    def test_no_decompose_without_autojob(self, decision_bridge, queued_task):
        decision_bridge.autojob = None
        queued_task.bounty_usd = 50.0
        decomp = decision_bridge._try_decompose(queued_task)
        assert decomp is None

    def test_no_decompose_autojob_unavailable(self, decision_bridge, queued_task):
        decision_bridge.autojob.is_available.return_value = False
        queued_task.bounty_usd = 50.0
        decomp = decision_bridge._try_decompose(queued_task)
        assert decomp is None

    def test_decompose_success(self, decision_bridge, queued_task):
        queued_task.bounty_usd = 50.0
        decision_bridge.autojob._post.return_value = {
            "success": True,
            "sub_tasks": [
                {"title": "Frontend", "skills": ["react"]},
                {"title": "Backend", "skills": ["python"]},
            ],
            "team_strategy": "parallel",
            "estimated_hours": 8.0,
        }
        decomp = decision_bridge._try_decompose(queued_task)
        assert decomp is not None
        assert decomp.is_compound is True
        assert len(decomp.sub_tasks) == 2
        assert decomp.team_strategy == "parallel"
        assert decision_bridge._total_decomposed == 1

    def test_decompose_single_task(self, decision_bridge, queued_task):
        queued_task.bounty_usd = 15.0
        decision_bridge.autojob._post.return_value = {
            "success": True,
            "sub_tasks": [
                {"title": "Photo verification", "skills": ["camera"]},
            ],
            "team_strategy": "solo",
        }
        decomp = decision_bridge._try_decompose(queued_task)
        assert decomp is not None
        assert decomp.is_compound is False

    def test_decompose_failure_graceful(self, decision_bridge, queued_task):
        queued_task.bounty_usd = 50.0
        decision_bridge.autojob._post.side_effect = Exception("timeout")
        decomp = decision_bridge._try_decompose(queued_task)
        assert decomp is None  # Graceful fallback

    def test_decompose_disabled(self, decision_bridge, queued_task):
        decision_bridge.decomposition_enabled = False
        queued_task.bounty_usd = 100.0
        result = decision_bridge._process_single_task(queued_task)
        assert result.decomposition is None


# ──────────────────────────────────────────────────────────────
# Feedback Loop Tests
# ──────────────────────────────────────────────────────────────


class TestFeedbackLoop:
    """Test the decision → outcome → weight evolution loop."""

    def test_record_outcome_basic(self, decision_bridge, queued_task):
        # First, process a task to create a decision record
        task_queue = {"t-001": queued_task}
        decision_bridge.process_with_synthesis(task_queue)

        # Record outcome
        decision_bridge.record_outcome(
            "t-001",
            outcome="completed",
            quality_rating=0.9,
            time_to_completion_hours=2.5,
        )

        assert decision_bridge._total_feedback_recorded == 1
        assert len(decision_bridge._feedback) == 1
        assert decision_bridge._feedback[0].actual_outcome == "completed"

    def test_record_outcome_disabled(self, decision_bridge):
        decision_bridge.feedback_enabled = False
        decision_bridge.record_outcome("t-001", "completed")
        assert decision_bridge._total_feedback_recorded == 0

    def test_record_unknown_task(self, decision_bridge):
        # Recording an outcome for a task we never processed
        decision_bridge.record_outcome("unknown-task", "completed")
        assert decision_bridge._total_feedback_recorded == 1
        assert decision_bridge._feedback[0].decision_outcome == "unknown"

    def test_feedback_history(self, decision_bridge, queued_task):
        task_queue = {"t-001": queued_task}
        decision_bridge.process_with_synthesis(task_queue)

        decision_bridge.record_outcome("t-001", "completed", quality_rating=0.85)
        decision_bridge.record_outcome("t-002", "expired")
        decision_bridge.record_outcome("t-003", "failed")

        history = decision_bridge.get_feedback_history(limit=10)
        assert len(history) == 3
        assert history[0]["actual"] == "completed"
        assert history[0]["quality"] == 0.85

    def test_auto_evolve_not_triggered_below_threshold(
        self, decision_bridge, queued_task
    ):
        decision_bridge.auto_evolve_threshold = 50
        mock_optimizer = MagicMock()
        decision_bridge.routing_optimizer = mock_optimizer

        decision_bridge.record_outcome("t-001", "completed")
        mock_optimizer.evolve.assert_not_called()

    def test_auto_evolve_triggered_at_threshold(self, decision_bridge, queued_task):
        decision_bridge.auto_evolve_threshold = 2
        decision_bridge._decisions_since_evolve = 3

        mock_optimizer = MagicMock()
        mock_optimizer.evolve.return_value = None
        decision_bridge.routing_optimizer = mock_optimizer

        decision_bridge.record_outcome("t-001", "completed")
        mock_optimizer.evolve.assert_called_once()

    def test_weight_update_from_optimizer(self, decision_bridge):
        decision_bridge.auto_evolve_threshold = 1
        decision_bridge._decisions_since_evolve = 2

        mock_optimizer = MagicMock()
        mock_rec = MagicMock()
        mock_rec.confidence = 0.8
        mock_rec.weights.skill_match = 0.40
        mock_rec.weights.reputation = 0.30
        mock_rec.weights.capacity = 0.15
        mock_rec.weights.speed = 0.10
        mock_rec.weights.cost = 0.05
        mock_optimizer.evolve.return_value = mock_rec

        decision_bridge.routing_optimizer = mock_optimizer
        decision_bridge.synthesizer.get_weights()

        decision_bridge.record_outcome("t-001", "completed")

        new_weights = decision_bridge.synthesizer.get_weights()
        assert new_weights["skill_match"] == 0.4
        assert new_weights["reputation"] == 0.3

    def test_low_confidence_skips_weight_update(self, decision_bridge):
        decision_bridge.auto_evolve_threshold = 1
        decision_bridge._decisions_since_evolve = 2

        mock_optimizer = MagicMock()
        mock_rec = MagicMock()
        mock_rec.confidence = 0.3  # Below 0.6 threshold
        mock_optimizer.evolve.return_value = mock_rec
        decision_bridge.routing_optimizer = mock_optimizer

        old_weights = decision_bridge.synthesizer.get_weights().copy()
        decision_bridge.record_outcome("t-001", "completed")
        new_weights = decision_bridge.synthesizer.get_weights()
        assert new_weights == old_weights  # Unchanged


# ──────────────────────────────────────────────────────────────
# Bridge Mode Tests
# ──────────────────────────────────────────────────────────────


class TestBridgeModes:
    """Test all operational modes."""

    def test_primary_mode_uses_synthesis(self, decision_bridge, queued_task):
        decision_bridge.mode = BridgeMode.PRIMARY
        result = decision_bridge._process_single_task(queued_task)
        assert result.used_synthesis is True
        assert result.decision is not None
        assert result.decision.outcome in (DecisionOutcome.ROUTED, DecisionOutcome.HELD)

    def test_shadow_mode_logs_only(self, decision_bridge, queued_task):
        decision_bridge.mode = BridgeMode.SHADOW
        result = decision_bridge._process_single_task(queued_task)
        assert result.used_synthesis is False
        assert result.decision is not None  # Computed for logging
        # Legacy routing was used
        assert result.mode == BridgeMode.SHADOW

    def test_advisory_mode(self, decision_bridge, queued_task):
        decision_bridge.mode = BridgeMode.ADVISORY
        result = decision_bridge._process_single_task(queued_task)
        assert result.used_synthesis is False
        assert result.decision is not None

    def test_disabled_mode_no_synthesis(self, decision_bridge, queued_task):
        decision_bridge.mode = BridgeMode.DISABLED
        result = decision_bridge._process_single_task(queued_task)
        assert result.decision is None
        assert result.used_synthesis is False


# ──────────────────────────────────────────────────────────────
# Stats & Dashboard Tests
# ──────────────────────────────────────────────────────────────


class TestStats:
    """Test bridge statistics and monitoring."""

    def test_initial_stats(self, decision_bridge):
        stats = decision_bridge.stats
        assert stats["mode"] == "primary"
        assert stats["total_processed"] == 0
        assert stats["total_synthesized"] == 0
        assert stats["total_decomposed"] == 0
        assert "synthesizer" in stats
        assert "current_weights" in stats

    def test_stats_after_processing(self, decision_bridge, queued_task):
        task_queue = {"t-001": queued_task}
        decision_bridge.process_with_synthesis(task_queue)

        stats = decision_bridge.stats
        assert stats["total_processed"] == 1
        assert stats["total_synthesized"] == 1
        assert len(stats["registered_signals"]) >= 3

    def test_stats_include_feedback_accuracy(self, decision_bridge, queued_task):
        task_queue = {"t-001": queued_task}
        decision_bridge.process_with_synthesis(task_queue)
        decision_bridge.record_outcome("t-001", "completed")

        stats = decision_bridge.stats
        assert stats["feedback_recorded"] == 1

    def test_bridge_result_to_dict(self, decision_bridge, queued_task):
        result = decision_bridge._process_single_task(queued_task)
        d = result.to_dict()
        assert "task_id" in d
        assert "mode" in d
        assert "used_synthesis" in d
        assert "synthesis_time_ms" in d


# ──────────────────────────────────────────────────────────────
# Factory Tests
# ──────────────────────────────────────────────────────────────


class TestFactory:
    """Test from_coordinator factory method."""

    def test_from_coordinator_basic(self, bridge_and_lifecycle, mock_autojob):
        rep_bridge, lifecycle, orch = bridge_and_lifecycle

        coordinator = MagicMock()
        coordinator.bridge = rep_bridge
        coordinator.lifecycle = lifecycle
        coordinator.orchestrator = orch
        coordinator.autojob = mock_autojob
        coordinator.routing_optimizer = None
        coordinator.availability_bridge = None
        coordinator.workforce_analytics = None

        bridge = DecisionBridge.from_coordinator(coordinator)
        assert bridge.synthesizer is not None
        assert bridge.mode == BridgeMode.PRIMARY
        signals = bridge.synthesizer.registered_signals
        assert "reputation" in signals

    def test_from_coordinator_custom_mode(self, bridge_and_lifecycle, mock_autojob):
        rep_bridge, lifecycle, orch = bridge_and_lifecycle

        coordinator = MagicMock()
        coordinator.bridge = rep_bridge
        coordinator.lifecycle = lifecycle
        coordinator.orchestrator = orch
        coordinator.autojob = mock_autojob
        coordinator.routing_optimizer = None
        coordinator.availability_bridge = None
        coordinator.workforce_analytics = None

        bridge = DecisionBridge.from_coordinator(coordinator, mode=BridgeMode.SHADOW)
        assert bridge.mode == BridgeMode.SHADOW


# ──────────────────────────────────────────────────────────────
# Integration / End-to-End Tests
# ──────────────────────────────────────────────────────────────


class TestE2E:
    """End-to-end tests for the full decision pipeline."""

    def test_full_pipeline_process_to_feedback(self, decision_bridge, queued_task):
        """Full cycle: process → decision → outcome → feedback."""
        # Step 1: Process task
        task_queue = {"t-001": queued_task}
        results = decision_bridge.process_with_synthesis(task_queue)
        assert len(results) == 1
        result = results[0]
        assert result.decision is not None

        # Step 2: Record outcome
        decision_bridge.record_outcome(
            "t-001",
            outcome="completed",
            quality_rating=0.92,
            time_to_completion_hours=1.5,
        )

        # Step 3: Check feedback
        history = decision_bridge.get_feedback_history()
        assert len(history) == 1
        assert history[0]["task_id"] == "t-001"
        assert history[0]["actual"] == "completed"
        assert history[0]["quality"] == 0.92

    def test_multiple_tasks_batch(self, decision_bridge):
        """Process multiple tasks in one batch."""
        tasks = {}
        for i in range(5):
            task = MagicMock()
            task.task_id = f"t-{i:03d}"
            task.title = f"Task {i}"
            task.categories = ["general"]
            task.bounty_usd = 5.0 + i
            task.priority = TaskPriority.NORMAL
            task.status = "pending"
            task.attempts = 0
            task.max_attempts = 3
            task.ingested_at = datetime.now(timezone.utc)
            task.raw_data = {}
            task.to_task_request.return_value = TaskRequest(
                task_id=f"t-{i:03d}",
                title=f"Task {i}",
                categories=["general"],
                bounty_usd=5.0 + i,
            )
            tasks[f"t-{i:03d}"] = task

        results = decision_bridge.process_with_synthesis(tasks, max_tasks=3)
        assert len(results) == 3  # max_tasks=3
        assert decision_bridge._total_processed == 3

    def test_decomposition_in_full_pipeline(self, decision_bridge, queued_task):
        """Test that decomposition integrates into the full pipeline."""
        queued_task.bounty_usd = 50.0
        decision_bridge.autojob._post.return_value = {
            "success": True,
            "sub_tasks": [
                {"title": "Part A", "skills": ["react"]},
                {"title": "Part B", "skills": ["python"]},
            ],
            "team_strategy": "specialist",
            "estimated_hours": 6.0,
        }

        result = decision_bridge._process_single_task(queued_task)
        assert result.decomposition is not None
        assert result.decomposition.is_compound is True
        assert result.decomposition.team_strategy == "specialist"
        # Decision still happens (decomposition is advisory)
        assert result.decision is not None

    def test_deque_bounded_growth(self, decision_bridge, queued_task):
        """Ensure internal buffers don't grow unbounded."""
        for i in range(1100):
            decision_bridge.record_outcome(f"t-{i}", "completed")

        # Deque maxlen=1000
        assert len(decision_bridge._feedback) <= 1000

    def test_graceful_without_optional_modules(self):
        """Bridge works with just orchestrator and synthesizer."""
        rep_bridge = ReputationBridge()
        lifecycle = LifecycleManager()

        # Register one agent
        lifecycle.register_agent(1, "Solo", "0xAAA", "explorer")
        lifecycle.transition(1, AgentState.IDLE, "test")
        lifecycle.transition(1, AgentState.ACTIVE, "test")

        orchestrator = SwarmOrchestrator(rep_bridge, lifecycle)
        orchestrator.register_reputation(
            1, OnChainReputation(1, "0xAAA"), InternalReputation(1)
        )
        synthesizer = DecisionSynthesizer()

        bridge = DecisionBridge(
            synthesizer=synthesizer,
            orchestrator=orchestrator,
            lifecycle_manager=lifecycle,
            reputation_bridge=rep_bridge,
            autojob_client=None,
            mode=BridgeMode.PRIMARY,
        )

        # Should still work with fewer signals
        signals = bridge.synthesizer.registered_signals
        assert "reputation" in signals
        assert "skill_match" not in signals  # No autojob

    def test_concurrent_decisions_independent(self, decision_bridge):
        """Each task gets independent signal evaluation."""
        task_a = MagicMock()
        task_a.task_id = "t-a"
        task_a.title = "Photo verification"
        task_a.categories = ["photo"]
        task_a.bounty_usd = 5.0
        task_a.priority = TaskPriority.NORMAL
        task_a.status = "pending"
        task_a.attempts = 0
        task_a.max_attempts = 3
        task_a.ingested_at = datetime.now(timezone.utc)
        task_a.raw_data = {}
        task_a.to_task_request.return_value = TaskRequest(
            task_id="t-a",
            title="Photo",
            categories=["photo"],
            bounty_usd=5.0,
        )

        task_b = MagicMock()
        task_b.task_id = "t-b"
        task_b.title = "Code review"
        task_b.categories = ["technical"]
        task_b.bounty_usd = 25.0
        task_b.priority = TaskPriority.HIGH
        task_b.status = "pending"
        task_b.attempts = 0
        task_b.max_attempts = 3
        task_b.ingested_at = datetime.now(timezone.utc)
        task_b.raw_data = {}
        task_b.to_task_request.return_value = TaskRequest(
            task_id="t-b",
            title="Code review",
            categories=["technical"],
            bounty_usd=25.0,
        )

        result_a = decision_bridge._process_single_task(task_a)
        result_b = decision_bridge._process_single_task(task_b)

        assert result_a.task_id == "t-a"
        assert result_b.task_id == "t-b"
        assert result_a.decision.task_id == "t-a"
        assert result_b.decision.task_id == "t-b"


class TestDecisionBridgeWith12Signals:
    """Test DecisionBridge with all 12 signals including MarketIntelligenceAdapter."""

    def test_market_intelligence_signal_registration(self):
        """MarketIntelligenceAdapter should register MARKET_INTELLIGENCE signal."""
        from mcp_server.swarm.market_intelligence_adapter import (
            MarketIntelligenceAdapter,
        )

        synthesizer = DecisionSynthesizer()
        rep_bridge = ReputationBridge()
        lifecycle = LifecycleManager()
        orchestrator = SwarmOrchestrator(rep_bridge, lifecycle)

        adapter = MarketIntelligenceAdapter(autojob_base_url="http://localhost:8899")

        bridge = DecisionBridge(
            synthesizer=synthesizer,
            orchestrator=orchestrator,
            lifecycle_manager=lifecycle,
            reputation_bridge=rep_bridge,
            market_intelligence_adapter=adapter,
            mode=BridgeMode.PRIMARY,
        )

        signals = bridge.synthesizer.registered_signals
        assert "market_intelligence" in signals

    def test_market_intelligence_scorer_returns_valid_score(self):
        """Market scorer should return health score for task category."""
        from mcp_server.swarm.market_intelligence_adapter import (
            MarketIntelligenceAdapter,
            MarketSnapshot,
            make_market_scorer,
        )

        adapter = MarketIntelligenceAdapter()
        # Pre-populate cache
        adapter._market_cache["delivery"] = MarketSnapshot(
            category="delivery",
            completion_rate=0.8,
            expiry_rate=0.2,
            demand_score=0.5,
            trend="growing",
            fetched_at=time.time(),
        )

        scorer = make_market_scorer(adapter)
        score = scorer(
            task={"category": "delivery"},
            candidate={"wallet": "0xAAA"},
        )

        assert 0 <= score <= 100
        assert score > 60  # Healthy market should score well

    def test_bridge_without_market_intelligence_still_works(self):
        """Bridge should work fine when market_intelligence_adapter is None."""
        synthesizer = DecisionSynthesizer()
        rep_bridge = ReputationBridge()
        lifecycle = LifecycleManager()
        orchestrator = SwarmOrchestrator(rep_bridge, lifecycle)

        bridge = DecisionBridge(
            synthesizer=synthesizer,
            orchestrator=orchestrator,
            lifecycle_manager=lifecycle,
            reputation_bridge=rep_bridge,
            market_intelligence_adapter=None,
            mode=BridgeMode.PRIMARY,
        )

        signals = bridge.synthesizer.registered_signals
        assert "market_intelligence" not in signals
        # Should still have reputation at least
        assert "reputation" in signals

    def test_all_12_signal_types_exist(self):
        """Verify all 12 SignalType enum values exist."""
        expected = [
            "reputation",
            "skill_match",
            "availability",
            "capacity",
            "speed",
            "cost",
            "recency",
            "reliability",
            "specialization",
            "performance",
            "pricing",
            "outcome",
            "decomposition",
            "retention",
            "market_intelligence",
        ]
        for name in expected:
            assert hasattr(SignalType, name.upper()), f"Missing SignalType: {name}"

    def test_market_intelligence_task_level_consistency(self):
        """Same task category should produce identical scores for different candidates."""
        from mcp_server.swarm.market_intelligence_adapter import (
            MarketIntelligenceAdapter,
            MarketSnapshot,
            make_market_scorer,
        )

        adapter = MarketIntelligenceAdapter()
        adapter._market_cache["physical_verification"] = MarketSnapshot(
            category="physical_verification",
            completion_rate=0.7,
            demand_score=0.5,
            trend="stable",
            fetched_at=time.time(),
        )

        scorer = make_market_scorer(adapter)
        task = {"category": "physical_verification"}

        scores = [scorer(task, {"wallet": f"0x{i:040x}"}) for i in range(5)]

        # All scores should be identical (task-level signal)
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"
