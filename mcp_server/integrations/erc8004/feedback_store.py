"""
Feedback Persistence Store for ERC-8004 Reputation

Stores feedback documents as JSON on S3, computes keccak256 hash for on-chain
reference, and provides retrieval for the /feedback/:id page.

Flow:
1. Build feedback JSON (task details, score, comment, evidence, tx hashes)
2. Upload to S3: feedback/{task_id}/{feedback_type}_{timestamp}.json
3. Compute keccak256 of the canonical JSON
4. Return (feedback_uri, feedback_hash) to pass to facilitator

The feedbackUri resolves to the public CDN URL of the JSON document.
The feedbackHash is the keccak256 digest, stored on-chain in ERC-8004 Reputation Registry.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# S3 config — same bucket as evidence uploads
FEEDBACK_BUCKET = os.environ.get("EVIDENCE_BUCKET", "")
FEEDBACK_CDN_URL = os.environ.get("EVIDENCE_PUBLIC_BASE_URL", "").rstrip("/")

# Fallback: try to derive bucket name from account
if not FEEDBACK_BUCKET:
    _acct = os.environ.get("AWS_ACCOUNT_ID", "518898403364")
    FEEDBACK_BUCKET = f"em-production-evidence-{_acct}"

# Also store feedback reference in Supabase for quick lookups
_SUPABASE_TABLE = "feedback_documents"


def _compute_keccak256(data: bytes) -> str:
    """Compute keccak256 hash of data, return as 0x-prefixed hex string."""
    try:
        from web3 import Web3

        return Web3.keccak(data).hex()
    except ImportError:
        # Fallback: use hashlib sha3_256 (not identical to keccak but close enough for test)
        import hashlib

        return "0x" + hashlib.sha3_256(data).hexdigest()


def build_feedback_document(
    task_id: str,
    feedback_type: str,
    score: int,
    rater_type: str = "agent",
    rater_id: str = "",
    target_type: str = "worker",
    target_address: str = "",
    target_agent_id: Optional[int] = None,
    comment: str = "",
    rejection_reason: str = "",
    evidence_urls: Optional[list] = None,
    submission_id: str = "",
    payment_tx: str = "",
    reputation_tx: str = "",
    network: str = "base",
    task_title: str = "",
    task_category: str = "",
    bounty_usd: float = 0.0,
) -> Dict[str, Any]:
    """
    Build a canonical feedback JSON document.

    This document is:
    - Uploaded to S3 for persistence
    - Hashed (keccak256) for on-chain verification
    - Referenced by feedbackUri in ERC-8004 Reputation Registry
    """
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "version": "1.0",
        "type": "execution_market_feedback",
        "feedback_type": feedback_type,
        "created_at": now,
        "network": network,
        "task": {
            "id": task_id,
            "title": task_title,
            "category": task_category,
            "bounty_usd": bounty_usd,
        },
        "rating": {
            "score": score,
            "max_score": 100,
            "rater_type": rater_type,
            "rater_id": rater_id,
            "target_type": target_type,
            "target_address": target_address,
        },
        "transactions": {
            "payment_tx": payment_tx,
            "reputation_tx": reputation_tx,
        },
    }

    if target_agent_id is not None:
        doc["rating"]["target_agent_id"] = target_agent_id

    if submission_id:
        doc["task"]["submission_id"] = submission_id

    if comment:
        doc["comment"] = comment

    if rejection_reason:
        doc["rejection"] = {
            "reason": rejection_reason,
            "severity": "major" if score <= 30 else "minor",
        }

    if evidence_urls:
        doc["evidence"] = evidence_urls

    return doc


def _canonical_json(doc: Dict[str, Any]) -> bytes:
    """Serialize document to canonical JSON (sorted keys, no extra whitespace)."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_feedback_hash(doc: Dict[str, Any]) -> str:
    """Compute keccak256 hash of the canonical feedback document."""
    canonical = _canonical_json(doc)
    return _compute_keccak256(canonical)


async def upload_feedback_to_s3(
    doc: Dict[str, Any],
    task_id: str,
    feedback_type: str,
) -> Optional[str]:
    """
    Upload feedback document to S3.

    Returns the public CDN URL of the uploaded document, or None on failure.
    Key format: feedback/{task_id}/{feedback_type}_{timestamp}.json
    """
    import asyncio

    if not FEEDBACK_BUCKET:
        logger.warning(
            "[feedback-store] No EVIDENCE_BUCKET configured, skipping S3 upload"
        )
        return None

    timestamp = int(time.time())
    s3_key = f"feedback/{task_id}/{feedback_type}_{timestamp}.json"
    canonical = _canonical_json(doc)

    def _do_upload():
        import boto3

        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=FEEDBACK_BUCKET,
            Key=s3_key,
            Body=canonical,
            ContentType="application/json",
            Metadata={
                "feedback-type": feedback_type,
                "task-id": task_id,
                "score": str(doc.get("rating", {}).get("score", "")),
            },
        )
        return s3_key

    try:
        key = await asyncio.to_thread(_do_upload)

        if FEEDBACK_CDN_URL:
            public_url = f"{FEEDBACK_CDN_URL}/{key}"
        else:
            public_url = f"https://{FEEDBACK_BUCKET}.s3.amazonaws.com/{key}"

        logger.info(
            "[feedback-store] Uploaded feedback: task=%s, type=%s, url=%s",
            task_id,
            feedback_type,
            public_url,
        )
        return public_url
    except Exception as exc:
        logger.error("[feedback-store] S3 upload failed: %s", exc)
        return None


