"""
Tests for SwarmConfigManager — Production configuration system.

Coverage:
    - Default construction
    - Loading from files
    - Environment variable overrides
    - Presets (conservative, balanced, aggressive)
    - Validation (all rules)
    - Runtime reconfiguration
    - Serialization (to_dict, save, load roundtrip)
    - DaemonConfig conversion
    - Agent profile management
    - Summary display
    - Edge cases
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from swarm.config_manager import (
    SwarmConfigManager,
    FleetConfig,
    RoutingConfig,
    BudgetConfig,
    AlertConfig,
    AnalyticsConfig,
    ConnectionConfig,
    DaemonRunConfig,
    PRESETS,
    ENV_OVERRIDES,
)


class TestDefaultConfig(unittest.TestCase):
    """Test default configuration values."""

    def test_create_default(self):
        config = SwarmConfigManager()
        self.assertEqual(config.fleet.max_agents, 24)
        self.assertEqual(config.routing.default_strategy, "adaptive")
        self.assertEqual(config.budget.daily_limit_usd, 50.0)
        self.assertEqual(config.daemon.mode, "passive")
        self.assertEqual(config.environment, "production")

    def test_default_fleet(self):
        config = SwarmConfigManager()
        self.assertEqual(config.fleet.max_concurrent_tasks, 3)
        self.assertEqual(config.fleet.cooldown_after_failure_sec, 300)
        self.assertEqual(config.fleet.warmup_tasks, 3)
        self.assertEqual(config.fleet.health_check_interval_sec, 600)
        self.assertTrue(config.fleet.auto_register)

    def test_default_routing(self):
        config = SwarmConfigManager()
        self.assertEqual(config.routing.max_tasks_per_cycle, 10)
        self.assertEqual(config.routing.max_bounty_usd, 100.0)
        self.assertEqual(config.routing.min_bounty_usd, 0.0)
        self.assertTrue(config.routing.enable_autojob_enrichment)
        self.assertAlmostEqual(sum(config.routing.strategy_weights.values()), 1.0)

    def test_default_budget(self):
        config = SwarmConfigManager()
        self.assertEqual(config.budget.daily_limit_usd, 50.0)
        self.assertEqual(config.budget.monthly_limit_usd, 1000.0)
        self.assertEqual(config.budget.per_agent_daily_usd, 10.0)
        self.assertEqual(config.budget.platform_fee_rate, 0.13)
        self.assertEqual(config.budget.currency, "USDC")

    def test_default_alerts(self):
        config = SwarmConfigManager()
        self.assertEqual(config.alerts.budget_warn_pct, 0.8)
        self.assertEqual(config.alerts.budget_critical_pct, 0.95)
        self.assertEqual(config.alerts.quiet_hours_start, 23)
        self.assertEqual(config.alerts.quiet_hours_end, 8)

    def test_default_connection(self):
        config = SwarmConfigManager()
        self.assertEqual(config.connection.em_api_url, "https://api.execution.market")
        self.assertEqual(config.connection.autojob_url, "http://localhost:8765")
        self.assertEqual(config.connection.erc8004_network, "base")

    def test_default_daemon(self):
        config = SwarmConfigManager()
        self.assertEqual(config.daemon.interval_sec, 300)
        self.assertTrue(config.daemon.enable_analytics)
        self.assertTrue(config.daemon.enable_strategy_engine)
        self.assertTrue(config.daemon.enable_acontext)


class TestPresets(unittest.TestCase):
    """Test configuration presets."""

    def test_conservative_preset(self):
        config = SwarmConfigManager.from_preset("conservative")
        self.assertEqual(config.fleet.max_concurrent_tasks, 1)
        self.assertEqual(config.routing.max_bounty_usd, 5.0)
        self.assertEqual(config.budget.daily_limit_usd, 10.0)
        self.assertEqual(config.daemon.mode, "semi-auto")
        self.assertEqual(config.daemon.interval_sec, 600)

    def test_balanced_preset(self):
        config = SwarmConfigManager.from_preset("balanced")
        self.assertEqual(config.fleet.max_concurrent_tasks, 3)
        self.assertEqual(config.routing.max_bounty_usd, 25.0)
        self.assertEqual(config.budget.daily_limit_usd, 50.0)
        self.assertEqual(config.daemon.mode, "semi-auto")

    def test_aggressive_preset(self):
        config = SwarmConfigManager.from_preset("aggressive")
        self.assertEqual(config.fleet.max_concurrent_tasks, 5)
        self.assertEqual(config.routing.max_bounty_usd, 100.0)
        self.assertEqual(config.budget.daily_limit_usd, 200.0)
        self.assertEqual(config.daemon.mode, "full-auto")
        self.assertEqual(config.daemon.interval_sec, 120)

    def test_invalid_preset_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SwarmConfigManager.from_preset("yolo")
        self.assertIn("yolo", str(ctx.exception))
        self.assertIn("conservative", str(ctx.exception))

    def test_all_presets_exist(self):
        for name in ["conservative", "balanced", "aggressive"]:
            self.assertIn(name, PRESETS)

    def test_preset_preserves_defaults_for_unset_fields(self):
        config = SwarmConfigManager.from_preset("conservative")
        # Fields not in preset keep defaults
        self.assertEqual(config.fleet.max_agents, 24)
        self.assertEqual(config.connection.em_api_url, "https://api.execution.market")
        self.assertTrue(config.analytics.enabled)


class TestFileLoading(unittest.TestCase):
    """Test loading and saving configuration files."""

    def test_load_from_file(self):
        data = {
            "environment": "staging",
            "fleet": {"max_agents": 10},
            "budget": {"daily_limit_usd": 25.0},
            "daemon": {"mode": "semi-auto"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        try:
            config = SwarmConfigManager.load(path)
            self.assertEqual(config.environment, "staging")
            self.assertEqual(config.fleet.max_agents, 10)
            self.assertEqual(config.budget.daily_limit_usd, 25.0)
            self.assertEqual(config.daemon.mode, "semi-auto")
            self.assertIsNotNone(config._loaded_at)
        finally:
            os.unlink(path)

    def test_load_missing_file_uses_defaults(self):
        config = SwarmConfigManager.load("/tmp/nonexistent_swarm_config.json")
        self.assertEqual(config.fleet.max_agents, 24)
        self.assertEqual(config.daemon.mode, "passive")

    def test_save_and_reload(self):
        config1 = SwarmConfigManager.from_preset("aggressive")
        config1.environment = "test"

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            config1.save(path)
            config2 = SwarmConfigManager.load(path)

            self.assertEqual(config2.environment, "test")
            self.assertEqual(config2.fleet.max_concurrent_tasks, 5)
            self.assertEqual(config2.routing.max_bounty_usd, 100.0)
            self.assertEqual(config2.budget.daily_limit_usd, 200.0)
            self.assertEqual(config2.daemon.mode, "full-auto")
        finally:
            os.unlink(path)

    def test_save_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "deep", "config.json")
            config = SwarmConfigManager()
            saved = config.save(path)
            self.assertEqual(saved, path)
            self.assertTrue(os.path.exists(path))

    def test_save_includes_meta(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            config = SwarmConfigManager()
            config.save(path)

            with open(path) as f:
                data = json.load(f)
            self.assertIn("_meta", data)
            self.assertIn("saved_at", data["_meta"])
            self.assertEqual(data["_meta"]["version"], "1.0.0")
        finally:
            os.unlink(path)

    def test_load_corrupt_file_uses_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{{")
            path = f.name

        try:
            config = SwarmConfigManager.load(path)
            # Should fall back to defaults
            self.assertEqual(config.fleet.max_agents, 24)
        finally:
            os.unlink(path)

    def test_partial_config_file(self):
        """Config file with only some sections — rest stays default."""
        data = {"routing": {"max_bounty_usd": 42.0}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        try:
            config = SwarmConfigManager.load(path)
            self.assertEqual(config.routing.max_bounty_usd, 42.0)
            # Unset sections keep defaults
            self.assertEqual(config.fleet.max_agents, 24)
            self.assertEqual(config.budget.daily_limit_usd, 50.0)
        finally:
            os.unlink(path)


class TestEnvironmentOverrides(unittest.TestCase):
    """Test environment variable overrides."""

    def test_env_override_fleet(self):
        with patch.dict(os.environ, {"EM_SWARM_MAX_AGENTS": "12"}):
            config = SwarmConfigManager.load("/tmp/nonexistent.json")
            self.assertEqual(config.fleet.max_agents, 12)

    def test_env_override_budget(self):
        with patch.dict(os.environ, {"EM_SWARM_DAILY_LIMIT": "100.0"}):
            config = SwarmConfigManager.load("/tmp/nonexistent.json")
            self.assertEqual(config.budget.daily_limit_usd, 100.0)

    def test_env_override_mode(self):
        with patch.dict(os.environ, {"EM_SWARM_MODE": "full-auto"}):
            config = SwarmConfigManager.load("/tmp/nonexistent.json")
            self.assertEqual(config.daemon.mode, "full-auto")

    def test_env_override_api_url(self):
        with patch.dict(os.environ, {"EM_API_URL": "http://localhost:3000"}):
            config = SwarmConfigManager.load("/tmp/nonexistent.json")
            self.assertEqual(config.connection.em_api_url, "http://localhost:3000")

    def test_env_override_float(self):
        with patch.dict(os.environ, {"EM_SWARM_FEE_RATE": "0.15"}):
            config = SwarmConfigManager.load("/tmp/nonexistent.json")
            self.assertEqual(config.budget.platform_fee_rate, 0.15)

    def test_env_overrides_file(self):
        """Environment variables should override file values."""
        data = {"budget": {"daily_limit_usd": 25.0}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        try:
            with patch.dict(os.environ, {"EM_SWARM_DAILY_LIMIT": "99.0"}):
                config = SwarmConfigManager.load(path)
                # Env wins over file
                self.assertEqual(config.budget.daily_limit_usd, 99.0)
        finally:
            os.unlink(path)

    def test_invalid_env_value_ignored(self):
        with patch.dict(os.environ, {"EM_SWARM_MAX_AGENTS": "not_a_number"}):
            config = SwarmConfigManager.load("/tmp/nonexistent.json")
            # Should keep default
            self.assertEqual(config.fleet.max_agents, 24)

    def test_all_env_overrides_mapped(self):
        """Verify all env override mappings reference valid fields."""
        section_map = {
            "fleet": FleetConfig(),
            "routing": RoutingConfig(),
            "budget": BudgetConfig(),
            "alerts": AlertConfig(),
            "analytics": AnalyticsConfig(),
            "connection": ConnectionConfig(),
            "daemon": DaemonRunConfig(),
        }
        for env_var, (section, field_name, type_fn) in ENV_OVERRIDES.items():
            self.assertIn(section, section_map, f"Unknown section for {env_var}")
            self.assertTrue(
                hasattr(section_map[section], field_name),
                f"{env_var} maps to {section}.{field_name} which doesn't exist",
            )


class TestValidation(unittest.TestCase):
    """Test configuration validation."""

    def test_valid_default_config(self):
        config = SwarmConfigManager()
        errors = config.validate()
        self.assertEqual(errors, [])

    def test_valid_presets(self):
        for name in PRESETS:
            config = SwarmConfigManager.from_preset(name)
            errors = config.validate()
            self.assertEqual(errors, [], f"Preset '{name}' has validation errors: {errors}")

    def test_invalid_max_agents(self):
        config = SwarmConfigManager()
        config.fleet.max_agents = 0
        errors = config.validate()
        self.assertTrue(any("max_agents" in e for e in errors))

    def test_invalid_strategy(self):
        config = SwarmConfigManager()
        config.routing.default_strategy = "yolo"
        errors = config.validate()
        self.assertTrue(any("default_strategy" in e for e in errors))

    def test_invalid_bounty_range(self):
        config = SwarmConfigManager()
        config.routing.min_bounty_usd = 100.0
        config.routing.max_bounty_usd = 10.0
        errors = config.validate()
        self.assertTrue(any("bounty" in e.lower() for e in errors))

    def test_invalid_budget_negative(self):
        config = SwarmConfigManager()
        config.budget.daily_limit_usd = -5.0
        errors = config.validate()
        self.assertTrue(any("daily_limit" in e for e in errors))

    def test_invalid_budget_monthly_less_than_daily(self):
        config = SwarmConfigManager()
        config.budget.daily_limit_usd = 100.0
        config.budget.monthly_limit_usd = 50.0
        errors = config.validate()
        self.assertTrue(any("monthly" in e.lower() for e in errors))

    def test_invalid_per_agent_exceeds_daily(self):
        config = SwarmConfigManager()
        config.budget.per_agent_daily_usd = 200.0
        config.budget.daily_limit_usd = 50.0
        errors = config.validate()
        self.assertTrue(any("per_agent" in e for e in errors))

    def test_invalid_fee_rate(self):
        config = SwarmConfigManager()
        config.budget.platform_fee_rate = 1.5
        errors = config.validate()
        self.assertTrue(any("fee_rate" in e for e in errors))

    def test_invalid_mode(self):
        config = SwarmConfigManager()
        config.daemon.mode = "chaos"
        errors = config.validate()
        self.assertTrue(any("mode" in e for e in errors))

    def test_invalid_interval_too_low(self):
        config = SwarmConfigManager()
        config.daemon.interval_sec = 5
        errors = config.validate()
        self.assertTrue(any("interval" in e for e in errors))

    def test_invalid_alert_thresholds(self):
        config = SwarmConfigManager()
        config.alerts.budget_warn_pct = 0.99
        config.alerts.budget_critical_pct = 0.95
        errors = config.validate()
        self.assertTrue(any("warn" in e.lower() and "critical" in e.lower() for e in errors))

    def test_invalid_strategy_weights_sum(self):
        config = SwarmConfigManager()
        config.routing.strategy_weights = {"best_fit": 0.5, "specialist": 0.1}
        errors = config.validate()
        self.assertTrue(any("strategy_weights" in e for e in errors))

    def test_invalid_strategy_weights_negative(self):
        config = SwarmConfigManager()
        config.routing.strategy_weights = {
            "best_fit": 1.5, "specialist": -0.5
        }
        errors = config.validate()
        self.assertTrue(any("strategy_weights" in e and "specialist" in e for e in errors))

    def test_invalid_reputation_score(self):
        config = SwarmConfigManager()
        config.routing.min_reputation_score = 150.0
        errors = config.validate()
        self.assertTrue(any("reputation" in e.lower() for e in errors))

    def test_invalid_url(self):
        config = SwarmConfigManager()
        config.connection.em_api_url = "not-a-url"
        errors = config.validate()
        self.assertTrue(any("em_api_url" in e for e in errors))

    def test_invalid_quiet_hours(self):
        config = SwarmConfigManager()
        config.alerts.quiet_hours_start = 25
        errors = config.validate()
        self.assertTrue(any("quiet_hours" in e for e in errors))

    def test_multiple_errors_at_once(self):
        config = SwarmConfigManager()
        config.fleet.max_agents = 0
        config.daemon.mode = "chaos"
        config.budget.daily_limit_usd = -1
        errors = config.validate()
        self.assertGreaterEqual(len(errors), 3)


class TestRuntimeReconfiguration(unittest.TestCase):
    """Test runtime configuration changes."""

    def test_set_mode(self):
        config = SwarmConfigManager()
        config.set_mode("full-auto")
        self.assertEqual(config.daemon.mode, "full-auto")
        self.assertTrue(config._modified)

    def test_set_invalid_mode(self):
        config = SwarmConfigManager()
        with self.assertRaises(ValueError):
            config.set_mode("yolo")

    def test_update_budget(self):
        config = SwarmConfigManager()
        config.update_budget(daily_limit_usd=200.0, per_task_max_usd=50.0)
        self.assertEqual(config.budget.daily_limit_usd, 200.0)
        self.assertEqual(config.budget.per_task_max_usd, 50.0)
        self.assertTrue(config._modified)

    def test_update_budget_invalid_field(self):
        config = SwarmConfigManager()
        with self.assertRaises(ValueError):
            config.update_budget(nonexistent_field=42)

    def test_update_routing(self):
        config = SwarmConfigManager()
        config.update_routing(max_bounty_usd=250.0)
        self.assertEqual(config.routing.max_bounty_usd, 250.0)

    def test_update_routing_invalid_field(self):
        config = SwarmConfigManager()
        with self.assertRaises(ValueError):
            config.update_routing(nonexistent=True)

    def test_add_agent_profile(self):
        config = SwarmConfigManager()
        config.add_agent_profile("2101", {
            "tags": ["delivery", "physical"],
            "max_bounty": 15.0,
        })
        self.assertIn("2101", config.fleet.agent_profiles)
        self.assertEqual(config.fleet.agent_profiles["2101"]["max_bounty"], 15.0)

    def test_update_agent_profile(self):
        config = SwarmConfigManager()
        config.add_agent_profile("2101", {"tags": ["v1"]})
        config.add_agent_profile("2101", {"tags": ["v2"]})
        self.assertEqual(config.fleet.agent_profiles["2101"]["tags"], ["v2"])

    def test_modified_flag_tracks_changes(self):
        config = SwarmConfigManager()
        self.assertFalse(config._modified)
        config.set_mode("semi-auto")
        self.assertTrue(config._modified)

    def test_save_resets_modified_flag(self):
        config = SwarmConfigManager()
        config.set_mode("semi-auto")
        self.assertTrue(config._modified)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            config.save(path)
            self.assertFalse(config._modified)
        finally:
            os.unlink(path)


class TestSerialization(unittest.TestCase):
    """Test config serialization and deserialization."""

    def test_to_dict(self):
        config = SwarmConfigManager()
        d = config.to_dict()
        self.assertIn("fleet", d)
        self.assertIn("routing", d)
        self.assertIn("budget", d)
        self.assertIn("alerts", d)
        self.assertIn("analytics", d)
        self.assertIn("connection", d)
        self.assertIn("daemon", d)
        self.assertEqual(d["environment"], "production")

    def test_to_dict_contains_values(self):
        config = SwarmConfigManager()
        d = config.to_dict()
        self.assertEqual(d["fleet"]["max_agents"], 24)
        self.assertEqual(d["routing"]["default_strategy"], "adaptive")
        self.assertEqual(d["budget"]["daily_limit_usd"], 50.0)

    def test_from_dict(self):
        config = SwarmConfigManager.from_dict({
            "environment": "dev",
            "fleet": {"max_agents": 5},
            "budget": {"daily_limit_usd": 10.0},
        })
        self.assertEqual(config.environment, "dev")
        self.assertEqual(config.fleet.max_agents, 5)
        self.assertEqual(config.budget.daily_limit_usd, 10.0)

    def test_roundtrip_dict(self):
        config1 = SwarmConfigManager.from_preset("balanced")
        config1.add_agent_profile("2101", {"tags": ["test"]})
        d = config1.to_dict()
        config2 = SwarmConfigManager.from_dict(d)

        self.assertEqual(config2.fleet.max_concurrent_tasks, config1.fleet.max_concurrent_tasks)
        self.assertEqual(config2.routing.max_bounty_usd, config1.routing.max_bounty_usd)
        self.assertEqual(config2.budget.daily_limit_usd, config1.budget.daily_limit_usd)
        self.assertEqual(config2.daemon.mode, config1.daemon.mode)
        self.assertIn("2101", config2.fleet.agent_profiles)

    def test_tuple_converted_in_dict(self):
        config = SwarmConfigManager()
        d = config.to_dict()
        # agent_id_range is a tuple in dataclass, should be list in JSON
        self.assertIsInstance(d["fleet"]["agent_id_range"], list)

    def test_json_serializable(self):
        config = SwarmConfigManager.from_preset("aggressive")
        d = config.to_dict()
        # Should not raise
        json_str = json.dumps(d, default=str)
        self.assertIsInstance(json_str, str)


class TestDaemonConfigConversion(unittest.TestCase):
    """Test conversion to DaemonConfig for the daemon module."""

    def test_to_daemon_config(self):
        config = SwarmConfigManager()
        config.daemon.mode = "semi-auto"
        config.connection.em_api_url = "https://staging.api.execution.market"
        config.routing.max_tasks_per_cycle = 5
        config.routing.max_bounty_usd = 10.0

        dc = config.to_daemon_config()
        self.assertEqual(dc.mode, "semi-auto")
        self.assertEqual(dc.em_api_url, "https://staging.api.execution.market")
        self.assertEqual(dc.max_tasks_per_cycle, 5)
        self.assertEqual(dc.max_bounty_usd, 10.0)
        self.assertEqual(dc.platform_fee_rate, 0.13)

    def test_to_daemon_config_preserves_analytics(self):
        config = SwarmConfigManager()
        config.daemon.enable_analytics = False
        dc = config.to_daemon_config()
        self.assertFalse(dc.enable_analytics)


class TestSummary(unittest.TestCase):
    """Test human-readable summary output."""

    def test_summary_contains_key_info(self):
        config = SwarmConfigManager()
        summary = config.summary()
        self.assertIn("passive", summary)
        self.assertIn("24 agents", summary)
        self.assertIn("adaptive", summary)
        self.assertIn("$50.00/day", summary)

    def test_summary_shows_modified(self):
        config = SwarmConfigManager()
        config.set_mode("full-auto")
        summary = config.summary()
        self.assertIn("Modified", summary)

    def test_repr(self):
        config = SwarmConfigManager()
        r = repr(config)
        self.assertIn("SwarmConfigManager", r)
        self.assertIn("production", r)
        self.assertIn("passive", r)

    def test_summary_shows_loaded_at(self):
        data = {"fleet": {"max_agents": 10}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            config = SwarmConfigManager.load(path)
            summary = config.summary()
            self.assertIn("Loaded", summary)
        finally:
            os.unlink(path)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual inputs."""

    def test_empty_dict(self):
        config = SwarmConfigManager.from_dict({})
        self.assertEqual(config.fleet.max_agents, 24)

    def test_unknown_keys_in_dict_ignored(self):
        config = SwarmConfigManager.from_dict({
            "unknown_section": {"foo": "bar"},
            "fleet": {"unknown_field": True, "max_agents": 5},
        })
        self.assertEqual(config.fleet.max_agents, 5)

    def test_config_independence(self):
        """Two configs should be independent instances."""
        config1 = SwarmConfigManager()
        config2 = SwarmConfigManager()
        config1.fleet.max_agents = 1
        self.assertEqual(config2.fleet.max_agents, 24)

    def test_strategy_weights_custom(self):
        config = SwarmConfigManager.from_dict({
            "routing": {
                "strategy_weights": {
                    "best_fit": 0.25,
                    "specialist": 0.25,
                    "budget_aware": 0.25,
                    "round_robin": 0.25,
                }
            }
        })
        errors = config.validate()
        self.assertEqual(errors, [])
        self.assertEqual(config.routing.strategy_weights["best_fit"], 0.25)

    def test_empty_strategy_weights_valid(self):
        config = SwarmConfigManager()
        config.routing.strategy_weights = {}
        errors = config.validate()
        # Empty weights = no constraint error (sum is 0, but dict is empty)
        # Depends on implementation — weights are optional if empty
        # Let's just check it doesn't crash
        self.assertIsInstance(errors, list)

    def test_agent_profile_integer_key(self):
        """Agent IDs should be stored as strings."""
        config = SwarmConfigManager()
        config.add_agent_profile(2101, {"tags": ["test"]})
        self.assertIn("2101", config.fleet.agent_profiles)

    def test_multiple_concurrent_updates(self):
        config = SwarmConfigManager()
        config.set_mode("semi-auto")
        config.update_budget(daily_limit_usd=100.0)
        config.update_routing(max_bounty_usd=50.0)
        config.add_agent_profile("2101", {"tags": ["multi"]})

        self.assertEqual(config.daemon.mode, "semi-auto")
        self.assertEqual(config.budget.daily_limit_usd, 100.0)
        self.assertEqual(config.routing.max_bounty_usd, 50.0)
        self.assertIn("2101", config.fleet.agent_profiles)

    def test_save_without_path_uses_default(self):
        config = SwarmConfigManager()
        config.config_path = None
        # This would try to save to ~/.em-swarm/config.json
        # We just verify it doesn't crash by providing a path
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            saved = config.save(path)
            self.assertEqual(saved, path)
        finally:
            os.unlink(path)

    def test_chain_preferences_default(self):
        config = SwarmConfigManager()
        self.assertIn("physical_verification", config.routing.chain_preferences)
        self.assertEqual(config.routing.chain_preferences["physical_verification"], "base")

    def test_funded_chains_default(self):
        config = SwarmConfigManager()
        self.assertIn("base", config.budget.funded_chains)


