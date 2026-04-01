#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Refund Flow -- E2E test for task cancellation and escrow refund.

Tests 3 refund scenarios on Base Mainnet:
  1. Cancel a published task (no escrow locked yet) → no-op refund
  2. Cancel an accepted task (escrow locked at assignment) → on-chain refund
  3. Cancel an already-cancelled task → idempotent success

Uses the same infra as the Golden Flow script.

Usage:
    python scripts/e2e_refund_flow.py
    python scripts/e2e_refund_flow.py --dry-run
    python scripts/e2e_refund_flow.py --bounty 0.05

Environment:
    EM_API_KEY           -- Agent API key (optional when EM_REQUIRE_API_KEY=false)
    EM_API_URL           -- API base URL (default: https://api.execution.market)
    EM_WORKER_WALLET     -- Worker wallet (default: 0x4aa8...)
    EM_TEST_EXECUTOR_ID  -- Existing executor UUID (skips registration if set)

Cost: ~$0.10 per run (1 escrow lock + refund; the other cancel is free).
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

# Blockchain
BASE_RPC = "https://mainnet.base.org"
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASESCAN_TX = "https://basescan.org/tx"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

DEFAULT_BOUNTY = 0.10
PLATFORM_FEE_PCT = Decimal("0.13")


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

    def partial(self, error: str, **kwargs: Any) -> "PhaseResult":
        self.status = "PARTIAL"
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
        if self.status == "PARTIAL":
            icon = "PARTIAL"
        print(f"  [{icon}] Phase: {self.description} ({self.elapsed_s}s)")
        if self.error:
            print(f"         Error: {self.error}")


class FlowResults:
    def __init__(self):
        self.phases: Dict[str, PhaseResult] = {}
        self.tx_hashes: List[str] = []
        self.start_time = time.time()

    def add(self, result: PhaseResult) -> None:
        self.phases[result.name] = result
        result.print_result()

    def add_tx(self, tx_hash: str) -> None:
        if tx_hash and tx_hash not in self.tx_hashes:
            self.tx_hashes.append(tx_hash)

    @property
    def all_passed(self) -> bool:
        return all(p.status == "PASS" for p in self.phases.values())

    @property
    def pass_count(self) -> int:
        return sum(1 for p in self.phases.values() if p.status == "PASS")

    @property
    def fail_count(self) -> int:
        return sum(1 for p in self.phases.values() if p.status == "FAIL")

    @property
    def overall(self) -> str:
        if self.all_passed:
            return "PASS"
        if self.fail_count == 0:
            return "PARTIAL"
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
    extra_headers: Optional[Dict[str, str]] = None,
) -> dict:
    url = f"{API_BASE}/api/v1{path}"
    headers = _auth_headers()
    if extra_headers:
        headers.update(extra_headers)
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
# On-chain TX verification
# ---------------------------------------------------------------------------
async def verify_tx_onchain(client: httpx.AsyncClient, tx_hash: str) -> Dict[str, Any]:
    try:
        resp = await client.post(
            BASE_RPC,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
            },
            timeout=30.0,
        )
        result = resp.json().get("result")
        if not result:
            return {"success": False, "error": "No receipt returned"}

        status_hex = result.get("status", "0x0")
        success = status_hex == "0x1"
        gas_used = int(result.get("gasUsed", "0x0"), 16)

        transfers = []
        for log in result.get("logs", []):
            topics = log.get("topics", [])
            if (
                len(topics) >= 3
                and topics[0].lower() == TRANSFER_TOPIC.lower()
                and log.get("address", "").lower() == USDC_CONTRACT.lower()
            ):
                from_addr = "0x" + topics[1][-40:]
                to_addr = "0x" + topics[2][-40:]
                raw_amount = int(log.get("data", "0x0"), 16)
                usdc_amount = raw_amount / 1e6
                transfers.append(
                    {
                        "from": from_addr,
                        "to": to_addr,
                        "amount_usdc": usdc_amount,
                    }
                )

        return {
            "success": success,
            "gas_used": gas_used,
            "transfers": transfers,
            "transfer_count": len(transfers),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------
async def phase_health(client: httpx.AsyncClient, results: FlowResults) -> PhaseResult:
    phase = PhaseResult("health", "API Health Check")
    _print_header("PHASE 1: HEALTH CHECK")

    try:
        data = await raw_get(client, "/health")
        if data.get("_http_status") != 200:
            return phase.fail(f"Health check returned {data.get('_http_status')}")
        _print_kv("Status", data.get("status", "?"))
        return phase.pass_()
    except Exception as e:
        return phase.fail(f"Health check failed: {e}")


async def phase_create_task(
    client: httpx.AsyncClient, results: FlowResults, bounty: float, label: str
) -> PhaseResult:
    """Create a task. Returns phase with task_id in details."""
    phase = PhaseResult(f"create_{label}", f"Create task ({label})")
    _print_header(f"CREATE TASK ({label.upper()})")

    try:
        task_data = {
            "title": f"[E2E Refund {label}] {ts()}",
            "description": f"Test task for refund flow ({label}). Auto-created by e2e_refund_flow.py.",
            "bounty_usd": bounty,
            "category": "simple_action",
            "deadline_minutes": 10,
            "evidence_requirements": [{"type": "photo", "description": "Any photo"}],
        }
        data = await api_call(client, "POST", "/tasks", task_data)
        status = data.get("_http_status")
        if status not in (200, 201):
            return phase.fail(
                f"Task creation failed: HTTP {status} — {data.get('detail', data)}"
            )

        task_id = data.get("id") or (data.get("data", {}) or {}).get("id")
        if not task_id:
            return phase.fail(f"No task_id in response: {data}")

        _print_kv("Task ID", task_id)
        _print_kv("Bounty", f"${bounty}")
        return phase.pass_(task_id=task_id)
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


async def phase_register_worker(
    client: httpx.AsyncClient, results: FlowResults
) -> PhaseResult:
    """Register or reuse a worker."""
    phase = PhaseResult("register_worker", "Register/Reuse Worker")
    _print_header("REGISTER WORKER")

    if EXISTING_EXECUTOR_ID:
        _print_kv("Using existing executor", EXISTING_EXECUTOR_ID)
        return phase.pass_(executor_id=EXISTING_EXECUTOR_ID)

    try:
        worker_data = {
            "wallet_address": WORKER_WALLET,
            "name": "E2E Refund Worker",
        }
        data = await api_call(client, "POST", "/workers/register", worker_data)
        status = data.get("_http_status")
        if status not in (200, 201):
            return phase.fail(f"Worker registration failed: HTTP {status} — {data}")

        executor_id = (
            data.get("executor_id")
            or (data.get("data", {}) or {}).get("id")
            or (data.get("data", {}) or {}).get("executor_id")
        )
        if not executor_id:
            return phase.fail(f"No executor_id in response: {data}")

        _print_kv("Executor ID", executor_id)
        return phase.pass_(executor_id=executor_id)
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


async def phase_apply_and_assign(
    client: httpx.AsyncClient, results: FlowResults, task_id: str, executor_id: str
) -> PhaseResult:
    """Apply worker to task, then assign (triggers escrow lock in direct_release)."""
    phase = PhaseResult("apply_assign", "Apply + Assign (escrow lock)")
    _print_header("APPLY + ASSIGN")

    try:
        # Apply
        apply_data = {"executor_id": executor_id, "message": "E2E refund test"}
        data = await api_call(client, "POST", f"/tasks/{task_id}/apply", apply_data)
        if data.get("_http_status") not in (200, 201):
            return phase.fail(f"Apply failed: HTTP {data.get('_http_status')} — {data}")
        _print_kv("Applied", "OK")

        await asyncio.sleep(2)

        # Assign
        assign_data = {"executor_id": executor_id}
        data = await api_call(client, "POST", f"/tasks/{task_id}/assign", assign_data)
        if data.get("_http_status") not in (200, 201):
            return phase.fail(
                f"Assign failed: HTTP {data.get('_http_status')} — {data}"
            )

        escrow_info = data.get("data", {}).get("escrow") or data.get("escrow") or {}
        escrow_tx = escrow_info.get("tx_hash") or escrow_info.get("escrow_tx_hash")
        _print_kv("Assigned", "OK")
        _print_kv("Escrow TX", escrow_tx or "(no TX — may be balance check only)")

        if escrow_tx:
            results.add_tx(escrow_tx)

        return phase.pass_(escrow_tx=escrow_tx)
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


async def phase_cancel_published(
    client: httpx.AsyncClient, results: FlowResults, task_id: str
) -> PhaseResult:
    """Cancel a published task (no escrow locked yet) — should be a no-op refund."""
    phase = PhaseResult("cancel_published", "Cancel published task (no escrow)")
    _print_header("SCENARIO 1: CANCEL PUBLISHED (NO ESCROW)")

    try:
        data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/cancel",
            {"reason": "E2E test: cancel before assign"},
        )
        status = data.get("_http_status")
        if status not in (200, 201):
            return phase.fail(f"Cancel failed: HTTP {status} — {data}")

        _print_kv("Response", data.get("message", "?"))
        escrow = (data.get("data", {}) or {}).get("escrow") or {}
        _print_kv("Escrow status", escrow.get("status", "n/a"))
        _print_kv("TX hash", escrow.get("tx_hash", "none (expected)"))

        return phase.pass_(
            escrow_status=escrow.get("status"),
            tx_hash=escrow.get("tx_hash"),
        )
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


