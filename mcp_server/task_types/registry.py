"""
Execution Market Task Type Registry

Central registry for all task types in the Execution Market system.
Provides:
- Registration of task types
- Lookup by type name
- Listing all available types
- Factory methods for creating task instances

Usage:
    from task_types.registry import TaskTypeRegistry

    # Get the global registry
    registry = TaskTypeRegistry.get_instance()

    # List all types
    types = registry.list_task_types()

    # Get a specific type
    photo_task = registry.get_task_type("photo_verification")

    # Create a task instance with config
    delivery = registry.create_task_type("delivery", config={...})
"""

from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
import importlib
import logging

from .base import TaskType, TaskContext, BountyRecommendation, TimeEstimate


logger = logging.getLogger(__name__)


@dataclass
class TaskTypeInfo:
    """
    Information about a registered task type.

    Attributes:
        type_name: Unique identifier for the type
        display_name: Human-readable name
        description: Description of what the type does
        category: Category (physical_presence, knowledge_access, etc.)
        task_class: The TaskType class
        default_config: Default configuration for the type
    """
    type_name: str
    display_name: str
    description: str
    category: str
    task_class: Type[TaskType]
    default_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (without class reference)."""
        return {
            "type_name": self.type_name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "default_config": self.default_config,
        }


class TaskTypeRegistry:
    """
    Singleton registry for task types.

    Manages registration and lookup of all task types in the system.
    """

    _instance: Optional["TaskTypeRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "TaskTypeRegistry":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the registry (only once)."""
        if not self._initialized:
            self._types: Dict[str, TaskTypeInfo] = {}
            self._initialized = True
            self._register_builtin_types()

    @classmethod
    def get_instance(cls) -> "TaskTypeRegistry":
        """Get the singleton instance."""
        return cls()

    def _register_builtin_types(self) -> None:
        """Register all built-in task types."""
        # Import and register each type
        try:
            from .photo_verification import PhotoVerificationTask, PhotoValidationConfig
            self.register(
                task_class=PhotoVerificationTask,
                default_config={
                    "max_gps_distance_meters": 500.0,
                    "max_photo_age_minutes": 60,
                    "require_gps": True,
                    "require_recent_timestamp": True,
                    "check_ai_generated": True,
                },
            )
        except ImportError as e:
            logger.warning(f"Could not import PhotoVerificationTask: {e}")

        try:
            from .delivery import DeliveryTask, DeliveryValidationConfig
            self.register(
                task_class=DeliveryTask,
                default_config={
                    "pickup_gps_radius_meters": 200.0,
                    "delivery_gps_radius_meters": 200.0,
                    "require_gps": True,
                    "max_delivery_hours": 24,
                    "require_signature": False,
                },
            )
        except ImportError as e:
            logger.warning(f"Could not import DeliveryTask: {e}")

        try:
            from .survey import SurveyTask, SurveyValidationConfig
            self.register(
                task_class=SurveyTask,
                default_config={
                    "require_all_fields": True,
                    "require_location": False,
                    "min_duration_seconds": 60,
                },
            )
        except ImportError as e:
            logger.warning(f"Could not import SurveyTask: {e}")

        try:
            from .mystery_shop import MysteryShopTask, MysteryShopConfig
            self.register(
                task_class=MysteryShopTask,
                default_config={
                    "require_receipt": True,
                    "max_receipt_age_days": 1,
                    "require_gps": True,
                    "require_photos": True,
                    "min_photos": 2,
                },
            )
        except ImportError as e:
            logger.warning(f"Could not import MysteryShopTask: {e}")

        try:
            from .price_check import PriceCheckTask, PriceCheckConfig
            self.register(
                task_class=PriceCheckTask,
                default_config={
                    "require_gps": True,
                    "gps_radius_meters": 200.0,
                    "require_photos": True,
                    "validate_price_format": True,
                },
            )
        except ImportError as e:
            logger.warning(f"Could not import PriceCheckTask: {e}")

    def register(
        self,
        task_class: Type[TaskType],
        default_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a task type.

        Args:
            task_class: The TaskType class to register
            default_config: Default configuration for creating instances

        Raises:
            ValueError: If type_name is already registered
        """
        type_name = task_class.type_name

        if type_name in self._types:
            logger.warning(f"Task type '{type_name}' already registered, overwriting")

        self._types[type_name] = TaskTypeInfo(
            type_name=type_name,
            display_name=task_class.display_name,
            description=task_class.description,
            category=task_class.category,
            task_class=task_class,
            default_config=default_config or {},
        )

        logger.debug(f"Registered task type: {type_name}")

    def unregister(self, type_name: str) -> bool:
        """
        Unregister a task type.

        Args:
            type_name: Name of the type to unregister

        Returns:
            True if type was unregistered, False if not found
        """
        if type_name in self._types:
            del self._types[type_name]
            return True
        return False

    def get_task_type(self, type_name: str) -> Optional[TaskType]:
        """
        Get a task type instance by name.

        Args:
            type_name: Name of the task type

        Returns:
            TaskType instance with default config, or None if not found
        """
        info = self._types.get(type_name)
        if info is None:
            return None

        # Create instance with default config
        return self.create_task_type(type_name)

    def create_task_type(
        self,
        type_name: str,
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[TaskType]:
        """
        Create a task type instance with custom configuration.

        Args:
            type_name: Name of the task type
            config: Configuration dictionary (merged with defaults)
            **kwargs: Additional arguments passed to constructor

        Returns:
            Configured TaskType instance, or None if type not found
        """
        info = self._types.get(type_name)
        if info is None:
            logger.error(f"Task type not found: {type_name}")
            return None

        # Merge config with defaults
        merged_config = {**info.default_config, **(config or {})}

        try:
            # Create config object if the task type expects one
            task_class = info.task_class

            # Try to create with config parameter
            if merged_config:
                # Get the config class name (conventionally {TaskName}Config -> {TaskName}ValidationConfig)
                config_class = None
                try:
                    module = importlib.import_module(task_class.__module__)
                    # Try common config class naming patterns
                    for suffix in ["ValidationConfig", "Config"]:
                        base_name = task_class.__name__.replace("Task", "")
                        config_class_name = f"{base_name}{suffix}"
                        if hasattr(module, config_class_name):
                            config_class = getattr(module, config_class_name)
                            break
                except Exception:
                    pass

                if config_class:
                    try:
                        config_obj = config_class(**merged_config)
                        return task_class(config=config_obj, **kwargs)
                    except TypeError:
                        pass

            # Fall back to creating without config
            return task_class(**kwargs)

        except Exception as e:
            logger.error(f"Error creating task type '{type_name}': {e}")
            return None

    def list_task_types(self) -> List[TaskTypeInfo]:
        """
        List all registered task types.

        Returns:
            List of TaskTypeInfo for all registered types
        """
        return list(self._types.values())

    def list_by_category(self, category: str) -> List[TaskTypeInfo]:
        """
        List task types in a specific category.

        Args:
            category: Category to filter by

        Returns:
            List of TaskTypeInfo in the category
        """
        return [
            info for info in self._types.values()
            if info.category == category
        ]

    def get_info(self, type_name: str) -> Optional[TaskTypeInfo]:
        """
        Get information about a task type.

        Args:
            type_name: Name of the task type

        Returns:
            TaskTypeInfo or None if not found
        """
        return self._types.get(type_name)

    def get_categories(self) -> List[str]:
        """
        Get all unique categories.

        Returns:
            List of category names
        """
        return list(set(info.category for info in self._types.values()))

    def get_bounty_recommendation(
        self,
        type_name: str,
        context: TaskContext,
        complexity: int = 1,
    ) -> Optional[BountyRecommendation]:
        """
        Get bounty recommendation for a task type.

        Args:
            type_name: Name of the task type
            context: Task context
            complexity: Task complexity (1-5)

        Returns:
            BountyRecommendation or None if type not found
        """
        task_type = self.get_task_type(type_name)
        if task_type is None:
            return None

        return task_type.get_bounty_recommendation(context, complexity)

    def get_time_estimate(
        self,
        type_name: str,
        context: TaskContext,
        complexity: int = 1,
    ) -> Optional[TimeEstimate]:
        """
        Get time estimate for a task type.

        Args:
            type_name: Name of the task type
            context: Task context
            complexity: Task complexity (1-5)

        Returns:
            TimeEstimate or None if type not found
        """
        task_type = self.get_task_type(type_name)
        if task_type is None:
            return None

        return task_type.get_time_estimate(context, complexity)

    def __len__(self) -> int:
        """Return number of registered types."""
        return len(self._types)

    def __contains__(self, type_name: str) -> bool:
        """Check if type is registered."""
        return type_name in self._types


# Convenience functions for module-level access
def get_registry() -> TaskTypeRegistry:
    """Get the global task type registry."""
    return TaskTypeRegistry.get_instance()


def get_task_type(type_name: str) -> Optional[TaskType]:
    """Get a task type by name from the global registry."""
    return get_registry().get_task_type(type_name)


def list_task_types() -> List[TaskTypeInfo]:
    """List all task types from the global registry."""
    return get_registry().list_task_types()


def register_task_type(
    task_class: Type[TaskType],
    default_config: Optional[Dict[str, Any]] = None,
) -> None:
    """Register a task type in the global registry."""
    get_registry().register(task_class, default_config)


# Dictionary export for quick lookup
TASK_TYPES: Dict[str, Type[TaskType]] = {}


def _init_task_types_dict() -> None:
    """Initialize the TASK_TYPES dictionary."""
    global TASK_TYPES
    registry = get_registry()
    TASK_TYPES = {
        info.type_name: info.task_class
        for info in registry.list_task_types()
    }


# Initialize on import
_init_task_types_dict()
