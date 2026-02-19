#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multichain Golden Flow -- E2E Acceptance Test across ALL deployed chains

Tests the COMPLETE platform flow on 7 blockchains (Fase 5 credit card model):
  Base, Polygon, Arbitrum, Avalanche, Monad, Celo, Optimism

For each chain: Task(balance-check) -> Lifecycle(escrow@assign) -> Payment(1-TX release) -> On-chain verification

Ethereum excluded: x402r-SDK factory label mismatch (pending fix from BackTrack).

Usage:
    python scripts/e2e_golden_flow_multichain.py
    python scripts/e2e_golden_flow_multichain.py --dry-run
    python scripts/e2e_golden_flow_multichain.py --bounty 0.05
    python scripts/e2e_golden_flow_multichain.py --networks base,polygon,arbitrum
    python scripts/e2e_golden_flow_multichain.py --skip-reputation

Environment:
    EM_API_KEY           -- Agent API key (optional when EM_REQUIRE_API_KEY=false)
    EM_API_URL           -- API base URL (default: https://api.execution.market)
    EM_WORKER_WALLET     -- Worker wallet (default: 0x52E0...)
    EM_WORKER_PRIVATE_KEY -- Worker private key (for on-chain reputation signing)
    EM_TEST_EXECUTOR_ID  -- Existing executor UUID (skips registration if set)

Cost: ~$0.10 per chain * 7 chains = ~$0.70 total
  Per chain: Worker receives bounty * 87%, Operator receives bounty * 13%
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
    "EM_WORKER_WALLET", "0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15"
)
TREASURY_WALLET = "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"
EXISTING_EXECUTOR_ID = os.environ.get("EM_TEST_EXECUTOR_ID", "")

# ERC-20 Transfer event topic
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Default bounty and fee (credit card model)
DEFAULT_BOUNTY = 0.10
PLATFORM_FEE_PCT = Decimal("0.13")
WORKER_PCT = Decimal("0.87")

EM_AGENT_ID = 2106


# ---------------------------------------------------------------------------
# Per-chain configuration
# ---------------------------------------------------------------------------
CHAIN_CONFIGS: Dict[str, Dict[str, Any]] = {
    "base": {
        "chain_id": 8453,
        "rpc_url": "https://mainnet.base.org",
        "usdc_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "operator": "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb",
        "explorer_tx": "https://basescan.org/tx",
        "display_name": "Base",
    },
    "polygon": {
        "chain_id": 137,
        "rpc_url": "https://polygon-bor-rpc.publicnode.com",
        "usdc_address": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "operator": "0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e",
        "explorer_tx": "https://polygonscan.com/tx",
        "display_name": "Polygon",
    },
    "arbitrum": {
        "chain_id": 42161,
        "rpc_url": "https://arb1.arbitrum.io/rpc",
        "usdc_address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "operator": "0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e",
        "explorer_tx": "https://arbiscan.io/tx",
        "display_name": "Arbitrum",
    },
    "avalanche": {
        "chain_id": 43114,
        "rpc_url": "https://api.avax.network/ext/bc/C/rpc",
        "usdc_address": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "operator": "0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e",
        "explorer_tx": "https://snowtrace.io/tx",
        "display_name": "Avalanche",
    },
    "monad": {
        "chain_id": 143,
        "rpc_url": "https://rpc.monad.xyz",
        "usdc_address": "0x754704Bc059F8C67012fEd69BC8A327a5aafb603",
        "operator": "0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3",
        "explorer_tx": "https://explorer.monad.xyz/tx",
        "display_name": "Monad",
    },
    "celo": {
        "chain_id": 42220,
        "rpc_url": "https://forno.celo.org",
        "usdc_address": "0xcebA9300f2b948710d2653dD7B07f33A8B32118C",
        "operator": "0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e",
        "explorer_tx": "https://celoscan.io/tx",
        "display_name": "Celo",
    },
    "optimism": {
        "chain_id": 10,
        "rpc_url": "https://mainnet.optimism.io",
        "usdc_address": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "operator": "0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e",
        "explorer_tx": "https://optimistic.etherscan.io/tx",
        "display_name": "Optimism",
    },
}

