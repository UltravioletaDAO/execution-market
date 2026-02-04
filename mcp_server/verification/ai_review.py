"""
AI-Powered Evidence Verification using Claude Vision

Uses Claude's vision capabilities to verify task completion evidence.
Provides a second layer of verification after auto-checks pass.
"""

import os
import json
import base64
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

import anthropic
import httpx


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


class AIVerifier:
    """
    Verifies task evidence using Claude Vision.

    Supports multiple task types with specialized prompts:
    - store_verification: Verify store/business photos
    - photo_verification: General photo verification
    - delivery: Verify delivery completion
    - presence: Verify physical presence at location
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI verifier.

        Args:
            api_key: Anthropic API key (default: env ANTHROPIC_API_KEY)
        """
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-sonnet-4-20250514"

    async def verify_evidence(
        self,
        task: dict,
        evidence: dict,
        photo_urls: List[str]
    ) -> VerificationResult:
        """
        Verify evidence against task requirements.

        Args:
            task: Task object with title, description, evidence_required
            evidence: Submitted evidence (GPS, timestamp, notes)
            photo_urls: List of photo URLs to analyze

        Returns:
            VerificationResult with decision and explanation
        """
        # Download and encode images
        images = []
        for url in photo_urls[:4]:  # Max 4 images
            try:
                image_data = await self._download_image(url)
                images.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": self._get_media_type(url),
                        "data": base64.b64encode(image_data).decode()
                    }
                })
            except Exception as e:
                # Log but continue with other images
                print(f"Failed to download image {url}: {e}")

        if not images:
            return VerificationResult(
                decision=VerificationDecision.NEEDS_HUMAN,
                confidence=0.0,
                explanation="No valid images could be downloaded for verification",
                issues=["Failed to download any images"],
                task_specific_checks={}
            )

        # Build verification prompt
        prompt = self._build_verification_prompt(task, evidence)

        try:
            # Call Claude Vision
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            *images,
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            # Parse response
            return self._parse_response(message.content[0].text)

        except Exception as e:
            # On API error, escalate to human
            return VerificationResult(
                decision=VerificationDecision.NEEDS_HUMAN,
                confidence=0.0,
                explanation=f"AI verification failed: {str(e)}",
                issues=["AI verification error"],
                task_specific_checks={}
            )

    def _build_verification_prompt(self, task: dict, evidence: dict) -> str:
        """Build the verification prompt for Claude."""

        task_type = task.get("task_type", task.get("category", "general"))
        prompt_template = self._get_prompt_for_task_type(task_type)

        return f"""You are a task verification system for Execution Market, a platform where humans complete physical tasks for AI agents.

## Task Details
- **Title**: {task.get('title', 'Unknown')}
- **Type**: {task_type}
- **Description**: {task.get('instructions', task.get('description', 'No description'))}

## Evidence Requirements
{self._format_requirements(task.get('evidence_schema', task.get('evidence_required', {})))}

## Submitted Evidence Metadata
- GPS: {evidence.get('gps', 'Not provided')}
- Timestamp: {evidence.get('timestamp', 'Not provided')}
- Notes: {evidence.get('notes', 'None')}

## Your Task
Analyze the submitted photo(s) and determine if the task was completed correctly.

{prompt_template}

## Response Format
Respond with a JSON object:
```json
{{
  "decision": "approved" | "rejected" | "needs_human",
  "confidence": 0.0-1.0,
  "explanation": "Brief explanation for the decision",
  "issues": ["List of any issues found"],
  "task_checks": {{
    "photo_matches_description": true/false,
    "location_appears_correct": true/false,
    "quality_acceptable": true/false,
    "no_fraud_indicators": true/false
  }}
}}
```

Be strict but fair. If something is slightly off but clearly a good-faith attempt, approve with notes. Only reject for clear failures or fraud indicators."""

    def _get_prompt_for_task_type(self, task_type: str) -> str:
        """Get specialized prompt additions for task type."""

        prompts = {
            "store_verification": """
## Store Verification Specific Checks
- Is a storefront/business visible?
- Is the store name/sign legible?
- Does it match the requested store?
- Is it clearly the exterior (not a photo of a photo)?
- Are operating hours or open/closed signs visible?
""",
            "photo_verification": """
## Photo Verification Specific Checks
- Is the subject clearly visible?
- Is the photo taken at the requested location?
- Is the lighting adequate to verify details?
- Is this a real photo (not screenshot/edited)?
- Does the photo contain the required elements?
""",
            "physical_presence": """
## Presence Verification Specific Checks
- Is the person clearly present at location?
- Are required elements visible (landmarks, signs)?
- Is this a live photo (not from gallery)?
- Does the environment match the expected location?
""",
            "delivery": """
## Delivery Verification Specific Checks
- Is the package/item visible?
- Is the delivery location visible (door, address)?
- Is there proof of delivery (doorstep, hand-off)?
- Is the condition of the item acceptable?
""",
            "knowledge_access": """
## Knowledge/Document Verification Specific Checks
- Is the requested information clearly visible?
- Is the document/source authentic?
- Is the text readable?
- Does it answer the task's question?
""",
            "human_authority": """
## Authority Verification Specific Checks
- Is the signature/stamp/seal visible?
- Is the document official/authentic?
- Are the required fields completed?
- Is the authority/person identifiable?
""",
        }

        return prompts.get(task_type, """
## General Checks
- Does the photo match the task description?
- Is the photo authentic (not manipulated)?
- Is sufficient detail visible to verify completion?
- Are there any red flags or fraud indicators?
""")

    def _format_requirements(self, requirements: dict) -> str:
        """Format evidence requirements for prompt."""
        if not requirements:
            return "- No specific requirements listed"

        lines = []

        # Handle schema format
        if isinstance(requirements, dict):
            required = requirements.get("required", [])
            optional = requirements.get("optional", [])

            if required:
                for item in required:
                    if isinstance(item, str):
                        lines.append(f"- {item.replace('_', ' ').title()} (required)")
                    elif isinstance(item, dict):
                        lines.append(f"- {item.get('type', 'Unknown').replace('_', ' ').title()} (required)")

            if optional:
                for item in optional:
                    if isinstance(item, str):
                        lines.append(f"- {item.replace('_', ' ').title()} (optional)")

        # Handle list format
        elif isinstance(requirements, list):
            for item in requirements:
                lines.append(f"- {item.replace('_', ' ').title()}")

        return "\n".join(lines) if lines else "- General photo evidence"

    async def _download_image(self, url: str) -> bytes:
        """Download image from URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.content

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
        """Parse Claude's response into VerificationResult."""

        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                raise ValueError("No JSON found in response")

            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            decision_map = {
                "approved": VerificationDecision.APPROVED,
                "rejected": VerificationDecision.REJECTED,
                "needs_human": VerificationDecision.NEEDS_HUMAN
            }

            return VerificationResult(
                decision=decision_map.get(data.get("decision"), VerificationDecision.NEEDS_HUMAN),
                confidence=float(data.get("confidence", 0.5)),
                explanation=data.get("explanation", "No explanation provided"),
                issues=data.get("issues", []),
                task_specific_checks=data.get("task_checks", {})
            )

        except Exception as e:
            # If parsing fails, default to human review
            return VerificationResult(
                decision=VerificationDecision.NEEDS_HUMAN,
                confidence=0.0,
                explanation=f"Failed to parse AI response: {str(e)}",
                issues=["AI response parsing error"],
                task_specific_checks={}
            )


