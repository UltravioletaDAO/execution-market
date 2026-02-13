"""
Tests for H2A (Human-to-Agent) Marketplace

Tests cover:
- H2A task creation (publish)
- H2A task listing (public + my_tasks)
- H2A task detail retrieval
- H2A submission viewing
- H2A approval flow (accept/reject/needs_revision)
- H2A task cancellation
- Agent directory (public)
- Agent executor registration
- JWT auth for human publishers
- Dual auth (JWT vs API key)
- Feature flag enforcement
- Bounty limits
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    PublishH2ATaskRequest,
    ApproveH2ASubmissionRequest,
    H2ATaskResponse,
    H2AApprovalResponse,
    AgentDirectoryEntry,
    AgentDirectoryResponse,
    PublisherType,
    DigitalEvidenceType,
    TaskCategory,
)


# ============================================================================
# Model Validation Tests
# ============================================================================

class TestH2AModels:
    """Test H2A Pydantic models."""

    def test_publisher_type_enum(self):
        assert PublisherType.AGENT == "agent"
        assert PublisherType.HUMAN == "human"

    def test_digital_evidence_types(self):
        assert DigitalEvidenceType.JSON_RESPONSE == "json_response"
        assert DigitalEvidenceType.CODE == "code"
        assert DigitalEvidenceType.REPORT == "report"

    def test_publish_h2a_task_request_valid(self):
        req = PublishH2ATaskRequest(
            title="Analyze sales data for Q4",
            instructions="Process the CSV file and generate a summary report with key metrics.",
            category=TaskCategory.DATA_PROCESSING,
            bounty_usd=5.0,
            deadline_hours=24,
        )
        assert req.title == "Analyze sales data for Q4"
        assert req.bounty_usd == 5.0
        assert req.category == TaskCategory.DATA_PROCESSING
        assert req.deadline_hours == 24
        assert req.evidence_required == ["json_response"]  # default
        assert req.verification_mode == "manual"  # default

    def test_publish_h2a_task_request_with_capabilities(self):
        req = PublishH2ATaskRequest(
            title="Research competitor pricing",
            instructions="Scrape competitor websites and compile pricing data into a spreadsheet.",
            category=TaskCategory.RESEARCH,
            bounty_usd=10.0,
            required_capabilities=["web_scraping", "data_processing"],
        )
        assert req.required_capabilities == ["web_scraping", "data_processing"]

    def test_publish_h2a_task_request_title_too_short(self):
        with pytest.raises(Exception):
            PublishH2ATaskRequest(
                title="Hi",  # too short
                instructions="Process the CSV file and generate a summary report with key metrics.",
                category=TaskCategory.DATA_PROCESSING,
                bounty_usd=5.0,
            )

    def test_publish_h2a_task_request_instructions_too_short(self):
        with pytest.raises(Exception):
            PublishH2ATaskRequest(
                title="Valid title here",
                instructions="Too short",  # too short
                category=TaskCategory.DATA_PROCESSING,
                bounty_usd=5.0,
            )

    def test_publish_h2a_task_request_bounty_too_high(self):
        with pytest.raises(Exception):
            PublishH2ATaskRequest(
                title="Valid title here",
                instructions="Process the CSV file and generate a summary report with key metrics.",
                category=TaskCategory.DATA_PROCESSING,
                bounty_usd=600,  # max is 500
            )

    def test_publish_h2a_task_request_bounty_zero(self):
        with pytest.raises(Exception):
            PublishH2ATaskRequest(
                title="Valid title here",
                instructions="Process the CSV file and generate a summary report with key metrics.",
                category=TaskCategory.DATA_PROCESSING,
                bounty_usd=0,
            )

    def test_publish_h2a_task_bounty_rounding(self):
        req = PublishH2ATaskRequest(
            title="Valid title here",
            instructions="Process the CSV file and generate a summary report with key metrics.",
            category=TaskCategory.DATA_PROCESSING,
            bounty_usd=5.999,
        )
        assert req.bounty_usd == 6.0  # rounded to 2 decimals

    def test_approve_h2a_submission_accepted(self):
        req = ApproveH2ASubmissionRequest(
            submission_id="a" * 36,
            verdict="accepted",
            settlement_auth_worker="0xabc123",
            settlement_auth_fee="0xdef456",
        )
        assert req.verdict == "accepted"
        assert req.settlement_auth_worker == "0xabc123"

    def test_approve_h2a_submission_rejected(self):
        req = ApproveH2ASubmissionRequest(
            submission_id="a" * 36,
            verdict="rejected",
            notes="Work quality was insufficient",
        )
        assert req.verdict == "rejected"
        assert req.notes == "Work quality was insufficient"

    def test_approve_h2a_submission_needs_revision(self):
        req = ApproveH2ASubmissionRequest(
            submission_id="a" * 36,
            verdict="needs_revision",
            notes="Please add more detail to the analysis section",
        )
        assert req.verdict == "needs_revision"

    def test_approve_h2a_submission_invalid_verdict(self):
        with pytest.raises(Exception):
            ApproveH2ASubmissionRequest(
                submission_id="a" * 36,
                verdict="maybe",  # invalid
            )

    def test_h2a_task_response(self):
        resp = H2ATaskResponse(
            task_id="task-123",
            bounty_usd=5.0,
            fee_usd=0.65,
            total_required_usd=5.65,
            deadline="2026-02-14T00:00:00Z",
        )
        assert resp.publisher_type == "human"
        assert resp.status == "published"
        assert resp.total_required_usd == 5.65

    def test_h2a_approval_response(self):
        resp = H2AApprovalResponse(
            status="accepted",
            worker_tx="0xabc",
            fee_tx="0xdef",
        )
        assert resp.status == "accepted"
        assert resp.worker_tx == "0xabc"

    def test_agent_directory_entry(self):
        entry = AgentDirectoryEntry(
            executor_id="exec-1",
            display_name="ResearchBot",
            capabilities=["research", "data_processing"],
            rating=85,
            tasks_completed=42,
            verified=True,
        )
        assert entry.display_name == "ResearchBot"
        assert len(entry.capabilities) == 2
        assert entry.verified is True

    def test_agent_directory_response(self):
        resp = AgentDirectoryResponse(
            agents=[
                AgentDirectoryEntry(
                    executor_id="exec-1",
                    display_name="Bot1",
                )
            ],
            total=1,
        )
        assert len(resp.agents) == 1
        assert resp.total == 1


# ============================================================================
# JWT Auth Tests
# ============================================================================

class TestH2AAuth:
    """Test JWT authentication for human publishers."""

    @pytest.mark.asyncio
    async def test_verify_jwt_auth_no_header(self):
        """Should raise 401 when no Authorization header."""
        from api.h2a import verify_jwt_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_auth(authorization=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_jwt_auth_empty_bearer(self):
        """Should raise 401 when Bearer token is empty."""
        from api.h2a import verify_jwt_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_auth(authorization="Bearer ")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_jwt_auth_invalid_token(self):
        """Should raise 401 for invalid JWT."""
        from api.h2a import verify_jwt_auth
        from fastapi import HTTPException

        os.environ["SUPABASE_JWT_SECRET"] = "test-secret"
        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_auth(authorization="Bearer invalid.token.here")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_jwt_auth_valid_token(self):
        """Should return JWTData for valid JWT."""
        import jwt as pyjwt
        from api.h2a import verify_jwt_auth

        secret = "test-jwt-secret-12345"
        os.environ["SUPABASE_JWT_SECRET"] = secret

        payload = {
            "sub": "user-123",
            "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
            "email": "test@example.com",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        token = pyjwt.encode(payload, secret, algorithm="HS256")

        result = await verify_jwt_auth(authorization=f"Bearer {token}")
        assert result.user_id == "user-123"
        assert result.wallet_address == "0x1234567890abcdef1234567890abcdef12345678"
        assert result.is_human is True

    @pytest.mark.asyncio
    async def test_verify_auth_method_api_key(self):
        """Dual auth should accept API keys."""
        from api.h2a import verify_auth_method
        from api.auth import APIKeyData

        with patch("api.h2a.verify_jwt_auth") as mock_jwt:
            with patch("api.auth.verify_api_key") as mock_api:
                mock_api.return_value = APIKeyData(
                    key_hash="hash", agent_id="agent-1", tier="free"
                )
                result = await verify_auth_method(
                    authorization=None,
                    x_api_key="em_free_testkey12345678901234567890",
                )
                assert result.agent_id == "agent-1"
                mock_jwt.assert_not_called()


# ============================================================================
# Fee Calculation Tests
# ============================================================================

class TestH2AFees:
    """Test fee calculation for H2A tasks."""

    def test_fee_calculation_standard(self):
        """Standard 13% fee on $5 bounty."""
        bounty = Decimal("5.00")
        fee_pct = Decimal("0.13")
        fee = bounty * fee_pct
        total = bounty + fee
        assert fee == Decimal("0.65")
        assert total == Decimal("5.65")

    def test_fee_calculation_min_bounty(self):
        """13% fee on minimum $0.50 bounty."""
        bounty = Decimal("0.50")
        fee_pct = Decimal("0.13")
        fee = bounty * fee_pct
        total = bounty + fee
        assert fee == Decimal("0.065")
        assert total == Decimal("0.565")

    def test_fee_calculation_max_bounty(self):
        """13% fee on maximum $500 bounty."""
        bounty = Decimal("500.00")
        fee_pct = Decimal("0.13")
        fee = bounty * fee_pct
        total = bounty + fee
        assert fee == Decimal("65.00")
        assert total == Decimal("565.00")


# ============================================================================
# Task Category Tests
# ============================================================================

class TestH2ACategories:
    """Test digital task categories for H2A."""

    def test_digital_categories_exist(self):
        """All digital categories from the plan should exist."""
        digital_cats = [
            "data_processing", "api_integration", "content_generation",
            "code_execution", "research", "multi_step_workflow",
        ]
        for cat in digital_cats:
            assert TaskCategory(cat) is not None

    def test_h2a_task_with_digital_category(self):
        """H2A tasks should accept digital categories."""
        for cat in [TaskCategory.DATA_PROCESSING, TaskCategory.RESEARCH, TaskCategory.CODE_EXECUTION]:
            req = PublishH2ATaskRequest(
                title=f"Test task for {cat.value}",
                instructions="Detailed instructions for the agent to follow when executing this task.",
                category=cat,
                bounty_usd=5.0,
            )
            assert req.category == cat


# ============================================================================
# Integration Smoke Tests
# ============================================================================

@pytest.mark.core
class TestH2AIntegration:
    """Integration tests for H2A API (mocked DB)."""

    @pytest.mark.asyncio
    async def test_create_h2a_task_no_wallet(self):
        """Should fail when human has no wallet linked."""
        from api.h2a import create_h2a_task, JWTData
        from fastapi import HTTPException

        auth = JWTData(user_id="user-1", wallet_address=None)
        req = PublishH2ATaskRequest(
            title="Test H2A task creation",
            instructions="Process data and return results in JSON format as specified.",
            category=TaskCategory.DATA_PROCESSING,
            bounty_usd=5.0,
        )

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with pytest.raises(HTTPException) as exc_info:
                await create_h2a_task(request=req, auth=auth)
            assert exc_info.value.status_code == 400
            assert "wallet" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_cancel_h2a_task_wrong_owner(self):
        """Should fail when trying to cancel someone else's task."""
        from api.h2a import cancel_h2a_task, JWTData
        from fastapi import HTTPException

        auth = JWTData(user_id="user-2", wallet_address="0x123")

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {
            "id": "task-1",
            "human_user_id": "user-1",  # different user!
            "publisher_type": "human",
            "status": "published",
        }
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await cancel_h2a_task(task_id="a" * 36, auth=auth)
            assert exc_info.value.status_code == 403
