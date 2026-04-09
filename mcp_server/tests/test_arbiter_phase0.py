"""
Phase 0 GR-0.2 — Arbiter kill-switch tests.

Covers the hard env-var gates added during the 2026-04-07 security
remediation:

    EM_AAAS_ENABLED                       -> POST /arbiter/verify + GET /arbiter/status
    EM_ARBITER_AUTO_RELEASE_ENABLED       -> processor.process_arbiter_verdict auto branch

Both flags default to false. When off, the AaaS endpoints return HTTP 503
and the processor refuses to auto-release/auto-refund even when the
PlatformConfig master switch (feature.arbiter_enabled) is ON.

Also verifies the canonical skill.md has been stripped of "dual-inference"
marketing language (the file is the one shipped to external agents) and
that the backend copy stays in sync.

Run:
    pytest tests/test_arbiter_phase0.py -v

Linked audit items: AI-001, AI-002, AI-003, AI-004, AI-005, AI-006, AI-013.
Linked plan:        docs/reports/security-audit-2026-04-07/40_FINAL_CONSOLIDATED_PLAN.md
"""

import re
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.arbiter


# ---------------------------------------------------------------------------
# Stub installation (mirrors test_arbiter_phase5.py + test_arbiter_integration.py)
# ---------------------------------------------------------------------------
#
# processor.py lazy-imports api.routers._helpers + integrations.x402.payment_dispatcher.
# arbiter_public.py imports api.auth + integrations.arbiter.service. We mock
# enough of those so the arbiter modules can be imported without touching
# real DBs, the Facilitator, or web3.


_STUB_MODULES_P0 = [
    "api",
    "api.routers",
    "api.routers._helpers",
    "api.routers.arbiter_public",
    "api.auth",
    "events.bus",
    "integrations.x402.payment_dispatcher",
    "supabase_client",
]


def _make_fake_supabase_client():
    """Minimal supabase client stub — .table().update/select/insert/eq chain."""
    table = MagicMock()
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{}]
    )
    table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "dispute-phase0-mock"}]
    )
    select_resp = MagicMock(data=[{"arbiter_verdict": None}])
    table.select.return_value.eq.return_value.execute.return_value = select_resp

    client = MagicMock()
    client.table.return_value = table
    return client


