"""
Execution Market Recon - Observation Tasks

Implements task types for observation/reconnaissance tasks:
- Store checks ("Is Walmart open right now?")
- Crowd counts ("How many people in line at DMV?")
- Price checks ("What's the price of X at store Y?")
- Availability checks ("Is product X available at store Y?")
- Condition reports ("What's the condition of X?")

These are low-cost, high-volume tasks ($0.25 - $5) perfect for bootstrap phase.

NOW-131: Task type tiers (Tier 1 $1-5, Tier 2 $10-30, Tier 3 $50-500)
NOW-132: Execution Market Recon observation tasks
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4


class TaskTier(Enum):
    """
    Task pricing tiers based on complexity and requirements.

    SIMPLE (Tier 1): Low barrier, high volume tasks ($1-5)
        - Quick observations
        - Single photo evidence
        - No special skills required

    STANDARD (Tier 2): Medium barrier tasks ($10-30)
        - Detailed inspections
        - Multiple evidence types
        - May require specific location/time

    PREMIUM (Tier 3): High barrier tasks ($50-500)
        - Professional-level work
        - Complex multi-step verification
        - May require credentials or special access
    """

    SIMPLE = "simple"  # $1-5
    STANDARD = "standard"  # $10-30
    PREMIUM = "premium"  # $50-500

    @property
    def min_bounty(self) -> Decimal:
        """Minimum bounty for this tier."""
        return {
            TaskTier.SIMPLE: Decimal("1.00"),
            TaskTier.STANDARD: Decimal("10.00"),
            TaskTier.PREMIUM: Decimal("50.00"),
        }[self]

    @property
    def max_bounty(self) -> Decimal:
        """Maximum bounty for this tier."""
        return {
            TaskTier.SIMPLE: Decimal("5.00"),
            TaskTier.STANDARD: Decimal("30.00"),
            TaskTier.PREMIUM: Decimal("500.00"),
        }[self]

    @property
    def typical_duration_minutes(self) -> int:
        """Typical time to complete task in this tier."""
        return {
            TaskTier.SIMPLE: 5,
            TaskTier.STANDARD: 30,
            TaskTier.PREMIUM: 120,
        }[self]


class ReconTaskType(Enum):
    """
    Types of reconnaissance/observation tasks.

    Each type has specific evidence requirements and bounty ranges.
    """

    STORE_CHECK = "store_check"  # Is store open? What are hours?
    CROWD_COUNT = "crowd_count"  # How many people in line/area?
    PRICE_CHECK = "price_check"  # What's the price of item(s)?
    AVAILABILITY = "availability"  # Is product X in stock?
    CONDITION_REPORT = "condition_report"  # What's the condition of X?

    @property
    def default_tier(self) -> TaskTier:
        """Default tier for this task type."""
        return {
            ReconTaskType.STORE_CHECK: TaskTier.SIMPLE,
            ReconTaskType.CROWD_COUNT: TaskTier.SIMPLE,
            ReconTaskType.PRICE_CHECK: TaskTier.SIMPLE,
            ReconTaskType.AVAILABILITY: TaskTier.SIMPLE,
            ReconTaskType.CONDITION_REPORT: TaskTier.STANDARD,
        }[self]

    @property
    def description(self) -> str:
        """Human-readable description of task type."""
        return {
            ReconTaskType.STORE_CHECK: "Verify store status (open/closed, hours, etc.)",
            ReconTaskType.CROWD_COUNT: "Count people, vehicles, or items in an area",
            ReconTaskType.PRICE_CHECK: "Check and report prices of specific items",
            ReconTaskType.AVAILABILITY: "Verify if a product is available/in stock",
            ReconTaskType.CONDITION_REPORT: "Document the condition of a location or item",
        }[self]


class EvidenceType(Enum):
    """Types of evidence that can be required or accepted."""

    PHOTO = "photo"  # Single photo
    PHOTO_GEO = "photo_geo"  # Photo with GPS coordinates
    PHOTO_TIMESTAMP = "photo_timestamp"  # Photo with timestamp verification
    VIDEO = "video"  # Video recording
    TEXT_RESPONSE = "text_response"  # Written answer
    NUMERIC_VALUE = "numeric_value"  # Number (count, price, etc.)
    SCREENSHOT = "screenshot"  # Screenshot (for online prices)
    RECEIPT = "receipt"  # Receipt or printed document


@dataclass
class EvidenceRequirement:
    """
    Specifies what evidence is required for a task.

    Attributes:
        evidence_type: Type of evidence required
        required: Whether this evidence is mandatory
        description: Instructions for capturing this evidence
        validation_rules: Rules for validating the evidence
    """

    evidence_type: EvidenceType
    required: bool = True
    description: str = ""
    validation_rules: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "evidence_type": self.evidence_type.value,
            "required": self.required,
            "description": self.description,
            "validation_rules": self.validation_rules,
        }


@dataclass
class Location:
    """
    Geographic location for a task.

    Attributes:
        latitude: GPS latitude
        longitude: GPS longitude
        address: Human-readable address
        radius_meters: Acceptable radius from coordinates
        place_name: Name of the place (store name, etc.)
    """

    latitude: float
    longitude: float
    address: str = ""
    radius_meters: float = 100.0
    place_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "radius_meters": self.radius_meters,
            "place_name": self.place_name,
        }


@dataclass
class BountySuggestion:
    """
    Suggested bounty amount with reasoning.

    Attributes:
        amount: Suggested bounty in USD
        tier: The tier this bounty falls into
        reasoning: Explanation of how bounty was calculated
        factors: Individual factors that influenced the bounty
    """

    amount: Decimal
    tier: TaskTier
    reasoning: str
    factors: Dict[str, Decimal] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "amount": str(self.amount),
            "tier": self.tier.value,
            "reasoning": self.reasoning,
            "factors": {k: str(v) for k, v in self.factors.items()},
        }


@dataclass
class ReconTask:
    """
    A reconnaissance/observation task.

    Attributes:
        id: Unique task identifier
        task_type: Type of recon task
        tier: Pricing tier
        title: Short task title
        instructions: Detailed instructions for worker
        location: Where the task must be performed
        questions: Specific questions to answer
        evidence_requirements: What evidence is needed
        bounty_usd: Payment amount in USD
        deadline: When task must be completed
        created_at: When task was created
        metadata: Additional task-specific data
    """

    id: str
    task_type: ReconTaskType
    tier: TaskTier
    title: str
    instructions: str
    location: Optional[Location]
    questions: List[str]
    evidence_requirements: List[EvidenceRequirement]
    bounty_usd: Decimal
    deadline: datetime
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "tier": self.tier.value,
            "title": self.title,
            "instructions": self.instructions,
            "location": self.location.to_dict() if self.location else None,
            "questions": self.questions,
            "evidence_requirements": [e.to_dict() for e in self.evidence_requirements],
            "bounty_usd": str(self.bounty_usd),
            "deadline": self.deadline.isoformat(),
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate task configuration.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate bounty is within tier range
        if self.bounty_usd < self.tier.min_bounty:
            errors.append(
                f"Bounty ${self.bounty_usd} is below tier minimum ${self.tier.min_bounty}"
            )
        if self.bounty_usd > self.tier.max_bounty:
            errors.append(
                f"Bounty ${self.bounty_usd} exceeds tier maximum ${self.tier.max_bounty}"
            )

        # Validate deadline is in the future
        if self.deadline <= datetime.utcnow():
            errors.append("Deadline must be in the future")

        # Validate at least one question
        if not self.questions:
            errors.append("At least one question is required")

        # Validate at least one required evidence
        required_evidence = [e for e in self.evidence_requirements if e.required]
        if not required_evidence:
            errors.append("At least one required evidence type is needed")

        # Location required for geo-tagged evidence
        geo_evidence = [
            e
            for e in self.evidence_requirements
            if e.evidence_type == EvidenceType.PHOTO_GEO and e.required
        ]
        if geo_evidence and not self.location:
            errors.append(
                "Location is required when geo-tagged photo evidence is needed"
            )

        return len(errors) == 0, errors


class ReconTaskFactory:
    """
    Factory for creating Recon tasks with sensible defaults.

    Provides methods for common task types with appropriate
    evidence requirements and bounty suggestions.
    """

    # Location complexity factors for bounty calculation
    LOCATION_FACTORS = {
        "urban_core": Decimal("1.0"),  # Dense urban area
        "urban": Decimal("1.1"),  # Regular urban
        "suburban": Decimal("1.2"),  # Suburban area
        "rural": Decimal("1.5"),  # Rural/hard to reach
        "remote": Decimal("2.0"),  # Very remote
    }

    # Time-of-day factors
    TIME_FACTORS = {
        "business_hours": Decimal("1.0"),  # 9am-5pm weekdays
        "evening": Decimal("1.1"),  # 5pm-9pm
        "night": Decimal("1.3"),  # 9pm-6am
        "weekend": Decimal("1.1"),  # Sat-Sun
        "holiday": Decimal("1.5"),  # Major holidays
    }

    # Base bounties by task type (in USD)
    BASE_BOUNTIES = {
        ReconTaskType.STORE_CHECK: Decimal("1.50"),
        ReconTaskType.CROWD_COUNT: Decimal("2.00"),
        ReconTaskType.PRICE_CHECK: Decimal("2.50"),
        ReconTaskType.AVAILABILITY: Decimal("2.00"),
        ReconTaskType.CONDITION_REPORT: Decimal("5.00"),
    }

    @classmethod
    def create_store_check(
        cls,
        location: Location,
        store_name: str,
        questions: Optional[List[str]] = None,
        deadline_hours: int = 4,
        bounty_override: Optional[Decimal] = None,
        location_type: str = "urban",
    ) -> ReconTask:
        """
        Create a store check task.

        Example: "Is Walmart open right now?"

        Args:
            location: Store location
            store_name: Name of the store
            questions: Specific questions (default: open/closed + hours)
            deadline_hours: Hours until deadline
            bounty_override: Override suggested bounty
            location_type: Type of area (urban, suburban, rural, etc.)

        Returns:
            Configured ReconTask
        """
        default_questions = [
            f"Is {store_name} currently open?",
            "What are the posted business hours?",
            "Is there anything unusual (renovations, special hours, etc.)?",
        ]

        evidence_requirements = [
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO_GEO,
                required=True,
                description=f"Take a photo of {store_name}'s entrance showing if open/closed",
                validation_rules={
                    "max_distance_meters": location.radius_meters,
                    "max_age_minutes": 15,
                },
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO,
                required=True,
                description="Photo of posted business hours",
                validation_rules={"max_age_minutes": 15},
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.TEXT_RESPONSE,
                required=True,
                description="Answer the questions about the store status",
            ),
        ]

        bounty = (
            bounty_override
            or cls.suggest_bounty(
                task_type=ReconTaskType.STORE_CHECK,
                location_type=location_type,
                question_count=len(questions or default_questions),
            ).amount
        )

        location.place_name = store_name

        return ReconTask(
            id=str(uuid4()),
            task_type=ReconTaskType.STORE_CHECK,
            tier=TaskTier.SIMPLE,
            title=f"Check if {store_name} is open",
            instructions=f"""
