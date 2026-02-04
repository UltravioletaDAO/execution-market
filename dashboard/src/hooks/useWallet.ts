/**
 * Unified Wallet Hook (NOW-041 to NOW-044)
 *
 * Provides a unified interface for multiple wallet providers:
 * - Wagmi (MetaMask, WalletConnect)
 * - Crossmint (email wallets)
 * - Magic.link (fallback email/social auth)
 */

import { useCallback, useState, useEffect, useRef } from 'react'
import { useAccount, useConnect, useDisconnect, useSignMessage } from 'wagmi'
import { supabase } from '../lib/supabase'

// =============================================================================
// Types
// =============================================================================

export type WalletType = 'metamask' | 'walletconnect' | 'crossmint' | 'magic'

export type ConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'authenticating'
  | 'authenticated'
  | 'error'

export interface WalletError {
  code: string
  message: string
  provider?: WalletType
}

export interface WalletState {
  // Connection state
  address: string | undefined
  isConnected: boolean
  isConnecting: boolean
  isAuthenticated: boolean
  signing: boolean
  status: ConnectionStatus
  walletType: WalletType | null

  // User info (from email wallets)
  email: string | undefined

  // Error handling
  error: WalletError | null

  // Actions
  connect: (type: WalletType, options?: ConnectOptions) => Promise<void>
  disconnect: () => Promise<void>
  signMessage: (message: string) => Promise<string>
  clearError: () => void
}

export interface ConnectOptions {
  email?: string
  displayName?: string
}

// =============================================================================
// Crossmint Integration
// =============================================================================

interface CrossmintWallet {
  address: string
  email: string
}

class CrossmintProvider {
  private apiKey: string
  private baseUrl: string

  constructor() {
    this.apiKey = import.meta.env.VITE_CROSSMINT_API_KEY || ''
    this.baseUrl = import.meta.env.VITE_CROSSMINT_API_URL || 'https://www.crossmint.com/api/v1-alpha2'
  }

  isConfigured(): boolean {
    return Boolean(this.apiKey)
  }

