"""
EvidenceParser — Extracts Skill DNA from task completion evidence.

This is the learning component of the feedback loop. When a task is completed,
the evidence submitted by the worker is parsed to extract:

1. **Skill Signals** — What skills were demonstrated?
2. **Quality Indicators** — How well was the work done?
3. **Behavioral Patterns** — Speed, thoroughness, communication style
4. **Category Expertise** — What domains does the worker excel in?

These signals feed into the ReputationBridge to build a worker's Skill DNA —
a portable, evidence-based profile that improves task routing over time.

Evidence Types (EM API):
    photo, photo_geo, video, document, receipt, signature,
    notarized, timestamp_proof, text_response, measurement, screenshot

Design decisions:
    - Heuristic-based: no ML model needed, works with structured evidence
    - Composable: each evidence type has its own parser
    - Additive: new evidence types can be added without changing existing code
    - Decay-aware: more recent evidence weighs more heavily
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger("em.swarm.evidence_parser")


# ─── Skill Signals ────────────────────────────────────────────────────────────


class SkillDimension(str, Enum):
    """Dimensions of a worker's Skill DNA."""

    PHYSICAL_EXECUTION = "physical_execution"  # Can do physical tasks
    DIGITAL_PROFICIENCY = "digital_proficiency"  # Can do digital/computer tasks
    VERIFICATION_SKILL = "verification_skill"  # Can verify/validate things
    COMMUNICATION = "communication"  # Clear reporting/documentation
    GEO_MOBILITY = "geo_mobility"  # Can travel to locations
    SPEED = "speed"  # Fast task completion
    THOROUGHNESS = "thoroughness"  # Detailed, complete work
    TECHNICAL_SKILL = "technical_skill"  # Technical/specialized knowledge
    CREATIVE_SKILL = "creative_skill"  # Creative/design abilities
    BLOCKCHAIN_LITERACY = "blockchain_literacy"  # Crypto/web3 understanding


class EvidenceQuality(str, Enum):
    """Quality assessment of submitted evidence."""

    EXCELLENT = "excellent"  # Multiple types, detailed, geo-verified
    GOOD = "good"  # Complete and relevant
    ADEQUATE = "adequate"  # Meets minimum requirements
    POOR = "poor"  # Minimal or irrelevant
    SUSPICIOUS = "suspicious"  # Potential fraud indicators


@dataclass
class SkillSignal:
    """A single skill signal extracted from evidence."""

    dimension: SkillDimension
    strength: float  # 0.0 - 1.0
    source: str  # What evidence type generated this
    detail: str = ""  # Human-readable explanation

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension.value,
            "strength": round(self.strength, 3),
            "source": self.source,
            "detail": self.detail,
        }


@dataclass
class QualityAssessment:
    """Quality assessment of a task's evidence."""

    quality: EvidenceQuality
    score: float  # 0.0 - 1.0
    evidence_count: int
    evidence_types: list[str]
    signals: list[SkillSignal] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)  # Warning flags
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "quality": self.quality.value,
            "score": round(self.score, 3),
            "evidence_count": self.evidence_count,
            "evidence_types": self.evidence_types,
            "signals": [s.to_dict() for s in self.signals],
            "flags": self.flags,
            "details": self.details,
        }


