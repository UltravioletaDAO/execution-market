"""
Ring 2 Provider Stack — Inference providers for semantic task-completion evaluation.

Provider priority (per x402r arbiter research):
1. ClawRouter (primary) -- pay-per-inference with USDC via x402, no API key
2. EigenAI (secondary, MAX tier) -- deterministic verifiable inference
3. OpenRouter (fallback) -- traditional OpenAI-compatible API with API key
4. Ollama (dev/test) -- local models, no API key

See: docs/reports/security-audit-2026-04-07/X402R_ARBITER_RESEARCH.md
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..types import ArbiterTier

logger = logging.getLogger(__name__)


@dataclass
class Ring2Response:
    """Response from a Ring 2 inference provider."""

    completed: bool
    confidence: float  # 0.0 - 1.0
    reason: str
    model: str
    provider: str
    cost_usd: float
    raw_response: Optional[str] = None


class Ring2Provider(ABC):
    """Abstract base for Ring 2 inference providers.

    All providers implement an OpenAI-compatible chat completions interface
    but differ in auth (API key vs x402 payment vs wallet-grant).
    """

    @abstractmethod
    async def evaluate(self, prompt: str, tier: ArbiterTier) -> Ring2Response:
        """Send a Ring 2 prompt to the provider and return a structured response.

        Args:
            prompt: The full user prompt (system prompt is provider-internal).
            tier: The inference tier (affects model selection).

        Returns:
            Ring2Response with completion verdict, confidence, and cost.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and ready to use.

        Returns False if required env vars are missing or the provider
        is known to be unavailable.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and RingScore.provider field."""
        ...


def get_ring2_provider() -> Ring2Provider:
    """Get primary Ring 2 provider.

    Priority: ClawRouter > OpenRouter.
    ClawRouter is the x402r-native way (pay with USDC, no API key).
    OpenRouter is the fallback (traditional API key auth).

    Raises:
        RuntimeError: If no provider is available.
    """
    from .clawrouter import ClawRouterProvider
    from .openrouter import OpenRouterProvider

    claw = ClawRouterProvider()
    if claw.is_available():
        logger.debug("Ring 2 primary provider: ClawRouter")
        return claw

    openrouter = OpenRouterProvider()
    if openrouter.is_available():
        logger.debug("Ring 2 primary provider: OpenRouter (ClawRouter unavailable)")
        return openrouter

    raise RuntimeError(
        "No Ring 2 provider available. "
        "Set CLAWROUTER_WALLET_KEY for ClawRouter or OPENROUTER_API_KEY for OpenRouter."
    )


def get_ring2_secondary_provider() -> Ring2Provider:
    """Get secondary provider for MAX tier dual-model consensus.

    Priority: EigenAI > OpenRouter with different model family.
    The secondary MUST use a different model than the primary to ensure
    independent verdicts in the 3-way consensus.

    Returns:
        Ring2Provider instance. Never raises -- falls back to OpenRouter
        with a different model family.
    """
    from .eigenai import EigenAIProvider
    from .openrouter import OpenRouterProvider

    eigen = EigenAIProvider()
    if eigen.is_available():
        logger.debug("Ring 2 secondary provider: EigenAI")
        return eigen

    # Fallback: OpenRouter with a different model family than primary
    logger.debug("Ring 2 secondary provider: OpenRouter/gpt-4o (EigenAI unavailable)")
    return OpenRouterProvider(model_override="openai/gpt-4o")


__all__ = [
    "Ring2Provider",
    "Ring2Response",
    "get_ring2_provider",
    "get_ring2_secondary_provider",
]
