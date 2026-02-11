#!/usr/bin/env python3
"""
Fase 2 Escrow E2E Test — Full lifecycle on Base Mainnet.

Tests the complete escrow flow using the EM PaymentOperator:
  1. AUTHORIZE  — Lock $0.05 USDC in escrow
  2. QUERY      — Verify escrow state (capturable > 0)
  3. RELEASE    — Release to worker (gasless via facilitator)
  -- OR --
  3b. REFUND   — Refund to agent (gasless via facilitator)

Usage:
  python scripts/test-fase2-escrow.py                    # Full lifecycle (authorize + release)
  python scripts/test-fase2-escrow.py --refund           # Authorize + refund instead of release
  python scripts/test-fase2-escrow.py --dry-run          # Print config, don't transact

Requires:
  - .env.local with WALLET_PRIVATE_KEY (dev wallet with USDC on Base)
  - uvd-x402-sdk >= 0.13.0
  - Facilitator v1.32.1+ with EM PaymentOperator registered
"""

import os
import sys
import time
import json
from pathlib import Path

from dotenv import load_dotenv

# Load env
load_dotenv(Path(__file__).parent.parent / ".env.local")

from uvd_x402_sdk.advanced_escrow import (  # noqa: E402
    AdvancedEscrowClient,
    TaskTier,
)

# ============================================================
# Config
# ============================================================

EM_OPERATOR = "0xb9635f544665758019159c04c08a3d583dadd723"
FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"
RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
CHAIN_ID = 8453

# Test amount: $0.05 USDC = 50000 atomic units (6 decimals)
TEST_AMOUNT = 50_000

# Worker address — use the EM treasury for this test (we'll release to ourselves)
# In production this would be an actual worker address
TEST_RECEIVER = "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"  # EM Treasury


