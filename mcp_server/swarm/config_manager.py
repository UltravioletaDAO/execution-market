"""
SwarmConfigManager — Centralized Configuration with Validation
================================================================

Production-grade configuration management for the KarmaCadabra V2 swarm.
Provides a single source of truth for all swarm settings with:

1. **Typed configuration** — Dataclass-based configs with sensible defaults
2. **Environment awareness** — dev/staging/production profiles with overrides
3. **Validation** — Constraints checked at load time, not at crash time
4. **Hot reload** — Update config without restarting the swarm
5. **Secrets management** — Sensitive values loaded from env vars, never hardcoded
6. **Config diffing** — Track what changed between reloads

Architecture:
    config.json/env → ConfigManager.load() → SwarmConfig (validated)
    SwarmConfig → all swarm modules (scheduler, coordinator, dashboard, etc.)
    Hot reload: ConfigManager.reload() → diff → notify listeners

Thread-safe. No external dependencies.
"""

import json
import os
import time
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Callable


# ──────────────────────────────────────────────────────────────
# Environment Profiles
# ──────────────────────────────────────────────────────────────


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# ──────────────────────────────────────────────────────────────
# Configuration Dataclasses
# ──────────────────────────────────────────────────────────────


@dataclass
class AgentPoolConfig:
    """Agent fleet configuration."""

    max_agents: int = 24
    min_healthy_agents: int = 12  # Minimum for fleet to be considered operational
    default_daily_budget_usd: float = 5.0
    default_monthly_budget_usd: float = 100.0
    max_task_bounty_usd: float = 10.0  # Max single task cost
    cooldown_seconds: int = 30  # Post-task cooldown
    heartbeat_interval_seconds: int = 60  # Expected heartbeat frequency
    stale_timeout_seconds: int = 600  # Agent considered stale after this
    max_consecutive_failures: int = 5  # Auto-suspend after this many failures


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""

    cycle_interval_seconds: int = 30  # How often scheduler runs
    max_batch_size: int = 10  # Max tasks per scheduling cycle
    urgency_critical_hours: float = 1.0  # <1h to deadline = critical
    urgency_urgent_hours: float = 4.0  # <4h to deadline = urgent
    urgency_relaxed_hours: float = 24.0  # >24h to deadline = relaxed
    retry_max_attempts: int = 3
    retry_base_delay_seconds: float = 5.0
    retry_max_delay_seconds: float = 300.0
    circuit_breaker_threshold: int = 5  # Failures before opening circuit
    circuit_breaker_reset_seconds: float = 60.0
    load_balancer_window_seconds: float = 300.0
    load_balancer_max_tasks: int = 3  # Max active tasks per agent


@dataclass
class CoordinationConfig:
    """Acontext / IRC coordination configuration."""

    irc_host: str = "meshrelay.local"
    irc_port: int = 6667
    irc_channel: str = "#em-swarm"
    irc_nickname_prefix: str = "EM-Agent"
    lock_ttl_seconds: int = 300  # Auto-expire locks after 5 min
    lock_renewal_seconds: int = 120  # Renew lock if still working at 2 min
    auction_timeout_seconds: int = 30  # Wait for competing bids
    heartbeat_broadcast_seconds: int = 60  # Broadcast presence every 60s
    reconnect_delay_seconds: int = 10
    max_reconnect_attempts: int = 5


@dataclass
class APIConfig:
    """Execution Market API configuration."""

    base_url: str = "https://api.execution.market"
    api_key: str = ""  # Loaded from env: EM_API_KEY
    timeout_seconds: int = 30
    max_retries: int = 3
    rate_limit_rpm: int = 60  # Requests per minute
    poll_interval_seconds: int = 15  # Task polling frequency


@dataclass
class ReputationConfig:
    """Reputation and scoring configuration."""

    erc8004_network: str = "base"
    identity_contract: str = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
    reputation_contract: str = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
    min_score_threshold: float = 0.3  # Min reputation to assign tasks
    quality_weight: float = 0.4
    speed_weight: float = 0.2
    reliability_weight: float = 0.3
    cost_weight: float = 0.1
    skill_decay_days: int = 90  # Skills decay if unused for 90 days


