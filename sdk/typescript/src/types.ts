/**
 * Chamba SDK Type Definitions
 *
 * Complete type system for the Chamba human task execution layer.
 */

// =============================================================================
// Enums
// =============================================================================

/**
 * Task status values representing the lifecycle of a task.
 */
export type TaskStatus =
  | 'published'
  | 'accepted'
  | 'in_progress'
  | 'submitted'
  | 'verifying'
  | 'completed'
  | 'disputed'
  | 'expired'
  | 'cancelled';

/**
 * Task categories defining what type of human action is needed.
 */
export type TaskCategory =
  | 'physical_presence'   // Verify presence at location
  | 'knowledge_access'    // Get information from real world
  | 'human_authority'     // Tasks requiring human action/authority
  | 'simple_action'       // Quick physical tasks
  | 'digital_physical';   // Bridge digital and physical

/**
 * Evidence types that can be required or provided.
 */
export type EvidenceType =
  | 'photo'           // Standard photo
  | 'photo_geo'       // Photo with GPS metadata
  | 'video'           // Video evidence (5-60 seconds)
  | 'document'        // Document upload (PDF or image)
  | 'signature'       // Signature capture
  | 'text_response';  // Text answer

/**
 * Verification tiers for task approval.
 */
export type VerificationTier =
  | 'auto'    // 0.95+ pre-check auto-approves
  | 'ai'      // AI (Claude Vision) reviews
  | 'manual'; // Human review required

/**
 * Payment tokens supported by Chamba.
 */
export type PaymentToken = 'USDC' | 'USDT' | 'DAI';

// =============================================================================
// Core Entities
// =============================================================================

/**
 * A Chamba task representing work to be done by a human.
 */
