"""
Ring 1 PHOTINT Verification Lambda Handler.

Receives SQS messages containing submission evidence metadata, runs the
full PHOTINT pipeline (EXIF, tampering, GenAI, photo-source, duplicate,
AI semantic), merges with Phase A results, and writes back to Supabase.
On success, publishes a summary message to the Ring 2 SQS queue.

Replaces the in-process ``asyncio.create_task()`` from background_runner.py
with a proper SQS-triggered Lambda for reliability and isolation.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import boto3
import httpx

logger = logging.getLogger()
logger.setLevel("INFO")

# ── Module-level cold-start caches ───────────────────────────────────────

_secrets_loaded = False
_google_api_key: Optional[str] = None
_openai_api_key: Optional[str] = None
_anthropic_api_key: Optional[str] = None
_sqs_client = None

# Ring 2 queue URL — set via environment variable.
RING2_QUEUE_URL = os.environ.get("RING2_QUEUE_URL", "")

# Image download limits.
MAX_IMAGES = 2
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
IMAGE_DOWNLOAD_TIMEOUT = 10.0  # seconds per image

# Per-check timeouts (seconds).
CHECK_TIMEOUT_DEFAULT = 60
CHECK_TIMEOUT_AI = 120


# ── Secrets loading ──────────────────────────────────────────────────────


def _load_secrets() -> None:
    """Load secrets from AWS Secrets Manager on first invocation.

    Caches in module globals so subsequent warm invocations skip the call.
    Injects values into ``os.environ`` so downstream verification modules
    (providers.py, ai_review.py) can read them via their normal env-var
    lookups without modification.
    """
    global _secrets_loaded, _google_api_key, _openai_api_key, _anthropic_api_key

    if _secrets_loaded:
        return

    sm = boto3.client("secretsmanager")

    def _get(secret_id: str) -> Dict[str, str]:
        raw = sm.get_secret_value(SecretId=secret_id)["SecretString"]
        return json.loads(raw)

    # Supabase
    sb = _get("em/supabase")
    supabase_url = sb.get("SUPABASE_URL", "")
    supabase_key = sb.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "em/supabase secret missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"
        )

    # Initialise supabase_helper with the loaded creds.
    import supabase_helper

    supabase_helper.init(supabase_url, supabase_key)

    # AI providers — set into env so verification.providers picks them up.
    try:
        google = _get("em/google")
        _google_api_key = google.get("GOOGLE_API_KEY", "")
        if _google_api_key:
            os.environ["GOOGLE_API_KEY"] = _google_api_key
    except Exception as e:
        logger.warning("Failed to load em/google secret: %s", e)

    try:
        openai_sec = _get("em/openai")
        _openai_api_key = openai_sec.get("OPENAI_API_KEY", "")
        if _openai_api_key:
            os.environ["OPENAI_API_KEY"] = _openai_api_key
    except Exception as e:
        logger.warning("Failed to load em/openai secret: %s", e)

    try:
        anthropic_sec = _get("em/anthropic")
        _anthropic_api_key = anthropic_sec.get("ANTHROPIC_API_KEY", "")
        if _anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = _anthropic_api_key
    except Exception as e:
        logger.warning("Failed to load em/anthropic secret: %s", e)

    _secrets_loaded = True
    logger.info(
        "Secrets loaded: supabase=set google=%s openai=%s anthropic=%s",
        "set" if _google_api_key else "unset",
        "set" if _openai_api_key else "unset",
        "set" if _anthropic_api_key else "unset",
    )


# ── Image download ───────────────────────────────────────────────────────


async def _download_images(photo_urls: List[str]) -> List[Tuple[str, bytes]]:
    """Download up to MAX_IMAGES images, enforcing size and timeout limits.

    Returns list of ``(url, image_bytes)`` for successful downloads.
    """
    downloaded: List[Tuple[str, bytes]] = []
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(IMAGE_DOWNLOAD_TIMEOUT)
    ) as client:
        for url in photo_urls[:MAX_IMAGES]:
            try:
                r = await client.get(url)
                r.raise_for_status()
                data = r.content
                if len(data) > MAX_IMAGE_BYTES:
                    logger.warning(
                        "Image too large (%d bytes > %d), skipping: %s",
                        len(data),
                        MAX_IMAGE_BYTES,
                        url[:120],
                    )
                    continue
                downloaded.append((url, data))
                logger.info(
                    "Downloaded image %d/%d: %d bytes from %s",
                    len(downloaded),
                    MAX_IMAGES,
                    len(data),
                    url[:120],
                )
            except Exception as e:
                logger.warning("Failed to download image %s: %s", url[:120], e)
    return downloaded


def _write_temp_files(images: List[Tuple[str, bytes]]) -> List[str]:
    """Write downloaded image bytes to temp files. Returns list of file paths."""
    paths: List[str] = []
    for url, data in images:
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".webp" in url.lower():
            ext = ".webp"
        fd, path = tempfile.mkstemp(suffix=ext, prefix="ring1_")
        os.write(fd, data)
        os.close(fd)
        paths.append(path)
    return paths


def _cleanup_temp_files(paths: List[str]) -> None:
    """Remove temporary image files."""
    for p in paths:
        try:
            os.unlink(p)
        except OSError:
            pass


# ── Individual check runners ─────────────────────────────────────────────
# Mirror the structure from background_runner.py but import from the
# copied verification package.


async def _run_exif_check(
    temp_paths: List[str],
) -> Tuple[str, dict]:
    """Extract EXIF metadata from the first image.

    Returns ``(exif_context_str, exif_metadata_dict)``.
    """
    from verification.exif_extractor import extract_exif

    exif_context = ""
    exif_metadata: dict = {}
    if not temp_paths:
        return exif_context, exif_metadata

    try:
        exif_data = extract_exif(temp_paths[0])
        exif_context = exif_data.to_prompt_context()
        exif_metadata = {
            "camera": f"{exif_data.camera_make or ''} {exif_data.camera_model or ''}".strip(),
            "gps": (
                f"{exif_data.gps_latitude},{exif_data.gps_longitude}"
                if exif_data.gps_latitude
                else None
            ),
            "has_exif": exif_data.has_exif,
            "metadata_stripped": exif_data.metadata_stripped,
            "has_editing_software": exif_data.has_editing_software,
            "container": exif_data.container_type,
            "resolution": f"{exif_data.width}x{exif_data.height}"
            if exif_data.width
            else None,
            "megapixels": exif_data.megapixels,
        }
        logger.info(
            "EXIF extracted: has_exif=%s stripped=%s editing=%s",
            exif_data.has_exif,
            exif_data.metadata_stripped,
            exif_data.has_editing_software,
        )
    except Exception as e:
        logger.warning("EXIF extraction failed: %s", e)

    return exif_context, exif_metadata


async def _run_tampering_check(temp_paths: List[str]) -> Any:
    """Run tampering detection on the first image."""
    from verification.checks.tampering import check_tampering
    from verification.pipeline import CheckResult

    if not temp_paths:
        return CheckResult(
            name="tampering", passed=True, score=0.5, reason="No images to check"
        )

    try:
        result = check_tampering(temp_paths[0])
        score = max(0.0, 1.0 - result.confidence) if result.is_suspicious else 1.0
        return CheckResult(
            name="tampering",
            passed=not result.is_suspicious,
            score=round(score, 3),
            reason=result.reason or "No tampering detected",
            details={
                "is_suspicious": result.is_suspicious,
                "confidence": result.confidence,
                "signals": result.signals[:5],
            },
        )
    except Exception as e:
        logger.warning("Tampering check failed: %s", e)
        return CheckResult(
            name="tampering",
            passed=True,
            score=0.5,
            reason=f"Tampering check failed: {e}",
        )


async def _run_genai_check(temp_paths: List[str]) -> Any:
    """Detect AI-generated images."""
    from verification.checks.genai import check_genai
    from verification.pipeline import CheckResult

    if not temp_paths:
        return CheckResult(
            name="genai_detection", passed=True, score=0.5, reason="No images to check"
        )

    try:
        result = check_genai(temp_paths[0])
        if result.is_ai_generated:
            score = max(0.1, 1.0 - result.confidence)
        else:
            score = min(1.0, 0.7 + result.confidence * 0.3)
        return CheckResult(
            name="genai_detection",
            passed=not result.is_ai_generated,
            score=round(score, 3),
            reason=result.reason or "No AI generation detected",
            details={
                "is_ai_generated": result.is_ai_generated,
                "confidence": result.confidence,
                "model_hint": result.model_hint,
                "signals": result.signals[:5],
            },
        )
    except Exception as e:
        logger.warning("GenAI detection failed: %s", e)
        return CheckResult(
            name="genai_detection",
            passed=True,
            score=0.5,
            reason=f"GenAI detection failed: {e}",
        )


async def _run_photo_source_check(
    temp_paths: List[str],
    category: str,
) -> Any:
    """Verify photo source (camera vs gallery vs screenshot)."""
    from verification.checks.photo_source import check_photo_source
    from verification.pipeline import CheckResult

    if not temp_paths:
        return CheckResult(
            name="photo_source", passed=True, score=0.5, reason="No images to check"
        )

    try:
        result = check_photo_source(temp_paths[0], max_age_minutes=60)
        source_scores = {
            "camera": 1.0,
            "screenshot": 0.1,
            "gallery": 0.3,
            "unknown": 0.4,
            "error": 0.5,
        }
        score = source_scores.get(result.source, 0.4)
        if result.source == "gallery" and category not in (
            "physical_presence",
            "simple_action",
        ):
            score = 0.6
        return CheckResult(
            name="photo_source",
            passed=result.is_valid,
            score=round(score, 3),
            reason=result.reason or f"Photo source: {result.source}",
            details={
                "source": result.source,
                "timestamp": result.timestamp.isoformat() if result.timestamp else None,
            },
        )
    except Exception as e:
        logger.warning("Photo source check failed: %s", e)
        return CheckResult(
            name="photo_source",
            passed=True,
            score=0.5,
            reason=f"Photo source check failed: {e}",
        )


async def _run_duplicate_check(
    temp_paths: List[str],
    submission_id: str,
    task_id: str,
) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """Check for duplicate images using perceptual hashing.

    Returns ``(CheckResult, hashes_dict_or_None)``.
    """
    from verification.checks.duplicate import DuplicateDetector
    from verification.pipeline import CheckResult

    import supabase_helper

    if not temp_paths:
        return (
            CheckResult(
                name="duplicate", passed=True, score=0.5, reason="No images to check"
            ),
            None,
        )

    try:
        detector = DuplicateDetector(similarity_threshold=0.85)
        phash, dhash, ahash = detector.compute_hash(temp_paths[0])

        existing_rows = await supabase_helper.get_existing_perceptual_hashes(
            exclude_task_id=task_id, limit=100
        )
        best_similarity = 0.0
        match_id = None
        for row in existing_rows:
            hashes = row.get("hashes", {})
            if hashes.get("phash") and hashes.get("dhash") and hashes.get("ahash"):
                similarity = detector.compute_similarity(
                    (phash, dhash, ahash),
                    (hashes["phash"], hashes["dhash"], hashes["ahash"]),
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    match_id = row["id"]

        is_duplicate = best_similarity >= 0.85
        score = 0.0 if is_duplicate else 1.0
        reason = (
            f"Duplicate detected ({best_similarity * 100:.0f}% similar to {match_id})"
            if is_duplicate
            else "No duplicates found"
        )
        hashes_dict = {"phash": phash, "dhash": dhash, "ahash": ahash}

        return (
            CheckResult(
                name="duplicate",
                passed=not is_duplicate,
                score=score,
                reason=reason,
                details={
                    "is_duplicate": is_duplicate,
                    "similarity": round(best_similarity, 3),
                    "match_id": match_id,
                },
            ),
            hashes_dict,
        )
    except Exception as e:
        logger.warning("Duplicate check failed: %s", e)
        return (
            CheckResult(
                name="duplicate",
                passed=True,
                score=0.5,
                reason=f"Duplicate check failed: {e}",
            ),
            None,
        )


async def _run_ai_semantic_check(
    task: Dict[str, Any],
    evidence: Dict[str, Any],
    photo_urls: List[str],
    exif_context: str,
    temp_paths: List[str],
) -> Any:
    """Run AI vision verification with the model router."""
    from verification.ai_review import AIVerifier, VerificationDecision
    from verification.pipeline import CheckResult

    try:
        verifier = AIVerifier()
        if not verifier.is_available:
            logger.warning("No AI verification provider available")
            return CheckResult(
                name="ai_semantic",
                passed=True,
                score=0.5,
                reason="No AI verification provider available",
                details={"provider": "none"},
            )

        result = await verifier.verify_evidence(
            task=task,
            evidence=evidence,
            photo_urls=photo_urls,
            exif_context=exif_context,
        )
        score = (
            result.confidence
            if result.decision == VerificationDecision.APPROVED
            else (1.0 - result.confidence)
        )
        passed = result.decision in (
            VerificationDecision.APPROVED,
            VerificationDecision.NEEDS_HUMAN,
        )

        return CheckResult(
            name="ai_semantic",
            passed=passed,
            score=round(score, 3),
            reason=result.explanation[:500],
            details={
                "decision": result.decision.value,
                "confidence": result.confidence,
                "issues": result.issues[:5],
                "provider": result.provider,
                "model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
        )
    except Exception as e:
        logger.warning("AI semantic check failed: %s", e, exc_info=True)
        return CheckResult(
            name="ai_semantic",
            passed=True,
            score=0.5,
            reason=f"AI semantic check failed: {e}",
        )


# ── Ring 2 publish ───────────────────────────────────────────────────────


def _publish_to_ring2(
    submission_id: str,
    task_id: str,
    ring1_result: Dict[str, Any],
) -> None:
    """Send summary message to Ring 2 SQS queue for arbiter evaluation."""
    global _sqs_client

    if not RING2_QUEUE_URL:
        logger.info("RING2_QUEUE_URL not set, skipping Ring 2 publish")
        return

    if _sqs_client is None:
        _sqs_client = boto3.client("sqs")

    body = {
        "submission_id": submission_id,
        "task_id": task_id,
        "ring1_result": {
            "passed": ring1_result.get("passed", False),
            "score": ring1_result.get("score", 0.0),
            "phase": ring1_result.get("phase", "AB"),
            "checks_count": len(ring1_result.get("checks", [])),
        },
        "enqueued_at": time.time(),
    }

    _sqs_client.send_message(
        QueueUrl=RING2_QUEUE_URL,
        MessageBody=json.dumps(body),
        MessageGroupId=submission_id if ".fifo" in RING2_QUEUE_URL else None,
    )
    logger.info(
        "Published to Ring 2: submission=%s score=%.3f",
        submission_id[:8],
        ring1_result.get("score", 0),
    )


# ── Core pipeline ────────────────────────────────────────────────────────


async def _process_submission(body: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full Ring 1 PHOTINT pipeline for one submission.

    Returns a dict summarising the outcome for the Lambda response.
    """
    import supabase_helper
    from verification.pipeline import CheckResult, merge_phase_b

    submission_id = body.get("submission_id", "")
    task_id = body.get("task_id", "")
    evidence = body.get("evidence") or {}
    task = body.get("task") or {}
    photo_urls: List[str] = body.get("photo_urls") or []
    phase_a_result: Dict[str, Any] = body.get("phase_a_result") or {}

    sid = submission_id[:8]
    logger.info(
        "[Ring1 %s] START task=%s photos=%d",
        sid,
        task_id[:8] if task_id else "?",
        len(photo_urls),
    )

    # ── 1. Idempotency check ────────────────────────────────────────
    try:
        existing = await supabase_helper.get_submission(submission_id)
    except Exception as e:
        # Supabase unreachable — transient error, let SQS retry.
        logger.error("[Ring1 %s] Supabase read failed (transient): %s", sid, e)
        raise

    if existing:
        details = existing.get("auto_check_details") or {}
        if details.get("ring1_status") == "complete":
            logger.info("[Ring1 %s] Already complete, skipping (idempotent)", sid)
            return {
                "submission_id": submission_id,
                "status": "skipped",
                "reason": "already_complete",
            }
    else:
        # Submission not found — permanent error, do not retry.
        logger.error("[Ring1 %s] Submission not found in DB", sid)
        return {
            "submission_id": submission_id,
            "status": "error",
            "reason": "submission_not_found",
        }

    # ── 2. Validate inputs ──────────────────────────────────────────
    if not photo_urls:
        # No photos — permanent error.  Write error to DB and succeed
        # so SQS deletes the message.
        logger.warning("[Ring1 %s] No photo URLs in message", sid)
        await _write_error(
            submission_id, phase_a_result, "No photo URLs in SQS message"
        )
        return {
            "submission_id": submission_id,
            "status": "error",
            "reason": "no_photos",
        }

    # ── 3. Mark ring1 as running ────────────────────────────────────
    try:
        running_details = {**(phase_a_result or {}), "ring1_status": "running"}
        await supabase_helper.update_auto_check(
            submission_id, phase_a_result.get("passed", False), running_details
        )
    except Exception as e:
        logger.warning("[Ring1 %s] Failed to mark running: %s", sid, e)

    # ── 4. Download images ──────────────────────────────────────────
    downloaded = await _download_images(photo_urls)
    if not downloaded:
        logger.warning("[Ring1 %s] No images downloaded", sid)
        await _write_error(
            submission_id, phase_a_result, "Could not download any evidence images"
        )
        return {
            "submission_id": submission_id,
            "status": "error",
            "reason": "download_failed",
        }

    temp_paths = _write_temp_files(downloaded)
    logger.info("[Ring1 %s] Downloaded %d images to temp", sid, len(temp_paths))

    try:
        # ── 5. EXIF extraction (not a scored check, feeds AI) ───────
        exif_context, exif_metadata = await _run_exif_check(temp_paths)

        # ── 6. Run 5 checks concurrently with timeouts ─────────────
        category = task.get("category", "")
        check_coros = {
            "tampering": asyncio.wait_for(
                _run_tampering_check(temp_paths), timeout=CHECK_TIMEOUT_DEFAULT
            ),
            "genai_detection": asyncio.wait_for(
                _run_genai_check(temp_paths), timeout=CHECK_TIMEOUT_DEFAULT
            ),
            "photo_source": asyncio.wait_for(
                _run_photo_source_check(temp_paths, category),
                timeout=CHECK_TIMEOUT_DEFAULT,
            ),
            "duplicate": asyncio.wait_for(
                _run_duplicate_check(temp_paths, submission_id, task_id),
                timeout=CHECK_TIMEOUT_DEFAULT,
            ),
            "ai_semantic": asyncio.wait_for(
                _run_ai_semantic_check(
                    task, evidence, photo_urls, exif_context, temp_paths
                ),
                timeout=CHECK_TIMEOUT_AI,
            ),
        }

        results: Dict[str, Any] = {}
        gathered = await asyncio.gather(
            *[_run_named_check(name, coro) for name, coro in check_coros.items()],
            return_exceptions=False,
        )
        for name, outcome in zip(check_coros.keys(), gathered):
            results[name] = outcome

        # ── 7. Collect results ──────────────────────────────────────
        phase_b_checks: List[CheckResult] = []
        perceptual_hashes: Optional[Dict[str, Any]] = None

        for name, result in results.items():
            if isinstance(result, Exception):
                logger.warning("[Ring1 %s] check '%s' FAILED: %s", sid, name, result)
                continue
            if isinstance(result, tuple):
                # duplicate check returns (CheckResult, hashes_dict)
                check_result, hashes = result
                phase_b_checks.append(check_result)
                if hashes:
                    perceptual_hashes = hashes
            elif isinstance(result, CheckResult):
                phase_b_checks.append(result)

        logger.info(
            "[Ring1 %s] checks done: %d/5 succeeded (%s)",
            sid,
            len(phase_b_checks),
            ", ".join(c.name for c in phase_b_checks),
        )

        if not phase_b_checks:
            logger.warning("[Ring1 %s] ALL checks failed", sid)
            await _write_error(
                submission_id, phase_a_result, "All Ring 1 checks failed"
            )
            return {
                "submission_id": submission_id,
                "status": "error",
                "reason": "all_checks_failed",
            }

        # ── 8. Merge Phase A + B ────────────────────────────────────
        merged = merge_phase_b(phase_a_result, phase_b_checks)
        merged["ring1_status"] = "complete"
        merged["ring1_exif"] = exif_metadata

        logger.info(
            "[Ring1 %s] merged: passed=%s score=%.3f phase=%s checks=%d",
            sid,
            merged["passed"],
            merged["score"],
            merged["phase"],
            len(merged.get("checks", [])),
        )

        # ── 9. Write to Supabase ───────────────────────────────────
        try:
            await supabase_helper.update_auto_check(
                submission_id, merged["passed"], merged
            )
        except Exception as e:
            # Supabase write failed — transient, let SQS retry.
            logger.error("[Ring1 %s] DB write failed (transient): %s", sid, e)
            raise

        # AI verification result (separate column).
        ai_check = next((c for c in phase_b_checks if c.name == "ai_semantic"), None)
        if ai_check:
            try:
                await supabase_helper.update_ai_verification(
                    submission_id,
                    {
                        "score": ai_check.score,
                        "passed": ai_check.passed,
                        "reason": ai_check.reason,
                        "details": ai_check.details,
                    },
                )
            except Exception as e:
                logger.warning("[Ring1 %s] Failed to write ai_verification: %s", sid, e)

        # Perceptual hashes.
        if perceptual_hashes:
            try:
                await supabase_helper.update_perceptual_hashes(
                    submission_id, perceptual_hashes
                )
            except Exception as e:
                logger.warning(
                    "[Ring1 %s] Failed to write perceptual_hashes: %s", sid, e
                )

        # ── 10. Publish to Ring 2 ──────────────────────────────────
        try:
            _publish_to_ring2(submission_id, task_id, merged)
        except Exception as e:
            # Ring 2 publish is best-effort.  Ring 2 can also be launched
            # independently by reading completed Ring 1 results from DB.
            logger.warning("[Ring1 %s] Ring 2 publish failed: %s", sid, e)

        logger.info(
            "[Ring1 %s] COMPLETE: passed=%s score=%.3f",
            sid,
            merged["passed"],
            merged["score"],
        )
        return {
            "submission_id": submission_id,
            "status": "complete",
            "passed": merged["passed"],
            "score": merged["score"],
        }

    finally:
        _cleanup_temp_files(temp_paths)


