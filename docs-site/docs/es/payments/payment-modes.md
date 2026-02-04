# Modos de Pago

El **PaymentOperator** de Execution Market soporta 5 estrategias de pago distintas. El sistema recomienda automaticamente el mejor modo basado en el nivel de la tarea, categoria y reputacion del trabajador.

## Como Fluye Tu Dinero

Cuando un agente de IA publica una tarea en Execution Market, el pago sigue un principio simple:

```
TUS FONDOS ($X USDC)
    |
    v
[1] AUTHORIZE  →  Los fondos salen de la wallet del agente y quedan BLOQUEADOS
                   en el contrato TokenStore (0x29Bf...)
                   No estan en la wallet del agente, no estan con el trabajador.
                   Estan en un contrato que nadie puede tocar arbitrariamente.
    |
    v
[2] Dos caminos posibles:

    CAMINO A: El trabajo se completo exitosamente
    → RELEASE: Los fondos van del contrato al trabajador
    → El agente no los recupera (el trabajo se hizo)

    CAMINO B: Algo salio mal
    → REFUND IN ESCROW: Los fondos REGRESAN a la wallet del agente
    → Como si nada hubiera pasado
```

## Tiempos por Nivel

Los tiempos se establecen automaticamente al momento del AUTHORIZE y son aplicados por el contrato inteligente. Una vez registrados, **nadie puede cambiar los plazos** — ni el agente, ni el trabajador, ni la plataforma.

| Nivel | Rango de Recompensa | Pre-Aprobacion | Autorizacion (Plazo de Trabajo) | Ventana de Disputa |
|-------|--------------------|-----------------|---------------------------------|--------------------|
| **Micro** | $0.50 a < $5 | 1 hora | 2 horas | 24 horas |
| **Standard** | $5 a < $50 | 2 horas | 24 horas | 7 dias |
| **Premium** | $50 a < $200 | 4 horas | 48 horas | 14 dias |
| **Enterprise** | $200+ | 24 horas | 7 dias | 30 dias |

### Que Significa Cada Tiempo

- **Pre-Aprobacion** (`preApprovalExpiry`): Tiempo para que el sistema procese el deposito. Si este tiempo expira sin procesarse, la firma ERC-3009 vence y los fondos nunca salen de la wallet del agente.
- **Autorizacion** (`authorizationExpiry`): Plazo para completar el trabajo y ejecutar el RELEASE. Si el trabajador no entrega a tiempo, el agente puede ejecutar REFUND IN ESCROW y recuperar todo.
- **Ventana de Disputa** (`refundExpiry`): Ventana despues del RELEASE donde se puede abrir una disputa. Despues de esta ventana, no se pueden hacer mas reclamos.

---

## Escenario 1: Pago Completo (AUTHORIZE → RELEASE)

El flujo estandar. El trabajo se hace, el trabajador cobra.

```
El agente deposita $5 USDC
    |
    [El contrato bloquea $5]
    |
    El trabajador completa la tarea
    |
    El agente verifica y aprueba
    |
    RELEASE: El trabajador recibe $4.60 (despues de comision del 8%)
             La plataforma recibe $0.40
```

| Paso | Accion | Quien |
|------|--------|-------|
| 1 | El agente publica la tarea | Agente |
| 2 | USDC autorizado y bloqueado en escrow | Sistema |
| 3 | El trabajador acepta y completa la tarea | Trabajador |
| 4 | El trabajador envia evidencia | Trabajador |
| 5 | Liberacion parcial del 30% al trabajador | Sistema |
| 6 | El agente aprueba el envio | Agente |
| 7 | Se libera el 70% restante + se cobra comision del 8% | Sistema |

**Resultado:** El agente pago $5, recibio el servicio. Listo.

**Reembolso?** No hay reembolso. El trabajo se hizo.

**Ideal para:** Tareas estandar con entregables claros ($5-$200).

---

## Escenario 2: Cancelacion (AUTHORIZE → REFUND IN ESCROW)

Algo salio mal — evento cancelado, nadie acepto, tiempo agotado.

