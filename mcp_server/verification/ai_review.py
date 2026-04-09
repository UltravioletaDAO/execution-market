"""
AI-Powered Evidence Verification (Multi-Provider)

Uses vision-capable AI models to verify task completion evidence.
Provides a second layer of verification after auto-checks pass.

Supported providers (configurable via AI_VERIFICATION_PROVIDER env):
- anthropic: Claude Vision (default)
- openai: GPT-4o Vision
- bedrock: AWS Bedrock (Claude via AWS)
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

import httpx

from .providers import (
    VerificationProvider,
    VisionRequest,
    get_provider,
)

logger = logging.getLogger(__name__)

# Cap evidence downloads to prevent memory exhaustion and malicious body sizes.
# Phase 0 GR-0.4 — see docs/reports/security-audit-2026-04-07/specialists/SC_05_BACKEND_API.md [API-004]
MAX_EVIDENCE_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class VerificationDecision(Enum):
    """Possible verification outcomes."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_HUMAN = "needs_human"


@dataclass
class VerificationResult:
    """Result of AI verification."""

    decision: VerificationDecision
    confidence: float  # 0-1
    explanation: str
    issues: List[str]
    task_specific_checks: dict
    provider: str = "unknown"
    model: str = "unknown"
    raw_prompt: str = ""
    raw_response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class AIVerifier:
    """
    Verifies task evidence using AI vision models.

    Supports multiple providers via the providers.py abstraction.
    Set AI_VERIFICATION_PROVIDER env to switch providers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider_name: Optional[str] = None,
        provider: Optional[VerificationProvider] = None,
    ):
        if provider:
            self._provider = provider
        else:
            kwargs = {}
            if api_key:
                kwargs["api_key"] = api_key
            try:
                self._provider = get_provider(provider_name, **kwargs)
            except ValueError:
                self._provider = None

    @property
    def provider_name(self) -> str:
        return self._provider.name if self._provider else "none"

    @property
    def is_available(self) -> bool:
        return self._provider is not None and self._provider.is_available()

    async def verify_evidence(
        self,
        task: dict,
        evidence: dict,
        photo_urls: List[str],
        *,
        exif_context: str = "",
        rekognition_context: str = "",
    ) -> VerificationResult:
        """
        Verify evidence against task requirements.

        Args:
            task: Task object with title, description, evidence_required
            evidence: Submitted evidence (GPS, timestamp, notes)
            photo_urls: List of photo URLs to analyze
            exif_context: Pre-extracted EXIF metadata summary (optional)
            rekognition_context: AWS Rekognition labels/text (optional)

        Returns:
            VerificationResult with decision and explanation
        """
        if not self._provider:
            return VerificationResult(
                decision=VerificationDecision.NEEDS_HUMAN,
                confidence=0.0,
                explanation="No AI verification provider available",
                issues=["No provider configured"],
                task_specific_checks={},
            )

        # Download images
        images = []
        image_types = []
        for url in photo_urls[:4]:  # Max 4 images
            try:
                image_data = await self._download_image(url)
                images.append(image_data)
                image_types.append(self._get_media_type(url))
            except Exception as e:
                logger.warning("Failed to download image %s: %s", url, e)

        if not images:
            return VerificationResult(
                decision=VerificationDecision.NEEDS_HUMAN,
                confidence=0.0,
                explanation="No valid images could be downloaded for verification",
                issues=["Failed to download any images"],
                task_specific_checks={},
            )

        # Build prompt using PHOTINT prompt library
        from .prompts import get_prompt_library

        prompt_lib = get_prompt_library()
        category = task.get("task_type", task.get("category", "general"))
        prompt_result = prompt_lib.get_prompt(
            category=category,
            task=task,
            evidence=evidence,
            exif_context=exif_context,
            rekognition_context=rekognition_context,
        )
        prompt = prompt_result.text

        try:
            response = await self._provider.analyze(
                VisionRequest(
                    prompt=prompt,
                    images=images,
                    image_types=image_types,
                    max_tokens=1024,
                )
            )

            result = self._parse_response(response.text)
            result.provider = response.provider
            result.model = response.model
            result.raw_prompt = prompt
            result.raw_response = response.text
            result.input_tokens = response.usage.get("input_tokens", 0)
            result.output_tokens = response.usage.get("output_tokens", 0)

            logger.info(
                "AI verification via %s/%s: decision=%s confidence=%.2f tokens=%d+%d",
                response.provider,
                response.model,
                result.decision.value,
                result.confidence,
                result.input_tokens,
                result.output_tokens,
            )

            return result

        except Exception as e:
            logger.error("AI verification failed (%s): %s", self.provider_name, e)
            return VerificationResult(
                decision=VerificationDecision.NEEDS_HUMAN,
                confidence=0.0,
                explanation=f"AI verification failed: {str(e)}",
                issues=["AI verification error"],
                task_specific_checks={},
                provider=self.provider_name,
                raw_prompt=prompt,
            )

    async def _download_image(self, url: str) -> bytes:
        """Download image from URL.

        Security (Phase 0 GR-0.4, closes API-004):
          - follow_redirects=False — blocks SSRF via 3xx redirect to internal
            services. Callers MUST validate host allowlist BEFORE calling us.
          - timeout=10.0 — bounded so a slowloris cannot hang a worker.
          - Response body capped at MAX_EVIDENCE_DOWNLOAD_BYTES (10 MB) to
            prevent memory exhaustion.
          - Explicit rejection of 3xx responses.
        """
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=10.0,
        ) as client:
            # Use streaming so we can enforce MAX_EVIDENCE_DOWNLOAD_BYTES
            # BEFORE the full body is buffered in memory.
            async with client.stream("GET", url) as response:
                # If we got a 3xx, it's a redirect attempt — reject explicitly.
                if 300 <= response.status_code < 400:
                    raise httpx.HTTPStatusError(
                        f"Evidence URL returned a redirect "
                        f"({response.status_code}); redirects are not allowed",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()

                # Pre-check Content-Length if the server sent one.
                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        if int(content_length) > MAX_EVIDENCE_DOWNLOAD_BYTES:
                            raise ValueError(
                                f"Evidence too large: Content-Length="
                                f"{content_length} > "
                                f"{MAX_EVIDENCE_DOWNLOAD_BYTES}"
                            )
                    except ValueError:
                        raise

                chunks: List[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > MAX_EVIDENCE_DOWNLOAD_BYTES:
                        raise ValueError(
                            f"Evidence too large (>{MAX_EVIDENCE_DOWNLOAD_BYTES} bytes)"
                        )
                    chunks.append(chunk)
                return b"".join(chunks)

    def _get_media_type(self, url: str) -> str:
        """Determine media type from URL."""
        url_lower = url.lower()
        if url_lower.endswith(".png"):
            return "image/png"
        elif url_lower.endswith(".gif"):
            return "image/gif"
        elif url_lower.endswith(".webp"):
            return "image/webp"
        return "image/jpeg"

    def _parse_response(self, response_text: str) -> VerificationResult:
        """Parse AI response into VerificationResult.

        Handles both PHOTINT schema (with 'forensic' field) and
        legacy schema (flat task_checks only) for backward compatibility.
        """
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                raise ValueError("No JSON found in response")

            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            decision_map = {
                "approved": VerificationDecision.APPROVED,
                "rejected": VerificationDecision.REJECTED,
                "needs_human": VerificationDecision.NEEDS_HUMAN,
            }

            # Merge forensic analysis into task_specific_checks for storage
            task_checks = data.get("task_checks", {})
            forensic = data.get("forensic", {})
            if forensic:
                task_checks["_forensic"] = forensic

            return VerificationResult(
                decision=decision_map.get(
                    data.get("decision"), VerificationDecision.NEEDS_HUMAN
                ),
                confidence=float(data.get("confidence", 0.5)),
                explanation=data.get("explanation", "No explanation provided"),
                issues=data.get("issues", []),
                task_specific_checks=task_checks,
            )

        except Exception as e:
            return VerificationResult(
                decision=VerificationDecision.NEEDS_HUMAN,
                confidence=0.0,
                explanation=f"Failed to parse AI response: {str(e)}",
                issues=["AI response parsing error"],
                task_specific_checks={},
            )


# Convenience function
async def verify_with_ai(
    task: dict,
    evidence: dict,
    photo_urls: List[str],
    provider_name: Optional[str] = None,
) -> VerificationResult:
    """
    Verify evidence with AI using the configured provider.

    Args:
        task: Task dict with title, description, evidence_required
        evidence: Submitted evidence metadata
        photo_urls: List of photo URLs
        provider_name: Override provider (anthropic/openai/bedrock)

    Returns:
        VerificationResult
    """
    verifier = AIVerifier(provider_name=provider_name)
    return await verifier.verify_evidence(task, evidence, photo_urls)


# Verification tier routing
async def process_verification(
    task: dict,
    evidence: dict,
    auto_checks: dict,
) -> dict:
    """
    Route to appropriate verification tier based on auto-check score.

    Tiers:
    - 0.95+: Auto-approve (all checks pass with high confidence)
    - 0.70+: AI verification (some uncertainty, needs vision review)
    - 0.50+: Agent review (significant issues, agent should decide)
    - <0.50: Human required (major problems or potential fraud)
    """
    auto_score = calculate_auto_score(auto_checks)

    if auto_score >= 0.95:
        return {
            "tier": "auto",
            "decision": "approved",
            "confidence": auto_score,
            "explanation": "All auto-checks passed",
        }

    elif auto_score >= 0.70:
        result = await verify_with_ai(
            task=task,
            evidence=evidence,
            photo_urls=evidence.get("photos", []),
        )

        if result.decision == VerificationDecision.APPROVED:
            return {
                "tier": "ai",
                "decision": "approved",
                "confidence": result.confidence,
                "explanation": result.explanation,
                "provider": result.provider,
                "model": result.model,
            }
        elif result.decision == VerificationDecision.REJECTED:
            return {
                "tier": "ai",
                "decision": "rejected",
                "confidence": result.confidence,
                "reason": result.explanation,
                "issues": result.issues,
                "provider": result.provider,
                "model": result.model,
            }
        else:
            return {
                "tier": "human_required",
                "ai_result": {
                    "confidence": result.confidence,
                    "explanation": result.explanation,
                    "issues": result.issues,
                    "provider": result.provider,
                },
            }

    elif auto_score >= 0.50:
        return {
            "tier": "agent",
            "decision": "pending_agent_review",
            "auto_score": auto_score,
            "checks": auto_checks,
        }

    else:
        return {
            "tier": "human",
            "decision": "pending_human_review",
            "auto_score": auto_score,
            "checks": auto_checks,
        }


def calculate_auto_score(checks: dict) -> float:
    """Calculate aggregate score from auto-verification checks."""
    if not checks:
        return 0.5

    weights = {
        "photo_source": 0.3,
        "gps_valid": 0.25,
        "timestamp_valid": 0.2,
        "schema_valid": 0.15,
        "duplicate_check": 0.1,
    }

    total_weight = 0
    weighted_sum = 0

    for check, result in checks.items():
        weight = weights.get(check, 0.1)
        total_weight += weight

        if isinstance(result, bool):
            score = 1.0 if result else 0.0
        elif isinstance(result, dict):
            score = 1.0 if result.get("is_valid", False) else 0.0
        else:
            score = float(result)

        weighted_sum += score * weight

    return weighted_sum / total_weight if total_weight > 0 else 0.5
