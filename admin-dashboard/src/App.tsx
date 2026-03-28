import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { useState } from 'react'
import Settings from './pages/Settings'
import Tasks from './pages/Tasks'
import Analytics from './pages/Analytics'
import Payments from './pages/Payments'
import Users from './pages/Users'
import AuditLog from './pages/AuditLog'
import ConnectionStatus from './components/ConnectionStatus'
import { useWebSocketInvalidation } from './lib/ws'

const navItems = [
  { path: '/', label: 'Analytics', icon: '📊' },
  { path: '/tasks', label: 'Tasks', icon: '📋' },
  { path: '/payments', label: 'Payments', icon: '💰' },
  { path: '/users', label: 'Users', icon: '👥' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
  { path: '/audit', label: 'Audit Log', icon: '📜' },
]

function App() {
  const [adminKey, setAdminKey] = useState('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loginError, setLoginError] = useState('')
  const location = useLocation()

  // Auto-invalidate React Query caches on WebSocket events
  useWebSocketInvalidation()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError('')

    if (!adminKey.trim()) {
      setLoginError('Please enter an admin key')
      return
    }

    // Verify the admin key with the backend using header auth
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'
      const response = await fetch(`${API_BASE}/api/v1/admin/verify`, {
        headers: { 'X-Admin-Key': adminKey },
      })

      if (response.ok) {
        setIsAuthenticated(true)
        sessionStorage.setItem('adminKey', adminKey)
      } else {
        setLoginError('Invalid admin key')
      }
    } catch {
      setLoginError('Cannot reach the server. Please try again.')
    }
  }

  const handleLogout = () => {
    setIsAuthenticated(false)
    setAdminKey('')
    sessionStorage.removeItem('adminKey')
  }

  // Check session storage on mount
  useState(() => {
    const storedKey = sessionStorage.getItem('adminKey')
    if (storedKey) {
      setAdminKey(storedKey)
      setIsAuthenticated(true)
    }
  })

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-gray-800 p-8 rounded-lg shadow-xl max-w-md w-full">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-em-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xl">🔧</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Execution Market Admin</h1>
              <p className="text-gray-400 text-sm">Platform Management Console</p>
            </div>
          </div>

          <form onSubmit={handleLogin}>
            <label className="block text-gray-400 text-sm mb-2">
              Admin Key
            </label>
            <input
              type="password"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 focus:border-em-500 focus:outline-none focus:ring-1 focus:ring-em-500"
              placeholder="Enter admin key..."
              autoFocus
            />
            {loginError && (
              <p className="mt-2 text-red-400 text-sm">{loginError}</p>
            )}
            <button
              type="submit"
              className="w-full mt-4 bg-em-600 hover:bg-em-700 text-white px-4 py-3 rounded-lg font-medium transition-colors"
            >
              Login
            </button>
          </form>

          <p className="mt-6 text-gray-500 text-xs text-center">
            Contact your administrator if you need access.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-em-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm">🔧</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Execution Market Admin</h1>
              <p className="text-gray-400 text-xs">Platform Management</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 mt-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center px-6 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors ${
                location.pathname === item.path ? 'bg-gray-700 text-white border-l-4 border-em-500' : ''
              }`}
            >
              <span className="mr-3 text-lg">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="p-6 border-t border-gray-700 space-y-3">
          <div className="flex items-center justify-between">
            <ConnectionStatus />
          </div>
          <div className="flex items-center justify-between">
            <div className="text-gray-400 text-sm">
              <span className="text-gray-500">Key:</span> {adminKey.slice(0, 8)}...
            </div>
            <button
              onClick={handleLogout}
              className="text-gray-400 hover:text-white text-sm"
            >
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 p-8">
        <Routes>
          <Route path="/" element={<Analytics adminKey={adminKey} />} />
          <Route path="/tasks" element={<Tasks adminKey={adminKey} />} />
          <Route path="/payments" element={<Payments adminKey={adminKey} />} />
          <Route path="/users" element={<Users adminKey={adminKey} />} />
          <Route path="/settings" element={<Settings adminKey={adminKey} />} />
          <Route path="/audit" element={<AuditLog adminKey={adminKey} />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
