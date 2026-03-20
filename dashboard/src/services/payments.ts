/**
 * Execution Market Payment API Service
 *
 * API service for payment operations including earnings,
 * payment history, escrow status, and withdrawals.
 */

import { supabase } from '../lib/supabase'
import type {
  Payment,
  EarningsSummary,
  EscrowStatus,
  PaymentHistoryResponse,
  FeeStructure,
  FeeCalculation,
} from './types'

// ============== EARNINGS ==============

/**
 * Get earnings summary for a worker
 */
export async function getEarnings(executorId: string): Promise<EarningsSummary> {
  // Get all payments for the executor
  const { data: payments, error } = await supabase
    .from('payments')
    .select('type, status, amount')
    .eq('executor_id', executorId)

  if (error) {
    throw new Error(`Failed to fetch earnings: ${error.message}`)
  }

  // Calculate totals
  let totalEarned = 0
  let totalWithdrawn = 0
  let pending = 0
  let taskCount = 0

  interface PaymentRecord {
    amount?: number
    status?: string
    type?: string
  }

  (payments || []).forEach((p: PaymentRecord) => {
    const amount = p.amount || 0

    if (p.status === 'confirmed') {
      if (p.type === 'task_payment' || p.type === 'bonus') {
        totalEarned += amount
        if (p.type === 'task_payment') taskCount++
      } else if (p.type === 'withdrawal') {
        totalWithdrawn += amount
      }
    } else if (p.status === 'pending') {
      if (p.type === 'task_payment' || p.type === 'bonus') {
        pending += amount
      }
    }
  })

  // Available balance is total earned minus withdrawn
  const availableBalance = totalEarned - totalWithdrawn

  return {
    totalEarned,
    totalWithdrawn,
    pending,
    available: availableBalance > 0 ? availableBalance : 0,
    taskCount,
    averagePerTask: taskCount > 0 ? totalEarned / taskCount : 0,
  }
}

// ============== PAYMENT HISTORY ==============

/**
 * Get payment history for an executor
 */
