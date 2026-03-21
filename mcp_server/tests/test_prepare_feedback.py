"""
Tests for the prepare-feedback + confirm-feedback endpoints.

These endpoints enable trustless worker -> agent reputation:
the worker signs giveFeedback() directly from their wallet.
"""

import importlib
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.erc8004


def _mock_request():
    """Create a mock FastAPI Request object."""
    mock = MagicMock()
    mock.url.path = "/test"
    return mock


# ---------------------------------------------------------------------------
# Module stubbing — ensure api.reputation can be imported cleanly.
#
# api.reputation imports from:
#   - supabase_client (as db)
#   - integrations.erc8004 (multiple exports)
#   - .auth (verify_api_key_if_required, APIKeyData)
#
# We stub the integrations.erc8004 package with all expected attributes so
# the try/except block in api.reputation succeeds and ERC8004_AVAILABLE=True.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

_PACKAGES = {
    "integrations": str(Path(__file__).parent.parent / "integrations"),
    "integrations.erc8004": str(
        Path(__file__).parent.parent / "integrations" / "erc8004"
    ),
    "integrations.x402": str(Path(__file__).parent.parent / "integrations" / "x402"),
}
for _pkg, _pkg_path in _PACKAGES.items():
    if _pkg not in sys.modules:
        _stub = ModuleType(_pkg)
        _stub.__path__ = [_pkg_path]
        _stub.__package__ = _pkg
        sys.modules[_pkg] = _stub

# Add ALL attributes that api.reputation imports from integrations.erc8004
_erc8004_pkg = sys.modules["integrations.erc8004"]
_erc8004_pkg.get_facilitator_client = MagicMock()
_erc8004_pkg.get_em_reputation = AsyncMock()
_erc8004_pkg.get_em_identity = AsyncMock()
_erc8004_pkg.rate_worker = AsyncMock()
_erc8004_pkg.rate_agent = AsyncMock()
_erc8004_pkg.get_agent_info = AsyncMock(return_value=None)
_erc8004_pkg.get_agent_reputation = AsyncMock()
_erc8004_pkg.EM_AGENT_ID = 2106
_erc8004_pkg.ERC8004_CONTRACTS = {
    "base": {
        "reputation_registry": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
        "chain_id": 8453,
    }
}
_erc8004_pkg.ERC8004_NETWORK = "base"
_erc8004_pkg.ERC8004_SUPPORTED_NETWORKS = ["base"]
_erc8004_pkg.FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"
# Types used by imports
_erc8004_pkg.ERC8004FacilitatorClient = MagicMock()
_erc8004_pkg.AgentIdentity = MagicMock()
_erc8004_pkg.FeedbackResult = MagicMock()
_erc8004_pkg.ReputationSummary = MagicMock()
_erc8004_pkg.give_feedback_direct = AsyncMock()
_erc8004_pkg.verify_agent_identity = AsyncMock()
_erc8004_pkg.clear_identity_cache = MagicMock()
_erc8004_pkg.check_worker_identity = AsyncMock()
_erc8004_pkg.register_worker_gasless = AsyncMock()
_erc8004_pkg.build_worker_registration_tx = AsyncMock()
_erc8004_pkg.confirm_worker_registration = AsyncMock()
_erc8004_pkg.update_executor_identity = AsyncMock()
_erc8004_pkg.WorkerIdentityStatus = MagicMock()
_erc8004_pkg.WorkerIdentityResult = MagicMock()
_erc8004_pkg.RegistrationTxData = MagicMock()
_erc8004_pkg.IDENTITY_REGISTRY_MAINNET = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
_erc8004_pkg.IDENTITY_REGISTRY_TESTNET = "0x8004A818BFB912233c491871b3d84c89A494BD9e"
_erc8004_pkg.ERC8004Registry = MagicMock()
_erc8004_pkg.ReputationManager = MagicMock()

