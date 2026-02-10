# Contrato ChambaEscrow — DEPRECADO

> **Este contrato ha sido deprecado y archivado.** Todas las operaciones de pago ahora usan el **x402 Facilitator** (sin gas, basado en EIP-3009).

## Reemplazo

| Anterior | Actual |
|----------|--------|
| ChambaEscrow.sol | x402 Facilitator (`uvd-x402-sdk`) |
| Llamadas directas al contrato | SDK + Facilitator (sin gas) |
| Escrow personalizado por red | AuthCaptureEscrow en 9 redes |

## Migracion

Todos los pagos de tareas ahora fluyen a traves de:

```
Agente firma auth EIP-3009 → SDK → Facilitator → TX on-chain (Facilitator paga gas)
```

Ver [Direcciones de Contratos](/es/contracts/addresses) para las direcciones actuales.

## Despliegues Historicos (Solo Lectura)

| Red | Direccion | Estado |
|-----|-----------|--------|
| Ethereum | `0x6c320efaC433690899725B3a7C84635430Acf722` | v1.0, pre-auditoria, sin fondos activos |
| Avalanche | `0xedA98AF95B76293a17399Af41A499C193A8DB51A` | v2, verificado, sin fondos activos |

Codigo fuente archivado en `_archive/contracts/ChambaEscrow.sol`.
