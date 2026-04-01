#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rejection Flow -- E2E test for submission rejection lifecycle.

Tests the full rejection cycle on Base Mainnet:
  1. Create task
  2. Worker applies + gets assigned
  3. Worker submits evidence
  4. Agent rejects submission (minor severity)
  5. Verify task returns to published status (available for re-application)
  6. Verify submission verdict = rejected

Usage:
    python scripts/e2e_rejection_flow.py
    python scripts/e2e_rejection_flow.py --dry-run
    python scripts/e2e_rejection_flow.py --bounty 0.05

Environment:
    EM_API_KEY           -- Agent API key
    EM_API_URL           -- API base URL (default: https://api.execution.market)
    EM_WORKER_WALLET     -- Worker wallet (default: 0x4aa8...)
    EM_TEST_EXECUTOR_ID  -- Existing executor UUID (skips registration)

Cost: ~$0.00 (no payment released on rejection).
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / "mcp_server" / ".env")
load_dotenv(_project_root / ".env.local")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = os.environ.get("EM_API_URL", "https://api.execution.market").rstrip("/")
API_KEY = os.environ.get("EM_API_KEY", "")

WORKER_WALLET = os.environ.get(
    "EM_WORKER_WALLET", "YOUR_TEST_WORKER_WALLET"
)
EXISTING_EXECUTOR_ID = os.environ.get("EM_TEST_EXECUTOR_ID", "")

DEFAULT_BOUNTY = 0.10


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _icon(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _print_header(title: str) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}")


def _print_kv(key: str, value: Any, indent: int = 4) -> None:
    prefix = " " * indent
    print(f"{prefix}{key}: {value}")


# ---------------------------------------------------------------------------
# Phase result collector
# ---------------------------------------------------------------------------
class PhaseResult:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = "PENDING"
        self.details: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.start_time = time.time()
        self.elapsed_s = 0.0

    def pass_(self, **kwargs: Any) -> "PhaseResult":
        self.status = "PASS"
        self.details.update(kwargs)
        self.elapsed_s = round(time.time() - self.start_time, 2)
        return self

    def fail(self, error: str, **kwargs: Any) -> "PhaseResult":
        self.status = "FAIL"
        self.error = error
        self.details.update(kwargs)
        self.elapsed_s = round(time.time() - self.start_time, 2)
        return self

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "elapsed_s": self.elapsed_s,
        }
        if self.error:
            d["error"] = self.error
        d.update(self.details)
        return d

    def print_result(self) -> None:
        icon = _icon(self.status == "PASS")
        print(f"  [{icon}] Phase: {self.description} ({self.elapsed_s}s)")
        if self.error:
            print(f"         Error: {self.error}")


class FlowResults:
    def __init__(self):
        self.phases: Dict[str, PhaseResult] = {}
        self.start_time = time.time()

    def add(self, result: PhaseResult) -> None:
        self.phases[result.name] = result
        result.print_result()

    @property
    def all_passed(self) -> bool:
        return all(p.status == "PASS" for p in self.phases.values())

    @property
    def pass_count(self) -> int:
        return sum(1 for p in self.phases.values() if p.status == "PASS")

    @property
    def overall(self) -> str:
        if self.all_passed:
            return "PASS"
        return "FAIL"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _auth_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
        headers["X-API-Key"] = API_KEY
    return headers


async def api_call(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    json_data: Optional[dict] = None,
) -> dict:
    url = f"{API_BASE}/api/v1{path}"
    headers = _auth_headers()
    resp = await client.request(method, url, json=json_data, headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text, "status_code": resp.status_code}
    data["_http_status"] = resp.status_code
    return data


async def raw_get(client: httpx.AsyncClient, path: str) -> dict:
    url = f"{API_BASE}{path}"
    resp = await client.request("GET", url)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    data["_http_status"] = resp.status_code
    return data


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------
async def phase_health(client: httpx.AsyncClient) -> PhaseResult:
    phase = PhaseResult("health", "API Health Check")
    _print_header("PHASE 1: HEALTH CHECK")
    try:
        data = await raw_get(client, "/health")
        if data.get("_http_status") != 200:
            return phase.fail(f"Health check returned {data.get('_http_status')}")
        return phase.pass_()
    except Exception as e:
        return phase.fail(str(e))


async def phase_create_task(client: httpx.AsyncClient, bounty: float) -> PhaseResult:
    phase = PhaseResult("create_task", "Create task for rejection test")
    _print_header("PHASE 2: CREATE TASK")
    try:
        task_data = {
            "title": f"[E2E Rejection] {ts()}",
            "description": "Test task for rejection flow. Agent will reject the submission.",
            "bounty_usd": bounty,
            "category": "simple_action",
            "deadline_minutes": 10,
            "evidence_requirements": [
                {"type": "photo", "description": "Take a photo of any object"}
            ],
        }
        data = await api_call(client, "POST", "/tasks", task_data)
        status = data.get("_http_status")
        if status not in (200, 201):
            return phase.fail(f"HTTP {status} — {data.get('detail', data)}")

        task_id = data.get("id") or (data.get("data", {}) or {}).get("id")
        if not task_id:
            return phase.fail(f"No task_id: {data}")

        _print_kv("Task ID", task_id)
        return phase.pass_(task_id=task_id)
    except Exception as e:
        return phase.fail(str(e))


