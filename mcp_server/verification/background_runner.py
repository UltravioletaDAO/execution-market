"""
Phase B — Asynchronous Evidence Verification Runner

Downloads evidence images and runs AI + image-analysis checks that
require actual pixel data (as opposed to Phase A metadata-only checks).

Launched as a fire-and-forget asyncio task from the submit endpoint.
Never blocks the HTTP response — failures are logged, not raised.
"""

import asyncio
import dataclasses
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import supabase_client as db
from .pipeline import CheckResult, merge_phase_b
from .image_downloader import (
    extract_photo_urls,
    download_images_to_temp,
    cleanup_temp_files,
)

logger = logging.getLogger(__name__)

# Kill switch
VERIFICATION_AI_ENABLED = os.environ.get("VERIFICATION_AI_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
VERIFICATION_AUTO_APPROVE = os.environ.get(
    "VERIFICATION_AUTO_APPROVE", "true"
).lower() in (
    "true",
    "1",
    "yes",
)
VERIFICATION_AI_MAX_IMAGES = int(os.environ.get("VERIFICATION_AI_MAX_IMAGES", "2"))

# Consensus weights: higher tiers have more authority
TIER_WEIGHTS = {"tier_1": 1.0, "tier_2": 2.0, "tier_3": 3.0, "tier_4": 4.0}


async def _report_phase_b_error(submission_id: str, error_msg: str) -> None:
    """Write Phase B error to submission so dashboard can display it."""
    try:
        current = await db.get_submission(submission_id)
        existing = (current or {}).get("auto_check_details") or {}
        await db.update_submission_auto_check(
            submission_id=submission_id,
            auto_check_passed=existing.get("passed", False),
            auto_check_details={
                **existing,
                "phase_b_status": "error",
                "phase_b_error": error_msg,
            },
        )
        logger.error("[AUDIT] Phase B error for %s: %s", submission_id, error_msg)
    except Exception as e:
        logger.error(
            "[AUDIT] Failed to report Phase B error for %s: %s", submission_id, e
        )


async def run_phase_b_verification(
    submission_id: str,
    submission: Dict[str, Any],
    task: Dict[str, Any],
) -> None:
    """
    Run all Phase B verification checks asynchronously.

    1. Extract photo URLs from evidence
    2. Download to temp files
    3. Run 5 checks concurrently
    4. Merge into existing auto_check_details
    5. Evaluate auto-approve conditions
    6. Store perceptual hashes
    7. Cleanup temp files

    This function never raises — all errors are logged.
    """
    if not VERIFICATION_AI_ENABLED:
        logger.info("Phase B verification disabled (VERIFICATION_AI_ENABLED=false)")
        await _report_phase_b_error(
            submission_id,
            "AI verification disabled (VERIFICATION_AI_ENABLED=false)",
        )
        return

    temp_paths: List[str] = []
    try:
        evidence = submission.get("evidence") or {}

        # 1. Extract photo URLs
        photo_urls = extract_photo_urls(evidence)
        if not photo_urls:
            logger.info(
                "Phase B skipped for %s: no photo URLs in evidence", submission_id
            )
            await _report_phase_b_error(
                submission_id, "No photo URLs found in evidence"
            )
            return

        # 2. Download to temp
        downloaded = await download_images_to_temp(
            photo_urls, max_images=VERIFICATION_AI_MAX_IMAGES
        )
        if not downloaded:
            logger.warning(
                "Phase B skipped for %s: no images downloaded", submission_id
            )
            await _report_phase_b_error(
                submission_id,
                "Could not download evidence images for analysis",
            )
            return

        temp_paths = [path for path, _ in downloaded]

        # 3. Run 5 checks concurrently
        check_tasks = [
            _run_ai_semantic_check(
                task, evidence, photo_urls, submission_id, temp_paths
            ),
            _run_tampering_check(temp_paths),
            _run_genai_detection_check(temp_paths),
            _run_photo_source_check(temp_paths, task.get("category", "")),
            _run_duplicate_check(temp_paths, submission_id, task.get("id", "")),
        ]

        results = await asyncio.gather(*check_tasks, return_exceptions=True)

        # Collect successful checks and perceptual hashes
        phase_b_checks: List[CheckResult] = []
        perceptual_hashes: Optional[Dict[str, Any]] = None

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_names = [
                    "ai_semantic",
                    "tampering",
                    "genai_detection",
                    "photo_source",
                    "duplicate",
                ]
                logger.warning(
                    "Phase B check '%s' failed for %s: %s",
                    check_names[i],
                    submission_id,
                    result,
                )
                continue

            if isinstance(result, tuple):
                # duplicate check returns (CheckResult, hashes_dict)
                check_result, hashes = result
                phase_b_checks.append(check_result)
                if hashes:
                    perceptual_hashes = hashes
            elif isinstance(result, CheckResult):
                phase_b_checks.append(result)

        if not phase_b_checks:
            logger.warning("No Phase B checks succeeded for %s", submission_id)
            await _report_phase_b_error(
                submission_id,
                "All AI verification checks failed — no provider available or all checks errored",
            )
            return

        # 4. Fetch current auto_check_details and merge
        current_submission = await db.get_submission(submission_id)
        if not current_submission:
            logger.warning("Submission %s not found for Phase B merge", submission_id)
            return

        existing_details = current_submission.get("auto_check_details") or {}
        merged = merge_phase_b(existing_details, phase_b_checks)

        # 5. Update DB with merged results
        await db.update_submission_auto_check(
            submission_id=submission_id,
            auto_check_passed=merged["passed"],
            auto_check_details=merged,
        )

        # Store AI verification result separately
        ai_check = next((c for c in phase_b_checks if c.name == "ai_semantic"), None)
        if ai_check:
            await db.update_submission_ai_verification(
                submission_id=submission_id,
                result={
                    "score": ai_check.score,
                    "passed": ai_check.passed,
                    "reason": ai_check.reason,
                    "details": ai_check.details,
                },
            )

        # 6. Store perceptual hashes
        if perceptual_hashes:
            await db.update_submission_perceptual_hashes(
                submission_id=submission_id,
                hashes=perceptual_hashes,
            )

        # 7. Evaluate auto-approve
        if VERIFICATION_AUTO_APPROVE:
            await _evaluate_auto_approve(
                submission_id=submission_id,
                merged=merged,
                phase_b_checks=phase_b_checks,
                task=task,
            )

        logger.info(
            "Phase B complete for %s: score=%.3f, checks=%d, phase=%s",
            submission_id,
            merged["score"],
            len(merged["checks"]),
            merged["phase"],
        )

        # 8. Run Ring 2 ArbiterService if task has arbiter_enabled
        # Fire-and-forget: never blocks Phase B response, never raises.
        try:
            if task.get("arbiter_enabled") and task.get("arbiter_mode") not in (
                None,
                "",
                "manual",
            ):
                await _run_arbiter_for_submission(
                    submission_id=submission_id,
                    task=task,
                    merged_phase_b=merged,
                )
        except Exception as arbiter_err:
            logger.error(
                "Arbiter post-Phase-B failed for %s: %s",
                submission_id,
                arbiter_err,
                exc_info=True,
            )

    except Exception as e:
        logger.error(
            "Phase B verification failed for %s: %s",
            submission_id,
            e,
            exc_info=True,
        )
        await _report_phase_b_error(submission_id, f"Unexpected error: {str(e)[:200]}")
    finally:
        cleanup_temp_files(temp_paths)


# ---------------------------------------------------------------------------
# Individual check runners
# ---------------------------------------------------------------------------


def _metadata_quality_score(evidence: Dict[str, Any]) -> float:
    """Score evidence metadata/EXIF quality (0.0-1.0).

    Checks for capture timestamp, GPS metadata, device info, and image
    dimensions.  A base score of 0.3 is given just for having evidence.
    """
    score = 0.3  # base: evidence exists
    for key in ("photo", "photo_geo", "screenshot"):
        item = evidence.get(key)
        if not isinstance(item, dict):
            continue
        meta = item.get("metadata") or item
        if meta.get("captureTimestamp") or meta.get("capture_timestamp"):
            score += 0.2  # has capture timestamp
        if meta.get("gps") or meta.get("latitude"):
            score += 0.2  # has GPS metadata
        if (
            meta.get("deviceInfo")
            or meta.get("device_info")
            or meta.get("source") == "camera"
        ):
            score += 0.15  # has device info or camera source
        if meta.get("imageWidth") or meta.get("width"):
            score += 0.15  # has image dimensions
        break  # only check first evidence item
    return min(1.0, score)


def _gps_proximity_score(evidence: Dict[str, Any], task: Dict[str, Any]) -> float:
    """Score GPS proximity between evidence and task location (0.0-1.0).

    Returns 0.0 when evidence has no GPS.  Returns 0.7 when evidence has GPS
    but the task has no coordinates to compare against.  Otherwise uses a
    haversine distance with tiered scoring.
    """
    # Lazy import to avoid circular imports
    from .pipeline import _extract_gps_from_evidence

    photo_lat, photo_lng = _extract_gps_from_evidence(evidence)
    if photo_lat is None:
        return 0.0  # no GPS in evidence

    task_lat = task.get("location_lat")
    task_lng = task.get("location_lng")
    if task_lat is None or task_lng is None:
        return 0.7  # GPS present but no task coords to compare

    import math

    R = 6371000  # Earth radius in meters
    dlat = math.radians(float(task_lat) - photo_lat)
    dlng = math.radians(float(task_lng) - photo_lng)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(photo_lat))
        * math.cos(math.radians(float(task_lat)))
        * math.sin(dlng / 2) ** 2
    )
    distance = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    if distance <= 500:
        return 1.0
    elif distance <= 2000:
        return 0.7
    elif distance <= 10000:
        return 0.4
    else:
        return 0.1