async def _run_named_check(name: str, coro) -> Any:
    """Execute a coroutine, catching timeouts and returning exceptions as values."""
    try:
        return await coro
    except asyncio.TimeoutError:
        logger.error("Check '%s' timed out", name)
        return TimeoutError(f"{name} timed out")
    except Exception as e:
        logger.error("Check '%s' raised: %s", name, e, exc_info=True)
        return e


async def _write_error(
    submission_id: str,
    phase_a_result: Dict[str, Any],
    error_msg: str,
) -> None:
    """Write a Ring 1 error to Supabase so the dashboard can display it."""
    import supabase_helper

    try:
        details = {
            **(phase_a_result or {}),
            "ring1_status": "error",
            "ring1_error": error_msg,
        }
        await supabase_helper.update_auto_check(
            submission_id,
            phase_a_result.get("passed", False),
            details,
        )
    except Exception as e:
        logger.error("Failed to write Ring 1 error for %s: %s", submission_id[:8], e)


# ── Lambda entry point ───────────────────────────────────────────────────


def lambda_handler(event, context):
    """Process Ring 1 verification messages from SQS.

    Expects exactly 1 record per invocation (Lambda batch size = 1).
    """
    _load_secrets()

    records = event.get("Records", [])
    logger.info("Ring 1 handler: received %d record(s)", len(records))

    if not records:
        return {"statusCode": 200, "body": json.dumps({"processed": 0})}

    # Process first record (batch size should be 1).
    record = records[0]
    try:
        body = json.loads(record["body"])
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Malformed SQS message: %s", e)
        # Permanent error — return success so SQS deletes the poison message.
        return {"statusCode": 200, "body": json.dumps({"error": "malformed_message"})}

    submission_id = body.get("submission_id", "unknown")

    try:
        result = asyncio.run(_process_submission(body))
        return {"statusCode": 200, "body": json.dumps(result, default=str)}
    except Exception as e:
        # Unhandled / transient error — raise so SQS retries.
        logger.error(
            "Ring 1 FAILED for submission=%s: %s",
            submission_id[:8] if submission_id else "?",
            e,
            exc_info=True,
        )
        raise
