// Execution Market: Authentication Context
// Provides authentication state and user type management across the application

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import { supabase } from '../lib/supabase'
import type { Executor } from '../types/database'
import type { User, Session } from '@supabase/supabase-js'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

export type UserType = 'worker' | 'agent' | null

interface AuthContextValue {
  // State
  user: User | null
  session: Session | null
  executor: Executor | null
  userType: UserType
  isAuthenticated: boolean
  isProfileComplete: boolean
  loading: boolean
  error: Error | null

  // Actions
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  signUp: (email: string, password: string, walletAddress: string, type?: UserType) => Promise<void>
  setUserType: (type: UserType) => void
  refreshExecutor: () => Promise<void>
  reloadSession: () => Promise<void>
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
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [executor, setExecutor] = useState<Executor | null>(null)
  const [userType, setUserTypeState] = useState<UserType>(() => {
    // Initialize from localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(USER_TYPE_STORAGE_KEY)
      if (stored === 'worker' || stored === 'agent') {
        return stored
      }
    }
    return null
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // Derived state
  const isAuthenticated = user !== null && session !== null
  const isProfileComplete = !!executor?.display_name

  // --------------------------------------------------------------------------
  // Direct fetch to bypass Supabase JS client issues with sb_publishable_ keys
  // --------------------------------------------------------------------------
  const fetchExecutorDirect = useCallback(
    async (userId: string, accessToken?: string): Promise<Executor | null> => {
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

      const headers: Record<string, string> = {
        apikey: supabaseKey,
        'Content-Type': 'application/json',
      }

      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`
      }

      // Retry up to 3 times with short delays to handle race conditions
      // after RPC calls (e.g. get_or_create_executor) that just created the row
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          console.log('[AuthContext] fetchExecutorDirect attempt', attempt + 1, 'for user:', userId)

          const response = await fetch(
            `${supabaseUrl}/rest/v1/executors?user_id=eq.${userId}&select=*`,
            { headers }
          )

          console.log('[AuthContext] fetchExecutorDirect response status:', response.status)

          if (!response.ok) {
            console.error(
              '[AuthContext] fetchExecutorDirect error:',
              response.status,
              response.statusText
            )
            return null
          }

          const data = await response.json()
          console.log('[AuthContext] fetchExecutorDirect got data:', data)

          if (data.length > 0) {
            return data[0]
          }

          // Row not found yet — wait before retrying
          if (attempt < 2) {
            await new Promise((r) => setTimeout(r, 500))
          }
        } catch (err) {
          console.error('[AuthContext] fetchExecutorDirect failed:', err)
          return null
        }
      }

      // Fallback: try by wallet_address from user metadata
      // This handles returning users whose executor has a stale user_id
      // (e.g. from a previous anonymous session that expired)
      try {
        const { data: { user: currentUser } } = await supabase.auth.getUser()
        const walletAddress = currentUser?.user_metadata?.wallet_address
        if (walletAddress) {
          console.log('[AuthContext] Fallback: trying by wallet_address:', walletAddress)
          const response = await fetch(
            `${supabaseUrl}/rest/v1/executors?wallet_address=eq.${walletAddress}&select=*`,
            { headers }
          )
          if (response.ok) {
            const data = await response.json()
            if (data.length > 0) {
              console.log('[AuthContext] Found executor by wallet_address fallback:', data[0].id)
              return data[0]
            }
          }
        }
      } catch (err) {
        console.error('[AuthContext] Wallet fallback failed:', err)
      }

      return null
    },
    []
  )

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
    console.log(
      '[AuthContext] refreshExecutor called, user:',
      user?.id ?? 'none',
      'session:',
      session?.access_token ? 'present' : 'none'
    )
    if (!user || !session) return

    console.log('[AuthContext] Fetching executor in refreshExecutor...')
    const executorData = await fetchExecutorDirect(user.id, session.access_token)
    console.log('[AuthContext] refreshExecutor got executor:', executorData?.id ?? 'none')
    setExecutor(executorData)
  }, [user, session, fetchExecutorDirect])

  // --------------------------------------------------------------------------
  // Reload session from Supabase
  // --------------------------------------------------------------------------
  const reloadSession = useCallback(async () => {
    console.log('[AuthContext] reloadSession called')
    const {
      data: { session: newSession },
    } = await supabase.auth.getSession()
    console.log('[AuthContext] reloadSession got session:', newSession?.user?.id ?? 'none')

    if (newSession?.user) {
      const executorData = await fetchExecutorDirect(
        newSession.user.id,
        newSession.access_token
      )
      console.log('[AuthContext] reloadSession got executor:', executorData?.id ?? 'none')
      setUser(newSession.user)
      setSession(newSession)
      setExecutor(executorData)
      setLoading(false)
      setError(null)
    } else {
      setUser(null)
      setSession(null)
      setExecutor(null)
      setLoading(false)
      setError(null)
    }
  }, [fetchExecutorDirect])

  // --------------------------------------------------------------------------
  // Initialize: Get session on mount and listen for auth changes
  // --------------------------------------------------------------------------
  useEffect(() => {
    console.log('[AuthContext] Getting initial session...')
    supabase.auth.getSession().then(async ({ data: { session: initialSession } }) => {
      console.log('[AuthContext] Initial session:', initialSession?.user?.id ?? 'none')
      let executorData: Executor | null = null

      if (initialSession?.user) {
        console.log('[AuthContext] Fetching executor for user:', initialSession.user.id)
        executorData = await fetchExecutorDirect(
          initialSession.user.id,
          initialSession.access_token
        )
        console.log('[AuthContext] Executor fetched:', executorData?.id ?? 'none')
      }

      setUser(initialSession?.user ?? null)
      setSession(initialSession)
      setExecutor(executorData)
      setLoading(false)
      console.log('[AuthContext] State updated with initial session')
    })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      console.log('[AuthContext] Auth state changed:', _event, newSession?.user?.id ?? 'none')
      let executorData: Executor | null = null

      if (newSession?.user) {
        console.log('[AuthContext] Fetching executor after auth change...')
        executorData = await fetchExecutorDirect(newSession.user.id, newSession.access_token)
        console.log('[AuthContext] Executor after auth change:', executorData?.id ?? 'none')
      } else {
        // Clear user type on logout
        setUserType(null)
      }

      setUser(newSession?.user ?? null)
      setSession(newSession)
      setExecutor(executorData)
      setLoading(false)
      console.log('[AuthContext] State updated after auth change')
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [fetchExecutorDirect, setUserType])

  // --------------------------------------------------------------------------
  // Login
  // --------------------------------------------------------------------------
  const login = useCallback(async (email: string, password: string) => {
    setLoading(true)
    setError(null)

    const { error: loginError } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (loginError) {
      setLoading(false)
      setError(loginError)
      throw loginError
    }
  }, [])

  // --------------------------------------------------------------------------
  // Sign Up
  // --------------------------------------------------------------------------
  const signUp = useCallback(
    async (
      email: string,
      password: string,
      walletAddress: string,
      type: UserType = 'worker'
    ) => {
      setLoading(true)
      setError(null)

      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
      })

      if (signUpError) {
        setLoading(false)
        setError(signUpError)
        throw signUpError
      }

      // Create executor profile
      if (data.user) {
        const { error: profileError } = await supabase.from('executors').insert({
          user_id: data.user.id,
          wallet_address: walletAddress,
        } as never)

        if (profileError) {
          console.error('[AuthContext] Failed to create executor profile:', profileError)
        }

        // Set user type
        setUserType(type)
      }
    },
    [setUserType]
  )

  // --------------------------------------------------------------------------
  // Logout
  // --------------------------------------------------------------------------
  const logout = useCallback(async () => {
    setLoading(true)
    const { error: logoutError } = await supabase.auth.signOut()

    if (logoutError) {
      setLoading(false)
      setError(logoutError)
      throw logoutError
    }

    // Clear user type
    setUserType(null)
  }, [setUserType])

  // --------------------------------------------------------------------------
  // Context Value
  // --------------------------------------------------------------------------
  const value: AuthContextValue = {
    user,
    session,
    executor,
    userType,
    isAuthenticated,
    isProfileComplete,
    loading,
    error,
    login,
    logout,
    signUp,
    setUserType,
    refreshExecutor,
    reloadSession,
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
