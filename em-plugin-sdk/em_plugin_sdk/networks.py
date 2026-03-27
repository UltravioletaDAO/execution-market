"""Static network and token registry for Execution Market.

Snapshot of the multichain token registry from the EM server. Pure data — no
server calls, no env vars. Useful for validating network+token combos before
making API calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TokenInfo:
    """A stablecoin deployed on a specific network."""
    symbol: str
    address: str
    name: str
    decimals: int = 6


@dataclass(frozen=True)
class NetworkInfo:
    """A blockchain network supported by Execution Market."""
    name: str
    chain_id: int | None
    network_type: str  # "evm" or "svm"
    tokens: tuple[TokenInfo, ...]
    has_escrow: bool = False
    has_operator: bool = False
    is_testnet: bool = False

    def get_token(self, symbol: str) -> TokenInfo | None:
        for t in self.tokens:
            if t.symbol == symbol:
                return t
        return None

    @property
    def token_symbols(self) -> list[str]:
        return [t.symbol for t in self.tokens]


# ---------------------------------------------------------------------------
# Registry data (synced from mcp_server/integrations/x402/sdk_client.py)
# ---------------------------------------------------------------------------

NETWORKS: dict[str, NetworkInfo] = {
    "base": NetworkInfo(
        name="base", chain_id=8453, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "USD Coin"),
            TokenInfo("EURC", "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42", "EURC"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "ethereum": NetworkInfo(
        name="ethereum", chain_id=1, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "USD Coin"),
            TokenInfo("EURC", "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c", "Euro Coin"),
            TokenInfo("PYUSD", "0x6c3ea9036406852006290770BEdFcAbA0e23A0e8", "PayPal USD"),
            TokenInfo("AUSD", "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a", "Agora Dollar"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "polygon": NetworkInfo(
        name="polygon", chain_id=137, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "USD Coin"),
            TokenInfo("AUSD", "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a", "Agora Dollar"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "arbitrum": NetworkInfo(
        name="arbitrum", chain_id=42161, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "USD Coin"),
            TokenInfo("USDT", "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "Tether USD"),
            TokenInfo("AUSD", "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a", "Agora Dollar"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "celo": NetworkInfo(
        name="celo", chain_id=42220, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0xcebA9300f2b948710d2653dD7B07f33A8B32118C", "USDC"),
            TokenInfo("USDT", "0x48065fbBE25f71C9282ddf5e1cD6D6A887483D5e", "Tether USD"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "monad": NetworkInfo(
        name="monad", chain_id=143, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0x754704Bc059F8C67012fEd69BC8A327a5aafb603", "USDC"),
            TokenInfo("AUSD", "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a", "Agora Dollar"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "avalanche": NetworkInfo(
        name="avalanche", chain_id=43114, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", "USD Coin"),
            TokenInfo("EURC", "0xC891EB4cbdEFf6e073e859e987815Ed1505c2ACD", "Euro Coin"),
            TokenInfo("AUSD", "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a", "Agora Dollar"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "optimism": NetworkInfo(
        name="optimism", chain_id=10, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "USD Coin"),
            TokenInfo("USDT", "0x01bff41798a0bcf287b996046ca68b395dbc1071", "Tether USD"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "skale": NetworkInfo(
        name="skale", chain_id=1187947933, network_type="evm",
        tokens=(
            TokenInfo("USDC", "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20", "Bridged USDC (SKALE Bridge)"),
        ),
        has_escrow=True, has_operator=True,
    ),
    "solana": NetworkInfo(
        name="solana", chain_id=None, network_type="svm",
        tokens=(
            TokenInfo("USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "USD Coin"),
            TokenInfo("AUSD", "AUSD1jCcCyPLybk1YnvPWsHQSrZ46dxwoMniN4N2UEB9", "Agora Dollar"),
        ),
    ),
}

# Enabled by default (matches EM_ENABLED_NETWORKS default)
DEFAULT_ENABLED = frozenset({
    "base", "ethereum", "polygon", "arbitrum",
    "celo", "monad", "avalanche", "optimism", "skale", "solana",
})

DEFAULT_NETWORK = "base"
DEFAULT_TOKEN = "USDC"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_network(name: str) -> NetworkInfo | None:
    """Get network info by name."""
    return NETWORKS.get(name)


def get_enabled_networks() -> list[NetworkInfo]:
    """Get all default-enabled networks."""
    return [n for name, n in NETWORKS.items() if name in DEFAULT_ENABLED]


def get_supported_tokens(network: str) -> list[str]:
    """Get token symbols supported on a network."""
    net = NETWORKS.get(network)
    return net.token_symbols if net else []


def is_valid_pair(network: str, token: str) -> bool:
    """Check if a network+token combination is valid."""
    net = NETWORKS.get(network)
    if not net:
        return False
    return net.get_token(token) is not None


def get_chain_id(network: str) -> int | None:
    """Get the chain ID for a network."""
    net = NETWORKS.get(network)
    return net.chain_id if net else None


def get_escrow_networks() -> list[str]:
    """Get networks with x402r escrow support."""
    return [name for name, n in NETWORKS.items() if n.has_escrow]
