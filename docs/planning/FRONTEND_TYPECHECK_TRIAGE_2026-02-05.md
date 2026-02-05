# Frontend Typecheck Triage - 2026-02-05

Estado actual de `dashboard`:
- Total errores TS: `353`

Comando usado:
```bash
cd dashboard
npm run typecheck
```

## Top archivos por cantidad de errores

1. `src/services/tasks.ts` -> `59`
2. `src/services/payments.ts` -> `59`
3. `src/services/submissions.ts` -> `46`
4. `src/hooks/useProfile.ts` -> `33`
5. `src/hooks/usePayments.ts` -> `25`
6. `src/hooks/useDisputes.ts` -> `15`
7. `src/components/notifications/NotificationProvider.tsx` -> `14`
8. `src/hooks/useTransaction.ts` -> `8`
9. `src/hooks/useTasks.ts` -> `8`
10. `src/components/NotificationBell.tsx` -> `7`

## Top códigos de error

1. `TS2339` -> `127` (propiedades no existentes / tipos no inferidos)
2. `TS2345` -> `120` (argumentos incompatibles)
3. `TS6133` -> `47` (variables declaradas y no usadas)
4. `TS2322` -> `37` (asignación de tipo incompatible)
5. `TS2769` -> `8` (overload mismatch)

## Plan de corrección recomendado (orden estricto)

### Fase 1: Contrato de datos (resolver cascada)
- [ ] Corregir tipados base en `src/services/tasks.ts`.
- [ ] Corregir tipados base en `src/services/payments.ts`.
- [ ] Corregir tipados base en `src/services/submissions.ts`.

### Fase 2: Hooks consumidores
- [ ] Corregir `src/hooks/useProfile.ts`.
- [ ] Corregir `src/hooks/usePayments.ts`.
- [ ] Corregir `src/hooks/useDisputes.ts`.

### Fase 3: UI dependiente
- [ ] Corregir `src/components/notifications/NotificationProvider.tsx`.
- [ ] Corregir `src/components/NotificationBell.tsx`.

### Fase 4: Limpieza
- [ ] Resolver todos los `TS6133` (unused) en componentes/hooks.
- [ ] Ejecutar `npm run typecheck` hasta `0` errores.

## Criterio de done

- `npm run typecheck` devuelve exit code `0`.
- Se mantiene `npm run test:run` verde.
- Se mantiene `npm run build` verde.

