"""
Execution Market Trials - Experience Testing Tasks (NOW-132)

Implements "mystery shopping" style tasks:
- Restaurant experience evaluations
- Product testing and reviews
- Service quality assessments
- Retail experience audits

Trials are typically Tier 2 tasks ($10-30) requiring:
- Actual purchase/experience (reimbursed)
- Detailed feedback on multiple criteria
- Photo/video evidence
- Structured scoring rubric
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4


class TrialType(str, Enum):
    """Types of trial/experience testing tasks."""
    RESTAURANT = "restaurant"       # Dining experience
    RETAIL = "retail"              # Store shopping experience
    PRODUCT = "product"            # Physical product testing
    SERVICE = "service"            # Service quality (salon, spa, etc.)
    HOSPITALITY = "hospitality"    # Hotel/lodging experience
    ENTERTAINMENT = "entertainment" # Movies, events, etc.
    DELIVERY = "delivery"          # Delivery service testing
    ONLINE = "online"              # Online service/UX testing


class EvaluationCriteria(str, Enum):
    """Standard evaluation criteria for trials."""
    # Common
    OVERALL_SATISFACTION = "overall_satisfaction"
    VALUE_FOR_MONEY = "value_for_money"
    WOULD_RECOMMEND = "would_recommend"

    # Restaurant/Food
    FOOD_QUALITY = "food_quality"
    FOOD_PRESENTATION = "food_presentation"
    PORTION_SIZE = "portion_size"
    MENU_VARIETY = "menu_variety"
    DIETARY_OPTIONS = "dietary_options"

    # Service
    STAFF_FRIENDLINESS = "staff_friendliness"
    SERVICE_SPEED = "service_speed"
    KNOWLEDGE = "knowledge"
    PROBLEM_RESOLUTION = "problem_resolution"

    # Environment
    CLEANLINESS = "cleanliness"
    AMBIANCE = "ambiance"
    NOISE_LEVEL = "noise_level"
    ACCESSIBILITY = "accessibility"

    # Product
    PRODUCT_QUALITY = "product_quality"
    PACKAGING = "packaging"
    EASE_OF_USE = "ease_of_use"
    DURABILITY = "durability"
    INSTRUCTIONS = "instructions"


@dataclass
class CriteriaConfig:
    """
    Configuration for an evaluation criterion.

    Attributes:
        criteria: The criterion being evaluated
        weight: Weight in overall score (0.0-1.0)
        min_score: Minimum score (usually 1)
        max_score: Maximum score (usually 5 or 10)
        required: Whether this criterion is mandatory
        description: Explanation for evaluator
    """
    criteria: EvaluationCriteria
    weight: float
    min_score: int = 1
    max_score: int = 5
    required: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "criteria": self.criteria.value,
            "weight": self.weight,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "required": self.required,
            "description": self.description,
        }


@dataclass
class ReimbursementConfig:
    """
    Configuration for expense reimbursement.

    Attributes:
        max_amount: Maximum reimbursable amount
        requires_receipt: Whether receipt is required
        allowed_categories: Categories eligible for reimbursement
        payment_method: How reimbursement is processed
    """
    max_amount: Decimal
    requires_receipt: bool = True
    allowed_categories: List[str] = field(default_factory=list)
    payment_method: str = "add_to_bounty"  # or "separate_payment"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "max_amount": str(self.max_amount),
            "requires_receipt": self.requires_receipt,
            "allowed_categories": self.allowed_categories,
            "payment_method": self.payment_method,
        }


@dataclass
class TrialTask:
    """
    A trial/experience testing task.

    Attributes:
        id: Unique task identifier
        trial_type: Type of trial
        title: Short task title
        business_name: Name of business being evaluated
        business_address: Address of business
        instructions: Detailed instructions for evaluator
        criteria: List of evaluation criteria configurations
        reimbursement: Reimbursement configuration
        bounty_usd: Payment amount (excluding reimbursement)
        deadline: When trial must be completed
        reveal_identity: Whether evaluator identifies themselves
        required_evidence: Evidence requirements
        scenario: Specific scenario to follow (if any)
        created_at: When task was created
        metadata: Additional task-specific data
    """
    id: str
    trial_type: TrialType
    title: str
    business_name: str
    business_address: str
    instructions: str
    criteria: List[CriteriaConfig]
    reimbursement: ReimbursementConfig
    bounty_usd: Decimal
    deadline: datetime
    reveal_identity: bool = False  # Mystery shopping stays anonymous
    required_evidence: List[str] = field(default_factory=list)
    scenario: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "trial_type": self.trial_type.value,
            "title": self.title,
            "business_name": self.business_name,
            "business_address": self.business_address,
            "instructions": self.instructions,
            "criteria": [c.to_dict() for c in self.criteria],
            "reimbursement": self.reimbursement.to_dict(),
            "bounty_usd": str(self.bounty_usd),
            "deadline": self.deadline.isoformat(),
            "reveal_identity": self.reveal_identity,
            "required_evidence": self.required_evidence,
            "scenario": self.scenario,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def calculate_total_payment(self, actual_expense: Decimal) -> Decimal:
        """
        Calculate total payment including reimbursement.

        Args:
            actual_expense: Actual amount spent

        Returns:
            Total payment (bounty + capped reimbursement)
        """
        reimbursement = min(actual_expense, self.reimbursement.max_amount)
        return self.bounty_usd + reimbursement


@dataclass
class TrialSubmission:
    """
    Submission for a trial task.

    Attributes:
        submission_id: Unique submission ID
        task_id: Related task ID
        executor_id: Worker who completed it
        scores: Dict of criteria -> score
        comments: Dict of criteria -> comment
        overall_notes: General observations
        expense_amount: Amount spent (for reimbursement)
        receipt_url: URL to receipt image
        evidence_urls: URLs to other evidence
        submitted_at: When submitted
    """
    submission_id: str
    task_id: str
    executor_id: str
    scores: Dict[str, int]
    comments: Dict[str, str]
    overall_notes: str
    expense_amount: Decimal
    receipt_url: Optional[str] = None
    evidence_urls: List[str] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def calculate_weighted_score(
        self,
        criteria_configs: List[CriteriaConfig],
    ) -> float:
        """
        Calculate weighted overall score.

        Args:
            criteria_configs: List of criteria configurations

        Returns:
            Weighted average score (0-100)
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for config in criteria_configs:
            if config.criteria.value in self.scores:
                score = self.scores[config.criteria.value]
                # Normalize to 0-100 scale
                normalized = ((score - config.min_score) /
                              (config.max_score - config.min_score)) * 100
                weighted_sum += normalized * config.weight
                total_weight += config.weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "submission_id": self.submission_id,
            "task_id": self.task_id,
            "executor_id": self.executor_id,
            "scores": self.scores,
            "comments": self.comments,
            "overall_notes": self.overall_notes,
            "expense_amount": str(self.expense_amount),
            "receipt_url": self.receipt_url,
            "evidence_urls": self.evidence_urls,
            "submitted_at": self.submitted_at.isoformat(),
        }


