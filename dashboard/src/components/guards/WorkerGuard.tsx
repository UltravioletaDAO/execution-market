// Execution Market: Worker Guard Component
// Allows only workers to access the route, redirects agents to their dashboard

import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface WorkerGuardProps {
  children: ReactNode
  /** Path to redirect agents to (defaults to '/agent/dashboard') */
  agentRedirect?: string
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
          <div className="absolute inset-0 border-4 border-green-600 rounded-full border-t-transparent animate-spin" />
        </div>
        <p className="text-gray-500 text-sm">Cargando...</p>
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------
// WorkerGuard Component
// --------------------------------------------------------------------------

export function WorkerGuard({
  children,
  agentRedirect = '/agent/dashboard',
  unauthRedirect = '/',
}: WorkerGuardProps) {
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

  // Redirect agents to their dashboard
  if (userType === 'agent') {
    return <Navigate to={agentRedirect} replace />
  }

  // User is authenticated and is a worker (or userType not set, defaults to worker access)
  return <>{children}</>
}

export default WorkerGuard
