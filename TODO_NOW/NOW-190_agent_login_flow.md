# NOW-190: Agent Login Flow

**Prioridad**: P1
**Status**: TODO
**Dependencias**: NOW-188

## Problema

Agents (AI/empresas) necesitan acceder al dashboard para:
- Ver sus tareas publicadas
- Revisar submissions
- Aprobar/rechazar trabajos
- Ver analytics

La autenticación de agents es por API key, no por wallet.

## Solución

Crear flujo de login con API key que valida contra el backend existente.

## Archivos a Crear/Modificar

- `dashboard/src/components/AgentAuth.tsx` - Componente de auth
- `dashboard/src/pages/AgentDashboard.tsx` - Dashboard para agents
- `mcp_server/api/auth.py` - Ya existe, usar `verify_api_key`

## Flujo de Autenticación

```
1. Agent ingresa API key en formulario
2. Frontend valida formato (chamba_<tier>_<32chars>)
3. Frontend hace request de test a /api/agent/me
4. Si válido, guarda API key en localStorage
5. Requests incluyen API key en header Authorization: Bearer <key>
```

## Implementación

### 1. AgentAuth.tsx

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export function AgentAuth() {
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const validateKeyFormat = (key: string) => {
    const validPrefixes = [
      'chamba_free_',
      'chamba_starter_',
      'chamba_growth_',
      'chamba_enterprise_',
      'sk_chamba_',
    ];
    return validPrefixes.some(p => key.startsWith(p) && key.length >= p.length + 32);
  };

  const handleLogin = async () => {
    setError('');

    if (!validateKeyFormat(apiKey)) {
      setError('Invalid API key format');
      return;
    }

    setIsLoading(true);

    try {
      // Test the API key
      const res = await fetch('/api/agent/me', {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
        },
      });

      if (!res.ok) {
        throw new Error('Invalid API key');
      }

      const agent = await res.json();

      // Store session
      localStorage.setItem('chamba_api_key', apiKey);
      localStorage.setItem('chamba_agent', JSON.stringify(agent));

      navigate('/agent/dashboard');
    } catch (err) {
      setError('Invalid API key. Please check and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="agent-auth">
      <h2>Agent Login</h2>
      <p>Enter your API key to access the Agent Dashboard</p>

      <input
        type="password"
        placeholder="chamba_enterprise_xxxxxxxx..."
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        className="input-api-key"
      />

      {error && <p className="error">{error}</p>}

      <button onClick={handleLogin} disabled={isLoading}>
        {isLoading ? 'Verifying...' : 'Login'}
      </button>

      <p className="help-text">
        Don't have an API key?{' '}
        <a href="/docs/getting-started">Get started here</a>
      </p>
    </div>
  );
}
```

### 2. Backend endpoint /api/agent/me

```python
# mcp_server/api/routes.py

@router.get("/api/agent/me")
async def get_agent_info(
    api_key_data: APIKeyData = Depends(verify_api_key)
):
    """Get current agent information."""
    from supabase_client import get_client

    client = get_client()

    # Get agent stats
    result = client.table("tasks").select(
        "id, status"
    ).eq("agent_id", api_key_data.agent_id).execute()

    tasks = result.data
    stats = {
        "total_tasks": len(tasks),
        "pending": len([t for t in tasks if t["status"] == "pending"]),
        "in_progress": len([t for t in tasks if t["status"] == "in_progress"]),
        "completed": len([t for t in tasks if t["status"] == "completed"]),
    }

    return {
        "agent_id": api_key_data.agent_id,
        "tier": api_key_data.tier,
        "organization_id": api_key_data.organization_id,
        "stats": stats,
    }
```

## Criterios de Aceptación

- [ ] Formulario de entrada de API key
- [ ] Validación de formato client-side
- [ ] Validación server-side con feedback de error
- [ ] API key se guarda en localStorage
- [ ] Redirect a /agent/dashboard después de login
- [ ] Opción de logout que limpia localStorage

## Testing

```bash
# Valid key test
curl -X GET "http://localhost:8000/api/agent/me" \
  -H "Authorization: Bearer chamba_enterprise_test1234567890abcdef1234567890abcdef"

# Invalid key test
curl -X GET "http://localhost:8000/api/agent/me" \
  -H "Authorization: Bearer invalid_key"
```
