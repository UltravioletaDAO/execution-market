/**
 * useTokenBalance - Token balance management for x402 payments
 *
 * Features:
 * - Multi-token balance fetching
 * - Auto-refresh on new blocks
 * - Formatted display values
 * - Native token (ETH) balance
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  useAccount,
  useBalance,
  useReadContracts,
  useBlockNumber,
} from 'wagmi'
import { formatUnits, type Address } from 'viem'
import { base } from 'wagmi/chains'
import { TOKEN_ADDRESSES, TOKEN_DECIMALS, type PaymentToken } from './usePayment'

// =============================================================================
// Types
// =============================================================================

export interface TokenBalance {
  token: PaymentToken
  raw: bigint
  formatted: string
  display: string
  usdValue?: number
}

export interface NativeBalance {
  raw: bigint
  formatted: string
  display: string
  symbol: string
}

export interface UseTokenBalanceOptions {
  tokens?: PaymentToken[]
  chainId?: number
  refreshInterval?: number // ms
  autoRefresh?: boolean
}

export interface UseTokenBalanceReturn {
  // State
  balances: Record<PaymentToken, TokenBalance>
  nativeBalance: NativeBalance | null
  loading: boolean
  error: Error | null
  lastUpdated: Date | null

  // Functions
  refetch: () => Promise<void>
  getBalance: (token: PaymentToken) => TokenBalance | null
  getTotalUsdValue: () => number
}

// =============================================================================
// Constants
// =============================================================================

const ERC20_BALANCE_ABI = [
  {
    inputs: [{ name: 'account', type: 'address' }],
    name: 'balanceOf',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
] as const

// Default tokens to track
const DEFAULT_TOKENS: PaymentToken[] = ['usdc', 'eurc', 'dai', 'usdt']

// Token symbols for display
const TOKEN_SYMBOLS: Record<PaymentToken, string> = {
  usdc: 'USDC',
  eurc: 'EURC',
  dai: 'DAI',
  usdt: 'USDT',
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useTokenBalance(options: UseTokenBalanceOptions = {}): UseTokenBalanceReturn {
  const {
    tokens = DEFAULT_TOKENS,
    chainId = base.id,
    refreshInterval = 15000, // 15 seconds
    autoRefresh = true,
  } = options

  const { address, isConnected } = useAccount()
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [error, setError] = useState<Error | null>(null)

  // Watch block number for auto-refresh
  const { data: blockNumber } = useBlockNumber({
    chainId,
    watch: autoRefresh,
  })

  // Native balance (ETH)
  const {
    data: nativeData,
    isLoading: nativeLoading,
    refetch: refetchNative,
  } = useBalance({
    address,
    chainId,
    query: {
      enabled: Boolean(address),
    },
  })

  // Build contract read configs for all tokens
  const contracts = useMemo(() => {
    if (!address) return []

    return tokens.map((token) => ({
      address: TOKEN_ADDRESSES.base[token] as Address,
      abi: ERC20_BALANCE_ABI,
      functionName: 'balanceOf' as const,
      args: [address] as [Address],
      chainId,
    }))
  }, [address, tokens, chainId])

  // Read all token balances in one call
  const {
    data: tokenData,
    isLoading: tokensLoading,
    refetch: refetchTokens,
  } = useReadContracts({
    contracts,
    query: {
      enabled: Boolean(address) && contracts.length > 0,
    },
  })

  // ==========================================================================
  // Process balances
  // ==========================================================================

  const balances = useMemo(() => {
    const result: Record<PaymentToken, TokenBalance> = {} as Record<PaymentToken, TokenBalance>

    tokens.forEach((token, index) => {
      const rawBalance = tokenData?.[index]?.result as bigint | undefined
      const balance = rawBalance ?? BigInt(0)
      const decimals = TOKEN_DECIMALS[token]
      const formatted = formatUnits(balance, decimals)
      const num = parseFloat(formatted)

      result[token] = {
        token,
        raw: balance,
        formatted,
        display: formatTokenDisplay(num, token),
        // USD value would come from price feed - stub for now
        usdValue: token === 'usdc' || token === 'usdt' ? num : undefined,
      }
    })

    return result
  }, [tokenData, tokens])

  const nativeBalance: NativeBalance | null = useMemo(() => {
    if (!nativeData) return null

    const num = parseFloat(nativeData.formatted)
    return {
      raw: nativeData.value,
      formatted: nativeData.formatted,
      display: `${num.toFixed(4)} ${nativeData.symbol}`,
      symbol: nativeData.symbol,
    }
  }, [nativeData])

  // ==========================================================================
  // Update timestamp when data changes
  // ==========================================================================

  useEffect(() => {
    if (tokenData || nativeData) {
      setLastUpdated(new Date())
    }
  }, [tokenData, nativeData])

  // ==========================================================================
  // Auto-refresh on new blocks
  // ==========================================================================

  useEffect(() => {
    if (autoRefresh && blockNumber && address) {
      // Silently refetch on new block
      refetchTokens().catch(() => {})
      refetchNative().catch(() => {})
    }
  }, [blockNumber, autoRefresh, address, refetchTokens, refetchNative])

  // ==========================================================================
  // Periodic refresh
  // ==========================================================================

  useEffect(() => {
    if (!autoRefresh || !address) return

    const interval = setInterval(() => {
      refetchTokens().catch(() => {})
      refetchNative().catch(() => {})
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, address, refreshInterval, refetchTokens, refetchNative])

  // ==========================================================================
  // Refetch function
  // ==========================================================================

  const refetch = useCallback(async (): Promise<void> => {
    if (!address) return

    try {
      setError(null)
      await Promise.all([refetchTokens(), refetchNative()])
      setLastUpdated(new Date())
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch balances'))
    }
  }, [address, refetchTokens, refetchNative])

  // ==========================================================================
  // Get single balance
  // ==========================================================================

  const getBalance = useCallback(
    (token: PaymentToken): TokenBalance | null => {
      return balances[token] || null
    },
    [balances]
  )

  // ==========================================================================
  // Get total USD value
  // ==========================================================================

  const getTotalUsdValue = useCallback((): number => {
    return Object.values(balances).reduce((total, balance) => {
      return total + (balance.usdValue || 0)
    }, 0)
  }, [balances])

  return {
    balances,
    nativeBalance,
    loading: tokensLoading || nativeLoading,
    error,
    lastUpdated,
    refetch,
    getBalance,
    getTotalUsdValue,
  }
}

// =============================================================================
// Single Token Balance Hook
// =============================================================================

export interface UseSingleTokenBalanceReturn {
  balance: TokenBalance | null
  loading: boolean
  error: Error | null
  refetch: () => void
}

export function useSingleTokenBalance(
  token: PaymentToken,
  chainId: number = base.id
): UseSingleTokenBalanceReturn {
  const { address } = useAccount()

  const {
    data,
    isLoading,
    error,
    refetch,
  } = useReadContracts({
    contracts: address
      ? [
          {
            address: TOKEN_ADDRESSES.base[token] as Address,
            abi: ERC20_BALANCE_ABI,
            functionName: 'balanceOf',
            args: [address],
            chainId,
          },
        ]
      : [],
    query: {
      enabled: Boolean(address),
    },
  })

  const balance: TokenBalance | null = useMemo(() => {
    const rawBalance = data?.[0]?.result as bigint | undefined
    if (rawBalance === undefined) return null

    const decimals = TOKEN_DECIMALS[token]
    const formatted = formatUnits(rawBalance, decimals)
    const num = parseFloat(formatted)

    return {
      token,
      raw: rawBalance,
      formatted,
      display: formatTokenDisplay(num, token),
      usdValue: token === 'usdc' || token === 'usdt' ? num : undefined,
    }
  }, [data, token])

  return {
    balance,
    loading: isLoading,
    error: error as Error | null,
    refetch: () => refetch(),
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format token amount for display
 */
