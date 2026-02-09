/**
 * useX402Wallet - Wallet connection hook optimized for x402 payments
 *
 * Provides:
 * - Multi-wallet support via WalletConnect/wagmi
 * - Chain switching for supported networks
 * - Connection state management
 * - Account change handling
 */

import { useState, useCallback, useEffect } from 'react'
import {
  useAccount,
  useConnect,
  useDisconnect,
  useSwitchChain,
  useChainId,
  useSignMessage,
} from 'wagmi'
import { base, baseSepolia, polygon, optimism, arbitrum, mainnet } from 'wagmi/chains'
import type { Address } from 'viem'

// =============================================================================
// Constants
// =============================================================================

// Supported chains for x402 payments
export const SUPPORTED_CHAINS = {
  base: base,
  baseSepolia: baseSepolia,
  polygon: polygon,
  optimism: optimism,
  arbitrum: arbitrum,
  mainnet: mainnet,
} as const

export type SupportedChainName = keyof typeof SUPPORTED_CHAINS
export type SupportedChainId = (typeof SUPPORTED_CHAINS)[SupportedChainName]['id']

// Chain IDs map
export const CHAIN_IDS: Record<SupportedChainName, number> = {
  base: 8453,
  baseSepolia: 84532,
  polygon: 137,
  optimism: 10,
  arbitrum: 42161,
  mainnet: 1,
}

// Reverse lookup
export const CHAIN_NAMES: Record<number, SupportedChainName> = {
  8453: 'base',
  84532: 'baseSepolia',
  137: 'polygon',
  10: 'optimism',
  42161: 'arbitrum',
  1: 'mainnet',
}

// =============================================================================
// Types
// =============================================================================

export type ConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'switching_chain'
  | 'error'

export interface WalletInfo {
  address: Address | undefined
  chainId: number | undefined
  chainName: SupportedChainName | undefined
  isConnected: boolean
  isOnSupportedChain: boolean
}

export interface X402WalletError {
  code: string
  message: string
}

export interface UseX402WalletReturn {
  // State
  address: Address | undefined
  chainId: number | undefined
  chainName: SupportedChainName | undefined
  isConnected: boolean
  isConnecting: boolean
  status: ConnectionStatus
  isOnSupportedChain: boolean
  error: X402WalletError | null

  // Actions
  connect: (connectorId?: string) => Promise<void>
  disconnect: () => Promise<void>
  switchChain: (chainName: SupportedChainName) => Promise<void>
  signMessage: (message: string) => Promise<string>
  clearError: () => void