def _install_stubs_phase0():
    """Install sys.modules stubs for the Phase 0 tests.

    Scoped to this module via an autouse fixture below.
    """
    # --- api.routers._helpers ---
    fake_settle = AsyncMock(return_value={"payment_tx": "0xPHASE0_SETTLE"})
    fake_dispatch_webhook = AsyncMock()

    existing_helpers = sys.modules.get("api.routers._helpers")
    if existing_helpers is not None:
        existing_helpers._settle_submission_payment = fake_settle
        existing_helpers.dispatch_webhook = fake_dispatch_webhook
        fake_helpers = existing_helpers
    else:
        fake_helpers = types.ModuleType("api.routers._helpers")
        fake_helpers._settle_submission_payment = fake_settle
        fake_helpers.dispatch_webhook = fake_dispatch_webhook
        fake_routers_pkg = types.ModuleType("api.routers")
        fake_routers_pkg.__path__ = []
        fake_routers_pkg._helpers = fake_helpers
        fake_api_pkg = types.ModuleType("api")
        fake_api_pkg.__path__ = []
        fake_api_pkg.routers = fake_routers_pkg
        sys.modules["api"] = fake_api_pkg
        sys.modules["api.routers"] = fake_routers_pkg
        sys.modules["api.routers._helpers"] = fake_helpers

    # --- api.auth ---
    fake_auth = types.ModuleType("api.auth")

    class _AgentAuth:
        def __init__(
            self,
            agent_id: str = "phase0-test",
            wallet_address: str = None,
            auth_method: str = "mcp_tool",
            tier: str = "free",
            chain_id: int = None,
            organization_id: str = None,
            erc8004_registered: bool = False,
            erc8004_agent_id: int = None,
        ):
            self.agent_id = agent_id
            self.wallet_address = wallet_address
            self.auth_method = auth_method
            self.tier = tier
            self.chain_id = chain_id
            self.organization_id = organization_id
            self.erc8004_registered = erc8004_registered
            self.erc8004_agent_id = erc8004_agent_id

    async def _verify_agent_auth():
        return _AgentAuth()

    fake_auth.AgentAuth = _AgentAuth
    fake_auth.verify_agent_auth = _verify_agent_auth
    sys.modules.setdefault("api.auth", fake_auth)

    # --- events.bus ---
    fake_event_bus_instance = MagicMock()
    fake_event_bus_instance.publish = AsyncMock()

    existing_events_bus = sys.modules.get("events.bus")
    if existing_events_bus is not None:
        existing_events_bus.get_event_bus = lambda: fake_event_bus_instance
    else:

        class _FakeEventBus:
            pass

        fake_bus_module = types.ModuleType("events.bus")
        fake_bus_module.get_event_bus = lambda: fake_event_bus_instance
        fake_bus_module.EventBus = _FakeEventBus
        sys.modules["events.bus"] = fake_bus_module

    # --- x402 payment dispatcher ---
    fake_dispatcher = MagicMock()
    fake_dispatcher.refund_trustless_escrow = AsyncMock(
        return_value={"success": True, "tx_hash": "0xPHASE0_REFUND"}
    )

    existing_pd = sys.modules.get("integrations.x402.payment_dispatcher")
    if existing_pd is not None:
        existing_pd.get_dispatcher = lambda: fake_dispatcher
        existing_pd.get_payment_dispatcher = lambda: fake_dispatcher
    else:
        fake_pd_module = types.ModuleType("integrations.x402.payment_dispatcher")
        fake_pd_module.get_dispatcher = lambda: fake_dispatcher
        fake_pd_module.get_payment_dispatcher = lambda: fake_dispatcher
        sys.modules["integrations.x402.payment_dispatcher"] = fake_pd_module

    # --- supabase_client ---
    existing_db = sys.modules.get("supabase_client")
    if existing_db is not None:
        existing_db.get_client = lambda: _make_fake_supabase_client()
    else:
        fake_db = types.ModuleType("supabase_client")
        fake_db.get_client = lambda: _make_fake_supabase_client()
        sys.modules["supabase_client"] = fake_db

    # --- api.routers.arbiter_public (loaded by file path to bypass api/__init__) ---
    if "api.routers.arbiter_public" not in sys.modules:
        import importlib.util

        repo_root = Path(__file__).resolve().parent.parent  # mcp_server/
        arbiter_public_path = repo_root / "api" / "routers" / "arbiter_public.py"
        spec = importlib.util.spec_from_file_location(
            "api.routers.arbiter_public", arbiter_public_path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["api.routers.arbiter_public"] = module
        spec.loader.exec_module(module)

    return fake_helpers, fake_event_bus_instance, fake_dispatcher


_FAKE_HELPERS_P0 = None
_FAKE_EVENT_BUS_P0 = None
_FAKE_DISPATCHER_P0 = None


@pytest.fixture(scope="module", autouse=True)
def _phase0_stubs():
    """Install stubs for the duration of this test module and restore on teardown."""
    global _FAKE_HELPERS_P0, _FAKE_EVENT_BUS_P0, _FAKE_DISPATCHER_P0

    saved_modules = {name: sys.modules.get(name) for name in _STUB_MODULES_P0}
    saved_attrs = {}

    def _save_attr(mod_name, attr_name):
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, attr_name):
            saved_attrs[(mod_name, attr_name)] = getattr(mod, attr_name)

    _save_attr("api.routers._helpers", "_settle_submission_payment")
    _save_attr("api.routers._helpers", "dispatch_webhook")
    _save_attr("events.bus", "get_event_bus")
    _save_attr("integrations.x402.payment_dispatcher", "get_dispatcher")
    _save_attr("supabase_client", "get_client")

    _FAKE_HELPERS_P0, _FAKE_EVENT_BUS_P0, _FAKE_DISPATCHER_P0 = _install_stubs_phase0()

    yield

    for (mod_name, attr_name), original in saved_attrs.items():
        mod = sys.modules.get(mod_name)
        if mod is not None:
            setattr(mod, attr_name, original)

    for name, original_mod in saved_modules.items():
        if original_mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original_mod


# ---------------------------------------------------------------------------
# AaaS kill-switch tests
# ---------------------------------------------------------------------------


