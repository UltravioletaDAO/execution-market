"""Tests for the multi-provider verification tier resolver.

Covers the 3x3 matrix (3 tiers x 3 verification states) plus the env-flag
backward-compat surface. See:
  - mcp_server/integrations/verification/enforcement.py
  - mcp_server/integrations/verification/tiers.py
  - docs/planning/MASTER_PLAN_VERYAI_INTEGRATION.md (Phase 1.4)
"""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_mcp_root = str(Path(__file__).resolve().parent.parent)
if _mcp_root not in sys.path:
    sys.path.insert(0, _mcp_root)

# Drop stale stubs the test runner may have cached.
for name in (
    "integrations",
    "integrations.verification",
    "integrations.verification.enforcement",
    "integrations.verification.tiers",
):
    if name in sys.modules and not hasattr(sys.modules[name], "__path__"):
        del sys.modules[name]

pytestmark = pytest.mark.core


def _mock_db(world_id_verified=False, world_id_level=None, veryai_verified=False):
    db = MagicMock()
    data = [
        {
            "world_id_verified": world_id_verified,
            "world_id_level": world_id_level,
            "veryai_verified": veryai_verified,
            "veryai_level": "palm_single" if veryai_verified else None,
        }
    ]
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=data
    )
    return db


def _mock_platform_config(values: dict | None = None):
    """Patch PlatformConfig.get with a values dict; defaults match production."""
    defaults = {
        "verification.tiers.t1.min_bounty_usd": Decimal("50.00"),
        "verification.tiers.t2.min_bounty_usd": Decimal("500.00"),
        "verification.tiers.t1.providers": ["veryai_palm", "worldid_orb"],
        "verification.tiers.t2.providers": ["worldid_orb"],
        "feature.veryai_required_for_mid_value": True,
        "feature.world_id_required_for_high_value": True,
    }
    if values:
        defaults.update(values)

    async def _get(key, default=None):
        return defaults.get(key, default)

    return AsyncMock(side_effect=_get)


# ---------------------------------------------------------------------------
# resolve_tier_for_bounty
# ---------------------------------------------------------------------------


class TestResolveTier:
    def test_below_t1_is_t0(self):
        from integrations.verification import TierConfig, resolve_tier_for_bounty
        from integrations.verification.tiers import Tier

        cfg = TierConfig(Decimal("50"), Decimal("500"), [], [])
        assert resolve_tier_for_bounty(Decimal("10.00"), cfg) == Tier.T0

    def test_at_t1_threshold_is_t1(self):
        from integrations.verification import TierConfig, resolve_tier_for_bounty
        from integrations.verification.tiers import Tier

        cfg = TierConfig(Decimal("50"), Decimal("500"), [], [])
        assert resolve_tier_for_bounty(Decimal("50.00"), cfg) == Tier.T1

    def test_below_t2_is_t1(self):
        from integrations.verification import TierConfig, resolve_tier_for_bounty
        from integrations.verification.tiers import Tier

        cfg = TierConfig(Decimal("50"), Decimal("500"), [], [])
        assert resolve_tier_for_bounty(Decimal("499.99"), cfg) == Tier.T1

    def test_at_t2_threshold_is_t2(self):
        from integrations.verification import TierConfig, resolve_tier_for_bounty
        from integrations.verification.tiers import Tier

        cfg = TierConfig(Decimal("50"), Decimal("500"), [], [])
        assert resolve_tier_for_bounty(Decimal("500.00"), cfg) == Tier.T2

    def test_far_above_t2_is_t2(self):
        from integrations.verification import TierConfig, resolve_tier_for_bounty
        from integrations.verification.tiers import Tier

        cfg = TierConfig(Decimal("50"), Decimal("500"), [], [])
        assert resolve_tier_for_bounty(Decimal("10000.00"), cfg) == Tier.T2


# ---------------------------------------------------------------------------
# check_tier_eligibility — env-flag short-circuits
# ---------------------------------------------------------------------------


