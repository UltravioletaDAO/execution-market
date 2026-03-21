"""
Tests for Phase 6: Relay Chains (MASTER_PLAN_MESHRELAY_V2.md).

Validates:
- Migration 069: relay_chains + relay_legs tables
- Relay API router (relay.py) file structure and endpoints
- Relay IRC commands (relay.ts)
- Relay payment handler (relay_payment.py)
- Dashboard component (RelayChainStatus.tsx)
- EMServ index registration of relay commands
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

EMSERV_ROOT = Path(__file__).parent.parent.parent / "xmtp-bot" / "src" / "emserv"
MIGRATIONS_ROOT = Path(__file__).parent.parent.parent / "supabase" / "migrations"
DASHBOARD_ROOT = Path(__file__).parent.parent.parent / "dashboard" / "src"


# ---------------------------------------------------------------------------
# Migration 069: Relay Chains + Relay Legs
# ---------------------------------------------------------------------------


class TestMigration069RelayChains:
    def test_migration_file_exists(self):
        assert (MIGRATIONS_ROOT / "069_relay_chains.sql").exists()

    def test_creates_relay_chains_table(self):
        content = (MIGRATIONS_ROOT / "069_relay_chains.sql").read_text()
        assert "CREATE TABLE" in content
        assert "relay_chains" in content

    def test_creates_relay_legs_table(self):
        content = (MIGRATIONS_ROOT / "069_relay_chains.sql").read_text()
        assert "relay_legs" in content

    def test_relay_chains_has_required_columns(self):
        content = (MIGRATIONS_ROOT / "069_relay_chains.sql").read_text()
        for col in [
            "chain_id",
            "parent_task_id",
            "status",
            "total_legs",
            "completed_legs",
        ]:
            assert col in content, f"Column {col} missing"

    def test_relay_legs_has_required_columns(self):
        content = (MIGRATIONS_ROOT / "069_relay_chains.sql").read_text()
        for col in [
            "leg_id",
            "chain_id",
            "leg_number",
            "worker_wallet",
            "handoff_code",
            "pickup_location",
            "dropoff_location",
            "bounty_usdc",
        ]:
            assert col in content, f"Column {col} missing"

    def test_relay_legs_references_chains(self):
        content = (MIGRATIONS_ROOT / "069_relay_chains.sql").read_text()
        assert "REFERENCES relay_chains(chain_id)" in content

    def test_relay_chains_references_tasks(self):
        content = (MIGRATIONS_ROOT / "069_relay_chains.sql").read_text()
        assert "REFERENCES tasks(id)" in content

    def test_unique_leg_number_per_chain(self):
        content = (MIGRATIONS_ROOT / "069_relay_chains.sql").read_text()
        assert "UNIQUE(chain_id, leg_number)" in content

    def test_has_rls_on_both_tables(self):
        content = (MIGRATIONS_ROOT / "069_relay_chains.sql").read_text()
        assert content.count("ENABLE ROW LEVEL SECURITY") == 2


# ---------------------------------------------------------------------------
# Relay API Router (relay.py)
# ---------------------------------------------------------------------------


class TestRelayRouter:
    def test_file_exists(self):
        relay = Path(__file__).parent.parent / "api" / "routers" / "relay.py"
        assert relay.exists()

    def test_has_create_endpoint(self):
        relay = Path(__file__).parent.parent / "api" / "routers" / "relay.py"
        content = relay.read_text()
        assert "create_relay_chain" in content
        assert 'prefix="/api/v1/relay-chains"' in content

    def test_has_get_endpoint(self):
        relay = Path(__file__).parent.parent / "api" / "routers" / "relay.py"
        content = relay.read_text()
        assert "get_relay_chain" in content

    def test_has_assign_endpoint(self):
        relay = Path(__file__).parent.parent / "api" / "routers" / "relay.py"
        content = relay.read_text()
        assert "assign_leg_worker" in content

    def test_has_handoff_endpoint(self):
        relay = Path(__file__).parent.parent / "api" / "routers" / "relay.py"
        content = relay.read_text()
        assert "record_handoff" in content

    def test_handoff_verifies_code(self):
        relay = Path(__file__).parent.parent / "api" / "routers" / "relay.py"
        content = relay.read_text()
        assert "handoff_code" in content
        assert "Invalid handoff code" in content

    def test_requires_min_two_legs(self):
        relay = Path(__file__).parent.parent / "api" / "routers" / "relay.py"
        content = relay.read_text()
        assert "min_length=2" in content

    def test_router_registered_in_routes(self):
        routes = Path(__file__).parent.parent / "api" / "routes.py"
        content = routes.read_text()
        assert "relay_router" in content
        assert "relay" in content


# ---------------------------------------------------------------------------
# Relay IRC Commands (relay.ts)
# ---------------------------------------------------------------------------


class TestRelayCommands:
    def test_file_exists(self):
        assert (EMSERV_ROOT / "commands" / "relay.ts").exists()

    def test_exports_relay_commands(self):
        content = (EMSERV_ROOT / "commands" / "relay.ts").read_text()
        assert "relayCommands" in content
        assert "CommandDefinition" in content

    def test_has_relay_status_command(self):
        content = (EMSERV_ROOT / "commands" / "relay.ts").read_text()
        assert 'name: "relay-status"' in content

    def test_has_handoff_command(self):
        content = (EMSERV_ROOT / "commands" / "relay.ts").read_text()
        assert 'name: "handoff"' in content

    def test_has_confirm_handoff_command(self):
        content = (EMSERV_ROOT / "commands" / "relay.ts").read_text()
        assert 'name: "confirm-handoff"' in content

    def test_handoff_requires_verified_trust(self):
        content = (EMSERV_ROOT / "commands" / "relay.ts").read_text()
        assert "TrustLevel.VERIFIED" in content

    def test_calls_relay_api(self):
        content = (EMSERV_ROOT / "commands" / "relay.ts").read_text()
        assert "/api/v1/relay-chains/" in content

    def test_relay_status_shows_leg_progress(self):
        content = (EMSERV_ROOT / "commands" / "relay.ts").read_text()
        assert "completed_legs" in content
        assert "total_legs" in content


# ---------------------------------------------------------------------------
# Relay Payment Handler (relay_payment.py)
# ---------------------------------------------------------------------------


class TestRelayPayment:
    def test_file_exists(self):
        relay_pay = (
            Path(__file__).parent.parent / "integrations" / "x402" / "relay_payment.py"
        )
        assert relay_pay.exists()

    def test_has_release_leg_payment(self):
        relay_pay = (
            Path(__file__).parent.parent / "integrations" / "x402" / "relay_payment.py"
        )
        content = relay_pay.read_text()
        assert "release_leg_payment" in content

    def test_has_refund_remaining_legs(self):
        relay_pay = (
            Path(__file__).parent.parent / "integrations" / "x402" / "relay_payment.py"
        )
        content = relay_pay.read_text()
        assert "refund_remaining_legs" in content

    def test_has_bounty_splitting(self):
        relay_pay = (
            Path(__file__).parent.parent / "integrations" / "x402" / "relay_payment.py"
        )
        content = relay_pay.read_text()
        assert "compute_leg_bounties" in content


class TestRelayPaymentUnit:
    """Unit tests using importlib to skip x402 __init__ treasury check."""

    def _get_handler_class(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "relay_payment",
            Path(__file__).parent.parent / "integrations" / "x402" / "relay_payment.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.RelayPaymentHandler

    def test_even_split(self):
        handler = self._get_handler_class()()
        bounties = handler.compute_leg_bounties(1.0, 4)
        assert len(bounties) == 4
        assert abs(sum(bounties) - 1.0) < 0.000001

    def test_weighted_split(self):
        handler = self._get_handler_class()()
        bounties = handler.compute_leg_bounties(1.0, 3, weights=[1, 2, 1])
        assert len(bounties) == 3
        assert abs(sum(bounties) - 1.0) < 0.000001
        assert bounties[1] > bounties[0]  # Middle leg gets more

    def test_even_split_remainder(self):
        handler = self._get_handler_class()()
        bounties = handler.compute_leg_bounties(1.0, 3)
        assert len(bounties) == 3
        assert abs(sum(bounties) - 1.0) < 0.000001


# ---------------------------------------------------------------------------
# Dashboard Component (RelayChainStatus.tsx)
# ---------------------------------------------------------------------------


class TestRelayChainDashboard:
    def test_component_file_exists(self):
        assert (DASHBOARD_ROOT / "components" / "RelayChainStatus.tsx").exists()

    def test_has_relay_chain_interface(self):
        content = (DASHBOARD_ROOT / "components" / "RelayChainStatus.tsx").read_text()
        assert "RelayChain" in content
        assert "RelayLeg" in content

    def test_shows_progress(self):
        content = (DASHBOARD_ROOT / "components" / "RelayChainStatus.tsx").read_text()
        assert "completed_legs" in content
        assert "total_legs" in content

    def test_shows_status_labels(self):
        content = (DASHBOARD_ROOT / "components" / "RelayChainStatus.tsx").read_text()
        assert "STATUS_LABELS" in content
        assert "In Transit" in content
        assert "Handed Off" in content

    def test_shows_bounty_per_leg(self):
        content = (DASHBOARD_ROOT / "components" / "RelayChainStatus.tsx").read_text()
        assert "bounty_usdc" in content


# ---------------------------------------------------------------------------
# EMServ Index Registration
# ---------------------------------------------------------------------------


class TestEMServRelayRegistration:
    def test_index_imports_relay_commands(self):
        content = (EMSERV_ROOT / "index.ts").read_text()
        assert "relayCommands" in content
        assert "relay.js" in content

    def test_index_registers_relay_commands(self):
        content = (EMSERV_ROOT / "index.ts").read_text()
        assert "for (const cmd of relayCommands)" in content
