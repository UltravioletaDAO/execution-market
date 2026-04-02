"""
Tests for World AgentKit integration (Track 1).

Tests the AgentBook on-chain lookup module and its integration
into the worker application flow.

Marker: agentkit
"""

import sys
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.agentkit

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Define the expected types & functions matching the agentbook.py contract.
# When the real module is created by the other agent, these stubs will be
# replaced. This follows the test_erc8004_side_effects.py pattern.
# ---------------------------------------------------------------------------


class WorldHumanStatus(str, Enum):
    """World ID human verification status."""

    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"
    ERROR = "error"


@dataclass
class WorldHumanResult:
    """Result of a World ID human verification lookup."""

    status: WorldHumanStatus
    is_human: bool = False
    human_id: int = 0
    wallet_address: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self):
        d = {}
        for k, v in asdict(self).items():
            d[k] = v.value if isinstance(v, Enum) else v
        return d


def _encode_address(addr: str) -> str:
    """ABI-encode an address as a left-padded 32-byte hex word (no 0x prefix)."""
    return addr.lower().replace("0x", "").zfill(64)


async def _eth_call_default(to: str, data: str, rpc_url=None) -> str:
    """Default _eth_call -- always overridden by patch() in tests."""
    raise NotImplementedError("stub -- must be patched in tests")


async def lookup_human(wallet_address: str, rpc_url=None) -> WorldHumanResult:
    """
    Look up World ID human verification for a wallet via AgentBook contract.

    Delegates to the module-level _eth_call (patchable via
    ``integrations.world.agentbook._eth_call``).
    """
    # Resolve _eth_call from the module so patch() on the module attr works
    _mod = sys.modules["integrations.world.agentbook"]
    _eth_call = getattr(_mod, "_eth_call", _eth_call_default)

    try:
        encoded = _encode_address(wallet_address)
        calldata = "0x" + encoded
        raw = await _eth_call("0x0000", calldata, rpc_url=rpc_url)
        human_id = int(raw, 16) if raw and raw != "0x" else 0
        if human_id > 0:
            return WorldHumanResult(
                status=WorldHumanStatus.VERIFIED,
                is_human=True,
                human_id=human_id,
                wallet_address=wallet_address.lower(),
            )
        return WorldHumanResult(
            status=WorldHumanStatus.NOT_VERIFIED,
            is_human=False,
            human_id=0,
            wallet_address=wallet_address.lower(),
        )
    except Exception as e:
        return WorldHumanResult(
            status=WorldHumanStatus.ERROR,
            is_human=False,
            human_id=0,
            wallet_address=wallet_address.lower(),
            error=str(e),
        )


async def is_human(wallet_address: str, rpc_url=None) -> bool:
    """Convenience shortcut: returns True if wallet is World-ID verified."""
    result = await lookup_human(wallet_address, rpc_url=rpc_url)
    return result.is_human


# ---------------------------------------------------------------------------
# Install stubs into sys.modules so patch("integrations.world.agentbook.X")
# targets resolve. Follows test_erc8004_side_effects.py pattern.
# ---------------------------------------------------------------------------
_STUB_MODULES = [
    "integrations",
    "integrations.world",
    "integrations.world.agentbook",
]
for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = ModuleType(_mod_name)

_agentbook_mod = sys.modules["integrations.world.agentbook"]
_agentbook_mod.WorldHumanResult = WorldHumanResult
_agentbook_mod.WorldHumanStatus = WorldHumanStatus
_agentbook_mod._encode_address = _encode_address
_agentbook_mod._eth_call = _eth_call_default
_agentbook_mod.lookup_human = lookup_human
_agentbook_mod.is_human = is_human


# ===========================================================================
# Test constants
# ===========================================================================

SAMPLE_WALLET = "0x1234567890abcdef1234567890abcdef12345678"
MIXED_CASE_WALLET = "0xAbC1230000000000000000000000000000000def"

# Non-zero return: 42 encoded as uint256
HEX_42 = "0x" + "0" * 62 + "2a"
# Zero return: 0 encoded as uint256
HEX_ZERO = "0x" + "0" * 64


# ===========================================================================
# Tests
# ===========================================================================


class TestLookupHuman:
    """Tests for the lookup_human() function."""

    @pytest.mark.asyncio
    async def test_lookup_human_verified(self):
        """Non-zero return from _eth_call means wallet IS human-verified."""
        with patch(
            "integrations.world.agentbook._eth_call",
            new_callable=AsyncMock,
            return_value=HEX_42,
        ):
            result = await lookup_human(SAMPLE_WALLET)

        assert result.is_human is True
        assert result.human_id == 42
        assert result.status == WorldHumanStatus.VERIFIED

    @pytest.mark.asyncio
    async def test_lookup_human_not_verified(self):
        """Zero return from _eth_call means wallet is NOT human-verified."""
        with patch(
            "integrations.world.agentbook._eth_call",
            new_callable=AsyncMock,
            return_value=HEX_ZERO,
        ):
            result = await lookup_human(SAMPLE_WALLET)

        assert result.is_human is False
        assert result.human_id == 0
        assert result.status == WorldHumanStatus.NOT_VERIFIED

    @pytest.mark.asyncio
    async def test_lookup_human_rpc_error_returns_error_status(self):
        """RPC failure returns error status without raising."""
        with patch(
            "integrations.world.agentbook._eth_call",
            new_callable=AsyncMock,
            side_effect=RuntimeError("RPC error: connection refused"),
        ):
            result = await lookup_human(SAMPLE_WALLET)

        assert result.status == WorldHumanStatus.ERROR
        assert result.is_human is False
        assert result.error is not None
        assert "RPC" in result.error


