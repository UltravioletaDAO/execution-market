/**
 * Execution Market API Service Types
 *
 * TypeScript types for the API service layer.
 * These types mirror the MCP server models and database types.
 */

// Re-export database types for consistency
export type {
  TaskCategory,
  TaskStatus,
  EvidenceType,
  DisputeStatus,
  EvidenceSchema,
  Location,
  Executor,
  Task,
  Submission,
  Dispute,
  ReputationLog,
  TaskApplication,
} from '../types/database'

// ============== API REQUEST TYPES ==============

/**
 * Filters for fetching tasks
 */
export interface TaskFilters {
  agentId?: string
  executorId?: string
  status?: string | string[]
  category?: string
  minBounty?: number
  maxBounty?: number
  locationHint?: string
  limit?: number
  offset?: number
}

/**
 * Data for creating a new task
 */
export interface CreateTaskData {
  agentId: string
  title: string
  instructions: string
  category: string
  bountyUsd: number
  deadlineHours: number
  evidenceRequired: string[]
  evidenceOptional?: string[]
  locationHint?: string
  minReputation?: number
  paymentToken?: string
  paymentNetwork?: string
  /**
   * Ring 2 arbiter mode for automated evidence verification.
   * - 'manual' (default): agent reviews and approves submissions
   * - 'auto':   ArbiterService auto-releases/refunds based on PHOTINT + LLM verdict
   * - 'hybrid': arbiter recommends, agent confirms before payment
   */
  arbiterMode?: 'manual' | 'auto' | 'hybrid'
}

/**
 * Data for applying to a task
 */
export interface ApplyToTaskData {
  taskId: string
  executorId: string
  message?: string
  proposedDeadline?: string
}

/**
 * Evidence data for submission
 */
export interface Evidence {
  type: string
  value?: string
  fileUrl?: string
  filename?: string
  mimeType?: string
  metadata?: Record<string, unknown>
}

/**
 * Data for submitting work
 */
export interface SubmitWorkData {
  taskId: string
  executorId: string
  evidence: Record<string, Evidence>
  notes?: string
}

/**
 * Verdict options for submissions
 */
export type SubmissionVerdict = 'accepted' | 'disputed' | 'more_info_requested'

/**
 * Data for approving/rejecting a submission
 */
export interface ApproveSubmissionData {
  submissionId: string
  agentId: string
  verdict: SubmissionVerdict
  notes?: string
  rating?: number
}

/**
 * Data for rejecting a submission
 */
export interface RejectSubmissionData {
  submissionId: string
  agentId: string
  feedback: string
}

/**
 * Data for cancelling a task
 */
export interface CancelTaskData {
  taskId: string
  agentId: string
  reason?: string
}

/**
 * Data for assigning a task
 */
export interface AssignTaskData {
  taskId: string
  agentId: string
  executorId: string
  notes?: string
}

// ============== API RESPONSE TYPES ==============

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  data: T[]
  total: number
  count: number
  offset: number
  hasMore: boolean
}

/**
 * Task with executor details
 */
export interface TaskWithExecutor extends Omit<import('../types/database').Task, 'executor'> {
  executor?: {
    id: string
    display_name: string | null
    wallet_address: string
    reputation_score: number
  }
}

/**
 * Submission with task and executor details
 */
export interface SubmissionWithDetails extends Omit<import('../types/database').Submission, 'task' | 'executor'> {
  task?: TaskWithExecutor
  executor?: {
    id: string
    display_name: string | null
    wallet_address: string
    reputation_score: number
  }
}

/**
 * Application with task details
 */
export type ApplicationWithTask = import('../types/database').TaskApplication & {
  task?: TaskWithExecutor
}

// ============== PAYMENT TYPES ==============

/**
 * Payment record
 */
export interface Payment {
  id: string
  type: 'task_payment' | 'withdrawal' | 'bonus' | 'refund'
  status: 'pending' | 'confirmed' | 'failed' | 'available'
  amountUsdc: number
  currency: string
  taskId?: string
  taskTitle?: string
  txHash?: string
  network: string
  createdAt: string
  confirmedAt?: string
}

/**
 * Earnings summary
 */
export interface EarningsSummary {
  totalEarned: number
  totalWithdrawn: number
  pending: number
  available: number
  taskCount: number
  averagePerTask: number
}

