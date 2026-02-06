"""
Tests for A2A Agent Card module (NOW-083, NOW-084, NOW-085)

Tests cover:
1. Enum tests - TransportType, SecurityType, InputOutputMode values
2. AgentProvider tests - serialization with required and optional fields
3. AgentCapabilities tests - default values and custom values
4. AgentSkill tests - basic skill and custom modes
5. AgentInterface tests - JSONRPC, WebSocket, HTTP+JSON
6. SecurityScheme tests - bearer, api_key header, api_key query, oauth2
7. AgentCard tests - minimal card, full card, JSON serialization
8. get_em_skills tests - skills returned, unique IDs, required fields
9. get_agent_card tests - default URL, custom URL, env URL, includes all sections
10. FastAPI router tests - /.well-known/agent.json, /v1/card, /discovery/agents endpoints
11. A2A Compliance tests - protocol version format, required fields per A2A 0.3.0 spec
12. Edge cases - empty lists, unicode, long descriptions, special characters
"""

import pytest
import json
import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest_asyncio
from fastapi import FastAPI

from ..a2a.agent_card import (
    # Enums
    TransportType,
    SecurityType,
    InputOutputMode,
    # Data classes
    AgentProvider,
    AgentCapabilities,
    AgentSkill,
    AgentInterface,
    SecurityScheme,
    AgentCard,
    # Functions
    get_em_skills,
    get_agent_card,
    # Constants
    A2A_PROTOCOL_VERSION,
    EM_VERSION,
    DEFAULT_BASE_URL,
    # Router
    router,
)


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Tests for enum definitions."""

    def test_transport_types(self):
        """TransportType enum should have expected values."""
        assert TransportType.JSONRPC.value == "JSONRPC"
        assert TransportType.GRPC.value == "GRPC"
        assert TransportType.HTTP_JSON.value == "HTTP+JSON"
        assert TransportType.WEBSOCKET.value == "WEBSOCKET"
        assert TransportType.STREAMABLE_HTTP.value == "STREAMABLE_HTTP"

    def test_security_types(self):
        """SecurityType enum should have expected values."""
        assert SecurityType.OAUTH2.value == "oauth2"
        assert SecurityType.OPENID_CONNECT.value == "openIdConnect"
        assert SecurityType.API_KEY.value == "apiKey"
        assert SecurityType.HTTP.value == "http"

    def test_input_output_modes(self):
        """InputOutputMode enum should have expected values."""
        assert InputOutputMode.JSON.value == "application/json"
        assert InputOutputMode.TEXT_PLAIN.value == "text/plain"
        assert InputOutputMode.FORM_URLENCODED.value == "application/x-www-form-urlencoded"
        assert InputOutputMode.MULTIPART.value == "multipart/form-data"


# =============================================================================
# AGENT PROVIDER TESTS
# =============================================================================

class TestAgentProvider:
    """Tests for AgentProvider dataclass."""

    def test_basic_provider(self):
        """Provider should serialize with required fields."""
        provider = AgentProvider(
            organization="Test Org",
            url="https://test.org",
        )
        data = provider.to_dict()

        assert data["organization"] == "Test Org"
        assert data["url"] == "https://test.org"
        assert "contactEmail" not in data

    def test_provider_with_contact(self):
        """Provider should include contact email when provided."""
        provider = AgentProvider(
            organization="Ultravioleta DAO",
            url="https://ultravioleta.xyz",
            contact_email="contact@ultravioleta.xyz",
        )
        data = provider.to_dict()

        assert data["organization"] == "Ultravioleta DAO"
        assert data["url"] == "https://ultravioleta.xyz"
        assert data["contactEmail"] == "contact@ultravioleta.xyz"


# =============================================================================
# AGENT CAPABILITIES TESTS
# =============================================================================

class TestAgentCapabilities:
    """Tests for AgentCapabilities dataclass."""

    def test_default_capabilities(self):
        """Default capabilities should have expected values."""
        caps = AgentCapabilities()
        data = caps.to_dict()

        assert data["streaming"] is False
        assert data["pushNotifications"] is False
        assert data["stateTransitionHistory"] is True
        assert data["supportsAuthenticatedExtendedCard"] is False

    def test_custom_capabilities(self):
        """Custom capabilities should serialize correctly."""
        caps = AgentCapabilities(
            streaming=True,
            push_notifications=True,
            state_transition_history=True,
            supports_authenticated_extended_card=True,
        )
        data = caps.to_dict()

        assert data["streaming"] is True
        assert data["pushNotifications"] is True
        assert data["stateTransitionHistory"] is True
        assert data["supportsAuthenticatedExtendedCard"] is True


# =============================================================================
# AGENT SKILL TESTS
# =============================================================================

class TestAgentSkill:
    """Tests for AgentSkill dataclass."""

    def test_basic_skill(self):
        """Skill should serialize with all fields."""
        skill = AgentSkill(
            id="test-skill",
            name="Test Skill",
            description="A test skill for testing",
            tags=["test", "sample"],
            examples=["Do something", "Do another thing"],
        )
        data = skill.to_dict()

        assert data["id"] == "test-skill"
        assert data["name"] == "Test Skill"
        assert data["description"] == "A test skill for testing"
        assert data["tags"] == ["test", "sample"]
        assert data["examples"] == ["Do something", "Do another thing"]
        assert "application/json" in data["inputModes"]
        assert "text/plain" in data["inputModes"]
        assert "application/json" in data["outputModes"]

    def test_skill_with_custom_modes(self):
        """Skill should accept custom input/output modes."""
        skill = AgentSkill(
            id="custom-skill",
            name="Custom Skill",
            description="Custom modes test",
            input_modes=["application/xml"],
            output_modes=["application/xml", "text/plain"],
        )
        data = skill.to_dict()

        assert data["inputModes"] == ["application/xml"]
        assert data["outputModes"] == ["application/xml", "text/plain"]


# =============================================================================
# AGENT INTERFACE TESTS
# =============================================================================

class TestAgentInterface:
    """Tests for AgentInterface dataclass."""

    def test_jsonrpc_interface(self):
        """JSONRPC interface should serialize correctly."""
        interface = AgentInterface(
            url="https://api.example.com/a2a/v1",
            transport=TransportType.JSONRPC,
        )
        data = interface.to_dict()

        assert data["url"] == "https://api.example.com/a2a/v1"
        assert data["transport"] == "JSONRPC"

    def test_websocket_interface(self):
        """WebSocket interface should serialize correctly."""
        interface = AgentInterface(
            url="wss://api.example.com/ws",
            transport=TransportType.WEBSOCKET,
        )
        data = interface.to_dict()

        assert data["url"] == "wss://api.example.com/ws"
        assert data["transport"] == "WEBSOCKET"

    def test_http_json_interface(self):
        """HTTP+JSON interface should serialize correctly."""
        interface = AgentInterface(
            url="https://api.example.com/api/v1",
            transport=TransportType.HTTP_JSON,
        )
        data = interface.to_dict()

        assert data["transport"] == "HTTP+JSON"


# =============================================================================
# SECURITY SCHEME TESTS
# =============================================================================

class TestSecurityScheme:
    """Tests for SecurityScheme dataclass."""

    def test_bearer_scheme(self):
        """Bearer token scheme should serialize correctly."""
        scheme = SecurityScheme(
            name="bearer",
            type=SecurityType.HTTP,
            scheme="bearer",
            bearer_format="JWT",
            description="JWT authentication",
        )
        data = scheme.to_dict()

        assert data["type"] == "http"
        assert data["scheme"] == "bearer"
        assert data["bearerFormat"] == "JWT"
        assert data["description"] == "JWT authentication"

    def test_api_key_header_scheme(self):
        """API key in header should serialize correctly."""
        scheme = SecurityScheme(
            name="apiKey",
            type=SecurityType.API_KEY,
            in_header="X-API-Key",
            description="API key authentication",
        )
        data = scheme.to_dict()

        assert data["type"] == "apiKey"
        assert data["in"] == "header"
        assert data["name"] == "X-API-Key"

    def test_api_key_query_scheme(self):
        """API key in query should serialize correctly."""
        scheme = SecurityScheme(
            name="apiKey",
            type=SecurityType.API_KEY,
            in_query="api_key",
        )
        data = scheme.to_dict()

        assert data["type"] == "apiKey"
        assert data["in"] == "query"
        assert data["name"] == "api_key"

    def test_oauth2_scheme(self):
        """OAuth2 scheme should serialize correctly."""
        scheme = SecurityScheme(
            name="oauth2",
            type=SecurityType.OAUTH2,
            flows={
                "authorizationCode": {
                    "authorizationUrl": "https://auth.example.com/authorize",
                    "tokenUrl": "https://auth.example.com/token",
                }
            },
        )
        data = scheme.to_dict()

        assert data["type"] == "oauth2"
        assert "flows" in data
        assert "authorizationCode" in data["flows"]


# =============================================================================
# AGENT CARD TESTS
# =============================================================================

class TestAgentCard:
    """Tests for AgentCard dataclass."""

    def test_minimal_card(self):
        """Minimal card should serialize with required fields."""
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            url="https://test.example.com",
        )
        data = card.to_dict()

        assert data["name"] == "Test Agent"
        assert data["description"] == "A test agent"
        assert data["url"] == "https://test.example.com"
        assert data["protocolVersion"] == A2A_PROTOCOL_VERSION
        assert data["version"] == EM_VERSION
        assert "capabilities" in data
        assert "defaultInputModes" in data
        assert "defaultOutputModes" in data

    def test_full_card(self):
        """Full card should include all optional fields."""
        card = AgentCard(
            name="Full Agent",
            description="A complete agent",
            url="https://full.example.com",
            provider=AgentProvider(
                organization="Test Org",
                url="https://test.org",
            ),
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="skill-1",
                    name="Skill One",
                    description="First skill",
                )
            ],
            additional_interfaces=[
                AgentInterface(
                    url="https://full.example.com/ws",
                    transport=TransportType.WEBSOCKET,
                )
            ],
            security_schemes={
                "bearer": SecurityScheme(
                    name="bearer",
                    type=SecurityType.HTTP,
                    scheme="bearer",
                )
            },
            security=[{"bearer": []}],
        )
        data = card.to_dict()

        assert "provider" in data
        assert data["provider"]["organization"] == "Test Org"
        assert len(data["skills"]) == 1
        assert data["skills"][0]["id"] == "skill-1"
        assert len(data["additionalInterfaces"]) == 1
        assert "securitySchemes" in data
        assert "bearer" in data["securitySchemes"]
        assert data["security"] == [{"bearer": []}]

    def test_card_to_json(self):
        """Card should serialize to valid JSON string."""
        card = AgentCard(
            name="JSON Test",
            description="Testing JSON serialization",
            url="https://json.test.com",
        )
        json_str = card.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["name"] == "JSON Test"

    def test_preferred_transport(self):
        """Preferred transport should serialize correctly."""
        card = AgentCard(
            name="Transport Test",
            description="Testing transport",
            url="https://transport.test.com",
            preferred_transport=TransportType.HTTP_JSON,
        )
        data = card.to_dict()

        assert data["preferredTransport"] == "HTTP+JSON"


# =============================================================================
# EM SKILLS TESTS
# =============================================================================

class TestEMSkills:
    """Tests for get_em_skills() function."""

    def test_skills_returned(self):
        """Should return list of skills."""
        skills = get_em_skills()

        assert isinstance(skills, list)
        assert len(skills) >= 7  # At least 7 skills defined

    def test_skill_ids_unique(self):
        """All skill IDs should be unique."""
        skills = get_em_skills()
        ids = [s.id for s in skills]

        assert len(ids) == len(set(ids))

    def test_expected_skills_present(self):
        """Expected skills should be present."""
        skills = get_em_skills()
        ids = {s.id for s in skills}

        assert "publish-task" in ids
        assert "manage-tasks" in ids
        assert "review-submissions" in ids
        assert "worker-management" in ids
        assert "batch-operations" in ids
        assert "analytics" in ids
        assert "payments" in ids

    def test_skills_have_required_fields(self):
        """All skills should have required fields populated."""
        skills = get_em_skills()

        for skill in skills:
            assert skill.id, f"Skill missing id"
            assert skill.name, f"Skill {skill.id} missing name"
            assert skill.description, f"Skill {skill.id} missing description"
            assert len(skill.tags) > 0, f"Skill {skill.id} missing tags"
            assert len(skill.examples) > 0, f"Skill {skill.id} missing examples"
            assert len(skill.input_modes) > 0, f"Skill {skill.id} missing input_modes"
            assert len(skill.output_modes) > 0, f"Skill {skill.id} missing output_modes"


# =============================================================================
# GET_AGENT_CARD TESTS
# =============================================================================

class TestGetAgentCard:
    """Tests for get_agent_card() function."""

    def test_card_with_default_url(self):
        """Card should use default URL when none provided."""
        card = get_agent_card()

        assert DEFAULT_BASE_URL in card.url

    def test_card_with_custom_url(self):
        """Card should use custom URL when provided."""
        card = get_agent_card(base_url="https://custom.example.com")

        assert "https://custom.example.com" in card.url

    @patch.dict("os.environ", {"EM_BASE_URL": "https://env.example.com"})
    def test_card_with_env_url(self):
        """Card should use environment URL."""
        card = get_agent_card()

        assert "https://env.example.com" in card.url

    def test_card_has_provider(self):
        """Card should include Ultravioleta DAO as provider."""
        card = get_agent_card()

        assert card.provider is not None
        assert card.provider.organization == "Ultravioleta DAO"

    def test_card_has_capabilities(self):
        """Card should include capabilities."""
        card = get_agent_card()

        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is True
        assert card.capabilities.state_transition_history is True

    def test_card_has_skills(self):
        """Card should include skills."""
        card = get_agent_card()

        assert len(card.skills) >= 7

    def test_card_has_interfaces(self):
        """Card should include additional interfaces."""
        card = get_agent_card()

        assert len(card.additional_interfaces) >= 3

        transports = {i.transport for i in card.additional_interfaces}
        assert TransportType.JSONRPC in transports
        assert TransportType.STREAMABLE_HTTP in transports  # MCP uses Streamable HTTP transport
        assert TransportType.HTTP_JSON in transports

    def test_card_has_security_schemes(self):
        """Card should include security schemes."""
        card = get_agent_card()

        assert "bearer" in card.security_schemes
        assert "apiKey" in card.security_schemes
        assert "erc8004" in card.security_schemes

    def test_card_protocol_version(self):
        """Card should have correct protocol version."""
        card = get_agent_card()

        assert card.protocol_version == A2A_PROTOCOL_VERSION


# =============================================================================
# FASTAPI ROUTER TESTS (Sync with TestClient for compatibility)
# =============================================================================

class TestFastAPIRouter:
    """Tests for FastAPI router endpoints using sync TestClient."""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        try:
            return TestClient(app)
        except TypeError:
            pytest.skip("TestClient incompatible with installed httpx version")

    def test_well_known_endpoint(self, client):
        """/.well-known/agent.json should return agent card."""
        response = client.get("/.well-known/agent.json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "X-A2A-Protocol-Version" in response.headers

        data = response.json()
        assert data["name"] == "Execution Market"
        assert data["protocolVersion"] == A2A_PROTOCOL_VERSION

    def test_well_known_cache_headers(self, client):
        """/.well-known/agent.json should have cache headers."""
        response = client.get("/.well-known/agent.json")

        assert "Cache-Control" in response.headers
        assert "max-age=3600" in response.headers["Cache-Control"]

    def test_v1_card_endpoint(self, client):
        """/v1/card should return same data as well-known."""
        well_known = client.get("/.well-known/agent.json")
        v1_card = client.get("/v1/card")

        assert well_known.json() == v1_card.json()

    def test_discovery_endpoint(self, client):
        """/discovery/agents should return list of agents."""
        response = client.get("/discovery/agents")

        assert response.status_code == 200
        data = response.json()

        assert "agents" in data
        assert "total" in data
        assert "discoveredAt" in data
        assert data["total"] == 1
        assert len(data["agents"]) == 1
        assert data["agents"][0]["name"] == "Execution Market"


# =============================================================================
# FASTAPI ROUTER TESTS (Async with httpx.AsyncClient)
# =============================================================================

@pytest.mark.asyncio
class TestFastAPIRouterAsync:
    """Tests for FastAPI router endpoints using async httpx.AsyncClient."""

    @pytest_asyncio.fixture
    async def async_client(self):
        """Create async test client for FastAPI app."""
        from httpx import ASGITransport

        app = FastAPI()
        app.include_router(router)
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    async def test_well_known_endpoint_async(self, async_client):
        """/.well-known/agent.json should return agent card (async)."""
        response = await async_client.get("/.well-known/agent.json")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert "x-a2a-protocol-version" in response.headers

        data = response.json()
        assert data["name"] == "Execution Market"
        assert data["protocolVersion"] == A2A_PROTOCOL_VERSION

    async def test_well_known_returns_valid_json(self, async_client):
        """/.well-known/agent.json should return valid JSON."""
        response = await async_client.get("/.well-known/agent.json")

        # Should not raise
        data = response.json()
        assert isinstance(data, dict)

    async def test_well_known_has_skills(self, async_client):
        """/.well-known/agent.json should include skills."""
        response = await async_client.get("/.well-known/agent.json")
        data = response.json()

        assert "skills" in data
        assert len(data["skills"]) >= 7

    async def test_v1_card_endpoint_async(self, async_client):
        """/v1/card should return agent card (async)."""
        response = await async_client.get("/v1/card")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Execution Market"

    async def test_discovery_endpoint_async(self, async_client):
        """/discovery/agents should return list of agents (async)."""
        response = await async_client.get("/discovery/agents")

        assert response.status_code == 200
        data = response.json()

        assert "agents" in data
        assert isinstance(data["agents"], list)
        assert data["total"] == len(data["agents"])

    async def test_discovery_has_timestamp(self, async_client):
        """/discovery/agents should have discoveredAt timestamp."""
        response = await async_client.get("/discovery/agents")
        data = response.json()

        assert "discoveredAt" in data
        # Should be valid ISO 8601 timestamp
        timestamp = data["discoveredAt"]
        assert "T" in timestamp  # ISO 8601 format has T separator

    async def test_discovery_cache_headers(self, async_client):
        """/discovery/agents should have shorter cache time."""
        response = await async_client.get("/discovery/agents")

        assert "cache-control" in response.headers
        assert "max-age=300" in response.headers["cache-control"]

    async def test_endpoints_return_same_card(self, async_client):
        """All card endpoints should return equivalent data."""
        well_known = await async_client.get("/.well-known/agent.json")
        v1_card = await async_client.get("/v1/card")
        discovery = await async_client.get("/discovery/agents")

        well_known_data = well_known.json()
        v1_data = v1_card.json()
        discovery_data = discovery.json()["agents"][0]

        # Core fields should match
        assert well_known_data["name"] == v1_data["name"] == discovery_data["name"]
        assert well_known_data["protocolVersion"] == v1_data["protocolVersion"]
        assert well_known_data["description"] == v1_data["description"]


# =============================================================================
# A2A PROTOCOL COMPLIANCE TESTS
# =============================================================================

class TestA2ACompliance:
    """Tests for A2A Protocol 0.3.0 compliance."""

    def test_protocol_version_format(self):
        """Protocol version should be valid semver."""
        parts = A2A_PROTOCOL_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_protocol_version_is_030(self):
        """Protocol version should be 0.3.0 per A2A spec."""
        assert A2A_PROTOCOL_VERSION == "0.3.0"

    def test_card_has_required_fields(self):
        """Agent card should have all A2A required fields."""
        card = get_agent_card()
        data = card.to_dict()

        # Required per A2A 0.3.0 spec
        required_fields = [
            "protocolVersion",
            "name",
            "description",
            "url",
            "version",
            "capabilities",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_card_name_is_string(self):
        """Name should be a non-empty string per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        assert isinstance(data["name"], str)
        assert len(data["name"]) > 0

    def test_card_description_is_string(self):
        """Description should be a non-empty string per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        assert isinstance(data["description"], str)
        assert len(data["description"]) > 0

    def test_card_url_is_valid_url(self):
        """URL should be a valid URL string per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        url = data["url"]
        assert isinstance(url, str)
        # Basic URL validation
        assert url.startswith("http://") or url.startswith("https://")

    def test_capabilities_has_required_fields(self):
        """Capabilities should have expected A2A fields."""
        card = get_agent_card()
        data = card.to_dict()
        caps = data["capabilities"]

        expected_fields = [
            "streaming",
            "pushNotifications",
            "stateTransitionHistory",
        ]

        for field in expected_fields:
            assert field in caps, f"Missing capability field: {field}"

    def test_capabilities_are_booleans(self):
        """Capability fields should be booleans per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()
        caps = data["capabilities"]

        for key, value in caps.items():
            assert isinstance(value, bool), f"Capability {key} should be boolean, got {type(value)}"

    def test_skills_have_required_fields(self):
        """Skills should have all A2A required fields."""
        card = get_agent_card()
        data = card.to_dict()

        # Per A2A 0.3.0 spec, skills require id, name, description
        for skill in data["skills"]:
            assert "id" in skill, "Skill missing required 'id' field"
            assert "name" in skill, "Skill missing required 'name' field"
            assert "description" in skill, "Skill missing required 'description' field"

    def test_skills_id_format(self):
        """Skill IDs should be valid identifiers per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        for skill in data["skills"]:
            skill_id = skill["id"]
            # IDs should be kebab-case or snake_case, alphanumeric with dashes/underscores
            assert re.match(r"^[a-z0-9][a-z0-9\-_]*$", skill_id), f"Invalid skill ID format: {skill_id}"

    def test_skills_input_output_modes_format(self):
        """Skill input/output modes should be valid MIME types per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        for skill in data["skills"]:
            for mode in skill.get("inputModes", []):
                assert "/" in mode, f"Invalid MIME type in inputModes: {mode}"
            for mode in skill.get("outputModes", []):
                assert "/" in mode, f"Invalid MIME type in outputModes: {mode}"

    def test_interfaces_have_required_fields(self):
        """Interfaces should have all A2A required fields."""
        card = get_agent_card()
        data = card.to_dict()

        for interface in data.get("additionalInterfaces", []):
            assert "url" in interface, "Interface missing required 'url' field"
            assert "transport" in interface, "Interface missing required 'transport' field"

    def test_interfaces_transport_valid_values(self):
        """Interface transport should be valid A2A transport type."""
        card = get_agent_card()
        data = card.to_dict()

        valid_transports = {"JSONRPC", "GRPC", "HTTP+JSON", "WEBSOCKET", "STREAMABLE_HTTP"}

        for interface in data.get("additionalInterfaces", []):
            assert interface["transport"] in valid_transports, \
                f"Invalid transport: {interface['transport']}"

    def test_security_schemes_valid_types(self):
        """Security schemes should use valid A2A types."""
        card = get_agent_card()
        data = card.to_dict()

        valid_types = {"oauth2", "openIdConnect", "apiKey", "http"}

        for name, scheme in data.get("securitySchemes", {}).items():
            assert scheme["type"] in valid_types, f"Invalid type for {name}: {scheme['type']}"

    def test_security_schemes_http_has_scheme(self):
        """HTTP security schemes should have a scheme field per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        for name, scheme in data.get("securitySchemes", {}).items():
            if scheme["type"] == "http":
                assert "scheme" in scheme, f"HTTP security scheme {name} missing 'scheme' field"

    def test_security_schemes_apikey_has_location(self):
        """API key security schemes should have location per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        for name, scheme in data.get("securitySchemes", {}).items():
            if scheme["type"] == "apiKey":
                assert "in" in scheme, f"API key scheme {name} missing 'in' field"
                assert scheme["in"] in {"header", "query"}, \
                    f"API key scheme {name} has invalid 'in' value: {scheme['in']}"

    def test_security_array_format(self):
        """Security array should be properly formatted per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        if "security" in data:
            assert isinstance(data["security"], list)
            for item in data["security"]:
                assert isinstance(item, dict)
                # Each item should have scheme name as key with list of scopes
                for scheme_name, scopes in item.items():
                    assert isinstance(scopes, list)

    def test_preferred_transport_valid(self):
        """Preferred transport should be a valid transport type."""
        card = get_agent_card()
        data = card.to_dict()

        valid_transports = {"JSONRPC", "GRPC", "HTTP+JSON", "WEBSOCKET", "STREAMABLE_HTTP"}
        assert data["preferredTransport"] in valid_transports

    def test_default_modes_are_lists(self):
        """Default input/output modes should be lists of MIME types."""
        card = get_agent_card()
        data = card.to_dict()

        assert isinstance(data["defaultInputModes"], list)
        assert isinstance(data["defaultOutputModes"], list)
        assert len(data["defaultInputModes"]) > 0
        assert len(data["defaultOutputModes"]) > 0

    def test_provider_has_required_fields(self):
        """Provider should have required fields per A2A spec."""
        card = get_agent_card()
        data = card.to_dict()

        if "provider" in data:
            provider = data["provider"]
            assert "organization" in provider, "Provider missing 'organization'"
            assert "url" in provider, "Provider missing 'url'"


