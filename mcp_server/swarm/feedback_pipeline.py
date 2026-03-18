"""
FeedbackPipeline — Closes the feedback loop from task completions to worker intelligence.

This is the ENGINE that makes the swarm get smarter over time:

    Task Completed → Evidence Parsed → Skill DNA Updated → ReputationBridge Updated
                                                         → AutoJob Notified
                                                         → Worker Rankings Recalculated

Without this pipeline, the swarm routes tasks but never LEARNS from outcomes.
With it, every completed task makes future routing better.

Data flow:
    1. Poll EM API for completed tasks (via EventListener watermark)
    2. Fetch evidence submissions for each completed task
    3. Parse evidence → QualityAssessment + SkillSignals
    4. Update worker's SkillDNA in WorkerRegistry
    5. Feed signals back to ReputationBridge (InternalReputation update)
    6. Persist state for crash recovery
    7. Emit analytics events for the dashboard

Integrations:
    - EvidenceParser: Extracts skill signals from evidence
    - WorkerRegistry: Stores and updates Skill DNA profiles
    - ReputationBridge: Receives score updates for routing decisions
    - LifecycleManager: Cooldown/state transitions on completion
    - Analytics: Event emission for monitoring
    - StatePersistence: Durable state across restarts

Usage:
    pipeline = FeedbackPipeline.create(
        em_api_url="https://api.execution.market",
        state_dir="./data/feedback",
    )

    # Process all new completions since last run
    results = pipeline.process_new_completions()

    # Or process a single task completion
    result = pipeline.process_completion(task_id="abc-123")

    # Get pipeline health/stats
    stats = pipeline.get_stats()
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .evidence_parser import (
    EvidenceParser,
    EvidenceQuality,
    QualityAssessment,
    SkillDNA,
    SkillDimension,
    WorkerRegistry,
)
from .reputation_bridge import (
    ReputationBridge,
    InternalReputation,
    OnChainReputation,
    CompositeScore,
)
from .lifecycle_manager import (
    LifecycleManager,
    AgentState,
)
from .event_listener import map_categories

logger = logging.getLogger("em.swarm.feedback_pipeline")


# ─── Feedback Result Types ────────────────────────────────────────────────────


@dataclass
class CompletionFeedback:
    """Result of processing a single task completion."""

    task_id: str
    worker_id: str
    quality: EvidenceQuality
    quality_score: float
    evidence_count: int
    evidence_types: list[str]
    skill_signals_count: int
    top_skills_updated: list[tuple[str, float]]
    worker_task_count: int
    worker_avg_quality: float
    reputation_delta: float  # How much reputation changed
    processing_time_ms: float
    flags: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "quality": self.quality.value,
            "quality_score": round(self.quality_score, 3),
            "evidence_count": self.evidence_count,
            "evidence_types": self.evidence_types,
            "skill_signals_count": self.skill_signals_count,
            "top_skills": [
                {"skill": s, "score": round(v, 3)} for s, v in self.top_skills_updated
            ],
            "worker_tasks": self.worker_task_count,
            "worker_avg_quality": round(self.worker_avg_quality, 3),
            "reputation_delta": round(self.reputation_delta, 3),
            "processing_time_ms": round(self.processing_time_ms, 1),
            "flags": self.flags,
            "error": self.error,
        }


@dataclass
class PipelineRunResult:
    """Result of a feedback pipeline run (processing multiple completions)."""

    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    tasks_processed: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tasks_skipped: int = 0
    total_evidence_parsed: int = 0
    total_skill_signals: int = 0
    avg_quality_score: float = 0.0
    quality_distribution: dict[str, int] = field(default_factory=dict)
    workers_updated: set[str] = field(default_factory=set)
    errors: list[dict] = field(default_factory=list)
    duration_ms: float = 0.0
    feedbacks: list[CompletionFeedback] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tasks_processed": self.tasks_processed,
            "tasks_succeeded": self.tasks_succeeded,
            "tasks_failed": self.tasks_failed,
            "tasks_skipped": self.tasks_skipped,
            "total_evidence_parsed": self.total_evidence_parsed,
            "total_skill_signals": self.total_skill_signals,
            "avg_quality_score": round(self.avg_quality_score, 3),
            "quality_distribution": self.quality_distribution,
            "workers_updated": len(self.workers_updated),
            "errors": self.errors[:10],  # Cap error reporting
            "duration_ms": round(self.duration_ms, 1),
        }

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Feedback Pipeline Run {self.run_id}",
            f"  Tasks: {self.tasks_succeeded}/{self.tasks_processed} succeeded"
            f" ({self.tasks_skipped} skipped, {self.tasks_failed} failed)",
            f"  Evidence: {self.total_evidence_parsed} items parsed → {self.total_skill_signals} skill signals",
            f"  Workers updated: {len(self.workers_updated)}",
            f"  Avg quality: {self.avg_quality_score:.2f}",
            f"  Quality distribution: {self.quality_distribution}",
            f"  Duration: {self.duration_ms:.0f}ms",
        ]
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        return "\n".join(lines)


# ─── Watermark State ──────────────────────────────────────────────────────────


@dataclass
class PipelineState:
    """Persisted pipeline state for crash recovery."""

    last_processed_at: Optional[str] = None  # ISO timestamp watermark
    processed_task_ids: list[str] = field(default_factory=list)  # Recent IDs for dedup
    total_runs: int = 0
    total_tasks_processed: int = 0
    total_evidence_parsed: int = 0
    last_run_at: Optional[str] = None
    worker_registry_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "last_processed_at": self.last_processed_at,
            "processed_task_ids": self.processed_task_ids[-500:],  # Keep last 500
            "total_runs": self.total_runs,
            "total_tasks_processed": self.total_tasks_processed,
            "total_evidence_parsed": self.total_evidence_parsed,
            "last_run_at": self.last_run_at,
            "worker_registry_path": self.worker_registry_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineState":
        state = cls()
        state.last_processed_at = data.get("last_processed_at")
        state.processed_task_ids = data.get("processed_task_ids", [])
        state.total_runs = data.get("total_runs", 0)
        state.total_tasks_processed = data.get("total_tasks_processed", 0)
        state.total_evidence_parsed = data.get("total_evidence_parsed", 0)
        state.last_run_at = data.get("last_run_at")
        state.worker_registry_path = data.get("worker_registry_path")
        return state


# ─── Feedback Pipeline ────────────────────────────────────────────────────────


class FeedbackPipeline:
    """
    Closes the feedback loop from task completions to worker intelligence.

    The pipeline:
    1. Fetches completed tasks from the EM API
    2. Parses evidence for quality + skill signals
    3. Updates worker Skill DNA profiles
    4. Feeds reputation data back for better routing
    5. Persists state for reliability

    Designed for periodic invocation (cron/heartbeat) or event-driven use.
    """

    def __init__(
        self,
        em_api_url: str = "https://api.execution.market",
        api_key: Optional[str] = None,
        state_dir: str = "./data/feedback",
        worker_registry: Optional[WorkerRegistry] = None,
        reputation_bridge: Optional[ReputationBridge] = None,
        lifecycle_manager: Optional[LifecycleManager] = None,
        on_feedback: Optional[Callable[[CompletionFeedback], None]] = None,
        request_timeout: float = 10.0,
        max_tasks_per_run: int = 100,
    ):
        self.em_api_url = em_api_url.rstrip("/")
        self.api_key = api_key
        self.state_dir = Path(state_dir)
        self.evidence_parser = EvidenceParser()
        self.worker_registry = worker_registry or WorkerRegistry()
        self.reputation_bridge = reputation_bridge or ReputationBridge()
        self.lifecycle_manager = lifecycle_manager
        self.on_feedback = on_feedback
        self.request_timeout = request_timeout
        self.max_tasks_per_run = max_tasks_per_run

        # Internal state
        self._state = PipelineState()
        self._internal_reputations: dict[str, InternalReputation] = {}

        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load persisted state
        self._load_state()

    @classmethod
    def create(
        cls,
        em_api_url: str = "https://api.execution.market",
        api_key: Optional[str] = None,
        state_dir: str = "./data/feedback",
        **kwargs,
    ) -> "FeedbackPipeline":
        """Factory method with sensible defaults."""
        pipeline = cls(
            em_api_url=em_api_url,
            api_key=api_key,
            state_dir=state_dir,
            **kwargs,
        )
        return pipeline

    # ─── Core Pipeline Methods ─────────────────────────────────────────────

    def process_new_completions(self) -> PipelineRunResult:
        """
        Main entry point: fetch and process all new completions since last run.

        This is the method you call from cron/heartbeat/daemon.
        """
        run_start = time.monotonic()
        now = datetime.now(timezone.utc)
        run_id = now.strftime("%Y%m%d_%H%M%S")

        result = PipelineRunResult(
            run_id=run_id,
            started_at=now,
        )

        try:
            # Fetch completed tasks from EM API
            completed_tasks = self._fetch_completed_tasks()

            if not completed_tasks:
                logger.info("No new completed tasks to process")
                result.completed_at = datetime.now(timezone.utc)
                result.duration_ms = (time.monotonic() - run_start) * 1000
                return result

            # Filter already-processed tasks
            new_tasks = [
                t for t in completed_tasks
                if t.get("id") not in self._state.processed_task_ids
            ]

            if not new_tasks:
                logger.info("All completed tasks already processed")
                result.tasks_skipped = len(completed_tasks)
                result.completed_at = datetime.now(timezone.utc)
                result.duration_ms = (time.monotonic() - run_start) * 1000
                return result

            # Cap per-run processing
            tasks_to_process = new_tasks[: self.max_tasks_per_run]
            result.tasks_skipped = len(new_tasks) - len(tasks_to_process)

            logger.info(
                f"Processing {len(tasks_to_process)} new completions "
                f"({result.tasks_skipped} deferred)"
            )

            # Process each completion
            quality_scores = []
            for task in tasks_to_process:
                feedback = self.process_completion_from_task(task)
                result.feedbacks.append(feedback)
                result.tasks_processed += 1

                if feedback.error:
                    result.tasks_failed += 1
                    result.errors.append({
                        "task_id": feedback.task_id,
                        "error": feedback.error,
                    })
                else:
                    result.tasks_succeeded += 1
                    result.total_evidence_parsed += feedback.evidence_count
                    result.total_skill_signals += feedback.skill_signals_count
                    result.workers_updated.add(feedback.worker_id)
                    quality_scores.append(feedback.quality_score)
                    result.quality_distribution[feedback.quality.value] = (
                        result.quality_distribution.get(feedback.quality.value, 0) + 1
                    )

                # Mark as processed
                self._state.processed_task_ids.append(task.get("id", ""))

                # Invoke callback if registered
                if self.on_feedback and not feedback.error:
                    try:
                        self.on_feedback(feedback)
                    except Exception as e:
                        logger.warning(f"Feedback callback error: {e}")

            # Compute averages
            if quality_scores:
                result.avg_quality_score = sum(quality_scores) / len(quality_scores)

            # Update watermark
            self._state.last_processed_at = now.isoformat()
            self._state.total_runs += 1
            self._state.total_tasks_processed += result.tasks_processed
            self._state.total_evidence_parsed += result.total_evidence_parsed
            self._state.last_run_at = now.isoformat()

            # Persist state + worker registry
            self._save_state()
            self._save_worker_registry()

        except Exception as e:
            logger.error(f"Pipeline run failed: {e}", exc_info=True)
            result.errors.append({"error": str(e), "type": "pipeline_error"})

        result.completed_at = datetime.now(timezone.utc)
        result.duration_ms = (time.monotonic() - run_start) * 1000

        logger.info(result.summary())
        return result

    def process_completion(self, task_id: str) -> CompletionFeedback:
        """
        Process a single task completion by ID.

        Fetches the task + evidence from EM API, then processes through
        the evidence parser → Skill DNA → reputation pipeline.
        """
        task = self._fetch_task(task_id)
        if not task:
            return CompletionFeedback(
                task_id=task_id,
                worker_id="unknown",
                quality=EvidenceQuality.POOR,
                quality_score=0.0,
                evidence_count=0,
                evidence_types=[],
                skill_signals_count=0,
                top_skills_updated=[],
                worker_task_count=0,
                worker_avg_quality=0.0,
                reputation_delta=0.0,
                processing_time_ms=0.0,
                error=f"Task {task_id} not found",
            )
        return self.process_completion_from_task(task)

    def process_completion_from_task(self, task: dict) -> CompletionFeedback:
        """
        Process a task completion from task data dict.

        Core processing logic:
        1. Extract worker identity
        2. Fetch and parse evidence
        3. Update Skill DNA
        4. Update internal reputation
        5. Return feedback result
        """
        start = time.monotonic()
        task_id = task.get("id", "unknown")

        # Extract worker identity
        worker_id = self._extract_worker_id(task)
        if not worker_id:
            return CompletionFeedback(
                task_id=task_id,
                worker_id="unknown",
                quality=EvidenceQuality.POOR,
                quality_score=0.0,
                evidence_count=0,
                evidence_types=[],
                skill_signals_count=0,
                top_skills_updated=[],
                worker_task_count=0,
                worker_avg_quality=0.0,
                reputation_delta=0.0,
                processing_time_ms=(time.monotonic() - start) * 1000,
                error="No worker identity found in task data",
            )

        try:
            # Extract evidence from task data or fetch separately
            evidence = self._extract_evidence(task)

            # Map task categories
            em_category = task.get("category", task.get("task_type", "general"))
            categories = map_categories(em_category)

            # Parse evidence → quality assessment + skill signals
            assessment = self.evidence_parser.parse_evidence(evidence, task)

            # Update worker's Skill DNA
            dna = self.worker_registry.get_or_create(worker_id)
            old_quality = dna.avg_quality

            self.evidence_parser.update_skill_dna(
                dna, assessment, task_categories=categories
            )

            # Update internal reputation scores
            reputation_delta = self._update_internal_reputation(
                worker_id, task, assessment, dna
            )

            # Build feedback result
            processing_time = (time.monotonic() - start) * 1000

            feedback = CompletionFeedback(
                task_id=task_id,
                worker_id=worker_id,
                quality=assessment.quality,
                quality_score=assessment.score,
                evidence_count=assessment.evidence_count,
                evidence_types=assessment.evidence_types,
                skill_signals_count=len(assessment.signals),
                top_skills_updated=dna.get_top_skills(5),
                worker_task_count=dna.task_count,
                worker_avg_quality=dna.avg_quality,
                reputation_delta=reputation_delta,
                processing_time_ms=processing_time,
                flags=assessment.flags,
            )

            logger.info(
                f"Processed completion {task_id}: "
                f"worker={worker_id}, quality={assessment.quality.value}, "
                f"signals={len(assessment.signals)}, "
                f"rep_delta={reputation_delta:+.3f}"
            )

            return feedback

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            return CompletionFeedback(
                task_id=task_id,
                worker_id=worker_id,
                quality=EvidenceQuality.POOR,
                quality_score=0.0,
                evidence_count=0,
                evidence_types=[],
                skill_signals_count=0,
                top_skills_updated=[],
                worker_task_count=0,
                worker_avg_quality=0.0,
                reputation_delta=0.0,
                processing_time_ms=(time.monotonic() - start) * 1000,
                error=str(e),
            )

    # ─── Reputation Update Logic ───────────────────────────────────────────

    def _update_internal_reputation(
        self,
        worker_id: str,
        task: dict,
        assessment: QualityAssessment,
        dna: SkillDNA,
    ) -> float:
        """
        Update the internal reputation based on completion feedback.

        Returns the reputation delta (change in bayesian_score).
        """
        # Get or create internal reputation
        if worker_id not in self._internal_reputations:
            self._internal_reputations[worker_id] = InternalReputation(
                agent_id=hash(worker_id) % 100000,  # Deterministic ID
            )

        rep = self._internal_reputations[worker_id]
        old_score = rep.bayesian_score

        # Update task counts
        rep.total_tasks += 1
        if assessment.quality != EvidenceQuality.SUSPICIOUS:
            rep.successful_tasks += 1
            rep.consecutive_failures = 0
        else:
            rep.consecutive_failures += 1

        # Update average rating (map quality score to 1-5 scale)
        quality_rating = 1.0 + assessment.score * 4.0  # 0.0→1.0, 1.0→5.0
        if rep.avg_rating == 0:
            rep.avg_rating = quality_rating
        else:
            rep.avg_rating = (
                rep.avg_rating * (rep.total_tasks - 1) + quality_rating
            ) / rep.total_tasks

        # Update category-specific scores (0.0 - 1.0 scale)
        em_category = task.get("category", "general")
        categories = map_categories(em_category)
        for cat in categories:
            current = rep.category_scores.get(cat, 0.5)
            # Blend: move toward assessment score (0-1 range)
            rep.category_scores[cat] = current * 0.8 + assessment.score * 0.2

        # Bayesian score update
        # Uses a modified Wilson score interval approach:
        # - More tasks = tighter confidence interval
        # - Quality of evidence directly affects score
        # - Consecutive failures cause faster degradation
        n = rep.total_tasks
        p = rep.success_rate
        z = 1.96  # 95% confidence

        if n > 0:
            # Wilson lower bound (conservative estimate)
            wilson_center = (p + z * z / (2 * n)) / (1 + z * z / n)
            wilson_width = (
                z
                * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
                / (1 + z * z / n)
            )
            wilson_lower = max(0, wilson_center - wilson_width)

            # Blend Wilson with quality-weighted score
            quality_factor = dna.avg_quality * 0.8 + 0.2  # Floor at 0.2
            rep.bayesian_score = wilson_lower * 0.6 + quality_factor * 0.4

            # Penalty for consecutive failures
            if rep.consecutive_failures >= 2:
                penalty = min(0.2, rep.consecutive_failures * 0.05)
                rep.bayesian_score = max(0, rep.bayesian_score - penalty)

        delta = rep.bayesian_score - old_score
        return delta

    def get_internal_reputation(self, worker_id: str) -> Optional[InternalReputation]:
        """Get a worker's current internal reputation."""
        return self._internal_reputations.get(worker_id)

    def get_composite_score(
        self,
        worker_id: str,
        wallet_address: str = "",
        task_categories: Optional[list[str]] = None,
    ) -> Optional[CompositeScore]:
        """
        Compute a worker's composite score using the reputation bridge.

        Combines internal reputation (from feedback pipeline) with
        on-chain reputation (from ERC-8004) for routing decisions.
        """
        rep = self._internal_reputations.get(worker_id)
        if not rep:
            return None

        # Create on-chain reputation stub (would be populated from ERC-8004)
        on_chain = OnChainReputation(
            agent_id=rep.agent_id,
            wallet_address=wallet_address or worker_id,
        )

        return self.reputation_bridge.compute_composite(
            on_chain=on_chain,
            internal=rep,
            task_categories=task_categories,
            last_active=datetime.now(timezone.utc),
        )

    # ─── EM API Interaction ────────────────────────────────────────────────

    def _em_request(self, method: str, path: str) -> Optional[dict]:
        """Make a request to the EM API."""
        url = f"{self.em_api_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = Request(url, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.request_timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as e:
            logger.warning(f"EM API error ({method} {path}): {e}")
            return None

    def _fetch_completed_tasks(self) -> list[dict]:
        """Fetch completed tasks from the EM API."""
        result = self._em_request("GET", "/api/v1/tasks?status=completed&limit=100")
        if not result:
            return []

        # Handle different API response formats
        if isinstance(result, list):
            return result
        return result.get("tasks", result.get("data", []))

    def _fetch_task(self, task_id: str) -> Optional[dict]:
        """Fetch a single task by ID."""
        return self._em_request("GET", f"/api/v1/tasks/{task_id}")

    def _extract_worker_id(self, task: dict) -> Optional[str]:
        """Extract the worker identity from a task."""
        # Try different field names used by the EM API
        for field_name in [
            "executor_id",  # EM production field name
            "worker_id",
            "assigned_worker",
            "worker_wallet",
            "worker_address",
            "assignee",
            "completed_by",
        ]:
            if task.get(field_name):
                return str(task[field_name])

        # Try nested structures
        worker = task.get("worker", {})
        if isinstance(worker, dict):
            nested_id = worker.get("id") or worker.get("wallet") or worker.get("address")
            if nested_id:
                return nested_id

        # Try applications (worker who was accepted)
        applications = task.get("applications", [])
        for app in applications:
            if isinstance(app, dict) and app.get("status") == "accepted":
                return app.get("worker_id") or app.get("wallet")

        return None

    def _extract_evidence(self, task: dict) -> list[dict]:
        """Extract evidence from task data or fetch separately.

        EM API evidence format:
        - In submissions: evidence is a dict like {"photo_geo": {...}, "device_metadata": {...}}
        - Needs to be converted to a list of {"type": type, ...data} for the parser
        - In embedded task data: may be a list of dicts with "type" field
        """
        # Evidence might be embedded in the task (test/mock format)
        evidence = task.get("evidence")
        if evidence is not None:
            if isinstance(evidence, list):
                return evidence
            if isinstance(evidence, dict):
                return self._normalize_evidence_dict(evidence)

        # Check embedded submissions
        submissions = task.get("submissions")
        if isinstance(submissions, list) and submissions:
            return self._flatten_submissions(submissions)

        # Fetch evidence separately from API
        task_id = task.get("id")
        if task_id:
            result = self._em_request(
                "GET", f"/api/v1/tasks/{task_id}/submissions"
            )
            if result:
                if isinstance(result, list):
                    return self._flatten_submissions(result)
                subs = result.get("submissions", result.get("data", []))
                return self._flatten_submissions(subs)

        return []

    def _normalize_evidence_dict(self, evidence: dict) -> list[dict]:
        """Convert EM evidence dict format to list format for parser.

        EM format: {"photo_geo": {"gps": {...}, "url": "..."}, "device_metadata": {...}}
        Parser format: [{"type": "photo_geo", "content": "url", "metadata": {...}}, ...]
        """
        items = []
        for ev_type, ev_data in evidence.items():
            if ev_type == "device_metadata":
                continue  # Skip device metadata, not evidence

            if isinstance(ev_data, dict):
                # Extract content from various possible fields
                content = (
                    ev_data.get("url")
                    or ev_data.get("fileUrl")
                    or ev_data.get("content")
                    or ev_data.get("text")
                    or str(ev_data)
                )

                # Build metadata from evidence data
                metadata = {}
                if ev_data.get("gps"):
                    gps = ev_data["gps"]
                    metadata["latitude"] = gps.get("lat")
                    metadata["longitude"] = gps.get("lng")
                    metadata["accuracy"] = gps.get("accuracy")
                if ev_data.get("timestamp"):
                    metadata["timestamp"] = ev_data["timestamp"]
                if ev_data.get("exif"):
                    metadata["exif"] = ev_data["exif"]

                items.append({
                    "type": ev_type,
                    "content": content,
                    "metadata": metadata,
                })
            else:
                items.append({
                    "type": ev_type,
                    "content": str(ev_data),
                })

        return items

    def _flatten_submissions(self, submissions: list) -> list[dict]:
        """Flatten a list of submission dicts into evidence items."""
        evidence_items = []
        for sub in submissions:
            if not isinstance(sub, dict):
                continue
            sub_evidence = sub.get("evidence", {})
            if isinstance(sub_evidence, dict):
                evidence_items.extend(self._normalize_evidence_dict(sub_evidence))
            elif isinstance(sub_evidence, list):
                evidence_items.extend(sub_evidence)
        return evidence_items

    # ─── State Persistence ─────────────────────────────────────────────────

    def _state_path(self) -> Path:
        return self.state_dir / "pipeline_state.json"

    def _registry_path(self) -> Path:
        return self.state_dir / "worker_registry.json"

    def _reputations_path(self) -> Path:
        return self.state_dir / "internal_reputations.json"

    def _load_state(self):
        """Load persisted pipeline state."""
        state_file = self._state_path()
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                self._state = PipelineState.from_dict(data)
                logger.info(
                    f"Loaded pipeline state: {self._state.total_runs} runs, "
                    f"{self._state.total_tasks_processed} tasks processed"
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load pipeline state: {e}")

        # Load worker registry
        registry_file = self._registry_path()
        if registry_file.exists():
            try:
                self.worker_registry = WorkerRegistry.load(str(registry_file))
                logger.info(
                    f"Loaded worker registry: {len(self.worker_registry.list_workers())} workers"
                )
            except Exception as e:
                logger.warning(f"Failed to load worker registry: {e}")

        # Load internal reputations
        rep_file = self._reputations_path()
        if rep_file.exists():
            try:
                with open(rep_file) as f:
                    data = json.load(f)
                for worker_id, rep_data in data.items():
                    rep = InternalReputation(
                        agent_id=rep_data.get("agent_id", hash(worker_id) % 100000),
                        bayesian_score=rep_data.get("bayesian_score", 0.5),
                        total_tasks=rep_data.get("total_tasks", 0),
                        successful_tasks=rep_data.get("successful_tasks", 0),
                        avg_rating=rep_data.get("avg_rating", 0.0),
                        avg_completion_time_hours=rep_data.get(
                            "avg_completion_time_hours", 0.0
                        ),
                        consecutive_failures=rep_data.get("consecutive_failures", 0),
                        category_scores=rep_data.get("category_scores", {}),
                    )
                    self._internal_reputations[worker_id] = rep
                logger.info(
                    f"Loaded {len(self._internal_reputations)} internal reputations"
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load internal reputations: {e}")

    def _save_state(self):
        """Persist pipeline state."""
        state_file = self._state_path()
        try:
            with open(state_file, "w") as f:
                json.dump(self._state.to_dict(), f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save pipeline state: {e}")

        # Save internal reputations
        self._save_reputations()

    def _save_worker_registry(self):
        """Persist worker registry."""
        registry_file = self._registry_path()
        try:
            self.worker_registry.save(str(registry_file))
        except OSError as e:
            logger.error(f"Failed to save worker registry: {e}")

    def _save_reputations(self):
        """Persist internal reputations."""
        rep_file = self._reputations_path()
        try:
            data = {}
            for worker_id, rep in self._internal_reputations.items():
                data[worker_id] = {
                    "agent_id": rep.agent_id,
                    "bayesian_score": rep.bayesian_score,
                    "total_tasks": rep.total_tasks,
                    "successful_tasks": rep.successful_tasks,
                    "avg_rating": rep.avg_rating,
                    "avg_completion_time_hours": rep.avg_completion_time_hours,
                    "consecutive_failures": rep.consecutive_failures,
                    "category_scores": rep.category_scores,
                }
            with open(rep_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save reputations: {e}")

    # ─── Statistics & Health ───────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        workers = self.worker_registry.list_workers()
        return {
            "pipeline": {
                "total_runs": self._state.total_runs,
                "total_tasks_processed": self._state.total_tasks_processed,
                "total_evidence_parsed": self._state.total_evidence_parsed,
                "last_run_at": self._state.last_run_at,
                "processed_ids_count": len(self._state.processed_task_ids),
            },
            "workers": {
                "total": len(workers),
                "with_reputation": len(self._internal_reputations),
                "avg_quality": (
                    sum(w.avg_quality for w in workers) / len(workers)
                    if workers
                    else 0
                ),
                "total_tasks": sum(w.task_count for w in workers),
            },
            "reputations": {
                "count": len(self._internal_reputations),
                "avg_bayesian_score": (
                    sum(r.bayesian_score for r in self._internal_reputations.values())
                    / len(self._internal_reputations)
                    if self._internal_reputations
                    else 0
                ),
                "avg_success_rate": (
                    sum(r.success_rate for r in self._internal_reputations.values())
                    / len(self._internal_reputations)
                    if self._internal_reputations
                    else 0
                ),
            },
        }

    def get_worker_profile(self, worker_id: str) -> Optional[dict]:
        """Get a complete worker profile (Skill DNA + reputation)."""
        dna = self.worker_registry.get_worker(worker_id)
        rep = self._internal_reputations.get(worker_id)

        if not dna and not rep:
            return None

        profile = {"worker_id": worker_id}
        if dna:
            profile["skill_dna"] = dna.to_dict()
        if rep:
            profile["reputation"] = {
                "bayesian_score": round(rep.bayesian_score, 3),
                "total_tasks": rep.total_tasks,
                "success_rate": round(rep.success_rate, 3),
                "avg_rating": round(rep.avg_rating, 2),
                "consecutive_failures": rep.consecutive_failures,
                "category_scores": {
                    k: round(v, 2) for k, v in rep.category_scores.items()
                },
            }

        # Compute composite score if both exist
        if dna and rep:
            on_chain = OnChainReputation(
                agent_id=rep.agent_id,
                wallet_address=worker_id,
            )
            composite = self.reputation_bridge.compute_composite(
                on_chain=on_chain,
                internal=rep,
                task_categories=list(dna.categories_seen)[:5],
                last_active=dna.last_updated,
            )
            profile["composite_score"] = composite.to_dict()

        return profile

    def get_leaderboard(self, top_n: int = 10) -> list[dict]:
        """Get top workers by composite reputation score."""
        scores = []
        for worker_id, rep in self._internal_reputations.items():
            dna = self.worker_registry.get_worker(worker_id)
            on_chain = OnChainReputation(
                agent_id=rep.agent_id,
                wallet_address=worker_id,
            )
            composite = self.reputation_bridge.compute_composite(
                on_chain=on_chain,
                internal=rep,
                last_active=dna.last_updated if dna else None,
            )
            scores.append({
                "worker_id": worker_id,
                "composite_score": round(composite.total, 2),
                "tier": composite.tier.value,
                "tasks": rep.total_tasks,
                "success_rate": round(rep.success_rate, 3),
                "avg_quality": round(dna.avg_quality, 3) if dna else 0,
                "top_skills": (
                    dna.get_top_skills(3) if dna else []
                ),
            })

        scores.sort(key=lambda x: x["composite_score"], reverse=True)
        return scores[:top_n]
