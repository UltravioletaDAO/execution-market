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
autojob_client = _load_swarm_module("autojob_client")
coordinator_mod = _load_swarm_module("coordinator")

ReputationBridge = reputation_bridge.ReputationBridge
OnChainReputation = reputation_bridge.OnChainReputation
InternalReputation = reputation_bridge.InternalReputation
LifecycleManager = lifecycle_manager.LifecycleManager
AgentState = lifecycle_manager.AgentState
SwarmOrchestrator = orchestrator_mod.SwarmOrchestrator
TaskRequest = orchestrator_mod.TaskRequest
TaskPriority = orchestrator_mod.TaskPriority
RoutingFailure = orchestrator_mod.RoutingFailure
EMApiClient = coordinator_mod.EMApiClient
SwarmCoordinator = coordinator_mod.SwarmCoordinator


def _register_agent(orchestrator: SwarmOrchestrator, agent_id: int, name: str, tasks: int, rating: float, success: int) -> None:
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
            avg_completion_time_hours=3.0,
            category_scores={"translation": 0.95, "verification": 0.85},
        ),
    )


def test_required_tier_filters_out_lower_tiers():
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)

    _register_agent(orchestrator, 1, "bronze", tasks=8, rating=3.6, success=6)
    _register_agent(orchestrator, 2, "gold", tasks=60, rating=4.7, success=56)
    _register_agent(orchestrator, 3, "new", tasks=0, rating=0.0, success=0)

    task = TaskRequest(
        task_id="task-gold-only",
        title="Spanish translation",
        categories=["translation"],
        priority=TaskPriority.HIGH,
        required_tier="gold",
    )

    assignment = orchestrator.route_task(task)

    assert not isinstance(assignment, RoutingFailure)
    assert assignment.agent_id == 2


def test_required_tier_rejects_unknown_values():
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)

    _register_agent(orchestrator, 1, "alpha", tasks=60, rating=4.7, success=56)

    failure = orchestrator.route_task(
        TaskRequest(
            task_id="task-bad-tier",
            title="Verification",
            categories=["verification"],
            required_tier="legendary",
        )
    )

    assert isinstance(failure, RoutingFailure)
    assert "Unknown required_tier" in failure.reason


def test_em_api_client_list_tasks_accepts_multiple_payload_shapes(monkeypatch):
    client = EMApiClient(base_url="https://api.execution.market")
    seen_paths = []

    def fake_request(method, path, data=None):
        seen_paths.append(path)
        return {"tasks": [{"id": "a"}]}

    client._request = fake_request  # type: ignore[method-assign]
    assert client.list_tasks(limit=1) == [{"id": "a"}]
    assert seen_paths[-1].startswith("/api/v1/tasks/available?")

    client._request = lambda method, path, data=None: {"data": [{"id": "b"}]}  # type: ignore[method-assign]
    assert client.list_tasks(limit=1) == [{"id": "b"}]

    client._request = lambda method, path, data=None: [{"id": "c"}]  # type: ignore[method-assign]
    assert client.list_tasks(limit=1) == [{"id": "c"}]


def test_em_api_client_task_stats_use_public_metrics_surface():
    client = EMApiClient(base_url="https://api.execution.market")

    client._request = lambda method, path, data=None: {  # type: ignore[method-assign]
        "tasks": {"live": 6, "completed": 281},
        "generated_at": "2026-04-05T06:00:00Z",
    }
    assert client.get_task_stats() == {"live": 6, "completed": 281}

    client._request = lambda method, path, data=None: {"error": True, "detail": "boom"}  # type: ignore[method-assign]
    assert client.get_task_stats()["error"] is True


def test_swarm_coordinator_factory_boots_core_components():
    coordinator = SwarmCoordinator.create(
        em_api_url="https://api.execution.market",
        autojob_url="http://localhost:8765",
    )

    assert coordinator.em_client is not None
    assert coordinator.autojob is not None
    assert coordinator.enriched is not None
    assert coordinator.orchestrator.lifecycle is coordinator.lifecycle