def _compute_ai_semantic_score(
    result: Any,
    evidence: Optional[Dict[str, Any]] = None,
    task: Optional[Dict[str, Any]] = None,
) -> float:
    """Compute a weighted score for AI semantic check.

    The final score blends three components with adaptive weighting:

      - **Visual content score** (60%): Based on AI decision + confidence.
      - **Metadata/EXIF quality score** (20%): Richness of evidence metadata.
      - **GPS proximity score** (20%): Distance between evidence and task.

    When GPS or metadata are unavailable, weights redistribute to visual.

    Visual scoring rules:
      - approved  -> confidence (e.g. 0.85)
      - needs_human -> confidence * 0.6 (e.g. 0.42)
      - rejected -> max(0.1, (1.0 - confidence) * 0.5)

    GPS-content heuristic: if the AI explanation indicates the visual content
    is plausible/matches but issues mention GPS/coordinates as the primary
    concern, add a 0.2 bonus (capped at 0.85). This prevents the separate
    GPS check from double-penalizing through the AI score.
    """
    from .ai_review import VerificationDecision

    decision = result.decision
    confidence = result.confidence
    explanation = (result.explanation or "").lower()
    issues = [i.lower() for i in (result.issues or [])]
    issues_text = " ".join(issues)

    # Base visual score from decision + confidence
    if decision == VerificationDecision.APPROVED:
        visual = confidence
    elif decision == VerificationDecision.NEEDS_HUMAN:
        visual = confidence * 0.6
    else:  # REJECTED
        visual = max(0.1, (1.0 - confidence) * 0.5)

    # GPS-content heuristic: detect when rejection is primarily about
    # missing GPS while the AI acknowledges the content itself matches.
    content_positive_phrases = [
        "visual content is plausible",
        "correct branding",
        "consistent with",
        "content appears genuine",
        "matches the task",
        "plausible and shows genuine",
        "live-capture characteristics",
    ]
    gps_issue_phrases = ["gps", "coordinates", "geolocation", "location data"]

    content_ok = any(phrase in explanation for phrase in content_positive_phrases)
    gps_flagged = any(
        any(gps in source for gps in gps_issue_phrases)
        for source in [issues_text, explanation]
    )

    if content_ok and gps_flagged:
        visual = min(0.85, visual + 0.2)

    # Weighted blending with adaptive weights
    if evidence and task:
        meta_score = _metadata_quality_score(evidence)
        gps_score = _gps_proximity_score(evidence, task)

        has_gps = gps_score > 0.0
        has_meta = meta_score > 0.3  # more than base

        if has_gps and has_meta:
            final = visual * 0.6 + meta_score * 0.2 + gps_score * 0.2
        elif has_meta:  # no GPS
            final = visual * 0.75 + meta_score * 0.25
        elif has_gps:  # no metadata
            final = visual * 0.75 + gps_score * 0.25
        else:  # neither
            final = visual
    else:
        final = visual  # fallback: no context provided

    return round(min(1.0, max(0.0, final)), 4)