export async function getPaymentHistory(
  executorId: string,
  options: {
    limit?: number
    offset?: number
    type?: string
  } = {}
): Promise<PaymentHistoryResponse> {
  const { limit = 20, offset = 0, type } = options

  // Build query
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
    `, { count: 'exact' })
    .eq('executor_id', executorId)
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1)

  if (type) {
    query = query.eq('type', type)
  }

  const { data, error, count } = await query

  if (error) {
    throw new Error(`Failed to fetch payment history: ${error.message}`)
  }

  // Format payments
  interface PaymentRow {
    id: string
    type: string
    status: string
    amount: number
    currency?: string
    task_id?: string
    tasks?: { title?: string } | null
    tx_hash?: string
    network?: string
    created_at: string
    confirmed_at?: string
  }

  const payments: Payment[] = (data || []).map((p: PaymentRow) => ({
    id: p.id,
    type: p.type,
    status: p.status,
    amountUsdc: p.amount,
    currency: p.currency || 'USDC',
    taskId: p.task_id,
    taskTitle: (p.tasks as { title?: string } | null)?.title,
    txHash: p.tx_hash,
    network: p.network || 'polygon',
    createdAt: p.created_at,
    confirmedAt: p.confirmed_at,
  }))

  return {
    payments,
    total: count || 0,
    hasMore: (count || 0) > offset + payments.length,
  }
}

/**
 * Get recent payments for an executor
 */
export async function getRecentPayments(executorId: string, limit: number = 5): Promise<Payment[]> {
  const result = await getPaymentHistory(executorId, { limit })
  return result.payments
}

// ============== ESCROW STATUS ==============

/**
 * Get escrow status for a task
 */
export async function getEscrowStatus(taskId: string): Promise<EscrowStatus | null> {
  // Get task with escrow info
  const { data: task, error } = await supabase
    .from('tasks')
    .select('id, escrow_id, escrow_tx, bounty_usd, created_at')
    .eq('id', taskId)
    .single()

  if (error) {
    if (error.code === 'PGRST116') {
      return null
    }
    throw new Error(`Failed to fetch escrow status: ${error.message}`)
  }

  if (!task || !task.escrow_id) {
    return null
  }

  // Get escrow record if it exists in a separate table
  const { data: escrow } = await supabase
    .from('escrows')
    .select('*, net_bounty_usdc')
    .eq('task_id', taskId)
    .single()

  if (escrow) {
    return {
      escrowId: escrow.escrow_id || task.escrow_id,
      taskId,
      status: escrow.status,
      amountUsdc: task.bounty_usd || escrow.net_bounty_usdc || escrow.amount_usdc,
      depositTx: escrow.deposit_tx || task.escrow_tx,
      releaseTx: escrow.release_tx,
      refundTx: escrow.refund_tx,
      createdAt: escrow.created_at || task.created_at,
      updatedAt: escrow.updated_at,
    }
  }

  // Return basic escrow info from task
  return {
    escrowId: task.escrow_id,
    taskId,
    status: 'funded',
    amountUsdc: task.bounty_usd,
    depositTx: task.escrow_tx || undefined,
    createdAt: task.created_at,
  }
}

// ============== WITHDRAWALS ==============

/**
 * Request a withdrawal
 */
export async function requestWithdrawal(
  executorId: string,
  amount: number,
  destinationAddress: string
): Promise<{ withdrawalId: string; status: string }> {
  // Verify balance
  const earnings = await getEarnings(executorId)
  if (amount > earnings.available) {
    throw new Error(`Insufficient balance. Available: ${earnings.available.toFixed(2)} USDC`)
  }

  // Minimum withdrawal check
  const minWithdrawal = 5.0 // $5 minimum
  if (amount < minWithdrawal) {
    throw new Error(`Minimum withdrawal is ${minWithdrawal} USDC`)
  }

  // Create withdrawal request via RPC or insert
  const { data, error } = await supabase.rpc('request_withdrawal', {
    p_executor_id: executorId,
    p_amount: amount,
    p_destination_address: destinationAddress,
  })

  if (error) {
    // If RPC doesn't exist, try direct insert
    if (error.code === '42883') {
      const { data: withdrawal, error: insertError } = await supabase
        .from('withdrawals')
        .insert({
          executor_id: executorId,
          amount_usdc: amount,
          destination_address: destinationAddress,
          status: 'pending',
          requested_at: new Date().toISOString(),
        })
        .select()
        .single()

      if (insertError) {
        throw new Error(`Failed to request withdrawal: ${insertError.message}`)
      }

      return {
        withdrawalId: withdrawal.id,
        status: 'pending',
      }
    }

    throw new Error(`Failed to request withdrawal: ${error.message}`)
  }

  return data
}

/**
 * Get withdrawal history
 */
export async function getWithdrawalHistory(
  executorId: string,
  limit: number = 20
): Promise<Array<{
  id: string
  amountUsdc: number
  destinationAddress: string
  status: string
  txHash?: string
  requestedAt: string
  processedAt?: string
}>> {
  const { data, error } = await supabase
    .from('withdrawals')
    .select('*')
    .eq('executor_id', executorId)
    .order('requested_at', { ascending: false })
    .limit(limit)

  if (error) {
    // Table might not exist yet
    if (error.code === '42P01') {
      return []
    }
    throw new Error(`Failed to fetch withdrawal history: ${error.message}`)
  }

  interface WithdrawalRow {
    id: string
    amount_usdc: number
    destination_address: string
    status: string
    tx_hash?: string
    requested_at: string
    processed_at?: string
  }

  return (data || []).map((w: WithdrawalRow) => ({
    id: w.id,
    amountUsdc: w.amount_usdc,
    destinationAddress: w.destination_address,
    status: w.status,
    txHash: w.tx_hash,
    requestedAt: w.requested_at,
    processedAt: w.processed_at,
  }))
}

// ============== AGENT PAYMENT STATS ==============

/**
 * Get payment statistics for an agent (total spent, etc.)
 */
export async function getAgentPaymentStats(agentId: string): Promise<{
  totalSpent: number
  tasksPaid: number
  averagePayment: number
  pendingEscrow: number
}> {
  // Get completed tasks for this agent
  const { data: tasks, error } = await supabase
    .from('tasks')
    .select('id, bounty_usd, status')
    .eq('agent_id', agentId)

  if (error) {
    throw new Error(`Failed to fetch agent stats: ${error.message}`)
  }

  let totalSpent = 0
  let tasksPaid = 0
  let pendingEscrow = 0

  interface TaskRecord {
    id: string
    bounty_usd?: number
    status?: string
  }

  (tasks || []).forEach((t: TaskRecord) => {
    if (t.status === 'completed') {
      totalSpent += t.bounty_usd || 0
      tasksPaid++
    } else if (['published', 'accepted', 'in_progress', 'submitted'].includes(t.status || '')) {
      pendingEscrow += t.bounty_usd || 0
    }
  })

  return {
    totalSpent,
    tasksPaid,
    averagePayment: tasksPaid > 0 ? totalSpent / tasksPaid : 0,
    pendingEscrow,
  }
}

// ============== FEE STRUCTURE ==============

/**
 * Get platform fee structure
 */
export async function getFeeStructure(): Promise<FeeStructure> {
  // Fee structure is typically configured in environment or backend
  // This returns the standard Execution Market fee structure
  return {
    ratesByCategory: {
      physical_presence: {
        ratePercent: 13.0,
        description: 'Tasks requiring physical presence (delivery, verification)',
      },
      knowledge_access: {
        ratePercent: 13.0,
        description: 'Tasks requiring specialized knowledge or access',
      },
      human_authority: {
        ratePercent: 13.0,
        description: 'Tasks requiring human authorization or signatures',
      },
      simple_action: {
        ratePercent: 13.0,
        description: 'Simple, quick tasks',
      },
      digital_physical: {
        ratePercent: 13.0,
        description: 'Tasks bridging digital and physical worlds',
      },
    },
    distribution: {
      workerPercent: '87%',
      platformPercent: '13%',
    },
    limits: {
      minimumFee: 0.50,
      maximumRatePercent: 13.0,
    },
  }
}

/**
 * Calculate fee for a bounty amount
 */
export async function calculateFee(bountyUsd: number, category: string): Promise<FeeCalculation> {
  const feeStructure = await getFeeStructure()
  const categoryInfo = feeStructure.ratesByCategory[category]

  if (!categoryInfo) {
    throw new Error(`Unknown category: ${category}`)
  }

  const feeRatePercent = categoryInfo.ratePercent
  const feeAmount = Math.max(
    feeStructure.limits.minimumFee,
    (bountyUsd * feeRatePercent) / 100
  )
  const workerAmount = bountyUsd - feeAmount
  const workerPercent = (workerAmount / bountyUsd) * 100

  return {
    bountyUsd,
    category,
    workerAmount,
    workerPercent,
    feeAmount,
    feeRatePercent,
  }
}
