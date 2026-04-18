"""Tests for PII truncation helpers (Phase 2.4, SAAS_PRODUCTION_HARDENING).

See ``mcp_server/utils/pii.py``.
"""

import pytest

from utils.pii import scrub_wallets_in_text, truncate_wallet


# ---------------------------------------------------------------------------
# truncate_wallet
# ---------------------------------------------------------------------------


class TestTruncateWallet:
    """``truncate_wallet`` handles single-address inputs."""

    def test_truncate_wallet_valid(self):
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        assert truncate_wallet(addr) == "0x12345678...5678"

    def test_truncate_wallet_valid_uppercase(self):
        addr = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        assert truncate_wallet(addr) == "0xABCDEF12...EF12"

    def test_truncate_wallet_valid_mixed_case(self):
        addr = "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"
        assert truncate_wallet(addr) == "0xAbCdEf12...Ef12"

    def test_truncate_wallet_none(self):
        assert truncate_wallet(None) is None

    def test_truncate_wallet_empty_string_passthrough(self):
        # Empty string is not a wallet — return as-is (callers may log "" freely).
        assert truncate_wallet("") == ""

    def test_truncate_wallet_short_string_passthrough(self):
        assert truncate_wallet("not a wallet") == "not a wallet"

    def test_truncate_wallet_wrong_prefix_passthrough(self):
        # 42 chars but not starting with 0x — leave untouched so we don't
        # corrupt arbitrary ID strings.
        fake = "0z1234567890abcdef1234567890abcdef12345678"
        assert truncate_wallet(fake) == fake

    def test_truncate_wallet_too_short_passthrough(self):
        assert truncate_wallet("0x1234") == "0x1234"

    def test_truncate_wallet_too_long_passthrough(self):
        too_long = "0x" + "a" * 45  # 47 chars total
        assert truncate_wallet(too_long) == too_long

    def test_truncate_wallet_non_hex_passthrough(self):
        # 42 chars, starts with 0x, but contains non-hex — leave untouched.
        bad = "0xZZZZ567890abcdef1234567890abcdef12345678"
        assert truncate_wallet(bad) == bad

    def test_truncate_wallet_strips_whitespace_before_check(self):
        # Leading/trailing whitespace is stripped before length check, so
        # a real wallet surrounded by spaces IS detected and truncated.
        padded = "  0x1234567890abcdef1234567890abcdef12345678  "
        assert truncate_wallet(padded) == "0x12345678...5678"

    def test_truncate_wallet_non_string_passthrough(self):
        # Accept non-str input gracefully (e.g. int from a buggy caller).
        assert truncate_wallet(42) == 42

    def test_truncate_wallet_output_length(self):
        """Output must be exactly 17 chars (10 + 3 ellipsis + 4)."""
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        out = truncate_wallet(addr)
        assert len(out) == 17


# ---------------------------------------------------------------------------
# scrub_wallets_in_text
# ---------------------------------------------------------------------------


class TestScrubWalletsInText:
    """``scrub_wallets_in_text`` replaces every wallet in a freeform string."""

    def test_scrub_wallets_in_text_single(self):
        text = "error from wallet 0x1234567890abcdef1234567890abcdef12345678 on base"
        assert (
            scrub_wallets_in_text(text) == "error from wallet 0x12345678...5678 on base"
        )

    def test_scrub_wallets_in_text_multiple(self):
        text = (
            "transfer "
            "0x1111111111111111111111111111111111111111 -> "
            "0x2222222222222222222222222222222222222222"
        )
        assert (
            scrub_wallets_in_text(text)
            == "transfer 0x11111111...1111 -> 0x22222222...2222"
        )

    def test_scrub_wallets_in_text_no_wallets(self):
        assert scrub_wallets_in_text("plain error message") == "plain error message"

    def test_scrub_wallets_in_text_none(self):
        assert scrub_wallets_in_text(None) is None

    def test_scrub_wallets_in_text_empty(self):
        assert scrub_wallets_in_text("") == ""

    def test_scrub_wallets_in_text_leaves_tx_hashes_alone(self):
        # A 66-char 0x-hash (tx hash) must NOT be truncated.  Our regex
        # is anchored on word boundaries so 40-hex only matches 40-hex.
        tx = "0x" + "a" * 64
        msg = f"settled with tx {tx}"
        # Hash should appear intact.
        assert tx in scrub_wallets_in_text(msg)

    def test_scrub_wallets_in_text_mixed_tx_and_wallet(self):
        tx = "0x" + "a" * 64
        wallet = "0x1234567890abcdef1234567890abcdef12345678"
        msg = f"tx={tx} from={wallet}"
        out = scrub_wallets_in_text(msg)
        # Wallet truncated, tx preserved.
        assert "0x12345678...5678" in out
        assert tx in out

    def test_scrub_wallets_in_text_non_string_passthrough(self):
        assert scrub_wallets_in_text(123) == 123

    def test_scrub_wallets_in_text_checksum_address(self):
        text = "from 0xAbCdEf1234567890AbCdEf1234567890AbCdEf12 done"
        assert scrub_wallets_in_text(text) == "from 0xAbCdEf12...Ef12 done"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