async def _run_ai_semantic_check(
    task: Dict[str, Any],
    evidence: Dict[str, Any],
    photo_urls: List[str],
    submission_id: str = "",
    temp_paths: Optional[List[str]] = None,
) -> CheckResult:
    """
    Run AI vision verification with tiered model routing.

    Flow:
    1. Extract EXIF metadata from downloaded images
    2. Run AWS Rekognition (if enabled) for labels/text/moderation
    3. Route to appropriate tier via ModelRouter
    4. Run verification, escalate if uncertain
    5. Log each inference to audit trail
    """
    try:
        from .ai_review import AIVerifier, VerificationDecision
        from .exif_extractor import extract_exif
        from .inference_logger import (
            InferenceRecord,
            InferenceTimer,
            compute_commitment_hash,
            get_inference_logger,
        )
        from .model_router import select_tier, should_escalate, tier_exceeds
        from .prompts import get_prompt_library
        from .providers import get_provider_for_tier
        from .providers_aws import analyze_with_rekognition

        # --- Step 1: Extract EXIF ---
        exif_context = ""
        exif_metadata = {}
        has_exif = True
        if temp_paths:
            try:
                exif_data = extract_exif(temp_paths[0])
                exif_context = exif_data.to_prompt_context()
                has_exif = exif_data.has_exif
                exif_metadata = {
                    "camera": f"{exif_data.camera_make or ''} {exif_data.camera_model or ''}".strip(),
                    "gps": f"{exif_data.gps_latitude},{exif_data.gps_longitude}"
                    if exif_data.gps_latitude
                    else None,
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
                    "EXIF extracted for %s: has_exif=%s stripped=%s editing=%s",
                    submission_id,
                    exif_data.has_exif,
                    exif_data.metadata_stripped,
                    exif_data.has_editing_software,
                )
            except Exception as e:
                logger.warning("EXIF extraction failed for %s: %s", submission_id, e)

        # --- Step 2: AWS Rekognition (if enabled, fire-and-forget) ---
        rekognition_context = ""
        if temp_paths:
            try:
                with open(temp_paths[0], "rb") as f:
                    image_bytes = f.read()
                rekog_result = await analyze_with_rekognition(image_bytes)
                rekognition_context = rekog_result.to_prompt_context()
                if rekog_result.available:
                    exif_metadata["rekognition"] = {
                        "labels": len(rekog_result.labels),
                        "text_detected": len(rekog_result.text_detections),
                        "moderation_flags": rekog_result.has_moderation_flags,
                        "faces": rekog_result.face_count,
                    }
            except Exception as e:
                logger.debug("Rekognition skipped for %s: %s", submission_id, e)

        # --- Step 3: Route to tier ---
        category = task.get("category", "general")
        bounty = float(task.get("bounty", task.get("bounty_amount", 0)) or 0)

        selection = select_tier(
            bounty_usd=bounty,
            category=category,
            worker_reputation=task.get("executor_reputation"),
            worker_completed_tasks=task.get("executor_completed_tasks"),
            is_disputed=task.get("status") == "disputed",
            has_exif=has_exif,
            photo_count=len(photo_urls[:VERIFICATION_AI_MAX_IMAGES]),
        )
        current_tier = selection.start_tier
        logger.info(
            "Model routing for %s: %s (max=%s) — %s",
            submission_id,
            current_tier,
            selection.max_tier,
            selection.reason,
        )

        # --- Step 4: Run verification (with escalation + consensus) ---
        inference_logger = get_inference_logger()
        prompt_lib = get_prompt_library()
        pv = (
            prompt_lib.get_prompt(category, task, evidence).version
            if prompt_lib.has_category(category)
            else f"photint-v1.0-{category}"
        )

        tier_results = []  # Collect (tier, score, confidence, result) from all tiers
        tiers_tried = []

        for _attempt in range(4):  # Max 4 tiers
            provider = get_provider_for_tier(current_tier)
            if not provider:
                # Fallback: try default provider
                provider_name = os.environ.get("AI_VERIFICATION_PROVIDER", "gemini")
                verifier = AIVerifier(provider_name=provider_name)
                if not verifier.is_available:
                    break
            else:
                verifier = AIVerifier(provider=provider)

            timer = InferenceTimer()
            try:
                with timer:
                    result = await verifier.verify_evidence(
                        task=task,
                        evidence=evidence,
                        photo_urls=photo_urls[:VERIFICATION_AI_MAX_IMAGES],
                        exif_context=exif_context,
                        rekognition_context=rekognition_context,
                    )
            except Exception as e:
                logger.warning("[AUDIT] Tier %s failed: %s", current_tier, str(e)[:100])
                # Don't include failed tier in consensus — try next
                next_tier = should_escalate(current_tier, 0.0, 0.0)
                if next_tier is None or tier_exceeds(next_tier, selection.max_tier):
                    break
                current_tier = next_tier
                continue

            tiers_tried.append(current_tier)
            score = _compute_ai_semantic_score(result, evidence=evidence, task=task)
            tier_results.append((current_tier, score, result.confidence, result))

            # Log this inference
            if submission_id:
                commitment_hash = compute_commitment_hash(
                    task.get("id", ""),
                    result.raw_response or result.explanation or "",
                )
                await inference_logger.log(
                    InferenceRecord(
                        submission_id=submission_id,
                        task_id=task.get("id", ""),
                        check_name="ai_semantic",
                        tier=current_tier,
                        provider=result.provider,
                        model=result.model,
                        prompt_version=pv,
                        prompt_text=result.raw_prompt,
                        response_text=result.raw_response,
                        parsed_decision=result.decision.value,
                        parsed_confidence=result.confidence,
                        parsed_issues=result.issues,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        latency_ms=timer.latency_ms,
                        task_category=category,
                        evidence_types=list(evidence.keys()) if evidence else [],
                        photo_count=len(photo_urls[:VERIFICATION_AI_MAX_IMAGES]),
                        commitment_hash=commitment_hash,
                        metadata={
                            "exif": exif_metadata,
                            "routing_reason": selection.reason,
                            "tiers_tried": tiers_tried,
                        },
                    )
                )

            # Check escalation with max_tier boundary
            next_tier = should_escalate(current_tier, score, result.confidence)
            if next_tier is None or tier_exceeds(next_tier, selection.max_tier):
                break

            logger.info(
                "[AUDIT] Escalating from %s to %s (score=%.2f, conf=%.2f)",
                current_tier,
                next_tier,
                score,
                result.confidence,
            )
            current_tier = next_tier

        # --- Step 5: Compute consensus score ---
        if len(tier_results) == 0:
            # All tiers failed — return neutral
            final_score = 0.5
            final_result = None
        elif len(tier_results) == 1:
            final_score = tier_results[0][1]
            final_result = tier_results[0][3]
        else:
            total_w = sum(TIER_WEIGHTS.get(t, 1.0) for t, _, _, _ in tier_results)
            final_score = (
                sum(TIER_WEIGHTS.get(t, 1.0) * s for t, s, _, _ in tier_results)
                / total_w
            )
            final_result = tier_results[-1][3]  # Use highest tier's explanation

        # --- Step 6: Detect tier disagreement ---
        consensus_type = "agreement"
        if len(tier_results) > 1:
            scores = [s for _, s, _, _ in tier_results]
            if max(scores) - min(scores) > 0.30:
                consensus_type = "disagreement"
                # When tiers strongly disagree, force human review
                if (
                    final_result
                    and final_result.decision == VerificationDecision.APPROVED
                ):
                    final_result = dataclasses.replace(
                        final_result, decision=VerificationDecision.NEEDS_HUMAN
                    )
                    logger.info(
                        "[AUDIT] Tier disagreement detected (spread=%.2f), "
                        "forcing NEEDS_HUMAN",
                        max(scores) - min(scores),
                    )

        # --- Step 7: Build final CheckResult ---
        if final_result is None:
            return CheckResult(
                name="ai_semantic",
                passed=True,
                score=0.5,
                reason="No AI provider available — skipped",
                details={"provider": "none"},
            )

        return CheckResult(
            name="ai_semantic",
            passed=final_result.decision == VerificationDecision.APPROVED,
            score=round(final_score, 4),
            reason=final_result.explanation,
            details={
                "decision": final_result.decision.value,
                "confidence": final_result.confidence,
                "explanation": final_result.explanation,
                "issues": final_result.issues,
                "provider": final_result.provider,
                "model": final_result.model,
                "tiers_tried": tiers_tried,
                "tier_scores": {t: round(s, 4) for t, s, _, _ in tier_results},
                "consensus_type": consensus_type,
                "start_tier": selection.start_tier,
                "max_tier": selection.max_tier,
                "routing_reason": selection.reason,
            },
        )

    except Exception as e:
        logger.warning("AI semantic check failed: %s", e)
        return CheckResult(
            name="ai_semantic",
            passed=True,
            score=0.5,
            reason=f"AI check failed: {e}",
            details={"error": str(e)},
        )


