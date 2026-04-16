"""
Tests for WS-3 (geo-matching) task-creation behavior:
    * geo_match_mode + location_radius_m fields on CreateTaskRequest
    * infer_geo_match_mode() helper
    * strict-mode validation (422 without coords)
    * location_radius_m ignored-with-warning for non-strict modes
    * Regression: tasks with no new fields still work
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.core

from fastapi import HTTPException

from ..api.routers import tasks as tasks_router
from ..api.routers._models import CreateTaskRequest
from ..models import (
    TaskCategory,
    EvidenceType,
    TargetExecutorType,
    GeoMatchMode,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_http_request(headers=None):
    """FastAPI Request stub with headers dict."""
    mock = MagicMock()
    mock.headers = headers or {}
    mock.url.path = "/api/v1/tasks"
    return mock


def _auth(agent_id="0xAgentTest"):
    return SimpleNamespace(
        agent_id=agent_id,
        wallet_address=agent_id,
        auth_method="erc8128",
        erc8004_registered=True,
    )


def _base_request_kwargs(**overrides):
    """Minimum kwargs for a valid CreateTaskRequest."""
    base = dict(
        title="Test geo matching task",
        instructions=(
            "Please take a photo of the storefront and submit it as evidence. "
            "This is a smoke test for WS-3 geo-matching fields."
        ),
        category=TaskCategory.SIMPLE_ACTION,
        bounty_usd=0.10,
        deadline_hours=2,
        evidence_required=[EvidenceType.SCREENSHOT],
        payment_token="USDC",
        payment_network="base",
        target_executor=TargetExecutorType.ANY,
    )
    base.update(overrides)
    return base


# =============================================================================
# infer_geo_match_mode — pure-function unit tests
# =============================================================================


def test_infer_strict_when_lat_lng_set():
    """Both lat + lng → strict (primary GPS signal wins over hint)."""
    assert (
        tasks_router.infer_geo_match_mode(25.7617, -80.1918, "Miami, FL, USA")
        == "strict"
    )


def test_infer_strict_when_only_coords_and_no_hint():
    assert tasks_router.infer_geo_match_mode(40.7128, -74.0060, None) == "strict"


def test_infer_city_when_hint_is_city_state():
    assert tasks_router.infer_geo_match_mode(None, None, "Miami, FL") == "city"


def test_infer_city_when_hint_is_city_state_country():
    assert tasks_router.infer_geo_match_mode(None, None, "Miami, FL, USA") == "city"


def test_infer_city_when_hint_is_city_country():
    assert tasks_router.infer_geo_match_mode(None, None, "Paris, France") == "city"


def test_infer_region_when_hint_has_no_comma():
    """A bare region/country without comma → region (non-city-like)."""
    assert tasks_router.infer_geo_match_mode(None, None, "California") == "region"


def test_infer_region_when_hint_is_non_city_like():
    assert (
        tasks_router.infer_geo_match_mode(None, None, "somewhere in the mountains")
        == "region"
    )


def test_infer_any_when_no_location_fields():
    assert tasks_router.infer_geo_match_mode(None, None, None) == "any"


def test_infer_any_ignores_only_lat_without_lng():
    """Just one coord (unusable for strict) + no hint → any."""
    assert tasks_router.infer_geo_match_mode(25.0, None, None) == "any"


def test_infer_region_when_only_lat_but_has_hint():
    """Partial coords + non-city-like hint → region."""
    assert tasks_router.infer_geo_match_mode(25.0, None, "somewhere") == "region"


# =============================================================================
# CreateTaskRequest — field acceptance + round-trip
# =============================================================================


def test_request_accepts_geo_match_mode_city():
    """New fields accepted + stored on the model (round-trip)."""
    req = CreateTaskRequest(
        **_base_request_kwargs(
            location_hint="Miami, FL, USA",
            geo_match_mode=GeoMatchMode.CITY,
        )
    )
    assert req.geo_match_mode == GeoMatchMode.CITY
    # JSON round-trip emits the raw string value
    dumped = req.model_dump()
    assert dumped["geo_match_mode"] == "city"
    assert dumped["location_radius_m"] is None


def test_request_accepts_strict_with_radius():
    req = CreateTaskRequest(
        **_base_request_kwargs(
            location_lat=25.7617,
            location_lng=-80.1918,
            geo_match_mode=GeoMatchMode.STRICT,
            location_radius_m=750,
        )
    )
    assert req.geo_match_mode == GeoMatchMode.STRICT
    assert req.location_radius_m == 750


def test_request_rejects_negative_radius():
    """location_radius_m must be > 0 at the schema layer."""
    with pytest.raises(Exception):  # pydantic ValidationError
        CreateTaskRequest(**_base_request_kwargs(location_radius_m=0))


def test_request_defaults_new_fields_to_none():
    """Regression: omitting the new fields keeps them as None."""
    req = CreateTaskRequest(**_base_request_kwargs())
    assert req.geo_match_mode is None
    assert req.location_radius_m is None


# =============================================================================
# Router — validation + inference wiring
# =============================================================================


def _stub_prelude(monkeypatch):
    """Patch out the heavy pre-flight work (idempotency, fees, x402 verify,
    ERC-8004 checks, geocoding) so create_task() reaches the geo-match branch.

    Returns the AsyncMock used for db.create_task so the test can assert on
    what was persisted.
    """
    monkeypatch.setattr(
        tasks_router.db,
        "get_task_by_idempotency_key",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        tasks_router, "get_platform_fee_percent", AsyncMock(return_value=0)
    )
    # Accept any bounty in tests
    from decimal import Decimal

    monkeypatch.setattr(
        tasks_router, "get_min_bounty", AsyncMock(return_value=Decimal("0.01"))
    )
    monkeypatch.setattr(
        tasks_router, "get_max_bounty", AsyncMock(return_value=Decimal("10000"))
    )
    monkeypatch.setattr(tasks_router, "X402_AVAILABLE", True)
    # Payment verify — return a success-stub.
    from datetime import datetime, timezone

    payment_stub = SimpleNamespace(
        success=True,
        payer_address="0xAgentTest",
        amount_usd=Decimal("0.10"),
        network="base",
        timestamp=datetime.now(timezone.utc),
        task_id="pending",
        tx_hash=None,
        error=None,
    )
    monkeypatch.setattr(
        tasks_router, "verify_x402_payment", AsyncMock(return_value=payment_stub)
    )
    # No dispatcher — skip escrow branches
    monkeypatch.setattr(tasks_router, "get_payment_dispatcher", lambda: None)
    # No ERC-8004 check
    monkeypatch.setattr(tasks_router, "ERC8004_IDENTITY_AVAILABLE", False)
    # No-op any lingering geocoder call (we want strict tests to NOT geocode)
    import sys

    fake_geo = SimpleNamespace(geocode_location=AsyncMock(return_value=None))
    sys.modules["integrations.geocoding"] = fake_geo

    # DB create_task — capture the kwargs
    created_task = {
        "id": "task-ws3-test-123",
        "title": "Test geo matching task",
        "status": "published",
        "category": "simple_action",
        "bounty_usd": 0.10,
        "deadline": "2026-05-01T00:00:00+00:00",
        "created_at": "2026-04-16T12:00:00+00:00",
        "agent_id": "0xAgentTest",
        "instructions": "...",
        "evidence_schema": {"required": ["screenshot"], "optional": []},
        "location_hint": None,
        "min_reputation": 0,
        "erc8004_agent_id": None,
        "payment_network": "base",
        "payment_token": "USDC",
        "escrow_tx": None,
        "refund_tx": None,
        "target_executor_type": "any",
        "metadata": None,
        "required_capabilities": None,
        "skill_version": None,
        "geo_match_mode": None,
        "location_radius_m": None,
    }
    create_mock = AsyncMock(return_value=created_task)
    monkeypatch.setattr(tasks_router.db, "create_task", create_mock)
    # Silence follow-up DB updates
    monkeypatch.setattr(tasks_router.db, "update_task", AsyncMock(return_value=None))
    return create_mock


@pytest.mark.asyncio
async def test_strict_without_coords_raises_422(monkeypatch):
    """Explicit 'strict' without lat/lng must fail with 422."""
    _stub_prelude(monkeypatch)

    req = CreateTaskRequest(
        **_base_request_kwargs(
            location_hint="Miami, FL, USA",
            geo_match_mode=GeoMatchMode.STRICT,
            # location_lat/lng intentionally omitted
        )
    )

    with pytest.raises(HTTPException) as excinfo:
        await tasks_router.create_task(
            http_request=_mock_http_request(),
            request=req,
            auth=_auth(),
        )
    assert excinfo.value.status_code == 422
    detail = excinfo.value.detail
    # Detail is a dict with our custom shape
    assert isinstance(detail, dict)
    assert detail.get("error") == "invalid_geo_match_mode"
    assert "location_lat" in detail.get("message", "")


@pytest.mark.asyncio
async def test_inference_city_from_hint(monkeypatch):
    """No explicit mode + 'City, ST, Country' hint → stored mode = 'city'."""
    create_mock = _stub_prelude(monkeypatch)

    req = CreateTaskRequest(**_base_request_kwargs(location_hint="Miami, FL, USA"))

    result = await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=req,
        auth=_auth(),
    )
    # Returned TaskResponse should not raise
    assert result is not None
    create_mock.assert_awaited_once()
    call_kwargs = create_mock.await_args.kwargs
    assert call_kwargs["geo_match_mode"] == "city"
    # Non-strict modes must not carry a radius.
    assert call_kwargs["location_radius_m"] is None


@pytest.mark.asyncio
async def test_explicit_city_mode_roundtrips(monkeypatch):
    """Explicit geo_match_mode='city' passes through unchanged."""
    create_mock = _stub_prelude(monkeypatch)

    req = CreateTaskRequest(
        **_base_request_kwargs(
            location_hint="San Francisco, CA",
            geo_match_mode=GeoMatchMode.CITY,
        )
    )

    await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=req,
        auth=_auth(),
    )
    kwargs = create_mock.await_args.kwargs
    assert kwargs["geo_match_mode"] == "city"
    assert kwargs["location_radius_m"] is None


@pytest.mark.asyncio
async def test_strict_with_coords_defaults_radius_to_500(monkeypatch):
    """Strict + coords but no radius → default 500m is applied."""
    create_mock = _stub_prelude(monkeypatch)

    req = CreateTaskRequest(
        **_base_request_kwargs(
            location_lat=25.7617,
            location_lng=-80.1918,
            geo_match_mode=GeoMatchMode.STRICT,
        )
    )

    await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=req,
        auth=_auth(),
    )
    kwargs = create_mock.await_args.kwargs
    assert kwargs["geo_match_mode"] == "strict"
    assert kwargs["location_radius_m"] == tasks_router.DEFAULT_STRICT_RADIUS_M
    assert kwargs["location_radius_m"] == 500


@pytest.mark.asyncio
async def test_strict_inferred_from_coords(monkeypatch):
    """lat+lng provided, no explicit mode → inferred strict + default radius."""
    create_mock = _stub_prelude(monkeypatch)

    req = CreateTaskRequest(
        **_base_request_kwargs(
            location_lat=40.7128,
            location_lng=-74.0060,
        )
    )

    await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=req,
        auth=_auth(),
    )
    kwargs = create_mock.await_args.kwargs
    assert kwargs["geo_match_mode"] == "strict"
    assert kwargs["location_radius_m"] == 500


@pytest.mark.asyncio
async def test_radius_ignored_for_non_strict_mode(monkeypatch):
    """location_radius_m for a non-strict mode is dropped (with warning log)."""
    create_mock = _stub_prelude(monkeypatch)

    req = CreateTaskRequest(
        **_base_request_kwargs(
            location_hint="Miami, FL, USA",
            geo_match_mode=GeoMatchMode.CITY,
            location_radius_m=2500,  # nonsensical for city
        )
    )

    await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=req,
        auth=_auth(),
    )
    kwargs = create_mock.await_args.kwargs
    assert kwargs["geo_match_mode"] == "city"
    assert kwargs["location_radius_m"] is None


# =============================================================================
# Regression: tasks with NO new fields still work
# =============================================================================


@pytest.mark.asyncio
async def test_regression_no_geo_fields_defaults_to_any(monkeypatch):
    """Baseline: omitting every new + every location field → mode='any'."""
    create_mock = _stub_prelude(monkeypatch)

    req = CreateTaskRequest(**_base_request_kwargs())

    result = await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=req,
        auth=_auth(),
    )
    assert result is not None
    create_mock.assert_awaited_once()
    kwargs = create_mock.await_args.kwargs
    assert kwargs["geo_match_mode"] == "any"
    assert kwargs["location_radius_m"] is None
    # Critical: legacy kwargs are still correctly passed
    assert kwargs["agent_id"] == "0xAgentTest"
    assert kwargs["category"] == "simple_action"


@pytest.mark.asyncio
async def test_regression_hint_only_infers_region_or_city(monkeypatch):
    """Legacy callers that only set location_hint still get a sane default."""
    create_mock = _stub_prelude(monkeypatch)

    # Bare region name — no comma, so 'region'
    req = CreateTaskRequest(**_base_request_kwargs(location_hint="Mountains"))
    await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=req,
        auth=_auth(),
    )
    kwargs = create_mock.await_args.kwargs
    assert kwargs["geo_match_mode"] == "region"
    assert kwargs["location_radius_m"] is None
