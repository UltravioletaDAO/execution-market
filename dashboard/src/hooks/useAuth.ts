// Execution Market: Auth and Executor Hooks
import { useEffect, useState, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import type { Executor } from '../types/database'
import type { User, Session } from '@supabase/supabase-js'

interface AuthState {
  user: User | null
  session: Session | null
  executor: Executor | null
  loading: boolean
  error: Error | null
}

interface UseAuthResult extends AuthState {
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, walletAddress: string) => Promise<void>
  signOut: () => Promise<void>
  refreshExecutor: () => Promise<void>
  reloadSession: () => Promise<void>
}

export function useAuth(): UseAuthResult {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    executor: null,
    loading: true,
    error: null,
  })

  // Direct fetch to bypass Supabase JS client which hangs with sb_publishable_ keys
  const fetchExecutorDirect = useCallback(async (userId: string, accessToken?: string): Promise<Executor | null> => {
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
    const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

    try {
      console.log('[useAuth] fetchExecutorDirect starting for user:', userId)
      const headers: Record<string, string> = {
        'apikey': supabaseKey,
        'Content-Type': 'application/json',
      }

      // Use access token if provided (for authenticated requests)
      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`
      }

      const response = await fetch(
        `${supabaseUrl}/rest/v1/executors?user_id=eq.${userId}&select=*`,
        { headers }
      )

      console.log('[useAuth] fetchExecutorDirect response status:', response.status)

      if (!response.ok) {
        console.error('[useAuth] fetchExecutorDirect error:', response.status, response.statusText)
        return null
      }

      const data = await response.json()
      console.log('[useAuth] fetchExecutorDirect got data:', data)

      // Return first result or null (maybeSingle equivalent)
      return data.length > 0 ? data[0] : null
    } catch (err) {
      console.error('[useAuth] fetchExecutorDirect failed:', err)
      return null
    }
  }, [])

  const fetchExecutor = useCallback(async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('executors')
        .select('*')
        .eq('user_id', userId)
        .maybeSingle()

      if (error) {
        throw error
      }

      return data
    } catch (err) {
      console.error('Failed to fetch executor:', err)
      return null
    }
  }, [])

  const refreshExecutor = useCallback(async () => {
    console.log('[useAuth] refreshExecutor called, user:', state.user?.id ?? 'none', 'session:', state.session?.access_token ? 'present' : 'none')
    if (!state.user || !state.session) return

    console.log('[useAuth] Fetching executor in refreshExecutor using direct fetch...')
    const executor = await fetchExecutorDirect(state.user.id, state.session.access_token)
    console.log('[useAuth] refreshExecutor got executor:', executor?.id ?? 'none')
    setState((prev) => ({ ...prev, executor }))
  }, [state.user, state.session, fetchExecutorDirect])

  // Reload session from Supabase - useful when state might be stale (e.g., after login errors)
  const reloadSession = useCallback(async () => {
    console.log('[useAuth] reloadSession called')
    const { data: { session } } = await supabase.auth.getSession()
    console.log('[useAuth] reloadSession got session:', session?.user?.id ?? 'none')

    if (session?.user) {
      const executor = await fetchExecutorDirect(session.user.id, session.access_token)
      console.log('[useAuth] reloadSession got executor:', executor?.id ?? 'none')
      setState({
        user: session.user,
        session,
        executor,
        loading: false,
        error: null,
      })
    } else {
      setState({
        user: null,
        session: null,
        executor: null,
        loading: false,
        error: null,
      })
    }
  }, [fetchExecutorDirect])

  useEffect(() => {
    // Get initial session
    console.log('[useAuth] Getting initial session...')
    supabase.auth.getSession().then(async ({ data: { session } }: { data: { session: { user: { id: string }; access_token: string } | null } }) => {
      console.log('[useAuth] Initial session:', session?.user?.id ?? 'none')
      let executor: Executor | null = null

      if (session?.user) {
        console.log('[useAuth] Fetching executor for user:', session.user.id)
        // Use direct fetch to bypass Supabase JS client which can hang with sb_publishable_ keys
        executor = await fetchExecutorDirect(session.user.id, session.access_token)
        console.log('[useAuth] Executor fetched:', executor?.id ?? 'none')
      }

      setState({
        user: session?.user ?? null,
        session,
        executor,
        loading: false,
        error: null,
      })
      console.log('[useAuth] State updated with session')
    })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event: string, session: { user: { id: string }; access_token: string } | null) => {
      console.log('[useAuth] Auth state changed:', _event, session?.user?.id ?? 'none')
      let executor: Executor | null = null

      if (session?.user) {
        console.log('[useAuth] Fetching executor after auth change using direct fetch...')
        // Use direct fetch to bypass Supabase JS client which hangs with sb_publishable_ keys
        executor = await fetchExecutorDirect(session.user.id, session.access_token)
        console.log('[useAuth] Executor after auth change:', executor?.id ?? 'none')
      }

      setState({
        user: session?.user ?? null,
        session,
        executor,
        loading: false,
        error: null,
      })
      console.log('[useAuth] State updated after auth change')
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [fetchExecutor, fetchExecutorDirect])

  const signIn = useCallback(async (email: string, password: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }))

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      setState((prev) => ({ ...prev, loading: false, error }))
      throw error
    }
  }, [])

  const signUp = useCallback(
    async (email: string, password: string, walletAddress: string) => {
      setState((prev) => ({ ...prev, loading: true, error: null }))

      const { data, error } = await supabase.auth.signUp({
        email,
        password,
      })

      if (error) {
        setState((prev) => ({ ...prev, loading: false, error }))
        throw error
      }

      // Create executor profile
      if (data.user) {
        const { error: profileError } = await supabase.from('executors').insert({
          user_id: data.user.id,
          wallet_address: walletAddress,
        } as never)

        if (profileError) {
          console.error('Failed to create executor profile:', profileError)
        }
      }
    },
    []
  )

  const signOut = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true }))
    const { error } = await supabase.auth.signOut()

    if (error) {
      setState((prev) => ({ ...prev, loading: false, error }))
      throw error
    }
  }, [])

  return {
    ...state,
    signIn,
    signUp,
    signOut,
    refreshExecutor,
    reloadSession,
  }
}

// Hook for fetching any executor by ID
export function useExecutor(executorId: string | undefined) {
  const [executor, setExecutor] = useState<Executor | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!executorId) {
      setExecutor(null)
      setLoading(false)
      return
    }

    const fetchExecutor = async () => {
      setLoading(true)
      setError(null)

      try {
        const { data, error: fetchError } = await supabase
          .from('executors')
          .select('*')
          .eq('id', executorId)
          .single()

        if (fetchError) throw fetchError
        setExecutor(data)
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch executor'))
      } finally {
        setLoading(false)
      }
    }

    fetchExecutor()
  }, [executorId])

  return { executor, loading, error }
}
