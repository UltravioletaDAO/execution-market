/**
 * Execution Market: Authentication Context (Dynamic.xyz Integration)
 *
 * Provides authentication state using Dynamic.xyz for wallet auth
 * and Supabase for executor data storage.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import { useDynamicContext, useIsLoggedIn } from '@dynamic-labs/sdk-react-core'
import { supabase } from '../lib/supabase'
import type { Executor } from '../types/database'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

export type UserType = 'worker' | 'agent' | null

interface AuthContextValue {
  // State
  walletAddress: string | null
  executor: Executor | null
  userType: UserType
  isAuthenticated: boolean
  isProfileComplete: boolean
  loading: boolean
  error: Error | null

  // Actions
  logout: () => Promise<void>
  setUserType: (type: UserType) => void
  refreshExecutor: () => Promise<void>
  openAuthModal: () => void
}

// --------------------------------------------------------------------------
// Constants
// --------------------------------------------------------------------------

const USER_TYPE_STORAGE_KEY = 'em_user_type'

// --------------------------------------------------------------------------
// Context
// --------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

// --------------------------------------------------------------------------
// Provider Component
// --------------------------------------------------------------------------

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { primaryWallet, handleLogOut, setShowAuthFlow } = useDynamicContext()
  const isLoggedIn = useIsLoggedIn()

  const [executor, setExecutor] = useState<Executor | null>(null)
  const [userType, setUserTypeState] = useState<UserType>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(USER_TYPE_STORAGE_KEY)
      if (stored === 'worker' || stored === 'agent') {
        return stored
      }
    }
    return null
  })
  const [loading, setLoading] = useState(true)
  const [error] = useState<Error | null>(null)

  // Derived state
  const walletAddress = primaryWallet?.address?.toLowerCase() || null
  const isAuthenticated = isLoggedIn && !!walletAddress
  const isProfileComplete = !!executor?.display_name

  // --------------------------------------------------------------------------
  // Fetch executor from Supabase by wallet address
  // --------------------------------------------------------------------------
  const fetchExecutor = useCallback(async (wallet: string): Promise<Executor | null> => {
    const normalizedWallet = wallet.toLowerCase()

    try {
      // Try to get existing executor
      const { data, error: fetchError } = await supabase
        .from('executors')
        .select('*')
        .eq('wallet_address', normalizedWallet)
        .single()

      if (fetchError && fetchError.code !== 'PGRST116') {
        // PGRST116 = no rows found, which is OK for new users
        return null
      }

      if (data) {
        return data as Executor
      }

      // No executor found - create one
      const { data: newExecutor, error: createError } = await supabase
        .from('executors')
        .insert({
          wallet_address: normalizedWallet,
          status: 'active',
        } as never)
        .select()
        .single()

      if (createError) {
        return null
      }

      return newExecutor as Executor
    } catch {
      return null
    }
  }, [])

  // --------------------------------------------------------------------------
  // Set user type (persisted to localStorage)
  // --------------------------------------------------------------------------
  const setUserType = useCallback((type: UserType) => {
    setUserTypeState(type)
    if (typeof window !== 'undefined') {
      if (type) {
        localStorage.setItem(USER_TYPE_STORAGE_KEY, type)
      } else {
        localStorage.removeItem(USER_TYPE_STORAGE_KEY)
      }
    }
  }, [])

  // --------------------------------------------------------------------------
  // Refresh executor data
  // --------------------------------------------------------------------------
  const refreshExecutor = useCallback(async () => {
    if (!walletAddress) return
    const executorData = await fetchExecutor(walletAddress)
    setExecutor(executorData)
  }, [walletAddress, fetchExecutor])

  // --------------------------------------------------------------------------
  // Logout
  // --------------------------------------------------------------------------
  const logout = useCallback(async () => {
    await handleLogOut()
    setExecutor(null)
    setUserType(null)
    localStorage.removeItem('em_last_wallet_address')
  }, [handleLogOut, setUserType])

  // --------------------------------------------------------------------------
  // Open auth modal
  // --------------------------------------------------------------------------
  const openAuthModal = useCallback(() => {
    setShowAuthFlow(true)
  }, [setShowAuthFlow])

  // --------------------------------------------------------------------------
  // Effect: Fetch executor when wallet changes
  // --------------------------------------------------------------------------
  useEffect(() => {
    if (walletAddress) {
      localStorage.setItem('em_last_wallet_address', walletAddress)
      setLoading(true)
      fetchExecutor(walletAddress).then((data) => {
        setExecutor(data)
        setLoading(false)
      })
    } else {
      setExecutor(null)
      setLoading(false)
    }
  }, [walletAddress, fetchExecutor])

  // --------------------------------------------------------------------------
  // Context Value
  // --------------------------------------------------------------------------
  const value: AuthContextValue = {
    walletAddress,
    executor,
    userType,
    isAuthenticated,
    isProfileComplete,
    loading,
    error,
    logout,
    setUserType,
    refreshExecutor,
    openAuthModal,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// --------------------------------------------------------------------------
// Hook
// --------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return context
}
