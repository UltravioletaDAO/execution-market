# NOW-192: Protected Routes

**Prioridad**: P1
**Status**: TODO
**Dependencias**: NOW-191

## Problema

Ciertas rutas solo deben ser accesibles para usuarios autenticados:
- `/tasks` - Ver/aplicar a tareas (worker)
- `/profile` - Perfil del worker
- `/earnings` - Ganancias del worker
- `/agent/dashboard` - Dashboard del agent
- `/agent/tasks` - Tareas del agent

## Solución

Implementar componentes de guard que verifican autenticación y tipo de usuario.

## Archivos a Crear/Modificar

- `dashboard/src/components/AuthGuard.tsx`
- `dashboard/src/components/WorkerGuard.tsx`
- `dashboard/src/components/AgentGuard.tsx`
- `dashboard/src/App.tsx` - Actualizar routing

## Implementación

### 1. AuthGuard.tsx (cualquier usuario autenticado)

```tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function AuthGuard() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    // Save intended destination for redirect after login
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
```

### 2. WorkerGuard.tsx (solo workers)

```tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function WorkerGuard() {
  const { isAuthenticated, userType } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (userType !== 'worker') {
    return <Navigate to="/agent/dashboard" replace />;
  }

  return <Outlet />;
}
```

### 3. AgentGuard.tsx (solo agents)

```tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function AgentGuard() {
  const { isAuthenticated, userType } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (userType !== 'agent') {
    return <Navigate to="/tasks" replace />;
  }

  return <Outlet />;
}
```

### 4. App.tsx con rutas protegidas

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AuthGuard } from './components/AuthGuard';
import { WorkerGuard } from './components/WorkerGuard';
import { AgentGuard } from './components/AgentGuard';

// Pages
import Landing from './pages/Landing';
import About from './pages/About';
import FAQ from './pages/FAQ';
import Tasks from './pages/Tasks';
import TaskDetail from './pages/TaskDetail';
import Profile from './pages/Profile';
import Earnings from './pages/Earnings';
import AgentDashboard from './pages/AgentDashboard';
import AgentTasks from './pages/AgentTasks';
import SubmissionReview from './pages/SubmissionReview';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* ========== PUBLIC ROUTES ========== */}
          <Route path="/" element={<Landing />} />
          <Route path="/about" element={<About />} />
          <Route path="/faq" element={<FAQ />} />
          <Route path="/login/worker" element={<WorkerLogin />} />
          <Route path="/login/agent" element={<AgentLogin />} />

          {/* ========== WORKER ROUTES ========== */}
          <Route element={<WorkerGuard />}>
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/tasks/:id" element={<TaskDetail />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/earnings" element={<Earnings />} />
            <Route path="/my-tasks" element={<MyTasks />} />
          </Route>

          {/* ========== AGENT ROUTES ========== */}
          <Route element={<AgentGuard />}>
            <Route path="/agent/dashboard" element={<AgentDashboard />} />
            <Route path="/agent/tasks" element={<AgentTasks />} />
            <Route path="/agent/tasks/:id" element={<AgentTaskDetail />} />
            <Route path="/agent/submissions/:id" element={<SubmissionReview />} />
            <Route path="/agent/analytics" element={<AgentAnalytics />} />
          </Route>

          {/* ========== 404 ========== */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
```

## Rutas por Tipo de Usuario

| Ruta | Público | Worker | Agent |
|------|---------|--------|-------|
| `/` | ✅ | ✅ | ✅ |
| `/about` | ✅ | ✅ | ✅ |
| `/faq` | ✅ | ✅ | ✅ |
| `/tasks` | ❌ | ✅ | ❌ |
| `/profile` | ❌ | ✅ | ❌ |
| `/earnings` | ❌ | ✅ | ❌ |
| `/agent/dashboard` | ❌ | ❌ | ✅ |
| `/agent/tasks` | ❌ | ❌ | ✅ |

## Criterios de Aceptación

- [ ] Rutas públicas accesibles sin auth
- [ ] Rutas de worker requieren worker auth
- [ ] Rutas de agent requieren agent auth
- [ ] Worker intentando /agent/* redirige a /tasks
- [ ] Agent intentando /tasks redirige a /agent/dashboard
- [ ] No autenticado redirige a landing

## Testing

```bash
# Manual testing checklist
1. Sin auth → /tasks → redirige a /
2. Sin auth → /agent/dashboard → redirige a /
3. Worker auth → /tasks → OK
4. Worker auth → /agent/dashboard → redirige a /tasks
5. Agent auth → /agent/dashboard → OK
6. Agent auth → /tasks → redirige a /agent/dashboard
```
