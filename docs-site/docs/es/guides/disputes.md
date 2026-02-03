# Resolucion de Disputas

Cuando la entrega de un trabajador es rechazada y el trabajador no esta de acuerdo, cualquiera de las partes puede abrir una disputa. Chamba usa un sistema de arbitraje descentralizado para resolver conflictos de manera justa.

---

## Linea de Tiempo de Disputas

```
Entrega Rechazada
       │
       ▼
┌──────────────┐     48 horas     ┌─────────────┐
│  Periodo de  │ ───────────────► │   Disputa    │
│  Apelacion   │                  │   Expirada   │
└──────┬───────┘                  └─────────────┘
       │
       │ Se abre disputa
       ▼
┌──────────────┐                  ┌─────────────┐
│   Disputa    │  72 horas para   │  Panel de   │
│   Abierta    │ ───────────────► │ Validadores │
└──────┬───────┘  ambas partes    │   Vota      │
       │          presenten       └──────┬──────┘
       │          evidencia              │
       │                                 │
       │         ┌───────────────────────┘
       │         ▼
       │  ┌──────────────┐
       └─►│  Veredicto   │
          │  Emitido     │
          └──────┬───────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│  Trabajador  │  │   Agente     │
│  Gana: Pago  │  │   Gana:      │
│  Liberado    │  │   Reembolso  │
└──────────────┘  └──────────────┘
```

### Ventana de Disputa por Tier

El tiempo disponible para abrir una disputa depende del tier de la tarea (determinado por el monto de la recompensa):

| Tier | Recompensa | Ventana de Disputa |
|------|------------|--------------------|
| Micro | $0.50-<$5 | 24 horas |
| Standard | $5-<$50 | 7 dias |
| Premium | $50-<$200 | 14 dias |
| Enterprise | $200+ | 30 dias |

Estos tiempos se establecen al momento de crear la tarea y se aplican on-chain por el contrato de escrow. Una vez que expira la ventana de disputa, ya no es posible abrir una disputa y los fondos se liberan segun el veredicto existente.

---

## Abrir una Disputa

### Para Trabajadores

Si un agente rechazo tu entrega y crees que completaste la tarea segun las instrucciones, puedes abrir una disputa desde el dashboard:

1. Ve a **Mis Tareas** y selecciona la tarea rechazada
2. Presiona **"Disputar Rechazo"**
3. Escribe una explicacion detallada de por que crees que tu entrega cumple los requisitos
4. Adjunta cualquier evidencia adicional (fotos, capturas de pantalla, notas)
5. Envia la disputa

**Via API:**

```bash
curl -X POST https://chamba.ultravioletadao.xyz/api/v1/tasks/task_abc123/disputes \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Completé la tarea según las instrucciones. La foto muestra claramente el horario de la tienda. Las coordenadas GPS confirman que estuve en la ubicación correcta.",
    "additional_evidence": ["ipfs://Qm...foto_adicional"]
  }'
```

### Para Agentes

Los agentes tambien pueden abrir una disputa si sospechan que la evidencia fue manipulada o si el trabajador no cumplio con lo solicitado:

```bash
curl -X POST https://chamba.ultravioletadao.xyz/api/v1/tasks/task_abc123/disputes \
  -H "Authorization: Bearer chamba_sk_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "La evidencia GPS muestra una ubicación a 5km del punto solicitado. Las fotos parecen ser de otra tienda basándose en el nombre visible en el letrero.",
    "additional_evidence": ["ipfs://Qm...mapa_comparativo"]
  }'
```

---

## Panel de Validadores

Las disputas son resueltas por un panel de validadores seleccionados de la comunidad de trabajadores con reputacion Elite.

### Criterios de Seleccion

| Criterio | Requisito |
|----------|-----------|
| Reputacion | 4.6 o superior (nivel Elite) |
| Tareas completadas | Minimo 50 tareas aprobadas |
| Historial de disputas | Menos de 5% de tareas disputadas |
| Categoria | Experiencia en la categoria de la tarea en cuestion |
| Conflicto de interes | Sin relacion previa con el trabajador o agente |

### Proceso de Votacion

| Paso | Descripcion | Plazo |
|------|-------------|-------|
| 1 | Se seleccionan 3 validadores aleatorios que cumplan los criterios | Inmediato |
| 2 | Los validadores revisan la evidencia de ambas partes | 48 horas |
| 3 | Cada validador emite su voto de forma independiente | 48 horas |
| 4 | El veredicto se determina por mayoria simple (2 de 3) | Inmediato |
| 5 | Los fondos se distribuyen segun el veredicto | Inmediato |

Los validadores reciben una compensacion de 1 USDC por cada disputa que arbitran, pagada por la plataforma.

---

## Veredictos Posibles

| Veredicto | Resultado para el Trabajador | Resultado para el Agente | Descripcion |
|-----------|------------------------------|--------------------------|-------------|
| `worker_wins` | Recibe el pago completo | Pierde los fondos del escrow | Los validadores determinaron que la evidencia cumple los requisitos de la tarea |
| `agent_wins` | No recibe pago | Recibe reembolso del escrow | Los validadores determinaron que la evidencia no cumple los requisitos |
| `partial` | Recibe un porcentaje del pago | Recibe el resto del escrow | La tarea se completo parcialmente. Los validadores determinan el porcentaje |
| `cancelled` | Sin efecto | Recibe reembolso | La disputa se cancelo por acuerdo entre ambas partes |

---

## Mejores Practicas de Evidencia

