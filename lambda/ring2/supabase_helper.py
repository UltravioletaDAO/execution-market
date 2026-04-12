"""
Supabase Helper for Ring 2 Lambda.

Provides lightweight Supabase access for the Lambda environment.
Secrets are loaded from AWS Secrets Manager at cold start and cached
globally for the lifetime of the Lambda container.

This module replaces the ECS-oriented supabase_client.py and
config.platform_config.PlatformConfig with Lambda-compatible versions
that read credentials from Secrets Manager instead of env vars.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
from supabase import Client, create_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global cache (persists across warm Lambda invocations)
# ---------------------------------------------------------------------------

_secrets_cache: Dict[str, Dict[str, str]] = {}
_supabase_client: Optional[Client] = None


# ---------------------------------------------------------------------------
# Secrets Manager
# ---------------------------------------------------------------------------

_REGION = os.environ.get("AWS_REGION", "us-east-2")


def _get_secret(secret_id: str) -> Dict[str, str]:
    """Fetch a secret from AWS Secrets Manager (cached per cold start).

    Args:
        secret_id: The Secrets Manager secret name (e.g. ``em/supabase``).

    Returns:
        Parsed JSON dict of key-value pairs.

    Raises:
        RuntimeError: If the secret cannot be fetched.
    """
    if secret_id in _secrets_cache:
        return _secrets_cache[secret_id]

    logger.info("Fetching secret %s from Secrets Manager (cold start)", secret_id)
    try:
        client = boto3.client("secretsmanager", region_name=_REGION)
        response = client.get_secret_value(SecretId=secret_id)
        parsed = json.loads(response["SecretString"])
        _secrets_cache[secret_id] = parsed
        return parsed
    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch secret '{secret_id}' from Secrets Manager: {e}"
        ) from e


def load_secrets() -> None:
    """Load all required secrets into environment variables.

    Called once at cold start. Sets env vars so that downstream modules
    (supabase_client.py, arbiter providers) can read them normally.

    Required secrets:
        em/supabase  -> SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
        em/openrouter -> OPENROUTER_API_KEY
    """
    # Supabase credentials
    supabase_secrets = _get_secret("em/supabase")
    os.environ.setdefault("SUPABASE_URL", supabase_secrets.get("SUPABASE_URL", ""))
    os.environ.setdefault(
        "SUPABASE_SERVICE_ROLE_KEY",
        supabase_secrets.get("SUPABASE_SERVICE_ROLE_KEY", ""),
    )

    # OpenRouter API key (for Ring 2 LLM inference)
    try:
        openrouter_secrets = _get_secret("em/openrouter")
        os.environ.setdefault(
            "OPENROUTER_API_KEY", openrouter_secrets.get("OPENROUTER_API_KEY", "")
        )
    except RuntimeError:
        logger.warning(
            "em/openrouter secret not available -- Ring 2 LLM inference may fail"
        )

    logger.info("Secrets loaded into environment")


# ---------------------------------------------------------------------------
# Supabase Client
# ---------------------------------------------------------------------------


def get_client() -> Client:
    """Get or create a Supabase client (lazy singleton).

    Uses service role key to bypass RLS (same as ECS server).
    """
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get(
            "SUPABASE_ANON_KEY", ""
        )
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set. "
                "Call load_secrets() first."
            )
        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized for Lambda")
    return _supabase_client


# ---------------------------------------------------------------------------
# Submission helpers
# ---------------------------------------------------------------------------


def get_submission(submission_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a submission row by ID.

    Returns None if not found.
    """
    client = get_client()
    result = client.table("submissions").select("*").eq("id", submission_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a task row by ID.

    Returns None if not found.
    """
    client = get_client()
    result = client.table("tasks").select("*").eq("id", task_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None


def is_arbiter_enabled() -> bool:
    """Check the feature.arbiter_enabled master switch in platform_config.

    Returns False if the key is missing or the query fails (fail-closed).
    """
    try:
        client = get_client()
        result = (
            client.table("platform_config")
            .select("value")
            .eq("key", "feature.arbiter_enabled")
            .execute()
        )
        if result.data and len(result.data) > 0:
            raw = result.data[0].get("value")
            # platform_config stores JSONB -- value may be bool or string
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str):
                return raw.strip().lower() in ("true", "1", "yes")
            return bool(raw)
    except Exception as e:
        logger.warning(
            "Failed to read arbiter master switch: %s -- defaulting to disabled", e
        )
    return False


def update_submission_verdict(submission_id: str, update_data: Dict[str, Any]) -> bool:
    """Update submissions table with arbiter verdict fields.

    Returns True on success, False on failure.
    """
    try:
        client = get_client()
        client.table("submissions").update(update_data).eq(
            "id", submission_id
        ).execute()
        return True
    except Exception as e:
        logger.error(
            "Failed to update submission %s with verdict: %s", submission_id, e
        )
        return False


def create_dispute(dispute_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a dispute row for L2 human arbiter escalation.

    Returns the created row, or None on failure.
    """
    try:
        client = get_client()
        result = client.table("disputes").insert(dispute_data).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.error("Failed to create dispute: %s", e)
        return None


def mark_submission_disputed(submission_id: str, dispute_id: str) -> None:
    """Mark a submission as disputed after L2 escalation."""
    try:
        client = get_client()
        client.table("submissions").update(
            {
                "agent_verdict": "disputed",
                "agent_notes": (
                    f"Escalated to L2 human arbiter (dispute={dispute_id}). "
                    f"Ring 2 verdict: INCONCLUSIVE."
                ),
            }
        ).eq("id", submission_id).execute()
    except Exception as e:
        logger.warning("Failed to mark submission %s as disputed: %s", submission_id, e)


def write_error_to_submission(submission_id: str, error_msg: str) -> None:
    """Write a permanent error to the submission for ops visibility.

    Called when arbiter evaluation fails with a non-retryable error.
    """
    try:
        client = get_client()
        client.table("submissions").update(
            {
                "arbiter_verdict": "error",
                "arbiter_verdict_data": {
                    "error": error_msg[:1000],
                    "source": "ring2_lambda",
                },
            }
        ).eq("id", submission_id).execute()
    except Exception as e:
        logger.error("Failed to write error to submission %s: %s", submission_id, e)
