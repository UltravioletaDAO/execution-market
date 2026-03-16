"""
Gas Dust Module — Fund workers with tiny ETH for on-chain reputation TX gas.

Workers sign giveFeedback() directly from their wallet (msg.sender = worker).
They need a small amount of ETH for gas (~0.0001 ETH on Base, < $0.01).

Anti-farming protections:
- Only after first APPROVED task (not just registration)
- One funding per wallet (executors.gas_dust_funded_at)
- Monthly budget cap (EM_GAS_DUST_MONTHLY_BUDGET_ETH, default 0.05 ETH)
- Rate limit: max 10 fundings per hour
- Feature flag: gas_dust_auto_fund in platform_config
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import supabase_client as db

logger = logging.getLogger(__name__)

# Default dust amount: 0.0001 ETH (~$0.25 at $2500/ETH, enough for ~5 giveFeedback TXs)
GAS_DUST_AMOUNT_ETH = float(os.environ.get("EM_GAS_DUST_AMOUNT_ETH", "0.0001"))

# Monthly budget cap in ETH (default 0.05 ETH = ~500 fundings)
MONTHLY_BUDGET_ETH = float(os.environ.get("EM_GAS_DUST_MONTHLY_BUDGET_ETH", "0.05"))

# Rate limit: max fundings per hour
MAX_FUNDINGS_PER_HOUR = int(os.environ.get("EM_GAS_DUST_RATE_LIMIT", "10"))


async def fund_worker_gas_dust(
    wallet_address: str,
    executor_id: str,
) -> Optional[str]:
    """
    Send gas dust (tiny ETH) to a worker's wallet for on-chain reputation TXs.

    Returns tx_hash on success, None on skip/failure.

    Pre-conditions checked:
    - Worker not already funded (gas_dust_funded_at is NULL)
    - Monthly budget not exceeded
    - Rate limit not exceeded
    """
    wallet_lower = wallet_address.lower()

    # Check if already funded
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("gas_dust_funded_at")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get("gas_dust_funded_at"):
            logger.debug(
                "Worker %s already funded, skipping gas dust", wallet_lower[:10]
            )
            return None
    except Exception as exc:
        logger.warning("Gas dust: could not check funding status: %s", exc)
        return None

    # Check rate limit
    if not await check_rate_limit():
        logger.warning("Gas dust: rate limit exceeded, skipping %s", wallet_lower[:10])
        return None

    # Check monthly budget
    if not await check_gas_dust_budget():
        logger.warning(
            "Gas dust: monthly budget exceeded, skipping %s", wallet_lower[:10]
        )
        return None

    # Record pending event
    event_id = None
    try:
        insert_result = (
            client.table("gas_dust_events")
            .insert(
                {
                    "executor_id": executor_id,
                    "wallet_address": wallet_lower,
                    "amount_eth": GAS_DUST_AMOUNT_ETH,
                    "status": "pending",
                    "network": "base",
                }
            )
            .execute()
        )
        if insert_result.data:
            event_id = insert_result.data[0].get("id")
    except Exception as exc:
        logger.warning("Gas dust: could not record event: %s", exc)

    # Send ETH
    try:
        tx_hash = await _send_eth_dust(wallet_lower, GAS_DUST_AMOUNT_ETH)
    except Exception as exc:
        logger.error("Gas dust: TX failed for %s: %s", wallet_lower[:10], exc)
        # Update event as failed
        if event_id:
            try:
                client.table("gas_dust_events").update(
                    {"status": "failed", "error": str(exc)[:500]}
                ).eq("id", event_id).execute()
            except Exception:
                pass
        return None

    # Mark success
    try:
        now = datetime.now(timezone.utc).isoformat()
        client.table("executors").update({"gas_dust_funded_at": now}).eq(
            "id", executor_id
        ).execute()

        if event_id:
            client.table("gas_dust_events").update(
                {"status": "success", "tx_hash": tx_hash}
            ).eq("id", event_id).execute()
    except Exception as exc:
        logger.warning("Gas dust: could not update records: %s", exc)

    logger.info(
        "Gas dust sent: %s ETH to %s, tx=%s",
        GAS_DUST_AMOUNT_ETH,
        wallet_lower[:10],
        tx_hash[:16] if tx_hash else "unknown",
    )
    return tx_hash


async def check_gas_dust_budget() -> bool:
    """Check if monthly gas dust budget has capacity remaining."""
    try:
        client = db.get_client()
        # Sum successful fundings this month
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = (
            client.table("gas_dust_events")
            .select("amount_eth")
            .eq("status", "success")
            .gte("created_at", month_start.isoformat())
            .execute()
        )

        total = sum(float(r.get("amount_eth", 0)) for r in (result.data or []))
        remaining = MONTHLY_BUDGET_ETH - total

        if remaining < GAS_DUST_AMOUNT_ETH:
            logger.warning(
                "Gas dust budget exhausted: spent %.6f / %.6f ETH this month",
                total,
                MONTHLY_BUDGET_ETH,
            )
            return False

        return True
    except Exception as exc:
        logger.warning("Gas dust: budget check failed: %s", exc)
        return False


async def check_rate_limit() -> bool:
    """Check if we're under the hourly rate limit for gas dust fundings."""
    try:
        client = db.get_client()
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        result = (
            client.table("gas_dust_events")
            .select("id", count="exact")
            .gte("created_at", one_hour_ago)
            .execute()
        )

        count = result.count if result.count is not None else len(result.data or [])
        return count < MAX_FUNDINGS_PER_HOUR
    except Exception as exc:
        logger.warning("Gas dust: rate limit check failed: %s", exc)
        return False


async def _send_eth_dust(to_address: str, amount_eth: float) -> str:
    """
    Send ETH dust from platform wallet to worker.

    Uses the platform wallet (WALLET_PRIVATE_KEY) to send a tiny amount
    of native ETH on Base for gas.
    """
    from web3 import Web3

    try:
        from web3.middleware import ExtraDataToPOAMiddleware as _poa_middleware
    except ImportError:
        from web3.middleware import geth_poa_middleware as _poa_middleware

    pk = os.environ.get("WALLET_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("WALLET_PRIVATE_KEY not set, cannot send gas dust")

    rpc_url = os.environ.get(
        "X402_RPC_URL", os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
    )

    def _do_send():
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        w3.middleware_onion.inject(_poa_middleware, layer=0)

        account = w3.eth.account.from_key(pk)
        amount_wei = w3.to_wei(amount_eth, "ether")

        tx = {
            "from": account.address,
            "to": Web3.to_checksum_address(to_address),
            "value": amount_wei,
            "chainId": 8453,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 21000,  # Standard ETH transfer
        }

        signed = w3.eth.account.sign_transaction(tx, pk)
        # web3.py v7+ uses `raw_transaction`, v6 uses `rawTransaction`
        raw_tx = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] != 1:
            raise RuntimeError(f"Gas dust TX reverted: {tx_hash.hex()}")

        return tx_hash.hex()

    return await asyncio.to_thread(_do_send)
