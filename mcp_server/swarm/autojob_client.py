"""
AutoJob Enrichment Client — Bridges EM SwarmOrchestrator with AutoJob's intelligence.

The SwarmOrchestrator handles lifecycle, claims, and routing strategy.
AutoJob handles evidence-based scoring, Skill DNA, and worker profiling.
This client connects the two.

Usage:
    from .autojob_client import AutoJobClient, AutoJobEnrichment

    client = AutoJobClient(base_url="http://localhost:8765")

    # Enrich agents before routing
    enrichments = client.enrich_agents(
        task={"id": "t1", "category": "photo", "title": "Verify store"},
        wallets=["0xABC...", "0xDEF..."],
    )

    # Use enrichments in orchestrator scoring
    for wallet, enrichment in enrichments.items():
        print(f"{wallet}: score={enrichment.match_score}, quality={enrichment.predicted_quality}")

    # Get routing recommendation (if you want AutoJob to pick the best)
    route = client.route_task(
        task={"id": "t1", "category": "photo", "title": "Verify store", "bounty_usd": 5.0},
        limit=5,
    )
"""

import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.autojob_client")


@dataclass
class AutoJobEnrichment:
    """Enrichment data from AutoJob for a single agent/wallet."""

    wallet: str
    match_score: float = 0.0  # 0-1, overall match quality
    predicted_quality: float = 0.0  # 0-1, expected output quality
    predicted_success: float = 0.0  # 0-1, probability of successful completion
    tier: str = "Unranked"
    skill_match: float = 0.0  # 0-100
    reputation_score: float = 0.0  # 0-100
    reliability_score: float = 0.0  # 0-100
    recency_score: float = 0.0  # 0-100
    on_chain_registered: bool = False
    category_experience: float = 0.0  # 0-1
    match_explanation: str = ""

    def to_composite_boost(self) -> dict:
        """Convert to a score boost dict for SwarmOrchestrator.

        Returns weights that the orchestrator can blend into its
        ReputationBridge scores for more informed routing.
        """
        return {
            "skill_boost": self.skill_match * 0.5,  # Half weight from AutoJob
            "reputation_boost": self.reputation_score * 0.3,
            "reliability_boost": self.reliability_score * 0.2,
            "total_boost": self.match_score * 15,  # Up to 15 bonus points
            "confidence": min(self.match_score * 1.5, 1.0),  # How much to trust this
        }


@dataclass
class AutoJobRouteResult:
    """Routing recommendation from AutoJob."""

    task_id: str
    task_category: str
    total_candidates: int
    qualified_candidates: int
    match_time_ms: float
    best_match: Optional[dict] = None
    rankings: list[dict] = field(default_factory=list)


@dataclass
class AutoJobHealth:
    """Health status from AutoJob's flywheel."""

    overall: str = "unknown"  # optimal, healthy, degraded
    workers_total: int = 0
    erc8004_coverage_pct: float = 0.0
    matching_ready: bool = False
    checks: dict = field(default_factory=dict)


