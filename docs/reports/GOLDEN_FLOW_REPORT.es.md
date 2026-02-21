# Reporte Golden Flow -- Prueba de Aceptacion E2E Definitiva (Fase 5)

> **Fecha**: 2026-02-21 09:14 UTC
> **Entorno**: Produccion (Base Mainnet, chain 8453)
> **API**: `https://api.execution.market`
> **Modelo de fee**: credit_card (fee descontado del bounty on-chain)
> **Modo escrow**: direct_release (escrow en asignacion, 1-TX release)
> **Token**: USDC (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
> **Resultado**: **PARTIAL**

---

## Resumen Ejecutivo

El Golden Flow probo el ciclo de vida completo de Execution Market end-to-end 
en produccion contra Base Mainnet usando el modelo de fee credit card (Fase 5) con **USDC**. 6/7 fases pasaron.

**Resultado General: PARTIAL**

---

## Configuracion de Prueba

| Parametro | Valor |
|-----------|-------|
| Token de pago | USDC |
| Contrato del token | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Bounty (monto bloqueado) | $0.10 USDC |
| Worker neto (87%) | $0.087000 USDC |
| Fee operador (13%) | $0.013000 USDC |
| Costo total para agente | $0.10 USDC |
| Modelo de fee | credit_card |
| Modo escrow | direct_release |
| Wallet del Worker | `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` |
| Treasury | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` |
| API Base | `https://api.execution.market` |
| EM Agent ID | 2106 |

---

## Diagrama de Flujo

```mermaid
sequenceDiagram
    participant Agente
    participant API
    participant Facilitator
    participant Escrow
    participant Worker
    participant ERC8004

    Note over Agente,ERC8004: Fase 1: Salud
    Agente->>API: GET /health
    Agente->>API: GET /config
    Agente->>API: GET /reputation/info

    Note over Agente,ERC8004: Fase 2: Creacion de Tarea (solo balance check)
    Agente->>API: POST /tasks (bounty=$0.10)
    API->>API: balanceOf(agente) -- verificacion advisory
    Note right of API: Sin escrow aun (diferido a asignacion)

    Note over Agente,ERC8004: Fase 3: Identidad del Worker
    Worker->>API: POST /executors/register
    Worker->>API: POST /reputation/register
    API->>Facilitator: Registro gasless
    Facilitator->>ERC8004: Mint NFT de identidad

    Note over Agente,ERC8004: Fase 4: Aplicar + Asignar (escrow) + Enviar
    Worker->>API: POST /tasks/{id}/apply
    Agente->>API: POST /tasks/{id}/assign
    API->>Facilitator: Bloquear $0.10 en escrow (receiver=worker)
    Facilitator->>Escrow: TX1: Bloquear $0.10
    Worker->>API: POST /tasks/{id}/submit (evidencia)

    Note over Agente,ERC8004: Fase 5: Aprobacion + Pago (1 TX)
    Agente->>API: POST /submissions/{id}/approve
    API->>Facilitator: Liberar escrow
    Facilitator->>Escrow: TX2: Release (fee calc divide)
    Escrow->>Worker: $0.087000 (87%)
    Escrow->>Operator: $0.013000 (13%)

    Note over Agente,ERC8004: Fase 6: Reputacion
    Agente->>API: Calificar worker (score: 90)
    API->>Facilitator: POST /feedback
    Worker->>API: Calificar agente (score: 85)
    API->>Facilitator: POST /feedback

    Note over Agente,ERC8004: Fase 7: Verificacion
    Agente->>API: GET /reputation/em
    Agente->>API: GET /reputation/feedback/{task_id}
```

---

## Resultados por Fase

| # | Fase | Estado | Tiempo |
|---|------|--------|--------|
| 1 | Salud y Configuracion | **APROBADO** | 0.5s |
| 2 | Creacion de Tarea (Balance Check) | **APROBADO** | 1.51s |
| 3 | Registro de Worker e Identidad | **APROBADO** | 14.01s |
| 4 | Ciclo de Vida (Aplicar -> Asignar+Escrow -> Enviar) | **APROBADO** | 13.11s |
| 5 | Aprobacion y Pago (1 TX, Credit Card) | **APROBADO** | 26.08s |
| 6 | Reputacion Bidireccional | **PARCIAL** | 1.51s |
| 7 | Verificacion Final | **APROBADO** | 0.25s |

---

## Salud y Configuracion

- **Estado**: APROBADO
- **Tiempo**: 0.5s

## Creacion de Tarea (Balance Check)

- **Estado**: APROBADO
- **Tiempo**: 1.51s
- **Task ID**: `2a78dfa3-f190-406c-8376-132b560ab449`
- **Escrow en creacion**: False
- **Modelo de fee**: credit_card

## Registro de Worker e Identidad

- **Estado**: APROBADO
- **Tiempo**: 14.01s
- **Executor ID**: `803dfbf1-7b91-4a41-8d31-518f4fa2fcd4`
- **ERC-8004 Agent ID**: 18644

## Ciclo de Vida (Aplicar -> Asignar+Escrow -> Enviar)

- **Estado**: APROBADO
- **Tiempo**: 13.11s
- **Submission ID**: `80f66105-3dfa-4d45-9b10-4e0f34c01997`
- **TX Escrow (en asignacion)**: [`0xd48cb139bb4328...`](https://basescan.org/tx/0xd48cb139bb43282b00908cac7ca58a43ec6f21ad68877a89aeefd42be5916d0b)
- **Escrow verificado**: True
- **Modo escrow**: direct_release

## Aprobacion y Pago (1 TX, Credit Card)

- **Estado**: APROBADO
- **Tiempo**: 26.08s
- **Modo de pago**: `unknown`
- **TX Worker**: [`0x1decddb3d26043...`](https://basescan.org/tx/0x1decddb3d2604327290723cf940e8c4447e9510d41a3f69ad9276618da51704d)
- **TX Fee**: [`0xa58c717ab94950...`](https://basescan.org/tx/0xa58c717ab94950786c9c42ce1df6f4e0396130ca8bfa80aa840b3277b214b473)

## Reputacion Bidireccional

- **Estado**: PARCIAL
- **Tiempo**: 1.51s
- **Error**: Worker->Agent: HTTP 200, success=False, error=EM_WORKER_PRIVATE_KEY not set — worker cannot sign on-chain TX
- **TX Agente->Worker**: [`8e1d50d8d685d503...`](https://basescan.org/tx/8e1d50d8d685d503ce28ec60e4ebc176bd5fce1ab50267a42d48260b25839685)

## Verificacion Final

- **Estado**: APROBADO
- **Tiempo**: 0.25s

---

## Resumen de Transacciones On-Chain

| # | TX Hash | BaseScan |
|---|---------|----------|
| 1 | `0xeb86981298d733dd40...` | [Ver](https://basescan.org/tx/0xeb86981298d733dd40f1f113692f422cb1aa04f3aa8223670804eb4c1d9d71fd) |
| 2 | `0xd48cb139bb43282b00...` | [Ver](https://basescan.org/tx/0xd48cb139bb43282b00908cac7ca58a43ec6f21ad68877a89aeefd42be5916d0b) |
| 3 | `0x1decddb3d260432729...` | [Ver](https://basescan.org/tx/0x1decddb3d2604327290723cf940e8c4447e9510d41a3f69ad9276618da51704d) |
| 4 | `0xa58c717ab94950786c...` | [Ver](https://basescan.org/tx/0xa58c717ab94950786c9c42ce1df6f4e0396130ca8bfa80aa840b3277b214b473) |
| 5 | `8e1d50d8d685d503ce28...` | [Ver](https://basescan.org/tx/8e1d50d8d685d503ce28ec60e4ebc176bd5fce1ab50267a42d48260b25839685) |

---

## Invariantes Verificados

- [x] API saludable y retornando configuracion correcta
- [x] Tarea creada exitosamente con status published (solo balance check)
- [x] Escrow bloqueado en asignacion (direct_release, worker como receiver)
- [x] TX de escrow verificada on-chain (status: SUCCESS)
- [x] Worker registrado con executor ID
- [x] Operador recibe $0.013000 (13% fee calculator on-chain)
- [x] Todas las TXs de pago verificadas on-chain (status: 0x1)
- [x] Release de escrow en 1 TX (fee split por StaticFeeCalculator 1300bps)
