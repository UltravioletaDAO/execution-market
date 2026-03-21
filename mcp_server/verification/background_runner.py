"""
Phase B — Asynchronous Evidence Verification Runner

Downloads evidence images and runs AI + image-analysis checks that
require actual pixel data (as opposed to Phase A metadata-only checks).

Launched as a fire-and-forget asyncio task from the submit endpoint.
Never blocks the HTTP response — failures are logged, not raised.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from web3 import Web3

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
            return

        # 2. Download to temp
        downloaded = await download_images_to_temp(
            photo_urls, max_images=VERIFICATION_AI_MAX_IMAGES
        )
        if not downloaded:
            logger.warning(
                "Phase B skipped for %s: no images downloaded", submission_id
            )
            return

        temp_paths = [path for path, _ in downloaded]

        # 3. Run 5 checks concurrently
        check_tasks = [
            _run_ai_semantic_check(task, evidence, photo_urls),
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

    except Exception as e:
        logger.error(
            "Phase B verification failed for %s: %s",
            submission_id,
            e,
            exc_info=True,
        )
    finally:
        cleanup_temp_files(temp_paths)


# ---------------------------------------------------------------------------
# Individual check runners
# ---------------------------------------------------------------------------


async def _run_ai_semantic_check(
    task: Dict[str, Any],
    evidence: Dict[str, Any],
    photo_urls: List[str],
) -> CheckResult:
    """Run AI vision verification on evidence images."""
    try:
        from .ai_review import AIVerifier, VerificationDecision

        provider_name = os.environ.get("AI_VERIFICATION_PROVIDER", "gemini")
        verifier = AIVerifier(provider_name=provider_name)

        if not verifier.is_available:
            return CheckResult(
                name="ai_semantic",
                passed=True,
                score=0.5,
                reason="No AI provider available — skipped",
                details={"provider": "none"},
            )

        result = await verifier.verify_evidence(
            task=task,
            evidence=evidence,
            photo_urls=photo_urls[:VERIFICATION_AI_MAX_IMAGES],
        )

        # Map decision to score
        score_map = {
            VerificationDecision.APPROVED: 1.0,
            VerificationDecision.REJECTED: 0.0,
            VerificationDecision.NEEDS_HUMAN: 0.5,
        }
        score = score_map.get(result.decision, 0.5)

        # Compute commitment hash for auditability
        prompt_text = f"task:{task.get('id', '')}"
        response_text = result.explanation or ""
        raw_hex = Web3.keccak(text=f"{prompt_text}|{response_text}").hex()
        commitment_hash = raw_hex if raw_hex.startswith("0x") else f"0x{raw_hex}"

        return CheckResult(
            name="ai_semantic",
            passed=result.decision == VerificationDecision.APPROVED,
            score=score,
            reason=result.explanation,
            details={
                "decision": result.decision.value,
                "confidence": result.confidence,
                "issues": result.issues,
                "provider": result.provider,
                "model": result.model,
                "commitment_hash": commitment_hash,
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

        if result.is_ai_generated:
            score = 0.0
        else:
            score = 1.0

        return CheckResult(
            name="genai_detection",
            passed=not result.is_ai_generated,
            score=score,
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
