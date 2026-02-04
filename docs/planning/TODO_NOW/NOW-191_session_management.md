# NOW-191: Session Management

**Prioridad**: P1
**Status**: TODO
**Dependencias**: NOW-189, NOW-190

## Problema

Necesitamos gestión unificada de sesiones para:
- Workers (JWT token)
- Agents (API key)
- Auto-refresh de tokens
- Logout

## Solución

Crear AuthContext y hooks para manejo centralizado de sesiones.

## Archivos a Crear

- `dashboard/src/context/AuthContext.tsx`
- `dashboard/src/hooks/useAuth.ts`
- `dashboard/src/utils/api.ts` - Cliente HTTP con auth

## Implementación

### 1. AuthContext.tsx

```tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type UserType = 'worker' | 'agent' | null;

interface AuthState {
  isAuthenticated: boolean;
  userType: UserType;
  token: string | null;
  user: any;
}

interface AuthContextType extends AuthState {
  loginAsWorker: (token: string, executor: any) => void;
  loginAsAgent: (apiKey: string, agent: any) => void;
  logout: () => void;
  getAuthHeader: () => Record<string, string>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    userType: null,
    token: null,
    user: null,
  });

  // Restore session on mount
  useEffect(() => {
    const workerToken = localStorage.getItem('em_token');
    const workerData = localStorage.getItem('em_executor');
    const apiKey = localStorage.getItem('em_api_key');
    const agentData = localStorage.getItem('em_agent');

    if (workerToken && workerData) {
      setState({
        isAuthenticated: true,
        userType: 'worker',
        token: workerToken,
        user: JSON.parse(workerData),
      });
    } else if (apiKey && agentData) {
      setState({
        isAuthenticated: true,
        userType: 'agent',
        token: apiKey,
        user: JSON.parse(agentData),
      });
    }
  }, []);

  const loginAsWorker = (token: string, executor: any) => {
    localStorage.setItem('em_token', token);
    localStorage.setItem('em_executor', JSON.stringify(executor));
    setState({
      isAuthenticated: true,
      userType: 'worker',
      token,
      user: executor,
    });
  };

  const loginAsAgent = (apiKey: string, agent: any) => {
    localStorage.setItem('em_api_key', apiKey);
    localStorage.setItem('em_agent', JSON.stringify(agent));
    setState({
      isAuthenticated: true,
      userType: 'agent',
      token: apiKey,
      user: agent,
    });
  };

  const logout = () => {
    localStorage.removeItem('em_token');
    localStorage.removeItem('em_executor');
    localStorage.removeItem('em_api_key');
    localStorage.removeItem('em_agent');
    setState({
      isAuthenticated: false,
      userType: null,
      token: null,
      user: null,
    });
  };

  const getAuthHeader = () => {
    if (!state.token) return {};
    return { Authorization: `Bearer ${state.token}` };
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        loginAsWorker,
        loginAsAgent,
        logout,
        getAuthHeader,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### 2. useAuth hook (alternative export)

```tsx
// dashboard/src/hooks/useAuth.ts
export { useAuth } from '../context/AuthContext';
```

### 3. API client with auth

```tsx
// dashboard/src/utils/api.ts
const API_BASE = import.meta.env.VITE_API_URL || '';

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('em_token') ||
                localStorage.getItem('em_api_key');

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Token expired or invalid
    localStorage.removeItem('em_token');
    localStorage.removeItem('em_api_key');
    window.location.href = '/';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Convenience methods
export const api = {
  get: <T>(endpoint: string) => apiRequest<T>(endpoint),
  post: <T>(endpoint: string, data: any) =>
    apiRequest<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  put: <T>(endpoint: string, data: any) =>
    apiRequest<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: <T>(endpoint: string) =>
    apiRequest<T>(endpoint, { method: 'DELETE' }),
};
```

## Criterios de Aceptación

- [ ] AuthContext disponible en toda la app
- [ ] Sesión se restaura al recargar página
- [ ] `useAuth()` hook funcional
- [ ] API client incluye token automáticamente
- [ ] 401 response limpia sesión y redirige
- [ ] Logout limpia localStorage completo

## Testing

```tsx
// Test component
function TestAuth() {
  const { isAuthenticated, userType, logout } = useAuth();

  return (
    <div>
      <p>Authenticated: {isAuthenticated ? 'Yes' : 'No'}</p>
      <p>Type: {userType || 'None'}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```