class TestEnvFlags:
    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "false", "EM_VERYAI_ENABLED": "false"}
    )
    async def test_both_env_flags_off_allows_all(self):
        from integrations.verification import check_tier_eligibility

        allowed, err = await check_tier_eligibility(
            "exec-1", Decimal("1000.00"), db_client=_mock_db()
        )
        assert allowed is True
        assert err is None


# ---------------------------------------------------------------------------
# check_tier_eligibility — full 3x3 matrix
# Combinations:
#   bounty in {T0, T1, T2}
#   verification in {none, veryai_palm, worldid_orb}
# ---------------------------------------------------------------------------


class TestTierMatrix:
    """3 bounty tiers x 3 verification states = 9 cases.

    All cases run with EM_VERYAI_ENABLED=true so the new tier path runs.
    """

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t0_unverified_allowed(self):
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1", Decimal("10.00"), db_client=_mock_db()
            )
        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t0_with_veryai_allowed(self):
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1", Decimal("10.00"), db_client=_mock_db(veryai_verified=True)
            )
        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t0_with_orb_allowed(self):
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1",
                Decimal("10.00"),
                db_client=_mock_db(world_id_verified=True, world_id_level="orb"),
            )
        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t1_unverified_blocked(self):
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1", Decimal("100.00"), db_client=_mock_db()
            )
        assert allowed is False
        assert err is not None
        assert err["error"] == "veryai_or_orb_required"
        assert err["required_tier"] == "t1"

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t1_with_veryai_allowed(self):
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1",
                Decimal("100.00"),
                db_client=_mock_db(veryai_verified=True),
            )
        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t1_with_orb_allowed(self):
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1",
                Decimal("100.00"),
                db_client=_mock_db(world_id_verified=True, world_id_level="orb"),
            )
        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t2_unverified_blocked(self):
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1", Decimal("1000.00"), db_client=_mock_db()
            )
        assert allowed is False
        assert err["error"] == "world_id_orb_required"
        assert err["required_tier"] == "t2"

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t2_with_veryai_blocked(self):
        """VeryAI palm does NOT satisfy T2 — only Orb does."""
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1",
                Decimal("1000.00"),
                db_client=_mock_db(veryai_verified=True),
            )
        assert allowed is False
        assert err["error"] == "world_id_orb_required"

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_t2_with_orb_allowed(self):
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1",
                Decimal("1000.00"),
                db_client=_mock_db(world_id_verified=True, world_id_level="orb"),
            )
        assert allowed is True
        assert err is None


# ---------------------------------------------------------------------------
# Backward-compat: VeryAI off should skip T1 enforcement
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "false"}
    )
    async def test_t1_skipped_when_veryai_disabled(self):
        """With VeryAI off, T1 ($50-$500) should not be enforced — legacy behavior."""
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1", Decimal("100.00"), db_client=_mock_db()
            )
        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "false"}
    )
    async def test_t2_still_enforced_when_veryai_disabled(self):
        """T2 ($500+) still requires Orb even with VeryAI off."""
        from integrations.verification import check_tier_eligibility

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1", Decimal("1000.00"), db_client=_mock_db()
            )
        assert allowed is False
        assert err["error"] == "world_id_orb_required"


# ---------------------------------------------------------------------------
# Fail-closed on errors
# ---------------------------------------------------------------------------


class TestFailClosed:
    @pytest.mark.asyncio
    @patch.dict(
        "os.environ", {"EM_WORLD_ID_ENABLED": "true", "EM_VERYAI_ENABLED": "true"}
    )
    async def test_db_error_fails_closed(self):
        from integrations.verification import check_tier_eligibility

        db = MagicMock()
        db.table.side_effect = Exception("DB down")

        with patch(
            "config.platform_config.PlatformConfig.get", _mock_platform_config()
        ):
            allowed, err = await check_tier_eligibility(
                "exec-1", Decimal("1000.00"), db_client=db
            )
        assert allowed is False
        assert err["error"] == "tier_check_failed"
