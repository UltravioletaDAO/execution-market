# Execution Market — Facilitator Gasless Analysis Request

**From:** 0xultravioleta (Execution Market)
**To:** Ultravioleta DAO Facilitator Team
**Date:** 2026-02-10
**Priority:** High — blocking production scaling

---

## TL;DR

Execution Market ya funciona 100% gasless en producción usando el Facilitator para liquidar pagos EIP-3009. Necesitamos que el equipo del Facilitador analice:

1. Si el flujo actual escala (1,000+ tasks/día)
2. Si podemos eliminar la hot wallet intermediaria
3. Si vale la pena agregar endpoints gasless para el escrow on-chain
4. Cuál es el modelo de costos de gas a escala

---

## 1. Contexto

Execution Market es un marketplace donde agentes AI publican bounties y humanos los ejecutan. El agente paga con USDC, el worker cobra al completar la tarea.

**Stack de pagos:**
- SDK: `uvd-x402-sdk>=0.11.0` (Python) / `uvd-x402-sdk@2.23.0` (TypeScript)
- Facilitador: `https://facilitator.ultravioletadao.xyz` (v1.29.0+)
- Red principal: Base (chain 8453)
- Redes habilitadas: Base, Ethereum, Polygon, Arbitrum, Celo, Monad, Avalanche, Optimism
- Token principal: USDC. También soportamos USDT, EURC, PYUSD, AUSD
- Agente registrado: ERC-8004 Agent #2106 en Base

**Incidente reciente (Feb 2026):**
Un bug causó pérdida de $1.404 USDC porque los fondos se liquidaron al treasury en vez de la platform wallet. Ya está corregido — cambiamos el modo de pago a `preauth` (no se mueven fondos al crear la tarea). Esto motivó este análisis.

---

## 2. Flujo actual de pagos (preauth — 100% gasless)

Todos los pasos usan EIP-3009 `transferWithAuthorization`, ejecutados por el Facilitador:

### 2.1 Crear tarea (no se mueve dinero)

```
Agente AI                    MCP Server                 Facilitador
    │                            │                          │
    │ Firma EIP-3009 auth        │                          │
    │ (from=agente, to=platform) │                          │
    │ amount = bounty + 13% fee  │                          │
    ├───────────────────────────►│                          │
    │                            │ POST /verify             │
    │                            │ (valida firma, balance)  │
    │                            ├─────────────────────────►│
    │                            │                          │
    │                            │◄─────────────────────────┤
    │                            │ ✅ Firma válida           │
    │                            │                          │
    │                            │ Guarda X-Payment header  │
    │                            │ en base de datos         │
    │                            │                          │
    │◄───────────────────────────┤                          │
    │ Task creada (ID: abc123)   │                          │
    │                            │                          │
    │     ⚡ CERO GAS GASTADO    │                          │
```

### 2.2 Aprobar tarea (3 liquidaciones gasless)

Cuando el agente aprueba el trabajo del worker, se ejecutan 3 transferencias:

```
MCP Server                     Facilitador               Blockchain
    │                              │                         │
    │ PASO A: Cobrar cheque        │                         │
    │ del agente                   │                         │
    │ POST /settle                 │                         │
    │ (auth original del agente)   │                         │
    ├─────────────────────────────►│                         │
    │                              │ transferWithAuth()      │
    │                              │ agente → platform       │
    │                              │ (Facilitador paga gas)  │
    │                              ├────────────────────────►│
    │                              │◄────────────────────────┤
    │◄─────────────────────────────┤ tx: 0xabc...            │
    │                              │                         │
    │ PASO B: Pagar al worker      │                         │
    │ Platform firma nueva auth    │                         │
    │ POST /settle                 │                         │
    │ (platform → worker, 87%)     │                         │
    ├─────────────────────────────►│                         │
    │                              │ transferWithAuth()      │
    │                              │ platform → worker       │
    │                              │ (Facilitador paga gas)  │
    │                              ├────────────────────────►│
    │                              │◄────────────────────────┤
    │◄─────────────────────────────┤ tx: 0xdef...            │
    │                              │                         │
    │ PASO C: Fee al treasury      │                         │
    │ Platform firma nueva auth    │                         │
    │ POST /settle                 │                         │
    │ (platform → treasury, 13%)   │                         │
    ├─────────────────────────────►│                         │
    │                              │ transferWithAuth()      │
    │                              │ platform → treasury     │
    │                              │ (Facilitador paga gas)  │
    │                              ├────────────────────────►│
    │                              │◄────────────────────────┤
    │◄─────────────────────────────┤ tx: 0xghi...            │
    │                              │                         │
    │  ⚡ 3 TX ON-CHAIN            │                         │
    │  ⚡ CERO GAS PARA AGENTE     │                         │
    │  ⚡ CERO GAS PARA PLATFORM   │                         │
    │  ⚡ CERO GAS PARA WORKER     │                         │
```

