/**
 * usePayment - Main x402 payment hook
 *
 * Integrates with x402 protocol for:
 * - Balance checking
 * - Direct payments via MerchantRouter
 * - Payment history
 */

import { useState, useEffect, useCallback } from 'react'
import { useAccount, useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi'
import { parseUnits, formatUnits, type Address } from 'viem'
import { base } from 'wagmi/chains'

// =============================================================================
// Constants (from x402 client)
// =============================================================================

export const MERCHANT_ROUTER = '0xa48E8AdcA504D2f48e5AF6be49039354e922913F' as const

export const TOKEN_ADDRESSES = {
  base: {
    usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    eurc: '0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42',
    dai: '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
    usdt: '0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2',
  },
} as const

export const TOKEN_DECIMALS = {
  usdc: 6,
  eurc: 6,
  dai: 18,
  usdt: 6,
} as const

export type PaymentToken = 'usdc' | 'eurc' | 'dai' | 'usdt'

// =============================================================================
// ABIs
// =============================================================================

const MERCHANT_ROUTER_ABI = [
  {
    inputs: [
      { name: 'token', type: 'address' },
      { name: 'amount', type: 'uint256' },
      { name: 'recipient', type: 'address' },
      { name: 'memo', type: 'string' },
    ],
    name: 'pay',
    outputs: [{ name: '', type: 'bool' }],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [{ name: 'merchant', type: 'address' }],
    name: 'getMerchantInfo',
    outputs: [
      { name: 'registered', type: 'bool' },
      { name: 'name', type: 'string' },
      { name: 'webhookUrl', type: 'string' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
] as const

const ERC20_ABI = [
  {
    inputs: [{ name: 'account', type: 'address' }],
    name: 'balanceOf',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [
      { name: 'spender', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    name: 'approve',
    outputs: [{ name: '', type: 'bool' }],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [
      { name: 'owner', type: 'address' },
      { name: 'spender', type: 'address' },
    ],
    name: 'allowance',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
] as const

// =============================================================================
// Types
// =============================================================================

export interface PaymentResult {
  success: boolean
  txHash: string | null
  amount: string
  token: PaymentToken
  recipient: string
  timestamp: Date
  error?: string
  gasUsed?: bigint
}

export interface PaymentHistoryItem {
  id: string
  type: 'payment' | 'escrow_release' | 'refund'
  amount: string
  token: PaymentToken
  recipient: string
  memo?: string
  txHash: string
  timestamp: Date
  status: 'pending' | 'confirmed' | 'failed'
}

export interface UsePaymentOptions {
  defaultToken?: PaymentToken
  chainId?: number
}

export interface UsePaymentReturn {
  // State
  balance: string | null
  loading: boolean
  error: Error | null
  pendingTx: string | null

  // Functions
  checkBalance: (token?: PaymentToken) => Promise<string>
  sendPayment: (
    recipient: string,
    amount: string,
    token?: PaymentToken,
    memo?: string
  ) => Promise<PaymentResult>
  getPaymentHistory: () => Promise<PaymentHistoryItem[]>
  approveToken: (token: PaymentToken, amount: string) => Promise<string>
  checkAllowance: (token: PaymentToken, spender?: string) => Promise<string>
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function usePayment(options: UsePaymentOptions = {}): UsePaymentReturn {
  const { defaultToken = 'usdc', chainId = base.id } = options

  const { address } = useAccount()
  const [balance, setBalance] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [pendingTx, setPendingTx] = useState<string | null>(null)

  // Get token address
  const getTokenAddress = useCallback(
    (token: PaymentToken): Address => {
      return TOKEN_ADDRESSES.base[token] as Address
    },
    []
  )

  // Get token decimals
  const getDecimals = useCallback((token: PaymentToken): number => {
    return TOKEN_DECIMALS[token]
  }, [])

  // Read balance for default token
  const { data: rawBalance, refetch: refetchBalance } = useReadContract({
    address: getTokenAddress(defaultToken),
    abi: ERC20_ABI,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    chainId: chainId as any,
    query: {
      enabled: Boolean(address),
    },
  })

  // Update balance when raw data changes
  useEffect(() => {
    if (rawBalance !== undefined) {
      const formatted = formatUnits(rawBalance, getDecimals(defaultToken))
      setBalance(formatted)
    }
  }, [rawBalance, defaultToken, getDecimals])

  // Write contract hooks
  const { writeContractAsync: approveAsync } = useWriteContract()
  const { writeContractAsync: payAsync } = useWriteContract()

  // Wait for transaction
  const { data: txReceipt } = useWaitForTransactionReceipt({
    hash: pendingTx as `0x${string}` | undefined,
  })

  // Clear pending tx when confirmed
  useEffect(() => {
    if (txReceipt) {
      setPendingTx(null)
      refetchBalance()
    }
  }, [txReceipt, refetchBalance])

  // ==========================================================================
  // Check Balance
  // ==========================================================================

  const checkBalance = useCallback(
    async (token: PaymentToken = defaultToken): Promise<string> => {
      if (!address) {
        throw new Error('Wallet not connected')
      }

      setLoading(true)
      setError(null)

      try {
        const result = await refetchBalance()
        if (result.data !== undefined) {
          const formatted = formatUnits(result.data, getDecimals(token))
          setBalance(formatted)
          return formatted
        }
        return '0'
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to check balance')
        setError(error)
        throw error
      } finally {
        setLoading(false)
      }
    },
    [address, defaultToken, refetchBalance, getDecimals]
  )

  // ==========================================================================
  // Check Allowance
  // ==========================================================================

  const checkAllowance = useCallback(
    async (
      token: PaymentToken,
      spender: string = MERCHANT_ROUTER
    ): Promise<string> => {
      if (!address) {
        throw new Error('Wallet not connected')
      }

      // This would need a separate read contract call
      // For now, return '0' - in production use multicall or separate hook
      console.log('Checking allowance for', token, 'spender:', spender)
      return '0'
    },
    [address]
  )

  // ==========================================================================
  // Approve Token
  // ==========================================================================

  const approveToken = useCallback(
    async (token: PaymentToken, amount: string): Promise<string> => {
      if (!address) {
        throw new Error('Wallet not connected')
      }

      setLoading(true)
      setError(null)

      try {
        const tokenAddress = getTokenAddress(token)
        const amountWei = parseUnits(amount, getDecimals(token))

        const hash = await approveAsync({
          address: tokenAddress,
          abi: ERC20_ABI,
          functionName: 'approve',
          args: [MERCHANT_ROUTER as Address, amountWei],
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
    chainId: chainId as any,
        })

        setPendingTx(hash)
        return hash
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Approval failed')
        setError(error)
        throw error
      } finally {
        setLoading(false)
      }
    },
    [address, approveAsync, chainId, getTokenAddress, getDecimals]
  )

  // ==========================================================================
  // Send Payment
  // ==========================================================================

  const sendPayment = useCallback(
    async (
      recipient: string,
      amount: string,
      token: PaymentToken = defaultToken,
      memo: string = ''
    ): Promise<PaymentResult> => {
      if (!address) {
        throw new Error('Wallet not connected')
      }

      setLoading(true)
      setError(null)

      try {
        const tokenAddress = getTokenAddress(token)
        const amountWei = parseUnits(amount, getDecimals(token))

        const hash = await payAsync({
          address: MERCHANT_ROUTER as Address,
          abi: MERCHANT_ROUTER_ABI,
          functionName: 'pay',
          args: [tokenAddress, amountWei, recipient as Address, memo],
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
    chainId: chainId as any,
        })

        setPendingTx(hash)

        return {
          success: true,
          txHash: hash,
          amount,
          token,
          recipient,
          timestamp: new Date(),
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Payment failed'
        setError(new Error(errorMsg))

        return {
          success: false,
          txHash: null,
          amount,
          token,
          recipient,
          timestamp: new Date(),
          error: errorMsg,
        }
      } finally {
        setLoading(false)
      }
    },
    [address, defaultToken, payAsync, chainId, getTokenAddress, getDecimals]
  )

  // ==========================================================================
  // Get Payment History
  // ==========================================================================

  const getPaymentHistory = useCallback(async (): Promise<PaymentHistoryItem[]> => {
    // In production, this would fetch from an indexer or backend
    // For now, return empty array
    console.log('Fetching payment history...')
    return []
  }, [])

  return {
    balance,
    loading,
    error,
    pendingTx,
    checkBalance,
    sendPayment,
    getPaymentHistory,
    approveToken,
    checkAllowance,
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

export function formatTokenAmount(amount: string, token: PaymentToken): string {
  const decimals = TOKEN_DECIMALS[token]
  const num = parseFloat(amount)
  if (isNaN(num)) return '0.00'

  // Format based on token decimals
  if (decimals <= 6) {
    return num.toFixed(2)
  }
  return num.toFixed(4)
}

export function parseTokenAmount(amount: string, token: PaymentToken): bigint {
  return parseUnits(amount, TOKEN_DECIMALS[token])
}
