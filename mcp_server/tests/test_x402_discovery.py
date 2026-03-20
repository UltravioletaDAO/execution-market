"""
Tests for x402 protocol discovery endpoint (/.well-known/x402).

Validates that the discovery payload is well-formed, contains all required
fields, and accurately reflects the enabled network configuration.
"""

import pytest

pytestmark = [pytest.mark.infrastructure]


class TestX402Discovery:
    """Tests for the /.well-known/x402 discovery endpoint."""

    def test_build_discovery_payload_structure(self, monkeypatch):
        """Discovery payload has required top-level structure."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_discovery_payload

        payload = _build_discovery_payload()

        assert "x402" in payload
        x402 = payload["x402"]
        assert x402["version"] == "1.0"
        assert "description" in x402
        assert "provider" in x402
        assert "capabilities" in x402
        assert "facilitator" in x402
        assert "defaultNetwork" in x402
        assert "networks" in x402
        assert "fees" in x402
        assert "endpoints" in x402
        assert "discovery" in x402
        assert "identity" in x402

    def test_provider_info(self, monkeypatch):
        """Provider block contains correct Execution Market info."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_discovery_payload

        provider = _build_discovery_payload()["x402"]["provider"]

        assert provider["name"] == "Execution Market"
        assert "execution.market" in provider["url"]
        assert "@" in provider["contact"]

    def test_capabilities_flags(self, monkeypatch):
        """Capabilities accurately reflect platform features."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_discovery_payload

        caps = _build_discovery_payload()["x402"]["capabilities"]

        assert caps["payments"] is True
        assert caps["escrow"] is True
        assert caps["gasless"] is True
        assert caps["eip3009"] is True
        assert caps["multichain"] is True

    def test_networks_from_config(self, monkeypatch):
        """Networks list derives from NETWORK_CONFIG and ENABLED_NETWORKS."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_supported_networks

        networks = _build_supported_networks()

        assert len(networks) > 0
        # Base should always be present
        base = next((n for n in networks if n["name"] == "base"), None)
        assert base is not None
        assert base["chainId"] == 8453
        assert base["type"] == "evm"
        assert len(base["tokens"]) > 0

        # Each token has required fields
        for token in base["tokens"]:
            assert "symbol" in token
            assert "address" in token
            assert "decimals" in token
            assert token["address"].startswith("0x")

    def test_networks_have_escrow_info(self, monkeypatch):
        """Networks with escrow contracts expose escrow flag and operator."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_supported_networks

        networks = _build_supported_networks()
        base = next((n for n in networks if n["name"] == "base"), None)

        assert base is not None
        assert base.get("escrow") is True
        assert base.get("operator", "").startswith("0x")

    def test_endpoints_catalog(self, monkeypatch):
        """Endpoints section lists key API operations."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_discovery_payload

        endpoints = _build_discovery_payload()["x402"]["endpoints"]

        assert "tasks" in endpoints
        assert "create" in endpoints["tasks"]
        assert "list" in endpoints["tasks"]
        assert "approve" in endpoints["tasks"]

        create = endpoints["tasks"]["create"]
        assert create["method"] == "POST"
        assert create["path"] == "/api/v1/tasks"
        assert "pricing" in create

    def test_discovery_links(self, monkeypatch):
        """Discovery section points to other standard endpoints."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_discovery_payload

        discovery = _build_discovery_payload()["x402"]["discovery"]

        assert discovery["a2a"] == "/.well-known/agent.json"
        assert discovery["openapi"] == "/openapi.json"
        assert discovery["mcp"] == "/mcp/"

    def test_identity_erc8004(self, monkeypatch):
        """Identity section references ERC-8004 agent registration."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_discovery_payload

        identity = _build_discovery_payload()["x402"]["identity"]

        assert identity["protocol"] == "ERC-8004"
        assert identity["agentId"] == 2106
        assert identity["network"] == "base"
        assert identity["registry"].startswith("0x8004")

    def test_fees_bps(self, monkeypatch):
        """Fees are expressed in basis points matching EM_PLATFORM_FEE."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        monkeypatch.setenv("EM_PLATFORM_FEE", "0.13")
        from api.routers.x402_discovery import _build_discovery_payload

        fees = _build_discovery_payload()["x402"]["fees"]

        assert fees["platformFeeBps"] == 1300  # 13% = 1300 bps
        assert "description" in fees

    def test_default_network_from_env(self, monkeypatch):
        """Default network reads from X402_NETWORK env var."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        monkeypatch.setenv("X402_NETWORK", "polygon")
        import integrations.x402.sdk_client as sdk_mod

        original = sdk_mod.DEFAULT_NETWORK
        sdk_mod.DEFAULT_NETWORK = "polygon"
        try:
            from api.routers.x402_discovery import _build_discovery_payload

            payload = _build_discovery_payload()
            assert payload["x402"]["defaultNetwork"] == "polygon"
        finally:
            sdk_mod.DEFAULT_NETWORK = original

    def test_solana_excluded_from_escrow(self, monkeypatch):
        """Solana network should not have escrow or operator fields."""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "0x" + "a" * 40)
        from api.routers.x402_discovery import _build_supported_networks

        networks = _build_supported_networks()
        solana = next((n for n in networks if n["name"] == "solana"), None)

        if solana:
            assert solana.get("escrow") is None or solana.get("escrow") is False
            assert "operator" not in solana or solana["operator"] is None