async def phase_cancel_accepted(
    client: httpx.AsyncClient, results: FlowResults, task_id: str
) -> PhaseResult:
    """Cancel an accepted task (escrow locked) — should trigger on-chain refund."""
    phase = PhaseResult("cancel_accepted", "Cancel accepted task (escrow refund)")
    _print_header("SCENARIO 2: CANCEL ACCEPTED (ESCROW REFUND)")

    try:
        data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/cancel",
            {"reason": "E2E test: cancel after assign"},
        )
        status = data.get("_http_status")
        if status not in (200, 201):
            return phase.fail(f"Cancel failed: HTTP {status} — {data}")

        _print_kv("Response", data.get("message", "?"))
        escrow = (data.get("data", {}) or {}).get("escrow") or {}
        refund_tx = escrow.get("tx_hash")
        escrow_status = escrow.get("status")
        _print_kv("Escrow status", escrow_status or "?")
        _print_kv("Refund TX", refund_tx or "none")

        if refund_tx:
            results.add_tx(refund_tx)

        return phase.pass_(
            escrow_status=escrow_status,
            refund_tx=refund_tx,
        )
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


async def phase_cancel_idempotent(
    client: httpx.AsyncClient, results: FlowResults, task_id: str
) -> PhaseResult:
    """Cancel an already-cancelled task — should return idempotent success."""
    phase = PhaseResult(
        "cancel_idempotent", "Cancel already-cancelled task (idempotent)"
    )
    _print_header("SCENARIO 3: CANCEL ALREADY-CANCELLED (IDEMPOTENT)")

    try:
        data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/cancel",
            {"reason": "E2E test: idempotent cancel"},
        )
        status = data.get("_http_status")
        _print_kv("HTTP status", status)
        _print_kv("Response", data.get("message", data.get("detail", "?")))

        # Accept both 200 (idempotent success) and 409 (already cancelled)
        if status in (200, 201, 409):
            return phase.pass_(http_status=status)
        else:
            return phase.fail(f"Unexpected status: {status}")
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