def main():
    is_dry_run = "--dry-run" in sys.argv
    do_refund = "--refund" in sys.argv

    private_key = os.environ.get("WALLET_PRIVATE_KEY")
    if not private_key:
        print("ERROR: WALLET_PRIVATE_KEY not set in .env.local")
        sys.exit(1)

    print("=" * 60)
    print("Fase 2 Escrow E2E Test — Base Mainnet")
    print("=" * 60)
    print(f"Facilitator:     {FACILITATOR_URL}")
    print(f"RPC:             {RPC_URL}")
    print(f"Chain:           Base ({CHAIN_ID})")
    print(f"Operator:        {EM_OPERATOR}")
    print(f"Test amount:     ${TEST_AMOUNT / 1_000_000:.2f} USDC")
    print(f"Receiver:        {TEST_RECEIVER}")
    print(f"Mode:            {'REFUND' if do_refund else 'RELEASE'}")
    print(f"Dry run:         {is_dry_run}")
    print()

    # Initialize client with EM's PaymentOperator
    client = AdvancedEscrowClient(
        private_key=private_key,
        facilitator_url=FACILITATOR_URL,
        rpc_url=RPC_URL,
        chain_id=CHAIN_ID,
        operator_address=EM_OPERATOR,
    )

    print(f"Payer (agent):   {client.payer}")
    print("Contracts:")
    for k, v in client.contracts.items():
        print(f"  {k:25s} {v}")
    print()

    if is_dry_run:
        print("DRY RUN — building PaymentInfo only, no transactions")
        pi = client.build_payment_info(
            receiver=TEST_RECEIVER,
            amount=TEST_AMOUNT,
            tier=TaskTier.MICRO,
        )
        print("\nPaymentInfo:")
        print(f"  operator:              {pi.operator}")
        print(f"  receiver:              {pi.receiver}")
        print(f"  token:                 {pi.token}")
        print(
            f"  maxAmount:             {pi.max_amount} ({pi.max_amount / 1_000_000:.6f} USDC)"
        )
        print(
            f"  preApprovalExpiry:     {pi.pre_approval_expiry} ({time.ctime(pi.pre_approval_expiry)})"
        )
        print(
            f"  authorizationExpiry:   {pi.authorization_expiry} ({time.ctime(pi.authorization_expiry)})"
        )
        print(
            f"  refundExpiry:          {pi.refund_expiry} ({time.ctime(pi.refund_expiry)})"
        )
        print(f"  minFeeBps:             {pi.min_fee_bps}")
        print(f"  maxFeeBps:             {pi.max_fee_bps}")
        print(f"  feeReceiver:           {pi.fee_receiver}")
        print(f"  salt:                  {pi.salt[:18]}...")
        print("\nDRY RUN complete. Remove --dry-run to execute on-chain.")
        return

    # ============================================================
    # Step 1: AUTHORIZE (lock funds in escrow)
    # ============================================================
    print("--- Step 1: AUTHORIZE (lock funds) ---")

    pi = client.build_payment_info(
        receiver=TEST_RECEIVER,
        amount=TEST_AMOUNT,
        tier=TaskTier.MICRO,
    )
    print("PaymentInfo built:")
    print(f"  salt: {pi.salt[:18]}...")
    print(f"  preApprovalExpiry: {time.ctime(pi.pre_approval_expiry)}")
    print(f"  authorizationExpiry: {time.ctime(pi.authorization_expiry)}")
    print()

    print("Sending authorize to facilitator...")
    t0 = time.time()
    auth_result = client.authorize(pi)
    t1 = time.time()

    if not auth_result.success:
        print(f"AUTHORIZE FAILED: {auth_result.error}")
        sys.exit(1)

    print(f"AUTHORIZE SUCCESS ({t1 - t0:.2f}s)")
    print(f"  TX: {auth_result.transaction_hash}")
    print(f"  https://basescan.org/tx/{auth_result.transaction_hash}")
    print()

    # ============================================================
    # Step 2: QUERY ESCROW STATE
    # ============================================================
    print("--- Step 2: QUERY ESCROW STATE ---")
    print("Waiting 3s for chain finality...")
    time.sleep(3)

    try:
        state = client.query_escrow_state(pi)
        print("Escrow state:")
        print(f"  {json.dumps(state, indent=2)}")
        capturable = int(state.get("capturableAmount", 0))
        refundable = int(state.get("refundableAmount", 0))
        collected = state.get("hasCollectedPayment", False)
        print(f"\n  Capturable: {capturable / 1_000_000:.6f} USDC")
        print(f"  Refundable: {refundable / 1_000_000:.6f} USDC")
        print(f"  Collected:  {collected}")

        if capturable == 0:
            print(
                "\nWARNING: capturableAmount is 0 — authorize may have failed silently"
            )
    except Exception as e:
        print(f"QUERY FAILED (non-fatal): {e}")
        print("Continuing with release/refund anyway...")
    print()

    # ============================================================
    # Step 3: RELEASE or REFUND
    # ============================================================
    if do_refund:
        print("--- Step 3: REFUND VIA FACILITATOR (gasless) ---")
        print("Sending refundInEscrow to facilitator...")
        t0 = time.time()
        result = client.refund_via_facilitator(pi)
        t1 = time.time()

        if not result.success:
            print(f"REFUND FAILED: {result.error}")
            sys.exit(1)

        print(f"REFUND SUCCESS ({t1 - t0:.2f}s)")
        print(f"  TX: {result.transaction_hash}")
        print(f"  https://basescan.org/tx/{result.transaction_hash}")
    else:
        print("--- Step 3: RELEASE VIA FACILITATOR (gasless) ---")
        print("Sending release to facilitator...")
        t0 = time.time()
        result = client.release_via_facilitator(pi)
        t1 = time.time()

        if not result.success:
            print(f"RELEASE FAILED: {result.error}")
            sys.exit(1)

        print(f"RELEASE SUCCESS ({t1 - t0:.2f}s)")
        print(f"  TX: {result.transaction_hash}")
        print(f"  https://basescan.org/tx/{result.transaction_hash}")

    # ============================================================
    # Step 4: Verify final state
    # ============================================================
    print()
    print("--- Step 4: VERIFY FINAL STATE ---")
    time.sleep(3)

    try:
        final_state = client.query_escrow_state(pi)
        print("Final escrow state:")
        print(f"  {json.dumps(final_state, indent=2)}")
        final_capturable = int(final_state.get("capturableAmount", 0))
        final_collected = final_state.get("hasCollectedPayment", False)

        if do_refund:
            if final_capturable == 0:
                print(
                    "\nREFUND VERIFIED: capturableAmount = 0 (funds returned to agent)"
                )
            else:
                print(f"\nWARNING: capturableAmount still {final_capturable}")
        else:
            if final_collected:
                print("\nRELEASE VERIFIED: hasCollectedPayment = true")
            else:
                print("\nWARNING: hasCollectedPayment still false")
    except Exception as e:
        print(f"FINAL QUERY FAILED (non-fatal): {e}")

    # ============================================================
    # Summary
    # ============================================================
    print()
    print("=" * 60)
    print("FASE 2 E2E TEST COMPLETE")
    print("=" * 60)
    print(f"Mode:           {'REFUND' if do_refund else 'RELEASE'}")
    print(f"Amount:         ${TEST_AMOUNT / 1_000_000:.2f} USDC")
    print(f"Authorize TX:   {auth_result.transaction_hash}")
    print(f"{'Refund' if do_refund else 'Release'} TX:    {result.transaction_hash}")
    print(f"Receiver:       {TEST_RECEIVER}")
    print(f"Operator:       {EM_OPERATOR}")
    print()
    print("BaseScan links:")
    print(f"  Authorize: https://basescan.org/tx/{auth_result.transaction_hash}")
    print(
        f"  {'Refund' if do_refund else 'Release'}:   https://basescan.org/tx/{result.transaction_hash}"
    )


if __name__ == "__main__":
    main()
