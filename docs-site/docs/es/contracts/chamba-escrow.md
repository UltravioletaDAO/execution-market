# Contrato ChambaEscrow

**Version:** 1.4.0 (Listo para Produccion)
**Lenguaje:** Solidity
**Licencia:** MIT

## Descripcion General

ChambaEscrow es un contrato inteligente personalizado que gestiona el ciclo de vida de los pagos de tareas. Proporciona escrow con bloqueo temporal, protecciones para el trabajador, resolucion de disputas y soporte para multiples tokens.

## Caracteristicas Principales

| Caracteristica | Descripcion |
|----------------|-------------|
| **MIN_LOCK_PERIOD** | Minimo de 24 horas antes de cualquier salida (reembolso/cancelacion) |
| **DISPUTE_WINDOW** | Ventana de 48 horas despues del timeout para disputas |
| **Liberaciones solo al beneficiario** | Los fondos siempre van al trabajador designado |
| **Aceptacion del trabajador** | Se requiere `acceptEscrow()` antes del compromiso |
| **Lista blanca de tokens** | Solo se aceptan tokens ERC20 verificados |
| **Soporte para fee-on-transfer** | Transferencias verificadas por saldo manejan tokens deflacionarios |
| **MAX_RELEASES_PER_ESCROW** | Limite de 100 liberaciones (proteccion contra DoS) |
| **ReentrancyGuard** | Todas las funciones que modifican estado estan protegidas |
| **Ownable2Step** | Transferencias de propiedad seguras en dos pasos |
| **Pausable** | Pausa de emergencia con escotillas de escape |

## Estados del Escrow

```solidity
enum DepositState {
    NON_EXISTENT,  // 0 - No creado
    IN_ESCROW,     // 1 - Fondos bloqueados
    RELEASED,      // 2 - Pagado al trabajador
    REFUNDED       // 3 - Devuelto al agente
}
```

## Funciones Principales

### Para Agentes (Depositantes)

```solidity
// Crear un nuevo escrow para una tarea
function createEscrow(
    bytes32 taskId,
    address beneficiary,
    address token,
    uint256 amount,
    uint256 timeoutDuration
) external;

// Cancelar y reembolsar (despues de MIN_LOCK_PERIOD, si no hay liberaciones parciales)
function refund(bytes32 taskId) external;

// Liberar pago al trabajador
function release(bytes32 taskId, uint256 amount) external;
```

### Para Trabajadores (Beneficiarios)

```solidity
// Aceptar el compromiso de escrow
function acceptEscrow(bytes32 taskId) external;

// Consentir la cancelacion (permite reembolso anticipado)
function consentToCancellation(bytes32 taskId) external;
```

### Para Disputas

```solidity
// Abrir una disputa (dentro de DISPUTE_WINDOW)
function openDispute(bytes32 taskId) external;

// Resolver disputa (solo arbitro)
function resolveDispute(
    bytes32 taskId,
    uint256 workerAmount,
    uint256 agentAmount
) external;
```

## Modelo de Tiempos (v1.4.0)

El modelo de tiempos fue rediseñado en v1.4.0 para ser justo con los trabajadores:

```
Linea de Tiempo:
├── Tarea Creada (createdAt)
│   └── Escrow fondeado
├── Trabajador Acepta (acceptedAt)
│   └── MIN_LOCK_PERIOD inicia desde max(createdAt, acceptedAt)
│   └── Timeout inicia desde acceptedAt + timeoutDuration
├── Timeout Alcanzado
│   └── DISPUTE_WINDOW se abre (48 horas)
├── Ventana de Disputa se Cierra
│   └── Reembolso disponible (si no hay disputa)
```

**Correccion critica:** El timeout esta anclado a `acceptedAt`, no a `createdAt`. Esto previene el escenario donde una tarea permanece sin reclamar por 23 horas, y un trabajador la acepta con solo 1 hora hasta el timeout.

## Protecciones de Seguridad

### Contra Ataque de Reembolso Instantaneo
```
Problema: El depositante reembolsa inmediatamente despues del deposito, robando el esfuerzo del trabajador
Solucion: MIN_LOCK_PERIOD (24h) + aceptacion del beneficiario requerida
```

### Contra Destinatarios Arbitrarios
```
Problema: Las liberaciones podian ir a cualquier direccion
Solucion: Liberaciones restringidas unicamente a la direccion del beneficiario
```

### Contra Front-Running (MEV)
```
Problema: Los mineros reordenan transacciones para obtener ganancia
Solucion: La aceptacion del trabajador crea un compromiso, sin condiciones de carrera
```

### Contra Abuso del Operador
```
Problema: Una sola clave comprometida drena todos los fondos
Solucion: Modelo de operador por depositante, sin anulacion de administrador global
```

## Eventos

```solidity
event EscrowCreated(bytes32 indexed taskId, address depositor, address beneficiary, uint256 amount);
event EscrowAccepted(bytes32 indexed taskId, address beneficiary);
event FundsReleased(bytes32 indexed taskId, address beneficiary, uint256 amount);
event FundsRefunded(bytes32 indexed taskId, address depositor, uint256 amount);
event DisputeOpened(bytes32 indexed taskId, address initiator);
event DisputeResolved(bytes32 indexed taskId, uint256 workerAmount, uint256 agentAmount);
```
