"""
Tests for MCP reputation tools (WS-4).

Tests:
- Feature flag gating (disabled returns appropriate error)
- em_rate_worker with valid inputs and dynamic scoring fallback
- em_rate_agent with valid inputs and authorization checks
- em_get_reputation with agent_id and wallet_address resolution
- em_check_identity for registered and unregistered wallets
- em_register_identity with gasless mode
- Missing required inputs produce validation errors
"""

import json
import os
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.erc8004

from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class FakeFeedbackResult:
    """Minimal stand-in for FeedbackResult."""

    success: bool
    transaction_hash: Optional[str] = None
    feedback_index: Optional[int] = None
    error: Optional[str] = None
    network: str = "base"


@dataclass
class FakeWorkerIdentityResult:
    """Minimal stand-in for WorkerIdentityResult."""

    class _Status:
        def __init__(self, v):
            self.value = v

    status: "_Status"
    agent_id: Optional[int] = None
    wallet_address: Optional[str] = None
    network: str = "base"
    chain_id: int = 8453
    registry_address: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def registered(cls, agent_id=42, wallet="0xabc"):
        return cls(
            status=cls._Status("registered"),
            agent_id=agent_id,
            wallet_address=wallet,
            network="base",
            chain_id=8453,
            registry_address="0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        )

    @classmethod
    def not_registered(cls, wallet="0xdef"):
        return cls(
            status=cls._Status("not_registered"),
            wallet_address=wallet,
            network="base",
            chain_id=8453,
            registry_address="0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        )

    @classmethod
    def errored(cls, error="RPC error"):
        return cls(
            status=cls._Status("error"),
            error=error,
            network="base",
        )


@dataclass
class FakeReputationSummary:
    """Minimal stand-in for ReputationSummary."""

    agent_id: int
    count: int
    summary_value: int
    summary_value_decimals: int = 0
    network: str = "base"

    @property
    def score(self) -> float:
        if self.summary_value_decimals == 0:
            return float(self.summary_value)
        return float(self.summary_value) / (10**self.summary_value_decimals)


@pytest.fixture(autouse=True)
def reset_feature_flag():
    """Reset the cached feature flag between tests."""
    import tools.reputation_tools as mod

    mod._ERC8004_MCP_TOOLS_ENABLED = None
    yield
    mod._ERC8004_MCP_TOOLS_ENABLED = None


@pytest.fixture
def mock_db():
    """Create a mock database module."""
    db = MagicMock()
    client = MagicMock()
    db.get_client.return_value = client

    # Default: get_task returns a completed task
    async def _get_task(task_id):
        return {
            "id": task_id,
            "title": "Test Task",
            "agent_id": "123",
            "status": "completed",
            "bounty_usd": 10.0,
            "executor_id": "exec-1",
            "executor": {"wallet_address": "0xworker"},
        }

    db.get_task = _get_task
    return db


# ---------------------------------------------------------------------------
# Feature flag tests
# ---------------------------------------------------------------------------


class TestFeatureFlag:
    """Tests that tools respect the feature flag."""

    @pytest.mark.asyncio
    async def test_disabled_via_env_var(self, mock_db):
        """When feature is disabled, tools return appropriate error."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "false"
        try:
            mcp = FastMCP("test")

            # Force re-import to pick up the env var
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None
            mod.register_reputation_tools(mcp, mock_db)

            # Call the tool directly via the internal registration
            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}

            result = await tools_dict["em_rate_worker"].fn(
                submission_id="a" * 36,
            )
            assert "not enabled" in result.lower()

            result = await tools_dict["em_get_reputation"].fn(agent_id=42)
            assert "not enabled" in result.lower()

            result = await tools_dict["em_check_identity"].fn(
                wallet_address="0x" + "a" * 40,
            )
            assert "not enabled" in result.lower()

        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_enabled_via_env_var(self, mock_db):
        """When feature is enabled and ERC8004 available, tools proceed."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            # The actual behavior depends on ERC8004_AVAILABLE
            assert mod._is_feature_enabled() is True
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)


# ---------------------------------------------------------------------------
# em_rate_worker tests
# ---------------------------------------------------------------------------


class TestRateWorker:
    """Tests for em_rate_worker tool."""

    @pytest.mark.asyncio
    async def test_rate_worker_submission_not_found(self, mock_db):
        """Should return error when submission not found."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            # Empty result from DB
            client = mock_db.get_client()
            client.table().select().eq().limit().execute.return_value = MagicMock(
                data=[]
            )

            mcp = FastMCP("test")
            mod.register_reputation_tools(mcp, mock_db)

            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
            result = await tools_dict["em_rate_worker"].fn(
                submission_id="a" * 36,
            )
            assert "not found" in result.lower()
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_rate_worker_with_explicit_score(self, mock_db):
        """Should use explicit score when provided."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            submission_data = {
                "id": "a" * 36,
                "task_id": "b" * 36,
                "tasks": {
                    "id": "b" * 36,
                    "title": "Test",
                    "agent_id": "123",
                    "status": "completed",
                },
                "executor": {"wallet_address": "0xworker"},
                "payment_tx": "0xtx123",
            }

            client = mock_db.get_client()
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = MagicMock(data=[submission_data])
            # Also mock the update chain for storing reputation_tx
            mock_update = MagicMock()
            mock_update.eq.return_value = mock_update
            mock_update.execute.return_value = MagicMock()
            mock_query.update = MagicMock(return_value=mock_update)
            client.table.return_value = mock_query

            feedback = FakeFeedbackResult(
                success=True,
                transaction_hash="0xfeedback123",
                network="base",
            )

            with patch.object(
                mod, "_rate_worker", new=AsyncMock(return_value=feedback)
            ):
                mcp = FastMCP("test")
                mod.register_reputation_tools(mcp, mock_db)

                tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
                result = await tools_dict["em_rate_worker"].fn(
                    submission_id="a" * 36,
                    score=85,
                    comment="Great work",
                )
                assert "85/100" in result
                assert "explicit" in result.lower()
                assert "0xfeedback123" in result
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)


