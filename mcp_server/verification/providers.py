"""
Multi-Provider AI Verification for Evidence Analysis

Supports multiple AI providers for evidence verification:
- Google Gemini (cheapest, ~$0.25/1K images) — default
- Anthropic (Claude Vision)
- OpenAI (GPT-4 Vision)
- AWS Bedrock (Claude, Titan)

Configuration via environment variables:
  AI_VERIFICATION_PROVIDER=gemini|anthropic|openai|bedrock  (default: gemini)
  GOOGLE_API_KEY=...
  ANTHROPIC_API_KEY=sk-ant-...
  OPENAI_API_KEY=sk-...
  AWS_BEDROCK_REGION=us-east-1  (default: us-east-2)
  AI_VERIFICATION_MODEL=<model-id>  (optional override)
"""

import asyncio
import os
import json
import base64
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Default timeout for all LLM inference calls (seconds).
# Gemini Flash typically responds in 5-15s; 60s is generous enough for
# large images on tier_3/tier_4 models while still preventing infinite hangs.
LLM_INFERENCE_TIMEOUT = int(os.environ.get("LLM_INFERENCE_TIMEOUT", "60"))


@dataclass
class ProviderConfig:
    """Configuration for a verification provider."""

    name: str
    model: str
    api_key: Optional[str] = None
    region: Optional[str] = None


@dataclass
class VisionRequest:
    """Standardized vision request across providers."""

    prompt: str
    images: List[bytes]
    image_types: List[str]  # MIME types
    max_tokens: int = 1024


@dataclass
class VisionResponse:
    """Standardized vision response across providers."""

    text: str
    model: str
    provider: str
    usage: dict  # token counts


class VerificationProvider(ABC):
    """Abstract base for AI verification providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        ...

    @abstractmethod
    async def analyze(self, request: VisionRequest) -> VisionResponse:
        """Send images + prompt to the provider and get analysis."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        ...


class AnthropicProvider(VerificationProvider):
    """Anthropic Claude Vision provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model_id = model or os.environ.get(
            "AI_VERIFICATION_MODEL", "claude-sonnet-4-6"
        )

    @property
    def name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        content = []
        for img_data, mime_type in zip(request.images, request.image_types):
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": base64.b64encode(img_data).decode(),
                    },
                }
            )
        content.append({"type": "text", "text": request.prompt})

        try:
            message = await asyncio.wait_for(
                client.messages.create(
                    model=self.model_id,
                    max_tokens=request.max_tokens,
                    messages=[{"role": "user", "content": content}],
                ),
                timeout=LLM_INFERENCE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Anthropic inference timed out after {LLM_INFERENCE_TIMEOUT}s "
                f"(model={self.model_id})"
            )

        return VisionResponse(
            text=message.content[0].text,
            model=self.model_id,
            provider=self.name,
            usage={
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            },
        )


class OpenAIProvider(VerificationProvider):
    """OpenAI GPT-4 Vision provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model_id = model or os.environ.get("AI_VERIFICATION_MODEL", "gpt-4o")

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        content = []
        for img_data, mime_type in zip(request.images, request.image_types):
            b64 = base64.b64encode(img_data).decode()
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                }
            )
        content.append({"type": "text", "text": request.prompt})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_id,
                    "max_tokens": request.max_tokens,
                    "messages": [{"role": "user", "content": content}],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})

        return VisionResponse(
            text=choice["message"]["content"],
            model=self.model_id,
            provider=self.name,
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
        )


