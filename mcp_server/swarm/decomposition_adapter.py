"""
DecompositionAdapter — Bridges TaskDecomposer into the DecisionBridge Pipeline
===============================================================================

The 10th signal: DECOMPOSITION — "Is this a compound task that should be split?"

The first 9 signals answer WHO, WHAT, WHEN, HOW MUCH, HOW WELL, and WILL IT
WORK. But they all assume the task is atomic. Many real tasks are compound:
"Build a landing page with SEO and deploy to AWS" requires frontend, SEO,
and DevOps skills — rarely found in one worker.

The DecompositionAdapter calls AutoJob's TaskDecomposer (exposed as
POST /api/swarm/decompose) and feeds decomposition intelligence into the
routing pipeline:

1. **Compound Detection**: Should this task be split before routing?
2. **Complexity Signal**: Simple/moderate/complex/expert affects candidate bar
3. **Skill Coverage**: Does a candidate cover all sub-task skills?
4. **Team Recommendation**: Solo, specialist, parallel, or hybrid?

Architecture:
    Task arrives → DecisionBridge evaluates
        → DecompositionAdapter.analyze(task) → AutoJob API
        → Returns DecompositionSnapshot (compound?, sub_tasks, skills)
        → For each candidate: skill coverage score (0-100)
        → SignalType.DECOMPOSITION normalizes → routing signal

Caching strategy:
    - Decompositions cached per task content hash for 1 hour
    - Stale cache used on API failure (up to 6h)
    - Default (non-compound, score 50) on total failure

Integration with DecisionBridge:
    The adapter serves two roles:
    1. Pre-routing: Informs DecisionBridge whether to decompose
    2. Per-candidate scoring: How well does a candidate cover sub-task skills?
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import timezone
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.decomposition_adapter")

UTC = timezone.utc


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


@dataclass
class SubTaskSnapshot:
    """A decomposed sub-task summary."""

    title: str
    task_type: str
    required_skills: list[str] = field(default_factory=list)
    estimated_hours: float = 1.0
    difficulty: float = 0.5
    bounty_share: float = 0.0


@dataclass
class DecompositionSnapshot:
    """Cached decomposition result for a task."""

    task_hash: str
    is_compound: bool = False
    sub_task_count: int = 1
    sub_tasks: list[SubTaskSnapshot] = field(default_factory=list)
    unique_skills: list[str] = field(default_factory=list)
    complexity: str = "simple"  # simple, moderate, complex, expert
    team_strategy: str = "solo"  # solo, specialist, parallel, hybrid
    estimated_hours: float = 0.0
    team_size: int = 1
    fetched_at: float = 0.0
    api_time_ms: float = 0.0
    from_cache: bool = False

    @property
    def age_seconds(self) -> float:
        return time.time() - self.fetched_at if self.fetched_at else float("inf")

    def skill_coverage_score(self, candidate_skills: list[str]) -> float:
        """Score how well a candidate covers this task's required skills.

        Returns 0-100 where:
        - 100 = candidate covers ALL unique skills across all sub-tasks
        - 0 = candidate covers NONE
        - Partial coverage weighted by sub-task difficulty
        """
        if not self.unique_skills:
            return 50.0  # No skill requirements → neutral

        candidate_set = {s.lower() for s in candidate_skills}
        required_set = {s.lower() for s in self.unique_skills}

        if not required_set:
            return 50.0

        # Basic coverage: what fraction of required skills does candidate have?
        covered = candidate_set & required_set
        basic_coverage = len(covered) / len(required_set)

        # Weighted coverage: harder sub-tasks matter more
        weighted_score = 0.0
        total_weight = 0.0
        for st in self.sub_tasks:
            weight = st.difficulty + 0.1  # Avoid zero weight
            total_weight += weight
            st_skills = {s.lower() for s in st.required_skills}
            if st_skills:
                st_covered = len(candidate_set & st_skills) / len(st_skills)
                weighted_score += st_covered * weight

        weighted_coverage = (
            weighted_score / total_weight if total_weight > 0 else basic_coverage
        )

        # Blend: 60% weighted + 40% basic
        blended = basic_coverage * 0.4 + weighted_coverage * 0.6

        return round(blended * 100, 2)

    @property
    def complexity_multiplier(self) -> float:
        """Complexity affects how much skill coverage matters.

        Simple tasks: coverage doesn't matter much (multiplier close to 1)
        Complex tasks: coverage is critical (multiplier amplifies gaps)
        """
        return {
            "simple": 0.7,
            "moderate": 0.85,
            "complex": 1.0,
            "expert": 1.15,
        }.get(self.complexity, 0.85)


# ──────────────────────────────────────────────────────────────
# Adapter
# ──────────────────────────────────────────────────────────────


# Cache TTL
FRESH_TTL = 3600  # 1 hour — decompositions rarely change for same task
STALE_TTL = 21600  # 6 hours — stale cache for API failures


def _task_hash(task: dict) -> str:
    """Deterministic hash of task content for caching."""
    key = json.dumps(
        {
            "title": task.get("title", ""),
            "description": task.get("description", ""),
            "category": task.get("category", ""),
        },
        sort_keys=True,
    )
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class DecompositionAdapter:
    """Bridges AutoJob's TaskDecomposer into the swarm routing pipeline.

    Provides two interfaces:
    1. analyze(task) → DecompositionSnapshot (compound detection)
    2. make_decomposition_scorer() → Callable for DecisionSynthesizer
    """

    def __init__(
        self,
        autojob_base_url: str = "http://localhost:8899",
        timeout_s: float = 5.0,
    ):
        self.base_url = autojob_base_url.rstrip("/")
        self.timeout_s = timeout_s

        # Cache: task_hash → DecompositionSnapshot
        self._cache: dict[str, DecompositionSnapshot] = {}

        # Stats
        self._total_requests = 0
        self._cache_hits = 0
        self._api_calls = 0
        self._api_errors = 0

    def analyze(self, task: dict) -> DecompositionSnapshot:
        """Analyze a task for compound decomposition.

        4-tier fallback:
        1. Fresh cache hit
        2. Live API call
        3. Stale cache
        4. Default (non-compound)
        """
        self._total_requests += 1
        th = _task_hash(task)

        # Tier 1: Fresh cache
        cached = self._cache.get(th)
        if cached and cached.age_seconds < FRESH_TTL:
            self._cache_hits += 1
            cached.from_cache = True
            return cached

        # Tier 2: Live API
        snapshot = self._fetch_from_api(task, th)
        if snapshot:
            self._cache[th] = snapshot
            return snapshot

        # Tier 3: Stale cache
        if cached and cached.age_seconds < STALE_TTL:
            self._cache_hits += 1
            cached.from_cache = True
            logger.info("Using stale decomposition cache for %s", th)
            return cached

        # Tier 4: Default
        return DecompositionSnapshot(
            task_hash=th,
            is_compound=False,
            fetched_at=time.time(),
        )

    def _fetch_from_api(
        self, task: dict, task_hash: str
    ) -> Optional[DecompositionSnapshot]:
        """Call AutoJob's /api/swarm/decompose endpoint."""
        self._api_calls += 1
        url = f"{self.base_url}/api/swarm/decompose"

        try:
            payload = json.dumps(task).encode("utf-8")
            req = Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            start = time.monotonic()
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            elapsed_ms = (time.monotonic() - start) * 1000

            if not data.get("success"):
                logger.warning("Decompose API returned failure: %s", data)
                self._api_errors += 1
                return None

            sub_tasks = []
            for st_data in data.get("sub_tasks", []):
                sub_tasks.append(
                    SubTaskSnapshot(
                        title=st_data.get("title", ""),
                        task_type=st_data.get("type", ""),
                        required_skills=st_data.get("required_skills", []),
                        estimated_hours=st_data.get("estimated_hours", 1.0),
                        difficulty=st_data.get("difficulty", 0.5),
                        bounty_share=st_data.get("bounty_share", 0.0),
                    )
                )

            # Determine team size from team_options
            team_size = 1
            for opt in data.get("team_options", []):
                ts = opt.get("team_size", len(opt.get("roles", [])))
                if ts > team_size:
                    team_size = ts

            return DecompositionSnapshot(
                task_hash=task_hash,
                is_compound=data.get("is_compound", False),
                sub_task_count=data.get("sub_task_count", 1),
                sub_tasks=sub_tasks,
                unique_skills=data.get("unique_skills", []),
                complexity=data.get("complexity", "simple"),
                team_strategy=data.get("team_strategy", "solo"),
                estimated_hours=data.get("estimated_hours", 0),
                team_size=team_size,
                fetched_at=time.time(),
                api_time_ms=elapsed_ms,
                from_cache=False,
            )

        except (URLError, HTTPError, TimeoutError, OSError) as e:
            self._api_errors += 1
            logger.warning("Decompose API error: %s", e)
            return None
        except Exception as e:
            self._api_errors += 1
            logger.error("Unexpected decompose error: %s", e)
            return None

    def stats(self) -> dict:
        """Return adapter statistics."""
        return {
            "total_requests": self._total_requests,
            "cache_hits": self._cache_hits,
            "api_calls": self._api_calls,
            "api_errors": self._api_errors,
            "cache_size": len(self._cache),
            "hit_rate": (
                round(self._cache_hits / self._total_requests, 3)
                if self._total_requests
                else 0
            ),
        }