  // Utilities
  getWalletInfo: () => WalletInfo
  getSupportedChains: () => SupportedChainName[]
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useX402Wallet(): UseX402WalletReturn {
  // Wagmi hooks
  const { address, isConnected } = useAccount()
  const { connectors, connectAsync, isPending: isConnecting } = useConnect()
  const { disconnectAsync } = useDisconnect()
  const chainId = useChainId()
  const { switchChainAsync, isPending: isSwitchingChain } = useSwitchChain()
  const { signMessageAsync } = useSignMessage()

  // Local state
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [error, setError] = useState<X402WalletError | null>(null)

  // Derived state
  const chainName = chainId ? CHAIN_NAMES[chainId] : undefined
  const isOnSupportedChain = chainId ? Object.values(CHAIN_IDS).includes(chainId) : false

  // ==========================================================================
  // Update status based on wagmi state
  // ==========================================================================

  useEffect(() => {
    if (isConnecting) {
      setStatus('connecting')
    } else if (isSwitchingChain) {
      setStatus('switching_chain')
    } else if (isConnected) {
      setStatus('connected')
    } else {
      setStatus('disconnected')
    }
  }, [isConnected, isConnecting, isSwitchingChain])

  // ==========================================================================
  // Connect
  // ==========================================================================

  const connect = useCallback(
    async (connectorId?: string): Promise<void> => {
      setError(null)

      try {
        // Find connector (default to injected/MetaMask)
        let selectedConnector = connectors.find((c) => c.id === connectorId)
        if (!selectedConnector) {
          // Try injected first, then walletConnect
          selectedConnector =
            connectors.find((c) => c.id === 'injected') ||
            connectors.find((c) => c.id === 'walletConnect')
        }

        if (!selectedConnector) {
          throw new Error('No wallet connector available')
        }

        await connectAsync({ connector: selectedConnector })
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to connect wallet'
        setError({ code: 'CONNECT_FAILED', message })
        setStatus('error')
        throw err
      }
    },
    [connectors, connectAsync]
  )

  // ==========================================================================
  // Disconnect
  // ==========================================================================

  const disconnect = useCallback(async (): Promise<void> => {
    try {
      await disconnectAsync()
      setError(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to disconnect'
      setError({ code: 'DISCONNECT_FAILED', message })
    }
  }, [disconnectAsync])

  // ==========================================================================
  // Switch Chain
  // ==========================================================================

  const switchChain = useCallback(
    async (targetChainName: SupportedChainName): Promise<void> => {
      if (!isConnected) {
        throw new Error('Wallet not connected')
      }

      const targetChainId = CHAIN_IDS[targetChainName]
      if (chainId === targetChainId) {
        return // Already on the right chain
      }

      setError(null)

      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        await switchChainAsync({ chainId: targetChainId as any })
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to switch chain'
        setError({ code: 'SWITCH_CHAIN_FAILED', message })
        throw err
      }
    },
    [isConnected, chainId, switchChainAsync]
  )

  // ==========================================================================
  // Sign Message
  // ==========================================================================

  const signMessage = useCallback(
    async (message: string): Promise<string> => {
      if (!isConnected) {
        throw new Error('Wallet not connected')
      }

      try {
        return await signMessageAsync({ message })
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to sign message'
        setError({ code: 'SIGN_FAILED', message: errorMsg })
        throw err
      }
    },
    [isConnected, signMessageAsync]
  )

  // ==========================================================================
  // Clear Error
  // ==========================================================================

  const clearError = useCallback(() => {
    setError(null)
    if (status === 'error') {
      setStatus(isConnected ? 'connected' : 'disconnected')
    }
  }, [status, isConnected])

  // ==========================================================================
  // Utilities
  // ==========================================================================

  const getWalletInfo = useCallback((): WalletInfo => {
    return {
      address,
      chainId,
      chainName,
      isConnected,
      isOnSupportedChain,
    }
  }, [address, chainId, chainName, isConnected, isOnSupportedChain])

  const getSupportedChains = useCallback((): SupportedChainName[] => {
    return Object.keys(SUPPORTED_CHAINS) as SupportedChainName[]
  }, [])

  return {
    // State
    address,
    chainId,
    chainName,
    isConnected,
    isConnecting: isConnecting || isSwitchingChain,
    status,
    isOnSupportedChain,
    error,

    // Actions
    connect,
    disconnect,
    switchChain,
    signMessage,
    clearError,

    // Utilities
    getWalletInfo,
    getSupportedChains,
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get chain configuration by name
 */
export function getChainConfig(chainName: SupportedChainName) {
  return SUPPORTED_CHAINS[chainName]
}

/**
 * Check if a chain ID is supported for x402
 */
export function isChainSupported(chainId: number): boolean {
  return Object.values(CHAIN_IDS).includes(chainId)
}

/**
 * Get chain name from ID
 */
export function getChainNameFromId(chainId: number): SupportedChainName | undefined {
  return CHAIN_NAMES[chainId]
}

/**
 * Get block explorer URL for a transaction
 */
export function getExplorerTxUrl(txHash: string, chainName: SupportedChainName): string {
  const explorers: Record<SupportedChainName, string> = {
    base: 'https://basescan.org',
    baseSepolia: 'https://sepolia.basescan.org',
    polygon: 'https://polygonscan.com',
    optimism: 'https://optimistic.etherscan.io',
    arbitrum: 'https://arbiscan.io',
    mainnet: 'https://etherscan.io',
  }

  return `${explorers[chainName]}/tx/${txHash}`
}

/**
 * Get block explorer URL for an address
 */
export function getExplorerAddressUrl(address: string, chainName: SupportedChainName): string {
  const explorers: Record<SupportedChainName, string> = {
    base: 'https://basescan.org',
    baseSepolia: 'https://sepolia.basescan.org',
    polygon: 'https://polygonscan.com',
    optimism: 'https://optimistic.etherscan.io',
    arbitrum: 'https://arbiscan.io',
    mainnet: 'https://etherscan.io',
  }

  return `${explorers[chainName]}/address/${address}`
}

/**
 * Format address for display (0x1234...5678)
 */
export function formatAddress(address: string, chars: number = 4): string {
  if (!address) return ''
  return `${address.slice(0, chars + 2)}...${address.slice(-chars)}`
}
