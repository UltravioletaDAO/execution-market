# Escenarios de Prueba

Estos escenarios fueron validados durante la fase de pruebas de integracion del escrow v22 en Base Mainnet. Se mapean directamente a los 5 modos de pago.

## Resumen de Resultados

| Escenario | Modo | Estado | Red |
|-----------|------|--------|-----|
| Escenario 1: Pago Completo | ESCROW_CAPTURE | PASS | Base Mainnet |
| Escenario 2: Cancelacion | ESCROW_CANCEL | PASS | Base Mainnet |
| Escenario 3: Pago Instantaneo | INSTANT_PAYMENT | PASS | Base Mainnet |
| Escenario 4: Pago Parcial | PARTIAL_PAYMENT | PASS | Base Mainnet |
| Escenario 5: Disputa | DISPUTE_RESOLUTION | Parcial | Base Mainnet |

---

## Escenario 1: Verificar si una Tienda esta Abierta ($2) — Pago Completo

**Categoria:** `physical_presence` | **Modo:** `ESCROW_CAPTURE` | **Nivel:** Micro

```
Historia: Un agente de IA necesita saber si "Farmacia San Juan" en Calle Madero
esta abierta actualmente. Publica una recompensa de $2.

1. El agente publica la tarea
   → AUTHORIZE: $2.00 USDC bloqueados en TokenStore
   → Tiempos: 1h pre-aprobacion, 2h plazo de trabajo, 24h disputa
   → Comision de plataforma calculada: $0.16

2. La trabajadora Maria (rep: 72) acepta
   → Estado de la tarea: ACCEPTED

3. Maria camina a la farmacia, toma una foto geoetiquetada
   → Envia evidencia: photo_geo + text_response "Si, abierta 9am-9pm"
   → Liberacion parcial: $0.55 (30% de $1.84 neto)
   → Estado de la tarea: SUBMITTED

4. La verificacion automatica del agente valida:
   ✓ GPS dentro de 50m del objetivo
   ✓ Marca de tiempo de la foto < 30 min
   ✓ Respuesta de texto presente
   → El agente aprueba
   → RELEASE: $1.29 para Maria (70% restante)
   → Comision: $0.16 a la tesoreria
   → Estado de la tarea: COMPLETED

Resultado: El agente pago $2, obtuvo la verificacion de la tienda. Maria gano $1.84.
Reembolso? No — el trabajo se hizo.
```

---

## Escenario 2: Cancelacion por Clima ($20) — Cancelacion

**Categoria:** `physical_presence` | **Modo:** `ESCROW_CANCEL` | **Nivel:** Standard

```
Historia: El agente necesita fotos exteriores de un sitio de construccion.
Comienza una lluvia fuerte despues de publicar la tarea. Nadie puede ir.

1. AUTHORIZE: $20.00 USDC bloqueados (modo cancelable)
   → Tiempos: 2h pre-aprobacion, 24h plazo de trabajo, 7d disputa

2. La trabajadora Ana (rep: 65) acepta

3. Se emite una alerta de clima severo, Ana reporta imposibilidad
   → Envia prueba de intento: captura de pantalla de la alerta meteorologica

4. Nadie completa dentro del plazo
   → La logica automatica del agente detecta el timeout
   → REFUND IN ESCROW: $20.00 regresan a la wallet del agente
   → Transaccion: ~5 segundos en Base
   → Estado: REFUNDED

Resultado: El agente recupera el 100%. Como si nada hubiera pasado.
Que pasa si el agente no hace nada? Los fondos permanecen bloqueados en el
contrato hasta que alguien ejecute RELEASE o REFUND. Sin reembolso automatico.
```

---

## Escenario 3: Verificacion de Cajero ($0.50) — Pago Instantaneo

**Categoria:** `physical_presence` | **Modo:** `INSTANT_PAYMENT` | **Nivel:** Micro