@dataclass
class DashboardConfig:
    """Dashboard and monitoring configuration."""

    snapshot_interval_seconds: int = 30
    alert_cooldown_seconds: int = 300  # Don't repeat same alert within 5 min
    sla_warning_threshold: float = 0.90
    sla_critical_threshold: float = 0.75
    budget_warning_threshold: float = 0.80
    failure_streak_warning: int = 3
    failure_streak_critical: int = 5
    max_alert_history: int = 1000


@dataclass
class PersistenceConfig:
    """State persistence configuration."""

    state_dir: str = ".swarm_state"
    save_interval_seconds: int = 60
    max_event_history: int = 10000
    backup_on_save: bool = True
    compression: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    file: Optional[str] = None
    max_file_size_mb: int = 50
    backup_count: int = 5


@dataclass
class SwarmConfig:
    """Complete swarm configuration."""

    environment: Environment = Environment.PRODUCTION
    version: str = "2.0.0"
    agent_pool: AgentPoolConfig = field(default_factory=AgentPoolConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    coordination: CoordinationConfig = field(default_factory=CoordinationConfig)
    api: APIConfig = field(default_factory=APIConfig)
    reputation: ReputationConfig = field(default_factory=ReputationConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    enabled_networks: list[str] = field(
        default_factory=lambda: [
            "base",
            "ethereum",
            "polygon",
            "arbitrum",
            "celo",
            "monad",
            "avalanche",
            "optimism",
        ]
    )
    features: dict[str, bool] = field(
        default_factory=lambda: {
            "acontext_coordination": True,
            "seal_bridge": True,
            "autojob_enrichment": True,
            "budget_enforcement": True,
            "auto_suspension": True,
            "irc_broadcast": True,
        }
    )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["environment"] = self.environment.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SwarmConfig":
        """Create config from dictionary (e.g., loaded from JSON)."""
        config = cls()
        if "environment" in data:
            config.environment = Environment(data["environment"])
        if "version" in data:
            config.version = data["version"]
        if "agent_pool" in data:
            config.agent_pool = _merge_dataclass(AgentPoolConfig, data["agent_pool"])
        if "scheduler" in data:
            config.scheduler = _merge_dataclass(SchedulerConfig, data["scheduler"])
        if "coordination" in data:
            config.coordination = _merge_dataclass(
                CoordinationConfig, data["coordination"]
            )
        if "api" in data:
            config.api = _merge_dataclass(APIConfig, data["api"])
        if "reputation" in data:
            config.reputation = _merge_dataclass(ReputationConfig, data["reputation"])
        if "dashboard" in data:
            config.dashboard = _merge_dataclass(DashboardConfig, data["dashboard"])
        if "persistence" in data:
            config.persistence = _merge_dataclass(
                PersistenceConfig, data["persistence"]
            )
        if "logging" in data:
            config.logging = _merge_dataclass(LoggingConfig, data["logging"])
        if "enabled_networks" in data:
            config.enabled_networks = data["enabled_networks"]
        if "features" in data:
            config.features.update(data["features"])
        return config


# ──────────────────────────────────────────────────────────────
# Environment Profiles
# ──────────────────────────────────────────────────────────────


ENVIRONMENT_OVERRIDES: dict[Environment, dict] = {
    Environment.DEVELOPMENT: {
        "agent_pool": {
            "max_agents": 4,
            "min_healthy_agents": 2,
            "default_daily_budget_usd": 1.0,
            "max_task_bounty_usd": 0.50,
        },
        "scheduler": {
            "cycle_interval_seconds": 10,
            "circuit_breaker_threshold": 3,
        },
        "api": {
            "base_url": "http://localhost:8000",
            "rate_limit_rpm": 120,
        },
        "coordination": {
            "irc_host": "localhost",
        },
        "logging": {
            "level": "DEBUG",
        },
    },
    Environment.STAGING: {
        "agent_pool": {
            "max_agents": 8,
            "min_healthy_agents": 4,
            "default_daily_budget_usd": 2.0,
        },
        "api": {
            "base_url": "https://api-staging.execution.market",
        },
        "logging": {
            "level": "DEBUG",
        },
    },
    Environment.TEST: {
        "agent_pool": {
            "max_agents": 4,
            "min_healthy_agents": 2,
            "default_daily_budget_usd": 0.0,
            "cooldown_seconds": 0,
        },
        "scheduler": {
            "cycle_interval_seconds": 1,
            "circuit_breaker_threshold": 2,
            "circuit_breaker_reset_seconds": 5.0,
        },
        "api": {
            "base_url": "http://test-api:8000",
            "timeout_seconds": 5,
        },
        "coordination": {
            "irc_host": "localhost",
            "lock_ttl_seconds": 10,
        },
        "logging": {
            "level": "DEBUG",
        },
    },
    Environment.PRODUCTION: {},  # Production uses defaults
}


# ──────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────


class ConfigValidationError(Exception):
    """Configuration validation failed."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Config validation failed: {'; '.join(errors)}")


def validate_config(config: SwarmConfig) -> list[str]:
    """Validate a SwarmConfig and return list of errors (empty = valid)."""
    errors = []

    # Agent pool
    ap = config.agent_pool
    if ap.max_agents < 1:
        errors.append("agent_pool.max_agents must be >= 1")
    if ap.max_agents > 100:
        errors.append("agent_pool.max_agents should not exceed 100")
    if ap.min_healthy_agents > ap.max_agents:
        errors.append("agent_pool.min_healthy_agents cannot exceed max_agents")
    if ap.default_daily_budget_usd < 0:
        errors.append("agent_pool.default_daily_budget_usd must be >= 0")
    if ap.max_task_bounty_usd < 0:
        errors.append("agent_pool.max_task_bounty_usd must be >= 0")
    if ap.cooldown_seconds < 0:
        errors.append("agent_pool.cooldown_seconds must be >= 0")
    if ap.stale_timeout_seconds < ap.heartbeat_interval_seconds:
        errors.append(
            "agent_pool.stale_timeout_seconds should be >= heartbeat_interval_seconds"
        )

    # Scheduler
    sc = config.scheduler
    if sc.cycle_interval_seconds < 1:
        errors.append("scheduler.cycle_interval_seconds must be >= 1")
    if sc.max_batch_size < 1:
        errors.append("scheduler.max_batch_size must be >= 1")
    if sc.retry_max_attempts < 0:
        errors.append("scheduler.retry_max_attempts must be >= 0")
    if sc.retry_base_delay_seconds <= 0:
        errors.append("scheduler.retry_base_delay_seconds must be > 0")
    if sc.circuit_breaker_threshold < 1:
        errors.append("scheduler.circuit_breaker_threshold must be >= 1")
    if sc.load_balancer_max_tasks < 1:
        errors.append("scheduler.load_balancer_max_tasks must be >= 1")

    # Coordination
    cc = config.coordination
    if cc.lock_ttl_seconds < 10:
        errors.append("coordination.lock_ttl_seconds must be >= 10")
    if cc.auction_timeout_seconds < 1:
        errors.append("coordination.auction_timeout_seconds must be >= 1")
    if cc.irc_port < 1 or cc.irc_port > 65535:
        errors.append("coordination.irc_port must be 1-65535")

    # API
    api = config.api
    if not api.base_url.startswith(("http://", "https://")):
        errors.append("api.base_url must start with http:// or https://")
    if api.timeout_seconds < 1:
        errors.append("api.timeout_seconds must be >= 1")
    if api.rate_limit_rpm < 1:
        errors.append("api.rate_limit_rpm must be >= 1")

    # Reputation
    rep = config.reputation
    weights = (
        rep.quality_weight + rep.speed_weight + rep.reliability_weight + rep.cost_weight
    )
    if abs(weights - 1.0) > 0.01:
        errors.append(f"reputation weights must sum to 1.0 (got {weights:.2f})")
    if rep.min_score_threshold < 0 or rep.min_score_threshold > 1:
        errors.append("reputation.min_score_threshold must be 0.0-1.0")

    # Dashboard
    db = config.dashboard
    if db.sla_critical_threshold >= db.sla_warning_threshold:
        errors.append(
            "dashboard.sla_critical_threshold must be < sla_warning_threshold"
        )

    # Networks
    valid_networks = {
        "base",
        "ethereum",
        "polygon",
        "arbitrum",
        "celo",
        "monad",
        "avalanche",
        "optimism",
        "solana",
        "sepolia",
        "base_sepolia",
    }
    unknown = set(config.enabled_networks) - valid_networks
    if unknown:
        errors.append(f"Unknown networks: {unknown}")

    return errors


# ──────────────────────────────────────────────────────────────
# Config Manager
# ──────────────────────────────────────────────────────────────


class ConfigManager:
    """
    Centralized configuration manager for the swarm.

    Supports:
    - Loading from JSON file + env var overrides
    - Environment profiles (dev/staging/production/test)
    - Validation at load time
    - Hot reload with change detection
    - Listener notification on config changes
    """

    ENV_PREFIX = "EM_SWARM_"

    def __init__(
        self, config_path: Optional[str] = None, environment: Optional[str] = None
    ):
        self._config_path = config_path
        self._environment = environment
        self._config: Optional[SwarmConfig] = None
        self._previous_config: Optional[SwarmConfig] = None
        self._load_time: float = 0.0
        self._reload_count: int = 0
        self._listeners: list[Callable[[SwarmConfig, list[str]], None]] = []

    @property
    def config(self) -> SwarmConfig:
        """Get current config. Loads defaults if not yet loaded."""
        if self._config is None:
            self.load()
        return self._config

    def load(self, strict: bool = True) -> SwarmConfig:
        """
        Load configuration from all sources.

        Priority (highest first):
        1. Environment variables (EM_SWARM_*)
        2. Config file (if provided)
        3. Environment profile overrides
        4. Defaults
        """
        # Start with defaults
        config_data = {}

        # Apply environment profile
        env = self._resolve_environment()
        profile_overrides = ENVIRONMENT_OVERRIDES.get(env, {})
        _deep_merge(config_data, profile_overrides)

        # Load from file
        if self._config_path and Path(self._config_path).exists():
            with open(self._config_path, "r") as f:
                file_data = json.load(f)
            _deep_merge(config_data, file_data)

        # Build config
        config = SwarmConfig.from_dict(config_data)
        config.environment = env

        # Apply env var overrides
        self._apply_env_overrides(config)

        # Load secrets from env
        self._load_secrets(config)

        # Validate
        errors = validate_config(config)
        if errors and strict:
            raise ConfigValidationError(errors)

        self._previous_config = self._config
        self._config = config
        self._load_time = time.time()
        self._reload_count += 1

        return config

    def reload(self) -> tuple[SwarmConfig, list[str]]:
        """
        Reload config and return (new_config, list_of_changes).
        Notifies registered listeners.
        """
        old_dict = self._config.to_dict() if self._config else {}
        new_config = self.load(strict=False)
        new_dict = new_config.to_dict()

        changes = _diff_dicts(old_dict, new_dict)

        if changes:
            for listener in self._listeners:
                try:
                    listener(new_config, changes)
                except Exception:
                    pass  # Don't let listener errors break reload

        return new_config, changes

    def on_change(self, callback: Callable[[SwarmConfig, list[str]], None]):
        """Register a listener for config changes."""
        self._listeners.append(callback)

    def save(self, path: Optional[str] = None):
        """Save current config to JSON file."""
        save_path = path or self._config_path
        if not save_path:
            raise ValueError("No config path specified")
        if self._config is None:
            raise ValueError("No config loaded")

        data = self._config.to_dict()
        # Remove secrets before saving
        if "api" in data:
            data["api"].pop("api_key", None)

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_status(self) -> dict:
        """Get config manager status."""
        return {
            "loaded": self._config is not None,
            "environment": self._config.environment.value if self._config else None,
            "version": self._config.version if self._config else None,
            "config_path": self._config_path,
            "load_time": self._load_time,
            "reload_count": self._reload_count,
            "listener_count": len(self._listeners),
        }

    # ──────── Internal ────────

    def _resolve_environment(self) -> Environment:
        """Determine environment from explicit setting or env var."""
        if self._environment:
            return Environment(self._environment)
        env_str = os.environ.get(f"{self.ENV_PREFIX}ENVIRONMENT", "production")
        try:
            return Environment(env_str.lower())
        except ValueError:
            return Environment.PRODUCTION

    def _apply_env_overrides(self, config: SwarmConfig):
        """Apply environment variable overrides."""
        env_map = {
            f"{self.ENV_PREFIX}MAX_AGENTS": ("agent_pool", "max_agents", int),
            f"{self.ENV_PREFIX}DAILY_BUDGET": (
                "agent_pool",
                "default_daily_budget_usd",
                float,
            ),
            f"{self.ENV_PREFIX}CYCLE_INTERVAL": (
                "scheduler",
                "cycle_interval_seconds",
                int,
            ),
            f"{self.ENV_PREFIX}MAX_BATCH": ("scheduler", "max_batch_size", int),
            f"{self.ENV_PREFIX}IRC_HOST": ("coordination", "irc_host", str),
            f"{self.ENV_PREFIX}IRC_PORT": ("coordination", "irc_port", int),
            f"{self.ENV_PREFIX}IRC_CHANNEL": ("coordination", "irc_channel", str),
            f"{self.ENV_PREFIX}API_URL": ("api", "base_url", str),
            f"{self.ENV_PREFIX}API_TIMEOUT": ("api", "timeout_seconds", int),
            f"{self.ENV_PREFIX}LOG_LEVEL": ("logging", "level", str),
            f"{self.ENV_PREFIX}NETWORKS": ("enabled_networks", None, str),
        }

        for env_key, (section, attr, type_fn) in env_map.items():
            value = os.environ.get(env_key)
            if value is not None:
                if section == "enabled_networks":
                    config.enabled_networks = [n.strip() for n in value.split(",")]
                else:
                    sub_config = getattr(config, section)
                    try:
                        setattr(sub_config, attr, type_fn(value))
                    except (ValueError, TypeError):
                        pass  # Skip invalid env var values

    def _load_secrets(self, config: SwarmConfig):
        """Load sensitive values from environment variables."""
        config.api.api_key = os.environ.get("EM_API_KEY", "")


# ──────────────────────────────────────────────────────────────
# Utility Functions
# ──────────────────────────────────────────────────────────────


def _merge_dataclass(cls, overrides: dict):
    """Create a dataclass instance with overrides."""
    instance = cls()
    for key, value in overrides.items():
        if hasattr(instance, key):
            setattr(instance, key, value)
    return instance


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Deep merge overrides into base dict (mutates base)."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)
    return base


def _diff_dicts(old: dict, new: dict, prefix: str = "") -> list[str]:
    """Find differences between two dicts. Returns list of change descriptions."""
    changes = []
    all_keys = set(list(old.keys()) + list(new.keys()))

    for key in sorted(all_keys):
        path = f"{prefix}.{key}" if prefix else key
        old_val = old.get(key)
        new_val = new.get(key)

        if old_val == new_val:
            continue

        if isinstance(old_val, dict) and isinstance(new_val, dict):
            changes.extend(_diff_dicts(old_val, new_val, path))
        elif key in old and key in new:
            changes.append(f"{path}: {old_val!r} → {new_val!r}")
        elif key not in old:
            changes.append(f"{path}: added ({new_val!r})")
        else:
            changes.append(f"{path}: removed (was {old_val!r})")

    return changes
