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

logger = logging.getLogger(__name__)

FEE_SWEEP_INTERVAL = int(os.environ.get("FEE_SWEEP_INTERVAL", "21600"))  # 6 hours

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
                    tx_hash = await dispatcher._distribute_operator_fees(
                        network=network, token="USDC"
                    )
                    if tx_hash:
                        swept += 1
                        logger.info(
                            "[fee-sweep] %s: fees distributed, tx=%s",
                            network,
                            tx_hash,
                        )
                    else:
                        skipped += 1
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

        await asyncio.sleep(FEE_SWEEP_INTERVAL)