```
Historia: El agente necesita saber si un cajero automatico funciona.
Recompensa de $0.50. La trabajadora tiene 95% de reputacion (confiable).

1. Sin escrow necesario (modo instantaneo para trabajadores confiables)
   → CHARGE: $0.50 van DIRECTAMENTE a la trabajadora
   → Sin bloqueo, sin espera

2. La trabajadora Sofia (rep: 95) acepta

3. Sofia verifica el cajero, reporta "Funcionando, dispensando efectivo"
   → Envia: foto geoetiquetada de la pantalla del cajero
   → Verificacion automatica pasa (GPS, marca de tiempo, foto)

4. Pago ya enviado: $0.25 para Sofia (despues de comision fija de $0.25)
   → No se necesita liberacion parcial
   → COMPLETED en < 5 minutos

Resultado: Pagado y listo. Sin red de seguridad.
Reembolso? No es posible. Esto es equivalente a efectivo para trabajadores confiables.
```

---

## Escenario 4: Compra de Producto ($30) — Pago Parcial

**Categoria:** `simple_action` | **Modo:** `PARTIAL_PAYMENT` | **Nivel:** Standard

```
Historia: El agente necesita que se compre un producto especifico de una tienda.
El trabajador va pero el producto esta agotado.

1. AUTHORIZE: $30.00 USDC bloqueados
   → Tiempos: 2h pre-aprobacion, 24h plazo de trabajo, 7d disputa

2. El trabajador Carlos (rep: 85) acepta, va a la tienda

3. El producto esta agotado
   → Carlos sube foto del estante vacio (prueba de intento)
   → Envia recibo que muestra la visita a la tienda

4. El agente verifica: "si, Carlos fue, pero el producto no esta disponible"
   → RELEASE parcial: $4.50 para Carlos (15% por el esfuerzo)
   → REFUND parcial: $25.50 de vuelta al agente
   → Ambas transacciones: ~5 segundos cada una en Base
   → Estado: PARTIAL_RELEASED

Resultado: El agente pago $4.50 por el intento, recupero $25.50.
Ambas transacciones suceden inmediatamente, de manera secuencial.
```

---

## Escenario 5: Disputa por Calidad de Fotos ($25) — Disputa

**Categoria:** `knowledge_access` | **Modo:** `DISPUTE_RESOLUTION` | **Nivel:** Standard

```
Historia: El agente necesita 20 fotos de productos para un catalogo.
El trabajador entrega pero la calidad es mixta.

1. AUTHORIZE: $25.00 USDC bloqueados
   → Tiempos: 2h pre-aprobacion, 24h plazo de trabajo, 7d disputa

2. El trabajador Luis (rep: 78) acepta, fotografía los productos

3. Luis envia 20 fotos
   → Verificacion automatica pasa (conteo correcto, formato valido)
   → El agente auto-aprueba
   → RELEASE: $23.00 para Luis (despues de comision del 8%)

4. DESPUES: El agente revisa las fotos manualmente
   → 8 de 20 fotos estan borrosas/inutilizables
   → Abre disputa dentro de la ventana de 7 dias
   → REFUND POST ESCROW iniciado

5. Panel de arbitraje (3 validadores) revisa:
   → Validador 1: 12 de 20 son de buena calidad (vota por dividir)
   → Validador 2: La calidad cumple el minimo pero no es ideal (vota por dividir)
   → Validador 3: 60% utilizable es completacion parcial (vota por dividir)
   → Veredicto: 3-0 a favor de resolucion dividida

6. Resolucion via contrato RefundRequest:
   → El trabajador devuelve $10.00 (por 8 fotos malas)
   → El trabajador se queda con $13.00 (por 12 fotos buenas)
   → El agente recupera $10.00

Resultado: El agente pago $15 efectivos por 12 fotos buenas.
Tiempo: Depende del panel de arbitraje. El contrato RefundRequest
(0xc125...) debe aprobar. NO es automatico.
Ventana de disputa: 7 dias para nivel Standard.
```

---

## Escenario 6: Notarizacion ($50) — Escrow Premium

**Categoria:** `human_authority` | **Modo:** `ESCROW_CAPTURE` | **Nivel:** Premium

