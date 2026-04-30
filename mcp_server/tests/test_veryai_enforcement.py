"""Unit tests for integrations.veryai.enforcement.check_veryai_eligibility.

6 tests: low/mid/high bounty × verified/unverified, plus master switch off
and fail-closed on DB error.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

# Phase 2 default: master switch OFF. Tests flip on demand.
os.environ.setdefault("EM_VERYAI_ENABLED", "false")

from integrations.veryai.enforcement import check_veryai_eligibility  # noqa: E402

pytestmark = pytest.mark.core


class _Result:
    def __init__(self, data: list[dict]):
        self.data = data


def _mock_db(rows: list[dict]) -> MagicMock:
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.execute.return_value = _Result(rows)
    client = MagicMock()
    client.table.return_value = table
    return client


def _mock_platform_config(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> None:
    """Patch PlatformConfig.get with a small lookup dict."""
    defaults = {
        "feature.veryai_required_for_mid_value": True,
        "veryai.min_bounty_for_palm_usd": Decimal("50.00"),
    }
    defaults.update(kwargs)

    async def fake_get(key: str, default: Any = None) -> Any:
        return defaults.get(key, default)

    from config import platform_config

    monkeypatch.setattr(platform_config.PlatformConfig, "get", fake_get)


# ---------------------------------------------------------------------------
# Master switch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_master_switch_off_allows_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "false")
    db = _mock_db([{}])  # would fail if reached
    allowed, err = await check_veryai_eligibility(
        "exec-1", Decimal("10000"), db_client=db
    )
    assert allowed is True
    assert err is None
    db.table.assert_not_called()  # Never even hit the DB


@pytest.mark.asyncio
async def test_feature_flag_off_allows_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "true")
    _mock_platform_config(
        monkeypatch, **{"feature.veryai_required_for_mid_value": False}
    )
    db = _mock_db([{}])
    allowed, err = await check_veryai_eligibility(
        "exec-1", Decimal("100"), db_client=db
    )
    assert allowed is True
    assert err is None


# ---------------------------------------------------------------------------
# Bounty bands × verification states
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_low_bounty_unverified_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "true")
    _mock_platform_config(monkeypatch)
    db = _mock_db([{"veryai_verified": False}])
    allowed, err = await check_veryai_eligibility("exec-1", Decimal("10"), db_client=db)
    assert allowed is True
    assert err is None


@pytest.mark.asyncio
async def test_low_bounty_verified_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "true")
    _mock_platform_config(monkeypatch)
    db = _mock_db([{"veryai_verified": True, "veryai_level": "palm_single"}])
    allowed, err = await check_veryai_eligibility("exec-1", Decimal("10"), db_client=db)
    assert allowed is True
    assert err is None


@pytest.mark.asyncio
async def test_mid_bounty_unverified_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "true")
    _mock_platform_config(monkeypatch)
    db = _mock_db([{"veryai_verified": False, "veryai_level": None}])
    allowed, err = await check_veryai_eligibility(
        "exec-1", Decimal("100"), db_client=db
    )
    assert allowed is False
    assert err is not None
    assert err["error"] == "veryai_required"
    assert err["required_provider"] == "veryai_palm"


@pytest.mark.asyncio
async def test_mid_bounty_verified_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "true")
    _mock_platform_config(monkeypatch)
    db = _mock_db([{"veryai_verified": True, "veryai_level": "palm_single"}])
    allowed, err = await check_veryai_eligibility(
        "exec-1", Decimal("100"), db_client=db
    )
    assert allowed is True
    assert err is None


@pytest.mark.asyncio
async def test_high_bounty_unverified_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "true")
    _mock_platform_config(monkeypatch)
    db = _mock_db([{"veryai_verified": False}])
    allowed, err = await check_veryai_eligibility(
        "exec-1", Decimal("1000"), db_client=db
    )
    assert allowed is False
    assert err["error"] == "veryai_required"


@pytest.mark.asyncio
async def test_high_bounty_verified_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "true")
    _mock_platform_config(monkeypatch)
    db = _mock_db([{"veryai_verified": True, "veryai_level": "palm_dual"}])
    allowed, err = await check_veryai_eligibility(
        "exec-1", Decimal("1000"), db_client=db
    )
    assert allowed is True


# ---------------------------------------------------------------------------
# Fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_error_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EM_VERYAI_ENABLED", "true")
    _mock_platform_config(monkeypatch)

    bad_client = MagicMock()
    bad_client.table.side_effect = RuntimeError("supabase down")

    allowed, err = await check_veryai_eligibility(
        "exec-1", Decimal("100"), db_client=bad_client
    )
    assert allowed is False
    assert err["error"] == "veryai_check_failed"
