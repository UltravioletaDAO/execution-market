/**
 * useWalletAuth - Hook for wallet-based authentication
 *
 * Combines Wagmi wallet connection with Supabase authentication.
 * Supports MetaMask, WalletConnect, and manual wallet entry.
 */

import { useCallback, useState, useEffect } from 'react'
import { useAccount, useConnect, useDisconnect, useSignMessage } from 'wagmi'
import { supabase } from '../lib/supabase'

interface UseWalletAuthOptions {
  onSuccess?: () => void
  onError?: (error: Error) => void
}

interface WalletAuthState {
  isConnecting: boolean
  isConnected: boolean
  address: string | undefined
  error: string | null
}

export function useWalletAuth(options: UseWalletAuthOptions = {}) {
  const { onSuccess, onError } = options

  const { address, isConnected } = useAccount()
  const { connectors, connect, isPending: isConnectPending, error: connectError } = useConnect()
  const { disconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()

  const [state, setState] = useState<WalletAuthState>({
    isConnecting: false,
    isConnected: false,
    address: undefined,
    error: null,
  })

  // Update state when Wagmi connection changes
  useEffect(() => {
    setState(prev => ({
      ...prev,
      isConnected,
      address: address?.toLowerCase(),
    }))
  }, [address, isConnected])

  // Handle connect errors
  useEffect(() => {
    if (connectError) {
      setState(prev => ({
        ...prev,
        error: connectError.message,
        isConnecting: false,
      }))
      onError?.(connectError)
    }
  }, [connectError, onError])

  /**
   * Connect using a specific connector (MetaMask, WalletConnect, etc.)
   */
  const connectWallet = useCallback(async (connectorId?: string) => {
    setState(prev => ({ ...prev, isConnecting: true, error: null }))

    try {
      // Find the connector
      const connector = connectorId
        ? connectors.find(c => c.id === connectorId)
        : connectors.find(c => c.id === 'injected') // Default to injected (MetaMask)

      if (!connector) {
        throw new Error('Connector not found')
      }

      // Connect wallet
      connect({ connector })
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to connect wallet')
      setState(prev => ({ ...prev, error: error.message, isConnecting: false }))
      onError?.(error)
    }
  }, [connectors, connect, onError])

  /**
   * Authenticate with Supabase after wallet is connected
   */
  const authenticateWithSupabase = useCallback(async (
    walletAddress: string,
    displayName?: string
  ) => {
    setState(prev => ({ ...prev, isConnecting: true, error: null }))

    const normalizedWallet = walletAddress.toLowerCase()

    try {
      // Check if wallet already exists
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

      const checkResponse = await fetch(
        `${supabaseUrl}/rest/v1/executors?wallet_address=eq.${normalizedWallet}&select=id,display_name`,
        { headers: { 'apikey': supabaseKey } }
      )
      const existingExecutors = await checkResponse.json()
      const isReturningUser = existingExecutors && existingExecutors.length > 0

      // Sign in anonymously to create session
      const { data: authData, error: authError } = await supabase.auth.signInAnonymously()
      if (authError) throw authError
      if (!authData.user) throw new Error('Failed to create session')

      if (isReturningUser) {
        // Returning user - link wallet to session
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: linkError } = await (supabase.rpc as any)(
          'link_wallet_to_session',
          {
            p_user_id: authData.user.id,
            p_wallet_address: normalizedWallet,
          }
        )
        if (linkError) {
          console.error('[WalletAuth] link_wallet_to_session error:', linkError)
          console.error('[WalletAuth] link_wallet_to_session details:', {
            code: (linkError as { code?: string }).code,
            message: (linkError as { message?: string }).message,
            details: (linkError as { details?: string }).details,
            hint: (linkError as { hint?: string }).hint,
          })
          // Fallback to get_or_create_executor (also links user_id)
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const { error: rpcError } = await (supabase.rpc as any)(
            'get_or_create_executor',
            {
              p_wallet_address: normalizedWallet,
              p_display_name: displayName || null,
            }
          )
          if (rpcError) {
            console.error('[WalletAuth] get_or_create_executor fallback error:', rpcError)
            console.error('[WalletAuth] get_or_create_executor fallback details:', {
              code: (rpcError as { code?: string }).code,
              message: (rpcError as { message?: string }).message,
              details: (rpcError as { details?: string }).details,
              hint: (rpcError as { hint?: string }).hint,
            })
            throw new Error('Failed to link wallet to session')
          }
        }
      } else {
        // New user - create executor profile
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: rpcError } = await (supabase.rpc as any)(
          'get_or_create_executor',
          {
            p_wallet_address: normalizedWallet,
            p_display_name: displayName || null,
          }
        )
        if (rpcError) throw rpcError
      }

      setState(prev => ({ ...prev, isConnecting: false }))
      onSuccess?.()
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Authentication failed')
      setState(prev => ({ ...prev, error: error.message, isConnecting: false }))
      onError?.(error)
      throw error
    }
  }, [onSuccess, onError])

  /**
   * Full connect + authenticate flow
   */
  const connectAndAuthenticate = useCallback(async (
    connectorId?: string,
    displayName?: string
  ) => {
    setState(prev => ({ ...prev, isConnecting: true, error: null }))

    try {
      // If not connected, connect first
      if (!isConnected) {
        const connector = connectorId
          ? connectors.find(c => c.id === connectorId)
          : connectors.find(c => c.id === 'injected')

        if (!connector) {
          throw new Error('Connector not found')
        }

        // Connect and wait for address
        connect({ connector })
        // Note: We'll need to handle the auth in useEffect when address becomes available
        // Store display name in state for later use
        localStorage.setItem('pendingAuthDisplayName', displayName || '')
        return
      }

      // Already connected, authenticate directly
      if (address) {
        await authenticateWithSupabase(address, displayName)
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to connect')
      setState(prev => ({ ...prev, error: error.message, isConnecting: false }))
      onError?.(error)
    }
  }, [isConnected, address, connectors, connect, authenticateWithSupabase, onError])

  // Handle pending authentication after wallet connects
  useEffect(() => {
    const pendingDisplayName = localStorage.getItem('pendingAuthDisplayName')
    if (isConnected && address && pendingDisplayName !== null) {
      localStorage.removeItem('pendingAuthDisplayName')
      authenticateWithSupabase(address, pendingDisplayName || undefined)
        .catch(console.error)
    }
  }, [isConnected, address, authenticateWithSupabase])

  /**
   * Sign a message to verify ownership (optional, for additional security)
   */
  const signVerificationMessage = useCallback(async () => {
    if (!address) throw new Error('No wallet connected')

    const message = `Sign this message to verify your ownership of ${address}\n\nTimestamp: ${Date.now()}`
    const signature = await signMessageAsync({ message })

    return { message, signature }
  }, [address, signMessageAsync])

  /**
   * Disconnect wallet
   */
  const disconnectWallet = useCallback(() => {
    disconnect()
    setState({
      isConnecting: false,
      isConnected: false,
      address: undefined,
      error: null,
    })
  }, [disconnect])

  return {
    // State
    ...state,
    isConnectPending,

    // Available connectors
    connectors,

    // Actions
    connectWallet,
    connectAndAuthenticate,
    authenticateWithSupabase,
    signVerificationMessage,
    disconnectWallet,

    // Clear error
    clearError: () => setState(prev => ({ ...prev, error: null })),
  }
}

export type { WalletAuthState }
