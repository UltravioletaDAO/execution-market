// Execution Market: Agent Guard Component
// Allows agents to access routes via either:
//   1. Dynamic.xyz wallet auth (existing flow, userType === 'agent')
//   2. API key JWT auth (new agent login flow)
//   3. Open access when EM_REQUIRE_API_KEY=false on backend
// Redirects unauthenticated agents to /agent/login only when API key is required

import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { isAgentLoggedIn } from '../../utils/agentAuth'
import { usePlatformConfig } from '../../hooks/usePlatformConfig'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface AgentGuardProps {
  children: ReactNode
  /** Path to redirect workers to (defaults to '/tasks') */
  workerRedirect?: string
  /** Path to redirect unauthenticated agents to (defaults to '/agent/login') */
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
  unauthRedirect = '/agent/login',
}: AgentGuardProps) {
  const { isAuthenticated, userType, loading } = useAuth()
  const location = useLocation()
  const { requireApiKey, loading: configLoading } = usePlatformConfig()

  // Check API key JWT auth (independent of Dynamic.xyz)
  const hasAgentJwt = isAgentLoggedIn()

  // If agent has a valid JWT from API key login, allow access immediately
  if (hasAgentJwt) {
    return <>{children}</>
  }

  // If API key is not required, allow open access
  if (!configLoading && !requireApiKey) {
    return <>{children}</>
  }

  // Show loading state while checking wallet authentication or config
  if (loading || configLoading) {
    return <LoadingSpinner />
  }

  // If authenticated via wallet as an agent, allow access
  if (isAuthenticated && userType === 'agent') {
    return <>{children}</>
  }

  // If authenticated via wallet but as a worker, redirect to tasks
  if (isAuthenticated && (userType === 'worker' || userType === null)) {
    return <Navigate to={workerRedirect} replace />
  }

  // Not authenticated at all — redirect to agent login
  return <Navigate to={unauthRedirect} state={{ from: location }} replace />
}

export default AgentGuard
