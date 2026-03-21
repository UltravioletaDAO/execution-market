"""
Tests for EMServ integration validation (Phase 4 of MASTER_PLAN_MESHRELAY_V2.md).

Validates that EMServ files exist and are structured correctly,
and that the Python-side endpoints support the EMServ command set.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

EMSERV_ROOT = Path(__file__).parent.parent.parent / "xmtp-bot" / "src" / "emserv"


# ---------------------------------------------------------------------------
# EMServ file structure
# ---------------------------------------------------------------------------


class TestEMServFileStructure:
    def test_emserv_directory_exists(self):
        assert EMSERV_ROOT.exists()
        assert EMSERV_ROOT.is_dir()

    def test_parser_exists(self):
        assert (EMSERV_ROOT / "parser.ts").exists()

    def test_types_exists(self):
        assert (EMSERV_ROOT / "types.ts").exists()

    def test_index_exists(self):
        assert (EMSERV_ROOT / "index.ts").exists()

    def test_personalities_exists(self):
        assert (EMSERV_ROOT / "personalities.ts").exists()

    def test_wire_format_exists(self):
        assert (EMSERV_ROOT / "wire.ts").exists()

    def test_wizard_state_exists(self):
        assert (EMSERV_ROOT / "wizard-state.ts").exists()

    def test_task_commands_exist(self):
        assert (EMSERV_ROOT / "commands" / "tasks.ts").exists()


# ---------------------------------------------------------------------------
# Parser validation
# ---------------------------------------------------------------------------


class TestParserContent:
    def test_parser_has_parse_command(self):
        content = (EMSERV_ROOT / "parser.ts").read_text()
        assert "parseCommand" in content
        assert "ParsedCommand" in content

    def test_parser_supports_json_mode(self):
        content = (EMSERV_ROOT / "parser.ts").read_text()
        assert "JSON.parse" in content
        assert "jsonPayload" in content

    def test_parser_supports_flags(self):
        content = (EMSERV_ROOT / "parser.ts").read_text()
        assert (
            '"--"' in content
            or "startsWith('--')" in content
            or 'startsWith("--")' in content
        )

    def test_parser_has_tokenizer(self):
        content = (EMSERV_ROOT / "parser.ts").read_text()
        assert "tokenize" in content

    def test_parser_has_channel_detection(self):
        content = (EMSERV_ROOT / "parser.ts").read_text()
        assert "getTaskIdFromChannel" in content
        assert "#task-" in content


# ---------------------------------------------------------------------------
# Personality system
# ---------------------------------------------------------------------------


class TestPersonalityContent:
    def test_four_personalities_defined(self):
        content = (EMSERV_ROOT / "personalities.ts").read_text()
        assert "em-bot" in content
        assert "em-match" in content
        assert "em-rep" in content
        assert "em-arb" in content

    def test_personality_routing(self):
        content = (EMSERV_ROOT / "personalities.ts").read_text()
        assert "routeToPersonality" in content

    def test_personality_tones(self):
        content = (EMSERV_ROOT / "personalities.ts").read_text()
        assert "direct" in content
        assert "analytic" in content
        assert "neutral" in content
        assert "formal" in content


# ---------------------------------------------------------------------------
# Wire format
# ---------------------------------------------------------------------------


class TestWireFormatContent:
    def test_wire_has_format_types(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert "human" in content
        assert "json" in content

    def test_wire_has_patterns(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert "WIRE_PATTERNS" in content
        assert "NEW_TASK" in content
        assert "ASSIGNED" in content
        assert "APPROVED" in content

    def test_wire_has_event_formatter(self):
        content = (EMSERV_ROOT / "wire.ts").read_text()
        assert "formatTaskEvent" in content


# ---------------------------------------------------------------------------
# Wizard state
# ---------------------------------------------------------------------------


class TestWizardContent:
    def test_wizard_has_steps(self):
        content = (EMSERV_ROOT / "wizard-state.ts").read_text()
        assert "title" in content
        assert "category" in content
        assert "bounty" in content
        assert "deadline" in content
        assert "confirm" in content

    def test_wizard_has_timeout(self):
        content = (EMSERV_ROOT / "wizard-state.ts").read_text()
        assert "WIZARD_TTL_MS" in content or "expiresAt" in content

    def test_wizard_has_categories(self):
        content = (EMSERV_ROOT / "wizard-state.ts").read_text()
        assert "physical_presence" in content
        assert "knowledge_access" in content
        assert "human_authority" in content
        assert "simple_action" in content
        assert "digital_physical" in content


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------


class TestCommandRegistry:
    def test_task_commands_exported(self):
        content = (EMSERV_ROOT / "commands" / "tasks.ts").read_text()
        assert "taskCommands" in content
        assert "CommandDefinition" in content

    def test_new_commands_registered(self):
        content = (EMSERV_ROOT / "commands" / "tasks.ts").read_text()
        expected_commands = [
            "search",
            "details",
            "publish",
            "confirm",
            "my-tasks",
            "my-claims",
        ]
        for cmd in expected_commands:
            assert f'name: "{cmd}"' in content, f"Command {cmd} not found in registry"

    def test_emserv_integration_in_meshrelay(self):
        meshrelay = (
            Path(__file__).parent.parent.parent
            / "xmtp-bot"
            / "src"
            / "bridges"
            / "meshrelay.ts"
        )
        content = meshrelay.read_text()
        assert "emservHandleCommand" in content
        assert "emserv/index" in content


# ---------------------------------------------------------------------------
# API endpoints support EMServ commands
# ---------------------------------------------------------------------------


class TestAPIEndpointsForEMServ:
    """Verify the REST API has endpoints needed by EMServ commands."""

    def test_tasks_endpoint_exists(self):
        from api.routes import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/tasks" in paths

    def test_submissions_endpoints_exist(self):
        from api.routes import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/submissions/{submission_id}/approve" in paths
        assert "/api/v1/submissions/{submission_id}/reject" in paths

    def test_cancel_endpoint_exists(self):
        from api.routes import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/tasks/{task_id}/cancel" in paths

    def test_identity_endpoints_exist(self):
        from api.routes import router

        paths = {r.path for r in router.routes if hasattr(r, "path")}
        assert "/api/v1/identity/lookup" in paths
        assert "/api/v1/identity/sync" in paths
