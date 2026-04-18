"""
Tests for Sentry SDK wiring (Phase 1.5 SAAS_PRODUCTION_HARDENING).

Validates:
    * App boots cleanly when SENTRY_DSN is unset (graceful degradation).
    * The PII scrubber truncates wallet addresses in strings, nested dicts,
      nested lists, and tuples.
    * The scrubber leaves non-wallet data untouched.
    * The main.py wiring exists (regression guard for accidental removals).

We do NOT actually call sentry_sdk.init here — that would open a real
transport. We import the private helper _scrub_pii from main.py after
forcing SENTRY_DSN="" so the init branch is bypassed.

Marker: security (error-path hardening)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.security


# ---------------------------------------------------------------------------
# 1. PII scrubber behavior
# ---------------------------------------------------------------------------
#
# Import _scrub_pii from main.py WITHOUT running its boot-time assertions by
# setting the escape hatch env var. If main has already been imported by a
# sibling test, we reload it with the DSN env var cleared.


@pytest.fixture(scope="module")
def _main_module():
    """Load ``main`` once per module.

    Reloading ``main`` on every test corrupts pydantic's generic model
    registry (pydantic.root_model module entry gets rebuilt under the
    module's fresh dict), so we load it exactly once per session. This is
    safe for scrubber tests because ``_scrub_pii`` is a pure function that
    does not depend on module-level env var state.
    """
    import os

    os.environ["EM_DISABLE_BOOT_ASSERTIONS"] = "true"
    os.environ.pop("SENTRY_DSN", None)
    if "main" in sys.modules:
        return sys.modules["main"]
    return importlib.import_module("main")


@pytest.fixture
def scrubber(_main_module):
    return _main_module._scrub_pii


class TestScrubberTruncatesWallets:
    WALLET = "0x" + "a" * 40
    EXPECTED = "0xaaaa...aaaa"

    def test_scrubs_top_level_string(self, scrubber):
        event = f"User wallet {self.WALLET} failed payment"
        out = scrubber(event, hint={})
        assert self.WALLET not in out
        assert self.EXPECTED in out

    def test_scrubs_wallet_in_dict(self, scrubber):
        event = {"user": {"wallet": self.WALLET}, "msg": f"ok {self.WALLET}"}
        out = scrubber(event, hint={})
        assert out["user"]["wallet"] == self.EXPECTED
        assert self.WALLET not in out["msg"]
        assert self.EXPECTED in out["msg"]

    def test_scrubs_wallet_in_list(self, scrubber):
        event = {"wallets": [self.WALLET, "0x" + "b" * 40]}
        out = scrubber(event, hint={})
        for item in out["wallets"]:
            assert not item.startswith(self.WALLET)
            assert "..." in item
            assert len(item) == len(self.EXPECTED)

    def test_scrubs_wallet_in_nested_structure(self, scrubber):
        event = {
            "request": {
                "body": {
                    "agents": [
                        {"id": 1, "wallet": self.WALLET},
                        {"id": 2, "wallet": "0x" + "C" * 40},
                    ]
                }
            }
        }
        out = scrubber(event, hint={})
        assert self.WALLET not in str(out)
        # Both wallets truncated correctly.
        assert out["request"]["body"]["agents"][0]["wallet"] == self.EXPECTED
        assert out["request"]["body"]["agents"][1]["wallet"].startswith("0xCCCC")
        assert out["request"]["body"]["agents"][1]["wallet"].endswith("CCCC")

    def test_scrubs_wallet_in_tuple(self, scrubber):
        event = ("login", self.WALLET, {"extra": self.WALLET})
        out = scrubber(event, hint={})
        assert isinstance(out, tuple)
        assert out[0] == "login"
        assert self.WALLET not in out[1]
        assert self.WALLET not in out[2]["extra"]


class TestScrubberLeavesNonWalletsAlone:
    def test_plain_string_untouched(self, scrubber):
        event = "Routine log line with no PII"
        assert scrubber(event, hint={}) == event

    def test_dict_without_wallets_untouched(self, scrubber):
        event = {"status": "ok", "count": 42, "items": ["a", "b"]}
        assert scrubber(event, hint={}) == event

    def test_numeric_and_bool_untouched(self, scrubber):
        event = {"count": 10, "enabled": True, "ratio": 3.14}
        out = scrubber(event, hint={})
        assert out == event
        assert out["enabled"] is True  # bool-identity preserved

    def test_short_hex_not_mistaken_for_wallet(self, scrubber):
        """A hex string shorter than 40 chars must NOT be truncated."""
        event = "tx hash prefix 0xabcdef"
        out = scrubber(event, hint={})
        assert out == event

    def test_longer_hex_wallet_prefix_still_truncates(self, scrubber):
        """If a 40-hex run appears inside a longer string, only that run
        is substituted."""
        event = "prefix 0x" + "f" * 40 + " suffix"
        out = scrubber(event, hint={})
        assert ("0x" + "f" * 40) not in out
        assert "prefix" in out
        assert "suffix" in out


# ---------------------------------------------------------------------------
# 2. Graceful degradation: boot with DSN unset must not raise
# ---------------------------------------------------------------------------


class TestBootWithoutDsn:
    """Validate graceful degradation when SENTRY_DSN is unset or whitespace.

    We assert on the module attributes loaded ONCE at import time (see the
    module-scoped ``_main_module`` fixture above). Reloading ``main`` on
    every test corrupts pydantic's generic model registry, so we rely on
    the test environment having no ``SENTRY_DSN`` set (pytest.ini + the
    ``_main_module`` fixture both unset it).
    """

    def test_import_main_with_empty_dsn_does_not_raise(self, _main_module):
        """The app must import cleanly with SENTRY_DSN empty (dev/test).

        Regression guard: ``sentry_sdk.init`` must NOT be called when the
        DSN is empty (would either open a real transport or raise).
        """
        # The module-scoped fixture imported main with SENTRY_DSN unset.
        assert _main_module._SENTRY_DSN == ""
        assert _main_module._SENTRY_INITIALIZED is False

    def test_whitespace_dsn_is_stripped_to_empty(self):
        """Whitespace-only DSN (common misconfig) must be treated as empty
        so the init branch is skipped.

        Asserts the source-level behavior rather than reloading the module
        (which would corrupt pydantic state across tests).
        """
        src = (Path(__file__).parent.parent / "main.py").read_text(encoding="utf-8")
        # The DSN read must call .strip() so "   \n  " -> "".
        assert 'os.environ.get("SENTRY_DSN", "").strip()' in src, (
            "main.py must .strip() SENTRY_DSN to tolerate whitespace misconfig"
        )
        # And init must be gated on the stripped value being truthy.
        assert "if _SENTRY_DSN:" in src


# ---------------------------------------------------------------------------
# 3. Source-level wiring contracts (hermetic — no imports of main needed)
# ---------------------------------------------------------------------------


class TestSentryWiringContract:
    """Regression guards: a future refactor that drops Sentry init or its
    integrations must fail one of these tests.
    """

    def _main_source(self) -> str:
        return (Path(__file__).parent.parent / "main.py").read_text(encoding="utf-8")

    def test_main_imports_sentry_integrations(self):
        src = self._main_source()
        assert "from sentry_sdk.integrations.fastapi import FastApiIntegration" in src
        assert "from sentry_sdk.integrations.httpx import HttpxIntegration" in src

    def test_main_passes_before_send_scrubber(self):
        src = self._main_source()
        assert "before_send=_scrub_pii" in src

    def test_main_sets_traces_sample_rate(self):
        src = self._main_source()
        assert "traces_sample_rate=0.1" in src

    def test_main_guards_init_with_dsn_presence(self):
        """Init must only run when _SENTRY_DSN is truthy (graceful
        degradation for dev/test)."""
        src = self._main_source()
        assert "if _SENTRY_DSN:" in src

    def test_requirements_includes_sentry_extras(self):
        req = (Path(__file__).parent.parent / "requirements.txt").read_text(
            encoding="utf-8"
        )
        assert "sentry-sdk[fastapi,httpx]" in req
