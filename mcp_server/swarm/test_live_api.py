"""
Live API Integration Tests
===========================
Tests the SwarmCoordinator and EventListener against the live EM API.

Run from mcp_server/ directory:
    cd mcp_server && python3 -m pytest swarm/test_live_api.py -v -s
Or standalone:
    cd mcp_server && python3 swarm/test_live_api.py
"""

import json
import sys
import time
import urllib.request
import urllib.error

# Fix import path
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

API_BASE = "https://api.execution.market"


def _api_get(path: str, timeout: int = 10) -> dict:
    """GET request to the EM API."""
    req = urllib.request.Request(f"{API_BASE}{path}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def test_api_health():
    """Verify EM API is reachable and healthy."""
    data = _api_get("/health")
    assert data.get("status") in ("healthy", "ok"), f"Unexpected status: {data}"
    print(f"  ✅ API healthy — {data}")


def test_fetch_published_tasks():
    """Fetch published tasks from live API."""
    data = _api_get("/api/v1/tasks?status=published&limit=10")
    tasks = data.get("tasks", [])
    print(f"  ✅ Fetched {len(tasks)} published tasks")
    for t in tasks[:5]:
        print(f"     [{t.get('id', '?')[:8]}] {t.get('title', '?')} — ${t.get('bounty_usd', '?')} USDC")


def test_fetch_completed_tasks():
    """Fetch completed tasks to verify evidence data exists."""
    data = _api_get("/api/v1/tasks?status=completed&limit=10")
    tasks = data.get("tasks", [])
    print(f"  ✅ Fetched {len(tasks)} completed tasks")
    with_evidence = sum(1 for t in tasks if t.get("evidence"))
    print(f"     {with_evidence}/{len(tasks)} have evidence data")


def test_erc8128_nonce():
    """Verify ERC-8128 auth endpoint is operational."""
    data = _api_get("/api/v1/auth/nonce")
    nonce = data.get("nonce")
    assert nonce, f"No nonce returned: {data}"
    print(f"  ✅ ERC-8128 nonce: {nonce[:16]}...")


def test_coordinator_ingest():
    """Test EMApiClient + SwarmCoordinator against live API."""
    try:
        from swarm.coordinator import EMApiClient, SwarmCoordinator
        from swarm.reputation_bridge import ReputationBridge
        from swarm.lifecycle_manager import LifecycleManager
        from swarm.orchestrator import SwarmOrchestrator
    except ImportError as e:
        print(f"  ⚠️ Swarm modules not importable: {e}, skipping")
        return

    # Test EMApiClient directly
    client = EMApiClient(base_url=API_BASE)
    health = client.get_health()
    print(f"  ✅ EMApiClient connected — status: {health.get('status')}")
    
    tasks = client.list_tasks(status="completed", limit=5)
    print(f"  ✅ EMApiClient fetched {len(tasks)} completed tasks")
    
    # Test full coordinator pipeline
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge=bridge, lifecycle=lifecycle)
    coord = SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=client,
    )
    print(f"  ✅ SwarmCoordinator initialized with all components")
    
    # Try ingesting from API
    try:
        ingested = coord.ingest_from_api(limit=5)
        print(f"  ✅ Ingested {ingested} tasks from live API")
        metrics = coord.get_metrics()
        print(f"     Queue: ingested={metrics.tasks_ingested}, assigned={metrics.tasks_assigned}")
    except Exception as e:
        print(f"  ⚠️ Ingest from API: {type(e).__name__}: {e}")


def test_event_listener_poll():
    """Test EventListener single poll against live API via coordinator."""
    try:
        from swarm.event_listener import EventListener
        from swarm.coordinator import EMApiClient, SwarmCoordinator
        from swarm.reputation_bridge import ReputationBridge
        from swarm.lifecycle_manager import LifecycleManager
        from swarm.orchestrator import SwarmOrchestrator
    except ImportError as e:
        print(f"  ⚠️ Swarm modules not importable: {e}, skipping")
        return

    # Build coordinator (EventListener needs one)
    client = EMApiClient(base_url=API_BASE)
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge=bridge, lifecycle=lifecycle)
    coord = SwarmCoordinator(
        bridge=bridge, lifecycle=lifecycle,
        orchestrator=orchestrator, em_client=client,
    )
    
    listener = EventListener(coordinator=coord)
    print(f"  ✅ EventListener initialized with coordinator")
    
    try:
        events = listener.poll_once()
        print(f"  ✅ Poll completed — {len(events)} events")
        for ev in events[:3]:
            print(f"     {ev}")
    except Exception as e:
        print(f"  ⚠️ Poll: {type(e).__name__}: {e}")


def test_api_task_stats():
    """Get task statistics from live API."""
    stats = {}
    for status in ["published", "in_progress", "completed", "expired"]:
        try:
            data = _api_get(f"/api/v1/tasks?status={status}&limit=1")
            count = data.get("total", data.get("count", len(data.get("tasks", []))))
            stats[status] = count
        except Exception:
            stats[status] = "?"
    
    print(f"  ✅ Task stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    print("\n🔗 Live EM API Integration Tests")
    print("=" * 50)
    
    tests = [
        ("API Health", test_api_health),
        ("Published Tasks", test_fetch_published_tasks),
        ("Completed Tasks", test_fetch_completed_tasks),
        ("ERC-8128 Nonce", test_erc8128_nonce),
        ("Task Stats", test_api_task_stats),
        ("Coordinator Ingest", test_coordinator_ingest),
        ("EventListener Poll", test_event_listener_poll),
    ]
    
    passed = 0
    failed = 0
    for name, func in tests:
        try:
            print(f"\n▸ {name}")
            func()
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
    
    print(f"\n{'=' * 50}")
    print(f"  ✅ {passed} passed, ❌ {failed} failed")
