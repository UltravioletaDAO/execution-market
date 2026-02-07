/**
 * usePayments - Payment history and management hooks
 *
 * Features:
 * - Fetch payment history
 * - Pagination support
 * - Real-time updates
 * - Payment stats
 */

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'

// Types
interface Payment {
  id: string
  type: 'task_payment' | 'withdrawal' | 'bonus' | 'refund'
  status: 'pending' | 'confirmed' | 'failed'
  amount: number
  currency: string
  task_id?: string
  task_title?: string
  tx_hash?: string
  network: string
  created_at: string
  confirmed_at?: string
}

interface PaymentStats {
  totalEarned: number
  totalWithdrawn: number
  pendingAmount: number
  availableBalance: number
  taskCount: number
  averagePerTask: number
}

interface UsePaymentsOptions {
  executorId: string
  limit?: number
  type?: Payment['type']
}

interface UsePaymentsReturn {
  payments: Payment[]
  loading: boolean
  error: Error | null
  hasMore: boolean
  loadMore: () => void
  refetch: () => Promise<void>
}

interface UsePaymentStatsReturn {
  stats: PaymentStats | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching payment history
 */
export function usePayments({
  executorId,
  limit = 20,
  type,
}: UsePaymentsOptions): UsePaymentsReturn {
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const [page, setPage] = useState(0)

  // Fetch payments
  const fetchPayments = useCallback(async (pageNum: number, append: boolean = false) => {
    try {
      setLoading(true)
      setError(null)

      let query = supabase
        .from('payments')
        .select(`
          id,
          type,
          status,
          amount,
          currency,
          task_id,
          tx_hash,
          network,
          created_at,
          confirmed_at,
          tasks (
            title
          )
        `)
        .eq('executor_id', executorId)
        .order('created_at', { ascending: false })
        .range(pageNum * limit, (pageNum + 1) * limit - 1)

      if (type) {
        query = query.eq('type', type)
      }

      const { data, error: fetchError } = await query

      if (fetchError) throw fetchError

      const formattedPayments: Payment[] = (data || []).map((p: any) => ({
        id: p.id,
        type: p.type,
        status: p.status,
        amount: p.amount,
        currency: p.currency,
        task_id: p.task_id,
        task_title: (p.tasks as { title?: string } | null)?.title,
        tx_hash: p.tx_hash,
        network: p.network,
        created_at: p.created_at,
        confirmed_at: p.confirmed_at,
      }))

      if (append) {
        setPayments((prev) => [...prev, ...formattedPayments])
      } else {
        setPayments(formattedPayments)
      }

      setHasMore(formattedPayments.length === limit)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch payments'))
    } finally {
      setLoading(false)
    }
  }, [executorId, limit, type])

  // Initial fetch
  useEffect(() => {
    setPage(0)
    fetchPayments(0, false)
  }, [fetchPayments])

  // Load more
  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      const nextPage = page + 1
      setPage(nextPage)
      fetchPayments(nextPage, true)
    }
  }, [loading, hasMore, page, fetchPayments])

  // Refetch
  const refetch = useCallback(async () => {
    setPage(0)
    await fetchPayments(0, false)
  }, [fetchPayments])

  // Subscribe to real-time updates
  useEffect(() => {
    const channel = supabase
      .channel('payments')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'payments',
          filter: `executor_id=eq.${executorId}`,
        },
        (payload: any) => {
          if (payload.eventType === 'INSERT') {
            const newPayment = payload.new as Payment
            setPayments((prev) => [newPayment, ...prev])
          } else if (payload.eventType === 'UPDATE') {
            const updatedPayment = payload.new as Payment
            setPayments((prev) =>
              prev.map((p) => (p.id === updatedPayment.id ? updatedPayment : p))
            )
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [executorId])

  return {
    payments,
    loading,
    error,
    hasMore,
    loadMore,
    refetch,
  }
}

/**
 * Hook for fetching payment statistics
 */
export function usePaymentStats(executorId: string): UsePaymentStatsReturn {
  const [stats, setStats] = useState<PaymentStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch all payments for calculations
      const { data: payments, error: fetchError } = await supabase
        .from('payments')
        .select('type, status, amount')
        .eq('executor_id', executorId)

      if (fetchError) throw fetchError

      // Calculate stats
      let totalEarned = 0
      let totalWithdrawn = 0
      let pendingAmount = 0
      let taskCount = 0

      ;(payments || []).forEach((p: any) => {
        if (p.status === 'confirmed') {
          if (p.type === 'task_payment' || p.type === 'bonus') {
            totalEarned += p.amount
            if (p.type === 'task_payment') taskCount++
          } else if (p.type === 'withdrawal') {
            totalWithdrawn += p.amount
          }
        } else if (p.status === 'pending') {
          if (p.type === 'task_payment' || p.type === 'bonus') {
            pendingAmount += p.amount
          }
        }
      })

      setStats({
        totalEarned,
        totalWithdrawn,
        pendingAmount,
        availableBalance: totalEarned - totalWithdrawn,
        taskCount,
        averagePerTask: taskCount > 0 ? totalEarned / taskCount : 0,
      })
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch stats'))
    } finally {
      setLoading(false)
    }
  }, [executorId])

  // Initial fetch
  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return {
    stats,
    loading,
    error,
    refetch: fetchStats,
  }
}

/**
 * Hook for withdrawal operations
 */
export function useWithdraw(executorId: string) {
  const [withdrawing, setWithdrawing] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const withdraw = useCallback(async (amount: number, destinationAddress: string) => {
    try {
      setWithdrawing(true)
      setError(null)

      // Call withdrawal RPC function
      const { data, error: withdrawError } = await supabase.rpc('request_withdrawal', {
        p_executor_id: executorId,
        p_amount: amount,
        p_destination_address: destinationAddress,
      })

      if (withdrawError) throw withdrawError

      return data
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Withdrawal failed')
      setError(error)
      throw error
    } finally {
      setWithdrawing(false)
    }
  }, [executorId])

  return {
    withdraw,
    withdrawing,
    error,
  }
}

export type { Payment, PaymentStats }