class AutoJobClient:
    """
    HTTP client for AutoJob's swarm routing API.

    Designed for zero-dependency operation (stdlib only, no requests/httpx).
    Falls back gracefully when AutoJob is unavailable.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8765",
        timeout_seconds: float = 5.0,
        retries: int = 1,
        fallback_on_error: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.retries = retries
        self.fallback_on_error = fallback_on_error
        self._last_health_check: Optional[datetime] = None
        self._is_available: Optional[bool] = None

    def _post(self, path: str, data: dict) -> dict:
        """Make a POST request to AutoJob API."""
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                with urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (URLError, HTTPError, TimeoutError) as e:
                last_error = e
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue

        if self.fallback_on_error:
            logger.warning(f"AutoJob API unavailable ({path}): {last_error}")
            return {"success": False, "error": str(last_error)}
        raise last_error

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Make a GET request to AutoJob API."""
        url = f"{self.base_url}{path}"
        if params:
            from urllib.parse import urlencode

            url += f"?{urlencode(params)}"

        req = Request(url, method="GET")

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                with urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (URLError, HTTPError, TimeoutError) as e:
                last_error = e
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue

        if self.fallback_on_error:
            logger.warning(f"AutoJob API unavailable ({path}): {last_error}")
            return {"success": False, "error": str(last_error)}
        raise last_error

    # ---- Core API Methods ----

    def enrich_agents(
        self,
        task: dict,
        wallets: list[str],
    ) -> dict[str, AutoJobEnrichment]:
        """Enrich agent wallets with AutoJob's evidence-based intelligence.

        This is the primary integration point. The EM SwarmOrchestrator
        calls this before routing to get enriched scoring data.

        Args:
            task: EM task dict {id, category, title, bounty_usd, ...}
            wallets: List of agent wallet addresses to evaluate

        Returns:
            Dict mapping wallet → AutoJobEnrichment
        """
        resp = self._post(
            "/api/swarm/enrich",
            {
                "task": task,
                "wallets": wallets,
            },
        )

        enrichments = {}
        if resp.get("success") and "enrichments" in resp:
            for wallet, data in resp["enrichments"].items():
                enrichments[wallet] = AutoJobEnrichment(
                    wallet=data.get("wallet", wallet),
                    match_score=data.get("match_score", 0.0),
                    predicted_quality=data.get("predicted_quality", 0.0),
                    predicted_success=data.get("predicted_success", 0.0),
                    tier=data.get("tier", "Unranked"),
                    skill_match=data.get("skill_match", 0.0),
                    reputation_score=data.get("reputation_score", 0.0),
                    reliability_score=data.get("reliability_score", 0.0),
                    recency_score=data.get("recency_score", 0.0),
                    on_chain_registered=data.get("on_chain_registered", False),
                    category_experience=data.get("category_experience", 0.0),
                    match_explanation=data.get("match_explanation", ""),
                )
        else:
            # Return empty enrichments for all wallets (graceful fallback)
            for wallet in wallets:
                enrichments[wallet] = AutoJobEnrichment(wallet=wallet)

        return enrichments

    def route_task(
        self,
        task: dict,
        limit: int = 5,
        min_score: float = 20.0,
    ) -> AutoJobRouteResult:
        """Get routing recommendation from AutoJob.

        If you want AutoJob to rank all workers for a task (not just
        enrich known wallets), use this instead of enrich_agents.

        Args:
            task: EM task dict
            limit: Max ranked results
            min_score: Minimum score threshold

        Returns:
            AutoJobRouteResult with ranked workers
        """
        resp = self._post(
            "/api/swarm/route",
            {
                "task": task,
                "limit": limit,
                "min_score": min_score,
            },
        )

        if not resp.get("success"):
            return AutoJobRouteResult(
                task_id=task.get("id", "unknown"),
                task_category=task.get("category", "unknown"),
                total_candidates=0,
                qualified_candidates=0,
                match_time_ms=0,
            )

        return AutoJobRouteResult(
            task_id=resp.get("task_id", "unknown"),
            task_category=resp.get("task_category", "unknown"),
            total_candidates=resp.get("total_candidates", 0),
            qualified_candidates=resp.get("qualified_candidates", 0),
            match_time_ms=resp.get("match_time_ms", 0),
            best_match=resp.get("best_match"),
            rankings=resp.get("rankings", []),
        )

    def get_health(self) -> AutoJobHealth:
        """Check AutoJob's flywheel health.

        Good for monitoring dashboards and determining if enrichment
        data is trustworthy.
        """
        resp = self._get("/api/swarm/health")

        if not resp.get("success"):
            return AutoJobHealth()

        health = resp.get("health", {})
        status = resp.get("status", {})

        return AutoJobHealth(
            overall=health.get("overall", "unknown"),
            workers_total=status.get("workers", {}).get("total", 0),
            erc8004_coverage_pct=status.get("erc8004", {}).get("coverage_pct", 0),
            matching_ready=status.get("matching", {}).get("ready", False),
            checks=health.get("checks", {}),
        )

    def is_available(self, force_check: bool = False) -> bool:
        """Check if AutoJob API is reachable.

        Caches result for 60 seconds to avoid hammering.
        """
        now = datetime.now(timezone.utc)
        if (
            not force_check
            and self._is_available is not None
            and self._last_health_check
            and (now - self._last_health_check).total_seconds() < 60
        ):
            return self._is_available

        try:
            resp = self._get("/api/swarm/health")
            self._is_available = resp.get("success", False)
        except Exception:
            self._is_available = False

        self._last_health_check = now
        return self._is_available

    def get_worker_profile(self, wallet: str) -> dict | None:
        """Get a worker's full profile from AutoJob.

        Returns Skill DNA, evidence sources, ratings, etc.
        """
        resp = self._get(f"/api/workers/{wallet}")
        if resp.get("success"):
            return resp.get("worker")
        return None


