"""
PHOTINT Prompt Library

Central registry for all verification prompts. Each task category has a
specialized forensic prompt that extends the PHOTINT base framework.

Usage:
    from verification.prompts import PromptLibrary

    lib = PromptLibrary()
    result = lib.get_prompt(
        category="physical_presence",
        task=task_dict,
        evidence=evidence_dict,
    )
    # result.text  — full rendered prompt
    # result.version  — "photint-v1.0-physical_presence"
    # result.hash  — SHA-256 of rendered prompt
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

from .base import build_base_prompt
from .version import prompt_version

# Category prompt modules — each exports get_category_checks(task) -> str
from . import (
    physical_presence,
    knowledge_access,
    human_authority,
    simple_action,
    digital_physical,
    location_based,
    verification,
    social_proof,
    data_collection,
    sensory,
    social,
    proxy,
    bureaucratic,
    emergency,
    creative,
    digital_fallback,
)


@dataclass
class PromptResult:
    """Result of prompt generation."""

    text: str  # Full rendered prompt
    version: str  # e.g. "photint-v1.0-physical_presence"
    hash: str  # SHA-256 of the rendered prompt
    category: str  # Task category used


# Registry mapping category -> module with get_category_checks()
_CATEGORY_MODULES = {
    "physical_presence": physical_presence,
    "knowledge_access": knowledge_access,
    "human_authority": human_authority,
    "simple_action": simple_action,
    "digital_physical": digital_physical,
    "location_based": location_based,
    "verification": verification,
    "social_proof": social_proof,
    "data_collection": data_collection,
    "sensory": sensory,
    "social": social,
    "proxy": proxy,
    "bureaucratic": bureaucratic,
    "emergency": emergency,
    "creative": creative,
    # Digital-only categories all use the same fallback
    "data_processing": digital_fallback,
    "api_integration": digital_fallback,
    "content_generation": digital_fallback,
    "code_execution": digital_fallback,
    "research": digital_fallback,
    "multi_step_workflow": digital_fallback,
}


class PromptLibrary:
    """Central registry for PHOTINT verification prompts."""

    def get_prompt(
        self,
        category: str,
        task: dict,
        evidence: dict,
        *,
        exif_context: str = "",
        rekognition_context: str = "",
    ) -> PromptResult:
        """Generate the full verification prompt for a task.

        Args:
            category: Task category (e.g. "physical_presence").
            task: Task dict with title, description, etc.
            evidence: Submitted evidence metadata.
            exif_context: Pre-extracted EXIF summary (optional).
            rekognition_context: Rekognition labels/text (optional).

        Returns:
            PromptResult with rendered text, version, and hash.
        """
        # Get category-specific checks
        module = _CATEGORY_MODULES.get(category)
        if module is not None:
            category_checks = module.get_category_checks(task)
        else:
            category_checks = _default_checks()

        # Build full prompt
        prompt_text = build_base_prompt(
            task=task,
            evidence=evidence,
            category_checks=category_checks,
            exif_context=exif_context,
            rekognition_context=rekognition_context,
        )

        # Compute hash
        prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

        # Determine version
        version = prompt_version(
            category if category in _CATEGORY_MODULES else "general"
        )

        return PromptResult(
            text=prompt_text,
            version=version,
            hash=prompt_hash,
            category=category,
        )

    def list_categories(self) -> list:
        """List all supported task categories."""
        return sorted(_CATEGORY_MODULES.keys())

    def has_category(self, category: str) -> bool:
        """Check if a category has a specialized prompt."""
        return category in _CATEGORY_MODULES


def _default_checks() -> str:
    """Fallback checks for unknown categories."""
    return """### Task Completion Checks
- Does the photo clearly show what the task requested?
- Is there sufficient detail to verify completion?
- Are all required evidence elements present?
- Is there any indication of fraud or deception?
- Is the photo authentic and unmanipulated?"""


# Module-level singleton
_library: Optional[PromptLibrary] = None


def get_prompt_library() -> PromptLibrary:
    """Get the module-level PromptLibrary singleton."""
    global _library
    if _library is None:
        _library = PromptLibrary()
    return _library
