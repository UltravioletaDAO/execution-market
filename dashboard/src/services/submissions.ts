/**
 * Execution Market Submission API Service
 *
 * API service for submission operations including submitting work,
 * fetching submissions, and approving/rejecting submissions.
 */

import { supabase } from '../lib/supabase'
import { buildAuthHeaders } from '../lib/auth'
import type {
  Submission,
  SubmitWorkData,
  ApproveSubmissionData,
  RejectSubmissionData,
  SubmissionWithDetails,
} from './types'

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
const AGENT_API_KEY = import.meta.env.VITE_API_KEY as string | undefined

function buildWorkerSubmitUrl(taskId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/tasks/${taskId}/submit`
  }
  return `${API_BASE_URL}/api/v1/tasks/${taskId}/submit`
}

function buildApproveSubmissionUrl(submissionId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/submissions/${submissionId}/approve`
  }
  return `${API_BASE_URL}/api/v1/submissions/${submissionId}/approve`
}

function buildRejectSubmissionUrl(submissionId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/submissions/${submissionId}/reject`
  }
  return `${API_BASE_URL}/api/v1/submissions/${submissionId}/reject`
}

function buildRequestMoreInfoUrl(submissionId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/submissions/${submissionId}/request-more-info`
  }
  return `${API_BASE_URL}/api/v1/submissions/${submissionId}/request-more-info`
}

function buildAgentJsonHeaders(): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (AGENT_API_KEY) {
    headers['Authorization'] = `Bearer ${AGENT_API_KEY}`
    headers['X-API-Key'] = AGENT_API_KEY
  }
  return headers
}

async function parseApiError(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json() as { detail?: string; message?: string; error?: string }
    return data.detail || data.message || data.error || fallback
  } catch {
    return fallback
  }
}

async function getTaskTitle(taskId: string): Promise<string> {
  const { data } = await supabase
    .from('tasks')
    .select('title')
    .eq('id', taskId)
    .single()

  return data?.title || 'Task'
}

// ============== SUBMIT WORK ==============

/**
 * Submit work evidence for a task
 */
export interface VerificationCheckResult {
  name: string
  passed: boolean
  score: number
  reason?: string
}

export interface VerificationResponse {
  passed: boolean
  score: number
  checks: VerificationCheckResult[]
  warnings: string[]
  phase: string
  phase_b_status: string
  summary?: string
}

export async function submitWork(data: SubmitWorkData): Promise<{ submission: Submission; task: { id: string; title: string }; verification: VerificationResponse | null }> {
  const { taskId, executorId, evidence, notes } = data
  try {
    const authHeaders = await buildAuthHeaders({ 'Content-Type': 'application/json' })
    const response = await fetch(buildWorkerSubmitUrl(taskId), {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        executor_id: executorId,
        evidence,
        notes,
      }),
    })

    if (!response.ok) {
      const fallback = `Failed to submit work via API (${response.status})`
      const detail = await parseApiError(response, fallback)
      throw new Error(detail)
    }

    const payload = await response.json() as { data?: { submission_id?: string; verification?: VerificationResponse } }
    const submissionId = payload?.data?.submission_id
    if (!submissionId) {
      throw new Error('Submission succeeded but no submission_id was returned by API')
    }

    const verification = (payload?.data?.verification as VerificationResponse) ?? null

    const { data: submission, error } = await supabase
      .from('submissions')
      .select('*')
      .eq('id', submissionId)
      .single()

    if (error || !submission) {
      throw new Error(
        `Submission created via API but could not load submission row: ${error?.message || 'unknown error'}`
      )
    }

    return {
      submission,
      task: {
        id: taskId,
        title: await getTaskTitle(taskId),
      },
      verification,
    }
  } catch (error) {
    throw error instanceof Error ? error : new Error('Failed to submit work via API')
  }
}

// ============== GET SUBMISSIONS ==============

/**
 * Get all submissions for a task
 */
export async function getSubmissions(taskId: string): Promise<SubmissionWithDetails[]> {
  const { data, error } = await supabase
    .from('submissions')
    .select('*, executor:executors(id, display_name, wallet_address, reputation_score)')
    .eq('task_id', taskId)
    .order('submitted_at', { ascending: false })

  if (error) {
    throw new Error(`Failed to fetch submissions: ${error.message}`)
  }

  return data || []
}

/**
 * Get a single submission by ID
 */
export async function getSubmission(submissionId: string): Promise<SubmissionWithDetails | null> {
  const { data, error } = await supabase
    .from('submissions')
    .select(`
      *,
      task:tasks(*),
      executor:executors(id, display_name, wallet_address, reputation_score)
    `)
    .eq('id', submissionId)
    .single()

  if (error) {
    if (error.code === 'PGRST116') {
      return null // Not found
    }
    throw new Error(`Failed to fetch submission: ${error.message}`)
  }

  return data
}

/**
 * Get submissions for an executor (worker)
 */
export async function getMySubmissions(executorId: string, limit: number = 20): Promise<SubmissionWithDetails[]> {
  const { data, error } = await supabase
    .from('submissions')
    .select('*, task:tasks(*)')
    .eq('executor_id', executorId)
    .order('submitted_at', { ascending: false })
    .limit(limit)

  if (error) {
    throw new Error(`Failed to fetch submissions: ${error.message}`)
  }

  return data || []
}

/**
 * Get pending submissions for an agent (tasks needing review)
 */
