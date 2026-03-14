"""
SwarmConfigManager — Production configuration system for the KK V2 Swarm.

Provides file-based configuration loading, validation, environment overrides,
and runtime reconfiguration. This is the missing layer between "library code"
and "deployable system."

Features:
    - Load from JSON config files (~/.em-swarm/config.json)
    - Environment variable overrides (EM_SWARM_* prefix)
    - Multi-environment support (development / staging / production)
    - Configuration validation with detailed error messages
    - Runtime reconfiguration (budget adjustments, mode changes)
    - Fleet definition: agent rosters, skill profiles, budget allocations
    - Routing policy: strategy weights, category preferences, chain priorities
    - Alert thresholds: performance, budget, health metrics
    - Preset profiles: conservative / balanced / aggressive

Usage:
    # Load from default location
    config = SwarmConfigManager.load()

    # Load from specific file
    config = SwarmConfigManager.load("/path/to/config.json")

    # Create with preset
    config = SwarmConfigManager.from_preset("balanced")

    # Access typed config
    config.fleet.max_agents          # 24
    config.routing.default_strategy  # "adaptive"
    config.budget.daily_limit_usd    # 50.0
    config.alerts.budget_warn_pct    # 0.8

    # Runtime updates
    config.update_budget(daily_limit_usd=100.0)
    config.set_mode("full-auto")
    config.save()

    # Convert to DaemonConfig
    daemon_config = config.to_daemon_config()

    # Validate
    errors = config.validate()
    assert not errors, f"Config errors: {errors}"
"""

import json
import logging
import os
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("em.swarm.config_manager")


# ─── Config Sections ──────────────────────────────────────────────────────────


@dataclass
class FleetConfig:
    """Agent fleet configuration."""
    max_agents: int = 24
    agent_id_range: tuple = (2101, 2124)
    auto_register: bool = True
    default_tags: list = field(default_factory=lambda: ["general"])
    warmup_tasks: int = 3  # Tasks before full routing weight
    cooldown_after_failure_sec: int = 300  # 5 min cooldown on failure
    max_concurrent_tasks: int = 3  # Per-agent concurrency limit
    health_check_interval_sec: int = 600  # 10 min health checks
    idle_suspend_after_sec: int = 86400  # Suspend idle agents after 24h
    agent_profiles: dict = field(default_factory=dict)
    """Per-agent overrides: { "2101": { "tags": ["delivery"], "max_bounty": 5.0 } }"""


@dataclass
class RoutingConfig:
    """Task routing configuration."""
    default_strategy: str = "adaptive"
    # Strategy weights for adaptive mode (0.0-1.0)
    strategy_weights: dict = field(default_factory=lambda: {
        "best_fit": 0.4,
        "specialist": 0.3,
        "budget_aware": 0.2,
        "round_robin": 0.1,
    })
    # Category → preferred chain mapping
    chain_preferences: dict = field(default_factory=lambda: {
        "physical_verification": "base",
        "content_creation": "base",
        "data_collection": "base",
        "delivery": "base",
    })
    # Min reputation score for assignment (0-100)
    min_reputation_score: float = 0.0
    # Max tasks to route per cycle
    max_tasks_per_cycle: int = 10
    # Enable AutoJob enrichment
    enable_autojob_enrichment: bool = True
    # SLA target in seconds
    sla_target_sec: float = 3600.0
    # Categories to accept (empty = all)
    accepted_categories: list = field(default_factory=list)
    # Categories to exclude
    excluded_categories: list = field(default_factory=list)
    # Min bounty to route (USD)
    min_bounty_usd: float = 0.0
    # Max bounty to route (USD)
    max_bounty_usd: float = 100.0


@dataclass
class BudgetConfig:
    """Budget and financial configuration."""
    daily_limit_usd: float = 50.0
    monthly_limit_usd: float = 1000.0
    per_agent_daily_usd: float = 10.0
    per_task_max_usd: float = 25.0
    platform_fee_rate: float = 0.13  # 13%
    reserve_pct: float = 0.1  # 10% reserve for gas/overhead
    auto_refill: bool = False
    alert_on_overspend: bool = True
    currency: str = "USDC"
    funded_chains: list = field(default_factory=lambda: ["base"])


