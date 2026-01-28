# NOW-079: TypeScript SDK Tests

## Status: PENDING
## Priority: P2

## Ubicación
`sdk/typescript/src/__tests__/`

## Test Files
- `client.test.ts` - SDK client tests
- `types.test.ts` - Type definition tests
- `errors.test.ts` - Error handling tests

## Ejecutar Tests

```bash
cd sdk/typescript
npm install
npm test
```

## Dependencias Requeridas

```json
{
  "devDependencies": {
    "vitest": "^1.0.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0"
  }
}
```

## Configuración Vitest

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
  },
})
```

## Tests a Implementar

### client.test.ts
- [ ] Client initialization
- [ ] Task creation
- [ ] Task assignment
- [ ] Evidence submission
- [ ] Payment flow
- [ ] Error handling

### types.test.ts
- [ ] Type validation
- [ ] Enum values
- [ ] Interface compliance

### errors.test.ts
- [ ] Custom error types
- [ ] Error messages
- [ ] Error codes

## Coverage Target
- Minimum: 80%
- Target: 90%
