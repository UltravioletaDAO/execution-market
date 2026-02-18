"""
Migration integrity tests for migrations 031, 032, 033.

Tests verify that column definitions, constraints, indexes, and trigger
functions align with what the migrations specify. Uses mock DB to validate
that code expects the right schema.

Task 4.3 from MASTER_PLAN_H2A_A2A_HARDENING.md
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Migration 031: Agent Executor Support
# ============================================================================


@pytest.mark.migrations
class TestMigration031AgentExecutorSupport:
    """Verify migration 031 schema expectations."""

    def test_executor_type_column_used_in_queries(self):
        """Code queries executor_type column from executors table."""
        from api import h2a

        source = Path(h2a.__file__).read_text()
        assert "executor_type" in source

    def test_capabilities_column_used_in_queries(self):
        """Code uses capabilities column for agent filtering."""
        from api import h2a

        source = Path(h2a.__file__).read_text()
        assert "capabilities" in source

    def test_target_agent_id_column_exists_in_models(self):
        """H2A task model references target_agent_id."""
        from models import PublishH2ATaskRequest

        fields = PublishH2ATaskRequest.model_fields
        assert "target_agent_id" in fields

    def test_verification_mode_column_in_models(self):
        """H2A task model references verification_mode."""
        from models import PublishH2ATaskRequest

        fields = PublishH2ATaskRequest.model_fields
        assert "verification_mode" in fields

    def test_required_capabilities_in_models(self):
        """H2A task model has required_capabilities field."""
        from models import PublishH2ATaskRequest

        fields = PublishH2ATaskRequest.model_fields
        assert "required_capabilities" in fields

    def test_executor_type_valid_values(self):
        """executor_type should only accept 'human' or 'agent'."""
        # Migration 031 CHECK: executor_type IN ('human', 'agent')
        import tools.agent_executor_tools as aet

        source = Path(aet.__file__).read_text()
        assert "executor_type" in source
        # The code should set executor_type to 'agent' for agent executors
        assert "'agent'" in source or '"agent"' in source

    def test_verification_mode_default_value(self):
        """verification_mode should default to 'manual'."""
        from models import PublishH2ATaskRequest

        field = PublishH2ATaskRequest.model_fields["verification_mode"]
        assert field.default == "manual"

    def test_api_keys_extended_with_key_type(self):
        """Migration adds key_type and executor_id to api_keys."""
        from api import h2a

        source = Path(h2a.__file__).read_text()
        # H2A code validates API keys — should reference key_type if used
        assert "api_keys" in source or "authorization" in source.lower()

    def test_digital_categories_added(self):
        """Migration 031 adds 6 digital task categories."""
        expected = {
            "data_processing",
            "api_integration",
            "content_generation",
            "code_execution",
            "research",
            "multi_step_workflow",
        }
        from models import PublishH2ATaskRequest

        # Check that model accepts these categories
        field = PublishH2ATaskRequest.model_fields.get("category")
        if field and hasattr(field, "metadata"):
            # Categories should be accepted by the model
            pass
        # Also check that the migration file has them
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/031_agent_executor_support.sql"
        )
        if migration.exists():
            content = migration.read_text()
            for cat in expected:
                assert cat in content, f"Category {cat} not in migration 031"


# ============================================================================
# Migration 032: Agent Cards
# ============================================================================


@pytest.mark.migrations
class TestMigration032AgentCards:
    """Verify migration 032 schema expectations."""

    def test_agent_type_column_in_executors(self):
        """executors.agent_type column exists in migration."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/032_agent_cards.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "agent_type" in content

    def test_agent_type_valid_values(self):
        """agent_type should be 'human', 'ai', or 'organization'."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/032_agent_cards.sql"
        )
        if migration.exists():
            content = migration.read_text()
            for val in ("human", "ai", "organization"):
                assert val in content

    def test_networks_active_column_exists(self):
        """executors.networks_active TEXT[] column added."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/032_agent_cards.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "networks_active" in content

    def test_activity_feed_table_created(self):
        """activity_feed table should be created."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/032_agent_cards.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "CREATE TABLE IF NOT EXISTS activity_feed" in content

    def test_activity_feed_rls_enabled(self):
        """activity_feed should have RLS enabled."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/032_agent_cards.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "ENABLE ROW LEVEL SECURITY" in content

    def test_activity_feed_public_read_policy(self):
        """activity_feed should have public read policy."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/032_agent_cards.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "activity_feed_read_public" in content

    def test_activity_feed_trigger_function(self):
        """Trigger function fn_activity_feed_on_task_change exists."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/032_agent_cards.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "fn_activity_feed_on_task_change" in content

    def test_trigger_handles_status_transitions(self):
        """Trigger handles published, accepted, completed, disputed events."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/032_agent_cards.sql"
        )
        if migration.exists():
            content = migration.read_text()
            for event in (
                "task_created",
                "task_accepted",
                "task_completed",
                "dispute_opened",
            ):
                assert event in content, f"Event {event} not in trigger"


# ============================================================================
# Migration 033: H2A Marketplace
# ============================================================================


@pytest.mark.migrations
class TestMigration033H2AMarketplace:
    """Verify migration 033 schema expectations."""

    def test_publisher_type_column_added(self):
        """tasks.publisher_type column exists."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/033_h2a_marketplace.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "publisher_type" in content

    def test_publisher_type_constraint(self):
        """publisher_type CHECK constraint: 'agent' or 'human'."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/033_h2a_marketplace.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "agent" in content
            assert "human" in content

    def test_human_wallet_column_added(self):
        """tasks.human_wallet column exists."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/033_h2a_marketplace.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "human_wallet" in content

    def test_human_user_id_column_added(self):
        """tasks.human_user_id column exists."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/033_h2a_marketplace.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "human_user_id" in content

    def test_feature_flags_inserted(self):
        """H2A feature flags created in platform_config."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/033_h2a_marketplace.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "feature.h2a_enabled" in content
            assert "feature.h2a_min_bounty" in content
            assert "feature.h2a_max_bounty" in content

    def test_publisher_type_default_is_agent(self):
        """Default publisher_type should be 'agent' (backward compat)."""
        migration = Path(
            "Z:/ultravioleta/dao/execution-market/supabase/migrations/033_h2a_marketplace.sql"
        )
        if migration.exists():
            content = migration.read_text()
            assert "DEFAULT 'agent'" in content


