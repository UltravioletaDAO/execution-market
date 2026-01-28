/**
 * useDisputes - Hook for managing disputes
 *
 * Provides functionality for:
 * - Fetching disputes (as executor or agent)
 * - Submitting evidence
 * - Tracking dispute status
 */

import { useState, useCallback, useEffect } from 'react'
import { supabase } from '../lib/supabase'

// Types
interface Dispute {
  id: string
  task_id: string
  submission_id: string
  agent_id: string
  executor_id: string
  reason: string
  status: 'open' | 'under_review' | 'resolved' | 'escalated'
  agent_evidence: Record<string, unknown> | null
  executor_evidence: Record<string, unknown> | null
  resolution: string | null
  resolved_by: string | null
  resolved_at: string | null
  created_at: string
  task?: {
    id: string
    title: string
    bounty_usd: number
    category: string
  }
  submission?: {
    id: string
    evidence: Record<string, unknown>
    submitted_at: string
  }
}

interface DisputeEvidence {
  description: string
  files?: string[]
  additional_info?: Record<string, unknown>
}

interface UseDisputesOptions {
  executorId?: string
  agentId?: string
  status?: 'open' | 'under_review' | 'resolved' | 'escalated'
}

export function useDisputes(options: UseDisputesOptions = {}) {
  const { executorId, agentId, status } = options

  const [disputes, setDisputes] = useState<Dispute[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch disputes
  const fetchDisputes = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      let query = supabase
        .from('disputes')
        .select(`
          *,
          task:tasks(id, title, bounty_usd, category),
          submission:submissions(id, evidence, submitted_at)
        `)
        .order('created_at', { ascending: false })

      if (executorId) {
        query = query.eq('executor_id', executorId)
      }
      if (agentId) {
        query = query.eq('agent_id', agentId)
      }
      if (status) {
        query = query.eq('status', status)
      }

      const { data, error: fetchError } = await query

      if (fetchError) throw fetchError

      setDisputes(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch disputes')
    } finally {
      setLoading(false)
    }
  }, [executorId, agentId, status])

  // Initial fetch
  useEffect(() => {
    fetchDisputes()
  }, [fetchDisputes])

  return {
    disputes,
    loading,
    error,
    refetch: fetchDisputes,
  }
}

export function useDispute(disputeId: string | undefined) {
  const [dispute, setDispute] = useState<Dispute | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch single dispute
  const fetchDispute = useCallback(async () => {
    if (!disputeId) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { data, error: fetchError } = await supabase
        .from('disputes')
        .select(`
          *,
          task:tasks(id, title, bounty_usd, category, instructions),
          submission:submissions(id, evidence, submitted_at, notes)
        `)
        .eq('id', disputeId)
        .single()

      if (fetchError) throw fetchError

      setDispute(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dispute')
    } finally {
      setLoading(false)
    }
  }, [disputeId])

  // Submit evidence as executor
  const submitExecutorEvidence = useCallback(async (evidence: DisputeEvidence) => {
    if (!disputeId) return { success: false, error: 'No dispute ID' }

    try {
      const { error: updateError } = await supabase
        .from('disputes')
        .update({
          executor_evidence: evidence,
          status: 'under_review',
        })
        .eq('id', disputeId)

      if (updateError) throw updateError

      await fetchDispute()
      return { success: true }
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Failed to submit evidence',
      }
    }
  }, [disputeId, fetchDispute])

  // Initial fetch
  useEffect(() => {
    fetchDispute()
  }, [fetchDispute])

  return {
    dispute,
    loading,
    error,
    refetch: fetchDispute,
    submitExecutorEvidence,
  }
}

// Hook for creating a dispute
export function useCreateDispute() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createDispute = useCallback(async (
    submissionId: string,
    reason: string,
    agentEvidence?: DisputeEvidence
  ) => {
    setLoading(true)
    setError(null)

    try {
      // Get submission to get task and executor info
      const { data: submission, error: subError } = await supabase
        .from('submissions')
        .select('task_id, executor_id, task:tasks(agent_id)')
        .eq('id', submissionId)
        .single()

      if (subError) throw subError
      if (!submission) throw new Error('Submission not found')

      // Create dispute
      const { data: dispute, error: createError } = await supabase
        .from('disputes')
        .insert({
          task_id: submission.task_id,
          submission_id: submissionId,
          agent_id: (submission.task as { agent_id: string }).agent_id,
          executor_id: submission.executor_id,
          reason,
          agent_evidence: agentEvidence,
          status: 'open',
        })
        .select()
        .single()

      if (createError) throw createError

      // Update task status
      await supabase
        .from('tasks')
        .update({ status: 'disputed' })
        .eq('id', submission.task_id)

      return { success: true, dispute }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create dispute'
      setError(message)
      return { success: false, error: message }
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    createDispute,
    loading,
    error,
  }
}

export type { Dispute, DisputeEvidence }
