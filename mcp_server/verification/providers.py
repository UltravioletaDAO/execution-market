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

import os
import json
import base64
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

import httpx

logger = logging.getLogger(__name__)


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
            "AI_VERIFICATION_MODEL", "claude-sonnet-4-20250514"
        )

    @property
    def name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

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

        message = client.messages.create(
            model=self.model_id,
            max_tokens=request.max_tokens,
            messages=[{"role": "user", "content": content}],
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
            "AI_VERIFICATION_MODEL", "anthropic.claude-sonnet-4-20250514-v1:0"
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

        response = client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
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
    """Google Gemini provider (cheapest vision model)."""

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
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_id)

        parts = []
        for img_data, mime_type in zip(request.images, request.image_types):
            parts.append({"mime_type": mime_type, "data": img_data})
        parts.append(request.prompt)

        response = model.generate_content(
            parts,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=request.max_tokens,
            ),
        )

        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "input_tokens": getattr(
                    response.usage_metadata, "prompt_token_count", 0
                ),
                "output_tokens": getattr(
                    response.usage_metadata, "candidates_token_count", 0
                ),
            }

        return VisionResponse(
            text=response.text,
            model=self.model_id,
            provider=self.name,
            usage=usage,
        )


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
TIER_MODELS = {
    "tier_1": [
        ("gemini", "gemini-2.5-flash"),
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-haiku-4-5-20251001"),
    ],
    "tier_2": [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("openai", "gpt-4o"),
        ("gemini", "gemini-2.5-pro"),
    ],
    "tier_3": [
        ("anthropic", "claude-opus-4-20250514"),
        ("bedrock", "anthropic.claude-opus-4-20250514-v1:0"),
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
        tier: "tier_1", "tier_2", or "tier_3"
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