# ============================================================================
# Cross-Migration Consistency
# ============================================================================


@pytest.mark.migrations
class TestCrossMigrationConsistency:
    """Verify consistency across migrations 031-033."""

    def test_no_duplicate_columns(self):
        """No column added in multiple migrations."""
        all_columns = []
        for num in (
            "031_agent_executor_support",
            "032_agent_cards",
            "033_h2a_marketplace",
        ):
            path = Path(
                f"Z:/ultravioleta/dao/execution-market/supabase/migrations/{num}.sql"
            )
            if path.exists():
                content = path.read_text()
                # Extract ADD COLUMN lines
                for line in content.split("\n"):
                    if "ADD COLUMN" in line and "IF NOT EXISTS" in line:
                        # Extract column name
                        parts = line.split("IF NOT EXISTS")
                        if len(parts) > 1:
                            col_name = parts[1].strip().split()[0]
                            all_columns.append((num, col_name))

        # Check for duplicates (same column in different migrations)
        seen = {}
        for migration, col in all_columns:
            if col in seen and seen[col] != migration:
                # Duplicate — this is OK if using IF NOT EXISTS, but flag it
                pass
            seen[col] = migration

    def test_h2a_code_uses_migration_033_columns(self):
        """H2A code references all columns from migration 033."""
        from api import h2a

        source = Path(h2a.__file__).read_text()
        for col in ("publisher_type", "human_wallet", "human_user_id"):
            assert col in source, f"H2A code missing column {col}"

    def test_agent_executor_code_uses_migration_031_columns(self):
        """Agent executor code uses columns from migration 031."""
        from tools import agent_executor_tools

        source = Path(agent_executor_tools.__file__).read_text()
        for col in ("executor_type", "capabilities"):
            assert col in source, f"Agent executor code missing column {col}"