class TestAaasKillSwitch:
    """POST /arbiter/verify and GET /arbiter/status must 503 when disabled."""

    @pytest.mark.asyncio
    async def test_aaas_returns_503_when_disabled(self, monkeypatch):
        """Explicit EM_AAAS_ENABLED=false -> POST /arbiter/verify -> 503."""
        from fastapi import HTTPException

        from api.auth import AgentAuth
        from api.routers.arbiter_public import (
            ArbiterVerifyRequest,
            TaskSchema,
            verify_evidence,
        )

        monkeypatch.setenv("EM_AAAS_ENABLED", "false")

        auth = AgentAuth(agent_id="evil-bot", wallet_address="0xdead")
        req = ArbiterVerifyRequest(
            evidence={"photo": "url", "gps": {"lat": 1, "lng": 2}},
            task_schema=TaskSchema(category="physical_presence"),
            bounty_usd=0.50,
            photint_score=0.95,
        )

        # If the gate is off the endpoint would have tried to run the
        # arbiter. is_arbiter_enabled is patched to True so we can prove
        # the env flag wins over the PlatformConfig master switch.
        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=True),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_evidence(req, auth)

        assert exc_info.value.status_code == 503
        assert "disabled" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_aaas_returns_503_when_env_missing(self, monkeypatch):
        """Unset EM_AAAS_ENABLED -> POST /arbiter/verify -> 503 (default disabled)."""
        from fastapi import HTTPException

        from api.auth import AgentAuth
        from api.routers.arbiter_public import (
            ArbiterVerifyRequest,
            TaskSchema,
            verify_evidence,
        )

        # Simulate the env var never being set at all.
        monkeypatch.delenv("EM_AAAS_ENABLED", raising=False)

        auth = AgentAuth(agent_id="probe", wallet_address="0xprobe")
        req = ArbiterVerifyRequest(
            evidence={"photo": "url"},
            task_schema=TaskSchema(category="general"),
            bounty_usd=0.10,
            photint_score=0.9,
        )

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=True),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_evidence(req, auth)

        assert exc_info.value.status_code == 503
        assert "disabled" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_aaas_status_endpoint_also_503_when_disabled(self, monkeypatch):
        """GET /arbiter/status must not leak that the endpoint exists when disabled."""
        from fastapi import HTTPException

        from api.routers.arbiter_public import arbiter_status

        monkeypatch.setenv("EM_AAAS_ENABLED", "false")

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=True),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await arbiter_status()

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_aaas_case_insensitive_true_value(self, monkeypatch):
        """EM_AAAS_ENABLED='True' (capitalized) should still enable the endpoint."""
        from unittest.mock import patch

        from api.auth import AgentAuth
        from api.routers.arbiter_public import (
            ArbiterVerifyRequest,
            TaskSchema,
            verify_evidence,
        )

        monkeypatch.setenv("EM_AAAS_ENABLED", "TRUE")

        auth = AgentAuth(agent_id="legit", wallet_address="0x1")
        req = ArbiterVerifyRequest(
            evidence={"photo": "url"},
            task_schema=TaskSchema(category="physical_presence"),
            bounty_usd=0.50,
            photint_score=0.92,
        )

        # is_arbiter_enabled=False makes the downstream endpoint raise 503
        # with a DIFFERENT detail. That proves we got past the Phase 0 gate.
        from fastapi import HTTPException

        with patch(
            "api.routers.arbiter_public.is_arbiter_enabled",
            new=AsyncMock(return_value=False),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_evidence(req, auth)

        # Phase 0 detail contains "disabled on this deployment"
        # Arbiter-master-off detail contains "not enabled on this deployment"
        # Both are 503 but we verify we hit the master-switch path, not the gate.
        assert exc_info.value.status_code == 503
        assert "not enabled" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Auto-release kill-switch tests
# ---------------------------------------------------------------------------


class TestAutoReleaseKillSwitch:
    """processor.process_arbiter_verdict() must refuse auto branch when env is off."""

    @pytest.fixture
    def task_auto(self):
        return {
            "id": "phase0-task-auto",
            "agent_id": "0xagent",
            "bounty_usd": 0.10,
            "arbiter_mode": "auto",
            "arbiter_enabled": True,  # PlatformConfig master switch ON
        }

    @pytest.fixture
    def submission(self):
        return {
            "id": "phase0-sub",
            "evidence": {"photo": "https://example.com/p.jpg"},
            "auto_check_details": {"score": 0.92},
            "ai_verification_result": {"score": 0.88},
            "executor": {"id": "exec-1", "wallet_address": "0xworker"},
        }

    @staticmethod
    def _make_pass_verdict():
        from integrations.arbiter.types import (
            ArbiterDecision,
            ArbiterTier,
            ArbiterVerdict,
            RingScore,
        )

        return ArbiterVerdict(
            decision=ArbiterDecision.PASS,
            tier=ArbiterTier.CHEAP,
            aggregate_score=0.92,
            confidence=0.85,
            evidence_hash="0x" + "a" * 64,
            commitment_hash="0x" + "b" * 64,
            ring_scores=[
                RingScore(
                    ring="ring1",
                    score=0.92,
                    decision="pass",
                    confidence=0.85,
                    provider="photint",
                    model="phase_a+b",
                )
            ],
            reason="phase0 pass verdict",
            disagreement=False,
        )

    @staticmethod
    def _make_fail_verdict():
        from integrations.arbiter.types import (
            ArbiterDecision,
            ArbiterTier,
            ArbiterVerdict,
            RingScore,
        )

        return ArbiterVerdict(
            decision=ArbiterDecision.FAIL,
            tier=ArbiterTier.CHEAP,
            aggregate_score=0.15,
            confidence=0.82,
            evidence_hash="0x" + "c" * 64,
            commitment_hash="0x" + "d" * 64,
            ring_scores=[
                RingScore(
                    ring="ring1",
                    score=0.15,
                    decision="fail",
                    confidence=0.82,
                    provider="photint",
                    model="phase_a+b",
                )
            ],
            reason="phase0 fail verdict",
            disagreement=False,
        )

    @pytest.mark.asyncio
    async def test_auto_release_refused_when_env_disabled(
        self, monkeypatch, task_auto, submission
    ):
        """Auto PASS + PlatformConfig.arbiter_enabled=True + env disabled ->
        verdict is STORED, settle is NOT called, no funds move."""
        monkeypatch.setenv("EM_ARBITER_AUTO_RELEASE_ENABLED", "false")

        from integrations.arbiter.processor import process_arbiter_verdict

        # Prove the mock would have been invoked if the gate failed.
        _FAKE_HELPERS_P0._settle_submission_payment = AsyncMock(
            return_value={"payment_tx": "0xSHOULD_NOT_BE_CALLED"}
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),  # passthrough
        ):
            verdict = self._make_pass_verdict()
            result = await process_arbiter_verdict(verdict, task_auto, submission)

        assert result.action == "stored"
        assert result.success is True
        # No payment attempted
        assert result.payment_tx is None
        _FAKE_HELPERS_P0._settle_submission_payment.assert_not_called()
        # Details include the reason for refusal
        assert result.details.get("reason") == "auto_release_disabled"
        assert result.details.get("env_var") == "EM_ARBITER_AUTO_RELEASE_ENABLED"

    @pytest.mark.asyncio
    async def test_auto_refund_refused_when_env_disabled(
        self, monkeypatch, task_auto, submission
    ):
        """Auto FAIL + env disabled -> stored, refund_trustless_escrow NOT called."""
        monkeypatch.setenv("EM_ARBITER_AUTO_RELEASE_ENABLED", "false")

        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_DISPATCHER_P0.refund_trustless_escrow = AsyncMock(
            return_value={"success": True, "tx_hash": "0xSHOULD_NOT_BE_CALLED"}
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            verdict = self._make_fail_verdict()
            result = await process_arbiter_verdict(verdict, task_auto, submission)

        assert result.action == "stored"
        assert result.success is True
        assert result.refund_tx is None
        _FAKE_DISPATCHER_P0.refund_trustless_escrow.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_release_refused_when_env_missing(
        self, monkeypatch, task_auto, submission
    ):
        """Unset env var is treated as disabled (secure default)."""
        monkeypatch.delenv("EM_ARBITER_AUTO_RELEASE_ENABLED", raising=False)

        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_HELPERS_P0._settle_submission_payment = AsyncMock(
            return_value={"payment_tx": "0xSHOULD_NOT_BE_CALLED"}
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            verdict = self._make_pass_verdict()
            result = await process_arbiter_verdict(verdict, task_auto, submission)

        assert result.action == "stored"
        _FAKE_HELPERS_P0._settle_submission_payment.assert_not_called()

    @pytest.mark.asyncio
    async def test_inconclusive_still_escalates_when_env_disabled(
        self, monkeypatch, task_auto, submission
    ):
        """INCONCLUSIVE verdicts must still escalate to L2 human disputes even
        when the auto-release kill-switch is off. The gate only blocks the
        PASS/FAIL auto path — dispute escalation is safe and must remain live."""
        monkeypatch.setenv("EM_ARBITER_AUTO_RELEASE_ENABLED", "false")

        from integrations.arbiter.processor import process_arbiter_verdict
        from integrations.arbiter.types import (
            ArbiterDecision,
            ArbiterTier,
            ArbiterVerdict,
            RingScore,
        )

        verdict = ArbiterVerdict(
            decision=ArbiterDecision.INCONCLUSIVE,
            tier=ArbiterTier.CHEAP,
            aggregate_score=0.55,
            confidence=0.60,
            evidence_hash="0x" + "e" * 64,
            commitment_hash="0x" + "f" * 64,
            ring_scores=[
                RingScore(
                    ring="ring1",
                    score=0.55,
                    decision="inconclusive",
                    confidence=0.60,
                    provider="photint",
                    model="phase_a+b",
                )
            ],
            reason="phase0 inconclusive",
            disagreement=True,
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            result = await process_arbiter_verdict(verdict, task_auto, submission)

        # Step 5 of process_arbiter_verdict escalates INCONCLUSIVE BEFORE
        # reaching the Step 7 auto branch and kill-switch check.
        assert result.action == "escalated"

    @pytest.mark.asyncio
    async def test_auto_release_honored_when_env_enabled(
        self, monkeypatch, task_auto, submission
    ):
        """Sanity check: flipping the flag on restores the auto branch."""
        monkeypatch.setenv("EM_ARBITER_AUTO_RELEASE_ENABLED", "true")

        from integrations.arbiter.processor import process_arbiter_verdict

        _FAKE_HELPERS_P0._settle_submission_payment = AsyncMock(
            return_value={"payment_tx": "0xPHASE0_ENABLED_SETTLE"}
        )

        with patch(
            "integrations.arbiter.processor.resolve_arbiter_mode",
            new=AsyncMock(side_effect=lambda m: m),
        ):
            verdict = self._make_pass_verdict()
            result = await process_arbiter_verdict(verdict, task_auto, submission)

        assert result.action == "released"
        assert result.payment_tx == "0xPHASE0_ENABLED_SETTLE"
        _FAKE_HELPERS_P0._settle_submission_payment.assert_called_once()


# ---------------------------------------------------------------------------
# Skill.md hygiene tests
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    # .../mcp_server/tests/test_arbiter_phase0.py -> repo root
    return Path(__file__).resolve().parent.parent.parent


class TestSkillMdNoDualInferenceLanguage:
    """The canonical skill.md shipped to agents must not promise "dual-inference"
    verification while Ring 2 LLM is still a stub (AI-001)."""

    CANONICAL = _repo_root() / "dashboard" / "public" / "skill.md"
    BACKEND_COPY = _repo_root() / "mcp_server" / "skills" / "SKILL.md"

    def test_canonical_skill_md_no_dual_inference_language(self):
        assert self.CANONICAL.exists(), f"canonical skill.md missing: {self.CANONICAL}"
        text = self.CANONICAL.read_text(encoding="utf-8")

        # Both "dual-inference" and "dual inference" — any case.
        pattern = re.compile(r"dual[ -]inference", re.IGNORECASE)
        matches = pattern.findall(text)
        assert not matches, (
            f"Found 'dual-inference' / 'dual inference' language in "
            f"{self.CANONICAL.relative_to(_repo_root())}: {matches}. "
            f"Ring 2 LLM is currently a stub (AI-001) — remove marketing "
            f"language that implies real dual-ring inference."
        )

    def test_backend_skill_md_no_dual_inference_language(self):
        assert self.BACKEND_COPY.exists(), (
            f"backend SKILL.md missing: {self.BACKEND_COPY}"
        )
        text = self.BACKEND_COPY.read_text(encoding="utf-8")
        pattern = re.compile(r"dual[ -]inference", re.IGNORECASE)
        matches = pattern.findall(text)
        assert not matches, (
            f"Found 'dual-inference' / 'dual inference' language in backend "
            f"SKILL.md copy: {matches}. Edit dashboard/public/skill.md "
            f"(canonical) and re-sync to mcp_server/skills/SKILL.md."
        )

    def test_canonical_and_backend_skill_md_in_sync(self):
        """CLAUDE.md rule — CI enforces this. Verify locally."""
        canonical = self.CANONICAL.read_text(encoding="utf-8")
        backend = self.BACKEND_COPY.read_text(encoding="utf-8")
        assert canonical == backend, (
            "dashboard/public/skill.md and mcp_server/skills/SKILL.md "
            "are out of sync. Run: "
            "cp dashboard/public/skill.md mcp_server/skills/SKILL.md"
        )

    def test_skill_md_version_bumped_to_v8_or_later(self):
        """v8.0.0 is the Phase 0 GR-0.2 breaking-change release."""
        text = self.CANONICAL.read_text(encoding="utf-8")
        match = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
        assert match is not None, "Could not find version in skill.md frontmatter"
        major = int(match.group(1))
        assert major >= 8, (
            f"Expected skill.md version >= 8.x.x (Phase 0 GR-0.2), got {match.group(0)}"
        )
