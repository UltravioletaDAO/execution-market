"""
Tests for x402 Client (NOW-024)

Run with: pytest test_client.py -v
"""

import pytest
from decimal import Decimal

from .client import (
    X402Client,
    PaymentToken,
    X402Error,
    EscrowCreationError,
    InsufficientFundsError,
    TOKEN_ADDRESSES,
    TOKEN_DECIMALS,
    DEFAULT_FACILITATOR_URL,
)


class TestPaymentToken:
    """Test PaymentToken enum."""

    def test_token_values(self):
        """Test token enum values."""
        assert PaymentToken.USDC.value == "usdc"
        assert PaymentToken.EURC.value == "eurc"
        assert PaymentToken.DAI.value == "dai"
        assert PaymentToken.USDT.value == "usdt"


class TestTokenAddresses:
    """Test token address constants."""

    def test_base_tokens(self):
        """Test Base network token addresses exist."""
        assert "usdc" in TOKEN_ADDRESSES["base"]
        assert "eurc" in TOKEN_ADDRESSES["base"]
        assert "dai" in TOKEN_ADDRESSES["base"]
        assert "usdt" in TOKEN_ADDRESSES["base"]

    def test_polygon_tokens(self):
        """Test Polygon network token addresses exist."""
        assert "usdc" in TOKEN_ADDRESSES["polygon"]
        assert "eurc" in TOKEN_ADDRESSES["polygon"]
        assert "dai" in TOKEN_ADDRESSES["polygon"]
        assert "usdt" in TOKEN_ADDRESSES["polygon"]

    def test_token_decimals(self):
        """Test token decimals are correct."""
        assert TOKEN_DECIMALS["usdc"] == 6
        assert TOKEN_DECIMALS["eurc"] == 6
        assert TOKEN_DECIMALS["dai"] == 18
        assert TOKEN_DECIMALS["usdt"] == 6


class TestX402ClientInit:
    """Test X402Client initialization."""

    def test_default_init(self):
        """Test client initializes with defaults."""
        # Note: This will fail Web3 init without valid RPC, but should not raise
        client = X402Client(rpc_url=None, private_key=None)
        assert client.network == "base"
        assert client.default_token == PaymentToken.USDC
        assert client.facilitator_url == DEFAULT_FACILITATOR_URL

    def test_custom_init(self):
        """Test client with custom parameters."""
        client = X402Client(
            facilitator_url="https://custom.example.com",
            network="polygon",
            default_token=PaymentToken.EURC,
            rpc_url=None,
            private_key=None,
        )
        assert client.network == "polygon"
        assert client.default_token == PaymentToken.EURC
        assert client.facilitator_url == "https://custom.example.com"


class TestTokenConversions:
    """Test token amount conversions."""

    def test_to_token_amount_usdc(self):
        """Test converting decimal to USDC wei."""
        client = X402Client(rpc_url=None, private_key=None)
        # 10.50 USDC = 10500000 (6 decimals)
        result = client.to_token_amount(Decimal("10.50"), PaymentToken.USDC)
        assert result == 10500000

    def test_to_token_amount_dai(self):
        """Test converting decimal to DAI wei."""
        client = X402Client(rpc_url=None, private_key=None)
        # 10.50 DAI = 10500000000000000000 (18 decimals)
        result = client.to_token_amount(Decimal("10.50"), PaymentToken.DAI)
        assert result == 10500000000000000000

    def test_from_token_amount_usdc(self):
        """Test converting USDC wei to decimal."""
        client = X402Client(rpc_url=None, private_key=None)
        # 10500000 = 10.50 USDC
        result = client.from_token_amount(10500000, PaymentToken.USDC)
        assert result == Decimal("10.50")

    def test_from_token_amount_dai(self):
        """Test converting DAI wei to decimal."""
        client = X402Client(rpc_url=None, private_key=None)
        # 10500000000000000000 = 10.50 DAI
        result = client.from_token_amount(10500000000000000000, PaymentToken.DAI)
        assert result == Decimal("10.50")


class TestGetTokenAddress:
    """Test token address retrieval."""

    def test_get_usdc_base(self):
        """Test getting USDC address on Base."""
        client = X402Client(network="base", rpc_url=None, private_key=None)
        addr = client.get_token_address(PaymentToken.USDC)
        assert addr == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

    def test_get_usdc_polygon(self):
        """Test getting USDC address on Polygon."""
        client = X402Client(network="polygon", rpc_url=None, private_key=None)
        addr = client.get_token_address(PaymentToken.USDC)
        assert addr == "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

    def test_invalid_token_on_network(self):
        """Test error when token not supported on network."""
        # Optimism doesn't have EURC in our config
        client = X402Client(network="optimism", rpc_url=None, private_key=None)
        with pytest.raises(X402Error):
            client.get_token_address(PaymentToken.EURC)


class TestExceptions:
    """Test custom exceptions."""

    def test_x402_error(self):
        """Test base X402Error."""
        err = X402Error("Test error", "TEST_CODE", {"key": "value"})
        assert str(err) == "Test error"
        assert err.code == "TEST_CODE"
        assert err.details == {"key": "value"}

    def test_escrow_creation_error(self):
        """Test EscrowCreationError."""
        err = EscrowCreationError("Creation failed")
        assert err.code == "ESCROW_CREATION_FAILED"

    def test_insufficient_funds_error(self):
        """Test InsufficientFundsError."""
        err = InsufficientFundsError(
            required=Decimal("100"),
            available=Decimal("50"),
            token=PaymentToken.USDC,
        )
        assert "100" in str(err)
        assert "50" in str(err)
        assert "USDC" in str(err)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
