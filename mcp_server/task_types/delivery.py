"""
Execution Market Delivery Task Type

Task type for delivery/pickup tasks:
- Package delivery between locations
- Document pickup and delivery
- Sample collection and transport
- Any physical item transportation

Evidence requirements:
- Pickup photo with GPS and timestamp
- Delivery photo with GPS and timestamp
- Recipient signature (optional based on task)
- Chain of custody documentation

Validation includes:
- GPS at both pickup and delivery locations
- Timestamps within delivery window
- Photo evidence of package/item
- Signature verification (when required)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
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


class DeliveryEvidenceType(str, Enum):
    """Types of delivery evidence."""
    PICKUP_PHOTO = "pickup_photo"
    DELIVERY_PHOTO = "delivery_photo"
    SIGNATURE = "signature"
    PACKAGE_CONDITION = "package_condition"
    ID_VERIFICATION = "id_verification"


class DeliveryEvidence(TypedDict, total=False):
    """Evidence structure for delivery tasks."""
    # Pickup evidence
    pickup_photo_url: str
    pickup_gps_lat: float
    pickup_gps_lng: float
    pickup_timestamp: str
    pickup_notes: Optional[str]

    # Delivery evidence
    delivery_photo_url: str
    delivery_gps_lat: float
    delivery_gps_lng: float
    delivery_timestamp: str
    delivery_notes: Optional[str]

    # Signature (optional)
    signature_url: Optional[str]
    recipient_name: Optional[str]

    # Package info
    package_condition_photos: Optional[List[str]]
    package_condition_notes: Optional[str]


@dataclass
class DeliveryValidationConfig:
    """Configuration for delivery validation."""
    # GPS settings
    pickup_gps_radius_meters: float = 200.0
    delivery_gps_radius_meters: float = 200.0
    require_gps: bool = True

    # Time settings
    max_delivery_hours: int = 24
    min_transit_minutes: int = 5  # Minimum time between pickup and delivery

    # Signature settings
    require_signature: bool = False
    require_recipient_name: bool = False

    # Package documentation
    require_package_photos: bool = False
    require_condition_report: bool = False


@dataclass
class DeliveryLocation:
    """Location information for pickup/delivery."""
    lat: float
    lng: float
    address: str = ""
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    instructions: str = ""


class DeliveryTask(TaskType[DeliveryEvidence]):
    """
    Task type for delivery/pickup tasks.

    Handles validation of evidence for physical delivery tasks
    including pickup confirmation, delivery confirmation, and
    optional signature verification.

    Examples:
    - "Deliver this package from A to B"
    - "Pick up documents and deliver to office"
    - "Collect sample and transport to lab"
    """

    type_name = "delivery"
    display_name = "Delivery Task"
    description = "Physical delivery tasks with pickup and delivery verification"
    category = "simple_action"

    # Base pricing
    BASE_BOUNTY = Decimal("8.00")
    MAX_BOUNTY = Decimal("50.00")
    PER_KM_RATE = Decimal("0.50")

    # Time estimates (minutes)
    BASE_TIME = 30
    MAX_TIME = 480  # 8 hours

    def __init__(
        self,
        config: Optional[DeliveryValidationConfig] = None,
        pickup_location: Optional[DeliveryLocation] = None,
        delivery_location: Optional[DeliveryLocation] = None,
    ):
        """
        Initialize delivery task type.

        Args:
            config: Validation configuration
            pickup_location: Pickup location details
            delivery_location: Delivery location details
        """
        super().__init__()
        self.config = config or DeliveryValidationConfig()
        self.pickup_location = pickup_location
        self.delivery_location = delivery_location

    def get_required_evidence(self) -> List[EvidenceSpec]:
        """Get required evidence for delivery task."""
        evidence = [
            # Pickup evidence
            EvidenceSpec(
                category=EvidenceCategory.PHOTO_GEO,
                required=True,
                description="Photo at pickup location showing the package/item",
                validation_rules={
                    "stage": "pickup",
                    "max_distance_meters": self.config.pickup_gps_radius_meters,
                    "require_gps": self.config.require_gps,
                },
            ),
            EvidenceSpec(
                category=EvidenceCategory.PHOTO_TIMESTAMP,
                required=True,
                description="Pickup photo must have timestamp",
                validation_rules={"stage": "pickup"},
            ),
            # Delivery evidence
            EvidenceSpec(
                category=EvidenceCategory.PHOTO_GEO,
                required=True,
                description="Photo at delivery location showing successful delivery",
                validation_rules={
                    "stage": "delivery",
                    "max_distance_meters": self.config.delivery_gps_radius_meters,
                    "require_gps": self.config.require_gps,
                },
            ),
            EvidenceSpec(
                category=EvidenceCategory.PHOTO_TIMESTAMP,
                required=True,
                description="Delivery photo must have timestamp",
                validation_rules={"stage": "delivery"},
            ),
        ]

        # Add signature requirement if configured
        if self.config.require_signature:
            evidence.append(
                EvidenceSpec(
                    category=EvidenceCategory.SIGNATURE,
                    required=True,
                    description="Recipient's signature confirming delivery",
                    validation_rules={
                        "require_name": self.config.require_recipient_name,
                    },
                )
            )

        return evidence

    def get_optional_evidence(self) -> List[EvidenceSpec]:
        """Get optional evidence for delivery task."""
        optional = [
            EvidenceSpec(
                category=EvidenceCategory.TEXT_RESPONSE,
                required=False,
                description="Notes about the delivery (special instructions followed, etc.)",
            ),
        ]

        # Package condition photos (optional by default)
        if not self.config.require_package_photos:
            optional.append(
                EvidenceSpec(
                    category=EvidenceCategory.PHOTO,
                    required=False,
                    description="Photos of package condition before/during delivery",
                    min_count=0,
                    max_count=5,
                )
            )

        return optional

    def validate_evidence(
        self,
        evidence: DeliveryEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """
        Validate delivery evidence.

        Checks:
        1. Pickup photo with valid GPS and timestamp
        2. Delivery photo with valid GPS and timestamp
        3. Timestamps within delivery window
        4. Signature if required
        """
        result = ValidationResult.success()

        # 1. Validate pickup evidence
        pickup_result = self._validate_pickup(evidence, context)
        result = result.merge(pickup_result)

        # 2. Validate delivery evidence
        delivery_result = self._validate_delivery(evidence, context)
        result = result.merge(delivery_result)

        # 3. Validate time window (pickup must be before delivery)
        time_result = self._validate_time_window(evidence)
        result = result.merge(time_result)

        # 4. Validate signature if required
        if self.config.require_signature:
            sig_result = self._validate_signature(evidence)
            result = result.merge(sig_result)

        return result

    def _validate_pickup(
        self,
        evidence: DeliveryEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """Validate pickup evidence."""
        # Check required fields
        required = ["pickup_photo_url"]
        if self.config.require_gps:
            required.extend(["pickup_gps_lat", "pickup_gps_lng"])

        field_result = self._validate_required_fields(evidence, required)
        if not field_result.is_valid:
            return ValidationResult.failure(
                errors=[f"Pickup: {e}" for e in field_result.errors],
            )

        # Validate GPS if pickup location is specified
        if self.pickup_location and self.config.require_gps:
            gps_result = self._validate_gps_location(
                evidence_lat=evidence.get("pickup_gps_lat"),
                evidence_lng=evidence.get("pickup_gps_lng"),
                target_lat=self.pickup_location.lat,
                target_lng=self.pickup_location.lng,
                max_distance=self.config.pickup_gps_radius_meters,
                stage="pickup",
            )
            if not gps_result.is_valid:
                return gps_result

        # Validate timestamp
        timestamp_result = self._validate_timestamp(
            evidence.get("pickup_timestamp"),
            stage="pickup",
        )

        return timestamp_result

    def _validate_delivery(
        self,
        evidence: DeliveryEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """Validate delivery evidence."""
        # Check required fields
        required = ["delivery_photo_url"]
        if self.config.require_gps:
            required.extend(["delivery_gps_lat", "delivery_gps_lng"])

        field_result = self._validate_required_fields(evidence, required)
        if not field_result.is_valid:
            return ValidationResult.failure(
                errors=[f"Delivery: {e}" for e in field_result.errors],
            )

        # Validate GPS if delivery location is specified
        if self.delivery_location and self.config.require_gps:
            gps_result = self._validate_gps_location(
                evidence_lat=evidence.get("delivery_gps_lat"),
                evidence_lng=evidence.get("delivery_gps_lng"),
                target_lat=self.delivery_location.lat,
                target_lng=self.delivery_location.lng,
                max_distance=self.config.delivery_gps_radius_meters,
                stage="delivery",
            )
            if not gps_result.is_valid:
                return gps_result

        # Validate timestamp
        timestamp_result = self._validate_timestamp(
            evidence.get("delivery_timestamp"),
            stage="delivery",
        )

        return timestamp_result

    def _validate_gps_location(
        self,
        evidence_lat: Optional[float],
        evidence_lng: Optional[float],
        target_lat: float,
        target_lng: float,
        max_distance: float,
        stage: str,
    ) -> ValidationResult:
        """Validate GPS coordinates for a stage (pickup/delivery)."""
        if evidence_lat is None or evidence_lng is None:
            return ValidationResult.failure(
                errors=[f"{stage.title()}: GPS coordinates missing"],
                details={f"{stage}_gps_check": "missing_coordinates"},
            )

        distance = self._haversine_distance(
            evidence_lat, evidence_lng,
            target_lat, target_lng,
        )

        if distance > max_distance:
            return ValidationResult.failure(
                errors=[
                    f"{stage.title()}: Location ({distance:.0f}m) outside radius ({max_distance}m)"
                ],
                details={
                    f"{stage}_gps_check": "outside_radius",
                    f"{stage}_distance_meters": distance,
                },
            )

        return ValidationResult.success(
            details={
                f"{stage}_gps_check": "valid",
                f"{stage}_distance_meters": distance,
            },
        )

    def _validate_timestamp(
        self,
        timestamp_str: Optional[str],
        stage: str,
    ) -> ValidationResult:
        """Validate timestamp for a stage."""
        if not timestamp_str:
            return ValidationResult.warning(
                warnings=[f"{stage.title()}: Timestamp not provided"],
                details={f"{stage}_timestamp": "missing"},
            )

        try:
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"
            timestamp = datetime.fromisoformat(timestamp_str)

            return ValidationResult.success(
                details={
                    f"{stage}_timestamp": timestamp.isoformat(),
                    f"{stage}_timestamp_valid": True,
                },
            )

        except (ValueError, TypeError) as e:
            return ValidationResult.warning(
                warnings=[f"{stage.title()}: Could not parse timestamp"],
                details={f"{stage}_timestamp_error": str(e)},
            )

    def _validate_time_window(
        self,
        evidence: DeliveryEvidence,
    ) -> ValidationResult:
        """Validate delivery was after pickup and within time limit."""
        pickup_ts = evidence.get("pickup_timestamp")
        delivery_ts = evidence.get("delivery_timestamp")

        if not pickup_ts or not delivery_ts:
            return ValidationResult.warning(
                warnings=["Cannot verify delivery time window without timestamps"],
            )

        try:
            # Parse timestamps
            if pickup_ts.endswith("Z"):
                pickup_ts = pickup_ts[:-1] + "+00:00"
            if delivery_ts.endswith("Z"):
                delivery_ts = delivery_ts[:-1] + "+00:00"

            pickup_time = datetime.fromisoformat(pickup_ts)
            delivery_time = datetime.fromisoformat(delivery_ts)

            # Make timezone-naive for comparison
            if pickup_time.tzinfo:
                pickup_time = pickup_time.replace(tzinfo=None)
            if delivery_time.tzinfo:
                delivery_time = delivery_time.replace(tzinfo=None)

            # Calculate transit time
            transit = delivery_time - pickup_time
            transit_minutes = transit.total_seconds() / 60
            transit_hours = transit_minutes / 60

            # Check delivery is after pickup
            if transit_minutes < 0:
                return ValidationResult.failure(
                    errors=["Delivery timestamp is before pickup timestamp"],
                    details={"time_window_check": "invalid_order"},
                )

            # Check minimum transit time (prevent instant "deliveries")
            if transit_minutes < self.config.min_transit_minutes:
                return ValidationResult.failure(
                    errors=[
                        f"Transit time ({transit_minutes:.0f}min) below minimum ({self.config.min_transit_minutes}min)"
                    ],
                    details={"time_window_check": "too_fast"},
                )

            # Check maximum delivery time
            if transit_hours > self.config.max_delivery_hours:
                return ValidationResult.failure(
                    errors=[
                        f"Delivery took too long ({transit_hours:.1f}h, max: {self.config.max_delivery_hours}h)"
                    ],
                    details={"time_window_check": "too_slow"},
                )

            return ValidationResult.success(
                details={
                    "time_window_check": "valid",
                    "transit_minutes": transit_minutes,
                    "transit_hours": transit_hours,
                },
            )

        except (ValueError, TypeError) as e:
            return ValidationResult.warning(
                warnings=[f"Could not validate time window: {e}"],
            )

    def _validate_signature(
        self,
        evidence: DeliveryEvidence,
    ) -> ValidationResult:
        """Validate signature evidence."""
        signature_url = evidence.get("signature_url")

        if not signature_url:
            return ValidationResult.failure(
                errors=["Signature required but not provided"],
                details={"signature_check": "missing"},
            )

        # Check recipient name if required
        if self.config.require_recipient_name:
            recipient_name = evidence.get("recipient_name")
            if not recipient_name:
                return ValidationResult.failure(
                    errors=["Recipient name required but not provided"],
                    details={"signature_check": "missing_name"},
                )

        return ValidationResult.success(
            details={
                "signature_check": "valid",
                "has_signature": True,
                "has_recipient_name": bool(evidence.get("recipient_name")),
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
        """Get bounty recommendation for delivery task."""
        base = self.BASE_BOUNTY

        # Distance factor
        distance_km = context.metadata.get("distance_km", 5)
        distance_bonus = self.PER_KM_RATE * Decimal(str(distance_km))

        # Complexity factor (fragile items, time-sensitive, etc.)
        complexity_factor = Decimal(str(1 + (complexity - 1) * 0.2))

        # Urgency factor
        urgency_factors = {
            "flexible": Decimal("0.9"),
            "normal": Decimal("1.0"),
            "urgent": Decimal("1.5"),
            "same_day": Decimal("2.0"),
        }
        urgency_factor = urgency_factors.get(context.urgency, Decimal("1.0"))

        # Signature requirement adds premium
        signature_premium = Decimal("2.00") if self.config.require_signature else Decimal("0")

        suggested = (base + distance_bonus + signature_premium) * complexity_factor * urgency_factor
        suggested = min(suggested, self.MAX_BOUNTY).quantize(Decimal("0.50"))

        return BountyRecommendation(
            min_usd=base,
            max_usd=self.MAX_BOUNTY,
            suggested_usd=suggested,
            factors={
                "base": base,
                "distance_km": Decimal(str(distance_km)),
                "distance_bonus": distance_bonus,
                "complexity": complexity_factor,
                "urgency": urgency_factor,
                "signature_premium": signature_premium,
            },
            reasoning=f"Base ${base} + distance ({distance_km}km) + adjustments for complexity and urgency",
        )

    def get_time_estimate(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> TimeEstimate:
        """Get time estimate for delivery task."""
        # Base time for pickup/delivery process
        base = self.BASE_TIME

        # Add estimated travel time based on distance
        distance_km = context.metadata.get("distance_km", 5)
        # Assume average speed of 20 km/h in urban areas (accounting for traffic, walking, etc.)
        travel_minutes = (distance_km / 20) * 60

        typical = int(base + travel_minutes)
        typical = min(typical, self.MAX_TIME)

        # Adjust for complexity
        if complexity > 3:
            typical = int(typical * 1.3)

        return TimeEstimate(
            min_minutes=int(typical * 0.6),
            max_minutes=int(typical * 2),
            typical_minutes=typical,
            factors={
                "base_minutes": base,
                "travel_minutes": int(travel_minutes),
                "distance_km": distance_km,
                "complexity": complexity,
            },
        )

    def get_instructions_template(self) -> str:
        """Get instruction template for delivery task."""
        return """
