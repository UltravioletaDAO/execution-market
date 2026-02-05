/**
 * useTaskPayment - Fetch payment data for a specific task
 *
 * Handles both canonical and legacy payment column names and can
 * synthesize a payment timeline from task escrow metadata when
 * payment rows are not present yet.
 */

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import type { PaymentData, PaymentStatusType, PaymentEvent } from '../components/PaymentStatus'

interface PaymentRow {
  id: string
  task_id: string | null
  status: string
  payment_type?: string | null
  type?: string | null
  amount?: number | null
  amount_usdc?: number | null
  total_amount_usdc?: number | null
  released_amount?: number | null
  released_amount_usdc?: number | null
  net_amount_usdc?: number | null
  currency?: string | null
  tx_hash?: string | null
  transaction_hash?: string | null
  escrow_tx?: string | null
  funding_tx?: string | null
  deposit_tx?: string | null
  release_tx?: string | null
  refund_tx?: string | null
  network?: string | null
  chain_id?: number | null
  created_at: string
  updated_at?: string | null
  confirmed_at?: string | null
  completed_at?: string | null
}

interface TaskEscrowRow {
  id: string
  status: string
  bounty_usd: number
  escrow_tx: string | null
  escrow_id: string | null
  created_at: string
  updated_at: string
}

interface UseTaskPaymentReturn {
  payment: PaymentData | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

const TX_HASH_REGEX = /^0x[a-fA-F0-9]{64}$/
const SETTLED_STATUSES = new Set(['confirmed', 'completed', 'available', 'funded', 'released'])

function isTxHash(value?: string | null): value is string {
  return typeof value === 'string' && TX_HASH_REGEX.test(value.trim())
}

function asNumber(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return 0
}

function normalizeAmount(row: PaymentRow): number {
  return asNumber(
    row.amount ??
      row.amount_usdc ??
      row.total_amount_usdc ??
      row.net_amount_usdc ??
      row.released_amount ??
      row.released_amount_usdc ??
      0
  )
}

function normalizeType(row: PaymentRow): string {
  return (row.payment_type ?? row.type ?? 'task_payment').toLowerCase()
}

function normalizeNetwork(row: Pick<PaymentRow, 'network' | 'chain_id'>): string {
  if (row.network) return row.network
  if (row.chain_id === 8453) return 'base'
  if (row.chain_id === 84532) return 'base-sepolia'
  return 'base'
}

function normalizeTimestamp(row: PaymentRow): string {
  return row.completed_at ?? row.confirmed_at ?? row.updated_at ?? row.created_at
}

function pickTxHash(...values: Array<string | null | undefined>): string | undefined {
  return values.find((value) => isTxHash(value))
}

function pickReference(...values: Array<string | null | undefined>): string | undefined {
  return values.find(
    (value): value is string => typeof value === 'string' && value.trim().length > 0 && !isTxHash(value)
  )
}

function formatReference(reference: string): string {
  const normalized = reference.trim()
  if (!normalized) return 'Autorizacion x402'
  if (normalized.length > 80 || normalized.startsWith('eyJ')) {
    return `Autorizacion x402: ${normalized.slice(0, 12)}...${normalized.slice(-8)}`
  }
  return `Referencia x402: ${normalized}`
}

function eventFromRow(row: PaymentRow): PaymentEvent | null {
  const type = normalizeType(row)
  const amount = normalizeAmount(row)
  const status = (row.status ?? '').toLowerCase()
  const txHash = pickTxHash(
    row.transaction_hash,
    row.tx_hash,
    row.release_tx,
    row.refund_tx,
    row.deposit_tx,
    row.funding_tx,
    row.escrow_tx
  )
  const reference = pickReference(
    row.transaction_hash,
    row.tx_hash,
    row.release_tx,
    row.refund_tx,
    row.deposit_tx,
    row.funding_tx,
    row.escrow_tx
  )

  let eventType: PaymentEvent['type']
  let actor: PaymentEvent['actor'] = 'system'

  if (status === 'disputed') {
    eventType = 'dispute_hold'
    actor = 'arbitrator'
  } else if (type === 'refund' || type === 'partial_refund' || status === 'refunded' || status === 'cancelled') {
    eventType = 'refund'
  } else if (type === 'partial_release' || status === 'partial_released') {
    eventType = 'partial_release'
  } else if (type === 'final_release' || type === 'full_release') {
    eventType = 'final_release'
  } else if (type === 'bonus') {
    eventType = 'instant_charge'
    actor = 'agent'
  } else if (type === 'escrow_create' || type === 'deposit') {
    eventType = 'escrow_created'
    actor = 'agent'
  } else if (type === 'task_payment') {
    eventType = SETTLED_STATUSES.has(status) ? 'final_release' : 'escrow_created'
    actor = SETTLED_STATUSES.has(status) ? 'system' : 'agent'
  } else {
    eventType = status === 'completed' ? 'final_release' : 'escrow_created'
  }

  return {
    id: `${row.id}-${eventType}`,
    type: eventType,
    amount: amount > 0 ? amount : undefined,
    tx_hash: txHash,
    network: normalizeNetwork(row),
    timestamp: normalizeTimestamp(row),
    actor,
    note: reference ? formatReference(reference) : undefined,
  }
}

function deriveStatus(rows: PaymentRow[]): PaymentStatusType {
  const statuses = rows.map((row) => (row.status ?? '').toLowerCase())
  const paymentTypes = rows.map((row) => normalizeType(row))

  if (statuses.includes('disputed')) return 'disputed'
  if (statuses.includes('refunded') || statuses.includes('cancelled') || paymentTypes.includes('refund') || paymentTypes.includes('partial_refund')) return 'refunded'
  if (statuses.includes('partial_released') || paymentTypes.includes('partial_release')) return 'partial_released'
  if (paymentTypes.includes('final_release') || paymentTypes.includes('full_release')) return 'completed'

  const hasTaskPaymentSettled = rows.some(
    (row) => normalizeType(row) === 'task_payment' && SETTLED_STATUSES.has((row.status ?? '').toLowerCase())
  )
  if (hasTaskPaymentSettled) return 'completed'

  const hasEscrowFunding = rows.some((row) => {
    const type = normalizeType(row)
    const status = (row.status ?? '').toLowerCase()
    return type === 'escrow_create' || type === 'deposit' || status === 'funded' || status === 'escrowed' || status === 'confirmed'
  })
  if (hasEscrowFunding) return 'escrowed'

  return 'pending'
}

function buildFromRows(taskId: string, rows: PaymentRow[]): PaymentData {
  const sortedRows = [...rows].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )
  const latestRow = sortedRows[sortedRows.length - 1]

