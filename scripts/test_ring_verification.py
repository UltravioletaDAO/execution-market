#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ring 1 + Ring 2 Verification E2E Test

Tests the dual-ring SQS+Lambda verification pipeline end-to-end:
  Ring 1 (PHOTINT): forensic authenticity check on a real photo
  Ring 2 (Arbiter): semantic task-completion check

Flow:
  1. Create task with photo evidence requirement
  2. Register / reuse test worker
  3. Apply + assign (triggers on-chain escrow via agent wallet)
  4. Submit evidence with a REAL photo URL
  5. Poll Ring 1 Lambda result (~30-90s)
  6. Poll Ring 2 Lambda result (~60-150s)
  7. Report full verdict (score, tier, hashes, auto-release/refund decision)

Usage:
    python scripts/test_ring_verification.py
    python scripts/test_ring_verification.py --no-payment   # Skip escrow, submit only
    python scripts/test_ring_verification.py --photo-url URL  # Custom photo URL
    python scripts/test_ring_verification.py --network skale  # Use SKALE (free gas)

Environment:
    WALLET_PRIVATE_KEY    -- Agent wallet (signs escrow)
    EM_WORKER_WALLET      -- Worker wallet address
    EM_WORKER_PRIVATE_KEY -- Worker private key (for ERC-8004 sign)
    EM_TEST_EXECUTOR_ID   -- Existing executor ID (skips registration)
    EM_API_URL            -- API base (default: https://api.execution.market)

Cost: ~$0.05 USDC per run (bounty $0.05, credit card model)
"""

import asyncio
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

# Add mcp_server to path so we can import the ERC-8128 signer
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))

# Windows UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / "mcp_server" / ".env")
load_dotenv(_project_root / ".env.local")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = os.environ.get("EM_API_URL", "https://api.execution.market").rstrip("/")
API_KEY = os.environ.get("EM_API_KEY", "")
EXISTING_EXECUTOR_ID = os.environ.get("EM_TEST_EXECUTOR_ID", "")
AGENT_PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY", "")
WORKER_PRIVATE_KEY = os.environ.get("EM_WORKER_PRIVATE_KEY", "")

# Derive worker wallet address from private key if not explicitly set
_worker_wallet_raw = os.environ.get("EM_WORKER_WALLET", "")
if not _worker_wallet_raw and WORKER_PRIVATE_KEY:
    try:
        from eth_account import Account as _Acct
        _worker_wallet_raw = _Acct.from_key(WORKER_PRIVATE_KEY).address
    except Exception:
        pass
WORKER_WALLET = _worker_wallet_raw

TEST_BOUNTY = 0.05
TEST_NETWORK = "base"

# Public JPEG photo — Wikimedia Commons, real outdoor photo, no EXIF strip
# Fits task "Take a photo of a natural outdoor scene"
DEFAULT_PHOTO_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/"
    "Sunflower_from_Silesia2.jpg/800px-Sunflower_from_Silesia2.jpg"
)

# Polling config
# Ring 1 Lambda can take up to 5 minutes (image download + 5 AI model calls)
RING1_POLL_INTERVAL = 15   # seconds between polls
RING1_TIMEOUT = 360        # max seconds to wait for Ring 1 (6 min)
RING2_POLL_INTERVAL = 15
RING2_TIMEOUT = 180        # max additional seconds after Ring 1 for Ring 2 (3 min)

BASESCAN_TX = "https://basescan.org/tx"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def ts_short() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


def _h(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def _kv(k: str, v: Any, indent: int = 4) -> None:
    print(f"{' ' * indent}{k}: {v}")


def _auth_headers() -> Dict[str, str]:
    """Legacy API key headers — only used if API_KEY is explicitly set."""
    headers: Dict[str, str] = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
        headers["X-API-Key"] = API_KEY
    return headers


async def _erc8128_headers(
    method: str,
    url: str,
    body_str: Optional[str],
    private_key: str,
    chain_id: int = 8453,
) -> Dict[str, str]:
    """Build ERC-8128 signature headers for a single request.

    Fetches a fresh nonce and signs the request per ERC-8128 (Signed HTTP
    Requests with Ethereum). Required because API key auth is disabled in
    production (EM_API_KEYS_ENABLED=false).
    """
    from integrations.erc8128.signer import sign_request, fetch_nonce

    nonce = await fetch_nonce(API_BASE)
    sig_headers = sign_request(
        private_key=private_key,
        method=method.upper(),
        url=url,
        body=body_str,
        nonce=nonce,
        chain_id=chain_id,
    )
    return sig_headers


async def api(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    body: Optional[dict] = None,
) -> dict:
    """Call /api/v1/* with ERC-8128 wallet signing (agent wallet)."""
    url = f"{API_BASE}/api/v1{path}"
    headers = _auth_headers()

    body_str: Optional[str] = None
    if body is not None:
        body_str = json.dumps(body, separators=(",", ":"))
        headers["Content-Type"] = "application/json"

    # ERC-8128 wallet signing (primary auth)
    if AGENT_PRIVATE_KEY and not API_KEY:
        try:
            sig_headers = await _erc8128_headers(method, url, body_str, AGENT_PRIVATE_KEY)
            headers.update(sig_headers)
        except Exception as e:
            print(f"         [WARN] ERC-8128 signing failed: {e} — proceeding without sig")

    if body_str is not None:
        resp = await client.request(
            method, url, content=body_str, headers=headers
        )
    else:
        resp = await client.request(method, url, headers=headers)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    data["_status"] = resp.status_code
    return data


# ---------------------------------------------------------------------------
# Escrow signing (reuses golden flow logic)
# ---------------------------------------------------------------------------
def sign_escrow(worker_wallet: str, bounty_usd: float, network: str) -> Dict[str, Any]:
    """Sign escrow authorization on-chain and return escrow_tx + payment_info."""
    # Import SDK lazily (only needed when AGENT_PRIVATE_KEY is set)
    from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient, TaskTier

    # Network config — mirrors golden flow CHAIN_CONFIGS
    network_configs = {
        "base": {
            "chain_id": 8453,
            "rpc_url": os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
            "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "escrow": "0xb9488351E48b23D798f24e8174514F28B741Eb4f",
            "operator": "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb",
            "token_collector": "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8",
        },
        "skale": {
            "chain_id": 1564830818,
            "rpc_url": os.environ.get(
                "SKALE_RPC_URL",
                "https://mainnet.skalenodes.com/v1/elated-tan-skat",
            ),
            "usdc": "0x7Cf76E740Cb23b99337b21F392F22c47Ad910c67",
            "escrow": "0xBC151792f80C0EB1973d56b0235e6bee2A60e245",
            "operator": "0x43E46d4587fCCc382285C52012227555ed78D183",
            "token_collector": "0x43E46d4587fCCc382285C52012227555ed78D183",
        },
    }

    cfg = network_configs.get(network, network_configs["base"])
    escrow_client = AdvancedEscrowClient(
        private_key=AGENT_PRIVATE_KEY,
        chain_id=cfg["chain_id"],
        rpc_url=cfg["rpc_url"],
        contracts={
            "usdc": cfg["usdc"],
            "escrow": cfg["escrow"],
            "operator": cfg["operator"],
            "token_collector": cfg["token_collector"],
        },
    )

    bounty_atomic = int(bounty_usd * 1_000_000)
    pi = escrow_client.build_payment_info(
        receiver=worker_wallet,
        amount=bounty_atomic,
        tier=TaskTier.MICRO,
        max_fee_bps=1800,
    )
    result = escrow_client.authorize(pi)
    if not result.success:
        raise RuntimeError(f"Escrow authorize failed: {result.error}")

    from eth_account import Account

    agent_address = Account.from_key(AGENT_PRIVATE_KEY).address

    payment_info = {
        "mode": "fase2",
        "payer": agent_address,
        "operator": pi.operator,
        "receiver": pi.receiver,
        "token": pi.token,
        "max_amount": pi.max_amount,
        "pre_approval_expiry": pi.pre_approval_expiry,
        "authorization_expiry": pi.authorization_expiry,
        "refund_expiry": pi.refund_expiry,
        "min_fee_bps": pi.min_fee_bps,
        "max_fee_bps": pi.max_fee_bps,
        "fee_receiver": pi.fee_receiver,
        "salt": pi.salt,
    }

    return {
        "escrow_tx": result.transaction_hash,
        "payment_info": payment_info,
        "agent_address": agent_address,
    }


# ---------------------------------------------------------------------------
# Phase 1: Register / reuse worker
# ---------------------------------------------------------------------------
async def register_worker(client: httpx.AsyncClient) -> str:
    """Return executor_id (create if needed)."""
    if EXISTING_EXECUTOR_ID:
        print(f"  [skip] Using existing executor: {EXISTING_EXECUTOR_ID}")
        return EXISTING_EXECUTOR_ID

    if not WORKER_WALLET:
        raise RuntimeError(
            "EM_WORKER_WALLET not set. Export it or set EM_TEST_EXECUTOR_ID."
        )

    print("  [1/2] Registering worker...")
    # Use api() so ERC-8128 signing is applied
    data = await api(
        client,
        "POST",
        "/executors/register",
        {"wallet_address": WORKER_WALLET, "display_name": "Ring Verification Test Worker"},
    )
    http_s = data.get("_status")
    print(f"         HTTP {http_s}")

    if http_s not in (200, 201):
        raise RuntimeError(f"Registration failed: HTTP {http_s} — {data.get('detail', data)}")

    executor_obj = data.get("executor", {})
    executor_id = executor_obj.get("id", "")
    if not executor_id:
        raise RuntimeError("No executor_id in registration response")

    print(f"         Executor ID: {executor_id}")
    print(f"         Created: {data.get('created', 'N/A')}")

    # ERC-8004 identity (non-fatal)
    print("  [2/2] ERC-8004 identity registration...")
    erc = await api(
        client,
        "POST",
        "/reputation/register",
        {
            "network": TEST_NETWORK,
            "agent_uri": "https://execution.market/workers/ring-verification-test",
            "recipient": WORKER_WALLET,
        },
    )
    erc_s = erc.get("_status")
    if erc_s in (200, 201):
        print(f"         Agent ID: {erc.get('agent_id', 'N/A')}")
    else:
        print(f"         ERC-8004: HTTP {erc_s} (non-fatal, continuing)")

    return executor_id


# ---------------------------------------------------------------------------
# Phase 2: Create task
# ---------------------------------------------------------------------------
async def create_task(client: httpx.AsyncClient, photo_url: str) -> str:
    """Create a task that requires photo evidence. Return task_id."""
    payload = {
        "title": f"[RING TEST] Take a photo of a natural scene - {ts_short()}",
        "instructions": (
            "Take a clear photo of any natural outdoor scene: sky, plants, landscape, "
            "or flowers. Photo must be clearly a real photograph (not AI-generated). "
            "Upload the photo as evidence."
        ),
        "category": "simple_action",
        "bounty_usd": TEST_BOUNTY,
        "deadline_hours": 1,
        "evidence_required": ["photo"],
        "location_hint": "Any outdoor location",
        "payment_network": TEST_NETWORK,
        "payment_token": "USDC",
        "arbiter_mode": "auto",
    }

    data = await api(client, "POST", "/tasks", payload)
    http_s = data.get("_status")
    print(f"  Task creation: HTTP {http_s}")

    if http_s != 201:
        raise RuntimeError(f"Task creation failed: {data.get('detail', data)}")

    task_id = data.get("id")
    print(f"  Task ID: {task_id}")
    print(f"  Status: {data.get('status')}")
    return task_id


# ---------------------------------------------------------------------------
# Phase 3: Apply + Assign + Submit
# ---------------------------------------------------------------------------
async def apply_assign_submit(
    client: httpx.AsyncClient,
    task_id: str,
    executor_id: str,
    photo_url: str,
    skip_escrow: bool,
) -> str:
    """Apply, assign (with optional escrow), submit evidence. Return submission_id."""
    # Apply
    print("  [1/3] Worker applying...")
    apply_data = await api(
        client,
        "POST",
        f"/tasks/{task_id}/apply",
        {
            "executor_id": executor_id,
            "message": "Ring Verification Test — ready to submit photo evidence",
        },
    )
    apply_s = apply_data.get("_status")
    print(f"         Apply: HTTP {apply_s}")
    if apply_s not in (200, 201):
        raise RuntimeError(f"Apply failed: {apply_data.get('detail', apply_data)}")
    app_id = (apply_data.get("data") or {}).get("application_id")
    print(f"         Application ID: {app_id}")

    # Assign
    print("  [2/3] Assigning worker (+ escrow)...")
    assign_payload: Dict[str, Any] = {
        "executor_id": executor_id,
        "notes": "Ring Verification Test assignment",
    }

    if not skip_escrow and AGENT_PRIVATE_KEY and WORKER_WALLET:
        print(f"         Signing escrow on {TEST_NETWORK}...")
        try:
            esc = sign_escrow(WORKER_WALLET, TEST_BOUNTY, TEST_NETWORK)
            assign_payload["escrow_tx"] = esc["escrow_tx"]
            assign_payload["payment_info"] = esc["payment_info"]
            print(f"         Escrow TX: {esc['escrow_tx'][:20]}...")
        except Exception as e:
            print(f"         Escrow signing failed: {e}")
            print("         Continuing without escrow (server-fallback)...")
    else:
        print("         Skipping escrow (no agent wallet or --no-payment mode)")

    assign_data = await api(
        client,
        "POST",
        f"/tasks/{task_id}/assign",
        assign_payload,
    )
    assign_s = assign_data.get("_status")
    print(f"         Assign: HTTP {assign_s}")
    if assign_s not in (200, 201):
        raise RuntimeError(f"Assign failed: {assign_data.get('detail', assign_data)}")

    escrow_tx = assign_data.get("escrow_tx") or (
        assign_data.get("data") or {}
    ).get("escrow_tx")
    if escrow_tx:
        print(f"         Escrow locked: {BASESCAN_TX}/{escrow_tx}")

    # Submit evidence with photo URL
    print("  [3/3] Submitting photo evidence...")
    print(f"         Photo URL: {photo_url[:80]}...")
    submit_data = await api(
        client,
        "POST",
        f"/tasks/{task_id}/submit",
        {
            "executor_id": executor_id,
            "evidence": {
                "photo": photo_url,
                "text_response": "Natural outdoor photo submitted for Ring 1+2 verification test",
                "photo_geo": {
                    "url": photo_url,
                    "source": "ring_verification_test",
                },
            },
            "notes": "Ring Verification E2E test submission",
        },
    )
    submit_s = submit_data.get("_status")
    print(f"         Submit: HTTP {submit_s}")
    if submit_s not in (200, 201):
        raise RuntimeError(f"Submit failed: {submit_data.get('detail', submit_data)}")

    # Extract submission_id
    submission_id = (submit_data.get("data") or {}).get("submission_id")
    if not submission_id:
        # Try alternate response format
        submission_id = submit_data.get("submission_id")
    if not submission_id:
        # Query submissions endpoint
        subs = await api(client, "GET", f"/tasks/{task_id}/submissions")
        subs_list = subs.get("submissions") or subs.get("data") or []
        if isinstance(subs_list, list) and subs_list:
            submission_id = subs_list[0].get("id")

    if not submission_id:
        raise RuntimeError("Could not get submission_id from submit response")

    # Get Phase A verification score (sync, returned immediately)
    verif = submit_data.get("verification") or {}
    phase_a_score = verif.get("score")
    if phase_a_score is not None:
        print(f"         Phase A score: {phase_a_score:.3f} (schema/GPS/timestamp)")
    print(f"         Submission ID: {submission_id}")
    return submission_id


# ---------------------------------------------------------------------------
# Phase 4: Poll Ring 1 result
# ---------------------------------------------------------------------------
async def poll_ring1(
    client: httpx.AsyncClient,
    submission_id: str,
) -> Dict[str, Any]:
    """Poll until Ring 1 (PHOTINT Lambda) populates ai_verification_result."""
    print(f"\n  Polling Ring 1 (PHOTINT Lambda, timeout={RING1_TIMEOUT}s)...")
    deadline = time.time() + RING1_TIMEOUT
    poll_count = 0

    while time.time() < deadline:
        await asyncio.sleep(RING1_POLL_INTERVAL)
        poll_count += 1
        elapsed = int(time.time() - (deadline - RING1_TIMEOUT))
        print(f"  [{elapsed:3d}s] Polling Ring 1 ({poll_count})...")

        raw = await api(client, "GET", f"/submissions/{submission_id}")
        http_s = raw.get("_status")

        if http_s != 200:
            print(f"         HTTP {http_s} — retrying...")
            continue

        # Unwrap envelope: {"success": ..., "data": {...}}
        sub = raw.get("data", raw)

        # Ring 1 is complete when ai_verification_result is populated
        ring1 = sub.get("ai_verification_result")
        if ring1 is not None:
            score = None
            if isinstance(ring1, dict):
                score = ring1.get("aggregate_score") or ring1.get("score")
            print(f"  [OK] Ring 1 complete (score={score})")
            return sub

        vstatus = sub.get("verification_status") or sub.get("ai_status")
        print(f"         Ring 1 pending (verification_status={vstatus})")

    print(f"  [TIMEOUT] Ring 1 did not complete within {RING1_TIMEOUT}s")
    # Return last known state even on timeout
    raw = await api(client, "GET", f"/submissions/{submission_id}")
    return raw.get("data", raw)


# ---------------------------------------------------------------------------
# Phase 5: Poll Ring 2 result
# ---------------------------------------------------------------------------
async def poll_ring2(
    client: httpx.AsyncClient,
    submission_id: str,
) -> Dict[str, Any]:
    """Poll until Ring 2 (Arbiter Lambda) populates arbiter_verdict."""
    print(f"\n  Polling Ring 2 (Arbiter Lambda, timeout={RING2_TIMEOUT}s)...")
    deadline = time.time() + RING2_TIMEOUT
    poll_count = 0

    while time.time() < deadline:
        await asyncio.sleep(RING2_POLL_INTERVAL)
        poll_count += 1
        elapsed = int(time.time() - (deadline - RING2_TIMEOUT))
        print(f"  [{elapsed:3d}s] Polling Ring 2 ({poll_count})...")

        raw = await api(client, "GET", f"/submissions/{submission_id}")
        http_s = raw.get("_status")

        if http_s != 200:
            print(f"         HTTP {http_s} — retrying...")
            continue

        # Unwrap envelope: {"success": ..., "data": {...}}
        sub = raw.get("data", raw)

        verdict = sub.get("arbiter_verdict")
        if verdict is not None:
            tier = sub.get("arbiter_tier")
            score = sub.get("arbiter_score")
            print(f"  [OK] Ring 2 complete (verdict={verdict}, tier={tier}, score={score})")
            return sub

        print(f"         Ring 2 pending (arbiter_verdict=null)")

    print(f"  [TIMEOUT] Ring 2 did not complete within {RING2_TIMEOUT}s")
    raw = await api(client, "GET", f"/submissions/{submission_id}")
    return raw.get("data", raw)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def print_verdict_report(
    task_id: str,
    submission_id: str,
    sub: Dict[str, Any],
    photo_url: str,
    elapsed_total: float,
) -> None:
    """Print full Ring 1 + Ring 2 verdict report."""
    _h("RING 1 + RING 2 VERDICT REPORT")

    print(f"\n  Task ID:      {task_id}")
    print(f"  Submission:   {submission_id}")
    print(f"  Elapsed:      {elapsed_total:.1f}s")
    print(f"  Photo URL:    {photo_url[:80]}...")

    print("\n  --- RING 1: PHOTINT Forensic ---")
    ring1 = sub.get("ai_verification_result")
    if ring1 is None:
        print("  [MISSING] ai_verification_result is NULL — Ring 1 did not complete")
    elif isinstance(ring1, dict):
        score = ring1.get("aggregate_score") or ring1.get("score")
        passed = ring1.get("passed")
        reason = ring1.get("reason") or ring1.get("summary", "")[:200]
        print(f"  Score:        {score}")
        print(f"  Passed:       {passed}")
        print(f"  Reason:       {reason}")

        checks = ring1.get("checks") or []
        if checks:
            print("  Checks:")
            for chk in checks[:10]:
                name = chk.get("name", "?")
                chk_p = chk.get("passed")
                chk_s = chk.get("score")
                print(f"    {name}: passed={chk_p} score={chk_s}")
    else:
        print(f"  [RAW] {str(ring1)[:300]}")

    print("\n  --- RING 2: Arbiter Semantic ---")
    verdict = sub.get("arbiter_verdict")
    tier = sub.get("arbiter_tier")
    a_score = sub.get("arbiter_score")
    evidence_hash = sub.get("arbiter_evidence_hash")
    commitment_hash = sub.get("arbiter_commitment_hash")
    ring1_score_r2 = sub.get("arbiter_ring1_score")

    if verdict is None:
        print("  [MISSING] arbiter_verdict is NULL — Ring 2 did not complete")
        print("  Possible causes:")
        print("    - feature.arbiter_enabled = False in platform_config")
        print("    - Ring 1 did not publish to ring2-arbiter SQS queue")
        print("    - Lambda Ring 2 error (check CloudWatch em-production-ring2-worker)")
    else:
        print(f"  Verdict:      {verdict.upper()}")
        print(f"  Tier:         {tier}")
        print(f"  Score:        {a_score}")
        print(f"  Ring 1 score: {ring1_score_r2}")
        print(f"  Evid. hash:   {evidence_hash}")
        print(f"  Commit hash:  {commitment_hash}")

        if verdict == "pass":
            print("\n  [AUTO-RELEASE] Evidence passed both rings — escrow released")
        elif verdict == "fail":
            print("\n  [AUTO-REFUND] Evidence failed — escrow refunded to agent")
        elif verdict == "inconclusive":
            dispute_id = sub.get("dispute_id")
            print(f"\n  [ESCALATED] Rings disagreed — dispute created: {dispute_id}")
        elif verdict == "skipped":
            print("\n  [SKIPPED] Tier=cheap, Ring 2 routed on Ring 1 score only")

    print("\n  --- Hash Integrity ---")
    if evidence_hash and len(evidence_hash) == 66 and evidence_hash.startswith("0x"):
        print(f"  [OK] Evidence hash valid (66 chars, 0x prefix)")
    else:
        print(f"  [WARN] Evidence hash missing or invalid: {evidence_hash}")
    if commitment_hash and len(commitment_hash) == 66 and commitment_hash.startswith("0x"):
        print(f"  [OK] Commitment hash valid (66 chars, 0x prefix)")
    else:
        print(f"  [WARN] Commitment hash missing or invalid: {commitment_hash}")

    # Overall verdict
    ring1_ok = ring1 is not None
    ring2_ok = verdict is not None
    print("\n  --- Summary ---")
    print(f"  Ring 1 Lambda:  {'PASS' if ring1_ok else 'FAIL (did not complete)'}")
    print(f"  Ring 2 Lambda:  {'PASS' if ring2_ok else 'FAIL (did not complete)'}")
    if ring1_ok and ring2_ok:
        print("\n  ** RING 1+2 PIPELINE: PASS — Full dual-ring verification working **")
    elif ring1_ok:
        print("\n  ** RING 1+2 PIPELINE: PARTIAL — Ring 1 OK, Ring 2 needs investigation **")
    else:
        print("\n  ** RING 1+2 PIPELINE: FAIL — Check Lambda logs in CloudWatch **")

    print(f"\n  CloudWatch Ring 1: /aws/lambda/em-production-ring1-worker")
    print(f"  CloudWatch Ring 2: /aws/lambda/em-production-ring2-worker")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> int:
    skip_escrow = "--no-payment" in sys.argv
    photo_url = DEFAULT_PHOTO_URL
    network = TEST_NETWORK

    for i, arg in enumerate(sys.argv):
        if arg == "--photo-url" and i + 1 < len(sys.argv):
            photo_url = sys.argv[i + 1]
        if arg == "--network" and i + 1 < len(sys.argv):
            network = sys.argv[i + 1]

    _h("RING 1 + RING 2 VERIFICATION TEST")
    print(f"  API:       {API_BASE}")
    print(f"  Network:   {network}")
    print(f"  Bounty:    ${TEST_BOUNTY} USDC (credit card model)")
    print(f"  Photo URL: {photo_url[:80]}...")
    print(f"  Skip escrow: {skip_escrow}")
    print(
        f"  Agent wallet: {'set (will sign escrow)' if AGENT_PRIVATE_KEY else 'NOT SET (server-fallback)'}"
    )
    print(f"  Worker:    {WORKER_WALLET or EXISTING_EXECUTOR_ID or 'NOT SET'}")
    print(f"  Time:      {ts()}")

    start_time = time.time()
    task_id = None
    submission_id = None

    timeout = httpx.Timeout(180.0, connect=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            _h("STEP 1: WORKER SETUP")
            executor_id = await register_worker(client)

            _h("STEP 2: CREATE TASK")
            task_id = await create_task(client, photo_url)

            _h("STEP 3: APPLY + ASSIGN + SUBMIT EVIDENCE")
            submission_id = await apply_assign_submit(
                client, task_id, executor_id, photo_url, skip_escrow
            )

            _h("STEP 4: WAIT FOR RING 1 (PHOTINT LAMBDA)")
            sub_after_ring1 = await poll_ring1(client, submission_id)

            _h("STEP 5: WAIT FOR RING 2 (ARBITER LAMBDA)")
            sub_final = await poll_ring2(client, submission_id)

    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        if task_id:
            print(f"  Task: {API_BASE}/api/v1/tasks/{task_id}")
        if submission_id:
            print(f"  Submission: {API_BASE}/api/v1/submissions/{submission_id}")
        return 1
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    elapsed = time.time() - start_time
    print_verdict_report(task_id, submission_id, sub_final, photo_url, elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