# Convenience function
async def verify_with_ai(
    task: dict,
    evidence: dict,
    photo_urls: List[str]
) -> VerificationResult:
    """
    Convenience function to verify evidence with AI.

    Args:
        task: Task dict with title, description, evidence_required
        evidence: Submitted evidence metadata
        photo_urls: List of photo URLs

    Returns:
        VerificationResult

    Example:
        >>> task = {
        ...     "title": "Verify store is open",
        ...     "task_type": "store_verification",
        ...     "description": "Take photo of Walmart entrance"
        ... }
        >>> evidence = {"gps": {"lat": 25.76, "lng": -80.19}}
        >>> result = await verify_with_ai(task, evidence, ["https://..."])
        >>> print(result.decision)
    """
    verifier = AIVerifier()
    return await verifier.verify_evidence(task, evidence, photo_urls)


# Verification tier routing
async def process_verification(
    task: dict,
    evidence: dict,
    auto_checks: dict
) -> dict:
    """
    Route to appropriate verification tier based on auto-check score.

    Tiers:
    - 0.95+: Auto-approve (all checks pass with high confidence)
    - 0.70+: AI verification (some uncertainty, needs vision review)
    - 0.50+: Agent review (significant issues, agent should decide)
    - <0.50: Human required (major problems or potential fraud)

    Args:
        task: Task details
        evidence: Submitted evidence
        auto_checks: Results of auto-verification checks

    Returns:
        Dict with tier, decision, and details
    """

    # Calculate auto-check score
    auto_score = calculate_auto_score(auto_checks)

    if auto_score >= 0.95:
        # Tier 1: Auto-approve
        return {
            "tier": "auto",
            "decision": "approved",
            "confidence": auto_score,
            "explanation": "All auto-checks passed"
        }

    elif auto_score >= 0.70:
        # Tier 2: AI verification
        result = await verify_with_ai(
            task=task,
            evidence=evidence,
            photo_urls=evidence.get("photos", [])
        )

        if result.decision == VerificationDecision.APPROVED:
            return {
                "tier": "ai",
                "decision": "approved",
                "confidence": result.confidence,
                "explanation": result.explanation
            }
        elif result.decision == VerificationDecision.REJECTED:
            return {
                "tier": "ai",
                "decision": "rejected",
                "confidence": result.confidence,
                "reason": result.explanation,
                "issues": result.issues
            }
        else:
            # Escalate to human
            return {
                "tier": "human_required",
                "ai_result": {
                    "confidence": result.confidence,
                    "explanation": result.explanation,
                    "issues": result.issues
                }
            }

    elif auto_score >= 0.50:
        # Tier 3: Agent review
        return {
            "tier": "agent",
            "decision": "pending_agent_review",
            "auto_score": auto_score,
            "checks": auto_checks
        }

    else:
        # Tier 4: Human required
        return {
            "tier": "human",
            "decision": "pending_human_review",
            "auto_score": auto_score,
            "checks": auto_checks
        }


def calculate_auto_score(checks: dict) -> float:
    """
    Calculate aggregate score from auto-verification checks.

    Args:
        checks: Dict with check results (each is bool or 0-1 score)

    Returns:
        Score from 0 to 1
    """
    if not checks:
        return 0.5  # No checks = moderate confidence

    weights = {
        "photo_source": 0.3,    # Gallery/screenshot detection
        "gps_valid": 0.25,      # GPS within range
        "timestamp_valid": 0.2,  # Recent timestamp
        "schema_valid": 0.15,   # All required evidence present
        "duplicate_check": 0.1,  # Not a duplicate submission
    }

    total_weight = 0
    weighted_sum = 0

    for check, result in checks.items():
        weight = weights.get(check, 0.1)
        total_weight += weight

        # Convert bool to float
        if isinstance(result, bool):
            score = 1.0 if result else 0.0
        elif isinstance(result, dict):
            score = 1.0 if result.get("is_valid", False) else 0.0
        else:
            score = float(result)

        weighted_sum += score * weight

    return weighted_sum / total_weight if total_weight > 0 else 0.5
