"""
Tests for SwarmConfigManager — Centralized Configuration
"""

import json
import os
import tempfile
import pytest
from mcp_server.swarm.config_manager import (
    ConfigManager,
    SwarmConfig,
    Environment,
    ConfigValidationError,
    validate_config,
    _deep_merge,
    _diff_dicts,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def default_config():
    return SwarmConfig()


@pytest.fixture
def config_manager():
    return ConfigManager()


@pytest.fixture
def temp_config_file():
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            {
                "agent_pool": {"max_agents": 12},
                "scheduler": {"cycle_interval_seconds": 15},
                "api": {"base_url": "https://api-test.execution.market"},
            },
            f,
        )
        return f.name


@pytest.fixture(autouse=True)
def clean_env():
    """Clean up env vars after each test."""
    yield
    for key in list(os.environ.keys()):
        if key.startswith("EM_SWARM_"):
            del os.environ[key]
    if "EM_API_KEY" in os.environ:
        del os.environ["EM_API_KEY"]


# ──────────────────────────────────────────────────────────────
# Default Configuration
# ──────────────────────────────────────────────────────────────


class TestDefaults:
    def test_default_environment(self, default_config):
        assert default_config.environment == Environment.PRODUCTION

    def test_default_agent_pool(self, default_config):
        assert default_config.agent_pool.max_agents == 24
        assert default_config.agent_pool.default_daily_budget_usd == 5.0
        assert default_config.agent_pool.cooldown_seconds == 30
        assert default_config.agent_pool.stale_timeout_seconds == 600

    def test_default_scheduler(self, default_config):
        assert default_config.scheduler.cycle_interval_seconds == 30
        assert default_config.scheduler.max_batch_size == 10
        assert default_config.scheduler.retry_max_attempts == 3
        assert default_config.scheduler.circuit_breaker_threshold == 5

    def test_default_coordination(self, default_config):
        assert default_config.coordination.irc_host == "meshrelay.local"
        assert default_config.coordination.irc_port == 6667
        assert default_config.coordination.lock_ttl_seconds == 300

    def test_default_api(self, default_config):
        assert default_config.api.base_url == "https://api.execution.market"
        assert default_config.api.timeout_seconds == 30

    def test_default_reputation(self, default_config):
        # Weights must sum to 1.0
        weights = (
            default_config.reputation.quality_weight
            + default_config.reputation.speed_weight
            + default_config.reputation.reliability_weight
            + default_config.reputation.cost_weight
        )
        assert abs(weights - 1.0) < 0.01

    def test_default_networks(self, default_config):
        assert "base" in default_config.enabled_networks
        assert "ethereum" in default_config.enabled_networks
        assert len(default_config.enabled_networks) == 8

    def test_default_features(self, default_config):
        assert default_config.features["acontext_coordination"] is True
        assert default_config.features["seal_bridge"] is True
        assert default_config.features["autojob_enrichment"] is True


# ──────────────────────────────────────────────────────────────
# Environment Profiles
# ──────────────────────────────────────────────────────────────


class TestEnvironmentProfiles:
    def test_development_profile(self):
        cm = ConfigManager(environment="development")
        config = cm.load()
        assert config.environment == Environment.DEVELOPMENT
        assert config.agent_pool.max_agents == 4
        assert config.agent_pool.default_daily_budget_usd == 1.0
        assert config.logging.level == "DEBUG"

    def test_staging_profile(self):
        cm = ConfigManager(environment="staging")
        config = cm.load()
        assert config.environment == Environment.STAGING
        assert config.agent_pool.max_agents == 8

    def test_test_profile(self):
        cm = ConfigManager(environment="test")
        config = cm.load()
        assert config.environment == Environment.TEST
        assert config.agent_pool.cooldown_seconds == 0
        assert config.scheduler.cycle_interval_seconds == 1

    def test_production_profile_uses_defaults(self):
        cm = ConfigManager(environment="production")
        config = cm.load()
        assert config.environment == Environment.PRODUCTION
        assert config.agent_pool.max_agents == 24

    def test_env_var_environment(self):
        os.environ["EM_SWARM_ENVIRONMENT"] = "staging"
        cm = ConfigManager()
        config = cm.load()
        assert config.environment == Environment.STAGING

    def test_explicit_overrides_env_var(self):
        os.environ["EM_SWARM_ENVIRONMENT"] = "staging"
        cm = ConfigManager(environment="production")
        config = cm.load()
        assert config.environment == Environment.PRODUCTION


