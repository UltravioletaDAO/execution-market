# Facilitador x402

El **Facilitador x402** es la infraestructura de enrutamiento de pagos que permite pagos con criptomonedas sin gas y entre cadenas para Execution Market.

## Que es el Facilitador?

El facilitador es un servidor operado por Ultravioleta DAO que:

1. **Recibe autorizaciones de pago** de agentes de IA
2. **Enruta pagos** a la red blockchain correcta
3. **Cubre los costos de gas** para que los usuarios no necesiten tokens nativos
4. **Verifica las liquidaciones** y confirma la finalizacion del pago
5. **Soporta EIP-3009** para transferencias USDC sin gas

## Endpoints

| Entorno | URL |
|---------|-----|
| Produccion | `https://facilitator.ultravioletadao.xyz` |
| SDK por defecto | `https://x402.ultravioleta.xyz` |

## Como Fluyen los Pagos a Traves del Facilitador

```
Agente IA                  Facilitador                   Blockchain
   │                            │                            │
   │  1. POST /authorize        │                            │
   │  {amount, token, network}  │                            │
   │ ─────────────────────────► │                            │
   │                            │  2. Crear firma EIP-3009   │
   │                            │ ──────────────────────────►│
   │                            │                            │
   │                            │  3. Enviar transaccion     │
   │                            │ ──────────────────────────►│
   │                            │                            │
   │                            │  4. Confirmar liquidacion  │
   │  5. 200 OK {tx_hash}      │ ◄──────────────────────────│
   │ ◄───────────────────────── │                            │
```

## Integracion con Execution Market

Execution Market usa el facilitador en dos niveles:

### Cliente SDK (Recomendado)

```python
from uvd_x402_sdk import X402Client

client = X402Client(
    facilitator_url="https://facilitator.ultravioletadao.xyz",
    private_key=os.environ["X402_PRIVATE_KEY"],
)

# Autorizar pago
result = await client.authorize(
    amount=10.00,
    token="USDC",
    network="base",
    recipient="0xWorkerAddress...",
)
```

### Cliente HTTP Raw

```python
from execution_market.integrations.x402 import X402Client

client = X402Client(
    rpc_url="https://mainnet.base.org",
    private_key="0x...",
    facilitator_url="https://facilitator.ultravioletadao.xyz",
)

# Crear deposito de escrow
tx = await client.create_deposit(
    amount=10_000_000,  # 10 USDC (6 decimales)
    token="USDC",
    recipient="0xWorker...",
)
```

## Pagos Sin Gas (EIP-3009)

El facilitador implementa EIP-3009 (`transferWithAuthorization`) que permite transferencias de USDC sin que el remitente necesite ETH para gas:

1. El agente firma un mensaje de autorizacion fuera de cadena
2. El facilitador envia la transaccion on-chain
3. El facilitador paga el costo de gas
4. USDC se transfiere directamente del agente al escrow

Esto significa:
- **Los agentes no necesitan ETH/tokens nativos**
- **Los trabajadores no necesitan gas para recibir pagos**
- **Costos de transaccion inferiores a un centavo** en L2s como Base

## Registro de Comerciante

Execution Market se registra como comerciante en el MerchantRouter de x402 para recibir pagos:

```typescript
// Desde scripts/register_x402r_merchant.ts
const merchantRouter = "0xa48E8AdcA504D2f48e5AF6be49039354e922913F"
const depositFactory = "0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814"

// Desplegar proxy deterministico para USDC
const proxy = await factory.deployProxy(USDC_ADDRESS)

// Registrar en el router de comerciante
await router.registerMerchant(emAddress, [proxy])
```

## Soportado por el Facilitador

| Caracteristica | Estado |
|----------------|--------|
| Enrutamiento multi-red | 17+ mainnets |
| EIP-3009 sin gas | USDC, EURC |
| Verificacion de pagos | Tiempo real |
| Confirmacion de liquidacion | < 30 segundos en L2 |
| Multi-token | USDC, EURC, DAI, USDT |
| Integracion escrow | Contratos x402r |
