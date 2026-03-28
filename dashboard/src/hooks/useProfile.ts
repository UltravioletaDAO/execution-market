// Execution Market: Profile Data Hooks
import { useEffect, useState, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import type { ReputationLog } from '../types/database'

// Extended types for profile
export interface EarningsData {
  balance_usdc: number
  total_earned_usdc: number
  total_withdrawn_usdc: number
  pending_earnings_usdc: number  // From in-progress tasks
  this_month_usdc: number
  last_month_usdc: number
}

export interface ReputationData {
  current_score: number
  total_tasks: number
  approved_tasks: number
  rejected_tasks: number
  disputed_tasks: number
  approval_rate: number
  history: ReputationLog[]
}

export interface TaskHistoryItem {
  id: string
  task_id: string
  task_title: string
  task_category: string
  bounty_usd: number
  status: string
  submitted_at: string
  verified_at: string | null
  payment_amount: number | null
  payment_network: string | null
}

// Hook for earnings data
export function useEarnings(executorId: string | undefined) {
  const [earnings, setEarnings] = useState<EarningsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchEarnings = useCallback(async () => {
    if (!executorId) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Fetch executor balance info
      const { error: execError } = await supabase
        .from('executors')
        .select('reputation_score, tasks_completed')
        .eq('id', executorId)
        .single()

      if (execError) throw execError

      // Fetch payments data if available
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

      let balanceData = {
        balance_usdc: 0,
        total_earned_usdc: 0,
        total_withdrawn_usdc: 0,
      }

      // Try to fetch from executor_dashboard view or payments table
      try {
        const response = await fetch(
          `${supabaseUrl}/rest/v1/executor_dashboard?id=eq.${executorId}&select=*`,
          {
            headers: {
              'apikey': supabaseKey,
              'Content-Type': 'application/json',
            }
          }
        )

        if (response.ok) {
          const dashboardData = await response.json()
          if (dashboardData.length > 0) {
            balanceData = {
              balance_usdc: dashboardData[0].balance_usdc || 0,
              total_earned_usdc: dashboardData[0].total_earned_usdc || 0,
              total_withdrawn_usdc: dashboardData[0].total_withdrawn_usdc || 0,
            }
          }
        }
      } catch {
        // View might not exist yet, use default values
        console.log('executor_dashboard view not available, using defaults')
      }

      // Calculate pending from assigned tasks
      const { data: assignedTasks } = await supabase
        .from('tasks')
        .select('bounty_usd')
        .eq('executor_id', executorId)
        .in('status', ['accepted', 'in_progress', 'submitted', 'verifying'])

      const pendingEarnings = assignedTasks?.reduce(
        (sum: number, t: { bounty_usd?: number }) => sum + (t.bounty_usd || 0), 0
      ) || 0

      // Calculate this month and last month earnings
      const now = new Date()
      const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString()
      const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString()
      const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0, 23, 59, 59).toISOString()

      const { data: thisMonthSubmissions } = await supabase
        .from('submissions')
        .select('payment_amount')
        .eq('executor_id', executorId)
        .gte('paid_at', thisMonthStart)
        .not('payment_amount', 'is', null)

      const { data: lastMonthSubmissions } = await supabase
        .from('submissions')
        .select('payment_amount')
        .eq('executor_id', executorId)
        .gte('paid_at', lastMonthStart)
        .lte('paid_at', lastMonthEnd)
        .not('payment_amount', 'is', null)

      const thisMonthEarnings = thisMonthSubmissions?.reduce(
        (sum: number, s: { payment_amount?: number | null }) => sum + (s.payment_amount || 0), 0
      ) || 0

      const lastMonthEarnings = lastMonthSubmissions?.reduce(
        (sum: number, s: { payment_amount?: number | null }) => sum + (s.payment_amount || 0), 0
      ) || 0

      setEarnings({
        ...balanceData,
        pending_earnings_usdc: pendingEarnings,
        this_month_usdc: thisMonthEarnings,
        last_month_usdc: lastMonthEarnings,
      })
    } catch (err) {
      console.error('Failed to fetch earnings:', err)
      setError(err instanceof Error ? err : new Error('Failed to fetch earnings'))
    } finally {
      setLoading(false)
    }
  }, [executorId])

  useEffect(() => {
    fetchEarnings()
  }, [fetchEarnings])

  return { earnings, loading, error, refetch: fetchEarnings }
}

