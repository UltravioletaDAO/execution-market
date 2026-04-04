// Execution Market Database Types
// Compatible with @supabase/supabase-js

export type TaskCategory =
  | 'physical_presence'
  | 'knowledge_access'
  | 'human_authority'
  | 'simple_action'
  | 'digital_physical'
  | 'data_processing'
  | 'research'
  | 'content_generation'
  | 'code_execution'
  | 'api_integration'
  | 'multi_step_workflow'

export type TaskStatus =
  | 'published'
  | 'accepted'
  | 'in_progress'
  | 'submitted'
  | 'verifying'
  | 'completed'
  | 'disputed'
  | 'expired'
  | 'cancelled'

export type EvidenceType =
  | 'photo'
  | 'photo_geo'
  | 'video'
  | 'document'
  | 'receipt'
  | 'signature'
  | 'notarized'
  | 'timestamp_proof'
  | 'text_response'
  | 'measurement'
  | 'screenshot'
  | 'json_response'
  | 'api_response'
  | 'code_output'
  | 'file_artifact'
  | 'url_reference'
  | 'structured_data'
  | 'text_report'

export type DisputeStatus =
  | 'open'
  | 'under_review'
  | 'resolved_for_agent'
  | 'resolved_for_executor'

export interface EvidenceSchema {
  required: EvidenceType[]
  optional?: EvidenceType[]
}

export interface Location {
  lat: number
  lng: number
}

export type AgentType = 'human' | 'ai' | 'organization'

// Database row types (what you get from SELECT)
export interface SocialLinkX {
  handle: string
  verified?: boolean
  user_id?: string
  linked_at?: string
}

export interface SocialLinks {
  x?: SocialLinkX
}

export interface Executor {
  id: string
  user_id: string | null
  wallet_address: string
  display_name: string | null
  bio: string | null
  avatar_url: string | null
  skills: string[]
  languages: string[]
  roles: string[]
  email: string | null
  phone: string | null
  default_location: Location | null
  location_city: string | null
  location_country: string | null
  reputation_score: number
  tasks_completed: number
  tasks_disputed: number
  tasks_abandoned: number
  avg_rating: number | null
  reputation_contract: string | null
  reputation_token_id: number | null
  erc8004_agent_id: number | null
  world_human_id: number | null
  world_verified_at: string | null
  agent_type: AgentType
  networks_active: string[]
  preferred_language?: string | null
  social_links?: SocialLinks | null
  world_id_verified?: boolean
  world_id_level?: string | null  // 'orb' | 'device'
  ens_name?: string | null          // auto-resolved ENS (e.g., alice.eth)
  ens_avatar?: string | null        // ENS avatar URL
  ens_subname?: string | null       // claimed subname (e.g., alice.execution-market.eth)
  ens_resolved_at?: string | null
  created_at: string
  updated_at: string
  last_active_at: string | null
}

export type ActivityEventType =
  | 'task_created'
  | 'task_accepted'
  | 'task_completed'
  | 'feedback_given'
  | 'worker_joined'
  | 'dispute_opened'
  | 'dispute_resolved'