async def store_feedback_reference(
    task_id: str,
    feedback_type: str,
    feedback_uri: str,
    feedback_hash: str,
    score: int,
    reputation_tx: str = "",
) -> None:
    """
    Store a reference to the feedback document in Supabase for quick lookups.
    Best-effort — table may not exist yet.
    """
    try:
        from supabase_client import get_client

        client = get_client()
        client.table(_SUPABASE_TABLE).insert(
            {
                "task_id": task_id,
                "feedback_type": feedback_type,
                "feedback_uri": feedback_uri,
                "feedback_hash": feedback_hash,
                "score": score,
                "reputation_tx": reputation_tx,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as exc:
        logger.debug("[feedback-store] Could not store reference in DB: %s", exc)


async def get_feedback_document(
    task_id: str, feedback_type: Optional[str] = None
) -> Optional[Dict]:
    """
    Retrieve a feedback document from S3.

    Tries Supabase lookup first (for the S3 key), falls back to listing S3 prefix.
    """
    import asyncio

    # Try Supabase lookup first
    try:
        from supabase_client import get_client

        client = get_client()
        query = (
            client.table(_SUPABASE_TABLE).select("feedback_uri").eq("task_id", task_id)
        )
        if feedback_type:
            query = query.eq("feedback_type", feedback_type)
        result = query.order("created_at", desc=True).limit(1).execute()

        if result.data and result.data[0].get("feedback_uri"):
            uri = result.data[0]["feedback_uri"]
            # Extract S3 key from CDN URL
            if FEEDBACK_CDN_URL and uri.startswith(FEEDBACK_CDN_URL):
                s3_key = uri[len(FEEDBACK_CDN_URL) :].lstrip("/")
            elif ".s3.amazonaws.com/" in uri:
                s3_key = uri.split(".s3.amazonaws.com/", 1)[1]
            else:
                s3_key = None

            if s3_key:
                return await _fetch_from_s3(s3_key)
    except Exception:
        pass

    # Fallback: list S3 prefix
    prefix = f"feedback/{task_id}/"
    if feedback_type:
        prefix = f"feedback/{task_id}/{feedback_type}_"

    def _list_and_fetch():
        import boto3

        s3 = boto3.client("s3")
        resp = s3.list_objects_v2(Bucket=FEEDBACK_BUCKET, Prefix=prefix, MaxKeys=5)
        contents = resp.get("Contents", [])
        if not contents:
            return None
        # Get most recent
        contents.sort(key=lambda x: x.get("LastModified", ""), reverse=True)
        key = contents[0]["Key"]
        obj = s3.get_object(Bucket=FEEDBACK_BUCKET, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))

    try:
        return await asyncio.to_thread(_list_and_fetch)
    except Exception as exc:
        logger.debug("[feedback-store] S3 fetch failed: %s", exc)
        return None


async def _fetch_from_s3(s3_key: str) -> Optional[Dict]:
    """Fetch a JSON document from S3 by key."""
    import asyncio

    def _do_fetch():
        import boto3

        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=FEEDBACK_BUCKET, Key=s3_key)
        return json.loads(obj["Body"].read().decode("utf-8"))

    try:
        return await asyncio.to_thread(_do_fetch)
    except Exception as exc:
        logger.debug("[feedback-store] S3 fetch failed for %s: %s", s3_key, exc)
        return None


async def persist_and_hash_feedback(
    task_id: str,
    feedback_type: str,
    score: int,
    **kwargs,
) -> tuple[str, str]:
    """
    High-level helper: build document → upload to S3 → compute hash → store reference.

    Returns:
        (feedback_uri, feedback_hash) tuple.
        feedback_uri: CDN URL of the JSON, or fallback URL if S3 fails.
        feedback_hash: keccak256 hex string (0x-prefixed).
    """
    doc = build_feedback_document(
        task_id=task_id,
        feedback_type=feedback_type,
        score=score,
        **kwargs,
    )

    feedback_hash = compute_feedback_hash(doc)

    feedback_uri = await upload_feedback_to_s3(doc, task_id, feedback_type)

    if not feedback_uri:
        # Fallback: use API endpoint as feedbackUri
        feedback_uri = (
            f"https://api.execution.market/api/v1/reputation/feedback/{task_id}"
        )

    # Store reference in Supabase (best-effort)
    await store_feedback_reference(
        task_id=task_id,
        feedback_type=feedback_type,
        feedback_uri=feedback_uri,
        feedback_hash=feedback_hash,
        score=score,
    )

    return feedback_uri, feedback_hash