class EnrichedOrchestrator:
    """
    Drop-in wrapper that enriches SwarmOrchestrator scoring with AutoJob data.

    Usage:
        from .orchestrator import SwarmOrchestrator
        from .autojob_client import EnrichedOrchestrator, AutoJobClient

        client = AutoJobClient(base_url="http://localhost:8765")
        orchestrator = SwarmOrchestrator(bridge, lifecycle)
        enriched = EnrichedOrchestrator(orchestrator, client)

        # Route with AutoJob enrichment
        result = enriched.route_task(task)
    """

    def __init__(
        self,
        orchestrator,  # SwarmOrchestrator
        autojob_client: AutoJobClient,
        enrichment_weight: float = 0.3,  # How much to trust AutoJob vs native scoring
    ):
        self.orchestrator = orchestrator
        self.autojob = autojob_client
        self.enrichment_weight = enrichment_weight
        self._enrichment_cache: OrderedDict[str, dict[str, AutoJobEnrichment]] = (
            OrderedDict()
        )
        self._cache_maxsize = 500

    def route_task(self, task, strategy=None):
        """Route with optional AutoJob enrichment.

        If AutoJob is available, enriches the scoring before routing.
        Falls back to native orchestrator scoring if unavailable.
        """
        from .orchestrator import TaskRequest

        if not isinstance(task, TaskRequest):
            raise TypeError("Expected TaskRequest")

        # Try to enrich from AutoJob
        if self.autojob.is_available():
            self._enrich_before_routing(task)

        # Route normally (scoring is now augmented)
        return self.orchestrator.route_task(task, strategy=strategy)

    def _enrich_before_routing(self, task):
        """Pre-flight enrichment: update internal reputation with AutoJob data."""

        # Get all registered agent wallets
        available = self.orchestrator.lifecycle.get_available_agents()
        wallets = [a.wallet_address for a in available if a.wallet_address]

        if not wallets:
            return

        # Build EM-format task for AutoJob
        em_task = {
            "id": task.task_id,
            "category": task.categories[0] if task.categories else "general",
            "title": task.title,
            "bounty_usd": task.bounty_usd,
        }

        cache_key = f"{task.task_id}:{','.join(sorted(wallets))}"
        if cache_key in self._enrichment_cache:
            # Move to end (most recently used)
            self._enrichment_cache.move_to_end(cache_key)
            enrichments = self._enrichment_cache[cache_key]
        else:
            enrichments = self.autojob.enrich_agents(em_task, wallets)
            self._enrichment_cache[cache_key] = enrichments
            # Evict oldest entries if cache exceeds maxsize
            while len(self._enrichment_cache) > self._cache_maxsize:
                self._enrichment_cache.popitem(last=False)

        # Boost internal reputation scores with AutoJob intelligence
        for agent in available:
            enrichment = enrichments.get(agent.wallet_address)
            if enrichment and enrichment.match_score > 0:
                agent_id = agent.agent_id
                if agent_id in self.orchestrator._internal:
                    internal = self.orchestrator._internal[agent_id]
                    enrichment.to_composite_boost()

                    # Blend category scores from AutoJob
                    for cat in task.categories or []:
                        current = internal.category_scores.get(cat, 0)
                        autojob_score = enrichment.category_experience * 100
                        blended = (
                            current * (1 - self.enrichment_weight)
                            + autojob_score * self.enrichment_weight
                        )
                        internal.category_scores[cat] = blended

                    logger.info(
                        f"Enriched agent {agent_id} ({agent.wallet_address[:10]}...): "
                        f"AutoJob score={enrichment.match_score:.2f}, "
                        f"quality={enrichment.predicted_quality:.2f}, "
                        f"tier={enrichment.tier}"
                    )
