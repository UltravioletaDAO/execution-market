"""
Tests for Phase 5: Discovery Layer (MASTER_PLAN_MESHRELAY_V2.md).

Validates:
- Worker availability migration (067)
- Task bids / auction migration (068)
- Discovery commands (discovery.ts) file structure
- Auction commands (auction.ts) file structure
- Match commands (match.ts) file structure
- CrossPostEngine (crosspost.py) logic
- Adaptive wire format (wire.ts formatChannelAnnouncement)
- EMServ index registers discovery + auction + match commands
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

EMSERV_ROOT = Path(__file__).parent.parent.parent / "xmtp-bot" / "src" / "emserv"
MIGRATIONS_ROOT = Path(__file__).parent.parent.parent / "supabase" / "migrations"


# ---------------------------------------------------------------------------
# Migration 067: Worker Availability
# ---------------------------------------------------------------------------


class TestMigration067WorkerAvailability:
    def test_migration_file_exists(self):
        assert (MIGRATIONS_ROOT / "067_worker_availability.sql").exists()

    def test_creates_worker_availability_table(self):
        content = (MIGRATIONS_ROOT / "067_worker_availability.sql").read_text()
        assert "CREATE TABLE" in content
        assert "worker_availability" in content

    def test_has_required_columns(self):
        content = (MIGRATIONS_ROOT / "067_worker_availability.sql").read_text()
        for col in [
            "wallet_address",
            "irc_nick",
            "city",
            "country",
            "categories",
            "available_until",
            "last_ping",
        ]:
            assert col in content, f"Column {col} missing from migration"

    def test_has_city_index(self):
        content = (MIGRATIONS_ROOT / "067_worker_availability.sql").read_text()
        assert "idx_worker_availability_city" in content

    def test_has_rls_enabled(self):
        content = (MIGRATIONS_ROOT / "067_worker_availability.sql").read_text()
        assert "ENABLE ROW LEVEL SECURITY" in content


# ---------------------------------------------------------------------------
# Migration 068: Task Bids
# ---------------------------------------------------------------------------


class TestMigration068TaskBids:
    def test_migration_file_exists(self):
        assert (MIGRATIONS_ROOT / "068_task_bids.sql").exists()

    def test_creates_task_bids_table(self):
        content = (MIGRATIONS_ROOT / "068_task_bids.sql").read_text()
        assert "CREATE TABLE" in content
        assert "task_bids" in content

    def test_has_required_columns(self):
        content = (MIGRATIONS_ROOT / "068_task_bids.sql").read_text()
        for col in [
            "task_id",
            "wallet_address",
            "amount_usdc",
            "message",
            "eta_minutes",
            "status",
        ]:
            assert col in content, f"Column {col} missing from migration"

    def test_references_tasks_table(self):
        content = (MIGRATIONS_ROOT / "068_task_bids.sql").read_text()
        assert "REFERENCES tasks(id)" in content

    def test_has_unique_constraint(self):
        content = (MIGRATIONS_ROOT / "068_task_bids.sql").read_text()
        assert "UNIQUE(task_id, wallet_address)" in content

    def test_has_rls_enabled(self):
        content = (MIGRATIONS_ROOT / "068_task_bids.sql").read_text()
        assert "ENABLE ROW LEVEL SECURITY" in content


# ---------------------------------------------------------------------------
# Discovery Commands (discovery.ts)
# ---------------------------------------------------------------------------


class TestDiscoveryCommands:
    def test_file_exists(self):
        assert (EMSERV_ROOT / "commands" / "discovery.ts").exists()

    def test_exports_discovery_commands(self):
        content = (EMSERV_ROOT / "commands" / "discovery.ts").read_text()
        assert "discoveryCommands" in content
        assert "CommandDefinition" in content

    def test_has_available_command(self):
        content = (EMSERV_ROOT / "commands" / "discovery.ts").read_text()
        assert 'name: "available"' in content

    def test_has_unavailable_command(self):
        content = (EMSERV_ROOT / "commands" / "discovery.ts").read_text()
        assert 'name: "unavailable"' in content

    def test_has_who_command(self):
        content = (EMSERV_ROOT / "commands" / "discovery.ts").read_text()
        assert 'name: "who"' in content

    def test_has_nearby_command(self):
        content = (EMSERV_ROOT / "commands" / "discovery.ts").read_text()
        assert 'name: "nearby"' in content

    def test_available_supports_json_payload(self):
        content = (EMSERV_ROOT / "commands" / "discovery.ts").read_text()
        assert "jsonPayload" in content

    def test_broadcasts_to_city_channel(self):
        content = (EMSERV_ROOT / "commands" / "discovery.ts").read_text()
        assert "#city-" in content


# ---------------------------------------------------------------------------
# Auction Commands (auction.ts)
# ---------------------------------------------------------------------------


class TestAuctionCommands:
    def test_file_exists(self):
        assert (EMSERV_ROOT / "commands" / "auction.ts").exists()

    def test_exports_auction_commands(self):
        content = (EMSERV_ROOT / "commands" / "auction.ts").read_text()
        assert "auctionCommands" in content
        assert "CommandDefinition" in content

    def test_has_bid_command(self):
        content = (EMSERV_ROOT / "commands" / "auction.ts").read_text()
        assert 'name: "bid"' in content

    def test_has_select_bid_command(self):
        content = (EMSERV_ROOT / "commands" / "auction.ts").read_text()
        assert 'name: "select-bid"' in content

    def test_has_bids_command(self):
        content = (EMSERV_ROOT / "commands" / "auction.ts").read_text()
        assert 'name: "bids"' in content

    def test_has_anti_sniping(self):
        content = (EMSERV_ROOT / "commands" / "auction.ts").read_text()
        assert "ANTI_SNIPE" in content

    def test_exports_start_auction(self):
        content = (EMSERV_ROOT / "commands" / "auction.ts").read_text()
        assert "export function startAuction" in content

    def test_bids_sorted_ascending(self):
        content = (EMSERV_ROOT / "commands" / "auction.ts").read_text()
        assert "sort((a, b) => a.amount - b.amount)" in content


# ---------------------------------------------------------------------------
# Match Commands (match.ts)
# ---------------------------------------------------------------------------


class TestMatchCommands:
    def test_file_exists(self):
        assert (EMSERV_ROOT / "commands" / "match.ts").exists()

    def test_exports_match_commands(self):
        content = (EMSERV_ROOT / "commands" / "match.ts").read_text()
        assert "matchCommands" in content
        assert "CommandDefinition" in content

    def test_has_match_command(self):
        content = (EMSERV_ROOT / "commands" / "match.ts").read_text()
        assert 'name: "match"' in content

    def test_has_suggest_command(self):
        content = (EMSERV_ROOT / "commands" / "match.ts").read_text()
        assert 'name: "suggest"' in content

    def test_match_queries_task_api(self):
        content = (EMSERV_ROOT / "commands" / "match.ts").read_text()
        assert "/api/v1/tasks/" in content

    def test_match_requires_linked_trust(self):
        content = (EMSERV_ROOT / "commands" / "match.ts").read_text()
        assert "TrustLevel.LINKED" in content


# ---------------------------------------------------------------------------
# CrossPostEngine (crosspost.py)
# ---------------------------------------------------------------------------


class TestCrossPostEngine:
    def test_file_exists(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        assert crosspost.exists()

    def test_has_category_channels(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        content = crosspost.read_text()
        assert "CATEGORY_CHANNELS" in content
        assert "#cat-physical" in content
        assert "#cat-knowledge" in content
        assert "#cat-authority" in content
        assert "#cat-action" in content
        assert "#cat-digital" in content

    def test_has_urgent_threshold(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        content = crosspost.read_text()
        assert "URGENT_THRESHOLD_MINUTES" in content

    def test_has_high_value_threshold(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        content = crosspost.read_text()
        assert "HIGH_VALUE_THRESHOLD_USD" in content

    def test_subscribes_to_task_created(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        content = crosspost.read_text()
        assert "task.created" in content

    def test_posts_to_geographic_channel(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        content = crosspost.read_text()
        assert "#city-" in content

    def test_posts_to_urgent_channel(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        content = crosspost.read_text()
        assert '"#urgent"' in content

    def test_posts_to_high_value_channel(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        content = crosspost.read_text()
        assert '"#high-value"' in content

    def test_graceful_404_handling(self):
        crosspost = (
            Path(__file__).parent.parent / "events" / "adapters" / "crosspost.py"
        )
        content = crosspost.read_text()
        assert "404" in content
        assert "skipped_no_channel" in content


class TestCrossPostEngineUnit:
    """Unit tests for CrossPostEngine._compute_targets()."""

    def test_compute_targets_category(self):
        from events.adapters.crosspost import CrossPostEngine
        from events.bus import EventBus
        from events.models import EMEvent

        engine = CrossPostEngine(bus=EventBus())
        event = EMEvent(
            event_type="task.created",
            payload={
                "task_id": "abc12345-1234-1234-1234-123456789012",
                "title": "Take photo",
                "bounty_usd": 0.10,
                "category": "physical_presence",
            },
        )
        targets = engine._compute_targets(event)
        channels = [ch for ch, _ in targets]
        assert "#cat-physical" in channels

    def test_compute_targets_geographic(self):
        from events.adapters.crosspost import CrossPostEngine
        from events.bus import EventBus
        from events.models import EMEvent

        engine = CrossPostEngine(bus=EventBus())
        event = EMEvent(
            event_type="task.created",
            payload={
                "task_id": "abc12345-1234-1234-1234-123456789012",
                "title": "Deliver package",
                "bounty_usd": 0.10,
                "city": "Medellin",
            },
        )
        targets = engine._compute_targets(event)
        channels = [ch for ch, _ in targets]
        assert "#city-medellin" in channels

    def test_compute_targets_urgent(self):
        from events.adapters.crosspost import CrossPostEngine
        from events.bus import EventBus
        from events.models import EMEvent

        engine = CrossPostEngine(bus=EventBus())
        event = EMEvent(
            event_type="task.created",
            payload={
                "task_id": "abc12345-1234-1234-1234-123456789012",
                "title": "Quick task",
                "bounty_usd": 0.10,
                "deadline_minutes": 10,
            },
        )
        targets = engine._compute_targets(event)
        channels = [ch for ch, _ in targets]
        assert "#urgent" in channels

    def test_compute_targets_high_value(self):
        from events.adapters.crosspost import CrossPostEngine
        from events.bus import EventBus
        from events.models import EMEvent

        engine = CrossPostEngine(bus=EventBus())
        event = EMEvent(
            event_type="task.created",
            payload={
                "task_id": "abc12345-1234-1234-1234-123456789012",
                "title": "Expensive task",
                "bounty_usd": 5.00,
                "category": "knowledge_access",
            },
        )
        targets = engine._compute_targets(event)
        channels = [ch for ch, _ in targets]
        assert "#high-value" in channels
        assert "#cat-knowledge" in channels

    def test_compute_targets_not_urgent_when_above_threshold(self):
        from events.adapters.crosspost import CrossPostEngine
        from events.bus import EventBus
        from events.models import EMEvent

        engine = CrossPostEngine(bus=EventBus())
        event = EMEvent(
            event_type="task.created",
            payload={
                "task_id": "abc12345-1234-1234-1234-123456789012",
                "title": "Normal task",
                "bounty_usd": 0.10,
                "deadline_minutes": 60,
            },
        )
        targets = engine._compute_targets(event)
        channels = [ch for ch, _ in targets]
        assert "#urgent" not in channels

    def test_compute_targets_empty_when_no_matches(self):
        from events.adapters.crosspost import CrossPostEngine
        from events.bus import EventBus
        from events.models import EMEvent

        engine = CrossPostEngine(bus=EventBus())
        event = EMEvent(
            event_type="task.created",
            payload={
                "task_id": "abc12345-1234-1234-1234-123456789012",
                "title": "Basic task",
                "bounty_usd": 0.50,
                "deadline_minutes": 60,
            },
        )
        targets = engine._compute_targets(event)
        # No category, no city, not urgent, not high-value — no targets
        assert len(targets) == 0


# ---------------------------------------------------------------------------
# Wire Format Adaptive Announcements (wire.ts)
# ---------------------------------------------------------------------------


class TestWireAdaptiveFormat:
    def test_wire_has_format_channel_announcement(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert "formatChannelAnnouncement" in content

    def test_wire_handles_city_channel(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert '#city-"' in content or 'startsWith("#city-")' in content

    def test_wire_handles_cat_channel(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert 'startsWith("#cat-")' in content

    def test_wire_handles_urgent_channel(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert '"#urgent"' in content

    def test_wire_handles_high_value_channel(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert '"#high-value"' in content

    def test_wire_nearby_prefix_for_city(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert "[NEARBY]" in content

    def test_wire_urgent_prefix(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert "[URGENT]" in content

    def test_wire_dollar_prefix_for_high_value(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert "[$$]" in content


# ---------------------------------------------------------------------------
# EMServ Index Registration
# ---------------------------------------------------------------------------


class TestEMServIndexRegistration:
    def test_index_imports_discovery_commands(self):
        content = (EMSERV_ROOT / "index.ts").read_text()
        assert "discoveryCommands" in content
        assert "discovery.js" in content

    def test_index_imports_auction_commands(self):
        content = (EMSERV_ROOT / "index.ts").read_text()
        assert "auctionCommands" in content
        assert "auction.js" in content

    def test_index_imports_match_commands(self):
        content = (EMSERV_ROOT / "index.ts").read_text()
        assert "matchCommands" in content
        assert "match.js" in content

    def test_index_registers_all_modules(self):
        content = (EMSERV_ROOT / "index.ts").read_text()
        assert "for (const cmd of discoveryCommands)" in content
        assert "for (const cmd of auctionCommands)" in content
        assert "for (const cmd of matchCommands)" in content

    def test_index_exports_format_channel_announcement(self):
        content = (EMSERV_ROOT / "index.ts").read_text()
        assert "formatChannelAnnouncement" in content
