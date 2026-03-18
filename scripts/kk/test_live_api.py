import json
import sys
import urllib.request
from pathlib import Path

# Fix import path
mcp_server_path = str(Path(__file__).parent.parent.parent / "mcp_server")
sys.path.insert(0, mcp_server_path)

API_BASE = "https://api.execution.market"


def _api_get(path: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(f"{API_BASE}{path}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def test_api_health():
    data = _api_get("/health")
    assert data.get("status") in ("healthy", "ok"), f"Unexpected status: {data}"
    print(f"  ✅ API healthy — {data['status']}")


def test_fetch_completed_tasks():
    try:
        data = _api_get("/api/v1/tasks?status=completed&limit=5")
        tasks = data.get("tasks", [])
        print(f"  ✅ Fetched {len(tasks)} completed tasks directly via API")
    except Exception as e:
        print(f"  ❌ Error fetching completed tasks: {e}")


def test_coordinator_ingest():
    from swarm.coordinator import SwarmCoordinator, EMApiClient
    from swarm.reputation_bridge import ReputationBridge
    from swarm.lifecycle_manager import LifecycleManager
    from swarm.orchestrator import SwarmOrchestrator

    # Initialize components
    client = EMApiClient(base_url=API_BASE)
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge=bridge, lifecycle=lifecycle)

    coord = SwarmCoordinator(
        bridge=bridge, lifecycle=lifecycle, orchestrator=orchestrator, em_client=client
    )
    print("  ✅ SwarmCoordinator initialized with EMApiClient")

    # Ingest from API
    try:
        ingested = coord.ingest_from_api(limit=5)
        print(f"  ✅ SwarmCoordinator ingested {ingested} tasks from Live API")

        metrics = coord.get_metrics()
        print(
            f"  ✅ Metrics: {metrics.tasks_ingested} ingested, {metrics.tasks_assigned} assigned"
        )
    except Exception as e:
        print(f"  ❌ Error during ingest: {e}")


if __name__ == "__main__":
    print("\n🔗 Live EM API Integration Tests")
    print("=" * 50)

    test_api_health()
    test_fetch_completed_tasks()
    test_coordinator_ingest()
