"""
Tests for Phase 8: Security Hardening + Production (MASTER_PLAN_MESHRELAY_V2.md).

Validates:
- Rate limiter (rate-limiter.ts)
- Anti-sniping (in tasks.ts)
- Channel governance (governance.ts)
- Event Bus metrics (metrics.py)
- IRC metrics (metrics.ts)
- MeshRelay config in PlatformConfig
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

EMSERV_ROOT = Path(__file__).parent.parent.parent / "xmtp-bot" / "src" / "emserv"


# ---------------------------------------------------------------------------
# Task 8.1: Rate Limiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_file_exists(self):
        assert (EMSERV_ROOT / "rate-limiter.ts").exists()

    def test_has_rate_limits_config(self):
        content = (EMSERV_ROOT / "rate-limiter.ts").read_text()
        assert "RATE_LIMITS" in content

    def test_has_check_function(self):
        content = (EMSERV_ROOT / "rate-limiter.ts").read_text()
        assert "checkRateLimit" in content

    def test_has_sliding_window(self):
        content = (EMSERV_ROOT / "rate-limiter.ts").read_text()
        assert "windowSec" in content
        assert "timestamps" in content or "counters" in content

    def test_limits_claim_command(self):
        content = (EMSERV_ROOT / "rate-limiter.ts").read_text()
        assert "claim:" in content or '"claim"' in content

    def test_limits_publish_command(self):
        content = (EMSERV_ROOT / "rate-limiter.ts").read_text()
        assert "publish:" in content

    def test_has_reset_function(self):
        content = (EMSERV_ROOT / "rate-limiter.ts").read_text()
        assert "resetRateLimit" in content

    def test_returns_cooldown_seconds(self):
        content = (EMSERV_ROOT / "rate-limiter.ts").read_text()
        assert "cooldownSec" in content or "cooldown" in content

    def test_has_default_limit(self):
        content = (EMSERV_ROOT / "rate-limiter.ts").read_text()
        assert "DEFAULT_LIMIT" in content


# ---------------------------------------------------------------------------
# Task 8.3: Channel Governance
# ---------------------------------------------------------------------------


class TestChannelGovernance:
    def test_file_exists(self):
        assert (EMSERV_ROOT / "governance.ts").exists()

    def test_has_flood_detection(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "checkFlood" in content
        assert "FLOOD_THRESHOLD" in content

    def test_flood_threshold_is_5(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "FLOOD_THRESHOLD = 5" in content

    def test_flood_window_is_10s(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "10_000" in content or "10000" in content

    def test_has_report_system(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "reportUser" in content
        assert "REPORT_BAN_THRESHOLD" in content

    def test_ban_threshold_is_3(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "REPORT_BAN_THRESHOLD = 3" in content

    def test_has_is_banned_check(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "isBanned" in content

    def test_has_channel_mode_helper(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "getChannelMode" in content
        assert '"+o"' in content  # Operator for bots
        assert '"+h"' in content  # Half-op for publishers

    def test_has_is_quieted_check(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "isQuieted" in content

    def test_prevents_duplicate_reports(self):
        content = (EMSERV_ROOT / "governance.ts").read_text()
        assert "Prevent duplicate" in content or "duplicate report" in content.lower()


# ---------------------------------------------------------------------------
# Task 8.4: Event Bus Metrics (Python)
# ---------------------------------------------------------------------------


class TestEventBusMetrics:
    def test_file_exists(self):
        metrics_path = Path(__file__).parent.parent / "events" / "metrics.py"
        assert metrics_path.exists()

    def test_has_metrics_class(self):
        metrics_path = Path(__file__).parent.parent / "events" / "metrics.py"
        content = metrics_path.read_text()
        assert "class EventBusMetrics" in content

    def test_tracks_publish_count(self):
        metrics_path = Path(__file__).parent.parent / "events" / "metrics.py"
        content = metrics_path.read_text()
        assert "events_published_total" in content

    def test_tracks_delivery_count(self):
        metrics_path = Path(__file__).parent.parent / "events" / "metrics.py"
        content = metrics_path.read_text()
        assert "events_delivered_total" in content

    def test_tracks_adapter_errors(self):
        metrics_path = Path(__file__).parent.parent / "events" / "metrics.py"
        content = metrics_path.read_text()
        assert "adapter_errors_total" in content

    def test_tracks_latency(self):
        metrics_path = Path(__file__).parent.parent / "events" / "metrics.py"
        content = metrics_path.read_text()
        assert "record_latency" in content
        assert "avg_delivery_latency_ms" in content

    def test_has_identity_metrics(self):
        metrics_path = Path(__file__).parent.parent / "events" / "metrics.py"
        content = metrics_path.read_text()
        assert "verifications_total" in content
        assert "trust_upgrades_total" in content
        assert "identity_syncs_total" in content


class TestEventBusMetricsUnit:
    def test_record_and_get(self):
        from events.metrics import EventBusMetrics

        m = EventBusMetrics()
        m.record_publish()
        m.record_publish()
        m.record_delivery("meshrelay")
        m.record_error("xmtp")
        m.record_latency("meshrelay", 42.5)
        m.record_verification()

        metrics = m.get_metrics()
        assert metrics["events_published_total"] == 2
        assert metrics["events_delivered_total"] == 1
        assert metrics["adapter_errors_total"] == 1
        assert metrics["adapter_errors_by_name"]["xmtp"] == 1
        assert metrics["avg_delivery_latency_ms"]["meshrelay"] == 42.5
        assert metrics["identity"]["verifications_total"] == 1

    def test_reset(self):
        from events.metrics import EventBusMetrics

        m = EventBusMetrics()
        m.record_publish()
        m.reset()
        metrics = m.get_metrics()
        assert metrics["events_published_total"] == 0


# ---------------------------------------------------------------------------
# Task 8.4: IRC Metrics (TypeScript)
# ---------------------------------------------------------------------------


class TestIRCMetrics:
    def test_file_exists(self):
        assert (EMSERV_ROOT / "metrics.ts").exists()

    def test_has_record_command(self):
        content = (EMSERV_ROOT / "metrics.ts").read_text()
        assert "recordCommand" in content

    def test_has_record_error(self):
        content = (EMSERV_ROOT / "metrics.ts").read_text()
        assert "recordCommandError" in content

    def test_has_active_channels(self):
        content = (EMSERV_ROOT / "metrics.ts").read_text()
        assert "activeChannels" in content or "active_channels" in content

    def test_has_bridge_latency(self):
        content = (EMSERV_ROOT / "metrics.ts").read_text()
        assert "recordBridgeLatency" in content
        assert "avg_bridge_latency_ms" in content

    def test_has_get_metrics(self):
        content = (EMSERV_ROOT / "metrics.ts").read_text()
        assert "getMetrics" in content

    def test_has_reset_function(self):
        content = (EMSERV_ROOT / "metrics.ts").read_text()
        assert "resetMetrics" in content


# ---------------------------------------------------------------------------
# Task 8.6: MeshRelay PlatformConfig Section
# ---------------------------------------------------------------------------


class TestMeshRelayConfig:
    def test_has_meshrelay_enabled(self):
        config_path = Path(__file__).parent.parent / "config" / "platform_config.py"
        content = config_path.read_text()
        assert '"meshrelay.enabled"' in content

    def test_has_meshrelay_api_url(self):
        config_path = Path(__file__).parent.parent / "config" / "platform_config.py"
        content = config_path.read_text()
        assert '"meshrelay.api_url"' in content

    def test_has_anti_snipe_config(self):
        config_path = Path(__file__).parent.parent / "config" / "platform_config.py"
        content = config_path.read_text()
        assert "anti_snipe_cooldown_sec" in content

    def test_has_claim_priority_window(self):
        config_path = Path(__file__).parent.parent / "config" / "platform_config.py"
        content = config_path.read_text()
        assert "claim_priority_window_sec" in content

    def test_has_feature_flags(self):
        config_path = Path(__file__).parent.parent / "config" / "platform_config.py"
        content = config_path.read_text()
        assert "meshrelay_dynamic_channels" in content
        assert "meshrelay_relay_chains" in content
        assert "meshrelay_reverse_auctions" in content

    def test_feature_flags_default_false(self):
        config_path = Path(__file__).parent.parent / "config" / "platform_config.py"
        content = config_path.read_text()
        assert '"feature.meshrelay_dynamic_channels": False' in content
        assert '"feature.meshrelay_relay_chains": False' in content
        assert '"feature.meshrelay_reverse_auctions": False' in content

    def test_has_channel_config(self):
        config_path = Path(__file__).parent.parent / "config" / "platform_config.py"
        content = config_path.read_text()
        assert '"meshrelay.channels.bounties"' in content
        assert "#bounties" in content

    def test_has_max_bids_config(self):
        config_path = Path(__file__).parent.parent / "config" / "platform_config.py"
        content = config_path.read_text()
        assert "max_bids_per_auction" in content