  const events = sortedRows
    .map((row) => eventFromRow(row))
    .filter((event): event is PaymentEvent => Boolean(event))

  let totalAmount = 0
  let releasedAmount = 0

  for (const row of sortedRows) {
    const amount = normalizeAmount(row)
    const type = normalizeType(row)
    const status = (row.status ?? '').toLowerCase()

    if (type === 'escrow_create' || type === 'deposit') {
      totalAmount = Math.max(totalAmount, amount)
    }

    if (type === 'task_payment' && totalAmount === 0) {
      totalAmount = Math.max(totalAmount, amount)
    }

    if (['partial_release', 'final_release', 'full_release', 'task_payment', 'bonus'].includes(type) && SETTLED_STATUSES.has(status)) {
      releasedAmount += amount
    }
  }

  if (totalAmount === 0) {
    totalAmount = Math.max(...sortedRows.map((row) => normalizeAmount(row)), 0)
  }
  if (releasedAmount > totalAmount) {
    totalAmount = releasedAmount
  }

  return {
    task_id: taskId,
    status: deriveStatus(sortedRows),
    total_amount: totalAmount,
    released_amount: releasedAmount,
    currency: latestRow.currency || 'USDC',
    escrow_tx: pickTxHash(
      latestRow.escrow_tx,
      latestRow.funding_tx,
      latestRow.deposit_tx,
      ...sortedRows.map((row) => row.escrow_tx),
      ...sortedRows.map((row) => row.funding_tx),
      ...sortedRows.map((row) => row.deposit_tx)
    ),
    escrow_contract: undefined,
    network: normalizeNetwork(latestRow),
    events,
    created_at: sortedRows[0].created_at,
    updated_at: latestRow.updated_at ?? latestRow.completed_at ?? latestRow.created_at,
  }
}