Visit {store_name} at the specified location and verify:
1. Whether the store is currently open or closed
2. What the posted business hours are
3. Any unusual conditions (renovations, special hours, temporary closure)

Take clear photos of:
- The store entrance (showing if doors are open/locked)
- The posted hours sign

Answer all questions based on what you observe.
            """.strip(),
            location=location,
            questions=questions or default_questions,
            evidence_requirements=evidence_requirements,
            bounty_usd=bounty,
            deadline=datetime.utcnow() + timedelta(hours=deadline_hours),
            metadata={
                "store_name": store_name,
                "location_type": location_type,
            },
        )

    @classmethod
    def create_crowd_count(
        cls,
        location: Location,
        count_what: str,
        specific_area: str = "",
        deadline_hours: int = 2,
        bounty_override: Optional[Decimal] = None,
        location_type: str = "urban",
    ) -> ReconTask:
        """
        Create a crowd/item counting task.

        Example: "How many people in line at DMV?"

        Args:
            location: Where to count
            count_what: What to count (people, cars, items, etc.)
            specific_area: Specific area description (e.g., "in the main line")
            deadline_hours: Hours until deadline
            bounty_override: Override suggested bounty
            location_type: Type of area

        Returns:
            Configured ReconTask
        """
        area_desc = f" {specific_area}" if specific_area else ""

        questions = [
            f"How many {count_what} did you count{area_desc}?",
            "What time did you make this observation?",
            "Were there any notable conditions (weather, event, etc.)?",
        ]

        evidence_requirements = [
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO_GEO,
                required=True,
                description=f"Photo showing the {count_what}{area_desc}",
                validation_rules={
                    "max_distance_meters": location.radius_meters,
                    "max_age_minutes": 10,
                },
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO_TIMESTAMP,
                required=True,
                description="Additional photo with visible timestamp context",
                validation_rules={"max_age_minutes": 10},
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.NUMERIC_VALUE,
                required=True,
                description=f"The count of {count_what}",
                validation_rules={"min_value": 0},
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.TEXT_RESPONSE,
                required=True,
                description="Brief description of what you observed",
            ),
        ]

        bounty = (
            bounty_override
            or cls.suggest_bounty(
                task_type=ReconTaskType.CROWD_COUNT,
                location_type=location_type,
                question_count=len(questions),
            ).amount
        )

        return ReconTask(
            id=str(uuid4()),
            task_type=ReconTaskType.CROWD_COUNT,
            tier=TaskTier.SIMPLE,
            title=f"Count {count_what} at {location.place_name or location.address}",
            instructions=f"""
