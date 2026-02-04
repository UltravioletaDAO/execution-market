# Escrow x402r

El sistema de escrow x402r es la infraestructura de pagos en produccion utilizada por Execution Market en Base. Es parte del ecosistema mas amplio del protocolo x402 mantenido por Ultravioleta DAO.

## Arquitectura

```
Agente (pagador)
    │
    ▼
MerchantRouter ──► DepositRelayFactory ──► Escrow Contract
    │                    │                      │
    │                    ▼                      │
    │              Relay Proxy                  │
    │              (por token)                  │
    │                    │                      │
    └────────────────────┴──────────────────────┘
                         │
                         ▼
                    Token USDC
                    (ERC-20)
```

## Como Funciona

### 1. Registro de Comerciante

Execution Market se registra como comerciante en el MerchantRouter:

```typescript
const merchantRouter = new Contract("0xa48E8...", abi, signer)
const factory = new Contract("0x41Cc4...", abi, signer)

// Deploy deterministic relay proxy for USDC
const proxy = await factory.deployProxy(USDC_ADDRESS)

// Register as merchant
await merchantRouter.registerMerchant(emAddress, [proxy])
```

### 2. Autorizacion de Pago

Cuando un agente publica una tarea, se autoriza y bloquea USDC:

```python
from integrations.x402 import X402rEscrow

escrow = X402rEscrow(
    network="base",
    private_key=os.environ["X402R_PRIVATE_KEY"],
)

# Create escrow deposit
result = await escrow.create_deposit(
    task_id="task_abc123",
    amount=10_000_000,  # 10 USDC
    beneficiary="0xWorkerAddress",
    timeout_duration=86400,  # 24 hours
)
```

### 3. Liberacion de Pago

Al aprobar la tarea, los fondos se liberan al trabajador:

```python
# Release to beneficiary
await escrow.release(
    task_id="task_abc123",
    amount=9_200_000,  # 9.20 USDC (neto despues de 8% de comision)
)
```

### 4. Reembolso

Si la tarea se cancela (despues del periodo de bloqueo de 24h):

```python
await escrow.refund(task_id="task_abc123")
```

## Estados del Deposito

```python
class DepositState(IntEnum):
    NON_EXISTENT = 0  # No creado
    IN_ESCROW = 1     # Fondos bloqueados
    RELEASED = 2      # Pagado al trabajador
    REFUNDED = 3      # Devuelto al agente
```

## Direcciones de Contratos

### Base Mainnet

| Contrato | Direccion |
|----------|-----------|
| Escrow | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| Factory | `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` |
| MerchantRouter | `0xa48E8AdcA504D2f48e5AF6be49039354e922913F` |

### Base Sepolia

| Contrato | Direccion |
|----------|-----------|
| Escrow | `0xF7F2Bc463d79Bd3E5Cb693944B422c39114De058` |
| Factory | `0xf981D813842eE78d18ef8ac825eef8e2C8A8BaC2` |

## Configuracion

```bash
# Network selection
X402R_NETWORK=base          # or base-sepolia for testing

# Credentials
X402R_PRIVATE_KEY=0x...
X402R_MERCHANT_ADDRESS=0x...
X402R_PROXY_ADDRESS=0x...
```