class BedrockProvider(VerificationProvider):
    """AWS Bedrock provider (Claude via Bedrock)."""

    def __init__(self, region: Optional[str] = None, model: Optional[str] = None):
        self.region = region or os.environ.get("AWS_BEDROCK_REGION", "us-east-2")
        self.model_id = model or os.environ.get(
            "AI_VERIFICATION_MODEL", "anthropic.claude-sonnet-4-6-v1:0"
        )

    @property
    def name(self) -> str:
        return "bedrock"

    def is_available(self) -> bool:
        try:
            import boto3

            boto3.client("bedrock-runtime", region_name=self.region)
            return True
        except Exception:
            return False

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=self.region)

        content = []
        for img_data, mime_type in zip(request.images, request.image_types):
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": base64.b64encode(img_data).decode(),
                    },
                }
            )
        content.append({"type": "text", "text": request.prompt})

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": request.max_tokens,
                "messages": [{"role": "user", "content": content}],
            }
        )

        # boto3 is synchronous — run in thread to avoid blocking the event loop.
        # Wrapped in wait_for to prevent infinite hangs.
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.invoke_model,
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=body,
                ),
                timeout=LLM_INFERENCE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Bedrock inference timed out after {LLM_INFERENCE_TIMEOUT}s "
                f"(model={self.model_id})"
            )

        result = json.loads(response["body"].read())

        return VisionResponse(
            text=result["content"][0]["text"],
            model=self.model_id,
            provider=self.name,
            usage={
                "input_tokens": result.get("usage", {}).get("input_tokens", 0),
                "output_tokens": result.get("usage", {}).get("output_tokens", 0),
            },
        )