Go to the specified location and count the {count_what}{area_desc}.

Steps:
1. Arrive at the location
2. Take a clear photo showing the {count_what}
3. Count carefully - take your time
4. Record the exact count
5. Note the time and any relevant conditions

Tips for accurate counting:
- Count in sections if there are many
- Take multiple photos if needed
- Note if count is changing rapidly
            """.strip(),
            location=location,
            questions=questions,
            evidence_requirements=evidence_requirements,
            bounty_usd=bounty,
            deadline=datetime.utcnow() + timedelta(hours=deadline_hours),
            metadata={
                "count_what": count_what,
                "specific_area": specific_area,
                "location_type": location_type,
            },
        )

    @classmethod
    def create_price_check(
        cls,
        location: Location,
        items: List[str],
        store_name: str = "",
        include_sale_prices: bool = True,
        deadline_hours: int = 6,
        bounty_override: Optional[Decimal] = None,
        location_type: str = "urban",
    ) -> ReconTask:
        """
        Create a price check task.

        Example: "What's the price of milk at Costco?"

        Args:
            location: Store location
            items: List of items to price check
            store_name: Name of the store
            include_sale_prices: Whether to check for sale prices
            deadline_hours: Hours until deadline
            bounty_override: Override suggested bounty
            location_type: Type of area

        Returns:
            Configured ReconTask
        """
        questions = [f"What is the price of {item}?" for item in items]
        if include_sale_prices:
            questions.append(
                "Are any of these items on sale? If so, what's the sale price?"
            )
        questions.append("Are all items available?")

        evidence_requirements = [
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO_GEO,
                required=True,
                description="Photo of store entrance or aisle confirming location",
                validation_rules={
                    "max_distance_meters": location.radius_meters,
                    "max_age_minutes": 30,
                },
            ),
        ]

        # Add photo requirement for each item
        for item in items:
            evidence_requirements.append(
                EvidenceRequirement(
                    evidence_type=EvidenceType.PHOTO,
                    required=True,
                    description=f"Photo of {item} showing the price tag clearly",
                    validation_rules={"max_age_minutes": 30},
                )
            )

        evidence_requirements.append(
            EvidenceRequirement(
                evidence_type=EvidenceType.TEXT_RESPONSE,
                required=True,
                description="List each item and its price",
            )
        )

        # Calculate bounty based on number of items
        base_bounty = cls.suggest_bounty(
            task_type=ReconTaskType.PRICE_CHECK,
            location_type=location_type,
            question_count=len(questions),
        ).amount

        # Add per-item bonus
        item_bonus = (
            Decimal("0.50") * (len(items) - 1) if len(items) > 1 else Decimal("0")
        )
        bounty = bounty_override or (base_bounty + item_bonus)

        location.place_name = store_name

        return ReconTask(
            id=str(uuid4()),
            task_type=ReconTaskType.PRICE_CHECK,
            tier=TaskTier.SIMPLE,
            title=f"Price check at {store_name or location.address}",
            instructions=f"""