# Default: all chains with deployed operators
DEFAULT_NETWORKS = list(CHAIN_CONFIGS.keys())


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
# Result collectors
# ---------------------------------------------------------------------------
class ChainResult:
    """Result for a single chain's lifecycle test."""

    def __init__(self, network: str):
        self.network = network
        self.display_name = CHAIN_CONFIGS[network]["display_name"]
        self.chain_id = CHAIN_CONFIGS[network]["chain_id"]
        self.status = "PENDING"
        self.error: Optional[str] = None
        self.task_id: Optional[str] = None
        self.submission_id: Optional[str] = None
        self.escrow_tx: Optional[str] = None
        self.payment_tx: Optional[str] = None
        self.fee_distribute_tx: Optional[str] = None
        self.escrow_verified = False
        self.payment_verified = False
        self.worker_net_usdc: Optional[float] = None
        self.platform_fee_usdc: Optional[float] = None
        self.payment_mode: Optional[str] = None
        self.tx_hashes: List[str] = []
        self.start_time = time.time()
        self.elapsed_s = 0.0
        self.phases: Dict[str, str] = {}  # phase_name -> status

    def finish(self) -> None:
        self.elapsed_s = round(time.time() - self.start_time, 2)
        # Determine overall status from phases
        statuses = list(self.phases.values())
        if all(s == "PASS" for s in statuses):
            self.status = "PASS"
        elif any(s == "FAIL" for s in statuses):
            self.status = "FAIL"
        else:
            self.status = "PARTIAL"

    def add_tx(self, tx_hash: str) -> None:
        if tx_hash and tx_hash not in self.tx_hashes:
            self.tx_hashes.append(tx_hash)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "network": self.network,
            "display_name": self.display_name,
            "chain_id": self.chain_id,
            "status": self.status,
            "error": self.error,
            "elapsed_s": self.elapsed_s,
            "task_id": self.task_id,
            "escrow_tx": self.escrow_tx,
            "payment_tx": self.payment_tx,
            "fee_distribute_tx": self.fee_distribute_tx,
            "escrow_verified": self.escrow_verified,
            "payment_verified": self.payment_verified,
            "worker_net_usdc": self.worker_net_usdc,
            "platform_fee_usdc": self.platform_fee_usdc,
            "payment_mode": self.payment_mode,
            "tx_hashes": self.tx_hashes,
            "phases": self.phases,
        }


