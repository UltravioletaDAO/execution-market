#!/usr/bin/env python3
"""
E2E Full Lifecycle Test — Fee Split Verification

The "test of all tests". Runs the complete production flow through the MCP
Server REST API and verifies the fee split between Worker and Treasury with
on-chain TX evidence.

Scenarios:
  1. HAPPY PATH: Create → Apply → Assign → Submit → Approve
     - TX 1: Escrow authorize (lock bounty * 1.13)
     - TX 2: Worker disbursement ($bounty → Worker)
     - TX 3: Fee collection ($fee → Treasury)
  2. CANCEL PATH: Create → Cancel (full refund to agent)
  3. REJECTION PATH: Create → Apply → Assign → Submit → Reject (no payment)

Usage:
  python scripts/e2e_full_lifecycle.py                   # Full test
  python scripts/e2e_full_lifecycle.py --dry-run          # Config check only
  python scripts/e2e_full_lifecycle.py --happy-only       # Skip cancel/reject
  python scripts/e2e_full_lifecycle.py --bounty 0.05      # Custom bounty

Requires:
  - Production MCP Server at api.execution.market (or EM_API_URL override)
  - pip install httpx python-dotenv
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = os.environ.get("EM_API_URL", "https://api.execution.market").rstrip("/")

# Test executor ID (must exist in Supabase)
TEST_EXECUTOR_ID = os.environ.get(
    "EM_TEST_EXECUTOR_ID", "33333333-3333-3333-3333-333333333333"
)

# Known addresses for verification
TEST_WORKER_ADDRESS = "YOUR_TEST_WORKER_WALLET"
TREASURY_ADDRESS = "YOUR_TREASURY_WALLET"

# Default bounty (keep small to conserve wallet funds)
DEFAULT_BOUNTY = 0.10

# Platform fee (must match production EM_PLATFORM_FEE)
PLATFORM_FEE_PCT = Decimal("0.13")

BASESCAN_TX = "https://basescan.org/tx"


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def ts_short() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


# ---------------------------------------------------------------------------
# Result collector
# ---------------------------------------------------------------------------
class TestResult:
    """Collects structured results for each scenario."""

    def __init__(self):
        self.scenarios: List[Dict[str, Any]] = []

    def add(self, name: str, desc: str, data: Dict[str, Any]):
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

    @property
    def passed(self) -> int:
        return sum(1 for s in self.scenarios if s.get("status") == "SUCCESS")

    @property
    def failed(self) -> int:
        return sum(1 for s in self.scenarios if s.get("status") == "FAILED")


results = TestResult()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
async def api_call(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    json_data: Optional[dict] = None,
) -> dict:
    """Call /api/v1/* endpoint."""
    url = f"{API_BASE}/api/v1{path}"
    resp = await client.request(method, url, json=json_data)
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
# Scenario 0: Health & Config
# ---------------------------------------------------------------------------
async def test_health(client: httpx.AsyncClient) -> dict:
    print("\n" + "=" * 72)
    print("SCENARIO 0: HEALTH & CONFIG CHECK")
    print("=" * 72)

    health = await raw_get(client, "/health/")
    print(f"  Health: HTTP {health.get('_http_status')}")
    print(f"  Status: {health.get('status', 'N/A')}")

    config = await api_call(client, "GET", "/config")
    print(f"  Config: HTTP {config.get('_http_status')}")
    networks = config.get("supported_networks", [])
    preferred = config.get("preferred_network", "N/A")
    print(f"  Networks: {networks}")
    print(f"  Preferred: {preferred}")

    payment_mode = "unknown"
    components = health.get("components", {})
    x402_info = components.get("x402", {})
    if isinstance(x402_info, dict):
        payment_mode = x402_info.get("mode", "unknown")
    print(f"  Payment mode: {payment_mode}")

    ok = health.get("_http_status") == 200 and config.get("_http_status") == 200
    results.add(
        "health_check",
        "API health and config verification",
        {
            "status": "SUCCESS" if ok else "FAILED",
            "payment_mode": payment_mode,
            "networks": networks,
        },
    )
    return config


# ---------------------------------------------------------------------------
# Scenario 1: Happy Path — Fee Split Verification
# ---------------------------------------------------------------------------
async def test_happy_path(
    client: httpx.AsyncClient,
    executor_id: str,
    bounty: float,
) -> Optional[str]:
    fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
    total = bounty + fee

    print("\n" + "=" * 72)
    print("SCENARIO 1: HAPPY PATH — FEE SPLIT VERIFICATION")
    print(f"  API:      {API_BASE}")
    print(f"  Bounty:   ${bounty:.2f} USDC")
    print(f"  Fee:      ${fee:.6f} USDC (13%)")
    print(f"  Total:    ${total:.6f} USDC (locked in escrow)")
    print(f"  Worker:   {TEST_WORKER_ADDRESS}")
    print(f"  Treasury: {TREASURY_ADDRESS}")
    print("=" * 72)

    # -- Step 1: Create task -------------------------------------------
    print("\n  [1/5] Creating task...")
    t0 = time.time()
    task_data = await api_call(
        client,
        "POST",
        "/tasks",
        {
            "title": f"E2E Fee Split Test {ts_short()}",
            "instructions": (
                "Take a photo of any nearby object. "
                "Automated E2E full lifecycle test — fee split verification."
            ),
            "category": "physical_presence",
            "bounty_usd": bounty,
            "deadline_hours": 1,
            "evidence_required": ["photo"],
            "location_hint": "Any location",
            "payment_network": "base",
            "payment_token": "USDC",
        },
    )
    t_create = time.time() - t0

    if task_data.get("_http_status") != 201:
        err = task_data.get("detail", task_data.get("error", str(task_data)[:200]))
        results.add(
            "happy_path",
            "Full lifecycle fee split",
            {
                "status": "FAILED",
                "error": f"Task creation failed: HTTP {task_data.get('_http_status')} - {err}",
            },
        )
        return None

    task_id = task_data.get("id")
    escrow_tx = task_data.get("escrow_tx")
    print(f"         Task ID:    {task_id}")
    print(f"         Status:     {task_data.get('status')}")
    print(f"         Created in: {t_create:.2f}s")
    if escrow_tx:
        print(f"         Escrow TX:  {escrow_tx}")
        print(f"         BaseScan:   {BASESCAN_TX}/{escrow_tx}")
    else:
        print("         Escrow:     N/A (Fase 1 balance-check only)")

    # -- Step 2: Worker applies ----------------------------------------
    print("\n  [2/5] Worker applying to task...")
    apply_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/apply",
        {
            "executor_id": executor_id,
            "message": "E2E fee split test — ready to work",
        },
    )
    print(f"         Apply: HTTP {apply_data.get('_http_status')}")

    if apply_data.get("_http_status") not in (200, 201):
        results.add(
            "happy_path",
            "Full lifecycle fee split",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Apply failed: {apply_data.get('detail', '')}",
            },
        )
        return task_id

    # -- Step 3: Agent assigns worker ----------------------------------
    print("\n  [3/5] Agent assigning worker...")
    assign_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/assign",
        {
            "executor_id": executor_id,
            "notes": "E2E fee split test assignment",
        },
    )
    print(f"         Assign: HTTP {assign_data.get('_http_status')}")

    if assign_data.get("_http_status") not in (200, 201):
        results.add(
            "happy_path",
            "Full lifecycle fee split",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Assign failed: {assign_data.get('detail', '')}",
            },
        )
        return task_id

    # -- Step 4: Worker submits evidence -------------------------------
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
            "notes": "Automated E2E full lifecycle submission",
        },
    )
    print(f"         Submit: HTTP {submit_data.get('_http_status')}")

    if submit_data.get("_http_status") not in (200, 201):
        results.add(
            "happy_path",
            "Full lifecycle fee split",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Submit failed: {submit_data.get('detail', str(submit_data)[:200])}",
            },
        )
        return task_id

    # Find submission ID
    submission_id = (submit_data.get("data") or {}).get("submission_id")
    if not submission_id:
        subs_data = await api_call(client, "GET", f"/tasks/{task_id}/submissions")
        subs_list = subs_data.get("submissions") or subs_data.get("data") or []
        if isinstance(subs_list, list) and subs_list:
            submission_id = subs_list[0].get("id")

    if not submission_id:
        results.add(
            "happy_path",
            "Full lifecycle fee split",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": "Could not find submission ID after submit",
            },
        )
        return task_id

    print(f"         Submission: {submission_id}")

    # -- Step 5: Agent approves (triggers payment) ---------------------
    print("\n  [5/5] Agent approving (triggers payment settlement)...")
    t0 = time.time()
    approve_data = await api_call(
        client,
        "POST",
        f"/submissions/{submission_id}/approve",
        {
            "notes": "E2E fee split verification — approving for payment",
            "rating_score": 85,
        },
    )
    t_approve = time.time() - t0
    print(
        f"         Approve: HTTP {approve_data.get('_http_status')} ({t_approve:.2f}s)"
    )
    print(f"         Message: {approve_data.get('message', 'N/A')}")

    resp_data = approve_data.get("data") or {}

    # Extract all TX hashes from enhanced response
    payment_tx = resp_data.get("payment_tx")
    fee_tx = resp_data.get("fee_tx")
    escrow_release = resp_data.get("escrow_release_tx")
    payment_mode = resp_data.get("payment_mode", "unknown")
    platform_fee_actual = resp_data.get("platform_fee_usdc")
    worker_net_actual = resp_data.get("worker_net_usdc")
    gross_actual = resp_data.get("gross_amount_usdc")

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │              PAYMENT SETTLEMENT RESULTS                 │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print(f"  │  Mode:           {payment_mode:<40s}│")
    if escrow_release:
        print(f"  │  Escrow Release:  {escrow_release[:42]:<40s}│")
        print(f"  │    {BASESCAN_TX}/{escrow_release}")
    if payment_tx:
        print(f"  │  Worker TX:      {payment_tx[:42]:<40s}│")
        print(f"  │    {BASESCAN_TX}/{payment_tx}")
    if fee_tx:
        print(f"  │  Fee TX:         {fee_tx[:42]:<40s}│")
        print(f"  │    {BASESCAN_TX}/{fee_tx}")
    if worker_net_actual is not None:
        print(f"  │  Worker net:     ${worker_net_actual:.6f} USDC{' ':>23s}│")
    if platform_fee_actual is not None:
        print(f"  │  Platform fee:   ${platform_fee_actual:.6f} USDC{' ':>23s}│")
    if gross_actual is not None:
        print(f"  │  Gross:          ${gross_actual:.6f} USDC{' ':>23s}│")
    print("  └─────────────────────────────────────────────────────────┘")

    # Verify fee math
    fee_mismatch = None
    if platform_fee_actual is not None and worker_net_actual is not None:
        expected_fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
        if abs(platform_fee_actual - expected_fee) > 0.001:
            fee_mismatch = (
                f"Expected fee ${expected_fee:.6f} but got ${platform_fee_actual:.6f}"
            )
        if abs(worker_net_actual - bounty) > 0.001:
            fee_mismatch = (
                f"Expected worker net ${bounty:.6f} but got ${worker_net_actual:.6f}"
            )

    # Determine status
    has_all_txs = bool(payment_tx)
    if payment_mode == "fase2":
        has_all_txs = bool(payment_tx and fee_tx)
    elif payment_mode == "fase1":
        has_all_txs = bool(payment_tx and fee_tx)

    status = (
        "SUCCESS"
        if (approve_data.get("_http_status") == 200 and has_all_txs)
        else "FAILED"
    )
    if fee_mismatch:
        status = "PARTIAL"

    results.add(
        "happy_path",
        "Create → Apply → Assign → Submit → Approve (fee split)",
        {
            "status": status,
            "task_id": task_id,
            "submission_id": submission_id,
            "escrow_tx": escrow_tx,
            "escrow_release_tx": escrow_release,
            "payment_tx": payment_tx,
            "fee_tx": fee_tx,
            "payment_mode": payment_mode,
            "worker_net_usdc": worker_net_actual,
            "platform_fee_usdc": platform_fee_actual,
            "gross_amount_usdc": gross_actual,
            "expected_bounty": bounty,
            "expected_fee": float(Decimal(str(bounty)) * PLATFORM_FEE_PCT),
            "expected_total": float(Decimal(str(bounty)) * (1 + PLATFORM_FEE_PCT)),
            "fee_mismatch": fee_mismatch,
            "approve_time_s": round(t_approve, 2),
            "create_time_s": round(t_create, 2),
            "error": fee_mismatch if fee_mismatch else None,
        },
    )

    return task_id


# ---------------------------------------------------------------------------
# Scenario 2: Cancel Path
# ---------------------------------------------------------------------------
async def test_cancel_path(
    client: httpx.AsyncClient,
    bounty: float,
) -> Optional[str]:
    print("\n" + "=" * 72)
    print("SCENARIO 2: CANCEL PATH (Create → Cancel → Refund)")
    print(f"  Bounty: ${bounty:.2f}")
    print("=" * 72)

    print("\n  [1/2] Creating task for cancellation...")
    t0 = time.time()
    task_data = await api_call(
        client,
        "POST",
        "/tasks",
        {
            "title": f"E2E Cancel Path {ts_short()}",
            "instructions": (
                "This task will be cancelled immediately. "
                "Automated E2E test for cancel + refund flow."
            ),
            "category": "simple_action",
            "bounty_usd": bounty,
            "deadline_hours": 1,
            "evidence_required": ["text_response"],
            "payment_network": "base",
            "payment_token": "USDC",
        },
    )
    t_create = time.time() - t0

    if task_data.get("_http_status") != 201:
        err = task_data.get("detail", "")
        if isinstance(err, list):
            err = str(err)[:200]
        results.add(
            "cancel_path",
            "Cancel flow",
            {
                "status": "FAILED",
                "error": f"Task creation failed: HTTP {task_data.get('_http_status')} - {err}",
            },
        )
        return None

    task_id = task_data.get("id")
    escrow_tx = task_data.get("escrow_tx")
    print(f"         Task ID:    {task_id}")
    print(f"         Created in: {t_create:.2f}s")
    if escrow_tx:
        print(f"         Escrow TX:  {escrow_tx}")
        print(f"         BaseScan:   {BASESCAN_TX}/{escrow_tx}")

    print("\n  [2/2] Cancelling task...")
    t0 = time.time()
    cancel_data = await api_call(client, "POST", f"/tasks/{task_id}/cancel")
    t_cancel = time.time() - t0
    print(f"         Cancel: HTTP {cancel_data.get('_http_status')} ({t_cancel:.2f}s)")
    print(f"         Message: {cancel_data.get('message', 'N/A')}")

    resp_data = cancel_data.get("data") or {}
    refund_tx = resp_data.get("refund_tx")

    if refund_tx:
        print(f"         Refund TX:  {refund_tx}")
        print(f"         BaseScan:   {BASESCAN_TX}/{refund_tx}")

    status = "SUCCESS" if cancel_data.get("_http_status") == 200 else "FAILED"
    results.add(
        "cancel_path",
        "Create → Cancel (full refund to agent)",
        {
            "status": status,
            "task_id": task_id,
            "escrow_tx": escrow_tx,
            "refund_tx": refund_tx,
            "create_time_s": round(t_create, 2),
            "cancel_time_s": round(t_cancel, 2),
            "error": cancel_data.get("detail") if status == "FAILED" else None,
        },
    )
    return task_id


# ---------------------------------------------------------------------------
# Scenario 3: Rejection Path
# ---------------------------------------------------------------------------
async def test_rejection_path(
    client: httpx.AsyncClient,
    executor_id: str,
    bounty: float,
) -> Optional[str]:
    print("\n" + "=" * 72)
    print("SCENARIO 3: REJECTION PATH")
    print("  Create → Apply → Assign → Submit → Reject (no payment)")
    print(f"  Bounty: ${bounty:.2f}")
    print("=" * 72)

    print("\n  [1/5] Creating task for rejection...")
    task_data = await api_call(
        client,
        "POST",
        "/tasks",
        {
            "title": f"E2E Rejection Path {ts_short()}",
            "instructions": (
                "This submission will be rejected. "
                "Automated E2E test for rejection flow."
            ),
            "category": "knowledge_access",
            "bounty_usd": bounty,
            "deadline_hours": 1,
            "evidence_required": ["photo", "text_response"],
            "payment_network": "base",
            "payment_token": "USDC",
        },
    )

    if task_data.get("_http_status") != 201:
        err = task_data.get("detail", "")
        if isinstance(err, list):
            err = str(err)[:200]
        results.add(
            "rejection_path",
            "Rejection flow",
            {
                "status": "FAILED",
                "error": f"Task creation failed: HTTP {task_data.get('_http_status')} - {err}",
            },
        )
        return None

    task_id = task_data.get("id")
    escrow_tx = task_data.get("escrow_tx")
    print(f"         Task ID:  {task_id}")
    if escrow_tx:
        print(f"         Escrow TX: {escrow_tx}")

    # Apply
    print("\n  [2/5] Worker applying...")
    apply_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/apply",
        {"executor_id": executor_id, "message": "E2E rejection test"},
    )
    if apply_data.get("_http_status") not in (200, 201):
        results.add(
            "rejection_path",
            "Rejection flow",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Apply failed: {apply_data.get('detail', '')}",
            },
        )
        return task_id

    # Assign
    print("\n  [3/5] Agent assigning worker...")
    assign_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/assign",
        {"executor_id": executor_id, "notes": "Rejection test assignment"},
    )
    if assign_data.get("_http_status") not in (200, 201):
        results.add(
            "rejection_path",
            "Rejection flow",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Assign failed: {assign_data.get('detail', '')}",
            },
        )
        return task_id

    # Submit
    print("\n  [4/5] Worker submitting evidence...")
    submit_data = await api_call(
        client,
        "POST",
        f"/tasks/{task_id}/submit",
        {
            "executor_id": executor_id,
            "evidence": {
                "photo": ["https://cdn.execution.market/evidence/e2e-blurry.jpg"],
                "text_response": "Incomplete — E2E rejection test.",
            },
            "notes": "Low-quality submission for E2E rejection test",
        },
    )
    if submit_data.get("_http_status") not in (200, 201):
        results.add(
            "rejection_path",
            "Rejection flow",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Submit failed: {submit_data.get('detail', '')}",
            },
        )
        return task_id

    submission_id = (submit_data.get("data") or {}).get("submission_id")
    if not submission_id:
        subs_data = await api_call(client, "GET", f"/tasks/{task_id}/submissions")
        subs_list = subs_data.get("submissions") or subs_data.get("data") or []
        if isinstance(subs_list, list) and subs_list:
            submission_id = subs_list[0].get("id")

    if not submission_id:
        results.add(
            "rejection_path",
            "Rejection flow",
            {
                "status": "FAILED",
                "task_id": task_id,
                "error": "Could not find submission ID",
            },
        )
        return task_id

    print(f"         Submission: {submission_id}")

    # Reject
    print("\n  [5/5] Agent rejecting with major severity...")
    reject_data = await api_call(
        client,
        "POST",
        f"/submissions/{submission_id}/reject",
        {
            "notes": "E2E test rejection — evidence incomplete",
            "severity": "major",
            "reputation_score": 30,
        },
    )
    print(f"         Reject: HTTP {reject_data.get('_http_status')}")
    print(f"         Message: {reject_data.get('message', 'N/A')}")

    status = "SUCCESS" if reject_data.get("_http_status") == 200 else "FAILED"
    results.add(
        "rejection_path",
        "Create → Apply → Assign → Submit → Reject (no payment, score=30)",
        {
            "status": status,
            "task_id": task_id,
            "submission_id": submission_id,
            "escrow_tx": escrow_tx,
            "error": reject_data.get("detail") if status == "FAILED" else None,
        },
    )
    return task_id


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(results_obj: TestResult, bounty: float) -> str:
    fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
    total = bounty + fee
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# E2E Full Lifecycle Report — Fee Split Verification",
        "",
        f"> Generated: {now}",
        f"> API: `{API_BASE}`",
        f"> Bounty: ${bounty:.2f} USDC | Fee: ${fee:.6f} (13%) | Total: ${total:.6f}",
        f"> Worker: `{TEST_WORKER_ADDRESS}`",
        f"> Treasury: `{TREASURY_ADDRESS}`",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| # | Scenario | Status | Key TX |",
        "|---|----------|--------|--------|",
    ]

    for i, s in enumerate(results_obj.scenarios, 1):
        status = s.get("status", "UNKNOWN")
        icon = (
            "PASS"
            if status == "SUCCESS"
            else "FAIL"
            if status == "FAILED"
            else "PARTIAL"
        )
        tx_link = ""
        for tx_key in (
            "payment_tx",
            "fee_tx",
            "escrow_release_tx",
            "refund_tx",
            "escrow_tx",
        ):
            tx = s.get(tx_key)
            if tx:
                tx_link = f"[`{tx[:12]}...`]({BASESCAN_TX}/{tx})"
                break
        if not tx_link and s.get("error"):
            tx_link = str(s["error"])[:60]

        lines.append(f"| {i} | {s['description'][:55]} | {icon} | {tx_link} |")

    lines.extend(["", "---", ""])

    # Detailed scenario sections
    for s in results_obj.scenarios:
        lines.append(f"## {s['name']}")
        lines.append("")
        lines.append(f"**{s['description']}**")
        lines.append("")
        lines.append(f"- **Status**: {s.get('status')}")
        lines.append(f"- **Timestamp**: {s.get('timestamp')}")

        if s.get("task_id"):
            lines.append(f"- **Task ID**: `{s['task_id']}`")
        if s.get("submission_id"):
            lines.append(f"- **Submission ID**: `{s['submission_id']}`")
        if s.get("payment_mode"):
            lines.append(f"- **Payment mode**: `{s['payment_mode']}`")

        # TX table for happy path
        txs = []
        if s.get("escrow_tx"):
            txs.append(("Escrow Lock", s["escrow_tx"], f"${total:.6f}"))
        if s.get("escrow_release_tx"):
            txs.append(("Escrow Release", s["escrow_release_tx"], f"${total:.6f}"))
        if s.get("payment_tx"):
            amt = (
                f"${s.get('worker_net_usdc', bounty):.6f}"
                if s.get("worker_net_usdc")
                else f"${bounty:.2f}"
            )
            txs.append(("Worker Disbursement", s["payment_tx"], amt))
        if s.get("fee_tx"):
            amt = (
                f"${s.get('platform_fee_usdc', fee):.6f}"
                if s.get("platform_fee_usdc")
                else f"${fee:.6f}"
            )
            txs.append(("Fee Collection", s["fee_tx"], amt))
        if s.get("refund_tx"):
            txs.append(("Refund", s["refund_tx"], f"${total:.6f}"))

        if txs:
            lines.append("")
            lines.append("| Step | TX Hash | Amount | BaseScan |")
            lines.append("|------|---------|--------|----------|")
            for label, tx, amount in txs:
                lines.append(
                    f"| {label} | `{tx[:16]}...` | {amount} | "
                    f"[View]({BASESCAN_TX}/{tx}) |"
                )

        # Fee verification
        if (
            s.get("worker_net_usdc") is not None
            and s.get("platform_fee_usdc") is not None
        ):
            lines.append("")
            lines.append("### Fee Verification")
            lines.append("")
            lines.append("| Metric | Expected | Actual | Match |")
            lines.append("|--------|----------|--------|-------|")
            exp_worker = bounty
            act_worker = s["worker_net_usdc"]
            w_ok = "YES" if abs(act_worker - exp_worker) < 0.001 else "NO"
            lines.append(
                f"| Worker net | ${exp_worker:.6f} | ${act_worker:.6f} | {w_ok} |"
            )

            exp_fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
            act_fee = s["platform_fee_usdc"]
            f_ok = "YES" if abs(act_fee - exp_fee) < 0.001 else "NO"
            lines.append(f"| Platform fee | ${exp_fee:.6f} | ${act_fee:.6f} | {f_ok} |")

            if s.get("gross_amount_usdc"):
                exp_gross = bounty + exp_fee
                act_gross = s["gross_amount_usdc"]
                g_ok = "YES" if abs(act_gross - exp_gross) < 0.001 else "NO"
                lines.append(
                    f"| Gross amount | ${exp_gross:.6f} | ${act_gross:.6f} | {g_ok} |"
                )

        if s.get("fee_mismatch"):
            lines.append(f"\n> **WARNING**: Fee mismatch — {s['fee_mismatch']}")

        if s.get("error"):
            lines.append(f"\n> **Error**: {s['error']}")

        # Timing
        timing_parts = []
        if s.get("create_time_s"):
            timing_parts.append(f"Create: {s['create_time_s']}s")
        if s.get("approve_time_s"):
            timing_parts.append(f"Approve: {s['approve_time_s']}s")
        if s.get("cancel_time_s"):
            timing_parts.append(f"Cancel: {s['cancel_time_s']}s")
        if timing_parts:
            lines.append(f"\n**Timing**: {' | '.join(timing_parts)}")

        lines.append("")

    # Invariants section
    lines.extend(
        [
            "---",
            "",
            "## Invariants Verified",
            "",
        ]
    )

    happy = next((s for s in results_obj.scenarios if s["name"] == "happy_path"), None)
    cancel = next(
        (s for s in results_obj.scenarios if s["name"] == "cancel_path"), None
    )

    checks = []
    if happy and happy.get("status") == "SUCCESS":
        if happy.get("payment_tx") and happy.get("fee_tx"):
            checks.append("Worker TX and Fee TX are distinct on-chain transactions")
        if happy.get("worker_net_usdc") is not None:
            if abs(happy["worker_net_usdc"] - bounty) < 0.001:
                checks.append(f"Worker receives exactly ${bounty:.2f} (100% of bounty)")
        if happy.get("platform_fee_usdc") is not None:
            checks.append(
                f"Treasury receives ${happy['platform_fee_usdc']:.6f} (13% platform fee)"
            )
    if cancel and cancel.get("status") == "SUCCESS":
        if cancel.get("refund_tx"):
            checks.append("Cancel returns 100% of locked funds to agent")

    if checks:
        for c in checks:
            lines.append(f"- [x] {c}")
    else:
        lines.append("- [ ] No invariants could be verified (tests may have failed)")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> int:
    bounty = DEFAULT_BOUNTY
    dry_run = "--dry-run" in sys.argv
    happy_only = "--happy-only" in sys.argv

    # Parse --bounty
    for i, arg in enumerate(sys.argv):
        if arg == "--bounty" and i + 1 < len(sys.argv):
            try:
                bounty = float(sys.argv[i + 1])
            except ValueError:
                print(f"Invalid bounty: {sys.argv[i + 1]}")
                return 1

    fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
    total = bounty + fee

    print("=" * 72)
    print("E2E FULL LIFECYCLE TEST — FEE SPLIT VERIFICATION")
    print("=" * 72)
    print(f"  API:       {API_BASE}")
    print(f"  Time:      {ts()}")
    print(f"  Bounty:    ${bounty:.2f} USDC")
    print(f"  Fee (13%): ${fee:.6f} USDC")
    print(f"  Total:     ${total:.6f} USDC")
    print(f"  Worker:    {TEST_WORKER_ADDRESS}")
    print(f"  Treasury:  {TREASURY_ADDRESS}")
    print(f"  Executor:  {TEST_EXECUTOR_ID}")
    print(f"  Dry run:   {dry_run}")
    print(f"  Happy only:{happy_only}")

    if dry_run:
        print("\nDRY RUN — configuration shown above. Remove --dry-run to execute.")
        return 0

    timeout = httpx.Timeout(180.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        await test_health(client)

        # Run lighter scenarios first, then the heavy happy path
        if not happy_only:
            await test_cancel_path(client, bounty)
            await asyncio.sleep(5)
            await test_rejection_path(client, TEST_EXECUTOR_ID, bounty)
            await asyncio.sleep(5)

        await test_happy_path(client, TEST_EXECUTOR_ID, bounty)

    # Generate and save reports
    report_dir = Path(__file__).parent.parent / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_md = generate_report(results, bounty)
    md_path = report_dir / "E2E_FULL_LIFECYCLE_REPORT.md"
    md_path.write_text(report_md, encoding="utf-8")
    print(f"\nReport:  {md_path}")

    json_path = report_dir / "E2E_FULL_LIFECYCLE_REPORT.json"
    json_path.write_text(
        json.dumps({"scenarios": results.scenarios}, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"JSON:    {json_path}")

    # Summary
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    total_tests = len(results.scenarios)
    print(
        f"  Total: {total_tests} | "
        f"Passed: {results.passed} | "
        f"Failed: {results.failed} | "
        f"Partial: {total_tests - results.passed - results.failed}"
    )

    # Highlight the fee split result
    happy = next((s for s in results.scenarios if s["name"] == "happy_path"), None)
    if happy:
        print()
        if happy.get("payment_tx") and happy.get("fee_tx"):
            print("  FEE SPLIT VERIFIED:")
            print(f"    Worker TX:  {happy['payment_tx']}")
            print(f"    Fee TX:     {happy['fee_tx']}")
            if happy.get("worker_net_usdc") is not None:
                print(f"    Worker:     ${happy['worker_net_usdc']:.6f} USDC")
            if happy.get("platform_fee_usdc") is not None:
                print(f"    Fee:        ${happy['platform_fee_usdc']:.6f} USDC")
        elif happy.get("payment_tx"):
            print("  PARTIAL: Worker paid but fee TX not captured")
            print(f"    Worker TX:  {happy['payment_tx']}")
        else:
            print("  FAILED: No payment TX captured")

    return 0 if results.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