# ──────────────────────────────────────────────────────────────
# Scorer Factory
# ──────────────────────────────────────────────────────────────


def make_decomposition_scorer(
    adapter: DecompositionAdapter,
) -> Callable:
    """Create a scorer function compatible with DecisionSynthesizer.

    The scorer evaluates: "How well does this candidate cover the skill
    requirements of all sub-tasks in a compound task?"

    Score formula:
        If task is compound:
            base = skill_coverage_score(candidate_skills)
            adjusted = base * complexity_multiplier
            Capped at 100
        If task is simple:
            50 (neutral — other signals should decide)

    This means for compound tasks, candidates with broad skill coverage
    score higher (they can handle more sub-tasks). For simple tasks,
    decomposition adds no routing signal.
    """

    def scorer(task: dict, candidate: dict) -> float:
        try:
            snapshot = adapter.analyze(task)

            if not snapshot.is_compound:
                return 50.0  # Neutral for simple tasks

            # Extract candidate skills
            skills = candidate.get("skills", [])
            if isinstance(skills, dict):
                skills = list(skills.keys())
            elif isinstance(skills, str):
                skills = [skills]

            # Also check skill_dna
            dna = candidate.get("skill_dna", {})
            if isinstance(dna, dict):
                skills = list(set(skills) | set(dna.keys()))

            coverage = snapshot.skill_coverage_score(skills)
            adjusted = coverage * snapshot.complexity_multiplier

            return min(100.0, max(0.0, adjusted))

        except Exception as e:
            logger.debug("Decomposition scorer error: %s", e)
            return 50.0  # Neutral on error

    return scorer
