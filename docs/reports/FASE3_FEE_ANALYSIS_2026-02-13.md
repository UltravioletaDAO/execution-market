# Fase 3 Fee Analysis — Conversacion con 0xultravioleta (2026-02-13)

## Contexto

Despues del deploy del PaymentOperator Fase 3 (`0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6`) en Base mainnet, se hizo un analisis profundo de la estructura de fees para entender exactamente quien gana que y cuando.

---

## Hallazgo Principal: x402r NO gana nada de nuestras transacciones

El equipo de x402r (BackTrack/Ali) actualmente gana **$0** de las transacciones de Execution Market.

Hay DOS mecanismos de fee distintos en x402r:

| Fee | Quien lo controla | A donde va | Estado en Base |
|-----|-------------------|------------|----------------|
| **Operator fee** (1%) | Nosotros (EM) | EM Treasury `0xae07...` | Activo |
| **Protocol fee** | BackTrack (Ali) | BackTrack multisig `0x773dBcB5...` | **0% (desactivado)** |

El 1% "operator fee" on-chain fue configurado por nosotros durante el deploy de Fase 3, apuntando a nuestro propio treasury. NO es el fee de Ali.

Ali confirmo: *"The configurable fee options are for you, not us."*

El `ProtocolFeeConfig` en `0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6`:
- `calculator()` = `address(0)` = **0% fee**
- `MAX_PROTOCOL_FEE_BPS` = 500 (maximo 5%)
- `TIMELOCK_DELAY` = 604,800 segundos (7 dias de aviso)
- `protocolFeeRecipient` = `0x773dBcB5...` (BackTrack multisig)

---

## Cuando cobra x402r su fee

**Solo en RELEASE (happy path).** Probado on-chain:

| Operacion | Cobra fee? | Evidencia |
|-----------|------------|-----------|
| Authorize (lockear fondos) | NO | TX `0x5f53898e...` - full amount locked |
| **Release (pagar al worker)** | **SI** | TX `0x06e85fb2...` - 1% retenido |
| Refund (devolver al agente) | NO | TX `0xb7709f83...` - 100% devuelto |

Esto significa: x402r gana solo cuando hay tareas completadas exitosamente. Cancelaciones y refunds = cero fee.

---

## La matematica deseada (modelo correcto)

```
Agente publica tarea de $1.00

Al completarse (release):
  -> Worker recibe:     $0.87  (87%)
  -> EM Treasury:       $0.12  (12%)   <- nosotros
  -> Ali (x402r):       $0.01  (1%)    <- ellos, cuando lo activen
                        ------
  Total:                $1.00

Si Ali esta en 0% (situacion actual):
  -> Worker:            $0.87
  -> EM Treasury:       $0.13  (13%)   <- nos quedamos con todo el fee
                        ------
  Total:                $1.00
```

Tres recipients. Simple. La comision de Ali sale del 13% total, NO es adicional.

---

## El problema del operator fee on-chain (1%)

Cuando desplegamos el operador Fase 3, configuramos un `StaticFeeCalculator` al 1% (100 BPS). Este fee:

1. Se retiene DENTRO del contrato del operador al hacer release
2. Requiere llamar `distributeFees()` para enviarlo a EM Treasury
3. Reduce el monto que llega al platform wallet
4. Crea un mismatch matematico en el Python

### Flujo actual (problematico)

```
1. Escrow lockea bounty + 13%
2. Release: operador retiene 1% (nuestro) -> queda atrapado en contrato
3. Platform wallet recibe: (bounty + 13%) * 0.99
4. Python intenta pagar: bounty al worker + 13% al treasury
5. NO ALCANZA -> shortfall de ~1.13% del bounty
```

### Por que es innecesario

- El 1% operator fee va a nuestro treasury de todas formas
- Solo agrega complejidad (distributeFees(), fondos atrapados)
- Cuando Ali active su Protocol fee, seria ADICIONAL al nuestro = 2% on-chain total
- El Python ya cobra el 13% off-chain -- duplica el cobro

---

## Decision: Opcion A — Nuevo operador limpio

**Desplegar nuevo PaymentOperator con `feeCalculator = address(0)` (0% operator fee), manteniendo las OR conditions de Fase 3.**

### Configuracion del nuevo operador

