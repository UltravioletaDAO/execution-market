"""
Execution Market Task Type Base Classes

Abstract base class for all task types in Execution Market.
Defines the interface that all task types must implement:
- Evidence requirements
- Validation logic
- Pre/post processing hooks
- Bounty recommendations
- Time estimates

This enables:
1. Type-safe task handling across the system
2. Consistent validation patterns
3. Pluggable task types via registry
4. Clear contracts for new task types
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic
from uuid import uuid4


class EvidenceCategory(str, Enum):
    """Categories of evidence that can be required."""
    PHOTO = "photo"
    PHOTO_GEO = "photo_geo"
    PHOTO_TIMESTAMP = "photo_timestamp"
    VIDEO = "video"
    DOCUMENT = "document"
    RECEIPT = "receipt"
    SIGNATURE = "signature"
    TEXT_RESPONSE = "text_response"
    NUMERIC_VALUE = "numeric_value"
    FORM_RESPONSE = "form_response"
    QUESTIONNAIRE = "questionnaire"
    SCREENSHOT = "screenshot"


class ValidationSeverity(str, Enum):
    """Severity of validation failures."""
    ERROR = "error"       # Task cannot be accepted
    WARNING = "warning"   # Task can be accepted with notes
    INFO = "info"         # Informational only


@dataclass
class EvidenceSpec:
    """
    Specification for a single piece of evidence.

    Attributes:
        category: Type of evidence
        required: Whether this evidence is mandatory
        description: Instructions for the worker
        validation_rules: Rules for validating this evidence
        max_age_minutes: Maximum age of evidence (for photos/videos)
        min_count: Minimum number required (e.g., multiple photos)
        max_count: Maximum number allowed
    """
    category: EvidenceCategory
    required: bool = True
    description: str = ""
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    max_age_minutes: Optional[int] = None
    min_count: int = 1
    max_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "category": self.category.value,
            "required": self.required,
            "description": self.description,
            "validation_rules": self.validation_rules,
            "max_age_minutes": self.max_age_minutes,
            "min_count": self.min_count,
            "max_count": self.max_count,
        }


@dataclass
class ValidationResult:
    """
    Result of validating evidence.

    Attributes:
        is_valid: Whether validation passed
        severity: Severity of any issues
        errors: List of error messages
        warnings: List of warning messages
        details: Additional validation details
    """
    is_valid: bool
    severity: ValidationSeverity = ValidationSeverity.INFO
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, details: Optional[Dict[str, Any]] = None) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            details=details or {},
        )

    @classmethod
    def failure(cls, errors: List[str], details: Optional[Dict[str, Any]] = None) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(
            is_valid=False,
            severity=ValidationSeverity.ERROR,
            errors=errors,
            details=details or {},
        )

    @classmethod
    def warning(cls, warnings: List[str], details: Optional[Dict[str, Any]] = None) -> "ValidationResult":
        """Create a validation result with warnings but still valid."""
        return cls(
            is_valid=True,
            severity=ValidationSeverity.WARNING,
            warnings=warnings,
            details=details or {},
        )

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge with another validation result."""
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            severity=max(self.severity, other.severity, key=lambda x: ["info", "warning", "error"].index(x.value)),
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            details={**self.details, **other.details},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "is_valid": self.is_valid,
            "severity": self.severity.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
        }


@dataclass
class BountyRecommendation:
    """
    Recommended bounty for a task.

    Attributes:
        min_usd: Minimum recommended bounty
        max_usd: Maximum recommended bounty
        suggested_usd: Suggested bounty (optimal)
        factors: Factors that influenced the recommendation
        reasoning: Human-readable explanation
    """
    min_usd: Decimal
    max_usd: Decimal
    suggested_usd: Decimal
    factors: Dict[str, Decimal] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "min_usd": str(self.min_usd),
            "max_usd": str(self.max_usd),
            "suggested_usd": str(self.suggested_usd),
            "factors": {k: str(v) for k, v in self.factors.items()},
            "reasoning": self.reasoning,
        }


