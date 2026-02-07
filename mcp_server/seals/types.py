"""
Seal Types and Definitions (NOW-183 to NOW-187)

Seals are on-chain credentials that verify worker capabilities:
- SKILL seals: Verified abilities (e.g., "Fotografía profesional")
- WORK seals: Work history milestones (e.g., "100+ deliveries completados")
- BEHAVIOR seals: Behavioral patterns (e.g., "Respuesta rápida")

Seals differ from reputation scores:
- Reputation is continuous (1-100)
- Seals are discrete achievements that persist
- Seals can have expiration dates (e.g., certifications)
- Seals are stored on-chain via SealRegistry contract
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
import hashlib


class SealCategory(str, Enum):
    """Categories of seals that workers can earn."""

    SKILL = "skill"  # Verified abilities (NOW-184)
    WORK = "work"  # Work history milestones (NOW-185)
    BEHAVIOR = "behavior"  # Behavioral patterns


class SkillSealType(str, Enum):
    """
    Skill-based seals (NOW-184)

    These require verification before issuance:
    - Portfolio review
    - Test task completion
    - External certification
    """

    # Visual documentation skills
    PHOTOGRAPHY_VERIFIED = "photography_verified"
    PHOTOGRAPHY_PROFESSIONAL = "photography_professional"
    VIDEO_VERIFIED = "video_verified"

    # Document handling
    DOCUMENT_HANDLING = "document_handling_verified"
    NOTARY_CERTIFIED = "notary_certified"

    # Physical tasks
    DELIVERY_CERTIFIED = "delivery_certified"
    DRIVING_VERIFIED = "driving_verified"

    # Technical skills
    TECHNICAL_BASIC = "technical_basic"
    TECHNICAL_ADVANCED = "technical_advanced"

    # Language skills
    BILINGUAL_EN_ES = "bilingual_en_es"
    TRILINGUAL = "trilingual"

    # Specialized
    MEDICAL_CERTIFIED = "medical_certified"
    LEGAL_CERTIFIED = "legal_certified"
    FINANCIAL_CERTIFIED = "financial_certified"


class WorkSealType(str, Enum):
    """
    Work milestone seals (NOW-185)

    Automatically issued when milestones are reached.
    These are non-revocable and permanent.
    """

    # Task completion milestones
    TASKS_10 = "tasks_10_completed"
    TASKS_25 = "tasks_25_completed"
    TASKS_50 = "tasks_50_completed"
    TASKS_100 = "tasks_100_completed"
    TASKS_250 = "tasks_250_completed"
    TASKS_500 = "tasks_500_completed"
    TASKS_1000 = "tasks_1000_completed"

    # Earnings milestones
    EARNED_100_USD = "earned_100_usd"
    EARNED_500_USD = "earned_500_usd"
    EARNED_1000_USD = "earned_1000_usd"
    EARNED_5000_USD = "earned_5000_usd"
    EARNED_10000_USD = "earned_10000_usd"

    # Category-specific milestones
    DELIVERY_10 = "delivery_10_completed"
    DELIVERY_50 = "delivery_50_completed"
    DELIVERY_100 = "delivery_100_completed"

    PHOTO_10 = "photo_10_completed"
    PHOTO_50 = "photo_50_completed"
    PHOTO_100 = "photo_100_completed"

    # Tenure milestones
    ACTIVE_30_DAYS = "active_30_days"
    ACTIVE_90_DAYS = "active_90_days"
    ACTIVE_180_DAYS = "active_180_days"
    ACTIVE_365_DAYS = "active_365_days"


class BehaviorSealType(str, Enum):
    """
    Behavior-based seals.

    Awarded based on patterns over time.
    Some can be revoked if behavior changes.
    """

    # Response time
    FAST_RESPONDER = "fast_responder"  # Avg response < 1 hour
    INSTANT_RESPONDER = "instant_responder"  # Avg response < 15 min

    # Reliability
    NEVER_CANCELLED = "never_cancelled"  # 0 cancellations in 50+ tasks
    ALWAYS_ON_TIME = "always_on_time"  # 100% on-time in 20+ tasks

    # Quality
    HIGH_QUALITY = "high_quality"  # Avg rating > 90 for 10+ tasks
    EXCEPTIONAL_QUALITY = "exceptional_quality"  # Avg rating > 95 for 25+ tasks

    # Consistency
    CONSISTENT_PERFORMER = "consistent_performer"  # Low variance in ratings

    # Community
    HELPFUL_REVIEWER = "helpful_reviewer"  # Provides useful feedback
    MENTOR = "mentor"  # Helps new workers


class SealStatus(str, Enum):
    """Status of a seal."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"  # Awaiting on-chain confirmation


