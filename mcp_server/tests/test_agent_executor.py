"""Tests for Agent Executor (A2A) functionality."""

import json, pytest, importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    ExecutorType, TargetExecutorType, VerificationMode,
    TaskCategory, EvidenceType,
    RegisterAgentExecutorInput, BrowseAgentTasksInput,
    AcceptAgentTaskInput, SubmitAgentWorkInput, GetAgentExecutionsInput,
)

_spec = importlib.util.spec_from_file_location(
    "agent_executor_tools",
    str(Path(__file__).parent.parent / "tools" / "agent_executor_tools.py"),
)
_aet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_aet)
capabilities_match = _aet.capabilities_match
_passes_auto_verification = _aet._passes_auto_verification
_calculate_fee_breakdown = _aet._calculate_fee_breakdown
_log_payment_event = _aet._log_payment_event
KNOWN_CAPABILITIES = _aet.KNOWN_CAPABILITIES
AgentExecutorToolsConfig = _aet.AgentExecutorToolsConfig


class TestExecutorType:
    def test_human(self): assert ExecutorType.HUMAN == "human"
    def test_agent(self): assert ExecutorType.AGENT == "agent"
    def test_invalid(self):
        with pytest.raises(ValueError): ExecutorType("robot")

class TestTargetExecutorType:
    def test_values(self):
        assert TargetExecutorType.HUMAN == "human"
        assert TargetExecutorType.AGENT == "agent"
        assert TargetExecutorType.ANY == "any"

class TestVerificationMode:
    def test_values(self):
        assert VerificationMode.MANUAL == "manual"
        assert VerificationMode.AUTO == "auto"
        assert VerificationMode.ORACLE == "oracle"

class TestDigitalCategories:
    def test_exist(self):
        assert TaskCategory.DATA_PROCESSING == "data_processing"
        assert TaskCategory.CODE_EXECUTION == "code_execution"
        assert TaskCategory.RESEARCH == "research"
    def test_physical_still_exist(self):
        assert TaskCategory.PHYSICAL_PRESENCE == "physical_presence"

class TestDigitalEvidence:
    def test_exist(self):
        assert EvidenceType.JSON_RESPONSE == "json_response"
        assert EvidenceType.CODE_OUTPUT == "code_output"
        assert EvidenceType.TEXT_REPORT == "text_report"
    def test_physical_still_exist(self):
        assert EvidenceType.PHOTO == "photo"

class TestRegisterInput:
    def test_valid(self):
        d = RegisterAgentExecutorInput(
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            capabilities=["data_processing"], display_name="Bot",
        )
        assert d.display_name == "Bot"
    def test_wallet_too_short(self):
        with pytest.raises(Exception):
            RegisterAgentExecutorInput(wallet_address="0x1234", capabilities=["x"], display_name="Bot")
    def test_empty_caps(self):
        with pytest.raises(Exception):
            RegisterAgentExecutorInput(wallet_address="0x1234567890abcdef1234567890abcdef12345678", capabilities=[], display_name="Bot")

class TestBrowseInput:
    def test_defaults(self):
        d = BrowseAgentTasksInput()
        assert d.limit == 20
        assert d.offset == 0

class TestAcceptInput:
    def test_valid(self):
        d = AcceptAgentTaskInput(task_id="a"*36, executor_id="b"*36)
        assert d.message is None

class TestSubmitInput:
    def test_valid(self):
        d = SubmitAgentWorkInput(task_id="a"*36, executor_id="b"*36, result_data={"x": 1})
        assert d.result_type == "json_response"

class TestCapabilitiesMatch:
    def test_no_req(self): assert capabilities_match(["x"], None) is True
    def test_no_req_empty(self): assert capabilities_match(["x"], []) is True
    def test_exact(self): assert capabilities_match(["a","b"], ["a","b"]) is True
    def test_superset(self): assert capabilities_match(["a","b","c"], ["a"]) is True
    def test_subset_fail(self): assert capabilities_match(["a"], ["a","b"]) is False
    def test_different(self): assert capabilities_match(["c"], ["a","b"]) is False
    def test_empty_exec(self): assert capabilities_match([], ["a"]) is False