export async function getPendingSubmissions(agentId: string): Promise<SubmissionWithDetails[]> {
  // First get agent's tasks
  const { data: tasks, error: tasksError } = await supabase
    .from('tasks')
    .select('id')
    .eq('agent_id', agentId)
    .in('status', ['submitted', 'verifying'])

  if (tasksError) {
    throw new Error(`Failed to fetch tasks: ${tasksError.message}`)
  }

  if (!tasks || tasks.length === 0) {
    return []
  }

  const taskIds = tasks.map((t: { id: string }) => t.id)

  // Get submissions for those tasks that are pending review
  const { data, error } = await supabase
    .from('submissions')
    .select(`
      *,
      task:tasks(*),
      executor:executors(id, display_name, wallet_address, reputation_score)
    `)
    .in('task_id', taskIds)
    .is('agent_verdict', null)
    .order('submitted_at', { ascending: true })

  if (error) {
    throw new Error(`Failed to fetch submissions: ${error.message}`)
  }

  return data || []
}

// ============== APPROVE/REJECT SUBMISSIONS ==============

/**
 * Approve a submission via backend API.
 * Direct Supabase mutations are no longer allowed (DB-008 security lockdown).
 */
export async function approveSubmission(data: ApproveSubmissionData): Promise<Submission> {
  const { submissionId, notes } = data

  const response = await fetch(buildApproveSubmissionUrl(submissionId), {
    method: 'POST',
    headers: buildAgentJsonHeaders(),
    body: JSON.stringify({ notes }),
  })

  if (!response.ok) {
    const fallback = `Failed to approve submission via API (${response.status})`
    throw new Error(await parseApiError(response, fallback))
  }

  const payload = await response.json() as { data?: { submission_id?: string } }
  const approvedSubmissionId = payload?.data?.submission_id || submissionId

  const { data: submission, error } = await supabase
    .from('submissions')
    .select('*')
    .eq('id', approvedSubmissionId)
    .single()

  if (error || !submission) {
    throw new Error(
      `Submission approved via API but could not load row: ${error?.message || 'unknown error'}`
    )
  }

  return submission
}

/**
 * Reject a submission via backend API.
 * Direct Supabase mutations are no longer allowed (DB-008 security lockdown).
 */
export async function rejectSubmission(data: RejectSubmissionData): Promise<Submission> {
  const { submissionId, feedback } = data

  const response = await fetch(buildRejectSubmissionUrl(submissionId), {
    method: 'POST',
    headers: buildAgentJsonHeaders(),
    body: JSON.stringify({ notes: feedback }),
  })

  if (!response.ok) {
    const fallback = `Failed to reject submission via API (${response.status})`
    throw new Error(await parseApiError(response, fallback))
  }

  const payload = await response.json() as { data?: { submission_id?: string } }
  const rejectedSubmissionId = payload?.data?.submission_id || submissionId

  const { data: submission, error } = await supabase
    .from('submissions')
    .select('*')
    .eq('id', rejectedSubmissionId)
    .single()

  if (error || !submission) {
    throw new Error(
      `Submission rejected via API but could not load row: ${error?.message || 'unknown error'}`
    )
  }

  return submission
}

/**
 * Request more information on a submission via backend API.
 * Direct Supabase mutations are no longer allowed (DB-008 security lockdown).
 */
export async function requestMoreInfo(submissionId: string, _agentId: string, notes: string): Promise<Submission> {
  const response = await fetch(buildRequestMoreInfoUrl(submissionId), {
    method: 'POST',
    headers: buildAgentJsonHeaders(),
    body: JSON.stringify({ notes }),
  })

  if (!response.ok) {
    const fallback = `Failed to request more info via API (${response.status})`
    throw new Error(await parseApiError(response, fallback))
  }

  const payload = await response.json() as { data?: { submission_id?: string } }
  const updatedSubmissionId = payload?.data?.submission_id || submissionId

  const { data: updatedSubmission, error } = await supabase
    .from('submissions')
    .select('*')
    .eq('id', updatedSubmissionId)
    .single()

  if (error || !updatedSubmission) {
    throw new Error(
      `More-info request succeeded via API but submission could not be reloaded: ${error?.message || 'unknown error'}`
    )
  }

  return updatedSubmission
}

// ============== EVIDENCE UPLOAD ==============

/**
 * Upload evidence file to S3 via presigned URL.
 *
 * Flow:
 *   1. GET /api/v1/evidence/presign-upload → presigned PUT URL
 *   2. PUT file directly to S3
 *   3. Return CloudFront public URL
 */
export async function uploadEvidenceFile(
  taskId: string,
  executorId: string,
  file: File,
  evidenceType: string
): Promise<{ fileUrl: string; filename: string }> {
  const presignUrl = API_BASE_URL.endsWith('/api')
    ? `${API_BASE_URL}/v1/evidence/presign-upload`
    : `${API_BASE_URL}/api/v1/evidence/presign-upload`

  const params = new URLSearchParams({
    task_id: taskId,
    executor_id: executorId,
    filename: file.name,
    evidence_type: evidenceType,
    content_type: file.type || 'application/octet-stream',
  })

  // Step 1: Get presigned URL (with auth)
  const presignHeaders = await buildAuthHeaders()
  const presignRes = await fetch(`${presignUrl}?${params}`, { headers: presignHeaders })
  if (!presignRes.ok) {
    const err = await presignRes.json().catch(() => ({ message: presignRes.statusText }))
    throw new Error(`Failed to get upload URL: ${err.message || presignRes.status}`)
  }
  const presign = await presignRes.json()

  // Step 2: PUT file directly to S3
  const putRes = await fetch(presign.upload_url, {
    method: 'PUT',
    headers: { 'Content-Type': presign.content_type },
    body: file,
  })

  if (!putRes.ok) {
    throw new Error(`S3 upload failed: ${putRes.status}`)
  }

  return {
    fileUrl: presign.public_url || presign.key,
    filename: file.name,
  }
}