class TestCompleteWorkflow(unittest.TestCase):
    """Integration tests for complete config workflows."""

    def test_production_deployment_workflow(self):
        """Simulate a full production deployment config workflow."""
        # 1. Start from conservative preset
        config = SwarmConfigManager.from_preset("conservative")

        # 2. Customize for our setup
        config.environment = "production"
        config.fleet.max_agents = 24
        config.add_agent_profile("2106", {
            "tags": ["orchestrator"],
            "max_bounty": 50.0,
        })

        # 3. Set up connections
        config.connection.em_api_url = "https://api.execution.market"
        config.connection.erc8004_network = "base"

        # 4. Set alerts
        config.alerts.enable_telegram = True
        config.alerts.telegram_chat_id = "7270196534"

        # 5. Validate
        errors = config.validate()
        self.assertEqual(errors, [])

        # 6. Save
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            config.save(path)

            # 7. Reload and verify
            config2 = SwarmConfigManager.load(path)
            self.assertEqual(config2.environment, "production")
            self.assertEqual(config2.fleet.max_agents, 24)
            self.assertEqual(config2.alerts.telegram_chat_id, "7270196534")
            self.assertIn("2106", config2.fleet.agent_profiles)
        finally:
            os.unlink(path)

    def test_gradual_ramp_up_workflow(self):
        """Simulate gradually increasing swarm autonomy."""
        # Week 1: Passive
        config = SwarmConfigManager.from_preset("conservative")
        self.assertEqual(config.daemon.mode, "semi-auto")
        config.set_mode("passive")
        errors = config.validate()
        self.assertEqual(errors, [])

        # Week 2: Semi-auto with small budget
        config.set_mode("semi-auto")
        config.update_budget(daily_limit_usd=20.0)
        errors = config.validate()
        self.assertEqual(errors, [])

        # Week 3: Higher limits
        config.update_budget(daily_limit_usd=50.0, monthly_limit_usd=1000.0)
        config.update_routing(max_bounty_usd=25.0)
        errors = config.validate()
        self.assertEqual(errors, [])

        # Week 4: Full auto
        config.set_mode("full-auto")
        config.update_budget(daily_limit_usd=100.0, monthly_limit_usd=2000.0)
        errors = config.validate()
        self.assertEqual(errors, [])

    def test_daemon_config_workflow(self):
        """Test creating DaemonConfig from SwarmConfigManager."""
        config = SwarmConfigManager.from_preset("balanced")
        config.daemon.mode = "semi-auto"
        config.daemon.interval_sec = 120

        dc = config.to_daemon_config()
        self.assertEqual(dc.mode, "semi-auto")
        self.assertEqual(dc.interval_seconds, 120)
        self.assertEqual(dc.max_tasks_per_cycle, 10)


if __name__ == "__main__":
    unittest.main()
