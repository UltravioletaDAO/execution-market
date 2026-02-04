"""
Execution Market Mystery Shopping Task Type

Task type for mystery shopping/experience testing:
- Retail experience evaluation
- Restaurant/service quality assessment
- Compliance checking
- Customer service evaluation

Evidence requirements:
- Receipt proving purchase
- Photos of location/experience
- Completed evaluation questionnaire

Validation includes:
- Receipt matches task location/date
- Photos verify presence
- Questionnaire fully completed
- Logical consistency in responses
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


class EvaluationCategory(str, Enum):
    """Categories for mystery shop evaluation."""
    CLEANLINESS = "cleanliness"
    SERVICE = "service"
    PRODUCT_QUALITY = "product_quality"
    WAIT_TIME = "wait_time"
    STAFF_KNOWLEDGE = "staff_knowledge"
    ATMOSPHERE = "atmosphere"
    PRICE_VALUE = "price_value"
    COMPLIANCE = "compliance"
    SAFETY = "safety"


class RatingScale(str, Enum):
    """Rating scale options."""
    SCALE_1_5 = "1-5"
    SCALE_1_10 = "1-10"
    YES_NO = "yes_no"
    EXCELLENT_POOR = "excellent_poor"


@dataclass
class EvaluationCriterion:
    """
    A single evaluation criterion for mystery shopping.

    Attributes:
        name: Criterion identifier
        label: Human-readable label
        category: Category of evaluation
        scale: Rating scale to use
        weight: Importance weight (0-1)
        required: Whether this criterion is required
        description: Detailed description of what to evaluate
    """
    name: str
    label: str
    category: EvaluationCategory
    scale: RatingScale = RatingScale.SCALE_1_5
    weight: float = 1.0
    required: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "label": self.label,
            "category": self.category.value,
            "scale": self.scale.value,
            "weight": self.weight,
            "required": self.required,
            "description": self.description,
        }


class MysteryShopEvidence(TypedDict, total=False):
    """Evidence structure for mystery shop tasks."""
    # Receipt evidence
    receipt_photo_url: str
    receipt_date: str
    receipt_amount: float
    receipt_store_name: Optional[str]
    receipt_items: Optional[List[str]]

    # Location evidence
    location_photos: List[str]
    location_gps_lat: Optional[float]
    location_gps_lng: Optional[float]
    visit_timestamp: str

    # Questionnaire responses
    ratings: Dict[str, int]         # criterion_name -> rating value
    comments: Dict[str, str]        # criterion_name -> text comment
    overall_rating: int
    overall_comments: str

    # Additional evidence
    staff_interaction_notes: Optional[str]
    issues_noted: Optional[List[str]]
    recommendations: Optional[str]


@dataclass
class MysteryShopConfig:
    """Configuration for mystery shop validation."""
    # Receipt validation
    require_receipt: bool = True
    max_receipt_age_days: int = 1
    min_purchase_amount: Optional[float] = None
    max_purchase_amount: Optional[float] = None

    # Location validation
    require_gps: bool = True
    gps_radius_meters: float = 500.0
    require_photos: bool = True
    min_photos: int = 2

    # Questionnaire validation
    require_all_ratings: bool = True
    require_comments: bool = False
    min_comment_length: int = 10

    # Timing
    min_visit_duration_minutes: int = 10
    max_visit_duration_hours: int = 2


class MysteryShopTask(TaskType[MysteryShopEvidence]):
    """
    Task type for mystery shopping.

    Handles validation of mystery shop evidence including receipt
    verification, location confirmation, and questionnaire completion.

    Examples:
    - "Evaluate customer service at Store X"
    - "Check compliance at Restaurant Y"
    - "Rate shopping experience at Location Z"
    """

    type_name = "mystery_shop"
    display_name = "Mystery Shopping"
    description = "Experience evaluation with receipt, photos, and questionnaire"
    category = "physical_presence"

    # Base pricing
    BASE_BOUNTY = Decimal("15.00")
    MAX_BOUNTY = Decimal("75.00")

    # Time estimates
    BASE_TIME = 45
    MAX_TIME = 180

    # Default evaluation criteria
    DEFAULT_CRITERIA = [
        EvaluationCriterion(
            name="greeting",
            label="Staff Greeting",
            category=EvaluationCategory.SERVICE,
            description="Were you greeted promptly and warmly?",
        ),
        EvaluationCriterion(
            name="cleanliness",
            label="Store Cleanliness",
            category=EvaluationCategory.CLEANLINESS,
            description="Was the location clean and well-maintained?",
        ),
        EvaluationCriterion(
            name="wait_time",
            label="Wait Time",
            category=EvaluationCategory.WAIT_TIME,
            description="Was the wait time reasonable?",
        ),
        EvaluationCriterion(
            name="staff_knowledge",
            label="Staff Knowledge",
            category=EvaluationCategory.STAFF_KNOWLEDGE,
            description="Did staff demonstrate good product knowledge?",
        ),
        EvaluationCriterion(
            name="checkout",
            label="Checkout Experience",
            category=EvaluationCategory.SERVICE,
            description="Was the checkout process smooth?",
        ),
    ]

    def __init__(
        self,
        criteria: Optional[List[EvaluationCriterion]] = None,
        config: Optional[MysteryShopConfig] = None,
        target_store: Optional[str] = None,
        reimbursement_amount: Optional[Decimal] = None,
    ):
        """
        Initialize mystery shop task type.

        Args:
            criteria: Evaluation criteria (uses defaults if not provided)
            config: Validation configuration
            target_store: Name of the store to evaluate
            reimbursement_amount: Amount to reimburse for required purchase
        """
        super().__init__()
        self.criteria = criteria or self.DEFAULT_CRITERIA
        self.config = config or MysteryShopConfig()
        self.target_store = target_store
        self.reimbursement_amount = reimbursement_amount

    def get_required_evidence(self) -> List[EvidenceSpec]:
        """Get required evidence for mystery shop task."""
        evidence = []

        # Receipt
        if self.config.require_receipt:
            evidence.append(
                EvidenceSpec(
                    category=EvidenceCategory.RECEIPT,
                    required=True,
                    description="Receipt from your purchase at the target location",
                    validation_rules={
                        "max_age_days": self.config.max_receipt_age_days,
                        "min_amount": self.config.min_purchase_amount,
                        "max_amount": self.config.max_purchase_amount,
                    },
                )
            )

        # Location photos
        if self.config.require_photos:
            evidence.append(
                EvidenceSpec(
                    category=EvidenceCategory.PHOTO_GEO,
                    required=True,
                    description="Photos of the location (entrance, interior, etc.)",
                    validation_rules={
                        "max_distance_meters": self.config.gps_radius_meters,
                    },
                    min_count=self.config.min_photos,
                    max_count=10,
                )
            )

        # Questionnaire
        evidence.append(
            EvidenceSpec(
                category=EvidenceCategory.QUESTIONNAIRE,
                required=True,
                description="Complete the evaluation questionnaire",
                validation_rules={
                    "criteria": [c.to_dict() for c in self.criteria],
                    "require_all": self.config.require_all_ratings,
                    "require_comments": self.config.require_comments,
                },
            )
        )

        return evidence

    def get_optional_evidence(self) -> List[EvidenceSpec]:
        """Get optional evidence for mystery shop task."""
        return [
            EvidenceSpec(
                category=EvidenceCategory.VIDEO,
                required=False,
                description="Short video of the experience (discreet)",
                validation_rules={"max_duration_seconds": 60},
            ),
            EvidenceSpec(
                category=EvidenceCategory.TEXT_RESPONSE,
                required=False,
                description="Additional observations and recommendations",
            ),
        ]

    def validate_evidence(
        self,
        evidence: MysteryShopEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """
        Validate mystery shop evidence.

        Checks:
        1. Receipt is valid and matches location
        2. Photos verify presence at location
        3. Questionnaire is complete
        4. Responses are logically consistent
        """
        result = ValidationResult.success()

        # 1. Validate receipt
        if self.config.require_receipt:
            receipt_result = self._validate_receipt(evidence)
            result = result.merge(receipt_result)

        # 2. Validate location/photos
        if self.config.require_photos and context.has_location():
            location_result = self._validate_location(evidence, context)
            result = result.merge(location_result)

        # 3. Validate questionnaire
        questionnaire_result = self._validate_questionnaire(evidence)
        result = result.merge(questionnaire_result)

        # 4. Check logical consistency
        consistency_result = self._validate_consistency(evidence)
        result = result.merge(consistency_result)

        return result

    def _validate_receipt(
        self,
        evidence: MysteryShopEvidence,
    ) -> ValidationResult:
        """Validate receipt evidence."""
        # Check receipt photo exists
        if not evidence.get("receipt_photo_url"):
            return ValidationResult.failure(
                errors=["Receipt photo required but not provided"],
            )

        # Validate receipt date
        receipt_date_str = evidence.get("receipt_date")
        if receipt_date_str:
            try:
                if receipt_date_str.endswith("Z"):
                    receipt_date_str = receipt_date_str[:-1] + "+00:00"
                receipt_date = datetime.fromisoformat(receipt_date_str)

                if receipt_date.tzinfo:
                    receipt_date = receipt_date.replace(tzinfo=None)

                max_age = timedelta(days=self.config.max_receipt_age_days)
                if datetime.utcnow() - receipt_date > max_age:
                    return ValidationResult.failure(
                        errors=[
                            f"Receipt is too old (max: {self.config.max_receipt_age_days} days)"
                        ],
                    )

            except (ValueError, TypeError):
                return ValidationResult.warning(
                    warnings=["Could not verify receipt date"],
                )

        # Validate purchase amount
        receipt_amount = evidence.get("receipt_amount")
        if receipt_amount is not None:
            if self.config.min_purchase_amount and receipt_amount < self.config.min_purchase_amount:
                return ValidationResult.failure(
                    errors=[
                        f"Purchase amount (${receipt_amount:.2f}) below minimum "
                        f"(${self.config.min_purchase_amount:.2f})"
                    ],
                )

            if self.config.max_purchase_amount and receipt_amount > self.config.max_purchase_amount:
                return ValidationResult.failure(
                    errors=[
                        f"Purchase amount (${receipt_amount:.2f}) exceeds maximum "
                        f"(${self.config.max_purchase_amount:.2f})"
                    ],
                )

        # Validate store name matches (if target store specified)
        if self.target_store and evidence.get("receipt_store_name"):
            receipt_store = evidence["receipt_store_name"].lower()
            target = self.target_store.lower()

            # Simple fuzzy match - check if target is contained in receipt store name
            if target not in receipt_store and receipt_store not in target:
                return ValidationResult.warning(
                    warnings=[
                        f"Receipt store '{evidence['receipt_store_name']}' "
                        f"may not match target '{self.target_store}'"
                    ],
                )

        return ValidationResult.success(
            details={
                "receipt_validated": True,
                "receipt_amount": receipt_amount,
                "receipt_date": receipt_date_str,
            },
        )

    def _validate_location(
        self,
        evidence: MysteryShopEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """Validate location evidence."""
        # Check photos exist
        photos = evidence.get("location_photos", [])
        if len(photos) < self.config.min_photos:
            return ValidationResult.failure(
                errors=[
                    f"At least {self.config.min_photos} photos required, "
                    f"got {len(photos)}"
                ],
            )

        # Validate GPS if available
        if self.config.require_gps:
            lat = evidence.get("location_gps_lat")
            lng = evidence.get("location_gps_lng")

            if lat is None or lng is None:
                return ValidationResult.warning(
                    warnings=["GPS coordinates not provided"],
                )

            if context.location_lat and context.location_lng:
                distance = self._haversine_distance(
                    lat, lng,
                    context.location_lat, context.location_lng,
                )

                if distance > self.config.gps_radius_meters:
                    return ValidationResult.failure(
                        errors=[
                            f"Location ({distance:.0f}m) outside acceptable radius "
                            f"({self.config.gps_radius_meters}m)"
                        ],
                    )

                return ValidationResult.success(
                    details={
                        "location_verified": True,
                        "distance_meters": distance,
                        "photos_count": len(photos),
                    },
                )

        return ValidationResult.success(
            details={
                "photos_count": len(photos),
            },
        )

    def _validate_questionnaire(
        self,
        evidence: MysteryShopEvidence,
    ) -> ValidationResult:
        """Validate questionnaire responses."""
        ratings = evidence.get("ratings", {})
        comments = evidence.get("comments", {})
        errors = []
        warnings = []

        # Check required criteria
        for criterion in self.criteria:
            if criterion.required and self.config.require_all_ratings:
                if criterion.name not in ratings:
                    errors.append(f"Missing rating for: {criterion.label}")
                else:
                    # Validate rating is in valid range
                    rating = ratings[criterion.name]
                    if not self._is_valid_rating(rating, criterion.scale):
                        errors.append(
                            f"Invalid rating for {criterion.label}: {rating}"
                        )

            # Check comments if required
            if self.config.require_comments:
                comment = comments.get(criterion.name, "")
                if len(comment) < self.config.min_comment_length:
                    warnings.append(
                        f"Comment for {criterion.label} is too short "
                        f"(min: {self.config.min_comment_length} chars)"
                    )

        # Check overall rating
        if evidence.get("overall_rating") is None:
            errors.append("Missing overall rating")

        if errors:
            return ValidationResult.failure(errors=errors)
        elif warnings:
            return ValidationResult.warning(warnings=warnings)

        return ValidationResult.success(
            details={
                "ratings_complete": True,
                "ratings_count": len(ratings),
                "has_comments": bool(comments),
            },
        )

    def _is_valid_rating(self, rating: Any, scale: RatingScale) -> bool:
        """Check if rating is valid for the given scale."""
        try:
            if scale == RatingScale.SCALE_1_5:
                return 1 <= int(rating) <= 5
            elif scale == RatingScale.SCALE_1_10:
                return 1 <= int(rating) <= 10
            elif scale == RatingScale.YES_NO:
                return rating in [True, False, "yes", "no", 1, 0]
            elif scale == RatingScale.EXCELLENT_POOR:
                valid = ["excellent", "good", "average", "poor", "very_poor"]
                return str(rating).lower() in valid
            return False
        except (ValueError, TypeError):
            return False

    def _validate_consistency(
        self,
        evidence: MysteryShopEvidence,
    ) -> ValidationResult:
        """Check logical consistency of responses."""
        ratings = evidence.get("ratings", {})
        overall = evidence.get("overall_rating")
        warnings = []

        if not ratings or overall is None:
            return ValidationResult.success()

        # Calculate average of individual ratings (normalized to 1-5)
        normalized_ratings = []
        for criterion in self.criteria:
            if criterion.name in ratings:
                rating = ratings[criterion.name]
                if criterion.scale == RatingScale.SCALE_1_10:
                    normalized = (rating - 1) / 9 * 4 + 1  # Convert to 1-5
                elif criterion.scale == RatingScale.YES_NO:
                    normalized = 5 if rating in [True, "yes", 1] else 1
                else:
                    normalized = rating
                normalized_ratings.append(normalized * criterion.weight)

        if normalized_ratings:
            avg_rating = sum(normalized_ratings) / len(normalized_ratings)

            # Check if overall rating is significantly different from average
            # Allow 1.5 points difference
            if abs(overall - avg_rating) > 1.5:
                warnings.append(
                    f"Overall rating ({overall}) differs significantly from "
                    f"individual ratings average ({avg_rating:.1f})"
                )

        if warnings:
            return ValidationResult.warning(
                warnings=warnings,
                details={"consistency_check": "warning"},
            )

        return ValidationResult.success(
            details={"consistency_check": "passed"},
        )

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate distance between two points."""
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
        """Get bounty recommendation for mystery shop task."""
        base = self.BASE_BOUNTY

        # Criteria count factor
        criteria_count = len(self.criteria)
        criteria_bonus = Decimal(str(max(0, criteria_count - 5))) * Decimal("1.00")

        # Complexity factor
        complexity_factor = Decimal(str(1 + (complexity - 1) * 0.25))

        # Reimbursement (added on top)
        reimbursement = self.reimbursement_amount or Decimal("0")

        # Urgency factor
        urgency_factors = {
            "flexible": Decimal("0.9"),
            "normal": Decimal("1.0"),
            "urgent": Decimal("1.4"),
        }
        urgency_factor = urgency_factors.get(context.urgency, Decimal("1.0"))

        suggested = (base + criteria_bonus) * complexity_factor * urgency_factor + reimbursement
        suggested = min(suggested, self.MAX_BOUNTY + reimbursement).quantize(Decimal("1.00"))

        return BountyRecommendation(
            min_usd=base + reimbursement,
            max_usd=self.MAX_BOUNTY + reimbursement,
            suggested_usd=suggested,
            factors={
                "base": base,
                "criteria_count": Decimal(str(criteria_count)),
                "criteria_bonus": criteria_bonus,
                "complexity": complexity_factor,
                "reimbursement": reimbursement,
                "urgency": urgency_factor,
            },
            reasoning=f"Base ${base} + {criteria_count} criteria, reimbursement ${reimbursement}",
        )

    def get_time_estimate(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> TimeEstimate:
        """Get time estimate for mystery shop task."""
        base = self.BASE_TIME

        # More criteria = more time
        criteria_count = len(self.criteria)
        criteria_time = criteria_count * 3  # ~3 min per criterion

        typical = base + criteria_time

        # Complexity factor
        complexity_factor = 1 + (complexity - 1) * 0.2
        typical = int(typical * complexity_factor)
        typical = min(typical, self.MAX_TIME)

        return TimeEstimate(
            min_minutes=int(typical * 0.6),
            max_minutes=int(typical * 2),
            typical_minutes=typical,
            factors={
                "base_minutes": base,
                "criteria_count": criteria_count,
                "criteria_time": criteria_time,
                "complexity": complexity,
            },
        )

    def get_instructions_template(self) -> str:
        """Get instruction template for mystery shop task."""
        return """
## Mystery Shopping Task

Visit {store_name} and evaluate the experience as a regular customer.

### Important: Act Like a Regular Customer
- Do NOT identify yourself as a mystery shopper
- Make a genuine purchase (you will be reimbursed)
- Observe naturally without drawing attention

### Your Visit:
1. Enter the store and note first impressions
2. Browse products/services naturally
3. Interact with staff (ask questions)
4. Make a purchase
5. Complete checkout
6. Note your overall experience

### Evidence Required:
1. **Receipt** - Photo of your receipt
2. **Location Photos** - At least {min_photos} photos showing:
   - Store entrance/signage
   - Interior (discreetly)
   - Your purchase
3. **Questionnaire** - Complete all evaluation criteria

### Evaluation Criteria:
{criteria_list}

### Reimbursement:
Purchase up to ${max_purchase} - you will be reimbursed upon approval.
Keep your receipt!

### Deadline:
{deadline}

### Tips:
- Visit during normal business hours
- Spend 15-30 minutes minimum
- Be objective in your ratings
- Provide specific examples in comments
        """.strip()

    def post_process(
        self,
        evidence: MysteryShopEvidence,
        validation_result: ValidationResult,
        context: TaskContext,
    ) -> Dict[str, Any]:
        """Extract structured data from mystery shop evidence."""
        ratings = evidence.get("ratings", {})

        # Calculate category scores
        category_scores = {}
        for criterion in self.criteria:
            if criterion.name in ratings:
                category = criterion.category.value
                if category not in category_scores:
                    category_scores[category] = []
                category_scores[category].append(ratings[criterion.name])

        # Average by category
        category_averages = {
            cat: sum(scores) / len(scores)
            for cat, scores in category_scores.items()
        }

        return {
            "store_name": evidence.get("receipt_store_name") or self.target_store,
            "visit_date": evidence.get("visit_timestamp") or evidence.get("receipt_date"),
            "purchase_amount": evidence.get("receipt_amount"),
            "overall_rating": evidence.get("overall_rating"),
            "category_scores": category_averages,
            "individual_ratings": ratings,
            "comments": evidence.get("comments", {}),
            "overall_comments": evidence.get("overall_comments"),
            "issues_noted": evidence.get("issues_noted", []),
            "recommendations": evidence.get("recommendations"),
            "photos_count": len(evidence.get("location_photos", [])),
        }


# Factory functions for common mystery shop types
def create_retail_mystery_shop(
    store_name: str,
    focus_areas: Optional[List[EvaluationCategory]] = None,
    max_purchase: Decimal = Decimal("25.00"),
) -> MysteryShopTask:
    """Create a retail mystery shop evaluation."""
    criteria = []

    if not focus_areas:
        focus_areas = [
            EvaluationCategory.SERVICE,
            EvaluationCategory.CLEANLINESS,
            EvaluationCategory.PRODUCT_QUALITY,
        ]

    if EvaluationCategory.SERVICE in focus_areas:
        criteria.extend([
            EvaluationCriterion(
                name="greeting",
                label="Initial Greeting",
                category=EvaluationCategory.SERVICE,
                description="Were you acknowledged within 30 seconds of entering?",
            ),
            EvaluationCriterion(
                name="assistance",
                label="Staff Assistance",
                category=EvaluationCategory.SERVICE,
                description="Did staff offer help and answer questions?",
            ),
            EvaluationCriterion(
                name="checkout",
                label="Checkout Experience",
                category=EvaluationCategory.SERVICE,
                description="Was checkout efficient and pleasant?",
            ),
        ])

    if EvaluationCategory.CLEANLINESS in focus_areas:
        criteria.extend([
            EvaluationCriterion(
                name="store_clean",
                label="Store Cleanliness",
                category=EvaluationCategory.CLEANLINESS,
                description="Overall cleanliness of the store",
            ),
            EvaluationCriterion(
                name="restroom",
                label="Restroom Condition",
                category=EvaluationCategory.CLEANLINESS,
                required=False,
                description="If visited, rate restroom cleanliness",
            ),
        ])

    if EvaluationCategory.PRODUCT_QUALITY in focus_areas:
        criteria.extend([
            EvaluationCriterion(
                name="product_display",
                label="Product Display",
                category=EvaluationCategory.PRODUCT_QUALITY,
                description="Were products well-organized and displayed?",
            ),
            EvaluationCriterion(
                name="stock_levels",
                label="Stock Levels",
                category=EvaluationCategory.PRODUCT_QUALITY,
                description="Were shelves well-stocked?",
            ),
        ])

    return MysteryShopTask(
        criteria=criteria,
        config=MysteryShopConfig(
            require_receipt=True,
            max_purchase_amount=float(max_purchase),
            min_photos=3,
        ),
        target_store=store_name,
        reimbursement_amount=max_purchase,
    )


def create_restaurant_mystery_shop(
    restaurant_name: str,
    max_purchase: Decimal = Decimal("40.00"),
) -> MysteryShopTask:
    """Create a restaurant mystery shop evaluation."""
    criteria = [
        EvaluationCriterion(
            name="seating",
            label="Seating/Wait Time",
            category=EvaluationCategory.WAIT_TIME,
            description="How long did you wait to be seated?",
        ),
        EvaluationCriterion(
            name="server_greeting",
            label="Server Greeting",
            category=EvaluationCategory.SERVICE,
            description="Were you greeted promptly by your server?",
        ),
        EvaluationCriterion(
            name="order_accuracy",
            label="Order Accuracy",
            category=EvaluationCategory.SERVICE,
            description="Was your order taken and delivered correctly?",
        ),
        EvaluationCriterion(
            name="food_quality",
            label="Food Quality",
            category=EvaluationCategory.PRODUCT_QUALITY,
            description="Rate the taste and presentation of your food",
        ),
        EvaluationCriterion(
            name="food_temp",
            label="Food Temperature",
            category=EvaluationCategory.PRODUCT_QUALITY,
            description="Was food served at proper temperature?",
        ),
        EvaluationCriterion(
            name="cleanliness",
            label="Restaurant Cleanliness",
            category=EvaluationCategory.CLEANLINESS,
            description="Overall cleanliness (tables, floors, restrooms)",
        ),
        EvaluationCriterion(
            name="atmosphere",
            label="Atmosphere",
            category=EvaluationCategory.ATMOSPHERE,
            description="Ambiance, noise level, comfort",
        ),
        EvaluationCriterion(
            name="value",
            label="Value for Money",
            category=EvaluationCategory.PRICE_VALUE,
            description="Did the experience match the price?",
        ),
    ]

    return MysteryShopTask(
        criteria=criteria,
        config=MysteryShopConfig(
            require_receipt=True,
            max_purchase_amount=float(max_purchase),
            min_photos=3,
            min_visit_duration_minutes=30,
        ),
        target_store=restaurant_name,
        reimbursement_amount=max_purchase,
    )
