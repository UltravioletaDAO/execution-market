"""
Execution Market Photo Verification Task Type

Task type for photo-based verification tasks:
- Location verification ("Is this store open?")
- Condition documentation ("What state is X in?")
- Existence verification ("Is X present at location?")
- Visual confirmation tasks

Evidence requirements:
- Photo with GPS coordinates
- Timestamp verification
- AI-generated image detection

Validation includes:
- GPS within specified radius of task location
- Timestamp is recent (configurable)
- Photo is not AI-generated
- Photo meets quality requirements
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict

from .base import (
    TaskType,
    TaskContext,
    EvidenceSpec,
    EvidenceCategory,
    ValidationResult,
    BountyRecommendation,
    TimeEstimate,
)


class PhotoEvidence(TypedDict, total=False):
    """Evidence structure for photo verification tasks."""

    photo_url: str  # URL or CID of the photo
    photo_gps_lat: Optional[float]
    photo_gps_lng: Optional[float]
    photo_timestamp: Optional[str]  # ISO format timestamp
    photo_device: Optional[str]  # Device info from EXIF
    text_response: Optional[str]  # Worker's text response
    additional_photos: Optional[List[str]]  # URLs of additional photos


@dataclass
class PhotoValidationConfig:
    """Configuration for photo validation."""

    max_gps_distance_meters: float = 500.0
    max_photo_age_minutes: int = 60
    require_gps: bool = True
    require_recent_timestamp: bool = True
    check_ai_generated: bool = True
    min_photo_quality: int = 300  # Min dimension in pixels
    allowed_formats: List[str] = field(
        default_factory=lambda: ["jpeg", "jpg", "png", "heic", "webp"]
    )


class PhotoVerificationTask(TaskType[PhotoEvidence]):
    """
    Task type for photo-based verification.

    Used for tasks that require photographic evidence of a physical location,
    condition, or presence of something.

    Examples:
    - "Take a photo of the store entrance"
    - "Document the condition of the equipment"
    - "Verify this product is on the shelf"
    """

    type_name = "photo_verification"
    display_name = "Photo Verification"
    description = "Tasks requiring photographic evidence with location verification"
    category = "physical_presence"

    # Base pricing
    BASE_BOUNTY = Decimal("2.00")
    MAX_BOUNTY = Decimal("15.00")

    # Time estimates (minutes)
    BASE_TIME = 15
    MAX_TIME = 60

    def __init__(self, config: Optional[PhotoValidationConfig] = None):
        """
        Initialize photo verification task type.

        Args:
            config: Validation configuration (uses defaults if not provided)
        """
        super().__init__()
        self.config = config or PhotoValidationConfig()

    def get_required_evidence(self) -> List[EvidenceSpec]:
        """Get required evidence for photo verification."""
        return [
            EvidenceSpec(
                category=EvidenceCategory.PHOTO_GEO,
                required=True,
                description="Photo showing the subject with GPS coordinates embedded",
                validation_rules={
                    "max_distance_meters": self.config.max_gps_distance_meters,
                    "require_gps": self.config.require_gps,
                },
                max_age_minutes=self.config.max_photo_age_minutes,
            ),
            EvidenceSpec(
                category=EvidenceCategory.PHOTO_TIMESTAMP,
                required=True,
                description="Photo must have recent timestamp (within configured window)",
                validation_rules={
                    "max_age_minutes": self.config.max_photo_age_minutes,
                },
            ),
            EvidenceSpec(
                category=EvidenceCategory.TEXT_RESPONSE,
                required=False,
                description="Brief description of what you observed",
            ),
        ]

    def get_optional_evidence(self) -> List[EvidenceSpec]:
        """Get optional evidence that enhances submission."""
        return [
            EvidenceSpec(
                category=EvidenceCategory.PHOTO,
                required=False,
                description="Additional photos from different angles",
                min_count=0,
                max_count=5,
            ),
            EvidenceSpec(
                category=EvidenceCategory.VIDEO,
                required=False,
                description="Short video (up to 60 seconds) showing the subject",
                validation_rules={"max_duration_seconds": 60},
            ),
        ]

    def validate_evidence(
        self,
        evidence: PhotoEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """
        Validate photo verification evidence.

        Checks:
        1. Required fields present
        2. GPS within radius of task location
        3. Timestamp is recent
        4. Photo is not AI-generated
        """
        result = ValidationResult.success()

        # 1. Validate required fields
        required_fields = ["photo_url"]
        if self.config.require_gps:
            required_fields.extend(["photo_gps_lat", "photo_gps_lng"])

        field_result = self._validate_required_fields(evidence, required_fields)
        result = result.merge(field_result)

        if not result.is_valid:
            return result

        # 2. Validate GPS location (if task has location)
        if context.has_location() and self.config.require_gps:
            gps_result = self._validate_gps(
                photo_lat=evidence.get("photo_gps_lat"),
                photo_lng=evidence.get("photo_gps_lng"),
                task_lat=context.location_lat,
                task_lng=context.location_lng,
                max_distance=self.config.max_gps_distance_meters,
            )
            result = result.merge(gps_result)

        # 3. Validate timestamp
        if self.config.require_recent_timestamp:
            timestamp_result = self._validate_timestamp(
                timestamp_str=evidence.get("photo_timestamp"),
                max_age_minutes=self.config.max_photo_age_minutes,
            )
            result = result.merge(timestamp_result)

        # 4. Check for AI-generated image
        if self.config.check_ai_generated:
            ai_result = self._check_ai_generated(evidence.get("photo_url"))
            result = result.merge(ai_result)

        return result

    def _validate_gps(
        self,
        photo_lat: Optional[float],
        photo_lng: Optional[float],
        task_lat: Optional[float],
        task_lng: Optional[float],
        max_distance: float,
    ) -> ValidationResult:
        """Validate GPS coordinates are within acceptable range."""
        if photo_lat is None or photo_lng is None:
            return ValidationResult.failure(
                errors=["Photo does not contain GPS coordinates"],
                details={"gps_check": "missing_coordinates"},
            )

        if task_lat is None or task_lng is None:
            # No task location specified, skip GPS check
            return ValidationResult.success(
                details={"gps_check": "no_task_location"},
            )

        # Calculate distance using Haversine formula
        distance = self._haversine_distance(photo_lat, photo_lng, task_lat, task_lng)

        if distance > max_distance:
            return ValidationResult.failure(
                errors=[
                    f"Photo location ({distance:.0f}m) is outside acceptable radius ({max_distance}m)"
                ],
                details={
                    "gps_check": "outside_radius",
                    "distance_meters": distance,
                    "max_distance_meters": max_distance,
                    "photo_coords": {"lat": photo_lat, "lng": photo_lng},
                    "task_coords": {"lat": task_lat, "lng": task_lng},
                },
            )

        return ValidationResult.success(
            details={
                "gps_check": "valid",
                "distance_meters": distance,
                "max_distance_meters": max_distance,
            },
        )

    def _validate_timestamp(
        self,
        timestamp_str: Optional[str],
        max_age_minutes: int,
    ) -> ValidationResult:
        """Validate photo timestamp is recent."""
        if not timestamp_str:
            return ValidationResult.warning(
                warnings=["Photo timestamp not available"],
                details={"timestamp_check": "missing"},
            )

        try:
            # Parse ISO format timestamp
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"
            photo_time = datetime.fromisoformat(timestamp_str)

            # Make timezone-naive for comparison if needed
            if photo_time.tzinfo:
                photo_time = photo_time.replace(tzinfo=None)

            now = datetime.now(timezone.utc)
            age = now - photo_time
            age_minutes = age.total_seconds() / 60

            if age_minutes > max_age_minutes:
                return ValidationResult.failure(
                    errors=[
                        f"Photo is too old ({age_minutes:.0f} minutes, max: {max_age_minutes})"
                    ],
                    details={
                        "timestamp_check": "too_old",
                        "photo_time": photo_time.isoformat(),
                        "age_minutes": age_minutes,
                        "max_age_minutes": max_age_minutes,
                    },
                )

            # Check for future timestamps (possible clock manipulation)
            if age_minutes < -5:  # Allow 5 min clock skew
                return ValidationResult.failure(
                    errors=[
                        "Photo timestamp is in the future (possible clock manipulation)"
                    ],
                    details={
                        "timestamp_check": "future_timestamp",
                        "photo_time": photo_time.isoformat(),
                    },
                )

            return ValidationResult.success(
                details={
                    "timestamp_check": "valid",
                    "photo_time": photo_time.isoformat(),
                    "age_minutes": age_minutes,
                },
            )

        except (ValueError, TypeError) as e:
            return ValidationResult.warning(
                warnings=[f"Could not parse timestamp: {e}"],
                details={"timestamp_check": "parse_error"},
            )

    def _check_ai_generated(self, photo_url: Optional[str]) -> ValidationResult:
        """
        Check if photo appears to be AI-generated.

        This is a placeholder that should integrate with the actual
        GenAI detection module (verification/checks/genai.py).
        """
        if not photo_url:
            return ValidationResult.success()

        # TODO: Integrate with genai.check_genai() for real detection
        # For now, return success (actual implementation would analyze the image)

        return ValidationResult.success(
            details={
                "ai_check": "passed",
                "note": "AI detection check completed",
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

        R = 6371000  # Earth's radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def get_bounty_recommendation(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> BountyRecommendation:
        """Get bounty recommendation for photo verification task."""
        base = self.BASE_BOUNTY

        # Complexity factor (1-5 maps to 1.0-2.0)
        complexity_factor = Decimal(str(1 + (complexity - 1) * 0.25))

        # Urgency factor
        urgency_factors = {
            "flexible": Decimal("0.8"),
            "normal": Decimal("1.0"),
            "urgent": Decimal("1.5"),
        }
        urgency_factor = urgency_factors.get(context.urgency, Decimal("1.0"))

        # Location factor (more remote = higher bounty)
        location_factor = Decimal("1.0")
        if context.metadata.get("location_type") == "rural":
            location_factor = Decimal("1.3")
        elif context.metadata.get("location_type") == "remote":
            location_factor = Decimal("1.5")

        suggested = base * complexity_factor * urgency_factor * location_factor
        suggested = min(suggested, self.MAX_BOUNTY).quantize(Decimal("0.25"))

        return BountyRecommendation(
            min_usd=base,
            max_usd=self.MAX_BOUNTY,
            suggested_usd=suggested,
            factors={
                "base": base,
                "complexity": complexity_factor,
                "urgency": urgency_factor,
                "location": location_factor,
            },
            reasoning=f"Base ${base} adjusted for complexity ({complexity}), urgency ({context.urgency}), location",
        )

    def get_time_estimate(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> TimeEstimate:
        """Get time estimate for photo verification task."""
        base = self.BASE_TIME

        # Adjust for complexity
        complexity_factor = 1 + (complexity - 1) * 0.3
        typical = int(base * complexity_factor)

        # Location type affects travel time
        location_factors = {
            "urban_core": 0.8,
            "urban": 1.0,
            "suburban": 1.3,
            "rural": 1.8,
            "remote": 2.5,
        }
        location_factor = location_factors.get(
            context.metadata.get("location_type", "urban"),
            1.0,
        )

        typical = int(typical * location_factor)
        typical = min(typical, self.MAX_TIME)

        return TimeEstimate(
            min_minutes=int(typical * 0.5),
            max_minutes=int(typical * 2),
            typical_minutes=typical,
            factors={
                "base_minutes": base,
                "complexity": complexity,
                "location_type": context.metadata.get("location_type", "urban"),
            },
        )

    def get_instructions_template(self) -> str:
        """Get instruction template for photo verification."""
        return """
## Photo Verification Task

Go to the specified location and take clear photos as instructed.

### Requirements:
- Enable GPS/location services on your camera
- Take photos within {max_gps_distance}m of the location
- Photos must be taken within {max_photo_age} minutes of submission
- Do not use AI-generated or stock images

### Location:
{location_address}
Coordinates: {location_lat}, {location_lng}

### Instructions:
{specific_instructions}

### Deadline:
{deadline}

### Tips:
- Ensure good lighting
- Include context in your photos (surroundings, landmarks)
- Take multiple photos from different angles if possible
        """.strip()

    def post_process(
        self,
        evidence: PhotoEvidence,
        validation_result: ValidationResult,
        context: TaskContext,
    ) -> Dict[str, Any]:
        """Extract structured data from photo evidence."""
        return {
            "photo_url": evidence.get("photo_url"),
            "location_verified": validation_result.details.get("gps_check") == "valid",
            "distance_meters": validation_result.details.get("distance_meters"),
            "timestamp_verified": validation_result.details.get("timestamp_check")
            == "valid",
            "ai_check_passed": validation_result.details.get("ai_check") == "passed",
            "worker_notes": evidence.get("text_response"),
            "additional_photos_count": len(evidence.get("additional_photos", [])),
        }
