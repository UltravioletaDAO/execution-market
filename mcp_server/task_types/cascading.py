"""
Execution Market Cascading Tasks (NOW-138)

Implements parent-child task chains:
- Task completion triggers child tasks
- Conditional task creation
- Multi-stage workflows
- Automatic escalation paths

Use cases:
- Verify -> Deliver if available
- Inspect -> Report issue -> Follow-up repair
- Survey -> Contact leads -> Qualify -> Close
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4


class TriggerType(str, Enum):
    """Types of cascade triggers."""

    ON_COMPLETE = "on_complete"  # Any completion
    ON_SUCCESS = "on_success"  # Successful completion
    ON_FAILURE = "on_failure"  # Failed/rejected
    CONDITIONAL = "conditional"  # Based on result data
    SCHEDULED = "scheduled"  # After time delay
    PARALLEL = "parallel"  # Start simultaneously


class CascadeStatus(str, Enum):
    """Status of a cascade chain."""

    PENDING = "pending"  # Not yet started
    ACTIVE = "active"  # In progress
    COMPLETED = "completed"  # All stages done
    FAILED = "failed"  # Chain broken
    CANCELLED = "cancelled"


@dataclass
class TriggerCondition:
    """
    Condition for triggering a child task.

    Attributes:
        field: Field in parent result to check
        operator: Comparison operator (eq, ne, gt, lt, contains, etc.)
        value: Value to compare against
        description: Human-readable description
    """

    field: str
    operator: str  # "eq", "ne", "gt", "lt", "gte", "lte", "contains", "not_contains"
    value: Any
    description: str = ""

    def evaluate(self, result_data: Dict[str, Any]) -> bool:
        """
        Evaluate condition against result data.

        Args:
            result_data: Result data from parent task

        Returns:
            True if condition is met
        """
        # Navigate nested fields (e.g., "response.is_available")
        actual = result_data
        for key in self.field.split("."):
            if isinstance(actual, dict):
                actual = actual.get(key)
            else:
                return False

        if actual is None:
            return False

        operators = {
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
            "gt": lambda a, b: float(a) > float(b),
            "lt": lambda a, b: float(a) < float(b),
            "gte": lambda a, b: float(a) >= float(b),
            "lte": lambda a, b: float(a) <= float(b),
            "contains": lambda a, b: b in str(a),
            "not_contains": lambda a, b: b not in str(a),
            "in": lambda a, b: a in b,
            "not_in": lambda a, b: a not in b,
            "is_true": lambda a, _: bool(a) is True,
            "is_false": lambda a, _: bool(a) is False,
        }

        op_func = operators.get(self.operator)
        if not op_func:
            return False

        try:
            return op_func(actual, self.value)
        except (TypeError, ValueError):
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "description": self.description,
        }


@dataclass
class TaskTemplate:
    """
    Template for generating child tasks.

    Attributes:
        template_id: Unique template identifier
        task_type: Type of task to create
        title_template: Title with {placeholders}
        instructions_template: Instructions with {placeholders}
        bounty_usd: Bounty for generated task
        deadline_hours: Hours until deadline
        evidence_required: Required evidence types
        inherit_location: Whether to inherit parent's location
        metadata_template: Additional metadata
    """

    template_id: str
    task_type: str
    title_template: str
    instructions_template: str
    bounty_usd: Decimal
    deadline_hours: int
    evidence_required: List[str] = field(default_factory=list)
    inherit_location: bool = True
    metadata_template: Dict[str, Any] = field(default_factory=dict)

    def generate_task(
        self,
        parent_result: Dict[str, Any],
        parent_task: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a task from this template.

        Args:
            parent_result: Result data from parent task
            parent_task: Parent task data

        Returns:
            Generated task dict
        """
        # Merge data for template substitution
        context = {
            **parent_task,
            "result": parent_result,
            "parent_id": parent_task.get("id"),
        }

        # Format templates
        title = self._format_template(self.title_template, context)
        instructions = self._format_template(self.instructions_template, context)

        task = {
            "id": str(uuid4()),
            "task_type": self.task_type,
            "title": title,
            "instructions": instructions,
            "bounty_usd": str(self.bounty_usd),
            "deadline_hours": self.deadline_hours,
            "evidence_required": self.evidence_required,
            "parent_task_id": parent_task.get("id"),
            "cascade_template_id": self.template_id,
            "metadata": self._format_metadata(context),
        }

        # Inherit location if specified
        if self.inherit_location:
            if "location" in parent_task:
                task["location"] = parent_task["location"]
            if "latitude" in parent_task and "longitude" in parent_task:
                task["latitude"] = parent_task["latitude"]
                task["longitude"] = parent_task["longitude"]

        return task

    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format a template string with context data."""
        try:
            # Simple placeholder replacement
            result = template
            for key, value in self._flatten_dict(context).items():
                placeholder = "{" + key + "}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value))
            return result
        except Exception:
            return template

    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = "",
        sep: str = ".",
    ) -> Dict[str, Any]:
        """Flatten nested dict for template substitution."""
        items: List[tuple] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _format_metadata(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Format metadata template with context."""
        metadata = self.metadata_template.copy()
        for key, value in metadata.items():
            if isinstance(value, str) and "{" in value:
                metadata[key] = self._format_template(value, context)
        return metadata

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "template_id": self.template_id,
            "task_type": self.task_type,
            "title_template": self.title_template,
            "instructions_template": self.instructions_template,
            "bounty_usd": str(self.bounty_usd),
            "deadline_hours": self.deadline_hours,
            "evidence_required": self.evidence_required,
            "inherit_location": self.inherit_location,
            "metadata_template": self.metadata_template,
        }


