"""
Showcase API — "Proof Wall" public evidence feed.

Backs the landing-page Evidence Carousel (Phase 1) and, later, the /proof/:id
and /showcase pages (Phases 2-3). Surfaces a PII-scrubbed view of accepted,
paid submissions so prospective agents can see real verified tasks that were
paid for on-chain.

Endpoints:
    GET /api/v1/showcase/evidence
        Cursor-paginated list of showcase items. Public, anonymous.

Guardrails:
    * Only accepted + paid submissions where the executor has not opted out.
    * PII stripped in ``_serialize_item`` — no GPS, no EXIF raw, no user_id,
      no email, no phone.
    * Response cached 60s in-process (TTLCache) and via HTTP Cache-Control.
    * Cursor is opaque base64(JSON{paid_at, id}).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

import supabase_client as db

try:
    from cachetools import TTLCache
except ImportError:  # pragma: no cover
    TTLCache = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/showcase", tags=["Showcase"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OrderMode = Literal["recent", "highest_paid", "most_verified"]

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50
_DESCRIPTION_TRUNCATE = 160
_DISPLAY_NAME_MAX = 40

_CACHE_TTL_SECONDS = 60
_HTTP_CACHE_MAX_AGE = 60
_HTTP_CACHE_SWR = 300

# Allowed task categories — kept in sync with the `task_category` enum.
# Callers that pass anything else get a 400 early; this prevents the enum
# from rejecting the query deep inside PostgREST with an opaque error.
_ALLOWED_CATEGORIES = {
    "physical_presence",
    "knowledge_access",
    "human_authority",
    "simple_action",
    "digital_physical",
    "phone_hold",
}

# Restrict network filter to values we actually serve — blocks arbitrary
# strings that could turn into expensive LIKE scans.
_ALLOWED_NETWORKS = {
    "base",
    "ethereum",
    "polygon",
    "arbitrum",
    "celo",
    "monad",
    "avalanche",
    "optimism",
    "skale",
    "solana",
}


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class VerificationBadges(BaseModel):
    """Which verification checks this submission passed. True only, never False-with-reason."""

    gps_verified: bool = False
    exif_verified: bool = False
    timestamp_verified: bool = False
    world_id_verified: bool = False


class ExecutorPreview(BaseModel):
    """Public-safe executor card. No wallet, no user_id, no email."""

    display_name: str
    avatar_url: Optional[str] = None
    rating: Optional[float] = None
    # Additive KYA trust signal — true only when ClawKey upstream confirmed the
    # binding. Never blocks rendering. False is the safe default for both
    # humans and unverified agents, so the frontend can treat it as a hint.
    kya_verified: bool = False


class EvidencePreview(BaseModel):
    """Public-safe evidence card. No GPS coords, no EXIF raw, no device fingerprint."""

    primary_image_url: str
    image_count: int
    blurhash: Optional[str] = None
    verification: VerificationBadges


class ShowcaseEvidence(BaseModel):
    """One slide in the Proof Wall carousel."""

    id: str
    task_title: str
    task_description: str
    category: str
    bounty_usd: float
    payment_token: Optional[str] = None
    payment_network: Optional[str] = None
    paid_at: str
    completed_at: Optional[str] = None
    executor: ExecutorPreview
    evidence: EvidencePreview


class ShowcaseResponse(BaseModel):
    items: List[ShowcaseEvidence]
    next_cursor: Optional[str] = None
    generated_at: str


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

# Key is a tuple (limit, category, network, order, cursor). Small cap —
# we only need to protect against stampedes on the landing page, not cache
# every permutation.
_RESPONSE_CACHE: Optional["TTLCache[Tuple[Any, ...], ShowcaseResponse]"] = (
    TTLCache(maxsize=128, ttl=_CACHE_TTL_SECONDS) if TTLCache else None
)


def _cache_key(
    limit: int,
    category: Optional[str],
    network: Optional[str],
    order: str,
    cursor: Optional[str],
) -> Tuple[Any, ...]:
    return (limit, category, network, order, cursor)


def _clear_cache() -> None:
    """Test hook — mirror of the approach in other routers."""
    if _RESPONSE_CACHE is not None:
        _RESPONSE_CACHE.clear()


# ---------------------------------------------------------------------------
# Cursor encoding
# ---------------------------------------------------------------------------


def _encode_cursor(paid_at: str, submission_id: str) -> str:
    payload = json.dumps(
        {"paid_at": paid_at, "id": submission_id}, separators=(",", ":")
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> Dict[str, str]:
    try:
        payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        data = json.loads(payload)
        if not isinstance(data, dict) or "paid_at" not in data or "id" not in data:
            raise ValueError("cursor missing fields")
        return {"paid_at": str(data["paid_at"]), "id": str(data["id"])}
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


# ---------------------------------------------------------------------------
# PII-safe serialization
# ---------------------------------------------------------------------------


def _truncate(text: Optional[str], n: int) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "\u2026"


def _sanitize_display_name(raw: Optional[str], fallback: str) -> str:
    """Strip zero-width / control chars and cap length. Falls back to a short
    placeholder so we don't expose an empty row."""
    if not raw:
        return fallback
    cleaned = "".join(
        ch
        for ch in raw
        if ch.isprintable() and ch not in {"\u200b", "\u200c", "\u200d", "\ufeff"}
    ).strip()
    if not cleaned:
        return fallback
    return cleaned[:_DISPLAY_NAME_MAX]