async def phase_verify_refund_tx(
    client: httpx.AsyncClient, results: FlowResults, tx_hash: Optional[str]
) -> PhaseResult:
    """Verify the refund TX on-chain."""
    phase = PhaseResult("verify_refund", "Verify refund TX on-chain")
    _print_header("VERIFY REFUND TX ON-CHAIN")

    if not tx_hash:
        _print_kv("Skip", "No refund TX to verify (may be direct_release with no lock)")
        return phase.partial(
            "No refund TX hash available — skipping on-chain verification"
        )

    try:
        tx_info = await verify_tx_onchain(client, tx_hash)
        _print_kv("TX success", tx_info.get("success"))
        _print_kv("Gas used", tx_info.get("gas_used"))
        _print_kv("Transfers", tx_info.get("transfer_count", 0))

        for i, t in enumerate(tx_info.get("transfers", [])):
            _print_kv(
                f"  Transfer {i + 1}",
                f"${t['amount_usdc']:.6f} {t['from'][:10]}... -> {t['to'][:10]}...",
            )

        if not tx_info.get("success"):
            return phase.fail(f"TX reverted: {tx_info.get('error', 'unknown')}")

        _print_kv("Explorer", f"{BASESCAN_TX}/{tx_hash}")
        return phase.pass_(
            gas_used=tx_info.get("gas_used"),
            transfers=tx_info.get("transfers"),
            explorer_url=f"{BASESCAN_TX}/{tx_hash}",
        )
    except Exception as e:
        return phase.fail(f"Verification failed: {e}")