_LEAF_STUBS = {
    "integrations.erc8004.register": {"ERC8004Registry": None},
    "integrations.erc8004.reputation": {"ReputationManager": None},
    "integrations.erc8004.identity": {
        "verify_agent_identity": None,
        "check_worker_identity": None,
        "register_worker_gasless": None,
        "update_executor_identity": None,
    },
    "integrations.erc8004.feedback_store": {
        "persist_and_hash_feedback": AsyncMock(
            return_value=("https://cdn/feedback.json", "0x" + "aa" * 32)
        ),
        "get_feedback_document": AsyncMock(return_value=None),
    },
    "integrations.erc8004.facilitator_client": {
        "ERC8004FacilitatorClient": MagicMock(),
        "get_facilitator_client": MagicMock(),
        "AgentIdentity": MagicMock(),
        "FeedbackResult": MagicMock(),
        "ReputationSummary": MagicMock(),
        "get_em_reputation": AsyncMock(),
        "get_em_identity": AsyncMock(),
        "rate_worker": AsyncMock(),
        "rate_agent": AsyncMock(),
        "get_agent_info": AsyncMock(return_value=None),
        "get_agent_reputation": AsyncMock(),
        "EM_AGENT_ID": 2106,
        "ERC8004_CONTRACTS": {
            "base": {
                "reputation_registry": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
                "chain_id": 8453,
            }
        },
        "ERC8004_NETWORK": "base",
        "ERC8004_SUPPORTED_NETWORKS": ["base"],
        "FACILITATOR_URL": "https://facilitator.ultravioletadao.xyz",
    },
    "integrations.erc8004.direct_reputation": {
        "give_feedback_direct": AsyncMock(),
        "REPUTATION_REGISTRY_ADDRESS": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
        "GIVE_FEEDBACK_ABI": [],
    },
    "integrations.x402.sdk_client": {
        "NETWORK_CONFIG": {
            "base": {
                "chain_id": 8453,
                "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            },
        },
    },
}
for _mod_name, _attrs in _LEAF_STUBS.items():
    if _mod_name not in sys.modules:
        _stub = ModuleType(_mod_name)
        for _k, _v in _attrs.items():
            setattr(_stub, _k, _v)
        sys.modules[_mod_name] = _stub

# Force-reload api.reputation so it picks up our stubs
if "api.reputation" in sys.modules:
    importlib.reload(sys.modules["api.reputation"])


# ============================================================================
# Tests
# ============================================================================


class TestPrepareFeedback:
    """Tests for POST /reputation/prepare-feedback."""

    @pytest.fixture
    def mock_task(self):
        return {
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "status": "completed",
            "agent_id": "test-agent",
            "executor_id": "exec-1",
            "executor": {
                "id": "exec-1",
                "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
            },
        }

    @pytest.fixture
    def mock_agent_identity(self):
        identity = MagicMock()
        identity.agent_id = 2106
        identity.owner = "YOUR_PLATFORM_WALLET"
        identity.agent_uri = "https://execution.market/agent-card.json"
        return identity

    @pytest.mark.asyncio
    async def test_prepare_feedback_happy_path(self, mock_task, mock_agent_identity):
        """Successful prepare returns all giveFeedback parameters."""
        with (
            patch("api.reputation.db") as mock_db,
            patch(
                "api.reputation.get_agent_info",
                new_callable=AsyncMock,
                return_value=mock_agent_identity,
            ),
            patch(
                "api.reputation.ERC8004_AVAILABLE",
                True,
            ),
            patch(
                "api.reputation.ERC8004_CONTRACTS",
                {
                    "base": {
                        "reputation_registry": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
                        "chain_id": 8453,
                    }
                },
            ),
            patch("api.reputation.ERC8004_NETWORK", "base"),
        ):
            mock_db.get_task = AsyncMock(return_value=mock_task)
            mock_client = MagicMock()
            mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            mock_db.get_client.return_value = mock_client

            from api.reputation import prepare_feedback_endpoint, PrepareFeedbackRequest

            request = PrepareFeedbackRequest(
                agent_id=2106,
                task_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                score=80,
                comment="Great agent!",
                worker_address="0x1234567890abcdef1234567890abcdef12345678",
            )

            result = await prepare_feedback_endpoint(
                raw_request=_mock_request(),
                request=request,
                worker_auth=None,
            )

        assert result.agent_id == 2106
        assert result.value == 80
        assert result.chain_id == 8453
        assert result.tag1 == "agent_rating"
        assert result.tag2 == "execution-market"
        assert result.prepare_id  # Should have a UUID
        assert result.contract_address == "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

    @pytest.mark.asyncio
    async def test_prepare_feedback_task_not_found(self):
        """Returns 404 when task doesn't exist."""
        with (
            patch("api.reputation.db") as mock_db,
            patch("api.reputation.ERC8004_AVAILABLE", True),
        ):
            mock_db.get_task = AsyncMock(return_value=None)

            from api.reputation import prepare_feedback_endpoint, PrepareFeedbackRequest

            request = PrepareFeedbackRequest(
                agent_id=2106,
                task_id="aaaaaaaa-bbbb-cccc-dddd-000000000000",
                score=80,
                worker_address="0x1234567890abcdef1234567890abcdef12345678",
            )

            with pytest.raises(Exception) as exc_info:
                await prepare_feedback_endpoint(
                    raw_request=_mock_request(),
                    request=request,
                    worker_auth=None,
                )
            assert "404" in str(exc_info.value.status_code)

    @pytest.mark.asyncio
    async def test_prepare_feedback_wrong_worker(self, mock_task, mock_agent_identity):
        """Returns 403 when worker address doesn't match executor."""
        with (
            patch("api.reputation.db") as mock_db,
            patch(
                "api.reputation.get_agent_info",
                new_callable=AsyncMock,
                return_value=mock_agent_identity,
            ),
            patch("api.reputation.ERC8004_AVAILABLE", True),
        ):
            mock_db.get_task = AsyncMock(return_value=mock_task)

            from api.reputation import prepare_feedback_endpoint, PrepareFeedbackRequest

            request = PrepareFeedbackRequest(
                agent_id=2106,
                task_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                score=80,
                worker_address="0xDEADDEADDEADDEADDEADDEADDEADDEADDEADDEAD",
            )

            with pytest.raises(Exception) as exc_info:
                await prepare_feedback_endpoint(
                    raw_request=_mock_request(),
                    request=request,
                    worker_auth=None,
                )
            assert "403" in str(exc_info.value.status_code)

    @pytest.mark.asyncio
    async def test_prepare_feedback_invalid_status(self, mock_agent_identity):
        """Returns 409 for tasks that can't be rated."""
        task = {
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "status": "published",
            "executor": {
                "wallet_address": "0x1234567890abcdef1234567890abcdef12345678"
            },
        }
        with (
            patch("api.reputation.db") as mock_db,
            patch("api.reputation.ERC8004_AVAILABLE", True),
        ):
            mock_db.get_task = AsyncMock(return_value=task)

            from api.reputation import prepare_feedback_endpoint, PrepareFeedbackRequest

            request = PrepareFeedbackRequest(
                agent_id=2106,
                task_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                score=80,
                worker_address="0x1234567890abcdef1234567890abcdef12345678",
            )

            with pytest.raises(Exception) as exc_info:
                await prepare_feedback_endpoint(
                    raw_request=_mock_request(),
                    request=request,
                    worker_auth=None,
                )
            assert "409" in str(exc_info.value.status_code)

    @pytest.mark.asyncio
    async def test_prepare_feedback_agent_not_found(self, mock_task):
        """Returns 404 when agent doesn't exist on-chain."""
        with (
            patch("api.reputation.db") as mock_db,
            patch(
                "api.reputation.get_agent_info",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("api.reputation.ERC8004_AVAILABLE", True),
        ):
            mock_db.get_task = AsyncMock(return_value=mock_task)

            from api.reputation import prepare_feedback_endpoint, PrepareFeedbackRequest

            request = PrepareFeedbackRequest(
                agent_id=9999,
                task_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                score=80,
                worker_address="0x1234567890abcdef1234567890abcdef12345678",
            )

            with pytest.raises(Exception) as exc_info:
                await prepare_feedback_endpoint(
                    raw_request=_mock_request(),
                    request=request,
                    worker_auth=None,
                )
            assert "404" in str(exc_info.value.status_code)


class TestConfirmFeedback:
    """Tests for POST /reputation/confirm-feedback."""

    @pytest.mark.asyncio
    async def test_confirm_feedback_happy_path(self):
        """Successful confirm stores tx_hash."""
        with (
            patch("api.reputation.db") as mock_db,
            patch("api.reputation.ERC8004_AVAILABLE", True),
            patch("api.reputation.ERC8004_NETWORK", "base"),
        ):
            mock_client = MagicMock()
            mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            mock_db.get_client.return_value = mock_client

            from api.reputation import (
                confirm_feedback_endpoint,
                ConfirmFeedbackRequest,
            )

            request = ConfirmFeedbackRequest(
                prepare_id="some-uuid",
                tx_hash="0x" + "ab" * 32,
                task_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            )

            result = await confirm_feedback_endpoint(
                raw_request=_mock_request(),
                request=request,
                worker_auth=None,
            )

        assert result.success is True
        assert result.transaction_hash == "0x" + "ab" * 32
        assert result.network == "base"

    @pytest.mark.asyncio
    async def test_confirm_feedback_stores_in_db(self):
        """Confirm stores tx_hash in both feedback_documents and submissions."""
        with (
            patch("api.reputation.db") as mock_db,
            patch("api.reputation.ERC8004_AVAILABLE", True),
            patch("api.reputation.ERC8004_NETWORK", "base"),
        ):
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            mock_client.table.return_value = mock_table
            mock_db.get_client.return_value = mock_client

            from api.reputation import (
                confirm_feedback_endpoint,
                ConfirmFeedbackRequest,
            )

            tx = "0x" + "cd" * 32
            request = ConfirmFeedbackRequest(
                prepare_id="some-uuid",
                tx_hash=tx,
                task_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            )

            await confirm_feedback_endpoint(
                raw_request=_mock_request(),
                request=request,
                worker_auth=None,
            )

            # Should have called table() at least twice (feedback_documents + submissions)
            assert mock_client.table.call_count >= 2


class TestRateAgentPendingSignature:
    """Tests that rate_agent() returns pending when no relay key (no Facilitator fallback)."""

    @pytest.mark.asyncio
    async def test_rate_agent_returns_pending(self):
        """rate_agent() without relay key returns pending_worker_signature=True."""
        _fc_mod = importlib.import_module("integrations.erc8004.facilitator_client")
        importlib.reload(_fc_mod)

        with patch(
            "integrations.erc8004.feedback_store.persist_and_hash_feedback",
            new_callable=AsyncMock,
            return_value=("https://cdn/feedback.json", "0x" + "aa" * 32),
        ):
            result = await _fc_mod.rate_agent(
                agent_id=2106,
                task_id="test-task-1",
                score=90,
            )

        assert result.success is True
        assert result.transaction_hash is None
        # No Facilitator fallback — tx hash is None

    @pytest.mark.asyncio
    async def test_rate_agent_no_relay_key_no_facilitator(self):
        """rate_agent() without relay key does NOT call Facilitator (trust violation)."""
        import os

        os.environ.pop("EM_REPUTATION_RELAY_KEY", None)

        _fc_mod = importlib.import_module("integrations.erc8004.facilitator_client")
        importlib.reload(_fc_mod)

        mock_client = AsyncMock()

        with (
            patch(
                "integrations.erc8004.feedback_store.persist_and_hash_feedback",
                new_callable=AsyncMock,
                return_value=("https://cdn/feedback.json", "0xhash"),
            ),
            patch.object(
                _fc_mod,
                "get_facilitator_client",
                return_value=mock_client,
            ),
        ):
            result = await _fc_mod.rate_agent(
                agent_id=2106,
                task_id="test-task-2",
                score=85,
            )

        assert result.success is True
        assert result.transaction_hash is None
        # Facilitator should NOT have been called
        mock_client.submit_feedback.assert_not_called()
