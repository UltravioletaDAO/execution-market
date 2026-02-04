# Integracion de Pagos x402

Execution Market usa el **protocolo x402** (HTTP 402 Payment Required) para todos los pagos. x402 permite pagos instantaneos con criptomonedas sin gas a traves de una red de facilitadores.

## Capas de Integracion

Execution Market implementa x402 a traves de multiples capas de integracion, cada una proporcionando diferentes niveles de abstraccion:

### Capa 1: Cliente X402 Raw (`client.py`)
Interaccion directa con contratos x402 via web3. Maneja la creacion y verificacion de pagos multi-token y multi-red.

### Capa 2: Gestor de Escrow (`escrow.py`)
Integracion del ciclo de vida de tareas con liberaciones parciales, calculo de comisiones y seguimiento de estado.

### Capa 3: Integracion SDK (`sdk_client.py`)
Usa el SDK oficial `uvd-x402-sdk` (v0.3.0+) para pagos gasless via EIP-3009 a traves del facilitador.

### Capa 4: Escrow Avanzado / PaymentOperator (`advanced_escrow_integration.py`)
Motor de estrategia de pagos con 5 modos que recomienda el flujo optimo segun las caracteristicas de la tarea.

### Capa 5: x402r Directo (`x402r_escrow.py`)
Interaccion directa de grado produccion con contratos escrow x402r en Base.

## Como Funciona

```
1. El agente publica la tarea con el monto de la recompensa
   └─→ Se crea el escrow x402, USDC bloqueado

2. El trabajador completa la tarea y envia evidencia
   └─→ Liberacion parcial del 30% (prueba de trabajo)

3. El agente aprueba el envio
   └─→ El 70% restante se libera al trabajador
   └─→ Se cobra la comision de plataforma del 8%

4. (Si hay disputa)
   └─→ Fondos bloqueados durante el arbitraje
   └─→ El arbitro distribuye segun el veredicto
```

## Facilitador

Todos los pagos x402 se enrutan a traves del **Facilitador de Ultravioleta DAO**:

| Entorno | URL |
|---------|-----|
| Produccion | `https://facilitator.ultravioletadao.xyz` |
| SDK por defecto | `https://x402.ultravioleta.xyz` |

El facilitador se encarga de:
- Autorizacion de pagos sin gas (EIP-3009)
- Enrutamiento multi-red
- Verificacion de pagos
- Confirmacion de liquidacion

## Configuracion

```bash
# Variables de entorno
X402_FACILITATOR_URL=https://facilitator.ultravioletadao.xyz
X402_RPC_URL=https://mainnet.base.org
X402_PRIVATE_KEY=0x...
X402_NETWORK=base
X402R_NETWORK=base-sepolia
EM_PLATFORM_FEE_BPS=800
EM_TREASURY_ADDRESS=0x...
```

## Dependencias

```
uvd-x402-sdk[fastapi]>=0.3.0
web3>=6.15.0
eth-account>=0.11.0
httpx>=0.26.0
```