async def _run_tampering_check(temp_paths: List[str]) -> CheckResult:
    """Run tampering detection on the first image."""
    try:
        from .checks.tampering import check_tampering

        if not temp_paths:
            return CheckResult(
                name="tampering",
                passed=True,
                score=0.5,
                reason="No images to check",
            )

        result = check_tampering(temp_paths[0])

        if result.is_suspicious:
            score = max(0.0, 1.0 - result.confidence)
        else:
            score = 1.0

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


async def _confirm_genai_with_vision(
    temp_paths: List[str],
) -> Optional[dict]:
    """Use vision model to confirm/deny AI-generated detection."""
    try:
        from .providers import get_provider, VisionRequest

        try:
            provider = get_provider()
        except ValueError:
            return None

        prompt = (
            "Analyze this image carefully. Is it AI-generated "
            "(made by Midjourney, DALL-E, Stable Diffusion, Flux, or similar) "
            "or a real photograph taken by a camera?\n\n"
            "Consider: natural lighting, hand/finger details, text rendering, "
            "perspective consistency, background coherence, skin texture, "
            "reflection accuracy, and overall photorealism.\n\n"
            "Respond with ONLY a JSON object:\n"
            '{"is_ai": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}'
        )

        # Read image bytes from first temp file
        with open(temp_paths[0], "rb") as f:
            image_bytes = f.read()

        # Determine MIME type from extension
        ext = (
            temp_paths[0].rsplit(".", 1)[-1].lower() if "." in temp_paths[0] else "jpg"
        )
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        response = await provider.analyze(
            VisionRequest(
                prompt=prompt,
                images=[image_bytes],
                image_types=[mime_type],
                max_tokens=256,
            )
        )

        import json as _json

        # Try to parse JSON from response
        text = response.text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = _json.loads(text)

        return {
            "is_ai_generated": bool(parsed.get("is_ai", False)),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reason": str(parsed.get("reason", "")),
        }
    except Exception as e:
        logger.warning("[AUDIT] genai vision confirmation failed: %s", e)
        return None


