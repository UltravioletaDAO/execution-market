"""
OpenRouter Provider — Traditional OpenAI-compatible API with API key auth.

OpenRouter provides access to 300+ models from 30+ providers through a
single API. It is the FALLBACK provider when ClawRouter is unavailable.

API: POST https://openrouter.ai/api/v1/chat/completions
Auth: Authorization: Bearer $OPENROUTER_API_KEY
Docs: https://openrouter.ai/docs

Key features for Ring 2:
- Model diversity for MAX tier consensus (different provider families)
- Per-request cost tracking via usage.total_cost
- Built-in failover via model array
- Structured output via response_format: json_schema

Env vars:
    OPENROUTER_API_KEY: API key (required)
    OPENROUTER_MODEL_STANDARD: Model for STANDARD tier
        (default: anthropic/claude-haiku-4-5-20251001)
    OPENROUTER_MODEL_MAX: Model for MAX tier primary
        (default: anthropic/claude-sonnet-4-6)
    OPENROUTER_BASE_URL: API base URL
        (default: https://openrouter.ai/api/v1)

See: docs/reports/security-audit-2026-04-07/RING2_ARBITER_ARCHITECTURE.md
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

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL_STANDARD = "anthropic/claude-haiku-4-5"
DEFAULT_MODEL_MAX = "anthropic/claude-sonnet-4-6"
TIMEOUT_SECONDS = 30
MAX_TOKENS = 512


class OpenRouterProvider(Ring2Provider):
    """OpenRouter: fallback OpenAI-compatible provider with API key auth.

    Supports 300+ models. Used as:
    - Primary fallback when ClawRouter is unavailable (STANDARD + MAX)
    - Secondary model in MAX tier when EigenAI is unavailable
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_override: Optional[str] = None,
    ):
        self._base_url = (
            base_url or os.environ.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self._model_override = model_override
        self._api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self._model_standard = os.environ.get(
            "OPENROUTER_MODEL_STANDARD", DEFAULT_MODEL_STANDARD
        )
        self._model_max = os.environ.get("OPENROUTER_MODEL_MAX", DEFAULT_MODEL_MAX)

    @property
    def name(self) -> str:
        return "openrouter"

    def is_available(self) -> bool:
        """OpenRouter is available if we have an API key."""
        return bool(self._api_key)

    def _select_model(self, tier: ArbiterTier) -> str:
        """Select model based on tier, with override support."""
        if self._model_override:
            return self._model_override
        if tier == ArbiterTier.MAX:
            return self._model_max
        return self._model_standard

    async def evaluate(self, prompt: str, tier: ArbiterTier) -> Ring2Response:
        """Send Ring 2 evaluation prompt to OpenRouter.

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
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": "https://execution.market",
            "X-OpenRouter-Title": "Execution Market Arbiter",
        }

        url = f"{self._base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code >= 400:
                try:
                    error_body = response.json()
                    error_detail = error_body.get("error", {}).get(
                        "message", response.text[:500]
                    )
                except Exception:
                    error_detail = response.text[:500]
                logger.error(
                    "OpenRouter %d for model=%s: %s",
                    response.status_code,
                    model,
                    error_detail,
                )
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
                reason="Empty response from OpenRouter",
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