class TestAutoVerification:
    def test_empty(self):
        ok, _ = _passes_auto_verification({"x": 1}, {})
        assert ok is True
    def test_none(self):
        ok, _ = _passes_auto_verification({"x": 1}, None)
        assert ok is True
    def test_required_present(self):
        ok, _ = _passes_auto_verification({"a": 1, "b": 2}, {"required_fields": ["a", "b"]})
        assert ok is True
    def test_required_missing(self):
        ok, r = _passes_auto_verification({"a": 1}, {"required_fields": ["a", "b"]})
        assert ok is False and "b" in r
    def test_min_length_pass(self):
        ok, _ = _passes_auto_verification({"data": "x"*100}, {"min_length": 50})
        assert ok is True
    def test_min_length_fail(self):
        ok, r = _passes_auto_verification({"a": "b"}, {"min_length": 1000})
        assert ok is False and "short" in r.lower()
    def test_type_object(self):
        ok, _ = _passes_auto_verification({"a": 1}, {"required_type": "object"})
        assert ok is True
    def test_type_mismatch(self):
        ok, _ = _passes_auto_verification({"a": 1}, {"required_type": "array"})
        assert ok is False
    def test_keywords(self):
        ok, _ = _passes_auto_verification({"r": "market growth"}, {"contains_keywords": ["market", "growth"]})
        assert ok is True
    def test_keywords_missing(self):
        ok, r = _passes_auto_verification({"r": "weather"}, {"contains_keywords": ["market"]})
        assert ok is False and "market" in r.lower()
    def test_keywords_case(self):
        ok, _ = _passes_auto_verification({"r": "MARKET GROWTH"}, {"contains_keywords": ["market"]})
        assert ok is True
    def test_combined(self):
        ok, _ = _passes_auto_verification(
            {"summary": "Market shows 15% growth", "data": [1,2,3], "conclusion": "Good"},
            {"required_fields": ["summary","data","conclusion"], "min_length": 50, "contains_keywords": ["growth"]},
        )
        assert ok is True

class TestConfig:
    def test_defaults(self):
        c = AgentExecutorToolsConfig()
        assert c.require_capability_match is True
        assert c.enforce_reputation_gate is True

    def test_disable_reputation_gate(self):
        c = AgentExecutorToolsConfig(enforce_reputation_gate=False)
        assert c.enforce_reputation_gate is False


class TestFeeBreakdown:
    """Tests for Fase 5 fee calculation integration."""

    def test_calculate_data_processing(self):
        result = _calculate_fee_breakdown(100.0, "data_processing")
        assert "fee_amount" in result
        assert "worker_amount" in result
        assert result["gross_amount"] == 100.0
        # Fee should be 13% for data_processing
        assert abs(result["fee_amount"] - 13.0) < 0.01
        assert abs(result["worker_amount"] - 87.0) < 0.01

    def test_calculate_code_execution(self):
        result = _calculate_fee_breakdown(50.0, "code_execution")
        assert result["gross_amount"] == 50.0
        # Fee should be 12% if fees module loads, 13% fallback
        assert 6.0 <= result["fee_amount"] <= 6.5
        assert 43.5 <= result["worker_amount"] <= 44.0

    def test_calculate_research(self):
        result = _calculate_fee_breakdown(200.0, "research")
        assert result["gross_amount"] == 200.0
        # Fee should be 12-13% depending on import path
        assert 24.0 <= result["fee_amount"] <= 26.0

    def test_fallback_unknown_category(self):
        result = _calculate_fee_breakdown(100.0, "unknown_category_xyz")
        # Should fallback to 13% default
        assert "fee_amount" in result
        assert result["gross_amount"] == 100.0

    def test_small_bounty(self):
        result = _calculate_fee_breakdown(1.0, "simple_action")
        assert result["worker_amount"] > 0
        assert result["fee_amount"] >= 0


class TestPaymentEventLogging:
    """Tests for audit trail logging."""

    def test_log_event_success(self):
        """Mock client that accepts inserts."""
        class MockTable:
            def insert(self, data):
                self._inserted = data
                return self
            def execute(self):
                return type("R", (), {"data": [self._inserted]})()

        class MockClient:
            def table(self, name):
                assert name == "payment_events"
                return MockTable()

        # Should not raise
        _log_payment_event(MockClient(), "task-123", "auto_approved", {"test": True})

    def test_log_event_failure_doesnt_raise(self):
        """Payment event logging should never crash the main flow."""
        class MockClient:
            def table(self, name):
                raise Exception("DB down")

        # Should NOT raise — just logs a warning
        _log_payment_event(MockClient(), "task-123", "auto_approved", {})

class TestKnownCaps:
    def test_core(self):
        assert "data_processing" in KNOWN_CAPABILITIES
        assert "web_research" in KNOWN_CAPABILITIES
    def test_is_set(self):
        assert isinstance(KNOWN_CAPABILITIES, set)

class TestMigration031:
    def test_exists(self):
        p = Path(__file__).parent.parent.parent / "supabase" / "migrations" / "031_agent_executor_support.sql"
        assert p.exists()
    def test_content(self):
        p = Path(__file__).parent.parent.parent / "supabase" / "migrations" / "031_agent_executor_support.sql"
        c = p.read_text()
        for kw in ["executor_type", "capabilities", "target_executor_type", "verification_mode", "data_processing"]:
            assert kw in c, f"Missing: {kw}"