async def phase_register_worker(client: httpx.AsyncClient) -> PhaseResult:
    phase = PhaseResult("register_worker", "Register/Reuse Worker")
    _print_header("PHASE 3: REGISTER WORKER")

    if EXISTING_EXECUTOR_ID:
        _print_kv("Using existing executor", EXISTING_EXECUTOR_ID)
        return phase.pass_(executor_id=EXISTING_EXECUTOR_ID)

    try:
        worker_data = {"wallet_address": WORKER_WALLET, "name": "E2E Rejection Worker"}
        data = await api_call(client, "POST", "/workers/register", worker_data)
        status = data.get("_http_status")
        if status not in (200, 201):
            return phase.fail(f"HTTP {status} — {data}")

        executor_id = (
            data.get("executor_id")
            or (data.get("data", {}) or {}).get("id")
            or (data.get("data", {}) or {}).get("executor_id")
        )
        if not executor_id:
            return phase.fail(f"No executor_id: {data}")

        _print_kv("Executor ID", executor_id)
        return phase.pass_(executor_id=executor_id)
    except Exception as e:
        return phase.fail(str(e))


async def phase_apply_and_assign(
    client: httpx.AsyncClient, task_id: str, executor_id: str
) -> PhaseResult:
    phase = PhaseResult("apply_assign", "Apply + Assign worker")
    _print_header("PHASE 4: APPLY + ASSIGN")
    try:
        # Apply
        data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/apply",
            {"executor_id": executor_id, "message": "E2E rejection test"},
        )
        if data.get("_http_status") not in (200, 201):
            return phase.fail(f"Apply failed: HTTP {data.get('_http_status')} — {data}")
        _print_kv("Applied", "OK")

        await asyncio.sleep(2)

        # Assign
        data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/assign",
            {"executor_id": executor_id},
        )
        if data.get("_http_status") not in (200, 201):
            return phase.fail(
                f"Assign failed: HTTP {data.get('_http_status')} — {data}"
            )
        _print_kv("Assigned", "OK")

        return phase.pass_()
    except Exception as e:
        return phase.fail(str(e))


async def phase_submit_evidence(
    client: httpx.AsyncClient, task_id: str, executor_id: str
) -> PhaseResult:
    phase = PhaseResult("submit_evidence", "Submit evidence (mock)")
    _print_header("PHASE 5: SUBMIT EVIDENCE")
    try:
        submit_data = {
            "executor_id": executor_id,
            "evidence": {
                "photo_url": "https://cdn.execution.market/e2e-test-rejection.jpg",
                "notes": "E2E test submission (intentionally low quality for rejection test)",
            },
            "evidence_files": ["https://cdn.execution.market/e2e-test-rejection.jpg"],
        }
        data = await api_call(client, "POST", f"/tasks/{task_id}/submit", submit_data)
        status = data.get("_http_status")
        if status not in (200, 201):
            return phase.fail(f"HTTP {status} — {data}")

        submission_id = (
            data.get("submission_id")
            or (data.get("data", {}) or {}).get("submission_id")
            or (data.get("data", {}) or {}).get("id")
        )
        if not submission_id:
            return phase.fail(f"No submission_id: {data}")

        _print_kv("Submission ID", submission_id)
        return phase.pass_(submission_id=submission_id)
    except Exception as e:
        return phase.fail(str(e))


async def phase_reject_submission(
    client: httpx.AsyncClient, submission_id: str
) -> PhaseResult:
    phase = PhaseResult("reject", "Reject submission (minor severity)")
    _print_header("PHASE 6: REJECT SUBMISSION")
    try:
        reject_data = {
            "notes": "E2E test rejection: photo quality insufficient. Please retake with clearer resolution and proper lighting.",
            "severity": "minor",
        }
        data = await api_call(
            client,
            "POST",
            f"/submissions/{submission_id}/reject",
            reject_data,
        )
        status = data.get("_http_status")
        if status not in (200, 201):
            return phase.fail(f"HTTP {status} — {data}")

        _print_kv("Response", data.get("message", "?"))
        verdict = (data.get("data", {}) or {}).get("verdict")
        _print_kv("Verdict", verdict or "?")

        return phase.pass_(verdict=verdict)
    except Exception as e:
        return phase.fail(str(e))


async def phase_verify_task_returned_to_published(
    client: httpx.AsyncClient, task_id: str
) -> PhaseResult:
    phase = PhaseResult("verify_published", "Verify task returned to published")
    _print_header("PHASE 7: VERIFY TASK = PUBLISHED")
    try:
        data = await api_call(client, "GET", f"/tasks/{task_id}")
        if data.get("_http_status") != 200:
            return phase.fail(f"GET task failed: HTTP {data.get('_http_status')}")

        actual_status = data.get("status")
        _print_kv("Expected", "published")
        _print_kv("Actual", actual_status)

        if actual_status == "published":
            return phase.pass_(task_status=actual_status)
        else:
            return phase.fail(f"Expected 'published', got '{actual_status}'")
    except Exception as e:
        return phase.fail(str(e))


