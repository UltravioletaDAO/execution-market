# NOW-193: Tests para A2A Agent Card

**Prioridad**: P1
**Status**: DONE ✅
**Archivo**: `mcp_server/tests/test_a2a.py`

## Descripción

Tests comprehensivos para el módulo A2A Agent Card que implementa el protocolo A2A 0.3.0.

## Tests Implementados (47 casos)

### Enum Tests
- `test_transport_types` - Valores de TransportType enum
- `test_security_types` - Valores de SecurityType enum
- `test_input_output_modes` - Valores de InputOutputMode enum

### AgentProvider Tests
- `test_basic_provider` - Serialización con campos requeridos
- `test_provider_with_contact` - Serialización con contactEmail

### AgentCapabilities Tests
- `test_default_capabilities` - Valores por defecto
- `test_custom_capabilities` - Valores personalizados

### AgentSkill Tests
- `test_basic_skill` - Serialización completa
- `test_skill_with_custom_modes` - Input/output modes personalizados

### AgentInterface Tests
- `test_jsonrpc_interface` - Interface JSONRPC
- `test_websocket_interface` - Interface WebSocket
- `test_http_json_interface` - Interface HTTP+JSON

### SecurityScheme Tests
- `test_bearer_scheme` - Esquema bearer token
- `test_api_key_header_scheme` - API key en header
- `test_api_key_query_scheme` - API key en query
- `test_oauth2_scheme` - OAuth2 flows

### AgentCard Tests
- `test_minimal_card` - Card con campos mínimos
- `test_full_card` - Card con todos los campos
- `test_card_to_json` - Serialización a JSON string
- `test_preferred_transport` - Transport preference

### get_chamba_skills Tests
- `test_skills_returned` - Retorna lista de skills
- `test_skill_ids_unique` - IDs únicos
- `test_expected_skills_present` - Skills esperados existen
- `test_skills_have_required_fields` - Campos requeridos

### get_agent_card Tests
- `test_card_with_default_url` - URL por defecto
- `test_card_with_custom_url` - URL personalizada
- `test_card_with_env_url` - URL de variable de entorno
- `test_card_has_provider` - Incluye provider
- `test_card_has_capabilities` - Incluye capabilities
- `test_card_has_skills` - Incluye skills
- `test_card_has_interfaces` - Incluye interfaces
- `test_card_has_security_schemes` - Incluye security schemes
- `test_card_protocol_version` - Version correcta

### FastAPI Router Tests
- `test_well_known_endpoint` - /.well-known/agent.json
- `test_well_known_cache_headers` - Cache headers
- `test_v1_card_endpoint` - /v1/card
- `test_discovery_endpoint` - /discovery/agents

### A2A Compliance Tests
- `test_protocol_version_format` - Formato semver
- `test_card_has_required_fields` - Campos requeridos A2A
- `test_capabilities_has_required_fields` - Capability fields
- `test_skills_have_required_fields` - Skill fields
- `test_interfaces_have_required_fields` - Interface fields
- `test_security_schemes_valid_types` - Tipos de security válidos

### Serialization Tests
- `test_full_card_json_round_trip` - Round-trip JSON
- `test_unicode_in_descriptions` - Unicode handling

### Edge Case Tests
- `test_empty_skills_list` - Lista vacía de skills
- `test_empty_security_schemes` - Security vacío
- `test_long_description` - Descripciones largas
- `test_special_characters_in_url` - Caracteres especiales en URL

## Ejecución

```bash
# Desde Docker
docker run --rm -v "//z/ultravioleta/dao/control-plane/ideas/chamba/mcp_server:/app" \
  -w /app python:3.11-slim bash -c \
  "pip install -q pytest pytest-asyncio httpx fastapi && python -m pytest tests/test_a2a.py -v"

# Local (con dependencias)
cd mcp_server
pytest tests/test_a2a.py -v
```

## Resultado

```
47 passed
```