function buildFromTaskFallback(task: TaskEscrowRow): PaymentData | null {
  if (!task.escrow_tx && !task.escrow_id) {
    return null
  }

  const status: PaymentStatusType =
    task.status === 'completed'
      ? 'completed'
      : task.status === 'cancelled' || task.status === 'expired'
      ? 'refunded'
      : 'escrowed'

  const txHash = pickTxHash(task.escrow_tx)
  const reference = pickReference(task.escrow_tx)
  const events: PaymentEvent[] = [
    {
      id: `${task.id}-escrow-created`,
      type: 'escrow_created',
      amount: task.bounty_usd,
      tx_hash: txHash,
      network: 'base',
      timestamp: task.created_at,
      actor: 'agent',
      note: reference ? formatReference(reference) : undefined,
    },
  ]

  if (status === 'completed') {
    events.push({
      id: `${task.id}-payout-complete`,
      type: 'final_release',
      amount: task.bounty_usd,
      network: 'base',
      timestamp: task.updated_at,
      actor: 'system',
    })
  }

  if (status === 'refunded') {
    events.push({
      id: `${task.id}-refund`,
      type: 'refund',
      amount: task.bounty_usd,
      network: 'base',
      timestamp: task.updated_at,
      actor: 'system',
    })
  }

  return {
    task_id: task.id,
    status,
    total_amount: task.bounty_usd,
    released_amount: status === 'completed' ? task.bounty_usd : 0,
    currency: 'USDC',
    escrow_tx: txHash,
    escrow_contract: undefined,
    network: 'base',
    events,
    created_at: task.created_at,
    updated_at: task.updated_at,
  }
}

function mergeTaskEscrowContext(base: PaymentData, task: TaskEscrowRow | null): PaymentData {
  if (!task || (!task.escrow_tx && !task.escrow_id)) {
    return base
  }

  const hasEscrowEvent = base.events.some((event) => event.type === 'escrow_created' || event.type === 'escrow_funded')
  const taskEscrowHash = pickTxHash(task.escrow_tx)
  const taskReference = pickReference(task.escrow_tx)
  const merged = { ...base, events: [...base.events] }

  if (!hasEscrowEvent) {
    merged.events.push({
      id: `${task.id}-escrow-created-fallback`,
      type: 'escrow_created',
      amount: task.bounty_usd || undefined,
      tx_hash: taskEscrowHash,
      network: merged.network || 'base',
      timestamp: task.created_at,
      actor: 'agent',
      note: taskReference ? formatReference(taskReference) : undefined,
    })
  }

  if (!merged.escrow_tx && taskEscrowHash) {
    merged.escrow_tx = taskEscrowHash
  }

  if (!merged.total_amount && task.bounty_usd > 0) {
    merged.total_amount = task.bounty_usd
  }

  if (merged.status === 'pending' && task.escrow_tx) {
    merged.status = 'escrowed'
  }

  return merged
}

export function useTaskPayment(taskId: string | null | undefined): UseTaskPaymentReturn {
  const [payment, setPayment] = useState<PaymentData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const fetchPayment = useCallback(async () => {
    if (!taskId) {
      setPayment(null)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const [paymentsResult, taskResult] = await Promise.all([
        supabase
          .from('payments')
          .select('*')
          .eq('task_id', taskId)
          .order('created_at', { ascending: true }),
        supabase
          .from('tasks')
          .select('id, status, bounty_usd, escrow_tx, escrow_id, created_at, updated_at')
          .eq('id', taskId)
          .maybeSingle(),
      ])

      if (paymentsResult.error) throw paymentsResult.error
      if (taskResult.error) throw taskResult.error

      const taskEscrow = (taskResult.data as TaskEscrowRow | null) ?? null
      const rows = (paymentsResult.data as PaymentRow[] | null) ?? []

      if (rows.length === 0) {
        setPayment(taskEscrow ? buildFromTaskFallback(taskEscrow) : null)
        return
      }

      const aggregated = buildFromRows(taskId, rows)
      setPayment(mergeTaskEscrowContext(aggregated, taskEscrow))
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch payment'))
      setPayment(null)
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    void fetchPayment()
  }, [fetchPayment])

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
        () => {
          void fetchPayment()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [taskId, fetchPayment])

  return {
    payment,
    loading,
    error,
    refetch: fetchPayment,
  }
}

export type { UseTaskPaymentReturn }
