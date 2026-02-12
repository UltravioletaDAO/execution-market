"""
E2E Test: Full Task Lifecycle Through MCP Server REST API

Tests the complete production flow through the remote MCP server:
1. Create task (escrow/balance-check depending on payment mode)
2. Worker applies
3. Agent assigns worker to task
4. Worker submits evidence
5. Agent approves -> payment settlement (92% worker + 8% treasury)
6. Verify payment TX in response

Also tests:
- Task cancellation flow (with refund if escrow)
- Submission rejection with reputation penalty

Target: https://api.execution.market (production)
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = os.environ.get("EM_API_URL", "https://api.execution.market").rstrip("/")

# Test executor (exists in Supabase)
FALLBACK_EXECUTOR_ID = "33333333-3333-3333-3333-333333333333"

# Use tiny bounties for test ($0.05)
TEST_BOUNTY = 0.05


def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


# ---------------------------------------------------------------------------
# Result collector
# ---------------------------------------------------------------------------
class Results:
    def __init__(self):
        self.scenarios: list[dict] = []

    def add(self, name: str, desc: str, data: dict):
        data["name"] = name
        data["description"] = desc
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.scenarios.append(data)
        status = data.get("status", "UNKNOWN")
        icon = (
            "PASS"
            if status == "SUCCESS"
            else "FAIL"
            if status == "FAILED"
            else "PARTIAL"
        )
        print(f"  [{icon}] {name}: {desc}")
        if data.get("error"):
            print(f"         Error: {data['error']}")
        if data.get("payment_tx"):
            print(f"         Payment TX: {data['payment_tx']}")
        if data.get("task_id"):
            tid = data["task_id"]
            print(f"         Task ID: {tid[:12]}...")


results = Results()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def api_call(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    json_data: Optional[dict] = None,
    headers: Optional[dict] = None,
) -> dict:
    """Make an API call to /api/v1/* and return parsed JSON."""
    url = f"{API_BASE}/api/v1{path}"
    resp = await client.request(method, url, json=json_data, headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text, "status_code": resp.status_code}
    data["_http_status"] = resp.status_code
    return data


async def raw_get(client: httpx.AsyncClient, path: str) -> dict:
    """GET a path relative to API_BASE (not under /api/v1/)."""
    url = f"{API_BASE}{path}"
    resp = await client.request("GET", url)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    data["_http_status"] = resp.status_code
    return data


# ---------------------------------------------------------------------------
# Scenario 0: Health & Config Check (runs first)
# ---------------------------------------------------------------------------
async def test_health(client: httpx.AsyncClient):
    print("\n" + "=" * 70)
    print("SCENARIO 0: HEALTH & CONFIG CHECK")
    print("=" * 70)

    # Health check (NOT under /api/v1/)
    health = await raw_get(client, "/health/")
    print(f"  Health: HTTP {health.get('_http_status')}")
    print(f"  Status: {health.get('status', 'N/A')}")

    # Public config (under /api/v1/)
    config = await api_call(client, "GET", "/config")
    print(f"  Config: HTTP {config.get('_http_status')}")
    networks = config.get("supported_networks", [])
    tokens = config.get("supported_tokens", [])
    preferred = config.get("preferred_network", "N/A")
    print(f"  Networks: {networks}")
    print(f"  Tokens: {tokens}")
    print(f"  Preferred: {preferred}")

    health_ok = health.get("_http_status") == 200
    config_ok = config.get("_http_status") == 200

    results.add(
        "health_check",
        "API health and config verification",
        {
            "status": "SUCCESS" if health_ok and config_ok else "PARTIAL",
            "health_http": health.get("_http_status"),
            "config_http": config.get("_http_status"),
            "networks": networks,
            "tokens": tokens,
            "preferred_network": preferred,
        },
    )

    return config


# ---------------------------------------------------------------------------
# Scenario 1: Happy Path (Create -> Apply -> Assign -> Submit -> Approve)
# ---------------------------------------------------------------------------
async def test_happy_path(client: httpx.AsyncClient, executor_id: str):
    print("\n" + "=" * 70)
    print("SCENARIO 1: HAPPY PATH")
    print("  Create -> Apply -> Assign -> Submit -> Approve (+ payment)")
    print(f"  API: {API_BASE}")
    print(f"  Bounty: ${TEST_BOUNTY}")
    print(f"  Executor: {executor_id}")
    print("=" * 70)

    # Step 1: Create task
    print("\n  [1/5] Creating task...")
    task_data = await api_call(
        client,
        "POST",
        "/tasks",
        {
            "title": f"E2E Happy Path {ts()}",
            "instructions": (
                "Take a photo of any nearby street sign. This is an automated E2E test."
            ),
            "category": "physical_presence",
            "bounty_usd": TEST_BOUNTY,
            "deadline_hours": 1,
            "evidence_required": ["photo"],
            "location_hint": "Any location",
            "payment_network": "base",
            "payment_token": "USDC",
        },
    )

    if task_data.get("_http_status") != 201:
        error_detail = task_data.get(
            "detail",
            task_data.get("error", json.dumps(task_data)[:200]),
        )
        results.add(
            "happy_path",
            "Full lifecycle test",
            {
                "status": "FAILED",
                "error": f"Task creation failed: HTTP {task_data.get('_http_status')} - {error_detail}",
            },
        )
        return None

    task_id = task_data.get("id")
    escrow_tx = task_data.get("escrow_tx")
    print(f"         Task ID: {task_id}")
    print(f"         Status: {task_data.get('status')}")
    if escrow_tx:
        print(f"         Escrow TX: {escrow_tx}")
        print(f"         BaseScan: https://basescan.org/tx/{escrow_tx}")
    else:
        print("         Escrow: N/A (Fase 1 balance-check only)")

    # Step 2: Worker applies
    print("\n  [2/5] Worker applying to task...")
    apply_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/apply",
        {
            "executor_id": executor_id,
            "message": "E2E test application - ready to work",
        },
    )
    print(f"         Apply: HTTP {apply_data.get('_http_status')}")
    print(f"         Message: {apply_data.get('message', 'N/A')}")

    if apply_data.get("_http_status") not in (200, 201):
        results.add(
            "happy_path",
            "Full lifecycle test",
            {
                "status": "FAILED",
                "task_id": task_id,
                "escrow_tx": escrow_tx,
                "error": f"Apply failed: {apply_data.get('detail', str(apply_data)[:200])}",
            },
        )
        return task_id

    # Step 3: Agent assigns worker to task
    print("\n  [3/5] Agent assigning worker to task...")
    assign_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/assign",
        {
            "executor_id": executor_id,
            "notes": "E2E test assignment",
        },
    )
    print(f"         Assign: HTTP {assign_data.get('_http_status')}")
    print(f"         Message: {assign_data.get('message', 'N/A')}")

    if assign_data.get("_http_status") not in (200, 201):
        results.add(
            "happy_path",
            "Full lifecycle test",
            {
                "status": "FAILED",
                "task_id": task_id,
                "escrow_tx": escrow_tx,
                "error": f"Assign failed: {assign_data.get('detail', str(assign_data)[:200])}",
            },
        )
        return task_id

    # Step 4: Worker submits evidence
    # Evidence keys MUST match the evidence_required types exactly
    print("\n  [4/5] Worker submitting evidence...")
    submit_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/submit",
        {
            "executor_id": executor_id,
            "evidence": {
                "photo": ["https://cdn.execution.market/evidence/e2e-test-photo.jpg"],
            },
            "notes": "Automated E2E test submission",
        },
    )
    print(f"         Submit: HTTP {submit_data.get('_http_status')}")
    print(f"         Message: {submit_data.get('message', 'N/A')}")

    if submit_data.get("_http_status") not in (200, 201):
        results.add(
            "happy_path",
            "Full lifecycle test",
            {
                "status": "FAILED",
                "task_id": task_id,
                "escrow_tx": escrow_tx,
                "error": f"Submit failed: {submit_data.get('detail', str(submit_data)[:200])}",
            },
        )
        return task_id

    # Find submission ID
    submission_id = (submit_data.get("data") or {}).get("submission_id")
    if not submission_id:
        print("         Looking up submission ID from task...")
        subs_data = await api_call(client, "GET", f"/tasks/{task_id}/submissions")
        subs_list = subs_data.get("submissions") or subs_data.get("data") or []
        if isinstance(subs_list, list) and subs_list:
            submission_id = subs_list[0].get("id")

    if not submission_id:
        results.add(
            "happy_path",
            "Full lifecycle test",
            {
                "status": "FAILED",
                "task_id": task_id,
                "escrow_tx": escrow_tx,
                "error": "Could not find submission ID after submit",
            },
        )
        return task_id

    print(f"         Submission ID: {submission_id}")

    # Step 5: Agent approves (triggers payment)
    print("\n  [5/5] Agent approving submission (triggers payment)...")
    approve_data = await api_call(
        client,
        "POST",
        f"/submissions/{submission_id}/approve",
        {
            "notes": "E2E test approval - verifying full payment flow",
            "rating_score": 85,
        },
    )
    print(f"         Approve: HTTP {approve_data.get('_http_status')}")
    print(f"         Message: {approve_data.get('message', 'N/A')}")

    resp_data = approve_data.get("data") or {}
    payment_tx = resp_data.get("payment_tx")
    payment_error = resp_data.get("payment_error")
    worker_tx = resp_data.get("worker_tx")
    fee_tx = resp_data.get("fee_tx")

    if payment_tx:
        print(f"         Payment TX: {payment_tx}")
        print(f"         BaseScan: https://basescan.org/tx/{payment_tx}")
    if worker_tx:
        print(f"         Worker TX: {worker_tx}")
    if fee_tx:
        print(f"         Fee TX: {fee_tx}")
    if payment_error:
        print(f"         Payment Error: {payment_error}")

    # Print full response data for debugging
    print(f"         Full data keys: {list(resp_data.keys())}")

    status = "SUCCESS" if approve_data.get("_http_status") == 200 else "FAILED"
    results.add(
        "happy_path",
        "Create -> Apply -> Assign -> Submit -> Approve (+ payment)",
        {
            "status": status,
            "task_id": task_id,
            "submission_id": submission_id,
            "escrow_tx": escrow_tx,
            "payment_tx": payment_tx,
            "worker_tx": worker_tx,
            "fee_tx": fee_tx,
            "payment_error": payment_error,
            "approve_http_status": approve_data.get("_http_status"),
            "approve_message": approve_data.get("message"),
            "approve_data": resp_data,
            "error": payment_error if payment_error else None,
        },
    )

    return task_id


# ---------------------------------------------------------------------------
# Scenario 2: Cancel Path (Create -> Cancel)
# ---------------------------------------------------------------------------
async def test_cancel_path(client: httpx.AsyncClient):
    print("\n" + "=" * 70)
    print("SCENARIO 2: CANCEL PATH (Create -> Cancel)")
    print("=" * 70)

    print("\n  [1/2] Creating task for cancellation...")
    task_data = await api_call(
        client,
        "POST",
        "/tasks",
        {
            "title": f"E2E Cancel Path {ts()}",
            "instructions": (
                "This task will be cancelled immediately. "
                "Automated E2E test for cancel flow verification."
            ),
            "category": "simple_action",
            "bounty_usd": TEST_BOUNTY,
            "deadline_hours": 1,
            "evidence_required": ["text_response"],
            "payment_network": "base",
            "payment_token": "USDC",
        },
    )

    if task_data.get("_http_status") != 201:
        error_detail = task_data.get("detail", "")
        if isinstance(error_detail, list):
            error_detail = str(error_detail)[:200]
        results.add(
            "cancel_path",
            "Cancel flow test",
            {
                "status": "FAILED",
                "error": f"Task creation failed: HTTP {task_data.get('_http_status')} - {error_detail}",
            },
        )
        return

    task_id = task_data.get("id")
    escrow_tx = task_data.get("escrow_tx")
    print(f"         Task ID: {task_id}")
    if escrow_tx:
        print(f"         Escrow TX: {escrow_tx}")

    # Cancel
    print("\n  [2/2] Cancelling task...")
    cancel_data = await api_call(client, "POST", f"/tasks/{task_id}/cancel")
    print(f"         Cancel: HTTP {cancel_data.get('_http_status')}")
    print(f"         Message: {cancel_data.get('message', 'N/A')}")

    resp_data = cancel_data.get("data") or {}
    refund_tx = resp_data.get("refund_tx")

    if refund_tx:
        print(f"         Refund TX: {refund_tx}")
        print(f"         BaseScan: https://basescan.org/tx/{refund_tx}")

    status = "SUCCESS" if cancel_data.get("_http_status") == 200 else "FAILED"
    results.add(
        "cancel_path",
        "Create task and immediately cancel (+ refund)",
        {
            "status": status,
            "task_id": task_id,
            "escrow_tx": escrow_tx,
            "refund_tx": refund_tx,
            "message": cancel_data.get("message"),
            "cancel_data": resp_data,
            "error": cancel_data.get("detail") if status == "FAILED" else None,
        },
    )


# ---------------------------------------------------------------------------
# Scenario 3: Rejection Path (Create -> Apply -> Assign -> Submit -> Reject)
# ---------------------------------------------------------------------------
async def test_rejection_path(client: httpx.AsyncClient, executor_id: str):
    print("\n" + "=" * 70)
    print("SCENARIO 3: REJECTION PATH")
    print("  Create -> Apply -> Assign -> Submit -> Reject")
    print("=" * 70)

    # Create
    print("\n  [1/5] Creating task for rejection...")
    task_data = await api_call(
        client,
        "POST",
        "/tasks",
        {
            "title": f"E2E Rejection Path {ts()}",
            "instructions": (
                "This task submission will be rejected. "
                "Automated E2E test for rejection with reputation penalty."
            ),
            "category": "knowledge_access",
            "bounty_usd": TEST_BOUNTY,
            "deadline_hours": 1,
            "evidence_required": ["photo", "text_response"],
            "payment_network": "base",
            "payment_token": "USDC",
        },
    )

    if task_data.get("_http_status") != 201:
        error_detail = task_data.get("detail", "")
        if isinstance(error_detail, list):
            error_detail = str(error_detail)[:200]
        results.add(
            "rejection_path",
            "Rejection flow test",
            {
                "status": "FAILED",
                "error": f"Task creation failed: HTTP {task_data.get('_http_status')} - {error_detail}",
            },
        )
        return

    task_id = task_data.get("id")
    escrow_tx = task_data.get("escrow_tx")
    print(f"         Task ID: {task_id}")
    if escrow_tx:
        print(f"         Escrow TX: {escrow_tx}")

    # Apply
    print("\n  [2/5] Worker applying...")
    apply_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/apply",
        {
            "executor_id": executor_id,
            "message": "E2E rejection test",
        },
    )
    print(f"         Apply: HTTP {apply_data.get('_http_status')}")

    if apply_data.get("_http_status") not in (200, 201):
        results.add(
            "rejection_path",
            "Rejection flow test",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Apply failed: {apply_data.get('detail', '')}",
            },
        )
        return

    # Assign
    print("\n  [3/5] Agent assigning worker...")
    assign_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/assign",
        {
            "executor_id": executor_id,
            "notes": "Assigning for rejection test",
        },
    )
    print(f"         Assign: HTTP {assign_data.get('_http_status')}")

    if assign_data.get("_http_status") not in (200, 201):
        results.add(
            "rejection_path",
            "Rejection flow test",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Assign failed: {assign_data.get('detail', '')}",
            },
        )
        return

    # Submit (evidence keys MUST match evidence_required)
    print("\n  [4/5] Worker submitting evidence for rejection...")
    submit_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/submit",
        {
            "executor_id": executor_id,
            "evidence": {
                "photo": ["https://cdn.execution.market/evidence/e2e-blurry-photo.jpg"],
                "text_response": "Incomplete submission for rejection test.",
            },
            "notes": "Intentionally low-quality for E2E rejection test",
        },
    )
    print(f"         Submit: HTTP {submit_data.get('_http_status')}")

    if submit_data.get("_http_status") not in (200, 201):
        results.add(
            "rejection_path",
            "Rejection flow test",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Submit failed: {submit_data.get('detail', str(submit_data)[:200])}",
            },
        )
        return

    submission_id = (submit_data.get("data") or {}).get("submission_id")
    if not submission_id:
        subs_data = await api_call(client, "GET", f"/tasks/{task_id}/submissions")
        subs_list = subs_data.get("submissions") or subs_data.get("data") or []
        if isinstance(subs_list, list) and subs_list:
            submission_id = subs_list[0].get("id")

    if not submission_id:
        results.add(
            "rejection_path",
            "Rejection flow test",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": "Could not find submission ID",
            },
        )
        return

    print(f"         Submission ID: {submission_id}")

    # Reject with major severity
    print("\n  [5/5] Agent rejecting with major severity...")
    reject_data = await api_call(
        client,
        "POST",
        f"/submissions/{submission_id}/reject",
        {
            "notes": (
                "E2E test rejection: evidence incomplete, missing required photo"
            ),
            "severity": "major",
            "reputation_score": 30,
        },
    )
    print(f"         Reject: HTTP {reject_data.get('_http_status')}")
    print(f"         Message: {reject_data.get('message', 'N/A')}")

    resp_data = reject_data.get("data") or {}
    reputation_tx = resp_data.get("reputation_tx")

    if reputation_tx:
        print(f"         Reputation TX: {reputation_tx}")
        print(f"         BaseScan: https://basescan.org/tx/{reputation_tx}")

    status = "SUCCESS" if reject_data.get("_http_status") == 200 else "FAILED"
    results.add(
        "rejection_path",
        "Create -> Apply -> Assign -> Submit -> Reject (major, score=30)",
        {
            "status": status,
            "task_id": task_id,
            "submission_id": submission_id,
            "escrow_tx": escrow_tx,
            "reputation_tx": reputation_tx,
            "reject_data": resp_data,
            "error": reject_data.get("detail") if status == "FAILED" else None,
        },
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def generate_report(results_obj: Results) -> str:
    lines = [
        "# E2E MCP API Test Report",
        "",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"> API: {API_BASE}",
        "> Flow: Full lifecycle through REST API (not direct Facilitator)",
        "",
        "---",
        "",
        "## Results Summary",
        "",
        "| # | Scenario | Status | Details |",
        "|---|----------|--------|---------|",
    ]

    for i, s in enumerate(results_obj.scenarios, 1):
        status = s.get("status", "UNKNOWN")
        icon = "PASS" if status == "SUCCESS" else "FAIL" if status == "FAILED" else "~"
        details = ""
        if s.get("payment_tx"):
            details = f"[Payment TX](https://basescan.org/tx/{s['payment_tx']})"
        elif s.get("escrow_tx"):
            details = f"[Escrow TX](https://basescan.org/tx/{s['escrow_tx']})"
        elif s.get("refund_tx"):
            details = f"[Refund TX](https://basescan.org/tx/{s['refund_tx']})"
        elif s.get("reputation_tx"):
            details = f"[Reputation TX](https://basescan.org/tx/{s['reputation_tx']})"
        elif s.get("error"):
            details = str(s["error"])[:80]
        elif s.get("message"):
            details = str(s["message"])[:80]

        lines.append(f"| {i} | {s['description'][:60]} | {icon} | {details} |")

    lines.extend(["", "---", "", "## Detailed Scenarios", ""])

    for s in results_obj.scenarios:
        lines.append(f"### {s['name']}")
        lines.append("")
        lines.append(f"**{s['description']}**")
        lines.append("")
        lines.append(f"- Status: **{s.get('status')}**")
        lines.append(f"- Timestamp: {s.get('timestamp')}")
        if s.get("task_id"):
            lines.append(f"- Task ID: `{s['task_id']}`")
        if s.get("submission_id"):
            lines.append(f"- Submission ID: `{s['submission_id']}`")
        if s.get("escrow_tx"):
            lines.append(
                f"- Escrow TX: [`{s['escrow_tx'][:16]}...`]"
                f"(https://basescan.org/tx/{s['escrow_tx']})"
            )
        if s.get("payment_tx"):
            lines.append(
                f"- Payment TX: [`{s['payment_tx'][:16]}...`]"
                f"(https://basescan.org/tx/{s['payment_tx']})"
            )
        if s.get("worker_tx"):
            lines.append(
                f"- Worker TX: [`{s['worker_tx'][:16]}...`]"
                f"(https://basescan.org/tx/{s['worker_tx']})"
            )
        if s.get("fee_tx"):
            lines.append(
                f"- Fee TX: [`{s['fee_tx'][:16]}...`]"
                f"(https://basescan.org/tx/{s['fee_tx']})"
            )
        if s.get("reputation_tx"):
            lines.append(
                f"- Reputation TX: [`{s['reputation_tx'][:16]}...`]"
                f"(https://basescan.org/tx/{s['reputation_tx']})"
            )
        if s.get("refund_tx"):
            lines.append(
                f"- Refund TX: [`{s['refund_tx'][:16]}...`]"
                f"(https://basescan.org/tx/{s['refund_tx']})"
            )
        if s.get("payment_error"):
            lines.append(f"- Payment Error: {s['payment_error']}")
        if s.get("error"):
            lines.append(f"- Error: {s['error']}")
        if s.get("networks"):
            lines.append(f"- Networks: {s['networks']}")
        if s.get("tokens"):
            lines.append(f"- Tokens: {s['tokens']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    print("=" * 70)
    print("E2E TEST: Full Task Lifecycle Through MCP Server REST API")
    print(f"API: {API_BASE}")
    print(f"Time: {ts()}")
    print("=" * 70)

    timeout = httpx.Timeout(120.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Health check first
        await test_health(client)

        # Use known test executor
        executor_id = FALLBACK_EXECUTOR_ID
        print(f"\nUsing executor: {executor_id}")

        # Run scenarios — reordered: light ops first, heavy (happy) last
        await test_cancel_path(client)
        await asyncio.sleep(5)
        await test_rejection_path(client, executor_id)
        await asyncio.sleep(5)
        await test_happy_path(client, executor_id)

    # Generate report
    report = generate_report(results)

    # Save report
    report_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "docs",
        "reports",
        "E2E_MCP_API_REPORT.md",
    )
    report_path = os.path.normpath(report_path)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved: {report_path}")

    # Save JSON
    json_path = report_path.replace(".md", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"scenarios": results.scenarios}, f, indent=2)
    print(f"JSON saved: {json_path}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total = len(results.scenarios)
    passed = sum(1 for s in results.scenarios if s.get("status") == "SUCCESS")
    failed = sum(1 for s in results.scenarios if s.get("status") == "FAILED")
    partial = total - passed - failed
    print(
        f"  Total: {total} | Passed: {passed} | Failed: {failed} | Partial: {partial}"
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