# Standard criteria sets by trial type
TRIAL_CRITERIA: Dict[TrialType, List[CriteriaConfig]] = {
    TrialType.RESTAURANT: [
        CriteriaConfig(
            criteria=EvaluationCriteria.FOOD_QUALITY,
            weight=0.25,
            description="Taste, freshness, temperature of food",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.FOOD_PRESENTATION,
            weight=0.10,
            description="Visual appeal and plating",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.SERVICE_SPEED,
            weight=0.15,
            description="Time to seat, order, receive food",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.STAFF_FRIENDLINESS,
            weight=0.15,
            description="Attitude and helpfulness of staff",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.CLEANLINESS,
            weight=0.15,
            description="Cleanliness of tables, floors, restrooms",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.VALUE_FOR_MONEY,
            weight=0.10,
            description="Price vs quality received",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.OVERALL_SATISFACTION,
            weight=0.10,
            description="Overall dining experience",
        ),
    ],
    TrialType.RETAIL: [
        CriteriaConfig(
            criteria=EvaluationCriteria.STAFF_FRIENDLINESS,
            weight=0.20,
            description="Greeting, helpfulness, attitude",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.KNOWLEDGE,
            weight=0.15,
            description="Product knowledge when asked",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.CLEANLINESS,
            weight=0.15,
            description="Store cleanliness and organization",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.SERVICE_SPEED,
            weight=0.15,
            description="Checkout speed, help availability",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.AMBIANCE,
            weight=0.10,
            description="Store layout, lighting, music",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.VALUE_FOR_MONEY,
            weight=0.15,
            description="Prices vs quality",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.OVERALL_SATISFACTION,
            weight=0.10,
            description="Overall shopping experience",
        ),
    ],
    TrialType.PRODUCT: [
        CriteriaConfig(
            criteria=EvaluationCriteria.PRODUCT_QUALITY,
            weight=0.25,
            description="Build quality, materials, finish",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.EASE_OF_USE,
            weight=0.20,
            description="Intuitive design, learning curve",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.PACKAGING,
            weight=0.10,
            description="Packaging quality, sustainability",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.INSTRUCTIONS,
            weight=0.10,
            description="Clarity of instructions/documentation",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.VALUE_FOR_MONEY,
            weight=0.20,
            description="Price vs quality received",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.OVERALL_SATISFACTION,
            weight=0.15,
            description="Overall product satisfaction",
        ),
    ],
    TrialType.SERVICE: [
        CriteriaConfig(
            criteria=EvaluationCriteria.STAFF_FRIENDLINESS,
            weight=0.20,
            description="Warmth, professionalism",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.KNOWLEDGE,
            weight=0.20,
            description="Expertise demonstrated",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.SERVICE_SPEED,
            weight=0.15,
            description="Wait times, efficiency",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.CLEANLINESS,
            weight=0.15,
            description="Facility cleanliness",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.VALUE_FOR_MONEY,
            weight=0.15,
            description="Price vs service quality",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.OVERALL_SATISFACTION,
            weight=0.15,
            description="Overall service experience",
        ),
    ],
    TrialType.DELIVERY: [
        CriteriaConfig(
            criteria=EvaluationCriteria.SERVICE_SPEED,
            weight=0.30,
            description="Delivery time vs promised",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.PACKAGING,
            weight=0.20,
            description="Package condition on arrival",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.STAFF_FRIENDLINESS,
            weight=0.15,
            description="Driver courtesy and professionalism",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.PRODUCT_QUALITY,
            weight=0.20,
            description="Item condition (for food: temperature, etc.)",
        ),
        CriteriaConfig(
            criteria=EvaluationCriteria.OVERALL_SATISFACTION,
            weight=0.15,
            description="Overall delivery experience",
        ),
    ],
}