class MultichainResults:
    """Collects results across all chains."""

    def __init__(self):
        self.chains: Dict[str, ChainResult] = {}
        self.health_ok = False
        self.executor_id: Optional[str] = None
        self.reputation_status: Optional[str] = None
        self.start_time = time.time()

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.chains.values() if c.status == "PASS")

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.chains.values() if c.status == "FAIL")

    @property
    def total_txs(self) -> int:
        return sum(len(c.tx_hashes) for c in self.chains.values())

    @property
    def overall(self) -> str:
        if not self.chains:
            return "FAIL"
        if all(c.status == "PASS" for c in self.chains.values()):
            return "PASS"
        if self.fail_count == 0:
            return "PARTIAL"
        return "FAIL"

    def to_dict(self, bounty: float) -> Dict[str, Any]:
        fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
        worker_net = float(Decimal(str(bounty)) * WORKER_PCT)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_base": API_BASE,
            "fee_model": "credit_card",
            "bounty_per_chain_usd": bounty,
            "fee_per_chain_usd": fee,
            "worker_net_per_chain_usd": worker_net,
            "total_chains": len(self.chains),
            "total_cost_usd": bounty * len(self.chains),
            "worker_wallet": WORKER_WALLET,
            "treasury_wallet": TREASURY_WALLET,
            "health_ok": self.health_ok,
            "executor_id": self.executor_id,
            "reputation_status": self.reputation_status,
            "chains": {name: c.to_dict() for name, c in self.chains.items()},
            "overall": self.overall,
            "total_elapsed_s": round(time.time() - self.start_time, 2),
        }


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
# On-chain TX verification (per-chain RPC)
# ---------------------------------------------------------------------------
async def verify_tx_onchain(
    client: httpx.AsyncClient,
    tx_hash: str,
    rpc_url: str,
    usdc_address: str,
) -> Dict[str, Any]:
    """Verify a transaction on any chain via RPC and parse USDC Transfer events."""
    try:
        resp = await client.post(
            rpc_url,
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

        # Parse USDC Transfer events
        transfers = []
        for log in result.get("logs", []):
            topics = log.get("topics", [])
            if (
                len(topics) >= 3
                and topics[0].lower() == TRANSFER_TOPIC.lower()
                and log.get("address", "").lower() == usdc_address.lower()
            ):
                sender = "0x" + topics[1][-40:]
                receiver = "0x" + topics[2][-40:]
                raw_amount = int(log.get("data", "0x0"), 16)
                amount_usdc = raw_amount / 1_000_000
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
            "transfers": transfers,
            "block_number": int(result.get("blockNumber", "0x0"), 16),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Phase: Health & Config (once)
# ---------------------------------------------------------------------------
async def check_health(client: httpx.AsyncClient) -> bool:
    _print_header("HEALTH & CONFIG CHECK")
    try:
        health = await raw_get(client, "/health/")
        h_status = health.get("_http_status")
        print(f"  Health: HTTP {h_status} - {health.get('status', 'N/A')}")

        config = await api_call(client, "GET", "/config")
        networks = config.get("supported_networks", [])
        print(f"  Networks: {networks}")
        print(f"  Preferred: {config.get('preferred_network', 'N/A')}")

        if h_status != 200:
            print(f"  [FAIL] Health check failed: HTTP {h_status}")
            return False

        print("  [PASS] API is healthy")
        return True
    except Exception as e:
        print(f"  [FAIL] Health check error: {e}")
        return False


# ---------------------------------------------------------------------------
# Phase: Worker Registration (once)
# ---------------------------------------------------------------------------
async def register_worker(client: httpx.AsyncClient) -> Optional[str]:
    _print_header("WORKER REGISTRATION")

    if EXISTING_EXECUTOR_ID:
        print(f"  Using existing executor: {EXISTING_EXECUTOR_ID}")
        return EXISTING_EXECUTOR_ID

    try:
        print("  Registering worker...")
        url = f"{API_BASE}/api/v1/executors/register"
        resp = await client.post(
            url,
            json={
                "wallet_address": WORKER_WALLET,
                "display_name": "Multichain Golden Flow Test Worker",
            },
            headers=_auth_headers(),
        )
        try:
            reg_data = resp.json()
        except Exception:
            reg_data = {"raw": resp.text}

        if resp.status_code not in (200, 201):
            print(f"  [FAIL] Registration: HTTP {resp.status_code}")
            return None

        executor_obj = reg_data.get("executor", {})
        executor_id = executor_obj.get("id", "")
        print(f"  Executor ID: {executor_id}")
        print(f"  Created: {reg_data.get('created', False)}")
        print("  [PASS] Worker registered")
        return executor_id
    except Exception as e:
        print(f"  [FAIL] Registration error: {e}")
        return None


# ---------------------------------------------------------------------------
# Per-chain lifecycle test
# ---------------------------------------------------------------------------
async def test_chain(
    client: httpx.AsyncClient,
    network: str,
    executor_id: str,
    bounty: float,
) -> ChainResult:
    """Run the full task lifecycle on a single chain."""
    chain_cfg = CHAIN_CONFIGS[network]
    result = ChainResult(network)
    explorer = chain_cfg["explorer_tx"]
    rpc_url = chain_cfg["rpc_url"]
    usdc_addr = chain_cfg["usdc_address"]

    _print_header(f"CHAIN: {chain_cfg['display_name']} (chain {chain_cfg['chain_id']})")
    print(f"    Operator:  {chain_cfg['operator']}")
    print(f"    USDC:      {usdc_addr}")
    print(f"    RPC:       {rpc_url}")
    print(f"    Bounty:    ${bounty:.2f}")

    # --- Step 1: Create task ---
    print(f"\n  [1/5] Creating task on {network}...")
    try:
        task_data = await api_call(
            client,
            "POST",
            "/tasks",
            {
                "title": f"[MULTICHAIN GF] {chain_cfg['display_name']} - {ts_short()}",
                "instructions": f"Multichain golden flow test on {network}. Respond: golden_flow_{network}",
                "category": "simple_action",
                "bounty_usd": bounty,
                "deadline_hours": 1,
                "evidence_required": ["text_response"],
                "location_hint": "Any location",
                "payment_network": network,
                "payment_token": "USDC",
            },
        )
        http_status = task_data.get("_http_status")
        print(f"         HTTP {http_status}")

        if http_status != 201:
            err = task_data.get("detail", task_data.get("error", str(task_data)[:200]))
            print(f"         [FAIL] {err}")
            result.error = f"Task creation failed: HTTP {http_status} - {err}"
            result.phases["create"] = "FAIL"
            result.finish()
            return result

        task_id = task_data.get("id")
        result.task_id = task_id
        print(f"         Task ID: {task_id}")
        print(f"         Status:  {task_data.get('status')}")
        result.phases["create"] = "PASS"
    except Exception as e:
        result.error = f"Task creation error: {e}"
        result.phases["create"] = "FAIL"
        result.finish()
        return result

    await asyncio.sleep(1)

    # --- Step 2: Worker applies ---
    print("\n  [2/5] Worker applying...")
    try:
        apply_data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/apply",
            {
                "executor_id": executor_id,
                "message": f"Multichain GF test -- {network}",
            },
        )
        apply_status = apply_data.get("_http_status")
        print(f"         HTTP {apply_status}")

        if apply_status not in (200, 201):
            err = apply_data.get("detail", str(apply_data)[:200])
            print(f"         [FAIL] {err}")
            result.error = f"Apply failed: {err}"
            result.phases["apply"] = "FAIL"
            result.finish()
            return result

        result.phases["apply"] = "PASS"
    except Exception as e:
        result.error = f"Apply error: {e}"
        result.phases["apply"] = "FAIL"
        result.finish()
        return result

    await asyncio.sleep(1)

    # --- Step 3: Assign worker (escrow lock) ---
    print(f"\n  [3/5] Assigning worker (+ escrow lock on {network})...")
    try:
        assign_data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/assign",
            {
                "executor_id": executor_id,
                "notes": f"Multichain GF assignment -- {network}",
            },
        )
        assign_status = assign_data.get("_http_status")
        print(f"         HTTP {assign_status}")

        if assign_status not in (200, 201):
            err = assign_data.get("detail", str(assign_data)[:200])
            print(f"         [FAIL] {err}")
            result.error = f"Assign failed: {err}"
            result.phases["assign"] = "FAIL"
            result.finish()
            return result

        # Extract escrow info
        assign_resp = assign_data.get("data") or {}
        escrow_info = assign_resp.get("escrow") or {}
        escrow_tx = escrow_info.get("escrow_tx")
        result.payment_mode = escrow_info.get("escrow_mode")

        if escrow_tx:
            result.escrow_tx = escrow_tx
            result.add_tx(escrow_tx)
            print(f"         Escrow TX: {escrow_tx}")
            print(f"         Mode:      {result.payment_mode}")
            print(f"         Explorer:  {explorer}/{escrow_tx}")

            # Verify on-chain
            receipt = await verify_tx_onchain(client, escrow_tx, rpc_url, usdc_addr)
            result.escrow_verified = receipt.get("success", False)
            print(
                f"         On-chain:  {'SUCCESS' if result.escrow_verified else 'FAILED'}"
            )
            if receipt.get("transfers"):
                for t in receipt["transfers"]:
                    print(
                        f"         Transfer:  ...{t['from'][-6:]} -> ...{t['to'][-6:]} : ${t['amount_usdc']:.6f}"
                    )
        else:
            print("         No escrow TX returned (may be balance-check only mode)")
            result.escrow_verified = True  # No TX to verify

        result.phases["assign"] = "PASS"
    except Exception as e:
        result.error = f"Assign error: {e}"
        result.phases["assign"] = "FAIL"
        result.finish()
        return result

    await asyncio.sleep(1)

    # --- Step 4: Submit evidence ---
    print("\n  [4/5] Submitting evidence...")
    try:
        submit_data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/submit",
            {
                "executor_id": executor_id,
                "evidence": {"text_response": f"golden_flow_{network}_complete"},
                "notes": f"Multichain GF submission -- {network}",
            },
        )
        submit_status = submit_data.get("_http_status")
        print(f"         HTTP {submit_status}")

        if submit_status not in (200, 201):
            err = submit_data.get("detail", str(submit_data)[:200])
            print(f"         [FAIL] {err}")
            result.error = f"Submit failed: {err}"
            result.phases["submit"] = "FAIL"
            result.finish()
            return result

        submission_id = (submit_data.get("data") or {}).get("submission_id")
        if not submission_id:
            # Fallback: query submissions
            subs_data = await api_call(client, "GET", f"/tasks/{task_id}/submissions")
            subs_list = subs_data.get("submissions") or subs_data.get("data") or []
            if isinstance(subs_list, list) and subs_list:
                submission_id = subs_list[0].get("id")

        if not submission_id:
            result.error = "No submission ID after submit"
            result.phases["submit"] = "FAIL"
            result.finish()
            return result

        result.submission_id = submission_id
        print(f"         Submission: {submission_id}")
        result.phases["submit"] = "PASS"
    except Exception as e:
        result.error = f"Submit error: {e}"
        result.phases["submit"] = "FAIL"
        result.finish()
        return result

    await asyncio.sleep(2)

    # --- Step 5: Approve + verify payment ---
    print(f"\n  [5/5] Approving submission (payment release on {network})...")
    try:
        t0 = time.time()
        approve_data = await api_call(
            client,
            "POST",
            f"/submissions/{submission_id}/approve",
            {
                "notes": f"Multichain GF approval -- {network}",
                "rating_score": 90,
            },
        )
        t_approve = time.time() - t0
        approve_status = approve_data.get("_http_status")
        print(f"         HTTP {approve_status} ({t_approve:.2f}s)")

        if approve_status != 200:
            err = approve_data.get(
                "detail", approve_data.get("error", str(approve_data)[:200])
            )
            print(f"         [FAIL] {err}")
            result.error = f"Approval failed: HTTP {approve_status} - {err}"
            result.phases["approve"] = "FAIL"
            result.finish()
            return result

        resp_data = approve_data.get("data") or {}
        payment_tx = resp_data.get("payment_tx")
        fee_distribute_tx = resp_data.get("fee_distribute_tx")
        escrow_release_tx = resp_data.get("escrow_release_tx")
        result.worker_net_usdc = resp_data.get("worker_net_usdc")
        result.platform_fee_usdc = resp_data.get("platform_fee_usdc")
        result.payment_mode = resp_data.get("payment_mode", result.payment_mode)

        if payment_tx:
            result.payment_tx = payment_tx
            result.add_tx(payment_tx)
        if escrow_release_tx and escrow_release_tx != payment_tx:
            result.add_tx(escrow_release_tx)
        if fee_distribute_tx:
            result.fee_distribute_tx = fee_distribute_tx
            result.add_tx(fee_distribute_tx)

        print(f"         Mode:     {result.payment_mode}")
        if payment_tx:
            print(f"         Release:  {payment_tx}")
            print(f"         Explorer: {explorer}/{payment_tx}")
        if fee_distribute_tx:
            print(f"         Fee dist: {fee_distribute_tx}")
        if result.worker_net_usdc is not None:
            print(f"         Worker:   ${result.worker_net_usdc:.6f} (87%)")
        if result.platform_fee_usdc is not None:
            print(f"         Fee:      ${result.platform_fee_usdc:.6f} (13%)")

        # Verify payment TX on-chain
        if payment_tx:
            receipt = await verify_tx_onchain(client, payment_tx, rpc_url, usdc_addr)
            result.payment_verified = receipt.get("success", False)
            print(
                f"         On-chain: {'SUCCESS' if result.payment_verified else 'FAILED'}"
            )
            if receipt.get("transfers"):
                for t in receipt["transfers"]:
                    print(
                        f"         Transfer: ...{t['from'][-6:]} -> ...{t['to'][-6:]} : ${t['amount_usdc']:.6f}"
                    )
        else:
            print("         No payment TX to verify")

        # Fee math check
        expected_worker = float(Decimal(str(bounty)) * WORKER_PCT)
        expected_fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
        fee_ok = True
        if result.worker_net_usdc is not None:
            if abs(result.worker_net_usdc - expected_worker) > 0.002:
                fee_ok = False
                print(
                    f"         FEE MISMATCH: worker got ${result.worker_net_usdc:.6f}, expected ${expected_worker:.6f}"
                )
        if result.platform_fee_usdc is not None:
            if abs(result.platform_fee_usdc - expected_fee) > 0.002:
                fee_ok = False
                print(
                    f"         FEE MISMATCH: fee is ${result.platform_fee_usdc:.6f}, expected ${expected_fee:.6f}"
                )

        if fee_ok:
            print("         Fee math: OK")

        has_payment = bool(payment_tx)
        if has_payment and result.payment_verified and fee_ok:
            result.phases["approve"] = "PASS"
        elif has_payment and not fee_ok:
            result.phases["approve"] = "PARTIAL"
        else:
            result.phases["approve"] = "PARTIAL" if has_payment else "FAIL"

    except Exception as e:
        result.error = f"Approval error: {e}"
        result.phases["approve"] = "FAIL"

    result.finish()

    # Print chain summary
    icon = _icon(result.status == "PASS")
    if result.status == "PARTIAL":
        icon = "PARTIAL"
    print(
        f"\n  [{icon}] {chain_cfg['display_name']}: {result.status} ({result.elapsed_s}s)"
    )
    if result.error:
        print(f"         Error: {result.error}")

    return result


