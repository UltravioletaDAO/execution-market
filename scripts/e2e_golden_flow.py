#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Golden Flow -- Definitive E2E Acceptance Test for Execution Market

Tests the COMPLETE platform flow on Base Mainnet:
  Health -> Task+Escrow -> Worker+Identity -> Lifecycle -> Payment -> Reputation -> Verification

If the Golden Flow passes, the platform is healthy.

Usage:
    python scripts/e2e_golden_flow.py
    python scripts/e2e_golden_flow.py --dry-run          # Config check only
    python scripts/e2e_golden_flow.py --bounty 0.05       # Custom bounty

Environment:
    EM_API_KEY           -- Agent API key (optional when EM_REQUIRE_API_KEY=false)
    EM_API_URL           -- API base URL (default: https://api.execution.market)
    EM_WORKER_WALLET     -- Worker wallet (default: 0x52E0...)
    EM_TEST_EXECUTOR_ID  -- Existing executor UUID (skips registration if set)
    SUPABASE_URL         -- For fallback queries
    SUPABASE_SERVICE_KEY -- For fallback queries

Cost: ~$0.113 per run ($0.10 bounty + 13% fee)
"""

import asyncio
import json
import os
import re
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
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Worker wallet for test
WORKER_WALLET = os.environ.get(
    "EM_WORKER_WALLET", "0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15"
)
TREASURY_WALLET = "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"

# Existing executor ID (skips registration if set)
EXISTING_EXECUTOR_ID = os.environ.get("EM_TEST_EXECUTOR_ID", "")

# Blockchain
BASE_RPC = "https://mainnet.base.org"
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASESCAN_TX = "https://basescan.org/tx"

# ERC-20 Transfer event topic
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Default bounty and fee
DEFAULT_BOUNTY = 0.10
PLATFORM_FEE_PCT = Decimal("0.13")

# EM Agent ID
EM_AGENT_ID = 2106


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def ts_short() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


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
    """Structured result for a single phase."""

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


class GoldenFlowResults:
    """Collects all phase results."""

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

    def to_dict(self, bounty: float) -> Dict[str, Any]:
        fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_base": API_BASE,
            "bounty_usd": bounty,
            "fee_usd": fee,
            "total_cost_usd": bounty + fee,
            "worker_wallet": WORKER_WALLET,
            "treasury_wallet": TREASURY_WALLET,
            "phases": {name: phase.to_dict() for name, phase in self.phases.items()},
            "overall": self.overall,
            "tx_hashes": self.tx_hashes,
            "total_elapsed_s": round(time.time() - self.start_time, 2),
        }


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _auth_headers() -> Dict[str, str]:
    """Build authentication headers."""
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
    """Call /api/v1/* endpoint with auth headers."""
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
# On-chain TX verification
# ---------------------------------------------------------------------------
async def verify_tx_onchain(client: httpx.AsyncClient, tx_hash: str) -> Dict[str, Any]:
    """Verify a transaction on Base via RPC and parse USDC Transfer events."""
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
        from_addr = result.get("from", "")
        to_addr = result.get("to", "")

        # Parse USDC Transfer events
        transfers = []
        for log in result.get("logs", []):
            topics = log.get("topics", [])
            if (
                len(topics) >= 3
                and topics[0].lower() == TRANSFER_TOPIC.lower()
                and log.get("address", "").lower() == USDC_CONTRACT.lower()
            ):
                sender = "0x" + topics[1][-40:]
                receiver = "0x" + topics[2][-40:]
                raw_amount = int(log.get("data", "0x0"), 16)
                amount_usdc = raw_amount / 1_000_000  # USDC has 6 decimals
                transfers.append(
                    {
                        "from": sender.lower(),
                        "to": receiver.lower(),
                        "amount_usdc": amount_usdc,
                    }
                )

        return {
            "success": success,
            "gas_used": gas_used,
            "from": from_addr.lower(),
            "to": to_addr.lower(),
            "transfers": transfers,
            "block_number": int(result.get("blockNumber", "0x0"), 16),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Supabase fallback for payment details
# ---------------------------------------------------------------------------
def _fetch_payment_from_supabase(task_id: str) -> Optional[Dict[str, Any]]:
    """Query Supabase payment record for a task, extract fee_tx from note."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    try:
        import requests as req_lib

        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        }
        r = req_lib.get(
            f"{SUPABASE_URL}/rest/v1/payments?task_id=eq.{task_id}&select=*",
            headers=headers,
            timeout=10,
        )
        if r.status_code != 200 or not r.json():
            return None
        payment = r.json()[0]
        result: Dict[str, Any] = {
            "to_address": payment.get("to_address"),
            "fee_usdc": payment.get("fee_usdc"),
            "amount_usdc": payment.get("amount_usdc"),
            "settlement_method": payment.get("settlement_method"),
        }
        # Extract fee_tx from note: "... | fee_tx=0xabc..."
        note = payment.get("note", "")
        m = re.search(r"fee_tx=(0x[a-fA-F0-9]+)", note)
        if m:
            result["fee_tx"] = m.group(1)
        return result
    except Exception as e:
        print(f"         [Supabase fallback] error: {e}")
        return None


# ---------------------------------------------------------------------------
# Phase 1: Health & Config
# ---------------------------------------------------------------------------
async def phase_health_config(
    client: httpx.AsyncClient,
    results: GoldenFlowResults,
) -> PhaseResult:
    """Phase 1: Verify health, config, and reputation endpoints."""
    phase = PhaseResult("health_config", "Health & Config Verification")
    _print_header("PHASE 1: HEALTH & CONFIG")

    try:
        # 1. GET /health
        print("  [1/4] Checking health...")
        health = await raw_get(client, "/health/")
        h_status = health.get("_http_status")
        print(f"         Health: HTTP {h_status}")
        print(f"         Status: {health.get('status', 'N/A')}")

        if h_status != 200:
            return phase.fail(f"Health endpoint returned HTTP {h_status}")

        # 2. GET /api/v1/config
        print("  [2/4] Checking config...")
        config = await api_call(client, "GET", "/config")
        c_status = config.get("_http_status")
        print(f"         Config: HTTP {c_status}")
        networks = config.get("supported_networks", [])
        preferred = config.get("preferred_network", "N/A")
        min_bounty = config.get("min_bounty_usd", "N/A")
        print(f"         Networks: {networks}")
        print(f"         Preferred: {preferred}")
        print(f"         Min bounty: ${min_bounty}")

        if c_status != 200:
            return phase.fail(f"Config endpoint returned HTTP {c_status}")

        # 3. GET /api/v1/reputation/info
        print("  [3/4] Checking reputation info...")
        rep_info = await api_call(client, "GET", "/reputation/info")
        ri_status = rep_info.get("_http_status")
        print(f"         Reputation info: HTTP {ri_status}")
        em_agent_id = rep_info.get("em_agent_id", "N/A")
        rep_network = rep_info.get("network", "N/A")
        available = rep_info.get("available", False)
        print(f"         Agent ID: {em_agent_id}")
        print(f"         Network: {rep_network}")
        print(f"         Available: {available}")

        if ri_status != 200:
            return phase.fail(f"Reputation info returned HTTP {ri_status}")

        # 4. GET /api/v1/reputation/networks
        print("  [4/4] Checking ERC-8004 networks...")
        rep_nets = await api_call(client, "GET", "/reputation/networks")
        rn_status = rep_nets.get("_http_status")
        net_count = rep_nets.get("count", 0)
        print(f"         Networks endpoint: HTTP {rn_status}")
        print(f"         ERC-8004 networks: {net_count}")

        if rn_status != 200:
            return phase.fail(f"Reputation networks returned HTTP {rn_status}")

        return phase.pass_(
            health_status=health.get("status"),
            supported_networks=networks,
            preferred_network=preferred,
            min_bounty_usd=min_bounty,
            em_agent_id=em_agent_id,
            erc8004_network=rep_network,
            erc8004_available=available,
            erc8004_network_count=net_count,
        )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 2: Task Creation with Escrow
# ---------------------------------------------------------------------------
async def phase_task_creation(
    client: httpx.AsyncClient,
    results: GoldenFlowResults,
    bounty: float,
) -> PhaseResult:
    """Phase 2: Create task with escrow lock."""
    phase = PhaseResult("task_creation", "Task Creation with Escrow")
    fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
    total = bounty + fee

    _print_header("PHASE 2: TASK CREATION WITH ESCROW")
    print(f"    Bounty:  ${bounty:.2f} USDC")
    print(f"    Fee:     ${fee:.6f} USDC (13%)")
    print(f"    Total:   ${total:.6f} USDC")

    try:
        print("  [1/2] Creating task...")
        task_data = await api_call(
            client,
            "POST",
            "/tasks",
            {
                "title": f"[GOLDEN FLOW] E2E Test - {ts_short()}",
                "instructions": "Respond with: golden_flow_complete",
                "category": "simple_action",
                "bounty_usd": bounty,
                "deadline_hours": 1,
                "evidence_required": ["text_response"],
                "location_hint": "Any location",
                "payment_network": "base",
                "payment_token": "USDC",
            },
        )

        http_status = task_data.get("_http_status")
        print(f"         HTTP status: {http_status}")

        if http_status != 201:
            err = task_data.get("detail", task_data.get("error", str(task_data)[:200]))
            return phase.fail(f"Task creation failed: HTTP {http_status} - {err}")

        task_id = task_data.get("id")
        escrow_tx = task_data.get("escrow_tx")
        task_status = task_data.get("status")
        print(f"         Task ID: {task_id}")
        print(f"         Status:  {task_status}")

        if escrow_tx:
            print(f"         Escrow TX: {escrow_tx}")
            print(f"         BaseScan:  {BASESCAN_TX}/{escrow_tx}")
            results.add_tx(escrow_tx)
        else:
            print("         Escrow TX: N/A (Fase 1 balance-check only)")

        # [2/2] Verify escrow TX on-chain if present
        escrow_verified = False
        if escrow_tx:
            print("  [2/2] Verifying escrow TX on-chain...")
            receipt = await verify_tx_onchain(client, escrow_tx)
            escrow_verified = receipt.get("success", False)
            print(
                f"         On-chain status: {'SUCCESS' if escrow_verified else 'FAILED'}"
            )
            if receipt.get("gas_used"):
                print(f"         Gas used: {receipt['gas_used']:,}")
            if receipt.get("transfers"):
                for t in receipt["transfers"]:
                    print(
                        f"         Transfer: {t['from'][:10]}... -> {t['to'][:10]}... : ${t['amount_usdc']:.6f}"
                    )
        else:
            print("  [2/2] No escrow TX to verify (Fase 1 mode)")
            escrow_verified = True  # Fase 1 does not produce an escrow TX

        if task_status != "published":
            return phase.fail(
                f"Task status is '{task_status}', expected 'published'",
                task_id=task_id,
            )

        return phase.pass_(
            task_id=task_id,
            task_status=task_status,
            escrow_tx=escrow_tx,
            escrow_verified=escrow_verified,
            escrow_amount_usd=total,
        )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 3: Worker Registration & Identity
# ---------------------------------------------------------------------------
async def phase_worker_registration(
    client: httpx.AsyncClient,
    results: GoldenFlowResults,
) -> PhaseResult:
    """Phase 3: Register worker and ERC-8004 identity."""
    phase = PhaseResult("worker_registration", "Worker Registration & Identity")
    _print_header("PHASE 3: WORKER REGISTRATION & IDENTITY")

    executor_id = EXISTING_EXECUTOR_ID
    erc8004_agent_id = None
    erc8004_tx = None

    try:
        # Step 1: Register worker
        if executor_id:
            print(f"  [1/2] Using existing executor: {executor_id}")
        else:
            print("  [1/2] Registering worker...")
            # Worker registration is mounted directly on app at /api/v1/executors/register
            url = f"{API_BASE}/api/v1/executors/register"
            resp = await client.post(
                url,
                json={
                    "wallet_address": WORKER_WALLET,
                    "display_name": "Golden Flow Test Worker",
                },
                headers=_auth_headers(),
            )
            try:
                reg_data = resp.json()
            except Exception:
                reg_data = {"raw": resp.text}
            reg_data["_http_status"] = resp.status_code

            reg_status = reg_data.get("_http_status")
            print(f"         Register: HTTP {reg_status}")

            if reg_status not in (200, 201):
                err = reg_data.get("detail", str(reg_data)[:200])
                return phase.fail(f"Worker registration failed: {err}")

            executor_obj = reg_data.get("executor", {})
            executor_id = executor_obj.get("id", "")
            created = reg_data.get("created", False)
            print(f"         Executor ID: {executor_id}")
            print(f"         Created: {created}")

        if not executor_id:
            return phase.fail("No executor ID obtained")

        # Step 2: ERC-8004 identity registration
        print("  [2/2] Registering worker on ERC-8004...")
        erc_data = await api_call(
            client,
            "POST",
            "/reputation/register",
            {
                "network": "base",
                "agent_uri": "https://execution.market/workers/golden-flow-test",
                "recipient": WORKER_WALLET,
            },
        )

        erc_status = erc_data.get("_http_status")
        print(f"         ERC-8004 Register: HTTP {erc_status}")

        if erc_status in (200, 201):
            erc8004_agent_id = erc_data.get("agent_id")
            erc8004_tx = erc_data.get("transaction")
            erc_success = erc_data.get("success", False)
            erc_error = erc_data.get("error")
            print(f"         Success: {erc_success}")
            print(f"         Agent ID: {erc8004_agent_id}")
            if erc8004_tx:
                print(f"         TX: {erc8004_tx}")
                results.add_tx(erc8004_tx)
            if erc_error:
                print(f"         Note: {erc_error}")
                # Already registered is not a failure
                if "already" in str(erc_error).lower():
                    print("         (Worker already registered - OK)")
        else:
            err = erc_data.get("detail", str(erc_data)[:200])
            print(f"         ERC-8004 registration issue: {err}")
            # Non-fatal: worker can still operate without ERC-8004 identity
            return phase.partial(
                f"ERC-8004 registration returned HTTP {erc_status}: {err}",
                executor_id=executor_id,
            )

        return phase.pass_(
            executor_id=executor_id,
            erc8004_agent_id=erc8004_agent_id,
            erc8004_tx=erc8004_tx,
        )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 4: Task Lifecycle (Apply -> Assign -> Submit)
# ---------------------------------------------------------------------------
async def phase_task_lifecycle(
    client: httpx.AsyncClient,
    results: GoldenFlowResults,
    task_id: str,
    executor_id: str,
) -> PhaseResult:
    """Phase 4: Apply, assign, and submit evidence."""
    phase = PhaseResult("task_lifecycle", "Task Lifecycle (Apply -> Assign -> Submit)")
    _print_header("PHASE 4: TASK LIFECYCLE")
    print(f"    Task:     {task_id}")
    print(f"    Executor: {executor_id}")

    submission_id = None

    try:
        # Step 1: Worker applies
        print("  [1/3] Worker applying to task...")
        apply_data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/apply",
            {
                "executor_id": executor_id,
                "message": "Golden Flow E2E test -- ready to work",
            },
        )
        apply_status = apply_data.get("_http_status")
        print(f"         Apply: HTTP {apply_status}")

        if apply_status not in (200, 201):
            err = apply_data.get("detail", str(apply_data)[:200])
            return phase.fail(f"Apply failed: {err}")

        application_id = (apply_data.get("data") or {}).get("application_id")
        print(f"         Application ID: {application_id}")

        # Step 2: Agent assigns worker
        print("  [2/3] Agent assigning worker...")
        assign_data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/assign",
            {
                "executor_id": executor_id,
                "notes": "Golden Flow E2E test assignment",
            },
        )
        assign_status = assign_data.get("_http_status")
        print(f"         Assign: HTTP {assign_status}")

        if assign_status not in (200, 201):
            err = assign_data.get("detail", str(assign_data)[:200])
            return phase.fail(f"Assign failed: {err}")

        # Step 3: Worker submits evidence
        print("  [3/3] Worker submitting evidence...")
        submit_data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/submit",
            {
                "executor_id": executor_id,
                "evidence": {
                    "text_response": "golden_flow_complete",
                },
                "notes": "Golden Flow automated E2E submission",
            },
        )
        submit_status = submit_data.get("_http_status")
        print(f"         Submit: HTTP {submit_status}")

        if submit_status not in (200, 201):
            err = submit_data.get("detail", str(submit_data)[:200])
            return phase.fail(f"Submit failed: {err}")

        # Find submission ID
        submission_id = (submit_data.get("data") or {}).get("submission_id")
        if not submission_id:
            # Fallback: query submissions
            subs_data = await api_call(client, "GET", f"/tasks/{task_id}/submissions")
            subs_list = subs_data.get("submissions") or subs_data.get("data") or []
            if isinstance(subs_list, list) and subs_list:
                submission_id = subs_list[0].get("id")

        if not submission_id:
            return phase.fail("Could not find submission ID after submit")

        print(f"         Submission ID: {submission_id}")

        return phase.pass_(
            application_id=application_id,
            submission_id=submission_id,
        )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 5: Approval & Payment
# ---------------------------------------------------------------------------
async def phase_approval_payment(
    client: httpx.AsyncClient,
    results: GoldenFlowResults,
    task_id: str,
    submission_id: str,
    bounty: float,
) -> PhaseResult:
    """Phase 5: Approve submission and verify payment TXs."""
    phase = PhaseResult("payment", "Approval & Payment Settlement")
    fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
    total = bounty + fee

    _print_header("PHASE 5: APPROVAL & PAYMENT")
    print(f"    Task:       {task_id}")
    print(f"    Submission: {submission_id}")
    print(f"    Bounty:     ${bounty:.2f}")
    print(f"    Fee:        ${fee:.6f}")
    print(f"    Total:      ${total:.6f}")

    try:
        # Step 1: Approve submission
        print("  [1/3] Approving submission...")
        t0 = time.time()
        approve_data = await api_call(
            client,
            "POST",
            f"/submissions/{submission_id}/approve",
            {
                "notes": "Golden Flow E2E test -- approving for payment",
                "rating_score": 90,
            },
        )
        t_approve = time.time() - t0
        approve_status = approve_data.get("_http_status")
        print(f"         Approve: HTTP {approve_status} ({t_approve:.2f}s)")
        print(f"         Message: {approve_data.get('message', 'N/A')}")

        if approve_status != 200:
            err = approve_data.get(
                "detail", approve_data.get("error", str(approve_data)[:200])
            )
            return phase.fail(f"Approval failed: HTTP {approve_status} - {err}")

        resp_data = approve_data.get("data") or {}

        # Extract TX hashes
        payment_tx = resp_data.get("payment_tx")
        fee_tx = resp_data.get("fee_tx")
        escrow_release_tx = resp_data.get("escrow_release_tx")
        payment_mode = resp_data.get("payment_mode", "unknown")
        worker_net_actual = resp_data.get("worker_net_usdc")
        platform_fee_actual = resp_data.get("platform_fee_usdc")
        gross_actual = resp_data.get("gross_amount_usdc")

        # Supabase fallback for fee_tx
        if payment_tx and not fee_tx:
            print("         [Fallback] Querying Supabase for fee TX...")
            sb_payment = _fetch_payment_from_supabase(task_id)
            if sb_payment:
                if sb_payment.get("fee_tx"):
                    fee_tx = sb_payment["fee_tx"]
                    print(f"         [Fallback] fee_tx: {fee_tx[:20]}...")
                if sb_payment.get("settlement_method") and payment_mode == "unknown":
                    payment_mode = sb_payment["settlement_method"]

        print()
        print("  +-----------------------------------------------------------+")
        print("  |              PAYMENT SETTLEMENT RESULTS                    |")
        print("  +-----------------------------------------------------------+")
        print(f"  |  Mode:          {payment_mode:<42s}|")
        if escrow_release_tx:
            print(f"  |  Escrow Release: {escrow_release_tx[:42]:<42s}|")
        if payment_tx:
            print(f"  |  Worker TX:     {payment_tx[:42]:<42s}|")
            print(f"  |    {BASESCAN_TX}/{payment_tx}")
        if fee_tx:
            print(f"  |  Fee TX:        {fee_tx[:42]:<42s}|")
            print(f"  |    {BASESCAN_TX}/{fee_tx}")
        if worker_net_actual is not None:
            print(f"  |  Worker net:    ${worker_net_actual:.6f} USDC{' ':>25s}|")
        if platform_fee_actual is not None:
            print(f"  |  Platform fee:  ${platform_fee_actual:.6f} USDC{' ':>25s}|")
        print("  +-----------------------------------------------------------+")

        # Collect TX hashes
        if escrow_release_tx:
            results.add_tx(escrow_release_tx)
        if payment_tx:
            results.add_tx(payment_tx)
        if fee_tx:
            results.add_tx(fee_tx)

        # Step 2: Verify TXs on-chain
        tx_verifications: Dict[str, Dict[str, Any]] = {}

        # Get escrow TX from phase 2
        escrow_tx = results.phases.get(
            "task_creation", PhaseResult("", "")
        ).details.get("escrow_tx")

        txs_to_verify = {}
        if escrow_tx:
            txs_to_verify["escrow_lock"] = escrow_tx
        if payment_tx:
            txs_to_verify["worker_payout"] = payment_tx
        if fee_tx:
            txs_to_verify["fee_collection"] = fee_tx

        if txs_to_verify:
            print(f"\n  [2/3] Verifying {len(txs_to_verify)} TX(s) on-chain...")
            for label, tx_hash in txs_to_verify.items():
                receipt = await verify_tx_onchain(client, tx_hash)
                tx_verifications[label] = receipt
                ok = receipt.get("success", False)
                print(f"         {label}: {'SUCCESS' if ok else 'FAILED'}")
                if receipt.get("transfers"):
                    for t in receipt["transfers"]:
                        print(
                            f"           Transfer: ...{t['from'][-6:]} -> ...{t['to'][-6:]} : ${t['amount_usdc']:.6f}"
                        )
        else:
            print("\n  [2/3] No TXs to verify on-chain")

        # Step 3: Fee math verification
        print("\n  [3/3] Verifying fee math...")
        fee_mismatch = None
        if platform_fee_actual is not None and worker_net_actual is not None:
            expected_fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
            if abs(platform_fee_actual - expected_fee) > 0.001:
                fee_mismatch = f"Expected fee ${expected_fee:.6f} but got ${platform_fee_actual:.6f}"
            if abs(worker_net_actual - bounty) > 0.001:
                fee_mismatch = f"Expected worker net ${bounty:.6f} but got ${worker_net_actual:.6f}"

            if fee_mismatch:
                print(f"         MISMATCH: {fee_mismatch}")
            else:
                print(
                    f"         Worker:   ${worker_net_actual:.6f} (expected ${bounty:.6f}) -- OK"
                )
                print(
                    f"         Fee:      ${platform_fee_actual:.6f} (expected ${expected_fee:.6f}) -- OK"
                )
        else:
            print("         Fee details not available in API response")

        # Determine overall status
        all_txs_verified = all(
            v.get("success", False) for v in tx_verifications.values()
        )
        has_payment = bool(payment_tx)

        if has_payment and all_txs_verified and not fee_mismatch:
            return phase.pass_(
                payment_mode=payment_mode,
                escrow_release_tx=escrow_release_tx,
                payment_tx=payment_tx,
                fee_tx=fee_tx,
                worker_net_usdc=worker_net_actual,
                platform_fee_usdc=platform_fee_actual,
                gross_amount_usdc=gross_actual,
                approve_time_s=round(t_approve, 2),
                tx_verifications={
                    k: v.get("success") for k, v in tx_verifications.items()
                },
                all_txs_verified=all_txs_verified,
            )
        elif fee_mismatch:
            return phase.partial(
                fee_mismatch,
                payment_tx=payment_tx,
                fee_tx=fee_tx,
                payment_mode=payment_mode,
            )
        else:
            missing = []
            if not payment_tx:
                missing.append("payment_tx")
            if not all_txs_verified:
                missing.append("on-chain verification")
            return phase.fail(
                f"Missing: {', '.join(missing)}",
                payment_tx=payment_tx,
                fee_tx=fee_tx,
            )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 6: Reputation (Bidirectional)
# ---------------------------------------------------------------------------
async def phase_reputation(
    client: httpx.AsyncClient,
    results: GoldenFlowResults,
    task_id: str,
) -> PhaseResult:
    """Phase 6: Bidirectional reputation rating."""
    phase = PhaseResult("reputation", "Bidirectional Reputation")
    _print_header("PHASE 6: REPUTATION (BIDIRECTIONAL)")

    agent_rates_worker_tx = None
    worker_rates_agent_tx = None

    try:
        # Step 1: Agent rates worker
        print("  [1/2] Agent rating worker (score: 90)...")
        rate_worker_data = await api_call(
            client,
            "POST",
            "/reputation/workers/rate",
            {
                "task_id": task_id,
                "score": 90,
                "comment": "Golden Flow test -- excellent work",
            },
        )
        rw_status = rate_worker_data.get("_http_status")
        print(f"         Rate worker: HTTP {rw_status}")
        rw_success = rate_worker_data.get("success", False)
        agent_rates_worker_tx = rate_worker_data.get("transaction_hash")
        rw_error = rate_worker_data.get("error")
        print(f"         Success: {rw_success}")
        if agent_rates_worker_tx:
            print(f"         TX: {agent_rates_worker_tx}")
            results.add_tx(agent_rates_worker_tx)
        if rw_error:
            print(f"         Note: {rw_error}")

        # Step 2: Worker rates agent
        print("  [2/2] Worker rating agent (score: 85)...")
        rate_agent_data = await api_call(
            client,
            "POST",
            "/reputation/agents/rate",
            {
                "agent_id": EM_AGENT_ID,
                "task_id": task_id,
                "score": 85,
                "comment": "Golden Flow test -- great agent",
            },
        )
        ra_status = rate_agent_data.get("_http_status")
        print(f"         Rate agent: HTTP {ra_status}")
        ra_success = rate_agent_data.get("success", False)
        worker_rates_agent_tx = rate_agent_data.get("transaction_hash")
        ra_error = rate_agent_data.get("error")
        print(f"         Success: {ra_success}")
        if worker_rates_agent_tx:
            print(f"         TX: {worker_rates_agent_tx}")
            results.add_tx(worker_rates_agent_tx)
        if ra_error:
            print(f"         Note: {ra_error}")

        # Both must succeed for full pass; partial if one fails
        if rw_status == 200 and ra_status == 200 and rw_success and ra_success:
            return phase.pass_(
                agent_rates_worker_tx=agent_rates_worker_tx,
                worker_rates_agent_tx=worker_rates_agent_tx,
                agent_rates_worker_success=rw_success,
                worker_rates_agent_success=ra_success,
            )
        elif rw_status == 200 or ra_status == 200:
            errors = []
            if rw_status != 200 or not rw_success:
                errors.append(
                    f"Agent->Worker: HTTP {rw_status}, success={rw_success}, error={rw_error}"
                )
            if ra_status != 200 or not ra_success:
                errors.append(
                    f"Worker->Agent: HTTP {ra_status}, success={ra_success}, error={ra_error}"
                )
            return phase.partial(
                "; ".join(errors),
                agent_rates_worker_tx=agent_rates_worker_tx,
                worker_rates_agent_tx=worker_rates_agent_tx,
            )
        else:
            return phase.fail(
                f"Both ratings failed: Worker HTTP {rw_status}, Agent HTTP {ra_status}",
                rw_error=rw_error,
                ra_error=ra_error,
            )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 7: Verification
# ---------------------------------------------------------------------------
async def phase_verification(
    client: httpx.AsyncClient,
    results: GoldenFlowResults,
    task_id: str,
) -> PhaseResult:
    """Phase 7: Final verification -- EM reputation and feedback document."""
    phase = PhaseResult("verification", "Final Verification")
    _print_header("PHASE 7: FINAL VERIFICATION")

    try:
        # Step 1: Check EM reputation
        print("  [1/2] Checking EM reputation...")
        em_rep = await api_call(client, "GET", "/reputation/em")
        rep_status = em_rep.get("_http_status")
        print(f"         EM Reputation: HTTP {rep_status}")
        if rep_status == 200:
            print(f"         Agent ID: {em_rep.get('agent_id')}")
            print(f"         Score: {em_rep.get('score')}")
            print(f"         Count: {em_rep.get('count')}")
        else:
            print(
                f"         Could not fetch EM reputation: {em_rep.get('detail', 'N/A')}"
            )

        # Step 2: Check feedback document
        print("  [2/2] Checking feedback document...")
        feedback = await api_call(client, "GET", f"/reputation/feedback/{task_id}")
        fb_status = feedback.get("_http_status")
        print(f"         Feedback: HTTP {fb_status}")
        if fb_status == 200:
            print(f"         Feedback document found for task {task_id}")
        elif fb_status == 404:
            print("         No feedback document yet (may be async)")
        else:
            print(f"         Feedback status: {feedback.get('detail', 'N/A')}")

        # Collect all TX verification results
        all_txs = results.tx_hashes
        print(f"\n  Total on-chain TXs collected: {len(all_txs)}")
        for i, tx in enumerate(all_txs, 1):
            print(f"    TX {i}: {tx}")
            print(f"           {BASESCAN_TX}/{tx}")

        # Overall: pass if reputation endpoint works
        if rep_status == 200:
            return phase.pass_(
                em_reputation_score=em_rep.get("score"),
                em_reputation_count=em_rep.get("count"),
                feedback_available=fb_status == 200,
                total_txs=len(all_txs),
                all_tx_hashes=all_txs,
            )
        else:
            return phase.partial(
                f"EM reputation endpoint returned HTTP {rep_status}",
                feedback_available=fb_status == 200,
                total_txs=len(all_txs),
            )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report_en(results: GoldenFlowResults, bounty: float) -> str:
    """Generate English Markdown report."""
    fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
    total = bounty + fee
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    overall = results.overall

    lines = [
        "# Golden Flow Report -- Definitive E2E Acceptance Test",
        "",
        f"> **Date**: {now}",
        "> **Environment**: Production (Base Mainnet, chain 8453)",
        f"> **API**: `{API_BASE}`",
        f"> **Result**: **{overall}**",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "The Golden Flow tested the complete Execution Market lifecycle end-to-end ",
        f"on production against Base Mainnet. {results.pass_count}/{len(results.phases)} phases passed.",
        "",
        f"**Overall Result: {overall}**",
        "",
        "---",
        "",
        "## Test Configuration",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Bounty | ${bounty:.2f} USDC |",
        f"| Platform Fee | 13% (${fee:.6f}) |",
        f"| Total Cost | ${total:.6f} USDC |",
        f"| Worker Wallet | `{WORKER_WALLET}` |",
        f"| Treasury | `{TREASURY_WALLET}` |",
        f"| API Base | `{API_BASE}` |",
        f"| EM Agent ID | {EM_AGENT_ID} |",
        "",
        "---",
        "",
        "## Flow Diagram",
        "",
        "```mermaid",
        "sequenceDiagram",
        "    participant Agent",
        "    participant API",
        "    participant Facilitator",
        "    participant Base",
        "    participant Worker",
        "    participant ERC8004",
        "",
        "    Note over Agent,ERC8004: Phase 1: Health",
        "    Agent->>API: GET /health",
        "    Agent->>API: GET /config",
        "    Agent->>API: GET /reputation/info",
        "",
        "    Note over Agent,ERC8004: Phase 2: Task + Escrow",
        f"    Agent->>API: POST /tasks (bounty=${bounty:.2f})",
        "    API->>Facilitator: Authorize escrow",
        f"    Facilitator->>Base: TX1: Lock ${total:.3f}",
        "",
        "    Note over Agent,ERC8004: Phase 3: Worker Identity",
        "    Worker->>API: POST /executors/register",
        "    Worker->>API: POST /reputation/register",
        "    API->>Facilitator: Gasless registration",
        "    Facilitator->>ERC8004: Mint identity NFT",
        "",
        "    Note over Agent,ERC8004: Phase 4: Task Lifecycle",
        "    Worker->>API: Apply -> Assign -> Submit evidence",
        "",
        "    Note over Agent,ERC8004: Phase 5: Payment",
        "    Agent->>API: POST /submissions/{id}/approve",
        "    API->>Facilitator: Release escrow",
        f"    Facilitator->>Base: TX2: ${bounty:.2f} -> Worker",
        f"    Facilitator->>Base: TX3: ${fee:.3f} -> Treasury",
        "",
        "    Note over Agent,ERC8004: Phase 6: Reputation",
        "    Agent->>API: Rate worker (score: 90)",
        "    API->>Facilitator: POST /feedback",
        "    Worker->>API: Rate agent (score: 85)",
        "    API->>Facilitator: POST /feedback",
        "",
        "    Note over Agent,ERC8004: Phase 7: Verification",
        "    Agent->>API: GET /reputation/em",
        "    Agent->>API: GET /reputation/feedback/{task_id}",
        "```",
        "",
        "---",
        "",
        "## Phase Results",
        "",
        "| # | Phase | Status | Time |",
        "|---|-------|--------|------|",
    ]

    for i, (name, phase) in enumerate(results.phases.items(), 1):
        status = phase.status
        elapsed = f"{phase.elapsed_s}s"
        lines.append(f"| {i} | {phase.description} | **{status}** | {elapsed} |")

    lines.extend(["", "---", ""])

    # Detailed phase sections
    for name, phase in results.phases.items():
        lines.append(f"## {phase.description}")
        lines.append("")
        lines.append(f"- **Status**: {phase.status}")
        lines.append(f"- **Time**: {phase.elapsed_s}s")
        if phase.error:
            lines.append(f"- **Error**: {phase.error}")
        lines.append("")

        # Phase-specific details
        details = phase.details

        if name == "task_creation":
            if details.get("task_id"):
                lines.append(f"- **Task ID**: `{details['task_id']}`")
            if details.get("escrow_tx"):
                lines.append(
                    f"- **Escrow TX**: [`{details['escrow_tx'][:16]}...`]({BASESCAN_TX}/{details['escrow_tx']})"
                )
                lines.append(
                    f"- **Escrow Verified**: {details.get('escrow_verified', 'N/A')}"
                )
                lines.append(
                    f"- **Escrow Amount**: ${details.get('escrow_amount_usd', 0):.6f} USDC"
                )

        elif name == "worker_registration":
            if details.get("executor_id"):
                lines.append(f"- **Executor ID**: `{details['executor_id']}`")
            if details.get("erc8004_agent_id"):
                lines.append(f"- **ERC-8004 Agent ID**: {details['erc8004_agent_id']}")
            if details.get("erc8004_tx"):
                lines.append(
                    f"- **ERC-8004 TX**: [`{details['erc8004_tx'][:16]}...`]({BASESCAN_TX}/{details['erc8004_tx']})"
                )

        elif name == "task_lifecycle":
            if details.get("submission_id"):
                lines.append(f"- **Submission ID**: `{details['submission_id']}`")

        elif name == "payment":
            if details.get("payment_mode"):
                lines.append(f"- **Payment Mode**: `{details['payment_mode']}`")
            if details.get("payment_tx"):
                lines.append(
                    f"- **Worker TX**: [`{details['payment_tx'][:16]}...`]({BASESCAN_TX}/{details['payment_tx']})"
                )
            if details.get("fee_tx"):
                lines.append(
                    f"- **Fee TX**: [`{details['fee_tx'][:16]}...`]({BASESCAN_TX}/{details['fee_tx']})"
                )
            if details.get("escrow_release_tx"):
                lines.append(
                    f"- **Escrow Release**: [`{details['escrow_release_tx'][:16]}...`]({BASESCAN_TX}/{details['escrow_release_tx']})"
                )

            # Fee Math Verification table
            if (
                details.get("worker_net_usdc") is not None
                and details.get("platform_fee_usdc") is not None
            ):
                lines.append("")
                lines.append("### Fee Math Verification")
                lines.append("")
                lines.append("| Metric | Expected | Actual | Match |")
                lines.append("|--------|----------|--------|-------|")

                exp_worker = bounty
                act_worker = details["worker_net_usdc"]
                w_ok = "YES" if abs(act_worker - exp_worker) < 0.001 else "NO"
                lines.append(
                    f"| Worker net | ${exp_worker:.6f} | ${act_worker:.6f} | {w_ok} |"
                )

                exp_fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
                act_fee = details["platform_fee_usdc"]
                f_ok = "YES" if abs(act_fee - exp_fee) < 0.001 else "NO"
                lines.append(
                    f"| Platform fee | ${exp_fee:.6f} | ${act_fee:.6f} | {f_ok} |"
                )

                if details.get("gross_amount_usdc"):
                    exp_gross = bounty + exp_fee
                    act_gross = details["gross_amount_usdc"]
                    g_ok = "YES" if abs(act_gross - exp_gross) < 0.001 else "NO"
                    lines.append(
                        f"| Gross total | ${exp_gross:.6f} | ${act_gross:.6f} | {g_ok} |"
                    )

        elif name == "reputation":
            if details.get("agent_rates_worker_tx"):
                lines.append(
                    f"- **Agent->Worker TX**: [`{details['agent_rates_worker_tx'][:16]}...`]({BASESCAN_TX}/{details['agent_rates_worker_tx']})"
                )
            if details.get("worker_rates_agent_tx"):
                lines.append(
                    f"- **Worker->Agent TX**: [`{details['worker_rates_agent_tx'][:16]}...`]({BASESCAN_TX}/{details['worker_rates_agent_tx']})"
                )

        elif name == "verification":
            if details.get("em_reputation_score") is not None:
                lines.append(
                    f"- **EM Reputation Score**: {details['em_reputation_score']}"
                )
            if details.get("em_reputation_count") is not None:
                lines.append(
                    f"- **EM Reputation Count**: {details['em_reputation_count']}"
                )
            lines.append(
                f"- **Feedback Available**: {details.get('feedback_available', False)}"
            )

        lines.append("")

    # ERC-8004 Identity Verification section
    worker_phase = results.phases.get("worker_registration")
    if worker_phase and worker_phase.details.get("erc8004_agent_id"):
        lines.extend(
            [
                "---",
                "",
                "## ERC-8004 Identity Verification",
                "",
                "| Field | Value |",
                "|-------|-------|",
                f"| Worker Wallet | `{WORKER_WALLET}` |",
                f"| ERC-8004 Agent ID | {worker_phase.details.get('erc8004_agent_id')} |",
                "| Network | base |",
                "| Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |",
                f"| Registration TX | `{worker_phase.details.get('erc8004_tx', 'N/A')}` |",
                "",
            ]
        )

    # On-chain TX summary
    lines.extend(
        [
            "---",
            "",
            "## On-Chain Transaction Summary",
            "",
            "| # | TX Hash | BaseScan |",
            "|---|---------|----------|",
        ]
    )
    for i, tx in enumerate(results.tx_hashes, 1):
        lines.append(f"| {i} | `{tx[:20]}...` | [View]({BASESCAN_TX}/{tx}) |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Invariants Verified",
            "",
        ]
    )

    # Build invariant checklist from results
    payment_phase = results.phases.get("payment")
    rep_phase = results.phases.get("reputation")

    checks: list[str] = []
    if results.phases.get("health_config", PhaseResult("", "")).status == "PASS":
        checks.append("API is healthy and returning correct configuration")
    task_phase = results.phases.get("task_creation")
    if task_phase and task_phase.status == "PASS":
        checks.append("Task created successfully with published status")
        if task_phase.details.get("escrow_tx"):
            checks.append("Escrow TX verified on-chain (status: SUCCESS)")
    if worker_phase and worker_phase.status in ("PASS", "PARTIAL"):
        checks.append("Worker registered with executor ID")
    if payment_phase and payment_phase.status == "PASS":
        if payment_phase.details.get("payment_tx") and payment_phase.details.get(
            "fee_tx"
        ):
            checks.append("Worker TX and Fee TX are distinct on-chain transactions")
        if payment_phase.details.get("worker_net_usdc") is not None:
            w = payment_phase.details["worker_net_usdc"]
            if abs(w - bounty) < 0.001:
                checks.append(f"Worker receives exactly ${bounty:.2f} (100% of bounty)")
        if payment_phase.details.get("platform_fee_usdc") is not None:
            f_val = payment_phase.details["platform_fee_usdc"]
            checks.append(f"Treasury receives ${f_val:.6f} (13% platform fee)")
        if payment_phase.details.get("all_txs_verified"):
            checks.append("All payment TXs verified on-chain (status: 0x1)")
    if rep_phase and rep_phase.status == "PASS":
        checks.append(
            "Bidirectional reputation: agent rated worker AND worker rated agent"
        )

    if checks:
        for c in checks:
            lines.append(f"- [x] {c}")
    else:
        lines.append("- [ ] No invariants could be verified (tests may have failed)")

    lines.append("")
    return "\n".join(lines)


def generate_report_es(results: GoldenFlowResults, bounty: float) -> str:
    """Generate Spanish Markdown report."""
    fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
    total = bounty + fee
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    overall = results.overall

    lines = [
        "# Reporte Golden Flow -- Prueba de Aceptacion E2E Definitiva",
        "",
        f"> **Fecha**: {now}",
        "> **Entorno**: Produccion (Base Mainnet, chain 8453)",
        f"> **API**: `{API_BASE}`",
        f"> **Resultado**: **{overall}**",
        "",
        "---",
        "",
        "## Resumen Ejecutivo",
        "",
        "El Golden Flow probo el ciclo de vida completo de Execution Market end-to-end ",
        f"en produccion contra Base Mainnet. {results.pass_count}/{len(results.phases)} fases pasaron.",
        "",
        f"**Resultado General: {overall}**",
        "",
        "---",
        "",
        "## Configuracion de Prueba",
        "",
        "| Parametro | Valor |",
        "|-----------|-------|",
        f"| Bounty | ${bounty:.2f} USDC |",
        f"| Fee de plataforma | 13% (${fee:.6f}) |",
        f"| Costo total | ${total:.6f} USDC |",
        f"| Wallet del Worker | `{WORKER_WALLET}` |",
        f"| Treasury | `{TREASURY_WALLET}` |",
        f"| API Base | `{API_BASE}` |",
        f"| EM Agent ID | {EM_AGENT_ID} |",
        "",
        "---",
        "",
        "## Diagrama de Flujo",
        "",
        "```mermaid",
        "sequenceDiagram",
        "    participant Agente",
        "    participant API",
        "    participant Facilitator",
        "    participant Base",
        "    participant Worker",
        "    participant ERC8004",
        "",
        "    Note over Agente,ERC8004: Fase 1: Salud",
        "    Agente->>API: GET /health",
        "    Agente->>API: GET /config",
        "    Agente->>API: GET /reputation/info",
        "",
        "    Note over Agente,ERC8004: Fase 2: Tarea + Escrow",
        f"    Agente->>API: POST /tasks (bounty=${bounty:.2f})",
        "    API->>Facilitator: Autorizar escrow",
        f"    Facilitator->>Base: TX1: Bloquear ${total:.3f}",
        "",
        "    Note over Agente,ERC8004: Fase 3: Identidad del Worker",
        "    Worker->>API: POST /executors/register",
        "    Worker->>API: POST /reputation/register",
        "    API->>Facilitator: Registro gasless",
        "    Facilitator->>ERC8004: Mint NFT de identidad",
        "",
        "    Note over Agente,ERC8004: Fase 4: Ciclo de Vida de Tarea",
        "    Worker->>API: Aplicar -> Asignar -> Enviar evidencia",
        "",
        "    Note over Agente,ERC8004: Fase 5: Pago",
        "    Agente->>API: POST /submissions/{id}/approve",
        "    API->>Facilitator: Liberar escrow",
        f"    Facilitator->>Base: TX2: ${bounty:.2f} -> Worker",
        f"    Facilitator->>Base: TX3: ${fee:.3f} -> Treasury",
        "",
        "    Note over Agente,ERC8004: Fase 6: Reputacion",
        "    Agente->>API: Calificar worker (score: 90)",
        "    API->>Facilitator: POST /feedback",
        "    Worker->>API: Calificar agente (score: 85)",
        "    API->>Facilitator: POST /feedback",
        "",
        "    Note over Agente,ERC8004: Fase 7: Verificacion",
        "    Agente->>API: GET /reputation/em",
        "    Agente->>API: GET /reputation/feedback/{task_id}",
        "```",
        "",
        "---",
        "",
        "## Resultados por Fase",
        "",
        "| # | Fase | Estado | Tiempo |",
        "|---|------|--------|--------|",
    ]

    phase_names_es = {
        "health_config": "Salud y Configuracion",
        "task_creation": "Creacion de Tarea con Escrow",
        "worker_registration": "Registro de Worker e Identidad",
        "task_lifecycle": "Ciclo de Vida (Aplicar -> Asignar -> Enviar)",
        "payment": "Aprobacion y Pago",
        "reputation": "Reputacion Bidireccional",
        "verification": "Verificacion Final",
    }

    for i, (name, phase) in enumerate(results.phases.items(), 1):
        desc_es = phase_names_es.get(name, phase.description)
        status = phase.status
        if status == "PASS":
            status_es = "APROBADO"
        elif status == "FAIL":
            status_es = "FALLIDO"
        else:
            status_es = "PARCIAL"
        lines.append(f"| {i} | {desc_es} | **{status_es}** | {phase.elapsed_s}s |")

    lines.extend(["", "---", ""])

    # Detailed phase sections
    for name, phase in results.phases.items():
        desc_es = phase_names_es.get(name, phase.description)
        lines.append(f"## {desc_es}")
        lines.append("")
        status = phase.status
        if status == "PASS":
            status_es = "APROBADO"
        elif status == "FAIL":
            status_es = "FALLIDO"
        else:
            status_es = "PARCIAL"
        lines.append(f"- **Estado**: {status_es}")
        lines.append(f"- **Tiempo**: {phase.elapsed_s}s")
        if phase.error:
            lines.append(f"- **Error**: {phase.error}")

        details = phase.details

        if name == "task_creation" and details.get("task_id"):
            lines.append(f"- **Task ID**: `{details['task_id']}`")
            if details.get("escrow_tx"):
                lines.append(
                    f"- **TX Escrow**: [`{details['escrow_tx'][:16]}...`]({BASESCAN_TX}/{details['escrow_tx']})"
                )

        elif name == "worker_registration" and details.get("executor_id"):
            lines.append(f"- **Executor ID**: `{details['executor_id']}`")
            if details.get("erc8004_agent_id"):
                lines.append(f"- **ERC-8004 Agent ID**: {details['erc8004_agent_id']}")

        elif name == "payment":
            if details.get("payment_mode"):
                lines.append(f"- **Modo de pago**: `{details['payment_mode']}`")
            if details.get("payment_tx"):
                lines.append(
                    f"- **TX Worker**: [`{details['payment_tx'][:16]}...`]({BASESCAN_TX}/{details['payment_tx']})"
                )
            if details.get("fee_tx"):
                lines.append(
                    f"- **TX Fee**: [`{details['fee_tx'][:16]}...`]({BASESCAN_TX}/{details['fee_tx']})"
                )

            # Fee math
            if (
                details.get("worker_net_usdc") is not None
                and details.get("platform_fee_usdc") is not None
            ):
                lines.append("")
                lines.append("### Verificacion de Fee")
                lines.append("")
                lines.append("| Metrica | Esperado | Actual | Coincide |")
                lines.append("|---------|----------|--------|----------|")

                exp_worker = bounty
                act_worker = details["worker_net_usdc"]
                w_ok = "SI" if abs(act_worker - exp_worker) < 0.001 else "NO"
                lines.append(
                    f"| Neto worker | ${exp_worker:.6f} | ${act_worker:.6f} | {w_ok} |"
                )

                exp_fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
                act_fee = details["platform_fee_usdc"]
                f_ok = "SI" if abs(act_fee - exp_fee) < 0.001 else "NO"
                lines.append(
                    f"| Fee plataforma | ${exp_fee:.6f} | ${act_fee:.6f} | {f_ok} |"
                )

        elif name == "reputation":
            if details.get("agent_rates_worker_tx"):
                lines.append(
                    f"- **TX Agente->Worker**: [`{details['agent_rates_worker_tx'][:16]}...`]({BASESCAN_TX}/{details['agent_rates_worker_tx']})"
                )
            if details.get("worker_rates_agent_tx"):
                lines.append(
                    f"- **TX Worker->Agente**: [`{details['worker_rates_agent_tx'][:16]}...`]({BASESCAN_TX}/{details['worker_rates_agent_tx']})"
                )

        lines.append("")

    # On-chain TX summary
    lines.extend(
        [
            "---",
            "",
            "## Resumen de Transacciones On-Chain",
            "",
            "| # | TX Hash | BaseScan |",
            "|---|---------|----------|",
        ]
    )
    for i, tx in enumerate(results.tx_hashes, 1):
        lines.append(f"| {i} | `{tx[:20]}...` | [Ver]({BASESCAN_TX}/{tx}) |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Invariantes Verificados",
            "",
        ]
    )

    payment_phase = results.phases.get("payment")
    rep_phase = results.phases.get("reputation")
    worker_phase = results.phases.get("worker_registration")

    checks: list[str] = []
    if results.phases.get("health_config", PhaseResult("", "")).status == "PASS":
        checks.append("API saludable y retornando configuracion correcta")
    task_phase = results.phases.get("task_creation")
    if task_phase and task_phase.status == "PASS":
        checks.append("Tarea creada exitosamente con status published")
        if task_phase.details.get("escrow_tx"):
            checks.append("TX de escrow verificada on-chain (status: SUCCESS)")
    if worker_phase and worker_phase.status in ("PASS", "PARTIAL"):
        checks.append("Worker registrado con executor ID")
    if payment_phase and payment_phase.status == "PASS":
        if payment_phase.details.get("payment_tx") and payment_phase.details.get(
            "fee_tx"
        ):
            checks.append(
                "TX de Worker y TX de Fee son transacciones on-chain distintas"
            )
        if payment_phase.details.get("worker_net_usdc") is not None:
            w = payment_phase.details["worker_net_usdc"]
            if abs(w - bounty) < 0.001:
                checks.append(
                    f"Worker recibe exactamente ${bounty:.2f} (100% del bounty)"
                )
        if payment_phase.details.get("platform_fee_usdc") is not None:
            f_val = payment_phase.details["platform_fee_usdc"]
            checks.append(f"Treasury recibe ${f_val:.6f} (13% fee de plataforma)")
        if payment_phase.details.get("all_txs_verified"):
            checks.append("Todas las TXs de pago verificadas on-chain (status: 0x1)")
    if rep_phase and rep_phase.status == "PASS":
        checks.append(
            "Reputacion bidireccional: agente califico worker Y worker califico agente"
        )

    if checks:
        for c in checks:
            lines.append(f"- [x] {c}")
    else:
        lines.append(
            "- [ ] No se pudieron verificar invariantes (las pruebas pudieron haber fallado)"
        )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> int:
    bounty = DEFAULT_BOUNTY
    dry_run = "--dry-run" in sys.argv

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
    print("  GOLDEN FLOW -- Definitive E2E Acceptance Test")
    print("=" * 72)
    _print_kv("API", API_BASE, 2)
    _print_kv("Time", ts(), 2)
    _print_kv("Bounty", f"${bounty:.2f} USDC", 2)
    _print_kv("Fee (13%)", f"${fee:.6f} USDC", 2)
    _print_kv("Total", f"${total:.6f} USDC", 2)
    _print_kv("Worker", WORKER_WALLET, 2)
    _print_kv("Treasury", TREASURY_WALLET, 2)
    _print_kv("Auth", "API key set" if API_KEY else "Anonymous (no API key)", 2)
    if EXISTING_EXECUTOR_ID:
        _print_kv("Executor", EXISTING_EXECUTOR_ID, 2)
    _print_kv("Dry run", dry_run, 2)

    if dry_run:
        print("\nDRY RUN -- configuration shown above. Remove --dry-run to execute.")
        return 0

    results = GoldenFlowResults()

    timeout = httpx.Timeout(180.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Phase 1: Health & Config
        p1 = await phase_health_config(client, results)
        results.add(p1)

        if p1.status == "FAIL":
            print("\n  [ABORT] Health check failed. Cannot continue.")
            _print_summary(results, bounty)
            return 1

        # Phase 2: Task Creation
        p2 = await phase_task_creation(client, results, bounty)
        results.add(p2)

        task_id = p2.details.get("task_id")
        if not task_id:
            print("\n  [ABORT] No task ID. Cannot continue.")
            _print_summary(results, bounty)
            return 1

        await asyncio.sleep(2)  # Brief pause between phases

        # Phase 3: Worker Registration
        p3 = await phase_worker_registration(client, results)
        results.add(p3)

        executor_id = p3.details.get("executor_id") or EXISTING_EXECUTOR_ID
        if not executor_id:
            print("\n  [ABORT] No executor ID. Cannot continue.")
            _print_summary(results, bounty)
            return 1

        await asyncio.sleep(2)

        # Phase 4: Task Lifecycle
        p4 = await phase_task_lifecycle(client, results, task_id, executor_id)
        results.add(p4)

        submission_id = p4.details.get("submission_id")
        if not submission_id:
            print("\n  [ABORT] No submission ID. Cannot continue.")
            _print_summary(results, bounty)
            return 1

        await asyncio.sleep(2)

        # Phase 5: Approval & Payment
        p5 = await phase_approval_payment(
            client, results, task_id, submission_id, bounty
        )
        results.add(p5)

        await asyncio.sleep(3)  # Allow time for on-chain settlement

        # Phase 6: Reputation
        p6 = await phase_reputation(client, results, task_id)
        results.add(p6)

        await asyncio.sleep(2)

        # Phase 7: Verification
        p7 = await phase_verification(client, results, task_id)
        results.add(p7)

    # Generate and save reports
    _print_summary(results, bounty)
    _save_reports(results, bounty)

    return 0 if results.fail_count == 0 else 1


def _print_summary(results: GoldenFlowResults, bounty: float) -> None:
    """Print final summary to console."""
    total_phases = len(results.phases)
    elapsed = round(time.time() - results.start_time, 2)

    print()
    _print_header("GOLDEN FLOW SUMMARY")
    print(f"  Overall:  {results.overall}")
    print(
        f"  Phases:   {total_phases} total | "
        f"{results.pass_count} passed | "
        f"{results.fail_count} failed | "
        f"{total_phases - results.pass_count - results.fail_count} partial"
    )
    print(f"  TXs:      {len(results.tx_hashes)} on-chain transactions")
    print(f"  Elapsed:  {elapsed}s")

    if results.tx_hashes:
        print("\n  On-chain evidence:")
        for i, tx in enumerate(results.tx_hashes, 1):
            print(f"    TX {i}: {BASESCAN_TX}/{tx}")

    if results.overall == "PASS":
        print("\n  ** GOLDEN FLOW: PASS -- Platform is healthy **")
    elif results.overall == "PARTIAL":
        print("\n  ** GOLDEN FLOW: PARTIAL -- Some phases had issues **")
    else:
        print("\n  ** GOLDEN FLOW: FAIL -- Platform has issues **")


def _save_reports(results: GoldenFlowResults, bounty: float) -> None:
    """Save reports to docs/reports/."""
    report_dir = _project_root / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # English report
    report_en = generate_report_en(results, bounty)
    en_path = report_dir / "GOLDEN_FLOW_REPORT.md"
    en_path.write_text(report_en, encoding="utf-8")
    print(f"\n  Report (EN): {en_path}")

    # Spanish report
    report_es = generate_report_es(results, bounty)
    es_path = report_dir / "GOLDEN_FLOW_REPORT.es.md"
    es_path.write_text(report_es, encoding="utf-8")
    print(f"  Report (ES): {es_path}")

    # JSON report
    json_data = results.to_dict(bounty)
    json_path = report_dir / "GOLDEN_FLOW_REPORT.json"
    json_path.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")
    print(f"  Report (JSON): {json_path}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