Visit {store_name or "the store"} and find the prices for the following items:
{chr(10).join(f"- {item}" for item in items)}

For each item:
1. Locate the item on the shelf
2. Take a clear photo showing the item AND its price tag
3. Record the price (include unit price if shown)
4. Note if item is on sale

If an item is not available:
- Take a photo of where it should be
- Note "Not available" in your response
            """.strip(),
            location=location,
            questions=questions,
            evidence_requirements=evidence_requirements,
            bounty_usd=bounty,
            deadline=datetime.utcnow() + timedelta(hours=deadline_hours),
            metadata={
                "store_name": store_name,
                "items": items,
                "include_sale_prices": include_sale_prices,
                "location_type": location_type,
            },
        )

    @classmethod
    def create_availability_check(
        cls,
        location: Location,
        product: str,
        product_details: str = "",
        check_alternatives: bool = True,
        deadline_hours: int = 4,
        bounty_override: Optional[Decimal] = None,
        location_type: str = "urban",
    ) -> ReconTask:
        """
        Create a product availability check task.

        Example: "Is the PS5 available at Best Buy?"

        Args:
            location: Store location
            product: Product to check
            product_details: Additional details (SKU, variant, etc.)
            check_alternatives: Whether to check for alternatives
            deadline_hours: Hours until deadline
            bounty_override: Override suggested bounty
            location_type: Type of area

        Returns:
            Configured ReconTask
        """
        product_desc = f"{product}"
        if product_details:
            product_desc += f" ({product_details})"

        questions = [
            f"Is {product_desc} currently in stock?",
            "How many units are available (if visible)?",
            "What is the price?",
        ]
        if check_alternatives:
            questions.append(
                "If not available, are there similar alternatives in stock?"
            )

        evidence_requirements = [
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO_GEO,
                required=True,
                description=f"Photo of the {product} section/shelf",
                validation_rules={
                    "max_distance_meters": location.radius_meters,
                    "max_age_minutes": 20,
                },
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO,
                required=True,
                description=f"Photo of {product} on shelf (or empty shelf if unavailable)",
                validation_rules={"max_age_minutes": 20},
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.TEXT_RESPONSE,
                required=True,
                description="Answer all questions about availability",
            ),
        ]

        bounty = (
            bounty_override
            or cls.suggest_bounty(
                task_type=ReconTaskType.AVAILABILITY,
                location_type=location_type,
                question_count=len(questions),
            ).amount
        )

        return ReconTask(
            id=str(uuid4()),
            task_type=ReconTaskType.AVAILABILITY,
            tier=TaskTier.SIMPLE,
            title=f"Check availability of {product}",
            instructions=f"""