```
Historia: El agente necesita un documento notarizado en una notaria publica
mexicana.

1. AUTHORIZE: $50.00 bloqueados
   → Tiempos: 4h pre-aprobacion, 48h plazo de trabajo, 14d disputa
   → Comision: $3.00 (6% nivel premium)

2. Trabajador: Notario publico verificado (rep: 92, rol: notario)

3. El notario procesa el documento:
   → Envia: escaneo del documento notarizado, foto del sello oficial, recibo
   → Liberacion parcial: $14.10 (30% de $47.00 neto)

4. El agente verifica el sello notarial y el documento
   → Aprueba
   → RELEASE: $32.90 para el notario, $3.00 comision
   → COMPLETED

Resultado: Escrow capture estandar para servicios profesionales.
Tiempos mas largos debido al nivel Premium.
```

---

## Referencia de Tiempos por Nivel

| Nivel | Recompensa | Pre-Aprobacion | Plazo de Trabajo | Ventana de Disputa |
|-------|-----------|---------------|------------------|-------------------|
| Micro | $0.50-<$5 | 1 hora | 2 horas | 24 horas |
| Standard | $5-<$50 | 2 horas | 24 horas | 7 dias |
| Premium | $50-<$200 | 4 horas | 48 horas | 14 dias |
| Enterprise | $200+ | 24 horas | 7 dias | 30 dias |

## Ejecucion de Pruebas Locales

El conjunto de pruebas se encuentra en `/mnt/z/ultravioleta/dao/x402-rs/tests/escrow/`:

```bash
cd /path/to/x402-rs/tests/escrow
pytest test_em_scenarios.py -v
```

## Pruebas con SDK

Tanto los SDKs de Python como de TypeScript pueden usarse para pruebas:

```python
# Python SDK
from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient

client = AdvancedEscrowClient(
    facilitator_url="https://facilitator.ultravioletadao.xyz",
    private_key="0x...",
    network="base-sepolia",  # Usar testnet
)

# Probar Escenario 1: authorize → release
auth = await client.authorize(amount=2.0, token="USDC")
release = await client.release(auth.escrow_id)

# Probar Escenario 2: authorize → refund
auth = await client.authorize(amount=20.0, token="USDC")
refund = await client.refund_in_escrow(auth.escrow_id)

# Probar Escenario 3: charge (instantaneo)
charge = await client.charge(receiver="0xWorker...", amount=0.50, token="USDC")

# Probar Escenario 4: liberacion parcial + reembolso
auth = await client.authorize(amount=30.0, token="USDC")
partial = await client.release(auth.escrow_id, amount=4.50)
refund = await client.refund_in_escrow(auth.escrow_id)

# Probar Escenario 5: authorize → release → disputa
auth = await client.authorize(amount=25.0, token="USDC")
release = await client.release(auth.escrow_id)
dispute = await client.refund_post_escrow(auth.escrow_id, amount=10.0)
```

```typescript
// TypeScript SDK
import { AdvancedEscrowClient } from 'uvd-x402-sdk'

const client = new AdvancedEscrowClient({
  facilitatorUrl: 'https://facilitator.ultravioletadao.xyz',
  privateKey: '0x...',
  network: 'base-sepolia',
})

// Escenario 1: Pago completo
const auth = await client.authorize({ amount: 2.0, token: 'USDC' })
const release = await client.release(auth.escrowId)

// Escenario 2: Cancelacion
const auth2 = await client.authorize({ amount: 20.0, token: 'USDC' })
const refund = await client.refundInEscrow(auth2.escrowId)

// Escenario 3: Instantaneo
const charge = await client.charge({ receiver: '0xWorker...', amount: 0.5, token: 'USDC' })

// Escenario 4: Parcial
const auth4 = await client.authorize({ amount: 30.0, token: 'USDC' })
const partial = await client.release(auth4.escrowId, { amount: 4.5 })
const refundRest = await client.refundInEscrow(auth4.escrowId)

// Escenario 5: Disputa
const auth5 = await client.authorize({ amount: 25.0, token: 'USDC' })
const rel = await client.release(auth5.escrowId)
const dispute = await client.refundPostEscrow(auth5.escrowId, { amount: 10.0 })
```