# ──────────────────────────────────────────────────────────────
# Config File Loading
# ──────────────────────────────────────────────────────────────


class TestFileLoading:
    def test_load_from_file(self, temp_config_file):
        cm = ConfigManager(config_path=temp_config_file, environment="production")
        config = cm.load()
        assert config.agent_pool.max_agents == 12
        assert config.scheduler.cycle_interval_seconds == 15
        os.unlink(temp_config_file)

    def test_file_overrides_profile(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"agent_pool": {"max_agents": 50}}, f)
            path = f.name
        cm = ConfigManager(config_path=path, environment="development")
        config = cm.load(strict=False)
        # File overrides dev profile (which sets max_agents=4)
        assert config.agent_pool.max_agents == 50
        os.unlink(path)

    def test_missing_file_uses_defaults(self):
        cm = ConfigManager(config_path="/nonexistent/config.json")
        config = cm.load()
        assert config.agent_pool.max_agents == 24


# ──────────────────────────────────────────────────────────────
# Environment Variable Overrides
# ──────────────────────────────────────────────────────────────


class TestEnvOverrides:
    def test_max_agents_override(self):
        os.environ["EM_SWARM_MAX_AGENTS"] = "16"
        cm = ConfigManager(environment="production")
        config = cm.load()
        assert config.agent_pool.max_agents == 16

    def test_daily_budget_override(self):
        os.environ["EM_SWARM_DAILY_BUDGET"] = "10.0"
        cm = ConfigManager(environment="production")
        config = cm.load()
        assert config.agent_pool.default_daily_budget_usd == 10.0

    def test_irc_host_override(self):
        os.environ["EM_SWARM_IRC_HOST"] = "irc.custom.net"
        cm = ConfigManager(environment="production")
        config = cm.load()
        assert config.coordination.irc_host == "irc.custom.net"

    def test_networks_override(self):
        os.environ["EM_SWARM_NETWORKS"] = "base,ethereum"
        cm = ConfigManager(environment="production")
        config = cm.load()
        assert config.enabled_networks == ["base", "ethereum"]

    def test_api_key_from_env(self):
        os.environ["EM_API_KEY"] = "test-key-123"
        cm = ConfigManager(environment="production")
        config = cm.load()
        assert config.api.api_key == "test-key-123"

    def test_invalid_env_var_ignored(self):
        os.environ["EM_SWARM_MAX_AGENTS"] = "not-a-number"
        cm = ConfigManager(environment="production")
        config = cm.load()
        assert config.agent_pool.max_agents == 24  # Default preserved


# ──────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────