_IMAGE_EVIDENCE_KEYS: Tuple[str, ...] = ("photo_geo", "photo", "screenshot")


def _primary_image_url(evidence_jsonb: Any) -> Optional[str]:
    """Extract a displayable image URL from the `evidence` jsonb column.

    Historical `evidence_files` array was never populated in practice —
    the real storage shape is `{<type>: {fileUrl, filename, metadata, ...}}`
    where <type> is one of photo_geo | photo | screenshot (or non-image
    keys like text_response / json_response which we skip).
    """
    if not isinstance(evidence_jsonb, dict):
        return None
    for key in _IMAGE_EVIDENCE_KEYS:
        node = evidence_jsonb.get(key)
        if not isinstance(node, dict):
            continue
        url = node.get("fileUrl") or node.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
    return None


def _image_count(evidence_jsonb: Any) -> int:
    if not isinstance(evidence_jsonb, dict):
        return 0
    count = 0
    for key in _IMAGE_EVIDENCE_KEYS:
        node = evidence_jsonb.get(key)
        if not isinstance(node, dict):
            continue
        url = node.get("fileUrl") or node.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            count += 1
    return count


def _primary_forensic_metadata(evidence_jsonb: Any) -> Dict[str, Any]:
    """Pull the forensic sub-tree from whichever image key is present.

    Structure observed in prod: `evidence[<type>].metadata.forensic = {gps, device, capture_timestamp, source}`.
    We only surface pass-flag booleans downstream, never raw values.
    """
    if not isinstance(evidence_jsonb, dict):
        return {}
    for key in _IMAGE_EVIDENCE_KEYS:
        node = evidence_jsonb.get(key)
        if not isinstance(node, dict):
            continue
        metadata = node.get("metadata")
        if isinstance(metadata, dict):
            forensic = metadata.get("forensic")
            if isinstance(forensic, dict):
                return forensic
    return {}


def _extract_verification(
    ai_result: Any,
    evidence_metadata: Any,
    forensic: Optional[Dict[str, Any]] = None,
) -> VerificationBadges:
    """Read only the boolean pass flags. Never surface scores, reasons,
    provider names, or raw GPS/EXIF — those are internal audit data.

    Prod submissions keep forensic data at
    `evidence.<type>.metadata.forensic.{gps, capture_timestamp, ...}`.
    Presence of GPS coords or a capture timestamp is treated as "captured",
    which is what the badges signal to the public viewer.
    """
    badges = VerificationBadges()

    ai = ai_result if isinstance(ai_result, dict) else {}
    meta = evidence_metadata if isinstance(evidence_metadata, dict) else {}
    fore = forensic if isinstance(forensic, dict) else {}

    gps_meta = meta.get("gps") if isinstance(meta.get("gps"), dict) else None
    gps_fore = fore.get("gps") if isinstance(fore.get("gps"), dict) else None
    badges.gps_verified = bool(
        (
            gps_meta
            and (gps_meta.get("verified") or gps_meta.get("latitude") is not None)
        )
        or (gps_fore and gps_fore.get("latitude") is not None)
    )

    exif_meta = meta.get("exif") if isinstance(meta.get("exif"), dict) else None
    badges.exif_verified = bool(exif_meta and exif_meta.get("verified"))

    badges.timestamp_verified = bool(
        ai.get("timestamp_verified")
        or meta.get("capture_timestamp")
        or fore.get("capture_timestamp")
    )

    badges.world_id_verified = bool(
        ai.get("world_id_verified") or meta.get("world_id_verified")
    )

    return badges


