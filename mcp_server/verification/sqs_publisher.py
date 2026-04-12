"""SQS publisher for verification pipeline.

The submit endpoint publishes to SQS. Lambda workers process Ring 1
(PHOTINT) and Ring 2 (Arbiter) messages.  This is the only verification
path — the legacy asyncio.create_task() path was removed in Phase 5.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

_sqs_client = None


def _get_sqs():
    """Lazy-initialise the SQS client (singleton)."""
    global _sqs_client
    if _sqs_client is None:
        _sqs_client = boto3.client(
            "sqs",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-2"),
        )
    return _sqs_client


def is_sqs_mode() -> bool:
    """Return True. SQS is the only verification backend since Phase 5.

    Kept for backward compatibility with any code that still checks.
    """
    return True


def _serialise_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the task fields needed by Lambda verifiers.

    Keeps the message small and avoids leaking full DB rows into SQS.
    """
    return {
        "id": task.get("id"),
        "category": task.get("category"),
        "title": task.get("title"),
        "instructions": task.get("instructions", ""),
        "bounty_usd": float(task.get("bounty_usd", 0)),
        "evidence_schema": task.get("evidence_schema"),
        "location_lat": task.get("location_lat"),
        "location_lng": task.get("location_lng"),
        "deadline": task.get("deadline"),
        "arbiter_enabled": task.get("arbiter_enabled", False),
        "arbiter_mode": task.get("arbiter_mode"),
    }


async def publish_ring1(
    *,
    submission_id: str,
    task_id: str,
    submission: Dict[str, Any],
    task: Dict[str, Any],
    photo_urls: List[str],
    phase_a_result: Optional[Dict[str, Any]],
) -> bool:
    """Publish a Ring 1 verification job to SQS.

    Returns True on success, False on failure.
    """
    queue_url = os.environ.get("RING1_QUEUE_URL")
    if not queue_url:
        logger.error("RING1_QUEUE_URL not set -- cannot publish to SQS")
        return False

    message: Dict[str, Any] = {
        "version": "1",
        "ring": "ring1",
        "submission_id": submission_id,
        "task_id": task_id,
        "evidence": submission.get("evidence") or {},
        "submitted_at": submission.get("submitted_at"),
        "notes": submission.get("notes"),
        "task": _serialise_task(task),
        "photo_urls": photo_urls,
        "phase_a_result": phase_a_result,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        _get_sqs().send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message, default=str),
        )
        logger.info(
            "Ring 1 published to SQS: submission=%s task=%s",
            submission_id,
            task_id,
        )
        return True
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to publish Ring 1 to SQS: %s", exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error publishing Ring 1 to SQS: %s", exc)
        return False


async def publish_ring2(
    *,
    submission_id: str,
    task_id: str,
    submission: Dict[str, Any],
    task: Dict[str, Any],
    photo_urls: List[str],
) -> bool:
    """Publish a Ring 2 (Arbiter) verification job to SQS.

    Returns True on success, False on failure.
    """
    queue_url = os.environ.get("RING2_QUEUE_URL")
    if not queue_url:
        logger.error("RING2_QUEUE_URL not set -- cannot publish Ring 2 to SQS")
        return False

    message: Dict[str, Any] = {
        "version": "1",
        "ring": "ring2",
        "submission_id": submission_id,
        "task_id": task_id,
        "evidence": submission.get("evidence") or {},
        "submitted_at": submission.get("submitted_at"),
        "task": _serialise_task(task),
        "photo_urls": photo_urls,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        _get_sqs().send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message, default=str),
        )
        logger.info(
            "Ring 2 published to SQS: submission=%s task=%s",
            submission_id,
            task_id,
        )
        return True
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to publish Ring 2 to SQS: %s", exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error publishing Ring 2 to SQS: %s", exc)
        return False