Visit the store and check if {product_desc} is available.

Steps:
1. Go to the appropriate section/aisle
2. Look for {product}
3. If found:
   - Take a photo showing the product on the shelf
   - Note the quantity available (if visible)
   - Record the price
4. If NOT found:
   - Take a photo of where it should be
   - Ask an employee if they have it (optional)
   - Note any similar alternatives available
            """.strip(),
            location=location,
            questions=questions,
            evidence_requirements=evidence_requirements,
            bounty_usd=bounty,
            deadline=datetime.utcnow() + timedelta(hours=deadline_hours),
            metadata={
                "product": product,
                "product_details": product_details,
                "check_alternatives": check_alternatives,
                "location_type": location_type,
            },
        )

    @classmethod
    def create_condition_report(
        cls,
        location: Location,
        subject: str,
        aspects_to_check: Optional[List[str]] = None,
        deadline_hours: int = 8,
        bounty_override: Optional[Decimal] = None,
        location_type: str = "urban",
    ) -> ReconTask:
        """
        Create a condition report task.

        Example: "What's the condition of the playground at Central Park?"

        Args:
            location: Location to inspect
            subject: What to report on
            aspects_to_check: Specific aspects to evaluate
            deadline_hours: Hours until deadline
            bounty_override: Override suggested bounty
            location_type: Type of area

        Returns:
            Configured ReconTask
        """
        default_aspects = [
            "Overall cleanliness",
            "Visible damage or wear",
            "Safety concerns",
            "Maintenance needs",
        ]
        aspects = aspects_to_check or default_aspects

        questions = [
            f"What is the overall condition of {subject}? (1-10 scale)",
        ]
        questions.extend([f"How would you rate {aspect}?" for aspect in aspects])
        questions.append("Are there any immediate concerns that should be addressed?")

        evidence_requirements = [
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO_GEO,
                required=True,
                description=f"Wide shot showing {subject} and surroundings",
                validation_rules={
                    "max_distance_meters": location.radius_meters,
                    "max_age_minutes": 30,
                },
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.PHOTO,
                required=True,
                description="Close-up photos of notable conditions (good or bad)",
                validation_rules={"max_age_minutes": 30, "min_count": 3},
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.VIDEO,
                required=False,
                description="Optional: Short video walkthrough (30-60 seconds)",
                validation_rules={"max_duration_seconds": 120},
            ),
            EvidenceRequirement(
                evidence_type=EvidenceType.TEXT_RESPONSE,
                required=True,
                description="Detailed written condition report",
            ),
        ]

        bounty = (
            bounty_override
            or cls.suggest_bounty(
                task_type=ReconTaskType.CONDITION_REPORT,
                location_type=location_type,
                question_count=len(questions),
            ).amount
        )

        return ReconTask(
            id=str(uuid4()),
            task_type=ReconTaskType.CONDITION_REPORT,
            tier=TaskTier.STANDARD,  # Condition reports are more detailed
            title=f"Condition report for {subject}",
            instructions=f"""