@dataclass
class AlertConfig:
    """Alert thresholds and notification settings."""
    budget_warn_pct: float = 0.8  # Alert at 80% budget spent
    budget_critical_pct: float = 0.95  # Critical at 95%
    routing_success_min_pct: float = 0.7  # Alert if routing drops below 70%
    completion_success_min_pct: float = 0.6  # Alert if completion drops below 60%
    avg_routing_time_max_ms: float = 100.0  # Alert if routing > 100ms
    agent_failure_streak_max: int = 3  # Alert after 3 consecutive failures
    api_error_rate_max_pct: float = 0.1  # Alert if >10% API errors
    enable_telegram: bool = True
    telegram_chat_id: str = ""
    enable_heartbeat_alerts: bool = True
    quiet_hours_start: int = 23  # No alerts 11pm-8am
    quiet_hours_end: int = 8


@dataclass
class AnalyticsConfig:
    """Analytics and reporting configuration."""
    enabled: bool = True
    retention_days: int = 90
    trend_window_days: int = 30
    export_format: str = "json"  # json | csv
    auto_report_interval_sec: int = 3600  # Hourly reports
    track_agent_performance: bool = True
    track_financial_metrics: bool = True
    track_routing_decisions: bool = True
    track_evidence_quality: bool = True


@dataclass
class ConnectionConfig:
    """External service connection configuration."""
    em_api_url: str = "https://api.execution.market"
    autojob_url: str = "http://localhost:8765"
    erc8004_rpc_url: str = "https://mainnet.base.org"
    erc8004_network: str = "base"
    describe_net_rpc_url: str = ""
    meshrelay_url: str = "http://127.0.0.1:3001"
    api_timeout_sec: float = 30.0
    api_retry_count: int = 3
    api_retry_backoff_sec: float = 1.0


@dataclass
class DaemonRunConfig:
    """Daemon runtime configuration."""
    mode: str = "passive"  # passive | semi-auto | full-auto
    interval_sec: int = 300  # 5 min default
    max_consecutive_errors: int = 5
    backoff_multiplier: float = 2.0
    max_backoff_sec: float = 3600.0  # 1 hour max
    state_persist_interval_sec: int = 60  # Save state every minute
    graceful_shutdown_timeout_sec: int = 30
    log_level: str = "INFO"
    enable_heartbeat: bool = True
    enable_analytics: bool = True
    enable_acontext: bool = True
    enable_strategy_engine: bool = True


# ─── Presets ──────────────────────────────────────────────────────────────────


PRESETS = {
    "conservative": {
        "fleet": {"max_concurrent_tasks": 1, "cooldown_after_failure_sec": 600},
        "routing": {
            "max_tasks_per_cycle": 3,
            "max_bounty_usd": 5.0,
            "min_reputation_score": 30.0,
        },
        "budget": {
            "daily_limit_usd": 10.0,
            "per_agent_daily_usd": 2.0,
            "per_task_max_usd": 5.0,
        },
        "daemon": {"mode": "semi-auto", "interval_sec": 600},
        "alerts": {"budget_warn_pct": 0.6, "agent_failure_streak_max": 2},
    },
    "balanced": {
        "fleet": {"max_concurrent_tasks": 3, "cooldown_after_failure_sec": 300},
        "routing": {
            "max_tasks_per_cycle": 10,
            "max_bounty_usd": 25.0,
            "min_reputation_score": 10.0,
        },
        "budget": {
            "daily_limit_usd": 50.0,
            "per_agent_daily_usd": 10.0,
            "per_task_max_usd": 25.0,
        },
        "daemon": {"mode": "semi-auto", "interval_sec": 300},
        "alerts": {"budget_warn_pct": 0.8, "agent_failure_streak_max": 3},
    },
    "aggressive": {
        "fleet": {"max_concurrent_tasks": 5, "cooldown_after_failure_sec": 120},
        "routing": {
            "max_tasks_per_cycle": 25,
            "max_bounty_usd": 100.0,
            "min_reputation_score": 0.0,
        },
        "budget": {
            "daily_limit_usd": 200.0,
            "per_agent_daily_usd": 25.0,
            "per_task_max_usd": 100.0,
        },
        "daemon": {"mode": "full-auto", "interval_sec": 120},
        "alerts": {"budget_warn_pct": 0.9, "agent_failure_streak_max": 5},
    },
}