async def _run_genai_detection_check(temp_paths: List[str]) -> CheckResult:
    """Detect AI-generated images."""
    try:
        from .checks.genai import check_genai

        if not temp_paths:
            return CheckResult(
                name="genai_detection",
                passed=True,
                score=0.5,
                reason="No images to check",
            )

        result = check_genai(temp_paths[0])

        # Vision model confirmation for moderate-confidence heuristic detections
        if result.is_ai_generated and result.confidence < 0.85:
            # Heuristic is uncertain — confirm with vision model
            confirmation = await _confirm_genai_with_vision(temp_paths)
            if (
                confirmation
                and not confirmation["is_ai_generated"]
                and confirmation["confidence"] >= 0.6
            ):
                # Vision model says it's real — override heuristic
                logger.info(
                    "[AUDIT] genai_detection vision override: heuristic=%s vision=%s",
                    result.confidence,
                    confirmation["confidence"],
                )
                result.is_ai_generated = False
                result.confidence = confirmation["confidence"]
                result.signals.append("vision_model_override_natural")
                result.signals.append(f"vision_reason: {confirmation['reason']}")

        # Nuanced scoring instead of binary 0.0/1.0
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
) -> CheckResult:
    """Verify photo source (camera vs gallery vs screenshot)."""
    try:
        from .checks.photo_source import check_photo_source

        if not temp_paths:
            return CheckResult(
                name="photo_source",
                passed=True,
                score=0.5,
                reason="No images to check",
            )

        # Use generous max_age for Phase B (evidence might be minutes old by now)
        result = check_photo_source(temp_paths[0], max_age_minutes=60)

        source_scores = {
            "camera": 1.0,
            "screenshot": 0.1,
            "gallery": 0.3,
            "unknown": 0.4,
            "error": 0.5,
        }
        score = source_scores.get(result.source, 0.4)

        # For non-physical tasks, gallery is acceptable
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
) -> Tuple[CheckResult, Optional[Dict[str, Any]]]:
    """Check for duplicate images using perceptual hashing."""
    try:
        from .checks.duplicate import DuplicateDetector

        if not temp_paths:
            return (
                CheckResult(
                    name="duplicate",
                    passed=True,
                    score=0.5,
                    reason="No images to check",
                ),
                None,
            )

        detector = DuplicateDetector(similarity_threshold=0.85)
        phash, dhash, ahash = detector.compute_hash(temp_paths[0])

        # Query existing hashes
        existing_rows = await db.get_existing_perceptual_hashes(
            exclude_task_id=task_id, limit=100
        )

        # Build existing_hashes list for comparison
        existing_hashes = []
        for row in existing_rows:
            hashes = row.get("hashes", {})
            if hashes.get("phash") and hashes.get("dhash") and hashes.get("ahash"):
                existing_hashes.append(
                    (row["id"], (hashes["phash"], hashes["dhash"], hashes["ahash"]))
                )

        # Check for duplicates
        is_duplicate = False
        best_similarity = 0.0
        match_id = None

        for existing_id, existing_hash_tuple in existing_hashes:
            similarity = detector.compute_similarity(
                (phash, dhash, ahash), existing_hash_tuple
            )
            if similarity > best_similarity:
                best_similarity = similarity
                match_id = existing_id

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
                    "best_similarity": round(best_similarity, 3),
                    "match_id": match_id if is_duplicate else None,
                    "compared_count": len(existing_hashes),
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


