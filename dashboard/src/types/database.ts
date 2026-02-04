// Execution Market Database Types
// Compatible with @supabase/supabase-js

export type TaskCategory =
  | 'physical_presence'
  | 'knowledge_access'
  | 'human_authority'
  | 'simple_action'
  | 'digital_physical'

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

// Database row types (what you get from SELECT)
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
  created_at: string
  updated_at: string
  last_active_at: string | null
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
  accepted_at: string | null
  chainwitness_proof: string | null
  completed_at: string | null
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
  chainwitness_proof: string | null
  submitted_at: string
  verified_at: string | null
  auto_check_passed: boolean | null
  auto_check_details: Record<string, unknown> | null
  agent_verdict: string | null
  agent_notes: string | null
  payment_tx: string | null
  paid_at: string | null
  payment_amount: number | null
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
  accepted_at?: string | null
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
  accepted_at?: string | null
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

// Supabase Database type definition
export interface Database {
  public: {
    Tables: {
      executors: {
        Row: Executor
        Insert: ExecutorInsert
        Update: Partial<ExecutorInsert>
      }
      tasks: {
        Row: Task
        Insert: TaskInsert
        Update: TaskUpdate
      }
      submissions: {
        Row: Submission
        Insert: SubmissionInsert
        Update: SubmissionUpdate
      }
      disputes: {
        Row: Dispute
        Insert: Omit<Dispute, 'id' | 'created_at'>
        Update: Partial<Omit<Dispute, 'id'>>
      }
      reputation_log: {
        Row: ReputationLog
        Insert: Omit<ReputationLog, 'id' | 'created_at'>
        Update: never
      }
      task_applications: {
        Row: TaskApplication
        Insert: Omit<TaskApplication, 'id' | 'created_at'>
        Update: Partial<Omit<TaskApplication, 'id'>>
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
