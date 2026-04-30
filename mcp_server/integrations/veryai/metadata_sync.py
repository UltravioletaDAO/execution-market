"""Async ERC-8004 metadata update for VeryAI.

Mirror of `api/routers/worldid.py:_update_erc8004_worldid_metadata`. Fire-
and-forget background task: pushes a `veryai_verified` badge onto the
agent's ERC-8004 metadata after a successful palm verification. Failures
log only — they NEVER roll back the DB write.
"""

from __future__ import annotations

import logging

import supabase_client as db

logger = logging.getLogger(__name__)


async def update_erc8004_veryai_metadata(
    executor_id: str,
    verification_level: str,
) -> None:
    """Fire-and-forget metadata update.

    Looks up the executor's ERC-8004 agent ID and pushes a metadata patch via
    the Facilitator. Always swallows exceptions — this is a best-effort badge
    sync, not a payment-critical path.
    """
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("erc8004_agent_id, wallet_address")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return

        agent_id = result.data[0].get("erc8004_agent_id")
        if not agent_id:
            logger.info(
                "Executor %s has no ERC-8004 agent ID, skipping VeryAI metadata sync",
                executor_id[:8],
            )
            return

        from integrations.erc8004.facilitator_client import ERC8004FacilitatorClient

        fac = ERC8004FacilitatorClient()
        await fac.update_metadata(
            agent_id=agent_id,
            metadata={
                "veryai_verified": True,
                "veryai_level": verification_level,
            },
            network="base",
        )
        logger.info(
            "ERC-8004 metadata updated with VeryAI for agent #%s (level=%s)",
            agent_id,
            verification_level,
        )
    except Exception as exc:
        logger.warning(
            "Failed to update ERC-8004 metadata with VeryAI for executor %s: %s",
            executor_id[:8],
            exc,
        )