# ─── Environment Mapping ─────────────────────────────────────────────────────


ENV_OVERRIDES = {
    # Fleet
    "EM_SWARM_MAX_AGENTS": ("fleet", "max_agents", int),
    "EM_SWARM_MAX_CONCURRENT": ("fleet", "max_concurrent_tasks", int),
    "EM_SWARM_COOLDOWN_SEC": ("fleet", "cooldown_after_failure_sec", int),
    # Routing
    "EM_SWARM_STRATEGY": ("routing", "default_strategy", str),
    "EM_SWARM_MAX_TASKS_CYCLE": ("routing", "max_tasks_per_cycle", int),
    "EM_SWARM_MAX_BOUNTY": ("routing", "max_bounty_usd", float),
    "EM_SWARM_MIN_REPUTATION": ("routing", "min_reputation_score", float),
    "EM_SWARM_SLA_SEC": ("routing", "sla_target_sec", float),
    # Budget
    "EM_SWARM_DAILY_LIMIT": ("budget", "daily_limit_usd", float),
    "EM_SWARM_MONTHLY_LIMIT": ("budget", "monthly_limit_usd", float),
    "EM_SWARM_PER_AGENT_DAILY": ("budget", "per_agent_daily_usd", float),
    "EM_SWARM_PER_TASK_MAX": ("budget", "per_task_max_usd", float),
    "EM_SWARM_FEE_RATE": ("budget", "platform_fee_rate", float),
    # Connection
    "EM_API_URL": ("connection", "em_api_url", str),
    "EM_SWARM_AUTOJOB_URL": ("connection", "autojob_url", str),
    "EM_SWARM_RPC_URL": ("connection", "erc8004_rpc_url", str),
    # Daemon
    "EM_SWARM_MODE": ("daemon", "mode", str),
    "EM_SWARM_INTERVAL": ("daemon", "interval_sec", int),
    "EM_SWARM_LOG_LEVEL": ("daemon", "log_level", str),
    # Alerts
    "EM_SWARM_TELEGRAM_CHAT": ("alerts", "telegram_chat_id", str),
}


# ─── Config Manager ──────────────────────────────────────────────────────────