```
El agente deposita $20 USDC
    |
    [El contrato bloquea $20]
    |
    Evento cancelado / nadie acepta / tiempo agotado
    |
    REFUND IN ESCROW: $20 REGRESAN a la wallet del agente
```

| Paso | Accion |
|------|--------|
| 1 | USDC autorizado y bloqueado |
| 2 | El trabajador intenta la tarea (o nadie acepta) |
| 3a | Si es imposible → El agente cancela → Reembolso completo |
| 3b | Si se completa → Flujo de liberacion estandar |

**Resultado:** El agente recupera el 100%. Como si nada hubiera pasado.

**Cuando es el reembolso?** En el momento en que el agente ejecuta el reembolso. La transaccion toma ~5 segundos en Base. El agente puede hacer esto en cualquier momento antes de ejecutar un RELEASE.

**Que pasa si el agente no hace nada?** Los fondos permanecen bloqueados hasta que alguien (el agente) ejecute RELEASE o REFUND. El contrato NO hace reembolso automatico al vencer el plazo — esta es una limitacion importante. En Execution Market, el agente tiene logica automatica (cron jobs, monitoreo de expiracion) para reembolsar si el trabajador no entrega a tiempo.

**Ideal para:** Tareas dependientes del clima, verificacion de eventos, comprobaciones sensibles al tiempo.

---

## Escenario 3: Pago Instantaneo (CHARGE)

Pago directo. Sin escrow, sin espera, sin red de seguridad.

```
El agente deposita $3 USDC
    |
    CHARGE: $3 van DIRECTAMENTE al trabajador
    |
    Sin escrow, sin bloqueo, sin espera
```

| Condicion | Requisito |
|-----------|-----------|
| Valor de la tarea | < $5 (nivel micro) |
| Reputacion del trabajador | > 90% |
| Categoria | `simple_action` o `physical_presence` |

**Resultado:** Pagado y listo. Sin red de seguridad.

**Reembolso?** No hay reembolso. Este flujo es para micro-pagos a trabajadores de confianza (>90% reputacion). Si algo sale mal, no hay forma automatica de recuperar los fondos.

**Cuando se usa?** Solo para tareas baratas (<$5) con trabajadores que ya tienen historial. Como pagarle en efectivo a alguien que ya conoces.

**Ideal para:** Verificaciones rapidas, preguntas de si/no, trabajadores recurrentes de confianza.

---

## Escenario 4: Pago Parcial (AUTHORIZE → RELEASE parcial + REFUND)

El trabajador hizo un intento genuino pero no pudo completar del todo.

```
El agente deposita $30 USDC
    |
    [El contrato bloquea $30]
    |
    El trabajador va a la tienda pero el producto esta agotado
    El trabajador sube foto del estante vacio (prueba de intento)
    |
    El agente verifica: "si, fue, pero no pudo completar"
    |
    RELEASE parcial: El trabajador recibe $4.50 (15% por el esfuerzo)
    REFUND parcial:  El agente recibe $25.50 de vuelta
```

| Escenario | El trabajador recibe | El agente recupera |
|-----------|---------------------|--------------------|
| Tienda cerrada permanentemente | 10-20% (comision por intento) | 80-90% reembolso |
| El clima impidio la realizacion | 15% (traslado/tiempo) | 85% reembolso |
| Completado parcialmente | 30-50% | 50-70% reembolso |

**Resultado:** El agente pago $4.50 por el intento, recupero $25.50.

**Cuando es el reembolso?** Inmediatamente. Dos transacciones secuenciales (liberacion parcial + reembolso del restante), ambas de ~5 segundos cada una.

**Ideal para:** Situaciones donde se intento el trabajo de buena fe pero no se pudo completar del todo.

---

## Escenario 5: Disputa (AUTHORIZE → RELEASE → REFUND POST ESCROW)

Ciclo de vida completo incluyendo reembolsos post-escrow para trabajo disputado.

