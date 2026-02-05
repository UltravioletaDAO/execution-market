import { useState, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import { useAuth } from '../context/AuthContext'

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
  const { executor, walletAddress, refreshExecutor } = useAuth()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateProfile = useCallback(
    async (data: ProfileUpdateData) => {
      setSaving(true)
      setError(null)

      try {
        // With Dynamic.xyz auth, we use the executor from context (loaded via wallet address)
        // No Supabase session exists - auth is wallet-based
        const executorId = executor?.id

        if (!executorId) {
          console.error('[useProfileUpdate] No executor in context')

          // If executor not in context but we have wallet, try to find by wallet
          if (walletAddress) {
            console.log('[useProfileUpdate] Trying wallet lookup:', walletAddress)
            const { data: execData, error: findError } = await supabase
              .from('executors')
              .select('id')
              .eq('wallet_address', walletAddress.toLowerCase())
              .single()

            if (findError || !execData) {
              setError('Executor not found. Please reconnect your wallet.')
              return false
            }

            // Found executor by wallet, use RPC to update
            const { error: updateError } = await supabase.rpc('update_executor_profile', {
              p_executor_id: execData.id,
              p_display_name: data.display_name,
              p_bio: data.bio,
              p_skills: data.skills,
              p_languages: data.languages,
              p_location_city: data.location_city || null,
              p_location_country: data.location_country || null,
              p_email: data.email || null,
            })

            if (updateError) {
              console.error('[useProfileUpdate] RPC update failed:', updateError)
              throw new Error(updateError.message)
            }

            await refreshExecutor()
            return true
          }

          setError('Not authenticated. Please connect your wallet.')
          return false
        }

        // Use RPC function to update profile (bypasses RLS)
        const { error: updateError } = await supabase.rpc('update_executor_profile', {
          p_executor_id: executorId,
          p_display_name: data.display_name,
          p_bio: data.bio,
          p_skills: data.skills,
          p_languages: data.languages,
          p_location_city: data.location_city || null,
          p_location_country: data.location_country || null,
          p_email: data.email || null,
        })

        if (updateError) {
          console.error('[useProfileUpdate] RPC update failed:', updateError)
          throw new Error(updateError.message)
        }

        console.log('[useProfileUpdate] Profile updated successfully')
        await refreshExecutor()
        return true
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update profile'
        console.error('[useProfileUpdate] Error:', message)
        setError(message)
        return false
      } finally {
        setSaving(false)
      }
    },
    [executor, walletAddress, refreshExecutor]
  )

  return { updateProfile, saving, error }
}