class TestValidation:
    def test_default_config_valid(self):
        errors = validate_config(SwarmConfig())
        assert len(errors) == 0

    def test_invalid_max_agents(self):
        config = SwarmConfig()
        config.agent_pool.max_agents = 0
        errors = validate_config(config)
        assert any("max_agents" in e for e in errors)

    def test_excessive_max_agents(self):
        config = SwarmConfig()
        config.agent_pool.max_agents = 200
        errors = validate_config(config)
        assert any("max_agents" in e for e in errors)

    def test_min_healthy_exceeds_max(self):
        config = SwarmConfig()
        config.agent_pool.max_agents = 10
        config.agent_pool.min_healthy_agents = 20
        errors = validate_config(config)
        assert any("min_healthy" in e for e in errors)

    def test_negative_budget(self):
        config = SwarmConfig()
        config.agent_pool.default_daily_budget_usd = -1.0
        errors = validate_config(config)
        assert any("budget" in e.lower() for e in errors)

    def test_invalid_batch_size(self):
        config = SwarmConfig()
        config.scheduler.max_batch_size = 0
        errors = validate_config(config)
        assert any("batch_size" in e for e in errors)

    def test_invalid_circuit_breaker(self):
        config = SwarmConfig()
        config.scheduler.circuit_breaker_threshold = 0
        errors = validate_config(config)
        assert any("circuit_breaker" in e for e in errors)

    def test_invalid_lock_ttl(self):
        config = SwarmConfig()
        config.coordination.lock_ttl_seconds = 5
        errors = validate_config(config)
        assert any("lock_ttl" in e for e in errors)

    def test_invalid_irc_port(self):
        config = SwarmConfig()
        config.coordination.irc_port = 0
        errors = validate_config(config)
        assert any("irc_port" in e for e in errors)

    def test_invalid_api_url(self):
        config = SwarmConfig()
        config.api.base_url = "ftp://not-http"
        errors = validate_config(config)
        assert any("base_url" in e for e in errors)

    def test_reputation_weights_not_summing(self):
        config = SwarmConfig()
        config.reputation.quality_weight = 0.5
        config.reputation.speed_weight = 0.5
        config.reputation.reliability_weight = 0.5
        config.reputation.cost_weight = 0.5
        errors = validate_config(config)
        assert any("weight" in e.lower() for e in errors)

    def test_invalid_score_threshold(self):
        config = SwarmConfig()
        config.reputation.min_score_threshold = 1.5
        errors = validate_config(config)
        assert any("score_threshold" in e for e in errors)

    def test_sla_threshold_ordering(self):
        config = SwarmConfig()
        config.dashboard.sla_critical_threshold = 0.95
        config.dashboard.sla_warning_threshold = 0.90
        errors = validate_config(config)
        assert any("sla_critical" in e for e in errors)

    def test_unknown_networks(self):
        config = SwarmConfig()
        config.enabled_networks = ["base", "ethereum", "mars_chain"]
        errors = validate_config(config)
        assert any("mars_chain" in e for e in errors)

    def test_strict_mode_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"agent_pool": {"max_agents": 0}}, f)
            path = f.name
        cm = ConfigManager(config_path=path, environment="production")
        with pytest.raises(ConfigValidationError):
            cm.load(strict=True)
        os.unlink(path)


# ──────────────────────────────────────────────────────────────
# Serialization
# ──────────────────────────────────────────────────────────────


class TestSerialization:
    def test_to_dict(self, default_config):
        d = default_config.to_dict()
        assert d["environment"] == "production"
        assert d["agent_pool"]["max_agents"] == 24

    def test_from_dict(self):
        data = {
            "environment": "staging",
            "agent_pool": {"max_agents": 16},
            "features": {"seal_bridge": False},
        }
        config = SwarmConfig.from_dict(data)
        assert config.environment == Environment.STAGING
        assert config.agent_pool.max_agents == 16
        assert config.features["seal_bridge"] is False
        # Other features should keep defaults
        assert config.features["acontext_coordination"] is True

    def test_round_trip(self, default_config):
        d = default_config.to_dict()
        restored = SwarmConfig.from_dict(d)
        assert restored.agent_pool.max_agents == default_config.agent_pool.max_agents
        assert restored.api.base_url == default_config.api.base_url


# ──────────────────────────────────────────────────────────────
# Config File Save
# ──────────────────────────────────────────────────────────────