class GeminiProvider(VerificationProvider):
    """Google Gemini provider (cheapest vision model).

    Uses the Gemini REST API directly via httpx instead of the
    ``google-generativeai`` SDK.  The SDK is synchronous under the hood and
    ``asyncio.to_thread()`` + ``asyncio.wait_for()`` cannot cancel the
    underlying blocking thread in CPython, which caused production hangs.
    A native async HTTP call with ``httpx`` respects the timeout correctly.
    """

    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.model_id = model or os.environ.get(
            "AI_VERIFICATION_MODEL", "gemini-2.5-flash"
        )

    @property
    def name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        """Call Gemini REST API with images + prompt.

        Timeout is enforced at the HTTP-transport level so there is no
        unkillable background thread.
        """
        import time

        # Build multimodal parts: images first, then the text prompt.
        parts: list[dict] = []
        for img_data, mime_type in zip(request.images, request.image_types):
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(img_data).decode(),
                    }
                }
            )
        parts.append({"text": request.prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"maxOutputTokens": request.max_tokens},
        }

        url = (
            f"{self._BASE_URL}/models/{self.model_id}:generateContent"
            f"?key={self.api_key}"
        )

        logger.info("Gemini HTTP: calling %s...", self.model_id)
        t0 = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(LLM_INFERENCE_TIMEOUT, connect=10.0),
            ) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Gemini inference timed out after {LLM_INFERENCE_TIMEOUT}s "
                f"(model={self.model_id})"
            )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info("Gemini HTTP: %s responded in %dms", self.model_id, elapsed_ms)

        # --- Error handling ------------------------------------------------
        if resp.status_code == 429:
            raise RuntimeError("rate limited")
        if resp.status_code in (400, 401, 403):
            try:
                detail = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                detail = resp.text
            raise ValueError(f"Gemini API error {resp.status_code}: {detail}")
        resp.raise_for_status()

        # --- Parse response ------------------------------------------------
        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ValueError(
                f"Unexpected Gemini response structure: {exc}. "
                f"Response: {json.dumps(data)[:500]}"
            )

        usage_meta = data.get("usageMetadata", {})
        usage = {
            "input_tokens": usage_meta.get("promptTokenCount", 0),
            "output_tokens": usage_meta.get("candidatesTokenCount", 0),
        }

        return VisionResponse(
            text=text,
            model=self.model_id,
            provider=self.name,
            usage=usage,
        )

    @classmethod
    async def validate_key(cls, api_key: Optional[str] = None) -> bool:
        """Lightweight check that the API key is valid.

        Makes a minimal generateContent call ("hello") and logs success or
        failure.  Returns ``True`` when the key works, ``False`` otherwise.
        This is informational — never blocks startup.
        """
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not key:
            logger.warning("Gemini validate_key: GOOGLE_API_KEY not set")
            return False

        url = f"{cls._BASE_URL}/models/gemini-2.5-flash:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": "hello"}]}],
            "generationConfig": {"maxOutputTokens": 8},
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Gemini validate_key: OK (key is valid)")
                return True
            logger.warning(
                "Gemini validate_key: HTTP %d — %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
        except Exception as exc:
            logger.warning("Gemini validate_key: failed — %s", exc)
            return False


# Provider registry
PROVIDERS = {
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "bedrock": BedrockProvider,
}


def get_provider(
    provider_name: Optional[str] = None,
    **kwargs,
) -> VerificationProvider:
    """
    Get a verification provider by name.

    Falls back through providers if the requested one is unavailable:
    1. Requested provider (env AI_VERIFICATION_PROVIDER or parameter)
    2. Anthropic (if API key available)
    3. OpenAI (if API key available)
    4. Bedrock (if AWS credentials available)

    Raises ValueError if no provider is available.
    """
    name = provider_name or os.environ.get("AI_VERIFICATION_PROVIDER", "gemini")

    # Try requested provider first
    if name in PROVIDERS:
        provider = PROVIDERS[name](**kwargs)
        if provider.is_available():
            logger.info(
                "Using AI provider: %s (model: %s)", provider.name, provider.model_id
            )
            return provider
        logger.warning("Requested provider '%s' not available, trying fallbacks", name)

    # Fallback chain
    for fallback_name, cls in PROVIDERS.items():
        if fallback_name == name:
            continue
        try:
            provider = cls()
            if provider.is_available():
                logger.info("Falling back to AI provider: %s", provider.name)
                return provider
        except Exception:
            continue

    raise ValueError(
        "No AI verification provider available. "
        "Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or configure AWS Bedrock."
    )


# ---------------------------------------------------------------------------
# Tier-based model selection
# ---------------------------------------------------------------------------

# Default models per tier — (provider, model_id)
# tier_1: cheapest, fastest — bulk screening, low-value tasks
# tier_2: mid-range — standard verification, balanced cost/quality
# tier_3: premium — high-value tasks, disputed evidence
# tier_4: frontier — consensus tiebreakers, critical disputes
TIER_MODELS = {
    "tier_1": [
        ("gemini", "gemini-2.5-flash-lite"),
        ("openai", "gpt-4.1-nano"),
        ("openai", "gpt-4o-mini"),
    ],
    "tier_2": [
        ("gemini", "gemini-2.5-flash"),
        ("openai", "gpt-4.1-mini"),
        ("anthropic", "claude-haiku-4-5-20251001"),
    ],
    "tier_3": [
        ("openai", "gpt-4.1"),
        ("anthropic", "claude-sonnet-4-6"),
        ("gemini", "gemini-2.5-pro"),
    ],
    "tier_4": [
        ("anthropic", "claude-opus-4-6"),
        ("bedrock", "anthropic.claude-opus-4-6-v1:0"),
    ],
}


def get_provider_for_tier(
    tier: str,
    exclude_providers: Optional[List[str]] = None,
) -> Optional[VerificationProvider]:
    """
    Get the best available provider for a verification tier.

    Tries each model in the tier's preference order, returning the
    first one with valid credentials. Returns None if no provider
    is available for this tier.

    Args:
        tier: "tier_1", "tier_2", "tier_3", or "tier_4"
        exclude_providers: Provider names to skip (for consensus/diversity)
    """
    exclude = set(exclude_providers or [])
    candidates = TIER_MODELS.get(tier, TIER_MODELS["tier_2"])

    for provider_name, model_id in candidates:
        if provider_name in exclude:
            continue
        if provider_name not in PROVIDERS:
            continue
        try:
            provider = PROVIDERS[provider_name](model=model_id)
            if provider.is_available():
                logger.info("Tier %s: using %s/%s", tier, provider_name, model_id)
                return provider
        except Exception:
            continue

    return None


def get_providers_for_tier(
    tier: str,
    exclude_providers: Optional[List[str]] = None,
) -> List[VerificationProvider]:
    """
    Get ALL available providers for a verification tier, in preference order.

    Unlike ``get_provider_for_tier`` which returns only the first match,
    this returns the full fallback chain so callers can retry within a tier
    when the primary provider fails (timeout, error, rate limit).

    Args:
        tier: "tier_1", "tier_2", "tier_3", or "tier_4"
        exclude_providers: Provider names to skip (for consensus/diversity)

    Returns:
        List of available providers, ordered by tier preference. May be empty.
    """
    exclude = set(exclude_providers or [])
    candidates = TIER_MODELS.get(tier, TIER_MODELS["tier_2"])
    result: List[VerificationProvider] = []

    for provider_name, model_id in candidates:
        if provider_name in exclude:
            continue
        if provider_name not in PROVIDERS:
            continue
        try:
            provider = PROVIDERS[provider_name](model=model_id)
            if provider.is_available():
                result.append(provider)
        except Exception:
            continue

    return result


def list_available_providers() -> List[dict]:
    """List all providers and their availability status."""
    result = []
    for name, cls in PROVIDERS.items():
        try:
            p = cls()
            result.append(
                {
                    "name": name,
                    "available": p.is_available(),
                    "model": p.model_id,
                }
            )
        except Exception:
            result.append({"name": name, "available": False, "model": None})
    return result


# ---------------------------------------------------------------------------
# Provider fallback chain — ordered by cost (cheapest first)
# ---------------------------------------------------------------------------

# Cost order: Gemini (~$0.001/call) < OpenAI GPT-4o (~$0.01) < Anthropic (~$0.01) < Bedrock (fallback)
PROVIDER_COST_ORDER: List[str] = ["gemini", "openai", "anthropic", "bedrock"]

# Total wall-clock budget for the entire fallback chain (seconds).
# Individual providers have LLM_INFERENCE_TIMEOUT (default 60s) each.
FALLBACK_CHAIN_TIMEOUT = int(os.environ.get("FALLBACK_CHAIN_TIMEOUT", "180"))


def get_provider_chain() -> List[VerificationProvider]:
    """Return available providers ordered by cost (cheapest first).

    Only includes providers whose ``is_available()`` returns True.
    Order: Gemini -> OpenAI -> Anthropic -> Bedrock.
    """
    chain: List[VerificationProvider] = []
    for name in PROVIDER_COST_ORDER:
        cls = PROVIDERS.get(name)
        if cls is None:
            continue
        try:
            provider = cls()
            if provider.is_available():
                chain.append(provider)
        except Exception:
            continue
    return chain


async def validate_all_providers() -> None:
    """Log health status of all verification providers at startup.

    Iterates the provider chain (cost order) and checks each provider's
    availability.  For providers with a ``validate_key`` classmethod
    (e.g. Gemini), performs a lightweight API probe.

    Never raises -- purely informational for startup diagnostics.
    """
    chain = get_provider_chain()
    if not chain:
        logger.critical(
            "[STARTUP] No verification providers available! "
            "Ring 1 will fail for all submissions."
        )
        return

    results: List[str] = []
    for provider in chain:
        try:
            # GeminiProvider exposes validate_key as a classmethod
            if hasattr(type(provider), "validate_key") and callable(
                getattr(type(provider), "validate_key")
            ):
                ok = await type(provider).validate_key()
                results.append(f"{provider.name}={'OK' if ok else 'INVALID'}")
            else:
                results.append(f"{provider.name}=available")
        except Exception as e:
            results.append(f"{provider.name}=ERROR({e})")

    logger.info("[STARTUP] Provider health: %s", ", ".join(results))


async def analyze_with_fallback(
    request: VisionRequest,
) -> Tuple[Optional[VisionResponse], List[Dict[str, Any]]]:
    """Try each provider in cost order; return first success.

    Returns:
        A tuple of (response, attempts) where *response* is the
        ``VisionResponse`` from the first provider that succeeded,
        or ``None`` if every provider failed.  *attempts* is a list of
        dicts recording each provider tried::

            {"provider": str, "model": str, "status": str,
             "latency_ms": int, "error": str | None}

    The function enforces two layers of timeout:
    * Per-provider: ``LLM_INFERENCE_TIMEOUT`` (default 60 s)
    * Overall chain: ``FALLBACK_CHAIN_TIMEOUT`` (default 180 s)
    """
    chain = get_provider_chain()
    if not chain:
        logger.warning("Fallback chain: no providers available")
        return None, [
            {
                "provider": "none",
                "model": None,
                "status": "no_providers",
                "latency_ms": 0,
                "error": "No AI verification providers configured",
            }
        ]

    attempts: List[Dict[str, Any]] = []
    chain_start = time.monotonic()

    for provider in chain:
        # Check overall chain budget
        elapsed_total = time.monotonic() - chain_start
        remaining = FALLBACK_CHAIN_TIMEOUT - elapsed_total
        if remaining <= 0:
            logger.warning(
                "Fallback chain: overall timeout (%ds) exhausted after %d attempts",
                FALLBACK_CHAIN_TIMEOUT,
                len(attempts),
            )
            attempts.append(
                {
                    "provider": provider.name,
                    "model": provider.model_id,
                    "status": "skipped_chain_timeout",
                    "latency_ms": 0,
                    "error": f"Chain timeout ({FALLBACK_CHAIN_TIMEOUT}s) exhausted",
                }
            )
            break

        logger.info(
            "Ring 1 [fallback] trying %s/%s...",
            provider.name,
            provider.model_id,
        )
        t0 = time.monotonic()

        try:
            response = await asyncio.wait_for(
                provider.analyze(request),
                timeout=min(LLM_INFERENCE_TIMEOUT, remaining),
            )
            latency_ms = int((time.monotonic() - t0) * 1000)

            attempts.append(
                {
                    "provider": provider.name,
                    "model": provider.model_id,
                    "status": "success",
                    "latency_ms": latency_ms,
                    "error": None,
                }
            )
            logger.info(
                "Ring 1 [fallback] COMPLETE via %s in %dms (after %d attempt%s)",
                provider.name,
                latency_ms,
                len(attempts),
                "s" if len(attempts) != 1 else "",
            )
            return response, attempts

        except asyncio.TimeoutError:
            latency_ms = int((time.monotonic() - t0) * 1000)
            error_msg = (
                f"{provider.name} inference timed out after {LLM_INFERENCE_TIMEOUT}s"
            )
            attempts.append(
                {
                    "provider": provider.name,
                    "model": provider.model_id,
                    "status": "timeout",
                    "latency_ms": latency_ms,
                    "error": error_msg,
                }
            )
            logger.warning(
                "Ring 1 [fallback] %s failed: %s. Trying next...",
                provider.name,
                error_msg,
            )

        except TimeoutError as exc:
            # Raised by providers internally (e.g. Gemini httpx timeout)
            latency_ms = int((time.monotonic() - t0) * 1000)
            error_msg = str(exc)
            attempts.append(
                {
                    "provider": provider.name,
                    "model": provider.model_id,
                    "status": "timeout",
                    "latency_ms": latency_ms,
                    "error": error_msg,
                }
            )
            logger.warning(
                "Ring 1 [fallback] %s failed: %s. Trying next...",
                provider.name,
                error_msg,
            )

        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            error_msg = f"{type(exc).__name__}: {str(exc)[:200]}"
            attempts.append(
                {
                    "provider": provider.name,
                    "model": provider.model_id,
                    "status": "error",
                    "latency_ms": latency_ms,
                    "error": error_msg,
                }
            )
            logger.warning(
                "Ring 1 [fallback] %s failed: %s. Trying next...",
                provider.name,
                error_msg,
            )

    # All providers failed
    total_ms = int((time.monotonic() - chain_start) * 1000)
    logger.error(
        "Ring 1 [fallback] ALL %d providers failed in %dms",
        len(attempts),
        total_ms,
    )
    return None, attempts