@dataclass
class SkillDNA:
    """
    A worker's extracted Skill DNA from evidence analysis.

    This is the portable profile that feeds into ReputationBridge scoring.
    """

    worker_id: str
    dimensions: dict[str, float] = field(default_factory=dict)  # dimension → score
    task_count: int = 0
    evidence_count: int = 0
    categories_seen: set[str] = field(default_factory=set)
    avg_quality: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_dimension(
        self, dimension: SkillDimension, strength: float, decay: float = 0.9
    ):
        """Update a skill dimension with exponential moving average."""
        key = dimension.value
        current = self.dimensions.get(key, 0.0)
        # EMA: new_score = decay * old + (1-decay) * new_signal
        self.dimensions[key] = decay * current + (1 - decay) * strength
        self.last_updated = datetime.now(timezone.utc)

    def apply_signals(self, signals: list[SkillSignal], decay: float = 0.9):
        """Apply multiple skill signals to the DNA."""
        for signal in signals:
            self.update_dimension(signal.dimension, signal.strength, decay)

    def get_top_skills(self, n: int = 5) -> list[tuple[str, float]]:
        """Get the top N strongest skill dimensions."""
        sorted_dims = sorted(self.dimensions.items(), key=lambda x: x[1], reverse=True)
        return sorted_dims[:n]

    def get_weakness(self) -> Optional[tuple[str, float]]:
        """Get the weakest skill dimension (if any exist)."""
        if not self.dimensions:
            return None
        return min(self.dimensions.items(), key=lambda x: x[1])

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "dimensions": {k: round(v, 3) for k, v in self.dimensions.items()},
            "task_count": self.task_count,
            "evidence_count": self.evidence_count,
            "categories": list(self.categories_seen),
            "avg_quality": round(self.avg_quality, 3),
            "top_skills": [
                {"skill": k, "score": round(v, 3)} for k, v in self.get_top_skills()
            ],
            "last_updated": self.last_updated.isoformat(),
        }


# ─── Evidence Type Parsers ────────────────────────────────────────────────────


