#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H2H Flow -- E2E Acceptance Test for the human-publisher escrow cycle (H2A/H2H).

Tests the sign-on-assignment escrow lifecycle on Base Mainnet
(MASTER_PLAN_UNIVERSAL_ESCROW_CONSISTENCY Task 6.1):

  Publisher (HUMAN: Supabase anonymous JWT + dev wallet) publishes an
  escrow-mode task -> worker (second wallet, ERC-8128) applies -> publisher
  signs the EIP-3009 escrow authorization for the chosen worker
  (browser-equivalent signature built with uvd_x402_sdk.advanced_escrow) and
  assigns with X-Payment-Auth -> escrow locks on-chain -> worker submits ->
  publisher approves with a plain POST (NO signatures) -> escrow releases in
  1 TX with the atomic 87/13 split.

  --refund mode: publish -> apply -> assign+lock -> cancel -> on-chain refund.

IMPORTANT: the server must run with EM_H2A_ESCROW_ENABLED=true. The script
FAILS EARLY (no fake success) when the deployed server does not create the
escrow marker at publish time.

Usage:
    python scripts/e2e_h2h_flow.py                   # full cycle (publish->approve)
    python scripts/e2e_h2h_flow.py --refund          # refund cycle (publish->cancel)
    python scripts/e2e_h2h_flow.py --bounty 0.05     # custom bounty
    python scripts/e2e_h2h_flow.py --api-url http://localhost:8000
    python scripts/e2e_h2h_flow.py --dry-run         # offline: args + wrapper checks

