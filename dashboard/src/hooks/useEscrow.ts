/**
 * useEscrow - Escrow operations hook for x402 protocol
 *
 * Handles:
 * - Creating escrow deposits
 * - Releasing escrow to recipients
 * - Refunding escrow to depositors
 * - Querying escrow status
 * - Subscribing to escrow events
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useAccount, useWriteContract, useReadContract, useWaitForTransactionReceipt, useWatchContractEvent } from 'wagmi'
import { parseUnits, formatUnits, keccak256, toBytes, type Address, type Hex } from 'viem'
import { base } from 'wagmi/chains'
import { TOKEN_ADDRESSES, TOKEN_DECIMALS, type PaymentToken } from './usePayment'

// =============================================================================
// Constants
// =============================================================================

export const DEPOSIT_RELAY_FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' as const

// =============================================================================
// ABIs
// =============================================================================

const DEPOSIT_RELAY_ABI = [
  {
    inputs: [
      { name: 'token', type: 'address' },
      { name: 'amount', type: 'uint256' },
      { name: 'beneficiary', type: 'address' },
      { name: 'timeout', type: 'uint256' },
      { name: 'taskId', type: 'bytes32' },
    ],
    name: 'createEscrow',
    outputs: [{ name: 'escrowId', type: 'bytes32' }],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [
      { name: 'escrowId', type: 'bytes32' },
      { name: 'recipient', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    name: 'releaseEscrow',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [{ name: 'escrowId', type: 'bytes32' }],
    name: 'refundEscrow',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [{ name: 'escrowId', type: 'bytes32' }],
    name: 'getEscrow',
    outputs: [
      { name: 'depositor', type: 'address' },
      { name: 'beneficiary', type: 'address' },
      { name: 'amount', type: 'uint256' },
      { name: 'timeout', type: 'uint256' },
      { name: 'released', type: 'bool' },
      { name: 'refunded', type: 'bool' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
] as const

const ERC20_ABI = [
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

// Escrow events ABI
const ESCROW_EVENTS_ABI = [
  {
    anonymous: false,
    inputs: [
      { indexed: true, name: 'escrowId', type: 'bytes32' },
      { indexed: true, name: 'depositor', type: 'address' },
      { indexed: false, name: 'amount', type: 'uint256' },
    ],
    name: 'EscrowCreated',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, name: 'escrowId', type: 'bytes32' },
      { indexed: true, name: 'recipient', type: 'address' },
      { indexed: false, name: 'amount', type: 'uint256' },
    ],
    name: 'EscrowReleased',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, name: 'escrowId', type: 'bytes32' },
      { indexed: true, name: 'depositor', type: 'address' },
    ],
    name: 'EscrowRefunded',
    type: 'event',
  },
] as const

// =============================================================================
// Types
// =============================================================================

export type EscrowStatus =
  | 'pending'
  | 'active'
  | 'released'
  | 'partial'
  | 'refunded'
  | 'expired'
  | 'disputed'

export interface EscrowInfo {
  escrowId: string
  depositor: string
  beneficiary: string
  amount: string
  token: PaymentToken
  timeoutTimestamp: number
  status: EscrowStatus
  releasedAmount: string
}

export interface EscrowCreateParams {
  taskId: string
  amount: string
  token?: PaymentToken
  beneficiary?: string
  timeoutHours?: number
}

export interface EscrowReleaseParams {
  escrowId: string
  recipient: string
  amount?: string
  token?: PaymentToken
}

export interface EscrowResult {
  success: boolean
  txHash: string | null
  escrowId?: string
  error?: string
}

export interface EscrowEvent {
  type: 'created' | 'released' | 'refunded'
  escrowId: string
  depositor?: string
  recipient?: string
  amount?: string
  timestamp: Date
  txHash: string
}

export interface UseEscrowOptions {
  defaultToken?: PaymentToken
  chainId?: number
  watchEvents?: boolean
}

export interface UseEscrowReturn {
  // State
  escrowStatus: EscrowStatus | null
  loading: boolean
  error: Error | null
  pendingTx: string | null
  events: EscrowEvent[]

  // Functions
  createEscrow: (params: EscrowCreateParams) => Promise<EscrowResult>
  releaseEscrow: (params: EscrowReleaseParams) => Promise<EscrowResult>
  refundEscrow: (escrowId: string, reason?: string) => Promise<EscrowResult>
  getEscrowInfo: (escrowId: string) => Promise<EscrowInfo | null>
  clearEvents: () => void
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useEscrow(options: UseEscrowOptions = {}): UseEscrowReturn {
  const { defaultToken = 'usdc', chainId = base.id, watchEvents = true } = options

  const { address, isConnected } = useAccount()
  const [escrowStatus, setEscrowStatus] = useState<EscrowStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [pendingTx, setPendingTx] = useState<string | null>(null)
  const [events, setEvents] = useState<EscrowEvent[]>([])

  // Track current escrow being monitored
  const monitoredEscrowId = useRef<string | null>(null)

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

  // Write contract hooks
  const { writeContractAsync: createEscrowAsync } = useWriteContract()
  const { writeContractAsync: releaseEscrowAsync } = useWriteContract()
  const { writeContractAsync: refundEscrowAsync } = useWriteContract()
  const { writeContractAsync: approveAsync } = useWriteContract()

  // Wait for transaction
  const { data: txReceipt } = useWaitForTransactionReceipt({
    hash: pendingTx as `0x${string}` | undefined,
  })

  // Clear pending tx when confirmed
  useEffect(() => {
    if (txReceipt) {
      setPendingTx(null)
    }
  }, [txReceipt])

  // ==========================================================================
  // Watch Escrow Events
  // ==========================================================================

  useWatchContractEvent({
    address: DEPOSIT_RELAY_FACTORY,
    abi: ESCROW_EVENTS_ABI,
    eventName: 'EscrowCreated',
    enabled: watchEvents && isConnected,
    onLogs(logs) {
      logs.forEach((log) => {
        if (!log.args) return
        const { escrowId, depositor, amount } = log.args as {
          escrowId: Hex
          depositor: Address
          amount: bigint
        }

        setEvents((prev) => [
          ...prev,
          {
            type: 'created' as const,
            escrowId,
            depositor,
            amount: formatUnits(amount, getDecimals(defaultToken)),
            timestamp: new Date(),
            txHash: log.transactionHash || '',
          },
        ])
      })
    },
  })

  useWatchContractEvent({
    address: DEPOSIT_RELAY_FACTORY,
    abi: ESCROW_EVENTS_ABI,
    eventName: 'EscrowReleased',
    enabled: watchEvents && isConnected,
    onLogs(logs) {
      logs.forEach((log) => {
        if (!log.args) return
        const { escrowId, recipient, amount } = log.args as {
          escrowId: Hex
          recipient: Address
          amount: bigint
        }

        setEvents((prev) => [
          ...prev,
          {
            type: 'released' as const,
            escrowId,
            recipient,
            amount: formatUnits(amount, getDecimals(defaultToken)),
            timestamp: new Date(),
            txHash: log.transactionHash || '',
          },
        ])

        // Update status if this is the monitored escrow
        if (monitoredEscrowId.current === escrowId) {
          setEscrowStatus('released')
        }
      })
    },
  })

  useWatchContractEvent({
    address: DEPOSIT_RELAY_FACTORY,
    abi: ESCROW_EVENTS_ABI,
    eventName: 'EscrowRefunded',
    enabled: watchEvents && isConnected,
    onLogs(logs) {
      logs.forEach((log) => {
        if (!log.args) return
        const { escrowId, depositor } = log.args as {
          escrowId: Hex
          depositor: Address
        }

        setEvents((prev) => [
          ...prev,
          {
            type: 'refunded' as const,
            escrowId,
            depositor,
            timestamp: new Date(),
            txHash: log.transactionHash || '',
          },
        ])

        // Update status if this is the monitored escrow
        if (monitoredEscrowId.current === escrowId) {
          setEscrowStatus('refunded')
        }
      })
    },
  })

  // ==========================================================================
  // Create Escrow
  // ==========================================================================

  const createEscrow = useCallback(
    async (params: EscrowCreateParams): Promise<EscrowResult> => {
      const { taskId, amount, token = defaultToken, beneficiary, timeoutHours = 48 } = params

      if (!address) {
        return { success: false, txHash: null, error: 'Wallet not connected' }
      }

      setLoading(true)
      setError(null)

      try {
        const tokenAddress = getTokenAddress(token)
        const amountWei = parseUnits(amount, getDecimals(token))
        const beneficiaryAddress = (beneficiary || address) as Address
        const timeoutTimestamp = BigInt(Math.floor(Date.now() / 1000) + timeoutHours * 3600)
        const taskIdBytes = keccak256(toBytes(taskId))

        // First approve the token spend
        const approveHash = await approveAsync({
          address: tokenAddress,
          abi: ERC20_ABI,
          functionName: 'approve',
          args: [DEPOSIT_RELAY_FACTORY as Address, amountWei],
          chainId,
        })

        // Wait a moment for approval to propagate
        await new Promise((resolve) => setTimeout(resolve, 2000))

        // Create the escrow
        const hash = await createEscrowAsync({
          address: DEPOSIT_RELAY_FACTORY,
          abi: DEPOSIT_RELAY_ABI,
          functionName: 'createEscrow',
          args: [tokenAddress, amountWei, beneficiaryAddress, timeoutTimestamp, taskIdBytes],
          chainId,
        })

        setPendingTx(hash)
        monitoredEscrowId.current = taskIdBytes
        setEscrowStatus('pending')

        return {
          success: true,
          txHash: hash,
          escrowId: taskIdBytes,
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to create escrow'
        setError(new Error(errorMsg))
        return { success: false, txHash: null, error: errorMsg }
      } finally {
        setLoading(false)
      }
    },
    [address, defaultToken, createEscrowAsync, approveAsync, chainId, getTokenAddress, getDecimals]
  )

  // ==========================================================================
  // Release Escrow
  // ==========================================================================

  const releaseEscrow = useCallback(
    async (params: EscrowReleaseParams): Promise<EscrowResult> => {
      const { escrowId, recipient, amount, token = defaultToken } = params

      if (!address) {
        return { success: false, txHash: null, error: 'Wallet not connected' }
      }

      setLoading(true)
      setError(null)

      try {
        // Get escrow info to determine amount if not provided
        let releaseAmount: bigint
        if (amount) {
          releaseAmount = parseUnits(amount, getDecimals(token))
        } else {
          // Release full amount - need to fetch from contract
          // For now, require explicit amount
          return { success: false, txHash: null, error: 'Amount required for release' }
        }

        const escrowIdBytes = escrowId.startsWith('0x')
          ? escrowId as Hex
          : (`0x${escrowId}` as Hex)

        const hash = await releaseEscrowAsync({
          address: DEPOSIT_RELAY_FACTORY,
          abi: DEPOSIT_RELAY_ABI,
          functionName: 'releaseEscrow',
          args: [escrowIdBytes, recipient as Address, releaseAmount],
          chainId,
        })

        setPendingTx(hash)
        monitoredEscrowId.current = escrowId

        return {
          success: true,
          txHash: hash,
          escrowId,
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to release escrow'
        setError(new Error(errorMsg))
        return { success: false, txHash: null, error: errorMsg }
      } finally {
        setLoading(false)
      }
    },
    [address, defaultToken, releaseEscrowAsync, chainId, getDecimals]
  )

  // ==========================================================================
  // Refund Escrow
  // ==========================================================================

  const refundEscrow = useCallback(
    async (escrowId: string, _reason?: string): Promise<EscrowResult> => {
      if (!address) {
        return { success: false, txHash: null, error: 'Wallet not connected' }
      }

      setLoading(true)
      setError(null)

      try {
        const escrowIdBytes = escrowId.startsWith('0x')
          ? escrowId as Hex
          : (`0x${escrowId}` as Hex)

        const hash = await refundEscrowAsync({
          address: DEPOSIT_RELAY_FACTORY,
          abi: DEPOSIT_RELAY_ABI,
          functionName: 'refundEscrow',
          args: [escrowIdBytes],
          chainId,
        })

        setPendingTx(hash)
        monitoredEscrowId.current = escrowId

        return {
          success: true,
          txHash: hash,
          escrowId,
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to refund escrow'
        setError(new Error(errorMsg))
        return { success: false, txHash: null, error: errorMsg }
      } finally {
        setLoading(false)
      }
    },
    [address, refundEscrowAsync, chainId]
  )

  // ==========================================================================
  // Get Escrow Info
  // ==========================================================================

  const getEscrowInfo = useCallback(
    async (escrowId: string): Promise<EscrowInfo | null> => {
      // This would need a read contract call
      // For now, return a placeholder implementation
      const escrowIdBytes = escrowId.startsWith('0x')
        ? escrowId as Hex
        : (`0x${escrowId}` as Hex)

      monitoredEscrowId.current = escrowId

      // In production, this would read from the contract
      console.log('Fetching escrow info for:', escrowIdBytes)

      return null
    },
    []
  )

  // ==========================================================================
  // Clear Events
  // ==========================================================================

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  return {
    escrowStatus,
    loading,
    error,
    pendingTx,
    events,
    createEscrow,
    releaseEscrow,
    refundEscrow,
    getEscrowInfo,
    clearEvents,
  }
}

// =============================================================================
// Escrow Info Hook (for reading specific escrow)
// =============================================================================

export interface UseEscrowInfoReturn {
  escrow: EscrowInfo | null
  loading: boolean
  error: Error | null
  refetch: () => void
}

export function useEscrowInfo(
  escrowId: string | null,
  token: PaymentToken = 'usdc'
): UseEscrowInfoReturn {
  const escrowIdBytes = escrowId
    ? (escrowId.startsWith('0x') ? escrowId : `0x${escrowId}`) as Hex
    : undefined

  const { data, isLoading, error, refetch } = useReadContract({
    address: DEPOSIT_RELAY_FACTORY,
    abi: DEPOSIT_RELAY_ABI,
    functionName: 'getEscrow',
    args: escrowIdBytes ? [escrowIdBytes] : undefined,
    chainId: base.id,
    query: {
      enabled: Boolean(escrowIdBytes),
    },
  })

  const escrow: EscrowInfo | null = data
    ? {
        escrowId: escrowId!,
        depositor: data[0],
        beneficiary: data[1],
        amount: formatUnits(data[2], TOKEN_DECIMALS[token]),
        token,
        timeoutTimestamp: Number(data[3]),
        status: data[4]
          ? 'released'
          : data[5]
          ? 'refunded'
          : Number(data[3]) < Math.floor(Date.now() / 1000)
          ? 'expired'
          : 'active',
        releasedAmount: '0',
      }
    : null

  return {
    escrow,
    loading: isLoading,
    error: error as Error | null,
    refetch: () => refetch(),
  }
}