export interface Task {
  /** Unique task identifier */
  id: string;
  /** Short task title (5-255 chars) */
  title: string;
  /** Detailed instructions (20-5000 chars) */
  instructions: string;
  /** Task category */
  category: TaskCategory;
  /** Payment amount in USD */
  bountyUsd: number;
  /** Current task status */
  status: TaskStatus;
  /** Task deadline */
  deadline: Date;
  /** Required evidence types */
  evidenceRequired: EvidenceType[];
  /** Optional evidence types */
  evidenceOptional?: EvidenceType[];
  /** Location hint for workers */
  locationHint?: string;
  /** ID of worker who accepted the task */
  executorId?: string;
  /** Task creation timestamp */
  createdAt: Date;
  /** Minimum worker reputation (0-100) */
  minReputation?: number;
  /** Payment token */
  paymentToken: PaymentToken;
  /** Verification tier */
  verificationTier?: VerificationTier;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * A submission of evidence for a task.
 */
export interface Submission {
  /** Unique submission identifier */
  id: string;
  /** Associated task ID */
  taskId: string;
  /** Worker who submitted */
  executorId: string;
  /** Submitted evidence */
  evidence: Evidence;
  /** Submission status */
  status: 'pending' | 'approved' | 'rejected';
  /** AI pre-check score (0-1) */
  preCheckScore: number;
  /** Submission timestamp */
  submittedAt: Date;
  /** Optional notes from worker */
  notes?: string;
}

/**
 * Evidence provided in a submission.
 */
export interface Evidence {
  /** Photo URL(s) */
  photo?: string | string[];
  /** Photo with GPS data */
  photoGeo?: {
    url: string;
    latitude: number;
    longitude: number;
    accuracy?: number;
  };
  /** Video URL */
  video?: string;
  /** Document URL */
  document?: string;
  /** Signature data URL */
  signature?: string;
  /** Text response */
  textResponse?: string;
  /** Raw evidence data */
  [key: string]: unknown;
}

/**
 * Result of a completed task.
 */
export interface TaskResult {
  /** Task ID */
  taskId: string;
  /** Final status */
  status: TaskStatus;
  /** Collected evidence */
  evidence: Evidence;
  /** Text answer if provided */
  answer?: string;
  /** Completion timestamp */
  completedAt?: Date;
  /** Payment transaction hash */
  paymentTx?: string;
}

// =============================================================================
// API Input Types
// =============================================================================

/**
 * Input for creating a new task.
 */
export interface CreateTaskInput {
  /** Short task title (5-255 chars) */
  title: string;
  /** Detailed instructions (20-5000 chars) */
  instructions: string;
  /** Task category */
  category: TaskCategory;
  /** Payment amount in USD ($0.50-$10,000) */
  bountyUsd: number;
  /** Hours until deadline (1-720) */
  deadlineHours: number;
  /** Required evidence types (1-5 types) */
  evidenceRequired: EvidenceType[];
  /** Optional evidence types */
  evidenceOptional?: EvidenceType[];
  /** Location hint for workers */
  locationHint?: string;
  /** Minimum worker reputation (0-100) */
  minReputation?: number;
  /** Payment token (default: USDC) */
  paymentToken?: PaymentToken;
  /** Verification tier */
  verificationTier?: VerificationTier;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Options for listing tasks.
 */
export interface ListTasksOptions {
  /** Filter by status */
  status?: TaskStatus | TaskStatus[];
  /** Filter by category */
  category?: TaskCategory;
  /** Limit results */
  limit?: number;
  /** Pagination offset */
  offset?: number;
  /** Sort field */
  sortBy?: 'createdAt' | 'deadline' | 'bountyUsd';
  /** Sort order */
  sortOrder?: 'asc' | 'desc';
}

/**
 * Options for waiting for task completion.
 */
export interface WaitOptions {
  /** Maximum wait time in hours (default: 24) */
  timeoutHours?: number;
  /** Polling interval in seconds (default: 30) */
  pollInterval?: number;
  /** Callback on status change */
  onStatusChange?: (status: TaskStatus) => void;
}

// =============================================================================
// API Response Types
// =============================================================================

/**
 * Paginated list response.
 */
export interface PaginatedResponse<T> {
  /** Items in this page */
  items: T[];
  /** Total count */
  total: number;
  /** Has more items */
  hasMore: boolean;
  /** Next page offset */
  nextOffset?: number;
}

/**
 * Batch create response.
 */
export interface BatchCreateResponse {
  /** Created tasks */
  tasks: Task[];
  /** Number of successful creates */
  succeeded: number;
  /** Number of failed creates */
  failed: number;
  /** Errors if any */
  errors?: Array<{
    index: number;
    error: string;
  }>;
}

/**
 * Analytics data.
 */
export interface Analytics {
  /** Time period in days */
  periodDays: number;
  /** Total tasks created */
  tasksCreated: number;
  /** Total tasks completed */
  tasksCompleted: number;
  /** Completion rate */
  completionRate: number;
  /** Average completion time in hours */
  avgCompletionTimeHours: number;
  /** Total spent in USD */
  totalSpentUsd: number;
  /** Tasks by status */
  byStatus: Record<TaskStatus, number>;
  /** Tasks by category */
  byCategory: Record<TaskCategory, number>;
}

// =============================================================================
// Webhook Types
// =============================================================================

/**
 * Webhook event types.
 */
export type WebhookEventType =
  | 'task.created'
  | 'task.accepted'
  | 'task.submitted'
  | 'task.completed'
  | 'task.disputed'
  | 'task.expired'
  | 'task.cancelled'
  | 'payment.sent';

/**
 * Base webhook event structure.
 */
export interface WebhookEvent<T extends WebhookEventType = WebhookEventType> {
  /** Event ID */
  id: string;
  /** Event type */
  type: T;
  /** Event timestamp */
  timestamp: Date;
  /** Event data */
  data: WebhookEventData[T];
}

/**
 * Event data by type.
 */
export interface WebhookEventData {
  'task.created': { taskId: string; task: Task };
  'task.accepted': { taskId: string; executorId: string };
  'task.submitted': { taskId: string; submissionId: string; submission: Submission };
  'task.completed': { taskId: string; submission: Submission; paymentTx?: string };
  'task.disputed': { taskId: string; reason: string; initiatedBy: 'agent' | 'executor' };
  'task.expired': { taskId: string };
  'task.cancelled': { taskId: string; reason?: string };
  'payment.sent': { taskId: string; amount: number; token: PaymentToken; txHash: string };
}

// =============================================================================
// Error Types
// =============================================================================

/**
 * Chamba API error.
 */
export interface ChambaError {
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** HTTP status code */
  statusCode: number;
  /** Additional details */
  details?: Record<string, unknown>;
}

/**
 * Validation error details.
 */
export interface ValidationError {
  /** Field that failed validation */
  field: string;
  /** Error message */
  message: string;
  /** Received value */
  received?: unknown;
}

// =============================================================================
// Additional Types for API Modules
// =============================================================================

/**
 * Alias for CreateTaskInput for compatibility.
 */
export type TaskCreateParams = CreateTaskInput;

/**
 * Parameters for updating a task.
 */
export interface TaskUpdateParams {
  /** Updated title */
  title?: string;
  /** Updated instructions */
  instructions?: string;
  /** Updated bounty */
  bountyUsd?: number;
  /** Updated deadline hours */
  deadlineHours?: number;
  /** Updated location hint */
  locationHint?: string;
  /** Updated metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Generic paginated list response.
 */
export interface ListResponse<T> {
  /** Items in this page */
  data: T[];
  /** Total count */
  total: number;
  /** Has more items */
  hasMore: boolean;
  /** Next page cursor */
  nextCursor?: string;
}

/**
 * Pagination parameters.
 */
export interface PaginationParams {
  /** Number of items to return */
  limit?: number;
  /** Number of items to skip */
  offset?: number;
  /** Pagination cursor */
  cursor?: string;
}

/**
 * Webhook endpoint configuration.
 */
export interface WebhookEndpoint {
  /** Unique endpoint identifier */
  id: string;
  /** Webhook URL */
  url: string;
  /** Events to send to this endpoint */
  events: WebhookEventType[];
  /** Whether the endpoint is active */
  active: boolean;
  /** Webhook secret for signature verification */
  secret: string;
  /** Creation timestamp */
  createdAt: Date;
}
