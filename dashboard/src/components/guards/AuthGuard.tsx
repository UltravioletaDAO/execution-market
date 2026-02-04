// Execution Market: Authentication Guard Component
// Protects routes that require authentication, redirects to landing if not authenticated

import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface AuthGuardProps {
  children: ReactNode
  /** Optional redirect path when not authenticated (defaults to '/') */
  redirectTo?: string
}

// --------------------------------------------------------------------------
// Loading Spinner Component
// --------------------------------------------------------------------------

function LoadingSpinner() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        {/* Spinner */}
        <div className="relative w-12 h-12 mx-auto mb-4">
          <div className="absolute inset-0 border-4 border-gray-200 rounded-full" />
          <div className="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin" />
        </div>
        {/* Text */}
        <p className="text-gray-500 text-sm">Verificando autenticacion...</p>
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------
// AuthGuard Component
// --------------------------------------------------------------------------

export function AuthGuard({ children, redirectTo = '/' }: AuthGuardProps) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  // Show loading state while checking authentication
  if (loading) {
    return <LoadingSpinner />
  }

  // Redirect to landing if not authenticated
  if (!isAuthenticated) {
    // Save the attempted URL for redirecting after login
    return <Navigate to={redirectTo} state={{ from: location }} replace />
  }

  // User is authenticated, render children
  return <>{children}</>
}

export default AuthGuard
