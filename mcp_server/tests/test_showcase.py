"""Tests for the Proof Wall showcase endpoint (api/routers/showcase.py).

Covers:
    * PII stripping — no GPS coords, no EXIF raw, no user_id leaks
    * Cursor pagination (encode/decode round-trip, next_cursor handoff)
    * Filters — category, network, order validation
    * Caching — identical queries hit the in-process TTLCache
    * Empty state — no rows returns items=[] without raising
    * Response shape matches ShowcaseResponse

Mocks the PostgREST query builder; never hits Supabase.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.core


# ---------------------------------------------------------------------------
# Supabase query-builder stub
# ---------------------------------------------------------------------------


class _QB:
    """Chainable stub: every mutator returns self, execute() returns the stored response."""

    def __init__(self, response: MagicMock):
        self._response = response

    def select(self, *_, **__):
        return self

    def eq(self, *_, **__):
        return self

    def neq(self, *_, **__):
        return self

    def is_(self, *_, **__):
        return self

    @property
    def not_(self):
        return self

    def or_(self, *_, **__):
        return self

    def order(self, *_, **__):
        return self

    def limit(self, *_, **__):
        return self

    def execute(self):
        return self._response


def _resp(data: list[dict] | None = None):
    r = MagicMock()
    r.data = data or []
    return r


def _client(response: MagicMock) -> MagicMock:
    c = MagicMock()
    c.table.return_value = _QB(response)
    return c


# ---------------------------------------------------------------------------
# Fixture rows — one "good" row with all fields, one with missing primary image
# ---------------------------------------------------------------------------

GOOD_ROW = {
    "id": "sub-1",
    # Prod schema: URLs live inside the `evidence` jsonb, keyed by capture type.
    # `evidence_files` array is legacy and never populated in practice.
    "evidence": {
        "photo_geo": {
            "type": "photo_geo",
            "fileUrl": "https://cdn.execution.market/evidence/photo1.jpg",
            "filename": "storefront.jpg",
            "mimeType": "image/jpeg",
            "metadata": {
                "size": 342775,
                "backend": "supabase",
                "forensic": {
                    # PII that MUST NOT leak to the response:
                    "gps": {"latitude": 4.711, "longitude": -74.072, "accuracy": 96},
                    "device": {"platform": "Win32", "userAgent": "Mozilla/5.0"},
                    "capture_timestamp": "2026-04-16T12:00:00Z",
                },
            },
        },
    },
    "evidence_metadata": {
        # PII that MUST NOT leak to the response:
        "exif": {"camera": "iPhone 15", "verified": True, "raw": "<blob>"},
        "device": {"fingerprint": "abc123"},
        # Legitimate public fields:
        "blurhash": "L6PZfSi_.AyE_3t7t7R**0o#DgR4",
    },
    "ai_verification_result": {"world_id_verified": True, "timestamp_verified": True},
    "paid_at": "2026-04-16T12:01:00Z",
    "task": {
        "title": "Photograph storefront of bodega",
        "instructions": "Take a vertical photo of the storefront of 'El Buen Sabor'.",
        "category": "physical_presence",
        "bounty_usd": 0.25,
        "payment_token": "USDC",
        "payment_network": "base",
        "completed_at": "2026-04-16T12:00:30Z",
        "status": "completed",
    },
    "executor": {
        "display_name": "ruben.eth",
        "avatar_url": "https://cdn.execution.market/avatars/ruben.jpg",
        "avg_rating": 4.87,
        # MUST NOT leak:
        "wallet_address": "0xDEADBEEF",
        "user_id": "user-secret-uuid",
        "email": "ruben@example.com",
    },
}

ROW_NO_IMAGE = {
    "id": "sub-2",
    # Text-only submission — no image keys, should be filtered out by _serialize_item.
    "evidence": {"text_response": "completed via skill, no photo"},
    "evidence_metadata": {},
    "ai_verification_result": None,
    "paid_at": "2026-04-16T11:00:00Z",
    "task": {
        "title": "missing image",
        "instructions": "",
        "category": "simple_action",
        "bounty_usd": 0.10,
        "payment_network": "base",
        "status": "completed",
    },
    "executor": {"display_name": None, "avatar_url": None, "avg_rating": None},
}


# ---------------------------------------------------------------------------
# FastAPI test client helper
# ---------------------------------------------------------------------------


def _make_app():
    from api.routers.showcase import _clear_cache, router

    _clear_cache()
    app = FastAPI()
    app.include_router(router)
    return app


# ===========================================================================
# 1. PII stripping
# ===========================================================================


class TestPIIStripping:
    def test_response_drops_gps_exif_and_user_id(self):
        db = _client(_resp([GOOD_ROW]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence")

        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 1

        # Full-body serialization MUST NOT contain the PII strings
        # anywhere, regardless of nesting.
        raw = json.dumps(body)
        for forbidden in [
            "lat",
            "lng",
            "-74.072",
            "iPhone 15",
            "fingerprint",
            "wallet_address",
            "user_id",
            "user-secret-uuid",
            "ruben@example.com",
            "0xDEADBEEF",
        ]:
            assert forbidden not in raw, f"{forbidden!r} leaked into showcase response"

        # But the boolean verification flags SHOULD be present
        item = body["items"][0]
        assert item["evidence"]["verification"]["gps_verified"] is True
        assert item["evidence"]["verification"]["exif_verified"] is True
        assert item["evidence"]["verification"]["world_id_verified"] is True
        assert item["evidence"]["verification"]["timestamp_verified"] is True

    def test_drops_rows_without_primary_image(self):
        db = _client(_resp([ROW_NO_IMAGE]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence")

        assert r.status_code == 200
        assert r.json()["items"] == []


# ===========================================================================
# 2. Shape of the successful response
# ===========================================================================


class TestResponseShape:
    def test_item_has_all_required_fields(self):
        db = _client(_resp([GOOD_ROW]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence")

        assert r.status_code == 200
        body = r.json()
        item = body["items"][0]

        assert item["id"] == "sub-1"
        assert item["task_title"].startswith("Photograph")
        assert item["bounty_usd"] == 0.25
        assert item["payment_network"] == "base"
        assert item["executor"]["display_name"] == "ruben.eth"
        assert item["executor"]["rating"] == 4.87
        assert item["evidence"]["primary_image_url"].startswith("https://")
        assert item["evidence"]["image_count"] == 1
        assert item["evidence"]["blurhash"] == "L6PZfSi_.AyE_3t7t7R**0o#DgR4"
        assert body["generated_at"]  # ISO timestamp present

    def test_http_cache_and_etag_headers(self):
        db = _client(_resp([GOOD_ROW]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence")

        assert r.status_code == 200
        assert "public" in r.headers.get("cache-control", "")
        assert "stale-while-revalidate" in r.headers.get("cache-control", "")
        assert r.headers.get("etag", "").startswith('W/"')


# ===========================================================================
# 2b. ClawKey KYA flag surfaced in executor preview
# ===========================================================================


class TestKyaVerifiedFlag:
    def test_default_false_when_executor_lacks_clawkey_column(self):
        # GOOD_ROW's executor dict has no `clawkey_verified` key — the
        # response must still serialize the field, defaulted to False.
        db = _client(_resp([GOOD_ROW]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence")
        assert r.status_code == 200
        assert r.json()["items"][0]["executor"]["kya_verified"] is False

    def test_true_when_executor_clawkey_verified(self):
        row = dict(GOOD_ROW)
        row["executor"] = dict(GOOD_ROW["executor"], clawkey_verified=True)
        db = _client(_resp([row]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence")
        assert r.status_code == 200
        assert r.json()["items"][0]["executor"]["kya_verified"] is True

    def test_no_kya_pii_leaks_in_response(self):
        # Even when the flag is True, only the boolean leaks — never the
        # human_id, public_key, or device_id from upstream.
        row = dict(GOOD_ROW)
        row["executor"] = dict(
            GOOD_ROW["executor"],
            clawkey_verified=True,
            clawkey_human_id="hum-abc-private",
            clawkey_public_key="PubKeyB58Secret",
            clawkey_device_id="dev-fingerprint",
        )
        db = _client(_resp([row]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence")
        raw = json.dumps(r.json())
        assert "hum-abc-private" not in raw
        assert "PubKeyB58Secret" not in raw
        assert "dev-fingerprint" not in raw


# ===========================================================================
# 3. Cursor pagination
# ===========================================================================


class TestCursorPagination:
    def test_next_cursor_emitted_when_more_rows(self):
        # Router requests limit+1 as sentinel. We supply 2 rows for limit=1.
        row_a = dict(GOOD_ROW, id="sub-a", paid_at="2026-04-16T12:00:00Z")
        row_b = dict(GOOD_ROW, id="sub-b", paid_at="2026-04-16T11:00:00Z")
        db = _client(_resp([row_a, row_b]))

        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence?limit=1")

        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 1
        assert body["next_cursor"] is not None

        # Cursor should round-trip to the last served item
        decoded = json.loads(
            base64.urlsafe_b64decode(body["next_cursor"].encode("ascii"))
        )
        assert decoded["id"] == "sub-a"
        assert decoded["paid_at"] == "2026-04-16T12:00:00Z"

    def test_no_cursor_when_last_page(self):
        db = _client(_resp([GOOD_ROW]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence?limit=10")

        assert r.status_code == 200
        assert r.json()["next_cursor"] is None

    def test_invalid_cursor_rejected_400(self):
        db = _client(_resp([]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence?cursor=not-base64")
        assert r.status_code == 400


# ===========================================================================
# 4. Query param validation
# ===========================================================================


class TestQueryValidation:
    def test_invalid_category_rejected(self):
        db = _client(_resp([]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence?category=bogus")
        assert r.status_code == 400

    def test_invalid_network_rejected(self):
        db = _client(_resp([]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence?network=fakechain")
        assert r.status_code == 400

    def test_limit_over_max_rejected(self):
        db = _client(_resp([]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence?limit=999")
        # Pydantic/FastAPI validation returns 422
        assert r.status_code == 422

    def test_invalid_order_rejected(self):
        db = _client(_resp([]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence?order=newest")
        assert r.status_code == 422


# ===========================================================================
# 5. Caching
# ===========================================================================


class TestCaching:
    def test_identical_request_hits_cache(self):
        db = _client(_resp([GOOD_ROW]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r1 = client.get("/api/v1/showcase/evidence")
            r2 = client.get("/api/v1/showcase/evidence")

        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["items"] == r2.json()["items"]
        # Client factory called for the cached request too (headers are set
        # per-request) but the underlying query builder must only have
        # executed once.
        assert db.table.call_count == 1


# ===========================================================================
# 6. Empty state
# ===========================================================================


class TestEmptyState:
    def test_empty_db_returns_empty_items(self):
        db = _client(_resp([]))
        with patch("api.routers.showcase.db.get_client", return_value=db):
            client = TestClient(_make_app())
            r = client.get("/api/v1/showcase/evidence")

        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert body["next_cursor"] is None
        assert body["generated_at"]


# ===========================================================================
# 7. Graceful failure mode
# ===========================================================================


class TestFailureMode:
    def test_db_exception_returns_503(self):
        c = MagicMock()
        c.table.side_effect = RuntimeError("db down")
        with patch("api.routers.showcase.db.get_client", return_value=c):
            # raise_server_exceptions=False lets the HTTPException surface as 503
            # instead of crashing the TestClient.
            client = TestClient(_make_app(), raise_server_exceptions=False)
            r = client.get("/api/v1/showcase/evidence")

        assert r.status_code == 503