class TestSave:
    def test_save_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            # Load without a pre-existing config file, then save
            cm = ConfigManager(config_path=path, environment="production")
            cm._config_path = None  # Load defaults first
            cm.load()
            cm._config_path = path
            cm.save()
            with open(path) as f:
                saved = json.load(f)
            assert saved["agent_pool"]["max_agents"] == 24

    def test_save_excludes_secrets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            os.environ["EM_API_KEY"] = "super-secret"
            cm = ConfigManager(environment="production")
            cm.load()
            cm._config_path = path
            cm.save()
            with open(path) as f:
                saved = json.load(f)
            assert "api_key" not in saved.get("api", {})


# ──────────────────────────────────────────────────────────────
# Hot Reload
# ──────────────────────────────────────────────────────────────


class TestReload:
    def test_reload_detects_changes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"agent_pool": {"max_agents": 24}}, f)
            path = f.name

        cm = ConfigManager(config_path=path, environment="production")
        cm.load()

        # Modify the file
        with open(path, "w") as f:
            json.dump({"agent_pool": {"max_agents": 16}}, f)

        new_config, changes = cm.reload()
        assert new_config.agent_pool.max_agents == 16
        assert len(changes) > 0
        os.unlink(path)

    def test_reload_notifies_listeners(self):
        changes_received = []

        def listener(config, changes):
            changes_received.extend(changes)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"agent_pool": {"max_agents": 24}}, f)
            path = f.name

        cm = ConfigManager(config_path=path, environment="production")
        cm.load()
        cm.on_change(listener)

        with open(path, "w") as f:
            json.dump({"agent_pool": {"max_agents": 16}}, f)

        cm.reload()
        assert len(changes_received) > 0
        os.unlink(path)

    def test_reload_no_changes(self):
        cm = ConfigManager(environment="production")
        cm.load()
        _, changes = cm.reload()
        assert len(changes) == 0


# ──────────────────────────────────────────────────────────────
# Config Manager Status
# ──────────────────────────────────────────────────────────────


class TestManagerStatus:
    def test_status_before_load(self):
        cm = ConfigManager()
        status = cm.get_status()
        assert status["loaded"] is False

    def test_status_after_load(self):
        cm = ConfigManager(environment="production")
        cm.load()
        status = cm.get_status()
        assert status["loaded"] is True
        assert status["environment"] == "production"
        assert status["reload_count"] == 1

    def test_reload_increments_count(self):
        cm = ConfigManager(environment="production")
        cm.load()
        cm.reload()
        status = cm.get_status()
        assert status["reload_count"] == 2


# ──────────────────────────────────────────────────────────────
# Utility Functions
# ──────────────────────────────────────────────────────────────


class TestUtilities:
    def test_deep_merge_flat(self):
        base = {"a": 1, "b": 2}
        overrides = {"b": 3, "c": 4}
        result = _deep_merge(base, overrides)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        overrides = {"a": {"y": 99, "z": 100}}
        result = _deep_merge(base, overrides)
        assert result["a"]["x"] == 1
        assert result["a"]["y"] == 99
        assert result["a"]["z"] == 100
        assert result["b"] == 3

    def test_diff_dicts_no_changes(self):
        d = {"a": 1, "b": "hello"}
        assert _diff_dicts(d, d) == []

    def test_diff_dicts_value_change(self):
        old = {"a": 1}
        new = {"a": 2}
        diffs = _diff_dicts(old, new)
        assert len(diffs) == 1
        assert "a:" in diffs[0]

    def test_diff_dicts_added_key(self):
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        diffs = _diff_dicts(old, new)
        assert len(diffs) == 1
        assert "added" in diffs[0]

    def test_diff_dicts_removed_key(self):
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        diffs = _diff_dicts(old, new)
        assert len(diffs) == 1
        assert "removed" in diffs[0]

    def test_diff_dicts_nested(self):
        old = {"a": {"x": 1}}
        new = {"a": {"x": 2}}
        diffs = _diff_dicts(old, new)
        assert len(diffs) == 1
        assert "a.x" in diffs[0]