## Delivery Task

Pick up the package at the pickup location and deliver it to the delivery location.

### Pickup Location:
{pickup_address}
Contact: {pickup_contact}
Instructions: {pickup_instructions}

### Delivery Location:
{delivery_address}
Contact: {delivery_contact}
Instructions: {delivery_instructions}

### Required Steps:
1. Go to pickup location
2. Take a photo showing you have the package (with GPS enabled)
3. Transport the package carefully
4. At delivery location, take a photo showing delivery (with GPS enabled)
5. {signature_instructions}

### Package Details:
{package_description}

### Time Window:
Pickup: {pickup_window}
Delivery: {delivery_window}

### Important Notes:
- Keep GPS/location enabled throughout the delivery
- Handle package with care
- Contact support if any issues arise
        """.strip()

    def post_process(
        self,
        evidence: DeliveryEvidence,
        validation_result: ValidationResult,
        context: TaskContext,
    ) -> Dict[str, Any]:
        """Extract structured data from delivery evidence."""
        details = validation_result.details

        return {
            "pickup_verified": details.get("pickup_gps_check") == "valid",
            "pickup_distance_meters": details.get("pickup_distance_meters"),
            "pickup_timestamp": details.get("pickup_timestamp"),
            "delivery_verified": details.get("delivery_gps_check") == "valid",
            "delivery_distance_meters": details.get("delivery_distance_meters"),
            "delivery_timestamp": details.get("delivery_timestamp"),
            "transit_minutes": details.get("transit_minutes"),
            "signature_obtained": details.get("has_signature", False),
            "recipient_name": evidence.get("recipient_name"),
            "delivery_notes": evidence.get("delivery_notes"),
        }