class EvidenceParser:
    """
    Parses task completion evidence to extract skill signals and quality assessment.

    Each evidence type maps to specific skill dimensions:
        photo        → physical_execution, thoroughness
        photo_geo    → geo_mobility, verification_skill, physical_execution
        video        → thoroughness, communication
        document     → digital_proficiency, communication
        receipt      → thoroughness, physical_execution
        text_response → communication, digital_proficiency
        screenshot   → digital_proficiency, verification_skill
        measurement  → technical_skill, thoroughness
        signature    → verification_skill
        notarized    → verification_skill, thoroughness
        timestamp_proof → verification_skill, speed
    """

    # Evidence type → (skill_dimension, base_strength) mappings
    EVIDENCE_SKILL_MAP = {
        "photo": [
            (SkillDimension.PHYSICAL_EXECUTION, 0.6),
            (SkillDimension.THOROUGHNESS, 0.4),
        ],
        "photo_geo": [
            (SkillDimension.GEO_MOBILITY, 0.8),
            (SkillDimension.VERIFICATION_SKILL, 0.7),
            (SkillDimension.PHYSICAL_EXECUTION, 0.6),
        ],
        "video": [
            (SkillDimension.THOROUGHNESS, 0.7),
            (SkillDimension.COMMUNICATION, 0.5),
            (SkillDimension.PHYSICAL_EXECUTION, 0.4),
        ],
        "document": [
            (SkillDimension.DIGITAL_PROFICIENCY, 0.6),
            (SkillDimension.COMMUNICATION, 0.7),
            (SkillDimension.THOROUGHNESS, 0.5),
        ],
        "receipt": [
            (SkillDimension.THOROUGHNESS, 0.6),
            (SkillDimension.PHYSICAL_EXECUTION, 0.5),
        ],
        "text_response": [
            (SkillDimension.COMMUNICATION, 0.6),
            (SkillDimension.DIGITAL_PROFICIENCY, 0.4),
        ],
        "screenshot": [
            (SkillDimension.DIGITAL_PROFICIENCY, 0.7),
            (SkillDimension.VERIFICATION_SKILL, 0.5),
        ],
        "measurement": [
            (SkillDimension.TECHNICAL_SKILL, 0.7),
            (SkillDimension.THOROUGHNESS, 0.6),
        ],
        "signature": [
            (SkillDimension.VERIFICATION_SKILL, 0.6),
        ],
        "notarized": [
            (SkillDimension.VERIFICATION_SKILL, 0.9),
            (SkillDimension.THOROUGHNESS, 0.8),
        ],
        "timestamp_proof": [
            (SkillDimension.VERIFICATION_SKILL, 0.5),
            (SkillDimension.SPEED, 0.4),
        ],
    }

    # Quality thresholds
    QUALITY_THRESHOLDS = {
        "excellent": 0.8,
        "good": 0.6,
        "adequate": 0.4,
        "poor": 0.2,
    }

    # Fraud detection patterns
    SUSPICIOUS_PATTERNS = [
        r"lorem ipsum",
        r"test\s*evidence",
        r"placeholder",
        r"dummy",
        r"asdf",
        r"xxx+",
    ]

    def parse_evidence(
        self,
        evidence: list[dict],
        task_data: Optional[dict] = None,
    ) -> QualityAssessment:
        """
        Parse a list of evidence items and produce a quality assessment.

        Args:
            evidence: List of evidence dicts from EM API
            task_data: Optional task context for richer analysis

        Returns:
            QualityAssessment with skill signals and quality score
        """
        if not evidence:
            return QualityAssessment(
                quality=EvidenceQuality.POOR,
                score=0.0,
                evidence_count=0,
                evidence_types=[],
                flags=["no_evidence_submitted"],
            )

        signals = []
        types_seen = []
        flags = []
        quality_factors = []

        for item in evidence:
            ev_type = self._normalize_type(item)
            types_seen.append(ev_type)

            # Extract skill signals for this evidence type
            type_signals = self._parse_single_evidence(item, ev_type)
            signals.extend(type_signals)

            # Check for suspicious patterns
            content = str(item.get("content", "")) + str(item.get("description", ""))
            if self._check_suspicious(content):
                flags.append(f"suspicious_content_{ev_type}")

            # Assess individual evidence quality
            item_quality = self._assess_item_quality(item, ev_type)
            quality_factors.append(item_quality)

        # Compute aggregate quality score
        base_score = (
            sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
        )

        # Bonus for evidence diversity (multiple types)
        unique_types = len(set(types_seen))
        diversity_bonus = min(0.15, unique_types * 0.05)

        # Bonus for quantity (more evidence = more thorough)
        quantity_bonus = min(0.1, len(evidence) * 0.02)

        # Penalty for suspicious content
        suspicion_penalty = len(flags) * 0.15

        # Final score
        final_score = max(
            0.0,
            min(1.0, base_score + diversity_bonus + quantity_bonus - suspicion_penalty),
        )

        # Determine quality tier
        if flags and any("suspicious" in f for f in flags):
            quality = EvidenceQuality.SUSPICIOUS
        elif final_score >= self.QUALITY_THRESHOLDS["excellent"]:
            quality = EvidenceQuality.EXCELLENT
        elif final_score >= self.QUALITY_THRESHOLDS["good"]:
            quality = EvidenceQuality.GOOD
        elif final_score >= self.QUALITY_THRESHOLDS["adequate"]:
            quality = EvidenceQuality.ADEQUATE
        else:
            quality = EvidenceQuality.POOR

        # Add task-context signals if available
        if task_data:
            context_signals = self._extract_task_context_signals(task_data)
            signals.extend(context_signals)

        return QualityAssessment(
            quality=quality,
            score=final_score,
            evidence_count=len(evidence),
            evidence_types=list(set(types_seen)),
            signals=signals,
            flags=flags,
            details={
                "base_score": round(base_score, 3),
                "diversity_bonus": round(diversity_bonus, 3),
                "quantity_bonus": round(quantity_bonus, 3),
                "suspicion_penalty": round(suspicion_penalty, 3),
                "unique_types": unique_types,
            },
        )

    def _normalize_type(self, item: dict) -> str:
        """Normalize evidence type from API response."""
        ev_type = item.get("type", item.get("evidence_type", "unknown"))
        return str(ev_type).lower().strip()

    def _parse_single_evidence(self, item: dict, ev_type: str) -> list[SkillSignal]:
        """Parse a single evidence item into skill signals."""
        signals = []
        mappings = self.EVIDENCE_SKILL_MAP.get(ev_type, [])

        for dimension, base_strength in mappings:
            # Adjust strength based on evidence content quality
            content = item.get("content", "")
            metadata = item.get("metadata", {}) or {}

            strength = base_strength
            detail_parts = [f"from {ev_type}"]

            # Boost for rich content
            if isinstance(content, str) and len(content) > 100:
                strength = min(1.0, strength + 0.1)
                detail_parts.append("detailed_content")

            # Boost for metadata richness
            if metadata and len(metadata) > 2:
                strength = min(1.0, strength + 0.05)
                detail_parts.append("rich_metadata")

            # Boost for geo data presence
            if metadata.get("latitude") or metadata.get("location"):
                if dimension == SkillDimension.GEO_MOBILITY:
                    strength = min(1.0, strength + 0.15)
                    detail_parts.append("geo_verified")

            # Boost for timestamp presence (proves timeliness)
            if metadata.get("timestamp") or metadata.get("captured_at"):
                if dimension == SkillDimension.SPEED:
                    strength = min(1.0, strength + 0.1)
                    detail_parts.append("timestamped")

            signals.append(
                SkillSignal(
                    dimension=dimension,
                    strength=strength,
                    source=ev_type,
                    detail=", ".join(detail_parts),
                )
            )

        # Default signal for unknown evidence types
        if not mappings:
            signals.append(
                SkillSignal(
                    dimension=SkillDimension.THOROUGHNESS,
                    strength=0.3,
                    source=ev_type,
                    detail=f"unknown evidence type: {ev_type}",
                )
            )

        return signals

    def _assess_item_quality(self, item: dict, ev_type: str) -> float:
        """Assess the quality of a single evidence item (0.0-1.0)."""
        score = 0.5  # Base: adequate

        content = item.get("content", "")
        metadata = item.get("metadata", {}) or {}

        # Content presence
        if content:
            score += 0.1
            if isinstance(content, str) and len(content) > 50:
                score += 0.1
            if isinstance(content, str) and len(content) > 200:
                score += 0.05

        # Metadata richness
        if metadata:
            score += 0.05
            if len(metadata) > 3:
                score += 0.05

        # Type-specific quality bonuses
        if ev_type == "photo_geo" and metadata.get("latitude"):
            score += 0.15  # Geo-verified photos are high quality
        elif ev_type == "notarized":
            score += 0.2  # Notarized evidence is premium
        elif ev_type == "video":
            score += 0.1  # Video takes more effort
        elif ev_type == "measurement" and content:
            score += 0.1  # Measurements with data are valuable

        return min(1.0, score)

    def _check_suspicious(self, content: str) -> bool:
        """Check content for suspicious/fraud patterns."""
        if not content:
            return False
        content_lower = content.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, content_lower):
                return True
        return False

    def _extract_task_context_signals(self, task_data: dict) -> list[SkillSignal]:
        """Extract additional signals from task context."""
        signals = []
        category = task_data.get("category", "").lower()

        # Category-specific skill signals
        if category in ("delivery", "pickup", "errand"):
            signals.append(
                SkillSignal(
                    dimension=SkillDimension.PHYSICAL_EXECUTION,
                    strength=0.3,
                    source="task_context",
                    detail=f"completed {category} task",
                )
            )
        elif category in ("coding", "testing", "data_entry"):
            signals.append(
                SkillSignal(
                    dimension=SkillDimension.DIGITAL_PROFICIENCY,
                    strength=0.3,
                    source="task_context",
                    detail=f"completed {category} task",
                )
            )
        elif category in ("design", "writing"):
            signals.append(
                SkillSignal(
                    dimension=SkillDimension.CREATIVE_SKILL,
                    strength=0.3,
                    source="task_context",
                    detail=f"completed {category} task",
                )
            )
        elif category in ("blockchain", "defi", "nft"):
            signals.append(
                SkillSignal(
                    dimension=SkillDimension.BLOCKCHAIN_LITERACY,
                    strength=0.3,
                    source="task_context",
                    detail=f"completed {category} task",
                )
            )

        # Bounty-based signal (higher bounty = more complex work, presumably)
        bounty = task_data.get("bounty_amount", 0)
        try:
            bounty = float(bounty)
        except (ValueError, TypeError):
            bounty = 0
        if bounty >= 50:
            signals.append(
                SkillSignal(
                    dimension=SkillDimension.TECHNICAL_SKILL,
                    strength=0.2,
                    source="task_context",
                    detail=f"high-value task (${bounty})",
                )
            )

        return signals

    def update_skill_dna(
        self,
        dna: SkillDNA,
        assessment: QualityAssessment,
        task_categories: Optional[list[str]] = None,
        decay: float = 0.9,
    ) -> SkillDNA:
        """
        Update a worker's Skill DNA based on evidence assessment.

        Args:
            dna: The worker's current Skill DNA
            assessment: Quality assessment from parse_evidence()
            task_categories: Categories of the completed task
            decay: EMA decay factor (higher = more weight on history)

        Returns:
            Updated SkillDNA
        """
        # Apply skill signals
        dna.apply_signals(assessment.signals, decay=decay)

        # Update counters
        dna.task_count += 1
        dna.evidence_count += assessment.evidence_count

        # Update categories
        if task_categories:
            dna.categories_seen.update(task_categories)

        # Update average quality (running average)
        if dna.task_count == 1:
            dna.avg_quality = assessment.score
        else:
            dna.avg_quality = (
                dna.avg_quality * (dna.task_count - 1) + assessment.score
            ) / dna.task_count

        return dna