### 2.3 Cancelar tarea (cero acción)

```
Agente AI                    MCP Server
    │                            │
    │ Cancelar tarea abc123      │
    │                            │
    ├───────────────────────────►│
    │                            │ La auth EIP-3009 nunca
    │                            │ se liquidó → expira sola
    │                            │
    │◄───────────────────────────┤
    │ ✅ Cancelada, sin refund   │
    │ necesario                  │
    │                            │
    │  ⚡ CERO GAS GASTADO       │
```

---

## 3. Wallets involucradas

| Wallet | Dirección | Rol | Control |
|--------|-----------|-----|---------|
| Agent wallet | Varía por agente (ej. `0x13ef...`) | Firma auth inicial. Fondos salen de aquí. | Agente AI |
| **Platform wallet** | `0xD3868E1eD738CED6945A574a7c769433BeD5d474` | **Punto de tránsito.** Recibe del agente, inmediatamente paga a worker + treasury. | MCP Server (WALLET_PRIVATE_KEY en AWS Secrets) |
| Treasury | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` | Solo recibe el 13% fee. Cold wallet Ledger. | 0xultravioleta |
| Worker wallet | Varía por worker | Recibe el 87% del bounty. | Worker humano |

**Problema actual:** La platform wallet es una hot wallet que:
- Retiene fondos ~2 segundos entre el Paso A y los Pasos B+C
- Firma EIP-3009 auths programáticamente con WALLET_PRIVATE_KEY
- Tiene ~$5 USDC por chain para testing
- Si el Paso A exitoso pero Paso B falla → fondos quedan atrapados en platform wallet

---

## 4. Preguntas para el equipo del Facilitador

### Pregunta 1: Viabilidad a escala del flujo actual

El flujo actual funciona. Pero a escala:

- **Costo de gas por tarea**: 3 llamadas a `POST /settle` por tarea aprobada. En Base, cada `transferWithAuthorization` cuesta ~$0.001-0.005. ¿A 1,000 tareas/día (~$3-15/día solo en Base), es sostenible?
- **Costo en otras redes**: Ethereum mainnet es mucho más caro. ¿Cuál es el costo por settle en cada red?
- **Ventana de riesgo**: Los fondos están en la platform wallet ~2 segundos. ¿Hay riesgo de que una transacción falle entre Paso A y B, dejando fondos atrapados?
- **Concurrencia**: Si 50 tareas se aprueban simultáneamente, ¿el Facilitador puede manejar 150 settlements concurrentes? ¿Hay rate limiting?

### Pregunta 2: Eliminar la platform wallet intermediaria

El flujo ideal sería:

```
Agente firma auth directamente al worker (87%) + directamente al treasury (13%)
Sin intermediario. Solo 2 transacciones en vez de 3.
```

**El problema:** El worker es DESCONOCIDO cuando el agente crea la tarea. El agente firma la auth al momento de crear la tarea, pero el worker se asigna después (pueden pasar minutos u horas).

**Opciones a evaluar:**

| Opción | Descripción | Pros | Contras |
|--------|-------------|------|---------|
| **A) Auth al momento de aprobar** | Agente firma nueva auth cuando aprueba (no al crear) | Elimina platform wallet, 2 tx en vez de 3 | Agente debe estar online para aprobar |
| **B) Platform wallet transit** (actual) | Agente → platform → worker + treasury | Agente puede estar offline | 3 tx, hot wallet risk |
| **C) Escrow on-chain gasless** | Fondos se lockean en contrato, se liberan al worker | Máxima seguridad, sin hot wallet | Requiere nuevos endpoints |
| **D) Permit2 / meta-tx** | Agente firma permit, Facilitador ejecuta cuando hay worker | Una sola firma, flexible | Complejidad de implementación |

**Nuestra preferencia:** Opción A es la más limpia si los agentes pueden estar online al aprobar. Si no, Opción C con escrow gasless.

**Pregunta concreta:** ¿El Facilitador puede soportar la Opción A? Es decir: cuando el MCP aprueba una tarea, el agente recibe un callback para firmar 2 auths nuevas (agente→worker + agente→treasury) y el MCP las envía al Facilitador. El agente NO firmaría nada al crear la tarea.

### Pregunta 3: Endpoints gasless para escrow on-chain

Ya tenemos el contrato `AuthCaptureEscrow` desplegado en 9 redes:

| Red | Dirección |
|-----|-----------|
| Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| Ethereum | `0xc1256Bb30bd0cdDa07D8C8Cf67a59105f2EA1b98` |
| Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| Arbitrum, Celo, Monad, Avalanche, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |

El escrow funciona así:

```solidity
// 1. Lockear fondos (al crear tarea)
authorize(receiver, amount, paymentInfo) → USDC va del depositor al contrato

