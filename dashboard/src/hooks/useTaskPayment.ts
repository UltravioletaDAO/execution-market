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
  payment_network: string | null
  created_at: string
  updated_at: string
}

interface SubmissionPaymentRow {
  id: string
  payment_tx: string | null
  payment_amount: number | null
  paid_at: string | null
  verified_at: string | null
  submitted_at: string
}

interface UseTaskPaymentReturn {
  payment: PaymentData | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

const TX_HASH_REGEX = /^0x[a-fA-F0-9]{64}$/
const SETTLED_STATUSES = new Set(['confirmed', 'completed', 'available', 'funded', 'released'])

function getTaskPaymentUrl(taskId: string): string {
  const base = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
  if (base.endsWith('/api')) {
    return `${base}/v1/tasks/${taskId}/payment`
  }
  return `${base}/api/v1/tasks/${taskId}/payment`
}

function isPaymentEvent(value: unknown): value is PaymentEvent {
  if (!value || typeof value !== 'object') return false
  const maybe = value as Record<string, unknown>
  return (
    typeof maybe.id === 'string' &&
    typeof maybe.type === 'string' &&
    typeof maybe.actor === 'string' &&
    typeof maybe.timestamp === 'string' &&
    typeof maybe.network === 'string'
  )
}

function normalizeCanonicalPayment(data: unknown): PaymentData | null {
  if (!data || typeof data !== 'object') return null
  const maybe = data as Record<string, unknown>
  if (
    typeof maybe.task_id !== 'string' ||
    typeof maybe.status !== 'string' ||
    typeof maybe.total_amount !== 'number' ||
    typeof maybe.released_amount !== 'number' ||
    typeof maybe.network !== 'string' ||
    !Array.isArray(maybe.events) ||
    typeof maybe.created_at !== 'string' ||
    typeof maybe.updated_at !== 'string'
  ) {
    return null
  }

  const events = maybe.events.filter(isPaymentEvent)

  return {
    task_id: maybe.task_id,
    status: maybe.status as PaymentStatusType,
    total_amount: maybe.total_amount,
    released_amount: maybe.released_amount,
    currency: typeof maybe.currency === 'string' ? maybe.currency : 'USDC',
    escrow_tx: typeof maybe.escrow_tx === 'string' ? maybe.escrow_tx : undefined,
    escrow_contract: typeof maybe.escrow_contract === 'string' ? maybe.escrow_contract : undefined,
    network: maybe.network,
    events,
    created_at: maybe.created_at,
    updated_at: maybe.updated_at,
  }
}

function isMissingTableError(error: unknown, tableName: string): boolean {
  if (!error || typeof error !== 'object') return false
  const maybeError = error as { code?: string; message?: string; details?: string }
  if (maybeError.code !== 'PGRST205') return false
  const haystack = `${maybeError.message || ''} ${maybeError.details || ''}`.toLowerCase()
  return haystack.includes(`public.${tableName.toLowerCase()}`)
}

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
  if (row.chain_id === 1) return 'ethereum'
  if (row.chain_id === 137) return 'polygon'
  if (row.chain_id === 42161) return 'arbitrum'
  if (row.chain_id === 42220) return 'celo'
  if (row.chain_id === 143) return 'monad'
  if (row.chain_id === 43114) return 'avalanche'
  if (row.chain_id === 10) return 'optimism'
  if (row.chain_id === 1187947933) return 'skale'
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

function buildFromTaskFallback(task: TaskEscrowRow, submissionPayment: SubmissionPaymentRow | null): PaymentData | null {
  if (!task.escrow_tx && !task.escrow_id) {
    return null
  }

  const taskNetwork = task.payment_network || 'base'
  const payoutTx = pickTxHash(submissionPayment?.payment_tx)
  const payoutAmount = asNumber(submissionPayment?.payment_amount) || task.bounty_usd
  const payoutTimestamp =
    submissionPayment?.paid_at ??
    submissionPayment?.verified_at ??
    task.updated_at

  const status: PaymentStatusType =
    task.status === 'completed' || Boolean(payoutTx)
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
      network: taskNetwork,
      timestamp: task.created_at,
      actor: 'agent',
      note: reference ? formatReference(reference) : undefined,
    },
  ]

  if (status === 'completed') {
    events.push({
      id: `${task.id}-payout-complete`,
      type: 'final_release',
      amount: payoutAmount,
      tx_hash: payoutTx,
      network: taskNetwork,
      timestamp: payoutTimestamp,
      actor: 'system',
    })
  }

  if (status === 'refunded') {
    events.push({
      id: `${task.id}-refund`,
      type: 'refund',
      amount: task.bounty_usd,
      network: taskNetwork,
      timestamp: task.updated_at,
      actor: 'system',
    })
  }

  return {
    task_id: task.id,
    status,
    total_amount: task.bounty_usd,
    released_amount: status === 'completed' ? payoutAmount : 0,
    currency: 'USDC',
    escrow_tx: txHash,
    escrow_contract: undefined,
    network: taskNetwork,
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

function mergeSubmissionPaymentContext(base: PaymentData, submissionPayment: SubmissionPaymentRow | null): PaymentData {
  const payoutTx = pickTxHash(submissionPayment?.payment_tx)
  if (!submissionPayment || !payoutTx) {
    return base
  }

  const alreadyHasPayoutTx = base.events.some(
    (event) => event.type === 'final_release' && Boolean(event.tx_hash)
  )
  if (alreadyHasPayoutTx) {
    return base
  }

  const payoutAmount = asNumber(submissionPayment.payment_amount) || base.total_amount
  const payoutTimestamp =
    submissionPayment.paid_at ??
    submissionPayment.verified_at ??
    submissionPayment.submitted_at

  const nextEvents: PaymentEvent[] = [
    ...base.events,
    {
      id: `${base.task_id}-submission-payout-${submissionPayment.id}`,
      type: 'final_release',
      amount: payoutAmount,
      tx_hash: payoutTx,
      network: base.network || 'base',
      timestamp: payoutTimestamp,
      actor: 'system',
      note: 'Pago liquidado via facilitador x402',
    },
  ]

  const nextTotal = Math.max(base.total_amount, payoutAmount)
  const nextReleased = Math.max(base.released_amount, payoutAmount)

  return {
    ...base,
    status: base.status === 'refunded' ? base.status : 'completed',
    total_amount: nextTotal,
    released_amount: nextReleased,
    events: nextEvents,
    updated_at: payoutTimestamp,
  }
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

      const canonicalResponse = await fetch(getTaskPaymentUrl(taskId), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (canonicalResponse.ok) {
        const canonicalData = normalizeCanonicalPayment(await canonicalResponse.json())
        if (canonicalData) {
          setPayment(canonicalData)
          return
        }
      } else if (![401, 403, 404, 500, 503].includes(canonicalResponse.status)) {
        throw new Error(`Failed to fetch canonical task payment (${canonicalResponse.status})`)
      }

      const [paymentsResult, taskResult, submissionResult] = await Promise.all([
        supabase
          .from('payments')
          .select('*')
          .eq('task_id', taskId)
          .order('created_at', { ascending: true }),
        supabase
          .from('tasks')
          .select('id, status, bounty_usd, escrow_tx, escrow_id, payment_network, created_at, updated_at')
          .eq('id', taskId)
          .maybeSingle(),
        supabase
          .from('submissions')
          .select('id, payment_tx, payment_amount, paid_at, verified_at, submitted_at')
          .eq('task_id', taskId)
          .not('payment_tx', 'is', null)
          .order('submitted_at', { ascending: false })
          .limit(1)
          .maybeSingle(),
      ])

      if (paymentsResult.error && !isMissingTableError(paymentsResult.error, 'payments')) {
        throw paymentsResult.error
      }
      if (taskResult.error) throw taskResult.error
      if (submissionResult.error && !isMissingTableError(submissionResult.error, 'submissions')) {
        throw submissionResult.error
      }

      const taskEscrow = (taskResult.data as TaskEscrowRow | null) ?? null
      const rows = (paymentsResult.data as PaymentRow[] | null) ?? []
      const submissionPayment = (submissionResult.data as SubmissionPaymentRow | null) ?? null

      if (rows.length === 0) {
        setPayment(taskEscrow ? buildFromTaskFallback(taskEscrow, submissionPayment) : null)
        return
      }

      const aggregated = buildFromRows(taskId, rows)
      const withTaskContext = mergeTaskEscrowContext(aggregated, taskEscrow)
      setPayment(mergeSubmissionPaymentContext(withTaskContext, submissionPayment))
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
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'submissions',
          filter: `task_id=eq.${taskId}`,
        },
        () => {
          void fetchPayment()
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'tasks',
          filter: `id=eq.${taskId}`,
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
