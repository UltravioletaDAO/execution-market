"""Tests for the static network/token registry."""

from em_plugin_sdk.networks import (
    NETWORKS,
    get_network,
    get_enabled_networks,
    get_supported_tokens,
    is_valid_pair,
    get_chain_id,
    get_escrow_networks,
    DEFAULT_NETWORK,
    DEFAULT_TOKEN,
)


class TestNetworkRegistry:
    def test_all_9_enabled_networks(self):
        enabled = get_enabled_networks()
        names = {n.name for n in enabled}
        assert "base" in names
        assert "ethereum" in names
        assert "solana" in names
        assert len(enabled) == 9

    def test_base_has_usdc_and_eurc(self):
        net = get_network("base")
        assert net is not None
        assert "USDC" in net.token_symbols
        assert "EURC" in net.token_symbols

    def test_solana_is_svm(self):
        net = get_network("solana")
        assert net is not None
        assert net.network_type == "svm"
        assert net.chain_id is None
        assert not net.has_escrow

    def test_get_chain_id(self):
        assert get_chain_id("base") == 8453
        assert get_chain_id("ethereum") == 1
        assert get_chain_id("polygon") == 137
        assert get_chain_id("nonexistent") is None

    def test_is_valid_pair(self):
        assert is_valid_pair("base", "USDC") is True
        assert is_valid_pair("base", "EURC") is True
        assert is_valid_pair("base", "PYUSD") is False
        assert is_valid_pair("ethereum", "PYUSD") is True
        assert is_valid_pair("nonexistent", "USDC") is False

    def test_get_supported_tokens(self):
        tokens = get_supported_tokens("ethereum")
        assert "USDC" in tokens
        assert "EURC" in tokens
        assert "PYUSD" in tokens
        assert "AUSD" in tokens
        assert get_supported_tokens("nonexistent") == []

    def test_escrow_networks(self):
        escrow = get_escrow_networks()
        assert "base" in escrow
        assert "ethereum" in escrow
        assert "solana" not in escrow

    def test_defaults(self):
        assert DEFAULT_NETWORK == "base"
        assert DEFAULT_TOKEN == "USDC"

    def test_operator_flag(self):
        net = get_network("base")
        assert net is not None
        assert net.has_operator is True
        sol = get_network("solana")
        assert sol is not None
        assert sol.has_operator is False

    def test_token_address_format(self):
        """EVM tokens start with 0x, Solana tokens are base58."""
        base_usdc = get_network("base").get_token("USDC")
        assert base_usdc.address.startswith("0x")
        sol_usdc = get_network("solana").get_token("USDC")
        assert not sol_usdc.address.startswith("0x")