// 2. Liberar al worker (al aprobar tarea)
release(paymentInfo) → USDC va del contrato al receiver

// 3. Refund al agente (al cancelar tarea)
refund(paymentInfo) → USDC vuelve del contrato al depositor
```

**Actualmente:** Estas funciones requieren una transacción on-chain directa. Alguien tiene que pagar gas.

**Lo que necesitamos:** Que el Facilitador ejecute estas funciones en nombre nuestro, pagando el gas.

**Endpoints propuestos:**

```
POST /escrow/authorize
  Body: { escrow_address, token, depositor, receiver, amount, paymentInfo, network }
  Facilitador llama: escrow.authorize(receiver, amount, paymentInfo)
  Facilitador paga gas

POST /escrow/release
  Body: { escrow_address, paymentInfo, network }
  Facilitador llama: escrow.release(paymentInfo)
  Facilitador paga gas

POST /escrow/refund
  Body: { escrow_address, paymentInfo, network }
  Facilitador llama: escrow.refund(paymentInfo)
  Facilitador paga gas
```

**Pregunta concreta:** ¿Es viable que el Facilitador actúe como relayer para estas funciones del escrow? El Facilitador ya paga gas para `transferWithAuthorization` — esto sería extender ese modelo a llamadas de contrato arbitrarias (pero solo al contrato de escrow).

**Consideración de seguridad:** El Facilitador necesitaría ser un "operator" autorizado en el contrato, o el contrato necesitaría un mecanismo de meta-transacciones. ¿Qué approach prefieren?

### Pregunta 4: Modelo de costos de gas

Actualmente el Facilitador subsidia todo el gas. A escala esto no es sostenible.

**Opciones propuestas:**

| Modelo | Descripción | Impacto en UX |
|--------|-------------|---------------|
| **A) % del settlement** | Facilitador cobra 0.1-0.5% de cada settle | Invisible para el usuario |
| **B) Gas sponsorship account** | EM pre-fondea una cuenta de gas en el Facilitador | EM paga por adelantado |
| **C) Incluir gas en auth** | Agente paga bounty + fee + gas recovery | Agente paga ligeramente más |
| **D) Suscripción mensual** | EM paga tarifa fija mensual al Facilitador | Predecible |

**Nuestra preferencia:** Opción A o B. Estamos dispuestos a pagar por el gas.

**Datos para estimar costos:**

| Métrica | Valor estimado |
|---------|----------------|
| Tareas/día (Q1 2026) | 10-50 |
| Tareas/día (Q2 2026) | 100-500 |
| Tareas/día (Q4 2026) | 1,000-5,000 |
| Settlements por tarea | 3 (con platform wallet) o 2 (sin ella) |
| Red principal | Base (gas barato) |
| Redes secundarias | Polygon, Arbitrum (gas bajo), Ethereum (gas alto) |
| Bounty promedio | $0.50 - $5.00 USDC |

---

## 5. Resumen de lo que necesitamos

| # | Item | Urgencia | Descripción |
|---|------|----------|-------------|
| 1 | Confirmación de viabilidad | **Alta** | ¿El flujo actual de 3 settlements/tarea escala en el Facilitador? |
| 2 | Rate limits | **Alta** | ¿Cuántos `POST /settle` concurrentes soporta? |
| 3 | Análisis Opción A vs C | **Media** | ¿Podemos eliminar la platform wallet? ¿Cuál opción recomienda el equipo? |
| 4 | Endpoints escrow gasless | **Media** | ¿Es viable `/escrow/authorize`, `/escrow/release`, `/escrow/refund`? |
| 5 | Modelo de costos | **Media** | ¿Cuál es el costo estimado por settlement en Base, Polygon, Ethereum? |
| 6 | Propuesta de pricing | **Baja** | ¿Cómo quieren cobrar el gas a escala? |

---

## 6. Contratos relevantes

### AuthCaptureEscrow (ya desplegado)

```solidity
interface IAuthCaptureEscrow {
    // Lock funds from depositor into escrow
    function authorize(
        address receiver,
        uint256 amount,
        PaymentInfo calldata paymentInfo
    ) external;