export interface ActivityFeedRow {
  id: string
  event_type: ActivityEventType
  actor_wallet: string
  actor_name: string | null
  actor_type: AgentType
  target_wallet: string | null
  target_name: string | null
  task_id: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface Task {
  id: string
  agent_id: string
  category: TaskCategory
  title: string
  instructions: string
  location: Location | null
  location_radius_km: number | null
  location_hint: string | null
  evidence_schema: EvidenceSchema
  bounty_usd: number
  payment_token: string
  payment_network: string
  escrow_tx: string | null
  escrow_id: string | null
  deadline: string
  created_at: string
  updated_at: string
  min_reputation: number
  required_roles: string[]
  max_executors: number
  status: TaskStatus
  executor_id: string | null
  assigned_at: string | null
  chainwitness_proof: string | null
  completed_at: string | null
  refund_tx: string | null
  escrow_status: string | null
  // Publisher identity fields
  erc8004_agent_id: string | null
  agent_name: string | null
  skills_required: string[] | null
  skill_version: string | null
  // H2A fields (optional — present when publisher_type='human')
  publisher_type?: PublisherType
  human_wallet?: string
  human_user_id?: string
  target_executor_type?: TargetExecutorType
  required_capabilities?: string[]
  verification_mode?: VerificationMode
  // Joined relations
  executor?: Executor
}

export interface Submission {
  id: string
  task_id: string
  executor_id: string
  evidence: Record<string, unknown>
  evidence_files: string[]
  evidence_ipfs_cid: string | null
  evidence_hash: string | null
  evidence_metadata: Record<string, unknown> | null
  evidence_content_hash: string | null
  storage_backend: 'supabase' | 's3' | 'ipfs' | null
  chainwitness_proof: string | null
  submitted_at: string
  verified_at: string | null
  auto_check_passed: boolean | null
  auto_check_details: Record<string, unknown> | null
  agent_verdict: string | null
  agent_notes: string | null
  payment_tx: string | null
  reputation_tx: string | null
  paid_at: string | null
  payment_amount: number | null
  ai_verification_result: Record<string, unknown> | null
  perceptual_hashes: Record<string, unknown> | null
  // Joined relations
  task?: Task
  executor?: Executor
}

export interface Dispute {
  id: string
  task_id: string
  submission_id: string
  agent_id: string
  executor_id: string
  reason: string
  agent_evidence: Record<string, unknown> | null
  executor_response: string | null
  executor_evidence: Record<string, unknown> | null
  status: DisputeStatus
  arbitrator_votes: unknown[]
  resolution_notes: string | null
  winner: 'agent' | 'executor' | null
  resolved_at: string | null
  created_at: string
}

export interface ReputationLog {
  id: string
  executor_id: string
  task_id: string | null
  delta: number
  new_score: number
  reason: string
  tx_hash: string | null
  created_at: string
}

export interface TaskApplication {
  id: string
  task_id: string
  executor_id: string
  message: string | null
  proposed_deadline: string | null
  status: 'pending' | 'accepted' | 'rejected'
  created_at: string
}

export type PaymentRowType =
  | 'task_payment'
  | 'withdrawal'
  | 'bonus'
  | 'refund'
  | 'escrow_create'
  | 'partial_release'
  | 'final_release'
  | 'full_release'
  | 'partial_refund'
  | 'platform_fee'
  | 'deposit'

export type PaymentRowStatus =
  | 'pending'
  | 'processing'
  | 'confirmed'
  | 'completed'
  | 'failed'
  | 'refunded'
  | 'cancelled'
  | 'available'
  | 'disputed'
  | 'partial_released'
  | 'escrowed'
  | 'funded'

export interface PaymentRow {
  id: string
  escrow_id: string | null
  task_id: string | null
  executor_id: string | null
  submission_id: string | null
  payment_type: PaymentRowType | null
  type: PaymentRowType | null
  status: PaymentRowStatus
  amount_usdc: number | null
  amount: number | null
  fee_usdc: number | null
  net_amount_usdc: number | null
  currency: string | null
  x402_escrow_id: string | null
  escrow_tx: string | null
  transaction_hash: string | null
  tx_hash: string | null
  from_address: string | null
  to_address: string | null
  chain_id: number | null
  network: string | null
  token_address: string | null
  block_number: number | null
  gas_used: number | null
  gas_price_gwei: number | null
  memo: string | null
  error_message: string | null
  error_code: string | null
  metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string | null
  confirmed_at: string | null
  completed_at: string | null
  processing_started_at: string | null
  failed_at: string | null
  retry_count: number | null
  last_retry_at: string | null
  next_retry_at: string | null
}

export interface PaymentInsert {
  escrow_id?: string | null
  task_id?: string | null
  executor_id?: string | null
  submission_id?: string | null
  payment_type?: PaymentRowType | null
  type?: PaymentRowType | null
  status?: PaymentRowStatus
  amount_usdc?: number | null
  amount?: number | null
  fee_usdc?: number | null
  currency?: string | null
  x402_escrow_id?: string | null
  escrow_tx?: string | null
  transaction_hash?: string | null
  tx_hash?: string | null
  from_address?: string | null
  to_address?: string | null
  chain_id?: number | null
  network?: string | null
  token_address?: string | null
  block_number?: number | null
  memo?: string | null
  error_message?: string | null
  error_code?: string | null
  metadata?: Record<string, unknown> | null
  confirmed_at?: string | null
  completed_at?: string | null
  processing_started_at?: string | null
  failed_at?: string | null
  retry_count?: number | null
  last_retry_at?: string | null
  next_retry_at?: string | null
}

export interface EscrowRow {
  id: string
  task_id: string
  agent_id: string
  escrow_id: string
  escrow_address: string | null
  funding_tx: string | null
  deposit_tx: string | null
  release_tx: string | null
  refund_tx: string | null
  status: string
  total_amount_usdc: number | null
  amount_usdc: number | null
  platform_fee_usdc: number | null
  net_bounty_usdc: number | null
  released_amount_usdc: number | null
  beneficiary_id: string | null
  beneficiary_address: string | null
  chain_id: number | null
  token_address: string | null
  timeout_hours: number | null
  expires_at: string | null
  metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string | null
  funded_at: string | null
  partial_released_at: string | null
  released_at: string | null
  refunded_at: string | null
}

export interface EscrowInsert {
  task_id: string
  agent_id: string
  escrow_id: string
  escrow_address?: string | null
  funding_tx?: string | null
  deposit_tx?: string | null
  release_tx?: string | null
  refund_tx?: string | null
  status?: string
  total_amount_usdc?: number | null
  amount_usdc?: number | null
  platform_fee_usdc?: number | null
  released_amount_usdc?: number | null
  beneficiary_id?: string | null
  beneficiary_address?: string | null
  chain_id?: number | null
  token_address?: string | null
  timeout_hours?: number | null
  expires_at?: string | null
  metadata?: Record<string, unknown> | null
  funded_at?: string | null
  partial_released_at?: string | null
  released_at?: string | null
  refunded_at?: string | null
}

export interface WithdrawalRow {
  id: string
  executor_id: string
  amount_usdc: number
  fee_usdc: number | null
  net_amount_usdc: number | null
  destination_address: string
  destination_chain_id: number | null
  status: string
  transaction_hash: string | null
  tx_hash: string | null
  block_number: number | null
  error_message: string | null
  error_code: string | null
  requested_at: string | null
  processed_at: string | null
  created_at: string
  processing_started_at: string | null
  completed_at: string | null
  failed_at: string | null
}

export interface WithdrawalInsert {
  executor_id: string
  amount_usdc: number
  fee_usdc?: number | null
  destination_address: string
  destination_chain_id?: number | null
  status?: string
  transaction_hash?: string | null
  tx_hash?: string | null
  block_number?: number | null
  error_message?: string | null
  error_code?: string | null
  requested_at?: string | null
  processed_at?: string | null
  processing_started_at?: string | null
  completed_at?: string | null
  failed_at?: string | null
}

// Insert types (for INSERT operations - id and timestamps auto-generated)
export interface ExecutorInsert {
  user_id?: string | null
  wallet_address: string
  display_name?: string | null
  bio?: string | null
  avatar_url?: string | null
  skills?: string[]
  languages?: string[]
  roles?: string[]
  email?: string | null
  phone?: string | null
  default_location?: Location | null
  location_city?: string | null
  location_country?: string | null
  reputation_score?: number
  tasks_completed?: number
  tasks_disputed?: number
  tasks_abandoned?: number
  avg_rating?: number | null
  reputation_contract?: string | null
  reputation_token_id?: number | null
  erc8004_agent_id?: number | null
  world_human_id?: number | null
  world_verified_at?: string | null
  last_active_at?: string | null
}

export interface TaskInsert {
  agent_id: string
  category: TaskCategory
  title: string
  instructions: string
  deadline: string
  bounty_usd: number
  location?: Location | null
  location_radius_km?: number | null
  location_hint?: string | null
  evidence_schema?: EvidenceSchema
  payment_token?: string
  escrow_tx?: string | null
  escrow_id?: string | null
  min_reputation?: number
  required_roles?: string[]
  max_executors?: number
  status?: TaskStatus
  executor_id?: string | null
  assigned_at?: string | null
  chainwitness_proof?: string | null
  completed_at?: string | null
}

export interface SubmissionInsert {
  task_id: string
  executor_id: string
  evidence: Record<string, unknown>
  evidence_files?: string[]
  evidence_ipfs_cid?: string | null
  evidence_hash?: string | null
  chainwitness_proof?: string | null
  verified_at?: string | null
  auto_check_passed?: boolean | null
  auto_check_details?: Record<string, unknown> | null
  agent_verdict?: string | null
  agent_notes?: string | null
  payment_tx?: string | null
  paid_at?: string | null
  payment_amount?: number | null
}

// Update types (for UPDATE operations - partial fields)
export interface TaskUpdate {
  status?: TaskStatus
  executor_id?: string | null
  assigned_at?: string | null
  chainwitness_proof?: string | null
  completed_at?: string | null
  title?: string
  instructions?: string
  deadline?: string
  bounty_usd?: number
}

export interface SubmissionUpdate {
  evidence?: Record<string, unknown>
  evidence_files?: string[]
  verified_at?: string | null
  auto_check_passed?: boolean | null
  auto_check_details?: Record<string, unknown> | null
  agent_verdict?: string | null
  agent_notes?: string | null
  payment_tx?: string | null
  paid_at?: string | null
  payment_amount?: number | null
}

// Notification types (for notifications table)
export type NotificationType =
  | 'task_nearby'
  | 'task_approved'
  | 'task_rejected'
  | 'payment_received'
  | 'payment_pending'
  | 'dispute_opened'
  | 'dispute_update'
  | 'dispute_resolved'
  | 'task_assigned'
  | 'task_expired'
  | 'task_reminder'
  | 'reputation_change'
  | 'system'
  | 'achievement'

export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent'

export interface NotificationRow {
  id: string
  executor_id: string
  type: NotificationType
  title: string
  message: string
  read: boolean
  task_id?: string
  submission_id?: string
  dispute_id?: string
  action_url?: string
  action_label?: string
  priority?: NotificationPriority
  metadata?: Record<string, unknown>
  expires_at?: string
  created_at: string
  updated_at: string
  deleted_at?: string
}

export interface NotificationInsert {
  executor_id: string
  type: NotificationType
  title: string
  message: string
  read?: boolean
  task_id?: string
  submission_id?: string
  dispute_id?: string
  action_url?: string
  action_label?: string
  priority?: NotificationPriority
  metadata?: Record<string, unknown>
  expires_at?: string
}

export interface NotificationUpdate {
  read?: boolean
  deleted_at?: string
}

// ============== H2A (HUMAN-TO-AGENT) TYPES ==============

export type PublisherType = 'agent' | 'human'

export type TargetExecutorType = 'human' | 'agent'

export type VerificationMode = 'manual' | 'auto'

export type DigitalEvidenceType =
  | 'json_response'
  | 'code'
  | 'report'
  | 'api_response'
  | 'data_file'
  | 'screenshot'
  | 'text_response'

export type UserRole = 'worker' | 'agent' | 'human_publisher'

/** H2A Task (extends Task with H2A-specific fields) */
export interface H2ATask extends Task {
  publisher_type: 'human'
  human_wallet: string
  human_user_id: string
  target_executor_type: 'agent'
  required_capabilities?: string[]
  verification_mode: VerificationMode
}

/** Request to create an H2A task */
export interface H2ATaskCreateRequest {
  title: string
  instructions: string
  category: TaskCategory
  bounty_usd: number
  deadline_hours?: number
  required_capabilities?: string[]
  verification_mode?: VerificationMode
  evidence_required?: string[]
  payment_network?: string
  target_agent_id?: string
}

/** Response from creating an H2A task */
export interface H2ATaskCreateResponse {
  task_id: string
  status: string
  bounty_usd: number
  fee_usd: number
  total_required_usd: number
  deadline: string
  publisher_type: 'human'
}

/** Request to approve/reject an H2A submission */
export interface H2AApprovalRequest {
  submission_id: string
  verdict: 'accepted' | 'rejected' | 'needs_revision'
  notes?: string
  settlement_auth_worker?: string
  settlement_auth_fee?: string
}

/** Response from H2A approval */
export interface H2AApprovalResponse {
  status: string
  worker_tx?: string
  fee_tx?: string
  notes?: string
}

/** Agent directory entry */
export interface AgentDirectoryEntry {
  executor_id: string
  display_name: string
  capabilities?: string[]
  rating: number
  tasks_completed: number
  avg_rating: number
  agent_card_url?: string
  mcp_endpoint_url?: string
  erc8004_agent_id?: number
  verified: boolean
  bio?: string
  avatar_url?: string
  pricing?: {
    min_bounty_usd?: number
    max_bounty_usd?: number
    avg_response_minutes?: number
  }
  role: 'publisher' | 'executor' | 'both'
  tasks_published: number
  total_bounty_usd: number
  active_tasks: number
}

/** Agent directory response */
export interface AgentDirectoryResponse {
  agents: AgentDirectoryEntry[]
  total: number
  page: number
  limit: number
}

// Supabase Database type definition
export interface Database {
  public: {
    Tables: {
      executors: {
        Row: Executor
        Insert: ExecutorInsert
        Update: Partial<ExecutorInsert>
        Relationships: []
      }
      tasks: {
        Row: Task
        Insert: TaskInsert
        Update: TaskUpdate
        Relationships: [
          {
            foreignKeyName: 'tasks_executor_id_fkey'
            columns: ['executor_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
        ]
      }
      submissions: {
        Row: Submission
        Insert: SubmissionInsert
        Update: SubmissionUpdate
        Relationships: [
          {
            foreignKeyName: 'submissions_task_id_fkey'
            columns: ['task_id']
            isOneToOne: false
            referencedRelation: 'tasks'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'submissions_executor_id_fkey'
            columns: ['executor_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
        ]
      }
      disputes: {
        Row: Dispute
        Insert: Omit<Dispute, 'id' | 'created_at'>
        Update: Partial<Omit<Dispute, 'id'>>
        Relationships: [
          {
            foreignKeyName: 'disputes_task_id_fkey'
            columns: ['task_id']
            isOneToOne: false
            referencedRelation: 'tasks'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'disputes_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'disputes_executor_id_fkey'
            columns: ['executor_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
        ]
      }
      reputation_log: {
        Row: ReputationLog
        Insert: Omit<ReputationLog, 'id' | 'created_at'>
        Update: never
        Relationships: [
          {
            foreignKeyName: 'reputation_log_executor_id_fkey'
            columns: ['executor_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'reputation_log_task_id_fkey'
            columns: ['task_id']
            isOneToOne: false
            referencedRelation: 'tasks'
            referencedColumns: ['id']
          },
        ]
      }
      task_applications: {
        Row: TaskApplication
        Insert: Omit<TaskApplication, 'id' | 'created_at'>
        Update: Partial<Omit<TaskApplication, 'id'>>
        Relationships: [
          {
            foreignKeyName: 'task_applications_task_id_fkey'
            columns: ['task_id']
            isOneToOne: false
            referencedRelation: 'tasks'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'task_applications_executor_id_fkey'
            columns: ['executor_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
        ]
      }
      escrows: {
        Row: EscrowRow
        Insert: EscrowInsert
        Update: Partial<EscrowInsert>
        Relationships: [
          {
            foreignKeyName: 'escrows_task_id_fkey'
            columns: ['task_id']
            isOneToOne: false
            referencedRelation: 'tasks'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'escrows_beneficiary_id_fkey'
            columns: ['beneficiary_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
        ]
      }
      payments: {
        Row: PaymentRow
        Insert: PaymentInsert
        Update: Partial<PaymentInsert>
        Relationships: [
          {
            foreignKeyName: 'payments_escrow_id_fkey'
            columns: ['escrow_id']
            isOneToOne: false
            referencedRelation: 'escrows'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'payments_task_id_fkey'
            columns: ['task_id']
            isOneToOne: false
            referencedRelation: 'tasks'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'payments_executor_id_fkey'
            columns: ['executor_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'payments_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      withdrawals: {
        Row: WithdrawalRow
        Insert: WithdrawalInsert
        Update: Partial<WithdrawalInsert>
        Relationships: [
          {
            foreignKeyName: 'withdrawals_executor_id_fkey'
            columns: ['executor_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
        ]
      }
      notifications: {
        Row: NotificationRow
        Insert: NotificationInsert
        Update: NotificationUpdate
        Relationships: [
          {
            foreignKeyName: 'notifications_executor_id_fkey'
            columns: ['executor_id']
            isOneToOne: false
            referencedRelation: 'executors'
            referencedColumns: ['id']
          },
        ]
      }
    }
    Enums: {
      task_category: TaskCategory
      task_status: TaskStatus
      evidence_type: EvidenceType
      dispute_status: DisputeStatus
    }
  }
}
