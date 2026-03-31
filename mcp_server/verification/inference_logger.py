"""
Verification Inference Logger — Full Audit Trail

Logs every AI inference during evidence verification:
prompt, response, model, tokens, latency, cost.

Part of PHOTINT Verification Overhaul (Phase 1).
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from web3 import Web3

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cost estimation lookup (per 1M tokens, March 2026 pricing)
# ---------------------------------------------------------------------------

COST_PER_1M_TOKENS: Dict[str, Dict[str, float]] = {
    # (provider, model) -> {"input": $/1M, "output": $/1M}
    # --- Tier 1: Lightweight / Flash models ---
    "gemini:gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini:gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "openai:gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai:gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    # --- Tier 2: Mid-range models ---
    "openai:gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "anthropic:claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gemini:gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    # --- Tier 3: Frontier models ---
    "openai:gpt-4.1": {"input": 2.00, "output": 8.00},
    "openai:gpt-4o": {"input": 2.50, "output": 10.00},
    "anthropic:claude-sonnet-4-6-20250627": {"input": 3.00, "output": 15.00},
    "anthropic:claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "anthropic:claude-opus-4-6-20250627": {"input": 15.00, "output": 75.00},
    "anthropic:claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    # --- Bedrock variants ---
    "bedrock:anthropic.claude-sonnet-4-6-v1:0": {"input": 3.00, "output": 15.00},
    "bedrock:anthropic.claude-opus-4-6-v1:0": {"input": 15.00, "output": 75.00},
}

# Fallback cost for unknown models
DEFAULT_COST = {"input": 3.00, "output": 15.00}


def estimate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Estimate USD cost for an inference call.

    Returns cost in USD (e.g., 0.000150 for a cheap Gemini Flash call).
    """
    key = f"{provider}:{model}"
    rates = COST_PER_1M_TOKENS.get(key, DEFAULT_COST)
    cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Inference record
# ---------------------------------------------------------------------------


@dataclass
class InferenceRecord:
    """Complete record of a single AI inference for audit trail."""

    submission_id: str
    task_id: str
    check_name: str  # 'ai_semantic', 'tampering', etc.
    tier: str  # 'tier_0', 'tier_1', 'tier_2', 'tier_3', 'tier_4'
    provider: str
    model: str
    prompt_version: str  # 'photint-v1.0-physical_presence'
    prompt_text: str
    response_text: str
    parsed_decision: Optional[str] = None
    parsed_confidence: Optional[float] = None
    parsed_issues: Optional[List[str]] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    task_category: Optional[str] = None
    evidence_types: Optional[List[str]] = None
    photo_count: Optional[int] = None
    commitment_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def compute_prompt_hash(prompt_text: str) -> str:
    """SHA-256 hash of prompt text for dedup/tracking."""
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


def compute_commitment_hash(task_id: str, response_text: str) -> str:
    """keccak256 commitment hash for on-chain auditability."""
    raw = f"task:{task_id}|{response_text}"
    raw_hex = Web3.keccak(text=raw).hex()
    return raw_hex if raw_hex.startswith("0x") else f"0x{raw_hex}"


# ---------------------------------------------------------------------------
# Inference Logger
# ---------------------------------------------------------------------------


class InferenceLogger:
    """
    Logs verification inferences to the verification_inferences table.

    Fire-and-forget: logging failures never block verification.
    """

    def __init__(self):
        self._db = None

    def _get_db(self):
        """Lazy import to avoid circular dependencies."""
        if self._db is None:
            import supabase_client as db

            self._db = db
        return self._db

    async def log(self, record: InferenceRecord) -> Optional[str]:
        """
        Log an inference record to the database.

        Returns the inference ID if successful, None if failed.
        Never raises — all errors are logged and swallowed.
        """
        try:
            db = self._get_db()

            # Compute cost if tokens available
            if (
                record.estimated_cost_usd is None
                and record.input_tokens is not None
                and record.output_tokens is not None
            ):
                record.estimated_cost_usd = estimate_cost(
                    record.provider,
                    record.model,
                    record.input_tokens,
                    record.output_tokens,
                )

            # Compute commitment hash if not set
            if record.commitment_hash is None:
                record.commitment_hash = compute_commitment_hash(
                    record.task_id, record.response_text
                )

            prompt_hash = compute_prompt_hash(record.prompt_text)

            inference_id = await db.log_verification_inference(
                submission_id=record.submission_id,
                task_id=record.task_id,
                check_name=record.check_name,
                tier=record.tier,
                provider=record.provider,
                model=record.model,
                prompt_version=record.prompt_version,
                prompt_hash=prompt_hash,
                prompt_text=record.prompt_text,
                response_text=record.response_text,
                parsed_decision=record.parsed_decision,
                parsed_confidence=record.parsed_confidence,
                parsed_issues=record.parsed_issues,
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                latency_ms=record.latency_ms,
                estimated_cost_usd=record.estimated_cost_usd,
                task_category=record.task_category,
                evidence_types=record.evidence_types,
                photo_count=record.photo_count,
                commitment_hash=record.commitment_hash,
                metadata=record.metadata,
            )

            logger.info(
                "Inference logged: %s/%s check=%s decision=%s cost=$%.6f latency=%dms",
                record.provider,
                record.model,
                record.check_name,
                record.parsed_decision,
                record.estimated_cost_usd or 0,
                record.latency_ms or 0,
            )
            return inference_id

        except Exception as e:
            logger.warning(
                "Failed to log inference for submission %s: %s",
                record.submission_id,
                e,
            )
            return None


class InferenceTimer:
    """Context manager for timing inference calls."""

    def __init__(self):
        self.start_time: float = 0
        self.latency_ms: int = 0

    def __enter__(self):
        self.start_time = time.monotonic()
        return self

    def __exit__(self, *args):
        elapsed = time.monotonic() - self.start_time
        self.latency_ms = int(elapsed * 1000)


# Module-level singleton
_logger_instance: Optional[InferenceLogger] = None


def get_inference_logger() -> InferenceLogger:
    """Get the module-level InferenceLogger singleton."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = InferenceLogger()
    return _logger_instance