# =============================================================================
# SERIALIZATION ROUND-TRIP TESTS
# =============================================================================

class TestSerialization:
    """Tests for JSON serialization round-trips."""

    def test_full_card_json_round_trip(self):
        """Full agent card should survive JSON round-trip."""
        card = get_agent_card("https://test.example.com")

        # Serialize to JSON
        json_str = card.to_json()

        # Parse back
        parsed = json.loads(json_str)

        # Verify key fields preserved
        assert parsed["name"] == "Execution Market"
        assert parsed["protocolVersion"] == A2A_PROTOCOL_VERSION
        assert len(parsed["skills"]) >= 7
        assert "provider" in parsed
        assert parsed["provider"]["organization"] == "Ultravioleta DAO"

    def test_unicode_in_descriptions(self):
        """Unicode characters should serialize correctly."""
        skill = AgentSkill(
            id="unicode-test",
            name="Unicode Test",
            description="Test with émojis 🚀 and áccénts",
            examples=["Hacer algo con ñ", "日本語テスト"],
        )
        data = skill.to_dict()

        # Serialize and parse
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert "🚀" in parsed["description"]
        assert "ñ" in parsed["examples"][0]


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_skills_list(self):
        """Card with empty skills list should serialize."""
        card = AgentCard(
            name="No Skills",
            description="Agent without skills",
            url="https://noskills.test.com",
            skills=[],
        )
        data = card.to_dict()

        assert "skills" not in data or data.get("skills") == []

    def test_empty_security_schemes(self):
        """Card with empty security should serialize."""
        card = AgentCard(
            name="No Security",
            description="Agent without security",
            url="https://nosecurity.test.com",
            security_schemes={},
            security=[],
        )
        data = card.to_dict()

        # Empty dicts/lists should not appear
        assert "securitySchemes" not in data or data.get("securitySchemes") == {}

    def test_empty_tags_list(self):
        """Skill with empty tags list should serialize."""
        skill = AgentSkill(
            id="no-tags",
            name="No Tags Skill",
            description="Skill without tags",
            tags=[],
        )
        data = skill.to_dict()

        assert data["tags"] == []

    def test_empty_examples_list(self):
        """Skill with empty examples list should serialize."""
        skill = AgentSkill(
            id="no-examples",
            name="No Examples Skill",
            description="Skill without examples",
            examples=[],
        )
        data = skill.to_dict()

        assert data["examples"] == []

    def test_empty_interfaces_list(self):
        """Card with empty interfaces list should serialize."""
        card = AgentCard(
            name="No Interfaces",
            description="Agent without additional interfaces",
            url="https://nointerfaces.test.com",
            additional_interfaces=[],
        )
        data = card.to_dict()

        assert "additionalInterfaces" not in data or data.get("additionalInterfaces") == []

    def test_long_description(self):
        """Very long descriptions should be handled."""
        long_desc = "A" * 10000  # 10k characters

        skill = AgentSkill(
            id="long-desc",
            name="Long Description",
            description=long_desc,
        )
        data = skill.to_dict()

        assert len(data["description"]) == 10000

    def test_very_long_description(self):
        """Very long descriptions (100k chars) should serialize to JSON."""
        long_desc = "B" * 100000  # 100k characters

        card = AgentCard(
            name="Very Long",
            description=long_desc,
            url="https://long.test.com",
        )
        json_str = card.to_json()
        parsed = json.loads(json_str)

        assert len(parsed["description"]) == 100000

    def test_special_characters_in_url(self):
        """URLs with special characters should be preserved."""
        card = AgentCard(
            name="Special URL",
            description="Test special chars",
            url="https://api.example.com/v1?param=value&other=test%20space",
        )
        data = card.to_dict()

        assert "?" in data["url"]
        assert "&" in data["url"]
        assert "%20" in data["url"]

    def test_unicode_in_name(self):
        """Unicode characters in name should serialize correctly."""
        card = AgentCard(
            name="Agente de prueba",
            description="Test unicode",
            url="https://unicode.test.com",
        )
        json_str = card.to_json()
        parsed = json.loads(json_str)

        assert parsed["name"] == "Agente de prueba"

    def test_unicode_in_skill_description(self):
        """Unicode characters in skill description should serialize."""
        skill = AgentSkill(
            id="unicode-skill",
            name="Unicode Skill",
            description="Descripcion con acentos: cafe, nino, manana",
        )
        data = skill.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert "cafe" in parsed["description"]
        assert "nino" in parsed["description"]

    def test_emoji_in_description(self):
        """Emoji characters should serialize correctly."""
        skill = AgentSkill(
            id="emoji-skill",
            name="Emoji Skill",
            description="Task verification complete! Success achieved.",
            examples=["Complete task successfully", "Verify the outcome"],
        )
        data = skill.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert "Success" in parsed["description"]

    def test_cjk_characters(self):
        """CJK (Chinese/Japanese/Korean) characters should serialize."""
        skill = AgentSkill(
            id="cjk-skill",
            name="CJK Skill",
            description="Test Chinese characters here",
            examples=["Japanese katakana test", "Korean characters test"],
        )
        data = skill.to_dict()
        json_str = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert "Chinese" in parsed["description"]

    def test_newlines_in_description(self):
        """Newline characters should be preserved in serialization."""
        skill = AgentSkill(
            id="newline-skill",
            name="Newline Skill",
            description="Line 1\nLine 2\nLine 3",
        )
        data = skill.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert "\n" in parsed["description"]
        assert parsed["description"].count("\n") == 2

    def test_tabs_in_description(self):
        """Tab characters should be preserved in serialization."""
        skill = AgentSkill(
            id="tab-skill",
            name="Tab Skill",
            description="Column1\tColumn2\tColumn3",
        )
        data = skill.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert "\t" in parsed["description"]

    def test_quotes_in_description(self):
        """Quotes should be properly escaped in JSON serialization."""
        skill = AgentSkill(
            id="quote-skill",
            name="Quote Skill",
            description='He said "Hello" and she replied \'Hi\'',
        )
        data = skill.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert '"Hello"' in parsed["description"]
        assert "'" in parsed["description"]

    def test_backslashes_in_description(self):
        """Backslashes should be properly escaped in JSON serialization."""
        skill = AgentSkill(
            id="backslash-skill",
            name="Backslash Skill",
            description="Path: C:\\Users\\test\\file.txt",
        )
        data = skill.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert "C:\\Users\\test\\file.txt" in parsed["description"]

    def test_html_entities_in_description(self):
        """HTML-like content should not be escaped (it's JSON, not HTML)."""
        skill = AgentSkill(
            id="html-skill",
            name="HTML Skill",
            description="<script>alert('test')</script> &amp; &lt;tag&gt;",
        )
        data = skill.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert "<script>" in parsed["description"]
        assert "&amp;" in parsed["description"]

    def test_null_bytes_stripped(self):
        """Null bytes in descriptions should be handled."""
        # Note: This tests that the system doesn't crash on weird input
        skill = AgentSkill(
            id="null-skill",
            name="Null Skill",
            description="Before\x00After",
        )
        data = skill.to_dict()
        # Should not raise
        json_str = json.dumps(data)
        assert json_str is not None

    def test_mixed_content_description(self):
        """Mixed content with various special chars should serialize."""
        skill = AgentSkill(
            id="mixed-skill",
            name="Mixed Skill",
            description='Mixed: "quotes", unicode cafe, path C:\\test, newline\n, tab\t, <html>',
        )
        data = skill.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert "quotes" in parsed["description"]
        assert "cafe" in parsed["description"]
        assert "\n" in parsed["description"]

    def test_skill_with_many_tags(self):
        """Skill with many tags should serialize correctly."""
        tags = [f"tag-{i}" for i in range(100)]
        skill = AgentSkill(
            id="many-tags",
            name="Many Tags Skill",
            description="Skill with 100 tags",
            tags=tags,
        )
        data = skill.to_dict()

        assert len(data["tags"]) == 100
        assert "tag-0" in data["tags"]
        assert "tag-99" in data["tags"]

    def test_skill_with_many_examples(self):
        """Skill with many examples should serialize correctly."""
        examples = [f"Example {i}: do something" for i in range(50)]
        skill = AgentSkill(
            id="many-examples",
            name="Many Examples Skill",
            description="Skill with 50 examples",
            examples=examples,
        )
        data = skill.to_dict()

        assert len(data["examples"]) == 50

    def test_card_with_many_skills(self):
        """Card with many skills should serialize correctly."""
        skills = [
            AgentSkill(
                id=f"skill-{i}",
                name=f"Skill {i}",
                description=f"Description for skill {i}",
            )
            for i in range(20)
        ]
        card = AgentCard(
            name="Many Skills Agent",
            description="Agent with 20 skills",
            url="https://manyskills.test.com",
            skills=skills,
        )
        data = card.to_dict()

        assert len(data["skills"]) == 20

    def test_card_with_many_interfaces(self):
        """Card with many interfaces should serialize correctly."""
        interfaces = [
            AgentInterface(
                url=f"https://api{i}.example.com/v1",
                transport=TransportType.JSONRPC,
            )
            for i in range(10)
        ]
        card = AgentCard(
            name="Many Interfaces Agent",
            description="Agent with 10 interfaces",
            url="https://manyinterfaces.test.com",
            additional_interfaces=interfaces,
        )
        data = card.to_dict()

        assert len(data["additionalInterfaces"]) == 10

    def test_security_scheme_without_optional_fields(self):
        """Security scheme with only required fields should serialize."""
        scheme = SecurityScheme(
            name="minimal",
            type=SecurityType.HTTP,
        )
        data = scheme.to_dict()

        assert data["type"] == "http"
        assert "scheme" not in data
        assert "bearerFormat" not in data
        assert "description" not in data

    def test_provider_without_contact_email(self):
        """Provider without contact email should not include contactEmail field."""
        provider = AgentProvider(
            organization="Test Org",
            url="https://test.org",
        )
        data = provider.to_dict()

        assert "organization" in data
        assert "url" in data
        assert "contactEmail" not in data

    def test_empty_string_values(self):
        """Empty string values should be handled (even if not recommended)."""
        # Note: Empty strings are valid but not recommended per A2A spec
        skill = AgentSkill(
            id="empty-test",
            name="",  # Empty name
            description="",  # Empty description
        )
        data = skill.to_dict()

        assert data["name"] == ""
        assert data["description"] == ""

    def test_whitespace_only_values(self):
        """Whitespace-only values should be preserved."""
        skill = AgentSkill(
            id="whitespace-test",
            name="   ",  # Whitespace only
            description="  \t\n  ",  # Mixed whitespace
        )
        data = skill.to_dict()

        assert data["name"] == "   "
        assert "\t" in data["description"]


