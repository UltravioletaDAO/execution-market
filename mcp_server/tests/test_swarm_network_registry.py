"""
Tests for NetworkRegistry — Module #56
========================================

Comprehensive test coverage for multi-chain network configuration:
- Network registration and lookup
- Alias resolution
- Feature queries (payments, identity, escrow)
- Gas profile filtering
- Token address queries
- Status management
- Explorer URL generation
- Factory defaults
- Diagnostics
- Edge cases
"""

import importlib.util
import os
import pytest

# Direct import to avoid swarm/__init__.py (Python 3.10+ syntax issues)
_swarm_dir = os.path.join(os.path.dirname(__file__), "..", "swarm")
_spec = importlib.util.spec_from_file_location(
    "network_registry",
    os.path.join(_swarm_dir, "network_registry.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

NetworkRegistry = _mod.NetworkRegistry
NetworkInfo = _mod.NetworkInfo
ChainType = _mod.ChainType
GasProfile = _mod.GasProfile
NetworkStatus = _mod.NetworkStatus
TokenInfo = _mod.TokenInfo


# ─── Helpers ──────────────────────────────────────────────────


def _base_network():
    return NetworkInfo(
        name="base",
        chain_id=8453,
        chain_type=ChainType.EVM,
        gas_profile=GasProfile.LOW,
        explorer_url="https://basescan.org",
        tokens={"USDC": TokenInfo("USDC", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")},
    )


def _skale_network():
    return NetworkInfo(
        name="skale",
        chain_id=1564830818,
        chain_type=ChainType.EVM,
        gas_profile=GasProfile.FREE,
        explorer_url="https://skale.explorer.example",
        notes="Zero gas fees",
    )


def _ethereum_network():
    return NetworkInfo(
        name="ethereum",
        chain_id=1,
        chain_type=ChainType.EVM,
        gas_profile=GasProfile.HIGH,
        explorer_url="https://etherscan.io",
        tokens={"USDC": TokenInfo("USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")},
    )


def _solana_network():
    return NetworkInfo(
        name="solana",
        chain_id=None,
        chain_type=ChainType.SVM,
        gas_profile=GasProfile.ULTRA_LOW,
    )


# ─── Test: Registration & Lookup ─────────────────────────────


class TestRegistration:
    """Network registration and basic lookup."""

    def test_register_and_get(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        info = reg.get("base")
        assert info is not None
        assert info.name == "base"
        assert info.chain_id == 8453

    def test_get_nonexistent(self):
        reg = NetworkRegistry()
        assert reg.get("bitcoin") is None

    def test_register_normalizes_name(self):
        reg = NetworkRegistry()
        net = NetworkInfo(
            name="  Base  ", chain_id=8453,
            chain_type=ChainType.EVM, gas_profile=GasProfile.LOW,
        )
        reg.register(net)
        assert reg.get("base") is not None
        assert reg.get("BASE") is not None

    def test_register_multiple(self):
        reg = NetworkRegistry()
        reg.register(_base_network())
        reg.register(_ethereum_network())
        reg.register(_skale_network())

        assert len(reg.all_networks()) == 3

    def test_overwrite_registration(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        updated = NetworkInfo(
            name="base", chain_id=8453,
            chain_type=ChainType.EVM, gas_profile=GasProfile.ULTRA_LOW,
        )
        reg.register(updated)

        info = reg.get("base")
        assert info.gas_profile == GasProfile.ULTRA_LOW

    def test_chain_fluent_api(self):
        reg = NetworkRegistry()
        result = reg.register(_base_network())
        assert result is reg  # Returns self for chaining


# ─── Test: Alias Resolution ──────────────────────────────────


class TestAliases:
    """Network name aliases."""

    def test_alias_lookup(self):
        reg = NetworkRegistry()
        reg.register(_ethereum_network())
        reg.register_alias("eth", "ethereum")

        info = reg.get("eth")
        assert info is not None
        assert info.name == "ethereum"

    def test_resolve_name(self):
        reg = NetworkRegistry()
        reg.register_alias("arb", "arbitrum")

        assert reg.resolve_name("arb") == "arbitrum"
        assert reg.resolve_name("base") == "base"  # No alias = identity

    def test_multiple_aliases(self):
        reg = NetworkRegistry()
        reg.register(_ethereum_network())
        reg.register_alias("eth", "ethereum")
        reg.register_alias("mainnet", "ethereum")

        assert reg.get("eth").name == "ethereum"
        assert reg.get("mainnet").name == "ethereum"

    def test_alias_case_insensitive(self):
        reg = NetworkRegistry()
        reg.register(_ethereum_network())
        reg.register_alias("ETH", "ethereum")

        assert reg.get("eth") is not None

    def test_alias_to_nonexistent(self):
        reg = NetworkRegistry()
        reg.register_alias("missing", "nonexistent")

        assert reg.get("missing") is None


# ─── Test: Validation ─────────────────────────────────────────


class TestValidation:
    """Chain validation."""

    def test_validate_known_chain(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        assert reg.validate_chain("base") is True

    def test_validate_unknown_chain(self):
        reg = NetworkRegistry()
        assert reg.validate_chain("bitcoin") is False

    def test_validate_disabled_chain(self):
        reg = NetworkRegistry()
        net = NetworkInfo(
            name="monad", chain_id=None,
            chain_type=ChainType.EVM, gas_profile=GasProfile.LOW,
            status=NetworkStatus.DISABLED,
        )
        reg.register(net)

        assert reg.validate_chain("monad") is False

    def test_validate_degraded_chain(self):
        """Degraded chains are still valid (usable but with warnings)."""
        reg = NetworkRegistry()
        net = NetworkInfo(
            name="polygon", chain_id=137,
            chain_type=ChainType.EVM, gas_profile=GasProfile.MEDIUM,
            status=NetworkStatus.DEGRADED,
        )
        reg.register(net)

        assert reg.validate_chain("polygon") is True

    def test_validate_via_alias(self):
        reg = NetworkRegistry()
        reg.register(_ethereum_network())
        reg.register_alias("eth", "ethereum")

        assert reg.validate_chain("eth") is True


# ─── Test: Feature Queries ────────────────────────────────────


class TestFeatureQueries:
    """Query chains by supported features."""

    def test_chains_with_payments(self):
        reg = NetworkRegistry()
        reg.register(_base_network())  # payments=True (default)
        net_no_pay = NetworkInfo(
            name="testnet", chain_id=999,
            chain_type=ChainType.EVM, gas_profile=GasProfile.FREE,
            supports_payments=False,
        )
        reg.register(net_no_pay)

        chains = reg.chains_with_feature("payments")
        assert "base" in chains
        assert "testnet" not in chains

    def test_chains_with_identity(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        chains = reg.chains_with_feature("identity")
        assert "base" in chains

    def test_chains_with_unknown_feature(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        assert reg.chains_with_feature("teleportation") == []

    def test_disabled_chains_excluded(self):
        reg = NetworkRegistry()
        net = NetworkInfo(
            name="disabled", chain_id=0,
            chain_type=ChainType.EVM, gas_profile=GasProfile.LOW,
            status=NetworkStatus.DISABLED,
        )
        reg.register(net)

        chains = reg.chains_with_feature("payments")
        assert "disabled" not in chains


# ─── Test: Gas Profile Filtering ──────────────────────────────


class TestGasProfiles:
    """Filter chains by gas cost."""

    def test_chains_by_gas_low(self):
        reg = NetworkRegistry()
        reg.register(_base_network())  # LOW
        reg.register(_ethereum_network())  # HIGH
        reg.register(_skale_network())  # FREE

        chains = reg.chains_by_gas(GasProfile.LOW)
        assert "base" in chains
        assert "skale" in chains
        assert "ethereum" not in chains

    def test_chains_by_gas_free(self):
        reg = NetworkRegistry()
        reg.register(_base_network())
        reg.register(_skale_network())

        chains = reg.chains_by_gas(GasProfile.FREE)
        assert "skale" in chains
        assert "base" not in chains

    def test_chains_by_gas_high_includes_all(self):
        reg = NetworkRegistry()
        reg.register(_base_network())
        reg.register(_ethereum_network())
        reg.register(_skale_network())

        chains = reg.chains_by_gas(GasProfile.HIGH)
        assert len(chains) == 3


# ─── Test: EVM Chain Filtering ────────────────────────────────


class TestChainTypes:
    """Filter by chain type."""

    def test_evm_chains(self):
        reg = NetworkRegistry()
        reg.register(_base_network())  # EVM
        reg.register(_solana_network())  # SVM

        evm = reg.evm_chains()
        assert "base" in evm
        assert "solana" not in evm


# ─── Test: Token Queries ─────────────────────────────────────


class TestTokenQueries:
    """Token address lookups."""

    def test_get_token_address(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        addr = reg.get_token_address("base", "USDC")
        assert addr == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

    def test_get_token_address_unknown_chain(self):
        reg = NetworkRegistry()
        assert reg.get_token_address("bitcoin", "USDC") is None

    def test_get_token_address_unknown_token(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        assert reg.get_token_address("base", "DOGE") is None

    def test_get_token_case_insensitive(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        assert reg.get_token_address("base", "usdc") is not None

    def test_chains_with_token(self):
        reg = NetworkRegistry()
        reg.register(_base_network())
        reg.register(_ethereum_network())
        reg.register(_skale_network())  # No USDC token

        chains = reg.chains_with_token("USDC")
        assert "base" in chains
        assert "ethereum" in chains
        assert "skale" not in chains


# ─── Test: Status Management ─────────────────────────────────


class TestStatusManagement:
    """Network status updates."""

    def test_set_status(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        assert reg.set_status("base", NetworkStatus.DEGRADED) is True
        assert reg.get("base").status == NetworkStatus.DEGRADED

    def test_set_status_unknown_chain(self):
        reg = NetworkRegistry()
        assert reg.set_status("bitcoin", NetworkStatus.ACTIVE) is False

    def test_disabled_chain_not_in_active(self):
        reg = NetworkRegistry()
        reg.register(_base_network())
        reg.register(_ethereum_network())

        reg.set_status("base", NetworkStatus.DISABLED)

        active = reg.active_networks()
        names = [n.name for n in active]
        assert "base" not in names
        assert "ethereum" in names


# ─── Test: Explorer URLs ─────────────────────────────────────


class TestExplorerURLs:
    """Explorer URL generation."""

    def test_tx_url(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        url = reg.tx_url("base", "0xABC123")
        assert url == "https://basescan.org/tx/0xABC123"

    def test_address_url(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        url = reg.address_url("base", "0xDEF456")
        assert url == "https://basescan.org/address/0xDEF456"

    def test_tx_url_no_explorer(self):
        reg = NetworkRegistry()
        net = NetworkInfo(
            name="private", chain_id=999,
            chain_type=ChainType.EVM, gas_profile=GasProfile.FREE,
        )
        reg.register(net)

        assert reg.tx_url("private", "0x123") is None

    def test_tx_url_unknown_chain(self):
        reg = NetworkRegistry()
        assert reg.tx_url("bitcoin", "0x123") is None


# ─── Test: Diagnostics ───────────────────────────────────────


class TestDiagnostics:
    """Summary and health."""

    def test_summary(self):
        reg = NetworkRegistry()
        reg.register(_base_network())
        reg.register(_ethereum_network())
        reg.register(_skale_network())

        summary = reg.summary()
        assert summary["total_networks"] == 3
        assert "by_status" in summary
        assert "by_gas_profile" in summary
        assert "features" in summary

    def test_health_with_active(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        health = reg.health()
        assert health["healthy"] is True
        assert health["active_networks"] == 1

    def test_health_empty(self):
        reg = NetworkRegistry()
        health = reg.health()
        assert health["healthy"] is False
        assert health["active_networks"] == 0

    def test_health_with_degraded(self):
        reg = NetworkRegistry()
        reg.register(_base_network())
        net = NetworkInfo(
            name="polygon", chain_id=137,
            chain_type=ChainType.EVM, gas_profile=GasProfile.MEDIUM,
            status=NetworkStatus.DEGRADED,
        )
        reg.register(net)

        health = reg.health()
        assert health["degraded_networks"] == 1

    def test_network_info_to_dict(self):
        info = _base_network()
        d = info.to_dict()

        assert d["name"] == "base"
        assert d["chain_id"] == 8453
        assert d["chain_type"] == "evm"
        assert d["gas_profile"] == "low"
        assert d["features"]["payments"] is True
        assert "USDC" in d["tokens"]


# ─── Test: Factory Defaults ──────────────────────────────────


class TestFactoryDefaults:
    """with_defaults() factory method."""

    def test_creates_registry(self):
        reg = NetworkRegistry.with_defaults()
        assert len(reg.all_networks()) >= 8  # At least 8 networks

    def test_base_configured(self):
        reg = NetworkRegistry.with_defaults()
        base = reg.get("base")

        assert base is not None
        assert base.chain_id == 8453
        assert base.gas_profile == GasProfile.LOW
        assert base.supports_payments is True

    def test_skale_configured(self):
        reg = NetworkRegistry.with_defaults()
        skale = reg.get("skale")

        assert skale is not None
        assert skale.gas_profile == GasProfile.FREE

    def test_ethereum_configured(self):
        reg = NetworkRegistry.with_defaults()
        eth = reg.get("ethereum")

        assert eth is not None
        assert eth.gas_profile == GasProfile.HIGH
        assert eth.chain_id == 1

    def test_monad_disabled(self):
        reg = NetworkRegistry.with_defaults()
        monad = reg.get("monad")

        assert monad is not None
        assert monad.status == NetworkStatus.DISABLED
        assert reg.validate_chain("monad") is False

    def test_aliases_work(self):
        reg = NetworkRegistry.with_defaults()

        assert reg.get("eth").name == "ethereum"
        assert reg.get("arb").name == "arbitrum"
        assert reg.get("avax").name == "avalanche"
        assert reg.get("op").name == "optimism"

    def test_usdc_on_base(self):
        reg = NetworkRegistry.with_defaults()
        addr = reg.get_token_address("base", "USDC")

        assert addr == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

    def test_all_active_have_payments(self):
        reg = NetworkRegistry.with_defaults()
        for net in reg.active_networks():
            # All active EM networks should support payments
            # (except some edge cases)
            if net.name != "monad":
                assert net.supports_payments is True, f"{net.name} missing payments"


# ─── Test: Edge Cases ────────────────────────────────────────


class TestEdgeCases:
    """Boundary conditions."""

    def test_empty_registry(self):
        reg = NetworkRegistry()
        assert reg.all_networks() == []
        assert reg.active_networks() == []
        assert reg.evm_chains() == []

    def test_empty_name(self):
        reg = NetworkRegistry()
        assert reg.get("") is None
        assert reg.validate_chain("") is False

    def test_case_insensitive_everything(self):
        reg = NetworkRegistry()
        reg.register(_base_network())

        assert reg.get("BASE") is not None
        assert reg.get("Base") is not None
        assert reg.validate_chain("BASE") is True

    def test_gas_profile_ordering(self):
        """Gas profiles should have a clear ordering."""
        assert GasProfile.FREE.value == "free"
        assert GasProfile.HIGH.value == "high"

    def test_chain_type_enum(self):
        assert ChainType.EVM.value == "evm"
        assert ChainType.SVM.value == "svm"