# ---------------------------------------------------------------------------
# em_rate_agent tests
# ---------------------------------------------------------------------------


class TestRateAgent:
    """Tests for em_rate_agent tool."""

    @pytest.mark.asyncio
    async def test_rate_agent_task_not_found(self, mock_db):
        """Should return error when task not found."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            async def _get_task(task_id):
                return None

            mock_db.get_task = _get_task

            mcp = FastMCP("test")
            mod.register_reputation_tools(mcp, mock_db)

            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
            result = await tools_dict["em_rate_agent"].fn(
                task_id="a" * 36,
                score=80,
            )
            assert "not found" in result.lower()
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_rate_agent_invalid_status(self, mock_db):
        """Should reject rating for published/cancelled/expired tasks."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            async def _get_task(task_id):
                return {
                    "id": task_id,
                    "status": "published",
                    "agent_id": "123",
                }

            mock_db.get_task = _get_task

            mcp = FastMCP("test")
            mod.register_reputation_tools(mcp, mock_db)

            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
            result = await tools_dict["em_rate_agent"].fn(
                task_id="a" * 36,
                score=80,
            )
            assert "cannot be rated" in result.lower()
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_rate_agent_non_numeric_agent_id(self, mock_db):
        """Should reject when task agent_id is not a numeric ERC-8004 ID."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            async def _get_task(task_id):
                return {
                    "id": task_id,
                    "status": "completed",
                    "agent_id": "0xSomeWalletAddress",
                }

            mock_db.get_task = _get_task

            mcp = FastMCP("test")
            mod.register_reputation_tools(mcp, mock_db)

            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
            result = await tools_dict["em_rate_agent"].fn(
                task_id="a" * 36,
                score=80,
            )
            assert "no numeric" in result.lower()
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_rate_agent_success(self, mock_db):
        """Should successfully rate agent with valid inputs."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            async def _get_task(task_id):
                return {
                    "id": task_id,
                    "status": "completed",
                    "agent_id": "2106",
                }

            mock_db.get_task = _get_task

            # Mock submissions query for proof_tx
            client = mock_db.get_client()
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = MagicMock(
                data=[{"payment_tx": "0xpay123"}]
            )
            client.table.return_value = mock_query

            feedback = FakeFeedbackResult(
                success=True,
                transaction_hash="0xfeedback456",
                network="base",
            )

            with patch.object(mod, "_rate_agent", new=AsyncMock(return_value=feedback)):
                mcp = FastMCP("test")
                mod.register_reputation_tools(mcp, mock_db)

                tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
                result = await tools_dict["em_rate_agent"].fn(
                    task_id="a" * 36,
                    score=90,
                    comment="Excellent agent",
                )
                assert "2106" in result
                assert "90/100" in result
                assert "0xfeedback456" in result
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)


# ---------------------------------------------------------------------------
# em_get_reputation tests
# ---------------------------------------------------------------------------


class TestGetReputation:
    """Tests for em_get_reputation tool."""

    @pytest.mark.asyncio
    async def test_requires_agent_id_or_wallet(self, mock_db):
        """Should return error when neither agent_id nor wallet provided."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            mcp = FastMCP("test")
            mod.register_reputation_tools(mcp, mock_db)

            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
            result = await tools_dict["em_get_reputation"].fn()
            assert "provide either" in result.lower()
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_get_reputation_by_agent_id(self, mock_db):
        """Should return reputation when queried by agent_id."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            rep = FakeReputationSummary(
                agent_id=2106,
                count=15,
                summary_value=82,
                network="base",
            )

            mock_client = AsyncMock()
            mock_client.get_reputation = AsyncMock(return_value=rep)
            mock_client.network = "base"

            with patch.object(mod, "get_facilitator_client", return_value=mock_client):
                mcp = FastMCP("test")
                mod.register_reputation_tools(mcp, mock_db)

                tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
                result = await tools_dict["em_get_reputation"].fn(agent_id=2106)
                data = json.loads(result)
                assert data["agent_id"] == 2106
                assert data["score"] == 82.0
                assert data["rating_count"] == 15
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)


