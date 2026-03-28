"""
PHOTINT Prompt Versioning

Every prompt has a version string: photint-v{MAJOR}.{MINOR}-{category}
This allows tracking which prompt version produced which verification result,
enabling A/B testing and prompt iteration.
"""

# Current prompt library version
MAJOR = 1
MINOR = 0

VERSION = f"{MAJOR}.{MINOR}"


def prompt_version(category: str) -> str:
    """Generate version string for a category prompt.

    Example: photint-v1.0-physical_presence
    """
    return f"photint-v{VERSION}-{category}"
