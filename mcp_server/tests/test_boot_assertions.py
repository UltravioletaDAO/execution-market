"""
Tests for boot-time security assertions in mcp_server/main.py.

Phase 0 GR-0.5 — Security audit 2026-04-07.

These tests exercise the two boot assertions that refuse to start the
server when it is misconfigured:

  - CRY-004: JWT secret unset or still the dev default.
  - SC-002:  settlement address falling back to the cold treasury wallet.

Each test runs the assertion function directly with a patched
``os.environ`` rather than spinning up a full FastAPI instance. This
keeps the tests fast and hermetic.
"""

from __future__ import annotations

import importlib
import os
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_main_module():
    """Import mcp_server.main with boot assertions disabled, then return it.

    We cannot let the boot assertions fire at import time because they
    would crash the test collector. The root ``conftest.py`` already sets
    ``TESTING=1`` which disables the top-level assertion block, but we
    also set ``EM_DISABLE_BOOT_ASSERTIONS`` as a belt-and-suspenders
    because some downstream tooling may strip TESTING. Then we call the
    private assertion helpers directly from inside each test.
    """
    os.environ["EM_DISABLE_BOOT_ASSERTIONS"] = "true"
    os.environ.setdefault("TESTING", "1")
    import main  # type: ignore

    return importlib.reload(main)


@pytest.fixture(scope="module")
def main_module() -> Iterator[object]:
    module = _load_main_module()
    yield module


# ---------------------------------------------------------------------------
# CRY-004: JWT secret boot assertion
# ---------------------------------------------------------------------------


class TestJwtSecretBootAssertion:
    """Exercises ``_assert_jwt_secret_not_default``."""

    def test_raises_when_env_vars_unset(self, main_module, monkeypatch):
        monkeypatch.delenv("EM_JWT_SECRET", raising=False)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        with pytest.raises(RuntimeError, match="JWT secret is unset"):
            main_module._assert_jwt_secret_not_default()

    def test_raises_when_em_jwt_secret_is_default(self, main_module, monkeypatch):
        monkeypatch.setenv("EM_JWT_SECRET", "em-dev-jwt-secret-change-me")
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        with pytest.raises(RuntimeError, match="default dev value"):
            main_module._assert_jwt_secret_not_default()

    def test_raises_when_supabase_jwt_secret_is_default(self, main_module, monkeypatch):
        monkeypatch.delenv("EM_JWT_SECRET", raising=False)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "em-dev-jwt-secret-change-me")
        with pytest.raises(RuntimeError, match="default dev value"):
            main_module._assert_jwt_secret_not_default()

    def test_raises_when_em_jwt_secret_is_empty_string(self, main_module, monkeypatch):
        monkeypatch.setenv("EM_JWT_SECRET", "")
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        with pytest.raises(RuntimeError, match="JWT secret is unset"):
            main_module._assert_jwt_secret_not_default()

    def test_passes_when_em_jwt_secret_is_real_value(self, main_module, monkeypatch):
        monkeypatch.setenv("EM_JWT_SECRET", "a-real-production-secret-" + "x" * 40)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        # Must not raise.
        main_module._assert_jwt_secret_not_default()

    def test_passes_when_supabase_jwt_secret_is_real_value(
        self, main_module, monkeypatch
    ):
        monkeypatch.delenv("EM_JWT_SECRET", raising=False)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "supabase-prod-jwt-" + "y" * 40)
        # Must not raise.
        main_module._assert_jwt_secret_not_default()

    def test_em_jwt_secret_takes_precedence_over_supabase(
        self, main_module, monkeypatch
    ):
        # If EM_JWT_SECRET is a real value and SUPABASE_JWT_SECRET is the
        # default, the assertion should still pass — EM_JWT_SECRET wins.
        monkeypatch.setenv("EM_JWT_SECRET", "a-real-production-secret-" + "x" * 40)
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "em-dev-jwt-secret-change-me")
        # Must not raise.
        main_module._assert_jwt_secret_not_default()


# ---------------------------------------------------------------------------
# SC-002: settlement address boot assertion
# ---------------------------------------------------------------------------


class TestSettlementAddressBootAssertion:
    """Exercises ``_assert_settlement_not_treasury``.

    SC-002 is a bonus assertion: it catches the class of bugs where the
    settlement address silently resolves to the cold treasury wallet
    (the Feb 2026 incident). We simulate the resolver by patching
    ``integrations.x402.sdk_client.EMX402SDK._resolve_settlement_address``.
    """

    TREASURY = "0xdeadBEEFdeadBEEFdeadBEEFdeadBEEFdeadBEEF"
    PLATFORM = "0xfEEDface0fEEDface0fEEDface0fEEDface0fEED"

    def test_raises_when_resolved_equals_treasury(self, main_module, monkeypatch):
        monkeypatch.setenv("EM_TREASURY_ADDRESS", self.TREASURY)
        with patch(
            "integrations.x402.sdk_client.EMX402SDK._resolve_settlement_address",
            return_value=self.TREASURY,
        ):
            with pytest.raises(RuntimeError, match="cold treasury"):
                main_module._assert_settlement_not_treasury()

    def test_raises_on_case_insensitive_match(self, main_module, monkeypatch):
        # Ethereum addresses are case-insensitive; a lowercase vs
        # checksum mismatch must still trigger the assertion.
        monkeypatch.setenv("EM_TREASURY_ADDRESS", self.TREASURY.upper())
        with patch(
            "integrations.x402.sdk_client.EMX402SDK._resolve_settlement_address",
            return_value=self.TREASURY.lower(),
        ):
            with pytest.raises(RuntimeError, match="cold treasury"):
                main_module._assert_settlement_not_treasury()

    def test_passes_when_resolved_is_platform_wallet(self, main_module, monkeypatch):
        monkeypatch.setenv("EM_TREASURY_ADDRESS", self.TREASURY)
        with patch(
            "integrations.x402.sdk_client.EMX402SDK._resolve_settlement_address",
            return_value=self.PLATFORM,
        ):
            # Must not raise.
            main_module._assert_settlement_not_treasury()

    def test_skips_when_treasury_env_unset(self, main_module, monkeypatch):
        # If EM_TREASURY_ADDRESS is unset, sdk_client.py already handles
        # the error surface. Our assertion must be a no-op (don't shadow
        # the existing error with a worse message).
        monkeypatch.delenv("EM_TREASURY_ADDRESS", raising=False)
        # Must not raise, must not import sdk_client if we can help it.
        main_module._assert_settlement_not_treasury()

    def test_skips_when_treasury_env_is_empty_string(self, main_module, monkeypatch):
        # Edge case: env var set to empty string should also be a no-op.
        monkeypatch.setenv("EM_TREASURY_ADDRESS", "")
        main_module._assert_settlement_not_treasury()
