# NOW-202: Reemplazar mock x402 con SDK real (uvd-x402-sdk)

## Metadata
- **Prioridad**: P0 (CRÍTICO)
- **Fase**: Production Integration
- **Dependencias**: Ninguna
- **Archivos a modificar**: `mcp_server/integrations/x402/`
- **Tiempo estimado**: 2-3 horas

## Descripción
El código actual de integración x402 es mock/placeholder. Debe reemplazarse con el SDK oficial `uvd-x402-sdk` que ya soporta FastAPI, 18 redes, y 5 stablecoins.

## Contexto Técnico
- **SDK**: `uvd-x402-sdk` (pip install uvd-x402-sdk[fastapi])
- **Facilitador**: https://facilitator.ultravioletadao.xyz
- **Redes objetivo**: Ethereum Mainnet (para ERC-8004), Avalanche (para tests rápidos)
- **Documentación**: Z:\ultravioleta\dao\uvd-x402-sdk-python\README.md

## Código de Referencia

### Instalación
```bash
pip install uvd-x402-sdk[fastapi]
```

### Integración FastAPI
```python
from decimal import Decimal
from fastapi import FastAPI, Depends
from uvd_x402_sdk.config import X402Config
from uvd_x402_sdk.models import PaymentResult
from uvd_x402_sdk.integrations import FastAPIX402

app = FastAPI()

# Configurar con wallet de Execution Market
x402 = FastAPIX402(
    app,
    recipient_address="0xChambaEscrowWallet...",  # Wallet que recibe pagos
)

@app.post("/api/tasks/{task_id}/fund")
async def fund_task(
    task_id: str,
    payment: PaymentResult = Depends(x402.require_payment(amount_usd="10.00"))
):
    """Agente fondea una tarea via x402"""
    return {
        "task_id": task_id,
        "funded": True,
        "payer": payment.payer_address,
        "network": payment.network,
        "tx_hash": payment.transaction_hash,
    }
```

### Escrow con x402r (Trustless Refunds)
```python
# x402r extension permite refunds trustless
# Ver: https://github.com/coinbase/x402/issues/864
# Contracts en Base: Factory 0x41Cc...A814, Escrow 0xC409...f6bC
```

## Archivos a Modificar

```
mcp_server/integrations/x402/
├── __init__.py          # Re-exportar desde uvd-x402-sdk
├── escrow.py            # ELIMINAR código mock, usar SDK
├── client.py            # ELIMINAR código mock, usar SDK
└── em_x402.py       # NUEVO: Wrapper específico para Execution Market
```

### em_x402.py (NUEVO)
```python
"""
Execution Market x402 Integration
Wrapper sobre uvd-x402-sdk con lógica específica de Execution Market
"""
import os
from decimal import Decimal
from uvd_x402_sdk import X402Client, X402Config
from uvd_x402_sdk.integrations import FastAPIX402

# Configuración Execution Market
EXECUTION MARKET_ESCROW_WALLET = os.environ.get("EXECUTION MARKET_ESCROW_WALLET")
EXECUTION MARKET_FEE_PERCENTAGE = Decimal("0.08")  # 8% platform fee

config = X402Config(
    recipient_evm=EXECUTION MARKET_ESCROW_WALLET,
    supported_networks=["ethereum", "avalanche", "base"],
)

client = X402Client(config=config)

async def receive_task_funding(x_payment_header: str, bounty_usd: Decimal) -> dict:
    """
    Recibir fondos de un agente para una tarea.
    El agente paga bounty + platform fee.
    """
    total = bounty_usd * (1 + EXECUTION MARKET_FEE_PERCENTAGE)
    result = client.process_payment(x_payment_header, total)

    return {
        "payer": result.payer_address,
        "network": result.network,
        "tx_hash": result.transaction_hash,
        "amount_received": str(total),
        "bounty": str(bounty_usd),
        "platform_fee": str(bounty_usd * EXECUTION MARKET_FEE_PERCENTAGE),
    }

async def release_to_worker(worker_address: str, amount_usd: Decimal) -> dict:
    """
    Liberar fondos al worker después de aprobación.
    Requiere que Execution Market tenga fondos y private key para enviar.
    """
    # Para MVP: Transfer directo desde escrow wallet
    # Para producción: Usar contrato ChambaEscrow.sol
    pass
```

## Variables de Entorno Requeridas
```bash
# Wallet que recibe pagos de agentes
EXECUTION MARKET_ESCROW_WALLET=0x...

# Para enviar pagos a workers (opcional, puede ser manual inicialmente)
EXECUTION MARKET_PRIVATE_KEY=...

# RPC URLs
RPC_URL_ETHEREUM=https://eth-mainnet.g.alchemy.com/v2/...
RPC_URL_AVALANCHE=https://api.avax.network/ext/bc/C/rpc
```

## Criterios de Éxito
- [x] `uvd-x402-sdk[fastapi]` instalado en requirements.txt
- [x] SDK wrapper creado (`integrations/x402/sdk_client.py`)
- [x] FastAPI x402 integración habilitada en `api.py`
- [x] Health check incluye status del SDK x402
- [x] Endpoints de diagnóstico: `/api/v1/x402/info`, `/api/v1/x402/networks`
- [x] Endpoint raíz incluye información de pagos
- [ ] Pagos llegan a wallet de escrow (requiere EXECUTION MARKET_TREASURY_ADDRESS)
- [ ] Tests pasan con facilitador real (testnet primero)

## COMPLETADO: 2026-01-25

### Archivos Creados/Modificados
```
mcp_server/
├── requirements.txt                     # + uvd-x402-sdk[fastapi]>=0.3.0
├── api.py                               # + x402 SDK initialization + endpoints
└── integrations/x402/
    ├── __init__.py                      # + exports for SDK wrapper
    └── sdk_client.py                    # NUEVO: Execution MarketX402SDK wrapper
```

### Endpoints Agregados
- `GET /api/v1/x402/info` - Estado del SDK y health del facilitador
- `GET /api/v1/x402/networks` - Redes soportadas (19 mainnets, 7 testnets)

### Variables de Entorno
```bash
# Requeridas para producción
EXECUTION MARKET_TREASURY_ADDRESS=0x...  # Wallet que recibe pagos
X402_NETWORK=base              # Red por defecto (o avalanche para tests)
```

## Test Cases
```python
# Test con Avalanche Fuji (testnet)
# 1. Obtener USDC de faucet: https://faucet.avax.network
# 2. Hacer pago x402 al endpoint
# 3. Verificar tx en snowtrace.io
```

## Notas
- El SDK ya tiene TODAS las direcciones del facilitador embebidas
- NO necesitas configurar nada del facilitador manualmente
- Usa Avalanche Fuji para tests (más rápido que Ethereum)