async def phase_verify_task_status(
    client: httpx.AsyncClient, results: FlowResults, task_id: str, expected_status: str
) -> PhaseResult:
    """Verify the task has the expected status after cancellation."""
    phase = PhaseResult(
        f"verify_status_{expected_status}", f"Verify task status = {expected_status}"
    )
    _print_header(f"VERIFY TASK STATUS = {expected_status.upper()}")

    try:
        data = await api_call(client, "GET", f"/tasks/{task_id}")
        if data.get("_http_status") != 200:
            return phase.fail(f"GET task failed: HTTP {data.get('_http_status')}")

        actual_status = data.get("status")
        _print_kv("Task ID", task_id)
        _print_kv("Expected status", expected_status)
        _print_kv("Actual status", actual_status)

        if actual_status == expected_status:
            return phase.pass_(actual_status=actual_status)
        else:
            return phase.fail(f"Expected '{expected_status}', got '{actual_status}'")
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


async def phase_check_transactions_endpoint(
    client: httpx.AsyncClient, results: FlowResults, task_id: str
) -> PhaseResult:
    """Verify the /tasks/{task_id}/transactions endpoint shows refund events."""
    phase = PhaseResult("check_transactions", "Check /transactions endpoint")
    _print_header("CHECK TRANSACTIONS ENDPOINT")

    try:
        data = await api_call(client, "GET", f"/tasks/{task_id}/transactions")
        if data.get("_http_status") != 200:
            return phase.fail(
                f"GET transactions failed: HTTP {data.get('_http_status')}"
            )

        txns = data.get("transactions", [])
        summary = data.get("summary", {})
        _print_kv("Transaction count", len(txns))
        _print_kv("Total locked", summary.get("total_locked"))
        _print_kv("Total refunded", summary.get("total_refunded"))

        for t in txns:
            _print_kv(
                f"  [{t.get('status', '?')}]",
                f"{t.get('event_type', '?')} — ${t.get('amount_usdc', 0) or 0:.6f}",
            )

        return phase.pass_(
            transaction_count=len(txns),
            summary=summary,
        )
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
async def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Refund Flow E2E Test")
    parser.add_argument("--bounty", type=float, default=DEFAULT_BOUNTY)
    parser.add_argument("--dry-run", action="store_true", help="Config check only")
    args = parser.parse_args()

    _print_header("REFUND FLOW E2E TEST")
    print(f"  API:    {API_BASE}")
    print(f"  Bounty: ${args.bounty}")
    print(f"  Worker: {WORKER_WALLET}")
    print(f"  Time:   {ts()}")

    if args.dry_run:
        print("\n  [DRY RUN] Config looks good. Exiting.")
        return 0

    results = FlowResults()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Phase 1: Health check
        r = phase_health(client, results)
        results.add(await r)
        if results.phases["health"].status != "PASS":
            print("\n  [ABORT] API not reachable.")
            return 1

        # Phase 2: Register worker (needed for scenario 2)
        r = await phase_register_worker(client, results)
        results.add(r)
        executor_id = r.details.get("executor_id")
        if not executor_id:
            print("\n  [ABORT] No executor ID.")
            return 1

        await asyncio.sleep(1)

        # =====================================================================
        # SCENARIO 1: Cancel a published task (no escrow)
        # =====================================================================
        r = await phase_create_task(client, results, args.bounty, "published")
        results.add(r)
        task1_id = r.details.get("task_id")
        if not task1_id:
            print("\n  [ABORT] Task creation failed for scenario 1.")
            return 1

        await asyncio.sleep(2)

        # Cancel immediately (still published)
        r = await phase_cancel_published(client, results, task1_id)
        results.add(r)

        # Verify status is cancelled
        await asyncio.sleep(1)
        r = await phase_verify_task_status(client, results, task1_id, "cancelled")
        results.add(r)

        await asyncio.sleep(2)

        # =====================================================================
        # SCENARIO 2: Cancel an accepted task (escrow locked)
        # =====================================================================
        r = await phase_create_task(client, results, args.bounty, "accepted")
        results.add(r)
        task2_id = r.details.get("task_id")
        if not task2_id:
            print("\n  [ABORT] Task creation failed for scenario 2.")
            return 1

        await asyncio.sleep(2)

        # Apply + Assign (triggers escrow lock)
        r = await phase_apply_and_assign(client, results, task2_id, executor_id)
        results.add(r)
        if r.status != "PASS":
            print("\n  [WARN] Apply/assign failed — skipping escrow cancel scenario.")
        else:
            await asyncio.sleep(3)

            # Cancel accepted task (triggers refund)
            r = await phase_cancel_accepted(client, results, task2_id)
            results.add(r)
            refund_tx = r.details.get("refund_tx")

            await asyncio.sleep(2)

            # Verify refund TX on-chain
            r = await phase_verify_refund_tx(client, results, refund_tx)
            results.add(r)

            # Verify task status
            r = await phase_verify_task_status(client, results, task2_id, "cancelled")
            results.add(r)

            await asyncio.sleep(2)

            # =====================================================================
            # SCENARIO 3: Cancel already-cancelled task (idempotent)
            # =====================================================================
            r = await phase_cancel_idempotent(client, results, task2_id)
            results.add(r)

        # Check transactions endpoint for task 2
        await asyncio.sleep(1)
        r = await phase_check_transactions_endpoint(client, results, task2_id)
        results.add(r)

    # =========================================================================
    # Summary
    # =========================================================================
    _print_header("REFUND FLOW RESULTS")
    for name, phase in results.phases.items():
        icon = _icon(phase.status == "PASS")
        if phase.status == "PARTIAL":
            icon = "PARTIAL"
        print(f"  [{icon}] {phase.description}")
        if phase.error:
            print(f"         {phase.error}")

    print(f"\n  Overall: {results.overall}")
    print(f"  Passed: {results.pass_count}/{len(results.phases)}")
    print(f"  Elapsed: {round(time.time() - results.start_time, 1)}s")
    if results.tx_hashes:
        print("  TX hashes:")
        for tx in results.tx_hashes:
            print(f"    {BASESCAN_TX}/{tx}")

    # Save JSON report
    report_path = _project_root / "docs" / "reports" / "REFUND_FLOW_REPORT.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "test": "refund_flow",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_base": API_BASE,
        "bounty_usd": args.bounty,
        "overall": results.overall,
        "pass_count": results.pass_count,
        "total_phases": len(results.phases),
        "phases": {k: v.to_dict() for k, v in results.phases.items()},
        "tx_hashes": results.tx_hashes,
        "elapsed_s": round(time.time() - results.start_time, 2),
    }
    report_path.write_text(json.dumps(report_data, indent=2, default=str))
    print(f"\n  Report: {report_path}")

    return 0 if results.all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
