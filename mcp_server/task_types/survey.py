"""
Execution Market Survey/Data Collection Task Type

Task type for survey and data collection tasks:
- Form-based data collection
- Questionnaires and interviews
- Field data gathering
- Census-style information collection

Evidence requirements:
- Completed form/questionnaire responses
- Optional supporting photos
- Location verification (optional)

Validation includes:
- All required fields completed
- Values within acceptable ranges
- Format validation (email, phone, etc.)
- Logical consistency checks
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict, Union

from .base import (
    TaskType,
    TaskContext,
    EvidenceSpec,
    EvidenceCategory,
    ValidationResult,
    BountyRecommendation,
    TimeEstimate,
)


class FieldType(str, Enum):
    """Types of form fields."""
    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    TIME = "time"
    SELECT = "select"          # Single choice
    MULTISELECT = "multiselect"  # Multiple choice
    BOOLEAN = "boolean"        # Yes/No
    SCALE = "scale"            # 1-5, 1-10, etc.
    LOCATION = "location"      # GPS coordinates
    PHOTO = "photo"            # Photo upload


@dataclass
class FormField:
    """
    Definition of a form field in a survey.

    Attributes:
        name: Field identifier (used in responses)
        label: Human-readable label
        field_type: Type of field
        required: Whether field is required
        options: Options for select/multiselect fields
        min_value: Minimum value (for number/scale)
        max_value: Maximum value (for number/scale)
        pattern: Regex pattern for validation
        placeholder: Placeholder text
        help_text: Help text for the field
    """
    name: str
    label: str
    field_type: FieldType
    required: bool = True
    options: List[str] = field(default_factory=list)
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    placeholder: str = ""
    help_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "label": self.label,
            "field_type": self.field_type.value,
            "required": self.required,
            "options": self.options,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "pattern": self.pattern,
            "placeholder": self.placeholder,
            "help_text": self.help_text,
        }


class SurveyEvidence(TypedDict, total=False):
    """Evidence structure for survey tasks."""
    responses: Dict[str, Any]       # Field name -> response value
    photos: Optional[List[str]]     # Supporting photo URLs
    location_lat: Optional[float]   # Location where survey was completed
    location_lng: Optional[float]
    completion_timestamp: str       # When survey was completed
    duration_seconds: Optional[int]  # How long it took
    notes: Optional[str]            # Worker notes


@dataclass
class SurveyValidationConfig:
    """Configuration for survey validation."""
    require_all_fields: bool = True
    require_location: bool = False
    location_radius_meters: float = 1000.0
    min_duration_seconds: int = 60      # Minimum time to complete (anti-bot)
    max_duration_seconds: int = 7200    # Maximum time (2 hours)
    allow_partial_responses: bool = False
    validate_field_formats: bool = True


class SurveyTask(TaskType[SurveyEvidence]):
    """
    Task type for survey and data collection.

    Handles validation of form-based responses with configurable
    fields, validation rules, and optional supporting evidence.

    Examples:
    - "Complete this customer feedback survey"
    - "Collect pricing data from 5 stores"
    - "Interview local residents about X"
    """

    type_name = "survey"
    display_name = "Survey/Data Collection"
    description = "Form-based data collection with configurable fields and validation"
    category = "knowledge_access"

    # Base pricing
    BASE_BOUNTY = Decimal("3.00")
    MAX_BOUNTY = Decimal("25.00")
    PER_QUESTION_RATE = Decimal("0.50")

    # Time estimates
    BASE_TIME = 10
    PER_QUESTION_TIME = 2  # Minutes per question

    def __init__(
        self,
        fields: Optional[List[FormField]] = None,
        config: Optional[SurveyValidationConfig] = None,
    ):
        """
        Initialize survey task type.

        Args:
            fields: List of form fields for the survey
            config: Validation configuration
        """
        super().__init__()
        self.fields = fields or []
        self.config = config or SurveyValidationConfig()

    def add_field(self, field: FormField) -> "SurveyTask":
        """Add a field to the survey (builder pattern)."""
        self.fields.append(field)
        return self

    def get_required_evidence(self) -> List[EvidenceSpec]:
        """Get required evidence for survey task."""
        evidence = [
            EvidenceSpec(
                category=EvidenceCategory.FORM_RESPONSE,
                required=True,
                description="Completed survey responses",
                validation_rules={
                    "fields": [f.to_dict() for f in self.fields],
                    "require_all": self.config.require_all_fields,
                },
            ),
        ]

        if self.config.require_location:
            evidence.append(
                EvidenceSpec(
                    category=EvidenceCategory.PHOTO_GEO,
                    required=True,
                    description="Location verification",
                    validation_rules={
                        "max_distance_meters": self.config.location_radius_meters,
                    },
                )
            )

        return evidence

    def get_optional_evidence(self) -> List[EvidenceSpec]:
        """Get optional evidence for survey task."""
        optional = [
            EvidenceSpec(
                category=EvidenceCategory.PHOTO,
                required=False,
                description="Supporting photos (receipts, products, locations)",
                min_count=0,
                max_count=10,
            ),
            EvidenceSpec(
                category=EvidenceCategory.TEXT_RESPONSE,
                required=False,
                description="Additional notes or observations",
            ),
        ]

        return optional

    def validate_evidence(
        self,
        evidence: SurveyEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """
        Validate survey evidence.

        Checks:
        1. All required fields are present
        2. Field values meet validation rules
        3. Location verification (if required)
        4. Duration is reasonable (anti-bot)
        """
        result = ValidationResult.success()

        # Get responses
        responses = evidence.get("responses", {})

        # 1. Validate required fields
        required_result = self._validate_required_fields_survey(responses)
        result = result.merge(required_result)

        # 2. Validate field values
        for field_def in self.fields:
            if field_def.name in responses:
                field_result = self._validate_field(field_def, responses[field_def.name])
                result = result.merge(field_result)

        # 3. Validate location if required
        if self.config.require_location and context.has_location():
            location_result = self._validate_location(
                evidence.get("location_lat"),
                evidence.get("location_lng"),
                context.location_lat,
                context.location_lng,
            )
            result = result.merge(location_result)

        # 4. Validate duration (anti-bot check)
        duration_result = self._validate_duration(evidence.get("duration_seconds"))
        result = result.merge(duration_result)

        return result

    def _validate_required_fields_survey(
        self,
        responses: Dict[str, Any],
    ) -> ValidationResult:
        """Validate all required fields are present."""
        missing = []

        for field_def in self.fields:
            if field_def.required:
                value = responses.get(field_def.name)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    missing.append(field_def.label)

        if missing and self.config.require_all_fields:
            return ValidationResult.failure(
                errors=[f"Missing required fields: {', '.join(missing)}"],
                details={"missing_fields": missing},
            )
        elif missing:
            return ValidationResult.warning(
                warnings=[f"Some fields not completed: {', '.join(missing)}"],
                details={"incomplete_fields": missing},
            )

        return ValidationResult.success(
            details={"all_required_present": True},
        )

    def _validate_field(
        self,
        field_def: FormField,
        value: Any,
    ) -> ValidationResult:
        """Validate a single field value."""
        errors = []
        warnings = []

        # Skip validation for empty optional fields
        if not field_def.required and (value is None or value == ""):
            return ValidationResult.success()

        # Type-specific validation
        if field_def.field_type == FieldType.NUMBER:
            errors.extend(self._validate_number(field_def, value))

        elif field_def.field_type == FieldType.EMAIL:
            errors.extend(self._validate_email(value))

        elif field_def.field_type == FieldType.PHONE:
            errors.extend(self._validate_phone(value))

        elif field_def.field_type == FieldType.SCALE:
            errors.extend(self._validate_scale(field_def, value))

        elif field_def.field_type == FieldType.SELECT:
            errors.extend(self._validate_select(field_def, value))

        elif field_def.field_type == FieldType.MULTISELECT:
            errors.extend(self._validate_multiselect(field_def, value))

        elif field_def.field_type == FieldType.DATE:
            errors.extend(self._validate_date(value))

        # Pattern validation (if specified)
        if field_def.pattern and isinstance(value, str):
            import re
            if not re.match(field_def.pattern, value):
                errors.append(f"{field_def.label}: Value does not match required format")

        if errors:
            return ValidationResult.failure(errors=errors)
        elif warnings:
            return ValidationResult.warning(warnings=warnings)

        return ValidationResult.success()

    def _validate_number(self, field_def: FormField, value: Any) -> List[str]:
        """Validate number field."""
        errors = []

        try:
            num_value = float(value)

            if field_def.min_value is not None and num_value < field_def.min_value:
                errors.append(
                    f"{field_def.label}: Value {num_value} below minimum {field_def.min_value}"
                )

            if field_def.max_value is not None and num_value > field_def.max_value:
                errors.append(
                    f"{field_def.label}: Value {num_value} above maximum {field_def.max_value}"
                )

        except (ValueError, TypeError):
            errors.append(f"{field_def.label}: Must be a valid number")

        return errors

    def _validate_email(self, value: Any) -> List[str]:
        """Validate email field."""
        import re
        if not isinstance(value, str):
            return ["Email must be a string"]

        # Simple email pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            return ["Invalid email format"]

        return []

    def _validate_phone(self, value: Any) -> List[str]:
        """Validate phone field."""
        if not isinstance(value, str):
            return ["Phone must be a string"]

        # Remove common formatting characters
        cleaned = "".join(c for c in value if c.isdigit() or c == "+")

        if len(cleaned) < 7 or len(cleaned) > 15:
            return ["Phone number should be 7-15 digits"]

        return []

    def _validate_scale(self, field_def: FormField, value: Any) -> List[str]:
        """Validate scale field (1-5, 1-10, etc.)."""
        try:
            num_value = int(value)
            min_val = field_def.min_value or 1
            max_val = field_def.max_value or 5

            if num_value < min_val or num_value > max_val:
                return [f"{field_def.label}: Must be between {min_val} and {max_val}"]

        except (ValueError, TypeError):
            return [f"{field_def.label}: Must be a valid integer"]

        return []

    def _validate_select(self, field_def: FormField, value: Any) -> List[str]:
        """Validate single-select field."""
        if not field_def.options:
            return []

        if value not in field_def.options:
            return [f"{field_def.label}: Invalid option. Must be one of: {', '.join(field_def.options)}"]

        return []

    def _validate_multiselect(self, field_def: FormField, value: Any) -> List[str]:
        """Validate multi-select field."""
        if not field_def.options:
            return []

        if not isinstance(value, list):
            return [f"{field_def.label}: Must be a list of selected options"]

        invalid = [v for v in value if v not in field_def.options]
        if invalid:
            return [f"{field_def.label}: Invalid options: {', '.join(invalid)}"]

        return []

    def _validate_date(self, value: Any) -> List[str]:
        """Validate date field."""
        if not isinstance(value, str):
            return ["Date must be a string"]

        try:
            # Try ISO format first
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
                try:
                    datetime.strptime(value, fmt)
                    return []
                except ValueError:
                    continue

            return ["Invalid date format. Use YYYY-MM-DD"]

        return []

    def _validate_location(
        self,
        evidence_lat: Optional[float],
        evidence_lng: Optional[float],
        task_lat: Optional[float],
        task_lng: Optional[float],
    ) -> ValidationResult:
        """Validate location is within acceptable range."""
        if evidence_lat is None or evidence_lng is None:
            return ValidationResult.failure(
                errors=["Location verification required but not provided"],
            )

        if task_lat is None or task_lng is None:
            return ValidationResult.success()

        distance = self._haversine_distance(
            evidence_lat, evidence_lng,
            task_lat, task_lng,
        )

        if distance > self.config.location_radius_meters:
            return ValidationResult.failure(
                errors=[
                    f"Survey completed {distance:.0f}m from target location "
                    f"(max: {self.config.location_radius_meters}m)"
                ],
            )

        return ValidationResult.success(
            details={
                "location_verified": True,
                "distance_meters": distance,
            },
        )

    def _validate_duration(
        self,
        duration_seconds: Optional[int],
    ) -> ValidationResult:
        """Validate survey completion duration."""
        if duration_seconds is None:
            return ValidationResult.warning(
                warnings=["Survey duration not recorded"],
            )

        if duration_seconds < self.config.min_duration_seconds:
            return ValidationResult.failure(
                errors=[
                    f"Survey completed too quickly ({duration_seconds}s, "
                    f"min: {self.config.min_duration_seconds}s)"
                ],
                details={"duration_check": "too_fast"},
            )

        if duration_seconds > self.config.max_duration_seconds:
            return ValidationResult.warning(
                warnings=[
                    f"Survey took unusually long ({duration_seconds}s)"
                ],
                details={"duration_check": "very_slow"},
            )

        return ValidationResult.success(
            details={
                "duration_check": "valid",
                "duration_seconds": duration_seconds,
            },
        )

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate distance between two points using Haversine formula."""
        import math

        R = 6371000

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def get_bounty_recommendation(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> BountyRecommendation:
        """Get bounty recommendation for survey task."""
        base = self.BASE_BOUNTY

        # Per-question bonus
        question_count = len(self.fields)
        question_bonus = self.PER_QUESTION_RATE * Decimal(str(max(0, question_count - 5)))

        # Complexity factor
        complexity_factor = Decimal(str(1 + (complexity - 1) * 0.2))

        # Location requirement adds premium
        location_premium = Decimal("2.00") if self.config.require_location else Decimal("0")

        # Urgency factor
        urgency_factors = {
            "flexible": Decimal("0.9"),
            "normal": Decimal("1.0"),
            "urgent": Decimal("1.3"),
        }
        urgency_factor = urgency_factors.get(context.urgency, Decimal("1.0"))

        suggested = (base + question_bonus + location_premium) * complexity_factor * urgency_factor
        suggested = min(suggested, self.MAX_BOUNTY).quantize(Decimal("0.50"))

        return BountyRecommendation(
            min_usd=base,
            max_usd=self.MAX_BOUNTY,
            suggested_usd=suggested,
            factors={
                "base": base,
                "question_count": Decimal(str(question_count)),
                "question_bonus": question_bonus,
                "complexity": complexity_factor,
                "location_premium": location_premium,
                "urgency": urgency_factor,
            },
            reasoning=f"Base ${base} + {question_count} questions, adjusted for complexity",
        )

    def get_time_estimate(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> TimeEstimate:
        """Get time estimate for survey task."""
        base = self.BASE_TIME

        # Time per question
        question_count = len(self.fields)
        question_time = self.PER_QUESTION_TIME * question_count

        typical = base + question_time

        # Adjust for complexity (harder questions take longer)
        complexity_factor = 1 + (complexity - 1) * 0.3
        typical = int(typical * complexity_factor)

        return TimeEstimate(
            min_minutes=int(typical * 0.5),
            max_minutes=int(typical * 2),
            typical_minutes=typical,
            factors={
                "base_minutes": base,
                "question_count": question_count,
                "question_time": question_time,
                "complexity": complexity,
            },
        )

    def get_instructions_template(self) -> str:
        """Get instruction template for survey task."""
        return """
## Survey/Data Collection Task

Complete the following survey with accurate information.

### Instructions:
{survey_instructions}

### Form Fields:
{fields_description}

### Requirements:
- Complete all required fields (marked with *)
- Provide accurate and honest responses
- {location_instruction}
- Take your time - rushing may invalidate your submission

### Supporting Evidence:
{photo_instructions}

### Deadline:
{deadline}
        """.strip()

    def post_process(
        self,
        evidence: SurveyEvidence,
        validation_result: ValidationResult,
        context: TaskContext,
    ) -> Dict[str, Any]:
        """Extract structured data from survey evidence."""
        responses = evidence.get("responses", {})

        # Calculate completion statistics
        total_fields = len(self.fields)
        completed_fields = sum(
            1 for f in self.fields
            if f.name in responses and responses[f.name] is not None
        )

        return {
            "responses": responses,
            "completion_rate": completed_fields / total_fields if total_fields > 0 else 0,
            "completed_fields": completed_fields,
            "total_fields": total_fields,
            "duration_seconds": evidence.get("duration_seconds"),
            "location_verified": validation_result.details.get("location_verified", False),
            "supporting_photos_count": len(evidence.get("photos", [])),
            "worker_notes": evidence.get("notes"),
        }


# Factory function for creating common survey types
def create_price_survey(
    products: List[str],
    require_photos: bool = True,
) -> SurveyTask:
    """
    Create a price survey for checking product prices.

    Args:
        products: List of product names to check
        require_photos: Whether to require photo evidence

    Returns:
        Configured SurveyTask
    """
    fields = []

    for product in products:
        fields.extend([
            FormField(
                name=f"{product}_price",
                label=f"Price of {product}",
                field_type=FieldType.NUMBER,
                required=True,
                min_value=0,
                help_text="Enter the price in local currency",
            ),
            FormField(
                name=f"{product}_available",
                label=f"Is {product} available?",
                field_type=FieldType.BOOLEAN,
                required=True,
            ),
            FormField(
                name=f"{product}_on_sale",
                label=f"Is {product} on sale?",
                field_type=FieldType.BOOLEAN,
                required=False,
            ),
        ])

    # Add store information
    fields.extend([
        FormField(
            name="store_name",
            label="Store Name",
            field_type=FieldType.TEXT,
            required=True,
        ),
        FormField(
            name="visit_date",
            label="Date of Visit",
            field_type=FieldType.DATE,
            required=True,
        ),
    ])

    return SurveyTask(
        fields=fields,
        config=SurveyValidationConfig(
            require_location=True,
            min_duration_seconds=120,
        ),
    )


def create_customer_feedback_survey() -> SurveyTask:
    """Create a standard customer feedback survey."""
    fields = [
        FormField(
            name="overall_satisfaction",
            label="Overall Satisfaction",
            field_type=FieldType.SCALE,
            required=True,
            min_value=1,
            max_value=5,
            help_text="1 = Very Dissatisfied, 5 = Very Satisfied",
        ),
        FormField(
            name="service_quality",
            label="Service Quality",
            field_type=FieldType.SCALE,
            required=True,
            min_value=1,
            max_value=5,
        ),
        FormField(
            name="would_recommend",
            label="Would you recommend?",
            field_type=FieldType.BOOLEAN,
            required=True,
        ),
        FormField(
            name="feedback_category",
            label="Feedback Category",
            field_type=FieldType.SELECT,
            required=True,
            options=["Product", "Service", "Price", "Location", "Other"],
        ),
        FormField(
            name="comments",
            label="Additional Comments",
            field_type=FieldType.TEXT,
            required=False,
            placeholder="Share any additional feedback...",
        ),
    ]

    return SurveyTask(
        fields=fields,
        config=SurveyValidationConfig(
            require_location=False,
            min_duration_seconds=60,
        ),
    )
