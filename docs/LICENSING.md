# Execution Market Licensing Strategy

> Análisis de opciones de licenciamiento para protocolo abierto + plataforma propietaria.
> Fecha: 2026-01-22

---

## Estructura Propuesta

```
execution-market-protocol/         (PÚBLICO - UltravioletaDAO)
├── specs/               Especificaciones del protocolo
├── schemas/             JSON schemas para tareas, workers, verificación
├── reference/           Implementación de referencia
└── docs/                Documentación

execution-market-platform/         (PRIVADO - por ahora)
├── api/                 Backend API
├── matching/            Algoritmo de matching workers
├── verification/        Sistema de verificación
└── frontend/            UI
```

---

## Opciones de Licencia para el Protocolo

### Opción 1: Apache 2.0 (Recomendada)

**Pros:**
- Máxima adopción - usado por la mayoría de protocolos exitosos
- Compatible con casi todo (MIT, BSD, GPL)
- Permite uso comercial sin restricciones
- Protección de patentes incluida
- No requiere que derivados sean open source

**Cons:**
- Competidores pueden tomar y comercializar sin contribuir back
- No hay "copyleft" que obligue a abrir mejoras

**Usado por:** Kubernetes, TensorFlow, Rust, Swift

**Ideal para:** Maximizar adopción del protocolo. Si queremos que muchos lo implementen.

---

### Opción 2: MIT

**Pros:**
- La más simple y permisiva
- Cero fricción legal
- Compatible con todo

**Cons:**
- Sin protección de patentes
- Mismo problema que Apache: no obliga contribuciones

**Usado por:** React, Node.js, jQuery

**Ideal para:** Si la simplicidad es prioridad sobre protección legal.

---

### Opción 3: AGPLv3 (Copyleft fuerte)

**Pros:**
- Obliga a que servicios de red también abran código
- Protege contra "cloud washing" (AWS/Google tomando sin contribuir)
- Comunidad fuerte de copyleft

**Cons:**
- Muchas empresas evitan AGPL por miedo legal
- Reduce adopción significativamente
- No compatible con Apache/MIT

**Usado por:** MongoDB (antes de SSPL), Grafana, Nextcloud

**Ideal para:** Si queremos forzar que todos contribuyan mejoras. Pero reduce adopción.

---

### Opción 4: Dual License (Apache 2.0 + Commercial)

**Pros:**
- Protocolo abierto para la comunidad (Apache)
- Licencia comercial para empresas que no quieren atribución
- Modelo de monetización directo

**Cons:**
- Complejidad administrativa
- Requiere que tengamos todos los copyrights (no podemos aceptar contribuciones externas fácilmente)

**Usado por:** MySQL, Qt, GitLab

**Ideal para:** Si queremos monetizar directamente el protocolo.

---

## Recomendación

### Para el Protocolo: **Apache 2.0**

Razones:
1. **Máxima adopción** - Queremos que muchos implementen Execution Market Protocol
2. **Estándar de la industria** - Web3/crypto prefiere Apache/MIT
3. **Protección de patentes** - Mejor que MIT para protocolo técnico
4. **Compatible con enterprise** - Empresas no tienen miedo de Apache
5. **El valor está en la red, no en el código** - Similar a HTTP, el protocolo es más valioso cuanto más se usa

### Para la Plataforma: **Propietaria** (por ahora)

Razones:
1. **Diferenciación competitiva** - El matching algorithm es nuestro moat
2. **Iteración rápida** - Sin overhead de open source
3. **Monetización directa** - La plataforma es el producto
4. **Puede abrirse después** - Si tiene sentido estratégicamente

---

## Estructura de Archivos de Licencia

### execution-market-protocol/LICENSE

```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Copyright 2026 Ultravioleta DAO

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
```

### execution-market-platform/ (sin LICENSE público)

Mantener privado. Si alguien pregunta:
> "Execution Market Platform is proprietary software developed by Ultravioleta DAO.
> The underlying Execution Market Protocol is open source under Apache 2.0."

---

## Menciones en el Artículo

**Sugerencia de texto para V19:**

> **Plataforma y protocolo**
>
> Algo importante: Execution Market es **ambos**.
>
> El **Execution Market Protocol** es open source bajo Apache 2.0 — el mismo estándar usado por Kubernetes, TensorFlow, y la mayoría de infraestructura moderna. Cualquiera puede implementarlo, modificarlo, o construir encima. Las specs, schemas, y documentación están públicas en GitHub.
>
> La **Execution Market Platform** es nuestra implementación del protocolo — el marketplace donde agentes publican tareas y humanos las toman. El matching algorithm, el sistema de verificación, y la interfaz son propietarios por ahora.
>
> ¿Por qué? Porque el valor del protocolo está en la adopción. Cuantos más lo implementen, más valioso se vuelve. Pero la plataforma es donde capturamos valor para seguir construyendo.
>
> HTTP es abierto. Chrome es de Google. Ambos pueden coexistir.

---

## Referencias

- [Apache 2.0 Full Text](https://www.apache.org/licenses/LICENSE-2.0)
- [Open Source in 2026: Licensing Battles](https://www.linuxinsider.com/story/open-source-in-2026-faces-a-defining-moment-177630.html)
- [Dual Licensing Explained](https://www.blackduck.com/blog/software-licensing-decisions-consider-dual-licensing.html)
- [AGPL vs Apache for Network Services](https://www.mend.io/blog/dual-licensing-for-open-source-components/)

---

## Próximos Pasos

1. [ ] Crear repo `execution-market-protocol` en UltravioletaDAO GitHub
2. [ ] Agregar LICENSE con Apache 2.0
3. [ ] Escribir specs iniciales
4. [ ] Crear schemas JSON para:
   - Task definition
   - Worker profile
   - Verification result
   - Payment settlement
5. [ ] Documentar MCP tools para agentes
6. [ ] Crear repo privado `execution-market-platform`
