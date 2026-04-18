"""
Unit tests for the pagination headers helper (Task 6.4).

These tests exercise the pure helper in ``api/routers/_pagination.py``
without standing up the full FastAPI app. They verify:

  - ``X-Total-Count`` is set whenever ``total`` is provided.
  - ``Link`` emits ``rel=next`` only when more pages remain.
  - ``Link`` emits ``rel=prev`` only when ``offset > 0``.
  - The helper preserves unrelated query parameters so filters stay
    stable across pages (a common footgun when clients walk paginated
    responses with stateful filters like ``status=published``).
  - ``MAX_PAGE_SIZE`` equals 100 — if this ever drifts we want the
    failure surfaced here rather than in a prod incident.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import Request, Response

from api.routers._pagination import MAX_PAGE_SIZE, set_pagination_headers


def _fake_request(path: str = "/api/v1/tasks", query: str = "") -> Request:
    """Build a minimal ASGI scope so Request.url / query_params work."""
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query.encode("utf-8"),
        "headers": [],
        "server": ("testserver", 443),
    }
    return Request(scope)


def _parse_links(link_header: str) -> dict[str, dict[str, str]]:
    """Parse a RFC 5988 ``Link`` header into ``{rel: {path, params}}``."""
    out: dict[str, dict[str, str]] = {}
    for entry in link_header.split(","):
        entry = entry.strip()
        uri_part, rel_part = entry.split(";", 1)
        uri = uri_part.strip().lstrip("<").rstrip(">")
        rel = rel_part.strip().split("=", 1)[1].strip('"')
        parsed = urlparse(uri)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        out[rel] = {"path": parsed.path, **params}
    return out


class TestPaginationHeaders:
    def test_max_page_size_is_100(self) -> None:
        """Sentinel — Task 6.4 requires a hard cap of 100."""
        assert MAX_PAGE_SIZE == 100

    def test_total_count_header_set_when_total_known(self) -> None:
        response = Response()
        request = _fake_request(query="status=published")

        set_pagination_headers(response, request, total=250, offset=0, limit=20)

        assert response.headers["X-Total-Count"] == "250"

    def test_total_count_header_omitted_when_total_unknown(self) -> None:
        response = Response()
        request = _fake_request()

        set_pagination_headers(response, request, total=None, offset=0, limit=20)

        assert "x-total-count" not in response.headers

    def test_next_link_present_when_more_pages_remain(self) -> None:
        response = Response()
        request = _fake_request(query="status=published")

        set_pagination_headers(response, request, total=100, offset=0, limit=20)

        links = _parse_links(response.headers["Link"])
        assert "next" in links
        assert links["next"]["offset"] == "20"
        assert links["next"]["limit"] == "20"
        # Filter must be preserved so the client can keep walking.
        assert links["next"]["status"] == "published"
        assert "prev" not in links

    def test_no_next_link_on_last_page(self) -> None:
        response = Response()
        request = _fake_request()

        set_pagination_headers(response, request, total=40, offset=20, limit=20)

        links = _parse_links(response.headers["Link"])
        assert "next" not in links
        assert "prev" in links
        assert links["prev"]["offset"] == "0"

    def test_prev_link_offset_clamps_to_zero(self) -> None:
        """Asking for prev from offset=5 with limit=20 should give offset=0."""
        response = Response()
        request = _fake_request()

        set_pagination_headers(response, request, total=100, offset=5, limit=20)

        links = _parse_links(response.headers["Link"])
        assert links["prev"]["offset"] == "0"

    def test_unknown_total_still_emits_next_link(self) -> None:
        """Callers that can't compute a total still need to paginate."""
        response = Response()
        request = _fake_request()

        set_pagination_headers(response, request, total=None, offset=0, limit=20)

        links = _parse_links(response.headers["Link"])
        assert "next" in links
        assert links["next"]["offset"] == "20"

    def test_preserves_query_params_other_than_offset_limit(self) -> None:
        response = Response()
        request = _fake_request(
            query="status=published&network=base&category=simple_action"
        )

        set_pagination_headers(response, request, total=200, offset=0, limit=20)

        links = _parse_links(response.headers["Link"])
        assert links["next"]["status"] == "published"
        assert links["next"]["network"] == "base"
        assert links["next"]["category"] == "simple_action"
        assert links["next"]["offset"] == "20"
        assert links["next"]["limit"] == "20"

    def test_overrides_incoming_offset_and_limit(self) -> None:
        """Incoming ?offset=X&limit=Y must not leak into the rel=next URI."""
        response = Response()
        request = _fake_request(query="offset=0&limit=20&status=published")

        set_pagination_headers(response, request, total=200, offset=0, limit=20)

        links = _parse_links(response.headers["Link"])
        assert links["next"]["offset"] == "20"  # not "0"
        assert links["next"]["limit"] == "20"

    @pytest.mark.parametrize(
        "total,offset,limit,expect_next,expect_prev",
        [
            (0, 0, 20, False, False),  # empty result
            (20, 0, 20, False, False),  # exactly one page
            (21, 0, 20, True, False),  # one over
            (40, 20, 20, False, True),  # last page
            (100, 40, 20, True, True),  # middle page
        ],
    )
    def test_link_header_presence_matrix(
        self,
        total: int,
        offset: int,
        limit: int,
        expect_next: bool,
        expect_prev: bool,
    ) -> None:
        response = Response()
        request = _fake_request()

        set_pagination_headers(
            response, request, total=total, offset=offset, limit=limit
        )

        link_header = response.headers.get("Link", "")
        links = _parse_links(link_header) if link_header else {}
        assert ("next" in links) is expect_next
        assert ("prev" in links) is expect_prev
