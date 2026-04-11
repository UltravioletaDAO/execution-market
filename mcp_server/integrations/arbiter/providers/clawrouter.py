"""
ClawRouter Provider — Pay-per-inference with USDC via x402 protocol.

ClawRouter (by BlockRunAI) is an OpenAI-compatible inference gateway that
accepts USDC payment via x402 instead of API keys. It routes to 55+ models.

API: POST https://blockrun.ai/api/v1/chat/completions
Auth: x402 USDC payment (requires funded wallet on Base)
Docs: https://github.com/BlockRunAI/ClawRouter

In the x402r arbiter-examples repo, ClawRouter is the DEFAULT provider.
It uses `wrapFetchWithPayment(fetch, client)` from `@x402/fetch` to
handle the 402 payment flow automatically (TypeScript SDK).

For Python, we implement the OpenAI-compatible client with a configurable
base URL. The x402 payment header integration requires the Python x402 SDK
which wraps the payment handshake. Until that SDK is available, this
provider falls back to standard Bearer auth if CLAWROUTER_API_KEY is set.

Env vars:
    CLAWROUTER_BASE_URL: API base URL (default: https://blockrun.ai/api/v1)
    CLAWROUTER_MODEL: Default model (default: openai/gpt-4o-mini)
    CLAWROUTER_API_KEY: API key (temporary fallback until x402 payment SDK)
    CLAWROUTER_WALLET_KEY: Wallet private key for x402 USDC payment (future)

See: docs/reports/security-audit-2026-04-07/X402R_ARBITER_RESEARCH.md
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

from ..types import ArbiterTier
from . import Ring2Provider, Ring2Response
from ..prompts import RING2_SYSTEM_PROMPT, parse_ring2_response

logger = logging.getLogger(__name__)

# Model selection by tier
TIER_MODELS = {
    ArbiterTier.CHEAP: "openai/gpt-4o-mini",  # Should not be called for CHEAP
    ArbiterTier.STANDARD: "openai/gpt-4o-mini",
    ArbiterTier.MAX: "anthropic/claude-sonnet-4-6",
}

DEFAULT_BASE_URL = "https://blockrun.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
TIMEOUT_SECONDS = 30
MAX_TOKENS = 512


class ClawRouterProvider(Ring2Provider):
    """ClawRouter: x402r-native pay-per-inference provider.

    Uses USDC payment via x402 protocol. Falls back to API key auth
    when x402 payment SDK is not available.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_override: Optional[str] = None,
    ):
        self._base_url = (
            base_url or os.environ.get("CLAWROUTER_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self._model_override = model_override or os.environ.get("CLAWROUTER_MODEL")
        self._api_key = os.environ.get("CLAWROUTER_API_KEY", "")
        # TODO: Wire x402 USDC payment header via Python x402 SDK
        # when available. For now, use API key as fallback auth.
        # See: @x402/fetch wrapFetchWithPayment() in TS SDK

    @property
    def name(self) -> str:
        return "clawrouter"

    def is_available(self) -> bool:
        """ClawRouter is available if we have either an API key or wallet key."""
        return bool(self._api_key or os.environ.get("CLAWROUTER_WALLET_KEY"))

    def _select_model(self, tier: ArbiterTier) -> str:
        """Select model based on tier, with override support."""
        if self._model_override:
            return self._model_override
        return TIER_MODELS.get(tier, DEFAULT_MODEL)

    async def evaluate(self, prompt: str, tier: ArbiterTier) -> Ring2Response:
        """Send Ring 2 evaluation prompt to ClawRouter.

        Args:
            prompt: User prompt with task + evidence summary.
            tier: Inference tier for model selection.

        Returns:
            Ring2Response with verdict.

        Raises:
            httpx.HTTPStatusError: On non-2xx response after retries.
            Exception: On network/parsing errors.
        """
        model = self._select_model(tier)
        payload = self._build_request(prompt, model)

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = f"{self._base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data, model)

    def _build_request(self, prompt: str, model: str) -> Dict[str, Any]:
        """Build OpenAI-compatible chat completion request."""
        return {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": RING2_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }

    def _parse_response(self, data: Dict[str, Any], model: str) -> Ring2Response:
        """Parse OpenAI-compatible response into Ring2Response."""
        choices = data.get("choices", [])
        if not choices:
            return Ring2Response(
                completed=False,
                confidence=0.0,
                reason="Empty response from ClawRouter",
                model=model,
                provider=self.name,
                cost_usd=0.0,
                raw_response=json.dumps(data),
            )

        content = choices[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        cost = float(usage.get("total_cost", 0.0))

        parsed = parse_ring2_response(content)

        return Ring2Response(
            completed=parsed["completed"],
            confidence=parsed["confidence"],
            reason=parsed["reason"],
            model=data.get("model", model),
            provider=self.name,
            cost_usd=cost,
            raw_response=content,
        )
