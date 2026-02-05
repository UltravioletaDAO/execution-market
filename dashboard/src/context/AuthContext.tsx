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
  const [dynamicInitialized, setDynamicInitialized] = useState(false)

  // Derived state
  const walletAddress = primaryWallet?.address?.toLowerCase() || null
  // Only consider authenticated once Dynamic has had a chance to restore session
  const isAuthenticated = dynamicInitialized && isLoggedIn && !!walletAddress
  const isProfileComplete = !!executor?.display_name

  // --------------------------------------------------------------------------
  // Fetch or create executor using RPC function (bypasses RLS)
  // --------------------------------------------------------------------------
  const fetchExecutor = useCallback(async (wallet: string): Promise<Executor | null> => {
    const normalizedWallet = wallet.toLowerCase()

    try {
      // Use RPC function that bypasses RLS to get or create executor
      const { data, error } = await supabase.rpc('get_or_create_executor', {
        p_wallet_address: normalizedWallet,
        p_display_name: null,
        p_email: null,
        p_signature: null,
        p_message: null,
      })

      if (error) {
        console.error('[Auth] get_or_create_executor error:', error)
        return null
      }

      // RPC returns an array, get first element
      const executorData = Array.isArray(data) ? data[0] : data
      if (!executorData) {
        console.error('[Auth] No executor data returned')
        return null
      }

      console.log('[Auth] Executor loaded:', executorData.id, 'isNew:', executorData.is_new)

      // Map RPC response to Executor type
      return {
        id: executorData.id,
        wallet_address: executorData.wallet_address,
        display_name: executorData.display_name,
        email: executorData.email,
        reputation_score: executorData.reputation_score,
        tier: executorData.tier,
        tasks_completed: executorData.tasks_completed,
        balance_usdc: executorData.balance_usdc,
        created_at: executorData.created_at,
        // Fill in optional fields with defaults
        bio: null,
        avatar_url: null,
        location_lat: null,
        location_lng: null,
        location_city: null,
        location_country: null,
        roles: [],
        status: 'active',
      } as Executor
    } catch (err) {
      console.error('[Auth] fetchExecutor exception:', err)
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
  // Effect: Track Dynamic.xyz initialization
  // Dynamic SDK restores session from localStorage on mount, we wait for it
  // --------------------------------------------------------------------------
  useEffect(() => {
    // Give Dynamic.xyz a moment to restore session from localStorage
    // If user has a session, primaryWallet will be set; if not, it stays undefined
    const timer = setTimeout(() => {
      setDynamicInitialized(true)
      console.log('[Auth] Dynamic initialized')
    }, 500) // 500ms should be enough for localStorage restore

    return () => clearTimeout(timer)
  }, []) // Only run once on mount

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