# ---------------------------------------------------------------------------
# Auto-approve evaluation
# ---------------------------------------------------------------------------


async def _evaluate_auto_approve(
    submission_id: str,
    merged: Dict[str, Any],
    phase_b_checks: List[CheckResult],
    task: Dict[str, Any],
) -> None:
    """
    Evaluate auto-approve conditions and approve if all are met.

    Conditions:
    1. Aggregate score >= 0.95
    2. Schema check passed
    3. AI semantic decision = "approved" with confidence >= 0.80
    4. No tampering detected (confidence < 0.50)
    5. No AI-generated content detected (confidence < 0.35)
    6. Task status is still "submitted"
    """
    score = merged.get("score", 0.0)

    # Condition 1: aggregate score
    if score < 0.95:
        logger.debug("Auto-approve skip: score %.3f < 0.95", score)
        return

    # Condition 2: schema check passed
    schema_passed = any(
        c.get("name") == "schema" and c.get("passed") for c in merged.get("checks", [])
    )
    if not schema_passed:
        logger.debug("Auto-approve skip: schema check not passed")
        return

    # Condition 3: AI semantic approved with high confidence
    ai_check = next((c for c in phase_b_checks if c.name == "ai_semantic"), None)
    if not ai_check:
        logger.debug("Auto-approve skip: no AI semantic check")
        return

    ai_decision = (ai_check.details or {}).get("decision", "")
    ai_confidence = (ai_check.details or {}).get("confidence", 0.0)
    if ai_decision != "approved" or ai_confidence < 0.80:
        logger.debug(
            "Auto-approve skip: AI decision=%s confidence=%.2f",
            ai_decision,
            ai_confidence,
        )
        return

    # Condition 4: no tampering
    tampering_check = next((c for c in phase_b_checks if c.name == "tampering"), None)
    if tampering_check:
        tamp_confidence = (tampering_check.details or {}).get("confidence", 0.0)
        if tamp_confidence >= 0.50:
            logger.debug(
                "Auto-approve skip: tampering confidence %.2f", tamp_confidence
            )
            return

    # Condition 5: no AI-generated content
    genai_check = next((c for c in phase_b_checks if c.name == "genai_detection"), None)
    if genai_check:
        genai_confidence = (genai_check.details or {}).get("confidence", 0.0)
        if genai_confidence >= 0.35:
            logger.debug("Auto-approve skip: genai confidence %.2f", genai_confidence)
            return

    # Condition 6: task status still "submitted"
    current_task = await db.get_task(task.get("id", ""))
    if not current_task or current_task.get("status") != "submitted":
        logger.debug(
            "Auto-approve skip: task status is %s",
            current_task.get("status") if current_task else "not found",
        )
        return

    # All conditions met — auto-approve
    agent_notes = f"Auto-approved by AI verification (score {score:.2f})"
    approved = await db.auto_approve_submission(
        submission_id=submission_id,
        score=score,
        agent_notes=agent_notes,
    )

    if approved:
        logger.info(
            "Submission %s auto-approved: score=%.3f, ai_confidence=%.2f",
            submission_id,
            score,
            ai_confidence,
        )


