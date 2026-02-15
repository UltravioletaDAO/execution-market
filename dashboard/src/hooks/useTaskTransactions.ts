/**
 * useTaskTransactions - Fetch transaction history from payment_events audit trail
 *
 * Calls GET /api/v1/tasks/{taskId}/transactions which reads from the
 * payment_events table and returns chronological on-chain transaction events.
 */

import { useState, useEffect, useCallback } from 'react'

export interface TransactionEvent {
  id: string
  event_type: string
  tx_hash: string | null
  amount_usdc: number | null
  from_address: string | null
  to_address: string | null
  network: string | null
  token: string
  status: string
  explorer_url: string | null
  label: string | null
  timestamp: string
  metadata: Record<string, unknown> | null
}

export interface TransactionSummary {
  total_locked: number
  total_released: number
  total_refunded: number
  fee_collected: number
}

export interface TaskTransactions {
  task_id: string
  transactions: TransactionEvent[]
  total_count: number
  summary: TransactionSummary
}

interface UseTaskTransactionsReturn {
  data: TaskTransactions | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

function getTransactionsUrl(taskId: string): string {
  const base = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
  if (base.endsWith('/api')) {
    return `${base}/v1/tasks/${taskId}/transactions`
  }
  return `${base}/api/v1/tasks/${taskId}/transactions`
}

export function useTaskTransactions(taskId: string | null): UseTaskTransactionsReturn {
  const [data, setData] = useState<TaskTransactions | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const fetchTransactions = useCallback(async () => {
    if (!taskId) {
      setData(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const url = getTransactionsUrl(taskId)
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const json = await response.json()

      if (
        json &&
        typeof json.task_id === 'string' &&
        Array.isArray(json.transactions) &&
        typeof json.total_count === 'number' &&
        json.summary
      ) {
        setData(json as TaskTransactions)
      } else {
        setData(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    fetchTransactions()
  }, [fetchTransactions])

  return { data, loading, error, refetch: fetchTransactions }
}