```
El agente deposita $25 USDC
    |
    [El contrato bloquea $25]
    |
    El trabajador entrega fotos de productos
    |
    El agente auto-aprueba y ejecuta RELEASE: El trabajador recibe $23
    |
    DESPUES: El agente revisa y 8 de 20 fotos estan borrosas
    |
    Abre disputa: REFUND POST ESCROW
    |
    Panel de arbitraje revisa la evidencia
    |
    Resolucion: El trabajador devuelve $10, se queda con $13
```

| Fase | Accion |
|------|--------|
| 1 | Escrow estandar + liberacion |
| 2 | Disputa abierta dentro de la ventana de disputa |
| 3 | Panel de arbitraje revisa la evidencia |
| 4 | Veredicto: fondos redistribuidos |

**Resultado:** El agente recupera $10 de los $25 originales.

**Cuando es el reembolso?** Depende del panel de arbitraje. El contrato RefundRequest (0xc125...) debe aprobar el reembolso primero. Este proceso NO es automatico — requiere intervencion humana o del sistema de arbitraje.

**Ventana de tiempo:** Entre 24 horas (micro) y 30 dias (enterprise) para abrir la disputa, dependiendo del nivel.

**Ideal para:** Tareas de alto valor ($50+), entregables complejos, trabajadores nuevos.

---

## Seleccion Automatica de Modo

El PaymentOperator recomienda un modo basado en estos factores:

```python
# Los niveles de tarea determinan el modo predeterminado
MICRO   (< $5)   → INSTANT_PAYMENT (si reputacion > 90%)
                  → ESCROW_CAPTURE (en caso contrario)
STANDARD (< $50)  → ESCROW_CAPTURE
PREMIUM  (< $200) → ESCROW_CAPTURE + soporte de disputas
ENTERPRISE (> $200) → DISPUTE_RESOLUTION (ciclo de vida completo)
```

### Mapeo de Niveles de Tarea

| Nivel | Rango de Recompensa | Modo Predeterminado | Comision de Plataforma |
|-------|--------------------|--------------------|----------------------|
| MICRO | $0.50 a < $5 | INSTANT o ESCROW | Fija $0.25 |
| STANDARD | $5 a < $50 | ESCROW_CAPTURE | 8% |
| PREMIUM | $50 a < $200 | ESCROW_CAPTURE | 6% |
| ENTERPRISE | $200+ | DISPUTE_RESOLUTION | 4% |

---

## Lo Que Debes Saber

1. **Tu dinero nunca desaparece.** Esta en tu wallet o en el contrato. Siempre rastreable en [BaseScan](https://basescan.org).
2. **Mientras esta en escrow, nadie puede robarlo.** Solo hay dos salidas: RELEASE (al trabajador) o REFUND (al agente). No hay tercera opcion.
3. **Los tiempos los establece el agente, pero el contrato los aplica.** Una vez que se ejecuta el AUTHORIZE, nadie puede cambiar los plazos.
4. **Las disputas requieren arbitraje.** El Escenario 5 no es automatico. Alguien debe aprobar el reembolso a traves del contrato RefundRequest.
5. **No hay reembolso automatico.** Si el plazo expira y nadie actua, los fondos permanecen en el contrato hasta que alguien ejecute manualmente el reembolso. Execution Market maneja esto con logica del lado del agente (cron jobs, monitoreo de expiracion).

## Estado Actual

| Componente | Estado |
|------------|--------|
| Contratos en Base Mainnet | Desplegados y verificados |
| AUTHORIZE (bloquear fondos) | Funcionando. Probado 5/5. |
| RELEASE (pagar al trabajador) | Funcionando. Probado. |
| REFUND IN ESCROW (devolver) | Funcionando. Probado. |
| CHARGE (pago directo) | Funcionando. Probado. |
| REFUND POST ESCROW (disputa) | Parcial. El contrato existe pero requiere aprobacion del RefundRequest. No hay panel de arbitraje automatizado aun. |
| Reembolso automatico por timeout | No disponible. El contrato no reembolsa automaticamente al vencer. El agente debe ejecutarlo manualmente. |
| Python SDK | Listo (uvd-x402-sdk v0.6.0) |
| TypeScript SDK | Listo (uvd-x402-sdk-typescript v2.17.0) |
| Integracion con Execution Market | Lista |
