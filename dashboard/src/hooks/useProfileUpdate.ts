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
  phone: string | null
  avatar_url?: string | null
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
        // If missing, attempt to create or lookup by wallet
        let executorId = executor?.id

        if (!executorId) {
          console.error('[useProfileUpdate] No executor in context')

          // If executor not in context but we have wallet, try to find by wallet
          if (walletAddress) {
            console.log('[useProfileUpdate] Trying wallet lookup:', walletAddress)
            const { data: execData, error: findError } = await supabase
              .from('executors')
              .select('id')
              .eq('wallet_address', walletAddress.toLowerCase())
              .maybeSingle()

            if (findError) {
              console.error('[useProfileUpdate] Wallet lookup error:', findError)
            }

            if (!execData && walletAddress) {
              // Try to create executor if missing (RPC)
              const { data: created, error: createError } = await supabase.rpc('get_or_create_executor', {
                p_wallet_address: walletAddress.toLowerCase(),
                p_display_name: data.display_name || null,
                p_email: data.email || null,
              })

              if (createError) {
                console.error('[useProfileUpdate] get_or_create_executor failed:', createError)
              } else {
                const createdExecutor = Array.isArray(created) ? created[0] : created
                if (createdExecutor?.id) {
                  executorId = createdExecutor.id
                }
              }
            } else if (execData?.id) {
              executorId = execData.id
            }
          }

          if (!executorId) {
            setError('Executor not found. Please reconnect your wallet.')
            return false
          }
        }

        const updatePayload = {
          p_executor_id: executorId,
          p_display_name: data.display_name,
          p_bio: data.bio,
          p_skills: data.skills,
          p_languages: data.languages,
          p_location_city: data.location_city || null,
          p_location_country: data.location_country || null,
          p_email: data.email || null,
          p_avatar_url: data.avatar_url || null,
          p_phone: data.phone || null,
        }

        // Use RPC function to update profile (bypasses RLS)
        const { error: updateError } = await supabase.rpc('update_executor_profile', updatePayload)

        if (updateError) {
          console.error('[useProfileUpdate] RPC update failed:', updateError)

          // Fallback to direct update when RPC is missing
          if (updateError.code?.startsWith('PGRST') || updateError.message?.includes('update_executor_profile')) {
            const updateFields: Record<string, unknown> = {
                display_name: data.display_name,
                bio: data.bio,
                skills: data.skills,
                languages: data.languages,
                location_city: data.location_city || null,
                location_country: data.location_country || null,
                email: data.email || null,
                phone: data.phone || null,
                avatar_url: data.avatar_url || null,
            }
            const { error: directError } = await supabase
              .from('executors')
              .update(updateFields)
              .eq('id', executorId)

            if (directError) {
              console.error('[useProfileUpdate] Direct update failed:', directError)
              throw new Error(directError.message)
            }
          } else {
            throw new Error(updateError.message)
          }
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