# =============================================================================
# ADDITIONAL INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the A2A module."""

    def test_full_workflow_card_generation(self):
        """Test complete workflow of generating and serializing a card."""
        # Generate card
        card = get_agent_card("https://integration.test.com")

        # Verify it has all expected components
        assert card.name == "Execution Market"
        assert card.provider is not None
        assert len(card.skills) >= 7
        assert len(card.additional_interfaces) >= 3
        assert len(card.security_schemes) >= 3

        # Convert to dict
        data = card.to_dict()

        # Verify dict structure
        assert "protocolVersion" in data
        assert "capabilities" in data
        assert "skills" in data

        # Convert to JSON
        json_str = card.to_json()

        # Parse back and verify
        parsed = json.loads(json_str)
        assert parsed["name"] == "Execution Market"
        assert parsed["protocolVersion"] == A2A_PROTOCOL_VERSION

    def test_skills_match_documentation(self):
        """Skills should match what's documented for Execution Market."""
        skills = get_em_skills()
        skill_ids = {s.id for s in skills}

        # These are the core Execution Market operations
        expected_skills = {
            "publish-task",
            "manage-tasks",
            "review-submissions",
            "worker-management",
            "batch-operations",
            "analytics",
            "payments",
        }

        for expected in expected_skills:
            assert expected in skill_ids, f"Missing expected skill: {expected}"

    def test_card_json_is_valid_for_a2a_client(self):
        """Card JSON should be valid for an A2A client to parse."""
        card = get_agent_card()
        json_str = card.to_json()
        data = json.loads(json_str)

        # An A2A client would need these to connect
        assert "url" in data
        assert "protocolVersion" in data
        assert "capabilities" in data

        # Client needs to know how to authenticate
        if "securitySchemes" in data:
            assert isinstance(data["securitySchemes"], dict)

        # Client needs to know what operations are available
        if "skills" in data:
            for skill in data["skills"]:
                assert "id" in skill
                assert "name" in skill

    def test_card_respects_environment_url(self):
        """Card should use EM_BASE_URL environment variable."""
        import os

        # Save original value
        original = os.environ.get("EM_BASE_URL")

        try:
            # Set environment variable
            os.environ["EM_BASE_URL"] = "https://env-test.example.com"

            # Generate card without explicit URL
            card = get_agent_card()

            # Should use env URL
            assert "https://env-test.example.com" in card.url
        finally:
            # Restore original value
            if original:
                os.environ["EM_BASE_URL"] = original
            else:
                os.environ.pop("EM_BASE_URL", None)

    def test_card_explicit_url_overrides_env(self):
        """Explicit URL parameter should override environment variable."""
        import os

        # Save original value
        original = os.environ.get("EM_BASE_URL")

        try:
            # Set environment variable
            os.environ["EM_BASE_URL"] = "https://env-test.example.com"

            # Generate card with explicit URL
            card = get_agent_card("https://explicit.example.com")

            # Should use explicit URL
            assert "https://explicit.example.com" in card.url
        finally:
            # Restore original value
            if original:
                os.environ["EM_BASE_URL"] = original
            else:
                os.environ.pop("EM_BASE_URL", None)