@dataclass
class TimeEstimate:
    """
    Estimated time to complete a task.

    Attributes:
        min_minutes: Minimum expected time
        max_minutes: Maximum expected time
        typical_minutes: Typical/average time
        factors: Factors that influenced the estimate
    """
    min_minutes: int
    max_minutes: int
    typical_minutes: int
    factors: Dict[str, Any] = field(default_factory=dict)

    def to_timedelta(self) -> timedelta:
        """Convert typical time to timedelta."""
        return timedelta(minutes=self.typical_minutes)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "min_minutes": self.min_minutes,
            "max_minutes": self.max_minutes,
            "typical_minutes": self.typical_minutes,
            "factors": self.factors,
        }


@dataclass
class TaskContext:
    """
    Context for task execution and validation.

    Contains information about the task, location, and requirements
    that task types use for validation and processing.
    """
    task_id: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    location_radius_meters: float = 500.0
    deadline_hours: int = 24
    urgency: str = "normal"  # normal, urgent, flexible
    worker_reputation: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_location(self) -> bool:
        """Check if location is specified."""
        return self.location_lat is not None and self.location_lng is not None


# Type variable for evidence data
EvidenceData = TypeVar("EvidenceData", bound=Dict[str, Any])


class TaskType(ABC, Generic[EvidenceData]):
    """
    Abstract base class for all Execution Market task types.

    Defines the interface that all task types must implement.
    Task types handle:
    - Defining what evidence is required
    - Validating submitted evidence
    - Pre/post processing hooks
    - Bounty recommendations
    - Time estimates

    Example usage:
        class PhotoVerificationTask(TaskType[PhotoEvidence]):
            def get_required_evidence(self) -> List[EvidenceSpec]:
                return [
                    EvidenceSpec(
                        category=EvidenceCategory.PHOTO_GEO,
                        required=True,
                        description="Photo with GPS coordinates",
                    )
                ]

            def validate_evidence(self, evidence: PhotoEvidence, context: TaskContext) -> ValidationResult:
                # Validate GPS, timestamp, AI-generation, etc.
                ...
    """

    # Class-level metadata
    type_name: str = "base"
    display_name: str = "Base Task"
    description: str = "Abstract base task type"
    category: str = "general"

    def __init__(self):
        """Initialize the task type."""
        self._id = str(uuid4())

    @property
    def id(self) -> str:
        """Unique identifier for this task type instance."""
        return self._id

    # ==================== Required Methods ====================

    @abstractmethod
    def get_required_evidence(self) -> List[EvidenceSpec]:
        """
        Get the list of required evidence specifications.

        Returns:
            List of EvidenceSpec defining what evidence is needed
        """
        pass

    @abstractmethod
    def validate_evidence(
        self,
        evidence: EvidenceData,
        context: TaskContext,
    ) -> ValidationResult:
        """
        Validate submitted evidence against task requirements.

        This is the core validation method that checks:
        - All required evidence is present
        - Evidence meets quality requirements
        - Evidence passes anti-fraud checks

        Args:
            evidence: The submitted evidence data
            context: Task context with location, deadline, etc.

        Returns:
            ValidationResult with success/failure and details
        """
        pass

    # ==================== Optional Methods ====================

    def pre_process(
        self,
        task_data: Dict[str, Any],
        context: TaskContext,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Pre-process task data before publication.

        Can be used to:
        - Normalize data
        - Set defaults
        - Generate derived fields
        - Validate task configuration

        Args:
            task_data: Raw task data
            context: Task context

        Returns:
            Tuple of (processed data, list of warnings)
        """
        return task_data, []

    def post_process(
        self,
        evidence: EvidenceData,
        validation_result: ValidationResult,
        context: TaskContext,
    ) -> Dict[str, Any]:
        """
        Post-process evidence after validation.

        Can be used to:
        - Extract structured data from evidence
        - Generate summaries
        - Calculate metrics
        - Prepare data for downstream systems

        Args:
            evidence: The submitted evidence
            validation_result: Result of validation
            context: Task context

        Returns:
            Dictionary of extracted/processed data
        """
        return {}

    def get_bounty_recommendation(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> BountyRecommendation:
        """
        Get recommended bounty for this task type.

        Args:
            context: Task context with location, urgency, etc.
            complexity: Task complexity (1-5)

        Returns:
            BountyRecommendation with suggested amounts
        """
        # Default implementation - subclasses should override
        base = Decimal("5.00")
        complexity_factor = Decimal(str(1 + (complexity - 1) * 0.25))

        urgency_factors = {
            "flexible": Decimal("0.9"),
            "normal": Decimal("1.0"),
            "urgent": Decimal("1.5"),
        }
        urgency_factor = urgency_factors.get(context.urgency, Decimal("1.0"))

        suggested = base * complexity_factor * urgency_factor

        return BountyRecommendation(
            min_usd=base,
            max_usd=suggested * Decimal("2"),
            suggested_usd=suggested.quantize(Decimal("0.01")),
            factors={
                "base": base,
                "complexity": complexity_factor,
                "urgency": urgency_factor,
            },
            reasoning=f"Base ${base} x complexity {complexity_factor} x urgency {urgency_factor}",
        )

    def get_time_estimate(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> TimeEstimate:
        """
        Get estimated time to complete this task.

        Args:
            context: Task context
            complexity: Task complexity (1-5)

        Returns:
            TimeEstimate with min/max/typical times
        """
        # Default implementation - subclasses should override
        base_minutes = 15
        complexity_factor = 1 + (complexity - 1) * 0.5

        typical = int(base_minutes * complexity_factor)

        return TimeEstimate(
            min_minutes=int(typical * 0.5),
            max_minutes=int(typical * 2),
            typical_minutes=typical,
            factors={
                "base_minutes": base_minutes,
                "complexity": complexity,
            },
        )

    def get_instructions_template(self) -> str:
        """
        Get a template for task instructions.

        Returns:
            String template with placeholders like {location}, {deadline}
        """
        return """
Complete this task by the deadline.

Required evidence:
{evidence_list}

Location: {location}
Deadline: {deadline}
        """.strip()

    def get_optional_evidence(self) -> List[EvidenceSpec]:
        """
        Get list of optional evidence that enhances the submission.

        Returns:
            List of optional EvidenceSpec
        """
        return []

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this task type.

        Returns:
            Dictionary with type_name, display_name, description, etc.
        """
        return {
            "type_name": self.type_name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "required_evidence": [e.to_dict() for e in self.get_required_evidence()],
            "optional_evidence": [e.to_dict() for e in self.get_optional_evidence()],
        }

    # ==================== Validation Helpers ====================

    def _validate_required_fields(
        self,
        evidence: Dict[str, Any],
        required_fields: List[str],
    ) -> ValidationResult:
        """
        Helper to validate required fields are present.

        Args:
            evidence: Evidence dictionary
            required_fields: List of required field names

        Returns:
            ValidationResult
        """
        missing = [f for f in required_fields if f not in evidence or evidence[f] is None]

        if missing:
            return ValidationResult.failure(
                errors=[f"Missing required fields: {', '.join(missing)}"],
            )

        return ValidationResult.success()

    def _validate_value_range(
        self,
        value: Any,
        field_name: str,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
    ) -> ValidationResult:
        """
        Helper to validate a value is within range.

        Args:
            value: The value to validate
            field_name: Name of the field (for error messages)
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)

        Returns:
            ValidationResult
        """
        errors = []

        if min_value is not None and value < min_value:
            errors.append(f"{field_name} ({value}) is below minimum ({min_value})")

        if max_value is not None and value > max_value:
            errors.append(f"{field_name} ({value}) exceeds maximum ({max_value})")

        if errors:
            return ValidationResult.failure(errors=errors)

        return ValidationResult.success()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type_name={self.type_name}>"