# ---------------------------------------------------------------------------
# em_check_identity tests
# ---------------------------------------------------------------------------


class TestCheckIdentity:
    """Tests for em_check_identity tool."""

    @pytest.mark.asyncio
    async def test_check_registered_wallet(self, mock_db):
        """Should return registered identity info."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            identity = FakeWorkerIdentityResult.registered(
                agent_id=42, wallet="0x" + "a" * 40
            )

            with patch.object(
                mod, "_check_worker_identity", new=AsyncMock(return_value=identity)
            ):
                mcp = FastMCP("test")
                mod.register_reputation_tools(mcp, mock_db)

                tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
                result = await tools_dict["em_check_identity"].fn(
                    wallet_address="0x" + "a" * 40,
                )
                data = json.loads(result)
                assert data["is_registered"] is True
                assert data["agent_id"] == 42
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_check_unregistered_wallet(self, mock_db):
        """Should return not registered for unknown wallets."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            identity = FakeWorkerIdentityResult.not_registered(wallet="0x" + "b" * 40)

            with patch.object(
                mod, "_check_worker_identity", new=AsyncMock(return_value=identity)
            ):
                mcp = FastMCP("test")
                mod.register_reputation_tools(mcp, mock_db)

                tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
                result = await tools_dict["em_check_identity"].fn(
                    wallet_address="0x" + "b" * 40,
                )
                data = json.loads(result)
                assert data["is_registered"] is False
                assert data["agent_id"] is None
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)


# ---------------------------------------------------------------------------
# em_register_identity tests
# ---------------------------------------------------------------------------


class TestRegisterIdentity:
    """Tests for em_register_identity tool."""

    @pytest.mark.asyncio
    async def test_register_invalid_mode(self, mock_db):
        """Should reject non-gasless modes."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            mcp = FastMCP("test")
            mod.register_reputation_tools(mcp, mock_db)

            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
            result = await tools_dict["em_register_identity"].fn(
                wallet_address="0x" + "a" * 40,
                mode="paid",
            )
            assert "only 'gasless'" in result.lower()
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_register_invalid_address(self, mock_db):
        """Should reject invalid wallet addresses."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            mcp = FastMCP("test")
            mod.register_reputation_tools(mcp, mock_db)

            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
            result = await tools_dict["em_register_identity"].fn(
                wallet_address="not-an-address",
            )
            assert "error" in result.lower()
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_register_success(self, mock_db):
        """Should register successfully with valid inputs."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            identity = FakeWorkerIdentityResult.registered(
                agent_id=999, wallet="0x" + "c" * 40
            )

            with patch.object(
                mod,
                "_register_worker_gasless",
                new=AsyncMock(return_value=identity),
            ):
                mcp = FastMCP("test")
                mod.register_reputation_tools(mcp, mock_db)

                tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
                result = await tools_dict["em_register_identity"].fn(
                    wallet_address="0x" + "c" * 40,
                    network="base",
                )
                data = json.loads(result)
                assert data["success"] is True
                assert data["agent_id"] == 999
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)


# ---------------------------------------------------------------------------
# Score range validation
# ---------------------------------------------------------------------------


class TestScoreValidation:
    """Test that invalid scores are handled."""

    @pytest.mark.asyncio
    async def test_rate_agent_score_out_of_range(self, mock_db):
        """Score must be 0-100."""
        os.environ["EM_ERC8004_MCP_TOOLS_ENABLED"] = "true"
        try:
            import tools.reputation_tools as mod

            mod._ERC8004_MCP_TOOLS_ENABLED = None

            if not mod.ERC8004_AVAILABLE:
                pytest.skip("ERC-8004 integration not available")

            async def _get_task(task_id):
                return {
                    "id": task_id,
                    "status": "completed",
                    "agent_id": "2106",
                }

            mock_db.get_task = _get_task

            mcp = FastMCP("test")
            mod.register_reputation_tools(mcp, mock_db)

            tools_dict = {t.name: t for t in mcp._tool_manager._tools.values()}
            result = await tools_dict["em_rate_agent"].fn(
                task_id="a" * 36,
                score=150,
            )
            assert "between 0 and 100" in result.lower()
        finally:
            os.environ.pop("EM_ERC8004_MCP_TOOLS_ENABLED", None)
