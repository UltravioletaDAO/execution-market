// Chamba: Agent Guard Component
// Allows only agents to access the route, redirects workers to their tasks page

import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface AgentGuardProps {
  children: ReactNode
  /** Path to redirect workers to (defaults to '/tasks') */
  workerRedirect?: string
  /** Path to redirect unauthenticated users to (defaults to '/') */
  unauthRedirect?: string
}

// --------------------------------------------------------------------------
// Loading Spinner Component
// --------------------------------------------------------------------------

function LoadingSpinner() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="relative w-12 h-12 mx-auto mb-4">
          <div className="absolute inset-0 border-4 border-gray-200 rounded-full" />
          <div className="absolute inset-0 border-4 border-purple-600 rounded-full border-t-transparent animate-spin" />
        </div>
        <p className="text-gray-500 text-sm">Cargando panel de agente...</p>
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------
// AgentGuard Component
// --------------------------------------------------------------------------

export function AgentGuard({
  children,
  workerRedirect = '/tasks',
  unauthRedirect = '/',
}: AgentGuardProps) {
  const { isAuthenticated, userType, loading } = useAuth()
  const location = useLocation()

  // Show loading state while checking authentication
  if (loading) {
    return <LoadingSpinner />
  }

  // Redirect to landing if not authenticated
  if (!isAuthenticated) {
    return <Navigate to={unauthRedirect} state={{ from: location }} replace />
  }

  // Redirect workers to tasks page
  if (userType === 'worker' || userType === null) {
    return <Navigate to={workerRedirect} replace />
  }

  // User is authenticated and is an agent
  return <>{children}</>
}

export default AgentGuard