  async createOrGetWallet(email: string): Promise<CrossmintWallet> {
    if (!this.isConfigured()) {
      throw new Error('Crossmint API key not configured')
    }

    try {
      // Create or retrieve wallet for email
      const response = await fetch(`${this.baseUrl}/wallets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-KEY': this.apiKey,
        },
        body: JSON.stringify({
          email,
          chain: 'base', // Default to Base for Execution Market
        }),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.message || `Crossmint API error: ${response.status}`)
      }

      const data = await response.json()
      return {
        address: data.publicKey || data.address,
        email,
      }
    } catch (err) {
      if (err instanceof Error) {
        throw err
      }
      throw new Error('Failed to create Crossmint wallet')
    }
  }

  async getWallet(email: string): Promise<CrossmintWallet | null> {
    if (!this.isConfigured()) {
      return null
    }

    try {
      const response = await fetch(
        `${this.baseUrl}/wallets?email=${encodeURIComponent(email)}`,
        {
          headers: {
            'X-API-KEY': this.apiKey,
          },
        }
      )

      if (!response.ok) {
        return null
      }

      const data = await response.json()
      if (data.length === 0) {
        return null
      }

      return {
        address: data[0].publicKey || data[0].address,
        email,
      }
    } catch {
      return null
    }
  }
}

// =============================================================================
// Magic.link Integration
// =============================================================================

interface MagicUser {
  address: string
  email: string
}

class MagicProvider {
  private apiKey: string
  private magic: unknown | null = null

  constructor() {
    this.apiKey = import.meta.env.VITE_MAGIC_API_KEY || ''
  }

  isConfigured(): boolean {
    return Boolean(this.apiKey)
  }

  private async getMagicInstance(): Promise<unknown> {
    if (this.magic) {
      return this.magic
    }

    if (!this.isConfigured()) {
      throw new Error('Magic API key not configured')
    }

    // Magic SDK disabled for initial build - will be enabled later
    // To enable: npm install magic-sdk and uncomment below
    throw new Error('Magic.link integration not available in this build')

    // Uncomment when magic-sdk is installed:
    // try {
    //   const { Magic } = await import('magic-sdk')
    //   this.magic = new Magic(this.apiKey, {
    //     network: {
    //       rpcUrl: import.meta.env.VITE_RPC_URL || 'https://mainnet.base.org',
    //       chainId: 8453, // Base mainnet
    //     },
    //   })
    //   return this.magic
    // } catch {
    //   throw new Error('Failed to load Magic SDK')
    // }
  }

  async loginWithEmail(email: string): Promise<MagicUser> {
    const magic = await this.getMagicInstance() as {
      auth: { loginWithMagicLink: (opts: { email: string }) => Promise<string> }
      user: { getInfo: () => Promise<{ publicAddress: string; email: string }> }
    }

    try {
      await magic.auth.loginWithMagicLink({ email })
      const userInfo = await magic.user.getInfo()

      return {
        address: userInfo.publicAddress,
        email: userInfo.email,
      }
    } catch (err) {
      if (err instanceof Error) {
        throw err
      }
      throw new Error('Magic login failed')
    }
  }

  async logout(): Promise<void> {
    if (!this.magic) return

    const magic = this.magic as {
      user: { logout: () => Promise<void> }
    }
    await magic.user.logout()
  }

  async isLoggedIn(): Promise<boolean> {
    if (!this.magic) return false

    const magic = this.magic as {
      user: { isLoggedIn: () => Promise<boolean> }
    }
    return magic.user.isLoggedIn()
  }
}

// =============================================================================
// Hook Implementation
// =============================================================================

const crossmintProvider = new CrossmintProvider()
const magicProvider = new MagicProvider()

export function useWallet(): WalletState {
  // Wagmi hooks
  const { address: wagmiAddress, isConnected: wagmiConnected } = useAccount()
  const { connectors, connect: wagmiConnect, isPending: wagmiPending } = useConnect()
  const { disconnect: wagmiDisconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()

  // Local state
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [walletType, setWalletType] = useState<WalletType | null>(null)
  const [address, setAddress] = useState<string | undefined>()
  const [email, setEmail] = useState<string | undefined>()
  const [error, setError] = useState<WalletError | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [signing, setSigning] = useState(false)

  // Prevent duplicate auth calls
  const authInProgress = useRef(false)
  const lastAuthAddress = useRef<string | null>(null)

  // Computed state
  const isConnected = status === 'connected' || status === 'authenticated' || status === 'authenticating'
  const isConnecting = status === 'connecting' || status === 'authenticating'

  // ==========================================================================
  // Sync Wagmi state
  // ==========================================================================

  useEffect(() => {
    if (wagmiConnected && wagmiAddress && walletType && ['metamask', 'walletconnect'].includes(walletType)) {
      setAddress(wagmiAddress.toLowerCase())
      if (status === 'connecting') {
        setStatus('connected')
      }
    }
  }, [wagmiConnected, wagmiAddress, walletType, status])

  // ==========================================================================
  // Supabase Authentication
  // ==========================================================================

  const authenticateWithSupabase = useCallback(async (
    walletAddress: string,
    displayName?: string,
    authWalletType?: WalletType
  ): Promise<void> => {
    // Prevent duplicate auth calls
    if (authInProgress.current || lastAuthAddress.current === walletAddress) {
      return
    }

    authInProgress.current = true
    const normalizedWallet = walletAddress.toLowerCase()

    try {
      setStatus('authenticating')

      // Require signature to prove wallet ownership for browser wallets
      const requiresSignature = authWalletType === 'metamask' || authWalletType === 'walletconnect'
      let signature: string | undefined
      let verificationMessage: string | undefined

      if (requiresSignature) {
        setSigning(true)
        const timestamp = Date.now()
        const nonce = Math.random().toString(36).substring(2, 10)
        verificationMessage = `Sign this message to verify you own this wallet and log in to Execution Market.\n\nWallet: ${normalizedWallet}\nTimestamp: ${timestamp}\nNonce: ${nonce}`

        try {
          signature = await signMessageAsync({ message: verificationMessage })
        } catch (signError) {
          setSigning(false)
          throw new Error('Wallet signature required to continue. Please sign the message in your wallet.')
        }
        setSigning(false)
      }

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
            p_wallet_address: normalizedWallet,
            ...(signature && verificationMessage ? {
              p_signature: signature,
              p_message: verificationMessage,
            } : {}),
          }
        )
        if (linkError) throw new Error('Failed to link wallet to session')
      } else {
        // New user - create executor profile
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: rpcError } = await (supabase.rpc as any)(
          'get_or_create_executor',
          {
            p_wallet_address: normalizedWallet,
            p_display_name: displayName || null,
            ...(signature && verificationMessage ? {
              p_signature: signature,
              p_message: verificationMessage,
            } : {}),
          }
        )
        if (rpcError) throw rpcError
      }

      lastAuthAddress.current = normalizedWallet
      setIsAuthenticated(true)
      setStatus('authenticated')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Authentication failed'
      setError({ code: 'AUTH_FAILED', message })
      setStatus('error')
      throw err
    } finally {
      authInProgress.current = false
    }
  }, [signMessageAsync])

  // ==========================================================================
  // Connect function
  // ==========================================================================

  const connect = useCallback(async (
    type: WalletType,
    options: ConnectOptions = {}
  ): Promise<void> => {
    const { email: userEmail, displayName } = options

    setError(null)
    setStatus('connecting')
    setWalletType(type)

    try {
      switch (type) {
        case 'metamask': {
          const injectedConnector = connectors.find(c => c.id === 'injected')
          if (!injectedConnector) {
            throw new Error('MetaMask not available')
          }
          wagmiConnect({ connector: injectedConnector })
          // Auth will happen in useEffect when wagmiAddress updates
          localStorage.setItem('pendingAuthDisplayName', displayName || '')
          break
        }

        case 'walletconnect': {
          const wcConnector = connectors.find(c => c.id === 'walletConnect')
          if (!wcConnector) {
            throw new Error('WalletConnect not available')
          }
          wagmiConnect({ connector: wcConnector })
          localStorage.setItem('pendingAuthDisplayName', displayName || '')
          break
        }

        case 'crossmint': {
          if (!userEmail) {
            throw new Error('Email required for Crossmint wallet')
          }

          if (!crossmintProvider.isConfigured()) {
            throw new Error('Crossmint not configured')
          }

          const wallet = await crossmintProvider.createOrGetWallet(userEmail)
          setAddress(wallet.address.toLowerCase())
          setEmail(wallet.email)
          setStatus('connected')

          // Authenticate with Supabase (no signature needed for email wallets)
          await authenticateWithSupabase(wallet.address, displayName || userEmail.split('@')[0], 'crossmint')
          break
        }

        case 'magic': {
          if (!userEmail) {
            throw new Error('Email required for Magic wallet')
          }

          if (!magicProvider.isConfigured()) {
            throw new Error('Magic.link not configured')
          }

          const user = await magicProvider.loginWithEmail(userEmail)
          setAddress(user.address.toLowerCase())
          setEmail(user.email)
          setStatus('connected')

          // Authenticate with Supabase (no signature needed for email wallets)
          await authenticateWithSupabase(user.address, displayName || userEmail.split('@')[0], 'magic')
          break
        }

        default:
          throw new Error(`Unknown wallet type: ${type}`)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Connection failed'
      setError({ code: 'CONNECT_FAILED', message, provider: type })
      setStatus('error')
      setWalletType(null)
      throw err
    }
  }, [connectors, wagmiConnect, authenticateWithSupabase])

  // ==========================================================================
  // Handle pending auth after Wagmi connection
  // ==========================================================================

  useEffect(() => {
    const pendingDisplayName = localStorage.getItem('pendingAuthDisplayName')
    if (
      wagmiConnected &&
      wagmiAddress &&
      pendingDisplayName !== null &&
      walletType &&
      ['metamask', 'walletconnect'].includes(walletType)
    ) {
      localStorage.removeItem('pendingAuthDisplayName')
      authenticateWithSupabase(wagmiAddress, pendingDisplayName || undefined, walletType)
        .catch((err) => {
          console.error('Auth failed:', err)
        })
    }
  }, [wagmiConnected, wagmiAddress, walletType, authenticateWithSupabase])

  // ==========================================================================
  // Disconnect function
  // ==========================================================================

  const disconnect = useCallback(async (): Promise<void> => {
    try {
      // Disconnect based on wallet type
      if (walletType === 'metamask' || walletType === 'walletconnect') {
        wagmiDisconnect()
      } else if (walletType === 'magic') {
        await magicProvider.logout()
      }
      // Crossmint doesn't have a logout concept

      // Sign out from Supabase
      await supabase.auth.signOut()

      // Reset state
      setStatus('disconnected')
      setWalletType(null)
      setAddress(undefined)
      setEmail(undefined)
      setIsAuthenticated(false)
      setError(null)
      authInProgress.current = false
      lastAuthAddress.current = null
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Disconnect failed'
      setError({ code: 'DISCONNECT_FAILED', message })
    }
  }, [walletType, wagmiDisconnect])

  // ==========================================================================
  // Sign message function
  // ==========================================================================

  const signMessage = useCallback(async (message: string): Promise<string> => {
    if (!address) {
      throw new Error('No wallet connected')
    }

    if (walletType === 'metamask' || walletType === 'walletconnect') {
      return signMessageAsync({ message })
    }

    // Email wallets don't support signing in the same way
    throw new Error('Message signing not supported for email wallets')
  }, [address, walletType, signMessageAsync])

  // ==========================================================================
  // Clear error function
  // ==========================================================================

  const clearError = useCallback(() => {
    setError(null)
    if (status === 'error') {
      setStatus('disconnected')
    }
  }, [status])

  // ==========================================================================
  // Return state
  // ==========================================================================

  return {
    // Connection state
    address,
    isConnected,
    isConnecting: isConnecting || wagmiPending,
    isAuthenticated,
    signing,
    status,
    walletType,

    // User info
    email,

    // Error handling
    error,

    // Actions
    connect,
    disconnect,
    signMessage,
    clearError,
  }
}

// =============================================================================
// Provider availability helpers
// =============================================================================

export function isCrossmintAvailable(): boolean {
  return crossmintProvider.isConfigured()
}

export function isMagicAvailable(): boolean {
  return magicProvider.isConfigured()
}

export function getAvailableWalletTypes(): WalletType[] {
  const types: WalletType[] = ['metamask', 'walletconnect']

  if (isCrossmintAvailable()) {
    types.push('crossmint')
  }

  if (isMagicAvailable()) {
    types.push('magic')
  }

  return types
}