// Hook for reputation data
export function useReputation(executorId: string | undefined) {
  const [reputation, setReputation] = useState<ReputationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!executorId) {
      setLoading(false)
      return
    }

    const fetchReputation = async () => {
      setLoading(true)
      setError(null)

      try {
        // Fetch executor stats
        const { data: executor, error: execError } = await supabase
          .from('executors')
          .select('reputation_score, tasks_completed, tasks_disputed')
          .eq('id', executorId)
          .single()

        if (execError) throw execError

        // Fetch submission stats
        const { data: submissions, error: subError } = await supabase
          .from('submissions')
          .select('id, auto_check_passed, agent_verdict')
          .eq('executor_id', executorId)

        if (subError) throw subError

        const approved = submissions?.filter((s: { agent_verdict?: string; auto_check_passed?: boolean | null }) =>
          s.agent_verdict === 'approved' || s.auto_check_passed === true
        ).length || 0

        const rejected = submissions?.filter((s: { agent_verdict?: string; auto_check_passed?: boolean | null }) =>
          s.agent_verdict === 'rejected' || s.auto_check_passed === false
        ).length || 0

        const total = submissions?.length || 0

        // Fetch reputation history
        const { data: history, error: histError } = await supabase
          .from('reputation_log')
          .select('*')
          .eq('executor_id', executorId)
          .order('created_at', { ascending: false })
          .limit(20)

        if (histError) throw histError

        setReputation({
          current_score: executor.reputation_score,
          total_tasks: total,
          approved_tasks: approved,
          rejected_tasks: rejected,
          disputed_tasks: executor.tasks_disputed || 0,
          approval_rate: total > 0 ? (approved / total) * 100 : 0,
          history: history || [],
        })
      } catch (err) {
        console.error('Failed to fetch reputation:', err)
        setError(err instanceof Error ? err : new Error('Failed to fetch reputation'))
      } finally {
        setLoading(false)
      }
    }

    fetchReputation()
  }, [executorId])

  return { reputation, loading, error }
}

// Hook for task history
export function useTaskHistory(executorId: string | undefined, limit: number = 10) {
  const [history, setHistory] = useState<TaskHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [hasMore, setHasMore] = useState(false)

  const fetchHistory = useCallback(async (offset: number = 0) => {
    if (!executorId) {
      setLoading(false)
      return
    }

    if (offset === 0) {
      setLoading(true)
    }
    setError(null)

    try {
      const { data: submissions, error: subError } = await supabase
        .from('submissions')
        .select(`
          id,
          task_id,
          submitted_at,
          verified_at,
          payment_amount,
          auto_check_passed,
          agent_verdict,
          task:tasks (
            title,
            category,
            bounty_usd,
            status
          )
        `)
        .eq('executor_id', executorId)
        .order('submitted_at', { ascending: false })
        .range(offset, offset + limit)

      if (subError) throw subError

      interface SubmissionWithTask {
        id: string
        task_id: string
        submitted_at: string
        verified_at: string | null
        payment_amount: number | null
        auto_check_passed?: boolean | null
        agent_verdict?: string | null
        task: { title: string; category: string; bounty_usd: number; status: string } | null
      }

      const items: TaskHistoryItem[] = (submissions || []).map((s: SubmissionWithTask) => {
        const task = s.task as { title: string; category: string; bounty_usd: number; status: string } | null
        let status = 'pending'
        if (s.agent_verdict === 'approved' || s.auto_check_passed === true) {
          status = 'approved'
        } else if (s.agent_verdict === 'rejected') {
          status = 'rejected'
        }

        return {
          id: s.id,
          task_id: s.task_id,
          task_title: task?.title || 'Unknown Task',
          task_category: task?.category || 'unknown',
          bounty_usd: task?.bounty_usd || 0,
          status,
          submitted_at: s.submitted_at,
          verified_at: s.verified_at,
          payment_amount: s.payment_amount,
        }
      })

      if (offset === 0) {
        setHistory(items)
      } else {
        setHistory(prev => [...prev, ...items])
      }

      setHasMore(items.length === limit + 1)
    } catch (err) {
      console.error('Failed to fetch task history:', err)
      setError(err instanceof Error ? err : new Error('Failed to fetch history'))
    } finally {
      setLoading(false)
    }
  }, [executorId, limit])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const loadMore = useCallback(() => {
    fetchHistory(history.length)
  }, [fetchHistory, history.length])

  return { history, loading, error, hasMore, loadMore }
}

// Hook for withdrawal
export function useWithdrawal(executorId: string | undefined) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [success, setSuccess] = useState(false)

  const withdraw = useCallback(async (amount: number, destinationAddress: string) => {
    if (!executorId) {
      setError(new Error('Not logged in'))
      return false
    }

    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      // Call the API endpoint for withdrawal
      const apiUrl = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${apiUrl}/v1/withdraw`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          executor_id: executorId,
          amount_usdc: amount,
          destination_address: destinationAddress,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Withdrawal failed')
      }

      setSuccess(true)
      return true
    } catch (err) {
      console.error('Withdrawal failed:', err)
      setError(err instanceof Error ? err : new Error('Withdrawal failed'))
      return false
    } finally {
      setLoading(false)
    }
  }, [executorId])

  const reset = useCallback(() => {
    setError(null)
    setSuccess(false)
  }, [])

  return { withdraw, loading, error, success, reset }
}
