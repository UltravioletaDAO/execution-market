"""
PHOTINT Structured Output Schemas

Pydantic models for the expected JSON response from vision models.
Richer than the legacy schema — includes forensic analysis fields.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ForensicAnalysis(BaseModel):
    """Forensic assessment of the photo evidence."""

    photo_authentic: bool = Field(
        description="Photo appears to be a genuine, unmanipulated capture"
    )
    photo_source: str = Field(
        description="Detected source: 'camera', 'gallery', 'screenshot', 'ai_generated', 'unknown'"
    )
    exif_consistent: Optional[bool] = Field(
        default=None,
        description="EXIF metadata is consistent with claims (null if no EXIF)",
    )
    location_match: Optional[bool] = Field(
        default=None,
        description="Photo location matches task location (null if no GPS data)",
    )
    temporal_match: Optional[bool] = Field(
        default=None,
        description="Photo timing matches task window (null if no timestamp)",
    )
    platform_chain: Optional[str] = Field(
        default=None,
        description="Detected platform processing: 'original', 'whatsapp', 'telegram', 'instagram', etc.",
    )
    manipulation_indicators: List[str] = Field(
        default_factory=list,
        description="List of detected manipulation or fraud signals",
    )
    confidence_factors: Dict[str, str] = Field(
        default_factory=dict,
        description="Key findings rated: CONFIRMED, HIGH, MODERATE, LOW",
    )


class VerificationOutput(BaseModel):
    """Complete structured output from PHOTINT verification."""

    decision: Literal["approved", "rejected", "needs_human"] = Field(
        description="Verification verdict"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in the decision (0.0-1.0)"
    )
    explanation: str = Field(description="Brief explanation for the decision")
    issues: List[str] = Field(default_factory=list, description="List of issues found")

    forensic: ForensicAnalysis = Field(description="Forensic analysis of the evidence")

    task_checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Task-specific verification checks (varies by category)",
    )


# JSON schema string for inclusion in prompts
VERIFICATION_OUTPUT_SCHEMA = """{
  "decision": "approved" | "rejected" | "needs_human",
  "confidence": 0.0-1.0,
  "explanation": "Brief explanation for the decision",
  "issues": ["List of any issues found"],
  "forensic": {
    "photo_authentic": true/false,
    "photo_source": "camera" | "gallery" | "screenshot" | "ai_generated" | "unknown",
    "exif_consistent": true/false/null,
    "location_match": true/false/null,
    "temporal_match": true/false/null,
    "platform_chain": "original" | "whatsapp" | "telegram" | null,
    "manipulation_indicators": ["list of signals"],
    "confidence_factors": {"finding": "CONFIRMED|HIGH|MODERATE|LOW"}
  },
  "task_checks": {
    "check_name": true/false
  }
}"""