@dataclass
class CascadeRule:
    """
    Rule defining when and how to create child tasks.

    Attributes:
        rule_id: Unique rule identifier
        trigger_type: When to trigger
        conditions: Conditions that must be met
        child_template: Template for child task
        delay_minutes: Delay before creating child
        max_children: Maximum children from this rule
        description: Human-readable description
    """

    rule_id: str
    trigger_type: TriggerType
    conditions: List[TriggerCondition]
    child_template: TaskTemplate
    delay_minutes: int = 0
    max_children: int = 1
    description: str = ""

    def should_trigger(
        self,
        parent_status: str,
        parent_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if this rule should trigger.

        Args:
            parent_status: Status of parent task
            parent_result: Result data from parent

        Returns:
            True if rule should trigger
        """
        # Check trigger type
        if self.trigger_type == TriggerType.ON_COMPLETE:
            if parent_status not in ["completed", "success", "failed"]:
                return False

        elif self.trigger_type == TriggerType.ON_SUCCESS:
            if parent_status not in ["completed", "success"]:
                return False

        elif self.trigger_type == TriggerType.ON_FAILURE:
            if parent_status not in ["failed", "rejected"]:
                return False

        elif self.trigger_type == TriggerType.CONDITIONAL:
            if not parent_result:
                return False
            # All conditions must be met
            for condition in self.conditions:
                if not condition.evaluate(parent_result):
                    return False

        elif self.trigger_type == TriggerType.PARALLEL:
            return True  # Triggers immediately with parent

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_id": self.rule_id,
            "trigger_type": self.trigger_type.value,
            "conditions": [c.to_dict() for c in self.conditions],
            "child_template": self.child_template.to_dict(),
            "delay_minutes": self.delay_minutes,
            "max_children": self.max_children,
            "description": self.description,
        }


@dataclass
class CascadeChain:
    """
    A chain of cascading tasks.

    Attributes:
        chain_id: Unique chain identifier
        name: Chain name
        description: Chain description
        root_task_id: ID of the first task
        rules: List of cascade rules
        status: Chain status
        created_tasks: List of created task IDs
        created_at: When chain was created
        completed_at: When chain completed
        metadata: Additional chain data
    """

    chain_id: str
    name: str
    description: str
    root_task_id: str
    rules: List[CascadeRule]
    status: CascadeStatus = CascadeStatus.PENDING
    created_tasks: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_applicable_rules(
        self,
        task_id: str,
        task_status: str,
        task_result: Optional[Dict[str, Any]] = None,
    ) -> List[CascadeRule]:
        """
        Get rules that should trigger for a task completion.

        Args:
            task_id: Completed task ID
            task_status: Task status
            task_result: Task result data

        Returns:
            List of rules that should trigger
        """
        applicable = []
        for rule in self.rules:
            if rule.should_trigger(task_status, task_result):
                applicable.append(rule)
        return applicable

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "root_task_id": self.root_task_id,
            "rules": [r.to_dict() for r in self.rules],
            "status": self.status.value,
            "created_tasks": self.created_tasks,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "metadata": self.metadata,
        }


class CascadeEngine:
    """
    Engine for processing cascade rules and creating child tasks.
    """

    def __init__(self, task_creator: Optional[Callable] = None):
        """
        Initialize cascade engine.

        Args:
            task_creator: Optional function to create tasks in database
        """
        self.task_creator = task_creator

    def process_completion(
        self,
        chain: CascadeChain,
        completed_task: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process a task completion and create child tasks.

        Args:
            chain: The cascade chain
            completed_task: The completed task
            result: Result data from the task

        Returns:
            List of created child tasks
        """
        created = []
        task_status = completed_task.get("status", "completed")

        applicable_rules = chain.get_applicable_rules(
            completed_task.get("id"),
            task_status,
            result,
        )

        for rule in applicable_rules:
            # Generate child task
            child_task = rule.child_template.generate_task(
                parent_result=result or {},
                parent_task=completed_task,
            )

            # Apply delay if specified
            if rule.delay_minutes > 0:
                child_task["delayed_until"] = (
                    datetime.now(UTC) + timedelta(minutes=rule.delay_minutes)
                ).isoformat()

            # Create task if creator provided
            if self.task_creator:
                self.task_creator(child_task)

            created.append(child_task)
            chain.created_tasks.append(child_task["id"])

        # Update chain status
        if created:
            chain.status = CascadeStatus.ACTIVE

        return created

    def check_chain_completion(self, chain: CascadeChain) -> bool:
        """
        Check if a cascade chain is complete.

        A chain is complete when there are no pending tasks
        and no more rules can trigger.

        Args:
            chain: The cascade chain to check

        Returns:
            True if chain is complete
        """
        # This would need integration with task database
        # For now, return False (needs external check)
        return False


class CascadeTemplates:
    """
    Pre-built cascade chain templates.
    """

    @staticmethod
    def verify_then_deliver() -> List[CascadeRule]:
        """
        Template: Verify availability, then deliver if available.

        Stage 1: Check if item is available at store
        Stage 2: If available, create delivery task to pick up and deliver
        """
        return [
            CascadeRule(
                rule_id="verify_to_deliver",
                trigger_type=TriggerType.CONDITIONAL,
                conditions=[
                    TriggerCondition(
                        field="result.is_available",
                        operator="is_true",
                        value=True,
                        description="Item is available",
                    ),
                ],
                child_template=TaskTemplate(
                    template_id="deliver_available_item",
                    task_type="delivery",
                    title_template="Deliver {result.item_name} from {location.place_name}",
                    instructions_template="""
Pick up {result.item_name} from {location.place_name} and deliver to customer.

ITEM DETAILS:
- Item: {result.item_name}
- Price: ${result.price}
- Location: {location.address}

DELIVERY INSTRUCTIONS:
1. Go to the store
2. Purchase the item (receipt required)
3. Deliver to customer address
4. Get proof of delivery
""".strip(),
                    bounty_usd=Decimal("10.00"),
                    deadline_hours=4,
                    evidence_required=["photo_receipt", "photo_delivery"],
                ),
                description="Create delivery task when item is available",
            ),
            CascadeRule(
                rule_id="notify_unavailable",
                trigger_type=TriggerType.CONDITIONAL,
                conditions=[
                    TriggerCondition(
                        field="result.is_available",
                        operator="is_false",
                        value=False,
                        description="Item is not available",
                    ),
                ],
                child_template=TaskTemplate(
                    template_id="check_alternative_store",
                    task_type="availability_check",
                    title_template="Check {result.item_name} at alternative location",
                    instructions_template="""
The item was not available at the first location. Check alternative stores.

ITEM: {result.item_name}
ORIGINAL LOCATION: {location.place_name}

Find and verify availability at a nearby alternative store.
""".strip(),
                    bounty_usd=Decimal("3.00"),
                    deadline_hours=2,
                    evidence_required=["photo_geo", "text_response"],
                ),
                description="Check alternative when item unavailable",
            ),
        ]

    @staticmethod
    def inspect_and_report() -> List[CascadeRule]:
        """
        Template: Inspect, then report issues if found.

        Stage 1: General inspection
        Stage 2: If issues found, create detailed report task
        Stage 3: If critical, escalate to priority repair
        """
        return [
            CascadeRule(
                rule_id="issues_found",
                trigger_type=TriggerType.CONDITIONAL,
                conditions=[
                    TriggerCondition(
                        field="result.issues_found",
                        operator="gt",
                        value=0,
                        description="At least one issue found",
                    ),
                ],
                child_template=TaskTemplate(
                    template_id="detailed_report",
                    task_type="condition_report",
                    title_template="Detailed report: {result.issues_count} issues at {location.place_name}",
                    instructions_template="""
Issues were found during initial inspection. Create detailed documentation.

ISSUES FOUND: {result.issues_count}
LOCATION: {location.place_name}

For each issue:
1. Take close-up photos
2. Document severity (1-10)
3. Note safety concerns
4. Estimate repair urgency
""".strip(),
                    bounty_usd=Decimal("15.00"),
                    deadline_hours=24,
                    evidence_required=["photo", "photo", "photo", "text_response"],
                ),
                description="Create detailed report when issues found",
            ),
            CascadeRule(
                rule_id="critical_issue",
                trigger_type=TriggerType.CONDITIONAL,
                conditions=[
                    TriggerCondition(
                        field="result.has_critical_issue",
                        operator="is_true",
                        value=True,
                        description="Critical safety issue found",
                    ),
                ],
                child_template=TaskTemplate(
                    template_id="emergency_escalation",
                    task_type="notification",
                    title_template="URGENT: Critical issue at {location.place_name}",
                    instructions_template="""
CRITICAL SAFETY ISSUE DETECTED

Location: {location.place_name}
Issue: {result.critical_issue_description}

This task has been auto-escalated due to safety concerns.
""".strip(),
                    bounty_usd=Decimal("5.00"),
                    deadline_hours=1,
                    evidence_required=["photo", "text_response"],
                ),
                delay_minutes=0,  # Immediate
                description="Immediate escalation for critical issues",
            ),
        ]

    @staticmethod
    def survey_to_follow_up() -> List[CascadeRule]:
        """
        Template: Survey leads, qualify interested ones.

        Stage 1: Initial survey
        Stage 2: If interested, schedule follow-up
        """
        return [
            CascadeRule(
                rule_id="interested_lead",
                trigger_type=TriggerType.CONDITIONAL,
                conditions=[
                    TriggerCondition(
                        field="result.interest_level",
                        operator="gte",
                        value=7,
                        description="Interest level 7 or higher",
                    ),
                ],
                child_template=TaskTemplate(
                    template_id="follow_up_call",
                    task_type="follow_up",
                    title_template="Follow up with interested lead: {result.contact_name}",
                    instructions_template="""
QUALIFIED LEAD - FOLLOW UP REQUIRED

Contact: {result.contact_name}
Interest Level: {result.interest_level}/10
Notes: {result.notes}

Schedule a follow-up within 48 hours to:
1. Answer any questions
2. Provide additional information
3. Schedule demonstration if requested
""".strip(),
                    bounty_usd=Decimal("8.00"),
                    deadline_hours=48,
                    evidence_required=["text_response"],
                    inherit_location=False,
                ),
                description="Create follow-up for interested leads",
            ),
        ]


# Convenience functions
def create_cascade_chain(
    name: str,
    root_task_id: str,
    rules: List[CascadeRule],
    description: str = "",
) -> CascadeChain:
    """
    Create a new cascade chain.

    Args:
        name: Chain name
        root_task_id: ID of the starting task
        rules: Cascade rules
        description: Chain description

    Returns:
        Configured CascadeChain
    """
    return CascadeChain(
        chain_id=str(uuid4()),
        name=name,
        description=description,
        root_task_id=root_task_id,
        rules=rules,
    )


def get_template(template_name: str) -> List[CascadeRule]:
    """
    Get a pre-built cascade template.

    Args:
        template_name: Name of template

    Returns:
        List of cascade rules
    """
    templates = {
        "verify_then_deliver": CascadeTemplates.verify_then_deliver,
        "inspect_and_report": CascadeTemplates.inspect_and_report,
        "survey_to_follow_up": CascadeTemplates.survey_to_follow_up,
    }

    template_func = templates.get(template_name)
    if not template_func:
        raise ValueError(f"Unknown template: {template_name}")

    return template_func()
