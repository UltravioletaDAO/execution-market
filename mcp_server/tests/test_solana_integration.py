"""
Tests for Solana (SVM) integration across backend modules.

Covers:
- NETWORK_CONFIG Solana entry (sdk_client.py)
- is_svm_network helper
- get_token_config / get_enabled_networks / get_escrow_config for Solana
- PaymentDispatcher Solana handling (_extract_tx_hash, _get_operator_for_network)
- ERC-8004 Solana entry (facilitator_client.py)
- network_type consistency across all NETWORK_CONFIG entries
"""

import sys
from pathlib import Path
from types import ModuleType

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = [pytest.mark.payments, pytest.mark.core]


def _import_facilitator_client() -> ModuleType:
    """Import facilitator_client directly, bypassing erc8004/__init__.py.

    The __init__.py imports register.py which needs web3.middleware.ExtraDataToPOAMiddleware
    that may not be available in all test environments.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "integrations.erc8004.facilitator_client",
        Path(__file__).parent.parent
        / "integrations"
        / "erc8004"
        / "facilitator_client.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =============================================================================
# Task 5.2: NETWORK_CONFIG Solana entry
# =============================================================================


class TestSolanaNetworkConfig:
    """Verify Solana exists in NETWORK_CONFIG with correct structure."""

    def test_solana_in_network_config(self):
        """Solana exists in NETWORK_CONFIG with correct structure."""
        from integrations.x402.sdk_client import NETWORK_CONFIG

        assert "solana" in NETWORK_CONFIG
        cfg = NETWORK_CONFIG["solana"]
        assert cfg["chain_id"] is None
        assert cfg["network_type"] == "svm"
        assert "USDC" in cfg["tokens"]
        assert (
            cfg["tokens"]["USDC"]["address"]
            == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        )
        assert cfg["tokens"]["USDC"]["decimals"] == 6

    def test_solana_has_ausd_token(self):
        """Solana has AUSD (Agora Dollar) as a second stablecoin."""
        from integrations.x402.sdk_client import NETWORK_CONFIG

        cfg = NETWORK_CONFIG["solana"]
        assert "AUSD" in cfg["tokens"]
        assert (
            cfg["tokens"]["AUSD"]["address"]
            == "AUSD1jCcCyPLybk1YnvPWsHQSrZ46dxwoMniN4N2UEB9"
        )

    def test_solana_has_no_escrow_infrastructure(self):
        """Solana config has no escrow/factory/operator keys (Fase 1 only)."""
        from integrations.x402.sdk_client import NETWORK_CONFIG

        cfg = NETWORK_CONFIG["solana"]
        assert "escrow" not in cfg
        assert "factory" not in cfg
        assert "operator" not in cfg
        assert "x402r_infra" not in cfg

    def test_is_svm_network(self):
        """is_svm_network returns True for Solana, False for EVM chains."""
        from integrations.x402.sdk_client import is_svm_network

        assert is_svm_network("solana") is True
        assert is_svm_network("base") is False
        assert is_svm_network("ethereum") is False
        assert is_svm_network("polygon") is False

    def test_is_svm_network_unknown(self):
        """is_svm_network returns False for unknown networks."""
        from integrations.x402.sdk_client import is_svm_network

        assert is_svm_network("unknown-chain") is False

    def test_get_token_config_solana(self):
        """get_token_config returns correct Solana USDC config."""
        from integrations.x402.sdk_client import get_token_config

        config = get_token_config("solana", "USDC")
        assert config is not None
        assert config["chain_id"] is None
        assert config["address"] == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        assert config["decimals"] == 6
        assert config["network_type"] == "svm"

    def test_get_token_config_solana_ausd(self):
        """get_token_config returns Solana AUSD config."""
        from integrations.x402.sdk_client import get_token_config

        config = get_token_config("solana", "AUSD")
        assert config is not None
        assert config["address"] == "AUSD1jCcCyPLybk1YnvPWsHQSrZ46dxwoMniN4N2UEB9"

    def test_get_token_config_solana_invalid_token(self):
        """get_token_config raises ValueError for unsupported token on Solana."""
        from integrations.x402.sdk_client import get_token_config

        with pytest.raises(ValueError, match="not available on solana"):
            get_token_config("solana", "WETH")

    def test_get_enabled_networks_includes_solana(self):
        """Solana is included in enabled networks by default."""
        from integrations.x402.sdk_client import get_enabled_networks

        networks = get_enabled_networks()
        assert "solana" in networks

    def test_solana_has_no_escrow(self):
        """get_escrow_config returns None for Solana (no x402r escrow)."""
        from integrations.x402.sdk_client import get_escrow_config

        config = get_escrow_config("solana")
        assert config is None

    def test_solana_has_no_operator(self):
        """get_operator_address returns None for Solana."""
        from integrations.x402.sdk_client import get_operator_address

        assert get_operator_address("solana") is None

    def test_all_networks_have_network_type(self):
        """Every NETWORK_CONFIG entry has a valid network_type field."""
        from integrations.x402.sdk_client import NETWORK_CONFIG

        for name, cfg in NETWORK_CONFIG.items():
            assert "network_type" in cfg, f"{name} missing network_type"
            assert cfg["network_type"] in (
                "evm",
                "svm",
            ), f"{name} has invalid network_type: {cfg['network_type']}"

    def test_solana_is_only_svm_network(self):
        """Only Solana should be SVM; all others should be EVM."""
        from integrations.x402.sdk_client import NETWORK_CONFIG

        svm_networks = [
            name
            for name, cfg in NETWORK_CONFIG.items()
            if cfg.get("network_type") == "svm"
        ]
        assert svm_networks == ["solana"]

    def test_solana_rpc_url(self):
        """Solana has a default RPC URL configured."""
        from integrations.x402.sdk_client import NETWORK_CONFIG

        cfg = NETWORK_CONFIG["solana"]
        assert "rpc_url" in cfg
        assert "solana" in cfg["rpc_url"] or "mainnet" in cfg["rpc_url"]


# =============================================================================
# Task 5.3: PaymentDispatcher Solana handling
# =============================================================================


class TestPaymentDispatcherSolana:
    """PaymentDispatcher correctly handles Solana transactions and networks."""

    def test_is_valid_tx_id_solana_signature(self):
        """Solana Base58 signatures are recognized as valid tx IDs."""
        from integrations.x402.payment_dispatcher import _is_valid_tx_id

        solana_sig = "5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW"
        assert _is_valid_tx_id(solana_sig) is True

    def test_is_valid_tx_id_evm_hash(self):
        """EVM 0x-prefixed hashes are still recognized."""
        from integrations.x402.payment_dispatcher import _is_valid_tx_id

        evm_hash = "0x" + "a" * 64
        assert _is_valid_tx_id(evm_hash) is True

    def test_is_valid_tx_id_rejects_short(self):
        """Short strings are not valid tx IDs."""
        from integrations.x402.payment_dispatcher import _is_valid_tx_id

        assert _is_valid_tx_id("short") is False
        assert _is_valid_tx_id("") is False
        assert _is_valid_tx_id(None) is False

    def test_extract_tx_hash_solana_signature(self):
        """_extract_tx_hash extracts Solana Base58 signatures from dicts."""
        from integrations.x402.payment_dispatcher import _extract_tx_hash

        solana_sig = "5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW"
        result = _extract_tx_hash({"transaction_hash": solana_sig})
        assert result == solana_sig

    def test_extract_tx_hash_evm_still_works(self):
        """EVM 0x-prefixed hashes still work via _extract_tx_hash."""
        from integrations.x402.payment_dispatcher import _extract_tx_hash

        evm_hash = "0x" + "a" * 64
        result = _extract_tx_hash({"transaction_hash": evm_hash})
        assert result == evm_hash

    def test_extract_tx_hash_none_returns_none(self):
        """_extract_tx_hash returns None for None input."""
        from integrations.x402.payment_dispatcher import _extract_tx_hash

        assert _extract_tx_hash(None) is None

    def test_no_operator_for_solana(self, monkeypatch):
        """Solana has no PaymentOperator (Fase 1 only)."""
        monkeypatch.delenv("EM_PAYMENT_OPERATOR", raising=False)
        # Ensure payment_dispatcher uses the real NETWORK_CONFIG (not the
        # empty-dict fallback that triggers when sdk_client import order races).
        from integrations.x402.sdk_client import NETWORK_CONFIG
        import integrations.x402.payment_dispatcher as pd

        monkeypatch.setattr(pd, "NETWORK_CONFIG", NETWORK_CONFIG)

        result = pd._get_operator_for_network("solana")
        assert result is None, f"Expected None for Solana, got {result}"


# =============================================================================
# Task 5.4: ERC-8004 Solana handling
# =============================================================================


class TestERC8004Solana:
    """ERC-8004 facilitator client handles Solana correctly."""

    def test_erc8004_contracts_include_solana(self):
        """Solana has program IDs instead of contract addresses."""
        mod = _import_facilitator_client()
        ERC8004_CONTRACTS = mod.ERC8004_CONTRACTS

        assert "solana" in ERC8004_CONTRACTS
        sol = ERC8004_CONTRACTS["solana"]
        assert "agent_registry_program" in sol
        assert sol["chain_id"] is None
        assert sol["network_type"] == "svm"

    def test_erc8004_solana_has_atom_engine(self):
        """Solana ERC-8004 config includes atom_engine_program."""
        mod = _import_facilitator_client()
        sol = mod.ERC8004_CONTRACTS["solana"]
        assert "atom_engine_program" in sol
        assert sol["atom_engine_program"].startswith("AToM")

    def test_erc8004_solana_no_evm_registries(self):
        """Solana ERC-8004 does NOT have EVM identity/reputation registries."""
        mod = _import_facilitator_client()
        sol = mod.ERC8004_CONTRACTS["solana"]
        assert "identity_registry" not in sol
        assert "reputation_registry" not in sol

    def test_erc8004_evm_networks_have_registries(self):
        """EVM networks in ERC8004_CONTRACTS have identity_registry (sanity check)."""
        mod = _import_facilitator_client()
        ERC8004_CONTRACTS = mod.ERC8004_CONTRACTS

        for name, cfg in ERC8004_CONTRACTS.items():
            if name == "solana":
                continue
            if name.endswith(("-sepolia", "-amoy", "-fuji")):
                continue
            assert "identity_registry" in cfg, (
                f"EVM network {name} missing identity_registry"
            )
