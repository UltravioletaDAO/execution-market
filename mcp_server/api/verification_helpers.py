"""Verification helpers for API routes."""

from verification.ai_review import AIVerifier

_verifier = None


def get_verifier() -> AIVerifier:
    """Get or create the singleton AIVerifier instance."""
    global _verifier
    if _verifier is None:
        _verifier = AIVerifier()
    return _verifier
