# NOW-069: Claude Vision verification

## Metadata
- **Prioridad**: P1
- **Fase**: 5 - Verification
- **Dependencias**: NOW-012
- **Archivos a crear**: `mcp_server/verification/ai_review.py`
- **Tiempo estimado**: 3-4 horas

## Descripción
Implementar verificación de evidencia usando Claude Vision para tareas que pasan auto-verification pero necesitan review AI.

## Contexto Técnico
- **Model**: claude-sonnet-4-20250514 (o newer)
- **Input**: Foto + task description + evidence requirements
- **Output**: approval/rejection + confidence + explanation

## Código de Referencia

### ai_review.py
```python
"""
AI-powered evidence verification using Claude Vision
"""
import anthropic
import base64
import httpx
import os
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class VerificationDecision(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_HUMAN = "needs_human"


@dataclass
class VerificationResult:
    decision: VerificationDecision
    confidence: float  # 0-1
    explanation: str
    issues: List[str]
    task_specific_checks: dict


class AIVerifier:
    """Verifies task evidence using Claude Vision"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ["ANTHROPIC_API_KEY"]
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
            image_data = await self._download_image(url)
            images.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(image_data).decode()
                }
            })

        # Build verification prompt
        prompt = self._build_verification_prompt(task, evidence)

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

    def _build_verification_prompt(self, task: dict, evidence: dict) -> str:
        """Build the verification prompt for Claude"""

        task_type = task.get("task_type", "general")
        prompt_template = self._get_prompt_for_task_type(task_type)

        return f"""You are a task verification system for Execution Market, a platform where humans complete physical tasks for AI agents.

## Task Details
- **Title**: {task.get('title', 'Unknown')}
- **Type**: {task_type}
- **Description**: {task.get('description', 'No description')}

## Evidence Requirements
{self._format_requirements(task.get('evidence_required', {}))}

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
        """Get specialized prompt additions for task type"""

        prompts = {
            "store_verification": """
## Store Verification Specific Checks
- Is a storefront/business visible?
- Is the store name/sign legible?
- Does it match the requested store?
- Is it clearly the exterior (not a photo of a photo)?
""",
            "photo_verification": """
## Photo Verification Specific Checks
- Is the subject clearly visible?
- Is the photo taken at the requested location?
- Is the lighting adequate to verify details?
- Is this a real photo (not screenshot/edited)?
""",
            "delivery": """
## Delivery Verification Specific Checks
- Is the package/item visible?
- Is the delivery location visible (door, address)?
- Is there proof of delivery (doorstep, hand-off)?
""",
            "presence": """
## Presence Verification Specific Checks
- Is the person clearly present at location?
- Are required elements visible (landmarks, signs)?
- Is this a live photo (not from gallery)?
""",
        }

        return prompts.get(task_type, """
## General Checks
- Does the photo match the task description?
- Is the photo authentic (not manipulated)?
- Is sufficient detail visible to verify completion?
""")

    def _format_requirements(self, requirements: dict) -> str:
        """Format evidence requirements for prompt"""
        if not requirements:
            return "- No specific requirements listed"

        lines = []
        if requirements.get("photos_min"):
            lines.append(f"- Minimum {requirements['photos_min']} photo(s)")
        if requirements.get("gps_required"):
            lines.append("- GPS location required")
        if requirements.get("must_show"):
            for item in requirements.get("must_show", []):
                lines.append(f"- Must show: {item}")

        return "\n".join(lines) if lines else "- General photo evidence"

    async def _download_image(self, url: str) -> bytes:
        """Download image from URL"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _parse_response(self, response_text: str) -> VerificationResult:
        """Parse Claude's response into VerificationResult"""
        import json

        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]

            data = json.loads(json_str)

            decision_map = {
                "approved": VerificationDecision.APPROVED,
                "rejected": VerificationDecision.REJECTED,
                "needs_human": VerificationDecision.NEEDS_HUMAN
            }

            return VerificationResult(
                decision=decision_map.get(data["decision"], VerificationDecision.NEEDS_HUMAN),
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
    """
    verifier = AIVerifier()
    return await verifier.verify_evidence(task, evidence, photo_urls)
```

### Integration with verification tier routing
```python
# In submit_work handler

from verification.ai_review import verify_with_ai, VerificationDecision

async def process_verification(task: dict, evidence: dict, auto_checks: dict) -> dict:
    """Route to appropriate verification tier"""

    # Calculate auto-check score
    auto_score = calculate_auto_score(auto_checks)

    if auto_score >= 0.95:
        # Tier 1: Auto-approve
        return {"tier": "auto", "decision": "approved", "confidence": auto_score}

    elif auto_score >= 0.70:
        # Tier 2: AI verification
        result = await verify_with_ai(
            task=task,
            evidence=evidence,
            photo_urls=evidence.get("photos", [])
        )

        if result.decision == VerificationDecision.APPROVED:
            return {"tier": "ai", "decision": "approved", "confidence": result.confidence, "explanation": result.explanation}
        elif result.decision == VerificationDecision.REJECTED:
            return {"tier": "ai", "decision": "rejected", "confidence": result.confidence, "reason": result.explanation, "issues": result.issues}
        else:
            # Escalate to human
            return {"tier": "human_required", "ai_result": result}

    elif auto_score >= 0.50:
        # Tier 3: Agent review
        return {"tier": "agent", "decision": "pending_agent_review"}

    else:
        # Tier 4: Human required
        return {"tier": "human", "decision": "pending_human_review"}
```

## Criterios de Éxito
- [ ] Claude Vision API funciona
- [ ] Prompts especializados por task_type
- [ ] Response parsing robusto
- [ ] Confidence scores útiles
- [ ] Integration con verification flow
- [ ] Error handling para API failures
- [ ] Rate limiting consideration

## Test Cases
```python
async def test_store_verification_approved():
    task = {
        "title": "Verify store is open",
        "task_type": "store_verification",
        "description": "Take photo of Walmart entrance"
    }
    evidence = {"gps": {"lat": 25.76, "lng": -80.19}}
    result = await verify_with_ai(task, evidence, ["valid_store_photo_url"])
    assert result.decision == VerificationDecision.APPROVED

async def test_screenshot_rejected():
    # AI should detect and reject screenshots
    result = await verify_with_ai(task, evidence, ["screenshot_url"])
    assert result.decision == VerificationDecision.REJECTED
    assert "screenshot" in result.explanation.lower() or "fraud" in result.issues

async def test_api_error_handled():
    # Should return needs_human on API error
    with mock.patch("anthropic.Anthropic") as mock_client:
        mock_client.side_effect = Exception("API Error")
        result = await verify_with_ai(task, evidence, photos)
        assert result.decision == VerificationDecision.NEEDS_HUMAN
```

## Cost Estimation
- claude-sonnet-4: ~$3/$15 per 1M input/output tokens
- Average verification: ~2000 input tokens (image + prompt), ~200 output
- Cost per verification: ~$0.006 + $0.003 = ~$0.009
- 1000 verifications/day: ~$9/day
