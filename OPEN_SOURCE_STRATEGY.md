# Chamba Open Source Strategy

> Documento de estrategia para la liberacion open source del proyecto Chamba.
> Fecha: 2026-01-24

---

## Resumen Ejecutivo

Chamba adoptara un **modelo hibrido** de licenciamiento:
- **Protocol**: MIT License (maximo alcance, adopcion libre)
- **Platform**: AGPL-3.0 o propietario (proteccion del negocio)

Este enfoque permite que el protocolo se convierta en un estandar abierto mientras Ultravioleta DAO mantiene ventaja competitiva en la implementacion.

---

## Estructura de Repositorios

```
github.com/UltravioletaDAO/
├── chamba-protocol/          ← MIT License
│   ├── specs/                # Especificaciones del protocolo
│   │   ├── task-schema.json  # Formato de tareas
│   │   ├── verification.md   # Estandar de verificacion
│   │   ├── reputation.md     # Integracion ERC-8004
│   │   └── payments.md       # Integracion x402
│   ├── reference/            # Implementacion de referencia
│   │   ├── mcp-tools/        # MCP tools para agentes
│   │   ├── worker-sdk/       # SDK para workers (TS + Python)
│   │   └── verifier/         # Verificador basico
│   └── examples/             # Ejemplos de integracion
│
├── chamba-platform/          ← AGPL-3.0 o Propietario
│   ├── api/                  # Backend de matching
│   ├── web/                  # Frontend (si aplica)
│   ├── verification/         # Sistema de verificacion avanzado
│   └── analytics/            # Metricas y dashboards
│
└── chamba-enterprise/        ← Propietario (licencia comercial)
    ├── private-pools/        # Pools privados de workers
    ├── points-system/        # Sistema de puntos interno
    └── integrations/         # Integraciones enterprise
```

---

## Licencias Comparadas

| Aspecto | MIT | Apache 2.0 | AGPL-3.0 | Propietario |
|---------|-----|------------|----------|-------------|
| Uso comercial | ✅ | ✅ | ✅ | ❌ (requiere licencia) |
| Modificacion | ✅ | ✅ | ✅ | ❌ |
| Distribucion | ✅ | ✅ | ✅ (con codigo) | ❌ |
| Obliga compartir cambios | ❌ | ❌ | ✅ | N/A |
| Proteccion patentes | ❌ | ✅ | ✅ | ✅ |
| Network use = distribucion | ❌ | ❌ | ✅ | N/A |

### Por que MIT para el Protocol

1. **Maxima adopcion**: Cualquiera puede implementar sin restricciones
2. **Interoperabilidad**: Otros proyectos pueden integrar sin friccion
3. **Estandarizacion**: Mayor probabilidad de convertirse en estandar
4. **Contribuciones**: Menos barreras para contributors

### Por que AGPL para la Platform

1. **Proteccion anti-cloud**: Si AWS/Azure quieren correr Chamba, deben liberar su codigo
2. **Contribuciones forzadas**: Mejoras de terceros vuelven al proyecto
3. **Valor diferencial**: La implementacion de Ultravioleta tiene ventaja

### Alternativa: Business Source License (BSL)

Si AGPL es muy restrictivo para atraer contribuidores:

```
BSL 1.1 con conversion a MIT en 3 anios
- Uso: Permitido para desarrollo y testing
- Produccion: Requiere licencia comercial
- Automaticamente MIT en 2029
```

---

## Que se libera y cuando

### Fase 1: Especificaciones (Inmediato)

```yaml
release: chamba-protocol v0.1
license: MIT
contenido:
  - Task Schema (JSON Schema)
  - Verification Standards
  - Payment Integration Specs
  - Reputation Guidelines
```

**Por que primero**: Permite que la comunidad revise y sugiera mejoras al diseno antes de implementar.

### Fase 2: SDKs y Reference Implementation (2-4 semanas)

```yaml
release: chamba-protocol v0.2
license: MIT
contenido:
  - MCP Tools (para que agentes publiquen tareas)
  - Worker SDK (TypeScript + Python)
  - Verifier de referencia
  - Ejemplos de integracion
```

**Por que segundo**: Con specs estables, la comunidad puede empezar a construir.

### Fase 3: Platform Basica (1-2 meses)

```yaml
release: chamba-platform v0.1
license: AGPL-3.0
contenido:
  - API de matching basica
  - Verificacion automatica
  - Integracion x402 + ERC-8004
```

**Por que AGPL**: Protege el trabajo mientras permite transparencia.

---

## Modelo de Contribucion

### Contributor License Agreement (CLA)

Todos los contributors firman un CLA que permite a Ultravioleta DAO:
- Relicensiar contribuciones (para enterprise)
- Mantener dual-licensing si es necesario

### Proceso de Contribucion

```
1. Issue / Discussion → Discutir cambio propuesto
2. RFC (si es significativo) → Documento formal
3. PR con tests → Codigo + pruebas
4. Review → Al menos 1 maintainer aprueba
5. Merge → Se incluye en proxima release
```

### Reconocimiento

- CONTRIBUTORS.md con todos los contributors
- Mencion en changelogs
- Badge de contributor en perfil (si implementamos sistema de badges)

---

## Modelo de Negocio Compatible

### Ingresos Protocol (6-8% fee)

El protocolo define un fee que va a:
- 70% → Facilitator (quien procesa x402)
- 20% → Protocol treasury
- 10% → Validators

Ultravioleta DAO opera el facilitator principal, capturando el 70%.

### Ingresos Platform

- Comision de matching (adicional al protocol fee)
- Features premium (analytics, prioridad, etc)
- API access para integradores

### Ingresos Enterprise

- Licencias comerciales para chamba-enterprise
- Soporte y SLA
- Custom integrations

---

## Gobernanza

### Ahora (Pre-lanzamiento)

Ultravioleta DAO tiene control total. Decisiones rapidas.

### Corto Plazo (Post-lanzamiento)

- Core maintainers: Ultravioleta DAO
- Contributors con merge rights por area
- Decisions via GitHub Discussions

### Largo Plazo (Madurez)

Considerar:
- Steering Committee con representantes externos
- Proceso de RFC formal para cambios mayores
- Posible fundacion independiente (como Linux Foundation)

---

## Mensaje para el Articulo

Agregar al articulo (seccion "Lo que queremos"):

> **El protocolo sera open source.** Las especificaciones, los schemas, los SDKs — todo estara disponible bajo licencia MIT para que cualquiera pueda construir encima. Queremos que Chamba Protocol se convierta en un estandar, no en un jardin cerrado.
>
> La plataforma que operamos (el marketplace, el matching, la verificacion avanzada) es nuestro negocio. Pero el protocolo es de todos.
>
> Si quieres contribuir al diseno del protocolo, estamos en github.com/UltravioletaDAO/chamba-protocol. Los specs todavia se estan definiendo. Tu input importa.

---

## Proximos Pasos

1. [ ] Crear repo `chamba-protocol` en GitHub
2. [ ] Escribir specs iniciales (task schema, verification)
3. [ ] Definir CLA
4. [ ] Publicar en articulo la invitacion a contribuir
5. [ ] Primer PR externo como validacion del proceso

---

## Referencias

- [MIT License](https://opensource.org/licenses/MIT)
- [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.en.html)
- [Business Source License](https://mariadb.com/bsl11/)
- [Contributor License Agreements](https://en.wikipedia.org/wiki/Contributor_License_Agreement)

---

*Documento vivo. Actualizar segun evolucione la estrategia.*