```
feeRecipient              = address(0)          <- SIN fee recipient (no necesario)
feeCalculator             = address(0)          <- SIN fee on-chain nuestro
authorizeCondition        = UsdcTvlLimit        <- igual que Fase 3
releaseCondition          = OR(Payer, Facilitator)  <- igual que Fase 3
refundInEscrowCondition   = OR(Payer, Facilitator)  <- igual que Fase 3
(todo lo demas = address(0))
```

### Flujo despues del fix

```
1. Escrow lockea $1.00
2. Release:
   - Ali toma su % via ProtocolFee (hoy 0%, futuro 1%) -> automatico on-chain
   - El resto llega al platform wallet
3. Python calcula:
   - Worker = 87% del total original
   - Treasury = lo que sobro despues de pagar al worker
4. Si Ali esta en 0%: treasury recibe 13%
5. Si Ali esta en 1%: treasury recibe ~12%, Ali recibio ~1% on-chain
```

### Ventajas

- Cero complejidad on-chain nuestra
- No hay fondos atrapados en contratos
- No hay que llamar `distributeFees()`
- Ali controla su propio fee (ProtocolFeeConfig)
- La matematica es simple: `treasury = total_recibido - bounty_worker`
- Compatible con futuras redes (mismo patron simple)

---

## Transacciones de referencia (Base Mainnet)

### E2E Test — Release (Happy Path)

**TX:** [`0x06e85fb2bcf28ab2606fed13073bf4e98c5cc1b471c2c43ad109099fea22ae54`](https://basescan.org/tx/0x06e85fb2bcf28ab2606fed13073bf4e98c5cc1b471c2c43ad109099fea22ae54)

| Recipient | Monto | % |
|-----------|-------|---|
| Operator (fee nuestro) | 20 USDC units | 1.0% |
| Receiver (worker/treasury) | 1,980 USDC units | 99.0% |
| **Total** | **2,000 USDC units** | **100%** |

### E2E Test — Refund

**TX:** [`0xb7709f8339aa90ddf8dc327aa4b20a50ecf322d974ff0003bc55a6dc903c3725`](https://basescan.org/tx/0xb7709f8339aa90ddf8dc327aa4b20a50ecf322d974ff0003bc55a6dc903c3725)

| Recipient | Monto | % |
|-----------|-------|---|
| Payer (refund completo) | 2,000 USDC units | 100% |
| Fee | 0 | 0% |

### Fondos atrapados en operador Fase 3

- Contrato: `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6`
- Balance USDC: 50 atomic units ($0.000050)
- Origen: 20 units (test 1) + 30 units (test 2)
- Estado: sin reclamar (nunca se llamo `distributeFees()`)

---

## Contratos relevantes

| Contrato | Address | Rol |
|----------|---------|-----|
| PaymentOperator Fase 3 (actual, con 1% fee) | `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6` | A reemplazar |
| PaymentOperator Fase 2 (legacy) | `0xb9635f544665758019159c04c08a3d583dadd723` | Legacy, mantener |
| StaticFeeCalculator (1%, innecesario) | `0xB422A41aae5aFCb150249228eEfCDcd54f1FD987` | No usar mas |
| OrCondition (Payer\|Facilitator) | `0xb365717C35004089996F72939b0C5b32Fa2ef8aE` | Reusar en nuevo operador |
| UsdcTvlLimit (authorize condition) | `0x67B63Af4bFC18d48e0cBb6BAB55f1E1Aab43cAC8` | Reusar en nuevo operador |
| StaticAddressCondition (Facilitator) | `0x9d03c03c15563E72CF2186E9FDB859A00ea661fc` | Referencia |
| ProtocolFeeConfig (Ali controla) | `0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6` | Monitorear |
| PaymentOperatorFactory | `0x3D0837fF8Ea36F417261577b9BA568400A840260` | Para deploy |
| AuthCaptureEscrow | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` | Escrow singleton |
| EM Treasury (Ledger) | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` | Cold wallet |
| BackTrack multisig | `0x773dBcB5...` | Protocol fee recipient |

---

## Accion inmediata

1. Desplegar nuevo PaymentOperator con `feeCalculator = address(0)` en Base
2. Registrar nuevo operador en Facilitator (`addresses.rs`)
3. Actualizar `EM_PAYMENT_OPERATOR` en ECS task definition
4. Ajustar matematica en Python: `treasury = total_recibido - bounty`
5. E2E test con nuevo operador
6. Una vez estable en Base, replicar en las otras 7 redes

---

*Documento generado: 2026-02-13*
*Participantes: 0xultravioleta, Claude Code*