class VerificationMethod(str, Enum):
    """How a seal was verified before issuance."""

    AUTOMATIC = "automatic"  # System-verified (milestones)
    PORTFOLIO = "portfolio"  # Portfolio review
    TEST_TASK = "test_task"  # Completed test task
    EXTERNAL_CERT = "external_cert"  # External certification
    PEER_REVIEW = "peer_review"  # Peer verification
    ADMIN = "admin"  # Admin manual verification


@dataclass
class SealRequirement:
    """
    Requirements for earning a seal (NOW-187).

    Defines what a worker must achieve or demonstrate
    to earn a specific seal.
    """

    seal_type: str
    category: SealCategory
    display_name: str
    display_name_es: str
    description: str
    description_es: str

    # Requirements
    min_tasks: Optional[int] = None
    min_earnings_usd: Optional[float] = None
    min_rating: Optional[float] = None
    min_active_days: Optional[int] = None
    task_category: Optional[str] = None  # Filter by task type

    # Verification
    verification_method: VerificationMethod = VerificationMethod.AUTOMATIC
    requires_test: bool = False
    requires_portfolio: bool = False

    # Expiration
    expires_after_days: Optional[int] = None  # None = permanent
    renewable: bool = False

    # Display
    icon: str = "badge"  # Icon name for UI
    color: str = "#4A90A4"  # Display color
    tier: int = 1  # 1-5 tier level for visual distinction


@dataclass
class Seal:
    """
    A seal credential held by a worker.

    Represents an on-chain seal with all metadata.
    """

    id: str  # Unique seal instance ID (hash of holder + type + issued_at)
    category: SealCategory
    seal_type: str  # SkillSealType, WorkSealType, or BehaviorSealType value
    holder_id: str  # Worker's ERC-8004 token ID or wallet address

    # Timestamps
    issued_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    # On-chain data
    tx_hash: Optional[str] = None  # Transaction hash when issued
    block_number: Optional[int] = None

    # Verification
    verification_method: VerificationMethod = VerificationMethod.AUTOMATIC
    verifier_id: Optional[str] = None  # Who verified (for non-automatic)
    verification_data: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> SealStatus:
        """Get current status of the seal."""
        if self.revoked_at:
            return SealStatus.REVOKED
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return SealStatus.EXPIRED
        if not self.tx_hash:
            return SealStatus.PENDING
        return SealStatus.ACTIVE

    @property
    def is_valid(self) -> bool:
        """Check if seal is currently valid."""
        return self.status == SealStatus.ACTIVE

    @classmethod
    def generate_id(cls, holder_id: str, seal_type: str, issued_at: datetime) -> str:
        """Generate unique seal ID."""
        data = f"{holder_id}:{seal_type}:{issued_at.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "category": self.category.value,
            "seal_type": self.seal_type,
            "holder_id": self.holder_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "status": self.status.value,
            "is_valid": self.is_valid,
            "verification_method": self.verification_method.value,
            "verifier_id": self.verifier_id,
            "verification_data": self.verification_data,
            "metadata": self.metadata,
        }


@dataclass
class SealBundle:
    """
    Collection of seals for display purposes.

    Groups seals by category for profile display.
    """

    holder_id: str
    skill_seals: List[Seal] = field(default_factory=list)
    work_seals: List[Seal] = field(default_factory=list)
    behavior_seals: List[Seal] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        """Total number of seals."""
        return len(self.skill_seals) + len(self.work_seals) + len(self.behavior_seals)

    @property
    def active_count(self) -> int:
        """Count of currently active seals."""
        return sum(1 for seal in self.all_seals if seal.is_valid)

    @property
    def all_seals(self) -> List[Seal]:
        """Get all seals as a single list."""
        return self.skill_seals + self.work_seals + self.behavior_seals

    def get_by_type(self, seal_type: str) -> Optional[Seal]:
        """Get a specific seal by type."""
        for seal in self.all_seals:
            if seal.seal_type == seal_type:
                return seal
        return None

    def has_seal(self, seal_type: str) -> bool:
        """Check if holder has a specific seal type."""
        seal = self.get_by_type(seal_type)
        return seal is not None and seal.is_valid


# =============================================================================
# SEAL REQUIREMENTS REGISTRY
# =============================================================================
# This defines requirements for all seals (NOW-187)

