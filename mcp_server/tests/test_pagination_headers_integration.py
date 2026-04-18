"""
Integration tests for Task 6.4 pagination header wiring.

Unit tests in ``test_pagination_headers.py`` cover the helper in isolation.
This file exercises the wiring in real FastAPI routes to ensure the helper
is actually invoked by each list endpoint, the ``le=100`` bound is rejected
via HTTP 422, and page=2 returns the expected ``rel=prev`` link — which is
the validation the Master Plan explicitly asks for.

Only GET /api/v1/tasks/available is exercised here as the representative
public endpoint. All other wired endpoints follow the same pattern
(inject ``Request``/``Response`` + call ``set_pagination_headers``) and the
unit tests for the helper itself cover the header shape exhaustively.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.core


class _QueryBuilder:
    """Chainable Supabase PostgREST stub whose ``.execute()`` returns a mock."""

    def __init__(self, rows: list[dict], total: int):
        self._rows = rows
        self._total = total

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def contains(self, *_args, **_kwargs):
        return self

    @property
    def not_(self):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, start: int, end: int):
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._rows
        result.count = self._total
        return result


def _client_with_tasks(rows: list[dict], total: int) -> TestClient:
    """Build a FastAPI app with the tasks router backed by a stub DB."""
    from api.routers.tasks import router

    app = FastAPI()
    app.include_router(router)

    mock_client = MagicMock()
    mock_client.table.return_value = _QueryBuilder(rows, total)

    mock_db = MagicMock()
    mock_db.get_client.return_value = mock_client

    with patch("api.routers.tasks.db", mock_db):
        yield TestClient(app, raise_server_exceptions=False)


class TestTasksAvailablePaginationHeaders:
    """Verify /api/v1/tasks/available emits the pagination helper output."""

    def test_first_page_emits_x_total_count_and_rel_next(self) -> None:
        gen = _client_with_tasks(rows=[], total=250)
        client = next(gen)

        response = client.get("/api/v1/tasks/available?limit=20&offset=0")
        # Close the patch context after asserting
        try:
            assert response.status_code == 200
            assert response.headers.get("X-Total-Count") == "250"

            link = response.headers.get("Link", "")
            assert 'rel="next"' in link
            # Next page starts at offset=20
            assert "offset=20" in link
            # First page has no prev
            assert 'rel="prev"' not in link
        finally:
            next(gen, None)

    def test_page_two_emits_rel_prev(self) -> None:
        """Master Plan validation: 'Test que page=2 funciona'."""
        gen = _client_with_tasks(rows=[], total=250)
        client = next(gen)

        response = client.get("/api/v1/tasks/available?limit=20&offset=20")
        try:
            assert response.status_code == 200
            assert response.headers.get("X-Total-Count") == "250"

            link = response.headers.get("Link", "")
            assert 'rel="prev"' in link
            assert 'rel="next"' in link
            # Prev on page 2 jumps back to offset=0
            assert "offset=0" in link
            assert "offset=40" in link
        finally:
            next(gen, None)

    def test_last_page_drops_rel_next(self) -> None:
        gen = _client_with_tasks(rows=[], total=40)
        client = next(gen)

        response = client.get("/api/v1/tasks/available?limit=20&offset=20")
        try:
            assert response.status_code == 200
            assert response.headers.get("X-Total-Count") == "40"

            link = response.headers.get("Link", "")
            assert 'rel="prev"' in link
            assert 'rel="next"' not in link
        finally:
            next(gen, None)

    def test_limit_above_100_rejected_with_422(self) -> None:
        """Task 6.4 ``le=100`` cap must hold end-to-end."""
        gen = _client_with_tasks(rows=[], total=0)
        client = next(gen)

        try:
            response = client.get("/api/v1/tasks/available?limit=101")
            assert response.status_code == 422
        finally:
            next(gen, None)