    // Release locked funds to receiver
    function release(
        PaymentInfo calldata paymentInfo
    ) external;

    // Refund locked funds to depositor
    function refund(
        PaymentInfo calldata paymentInfo
    ) external;

    // PaymentInfo struct (hashed for on-chain reference)
    struct PaymentInfo {
        address receiver;
        uint256 amount;
        uint8 tier;         // 0=standard, 1=premium
        uint16 maxFeeBps;   // max fee in basis points (1300 = 13%)
        address feeReceiver;
    }
}
```

### Direcciones de escrow por red

```json
{
  "base":      "0xb9488351E48b23D798f24e8174514F28B741Eb4f",
  "ethereum":  "0xc1256Bb30bd0cdDa07D8C8Cf67a59105f2EA1b98",
  "polygon":   "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
  "arbitrum":  "0x320a3c35F131E5D2Fb36af56345726B298936037",
  "celo":      "0x320a3c35F131E5D2Fb36af56345726B298936037",
  "monad":     "0x320a3c35F131E5D2Fb36af56345726B298936037",
  "avalanche": "0x320a3c35F131E5D2Fb36af56345726B298936037",
  "optimism":  "0x320a3c35F131E5D2Fb36af56345726B298936037"
}
```

### USDC por red (las más usadas)

```json
{
  "base":      "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "ethereum":  "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  "polygon":   "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
  "arbitrum":  "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
  "optimism":  "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"
}
```

---

## 7. Código relevante (para referencia)

| Archivo | Qué hace |
|---------|----------|
| `mcp_server/integrations/x402/sdk_client.py` | Wrapper del SDK, token registry, settlement |
| `mcp_server/integrations/x402/payment_dispatcher.py` | Router preauth vs x402r, orquesta los 3 pasos |
| `mcp_server/integrations/x402/payment_events.py` | Audit trail de pagos |
| `mcp_server/api/routes.py` | REST API, task creation, cancellation |

Todo el código está en: `github.com/ultravioletadao/execution-market`

---

*Documento generado el 2026-02-10. Para preguntas contactar a 0xultravioleta.*