def _blurhash(evidence_metadata: Any) -> Optional[str]:
    if not isinstance(evidence_metadata, dict):
        return None
    bh = evidence_metadata.get("blurhash")
    if isinstance(bh, str) and 20 <= len(bh) <= 200:
        return bh
    return None


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _serialize_item(row: Dict[str, Any]) -> Optional[ShowcaseEvidence]:
    """Convert a joined row from PostgREST into a showcase item.

    Returns None if the row is missing a displayable primary image — the
    partial index already filters most of these out, but defensively skip
    any stragglers.
    """
    task = row.get("task") or row.get("tasks") or {}
    executor = row.get("executor") or row.get("executors") or {}
    if isinstance(task, list):
        task = task[0] if task else {}
    if isinstance(executor, list):
        executor = executor[0] if executor else {}

    evidence_jsonb = row.get("evidence")
    primary = _primary_image_url(evidence_jsonb)
    if not primary:
        return None

    paid_at = _iso(row.get("paid_at"))
    if not paid_at:
        return None

    rating_raw = executor.get("avg_rating")
    try:
        rating = round(float(rating_raw), 2) if rating_raw is not None else None
    except (TypeError, ValueError):
        rating = None

    forensic = _primary_forensic_metadata(evidence_jsonb)

    return ShowcaseEvidence(
        id=str(row["id"]),
        task_title=_truncate(task.get("title"), 120),
        task_description=_truncate(task.get("instructions"), _DESCRIPTION_TRUNCATE),
        category=str(task.get("category") or "unknown"),
        bounty_usd=float(task.get("bounty_usd") or 0.0),
        payment_token=task.get("payment_token"),
        payment_network=task.get("payment_network"),
        paid_at=paid_at,
        completed_at=_iso(task.get("completed_at")),
        executor=ExecutorPreview(
            display_name=_sanitize_display_name(
                executor.get("display_name"), fallback="anonymous"
            ),
            avatar_url=executor.get("avatar_url") or None,
            rating=rating,
            kya_verified=bool(executor.get("clawkey_verified")),
        ),
        evidence=EvidencePreview(
            primary_image_url=primary,
            image_count=_image_count(evidence_jsonb),
            blurhash=_blurhash(row.get("evidence_metadata")),
            verification=_extract_verification(
                row.get("ai_verification_result"),
                row.get("evidence_metadata"),
                forensic=forensic,
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


def _build_query(
    limit: int,
    category: Optional[str],
    network: Optional[str],
    order: OrderMode,
    cursor: Optional[Dict[str, str]],
):
    client = db.get_client()

    select_expr = (
        "id,"
        "evidence,"
        "evidence_metadata,"
        "ai_verification_result,"
        "paid_at,"
        "task:tasks!inner("
        "title,instructions,category,bounty_usd,payment_token,payment_network,"
        "completed_at,status"
        "),"
        "executor:executors("
        "display_name,avatar_url,avg_rating,clawkey_verified"
        ")"
    )

    q = (
        client.table("submissions")
        .select(select_expr)
        .eq("agent_verdict", "accepted")
        .not_.is_("paid_at", "null")
        .not_.is_("evidence", "null")
        .or_("show_in_showcase.is.null,show_in_showcase.eq.true")
    )

    # Tasks must be completed — exclude submissions where the task was later
    # disputed/cancelled.
    q = q.eq("task.status", "completed")

    if category:
        q = q.eq("task.category", category)
    if network:
        q = q.eq("task.payment_network", network)

    if order == "highest_paid":
        q = q.order("task(bounty_usd)", desc=True).order("paid_at", desc=True)
    elif order == "most_verified":
        # Approximation: rely on paid_at desc + cached verification score.
        # A proper "most verified" sort needs a derived column; defer to
        # Phase 3 when /showcase has real filters.
        q = q.order("paid_at", desc=True)
    else:  # recent
        q = q.order("paid_at", desc=True).order("id", desc=True)

    if cursor:
        # Keyset pagination on (paid_at DESC, id DESC).
        paid_at = cursor["paid_at"]
        sub_id = cursor["id"]
        # PostgREST doesn't support row-value comparisons, so emulate with
        # an OR: paid_at < cursor.paid_at, or (paid_at == cursor.paid_at AND id < cursor.id).
        q = q.or_(f"paid_at.lt.{paid_at},and(paid_at.eq.{paid_at},id.lt.{sub_id})")

    # Over-fetch so we can filter out submissions whose `evidence` jsonb only
    # holds text_response / json_response (no displayable image). Factor of 3
    # covers the observed ratio (~1/3 of paid accepted submissions are
    # text-only) with headroom. The HTTP response still honours `limit`.
    q = q.limit(max((limit + 1) * 3, 15))
    return q


def _fetch_items(
    limit: int,
    category: Optional[str],
    network: Optional[str],
    order: OrderMode,
    cursor: Optional[Dict[str, str]],
) -> Tuple[List[ShowcaseEvidence], Optional[str]]:
    try:
        q = _build_query(limit, category, network, order, cursor)
        result = q.execute()
    except Exception as exc:
        logger.exception("Showcase query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Showcase unavailable") from exc

    rows = list(result.data or [])

    items: List[ShowcaseEvidence] = []
    for row in rows:
        item = _serialize_item(row)
        if item is not None:
            items.append(item)
        if len(items) > limit:
            break

    has_more = len(items) > limit
    items = items[:limit]

    next_cursor: Optional[str] = None
    if has_more and items:
        last = items[-1]
        next_cursor = _encode_cursor(last.paid_at, last.id)
    return items, next_cursor


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/evidence",
    response_model=ShowcaseResponse,
    summary="Proof Wall — accepted+paid evidence feed",
    description=(
        "Public, anonymous feed of accepted and paid submissions, stripped of PII. "
        "Backs the landing-page Evidence Carousel and the /showcase page. "
        "Cursor-paginated by (paid_at, id). Cached 60s in-process + HTTP."
    ),
)
async def get_showcase_evidence(
    response: Response,
    limit: int = Query(
        _DEFAULT_LIMIT,
        ge=1,
        le=_MAX_LIMIT,
        description=f"Items per page (max {_MAX_LIMIT})",
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by task category",
    ),
    network: Optional[str] = Query(
        default=None,
        description="Filter by payment network (e.g. base, polygon)",
    ),
    order: OrderMode = Query(
        default="recent",
        description="recent | highest_paid | most_verified",
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Opaque pagination cursor from a previous response",
    ),
) -> ShowcaseResponse:
    # Validate enum-ish filters early.
    if category is not None and category not in _ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=(f"Invalid category. Must be one of: {sorted(_ALLOWED_CATEGORIES)}"),
        )
    if network is not None and network not in _ALLOWED_NETWORKS:
        raise HTTPException(
            status_code=400,
            detail=(f"Invalid network. Must be one of: {sorted(_ALLOWED_NETWORKS)}"),
        )

    decoded_cursor = _decode_cursor(cursor) if cursor else None
    key = _cache_key(limit, category, network, order, cursor)

    cached = _RESPONSE_CACHE.get(key) if _RESPONSE_CACHE is not None else None
    if cached is None:
        items, next_cursor = _fetch_items(
            limit, category, network, order, decoded_cursor
        )
        payload = ShowcaseResponse(
            items=items,
            next_cursor=next_cursor,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        if _RESPONSE_CACHE is not None:
            _RESPONSE_CACHE[key] = payload
    else:
        payload = cached

    body_hash = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()[
        :16
    ]
    response.headers["Cache-Control"] = (
        f"public, max-age={_HTTP_CACHE_MAX_AGE}, "
        f"stale-while-revalidate={_HTTP_CACHE_SWR}"
    )
    response.headers["ETag"] = f'W/"{body_hash}"'

    return payload
