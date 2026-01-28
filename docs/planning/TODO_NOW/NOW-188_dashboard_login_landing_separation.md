# NOW-188: Dashboard Login/Landing Separation

**Prioridad**: P0
**Status**: TODO
**Dependencias**: NOW-041 (Wagmi wallet connection)

## Problema

Actualmente el dashboard solo muestra la landing page. No hay forma de que un worker o agent entre a la aplicación para ver tareas disponibles o gestionar sus tareas.

## Solución

Separar la landing page del dashboard funcional con un flujo de entrada claro.

## Archivos a Modificar

- `dashboard/src/App.tsx` - Routing
- `dashboard/src/pages/Landing.tsx` - Agregar botón "Enter App"
- `dashboard/src/pages/Dashboard.tsx` - Crear página principal post-login
- `dashboard/src/components/AuthGuard.tsx` - Crear guard para rutas protegidas

## Implementación

### 1. Actualizar App.tsx con rutas

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Tasks from './pages/Tasks';
import Profile from './pages/Profile';
import AuthGuard from './components/AuthGuard';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/about" element={<About />} />
        <Route path="/faq" element={<FAQ />} />

        {/* Protected routes */}
        <Route element={<AuthGuard />}>
          <Route path="/app" element={<Dashboard />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/earnings" element={<Earnings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

### 2. Landing.tsx - Agregar botón de entrada

```tsx
import { useNavigate } from 'react-router-dom';
import { useAccount } from 'wagmi';

export default function Landing() {
  const navigate = useNavigate();
  const { isConnected } = useAccount();

  const handleEnterApp = () => {
    if (isConnected) {
      navigate('/app');
    } else {
      // Open wallet connection modal
      setShowAuthModal(true);
    }
  };

  return (
    <div>
      {/* Existing landing content */}

      <button
        onClick={handleEnterApp}
        className="btn-primary"
      >
        {isConnected ? 'Enter App' : 'Connect Wallet to Start'}
      </button>
    </div>
  );
}
```

### 3. AuthGuard.tsx

```tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAccount } from 'wagmi';

export default function AuthGuard() {
  const { isConnected } = useAccount();

  if (!isConnected) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
```

## Criterios de Aceptación

- [ ] Landing page tiene botón visible "Enter App" o "Connect Wallet"
- [ ] Click en botón abre modal de conexión si no está conectado
- [ ] Si está conectado, redirige a `/app`
- [ ] Rutas `/app`, `/tasks`, `/profile`, `/earnings` están protegidas
- [ ] Acceso a ruta protegida sin auth redirige a landing

## Testing

```bash
# Manual testing
1. Ir a landing page
2. Verificar que botón "Enter App" existe
3. Click sin wallet conectada → modal de conexión
4. Conectar wallet → redirect a /app
5. Navegar a /tasks directamente sin auth → redirect a /
```
