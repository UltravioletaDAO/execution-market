"""
Verification Analytics — Prompt Performance Metrics

Queries verification_inferences table to produce metrics for
evaluating and improving prompts.

Part of PHOTINT Verification Overhaul (Phase 6).
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_prompt_performance(
    prompt_version: Optional[str] = None,
    category: Optional[str] = None,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Get performance metrics for prompt versions.

    Returns:
        Dict with agreement_rate, avg_confidence, avg_cost, avg_latency,
        false_positive_rate, false_negative_rate, total_inferences.
    """
    import supabase_client as db

    client = db.get_client()

    try:
        query = client.table("verification_inferences").select(
            "parsed_decision, parsed_confidence, estimated_cost_usd, "
            "latency_ms, prompt_version, task_category, agent_agreed, "
            "agent_decision, provider, model"
        )

        if prompt_version:
            query = query.eq("prompt_version", prompt_version)
        if category:
            query = query.eq("task_category", category)

        query = query.order("created_at", desc=True).limit(1000)
        result = query.execute()
        rows = result.data or []

        if not rows:
            return {"total_inferences": 0, "message": "No data available"}

        total = len(rows)
        with_feedback = [r for r in rows if r.get("agent_agreed") is not None]

        # Agreement rate
        agreed = sum(1 for r in with_feedback if r.get("agent_agreed") is True)
        agreement_rate = agreed / len(with_feedback) if with_feedback else None

        # False positives (AI approved, agent rejected)
        fp = sum(
            1
            for r in with_feedback
            if r.get("parsed_decision") == "approved"
            and r.get("agent_decision") in ("rejected",)
        )
        fp_rate = fp / len(with_feedback) if with_feedback else None

        # False negatives (AI rejected, agent approved)
        fn = sum(
            1
            for r in with_feedback
            if r.get("parsed_decision") == "rejected"
            and r.get("agent_decision") in ("accepted", "approved")
        )
        fn_rate = fn / len(with_feedback) if with_feedback else None

        # Averages
        confidences = [
            r["parsed_confidence"] for r in rows if r.get("parsed_confidence")
        ]
        costs = [r["estimated_cost_usd"] for r in rows if r.get("estimated_cost_usd")]
        latencies = [r["latency_ms"] for r in rows if r.get("latency_ms")]

        avg_confidence = sum(confidences) / len(confidences) if confidences else None
        avg_cost = sum(costs) / len(costs) if costs else None

        # Latency percentiles
        latency_stats = {}
        if latencies:
            sorted_lat = sorted(latencies)
            latency_stats = {
                "p50": sorted_lat[len(sorted_lat) // 2],
                "p95": sorted_lat[int(len(sorted_lat) * 0.95)],
                "p99": sorted_lat[int(len(sorted_lat) * 0.99)],
            }

        # Provider breakdown
        providers = {}
        for r in rows:
            key = f"{r.get('provider', '?')}/{r.get('model', '?')}"
            providers[key] = providers.get(key, 0) + 1

        # Version breakdown
        versions = {}
        for r in rows:
            v = r.get("prompt_version", "unknown")
            versions[v] = versions.get(v, 0) + 1

        return {
            "total_inferences": total,
            "with_feedback": len(with_feedback),
            "agreement_rate": round(agreement_rate, 3)
            if agreement_rate is not None
            else None,
            "false_positive_rate": round(fp_rate, 3) if fp_rate is not None else None,
            "false_negative_rate": round(fn_rate, 3) if fn_rate is not None else None,
            "avg_confidence": round(avg_confidence, 3)
            if avg_confidence is not None
            else None,
            "avg_cost_usd": round(avg_cost, 6) if avg_cost is not None else None,
            "total_cost_usd": round(sum(costs), 4) if costs else 0,
            "latency_ms": latency_stats,
            "providers": providers,
            "prompt_versions": versions,
        }

    except Exception as e:
        logger.warning("Failed to get prompt performance: %s", e)
        return {"total_inferences": 0, "error": str(e)}


async def get_disagreements(
    prompt_version: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Get cases where AI and agent disagreed — most valuable for prompt tuning.

    Returns list of inference records where agent_agreed is False.
    """
    import supabase_client as db

    client = db.get_client()

    try:
        query = (
            client.table("verification_inferences")
            .select("*")
            .eq("agent_agreed", False)
            .order("created_at", desc=True)
            .limit(limit)
        )

        if prompt_version:
            query = query.eq("prompt_version", prompt_version)

        result = query.execute()
        return result.data or []

    except Exception as e:
        logger.warning("Failed to get disagreements: %s", e)
        return []
