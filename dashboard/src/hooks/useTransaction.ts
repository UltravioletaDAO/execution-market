/**
 * useTransaction - Transaction management for x402 payments
 *
 * Features:
 * - Track pending, confirmed, and failed transactions
 * - Wait for confirmations
 * - Toast notifications on status changes
 * - Transaction history
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { useWaitForTransactionReceipt, usePublicClient } from 'wagmi'
import type { Hash, TransactionReceipt } from 'viem'
import { base } from 'wagmi/chains'

// =============================================================================
// Types
// =============================================================================

export type TransactionStatus = 'pending' | 'confirming' | 'confirmed' | 'failed' | 'replaced'

export interface Transaction {
  hash: Hash
  status: TransactionStatus
  type: 'payment' | 'approval' | 'escrow_create' | 'escrow_release' | 'escrow_refund' | 'other'
  description: string
  amount?: string
  token?: string
  recipient?: string
  createdAt: Date
  confirmedAt?: Date
  gasUsed?: bigint
  blockNumber?: bigint
  error?: string
}

export interface TransactionNotification {
  id: string
  type: 'pending' | 'success' | 'error'
  title: string
  message: string
  txHash?: Hash
  timestamp: Date
}

export interface UseTransactionOptions {
  chainId?: number
  confirmations?: number
  onPending?: (tx: Transaction) => void
  onConfirmed?: (tx: Transaction, receipt: TransactionReceipt) => void
  onFailed?: (tx: Transaction, error: Error) => void
}

export interface UseTransactionReturn {
  // State
  transactions: Transaction[]
  pendingCount: number
  notifications: TransactionNotification[]

  // Functions
  addTransaction: (params: AddTransactionParams) => void
  waitForConfirmation: (hash: Hash) => Promise<TransactionReceipt>
  getTransaction: (hash: Hash) => Transaction | undefined
  clearTransaction: (hash: Hash) => void
  clearAllTransactions: () => void
  dismissNotification: (id: string) => void
  clearAllNotifications: () => void
}

export interface AddTransactionParams {
  hash: Hash
  type: Transaction['type']
  description: string
  amount?: string
  token?: string
  recipient?: string
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useTransaction(options: UseTransactionOptions = {}): UseTransactionReturn {
  const {
    chainId = base.id,
    confirmations = 1,
    onPending,
    onConfirmed,
    onFailed,
  } = options

  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [notifications, setNotifications] = useState<TransactionNotification[]>([])
  const [watchingHash, setWatchingHash] = useState<Hash | null>(null)

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const publicClient = usePublicClient({ chainId: chainId as any })

  // Track callbacks to avoid stale closures
  const callbacksRef = useRef({ onPending, onConfirmed, onFailed })
  useEffect(() => {
    callbacksRef.current = { onPending, onConfirmed, onFailed }
  }, [onPending, onConfirmed, onFailed])

  // ==========================================================================
  // Add notification helper (defined early to avoid "used before declaration")
  // ==========================================================================

  const addNotification = useCallback(
    (params: Omit<TransactionNotification, 'id' | 'timestamp'>) => {
      const notification: TransactionNotification = {
        ...params,
        id: `notif_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        timestamp: new Date(),
      }
      setNotifications((prev) => [notification, ...prev])

      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        setNotifications((prev) => prev.filter((n) => n.id !== notification.id))
      }, 5000)
    },
    []
  )

  // Watch for transaction receipt
  const { data: receipt, isError } = useWaitForTransactionReceipt({
    hash: watchingHash || undefined,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    chainId: chainId as any,
    confirmations,
    query: {
      enabled: Boolean(watchingHash),
    },
  })

  // ==========================================================================
  // Handle receipt updates
  // ==========================================================================

  useEffect(() => {
    if (!watchingHash) return

    if (receipt) {
      // Transaction confirmed
      setTransactions((prev) =>
        prev.map((tx) =>
          tx.hash === watchingHash
            ? {
                ...tx,
                status: receipt.status === 'success' ? 'confirmed' : 'failed',
                confirmedAt: new Date(),
                gasUsed: receipt.gasUsed,
                blockNumber: receipt.blockNumber,
              }
            : tx
        )
      )

      const tx = transactions.find((t) => t.hash === watchingHash)
      if (tx) {
        if (receipt.status === 'success') {
          addNotification({
            type: 'success',
            title: 'Transaction Confirmed',
            message: tx.description,
            txHash: watchingHash,
          })
          callbacksRef.current.onConfirmed?.(tx, receipt)
        } else {
          addNotification({
            type: 'error',
            title: 'Transaction Failed',
            message: tx.description,
            txHash: watchingHash,
          })
          callbacksRef.current.onFailed?.(tx, new Error('Transaction reverted'))
        }
      }

      setWatchingHash(null)
    }
  }, [receipt, watchingHash, transactions, addNotification])

  // ==========================================================================
  // Handle errors
  // ==========================================================================

  useEffect(() => {
    if (isError && watchingHash) {
      setTransactions((prev) =>
        prev.map((tx) =>
          tx.hash === watchingHash
            ? { ...tx, status: 'failed', error: 'Transaction failed' }
            : tx
        )
      )

      const tx = transactions.find((t) => t.hash === watchingHash)
      if (tx) {
        addNotification({
          type: 'error',
          title: 'Transaction Failed',
          message: tx.description,
          txHash: watchingHash,
        })
        callbacksRef.current.onFailed?.(tx, new Error('Transaction failed'))
      }

      setWatchingHash(null)
    }
  }, [isError, watchingHash, transactions, addNotification])

  // ==========================================================================
  // Add Transaction
  // ==========================================================================

  const addTransaction = useCallback(
    (params: AddTransactionParams) => {
      const { hash, type, description, amount, token, recipient } = params

      // Check if already tracking
      if (transactions.find((tx) => tx.hash === hash)) {
        return
      }

      const tx: Transaction = {
        hash,
        status: 'pending',
        type,
        description,
        amount,
        token,
        recipient,
        createdAt: new Date(),
      }

      setTransactions((prev) => [tx, ...prev])

      // Add pending notification
      addNotification({
        type: 'pending',
        title: 'Transaction Pending',
        message: description,
        txHash: hash,
      })

      // Start watching
      setWatchingHash(hash)

      // Callback
      callbacksRef.current.onPending?.(tx)
    },
    [transactions, addNotification]
  )

  // ==========================================================================
  // Wait for Confirmation
  // ==========================================================================

  const waitForConfirmation = useCallback(
    async (hash: Hash): Promise<TransactionReceipt> => {
      if (!publicClient) {
        throw new Error('Public client not available')
      }

      const receipt = await publicClient.waitForTransactionReceipt({
        hash,
        confirmations,
      })

      return receipt
    },
    [publicClient, confirmations]
  )

  // ==========================================================================
  // Get Transaction
  // ==========================================================================

  const getTransaction = useCallback(
    (hash: Hash): Transaction | undefined => {
      return transactions.find((tx) => tx.hash === hash)
    },
    [transactions]
  )

  // ==========================================================================
  // Clear Transaction
  // ==========================================================================

  const clearTransaction = useCallback((hash: Hash) => {
    setTransactions((prev) => prev.filter((tx) => tx.hash !== hash))
  }, [])

  // ==========================================================================
  // Clear All Transactions
  // ==========================================================================

  const clearAllTransactions = useCallback(() => {
    setTransactions([])
  }, [])

  // ==========================================================================
  // Dismiss Notification
  // ==========================================================================

  const dismissNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }, [])

  // ==========================================================================
  // Clear All Notifications
  // ==========================================================================

  const clearAllNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  // ==========================================================================
  // Computed values
  // ==========================================================================

  const pendingCount = transactions.filter(
    (tx) => tx.status === 'pending' || tx.status === 'confirming'
  ).length

  return {
    transactions,
    pendingCount,
    notifications,
    addTransaction,
    waitForConfirmation,
    getTransaction,
    clearTransaction,
    clearAllTransactions,
    dismissNotification,
    clearAllNotifications,
  }
}

// =============================================================================
// Transaction History Hook
// =============================================================================

export interface UseTransactionHistoryOptions {
  address?: string
  limit?: number
  chainId?: number
}

export interface UseTransactionHistoryReturn {
  history: Transaction[]
  loading: boolean
  error: Error | null
  loadMore: () => void
  hasMore: boolean
}

export function useTransactionHistory(
  _options: UseTransactionHistoryOptions = {}
): UseTransactionHistoryReturn {
  const [history] = useState<Transaction[]>([])
  const [loading] = useState(false)
  const [error] = useState<Error | null>(null)
  const [hasMore] = useState(true)

  // In production, this would fetch from an indexer or backend
  // For now, return empty state

  const loadMore = useCallback(() => {
    // Would load next page of transactions
    console.log('Loading more transactions...')
  }, [])

  return {
    history,
    loading,
    error,
    loadMore,
    hasMore,
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get transaction type label
 */
export function getTransactionTypeLabel(type: Transaction['type']): string {
  const labels: Record<Transaction['type'], string> = {
    payment: 'Payment',
    approval: 'Token Approval',
    escrow_create: 'Create Escrow',
    escrow_release: 'Release Escrow',
    escrow_refund: 'Refund Escrow',
    other: 'Transaction',
  }
  return labels[type]
}

/**
 * Get status color
 */
export function getStatusColor(status: TransactionStatus): string {
  const colors: Record<TransactionStatus, string> = {
    pending: 'yellow',
    confirming: 'blue',
    confirmed: 'green',
    failed: 'red',
    replaced: 'gray',
  }
  return colors[status]
}

/**
 * Format transaction hash for display
 */
export function formatTxHash(hash: Hash, chars: number = 6): string {
  return `${hash.slice(0, chars + 2)}...${hash.slice(-chars)}`
}

/**
 * Calculate time since transaction
 */
export function getTimeSince(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)

  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}