class TrialFactory:
    """
    Factory for creating trial tasks with sensible defaults.
    """

    # Default reimbursement limits by trial type
    DEFAULT_REIMBURSEMENT: Dict[TrialType, Decimal] = {
        TrialType.RESTAURANT: Decimal("50.00"),
        TrialType.RETAIL: Decimal("30.00"),
        TrialType.PRODUCT: Decimal("100.00"),
        TrialType.SERVICE: Decimal("75.00"),
        TrialType.HOSPITALITY: Decimal("200.00"),
        TrialType.ENTERTAINMENT: Decimal("40.00"),
        TrialType.DELIVERY: Decimal("30.00"),
        TrialType.ONLINE: Decimal("20.00"),
    }

    # Default bounties by trial type
    DEFAULT_BOUNTY: Dict[TrialType, Decimal] = {
        TrialType.RESTAURANT: Decimal("15.00"),
        TrialType.RETAIL: Decimal("12.00"),
        TrialType.PRODUCT: Decimal("20.00"),
        TrialType.SERVICE: Decimal("15.00"),
        TrialType.HOSPITALITY: Decimal("30.00"),
        TrialType.ENTERTAINMENT: Decimal("12.00"),
        TrialType.DELIVERY: Decimal("10.00"),
        TrialType.ONLINE: Decimal("15.00"),
    }

    @classmethod
    def create_restaurant_trial(
        cls,
        business_name: str,
        business_address: str,
        max_reimbursement: Optional[Decimal] = None,
        bounty: Optional[Decimal] = None,
        deadline_days: int = 7,
        scenario: Optional[str] = None,
        additional_criteria: Optional[List[CriteriaConfig]] = None,
    ) -> TrialTask:
        """
        Create a restaurant mystery shopping trial.

        Args:
            business_name: Restaurant name
            business_address: Restaurant address
            max_reimbursement: Max meal cost to reimburse
            bounty: Payment for completing trial
            deadline_days: Days to complete
            scenario: Specific scenario (e.g., "dine-in lunch for 2")
            additional_criteria: Extra evaluation criteria

        Returns:
            Configured TrialTask
        """
        criteria = TRIAL_CRITERIA[TrialType.RESTAURANT].copy()
        if additional_criteria:
            criteria.extend(additional_criteria)

        reimbursement = ReimbursementConfig(
            max_amount=max_reimbursement or cls.DEFAULT_REIMBURSEMENT[TrialType.RESTAURANT],
            requires_receipt=True,
            allowed_categories=["food", "beverages", "tip"],
        )

        default_scenario = scenario or "Dine in as a regular customer. Order an appetizer, main course, and beverage."

        instructions = f"""
MYSTERY SHOPPING ASSIGNMENT: {business_name}

SCENARIO: {default_scenario}

IMPORTANT GUIDELINES:
1. Act as a regular customer - do NOT reveal you are evaluating
2. Take note of timestamps (arrival, seating, ordering, food arrival)
3. Photograph your meal discretely
4. Keep your receipt - it is required for reimbursement

EVALUATION FOCUS:
- First impressions upon entering
- Greeting and seating process
- Server knowledge and recommendations
- Food quality, presentation, temperature
- Cleanliness of dining area and restrooms
- Overall atmosphere and experience

EVIDENCE REQUIRED:
1. Photo of the exterior/entrance
2. Photo of your meal
3. Photo of the receipt (clear, showing items and total)
4. Optional: photos of any notable issues

SUBMISSION:
- Complete all evaluation criteria
- Provide detailed comments for each area
- Include specific examples and timestamps
""".strip()

        required_evidence = [
            "photo_exterior",
            "photo_meal",
            "photo_receipt",
            "text_response",
        ]

        return TrialTask(
            id=str(uuid4()),
            trial_type=TrialType.RESTAURANT,
            title=f"Restaurant Trial: {business_name}",
            business_name=business_name,
            business_address=business_address,
            instructions=instructions,
            criteria=criteria,
            reimbursement=reimbursement,
            bounty_usd=bounty or cls.DEFAULT_BOUNTY[TrialType.RESTAURANT],
            deadline=datetime.now(UTC) + timedelta(days=deadline_days),
            required_evidence=required_evidence,
            scenario=default_scenario,
            metadata={
                "trial_type": "restaurant",
                "max_party_size": 2,
            }
        )

    @classmethod
    def create_retail_trial(
        cls,
        business_name: str,
        business_address: str,
        target_department: Optional[str] = None,
        must_purchase: bool = False,
        max_reimbursement: Optional[Decimal] = None,
        bounty: Optional[Decimal] = None,
        deadline_days: int = 7,
        scenario: Optional[str] = None,
    ) -> TrialTask:
        """
        Create a retail mystery shopping trial.

        Args:
            business_name: Store name
            business_address: Store address
            target_department: Specific department to evaluate
            must_purchase: Whether a purchase is required
            max_reimbursement: Max purchase cost to reimburse
            bounty: Payment for completing trial
            deadline_days: Days to complete
            scenario: Specific scenario to follow

        Returns:
            Configured TrialTask
        """
        criteria = TRIAL_CRITERIA[TrialType.RETAIL].copy()

        reimbursement = ReimbursementConfig(
            max_amount=max_reimbursement or cls.DEFAULT_REIMBURSEMENT[TrialType.RETAIL],
            requires_receipt=must_purchase,
            allowed_categories=["purchase"],
        )

        dept_text = f" in the {target_department} department" if target_department else ""
        purchase_text = "Make a small purchase to evaluate the checkout process." if must_purchase else "A purchase is not required, but evaluate the checkout area."
        default_scenario = scenario or f"Visit as a regular shopper{dept_text}. Browse, ask for assistance, and {purchase_text.lower()}"

        instructions = f"""
MYSTERY SHOPPING ASSIGNMENT: {business_name}

SCENARIO: {default_scenario}

IMPORTANT GUIDELINES:
1. Act as a regular customer - do NOT reveal you are evaluating
2. Time yourself: how long until greeted? How long for help?
3. Ask at least one product question to test staff knowledge
4. Evaluate the checkout experience

EVALUATION FOCUS:
- Store entrance and first impressions
- Staff greeting and availability
- Product knowledge when asked
- Store cleanliness and organization
- Checkout efficiency and courtesy

EVIDENCE REQUIRED:
1. Photo of store entrance
2. Photo of the department/area evaluated
{"3. Photo of receipt" if must_purchase else ""}
4. Written observations

SUBMISSION:
- Complete all evaluation criteria
- Provide specific examples (quote what staff said, etc.)
- Include timestamps for key interactions
""".strip()

        required_evidence = ["photo_exterior", "photo_department", "text_response"]
        if must_purchase:
            required_evidence.append("photo_receipt")

        return TrialTask(
            id=str(uuid4()),
            trial_type=TrialType.RETAIL,
            title=f"Retail Trial: {business_name}",
            business_name=business_name,
            business_address=business_address,
            instructions=instructions,
            criteria=criteria,
            reimbursement=reimbursement,
            bounty_usd=bounty or cls.DEFAULT_BOUNTY[TrialType.RETAIL],
            deadline=datetime.now(UTC) + timedelta(days=deadline_days),
            required_evidence=required_evidence,
            scenario=default_scenario,
            metadata={
                "trial_type": "retail",
                "target_department": target_department,
                "must_purchase": must_purchase,
            }
        )

    @classmethod
    def create_product_trial(
        cls,
        product_name: str,
        product_url: str,
        usage_duration_days: int = 3,
        max_reimbursement: Optional[Decimal] = None,
        bounty: Optional[Decimal] = None,
        deadline_days: int = 14,
        test_scenarios: Optional[List[str]] = None,
    ) -> TrialTask:
        """
        Create a product testing trial.

        Args:
            product_name: Name of product to test
            product_url: Where to purchase product
            usage_duration_days: How many days to use before reviewing
            max_reimbursement: Max product cost to reimburse
            bounty: Payment for completing trial
            deadline_days: Days to complete
            test_scenarios: Specific scenarios to test

        Returns:
            Configured TrialTask
        """
        criteria = TRIAL_CRITERIA[TrialType.PRODUCT].copy()

        reimbursement = ReimbursementConfig(
            max_amount=max_reimbursement or cls.DEFAULT_REIMBURSEMENT[TrialType.PRODUCT],
            requires_receipt=True,
            allowed_categories=["product_purchase", "shipping"],
        )

        scenarios_text = ""
        if test_scenarios:
            scenarios_text = "\n\nSPECIFIC TESTS TO PERFORM:\n" + "\n".join(
                f"- {s}" for s in test_scenarios
            )

        instructions = f"""
PRODUCT TESTING ASSIGNMENT: {product_name}

PURCHASE FROM: {product_url}

TESTING PROTOCOL:
1. Purchase the product (save receipt)
2. Document unboxing experience
3. Use the product for at least {usage_duration_days} days
4. Test in normal conditions
5. Submit detailed evaluation
{scenarios_text}

EVALUATION FOCUS:
- Unboxing and packaging quality
- Setup/assembly experience
- Daily use experience
- Build quality and durability indicators
- Does it match marketing claims?

EVIDENCE REQUIRED:
1. Photo of product in packaging
2. Photo of unboxing
3. Photos during use (multiple)
4. Photo of receipt/order confirmation
5. Video (optional): 30-60 second usage demo

SUBMISSION:
- Complete all evaluation criteria
- Pros and cons list
- Would you recommend? Why/why not?
- Comparison to similar products (if applicable)
""".strip()

        required_evidence = [
            "photo_packaging",
            "photo_unboxing",
            "photo_in_use",
            "photo_receipt",
            "text_response",
        ]

        return TrialTask(
            id=str(uuid4()),
            trial_type=TrialType.PRODUCT,
            title=f"Product Trial: {product_name}",
            business_name=product_name,
            business_address=product_url,
            instructions=instructions,
            criteria=criteria,
            reimbursement=reimbursement,
            bounty_usd=bounty or cls.DEFAULT_BOUNTY[TrialType.PRODUCT],
            deadline=datetime.now(UTC) + timedelta(days=deadline_days),
            required_evidence=required_evidence,
            metadata={
                "trial_type": "product",
                "product_url": product_url,
                "usage_duration_days": usage_duration_days,
                "test_scenarios": test_scenarios,
            }
        )

    @classmethod
    def create_delivery_trial(
        cls,
        service_name: str,
        service_type: str,  # "food", "grocery", "package"
        order_requirements: str,
        max_reimbursement: Optional[Decimal] = None,
        bounty: Optional[Decimal] = None,
        deadline_days: int = 5,
    ) -> TrialTask:
        """
        Create a delivery service trial.

        Args:
            service_name: Delivery service name (UberEats, DoorDash, etc.)
            service_type: Type of delivery (food, grocery, package)
            order_requirements: What to order
            max_reimbursement: Max order cost to reimburse
            bounty: Payment for completing trial
            deadline_days: Days to complete

        Returns:
            Configured TrialTask
        """
        criteria = TRIAL_CRITERIA[TrialType.DELIVERY].copy()

        reimbursement = ReimbursementConfig(
            max_amount=max_reimbursement or cls.DEFAULT_REIMBURSEMENT[TrialType.DELIVERY],
            requires_receipt=True,
            allowed_categories=["order", "delivery_fee", "tip"],
        )

        instructions = f"""
DELIVERY SERVICE TRIAL: {service_name}

ORDER TYPE: {service_type}
ORDER REQUIREMENTS: {order_requirements}

TESTING PROTOCOL:
1. Place order through the app
2. Screenshot the estimated delivery time
3. Track delivery progress
4. Record actual delivery time
5. Inspect package/food condition
6. Rate the overall experience

TIMING CHECKPOINTS:
- Order placed time
- Estimated delivery time shown
- Driver assigned time
- Driver picked up time
- Actual delivery time

EVALUATION FOCUS:
- App/ordering experience
- Communication and tracking
- Delivery speed vs estimate
- Driver professionalism
- Package/food condition
- Accuracy of order

EVIDENCE REQUIRED:
1. Screenshot of order confirmation with estimated time
2. Screenshot of tracking/status updates
3. Photo of delivered items
4. Photo showing item condition
5. Photo of receipt/order summary

SUBMISSION:
- Complete all evaluation criteria
- Include all timestamps
- Note any communication with driver
""".strip()

        required_evidence = [
            "screenshot_order",
            "screenshot_tracking",
            "photo_delivery",
            "photo_condition",
            "photo_receipt",
            "text_response",
        ]

        return TrialTask(
            id=str(uuid4()),
            trial_type=TrialType.DELIVERY,
            title=f"Delivery Trial: {service_name} ({service_type})",
            business_name=service_name,
            business_address="N/A - Delivery Service",
            instructions=instructions,
            criteria=criteria,
            reimbursement=reimbursement,
            bounty_usd=bounty or cls.DEFAULT_BOUNTY[TrialType.DELIVERY],
            deadline=datetime.now(UTC) + timedelta(days=deadline_days),
            required_evidence=required_evidence,
            metadata={
                "trial_type": "delivery",
                "service_type": service_type,
                "order_requirements": order_requirements,
            }
        )


# Convenience functions
def create_trial(
    trial_type: TrialType,
    business_name: str,
    business_address: str,
    **kwargs,
) -> TrialTask:
    """
    Create a trial task using the appropriate factory method.

    Args:
        trial_type: Type of trial
        business_name: Business to evaluate
        business_address: Business address
        **kwargs: Additional arguments for specific trial type

    Returns:
        Configured TrialTask
    """
    factory_methods = {
        TrialType.RESTAURANT: TrialFactory.create_restaurant_trial,
        TrialType.RETAIL: TrialFactory.create_retail_trial,
        TrialType.PRODUCT: TrialFactory.create_product_trial,
        TrialType.DELIVERY: TrialFactory.create_delivery_trial,
    }

    method = factory_methods.get(trial_type)
    if not method:
        raise ValueError(f"No factory method for trial type: {trial_type}")

    return method(business_name=business_name, business_address=business_address, **kwargs)


def get_criteria_for_type(trial_type: TrialType) -> List[CriteriaConfig]:
    """Get default evaluation criteria for a trial type."""
    return TRIAL_CRITERIA.get(trial_type, [])
