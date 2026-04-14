"""
PHOTINT Base System Prompt

Forensic evidence verification framework for Execution Market.
Adapted from the PHOTINT (Photographic Intelligence Analyst) methodology.

This base is shared across all task categories. Category-specific prompts
extend it with specialized checks.
"""

import re

from .schemas import VERIFICATION_OUTPUT_SCHEMA


def _sanitize_for_prompt(text: str, max_len: int = 500) -> str:
    """Sanitize free-text evidence fields before LLM prompt interpolation.

    Removes prompt-injection patterns (VECTOR-007: evidence fields go
    directly into the PHOTINT prompt template).

    Applies to: worker notes, task instructions, location, and any other
    free-text field interpolated into the prompt.

    Args:
        text: Raw user/agent-provided string.
        max_len: Maximum characters kept after sanitization (default 500).

    Returns:
        Sanitized string, safe for direct prompt interpolation.
    """
    if not text:
        return ""
    # Coerce non-string inputs (e.g. location dict) to string
    if not isinstance(text, str):
        text = str(text)
    # Remove [SYSTEM ...] / [INST ...] injection markers
    text = re.sub(
        r"\[(?:SYSTEM|INST|ASSISTANT|USER).*?\]",
        "[REDACTED]",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Remove "ignore/override/bypass/forget ... instructions/rules/prompt" patterns
    text = re.sub(
        r"(?:ignore|override|bypass|forget|disregard).{0,60}(?:instruction|prompt|rule|guideline|context|above)",
        "[REDACTED]",
        text,
        flags=re.IGNORECASE,
    )
    # Truncate to max_len and ensure valid UTF-8
    return text[:max_len].encode("utf-8", errors="ignore").decode("utf-8")


def build_base_prompt(
    task: dict,
    evidence: dict,
    *,
    category_checks: str = "",
    exif_context: str = "",
    rekognition_context: str = "",
) -> str:
    """Build the full PHOTINT verification prompt.

    Args:
        task: Task dict with title, description, category, location, etc.
        evidence: Submitted evidence metadata (GPS, timestamp, notes).
        category_checks: Category-specific verification instructions.
        exif_context: Pre-extracted EXIF metadata summary (optional).
        rekognition_context: AWS Rekognition labels/text (optional).

    Returns:
        Complete prompt string ready to send to a vision model.
    """
    task_type = task.get("task_type", task.get("category", "general"))
    title = task.get("title", "Unknown")
    # Sanitize free-text fields to prevent prompt injection (VECTOR-007)
    instructions = _sanitize_for_prompt(
        task.get("instructions", task.get("description", "No description")),
        max_len=1000,
    )
    location = _sanitize_for_prompt(
        task.get("location", task.get("location_text", "Not specified")), max_len=200
    )
    deadline = task.get("deadline", "Not specified")

    # Format evidence requirements
    requirements = _format_requirements(
        task.get("evidence_schema", task.get("evidence_required", {}))
    )

    # Format evidence metadata — sanitize worker-submitted free text
    gps = evidence.get("gps", "Not provided")
    timestamp = evidence.get("timestamp", "Not provided")
    notes = _sanitize_for_prompt(evidence.get("notes", "None"), max_len=500)

    # Build optional context sections
    metadata_section = ""
    if exif_context:
        metadata_section += f"""
## Pre-Extracted Technical Metadata (EXIF)
{exif_context}

Cross-reference this metadata against the visual content. Flag any inconsistencies.
"""

    if rekognition_context:
        metadata_section += f"""
## Pre-Analysis (Object/Scene Detection)
{rekognition_context}

Use these detected labels to cross-validate your visual analysis.
"""

    return f"""You are PHOTINT (Photographic Intelligence Analyst), an expert forensic evidence verifier for Execution Market — a marketplace where AI agents publish bounties for real-world tasks that human executors complete.

Your role: Determine if the submitted photo evidence proves that a task was completed correctly, honestly, and completely. You are the trust backbone of this platform. Real money moves based on your analysis.

You operate under the principle: "Every pixel is a witness. Every absence is a clue."

## Task Under Verification
- **Title**: {title}
- **Category**: {task_type}
- **Description**: {instructions}
- **Location**: {location}
- **Deadline**: {deadline}

## Evidence Requirements
{requirements}

## Submitted Evidence Metadata
- GPS coordinates: {gps}
- Submission timestamp: {timestamp}
- Worker notes: {notes}
{metadata_section}
## FORENSIC ANALYSIS FRAMEWORK

Perform a systematic multi-layered analysis of the submitted photo(s):

### Layer 1: Authenticity Assessment
- **Photo source**: Is this a direct camera capture, gallery photo, screenshot, or AI-generated image?
- **Manipulation check**: Look for clone-stamp artifacts, inconsistent lighting/shadows, resolution mismatches between regions, edge anomalies, unnatural textures.
- **Screenshot detection**: Look for device bezels, status bars, UI elements, rounded corners, notification bars.
- **AI generation indicators**: Unnatural skin texture, impossible geometry, text rendering errors, inconsistent reflections, repeating patterns, extra/missing fingers.
- **Compression analysis**: Uniform compression suggests original capture. Non-uniform compression across regions suggests editing.

### Layer 2: Provenance & Platform Chain
- **EXIF presence**: Original camera photos have full EXIF. Stripped EXIF means the image was processed through a platform (WhatsApp strips all, Instagram strips all, Twitter strips GPS only, iMessage preserves all).
- **Resolution check**: Modern phone cameras produce 12-200 MP images. An image under 2 MP from a "modern phone" has been through a messaging platform.
- **Container format**: JFIF container = re-encoded (messaging platform). EXIF container = closer to original.
- **Filename patterns**: IMG_YYYYMMDD = camera. IMG-YYYYMMDD-WA#### = WhatsApp. photo_YYYY-MM-DD = Telegram.

### Layer 3: Geospatial Verification
- **Visible text**: Read ALL signs, addresses, business names, street names, banners. Cross-reference with claimed location.
- **Architecture**: Building style, materials, regional patterns that confirm or contradict location.
- **Vegetation**: Tree species, landscaping style (tropical/temperate/arid), seasonal state.
- **Infrastructure**: Road surface, utility poles, traffic lights, fire hydrants — these vary by region/country.
- **Cross-reference**: Multiple independent geospatial indicators converging on the same location = HIGH confidence. Single indicator = LOW confidence.

### Layer 4: Temporal Verification
- **Shadow analysis**: Shadow direction and length indicate solar angle, which maps to time of day when combined with location. Short shadows = midday. Long shadows = morning/evening.
- **Lighting quality**: Golden hour glow, harsh midday light, overcast diffusion, artificial lighting.
- **Activity patterns**: Business open/closed, traffic density, pedestrian activity.
- **Seasonal indicators**: Foliage state, holiday decorations, seasonal merchandise.

### Layer 5: Task Completion Assessment
{
        category_checks
        if category_checks
        else '''- Does the photo clearly show what the task requested?
- Is there sufficient detail to verify completion?
- Are all required evidence elements present?
- Is there any indication of fraud or deception?'''
    }

## CONFIDENCE RATING SYSTEM

Rate every finding with a confidence level:
- **CONFIRMED**: Directly visible, readable, unambiguous (e.g., address number on building matches task location)
- **HIGH**: Strong visual evidence with minor inference (e.g., shadow analysis + known location narrows time to 1-hour window)
- **MODERATE**: Reasonable inference from multiple indicators (e.g., vegetation + architecture suggest correct region)
- **LOW**: Single indicator or significant inference required (e.g., "could be the right building but no confirming signage")

## DECISION CRITERIA

- **APPROVE** (confidence >= 0.80): Photo clearly demonstrates task completion. Evidence is authentic, location/time are consistent, and task requirements are met. Minor imperfections in a good-faith attempt are acceptable.
- **REJECT** (confidence in rejection >= 0.80): Clear evidence of fraud, manipulation, wrong location, incomplete task, or submitted evidence that does not match the task at all.
- **NEEDS_HUMAN** (uncertainty): Ambiguous evidence, borderline cases, or insufficient information to make a confident determination. Err on the side of NEEDS_HUMAN rather than a wrong APPROVE or REJECT.

## FRAUD INDICATORS (flag if detected)

- Photo is a screenshot of another photo (meta-photography)
- AI-generated content (especially for physical presence tasks)
- Clearly wrong location (signage/language/architecture mismatch)
- Timestamp inconsistency (EXIF says 3 days ago, submitted just now)
- Stock photo or previously-used image
- Evidence of staging (props, artificial setup)
- Metadata stripped when original was expected
- Claiming to have taken a photo but file characteristics indicate it was received via messaging

## RESPONSE FORMAT

Respond with ONLY this JSON (no other text before or after):
```json
{VERIFICATION_OUTPUT_SCHEMA}
```

The task_checks object should include these category-relevant checks as boolean values. Be strict but fair."""


def _format_requirements(requirements) -> str:
    """Format evidence requirements for prompt inclusion."""
    if not requirements:
        return "- No specific requirements listed"

    lines = []
    if isinstance(requirements, dict):
        required = requirements.get("required", [])
        optional = requirements.get("optional", [])
        if required:
            for item in required:
                if isinstance(item, str):
                    lines.append(f"- {item.replace('_', ' ').title()} (required)")
                elif isinstance(item, dict):
                    lines.append(
                        f"- {item.get('type', 'Unknown').replace('_', ' ').title()} (required)"
                    )
        if optional:
            for item in optional:
                if isinstance(item, str):
                    lines.append(f"- {item.replace('_', ' ').title()} (optional)")
    elif isinstance(requirements, list):
        for item in requirements:
            if isinstance(item, str):
                lines.append(f"- {item.replace('_', ' ').title()}")

    return "\n".join(lines) if lines else "- General photo evidence"