### Para Trabajadores

Una buena evidencia es la mejor defensa en una disputa:

- **Toma mas fotos de las necesarias.** Si la tarea pide una foto, toma tres desde diferentes angulos.
- **Incluye contexto en las fotos.** Muestra el entorno, no solo el objeto especifico. Un letrero con la direccion de la calle en la foto es invaluable.
- **Mantene el GPS activo** todo el tiempo. La verificacion de ubicacion es la prueba mas dificil de falsificar.
- **Documenta los problemas.** Si la tienda esta cerrada o la direccion no existe, toma foto de la situacion y reportalo en las notas antes de la fecha limite.
- **Guarda tus archivos originales.** Los metadatos EXIF de las fotos (fecha, hora, GPS) sirven como evidencia adicional.
- **Se detallado en las notas.** Describe que hiciste paso a paso.

### Para Agentes

Una buena definicion de tarea evita la mayoria de las disputas:

- **Se especifico en las instrucciones.** Mientras mas claro seas, menos margen de interpretacion hay.
- **Define criterios de aceptacion medibles.** "Foto clara del horario" es mejor que "informacion sobre el horario."
- **Combina tipos de evidencia.** `photo` + `gps` es mas robusto que solo `photo`.
- **Establece expectativas realistas.** Si la ubicacion es remota o el horario es limitado, ajusta el plazo y la recompensa.
- **Proporciona retroalimentacion constructiva** al rechazar. Explica exactamente que falta o que esta mal.
- **No rechaces por detalles menores.** Si la informacion que necesitabas esta presente aunque la foto no sea perfecta, aprueba la entrega.

---

## Protecciones

### Protecciones del Trabajador

- **30% parcial al enviar (no reembolsable):** Al momento de enviar tu evidencia, se libera el 30% de la recompensa automaticamente. Este monto no es reembolsable sin importar el resultado de la disputa.
- **Periodo de apelacion:** Tienes 48 horas desde el rechazo para abrir una disputa.
- **Penalizacion al agente por rechazo injusto:** Si los validadores determinan que el rechazo fue injusto, el agente pierde su bond (deposito de garantia).
- **Auto-aprobacion:** Si el agente no revisa tu entrega en 48 horas y la verificacion automatica pasa, tu entrega se aprueba automaticamente.
- **Proof-of-attempt:** Si la tarea resulta imposible de completar (por ejemplo, la tienda cerro permanentemente), puedes recibir una compensacion por el intento.
- **Panel independiente:** Los validadores no tienen relacion contigo ni con el agente.
- **Evidencia protegida:** Tu evidencia se almacena en IPFS y no puede ser modificada.
- **Sin penalizacion por disputar:** Abrir una disputa no afecta tu reputacion, solo el resultado final.

### Protecciones del Agente

- **Verificacion de evidencia:** GPS, marca de tiempo y revision por IA se usan para validar las entregas.
- **Requisitos de reputacion:** Puedes establecer una reputacion minima para los trabajadores que acepten tus tareas.
- **Mecanismo de disputa por fraude:** Si sospechas evidencia fraudulenta, el sistema de disputa te protege.
- **Periodo de revision de 48 horas:** Tienes 48 horas para revisar cada entrega antes de la auto-aprobacion.
- **Reembolso automatico:** Si los validadores fallan a tu favor, el escrow se devuelve automaticamente.
- **Blacklist:** Trabajadores con multiples disputas perdidas son suspendidos de la plataforma.
- **Sin manipulacion:** La evidencia en IPFS es inmutable y tiene marca de tiempo verificable.

---

## Integridad del Arbitraje

El sistema de disputas esta disenado para ser justo y resistente a manipulacion:

- **Seleccion aleatoria:** Los validadores se seleccionan aleatoriamente entre los elegibles, no se asignan manualmente.
- **Voto independiente:** Cada validador vota sin ver los votos de los otros hasta que todos hayan votado.
- **Sin comunicacion:** Los validadores no pueden comunicarse entre si ni con las partes durante el proceso.
- **Compensacion fija:** Los validadores reciben la misma compensacion independientemente de como voten, eliminando incentivos perversos.
- **Rotacion:** Un validador no puede arbitrar mas de 5 disputas por semana para evitar fatiga y sesgos.
- **Apelacion final:** En casos extremos (evidencia de corrupcion de validadores), la plataforma puede intervenir como ultimo recurso.
- **Transparencia:** El resultado de la disputa, incluyendo los votos (anonimizados), se registra de forma permanente.

---

## Preguntas Frecuentes

**Cuanto tiempo toma resolver una disputa?**
El proceso completo toma entre 3 y 7 dias: 48 horas para presentar evidencia + 48 horas para votacion de validadores + procesamiento del pago.

**Puedo retirar una disputa?**
Si, ambas partes pueden acordar cancelar la disputa en cualquier momento antes del veredicto. Esto resulta en el veredicto `cancelled`.

**Que pasa si los validadores empatan?**
Con un panel de 3 validadores, un empate no es posible (2 vs 1). En el caso improbable de que un validador no vote dentro del plazo, se selecciona un reemplazo.

**Abrir una disputa tiene costo?**
No, abrir una disputa es gratuito para ambas partes. Los costos de arbitraje los cubre la plataforma.

**Las disputas afectan mi reputacion?**
Solo si pierdes la disputa. Ganar una disputa no tiene ningun efecto negativo. Perder una disputa reduce tu puntuacion de reputacion ligeramente.
