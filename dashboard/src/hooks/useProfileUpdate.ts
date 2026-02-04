import { useState, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import { useAuth } from '../context/AuthContext'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

export interface ProfileUpdateData {
  display_name: string
  bio: string
  skills: string[]
  languages: string[]
  location_city: string
  location_country: string
  email: string | null
}

export function useProfileUpdate() {
  const { executor, refreshExecutor } = useAuth()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateProfile = useCallback(
    async (data: ProfileUpdateData) => {
      setSaving(true)
      setError(null)

      try {
        // Get fresh session directly from Supabase (not React state)
        const { data: { session: currentSession } } = await supabase.auth.getSession()

        if (!currentSession?.user) {
          setError('Not authenticated')
          return false
        }

        const headers: Record<string, string> = {
          apikey: SUPABASE_KEY,
          'Content-Type': 'application/json',
          Prefer: 'return=minimal',
        }

        if (currentSession.access_token) {
          headers['Authorization'] = `Bearer ${currentSession.access_token}`
        }

        // Resolve executor ID: try context first, then query by user_id,
        // then fallback to wallet_address from user metadata.
        // This handles race conditions where onAuthStateChange set executor=null
        // before the RPC call created the executor row.
        let executorId = executor?.id

        if (!executorId) {
          console.log('[useProfileUpdate] executor is null in context, looking up by user_id...')
          const findResponse = await fetch(
            `${SUPABASE_URL}/rest/v1/executors?user_id=eq.${currentSession.user.id}&select=id`,
            { headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${currentSession.access_token}` } }
          )
          if (findResponse.ok) {
            const found = await findResponse.json()
            if (found.length > 0) {
              executorId = found[0].id
              console.log('[useProfileUpdate] found executor by user_id:', executorId)
            }
          }
        }

        if (!executorId) {
          const wallet = currentSession.user.user_metadata?.wallet_address
          if (wallet) {
            console.log('[useProfileUpdate] trying wallet_address fallback:', wallet)
            const walletResponse = await fetch(
              `${SUPABASE_URL}/rest/v1/executors?wallet_address=eq.${wallet}&select=id`,
              { headers: { apikey: SUPABASE_KEY } }
            )
            if (walletResponse.ok) {
              const walletData = await walletResponse.json()
              if (walletData.length > 0) {
                executorId = walletData[0].id
                console.log('[useProfileUpdate] found executor by wallet:', executorId)
              }
            }
          }
        }

        if (!executorId) {
          setError('Not authenticated')
          return false
        }

        const response = await fetch(
          `${SUPABASE_URL}/rest/v1/executors?id=eq.${executorId}`,
          {
            method: 'PATCH',
            headers,
            body: JSON.stringify({
              display_name: data.display_name,
              bio: data.bio,
              skills: data.skills,
              languages: data.languages,
              location_city: data.location_city || null,
              location_country: data.location_country || null,
              email: data.email || null,
              updated_at: new Date().toISOString(),
            }),
          }
        )

        if (!response.ok) {
          const text = await response.text()
          throw new Error(text || `Update failed: ${response.status}`)
        }

        await refreshExecutor()
        return true
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update profile'
        setError(message)
        return false
      } finally {
        setSaving(false)
      }
    },
    [executor, refreshExecutor]
  )

  return { updateProfile, saving, error }
}
