/**
 * useTaskPayment - Fetch payment data for a specific task
 *
 * Queries the Supabase `payments` table by task_id and returns
 * PaymentData compatible with the PaymentStatus component.
 * Includes real-time subscription for live updates.
 */

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import type { PaymentData, PaymentStatusType, PaymentEvent } from '../components/PaymentStatus'

// Raw row shape coming back from Supabase `payments` table
interface PaymentRow {
  id: string
  task_id: string
  status: string
  type: string
  amount: number
  released_amount?: number
  currency: string
  tx_hash?: string
  escrow_tx?: string
  escrow_contract?: string
  network: string
  created_at: string
  updated_at: string
  confirmed_at?: string
  refund_tx?: string
  events?: PaymentEvent[]
}

interface UseTaskPaymentReturn {
  payment: PaymentData | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

/**
 * Map the raw row status string to a PaymentStatusType understood by PaymentStatus.
 */
function mapStatus(row: PaymentRow): PaymentStatusType {
  const statusMap: Record<string, PaymentStatusType> = {
    pending: 'pending',
    confirmed: 'escrowed',
    escrowed: 'escrowed',
    funded: 'escrowed',
    partial_released: 'partial_released',
    released: 'completed',
    completed: 'completed',
    refunded: 'refunded',
    failed: 'pending',
    disputed: 'disputed',
    charged: 'charged',
  }
  return statusMap[row.status] ?? 'pending'
}

/**
 * Build a synthetic events array from the payment row when the row
 * does not already carry an `events` JSONB column.
 */
function buildEventsFromRow(row: PaymentRow): PaymentEvent[] {
  const events: PaymentEvent[] = []

  // Escrow / payment created
  events.push({
    id: `${row.id}-created`,
    type: row.type === 'refund' ? 'refund' : 'escrow_created',
    amount: row.amount,
    tx_hash: row.escrow_tx ?? row.tx_hash,
    network: row.network,
    timestamp: row.created_at,
    actor: 'agent',
    note: undefined,
  })

  // If there is a separate escrow_tx and confirmed_at, mark it as funded
  if (row.confirmed_at && row.escrow_tx) {
    events.push({
      id: `${row.id}-funded`,
      type: 'escrow_funded',
      amount: row.amount,
      tx_hash: row.escrow_tx,
      network: row.network,
      timestamp: row.confirmed_at,
      actor: 'system',
    })
  }

  // Released / completed
  if (row.status === 'completed' || row.status === 'released') {
    events.push({
      id: `${row.id}-released`,
      type: 'final_release',
      amount: row.released_amount ?? row.amount,
      tx_hash: row.tx_hash,
      network: row.network,
      timestamp: row.updated_at,
      actor: 'system',
    })
  }

  // Partial release
  if (row.status === 'partial_released' && row.released_amount) {
    events.push({
      id: `${row.id}-partial`,
      type: 'partial_release',
      amount: row.released_amount,
      tx_hash: row.tx_hash,
      network: row.network,
      timestamp: row.updated_at,
      actor: 'system',
    })
  }

  // Refund
  if (row.status === 'refunded') {
    events.push({
      id: `${row.id}-refund`,
      type: 'refund',
      amount: row.amount,
      tx_hash: row.refund_tx ?? row.tx_hash,
      network: row.network,
      timestamp: row.updated_at,
      actor: 'system',
      note: 'Fondos devueltos al agente',
    })
  }

  // Disputed
  if (row.status === 'disputed') {
    events.push({
      id: `${row.id}-dispute`,
      type: 'dispute_hold',
      amount: row.amount,
      network: row.network,
      timestamp: row.updated_at,
      actor: 'arbitrator',
    })
  }

  // Instant charge
  if (row.status === 'charged' || row.type === 'bonus') {
    events.push({
      id: `${row.id}-charge`,
      type: 'instant_charge',
      amount: row.amount,
      tx_hash: row.tx_hash,
      network: row.network,
      timestamp: row.created_at,
      actor: 'agent',
    })
  }

  return events
}

/**
 * Transform a raw Supabase row into the PaymentData shape expected by
 * the PaymentStatus component.
 */
function rowToPaymentData(row: PaymentRow): PaymentData {
  const events = Array.isArray(row.events) && row.events.length > 0
    ? row.events
    : buildEventsFromRow(row)

  return {
    task_id: row.task_id,
    status: mapStatus(row),
    total_amount: row.amount,
    released_amount: row.released_amount ?? 0,
    currency: row.currency || 'USDC',
    escrow_tx: row.escrow_tx ?? row.tx_hash,
    escrow_contract: row.escrow_contract,
    network: row.network || 'base-sepolia',
    events,
    created_at: row.created_at,
    updated_at: row.updated_at,
  }
}

/**
 * Hook: useTaskPayment
 *
 * @param taskId  The task UUID to look up payment data for.
 *                Pass `null` or `undefined` to skip the query.
 */
export function useTaskPayment(taskId: string | null | undefined): UseTaskPaymentReturn {
  const [payment, setPayment] = useState<PaymentData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  // Fetch payment row from Supabase
  const fetchPayment = useCallback(async () => {
    if (!taskId) {
      setPayment(null)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const { data, error: fetchError } = await supabase
        .from('payments')
        .select('*')
        .eq('task_id', taskId)
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle()

      if (fetchError) throw fetchError

      if (data) {
        setPayment(rowToPaymentData(data as unknown as PaymentRow))
      } else {
        setPayment(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch payment'))
      setPayment(null)
    } finally {
      setLoading(false)
    }
  }, [taskId])

  // Initial fetch
  useEffect(() => {
    fetchPayment()
  }, [fetchPayment])

  // Real-time subscription for live updates
  useEffect(() => {
    if (!taskId) return

    const channel = supabase
      .channel(`task-payment-${taskId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'payments',
          filter: `task_id=eq.${taskId}`,
        },
        (payload) => {
          if (payload.eventType === 'INSERT' || payload.eventType === 'UPDATE') {
            const row = payload.new as unknown as PaymentRow
            setPayment(rowToPaymentData(row))
          } else if (payload.eventType === 'DELETE') {
            setPayment(null)
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [taskId])

  return {
    payment,
    loading,
    error,
    refetch: fetchPayment,
  }
}

export type { UseTaskPaymentReturn }