Conduct a thorough condition inspection of {subject} at the specified location.

Evaluation criteria:
{chr(10).join(f"- {aspect}" for aspect in aspects)}

Documentation requirements:
1. Take a wide-angle photo showing the overall area
2. Take close-up photos of:
   - Any damage, wear, or problems
   - Any particularly well-maintained areas
   - Safety concerns (if any)
3. Optionally record a short video walkthrough
4. Write a detailed report covering each evaluation criteria

Rating scale (1-10):
1-3: Poor condition, needs immediate attention
4-5: Below average, some issues
6-7: Average/acceptable condition
8-9: Good condition, well maintained
10: Excellent condition
            """.strip(),
            location=location,
            questions=questions,
            evidence_requirements=evidence_requirements,
            bounty_usd=bounty,
            deadline=datetime.utcnow() + timedelta(hours=deadline_hours),
            metadata={
                "subject": subject,
                "aspects_to_check": aspects,
                "location_type": location_type,
            },
        )

    @classmethod
    def suggest_bounty(
        cls,
        task_type: ReconTaskType,
        location_type: str = "urban",
        time_type: str = "business_hours",
        question_count: int = 3,
        urgency_factor: float = 1.0,
    ) -> BountySuggestion:
        """
        Suggest an appropriate bounty for a task.

        Calculates bounty based on:
        - Base rate for task type
        - Location difficulty
        - Time-of-day factor
        - Number of questions
        - Urgency multiplier

        Args:
            task_type: Type of recon task
            location_type: Type of area (urban, suburban, rural, remote)
            time_type: Time of day (business_hours, evening, night, weekend, holiday)
            question_count: Number of questions to answer
            urgency_factor: Multiplier for urgent tasks (1.0 = normal)

        Returns:
            BountySuggestion with calculated amount and reasoning
        """
        base = cls.BASE_BOUNTIES.get(task_type, Decimal("2.00"))
        location_factor = cls.LOCATION_FACTORS.get(location_type, Decimal("1.0"))
        time_factor = cls.TIME_FACTORS.get(time_type, Decimal("1.0"))

        # Question complexity bonus
        question_bonus = Decimal("0.25") * max(0, question_count - 3)

        # Calculate total
        subtotal = base * location_factor * time_factor
        subtotal += question_bonus
        subtotal *= Decimal(str(urgency_factor))

        # Round to nearest $0.25
        amount = (subtotal * 4).quantize(Decimal("1")) / 4

        # Determine tier
        if amount <= TaskTier.SIMPLE.max_bounty:
            tier = TaskTier.SIMPLE
        elif amount <= TaskTier.STANDARD.max_bounty:
            tier = TaskTier.STANDARD
        else:
            tier = TaskTier.PREMIUM

        # Clamp to tier bounds
        amount = max(tier.min_bounty, min(tier.max_bounty, amount))

        reasoning = (
            f"Base rate for {task_type.value}: ${base}, "
            f"Location factor ({location_type}): {location_factor}x, "
            f"Time factor ({time_type}): {time_factor}x"
        )
        if question_bonus > 0:
            reasoning += f", Question bonus: +${question_bonus}"
        if urgency_factor != 1.0:
            reasoning += f", Urgency: {urgency_factor}x"

        return BountySuggestion(
            amount=amount,
            tier=tier,
            reasoning=reasoning,
            factors={
                "base": base,
                "location_factor": location_factor,
                "time_factor": time_factor,
                "question_bonus": question_bonus,
                "urgency_factor": Decimal(str(urgency_factor)),
            },
        )

    @classmethod
    def estimate_completion_time(
        cls,
        task_type: ReconTaskType,
        location_type: str = "urban",
    ) -> timedelta:
        """
        Estimate how long a task will take to complete.

        Args:
            task_type: Type of recon task
            location_type: Type of area

        Returns:
            Estimated completion time
        """
        base_minutes = task_type.default_tier.typical_duration_minutes

        # Location multiplier for travel time
        location_multipliers = {
            "urban_core": 0.8,
            "urban": 1.0,
            "suburban": 1.3,
            "rural": 1.8,
            "remote": 2.5,
        }
        multiplier = location_multipliers.get(location_type, 1.0)

        return timedelta(minutes=int(base_minutes * multiplier))