class SwarmConfigManager:
    """Production configuration manager for the KK V2 Swarm."""

    DEFAULT_CONFIG_DIR = os.path.expanduser("~/.em-swarm")
    DEFAULT_CONFIG_FILE = "config.json"

    def __init__(
        self,
        fleet: Optional[FleetConfig] = None,
        routing: Optional[RoutingConfig] = None,
        budget: Optional[BudgetConfig] = None,
        alerts: Optional[AlertConfig] = None,
        analytics: Optional[AnalyticsConfig] = None,
        connection: Optional[ConnectionConfig] = None,
        daemon: Optional[DaemonRunConfig] = None,
        environment: str = "production",
        config_path: Optional[str] = None,
    ):
        self.fleet = fleet or FleetConfig()
        self.routing = routing or RoutingConfig()
        self.budget = budget or BudgetConfig()
        self.alerts = alerts or AlertConfig()
        self.analytics = analytics or AnalyticsConfig()
        self.connection = connection or ConnectionConfig()
        self.daemon = daemon or DaemonRunConfig()
        self.environment = environment
        self.config_path = config_path
        self._loaded_at: Optional[datetime] = None
        self._modified: bool = False

    # ─── Factory Methods ──────────────────────────────────────────────

    @classmethod
    def load(cls, path: Optional[str] = None) -> "SwarmConfigManager":
        """Load configuration from JSON file with env var overrides.

        Load order:
        1. Defaults (dataclass defaults)
        2. Config file (if exists)
        3. Environment variables (EM_SWARM_* prefix)
        """
        config_path = path or os.path.join(cls.DEFAULT_CONFIG_DIR, cls.DEFAULT_CONFIG_FILE)
        instance = cls(config_path=config_path)

        # Step 1: Load from file if it exists
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    data = json.load(f)
                instance._apply_dict(data)
                instance._loaded_at = datetime.now(timezone.utc)
                logger.info("Loaded config from %s", config_path)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load config from %s: %s", config_path, e)
        else:
            logger.info("No config file at %s, using defaults", config_path)

        # Step 2: Apply environment variable overrides
        instance._apply_env_overrides()

        return instance

    @classmethod
    def from_preset(cls, preset_name: str) -> "SwarmConfigManager":
        """Create configuration from a named preset.

        Presets:
            - conservative: Low risk, human approval, small budgets
            - balanced: Moderate automation, reasonable limits (default)
            - aggressive: Full automation, large budgets, fast cycles
        """
        if preset_name not in PRESETS:
            raise ValueError(
                f"Unknown preset '{preset_name}'. "
                f"Available: {', '.join(PRESETS.keys())}"
            )
        instance = cls()
        instance._apply_dict(PRESETS[preset_name])
        logger.info("Created config from '%s' preset", preset_name)
        return instance

    @classmethod
    def from_dict(cls, data: dict) -> "SwarmConfigManager":
        """Create configuration from a dictionary."""
        instance = cls()
        instance._apply_dict(data)
        return instance

    # ─── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize configuration to a dictionary."""
        result = {
            "environment": self.environment,
            "fleet": self._dataclass_to_dict(self.fleet),
            "routing": self._dataclass_to_dict(self.routing),
            "budget": self._dataclass_to_dict(self.budget),
            "alerts": self._dataclass_to_dict(self.alerts),
            "analytics": self._dataclass_to_dict(self.analytics),
            "connection": self._dataclass_to_dict(self.connection),
            "daemon": self._dataclass_to_dict(self.daemon),
        }
        return result

    def save(self, path: Optional[str] = None) -> str:
        """Save configuration to JSON file.

        Returns the path where the config was saved.
        """
        save_path = path or self.config_path or os.path.join(
            self.DEFAULT_CONFIG_DIR, self.DEFAULT_CONFIG_FILE
        )

        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        data = self.to_dict()
        data["_meta"] = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
        }

        with open(save_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self._modified = False
        logger.info("Saved config to %s", save_path)
        return save_path

    # ─── Conversion to DaemonConfig ───────────────────────────────────

    def to_daemon_config(self):
        """Convert to the DaemonConfig expected by SwarmDaemon.

        This bridges the new config system with the existing daemon.
        """
        from .daemon import DaemonConfig as DC

        return DC(
            mode=self.daemon.mode,
            em_api_url=self.connection.em_api_url,
            autojob_url=self.connection.autojob_url,
            state_dir=self.DEFAULT_CONFIG_DIR,
            interval_seconds=self.daemon.interval_sec,
            max_tasks_per_cycle=self.routing.max_tasks_per_cycle,
            max_bounty_usd=self.routing.max_bounty_usd,
            sla_target_seconds=self.routing.sla_target_sec,
            platform_fee_rate=self.budget.platform_fee_rate,
            enable_analytics=self.daemon.enable_analytics,
            enable_strategy_engine=self.daemon.enable_strategy_engine,
            enable_notifications=self.alerts.enable_telegram,
        )

    # ─── Runtime Reconfiguration ──────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        """Change the daemon operating mode at runtime.

        Args:
            mode: One of 'passive', 'semi-auto', 'full-auto'
        """
        valid_modes = ("passive", "semi-auto", "full-auto")
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Valid: {valid_modes}")
        self.daemon.mode = mode
        self._modified = True
        logger.info("Mode changed to '%s'", mode)

    def update_budget(self, **kwargs) -> None:
        """Update budget configuration at runtime.

        Args:
            daily_limit_usd: New daily budget limit
            monthly_limit_usd: New monthly budget limit
            per_agent_daily_usd: New per-agent daily limit
            per_task_max_usd: New per-task maximum
        """
        for key, value in kwargs.items():
            if hasattr(self.budget, key):
                setattr(self.budget, key, value)
                self._modified = True
                logger.info("Budget.%s updated to %s", key, value)
            else:
                raise ValueError(f"Unknown budget parameter: {key}")

    def update_routing(self, **kwargs) -> None:
        """Update routing configuration at runtime."""
        for key, value in kwargs.items():
            if hasattr(self.routing, key):
                setattr(self.routing, key, value)
                self._modified = True
                logger.info("Routing.%s updated to %s", key, value)
            else:
                raise ValueError(f"Unknown routing parameter: {key}")

    def add_agent_profile(self, agent_id: str, profile: dict) -> None:
        """Add or update a per-agent profile override.

        Args:
            agent_id: Agent ID (e.g., "2101")
            profile: Override dict with keys like 'tags', 'max_bounty', etc.
        """
        self.fleet.agent_profiles[str(agent_id)] = profile
        self._modified = True
        logger.info("Agent profile added/updated for %s", agent_id)

    # ─── Validation ───────────────────────────────────────────────────

    def validate(self) -> list:
        """Validate the configuration and return a list of errors.

        Returns an empty list if configuration is valid.
        """
        errors = []

        # Fleet validation
        if self.fleet.max_agents < 1:
            errors.append("fleet.max_agents must be >= 1")
        if self.fleet.max_concurrent_tasks < 1:
            errors.append("fleet.max_concurrent_tasks must be >= 1")
        if self.fleet.cooldown_after_failure_sec < 0:
            errors.append("fleet.cooldown_after_failure_sec must be >= 0")

        # Routing validation
        valid_strategies = ("adaptive", "best_fit", "specialist", "budget_aware", "round_robin")
        if self.routing.default_strategy not in valid_strategies:
            errors.append(
                f"routing.default_strategy must be one of {valid_strategies}, "
                f"got '{self.routing.default_strategy}'"
            )
        if self.routing.max_bounty_usd < self.routing.min_bounty_usd:
            errors.append("routing.max_bounty_usd must be >= routing.min_bounty_usd")
        if self.routing.max_tasks_per_cycle < 1:
            errors.append("routing.max_tasks_per_cycle must be >= 1")
        if not (0.0 <= self.routing.min_reputation_score <= 100.0):
            errors.append("routing.min_reputation_score must be 0-100")

        # Budget validation
        if self.budget.daily_limit_usd <= 0:
            errors.append("budget.daily_limit_usd must be > 0")
        if self.budget.monthly_limit_usd < self.budget.daily_limit_usd:
            errors.append("budget.monthly_limit_usd should be >= budget.daily_limit_usd")
        if self.budget.per_agent_daily_usd > self.budget.daily_limit_usd:
            errors.append("budget.per_agent_daily_usd should be <= budget.daily_limit_usd")
        if not (0.0 <= self.budget.platform_fee_rate <= 1.0):
            errors.append("budget.platform_fee_rate must be 0.0-1.0")
        if not (0.0 <= self.budget.reserve_pct <= 1.0):
            errors.append("budget.reserve_pct must be 0.0-1.0")

        # Daemon validation
        valid_modes = ("passive", "semi-auto", "full-auto")
        if self.daemon.mode not in valid_modes:
            errors.append(f"daemon.mode must be one of {valid_modes}")
        if self.daemon.interval_sec < 10:
            errors.append("daemon.interval_sec must be >= 10 (10 seconds minimum)")
        if self.daemon.max_consecutive_errors < 1:
            errors.append("daemon.max_consecutive_errors must be >= 1")

        # Alerts validation
        if self.alerts.budget_warn_pct >= self.alerts.budget_critical_pct:
            errors.append("alerts.budget_warn_pct must be < alerts.budget_critical_pct")
        if not (0 <= self.alerts.quiet_hours_start <= 23):
            errors.append("alerts.quiet_hours_start must be 0-23")
        if not (0 <= self.alerts.quiet_hours_end <= 23):
            errors.append("alerts.quiet_hours_end must be 0-23")

        # Connection validation
        if not self.connection.em_api_url.startswith("http"):
            errors.append("connection.em_api_url must be a valid HTTP(S) URL")

        # Strategy weights validation
        weights = self.routing.strategy_weights
        if weights:
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                errors.append(
                    f"routing.strategy_weights must sum to ~1.0, got {total:.2f}"
                )
            for name, weight in weights.items():
                if weight < 0:
                    errors.append(f"routing.strategy_weights[{name}] must be >= 0")

        return errors

    # ─── Display ──────────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a human-readable configuration summary."""
        lines = [
            f"SwarmConfig ({self.environment})",
            f"  Mode: {self.daemon.mode}",
            f"  Fleet: {self.fleet.max_agents} agents, "
            f"{self.fleet.max_concurrent_tasks} concurrent tasks/agent",
            f"  Routing: {self.routing.default_strategy} strategy, "
            f"max {self.routing.max_tasks_per_cycle}/cycle",
            f"  Bounty range: ${self.routing.min_bounty_usd:.2f} - "
            f"${self.routing.max_bounty_usd:.2f}",
            f"  Budget: ${self.budget.daily_limit_usd:.2f}/day, "
            f"${self.budget.monthly_limit_usd:.2f}/month",
            f"  Per-agent: ${self.budget.per_agent_daily_usd:.2f}/day, "
            f"fee: {self.budget.platform_fee_rate * 100:.0f}%",
            f"  EM API: {self.connection.em_api_url}",
            f"  AutoJob: {self.connection.autojob_url}",
            f"  Interval: {self.daemon.interval_sec}s",
            f"  Analytics: {'enabled' if self.analytics.enabled else 'disabled'}",
            f"  Alerts: telegram={'on' if self.alerts.enable_telegram else 'off'}, "
            f"quiet={self.alerts.quiet_hours_start:02d}:00-"
            f"{self.alerts.quiet_hours_end:02d}:00",
        ]
        if self._loaded_at:
            lines.append(f"  Loaded: {self._loaded_at.isoformat()}")
        if self._modified:
            lines.append("  ⚠ Modified (unsaved)")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"SwarmConfigManager(env={self.environment!r}, "
            f"mode={self.daemon.mode!r}, "
            f"agents={self.fleet.max_agents}, "
            f"budget=${self.budget.daily_limit_usd:.0f}/day)"
        )

    # ─── Internal Helpers ─────────────────────────────────────────────

    def _apply_dict(self, data: dict) -> None:
        """Apply a configuration dictionary to the current config."""
        if "environment" in data:
            self.environment = data["environment"]

        section_map = {
            "fleet": self.fleet,
            "routing": self.routing,
            "budget": self.budget,
            "alerts": self.alerts,
            "analytics": self.analytics,
            "connection": self.connection,
            "daemon": self.daemon,
        }

        for section_name, section_obj in section_map.items():
            section_data = data.get(section_name, {})
            for key, value in section_data.items():
                if hasattr(section_obj, key):
                    setattr(section_obj, key, value)

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        for env_var, (section, field_name, type_fn) in ENV_OVERRIDES.items():
            value = os.environ.get(env_var)
            if value is not None:
                section_map = {
                    "fleet": self.fleet,
                    "routing": self.routing,
                    "budget": self.budget,
                    "alerts": self.alerts,
                    "analytics": self.analytics,
                    "connection": self.connection,
                    "daemon": self.daemon,
                }
                section_obj = section_map.get(section)
                if section_obj and hasattr(section_obj, field_name):
                    try:
                        typed_value = type_fn(value)
                        setattr(section_obj, field_name, typed_value)
                        logger.debug("Env override: %s=%s", env_var, typed_value)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            "Invalid env var %s=%s: %s", env_var, value, e
                        )

    @staticmethod
    def _dataclass_to_dict(obj) -> dict:
        """Convert a dataclass to dict, handling tuples and other non-JSON types."""
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            if isinstance(value, tuple):
                value = list(value)
            result[field_name] = value
        return result