SEAL_REQUIREMENTS: Dict[str, SealRequirement] = {
    # =========================================================================
    # SKILL SEALS (NOW-184)
    # =========================================================================
    SkillSealType.PHOTOGRAPHY_VERIFIED.value: SealRequirement(
        seal_type=SkillSealType.PHOTOGRAPHY_VERIFIED.value,
        category=SealCategory.SKILL,
        display_name="Verified: Photography",
        display_name_es="Verificado: Fotografía",
        description="Worker has demonstrated basic photography skills",
        description_es="El trabajador ha demostrado habilidades básicas de fotografía",
        verification_method=VerificationMethod.TEST_TASK,
        requires_test=True,
        icon="camera",
        color="#2196F3",
        tier=1,
    ),
    SkillSealType.PHOTOGRAPHY_PROFESSIONAL.value: SealRequirement(
        seal_type=SkillSealType.PHOTOGRAPHY_PROFESSIONAL.value,
        category=SealCategory.SKILL,
        display_name="Professional Photography",
        display_name_es="Fotografía Profesional",
        description="Worker has professional-grade photography skills",
        description_es="El trabajador tiene habilidades profesionales de fotografía",
        verification_method=VerificationMethod.PORTFOLIO,
        requires_portfolio=True,
        min_rating=85.0,
        min_tasks=10,
        task_category="photography",
        icon="camera_pro",
        color="#1565C0",
        tier=3,
    ),
    SkillSealType.DELIVERY_CERTIFIED.value: SealRequirement(
        seal_type=SkillSealType.DELIVERY_CERTIFIED.value,
        category=SealCategory.SKILL,
        display_name="Certified Delivery",
        display_name_es="Entrega Certificada",
        description="Worker is certified for delivery tasks",
        description_es="El trabajador está certificado para tareas de entrega",
        verification_method=VerificationMethod.TEST_TASK,
        requires_test=True,
        icon="delivery",
        color="#4CAF50",
        tier=1,
    ),
    SkillSealType.DOCUMENT_HANDLING.value: SealRequirement(
        seal_type=SkillSealType.DOCUMENT_HANDLING.value,
        category=SealCategory.SKILL,
        display_name="Document Handling",
        display_name_es="Manejo de Documentos",
        description="Verified for handling sensitive documents",
        description_es="Verificado para manejar documentos sensibles",
        verification_method=VerificationMethod.TEST_TASK,
        requires_test=True,
        icon="document",
        color="#FF9800",
        tier=2,
    ),
    SkillSealType.BILINGUAL_EN_ES.value: SealRequirement(
        seal_type=SkillSealType.BILINGUAL_EN_ES.value,
        category=SealCategory.SKILL,
        display_name="Bilingual (EN/ES)",
        display_name_es="Bilingüe (EN/ES)",
        description="Fluent in English and Spanish",
        description_es="Fluido en inglés y español",
        verification_method=VerificationMethod.TEST_TASK,
        requires_test=True,
        icon="language",
        color="#9C27B0",
        tier=2,
    ),
    # =========================================================================
    # WORK SEALS (NOW-185)
    # =========================================================================
    WorkSealType.TASKS_10.value: SealRequirement(
        seal_type=WorkSealType.TASKS_10.value,
        category=SealCategory.WORK,
        display_name="10 Tasks Completed",
        display_name_es="10 Tareas Completadas",
        description="Successfully completed 10 tasks",
        description_es="Completó exitosamente 10 tareas",
        min_tasks=10,
        verification_method=VerificationMethod.AUTOMATIC,
        icon="badge_10",
        color="#78909C",
        tier=1,
    ),
    WorkSealType.TASKS_50.value: SealRequirement(
        seal_type=WorkSealType.TASKS_50.value,
        category=SealCategory.WORK,
        display_name="50 Tasks Completed",
        display_name_es="50 Tareas Completadas",
        description="Successfully completed 50 tasks",
        description_es="Completó exitosamente 50 tareas",
        min_tasks=50,
        verification_method=VerificationMethod.AUTOMATIC,
        icon="badge_50",
        color="#607D8B",
        tier=2,
    ),
    WorkSealType.TASKS_100.value: SealRequirement(
        seal_type=WorkSealType.TASKS_100.value,
        category=SealCategory.WORK,
        display_name="100+ Completed",
        display_name_es="100+ Completadas",
        description="Successfully completed 100+ tasks",
        description_es="Completó exitosamente 100+ tareas",
        min_tasks=100,
        verification_method=VerificationMethod.AUTOMATIC,
        icon="badge_100",
        color="#455A64",
        tier=3,
    ),
    WorkSealType.TASKS_500.value: SealRequirement(
        seal_type=WorkSealType.TASKS_500.value,
        category=SealCategory.WORK,
        display_name="500+ Completed",
        display_name_es="500+ Completadas",
        description="Elite worker with 500+ completed tasks",
        description_es="Trabajador élite con 500+ tareas completadas",
        min_tasks=500,
        verification_method=VerificationMethod.AUTOMATIC,
        icon="badge_500",
        color="#263238",
        tier=5,
    ),
    WorkSealType.EARNED_1000_USD.value: SealRequirement(
        seal_type=WorkSealType.EARNED_1000_USD.value,
        category=SealCategory.WORK,
        display_name="$1,000+ Earned",
        display_name_es="$1,000+ Ganados",
        description="Earned over $1,000 on the platform",
        description_es="Ganó más de $1,000 en la plataforma",
        min_earnings_usd=1000.0,
        verification_method=VerificationMethod.AUTOMATIC,
        icon="money_1k",
        color="#FFD700",
        tier=3,
    ),
    WorkSealType.DELIVERY_100.value: SealRequirement(
        seal_type=WorkSealType.DELIVERY_100.value,
        category=SealCategory.WORK,
        display_name="100+ Deliveries",
        display_name_es="100+ Entregas",
        description="Completed 100+ delivery tasks",
        description_es="Completó 100+ tareas de entrega",
        min_tasks=100,
        task_category="delivery",
        verification_method=VerificationMethod.AUTOMATIC,
        icon="delivery_100",
        color="#4CAF50",
        tier=3,
    ),
    WorkSealType.ACTIVE_90_DAYS.value: SealRequirement(
        seal_type=WorkSealType.ACTIVE_90_DAYS.value,
        category=SealCategory.WORK,
        display_name="90 Days Active",
        display_name_es="90 Días Activo",
        description="Active on the platform for 90+ days",
        description_es="Activo en la plataforma por 90+ días",
        min_active_days=90,
        verification_method=VerificationMethod.AUTOMATIC,
        icon="calendar_90",
        color="#00BCD4",
        tier=2,
    ),
    # =========================================================================
    # BEHAVIOR SEALS
    # =========================================================================
    BehaviorSealType.FAST_RESPONDER.value: SealRequirement(
        seal_type=BehaviorSealType.FAST_RESPONDER.value,
        category=SealCategory.BEHAVIOR,
        display_name="Fast Responder",
        display_name_es="Respuesta Rápida",
        description="Average response time under 1 hour",
        description_es="Tiempo de respuesta promedio menor a 1 hora",
        min_tasks=20,
        verification_method=VerificationMethod.AUTOMATIC,
        expires_after_days=30,  # Must maintain behavior
        renewable=True,
        icon="lightning",
        color="#FFC107",
        tier=2,
    ),
    BehaviorSealType.HIGH_QUALITY.value: SealRequirement(
        seal_type=BehaviorSealType.HIGH_QUALITY.value,
        category=SealCategory.BEHAVIOR,
        display_name="High Quality",
        display_name_es="Alta Calidad",
        description="Maintains 90+ average rating",
        description_es="Mantiene promedio de 90+ en calificación",
        min_tasks=10,
        min_rating=90.0,
        verification_method=VerificationMethod.AUTOMATIC,
        expires_after_days=60,
        renewable=True,
        icon="star",
        color="#FFD700",
        tier=3,
    ),
    BehaviorSealType.NEVER_CANCELLED.value: SealRequirement(
        seal_type=BehaviorSealType.NEVER_CANCELLED.value,
        category=SealCategory.BEHAVIOR,
        display_name="Never Cancelled",
        display_name_es="Nunca Cancela",
        description="Zero cancellations in 50+ tasks",
        description_es="Cero cancelaciones en 50+ tareas",
        min_tasks=50,
        verification_method=VerificationMethod.AUTOMATIC,
        icon="check_circle",
        color="#4CAF50",
        tier=3,
    ),
    BehaviorSealType.EXCEPTIONAL_QUALITY.value: SealRequirement(
        seal_type=BehaviorSealType.EXCEPTIONAL_QUALITY.value,
        category=SealCategory.BEHAVIOR,
        display_name="Exceptional Quality",
        display_name_es="Calidad Excepcional",
        description="Maintains 95+ average rating across 25+ tasks",
        description_es="Mantiene promedio de 95+ en 25+ tareas",
        min_tasks=25,
        min_rating=95.0,
        verification_method=VerificationMethod.AUTOMATIC,
        expires_after_days=90,
        renewable=True,
        icon="diamond",
        color="#E91E63",
        tier=5,
    ),
}


def get_requirement(seal_type: str) -> Optional[SealRequirement]:
    """Get requirement for a seal type."""
    return SEAL_REQUIREMENTS.get(seal_type)


def get_requirements_by_category(category: SealCategory) -> List[SealRequirement]:
    """Get all requirements for a category."""
    return [req for req in SEAL_REQUIREMENTS.values() if req.category == category]


def get_automatic_seals() -> List[SealRequirement]:
    """Get all seals that can be automatically issued."""
    return [
        req
        for req in SEAL_REQUIREMENTS.values()
        if req.verification_method == VerificationMethod.AUTOMATIC
    ]