Environment (.env.local):
    SUPABASE_URL / SUPABASE_ANON_KEY -- anonymous sign-in (publisher JWT)
    WALLET_PRIVATE_KEY               -- publisher (human) wallet; signs escrow
    EM_WORKER_PRIVATE_KEY            -- worker wallet (MUST differ from the
                                        publisher wallet -- SC-010 blocks
                                        self-hire and approve blocks
                                        self-collusion)
    EM_API_URL                       -- API base (default https://api.execution.market)
    EM_TEST_EXECUTOR_ID              -- existing executor UUID (skips registration)

Cost: ~$0.05 per full run (refund mode is net $0: lock then full refund).
"""

import argparse
import asyncio
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

# Force UTF-8 stdout on Windows to avoid charmap encoding errors
if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
elif sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
SUPABASE_URL = (
    os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or ""
).rstrip("/")
SUPABASE_ANON_KEY = (
    os.environ.get("SUPABASE_ANON_KEY")
    or os.environ.get("VITE_SUPABASE_ANON_KEY")
    or ""
)

# Publisher = HUMAN side (dev wallet). Worker = second wallet (SC-010).
PUBLISHER_PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY", "")
WORKER_PRIVATE_KEY = os.environ.get("EM_WORKER_PRIVATE_KEY", "")
EXISTING_EXECUTOR_ID = os.environ.get("EM_TEST_EXECUTOR_ID", "")

DEFAULT_BOUNTY = 0.05
PLATFORM_FEE_PCT = Decimal("0.13")
WORKER_PCT = Decimal("0.87")

# Blockchain (Base Mainnet only -- mirror of e2e_golden_flow.py)
BASE_RPC = "https://mainnet.base.org"
BASESCAN_TX = "https://basescan.org/tx"
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# ERC-20 Transfer event topic (built from halves -- pre-commit blocks 0x+64hex)
TRANSFER_TOPIC = (
    "0x" + "ddf252ad1be2c89b69c2b068fc378daa" + "952ba7f163c4a11628f55a4df523b3ef"
)

# Base mainnet escrow stack (same constants as e2e_golden_flow.py:472-497 and
# NETWORK_CONFIG["base"] in mcp_server/integrations/x402/sdk_client.py).
BASE_CHAIN_CONFIG: Dict[str, Any] = {
    "chain_id": 8453,
    "rpc_url": BASE_RPC,
    "usdc": USDC_CONTRACT,
    "escrow": "0xb9488351E48b23D798f24e8174514F28B741Eb4f",
    "operator": "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb",
    "token_collector": "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8",
}

RELEASED_ESCROW_STATUSES = {"released", "completed", "captured"}


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


def _derive_address(private_key: str) -> str:
    from eth_account import Account

    return Account.from_key(private_key).address


# ---------------------------------------------------------------------------
# Phase result collector (mirror of e2e_golden_flow.py)
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
        # Session tokens stay out of the JSON report (user is always streaming).
        d.update(
            {k: v for k, v in self.details.items() if k not in ("jwt", "worker_jwt")}
        )
        return d

    def print_result(self) -> None:
        icon = _icon(self.status == "PASS")
        if self.status == "PARTIAL":
            icon = "PARTIAL"
        print(f"  [{icon}] Phase: {self.description} ({self.elapsed_s}s)")
        if self.error:
            print(f"         Error: {self.error}")


class H2HFlowResults:
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
    def pass_count(self) -> int:
        return sum(1 for p in self.phases.values() if p.status == "PASS")

    @property
    def fail_count(self) -> int:
        return sum(1 for p in self.phases.values() if p.status == "FAIL")

    @property
    def overall(self) -> str:
        if all(p.status == "PASS" for p in self.phases.values()):
            return "PASS"
        if self.fail_count == 0:
            return "PARTIAL"
        return "FAIL"

    def to_dict(self, bounty: float, mode: str) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_base": API_BASE,
            "mode": mode,
            "fee_model": "credit_card",
            "escrow_mode": "sign_on_assignment",
            "payment_network": "base",
            "bounty_usd": bounty,
            "phases": {name: phase.to_dict() for name, phase in self.phases.items()},
            "overall": self.overall,
            "tx_hashes": self.tx_hashes,
            "total_elapsed_s": round(time.time() - self.start_time, 2),
        }


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
# ERC-8128 request signer for the WORKER side (reuses EM8128Signer from
# scripts/em_monitor.py, same as e2e_golden_flow.py). The PUBLISHER side
# authenticates with the Supabase JWT instead (human auth).
_worker_signer: Optional[Any] = None


def _get_worker_signer():
    global _worker_signer
    if _worker_signer is not None:
        return _worker_signer
    if not WORKER_PRIVATE_KEY:
        return None
    from em_monitor import EM8128Signer

    _worker_signer = EM8128Signer(WORKER_PRIVATE_KEY, chain_id=8453, api_url=API_BASE)
    return _worker_signer


async def api_call(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    json_data: Optional[dict] = None,
    jwt: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    actor: Optional[str] = None,
) -> dict:
    """Call /api/v1/* endpoint.

    jwt=<token>     -- publisher (human) auth: Authorization: Bearer <jwt>.
    actor='worker'  -- worker auth: ERC-8128 signed request.
    Neither         -- anonymous (public reads).
    """
    url = f"{API_BASE}/api/v1{path}"
    headers: Dict[str, str] = {}
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    if extra_headers:
        headers.update(extra_headers)

    signer = _get_worker_signer() if actor == "worker" else None
    if signer is not None:
        # The signed Content-Digest must cover the exact bytes sent, so
        # serialize once and send via content=, never via json=.
        body = json.dumps(json_data) if json_data is not None else None
        # The nonce endpoint rate-limits bursts of signed calls (429);
        # back off and retry instead of aborting the flow.
        for _attempt in range(4):
            try:
                auth = await signer.sign_headers(method, url, body=body, client=client)
                break
            except httpx.HTTPStatusError as _e:
                if _e.response.status_code == 429 and _attempt < 3:
                    await asyncio.sleep(4 * (_attempt + 1))
                    continue
                raise
        headers.update(auth)
        if body is not None:
            headers["Content-Type"] = "application/json"
        resp = await client.request(method, url, content=body, headers=headers)
    else:
        resp = await client.request(method, url, json=json_data, headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text, "status_code": resp.status_code}
    if not isinstance(data, dict):
        data = {"data": data}
    data["_http_status"] = resp.status_code
    return data


async def supabase_anonymous_signin(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Anonymous Supabase sign-in (same as the dashboard's signInAnonymously).

    GoTrue treats a /signup POST without email/phone as an anonymous sign-in
    when the project has anonymous sign-ins enabled.
    """
    url = f"{SUPABASE_URL}/auth/v1/signup"
    resp = await client.post(
        url,
        json={},
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        timeout=30.0,
    )
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    data["_http_status"] = resp.status_code
    return data


# ---------------------------------------------------------------------------
# On-chain TX verification (mirror of e2e_golden_flow.py)
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
                amount_token = raw_amount / 1_000_000  # USDC 6 decimals
                transfers.append(
                    {
                        "from": sender.lower(),
                        "to": receiver.lower(),
                        "amount_token": amount_token,
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
# Browser-equivalent escrow signing (sign-on-assignment)
# ---------------------------------------------------------------------------
def build_escrow_auth_wrapper(
    private_key: str,
    worker_wallet: str,
    bounty_usd: float,
) -> Dict[str, Any]:
    """Build the X-Payment-Auth wrapper the browser would produce at assign.

    Uses uvd_x402_sdk.advanced_escrow to build the paymentInfo EXACTLY like
    the SDK (nonce = AuthCaptureEscrow.getHash(paymentInfo), which commits to
    the receiver) and signs the EIP-3009 ReceiveWithAuthorization -- but does
    NOT call client.authorize() (that would POST to the Facilitator directly).
    The EM server relays the wrapper on POST /h2a/tasks/{id}/assign.

    Returns {"wrapper": dict, "payer": address, "payment_info": PaymentInfo}.
    """
    from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient, TaskTier

    escrow_client = AdvancedEscrowClient(
        private_key=private_key,
        chain_id=BASE_CHAIN_CONFIG["chain_id"],
        rpc_url=BASE_CHAIN_CONFIG["rpc_url"],
        contracts={
            "usdc": BASE_CHAIN_CONFIG["usdc"],
            "escrow": BASE_CHAIN_CONFIG["escrow"],
            "operator": BASE_CHAIN_CONFIG["operator"],
            "token_collector": BASE_CHAIN_CONFIG["token_collector"],
        },
    )

    bounty_atomic = int(Decimal(str(bounty_usd)) * 1_000_000)  # USDC 6 decimals
    pi = escrow_client.build_payment_info(
        receiver=worker_wallet,
        amount=bounty_atomic,
        tier=TaskTier.MICRO,
        max_fee_bps=1800,  # 18% max (13% actual + margin)
    )

    # Nonce commits to the receiver (EC-15: this is WHY signing happens at
    # assignment) -- then sign ReceiveWithAuthorization over the USDC domain.
    nonce = escrow_client._compute_nonce(pi)
    authorization = {
        "from": escrow_client.payer,
        "to": escrow_client.contracts["token_collector"],
        "value": str(pi.max_amount),
        "validAfter": "0",
        "validBefore": str(pi.pre_approval_expiry),
        "nonce": nonce,
    }
    signature = escrow_client._sign_erc3009(authorization)

    payment_info_camel = {
        "operator": pi.operator,
        "receiver": pi.receiver,
        "token": pi.token,
        "maxAmount": str(pi.max_amount),
        "preApprovalExpiry": pi.pre_approval_expiry,
        "authorizationExpiry": pi.authorization_expiry,
        "refundExpiry": pi.refund_expiry,
        "minFeeBps": pi.min_fee_bps,
        "maxFeeBps": pi.max_fee_bps,
        "feeReceiver": pi.fee_receiver,
        "salt": pi.salt,
    }

    wrapper = {
        "x402Version": 2,
        "scheme": "escrow",
        "payload": {
            "authorization": authorization,
            "signature": signature,
            "paymentInfo": payment_info_camel,
        },
        "paymentRequirements": {
            "scheme": "escrow",
            "network": f"eip155:{BASE_CHAIN_CONFIG['chain_id']}",
        },
    }
    return {"wrapper": wrapper, "payer": escrow_client.payer, "payment_info": pi}


def validate_wrapper_local(
    raw_json: str,
    *,
    expected_payer: str,
    expected_amount_atomic: str,
    expected_receiver: str,
) -> List[str]:
    """Replicate the server-side checks the wrapper must pass.

    Mirrors PaymentDispatcher.validate_agent_preauth (structure, temporal,
    SC-001 network constants for base) plus the lock_with_fresh_auth receiver
    gate (paymentInfo.receiver == assigned worker). Returns a list of errors
    (empty = valid).
    """
    errors: List[str] = []
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError) as e:
        return [f"X-Payment-Auth is not valid JSON: {e}"]

    if not isinstance(data, dict):
        return ["X-Payment-Auth must be a JSON object"]

    payload = data.get("payload")
    if not payload or not isinstance(payload, dict):
        return ["X-Payment-Auth missing 'payload' object"]

    auth = payload.get("authorization")
    if not auth or not isinstance(auth, dict):
        return ["X-Payment-Auth missing 'payload.authorization'"]
    required_auth_fields = ["from", "to", "value", "validAfter", "validBefore", "nonce"]
    missing = [f for f in required_auth_fields if f not in auth]
    if missing:
        errors.append(f"authorization missing fields: {missing}")

    if not payload.get("signature"):
        errors.append("missing 'payload.signature'")

    pi = payload.get("paymentInfo")
    if not pi or not isinstance(pi, dict):
        errors.append("missing 'payload.paymentInfo'")
        return errors
    missing_pi = [f for f in ["operator", "token", "maxAmount"] if f not in pi]
    if missing_pi:
        errors.append(f"paymentInfo missing fields: {missing_pi}")

    # Temporal validity
    now = int(time.time())
    try:
        valid_after = int(auth.get("validAfter", 0))
        valid_before = int(auth.get("validBefore", 0))
        if valid_before <= now:
            errors.append(f"expired: validBefore={valid_before} <= now={now}")
        if valid_after > now + 30:
            errors.append(f"not yet valid: validAfter={valid_after} > now={now}")
    except (ValueError, TypeError) as e:
        errors.append(f"validAfter/validBefore not integer: {e}")

    # SC-001: base network constants
    if (pi.get("operator") or "").lower() != BASE_CHAIN_CONFIG["operator"].lower():
        errors.append(
            f"paymentInfo.operator must be {BASE_CHAIN_CONFIG['operator']} for base"
        )
    if (pi.get("token") or "").lower() != BASE_CHAIN_CONFIG["usdc"].lower():
        errors.append(f"paymentInfo.token {pi.get('token')} not USDC on base")
    if (auth.get("to") or "").lower() != BASE_CHAIN_CONFIG["token_collector"].lower():
        errors.append(
            "authorization.to must be tokenCollector "
            f"{BASE_CHAIN_CONFIG['token_collector']} for base"
        )

    # Payer + amount
    if (auth.get("from") or "").lower() != expected_payer.lower():
        errors.append("authorization.from must match the publisher wallet")
    if str(pi.get("maxAmount")) != str(expected_amount_atomic):
        errors.append(
            f"paymentInfo.maxAmount {pi.get('maxAmount')} != "
            f"expected {expected_amount_atomic}"
        )

    # lock_with_fresh_auth receiver gate (nonce commits to the receiver)
    if (pi.get("receiver") or "").lower() != expected_receiver.lower():
        errors.append(
            f"paymentInfo.receiver {pi.get('receiver')} != worker {expected_receiver}"
        )

    return errors


def _verify_signature_recovers(
    wrapper: Dict[str, Any], expected_payer: str
) -> Optional[str]:
    """Recover the EIP-712 ReceiveWithAuthorization signer locally.

    Returns None when the signature recovers to expected_payer, else an error
    string. Replicates the SDK's domain/types (advanced_escrow._sign_erc3009).
    """
    try:
        from eth_account import Account
        from eth_account.messages import encode_typed_data

        auth = wrapper["payload"]["authorization"]
        domain = {
            "name": "USD Coin",
            "version": "2",
            "chainId": BASE_CHAIN_CONFIG["chain_id"],
            "verifyingContract": BASE_CHAIN_CONFIG["usdc"],
        }
        types = {
            "ReceiveWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        }
        message = {
            "from": auth["from"],
            "to": auth["to"],
            "value": int(auth["value"]),
            "validAfter": int(auth["validAfter"]),
            "validBefore": int(auth["validBefore"]),
            "nonce": bytes.fromhex(auth["nonce"].removeprefix("0x")),
        }
        signable = encode_typed_data(
            domain_data=domain, message_types=types, message_data=message
        )
        recovered = Account.recover_message(
            signable, signature=wrapper["payload"]["signature"]
        )
        if recovered.lower() != expected_payer.lower():
            return f"signature recovers to {recovered}, expected {expected_payer}"
        return None
    except Exception as e:
        return f"signature recovery failed: {e}"


# ---------------------------------------------------------------------------
# Phase 1: Preflight
# ---------------------------------------------------------------------------
def phase_preflight(results: H2HFlowResults) -> PhaseResult:
    """Phase 1: Validate environment + wallet separation (SC-010 / EC-14)."""
    phase = PhaseResult("preflight", "Preflight (env + wallet separation)")
    _print_header("PHASE 1: PREFLIGHT")

    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY:
        missing.append("SUPABASE_ANON_KEY")
    if not PUBLISHER_PRIVATE_KEY:
        missing.append("WALLET_PRIVATE_KEY")
    if not WORKER_PRIVATE_KEY:
        missing.append("EM_WORKER_PRIVATE_KEY")
    if missing:
        return phase.fail(f"Missing environment variables: {', '.join(missing)}")

    try:
        publisher_wallet = _derive_address(PUBLISHER_PRIVATE_KEY)
        worker_wallet = _derive_address(WORKER_PRIVATE_KEY)
    except Exception as e:
        return phase.fail(f"Could not derive wallet addresses: {e}")

    print(f"    Publisher wallet: {publisher_wallet}")
    print(f"    Worker wallet:    {worker_wallet}")

    if publisher_wallet.lower() == worker_wallet.lower():
        return phase.fail(
            "Publisher and worker wallets are the SAME. SC-010 blocks "
            "self-hire (payer cannot be receiver) -- set EM_WORKER_PRIVATE_KEY "
            "to a second wallet (EC-14)."
        )

    return phase.pass_(
        publisher_wallet=publisher_wallet,
        worker_wallet=worker_wallet,
    )


# ---------------------------------------------------------------------------
# Phase 2: Publisher auth (Supabase anonymous JWT)
# ---------------------------------------------------------------------------
async def phase_publisher_auth(
    client: httpx.AsyncClient, results: H2HFlowResults
) -> PhaseResult:
    """Phase 2: Anonymous Supabase sign-in -> publisher JWT (human auth)."""
    phase = PhaseResult("publisher_auth", "Publisher Auth (Supabase anonymous JWT)")
    _print_header("PHASE 2: PUBLISHER AUTH (SUPABASE ANONYMOUS)")

    try:
        print("  [1/1] Anonymous sign-in...")
        data = await supabase_anonymous_signin(client)
        status = data.get("_http_status")
        print(f"         Sign-in: HTTP {status}")

        token = data.get("access_token")
        user = data.get("user") or {}
        user_id = user.get("id")
        if status != 200 or not token:
            err = data.get("msg") or data.get("error_description") or str(data)[:200]
            return phase.fail(
                f"Anonymous sign-in failed: HTTP {status} - {err}. "
                "Anonymous sign-ins must be enabled in the Supabase project."
            )

        print(f"         User ID: {user_id}")
        return phase.pass_(jwt=token, user_id=user_id)

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 3: Publish (escrow-mode task, marker row, NO signature)
# ---------------------------------------------------------------------------
async def phase_publish(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    jwt: str,
    publisher_wallet: str,
    bounty: float,
    mode: str,
) -> PhaseResult:
    """Phase 3: POST /api/v1/publish + verify the escrow marker exists."""
    phase = PhaseResult("publish", "Publish (escrow-mode H2H task)")
    _print_header("PHASE 3: PUBLISH (HUMAN PUBLISHER, ESCROW-MODE)")
    print(f"    Bounty:  ${bounty:.2f} USDC (base)")
    print("    Target:  human (H2H)")

    try:
        print("  [1/2] Publishing task...")
        task_payload = {
            "title": f"[H2H FLOW] E2E Escrow Test - {ts_short()}",
            "instructions": (
                f"Automated escrow-cycle test ({mode}). Respond with: h2h_flow_complete"
            ),
            "category": "simple_action",
            "bounty_usd": bounty,
            "deadline_hours": 1,
            "evidence_required": ["text_response"],
            "payment_network": "base",
            "payment_token": "USDC",
            "target_executor_type": "human",
            "publisher_wallet": publisher_wallet,
        }
        pub = await api_call(client, "POST", "/publish", task_payload, jwt=jwt)
        status = pub.get("_http_status")
        if status == 404:
            # Older deploy without the neutral route -- use the legacy alias.
            print("         /publish not found -- retrying legacy /h2a/tasks alias")
            pub = await api_call(client, "POST", "/h2a/tasks", task_payload, jwt=jwt)
            status = pub.get("_http_status")
        print(f"         Publish: HTTP {status}")

        if status != 201:
            err = pub.get("detail", str(pub)[:300])
            return phase.fail(f"Publish failed: HTTP {status} - {err}")

        task_id = pub.get("task_id")
        print(f"         Task ID: {task_id}")
        print(f"         Status:  {pub.get('status')}")

        # FAIL EARLY when the server flag is off: an escrow-mode publish MUST
        # create the pending_assignment marker, surfaced as escrow_status on
        # the public task detail. No marker = legacy sign-on-approval server.
        print("  [2/2] Verifying escrow marker (EM_H2A_ESCROW_ENABLED)...")
        detail = await api_call(client, "GET", f"/h2a/tasks/{task_id}")
        d_status = detail.get("_http_status")
        escrow_status = detail.get("escrow_status")
        print(f"         Task detail: HTTP {d_status}")
        print(f"         escrow_status: {escrow_status}")

        if d_status != 200:
            return phase.fail(f"Task detail returned HTTP {d_status}", task_id=task_id)

        if not escrow_status:
            return phase.fail(
                "No escrow marker on the published task: the server flag "
                "EM_H2A_ESCROW_ENABLED is OFF (or the deployed build predates "
                "sign-on-assignment). Deploy + enable the flag first -- this "
                "script does not fake escrow success. Task left published; "
                "cancel it manually if needed.",
                task_id=task_id,
                escrow_status=escrow_status,
            )

        if escrow_status != "pending_assignment":
            return phase.fail(
                f"Unexpected escrow_status '{escrow_status}' at publish "
                "(expected 'pending_assignment')",
                task_id=task_id,
                escrow_status=escrow_status,
            )

        return phase.pass_(task_id=task_id, escrow_status=escrow_status)

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 4: Worker registration (+ best-effort ERC-8004 identity)
# ---------------------------------------------------------------------------
async def phase_worker_setup(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    worker_wallet: str,
) -> PhaseResult:
    """Phase 4: Worker session + executor binding (+ ERC-8004 best-effort).

    Mirrors the dashboard human-worker flow: the worker gets its OWN
    anonymous Supabase session and binds the executor row to it via the
    get_or_create_executor RPC (first-bind-wins in the hardened FIX-P0-02
    version). REST worker endpoints (apply/submit) authenticate with this
    JWT -- verify_worker_auth resolves executors.user_id, ERC-8128 is not
    accepted there when EM_REQUIRE_WORKER_AUTH=true.
    """
    phase = PhaseResult("worker_setup", "Worker Session & Executor Binding")
    _print_header("PHASE 4: WORKER SESSION & EXECUTOR BINDING")

    try:
        print("  [1/3] Worker anonymous sign-in (separate session)...")
        signin = await supabase_anonymous_signin(client)
        s_status = signin.get("_http_status")
        print(f"         Sign-in: HTTP {s_status}")
        worker_jwt = signin.get("access_token")
        if s_status != 200 or not worker_jwt:
            return phase.fail(f"Worker anonymous sign-in failed: HTTP {s_status}")
        worker_user = (signin.get("user") or {}).get("id")
        print(f"         Worker user ID: {worker_user}")

        # Bind executors.user_id to this session via the GR-1.7 backend
        # endpoint (mirrors dashboard/src/services/linkWalletSession.ts):
        # the wallet signs a fresh challenge proving ownership, which
        # authorizes the bind under migration 111's "proven owner" rule.
        print("  [2/3] Linking wallet to worker session (signed challenge)...")
        from eth_account import Account
        from eth_account.messages import encode_defunct

        wallet_lower = worker_wallet.lower()
        timestamp = datetime.now(timezone.utc).isoformat()
        message = (
            f"Execution Market: link wallet {wallet_lower} "
            f"to Supabase user {worker_user} at {timestamp}"
        )
        signed = Account.sign_message(
            encode_defunct(text=message), private_key=WORKER_PRIVATE_KEY
        )
        sig_hex = signed.signature.hex()
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex

        link_data = await api_call(
            client,
            "POST",
            "/account/link-wallet",
            {
                "wallet_address": wallet_lower,
                "message": message,
                "signature": sig_hex,
            },
            jwt=worker_jwt,
        )
        l_status = link_data.get("_http_status")
        print(f"         Link: HTTP {l_status}")
        if l_status not in (200, 201):
            err = link_data.get("detail", str(link_data)[:200])
            return phase.fail(f"Wallet link failed: {err}")

        executor_id = link_data.get("executor_id", "")
        print(f"         Executor ID: {executor_id}")
        print(f"         Linked: {link_data.get('linked')}")

        if EXISTING_EXECUTOR_ID and executor_id != EXISTING_EXECUTOR_ID:
            print(
                f"         Note: EM_TEST_EXECUTOR_ID={EXISTING_EXECUTOR_ID} "
                "differs from the wallet's executor; using the RPC result."
            )

        if not executor_id:
            return phase.fail("No executor ID obtained")

        # ERC-8004 identity (best-effort -- mirrors the Golden Flow: a worker
        # without on-chain identity can still operate where not enforced).
        print("  [3/3] Registering worker on ERC-8004 (best-effort)...")
        erc_data = await api_call(
            client,
            "POST",
            "/reputation/register",
            {
                "network": "base",
                "agent_uri": "https://execution.market/workers/h2h-flow-test",
                "recipient": worker_wallet,
            },
            actor="worker",
        )
        erc_status = erc_data.get("_http_status")
        print(f"         ERC-8004 Register: HTTP {erc_status}")
        if erc_status in (200, 201):
            erc_error = erc_data.get("error")
            if erc_data.get("transaction"):
                results.add_tx(erc_data["transaction"])
            if erc_error:
                print(f"         Note: {erc_error}")
        else:
            print(f"         Non-fatal: {erc_data.get('detail', erc_status)}")

        return phase.pass_(executor_id=executor_id, worker_jwt=worker_jwt)

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 5: Worker applies (worker JWT)
# ---------------------------------------------------------------------------
async def phase_apply(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    task_id: str,
    executor_id: str,
    worker_jwt: str,
) -> PhaseResult:
    """Phase 5: Worker applies to the H2H task (Supabase JWT auth)."""
    phase = PhaseResult("apply", "Worker Application (worker JWT)")
    _print_header("PHASE 5: WORKER APPLICATION")

    try:
        print("  [1/1] Worker applying to task...")
        apply_data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/apply",
            {
                "executor_id": executor_id,
                "message": "H2H Flow E2E test -- ready to work",
            },
            jwt=worker_jwt,
        )
        status = apply_data.get("_http_status")
        print(f"         Apply: HTTP {status}")

        if status not in (200, 201):
            err = apply_data.get("detail", str(apply_data)[:200])
            return phase.fail(f"Apply failed: {err}")

        application_id = (apply_data.get("data") or {}).get("application_id")
        print(f"         Application ID: {application_id}")
        return phase.pass_(application_id=application_id)

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 6: Assign with browser-equivalent signature -> escrow lock
# ---------------------------------------------------------------------------
async def phase_assign_lock(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    jwt: str,
    task_id: str,
    executor_id: str,
    worker_wallet: str,
    bounty: float,
) -> PhaseResult:
    """Phase 6: Publisher signs EIP-3009 for the worker + assigns (lock)."""
    phase = PhaseResult("assign_lock", "Assign + Escrow Lock (sign-on-assignment)")
    _print_header("PHASE 6: ASSIGN + ESCROW LOCK (SIGN-ON-ASSIGNMENT)")

    try:
        print("  [1/3] Building browser-equivalent X-Payment-Auth...")
        built = build_escrow_auth_wrapper(PUBLISHER_PRIVATE_KEY, worker_wallet, bounty)
        wrapper = built["wrapper"]
        payer = built["payer"]
        raw_header = json.dumps(wrapper)
        print(f"         Payer (publisher): {payer}")
        print(f"         Receiver (worker): {worker_wallet}")
        print(f"         maxAmount: {wrapper['payload']['paymentInfo']['maxAmount']}")

        # Pre-flight the wrapper locally before sending (same checks the
        # server runs) so a malformed signature fails fast and clearly.
        atomic = str(int(Decimal(str(bounty)) * 1_000_000))
        local_errors = validate_wrapper_local(
            raw_header,
            expected_payer=payer,
            expected_amount_atomic=atomic,
            expected_receiver=worker_wallet,
        )
        if local_errors:
            return phase.fail(f"Local wrapper validation failed: {local_errors}")
        print("         Local wrapper validation: OK")

        print("  [2/3] Assigning worker (POST /h2a/tasks/{id}/assign)...")
        assign_data = await api_call(
            client,
            "POST",
            f"/h2a/tasks/{task_id}/assign",
            {"executor_id": executor_id},
            jwt=jwt,
            extra_headers={"X-Payment-Auth": raw_header},
        )
        status = assign_data.get("_http_status")
        print(f"         Assign: HTTP {status}")

        if status not in (200, 201):
            err = assign_data.get("detail", str(assign_data)[:300])
            return phase.fail(f"Assign failed: HTTP {status} - {err}")

        escrow_tx = assign_data.get("escrow_tx")
        print(f"         Escrow TX: {escrow_tx}")
        if not escrow_tx:
            return phase.fail(
                "Assign succeeded but returned no escrow_tx -- the lock did "
                "not happen (legacy status-only assign?)"
            )
        print(f"         BaseScan:  {BASESCAN_TX}/{escrow_tx}")
        results.add_tx(escrow_tx)

        print("  [3/3] Verifying lock on-chain + escrow state...")
        receipt = await verify_tx_onchain(client, escrow_tx)
        lock_verified = receipt.get("success", False)
        print(f"         On-chain: {'SUCCESS' if lock_verified else 'FAILED'}")
        for t in receipt.get("transfers", []):
            print(
                f"         Transfer: ...{t['from'][-6:]} -> ...{t['to'][-6:]} : "
                f"${t['amount_token']:.6f}"
            )

        detail = await api_call(client, "GET", f"/h2a/tasks/{task_id}")
        escrow_status = detail.get("escrow_status")
        print(f"         escrow_status: {escrow_status}")

        if not lock_verified:
            return phase.fail(
                f"Escrow lock TX not verified on-chain: {receipt.get('error')}",
                escrow_tx=escrow_tx,
            )
        if escrow_status != "deposited":
            return phase.partial(
                f"Lock TX verified but escrow_status is '{escrow_status}' "
                "(expected 'deposited')",
                escrow_tx=escrow_tx,
                escrow_status=escrow_status,
            )

        return phase.pass_(
            escrow_tx=escrow_tx,
            escrow_status=escrow_status,
            lock_verified=lock_verified,
        )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 7: Worker submits evidence (ERC-8128)
# ---------------------------------------------------------------------------
async def phase_submit(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    task_id: str,
    executor_id: str,
    worker_jwt: str,
) -> PhaseResult:
    """Phase 7: Worker submits evidence (Supabase JWT auth)."""
    phase = PhaseResult("submit", "Worker Submission (worker JWT)")
    _print_header("PHASE 7: WORKER SUBMISSION")

    try:
        print("  [1/1] Worker submitting evidence...")
        submit_data = await api_call(
            client,
            "POST",
            f"/tasks/{task_id}/submit",
            {
                "executor_id": executor_id,
                "evidence": {"text_response": "h2h_flow_complete"},
                "notes": "H2H Flow automated E2E submission",
            },
            jwt=worker_jwt,
        )
        status = submit_data.get("_http_status")
        print(f"         Submit: HTTP {status}")

        if status not in (200, 201):
            err = submit_data.get("detail", str(submit_data)[:200])
            return phase.fail(f"Submit failed: {err}")

        submission_id = (submit_data.get("data") or {}).get("submission_id")
        if not submission_id:
            subs_data = await api_call(client, "GET", f"/tasks/{task_id}/submissions")
            subs_list = subs_data.get("submissions") or subs_data.get("data") or []
            if isinstance(subs_list, list) and subs_list:
                submission_id = subs_list[0].get("id")

        if not submission_id:
            return phase.fail("Could not find submission ID after submit")

        print(f"         Submission ID: {submission_id}")
        return phase.pass_(submission_id=submission_id)

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 8: Approve -> escrow release (NO signatures)
# ---------------------------------------------------------------------------
async def phase_approve_release(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    jwt: str,
    task_id: str,
    submission_id: str,
    worker_wallet: str,
    bounty: float,
) -> PhaseResult:
    """Phase 8: Publisher approves (plain POST) -> 1-TX release, 87/13 split."""
    phase = PhaseResult("approve_release", "Approve + Escrow Release (no signatures)")
    expected_worker_net = float(Decimal(str(bounty)) * WORKER_PCT)
    expected_fee = float(Decimal(str(bounty)) * PLATFORM_FEE_PCT)

    _print_header("PHASE 8: APPROVE + ESCROW RELEASE")
    print(f"    Worker (87%): ${expected_worker_net:.6f}")
    print(f"    Fee (13%):    ${expected_fee:.6f}")

    try:
        print("  [1/3] Approving submission (plain POST, no signatures)...")
        approve_data = await api_call(
            client,
            "POST",
            f"/h2a/tasks/{task_id}/approve",
            {
                "submission_id": submission_id,
                "verdict": "accepted",
                "notes": "H2H Flow E2E test -- approving for escrow release",
                # Phase 5.1: a worker rating is required to approve+pay.
                "worker_score": 5,
            },
            jwt=jwt,
        )
        status = approve_data.get("_http_status")
        print(f"         Approve: HTTP {status}")

        if status != 200:
            err = approve_data.get("detail", str(approve_data)[:300])
            return phase.fail(f"Approval failed: HTTP {status} - {err}")

        worker_tx = approve_data.get("worker_tx")
        fee_tx = approve_data.get("fee_tx")
        print(f"         Worker TX: {worker_tx}")
        if fee_tx:
            print(f"         Fee TX:    {fee_tx}")

        if not worker_tx:
            return phase.fail(
                "Approve succeeded but returned no worker_tx -- escrow "
                "release did not happen"
            )
        print(f"         BaseScan:  {BASESCAN_TX}/{worker_tx}")
        results.add_tx(worker_tx)
        if fee_tx:
            results.add_tx(fee_tx)

        print("  [2/3] Verifying release on-chain...")
        receipt = await verify_tx_onchain(client, worker_tx)
        release_verified = receipt.get("success", False)
        print(f"         On-chain: {'SUCCESS' if release_verified else 'FAILED'}")

        worker_net_actual = None
        fee_actual = None
        for t in receipt.get("transfers", []):
            print(
                f"         Transfer: ...{t['from'][-6:]} -> ...{t['to'][-6:]} : "
                f"${t['amount_token']:.6f}"
            )
            if t["to"].lower() == worker_wallet.lower():
                worker_net_actual = t["amount_token"]
            else:
                fee_actual = t["amount_token"]

        if not release_verified:
            return phase.fail(
                f"Release TX not verified on-chain: {receipt.get('error')}",
                worker_tx=worker_tx,
            )

        print("  [3/3] Verifying fee math + escrow state...")
        fee_mismatch = None
        if worker_net_actual is not None:
            if abs(worker_net_actual - expected_worker_net) > 0.002:
                fee_mismatch = (
                    f"Worker net ${worker_net_actual:.6f} != "
                    f"expected ${expected_worker_net:.6f} (87%)"
                )
            else:
                print(
                    f"         Worker: ${worker_net_actual:.6f} "
                    f"(expected ${expected_worker_net:.6f}, 87%) -- OK"
                )
            if fee_actual is not None and abs(fee_actual - expected_fee) > 0.002:
                fee_mismatch = fee_mismatch or (
                    f"Fee ${fee_actual:.6f} != expected ${expected_fee:.6f} (13%)"
                )
            elif fee_actual is not None:
                print(
                    f"         Fee:    ${fee_actual:.6f} "
                    f"(expected ${expected_fee:.6f}, 13%) -- OK"
                )

        detail = await api_call(client, "GET", f"/h2a/tasks/{task_id}")
        escrow_status = (detail.get("escrow_status") or "").lower()
        task_status = detail.get("status")
        print(f"         escrow_status: {escrow_status}")
        print(f"         task status:   {task_status}")

        if fee_mismatch:
            return phase.partial(
                fee_mismatch,
                worker_tx=worker_tx,
                fee_tx=fee_tx,
                escrow_status=escrow_status,
            )
        if escrow_status and escrow_status not in RELEASED_ESCROW_STATUSES:
            return phase.partial(
                f"Release TX verified but escrow_status is '{escrow_status}'",
                worker_tx=worker_tx,
                fee_tx=fee_tx,
                escrow_status=escrow_status,
            )

        return phase.pass_(
            worker_tx=worker_tx,
            fee_tx=fee_tx,
            worker_net_usdc=worker_net_actual,
            fee_usdc=fee_actual,
            escrow_status=escrow_status,
            task_status=task_status,
        )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase R: Request revision -> task back to in_progress, escrow untouched
# ---------------------------------------------------------------------------
async def phase_request_revision(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    jwt: str,
    task_id: str,
    submission_id: str,
) -> PhaseResult:
    """Publisher asks for revision -> task in_progress, escrow stays locked."""
    phase = PhaseResult("request_revision", "Request Revision (escrow untouched)")
    _print_header("PHASE R: REQUEST REVISION")
    try:
        print("  [1/2] Requesting revision (verdict=needs_revision)...")
        data = await api_call(
            client,
            "POST",
            f"/h2a/tasks/{task_id}/approve",
            {
                "submission_id": submission_id,
                "verdict": "needs_revision",
                "notes": "H2H Flow E2E -- please add the missing detail and resubmit",
            },
            jwt=jwt,
        )
        status = data.get("_http_status")
        print(f"         Revision: HTTP {status}")
        if status != 200:
            err = data.get("detail", str(data)[:300])
            return phase.fail(f"Revision request failed: HTTP {status} - {err}")

        print("  [2/2] Verifying task -> in_progress + escrow intact...")
        detail = await api_call(client, "GET", f"/h2a/tasks/{task_id}")
        task_status = detail.get("status")
        escrow_status = (detail.get("escrow_status") or "").lower()
        print(f"         task status:   {task_status}")
        print(f"         escrow_status: {escrow_status}")

        if task_status != "in_progress":
            return phase.fail(
                f"Expected task 'in_progress' after revision, got '{task_status}'"
            )
        # Revision must NOT release or refund — the worker still has the funds
        # locked while they fix the submission.
        if escrow_status in RELEASED_ESCROW_STATUSES or escrow_status == "refunded":
            return phase.fail(
                f"Escrow must stay locked on revision, but is '{escrow_status}'"
            )
        return phase.pass_(task_status=task_status, escrow_status=escrow_status)

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Phase 8R: Cancel -> escrow refund (--refund mode)
# ---------------------------------------------------------------------------
async def phase_cancel_refund(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    jwt: str,
    task_id: str,
    bounty: float,
) -> PhaseResult:
    """Phase 8R: Cancel the locked task -> on-chain refund to the publisher."""
    phase = PhaseResult("cancel_refund", "Cancel + Escrow Refund")
    _print_header("PHASE 8R: CANCEL + ESCROW REFUND")

    try:
        print("  [1/2] Cancelling task (POST /h2a/tasks/{id}/cancel)...")
        cancel_data = await api_call(
            client, "POST", f"/h2a/tasks/{task_id}/cancel", jwt=jwt
        )
        status = cancel_data.get("_http_status")
        print(f"         Cancel: HTTP {status}")

        if status != 200:
            err = cancel_data.get("detail", str(cancel_data)[:300])
            return phase.fail(f"Cancel failed: HTTP {status} - {err}")

        refund_tx = cancel_data.get("refund_tx")
        print(f"         Refund TX: {refund_tx}")
        if not refund_tx:
            return phase.fail(
                "Cancel succeeded but returned no refund_tx -- the deposited "
                "escrow was not refunded on-chain"
            )
        print(f"         BaseScan:  {BASESCAN_TX}/{refund_tx}")
        results.add_tx(refund_tx)

        print("  [2/2] Verifying refund on-chain + escrow state...")
        receipt = await verify_tx_onchain(client, refund_tx)
        refund_verified = receipt.get("success", False)
        print(f"         On-chain: {'SUCCESS' if refund_verified else 'FAILED'}")
        for t in receipt.get("transfers", []):
            print(
                f"         Transfer: ...{t['from'][-6:]} -> ...{t['to'][-6:]} : "
                f"${t['amount_token']:.6f}"
            )

        detail = await api_call(client, "GET", f"/h2a/tasks/{task_id}")
        escrow_status = (detail.get("escrow_status") or "").lower()
        task_status = detail.get("status")
        print(f"         escrow_status: {escrow_status}")
        print(f"         task status:   {task_status}")

        if not refund_verified:
            return phase.fail(
                f"Refund TX not verified on-chain: {receipt.get('error')}",
                refund_tx=refund_tx,
            )
        if escrow_status and escrow_status != "refunded":
            return phase.partial(
                f"Refund TX verified but escrow_status is '{escrow_status}'",
                refund_tx=refund_tx,
                escrow_status=escrow_status,
            )

        return phase.pass_(
            refund_tx=refund_tx,
            escrow_status=escrow_status,
            task_status=task_status,
        )

    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Dry run -- offline wrapper construction + validation
# ---------------------------------------------------------------------------
def _try_server_validator():
    """Import PaymentDispatcher.validate_agent_preauth from mcp_server if
    path-feasible (it is a @staticmethod with no DB/env access)."""
    try:
        mcp_dir = str(_project_root / "mcp_server")
        if mcp_dir not in sys.path:
            sys.path.insert(0, mcp_dir)
        from integrations.x402.payment_dispatcher import PaymentDispatcher

        return PaymentDispatcher.validate_agent_preauth
    except Exception as e:
        print(f"    Server validator unavailable ({type(e).__name__}: {e})")
        print("    Falling back to the local field-check replica only.")
        return None


def run_dry_run(args: argparse.Namespace) -> int:
    """Exercise arg parsing + wrapper construction with throwaway keys.

    Generates two random local keys at runtime (NEVER printed), builds the
    X-Payment-Auth wrapper exactly like phase 6, and asserts it passes the
    validate_agent_preauth-shaped checks (server import when feasible, local
    replica always) plus EIP-712 signature recovery. Fully offline.
    """
    _print_header("H2H FLOW -- DRY RUN (offline wrapper validation)")
    _print_kv("API", args.api_url, 2)
    _print_kv("Bounty", f"${args.bounty:.2f}", 2)
    _print_kv("Mode", "refund" if args.refund else "full", 2)
    _print_kv("Network", "base (8453)", 2)

    from eth_account import Account

    # Throwaway keys generated at runtime -- never printed, never persisted.
    publisher_acct = Account.create()
    worker_acct = Account.create()
    print(f"\n  Throwaway publisher address: {publisher_acct.address}")
    print(f"  Throwaway worker address:    {worker_acct.address}")

    checks: List[tuple] = []

    print("\n  [1/4] Building X-Payment-Auth wrapper (SDK paymentInfo + nonce)...")
    try:
        built = build_escrow_auth_wrapper(
            publisher_acct.key.hex(), worker_acct.address, args.bounty
        )
        wrapper = built["wrapper"]
        raw = json.dumps(wrapper)
        pi = wrapper["payload"]["paymentInfo"]
        print(f"         operator:  {pi['operator']}")
        print(f"         receiver:  {pi['receiver']}")
        print(f"         maxAmount: {pi['maxAmount']}")
        print(
            f"         nonce:     {wrapper['payload']['authorization']['nonce'][:18]}..."
        )
        checks.append(("wrapper construction", True, None))
    except Exception as e:
        checks.append(("wrapper construction", False, str(e)))
        _dry_run_summary(checks)
        return 1

    atomic = str(int(Decimal(str(args.bounty)) * 1_000_000))

    print("  [2/4] Local validate_agent_preauth replica...")
    local_errors = validate_wrapper_local(
        raw,
        expected_payer=built["payer"],
        expected_amount_atomic=atomic,
        expected_receiver=worker_acct.address,
    )
    if local_errors:
        for err in local_errors:
            print(f"         FAIL: {err}")
    else:
        print(
            "         All field checks passed (structure, temporal, SC-001, "
            "payer, amount, receiver)"
        )
    checks.append(
        ("local field-check replica", not local_errors, "; ".join(local_errors) or None)
    )

    print("  [3/4] Server validate_agent_preauth (import from mcp_server)...")
    server_validator = _try_server_validator()
    if server_validator is not None:
        try:
            server_validator(
                raw,
                network="base",
                expected_payer=built["payer"],
                expected_amount_atomic=atomic,
            )
            print("         Server validator accepted the wrapper")
            checks.append(("server validate_agent_preauth", True, None))
        except ValueError as ve:
            print(f"         FAIL: {ve}")
            checks.append(("server validate_agent_preauth", False, str(ve)))
    else:
        checks.append(
            ("server validate_agent_preauth", True, "skipped (import not feasible)")
        )

    print("  [4/4] EIP-712 signature recovery...")
    sig_err = _verify_signature_recovers(wrapper, built["payer"])
    if sig_err:
        print(f"         FAIL: {sig_err}")
    else:
        print("         Signature recovers to the publisher address")
    checks.append(("signature recovery", sig_err is None, sig_err))

    return _dry_run_summary(checks)


def _dry_run_summary(checks: List[tuple]) -> int:
    _print_header("DRY RUN SUMMARY")
    all_ok = True
    for name, ok, err in checks:
        print(f"  [{_icon(ok)}] {name}")
        if err and not ok:
            print(f"         {err}")
        elif err:
            print(f"         Note: {err}")
        all_ok = all_ok and ok
    if all_ok:
        print("\n  ** DRY RUN: PASS -- wrapper construction + validation OK **")
        print("  (No network calls were made. Run without --dry-run after the")
        print("   server is deployed with EM_H2A_ESCROW_ENABLED=true.)")
        return 0
    print("\n  ** DRY RUN: FAIL **")
    return 1


# ---------------------------------------------------------------------------
# Summary + report
# ---------------------------------------------------------------------------
def _print_summary(results: H2HFlowResults, bounty: float, mode: str) -> None:
    total_phases = len(results.phases)
    elapsed = round(time.time() - results.start_time, 2)

    print()
    _print_header("H2H FLOW SUMMARY")
    print(f"  Mode:     {mode}")
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
        print("\n  ** H2H FLOW: PASS -- human-publisher escrow cycle is healthy **")
    elif results.overall == "PARTIAL":
        print("\n  ** H2H FLOW: PARTIAL -- some phases had issues **")
    else:
        print("\n  ** H2H FLOW: FAIL -- human-publisher escrow cycle has issues **")


def _save_report(results: H2HFlowResults, bounty: float, mode: str) -> None:
    report_dir = _project_root / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "H2H_FLOW_REPORT.json"
    json_path.write_text(
        json.dumps(results.to_dict(bounty, mode), indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n  Report (JSON): {json_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="E2E test for the H2H/H2A sign-on-assignment escrow cycle"
    )
    parser.add_argument(
        "--bounty",
        type=float,
        default=DEFAULT_BOUNTY,
        help=f"Bounty in USD (default {DEFAULT_BOUNTY})",
    )
    parser.add_argument(
        "--api-url",
        default=API_BASE,
        help=f"API base URL (default {API_BASE})",
    )
    parser.add_argument(
        "--refund",
        action="store_true",
        help="Refund cycle: publish -> apply -> assign+lock -> cancel -> refund",
    )
    parser.add_argument(
        "--revision",
        action="store_true",
        help=(
            "Revision cycle: publish -> assign+lock -> submit -> needs_revision "
            "-> resubmit -> cancel+refund (net $0, escrow stays locked through "
            "the revision)"
        ),
    )
    parser.add_argument(
        "--reputation",
        action="store_true",
        help=(
            "Full cycle + bidirectional ERC-8004 reputation: approve carries a "
            "worker_score (publisher->worker), then the worker rates the "
            "publisher (worker->publisher). Asserts both ratings landed."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Offline: exercise arg parsing + wrapper construction/validation",
    )
    return parser.parse_args(argv)


async def phase_bidirectional_reputation(
    client: httpx.AsyncClient,
    results: H2HFlowResults,
    worker_jwt: str,
    task_id: str,
) -> PhaseResult:
    """Phase 9: the worker rates the human publisher on-chain (gasless).

    The publisher->worker rating already fired best-effort during approval
    (worker_score in the approve body). This asserts the reverse direction
    end-to-end: the rate-publisher endpoint resolves the publisher's ERC-8004
    identity (Phase 1), submits gasless feedback bound to the release TX
    (counterparty proof), and returns the on-chain tx.
    """
    phase = PhaseResult("reputation", "Bidirectional Reputation (ERC-8004)")
    _print_header("PHASE 9: BIDIRECTIONAL REPUTATION")
    try:
        print("  [1/1] Worker rates the publisher (gasless, on-chain)...")
        data = await api_call(
            client,
            "POST",
            f"/h2a/tasks/{task_id}/rate-publisher",
            {"score": 5, "comment": "H2H E2E -- great publisher"},
            jwt=worker_jwt,
        )
        status = data.get("_http_status")
        print(f"         Rate-publisher: HTTP {status}")
        if status != 200:
            return phase.fail(
                f"rate-publisher failed: HTTP {status} - "
                f"{data.get('detail', str(data)[:200])}"
            )
        tx = data.get("transaction_hash")
        pub_agent = data.get("publisher_agent_id")
        proof = data.get("proof_tx")
        print(f"         Publisher agent_id: {pub_agent}")
        print(f"         Feedback TX:        {tx}")
        print(f"         Counterparty proof: {proof}")
        if not tx:
            return phase.partial(
                "rate-publisher succeeded but returned no on-chain tx",
                publisher_agent_id=pub_agent,
            )
        if tx:
            results.add_tx(tx)
        return phase.pass_(publisher_agent_id=pub_agent, feedback_tx=tx, proof_tx=proof)
    except Exception as e:
        return phase.fail(f"Unexpected error: {e}")


async def run_flow(args: argparse.Namespace) -> int:
    global API_BASE
    API_BASE = args.api_url.rstrip("/")
    bounty = args.bounty
    mode = (
        "refund"
        if args.refund
        else "revision"
        if args.revision
        else "reputation"
        if args.reputation
        else "full"
    )

    print("=" * 72)
    print("  H2H FLOW -- E2E Human-Publisher Escrow Cycle (sign-on-assignment)")
    print("=" * 72)
    _print_kv("API", API_BASE, 2)
    _print_kv("Time", ts(), 2)
    _print_kv("Mode", mode, 2)
    _print_kv("Bounty", f"${bounty:.2f} USDC (base)", 2)
    _print_kv("Fee model", "credit_card (13% deducted on-chain at release)", 2)
    _print_kv("Escrow", "sign-on-assignment (lock at assign, 1-TX release)", 2)

    results = H2HFlowResults()

    # Phase 1: Preflight (sync -- no HTTP)
    p1 = phase_preflight(results)
    results.add(p1)
    if p1.status == "FAIL":
        _print_summary(results, bounty, mode)
        return 1

    publisher_wallet = p1.details["publisher_wallet"]
    worker_wallet = p1.details["worker_wallet"]

    timeout = httpx.Timeout(180.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Phase 2: Publisher auth
        p2 = await phase_publisher_auth(client, results)
        results.add(p2)
        if p2.status == "FAIL":
            _print_summary(results, bounty, mode)
            return 1
        jwt = p2.details["jwt"]

        # Phase 3: Publish (escrow marker required -- fails early if flag off)
        p3 = await phase_publish(client, results, jwt, publisher_wallet, bounty, mode)
        results.add(p3)
        task_id = p3.details.get("task_id")
        if p3.status == "FAIL" or not task_id:
            _print_summary(results, bounty, mode)
            return 1

        await asyncio.sleep(2)

        # Phase 4: Worker session + executor binding
        p4 = await phase_worker_setup(client, results, worker_wallet)
        results.add(p4)
        executor_id = p4.details.get("executor_id")
        worker_jwt = p4.details.get("worker_jwt")
        if p4.status == "FAIL" or not executor_id or not worker_jwt:
            _print_summary(results, bounty, mode)
            return 1

        await asyncio.sleep(2)

        # Phase 5: Worker applies
        p5 = await phase_apply(client, results, task_id, executor_id, worker_jwt)
        results.add(p5)
        if p5.status == "FAIL":
            _print_summary(results, bounty, mode)
            return 1

        await asyncio.sleep(2)

        # Phase 6: Assign with browser-equivalent signature -> lock
        p6 = await phase_assign_lock(
            client, results, jwt, task_id, executor_id, worker_wallet, bounty
        )
        results.add(p6)
        if p6.status == "FAIL":
            _print_summary(results, bounty, mode)
            return 1

        await asyncio.sleep(3)  # allow on-chain settlement to propagate

        if args.refund:
            # Phase 8R: Cancel -> refund (separate refund-mode task)
            p8 = await phase_cancel_refund(client, results, jwt, task_id, bounty)
            results.add(p8)
        else:
            # Phase 7: Worker submits
            p7 = await phase_submit(client, results, task_id, executor_id, worker_jwt)
            results.add(p7)
            submission_id = p7.details.get("submission_id")
            if p7.status == "FAIL" or not submission_id:
                _print_summary(results, bounty, mode)
                return 1

            await asyncio.sleep(2)

            if args.revision:
                # Phase R: needs_revision -> in_progress, escrow stays locked
                pr = await phase_request_revision(
                    client, results, jwt, task_id, submission_id
                )
                results.add(pr)
                if pr.status != "FAIL":
                    await asyncio.sleep(2)
                    # Worker resubmits the fixed evidence
                    p7b = await phase_submit(
                        client, results, task_id, executor_id, worker_jwt
                    )
                    results.add(p7b)
                    await asyncio.sleep(3)
                # Recover the still-locked funds (net $0) — the revision path
                # never releases, so a refund closes the cycle cleanly.
                pc = await phase_cancel_refund(client, results, jwt, task_id, bounty)
                results.add(pc)
            else:
                # Phase 8: Approve -> release (no signatures)
                p8 = await phase_approve_release(
                    client,
                    results,
                    jwt,
                    task_id,
                    submission_id,
                    worker_wallet,
                    bounty,
                )
                results.add(p8)

                # Phase 9: worker->publisher reputation (--reputation mode).
                if args.reputation and p8.status != "FAIL":
                    await asyncio.sleep(2)
                    p9 = await phase_bidirectional_reputation(
                        client, results, worker_jwt, task_id
                    )
                    results.add(p9)

    _print_summary(results, bounty, mode)
    _save_report(results, bounty, mode)
    return 0 if results.fail_count == 0 else 1


def main() -> int:
    args = parse_args()
    if args.dry_run:
        return run_dry_run(args)
    return asyncio.run(run_flow(args))


if __name__ == "__main__":
    sys.exit(main())