# ---------------------------------------------------------------------------
# Reputation phase (once, on Base)
# ---------------------------------------------------------------------------
async def test_reputation(
    client: httpx.AsyncClient,
    task_id: str,
) -> str:
    """Test bidirectional reputation using the first successful task (on Base)."""
    _print_header("REPUTATION (Base, bidirectional)")

    status = "SKIP"

    # Agent rates worker
    print("  [1/2] Agent rating worker (score: 90)...")
    try:
        rate_data = await api_call(
            client,
            "POST",
            "/reputation/workers/rate",
            {
                "task_id": task_id,
                "score": 90,
                "comment": "Multichain Golden Flow -- excellent work",
            },
        )
        rw_status = rate_data.get("_http_status")
        rw_success = rate_data.get("success", False)
        rw_tx = rate_data.get("transaction_hash")
        print(f"         HTTP {rw_status}, success={rw_success}")
        if rw_tx:
            print(f"         TX: {rw_tx}")
    except Exception as e:
        print(f"         Error: {e}")
        rw_success = False

    # Worker rates agent (prepare-feedback flow)
    print("  [2/2] Worker preparing feedback for agent (score: 85)...")
    ra_success = False
    try:
        prepare_data = await api_call(
            client,
            "POST",
            "/reputation/prepare-feedback",
            {
                "agent_id": EM_AGENT_ID,
                "task_id": task_id,
                "score": 85,
                "comment": "Multichain Golden Flow -- great agent",
                "worker_address": WORKER_WALLET,
            },
        )
        prep_status = prepare_data.get("_http_status")
        print(f"         HTTP {prep_status}")

        if prep_status == 200:
            worker_private_key = os.environ.get("EM_WORKER_PRIVATE_KEY", "")
            if worker_private_key:
                print("         Signing giveFeedback() on-chain...")
                try:
                    from web3 import Web3

                    try:
                        from web3.middleware import ExtraDataToPOAMiddleware as _poa
                    except ImportError:
                        from web3.middleware import geth_poa_middleware as _poa

                    rpc_url = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
                    w3 = Web3(Web3.HTTPProvider(rpc_url))
                    try:
                        w3.middleware_onion.inject(_poa, layer=0)
                    except Exception:
                        pass

                    GIVE_FEEDBACK_ABI = [
                        {
                            "inputs": [
                                {"name": "agentId", "type": "uint256"},
                                {"name": "value", "type": "int128"},
                                {"name": "valueDecimals", "type": "uint8"},
                                {"name": "tag1", "type": "string"},
                                {"name": "tag2", "type": "string"},
                                {"name": "endpoint", "type": "string"},
                                {"name": "feedbackURI", "type": "string"},
                                {"name": "feedbackHash", "type": "bytes32"},
                            ],
                            "name": "giveFeedback",
                            "outputs": [],
                            "stateMutability": "nonpayable",
                            "type": "function",
                        }
                    ]

                    contract_address = prepare_data.get("contract_address", "")
                    registry = w3.eth.contract(
                        address=Web3.to_checksum_address(contract_address),
                        abi=GIVE_FEEDBACK_ABI,
                    )

                    acct = w3.eth.account.from_key(worker_private_key)
                    nonce = w3.eth.get_transaction_count(acct.address, "pending")

                    agent_id_param = prepare_data.get("agent_id", EM_AGENT_ID)
                    value_param = prepare_data.get("value", 85)
                    tag1 = prepare_data.get("tag1", "agent_rating")
                    tag2 = prepare_data.get("tag2", "execution-market")
                    endpoint_param = prepare_data.get("endpoint", f"task:{task_id}")
                    feedback_uri = prepare_data.get("feedback_uri", "")
                    feedback_hash = prepare_data.get("feedback_hash", "0x" + "00" * 32)

                    if isinstance(feedback_hash, str):
                        fb_hash_bytes = bytes.fromhex(
                            feedback_hash.replace("0x", "").ljust(64, "0")
                        )
                    else:
                        fb_hash_bytes = feedback_hash

                    tx = registry.functions.giveFeedback(
                        agent_id_param,
                        value_param,
                        0,
                        tag1,
                        tag2,
                        endpoint_param,
                        feedback_uri,
                        fb_hash_bytes,
                    ).build_transaction(
                        {
                            "from": acct.address,
                            "nonce": nonce,
                            "gas": 250000,
                            "maxFeePerGas": w3.to_wei(0.5, "gwei"),
                            "maxPriorityFeePerGas": w3.to_wei(0.1, "gwei"),
                            "chainId": 8453,
                        }
                    )

                    signed = acct.sign_transaction(tx)
                    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                    ra_tx = tx_hash.hex()
                    print(f"         TX: {ra_tx}")

                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    if receipt["status"] == 1:
                        print(f"         Confirmed! Gas: {receipt['gasUsed']}")
                        ra_success = True

                        # Confirm with API
                        prepare_id = prepare_data.get("prepare_id", "")
                        await api_call(
                            client,
                            "POST",
                            "/reputation/confirm-feedback",
                            {
                                "prepare_id": prepare_id,
                                "task_id": task_id,
                                "tx_hash": ra_tx,
                            },
                        )
                    else:
                        print("         TX reverted on-chain")
                except Exception as e:
                    print(f"         On-chain error: {e}")
            else:
                print(
                    "         EM_WORKER_PRIVATE_KEY not set -- skipping on-chain signing"
                )
    except Exception as e:
        print(f"         Error: {e}")

    if rw_success and ra_success:
        status = "PASS"
    elif rw_success or ra_success:
        status = "PARTIAL"
    else:
        status = "FAIL"

    print(f"\n  [{'PASS' if status == 'PASS' else status}] Reputation: {status}")
    return status


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(results: MultichainResults, bounty: float) -> str:
    """Generate the multichain report in English."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    overall = results.overall
    total_chains = len(results.chains)
    fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
    worker_net = float(Decimal(str(bounty)) * WORKER_PCT)

    lines = [
        "# Multichain Golden Flow Report",
        "",
        f"> **Date**: {now}",
        f"> **API**: `{API_BASE}`",
        "> **Fee Model**: credit_card (fee deducted from bounty on-chain)",
        "> **Escrow Mode**: direct_release (Fase 5, 1-TX release)",
        f"> **Chains tested**: {total_chains}",
        f"> **Result**: **{overall}**",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"Tested the complete Execution Market lifecycle across **{total_chains} blockchains** ",
        f"using the Fase 5 credit card model. {results.pass_count}/{total_chains} chains passed.",
        "",
        f"**Overall Result: {overall}**",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Bounty per chain | ${bounty:.2f} USDC |",
        f"| Worker net (87%) | ${worker_net:.6f} USDC |",
        f"| Fee (13%) | ${fee:.6f} USDC |",
        f"| Total cost | ${bounty * total_chains:.2f} USDC |",
        f"| Total on-chain TXs | {results.total_txs} |",
        f"| Reputation | {results.reputation_status or 'N/A'} |",
        "",
        "---",
        "",
        "## Results by Chain",
        "",
        "| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |",
        "|-------|----------|--------|-----------|------------|------------|------|",
    ]

    for name, cr in results.chains.items():
        cfg = CHAIN_CONFIGS[name]
        explorer = cfg["explorer_tx"]
        esc = f"[View]({explorer}/{cr.escrow_tx})" if cr.escrow_tx else "N/A"
        pay = f"[View]({explorer}/{cr.payment_tx})" if cr.payment_tx else "N/A"
        wn = f"${cr.worker_net_usdc:.6f}" if cr.worker_net_usdc is not None else "N/A"
        lines.append(
            f"| **{cr.display_name}** | {cr.chain_id} | **{cr.status}** | {esc} | {pay} | {wn} | {cr.elapsed_s}s |"
        )

    lines.extend(["", "---", ""])

    # Per-chain details
    for name, cr in results.chains.items():
        cfg = CHAIN_CONFIGS[name]
        explorer = cfg["explorer_tx"]
        lines.append(f"### {cr.display_name} (chain {cr.chain_id})")
        lines.append("")
        lines.append(f"- **Status**: {cr.status}")
        lines.append(f"- **Operator**: `{cfg['operator']}`")
        lines.append(f"- **USDC**: `{cfg['usdc_address']}`")
        if cr.error:
            lines.append(f"- **Error**: {cr.error}")
        if cr.task_id:
            lines.append(f"- **Task ID**: `{cr.task_id}`")
        if cr.payment_mode:
            lines.append(f"- **Payment Mode**: `{cr.payment_mode}`")

        # Phase breakdown
        if cr.phases:
            lines.append("")
            lines.append("| Phase | Status |")
            lines.append("|-------|--------|")
            for phase_name, phase_status in cr.phases.items():
                lines.append(f"| {phase_name} | {phase_status} |")

        # TX list
        if cr.tx_hashes:
            lines.append("")
            lines.append("**Transactions:**")
            for i, tx in enumerate(cr.tx_hashes, 1):
                lines.append(f"- TX {i}: [`{tx[:20]}...`]({explorer}/{tx})")

        # Fee math
        if cr.worker_net_usdc is not None and cr.platform_fee_usdc is not None:
            lines.append("")
            exp_w = float(Decimal(str(bounty)) * WORKER_PCT)
            exp_f = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)
            w_ok = "YES" if abs(cr.worker_net_usdc - exp_w) < 0.002 else "NO"
            f_ok = "YES" if abs(cr.platform_fee_usdc - exp_f) < 0.002 else "NO"
            lines.append("| Metric | Expected | Actual | Match |")
            lines.append("|--------|----------|--------|-------|")
            lines.append(
                f"| Worker (87%) | ${exp_w:.6f} | ${cr.worker_net_usdc:.6f} | {w_ok} |"
            )
            lines.append(
                f"| Fee (13%) | ${exp_f:.6f} | ${cr.platform_fee_usdc:.6f} | {f_ok} |"
            )

        lines.append("")

    # Invariants
    lines.extend(["---", "", "## Invariants Verified", ""])
    for name, cr in results.chains.items():
        if cr.status == "PASS":
            lines.append(
                f"- [x] {cr.display_name}: Full lifecycle (create -> escrow -> release -> verify)"
            )
        elif cr.status == "PARTIAL":
            lines.append(f"- [~] {cr.display_name}: Partial (some phases incomplete)")
        else:
            lines.append(f"- [ ] {cr.display_name}: Failed ({cr.error or 'unknown'})")

    if results.reputation_status == "PASS":
        lines.append("- [x] Bidirectional reputation (agent<->worker) on Base")
    elif results.reputation_status == "PARTIAL":
        lines.append("- [~] Reputation: partial (one direction only)")
    elif results.reputation_status:
        lines.append(f"- [ ] Reputation: {results.reputation_status}")

    lines.extend(["", "---", "", "## Excluded Chains", ""])
    lines.append(
        "- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). "
        "See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues)."
    )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> int:
    bounty = DEFAULT_BOUNTY
    dry_run = "--dry-run" in sys.argv
    skip_reputation = "--skip-reputation" in sys.argv

    # Parse --bounty
    for i, arg in enumerate(sys.argv):
        if arg == "--bounty" and i + 1 < len(sys.argv):
            try:
                bounty = float(sys.argv[i + 1])
            except ValueError:
                print(f"Invalid bounty: {sys.argv[i + 1]}")
                return 1

    # Parse --networks
    networks = DEFAULT_NETWORKS
    for i, arg in enumerate(sys.argv):
        if arg == "--networks" and i + 1 < len(sys.argv):
            networks = [n.strip() for n in sys.argv[i + 1].split(",") if n.strip()]
            invalid = [n for n in networks if n not in CHAIN_CONFIGS]
            if invalid:
                print(f"Unknown networks: {invalid}")
                print(f"Available: {list(CHAIN_CONFIGS.keys())}")
                return 1

    total_cost = bounty * len(networks)

    print("=" * 72)
    print("  MULTICHAIN GOLDEN FLOW -- E2E across all deployed chains")
    print("=" * 72)
    _print_kv("API", API_BASE, 2)
    _print_kv("Time", ts(), 2)
    _print_kv("Fee model", "credit_card (Fase 5)", 2)
    _print_kv("Bounty/chain", f"${bounty:.2f} USDC", 2)
    _print_kv("Chains", f"{len(networks)}: {', '.join(networks)}", 2)
    _print_kv("Total cost", f"${total_cost:.2f} USDC", 2)
    _print_kv("Worker", WORKER_WALLET, 2)
    _print_kv("Reputation", "skip" if skip_reputation else "Base only", 2)
    _print_kv("Auth", "API key set" if API_KEY else "Anonymous", 2)
    _print_kv("Dry run", dry_run, 2)

    if dry_run:
        print("\nDRY RUN -- config shown above. Remove --dry-run to execute.")
        print("\nChain details:")
        for net in networks:
            cfg = CHAIN_CONFIGS[net]
            print(
                f"  {cfg['display_name']:12s} chain={cfg['chain_id']:>5d}  operator={cfg['operator']}"
            )
        return 0

    results = MultichainResults()

    timeout = httpx.Timeout(180.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Phase 1: Health check
        results.health_ok = await check_health(client)
        if not results.health_ok:
            print("\n  [ABORT] Health check failed. Cannot continue.")
            return 1

        # Phase 2: Worker registration
        executor_id = await register_worker(client)
        if not executor_id:
            print("\n  [ABORT] Worker registration failed.")
            return 1
        results.executor_id = executor_id

        await asyncio.sleep(2)

        # Phase 3: Per-chain lifecycle tests
        for i, network in enumerate(networks, 1):
            print(f"\n{'#' * 72}")
            print(
                f"  CHAIN {i}/{len(networks)}: {CHAIN_CONFIGS[network]['display_name']}"
            )
            print(f"{'#' * 72}")

            chain_result = await test_chain(client, network, executor_id, bounty)
            results.chains[network] = chain_result

            # Brief pause between chains
            if i < len(networks):
                print("\n  Waiting 3s before next chain...")
                await asyncio.sleep(3)

        # Phase 4: Reputation (optional, uses first successful Base task)
        if not skip_reputation:
            # Find a Base task for reputation (or first successful task)
            rep_task_id = None
            if "base" in results.chains and results.chains["base"].task_id:
                rep_task_id = results.chains["base"].task_id
            else:
                for cr in results.chains.values():
                    if cr.task_id and cr.status == "PASS":
                        rep_task_id = cr.task_id
                        break

            if rep_task_id:
                await asyncio.sleep(3)
                results.reputation_status = await test_reputation(client, rep_task_id)
            else:
                print("\n  [SKIP] No successful task for reputation testing")
                results.reputation_status = "SKIP"
        else:
            results.reputation_status = "SKIP"

    # Print summary
    _print_summary(results, bounty)

    # Save reports
    _save_reports(results, bounty)

    return 0 if results.fail_count == 0 else 1


def _print_summary(results: MultichainResults, bounty: float) -> None:
    total_elapsed = round(time.time() - results.start_time, 2)

    _print_header("MULTICHAIN GOLDEN FLOW SUMMARY")
    print(f"  Overall:    {results.overall}")
    print(
        f"  Chains:     {len(results.chains)} tested | "
        f"{results.pass_count} passed | "
        f"{results.fail_count} failed"
    )
    print(f"  On-chain:   {results.total_txs} transactions")
    print(f"  Reputation: {results.reputation_status}")
    print(f"  Elapsed:    {total_elapsed}s")

    print("\n  Per-chain results:")
    for name, cr in results.chains.items():
        icon = _icon(cr.status == "PASS")
        if cr.status == "PARTIAL":
            icon = "PARTIAL"
        tx_count = len(cr.tx_hashes)
        print(
            f"    [{icon}] {cr.display_name:12s} {cr.status:8s} ({cr.elapsed_s}s, {tx_count} TXs)"
        )
        if cr.error:
            print(f"           Error: {cr.error}")

    if results.total_txs > 0:
        print("\n  All on-chain transactions:")
        idx = 1
        for name, cr in results.chains.items():
            cfg = CHAIN_CONFIGS[name]
            for tx in cr.tx_hashes:
                print(
                    f"    TX {idx}: [{cfg['display_name']}] {cfg['explorer_tx']}/{tx}"
                )
                idx += 1

    if results.overall == "PASS":
        print("\n  ** MULTICHAIN GOLDEN FLOW: PASS -- All chains healthy **")
    elif results.overall == "PARTIAL":
        print("\n  ** MULTICHAIN GOLDEN FLOW: PARTIAL -- Some chains had issues **")
    else:
        print("\n  ** MULTICHAIN GOLDEN FLOW: FAIL -- Some chains failed **")


def _save_reports(results: MultichainResults, bounty: float) -> None:
    report_dir = _project_root / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Markdown report
    report_md = generate_report(results, bounty)
    md_path = report_dir / "MULTICHAIN_GOLDEN_FLOW_REPORT.md"
    md_path.write_text(report_md, encoding="utf-8")
    print(f"\n  Report (MD):   {md_path}")

    # JSON report
    json_data = results.to_dict(bounty)
    json_path = report_dir / "MULTICHAIN_GOLDEN_FLOW_REPORT.json"
    json_path.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")
    print(f"  Report (JSON): {json_path}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