/**
 * Payment strategy (matches PaymentOperator 5 modes)
 */
export type PaymentStrategy =
  | 'escrow_capture'       // Scenario 1: AUTHORIZE → RELEASE
  | 'escrow_cancel'        // Scenario 2: AUTHORIZE → REFUND IN ESCROW
  | 'instant_payment'      // Scenario 3: CHARGE (direct, no escrow)
  | 'partial_payment'      // Scenario 4: AUTHORIZE → partial RELEASE + REFUND
  | 'dispute_resolution'   // Scenario 5: AUTHORIZE → RELEASE → REFUND POST ESCROW

/**
 * Task payment tier
 */
export type PaymentTier = 'micro' | 'standard' | 'premium' | 'enterprise'

/**
 * Tier timing constraints (set at AUTHORIZE, enforced by contract)
 */
export interface TierTiming {
  tier: PaymentTier
  preApprovalHours: number
  authorizationHours: number
  disputeWindowHours: number
}

/**
 * Tier timing lookup
 */
export const TIER_TIMINGS: Record<PaymentTier, TierTiming> = {
  micro:      { tier: 'micro',      preApprovalHours: 1,  authorizationHours: 2,    disputeWindowHours: 24 },
  standard:   { tier: 'standard',   preApprovalHours: 2,  authorizationHours: 24,   disputeWindowHours: 168 },
  premium:    { tier: 'premium',    preApprovalHours: 4,  authorizationHours: 48,   disputeWindowHours: 336 },
  enterprise: { tier: 'enterprise', preApprovalHours: 24, authorizationHours: 168,  disputeWindowHours: 720 },
}

/**
 * Get tier from bounty amount
 */
export function getTierFromAmount(amountUsdc: number): PaymentTier {
  if (amountUsdc < 5) return 'micro'
  if (amountUsdc < 50) return 'standard'
  if (amountUsdc < 200) return 'premium'
  return 'enterprise'
}

/**
 * Escrow status
 */
export interface EscrowStatus {
  escrowId: string
  taskId: string
  status: 'created' | 'funded' | 'partial_released' | 'released' | 'refunded' | 'disputed' | 'charged'
  strategy?: PaymentStrategy
  tier?: PaymentTier
  amountUsdc: number
  releasedUsdc?: number
  refundedUsdc?: number
  depositTx?: string
  releaseTx?: string
  refundTx?: string
  timing?: {
    preApprovalExpiry?: string
    authorizationExpiry?: string
    refundExpiry?: string
  }
  createdAt: string
  updatedAt?: string
}

/**
 * Payment history response
 */
export interface PaymentHistoryResponse {
  payments: Payment[]
  total: number
  hasMore: boolean
}

// ============== WORKER TASK RESPONSE TYPES ==============

/**
 * Worker's tasks response
 */
export interface WorkerTasksResponse {
  assignedTasks: TaskWithExecutor[]
  applications: ApplicationWithTask[]
  recentSubmissions: SubmissionWithDetails[]
  totals: {
    assigned: number
    pendingApplications: number
    submissions: number
  }
}

// ============== AGENT ANALYTICS TYPES ==============

/**
 * Agent analytics response
 */
export interface AgentAnalytics {
  totals: {
    total: number
    completed: number
    completionRate: number
    totalPaid: number
    avgBounty: number
  }
  byStatus: Record<string, number>
  byCategory: Record<string, number>
  averageTimes: {
    toAccept: string
    toComplete: string
    toApprove: string
  }
  topWorkers: Array<{
    id: string
    displayName: string | null
    reputation: number
    tasksCompleted: number
  }>
  periodDays: number
}

// ============== FEE TYPES ==============

/**
 * Fee structure
 */
export interface FeeStructure {
  ratesByCategory: Record<string, {
    ratePercent: number
    description: string
  }>
  distribution: {
    workerPercent: string
    platformPercent: string
  }
  limits: {
    minimumFee: number
    maximumRatePercent: number
  }
  treasuryWallet?: string
}

/**
 * Fee calculation result
 */
export interface FeeCalculation {
  bountyUsd: number
  category: string
  workerAmount: number
  workerPercent: number
  feeAmount: number
  feeRatePercent: number
}

// ============== API ERROR TYPE ==============

/**
 * API error response
 */
export interface ApiError {
  message: string
  code?: string
  status?: number
  details?: Record<string, unknown>
}