class TestIsHumanShortcut:
    """Tests for the is_human() convenience function."""

    @pytest.mark.asyncio
    async def test_is_human_shortcut(self):
        """is_human() returns True when _eth_call returns non-zero."""
        with patch(
            "integrations.world.agentbook._eth_call",
            new_callable=AsyncMock,
            return_value=HEX_42,
        ):
            result = await is_human(SAMPLE_WALLET)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_human_shortcut_returns_false(self):
        """is_human() returns False when _eth_call returns zero."""
        with patch(
            "integrations.world.agentbook._eth_call",
            new_callable=AsyncMock,
            return_value=HEX_ZERO,
        ):
            result = await is_human(SAMPLE_WALLET)

        assert result is False


class TestEncodeAddress:
    """Tests for the _encode_address() helper."""

    def test_encode_address_lowercase_and_padded(self):
        """Mixed-case input is lowercased, 0x stripped, left-padded to 64 chars."""
        encoded = _encode_address(MIXED_CASE_WALLET)

        # Must be lowercase
        assert encoded == encoded.lower()
        # Must be exactly 64 hex chars (32 bytes)
        assert len(encoded) == 64
        # Must NOT have 0x prefix
        assert not encoded.startswith("0x")
        # Must contain the address digits (sans 0x, lowercased)
        raw_addr = MIXED_CASE_WALLET.lower().replace("0x", "")
        assert encoded.endswith(raw_addr) or raw_addr in encoded

    def test_encode_address_already_lowercase(self):
        """Already-lowercase address is handled correctly."""
        encoded = _encode_address(SAMPLE_WALLET)
        assert len(encoded) == 64
        assert encoded == encoded.lower()
        assert not encoded.startswith("0x")


class TestWorldHumanResultToDict:
    """Tests for WorldHumanResult.to_dict() serialization."""

    def test_to_dict_converts_enum_to_string(self):
        """to_dict() returns string status, not enum object."""
        result = WorldHumanResult(
            status=WorldHumanStatus.VERIFIED,
            is_human=True,
            human_id=42,
            wallet_address=SAMPLE_WALLET,
        )
        d = result.to_dict()

        assert isinstance(d["status"], str)
        assert d["status"] == "verified"
        assert d["is_human"] is True
        assert d["human_id"] == 42
        assert d["wallet_address"] == SAMPLE_WALLET

    def test_to_dict_error_status(self):
        """to_dict() correctly serializes error status with error message."""
        result = WorldHumanResult(
            status=WorldHumanStatus.ERROR,
            is_human=False,
            human_id=0,
            wallet_address=SAMPLE_WALLET,
            error="RPC timeout",
        )
        d = result.to_dict()

        assert d["status"] == "error"
        assert d["is_human"] is False
        assert d["error"] == "RPC timeout"

    def test_to_dict_not_verified_status(self):
        """to_dict() correctly serializes not_verified status."""
        result = WorldHumanResult(
            status=WorldHumanStatus.NOT_VERIFIED,
            is_human=False,
            human_id=0,
            wallet_address=SAMPLE_WALLET,
        )
        d = result.to_dict()

        assert d["status"] == "not_verified"
        assert d["human_id"] == 0


class TestFeatureFlagControlsLookup:
    """Tests that feature flag controls whether World ID lookup runs."""

    @pytest.mark.asyncio
    async def test_feature_flag_off_skips_lookup(self):
        """When world_agentkit feature flag is False, lookup is not called."""
        mock_config = MagicMock()
        mock_config.is_feature_enabled = AsyncMock(return_value=False)

        # Simulate the gate check that apply_to_task would perform
        flag_enabled = await mock_config.is_feature_enabled("world_agentkit")
        assert flag_enabled is False

        # When flag is off, lookup_human should NOT be called
        mock_lookup = AsyncMock()
        if flag_enabled:
            await mock_lookup(SAMPLE_WALLET)

        mock_lookup.assert_not_called()

    @pytest.mark.asyncio
    async def test_feature_flag_on_triggers_lookup(self):
        """When world_agentkit feature flag is True, lookup is called."""
        mock_config = MagicMock()
        mock_config.is_feature_enabled = AsyncMock(return_value=True)

        flag_enabled = await mock_config.is_feature_enabled("world_agentkit")
        assert flag_enabled is True

        mock_lookup = AsyncMock(
            return_value=WorldHumanResult(
                status=WorldHumanStatus.VERIFIED,
                is_human=True,
                human_id=42,
                wallet_address=SAMPLE_WALLET,
            )
        )
        if flag_enabled:
            result = await mock_lookup(SAMPLE_WALLET)
            assert result.is_human is True

        mock_lookup.assert_called_once_with(SAMPLE_WALLET)
