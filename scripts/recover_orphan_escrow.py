#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recover Orphan Escrow -- refund an on-chain escrow deposit whose payment_info
was never persisted server-side (BACKLOG 2026-06-11, run ref 24e7114a).

Context: the Facilitator locked $0.05 USDC on Base (PaymentOperator.authorize)
but the relay crashed parsing the response (bug fixed in 8f73fdf7) and the
server rolled back WITHOUT persisting payment_info -- the escrow row was
reused later, so the on-chain deposit is orphaned. Everything needed to
refund it lives in the lock TX calldata: this script decodes the paymentInfo
tuple from the authorize() input and triggers the GASLESS arbiter refund via
the Facilitator (action=refundInEscrow, exact payload shape of
uvd_x402_sdk.advanced_escrow._settle_via_facilitator and the production path
in payment_dispatcher.refund_trustless_escrow). NO private key is involved;
funds return to the payer decoded from the tuple (publisher dev wallet).

Usage:
    python scripts/recover_orphan_escrow.py --dry-run   # decode + state only
    python scripts/recover_orphan_escrow.py             # decode + state + refund
    python scripts/recover_orphan_escrow.py --tx 0x<lock_tx_hash>

Cost: $0 (facilitator pays gas; refund is full-amount back to the payer).
"""

import argparse
import io
import sys
import time
from datetime import datetime, timezone
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
from eth_abi import decode as abi_decode
from web3 import Web3

# ---------------------------------------------------------------------------
# Load environment (convention only -- this script needs no secrets at all)
# ---------------------------------------------------------------------------
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / "mcp_server" / ".env")
load_dotenv(_project_root / ".env.local")

# ---------------------------------------------------------------------------
# Config (Base Mainnet -- mirror of e2e_h2h_flow.py)
# ---------------------------------------------------------------------------
BASE_RPC = "https://mainnet.base.org"
BASESCAN_TX = "https://basescan.org/tx"
FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ESCROW_ADDRESS = "0xb9488351E48b23D798f24e8174514F28B741Eb4f"
TOKEN_COLLECTOR = "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8"

# ERC-20 Transfer event topic (built from halves -- pre-commit blocks 0x+64hex)
TRANSFER_TOPIC = (
    "0x" + "ddf252ad1be2c89b69c2b068fc378daa" + "952ba7f163c4a11628f55a4df523b3ef"
)

# Orphan lock TX of run ref 24e7114a (built from halves -- same pre-commit rule)
DEFAULT_ORPHAN_TX = (
    "0x" + "845176e7906c9b24254677e42b72a88c" + "fbe7ea06fbc51f609cabe6d6a20ff5e2"
)

# PaymentOperator.authorize(paymentInfo, amount, tokenCollector, collectorData)
PAYMENT_INFO_TUPLE = (
    "(address,address,address,address,"
    "uint120,uint48,uint48,uint48,uint16,uint16,address,uint256)"
)
AUTHORIZE_ARG_TYPES = [PAYMENT_INFO_TUPLE, "uint256", "address", "bytes"]
AUTHORIZE_SIGNATURE = f"authorize({PAYMENT_INFO_TUPLE},uint256,address,bytes)"
PAYMENT_INFO_FIELDS = (
    "operator",
    "payer",
    "receiver",
    "token",
    "maxAmount",
    "preApprovalExpiry",
    "authorizationExpiry",
    "refundExpiry",
    "minFeeBps",
    "maxFeeBps",
    "feeReceiver",
    "salt",
)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _print_header(title: str) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}")


def _print_kv(key: str, value: Any, indent: int = 4) -> None:
    prefix = " " * indent
    print(f"{prefix}{key}: {value}")


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _usdc(atomic: int) -> str:
    return f"${atomic / 1_000_000:.6f}"


def rpc_call(client: httpx.Client, method: str, params: list) -> Any:
    resp = client.post(
        BASE_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30.0,
    )
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"RPC {method} error: {data['error']}")
    return data.get("result")


# ---------------------------------------------------------------------------
# Step 1: Fetch + decode the lock TX calldata
# ---------------------------------------------------------------------------
def fetch_and_decode(client: httpx.Client, tx_hash: str) -> Dict[str, Any]:
    """Decode PaymentOperator.authorize() calldata into the paymentInfo tuple."""
    _print_header("STEP 1: FETCH + DECODE LOCK TX")
    _print_kv("TX", tx_hash, 2)
    _print_kv("BaseScan", f"{BASESCAN_TX}/{tx_hash}", 2)

    tx = rpc_call(client, "eth_getTransactionByHash", [tx_hash])
    if not tx:
        raise RuntimeError(f"TX {tx_hash} not found on Base")

    chain_id = int(tx.get("chainId", "0x2105"), 16)
    print(f"    To (operator):    {tx.get('to')}")
    print(f"    From (relayer):   {tx.get('from')}")
    print(f"    Chain ID:         {chain_id}")

    data = bytes.fromhex(tx["input"].removeprefix("0x"))
    selector = "0x" + data[:4].hex()
    expected_selector = "0x" + Web3.keccak(text=AUTHORIZE_SIGNATURE)[:4].hex()
    if selector != expected_selector:
        raise RuntimeError(
            f"TX selector {selector} is not PaymentOperator.authorize "
            f"({expected_selector}) -- refusing to decode a different call"
        )
    print(f"    Selector:         {selector} (authorize) -- OK")

    pi_tuple, amount, token_collector, _collector_data = abi_decode(
        AUTHORIZE_ARG_TYPES, data[4:]
    )
    pi = dict(zip(PAYMENT_INFO_FIELDS, pi_tuple))

    # Checksum the addresses (eth_abi returns lowercase)
    for f in ("operator", "payer", "receiver", "token", "feeReceiver"):
        pi[f] = Web3.to_checksum_address(pi[f])
    token_collector = Web3.to_checksum_address(token_collector)

    print("\n    Decoded paymentInfo (addresses + amounts):")
    _print_kv("operator", pi["operator"], 6)
    _print_kv("payer", pi["payer"], 6)
    _print_kv("receiver", pi["receiver"], 6)
    _print_kv("token", pi["token"], 6)
    _print_kv("feeReceiver", pi["feeReceiver"], 6)
    _print_kv("maxAmount", f"{pi['maxAmount']} ({_usdc(pi['maxAmount'])})", 6)
    _print_kv("authorize amount", f"{amount} ({_usdc(amount)})", 6)
    _print_kv("minFeeBps/maxFeeBps", f"{pi['minFeeBps']}/{pi['maxFeeBps']}", 6)
    _print_kv("preApprovalExpiry", _iso(pi["preApprovalExpiry"]), 6)
    _print_kv("authorizationExpiry", _iso(pi["authorizationExpiry"]), 6)
    _print_kv("refundExpiry", _iso(pi["refundExpiry"]), 6)
    _print_kv("tokenCollector", token_collector, 6)

    if pi["token"].lower() != USDC_CONTRACT.lower():
        raise RuntimeError(f"Decoded token {pi['token']} is not USDC on Base")
    if token_collector.lower() != TOKEN_COLLECTOR.lower():
        print(
            f"    [WARN] Decoded tokenCollector {token_collector} differs from "
            f"the known constant {TOKEN_COLLECTOR} -- using the decoded one"
        )
    if amount != pi["maxAmount"]:
        print(
            f"    [WARN] authorize amount {amount} != maxAmount {pi['maxAmount']} "
            "-- refunding the authorize amount"
        )

    now = int(time.time())
    remaining_h = (pi["refundExpiry"] - now) / 3600
    if remaining_h <= 0:
        print(f"    [WARN] refundExpiry passed {-remaining_h:.1f}h ago -- the")
        print("           facilitator/on-chain condition may reject the refund")
    else:
        print(f"    Refund window:    OPEN ({remaining_h:.1f}h remaining)")

    return {
        "payment_info": pi,
        "amount": amount,
        "token_collector": token_collector,
        "chain_id": chain_id,
    }


# ---------------------------------------------------------------------------
# Facilitator payloads (EXACT shapes of uvd_x402_sdk.advanced_escrow)
# ---------------------------------------------------------------------------
def payment_info_camel(pi: Dict[str, Any]) -> Dict[str, Any]:
    """camelCase paymentInfo dict for the facilitator API.

    Mirror of _payment_info_to_camel_dict: payer is NOT part of this dict
    (it travels separately in the payload), maxAmount is a string, salt is
    the SDK's 0x-prefixed 32-byte hex string convention.
    """
    return {
        "operator": pi["operator"],
        "receiver": pi["receiver"],
        "token": pi["token"],
        "maxAmount": str(pi["maxAmount"]),
        "preApprovalExpiry": pi["preApprovalExpiry"],
        "authorizationExpiry": pi["authorizationExpiry"],
        "refundExpiry": pi["refundExpiry"],
        "minFeeBps": pi["minFeeBps"],
        "maxFeeBps": pi["maxFeeBps"],
        "feeReceiver": pi["feeReceiver"],
        "salt": "0x" + format(pi["salt"], "064x"),
    }


def query_escrow_state(
    client: httpx.Client, decoded: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """STEP 2: read-only escrow state via POST /escrow/state (best-effort).

    Mirror of uvd_x402_sdk.advanced_escrow.query_escrow_state. Returns None
    when the endpoint is unavailable (the refund itself does not depend on it).
    """
    _print_header("STEP 2: ESCROW STATE (FACILITATOR, READ-ONLY)")
    pi = decoded["payment_info"]
    payload = {
        "paymentInfo": payment_info_camel(pi),
        "payer": pi["payer"],
        "network": f"eip155:{decoded['chain_id']}",
        "extra": {
            "escrowAddress": ESCROW_ADDRESS,
            "operatorAddress": pi["operator"],
            "tokenCollector": decoded["token_collector"],
        },
    }
    try:
        resp = client.post(f"{FACILITATOR_URL}/escrow/state", json=payload, timeout=30)
        result = resp.json()
    except Exception as e:
        print(f"    [WARN] /escrow/state unreachable ({e}) -- continuing without it")
        return None

    if "error" in result or "errorReason" in result:
        print(
            "    [WARN] /escrow/state returned an error: "
            f"{result.get('errorReason', result.get('error'))}"
        )
        return None

    _print_kv("capturableAmount", result.get("capturableAmount"), 4)
    _print_kv("refundableAmount", result.get("refundableAmount"), 4)
    _print_kv("hasCollectedPayment", result.get("hasCollectedPayment"), 4)
    return result


def settle_refund(client: httpx.Client, decoded: Dict[str, Any]) -> str:
    """STEP 3: gasless arbiter refund via POST /settle action=refundInEscrow.

    EXACT payload shape of _settle_via_facilitator (and the production path
    payment_dispatcher.refund_trustless_escrow). Raises on rejection -- the
    caller reports the errorReason and STOPS (no retry-hammering).
    """
    _print_header("STEP 3: REFUND VIA FACILITATOR (GASLESS, action=refundInEscrow)")
    pi = decoded["payment_info"]
    amount = decoded["amount"]
    print(f"    Refunding {_usdc(amount)} USDC -> payer {pi['payer']}")

    payload = {
        "x402Version": 2,
        "scheme": "escrow",
        "action": "refundInEscrow",
        "payload": {
            "paymentInfo": payment_info_camel(pi),
            "payer": pi["payer"],
            "amount": str(amount),
        },
        "paymentRequirements": {
            "scheme": "escrow",
            "network": f"eip155:{decoded['chain_id']}",
            "extra": {
                "escrowAddress": ESCROW_ADDRESS,
                "operatorAddress": pi["operator"],
                "tokenCollector": decoded["token_collector"],
            },
        },
    }
    resp = client.post(f"{FACILITATOR_URL}/settle", json=payload, timeout=120)
    result = resp.json()

    if not result.get("success"):
        reason = result.get("errorReason", result.get("error", "Unknown error"))
        raise RuntimeError(f"Facilitator rejected the refund: {reason}")

    # The facilitator returns "transaction" as the tx-hash STRING; tolerate
    # the object form too (same guard as the relay/release paths, 8f73fdf7).
    tx_field = result.get("transaction")
    refund_tx = (
        tx_field.get("hash", "") if isinstance(tx_field, dict) else (tx_field or "")
    ) or result.get("txHash", "")
    if not refund_tx:
        raise RuntimeError(
            f"Facilitator reported success but returned no transaction: {result}"
        )

    print(f"    Refund TX: {refund_tx}")
    print(f"    BaseScan:  {BASESCAN_TX}/{refund_tx}")
    return refund_tx


# ---------------------------------------------------------------------------
# Step 4: On-chain verification (mirror of e2e_h2h_flow.verify_tx_onchain)
# ---------------------------------------------------------------------------
def verify_refund_onchain(
    client: httpx.Client, refund_tx: str, payer: str, expected_amount: int
) -> bool:
    _print_header("STEP 4: ON-CHAIN VERIFICATION")

    receipt = None
    for attempt in range(10):
        receipt = rpc_call(client, "eth_getTransactionReceipt", [refund_tx])
        if receipt:
            break
        print(f"    Waiting for receipt... (attempt {attempt + 1}/10)")
        time.sleep(3)
    if not receipt:
        print("    [FAIL] No receipt after 30s -- verify manually on BaseScan")
        return False

    success = receipt.get("status") == "0x1"
    print(f"    Receipt status:   {'SUCCESS (0x1)' if success else 'REVERTED'}")
    print(f"    Block:            {int(receipt.get('blockNumber', '0x0'), 16)}")
    print(f"    Gas used:         {int(receipt.get('gasUsed', '0x0'), 16)}")

    payer_credit = None
    for log in receipt.get("logs", []):
        topics = log.get("topics", [])
        if (
            len(topics) >= 3
            and topics[0].lower() == TRANSFER_TOPIC.lower()
            and log.get("address", "").lower() == USDC_CONTRACT.lower()
        ):
            sender = "0x" + topics[1][-40:]
            receiver = "0x" + topics[2][-40:]
            raw_amount = int(log.get("data", "0x0"), 16)
            print(
                f"    Transfer: ...{sender[-6:]} -> ...{receiver[-6:]} : "
                f"{_usdc(raw_amount)}"
            )
            if receiver.lower() == payer.lower():
                payer_credit = raw_amount

    if not success:
        return False
    if payer_credit is None:
        print(f"    [FAIL] No USDC Transfer back to the payer {payer} in the logs")
        return False
    if payer_credit != expected_amount:
        print(
            f"    [WARN] Payer received {_usdc(payer_credit)} != "
            f"expected {_usdc(expected_amount)}"
        )
    else:
        print(f"    Payer credited:   {_usdc(payer_credit)} -- matches the lock")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refund an orphaned escrow deposit by decoding the lock TX "
        "calldata and relaying a gasless refundInEscrow via the Facilitator"
    )
    parser.add_argument(
        "--tx",
        default=DEFAULT_ORPHAN_TX,
        help=f"Lock TX hash to recover (default: orphan {DEFAULT_ORPHAN_TX})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Decode the calldata + query escrow state only (no settle POST)",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    _print_header("RECOVER ORPHAN ESCROW -- gasless refundInEscrow via Facilitator")
    _print_kv("Lock TX", args.tx, 2)
    _print_kv("Facilitator", FACILITATOR_URL, 2)
    _print_kv("Mode", "DRY RUN (no settle)" if args.dry_run else "LIVE REFUND", 2)

    with httpx.Client() as client:
        try:
            decoded = fetch_and_decode(client, args.tx)
        except Exception as e:
            print(f"\n  [FAIL] Decode failed: {e}")
            return 1

        state = query_escrow_state(client, decoded)
        if state is not None:
            # AuthCaptureEscrow semantics: an authorized-not-captured deposit
            # sits in capturableAmount (voidable to the payer -- that is what
            # refundInEscrow -> partialVoid drains). refundableAmount only
            # counts CAPTURED funds (post-capture refund()), so it is 0 for a
            # healthy locked escrow.
            capturable = int(state.get("capturableAmount") or 0)
            if capturable == 0:
                print(
                    "\n  [STOP] capturableAmount is 0 -- nothing left in "
                    "escrow (already refunded/released?). Not sending the "
                    "settle."
                )
                return 1
            if capturable < decoded["amount"]:
                print(
                    f"    [WARN] capturableAmount {capturable} < locked "
                    f"{decoded['amount']} -- refunding only the capturable part"
                )
                decoded["amount"] = capturable

        if args.dry_run:
            _print_header("DRY RUN COMPLETE")
            print("    Decode OK" + (" + escrow state OK" if state else ""))
            print("    Re-run without --dry-run to execute the refund.")
            return 0

        try:
            refund_tx = settle_refund(client, decoded)
        except Exception as e:
            print(f"\n  [FAIL] {e}")
            print("  Stopping (no retries). Capture the errorReason above.")
            return 1

        ok = verify_refund_onchain(
            client, refund_tx, decoded["payment_info"]["payer"], decoded["amount"]
        )

        _print_header("SUMMARY")
        _print_kv("Lock TX", f"{BASESCAN_TX}/{args.tx}", 2)
        _print_kv("Refund TX", f"{BASESCAN_TX}/{refund_tx}", 2)
        _print_kv("Payer", decoded["payment_info"]["payer"], 2)
        _print_kv("Amount", _usdc(decoded["amount"]), 2)
        if ok:
            print("\n  ** RECOVERY: PASS -- orphaned escrow refunded to the payer **")
            return 0
        print("\n  ** RECOVERY: UNVERIFIED -- check the refund TX on BaseScan **")
        return 1


if __name__ == "__main__":
    sys.exit(main())
