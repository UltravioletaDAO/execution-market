"""
Tests for SwarmConfigManager — Centralized Configuration with Validation
=========================================================================

Coverage:
1. Default configuration — dataclass defaults, sensible values
2. Environment profiles — dev/staging/prod/test overrides
3. Config from_dict/to_dict — serialization roundtrip
4. Validation — all constraint checks
5. ConfigManager load/reload — file loading, env overrides, secrets
6. Hot reload — change detection, listener notification
7. Config save — file persistence, secret stripping
8. Utility functions — deep_merge, diff_dicts, merge_dataclass
9. Edge cases — missing files, invalid values, concurrent access
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ.setdefault("TESTING", "1")

from swarm.config_manager import (
    Environment,
    AgentPoolConfig,
    SchedulerConfig,
    CoordinationConfig,
    APIConfig,
    ReputationConfig,
    DashboardConfig,
    PersistenceConfig,
    LoggingConfig,
    SwarmConfig,
    ConfigManager,
    ConfigValidationError,
    validate_config,
    _merge_dataclass,
    _deep_merge,
    _diff_dicts,
    ENVIRONMENT_OVERRIDES,
)


# ---------------------------------------------------------------------------
# 1. Default Configuration
# ---------------------------------------------------------------------------


class TestDefaults:
    """Verify sensible defaults on all config dataclasses."""

    def test_agent_pool_defaults(self):
        ap = AgentPoolConfig()
        assert ap.max_agents == 24
        assert ap.min_healthy_agents == 12
        assert ap.default_daily_budget_usd == 5.0
        assert ap.max_task_bounty_usd == 10.0
        assert ap.cooldown_seconds == 30
        assert ap.heartbeat_interval_seconds == 60
        assert ap.stale_timeout_seconds == 600
        assert ap.max_consecutive_failures == 5

    def test_scheduler_defaults(self):
        sc = SchedulerConfig()
        assert sc.cycle_interval_seconds == 30
        assert sc.max_batch_size == 10
        assert sc.urgency_critical_hours == 1.0
        assert sc.retry_max_attempts == 3
        assert sc.circuit_breaker_threshold == 5
        assert sc.load_balancer_max_tasks == 3

    def test_coordination_defaults(self):
        cc = CoordinationConfig()
        assert cc.irc_host == "meshrelay.local"
        assert cc.irc_port == 6667
        assert cc.irc_channel == "#em-swarm"
        assert cc.lock_ttl_seconds == 300
        assert cc.auction_timeout_seconds == 30

    def test_api_defaults(self):
        api = APIConfig()
        assert api.base_url == "https://api.execution.market"
        assert api.api_key == ""
        assert api.timeout_seconds == 30
        assert api.rate_limit_rpm == 60

    def test_reputation_defaults(self):
        rep = ReputationConfig()
        assert rep.erc8004_network == "base"
        total_weight = (
            rep.quality_weight
            + rep.speed_weight
            + rep.reliability_weight
            + rep.cost_weight
        )
        assert abs(total_weight - 1.0) < 0.01

    def test_dashboard_defaults(self):
        db = DashboardConfig()
        assert db.sla_warning_threshold > db.sla_critical_threshold
        assert db.alert_cooldown_seconds == 300

    def test_persistence_defaults(self):
        p = PersistenceConfig()
        assert p.state_dir == ".swarm_state"
        assert p.save_interval_seconds == 60
        assert p.backup_on_save is True

    def test_logging_defaults(self):
        lg = LoggingConfig()
        assert lg.level == "INFO"
        assert lg.file is None

    def test_swarm_config_defaults(self):
        cfg = SwarmConfig()
        assert cfg.environment == Environment.PRODUCTION
        assert cfg.version == "2.0.0"
        assert len(cfg.enabled_networks) == 8
        assert "base" in cfg.enabled_networks
        assert cfg.features["acontext_coordination"] is True

    def test_default_config_validates(self):
        """Default configuration must pass validation."""
        cfg = SwarmConfig()
        errors = validate_config(cfg)
        assert errors == []


# ---------------------------------------------------------------------------
# 2. Environment Profiles
# ---------------------------------------------------------------------------


class TestEnvironmentProfiles:
    """Test environment-specific overrides."""

    def test_development_profile(self):
        overrides = ENVIRONMENT_OVERRIDES[Environment.DEVELOPMENT]
        assert overrides["agent_pool"]["max_agents"] == 4
        assert overrides["api"]["base_url"] == "http://localhost:8000"

    def test_staging_profile(self):
        overrides = ENVIRONMENT_OVERRIDES[Environment.STAGING]
        assert overrides["agent_pool"]["max_agents"] == 8

    def test_test_profile(self):
        overrides = ENVIRONMENT_OVERRIDES[Environment.TEST]
        assert overrides["agent_pool"]["default_daily_budget_usd"] == 0.0
        assert overrides["scheduler"]["cycle_interval_seconds"] == 1

    def test_production_profile_empty(self):
        """Production uses defaults — no overrides."""
        overrides = ENVIRONMENT_OVERRIDES[Environment.PRODUCTION]
        assert overrides == {}

    def test_environment_enum_values(self):
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TEST.value == "test"


# ---------------------------------------------------------------------------
# 3. Config Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    """Test to_dict/from_dict roundtrip."""

    def test_to_dict_produces_valid_json(self):
        cfg = SwarmConfig()
        d = cfg.to_dict()
        # Must be JSON-serializable
        json_str = json.dumps(d, default=str)
        assert isinstance(json_str, str)

    def test_to_dict_includes_all_sections(self):
        cfg = SwarmConfig()
        d = cfg.to_dict()
        assert "agent_pool" in d
        assert "scheduler" in d
        assert "coordination" in d
        assert "api" in d
        assert "reputation" in d
        assert "dashboard" in d
        assert "persistence" in d
        assert "logging" in d
        assert "enabled_networks" in d
        assert "features" in d

    def test_to_dict_environment_is_string(self):
        cfg = SwarmConfig()
        d = cfg.to_dict()
        assert d["environment"] == "production"
        assert isinstance(d["environment"], str)

    def test_from_dict_overrides(self):
        cfg = SwarmConfig.from_dict(
            {
                "agent_pool": {"max_agents": 50},
                "scheduler": {"cycle_interval_seconds": 15},
            }
        )
        assert cfg.agent_pool.max_agents == 50
        assert cfg.scheduler.cycle_interval_seconds == 15
        # Other defaults preserved
        assert cfg.agent_pool.min_healthy_agents == 12

    def test_from_dict_environment(self):
        cfg = SwarmConfig.from_dict({"environment": "development"})
        assert cfg.environment == Environment.DEVELOPMENT

    def test_from_dict_networks(self):
        cfg = SwarmConfig.from_dict({"enabled_networks": ["base", "ethereum"]})
        assert cfg.enabled_networks == ["base", "ethereum"]

    def test_from_dict_features_merge(self):
        """Features should merge, not replace."""
        cfg = SwarmConfig.from_dict({"features": {"new_feature": True}})
        assert cfg.features["new_feature"] is True
        assert cfg.features["acontext_coordination"] is True  # Default preserved

    def test_roundtrip(self):
        cfg1 = SwarmConfig()
        cfg1.agent_pool.max_agents = 42
        d = cfg1.to_dict()
        cfg2 = SwarmConfig.from_dict(d)
        assert cfg2.agent_pool.max_agents == 42

    def test_from_dict_empty(self):
        """Empty dict produces default config."""
        cfg = SwarmConfig.from_dict({})
        assert cfg.agent_pool.max_agents == 24  # Default


# ---------------------------------------------------------------------------
# 4. Validation
# ---------------------------------------------------------------------------


class TestValidation:
    """Test all validation constraints."""

    def test_valid_config_no_errors(self):
        cfg = SwarmConfig()
        assert validate_config(cfg) == []

    def test_agent_pool_max_agents_zero(self):
        cfg = SwarmConfig()
        cfg.agent_pool.max_agents = 0
        errors = validate_config(cfg)
        assert any("max_agents" in e for e in errors)

    def test_agent_pool_max_agents_too_high(self):
        cfg = SwarmConfig()
        cfg.agent_pool.max_agents = 200
        errors = validate_config(cfg)
        assert any("max_agents" in e and "100" in e for e in errors)

    def test_agent_pool_min_exceeds_max(self):
        cfg = SwarmConfig()
        cfg.agent_pool.min_healthy_agents = 30
        cfg.agent_pool.max_agents = 24
        errors = validate_config(cfg)
        assert any("min_healthy_agents" in e for e in errors)

    def test_negative_budget(self):
        cfg = SwarmConfig()
        cfg.agent_pool.default_daily_budget_usd = -1.0
        errors = validate_config(cfg)
        assert any("budget" in e.lower() for e in errors)

    def test_negative_cooldown(self):
        cfg = SwarmConfig()
        cfg.agent_pool.cooldown_seconds = -1
        errors = validate_config(cfg)
        assert any("cooldown" in e for e in errors)

    def test_stale_less_than_heartbeat(self):
        cfg = SwarmConfig()
        cfg.agent_pool.stale_timeout_seconds = 30
        cfg.agent_pool.heartbeat_interval_seconds = 60
        errors = validate_config(cfg)
        assert any("stale_timeout" in e for e in errors)

    def test_scheduler_zero_interval(self):
        cfg = SwarmConfig()
        cfg.scheduler.cycle_interval_seconds = 0
        errors = validate_config(cfg)
        assert any("cycle_interval" in e for e in errors)

    def test_scheduler_zero_batch(self):
        cfg = SwarmConfig()
        cfg.scheduler.max_batch_size = 0
        errors = validate_config(cfg)
        assert any("max_batch" in e for e in errors)

    def test_scheduler_negative_retries(self):
        cfg = SwarmConfig()
        cfg.scheduler.retry_max_attempts = -1
        errors = validate_config(cfg)
        assert any("retry" in e for e in errors)

    def test_scheduler_zero_delay(self):
        cfg = SwarmConfig()
        cfg.scheduler.retry_base_delay_seconds = 0
        errors = validate_config(cfg)
        assert any("delay" in e for e in errors)

    def test_coordination_short_lock(self):
        cfg = SwarmConfig()
        cfg.coordination.lock_ttl_seconds = 5
        errors = validate_config(cfg)
        assert any("lock_ttl" in e for e in errors)

    def test_coordination_zero_auction(self):
        cfg = SwarmConfig()
        cfg.coordination.auction_timeout_seconds = 0
        errors = validate_config(cfg)
        assert any("auction" in e for e in errors)

    def test_coordination_invalid_port(self):
        cfg = SwarmConfig()
        cfg.coordination.irc_port = 0
        errors = validate_config(cfg)
        assert any("irc_port" in e for e in errors)

        cfg.coordination.irc_port = 70000
        errors = validate_config(cfg)
        assert any("irc_port" in e for e in errors)

    def test_api_invalid_url(self):
        cfg = SwarmConfig()
        cfg.api.base_url = "ftp://wrong"
        errors = validate_config(cfg)
        assert any("base_url" in e for e in errors)

    def test_api_short_timeout(self):
        cfg = SwarmConfig()
        cfg.api.timeout_seconds = 0
        errors = validate_config(cfg)
        assert any("timeout" in e for e in errors)

    def test_reputation_weights_dont_sum(self):
        cfg = SwarmConfig()
        cfg.reputation.quality_weight = 0.5
        cfg.reputation.speed_weight = 0.5
        cfg.reputation.reliability_weight = 0.5
        cfg.reputation.cost_weight = 0.5
        errors = validate_config(cfg)
        assert any("weights" in e for e in errors)

    def test_reputation_threshold_out_of_range(self):
        cfg = SwarmConfig()
        cfg.reputation.min_score_threshold = 1.5
        errors = validate_config(cfg)
        assert any("min_score_threshold" in e for e in errors)

    def test_dashboard_sla_inverted(self):
        cfg = SwarmConfig()
        cfg.dashboard.sla_critical_threshold = 0.95
        cfg.dashboard.sla_warning_threshold = 0.90
        errors = validate_config(cfg)
        assert any("sla_critical" in e for e in errors)

    def test_unknown_networks(self):
        cfg = SwarmConfig()
        cfg.enabled_networks = ["base", "unknown_chain", "fake_net"]
        errors = validate_config(cfg)
        assert any("Unknown networks" in e for e in errors)

    def test_multiple_errors_collected(self):
        """Multiple validation errors are all reported."""
        cfg = SwarmConfig()
        cfg.agent_pool.max_agents = 0
        cfg.scheduler.cycle_interval_seconds = 0
        cfg.api.base_url = "not_a_url"
        errors = validate_config(cfg)
        assert len(errors) >= 3


# ---------------------------------------------------------------------------
# 5. ConfigManager Load
# ---------------------------------------------------------------------------


class TestConfigManagerLoad:
    """Test ConfigManager loading from files and env vars."""

    def test_load_defaults(self, monkeypatch):
        monkeypatch.delenv("EM_SWARM_ENVIRONMENT", raising=False)
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        cfg = mgr.load()
        assert isinstance(cfg, SwarmConfig)
        assert cfg.environment == Environment.PRODUCTION

    def test_load_from_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EM_SWARM_ENVIRONMENT", raising=False)
        monkeypatch.delenv("EM_API_KEY", raising=False)
        config_file = tmp_path / "swarm.json"
        config_file.write_text(
            json.dumps(
                {
                    "agent_pool": {"max_agents": 42},
                    "scheduler": {"max_batch_size": 20},
                }
            )
        )
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert cfg.agent_pool.max_agents == 42
        assert cfg.scheduler.max_batch_size == 20

    def test_load_with_environment(self, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager(environment="development")
        cfg = mgr.load()
        assert cfg.environment == Environment.DEVELOPMENT
        assert cfg.agent_pool.max_agents == 4  # Dev override

    def test_env_var_overrides(self, monkeypatch):
        monkeypatch.setenv("EM_SWARM_MAX_AGENTS", "16")
        monkeypatch.setenv("EM_SWARM_IRC_HOST", "custom.irc.host")
        monkeypatch.setenv("EM_SWARM_LOG_LEVEL", "WARNING")
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg.agent_pool.max_agents == 16
        assert cfg.coordination.irc_host == "custom.irc.host"
        assert cfg.logging.level == "WARNING"

    def test_env_var_networks(self, monkeypatch):
        monkeypatch.setenv("EM_SWARM_NETWORKS", "base,ethereum,polygon")
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg.enabled_networks == ["base", "ethereum", "polygon"]

    def test_secret_loading(self, monkeypatch):
        monkeypatch.setenv("EM_API_KEY", "secret-api-key-123")
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg.api.api_key == "secret-api-key-123"

    def test_invalid_env_var_skipped(self, monkeypatch):
        monkeypatch.setenv("EM_SWARM_MAX_AGENTS", "not_a_number")
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg.agent_pool.max_agents == 24  # Default preserved

    def test_nonexistent_file_uses_defaults(self, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager(config_path="/nonexistent/config.json")
        cfg = mgr.load()
        assert cfg.agent_pool.max_agents == 24

    def test_strict_validation_raises(self, monkeypatch):
        monkeypatch.setenv("EM_SWARM_MAX_AGENTS", "0")
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        with pytest.raises(ConfigValidationError):
            mgr.load(strict=True)

    def test_non_strict_validation_allows(self, monkeypatch):
        monkeypatch.setenv("EM_SWARM_MAX_AGENTS", "0")
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        cfg = mgr.load(strict=False)
        assert cfg.agent_pool.max_agents == 0

    def test_config_property_auto_loads(self, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        monkeypatch.delenv("EM_SWARM_ENVIRONMENT", raising=False)
        mgr = ConfigManager()
        cfg = mgr.config
        assert isinstance(cfg, SwarmConfig)

    def test_reload_count(self, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        monkeypatch.delenv("EM_SWARM_ENVIRONMENT", raising=False)
        mgr = ConfigManager()
        mgr.load()
        mgr.load()
        status = mgr.get_status()
        assert status["reload_count"] == 2


# ---------------------------------------------------------------------------
# 6. Hot Reload
# ---------------------------------------------------------------------------


class TestHotReload:
    """Test config reload with change detection."""

    def test_reload_detects_changes(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        config_file = tmp_path / "swarm.json"
        config_file.write_text(
            json.dumps({"agent_pool": {"max_agents": 24, "min_healthy_agents": 8}})
        )

        mgr = ConfigManager(config_path=str(config_file))
        mgr.load()

        # Change config file
        config_file.write_text(
            json.dumps({"agent_pool": {"max_agents": 30, "min_healthy_agents": 8}})
        )
        new_cfg, changes = mgr.reload()

        assert new_cfg.agent_pool.max_agents == 30
        assert len(changes) > 0
        assert any("max_agents" in c for c in changes)

    def test_reload_no_changes(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        config_file = tmp_path / "swarm.json"
        config_file.write_text(json.dumps({"agent_pool": {"max_agents": 24}}))

        mgr = ConfigManager(config_path=str(config_file))
        mgr.load()
        _, changes = mgr.reload()
        assert changes == []

    def test_listener_notified(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        config_file = tmp_path / "swarm.json"
        config_file.write_text(json.dumps({"agent_pool": {"max_agents": 24}}))

        mgr = ConfigManager(config_path=str(config_file))
        mgr.load()

        received = []
        mgr.on_change(lambda cfg, changes: received.append((cfg, changes)))

        config_file.write_text(json.dumps({"agent_pool": {"max_agents": 30}}))
        mgr.reload()

        assert len(received) == 1
        assert received[0][0].agent_pool.max_agents == 30

    def test_listener_error_doesnt_break_reload(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        config_file = tmp_path / "swarm.json"
        config_file.write_text(json.dumps({"agent_pool": {"max_agents": 24}}))

        mgr = ConfigManager(config_path=str(config_file))
        mgr.load()

        def bad_listener(cfg, changes):
            raise RuntimeError("Listener exploded!")

        mgr.on_change(bad_listener)

        config_file.write_text(json.dumps({"agent_pool": {"max_agents": 30}}))
        # Should not raise despite bad listener
        new_cfg, _ = mgr.reload()
        assert new_cfg.agent_pool.max_agents == 30


# ---------------------------------------------------------------------------
# 7. Config Save
# ---------------------------------------------------------------------------


class TestConfigSave:
    """Test saving config to file."""

    def test_save_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager(config_path=str(tmp_path / "out.json"))
        mgr.load()
        mgr.save()
        assert (tmp_path / "out.json").exists()

    def test_save_strips_secrets(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EM_API_KEY", "super-secret-key")
        mgr = ConfigManager(config_path=str(tmp_path / "out.json"))
        mgr.load()
        mgr.save()

        saved = json.loads((tmp_path / "out.json").read_text())
        assert "api_key" not in saved.get("api", {})

    def test_save_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        save_path = str(tmp_path / "roundtrip.json")
        mgr = ConfigManager(config_path=save_path)
        mgr.load()
        mgr.config.agent_pool.max_agents = 99
        mgr.save()

        mgr2 = ConfigManager(config_path=save_path)
        cfg2 = mgr2.load()
        assert cfg2.agent_pool.max_agents == 99

    def test_save_no_path_raises(self, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        mgr.load()
        with pytest.raises(ValueError):
            mgr.save()

    def test_save_no_config_raises(self):
        mgr = ConfigManager(config_path="/tmp/test.json")
        with pytest.raises(ValueError):
            mgr.save()

    def test_save_creates_directories(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        deep_path = str(tmp_path / "a" / "b" / "c" / "config.json")
        mgr = ConfigManager(config_path=deep_path)
        mgr.load()
        mgr.save()
        assert Path(deep_path).exists()


# ---------------------------------------------------------------------------
# 8. Utility Functions
# ---------------------------------------------------------------------------


class TestUtilities:
    """Test utility functions."""

    def test_deep_merge_simple(self):
        base = {"a": 1, "b": 2}
        _deep_merge(base, {"b": 3, "c": 4})
        assert base == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        _deep_merge(base, {"a": {"y": 99, "z": 100}})
        assert base["a"]["x"] == 1
        assert base["a"]["y"] == 99
        assert base["a"]["z"] == 100
        assert base["b"] == 3

    def test_deep_merge_replace_non_dict(self):
        base = {"a": [1, 2, 3]}
        _deep_merge(base, {"a": [4, 5]})
        assert base["a"] == [4, 5]

    def test_diff_dicts_no_changes(self):
        d = {"a": 1, "b": {"c": 2}}
        assert _diff_dicts(d, d) == []

    def test_diff_dicts_value_change(self):
        old = {"a": 1}
        new = {"a": 2}
        changes = _diff_dicts(old, new)
        assert len(changes) == 1
        assert "a:" in changes[0]

    def test_diff_dicts_added_key(self):
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        changes = _diff_dicts(old, new)
        assert len(changes) == 1
        assert "added" in changes[0]

    def test_diff_dicts_removed_key(self):
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        changes = _diff_dicts(old, new)
        assert len(changes) == 1
        assert "removed" in changes[0]

    def test_diff_dicts_nested(self):
        old = {"a": {"b": 1, "c": 2}}
        new = {"a": {"b": 1, "c": 99}}
        changes = _diff_dicts(old, new)
        assert len(changes) == 1
        assert "a.c:" in changes[0]

    def test_merge_dataclass(self):
        ap = _merge_dataclass(
            AgentPoolConfig, {"max_agents": 50, "cooldown_seconds": 10}
        )
        assert ap.max_agents == 50
        assert ap.cooldown_seconds == 10
        assert ap.min_healthy_agents == 12  # Default

    def test_merge_dataclass_unknown_key_ignored(self):
        ap = _merge_dataclass(AgentPoolConfig, {"unknown_field": 99})
        assert not hasattr(ap, "unknown_field") or ap.max_agents == 24


# ---------------------------------------------------------------------------
# 9. Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_environment_from_env_var(self, monkeypatch):
        monkeypatch.setenv("EM_SWARM_ENVIRONMENT", "staging")
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg.environment == Environment.STAGING

    def test_invalid_environment_defaults_to_production(self, monkeypatch):
        monkeypatch.setenv("EM_SWARM_ENVIRONMENT", "invalid_env")
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg.environment == Environment.PRODUCTION

    def test_explicit_env_overrides_env_var(self, monkeypatch):
        monkeypatch.setenv("EM_SWARM_ENVIRONMENT", "staging")
        monkeypatch.delenv("EM_API_KEY", raising=False)
        mgr = ConfigManager(environment="development")
        cfg = mgr.load()
        assert cfg.environment == Environment.DEVELOPMENT

    def test_get_status_before_load(self):
        mgr = ConfigManager()
        status = mgr.get_status()
        assert status["loaded"] is False
        assert status["environment"] is None

    def test_get_status_after_load(self, monkeypatch):
        monkeypatch.delenv("EM_API_KEY", raising=False)
        monkeypatch.delenv("EM_SWARM_ENVIRONMENT", raising=False)
        mgr = ConfigManager()
        mgr.load()
        status = mgr.get_status()
        assert status["loaded"] is True
        assert status["environment"] == "production"
        assert status["reload_count"] == 1

    def test_file_overrides_profile(self, tmp_path, monkeypatch):
        """File settings override environment profile settings."""
        monkeypatch.delenv("EM_API_KEY", raising=False)
        config_file = tmp_path / "swarm.json"
        # Dev profile sets max_agents=4, but file sets max_agents=15
        config_file.write_text(json.dumps({"agent_pool": {"max_agents": 15}}))

        mgr = ConfigManager(config_path=str(config_file), environment="development")
        cfg = mgr.load()
        assert cfg.agent_pool.max_agents == 15  # File wins

    def test_config_validation_error_contains_errors(self):
        err = ConfigValidationError(["error1", "error2"])
        assert len(err.errors) == 2
        assert "error1" in str(err)

    def test_empty_config_file(self, tmp_path, monkeypatch):
        """Empty JSON object in config file works."""
        monkeypatch.delenv("EM_API_KEY", raising=False)
        config_file = tmp_path / "empty.json"
        config_file.write_text("{}")
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert cfg.agent_pool.max_agents == 24  # Default


# ---------------------------------------------------------------------------
# 10. Integration: Full Config Lifecycle
# ---------------------------------------------------------------------------


class TestConfigLifecycle:
    """End-to-end configuration lifecycle."""

    def test_full_lifecycle(self, tmp_path, monkeypatch):
        """Load → modify → save → reload → verify."""
        monkeypatch.delenv("EM_API_KEY", raising=False)
        config_path = str(tmp_path / "lifecycle.json")

        # 1. Load defaults
        mgr = ConfigManager(config_path=config_path)
        cfg = mgr.load()
        assert cfg.agent_pool.max_agents == 24

        # 2. Modify
        mgr.config.agent_pool.max_agents = 32

        # 3. Save
        mgr.save()

        # 4. Create new manager, reload
        mgr2 = ConfigManager(config_path=config_path)
        cfg2 = mgr2.load()
        assert cfg2.agent_pool.max_agents == 32

    def test_config_with_all_env_profiles(self, monkeypatch):
        """All environment profiles produce valid configs."""
        monkeypatch.delenv("EM_API_KEY", raising=False)
        for env in Environment:
            mgr = ConfigManager(environment=env.value)
            cfg = mgr.load(strict=False)
            errors = validate_config(cfg)
            assert errors == [], f"{env.value} profile has validation errors: {errors}"
