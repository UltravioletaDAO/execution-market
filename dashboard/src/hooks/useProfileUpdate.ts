import { useState, useCallback } from 'react'
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
  const { executor, session, refreshExecutor } = useAuth()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateProfile = useCallback(
    async (data: ProfileUpdateData) => {
      if (!executor || !session) {
        setError('Not authenticated')
        return false
      }

      setSaving(true)
      setError(null)

      try {
        const headers: Record<string, string> = {
          apikey: SUPABASE_KEY,
          'Content-Type': 'application/json',
          Prefer: 'return=minimal',
        }

        if (session.access_token) {
          headers['Authorization'] = `Bearer ${session.access_token}`
        }

        const response = await fetch(
          `${SUPABASE_URL}/rest/v1/executors?id=eq.${executor.id}`,
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
    [executor, session, refreshExecutor]
  )

  return { updateProfile, saving, error }
}
