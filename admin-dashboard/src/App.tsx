import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import Settings from './pages/Settings'
import Tasks from './pages/Tasks'
import Analytics from './pages/Analytics'
import Payments from './pages/Payments'
import Users from './pages/Users'
import AuditLog from './pages/AuditLog'
import { AuthError } from './lib/api'

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

const navItems = [
  { path: '/', label: 'Analytics', icon: '📊' },
  { path: '/tasks', label: 'Tasks', icon: '📋' },
  { path: '/payments', label: 'Payments', icon: '💰' },
  { path: '/users', label: 'Users', icon: '👥' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
  { path: '/audit', label: 'Audit Log', icon: '📜' },
]

/**
 * Verify an admin key against the backend.
 * Returns true if the key is valid, false otherwise.
 */
async function verifyAdminKey(key: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/admin/verify`, {
      headers: { 'X-Admin-Key': key },
    })
    return response.ok
  } catch {
    // Network error — treat as invalid so user can re-authenticate
    return false
  }
}

function App() {
  // Lazy initializers read sessionStorage synchronously on first render
  const [adminKey, setAdminKey] = useState<string>(
    () => sessionStorage.getItem('adminKey') || '',
  )
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [isVerifying, setIsVerifying] = useState<boolean>(
    () => !!sessionStorage.getItem('adminKey'),
  )
  const [loginError, setLoginError] = useState('')
  const location = useLocation()

  /** Clear auth state and sessionStorage. */
  const handleLogout = useCallback(() => {
    setIsAuthenticated(false)
    setAdminKey('')
    setLoginError('')
    sessionStorage.removeItem('adminKey')
  }, [])

  // On mount: if we have a stored key, verify it is still valid
  useEffect(() => {
    const storedKey = sessionStorage.getItem('adminKey')
    if (!storedKey) {
      setIsVerifying(false)
      return
    }

    let cancelled = false
    verifyAdminKey(storedKey).then((valid) => {
      if (cancelled) return
      if (valid) {
        setAdminKey(storedKey)
        setIsAuthenticated(true)
      } else {
        // Stored key is stale or invalid — force re-login
        handleLogout()
      }
      setIsVerifying(false)
    })

    return () => {
      cancelled = true
    }
  }, [handleLogout])

  // Global listener: auto-logout on AuthError (401/403) from any child page.
  // Child pages use react-query which may swallow errors, so we also listen for
  // unhandled rejections that carry an AuthError.
  useEffect(() => {
    const onUnhandled = (event: PromiseRejectionEvent) => {
      if (event.reason instanceof AuthError) {
        handleLogout()
      }
    }
    window.addEventListener('unhandledrejection', onUnhandled)
    return () => window.removeEventListener('unhandledrejection', onUnhandled)
  }, [handleLogout])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError('')

    if (!adminKey.trim()) {
      setLoginError('Please enter an admin key')
      return
    }

    try {
      const valid = await verifyAdminKey(adminKey)
      if (valid) {
        setIsAuthenticated(true)
        sessionStorage.setItem('adminKey', adminKey)
      } else {
        setLoginError('Invalid admin key')
      }
    } catch {
      setLoginError('Cannot reach the server. Please try again.')
    }
  }

  // Show spinner while verifying a stored session
  if (isVerifying) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-em-500 mx-auto mb-4" />
          <p className="text-gray-400 text-sm">Verifying session...</p>
        </div>
      </div>
    )
  }

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

        <div className="p-6 border-t border-gray-700">
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
