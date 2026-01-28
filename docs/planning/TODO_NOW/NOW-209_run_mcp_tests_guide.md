# NOW-209: Guía para Correr Tests de MCP

## Metadata
- **Prioridad**: P1
- **Fase**: Testing
- **Dependencias**: Ninguna (documentación)
- **Tiempo estimado**: 15 minutos

## Descripción
Documentar cómo correr los tests del MCP server para que el usuario pueda verificar la funcionalidad.

## Comandos para Correr Tests

### 1. Setup inicial
```bash
cd Z:\ultravioleta\dao\control-plane\ideas\chamba\mcp_server

# Crear virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
```

### 2. Correr todos los tests
```bash
# Desde el directorio mcp_server
pytest tests/ -v

# Con output detallado
pytest tests/ -v --tb=short

# Solo un archivo específico
pytest tests/test_a2a.py -v
```

### 3. Tests específicos

```bash
# Tests de A2A (Agent Card, protocol compliance)
pytest tests/test_a2a.py -v
# Resultado esperado: 99 tests passed

# Tests de GPS
pytest tests/test_gps.py -v

# Tests de Timestamp
pytest tests/test_timestamp.py -v

# Tests de Reputación
pytest tests/test_reputation.py -v

# Tests de WebSocket
pytest tests/test_websocket.py -v

# Tests de Fraud Detection
pytest tests/test_fraud_detection.py -v
```

### 4. Tests con coverage
```bash
pytest tests/ --cov=. --cov-report=html
# Abre htmlcov/index.html para ver reporte
```

### 5. Tests de integración (requieren servicios)
```bash
# Estos requieren Supabase corriendo
pytest tests/ -m integration

# Estos requieren facilitador x402
pytest tests/ -m x402
```

## Qué Esperar al Correr Tests

### Tests que deben pasar (sin servicios externos)
- `test_a2a.py` - 99 tests
- `test_gps.py` - ~10 tests
- `test_timestamp.py` - ~10 tests
- `test_reputation.py` - ~15 tests
- `test_fraud_detection.py` - ~20 tests

### Tests que pueden fallar (requieren config)
- `test_escrow.py` - Requiere mock de x402
- `test_mcp_tools.py` - Requiere FastMCP configurado
- `test_websocket_module.py` - Puede requerir ajustes

## Verificar que Tests Pasan

```bash
# Comando completo para verificar MVP
cd Z:\ultravioleta\dao\control-plane\ideas\chamba\mcp_server
pytest tests/test_a2a.py tests/test_gps.py tests/test_timestamp.py tests/test_reputation.py -v

# Resultado esperado:
# ==================== 134 passed in X.XXs ====================
```

## Troubleshooting

### Error: ModuleNotFoundError
```bash
# Asegurarse de estar en el directorio correcto
cd Z:\ultravioleta\dao\control-plane\ideas\chamba\mcp_server

# Instalar en modo editable
pip install -e .
```

### Error: Import error con FastMCP
```bash
# Instalar FastMCP
pip install fastmcp
```

### Error: Supabase not configured
```bash
# Para tests que requieren Supabase, crear .env.test
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=test-key
```

## Criterios de Éxito
- [x] `pytest tests/test_a2a.py -v` pasa 99 tests
- [x] No hay errores de import
- [ ] Coverage > 70%

## COMPLETADO: 2026-01-25

### Tests Existentes (20 archivos)
```
tests/
├── __init__.py
├── conftest.py               # Fixtures compartidos
├── test_a2a.py               # 99 tests - Agent Card, A2A protocol
├── test_consensus.py         # Validator consensus
├── test_escrow.py            # Escrow x402
├── test_fees.py              # Fee calculation
├── test_fraud_detection.py   # Fraud detection module
├── test_gps.py               # GPS validation
├── test_gps_antispoofing.py  # GPS anti-spoofing
├── test_mcp_tools.py         # MCP tools
├── test_protection_fund.py   # Worker protection fund
├── test_recon.py             # Recon task type
├── test_reputation.py        # Reputation system
├── test_safety.py            # Safety module
├── test_seals.py             # Seals & credentials
├── test_timestamp.py         # Timestamp validation
├── test_webhooks.py          # Webhook payloads
├── test_websocket.py         # WebSocket endpoints
├── test_websocket_module.py  # WebSocket module
└── test_workers.py           # Worker management
```

### Comando Rápido para MVP
```bash
cd Z:\ultravioleta\dao\control-plane\ideas\chamba\mcp_server

# Instalar dependencias
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx

# Correr tests principales (sin servicios externos)
pytest tests/test_a2a.py tests/test_gps.py tests/test_reputation.py -v

# Output esperado: ~120+ tests passed
```

### Notas Importantes
1. **test_a2a.py** es el más completo (99 tests de A2A protocol compliance)
2. Los tests de escrow/x402 pueden fallar sin facilitador real
3. Los tests de WebSocket requieren pytest-asyncio
4. Para coverage completo, instalar `pytest-cov`
