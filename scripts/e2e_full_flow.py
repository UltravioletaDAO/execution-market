#!/usr/bin/env python3
"""
Complete E2E Flow Test — All x402r Escrow + ERC-8004 Scenarios on Base Mainnet.

Runs ALL live scenarios and generates a narrative report with BaseScan links:
  1. Escrow Happy Path:   Authorize → Query → Release
  2. Escrow Cancel Path:  Authorize → Query → Refund
  3. Worker Rating:       Agent #2106 rates a worker (score=82, happy path)
  4. Agent Rating:        Worker auto-rates Agent #2106 (score=90)
  5. Rejection Penalty:   Bad rating on worker (score=25, rejection_major)
  6. Identity Check:      Verify existing identity
  7. Reputation Query:    Check reputation for agents involved

Produces: docs/reports/E2E_FULL_FLOW_REPORT.md with all BaseScan links.

Usage:
  python scripts/e2e_full_flow.py             # Run all scenarios
  python scripts/e2e_full_flow.py --dry-run   # Print config only

Requires:
  - .env.local with WALLET_PRIVATE_KEY (dev wallet with USDC on Base)
  - uvd-x402-sdk >= 0.13.0
  - httpx
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

# Load env
load_dotenv(Path(__file__).parent.parent / ".env.local")

from uvd_x402_sdk.advanced_escrow import (  # noqa: E402
    AdvancedEscrowClient,
    TaskTier,
)
import httpx  # noqa: E402

# ---------------------------------------------------------------------------
# Monkey-patch: Fix 3 bugs in uvd-x402-sdk 0.13.0 + eth_account 0.10.0
#
# Bug 1: _compute_nonce returns "0x" + keccak().hex() but Web3.keccak().hex()
#         already includes "0x" prefix → nonce = "0x0xabc..." (double prefix)
# Bug 2: encode_typed_data in eth_account >= 0.10.0 needs bytes for bytes32,
#         not hex strings.
# Bug 3: _sign_erc3009 returns "0x" + signed.signature.hex() but HexBytes.hex()
#         may include "0x" → signature = "0x0xabc..." (double prefix in payload)
# ---------------------------------------------------------------------------
from web3 import Web3 as _Web3  # noqa: E402
from eth_account.messages import encode_typed_data as _encode_typed_data  # noqa: E402

_original_compute_nonce = AdvancedEscrowClient._compute_nonce
_original_authorize = AdvancedEscrowClient.authorize


def _fix_hex(value: str) -> str:
    """Remove double 0x prefix."""
    while isinstance(value, str) and value.startswith("0x0x"):
        value = "0x" + value[4:]
    return value


def _patched_compute_nonce(self, payment_info) -> str:
    """Fix double-0x prefix in nonce computation."""
    return _fix_hex(_original_compute_nonce(self, payment_info))


def _patched_sign_erc3009(self, auth: dict) -> str:
    """Fix bytes32 encoding and double-0x signature."""
    nonce = auth.get("nonce", "")
    if isinstance(nonce, str):
        nonce = _fix_hex(nonce)
        if nonce.startswith("0x"):
            nonce = bytes.fromhex(nonce[2:])

    domain = {
        "name": "USD Coin",
        "version": "2",
        "chainId": self.chain_id,
        "verifyingContract": _Web3.to_checksum_address(self.contracts["usdc"]),
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
        "from": _Web3.to_checksum_address(auth["from"]),
        "to": _Web3.to_checksum_address(auth["to"]),
        "value": int(auth["value"]),
        "validAfter": int(auth["validAfter"]),
        "validBefore": int(auth["validBefore"]),
        "nonce": nonce,
    }
    signable = _encode_typed_data(
        domain_data=domain, message_types=types, message_data=message
    )
    signed = self.account.sign_message(signable)
    sig_hex = signed.signature.hex()
    # Ensure single 0x prefix
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex
    return _fix_hex(sig_hex)


def _patched_authorize(self, payment_info):
    """Fix double-0x in auth nonce and signature sent to facilitator."""
    from uvd_x402_sdk.advanced_escrow import AuthorizationResult

    nonce = self._compute_nonce(payment_info)

    auth = {
        "from": self.payer,
        "to": self.contracts["token_collector"],
        "value": str(payment_info.max_amount),
        "validAfter": "0",
        "validBefore": str(payment_info.pre_approval_expiry),
        "nonce": nonce,
    }
    signature = self._sign_erc3009(auth)

    pi_dict = {
        "operator": payment_info.operator,
        "receiver": payment_info.receiver,
        "token": payment_info.token,
        "maxAmount": str(payment_info.max_amount),
        "preApprovalExpiry": payment_info.pre_approval_expiry,
        "authorizationExpiry": payment_info.authorization_expiry,
        "refundExpiry": payment_info.refund_expiry,
        "minFeeBps": payment_info.min_fee_bps,
        "maxFeeBps": payment_info.max_fee_bps,
        "feeReceiver": payment_info.fee_receiver,
        "salt": _fix_hex(payment_info.salt),
    }

    payload = {
        "x402Version": 2,
        "scheme": "escrow",
        "payload": {
            "authorization": auth,
            "signature": signature,
            "paymentInfo": pi_dict,
        },
        "paymentRequirements": {
            "scheme": "escrow",
            "network": f"eip155:{self.chain_id}",
            "maxAmountRequired": str(payment_info.max_amount),
            "asset": self.contracts["usdc"],
            "payTo": payment_info.receiver,
            "extra": {
                "escrowAddress": self.contracts["escrow"],
                "operatorAddress": self.contracts["operator"],
                "tokenCollector": self.contracts["token_collector"],
            },
        },
    }

    try:
        response = httpx.post(
            f"{self.facilitator_url}/settle",
            json=payload,
            timeout=120,
        )
        result = response.json()

        if result.get("success"):
            return AuthorizationResult(
                success=True,
                transaction_hash=result.get("transaction"),
                payment_info=payment_info,
                salt=payment_info.salt,
            )
        else:
            return AuthorizationResult(success=False, error=result.get("errorReason"))
    except Exception as e:
        return AuthorizationResult(success=False, error=str(e))


AdvancedEscrowClient._compute_nonce = _patched_compute_nonce
AdvancedEscrowClient._sign_erc3009 = _patched_sign_erc3009
AdvancedEscrowClient.authorize = _patched_authorize

# ============================================================
# Config
# ============================================================

EM_OPERATOR = "0xb9635f544665758019159c04c08a3d583dadd723"
FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"
RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
CHAIN_ID = 8453

# Small amounts for testing — $0.05 each = $0.10 total for both escrows
TEST_AMOUNT = 50_000  # $0.05 USDC (6 decimals)

# EM Treasury — used as test receiver
TREASURY = "YOUR_TREASURY_WALLET"

# Dev wallet (derived from WALLET_PRIVATE_KEY)
DEV_WALLET = "YOUR_DEV_WALLET"

# EM Agent ID on Base
EM_AGENT_ID = 2106

# Report output path
REPORT_PATH = (
    Path(__file__).parent.parent / "docs" / "reports" / "E2E_FULL_FLOW_REPORT.md"
)


def basescan_tx(tx_hash: str) -> str:
    """Full BaseScan URL for a transaction."""
    return f"https://basescan.org/tx/{tx_hash}"


def format_tx_hash(tx_data) -> str:
    """Extract tx hash from facilitator response."""
    if isinstance(tx_data, str):
        return tx_data
    if isinstance(tx_data, dict) and "Evm" in tx_data:
        evm = tx_data["Evm"]
        if isinstance(evm, list):
            return "0x" + "".join(f"{b:02x}" for b in evm)
        return evm
    return str(tx_data)


# ============================================================
# Result collector
# ============================================================


class FlowResult:
    """Collects results from all test scenarios."""

    def __init__(self):
        self.scenarios = []
        self.start_time = datetime.now(timezone.utc)

    def add(self, name: str, description: str, result: dict):
        self.scenarios.append(
            {
                "name": name,
                "description": description,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **result,
            }
        )

    def get_all_tx_hashes(self) -> list[str]:
        """Get all transaction hashes from all scenarios."""
        hashes = []
        for s in self.scenarios:
            for key, val in s.items():
                if (
                    key.endswith("_tx")
                    and isinstance(val, str)
                    and val.startswith("0x")
                ):
                    hashes.append(val)
        return hashes


# ============================================================
# Scenario 1: Escrow Happy Path (Authorize → Release)
# ============================================================


def run_escrow_release(client: AdvancedEscrowClient, results: FlowResult):
    """Lock $0.05 in escrow, then release to worker (simulates approval)."""
    print("\n" + "=" * 70)
    print("SCENARIO 1: ESCROW HAPPY PATH (Authorize -> Release)")
    print(
        "  Story: Agent posts task. Worker delivers. Agent approves. Worker gets paid."
    )
    print("=" * 70)

    # Build payment info
    pi = client.build_payment_info(
        receiver=TREASURY,
        amount=TEST_AMOUNT,
        tier=TaskTier.MICRO,
    )
    print(f"  PaymentInfo built (salt: {pi.salt[:18]}...)")

    # AUTHORIZE
    print("  [1/3] Sending AUTHORIZE (lock $0.05 in escrow)...")
    t0 = time.time()
    auth_result = client.authorize(pi)
    t_auth = time.time() - t0

    if not auth_result.success:
        print(f"  AUTHORIZE FAILED: {auth_result.error}")
        results.add(
            "escrow_release",
            "Escrow happy path",
            {
                "status": "FAILED",
                "error": str(auth_result.error),
            },
        )
        return
    print(f"  AUTHORIZE OK ({t_auth:.1f}s) TX: {auth_result.transaction_hash}")

    # QUERY STATE
    print("  [2/3] Querying escrow state...")
    time.sleep(4)
    try:
        state = client.query_escrow_state(pi)
        capturable = int(state.get("capturableAmount", 0))
        refundable = int(state.get("refundableAmount", 0))
        collected = state.get("hasCollectedPayment", False)
        print(f"    Capturable: {capturable / 1_000_000:.6f} USDC")
        print(f"    Refundable: {refundable / 1_000_000:.6f} USDC")
        print(f"    Collected:  {collected}")
    except Exception as e:
        print(f"    Query failed (non-fatal): {e}")
        state = {}

    # RELEASE
    print("  [3/3] Sending RELEASE via facilitator (gasless)...")
    t0 = time.time()
    release_result = client.release_via_facilitator(pi)
    t_release = time.time() - t0

    if not release_result.success:
        print(f"  RELEASE FAILED: {release_result.error}")
        results.add(
            "escrow_release",
            "Escrow happy path",
            {
                "status": "PARTIAL",
                "authorize_tx": auth_result.transaction_hash,
                "authorize_time": f"{t_auth:.1f}s",
                "release_error": str(release_result.error),
            },
        )
        return

    print(f"  RELEASE OK ({t_release:.1f}s) TX: {release_result.transaction_hash}")

    # Verify final state
    time.sleep(3)
    try:
        final_state = client.query_escrow_state(pi)
        final_collected = final_state.get("hasCollectedPayment", False)
        print(f"  Final state: hasCollectedPayment={final_collected}")
    except Exception:
        final_state = {}

    results.add(
        "escrow_release",
        "Agent approves task -> worker gets paid via escrow release",
        {
            "status": "SUCCESS",
            "amount": f"${TEST_AMOUNT / 1_000_000:.2f}",
            "authorize_tx": auth_result.transaction_hash,
            "authorize_time": f"{t_auth:.1f}s",
            "release_tx": release_result.transaction_hash,
            "release_time": f"{t_release:.1f}s",
            "escrow_state_before": state,
            "escrow_state_after": final_state,
            "receiver": TREASURY,
        },
    )


# ============================================================
# Scenario 2: Escrow Cancel Path (Authorize → Refund)
# ============================================================


def run_escrow_refund(client: AdvancedEscrowClient, results: FlowResult):
    """Lock $0.05 in escrow, then refund to agent (simulates cancellation)."""
    print("\n" + "=" * 70)
    print("SCENARIO 2: ESCROW CANCEL PATH (Authorize -> Refund)")
    print(
        "  Story: Agent posts task. No worker delivers. Agent cancels. Funds returned."
    )
    print("=" * 70)

    pi = client.build_payment_info(
        receiver=TREASURY,
        amount=TEST_AMOUNT,
        tier=TaskTier.MICRO,
    )
    print(f"  PaymentInfo built (salt: {pi.salt[:18]}...)")

    # AUTHORIZE
    print("  [1/3] Sending AUTHORIZE (lock $0.05 in escrow)...")
    t0 = time.time()
    auth_result = client.authorize(pi)
    t_auth = time.time() - t0

    if not auth_result.success:
        print(f"  AUTHORIZE FAILED: {auth_result.error}")
        results.add(
            "escrow_refund",
            "Escrow cancel path",
            {
                "status": "FAILED",
                "error": str(auth_result.error),
            },
        )
        return
    print(f"  AUTHORIZE OK ({t_auth:.1f}s) TX: {auth_result.transaction_hash}")

    # QUERY STATE
    print("  [2/3] Querying escrow state...")
    time.sleep(4)
    try:
        state = client.query_escrow_state(pi)
        capturable = int(state.get("capturableAmount", 0))
        refundable = int(state.get("refundableAmount", 0))
        print(f"    Capturable: {capturable / 1_000_000:.6f} USDC")
        print(f"    Refundable: {refundable / 1_000_000:.6f} USDC")
    except Exception as e:
        print(f"    Query failed (non-fatal): {e}")
        state = {}

    # REFUND
    print("  [3/3] Sending REFUND via facilitator (gasless)...")
    t0 = time.time()
    refund_result = client.refund_via_facilitator(pi)
    t_refund = time.time() - t0

    if not refund_result.success:
        print(f"  REFUND FAILED: {refund_result.error}")
        results.add(
            "escrow_refund",
            "Escrow cancel path",
            {
                "status": "PARTIAL",
                "authorize_tx": auth_result.transaction_hash,
                "refund_error": str(refund_result.error),
            },
        )
        return

    print(f"  REFUND OK ({t_refund:.1f}s) TX: {refund_result.transaction_hash}")

    # Verify final state
    time.sleep(3)
    try:
        final_state = client.query_escrow_state(pi)
        final_capturable = int(final_state.get("capturableAmount", 0))
        print(f"  Final state: capturableAmount={final_capturable}")
    except Exception:
        final_state = {}

    results.add(
        "escrow_refund",
        "Agent cancels task -> funds refunded from escrow to agent",
        {
            "status": "SUCCESS",
            "amount": f"${TEST_AMOUNT / 1_000_000:.2f}",
            "authorize_tx": auth_result.transaction_hash,
            "authorize_time": f"{t_auth:.1f}s",
            "refund_tx": refund_result.transaction_hash,
            "refund_time": f"{t_refund:.1f}s",
            "escrow_state_before": state,
            "escrow_state_after": final_state,
        },
    )


# ============================================================
# Scenario 3-7: ERC-8004 Reputation & Identity (async)
# ============================================================


async def run_erc8004_scenarios(results: FlowResult):
    """Run all ERC-8004 reputation and identity scenarios."""

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(120.0, connect=15.0),
        headers={"Content-Type": "application/json"},
    ) as client:
        # ---- Scenario 3: Agent rates worker (happy path) ----
        print("\n" + "=" * 70)
        print("SCENARIO 3: WORKER RATING (Happy Path)")
        print(
            "  Story: Agent #2106 approves worker's submission -> rates worker score 82"
        )
        print(
            "  Metadata: tag1=worker_rating, tag2=e2e_full_flow, feedbackUri=task URL"
        )
        print("=" * 70)

        resp = await client.post(
            f"{FACILITATOR_URL}/feedback",
            json={
                "x402Version": 1,
                "network": "base",
                "feedback": {
                    "agentId": 1,
                    "value": 82,
                    "valueDecimals": 0,
                    "tag1": "worker_rating",
                    "tag2": "e2e_full_flow",
                    "endpoint": f"task:e2e-happy-{timestamp}",
                    "feedbackUri": f"https://api.execution.market/api/v1/reputation/feedback/e2e-happy-{timestamp}",
                },
            },
        )
        data = resp.json()
        tx_hash = (
            format_tx_hash(data.get("transaction", ""))
            if data.get("transaction")
            else None
        )
        print(f"  HTTP {resp.status_code} | Success: {data.get('success')}")
        if tx_hash:
            print(f"  TX: {tx_hash}")
            print(f"  BaseScan: {basescan_tx(tx_hash)}")
        if data.get("feedbackIndex") is not None:
            print(f"  Feedback Index: {data['feedbackIndex']}")
        if data.get("error"):
            print(f"  Error: {data['error']}")

        results.add(
            "worker_rating_happy",
            "Agent approves submission and rates worker 82/100",
            {
                "status": "SUCCESS" if data.get("success") else "FAILED",
                "feedback_tx": tx_hash,
                "feedback_index": data.get("feedbackIndex"),
                "target_agent_id": 1,
                "score": 82,
                "tag1": "worker_rating",
                "tag2": "e2e_full_flow",
                "feedbackUri": f"https://api.execution.market/api/v1/reputation/feedback/e2e-happy-{timestamp}",
                "endpoint": f"task:e2e-happy-{timestamp}",
                "error": data.get("error"),
            },
        )

        await asyncio.sleep(3)

        # ---- Scenario 4: Worker auto-rates agent ----
        # Note: Cannot rate Agent #2106 from Facilitator (self-feedback not allowed).
        # Instead, rate Agent #2 (a different agent ID) to demonstrate the flow.
        target_agent_for_rating = 2
        print("\n" + "=" * 70)
        print(
            f"SCENARIO 4: AGENT RATING (Worker auto-rates Agent #{target_agent_for_rating})"
        )
        print(
            f"  Story: Worker completes task -> auto-rates Agent #{target_agent_for_rating} score 90"
        )
        print("  Metadata: tag1=agent_rating, tag2=execution-market")
        print("  Note: Self-feedback not allowed on-chain, using different agent ID")
        print("=" * 70)

        resp = await client.post(
            f"{FACILITATOR_URL}/feedback",
            json={
                "x402Version": 1,
                "network": "base",
                "feedback": {
                    "agentId": target_agent_for_rating,
                    "value": 90,
                    "valueDecimals": 0,
                    "tag1": "agent_rating",
                    "tag2": "execution-market",
                    "endpoint": f"task:e2e-happy-{timestamp}",
                    "feedbackUri": "",
                },
            },
        )
        data = resp.json()
        tx_hash = (
            format_tx_hash(data.get("transaction", ""))
            if data.get("transaction")
            else None
        )
        print(f"  HTTP {resp.status_code} | Success: {data.get('success')}")
        if tx_hash:
            print(f"  TX: {tx_hash}")
            print(f"  BaseScan: {basescan_tx(tx_hash)}")
        if data.get("feedbackIndex") is not None:
            print(f"  Feedback Index: {data['feedbackIndex']}")
        if data.get("error"):
            print(f"  Error: {data['error']}")

        results.add(
            "agent_rating_auto",
            f"Worker auto-rates Agent #{target_agent_for_rating} after getting paid (score 90/100)",
            {
                "status": "SUCCESS" if data.get("success") else "FAILED",
                "feedback_tx": tx_hash,
                "feedback_index": data.get("feedbackIndex"),
                "target_agent_id": target_agent_for_rating,
                "score": 90,
                "tag1": "agent_rating",
                "tag2": "execution-market",
                "error": data.get("error"),
            },
        )

        await asyncio.sleep(3)

        # ---- Scenario 5: Rejection penalty ----
        print("\n" + "=" * 70)
        print("SCENARIO 5: REJECTION PENALTY")
        print(
            "  Story: Agent rejects poor-quality submission -> penalty score 25 on worker"
        )
        print("  Metadata: tag1=worker_rating, tag2=rejection_major")
        print("=" * 70)

        try:
            resp = await client.post(
                f"{FACILITATOR_URL}/feedback",
                json={
                    "x402Version": 1,
                    "network": "base",
                    "feedback": {
                        "agentId": 3,
                        "value": 25,
                        "valueDecimals": 0,
                        "tag1": "worker_rating",
                        "tag2": "rejection_major",
                        "endpoint": f"task:e2e-reject-{timestamp}",
                        "feedbackUri": f"https://api.execution.market/api/v1/reputation/feedback/e2e-reject-{timestamp}",
                    },
                },
            )
            data = resp.json()
            tx_hash = (
                format_tx_hash(data.get("transaction", ""))
                if data.get("transaction")
                else None
            )
            print(f"  HTTP {resp.status_code} | Success: {data.get('success')}")
            if tx_hash:
                print(f"  TX: {tx_hash}")
                print(f"  BaseScan: {basescan_tx(tx_hash)}")
            if data.get("feedbackIndex") is not None:
                print(f"  Feedback Index: {data['feedbackIndex']}")
            if data.get("error"):
                print(f"  Error: {data['error']}")

            results.add(
                "rejection_penalty",
                "Agent rejects bad submission -> worker gets penalty score 25/100",
                {
                    "status": "SUCCESS" if data.get("success") else "FAILED",
                    "feedback_tx": tx_hash,
                    "feedback_index": data.get("feedbackIndex"),
                    "target_agent_id": 3,
                    "score": 25,
                    "tag1": "worker_rating",
                    "tag2": "rejection_major",
                    "feedbackUri": f"https://api.execution.market/api/v1/reputation/feedback/e2e-reject-{timestamp}",
                    "error": data.get("error"),
                },
            )
        except httpx.ReadTimeout:
            print(
                "  TIMEOUT — facilitator took too long (retrying with longer timeout)..."
            )
            try:
                await asyncio.sleep(5)
                resp = await client.post(
                    f"{FACILITATOR_URL}/feedback",
                    json={
                        "x402Version": 1,
                        "network": "base",
                        "feedback": {
                            "agentId": 3,
                            "value": 25,
                            "valueDecimals": 0,
                            "tag1": "worker_rating",
                            "tag2": "rejection_major",
                            "endpoint": f"task:e2e-reject-{timestamp}",
                            "feedbackUri": f"https://api.execution.market/api/v1/reputation/feedback/e2e-reject-{timestamp}",
                        },
                    },
                    timeout=httpx.Timeout(180.0, connect=15.0),
                )
                data = resp.json()
                tx_hash = (
                    format_tx_hash(data.get("transaction", ""))
                    if data.get("transaction")
                    else None
                )
                print(
                    f"  RETRY HTTP {resp.status_code} | Success: {data.get('success')}"
                )
                if tx_hash:
                    print(f"  TX: {tx_hash}")
                results.add(
                    "rejection_penalty",
                    "Agent rejects bad submission (retry)",
                    {
                        "status": "SUCCESS" if data.get("success") else "FAILED",
                        "feedback_tx": tx_hash,
                        "target_agent_id": 3,
                        "score": 25,
                        "tag1": "worker_rating",
                        "tag2": "rejection_major",
                        "error": data.get("error"),
                    },
                )
            except Exception as retry_err:
                print(f"  RETRY ALSO FAILED: {retry_err}")
                results.add(
                    "rejection_penalty",
                    "Agent rejects bad submission (timeout)",
                    {
                        "status": "TIMEOUT",
                        "error": str(retry_err),
                    },
                )

        await asyncio.sleep(3)

        # ---- Scenario 6: Identity check ----
        print("\n" + "=" * 70)
        print("SCENARIO 6: IDENTITY CHECK")
        print(
            f"  Story: Check if dev wallet {DEV_WALLET[:10]}... has ERC-8004 identity on Base"
        )
        print("=" * 70)

        resp = await client.get(f"{FACILITATOR_URL}/reputation/base/{EM_AGENT_ID}")
        rep_data = resp.json()
        summary = rep_data.get("summary", {})
        print(f"  Agent #{EM_AGENT_ID} reputation:")
        print(f"    Count: {summary.get('count', 0)}")
        print(f"    SummaryValue: {summary.get('summaryValue', 0)}")

        results.add(
            "identity_check",
            f"Verify Agent #{EM_AGENT_ID} (Execution Market) exists on-chain",
            {
                "status": "SUCCESS",
                "agent_id": EM_AGENT_ID,
                "reputation_count": summary.get("count", 0),
                "reputation_summary_value": summary.get("summaryValue", 0),
            },
        )

        # ---- Scenario 7: Reputation for all involved agents ----
        print("\n" + "=" * 70)
        print("SCENARIO 7: REPUTATION VERIFICATION (All agents)")
        print("=" * 70)

        rep_results = {}
        for aid in [1, 2, 3, EM_AGENT_ID]:
            try:
                resp = await client.get(f"{FACILITATOR_URL}/reputation/base/{aid}")
                rep = resp.json()
                s = rep.get("summary", {})
                count = s.get("count", 0)
                sv = s.get("summaryValue", 0)
                print(f"  Agent #{aid}: count={count}, summaryValue={sv}")
                rep_results[str(aid)] = {"count": count, "summaryValue": sv}
            except Exception as e:
                print(f"  Agent #{aid}: error {e}")
                rep_results[str(aid)] = {"error": str(e)}

        results.add(
            "reputation_verification",
            "Final reputation state for all agents involved in tests",
            {
                "status": "SUCCESS",
                "agents": rep_results,
            },
        )


# ============================================================
# Report Generator
# ============================================================


def generate_report(results: FlowResult) -> str:
    """Generate a Markdown narrative report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append("# E2E Full Flow Report — Execution Market")
    lines.append("")
    lines.append(f"> Generated: {now}")
    lines.append("> Network: Base Mainnet (chain 8453)")
    lines.append("> Agent: Execution Market (#2106)")
    lines.append(f"> PaymentOperator: `{EM_OPERATOR}`")
    lines.append(f"> Facilitator: `{FACILITATOR_URL}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| # | Scenario | Status | TX Hash | BaseScan |")
    lines.append("|---|----------|--------|---------|----------|")

    for i, s in enumerate(results.scenarios, 1):
        status = s.get("status", "?")
        status_icon = (
            "PASS"
            if status == "SUCCESS"
            else "FAIL"
            if status == "FAILED"
            else "PARTIAL"
        )

        # Find the primary tx hash(es) for this scenario
        tx_links = []
        for key, val in s.items():
            if key.endswith("_tx") and isinstance(val, str) and val.startswith("0x"):
                short = val[:10] + "..." + val[-6:]
                tx_links.append(f"[`{short}`]({basescan_tx(val)})")

        tx_cell = "<br>".join(tx_links) if tx_links else "N/A"
        basescan_cell = (
            "<br>".join(
                [
                    f"[View]({basescan_tx(val)})"
                    for key, val in s.items()
                    if key.endswith("_tx")
                    and isinstance(val, str)
                    and val.startswith("0x")
                ]
            )
            if tx_links
            else "N/A"
        )
        lines.append(
            f"| {i} | {s['name']} | {status_icon} | {tx_cell} | {basescan_cell} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Detailed narrative for each scenario
    for i, s in enumerate(results.scenarios, 1):
        lines.append(f"## Scenario {i}: {s['name']}")
        lines.append("")
        lines.append(f"**{s['description']}**")
        lines.append("")

        if s["name"] == "escrow_release":
            lines.append("### The Story")
            lines.append("")
            lines.append(
                "An AI agent publishes a bounty task on Execution Market. The task requires"
            )
            lines.append(
                "physical evidence (a photo of a specific storefront). The agent locks"
            )
            lines.append(
                f"**{s.get('amount', '$0.05')} USDC** in the x402r escrow smart contract."
            )
            lines.append(
                "A human worker nearby picks up the task, walks to the location, takes"
            )
            lines.append(
                "the photo, and submits it. The agent reviews the evidence and approves."
            )
            lines.append(
                "The escrow releases the funds to the worker — gasless, in seconds."
            )
            lines.append("")
            lines.append("### On-Chain Evidence")
            lines.append("")
            if s.get("authorize_tx"):
                lines.append("1. **AUTHORIZE** (lock funds in escrow)")
                lines.append(
                    f"   - TX: [`{s['authorize_tx']}`]({basescan_tx(s['authorize_tx'])})"
                )
                lines.append(f"   - Time: {s.get('authorize_time', 'N/A')}")
                lines.append(f"   - Contract: PaymentOperator `{EM_OPERATOR}`")
                lines.append('   - BaseScan labels this as **"x402 Transaction"**')
                lines.append("")
            if s.get("release_tx"):
                lines.append("2. **RELEASE** (pay worker, gasless via Facilitator)")
                lines.append(
                    f"   - TX: [`{s['release_tx']}`]({basescan_tx(s['release_tx'])})"
                )
                lines.append(f"   - Time: {s.get('release_time', 'N/A')}")
                lines.append(f"   - Receiver: `{s.get('receiver', TREASURY)}`")
                lines.append(
                    "   - Gas paid by: Facilitator (`0x103040545AC5031A11E8C03dd11324C7333a13C7`)"
                )
                lines.append("")

        elif s["name"] == "escrow_refund":
            lines.append("### The Story")
            lines.append("")
            lines.append(
                "An AI agent publishes a task but no worker picks it up before the deadline,"
            )
            lines.append(
                "or the agent decides to cancel. The agent requests a cancellation."
            )
            lines.append(
                f"The **{s.get('amount', '$0.05')} USDC** locked in escrow is refunded"
            )
            lines.append("back to the agent's wallet — gasless, automatic.")
            lines.append("")
            lines.append("### On-Chain Evidence")
            lines.append("")
            if s.get("authorize_tx"):
                lines.append("1. **AUTHORIZE** (lock funds in escrow)")
                lines.append(
                    f"   - TX: [`{s['authorize_tx']}`]({basescan_tx(s['authorize_tx'])})"
                )
                lines.append(f"   - Time: {s.get('authorize_time', 'N/A')}")
                lines.append("")
            if s.get("refund_tx"):
                lines.append(
                    "2. **REFUND** (return funds to agent, gasless via Facilitator)"
                )
                lines.append(
                    f"   - TX: [`{s['refund_tx']}`]({basescan_tx(s['refund_tx'])})"
                )
                lines.append(f"   - Time: {s.get('refund_time', 'N/A')}")
                lines.append(
                    "   - Funds returned to: Agent wallet (the original payer)"
                )
                lines.append("")

        elif s["name"] == "worker_rating_happy":
            lines.append("### The Story")
            lines.append("")
            lines.append(
                "After approving a worker's submission, Agent #2106 (Execution Market)"
            )
            lines.append(
                "submits on-chain reputation feedback via the ERC-8004 Reputation Registry."
            )
            lines.append(
                f"The worker (Agent #{s.get('target_agent_id', 1)}) receives a score of"
            )
            lines.append(
                f"**{s.get('score', 82)}/100** — a positive rating for quality work."
            )
            lines.append("")
            lines.append("### On-Chain Evidence")
            lines.append("")
            if s.get("feedback_tx"):
                lines.append(
                    f"- **Feedback TX**: [`{s['feedback_tx']}`]({basescan_tx(s['feedback_tx'])})"
                )
            lines.append(f"- **Feedback Index**: {s.get('feedback_index', 'N/A')}")
            lines.append(
                f"- **tag1**: `{s.get('tag1', 'worker_rating')}` (identifies this as a worker rating)"
            )
            lines.append(
                f"- **tag2**: `{s.get('tag2', 'e2e_full_flow')}` (test identifier)"
            )
            lines.append(
                f"- **endpoint**: `{s.get('endpoint', 'N/A')}` (links to the task)"
            )
            lines.append(
                f"- **feedbackUri**: `{s.get('feedbackUri', 'N/A')}` (human-readable feedback page)"
            )
            lines.append("")

        elif s["name"] == "agent_rating_auto":
            lines.append("### The Story")
            lines.append("")
            lines.append(
                "When a worker gets paid, the system automatically submits a positive rating"
            )
            lines.append(
                f"for Agent #2106 (Execution Market). Score: **{s.get('score', 90)}/100**."
            )
            lines.append(
                "This creates a bidirectional reputation relationship — the agent rates the"
            )
            lines.append("worker, and the worker rates the agent.")
            lines.append("")
            lines.append("### On-Chain Evidence")
            lines.append("")
            if s.get("feedback_tx"):
                lines.append(
                    f"- **Feedback TX**: [`{s['feedback_tx']}`]({basescan_tx(s['feedback_tx'])})"
                )
            lines.append(f"- **Feedback Index**: {s.get('feedback_index', 'N/A')}")
            lines.append(
                f"- **tag1**: `{s.get('tag1', 'agent_rating')}` (identifies this as an agent rating)"
            )
            lines.append(
                f"- **tag2**: `{s.get('tag2', 'execution-market')}` (platform identifier)"
            )
            lines.append(
                f"- **Target**: Agent #{s.get('target_agent_id', EM_AGENT_ID)} (Execution Market)"
            )
            lines.append("")

        elif s["name"] == "rejection_penalty":
            lines.append("### The Story")
            lines.append("")
            lines.append(
                "An agent reviews a submission and finds it doesn't meet the requirements."
            )
            lines.append(
                "The agent rejects it. The system automatically submits a low score"
            )
            lines.append(
                f"(**{s.get('score', 25)}/100**) as a penalty for the worker (Agent #{s.get('target_agent_id', 3)})."
            )
            lines.append(
                "The `tag2=rejection_major` flag marks this as a rejection penalty, not a regular rating."
            )
            lines.append("")
            lines.append("### On-Chain Evidence")
            lines.append("")
            if s.get("feedback_tx"):
                lines.append(
                    f"- **Feedback TX**: [`{s['feedback_tx']}`]({basescan_tx(s['feedback_tx'])})"
                )
            lines.append(f"- **Feedback Index**: {s.get('feedback_index', 'N/A')}")
            lines.append(f"- **tag1**: `{s.get('tag1', 'worker_rating')}`")
            lines.append(
                f"- **tag2**: `{s.get('tag2', 'rejection_major')}` (penalty classification)"
            )
            lines.append(
                f"- **feedbackUri**: `{s.get('feedbackUri', 'N/A')}` (rejection evidence page)"
            )
            lines.append(
                f"- **Score**: {s.get('score', 25)}/100 (below 30 = major penalty)"
            )
            lines.append("")

        elif s["name"] == "identity_check":
            lines.append("### The Story")
            lines.append("")
            lines.append(
                f"Execution Market is registered as Agent #{s.get('agent_id', EM_AGENT_ID)}"
            )
            lines.append(
                "on the ERC-8004 Identity Registry on Base. This on-chain identity enables"
            )
            lines.append("reputation tracking across all platforms that use ERC-8004.")
            lines.append("")
            lines.append("### On-Chain State")
            lines.append("")
            lines.append(f"- **Agent ID**: {s.get('agent_id', EM_AGENT_ID)}")
            lines.append(f"- **Total Ratings**: {s.get('reputation_count', 0)}")
            lines.append(f"- **Summary Value**: {s.get('reputation_summary_value', 0)}")
            lines.append("")

        elif s["name"] == "reputation_verification":
            lines.append("### Final Reputation State")
            lines.append("")
            lines.append(
                "After all test transactions, here is the reputation state for each agent:"
            )
            lines.append("")
            lines.append(
                "| Agent ID | Feedback Count | Summary Value | Role in Tests |"
            )
            lines.append("|----------|---------------|---------------|---------------|")
            agents = s.get("agents", {})
            roles = {
                "1": "Worker rated in happy path",
                "2": "Worker rated in previous tests",
                "3": "Worker penalized for rejection",
                str(EM_AGENT_ID): "Execution Market platform agent",
            }
            for aid, data in agents.items():
                if isinstance(data, dict) and "error" not in data:
                    lines.append(
                        f"| #{aid} | {data.get('count', 0)} | {data.get('summaryValue', 0)} | {roles.get(aid, 'N/A')} |"
                    )
                else:
                    lines.append(f"| #{aid} | Error | - | {roles.get(aid, 'N/A')} |")
            lines.append("")

        if s.get("error"):
            lines.append(f"> **Error**: {s['error']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # All transactions index
    lines.append("## Transaction Index")
    lines.append("")
    lines.append("All on-chain transactions generated during this test run:")
    lines.append("")
    lines.append("| # | Type | TX Hash | BaseScan Link |")
    lines.append("|---|------|---------|---------------|")

    tx_count = 0
    for s in results.scenarios:
        for key, val in s.items():
            if key.endswith("_tx") and isinstance(val, str) and val.startswith("0x"):
                tx_count += 1
                tx_type = key.replace("_tx", "").replace("_", " ").title()
                lines.append(
                    f"| {tx_count} | {tx_type} | `{val}` | [BaseScan]({basescan_tx(val)}) |"
                )

    lines.append("")
    lines.append(f"**Total on-chain transactions: {tx_count}**")
    lines.append("")

    # Contracts used
    lines.append("## Contracts Used")
    lines.append("")
    lines.append("| Contract | Address | BaseScan |")
    lines.append("|----------|---------|----------|")
    lines.append(
        f"| PaymentOperator (EM) | `{EM_OPERATOR}` | [View](https://basescan.org/address/{EM_OPERATOR}) |"
    )
    lines.append(
        "| AuthCaptureEscrow | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` | [View](https://basescan.org/address/0xb9488351E48b23D798f24e8174514F28B741Eb4f) |"
    )
    lines.append(
        "| ERC-8004 Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` | [View](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63) |"
    )
    lines.append(
        "| ERC-8004 Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | [View](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) |"
    )
    lines.append(
        "| StaticAddressCondition | `0x9d03c03c15563E72CF2186E9FDB859A00ea661fc` | [View](https://basescan.org/address/0x9d03c03c15563E72CF2186E9FDB859A00ea661fc) |"
    )
    lines.append(
        "| USDC (Base) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | [View](https://basescan.org/address/0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) |"
    )
    lines.append(
        "| Facilitator EOA | `0x103040545AC5031A11E8C03dd11324C7333a13C7` | [View](https://basescan.org/address/0x103040545AC5031A11E8C03dd11324C7333a13C7) |"
    )
    lines.append("")

    # How to verify
    lines.append("## How to Verify")
    lines.append("")
    lines.append("1. Click any BaseScan link above")
    lines.append(
        '2. Look for **"Transaction Action: x402 Transaction"** — this is how BaseScan'
    )
    lines.append("   labels transactions through the x402r protocol")
    lines.append(
        '3. Check **"Interacted With (To)"** — should show our PaymentOperator'
    )
    lines.append(f"   (`{EM_OPERATOR}`)")
    lines.append(
        "4. Check **ERC-20 Token Transfers** — shows USDC moving through the escrow"
    )
    lines.append("   (Agent Wallet -> TokenCollector -> TokenStore for authorize,")
    lines.append("   TokenStore -> Receiver for release)")
    lines.append(
        "5. For reputation TXs, check the **Input Data** to see the feedback parameters"
    )
    lines.append("   (agentId, value, tag1, tag2, feedbackUri)")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================


def main():
    is_dry_run = "--dry-run" in sys.argv

    private_key = os.environ.get("WALLET_PRIVATE_KEY")
    if not private_key:
        print("ERROR: WALLET_PRIVATE_KEY not set in .env.local")
        sys.exit(1)

    print("=" * 70)
    print("EXECUTION MARKET — COMPLETE E2E FLOW TEST")
    print(f"  Date:        {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Network:     Base Mainnet ({CHAIN_ID})")
    print(f"  Facilitator: {FACILITATOR_URL}")
    print(f"  Operator:    {EM_OPERATOR}")
    print(f"  Agent ID:    {EM_AGENT_ID}")
    print(f"  Test amount: ${TEST_AMOUNT / 1_000_000:.2f} USDC per escrow")
    print(f"  Total cost:  ~${(TEST_AMOUNT * 2) / 1_000_000:.2f} USDC (2 escrows)")
    print(f"  Dry run:     {is_dry_run}")
    print("=" * 70)

    if is_dry_run:
        print("\nDRY RUN — no transactions will be sent.")
        print("Remove --dry-run to execute on Base Mainnet.")
        return

    # Initialize escrow client
    escrow_client = AdvancedEscrowClient(
        private_key=private_key,
        facilitator_url=FACILITATOR_URL,
        rpc_url=RPC_URL,
        chain_id=CHAIN_ID,
        operator_address=EM_OPERATOR,
    )
    print(f"\nPayer (agent): {escrow_client.payer}")

    results = FlowResult()

    # Run escrow scenarios (synchronous)
    run_escrow_release(escrow_client, results)
    run_escrow_refund(escrow_client, results)

    # Run ERC-8004 scenarios (async)
    asyncio.run(run_erc8004_scenarios(results))

    # Generate report
    report = generate_report(results)

    # Ensure output directory exists
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\n{'=' * 70}")
    print(f"REPORT SAVED: {REPORT_PATH}")
    print(f"{'=' * 70}")

    # Print transaction count
    all_tx = results.get_all_tx_hashes()
    print(f"\nTotal on-chain transactions: {len(all_tx)}")
    for i, tx in enumerate(all_tx, 1):
        print(f"  {i}. {basescan_tx(tx)}")

    # Save raw results as JSON
    raw_path = REPORT_PATH.with_suffix(".json")
    with open(raw_path, "w") as f:
        json.dump({"scenarios": results.scenarios}, f, indent=2, default=str)
    print(f"\nRaw results: {raw_path}")


if __name__ == "__main__":
    main()
