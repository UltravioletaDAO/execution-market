"""
NetworkRegistry — Multi-Chain Network Configuration for the Swarm (Module #56)
================================================================================

Provides a clean, centralized interface for network configuration used by
swarm components (routing, identity, payments, reputation).

Motivation:
    The SKALE integration revealed that network-specific knowledge was scattered
    across the codebase: facilitator_client.py had network mappings, identity.py
    had chain lookups, reputation.py had per-chain logic. When SKALE was added,
    each file needed independent updates.

    NetworkRegistry centralizes network knowledge so swarm components can ask
    "what chains support payments?" or "what's the gas cost profile for Base?"
    without importing payment or identity modules.

Architecture:
    ┌──────────────────────────────────────┐
    │          NetworkRegistry              │
    │                                       │
    │  ┌─────────────┐ ┌───────────────┐   │
    │  │ NetworkInfo  │ │ Capabilities  │   │
    │  │ (per chain)  │ │ (per feature) │   │
    │  └──────┬──────┘ └───────┬───────┘   │
    │         │                 │            │
    │  ┌──────▼─────────────────▼──────┐    │
    │  │   Feature Query Engine         │    │
    │  │  "Which chains support X?"     │    │
    │  └────────────────────────────────┘    │
    └──────────────────────────────────────┘

Usage:
    registry = NetworkRegistry.with_defaults()
    
    # Query network info
    base = registry.get("base")
    print(base.gas_profile)  # "low"
    
    # Feature queries
    chains = registry.chains_with_feature("payments")
    usdc = registry.get_token_address("base", "USDC")
    
    # Validation
    registry.validate_chain("skale")  # True
    registry.validate_chain("bitcoin")  # False
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Set

logger = logging.getLogger("em.swarm.network_registry")


# ─── Types ────────────────────────────────────────────────────


class ChainType(str, Enum):
    """Blockchain virtual machine type."""
    EVM = "evm"
    SVM = "svm"  # Solana
    MOVE = "move"  # Aptos/Sui


class GasProfile(str, Enum):
    """Relative gas cost category."""
    FREE = "free"  # SKALE (zero gas)
    ULTRA_LOW = "ultra_low"  # L2s under $0.001
    LOW = "low"  # Base, Arbitrum, Optimism
    MEDIUM = "medium"  # Polygon, Celo
    HIGH = "high"  # Ethereum mainnet


class NetworkStatus(str, Enum):
    """Network operational status."""
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


@dataclass
class TokenInfo:
    """Token configuration on a specific chain."""
    symbol: str
    address: str
    decimals: int = 6  # USDC default
    is_native: bool = False


@dataclass
class NetworkInfo:
    """Complete configuration for a blockchain network."""
    name: str
    chain_id: Optional[int]
    chain_type: ChainType
    gas_profile: GasProfile
    status: NetworkStatus = NetworkStatus.ACTIVE
    
    # Feature flags
    supports_payments: bool = True
    supports_identity: bool = True  # ERC-8004
    supports_reputation: bool = True
    supports_escrow: bool = True
    
    # Explorer and RPC
    explorer_url: Optional[str] = None
    
    # Tokens
    tokens: Dict[str, TokenInfo] = field(default_factory=dict)
    
    # Performance characteristics
    avg_block_time_seconds: float = 2.0
    avg_confirmation_time_seconds: float = 5.0
    
    # Network-specific notes
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "chain_id": self.chain_id,
            "chain_type": self.chain_type.value,
            "gas_profile": self.gas_profile.value,
            "status": self.status.value,
            "features": {
                "payments": self.supports_payments,
                "identity": self.supports_identity,
                "reputation": self.supports_reputation,
                "escrow": self.supports_escrow,
            },
            "tokens": {
                sym: {"address": t.address, "decimals": t.decimals}
                for sym, t in self.tokens.items()
            },
            "explorer_url": self.explorer_url,
        }


# ─── NetworkRegistry ─────────────────────────────────────────


class NetworkRegistry:
    """
    Centralized network configuration for the swarm.
    
    All swarm components query this instead of maintaining their own
    chain-specific logic.
    """

    def __init__(self):
        self._networks: Dict[str, NetworkInfo] = {}
        self._aliases: Dict[str, str] = {}  # alias → canonical name
        self._created_at = time.time()

    # ─── Registration ─────────────────────────────────────────

    def register(self, network: NetworkInfo) -> "NetworkRegistry":
        """Register a network configuration."""
        name = network.name.lower().strip()
        self._networks[name] = network
        return self

    def register_alias(self, alias: str, canonical: str) -> "NetworkRegistry":
        """Register a network name alias."""
        self._aliases[alias.lower().strip()] = canonical.lower().strip()
        return self

    # ─── Lookup ───────────────────────────────────────────────

    def get(self, name: str) -> Optional[NetworkInfo]:
        """Get network info by name or alias."""
        name = name.lower().strip()
        canonical = self._aliases.get(name, name)
        return self._networks.get(canonical)

    def resolve_name(self, name: str) -> str:
        """Resolve an alias to canonical network name."""
        name = name.lower().strip()
        return self._aliases.get(name, name)

    def validate_chain(self, name: str) -> bool:
        """Check if a chain name is known and active."""
        info = self.get(name)
        return info is not None and info.status != NetworkStatus.DISABLED

    def all_networks(self) -> List[NetworkInfo]:
        """Get all registered networks."""
        return list(self._networks.values())

    def active_networks(self) -> List[NetworkInfo]:
        """Get all active (non-disabled) networks."""
        return [
            n for n in self._networks.values()
            if n.status != NetworkStatus.DISABLED
        ]

    # ─── Feature Queries ──────────────────────────────────────

    def chains_with_feature(self, feature: str) -> List[str]:
        """Get chain names that support a specific feature."""
        feature_map = {
            "payments": lambda n: n.supports_payments,
            "identity": lambda n: n.supports_identity,
            "reputation": lambda n: n.supports_reputation,
            "escrow": lambda n: n.supports_escrow,
        }
        check = feature_map.get(feature.lower())
        if not check:
            return []
        return [
            name for name, info in self._networks.items()
            if check(info) and info.status == NetworkStatus.ACTIVE
        ]

    def chains_by_gas(self, max_profile: GasProfile = GasProfile.LOW) -> List[str]:
        """Get chains at or below a gas cost threshold."""
        profile_order = [
            GasProfile.FREE, GasProfile.ULTRA_LOW,
            GasProfile.LOW, GasProfile.MEDIUM, GasProfile.HIGH,
        ]
        max_idx = profile_order.index(max_profile)
        return [
            name for name, info in self._networks.items()
            if profile_order.index(info.gas_profile) <= max_idx
            and info.status == NetworkStatus.ACTIVE
        ]

    def evm_chains(self) -> List[str]:
        """Get all EVM-compatible chains."""
        return [
            name for name, info in self._networks.items()
            if info.chain_type == ChainType.EVM
            and info.status == NetworkStatus.ACTIVE
        ]

    # ─── Token Queries ────────────────────────────────────────

    def get_token_address(self, chain: str, symbol: str) -> Optional[str]:
        """Get a token's contract address on a specific chain."""
        info = self.get(chain)
        if not info:
            return None
        token = info.tokens.get(symbol.upper())
        return token.address if token else None

    def chains_with_token(self, symbol: str) -> List[str]:
        """Get all chains that have a specific token."""
        symbol = symbol.upper()
        return [
            name for name, info in self._networks.items()
            if symbol in info.tokens
            and info.status == NetworkStatus.ACTIVE
        ]

    # ─── Status Management ────────────────────────────────────

    def set_status(self, chain: str, status: NetworkStatus) -> bool:
        """Update a network's operational status."""
        info = self.get(chain)
        if not info:
            return False
        info.status = status
        return True

    # ─── Explorer URLs ────────────────────────────────────────

    def tx_url(self, chain: str, tx_hash: str) -> Optional[str]:
        """Build a transaction explorer URL."""
        info = self.get(chain)
        if not info or not info.explorer_url:
            return None
        return f"{info.explorer_url}/tx/{tx_hash}"

    def address_url(self, chain: str, address: str) -> Optional[str]:
        """Build an address explorer URL."""
        info = self.get(chain)
        if not info or not info.explorer_url:
            return None
        return f"{info.explorer_url}/address/{address}"

    # ─── Diagnostics ──────────────────────────────────────────

    def summary(self) -> dict:
        """Get a summary of all registered networks."""
        by_status = {}
        by_gas = {}
        by_type = {}
        for name, info in self._networks.items():
            by_status[info.status.value] = by_status.get(info.status.value, 0) + 1
            by_gas[info.gas_profile.value] = by_gas.get(info.gas_profile.value, 0) + 1
            by_type[info.chain_type.value] = by_type.get(info.chain_type.value, 0) + 1

        return {
            "total_networks": len(self._networks),
            "total_aliases": len(self._aliases),
            "by_status": by_status,
            "by_gas_profile": by_gas,
            "by_chain_type": by_type,
            "features": {
                "payments": len(self.chains_with_feature("payments")),
                "identity": len(self.chains_with_feature("identity")),
                "reputation": len(self.chains_with_feature("reputation")),
                "escrow": len(self.chains_with_feature("escrow")),
            },
        }

    def health(self) -> dict:
        """Quick health check for SwarmIntegrator compatibility."""
        active = sum(
            1 for n in self._networks.values()
            if n.status == NetworkStatus.ACTIVE
        )
        degraded = sum(
            1 for n in self._networks.values()
            if n.status == NetworkStatus.DEGRADED
        )
        return {
            "healthy": active > 0,
            "active_networks": active,
            "degraded_networks": degraded,
            "total_networks": len(self._networks),
        }

    # ─── Factory ──────────────────────────────────────────────

    @classmethod
    def with_defaults(cls) -> "NetworkRegistry":
        """Create a registry with all EM-supported networks pre-configured."""
        registry = cls()

        # USDC addresses (shared across many chains)
        USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        USDC_ETH = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        USDC_POLYGON = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
        USDC_ARBITRUM = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
        USDC_OPTIMISM = "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"
        USDC_AVALANCHE = "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
        USDC_CELO = "0xcebA9300f2b948710d2653dD7B07f33A8B32118C"

        # ── Base ──
        registry.register(NetworkInfo(
            name="base",
            chain_id=8453,
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.LOW,
            explorer_url="https://basescan.org",
            tokens={"USDC": TokenInfo("USDC", USDC_BASE)},
            avg_block_time_seconds=2.0,
            avg_confirmation_time_seconds=5.0,
            notes="Primary EM network. ERC-8004 + payments + reputation.",
        ))

        # ── Ethereum ──
        registry.register(NetworkInfo(
            name="ethereum",
            chain_id=1,
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.HIGH,
            explorer_url="https://etherscan.io",
            tokens={"USDC": TokenInfo("USDC", USDC_ETH)},
            avg_block_time_seconds=12.0,
            avg_confirmation_time_seconds=60.0,
            notes="Mainnet. High gas. Used for high-value transactions.",
        ))

        # ── Polygon ──
        registry.register(NetworkInfo(
            name="polygon",
            chain_id=137,
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.MEDIUM,
            explorer_url="https://polygonscan.com",
            tokens={"USDC": TokenInfo("USDC", USDC_POLYGON)},
            avg_block_time_seconds=2.0,
            avg_confirmation_time_seconds=10.0,
        ))

        # ── Arbitrum ──
        registry.register(NetworkInfo(
            name="arbitrum",
            chain_id=42161,
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.LOW,
            explorer_url="https://arbiscan.io",
            tokens={"USDC": TokenInfo("USDC", USDC_ARBITRUM)},
            avg_block_time_seconds=0.25,
            avg_confirmation_time_seconds=2.0,
        ))

        # ── Optimism ──
        registry.register(NetworkInfo(
            name="optimism",
            chain_id=10,
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.LOW,
            explorer_url="https://optimistic.etherscan.io",
            tokens={"USDC": TokenInfo("USDC", USDC_OPTIMISM)},
            avg_block_time_seconds=2.0,
            avg_confirmation_time_seconds=5.0,
        ))

        # ── Avalanche ──
        registry.register(NetworkInfo(
            name="avalanche",
            chain_id=43114,
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.LOW,
            explorer_url="https://snowtrace.io",
            tokens={"USDC": TokenInfo("USDC", USDC_AVALANCHE)},
            avg_block_time_seconds=2.0,
            avg_confirmation_time_seconds=5.0,
        ))

        # ── Celo ──
        registry.register(NetworkInfo(
            name="celo",
            chain_id=42220,
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.ULTRA_LOW,
            explorer_url="https://celoscan.io",
            tokens={"USDC": TokenInfo("USDC", USDC_CELO)},
            avg_block_time_seconds=5.0,
            avg_confirmation_time_seconds=15.0,
        ))

        # ── SKALE ──
        registry.register(NetworkInfo(
            name="skale",
            chain_id=1564830818,  # SKALE Europa
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.FREE,
            explorer_url="https://elated-tan-skat.explorer.mainnet.skalenodes.com",
            supports_escrow=True,
            avg_block_time_seconds=1.0,
            avg_confirmation_time_seconds=3.0,
            notes="Zero gas fees. Good for high-frequency micro-tasks.",
        ))

        # ── Monad (placeholder — not yet mainnet) ──
        registry.register(NetworkInfo(
            name="monad",
            chain_id=None,  # TBD
            chain_type=ChainType.EVM,
            gas_profile=GasProfile.ULTRA_LOW,
            status=NetworkStatus.DISABLED,  # Not yet live
            supports_payments=False,
            notes="Pending mainnet launch. describe-net contracts deployed on testnet.",
        ))

        # ── Aliases ──
        registry.register_alias("eth", "ethereum")
        registry.register_alias("matic", "polygon")
        registry.register_alias("arb", "arbitrum")
        registry.register_alias("op", "optimism")
        registry.register_alias("avax", "avalanche")
        registry.register_alias("skale-base", "skale")

        return registry