# ---------------------------------------------------------------------------
# Ring 2 — Arbiter post-Phase-B integration
# ---------------------------------------------------------------------------


async def _run_arbiter_for_submission(
    submission_id: str,
    task: Dict[str, Any],
    merged_phase_b: Dict[str, Any],
) -> None:
    """Run the Ring 2 ArbiterService after Phase B completes.

    Reads the merged Phase A+B PHOTINT scores, runs the dual-ring arbiter,
    and dispatches the verdict to the payment processor (release/refund/escalate).

    Idempotency: ArbiterService.evaluate() is safe to call multiple times --
    same input -> same evidence_hash and commitment_hash. The processor's
    underlying _settle_submission_payment also has its own idempotency check.

    This function NEVER raises -- all errors are logged. Failures here must
    not break Phase B for the rest of the system.
    """
    try:
        # Lazy imports to avoid circular deps and to keep verification module
        # importable without the arbiter package being available.
        from integrations.arbiter.config import is_arbiter_enabled
        from integrations.arbiter.processor import process_arbiter_verdict
        from integrations.arbiter.service import ArbiterService

        # Master switch -- if globally disabled, skip silently
        if not await is_arbiter_enabled():
            logger.debug(
                "Arbiter master switch OFF -- skipping arbiter for submission %s",
                submission_id,
            )
            return

        # Refresh submission to get the latest merged data
        current = await db.get_submission(submission_id)
        if not current:
            logger.warning(
                "Submission %s not found for arbiter run", submission_id
            )
            return

        # Idempotency: skip if arbiter already ran for this submission
        if current.get("arbiter_verdict") is not None:
            logger.info(
                "Submission %s already has arbiter verdict (%s) -- skipping",
                submission_id,
                current.get("arbiter_verdict"),
            )
            return

        # Build a submission dict the arbiter expects (with task + executor relations)
        if not current.get("task"):
            current["task"] = task

        # Run the arbiter
        arbiter = ArbiterService.from_defaults()
        verdict = await arbiter.evaluate(task=task, submission=current)

        logger.info(
            "Arbiter verdict for submission %s: decision=%s tier=%s score=%.3f",
            submission_id,
            verdict.decision.value,
            verdict.tier.value,
            verdict.aggregate_score,
        )

        # Dispatch verdict to processor (release / refund / escalate / store)
        result = await process_arbiter_verdict(
            verdict=verdict, task=task, submission=current
        )

        logger.info(
            "Arbiter dispatch for submission %s: action=%s success=%s tx=%s",
            submission_id,
            result.action,
            result.success,
            result.payment_tx or result.refund_tx or result.dispute_id or "-",
        )

    except Exception as e:
        # Critical: never raise -- log only
        logger.error(
            "Arbiter run failed for submission %s: %s: %s",
            submission_id,
            type(e).__name__,
            e,
            exc_info=True,
        )
