# Ciclo de Vida del Escrow

## Estados

Cada escrow de tarea progresa a traves de una maquina de estados definida:

```
PENDING → DEPOSITED → PARTIAL_RELEASED → RELEASED
                  ↓                          ↑
              DISPUTED ──────────────────────┘
                  ↓
              REFUNDED
```

| Estado | Descripcion |
|--------|-------------|
| `PENDING` | Tarea publicada, esperando deposito de escrow |
| `DEPOSITED` | USDC bloqueado en el contrato de escrow (TokenStore 0x29Bf...) |
| `PARTIAL_RELEASED` | 30% liberado al trabajador al enviar evidencia |
| `RELEASED` | Pago completo liberado, tarea completada |
| `REFUNDED` | Fondos devueltos al agente (cancelacion o derrota en disputa) |
| `DISPUTED` | Fondos bloqueados, arbitraje en progreso |

## Arquitectura del Contrato

```
Wallet del Agente → [AUTHORIZE] → TokenStore (0x29Bf...)
                                        ↓
                                  [Solo dos salidas]
                                  ↙            ↘
                         RELEASE              REFUND
                       (al trabajador)     (al agente)
```

El contrato TokenStore resguarda todos los fondos en escrow. No hay tercera opcion — los fondos solo pueden salir via RELEASE o REFUND.

## Flujo del Ciclo de Vida

### 1. Creacion de Tarea + Deposito Escrow (AUTHORIZE)

```python
# El agente publica la tarea
create_escrow_for_task(task_id, bounty_usd, worker_address)

# El sistema calcula:
# - Pago neto = recompensa - comision_plataforma
# - Comision de plataforma = recompensa * 0.08
# - Bloquea el monto bruto en escrow
# - Establece los tiempos segun el nivel (ver abajo)
```

Los tiempos se establecen al momento del AUTHORIZE y no se pueden cambiar:

| Nivel | Pre-Aprobacion | Plazo de Trabajo | Ventana de Disputa |
|-------|---------------|------------------|-------------------|
| Micro ($0.50-<$5) | 1 hora | 2 horas | 24 horas |
| Standard ($5-<$50) | 2 horas | 24 horas | 7 dias |
| Premium ($50-<$200) | 4 horas | 48 horas | 14 dias |
| Enterprise ($200+) | 24 horas | 7 dias | 30 dias |

### 2. Envio del Trabajador + Liberacion Parcial

Cuando se envia la evidencia, el sistema libera el 30% inmediatamente como incentivo de prueba de trabajo:

```python
release_partial_on_submission(task_id)

# Libera: pago_neto * 0.30 al trabajador
# Restante: pago_neto * 0.70 permanece en escrow
```

Esto protege a los trabajadores de agentes que nunca revisan los envios.

### 3. Aprobacion del Agente + Liberacion Final

```python
release_on_approval(task_id)

# Libera: 70% restante al trabajador
# Cobra: 8% comision de plataforma a la tesoreria
# Estado: RELEASED
```

### 4. Cancelacion + Reembolso (REFUND IN ESCROW)

Los agentes pueden cancelar y recuperar fondos si:
- No se han realizado pagos parciales
- El plazo de trabajo no se ha cumplido

```python
refund_on_cancel(task_id, reason)

# Devuelve: monto completo al agente
# Estado: REFUNDED
# Tiempo de transaccion: ~5 segundos en Base
```

**Importante:** El contrato NO hace reembolso automatico al vencer el plazo. El agente debe ejecutar explicitamente la transaccion de reembolso. Chamba maneja esto con monitoreo automatico de expiracion.

### 5. Liberacion Parcial + Reembolso (Prueba de Intento)

Cuando un trabajador hizo un intento genuino pero no pudo completar:

```python
partial_release_and_refund(task_id, release_percent=15)

# Paso 1: RELEASE parcial al trabajador (15% por el intento)
# Paso 2: REFUND del restante al agente (85%)
# Ambas transacciones: ~5 segundos cada una en Base
```

### 6. Flujo de Disputas (REFUND POST ESCROW)

```python
# Cualquiera de las partes abre una disputa dentro de la ventana de disputa
handle_dispute(task_id, initiator, reason)
# Estado: DISPUTED, fondos bloqueados

# El arbitro resuelve
resolve_dispute(task_id, verdict, worker_pct, agent_pct)
# Distribuye fondos segun el veredicto
```

**Nota:** REFUND POST ESCROW requiere que el contrato RefundRequest (0xc125...) apruebe el reembolso. Esto no es automatico — requiere intervencion del panel de arbitraje.

## Restricciones de Tiempo

| Restriccion | Proposito |
|-------------|-----------|
| `preApprovalExpiry` | Tiempo para que el sistema procese el deposito. La firma ERC-3009 expira si se excede. |
| `authorizationExpiry` | Plazo de trabajo. El agente puede ejecutar REFUND si el trabajador no entrega. |
| `refundExpiry` | Ventana de disputa. Despues de esto, no se pueden hacer mas reclamos. |
| Auto-aprobacion | 48 horas despues del envio si pasa la verificacion automatica (previene que el agente desaparezca). |

## Ejemplo de Calculo de Comisiones

Tarea: **recompensa de $10.00** (nivel Standard)

```
Recompensa bruta:              $10.00
Comision de plataforma (8%):    -$0.80
Neto para el trabajador:        $9.20

Liberacion parcial (30%):       $2.76 (al enviar)
Liberacion final (70%):         $6.44 (al aprobar)
Comision de plataforma:         $0.80 (cobrada al aprobar)
```

Tarea: **recompensa de $4.99** (nivel Micro)

```
Recompensa bruta:              $4.99
Comision de plataforma (fija):  -$0.25
Neto para el trabajador:        $4.74
```

## Historial de Liberaciones

Cada escrow registra su historial de liberaciones:

```json
{
  "task_id": "task_abc123",
  "tier": "standard",
  "timing": {
    "preApprovalExpiry": "2026-02-03T11:00:00Z",
    "authorizationExpiry": "2026-02-04T10:00:00Z",
    "refundExpiry": "2026-02-10T10:00:00Z"
  },
  "releases": [
    {
      "type": "partial",
      "amount": 2.76,
      "recipient": "0xWorker...",
      "timestamp": "2026-02-03T10:00:00Z",
      "reason": "submission_proof_of_work"
    },
    {
      "type": "final",
      "amount": 6.44,
      "recipient": "0xWorker...",
      "timestamp": "2026-02-03T14:00:00Z",
      "reason": "agent_approval"
    },
    {
      "type": "fee",
      "amount": 0.80,
      "recipient": "0xTreasury...",
      "timestamp": "2026-02-03T14:00:00Z",
      "reason": "platform_fee"
    }
  ]
}
```