# ─── Worker Registry ──────────────────────────────────────────────────────────


class WorkerRegistry:
    """
    In-memory registry of worker Skill DNA profiles.

    Persists to JSON for state recovery across restarts.
    In production, this would be backed by a database.
    """

    def __init__(self):
        self._workers: dict[str, SkillDNA] = {}
        self._parser = EvidenceParser()

    def get_or_create(self, worker_id: str) -> SkillDNA:
        """Get a worker's Skill DNA, creating if new."""
        if worker_id not in self._workers:
            self._workers[worker_id] = SkillDNA(worker_id=worker_id)
        return self._workers[worker_id]

    def process_completion(
        self,
        worker_id: str,
        evidence: list[dict],
        task_data: Optional[dict] = None,
        task_categories: Optional[list[str]] = None,
    ) -> tuple[SkillDNA, QualityAssessment]:
        """
        Process a task completion: parse evidence + update worker's Skill DNA.

        Returns (updated_dna, quality_assessment).
        """
        dna = self.get_or_create(worker_id)
        assessment = self._parser.parse_evidence(evidence, task_data)
        self._parser.update_skill_dna(dna, assessment, task_categories)

        logger.info(
            f"Updated Skill DNA for {worker_id}: "
            f"quality={assessment.quality.value}, "
            f"score={assessment.score:.2f}, "
            f"tasks={dna.task_count}, "
            f"top_skills={dna.get_top_skills(3)}"
        )

        return dna, assessment

    def get_worker(self, worker_id: str) -> Optional[SkillDNA]:
        """Get a worker's Skill DNA, or None if not registered."""
        return self._workers.get(worker_id)

    def list_workers(self) -> list[SkillDNA]:
        """List all registered workers."""
        return list(self._workers.values())

    def get_specialists(
        self, dimension: SkillDimension, min_score: float = 0.5
    ) -> list[SkillDNA]:
        """Find workers who are strong in a specific skill dimension."""
        specialists = []
        for dna in self._workers.values():
            score = dna.dimensions.get(dimension.value, 0.0)
            if score >= min_score:
                specialists.append(dna)
        return sorted(
            specialists,
            key=lambda d: d.dimensions.get(dimension.value, 0),
            reverse=True,
        )

    def get_best_for_category(self, category: str, top_n: int = 5) -> list[SkillDNA]:
        """Find workers with experience in a specific category."""
        experienced = [
            dna for dna in self._workers.values() if category in dna.categories_seen
        ]
        return sorted(experienced, key=lambda d: d.avg_quality, reverse=True)[:top_n]

    def save(self, path: str):
        """Save registry to JSON file."""
        import json

        data = {worker_id: dna.to_dict() for worker_id, dna in self._workers.items()}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "WorkerRegistry":
        """Load registry from JSON file."""
        import json

        registry = cls()
        try:
            with open(path) as f:
                data = json.load(f)
            for worker_id, dna_data in data.items():
                dna = SkillDNA(worker_id=worker_id)
                dna.dimensions = dna_data.get("dimensions", {})
                dna.task_count = dna_data.get("task_count", 0)
                dna.evidence_count = dna_data.get("evidence_count", 0)
                dna.categories_seen = set(dna_data.get("categories", []))
                dna.avg_quality = dna_data.get("avg_quality", 0.0)
                if dna_data.get("last_updated"):
                    dna.last_updated = datetime.fromisoformat(dna_data["last_updated"])
                registry._workers[worker_id] = dna
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return registry

    def to_dict(self) -> dict:
        """Export full registry as dict."""
        return {
            "worker_count": len(self._workers),
            "workers": {wid: dna.to_dict() for wid, dna in self._workers.items()},
        }
