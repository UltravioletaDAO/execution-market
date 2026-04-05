"""
Fee Sweep Background Job

Periodically calls distributeFees(USDC) on PaymentOperator contracts across
all EVM chains to flush accumulated platform fees to treasury.

distributeFees() is permissionless — any wallet with gas can call it.
The StaticFeeCalculator(1300 BPS = 13%) accumulates fees on each release;
this job sweeps them to the EM treasury.

Runs every FEE_SWEEP_INTERVAL seconds (default: 21600 = 6 hours).
"""

import asyncio
import logging
import os
import time as _time

logger = logging.getLogger(__name__)

FEE_SWEEP_INTERVAL = int(os.environ.get("FEE_SWEEP_INTERVAL", "21600"))  # 6 hours

# Health pulse
_last_cycle_time: float = 0.0


def get_fee_sweep_health() -> dict:
    """Return health status for the fee sweep job."""
    if _last_cycle_time == 0.0:
        return {"status": "starting"}
    age = _time.time() - _last_cycle_time
    if age > FEE_SWEEP_INTERVAL * 2:
        return {"status": "stale", "last_cycle_age_s": round(age)}
    return {"status": "healthy", "last_cycle_age_s": round(age)}


# EVM networks with deployed PaymentOperator contracts (Fase 5).
# Solana excluded — uses Fase 1 only (no operator).
SWEEP_NETWORKS = [
    "base",
    "ethereum",
    "polygon",
    "arbitrum",
    "avalanche",
    "monad",
    "celo",
    "optimism",
    "skale",
]


async def run_fee_sweep_loop() -> None:
    """
    Background loop that calls distributeFees(USDC) on all EVM chains.

    For each network with a deployed PaymentOperator:
    1. Calls distributeFees(USDC_address) on the operator contract
    2. Gas estimation failure = no fees to distribute (normal, not an error)
    3. Logs results and continues to the next chain

    Each chain has independent nonce/RPC so no collision risk.
    """
    logger.info(
        "[fee-sweep] Fee sweep job started (interval=%ds, networks=%d)",
        FEE_SWEEP_INTERVAL,
        len(SWEEP_NETWORKS),
    )

    # Wait for other services to initialize
    await asyncio.sleep(30)

    if not os.environ.get("WALLET_PRIVATE_KEY"):
        logger.warning("[fee-sweep] No WALLET_PRIVATE_KEY set, fee sweep disabled")
        return

    while True:
        try:
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            dispatcher = PaymentDispatcher()
            swept = 0
            skipped = 0

            for network in SWEEP_NETWORKS:
                try:
                    tx_hash = await asyncio.wait_for(
                        dispatcher._distribute_operator_fees(
                            network=network, token="USDC"
                        ),
                        timeout=120,
                    )
                    if tx_hash:
                        swept += 1
                        logger.info(
                            "[fee-sweep] %s: fees distributed, tx=%s",
                            network,
                            tx_hash,
                        )
                        # Mark fee distribution for tasks on this network
                        try:
                            from audit.checkpoint_updater import (
                                mark_fees_distributed,
                            )

                            # Fee sweep is network-wide, not per-task.
                            # Mark all completed tasks on this network that
                            # have payment_released=True but fees_distributed=False
                            import supabase_client as sdb

                            sdb_client = sdb.get_client()
                            pending = (
                                sdb_client.table("task_lifecycle_checkpoints")
                                .select("task_id")
                                .eq("payment_released", True)
                                .eq("fees_distributed", False)
                                .eq("network", network)
                                .limit(100)
                                .execute()
                            )
                            for row in pending.data or []:
                                await mark_fees_distributed(
                                    row["task_id"], tx_hash=tx_hash
                                )
                        except Exception as ckpt_err:
                            logger.debug("[fee-sweep] checkpoint update: %s", ckpt_err)
                    else:
                        skipped += 1
                except asyncio.TimeoutError:
                    logger.warning("[fee-sweep] %s: timed out after 120s", network)
                except Exception as e:
                    logger.warning("[fee-sweep] %s: error: %s", network, e)

                # Delay between chains to avoid wallet nonce issues
                await asyncio.sleep(5)

            if swept > 0:
                logger.info(
                    "[fee-sweep] Cycle complete: %d distributed, %d skipped (no fees)",
                    swept,
                    skipped,
                )
            else:
                logger.debug("[fee-sweep] Cycle complete: no fees on any chain")

        except Exception as exc:
            logger.error("[fee-sweep] Error in sweep loop: %s", exc)

        global _last_cycle_time
        _last_cycle_time = _time.time()
        await asyncio.sleep(FEE_SWEEP_INTERVAL)
