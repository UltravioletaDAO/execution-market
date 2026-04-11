"""
EigenAI Provider — Deterministic verifiable inference via EigenLayer AVS.

EigenAI provides cryptographically verifiable LLM inference: the same
request with the same seed produces the same output bit-for-bit, and
a verification layer (EigenVerify) provides bonded attestations.

API: POST https://eigenai.eigencloud.xyz/v1/chat/completions
Auth: x-api-key header (simplified from wallet-grant for Python integration)
Model: gpt-oss-120b-f16 (single model, 120B params, float16)

Key value for Ring 2: deterministic replay enables provably fair verdicts.
If disputed, anyone can re-run the exact inference and confirm the output.

Used ONLY for MAX tier (secondary model in dual-consensus).

Env vars:
    EIGENAI_API_KEY: API key for authentication
    EIGENAI_BASE_URL: API base URL (default: https://eigenai.eigencloud.xyz/v1)
    EIGENAI_MODEL: Model ID (default: gpt-oss-120b-f16)
    EIGENAI_SEED: Deterministic seed for reproducibility (default: 42)

Note: The x402r arbiter-examples repo uses wallet-grant auth
(EIP-191 signature challenge). This implementation uses API key auth
for simplicity. TODO: Add wallet-grant auth for full x402r parity.

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

DEFAULT_BASE_URL = "https://eigenai.eigencloud.xyz/v1"
DEFAULT_MODEL = "gpt-oss-120b-f16"
DEFAULT_SEED = 42
TIMEOUT_SECONDS = 60  # EigenAI can be slower (large model, verification overhead)
MAX_TOKENS = 512


class EigenAIProvider(Ring2Provider):
    """EigenAI: deterministic verifiable inference for MAX tier.

    Only used as secondary provider in dual-model consensus.
    Single model (gpt-oss-120b-f16) with deterministic seed.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_override: Optional[str] = None,
    ):
        self._base_url = (
            base_url or os.environ.get("EIGENAI_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self._model = model_override or os.environ.get("EIGENAI_MODEL", DEFAULT_MODEL)
        self._api_key = os.environ.get("EIGENAI_API_KEY", "")
        self._seed = int(os.environ.get("EIGENAI_SEED", str(DEFAULT_SEED)))

    @property
    def name(self) -> str:
        return "eigenai"

    def is_available(self) -> bool:
        """EigenAI is available if we have an API key.

        Note: The x402r arbiter-examples repo marks EigenAI as
        'currently unavailable'. This check allows graceful fallback
        to OpenRouter when EigenAI is not configured.
        """
        return bool(self._api_key)

    async def evaluate(self, prompt: str, tier: ArbiterTier) -> Ring2Response:
        """Send Ring 2 evaluation prompt to EigenAI.

        Uses deterministic seed for reproducible verdicts. The seed
        is included in the commitment hash for on-chain auditability.

        Args:
            prompt: User prompt with task + evidence summary.
            tier: Inference tier (EigenAI is MAX-only, ignored here).

        Returns:
            Ring2Response with verdict.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
            Exception: On network/parsing errors.
        """
        payload = self._build_request(prompt)

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
        }

        url = f"{self._base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data)

    def _build_request(self, prompt: str) -> Dict[str, Any]:
        """Build OpenAI-compatible request with deterministic seed."""
        return {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
            "seed": self._seed,  # REQUIRED for deterministic replay
            "messages": [
                {"role": "system", "content": RING2_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }

    def _parse_response(self, data: Dict[str, Any]) -> Ring2Response:
        """Parse OpenAI-compatible response into Ring2Response."""
        choices = data.get("choices", [])
        if not choices:
            return Ring2Response(
                completed=False,
                confidence=0.0,
                reason="Empty response from EigenAI",
                model=self._model,
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
            model=data.get("model", self._model),
            provider=self.name,
            cost_usd=cost,
            raw_response=content,
        )
