from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SWARM_DIR = ROOT / "mcp_server" / "swarm"


def _ensure_package() -> None:
    if "mcp_server" not in sys.modules:
        pkg = types.ModuleType("mcp_server")
        pkg.__path__ = [str(ROOT / "mcp_server")]
        sys.modules["mcp_server"] = pkg
    if "mcp_server.swarm" not in sys.modules:
        pkg = types.ModuleType("mcp_server.swarm")
        pkg.__path__ = [str(SWARM_DIR)]
        sys.modules["mcp_server.swarm"] = pkg


def _load_swarm_module(name: str):
    _ensure_package()
    fullname = f"mcp_server.swarm.{name}"
    if fullname in sys.modules:
        return sys.modules[fullname]

    path = SWARM_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(fullname, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[fullname] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


reputation_bridge = _load_swarm_module("reputation_bridge")
lifecycle_manager = _load_swarm_module("lifecycle_manager")
orchestrator_mod = _load_swarm_module("orchestrator")
coordinator_mod = _load_swarm_module("coordinator")
route_regret_mod = _load_swarm_module("route_regret")

ReputationBridge = reputation_bridge.ReputationBridge
OnChainReputation = reputation_bridge.OnChainReputation
InternalReputation = reputation_bridge.InternalReputation
LifecycleManager = lifecycle_manager.LifecycleManager
AgentState = lifecycle_manager.AgentState
SwarmOrchestrator = orchestrator_mod.SwarmOrchestrator
TaskPriority = orchestrator_mod.TaskPriority
SwarmCoordinator = coordinator_mod.SwarmCoordinator
RouteRegretCompiler = route_regret_mod.RouteRegretCompiler


def _register_agent(orchestrator: SwarmOrchestrator, agent_id: int, name: str, tasks: int, rating: float, success: int, category_score: float = 0.9) -> None:
    lifecycle = orchestrator.lifecycle
    lifecycle.register_agent(agent_id, name, f"0x{agent_id:040x}")
    lifecycle.transition(agent_id, AgentState.IDLE, "ready")
    orchestrator.register_reputation(
        agent_id=agent_id,
        on_chain=OnChainReputation(agent_id=agent_id, wallet_address=f"0x{agent_id:040x}"),
        internal=InternalReputation(
            agent_id=agent_id,
            total_tasks=tasks,
            successful_tasks=success,
            avg_rating=rating,
            avg_completion_time_hours=2.5,
            category_scores={"translation": category_score},
        ),
    )


def test_route_alternatives_capture_runner_ups():
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)
    coordinator = SwarmCoordinator(bridge=bridge, lifecycle=lifecycle, orchestrator=orchestrator)

    _register_agent(orchestrator, 1, "alpha", tasks=60, rating=4.8, success=58, category_score=0.95)
    _register_agent(orchestrator, 2, "beta", tasks=55, rating=4.6, success=50, category_score=0.88)
    _register_agent(orchestrator, 3, "gamma", tasks=20, rating=4.1, success=17, category_score=0.72)

    coordinator.ingest_task(
        task_id="task-1",
        title="Translate proof",
        categories=["translation"],
        bounty_usd=0.42,
        priority=TaskPriority.HIGH,
        raw_data={"id": "task-1", "category": "translation"},
    )

    results = coordinator.process_task_queue()
    assert len(results) == 1

    route_event = next(event for event in coordinator.get_events(limit=10) if event["event"] == "route_recorded")
    alternatives = route_event["alternatives"]
    assert alternatives
    assert alternatives[0]["agent_id"] != route_event["selected_agent_id"]
    assert "score" in alternatives[0]


def test_route_regret_compiler_marks_failed_route_as_regret():
    compiler = RouteRegretCompiler()
    report = compiler.compile_episode([
        {
            "event_type": "route",
            "task_id": "task-2",
            "coordination_session_id": "coord_task-2",
            "selected_agent_id": 1,
            "selected_score": 0.84,
            "alternatives": [
                {"agent_id": 2, "score": 0.82},
                {"agent_id": 3, "score": 0.77},
            ],
            "timestamp": 1.0,
        },
        {
            "event_type": "degrade",
            "task_id": "task-2",
            "coordination_session_id": "coord_task-2",
            "reason": "timeout",
            "timestamp": 2.0,
        },
        {
            "event_type": "outcome",
            "task_id": "task-2",
            "coordination_session_id": "coord_task-2",
            "status": "failed",
            "metadata": {"quality": 0.41},
            "timestamp": 3.0,
        },
    ])

    assert report is not None
    payload = report.to_dict()
    assert payload["judgment"] == "regret"
    assert payload["best_alternative_agent_id"] == 2
    assert payload["regret_score"] > 0.5


def test_route_regret_compiler_marks_clean_completion_as_validated():
    compiler = RouteRegretCompiler()
    report = compiler.compile_episode([
        {
            "event_type": "route",
            "task_id": "task-3",
            "coordination_session_id": "coord_task-3",
            "selected_agent_id": 7,
            "selected_score": 0.91,
            "alternatives": [{"agent_id": 8, "score": 0.8}],
            "timestamp": 1.0,
        },
        {
            "event_type": "outcome",
            "task_id": "task-3",
            "coordination_session_id": "coord_task-3",
            "status": "completed",
            "quality": 0.95,
            "timestamp": 5.0,
        },
    ])

    assert report is not None
    payload = report.to_dict()
    assert payload["judgment"] == "validated"
    assert payload["regret_score"] < 0