async def phase_verify_submission_rejected(
    client: httpx.AsyncClient, submission_id: str
) -> PhaseResult:
    phase = PhaseResult("verify_verdict", "Verify submission verdict = rejected")
    _print_header("PHASE 8: VERIFY SUBMISSION VERDICT")
    try:
        data = await api_call(client, "GET", f"/submissions/{submission_id}")
        if data.get("_http_status") != 200:
            return phase.fail(f"GET submission failed: HTTP {data.get('_http_status')}")

        verdict = data.get("agent_verdict") or data.get("verdict")
        _print_kv("Verdict", verdict)
        _print_kv("Notes", (data.get("agent_notes") or data.get("notes", ""))[:80])

        if verdict == "rejected":
            return phase.pass_(verdict=verdict)
        else:
            return phase.fail(f"Expected 'rejected', got '{verdict}'")
    except Exception as e:
        return phase.fail(str(e))


async def phase_cancel_task(client: httpx.AsyncClient, task_id: str) -> PhaseResult:
    """Cancel the test task to clean up."""
    phase = PhaseResult("cleanup_cancel", "Cancel test task (cleanup)")
    _print_header("PHASE 9: CLEANUP — CANCEL TASK")
    try:
        data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/cancel",
            {"reason": "E2E rejection test cleanup"},
        )
        status = data.get("_http_status")
        _print_kv("HTTP status", status)
        # Accept any success/conflict status for cleanup
        if status in (200, 201, 409):
            return phase.pass_()
        else:
            return phase.fail(f"Cancel failed: HTTP {status}")
    except Exception as e:
        return phase.fail(str(e))


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
async def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Rejection Flow E2E Test")
    parser.add_argument("--bounty", type=float, default=DEFAULT_BOUNTY)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _print_header("REJECTION FLOW E2E TEST")
    print(f"  API:    {API_BASE}")
    print(f"  Bounty: ${args.bounty}")
    print(f"  Worker: {WORKER_WALLET}")
    print(f"  Time:   {ts()}")

    if args.dry_run:
        print("\n  [DRY RUN] Config looks good. Exiting.")
        return 0

    results = FlowResults()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Phase 1: Health
        r = await phase_health(client)
        results.add(r)
        if r.status != "PASS":
            return 1

        # Phase 2: Create task
        r = await phase_create_task(client, args.bounty)
        results.add(r)
        task_id = r.details.get("task_id")
        if not task_id:
            return 1

        await asyncio.sleep(1)

        # Phase 3: Register worker
        r = await phase_register_worker(client)
        results.add(r)
        executor_id = r.details.get("executor_id")
        if not executor_id:
            return 1

        await asyncio.sleep(1)

        # Phase 4: Apply + Assign
        r = await phase_apply_and_assign(client, task_id, executor_id)
        results.add(r)
        if r.status != "PASS":
            return 1

        await asyncio.sleep(2)

        # Phase 5: Submit evidence
        r = await phase_submit_evidence(client, task_id, executor_id)
        results.add(r)
        submission_id = r.details.get("submission_id")
        if not submission_id:
            return 1

        await asyncio.sleep(2)

        # Phase 6: Reject submission
        r = await phase_reject_submission(client, submission_id)
        results.add(r)
        if r.status != "PASS":
            return 1

        await asyncio.sleep(2)

        # Phase 7: Verify task returned to published
        r = await phase_verify_task_returned_to_published(client, task_id)
        results.add(r)

        # Phase 8: Verify submission verdict
        r = await phase_verify_submission_rejected(client, submission_id)
        results.add(r)

        await asyncio.sleep(1)

        # Phase 9: Cleanup — cancel the test task
        r = await phase_cancel_task(client, task_id)
        results.add(r)

    # =========================================================================
    # Summary
    # =========================================================================
    _print_header("REJECTION FLOW RESULTS")
    for phase in results.phases.values():
        icon = _icon(phase.status == "PASS")
        print(f"  [{icon}] {phase.description}")
        if phase.error:
            print(f"         {phase.error}")

    print(f"\n  Overall: {results.overall}")
    print(f"  Passed: {results.pass_count}/{len(results.phases)}")
    print(f"  Elapsed: {round(time.time() - results.start_time, 1)}s")

    # Save JSON report
    report_path = _project_root / "docs" / "reports" / "REJECTION_FLOW_REPORT.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "test": "rejection_flow",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_base": API_BASE,
        "bounty_usd": args.bounty,
        "overall": results.overall,
        "pass_count": results.pass_count,
        "total_phases": len(results.phases),
        "phases": {k: v.to_dict() for k, v in results.phases.items()},
        "elapsed_s": round(time.time() - results.start_time, 2),
    }
    report_path.write_text(json.dumps(report_data, indent=2, default=str))
    print(f"\n  Report: {report_path}")

    return 0 if results.all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
