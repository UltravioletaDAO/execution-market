"""
Pagination response helpers (Task 6.4 — SaaS production hardening).

Centralises the logic that emits:

  - ``X-Total-Count`` — total rows matching the query (before pagination).
  - ``Link`` — RFC 5988 rel=next / rel=prev URIs so clients can traverse
    pages without reinventing the offset maths.

The helper is intentionally small and stateless so it can be reused from
any list endpoint regardless of storage backend (Supabase count="exact",
in-memory coordinator, etc.). Endpoints that cannot compute a true total
should still call ``set_total`` with ``None`` to signal "unknown" to the
caller — we simply skip the ``X-Total-Count`` header in that case.

RFC 5988 reference: https://www.rfc-editor.org/rfc/rfc5988
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

from fastapi import Request, Response

# Hard platform cap — any endpoint above this needs an explicit exemption
# documented in the Master Plan (Task 6.4). Mirrors the ``le=`` bound we
# enforce on the Query parameters.
MAX_PAGE_SIZE: int = 100


def _build_link(request: Request, offset: int, limit: int, rel: str) -> str:
    """Produce a single RFC 5988 link-value for ``rel``.

    We preserve all existing query string parameters and only replace the
    ``offset`` + ``limit`` pair so that filters stay stable across pages.
    """
    params = dict(request.query_params)
    params["offset"] = str(max(offset, 0))
    params["limit"] = str(limit)
    return f'<{request.url.path}?{urlencode(params)}>; rel="{rel}"'


def set_pagination_headers(
    response: Response,
    request: Request,
    *,
    total: Optional[int],
    offset: int,
    limit: int,
) -> None:
    """Populate ``X-Total-Count`` and ``Link`` on the outbound response.

    ``total`` can be ``None`` when the backend cannot cheaply compute a
    total — we skip the count header but still emit ``rel=next`` as long
    as we received ``limit`` rows, since that's a reasonable "there might
    be more" signal for the client.
    """
    links: list[str] = []

    if total is not None:
        response.headers["X-Total-Count"] = str(total)

        if offset + limit < total:
            links.append(_build_link(request, offset + limit, limit, "next"))
        if offset > 0:
            prev_offset = max(offset - limit, 0)
            links.append(_build_link(request, prev_offset, limit, "prev"))
    else:
        # Unknown total — emit rel=next optimistically; callers are
        # expected to stop paging when they receive an empty page.
        links.append(_build_link(request, offset + limit, limit, "next"))
        if offset > 0:
            prev_offset = max(offset - limit, 0)
            links.append(_build_link(request, prev_offset, limit, "prev"))

    if links:
        response.headers["Link"] = ", ".join(links)