export function formatTokenDisplay(amount: number, token: PaymentToken): string {
  const symbol = TOKEN_SYMBOLS[token]

  if (amount === 0) {
    return `0.00 ${symbol}`
  }

  if (amount < 0.01) {
    return `<0.01 ${symbol}`
  }

  if (amount < 1000) {
    return `${amount.toFixed(2)} ${symbol}`
  }

  if (amount < 1000000) {
    return `${(amount / 1000).toFixed(2)}K ${symbol}`
  }

  return `${(amount / 1000000).toFixed(2)}M ${symbol}`
}

/**
 * Format USD value for display
 */
export function formatUsdValue(amount: number): string {
  if (amount === 0) return '$0.00'
  if (amount < 0.01) return '<$0.01'
  if (amount < 1000) return `$${amount.toFixed(2)}`
  if (amount < 1000000) return `$${(amount / 1000).toFixed(2)}K`
  return `$${(amount / 1000000).toFixed(2)}M`
}

/**
 * Check if balance is sufficient for amount
 */
export function hasEnoughBalance(
  balance: TokenBalance | null,
  amount: string,
  token: PaymentToken
): boolean {
  if (!balance) return false

  const decimals = TOKEN_DECIMALS[token]
  const amountBigInt = BigInt(Math.floor(parseFloat(amount) * 10 ** decimals))

  return balance.raw >= amountBigInt
}

/**
 * Get token symbol
 */
export function getTokenSymbol(token: PaymentToken): string {
  return TOKEN_SYMBOLS[token]
}
