# NOW-208: Credenciales Cloud para Skill de CLAWDBOT

## Metadata
- **Prioridad**: P2 (Después del MVP)
- **Fase**: Integration
- **Dependencias**: Execution Market funcionando (NOW-202, NOW-203, NOW-204)
- **Tiempo estimado**: 1 hora (después de recibir credenciales)

## Descripción
El usuario necesita proporcionar credenciales de Cloud para crear un skill que integre CLAWDBOT con Execution Market.

## BLOQUEADO: Requiere Credenciales del Usuario

```
ACCIÓN REQUERIDA DEL USUARIO:
1. Proporcionar API key o credenciales de Cloud
2. Especificar qué servicio de Cloud (AWS, GCP, Azure, etc.)
3. Definir qué quiere que el skill haga exactamente
```

## Posible Flujo del Skill

### Concepto: CLAWDBOT + Execution Market
```
1. CLAWDBOT (Claude en Mac Mini) recibe tarea que requiere acción física
2. CLAWDBOT publica tarea en Execution Market via MCP
3. Worker humano completa la tarea
4. CLAWDBOT recibe notificación de completado
5. CLAWDBOT continúa con su flujo
```

### Skill Tentativo
```python
# .claude/skills/clawdbot-em/skill.md
"""
Skill: CLAWDBOT Execution Market Integration

Permite a CLAWDBOT publicar tareas en Execution Market y recibir resultados.

Uso:
/clawdbot-task "Take a photo of the nearest coffee shop menu"

El skill:
1. Crea la tarea en Execution Market
2. Espera a que un worker la complete
3. Retorna la evidencia (foto, etc.)
"""
```

## Preguntas para el Usuario

1. **¿Qué Cloud?**
   - [ ] AWS (ya tenemos experiencia con facilitator)
   - [ ] GCP
   - [ ] Azure
   - [ ] Otro

2. **¿Qué quieres que haga el skill?**
   - [ ] Solo publicar tareas
   - [ ] Publicar y esperar resultado
   - [ ] Integración completa con webhooks

3. **¿Webhook o polling?**
   - Webhook: CLAWDBOT recibe notificación cuando tarea completa
   - Polling: CLAWDBOT pregunta periódicamente

## Una vez recibidas las credenciales

```bash
# Crear estructura del skill
mkdir -p .claude/skills/clawdbot-em
touch .claude/skills/clawdbot-em/skill.md
touch .claude/skills/clawdbot-em/scripts/publish_task.py
touch .claude/skills/clawdbot-em/scripts/wait_for_result.py
```

## Notas
- Este TODO queda pendiente hasta que el usuario proporcione credenciales
- La integración depende de que Execution Market esté funcionando primero
- El timing con el hype de CLAWDBOT es bueno si logramos tenerlo para el jueves
