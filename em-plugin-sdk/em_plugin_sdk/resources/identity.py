"""Identity registration resource — ERC-8004 via Facilitator.

Provides gasless on-chain identity registration through the Ultravioleta
Facilitator.  The wallet address is resolved automatically from the
:class:`~uvd_x402_sdk.wallet.WalletAdapter` attached to the client, or
can be passed explicitly.

Usage::

    from uvd_x402_sdk.wallet import EnvKeyAdapter

    async with EMClient(wallet=EnvKeyAdapter()) as client:
        result = await client.identity.register("my-agent")
        print(result)  # {"agent_id": 2107, "tx_hash": "0x..."}
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import EMClient

FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"


class IdentityResource:
    """ERC-8004 on-chain identity registration (gasless via Facilitator).

    Usage::

        result = await client.identity.register("my-agent")
        result = await client.identity.register("my-agent", network="polygon")
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    # -- registration ----------------------------------------------------------

    async def register(
        self,
        agent_name: str,
        network: str = "base",
        wallet_address: str | None = None,
    ) -> dict[str, Any]:
        """Register ERC-8004 on-chain identity (gasless via Facilitator).

        Args:
            agent_name: Human-readable name for the agent.
            network: Target blockchain network (default ``"base"``).
            wallet_address: Explicit wallet address.  When *None*, the address
                is derived from the :pyattr:`EMClient._wallet` adapter.

        Returns:
            Facilitator response dict (typically contains ``agent_id`` and
            ``tx_hash``).

        Raises:
            ValueError: If no wallet address is available.
        """
        address = wallet_address
        if not address and self._client._wallet:
            address = self._client._wallet.get_address()
        if not address:
            raise ValueError(
                "No wallet address. Provide wallet_address or attach a "
                "WalletAdapter to EMClient."
            )

        resp = await self._client._client.post(
            f"{FACILITATOR_URL}/register",
            json={
                "x402Version": 1,
                "network": network,
                "recipient": address,
                "agentUri": f"https://execution.market/agents/{address.lower()}",
                "name": agent_name,
            },
        )
        resp.raise_for_status()
        return resp.json()
