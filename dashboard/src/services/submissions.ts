/**
 * Execution Market Submission API Service
 *
 * API service for submission operations including submitting work,
 * fetching submissions, and approving/rejecting submissions.
 */

import { supabase } from '../lib/supabase'
import type {
  Submission,
  SubmitWorkData,
  ApproveSubmissionData,
  RejectSubmissionData,
  SubmissionWithDetails,
  Evidence,
} from './types'

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
const ALLOW_DIRECT_SUPABASE_MUTATIONS = import.meta.env.VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS === 'true'

function buildWorkerSubmitUrl(taskId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/tasks/${taskId}/submit`
  }
  return `${API_BASE_URL}/api/v1/tasks/${taskId}/submit`
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

async function submitWorkDirect(data: SubmitWorkData): Promise<{ submission: Submission; task: { id: string; title: string } }> {
  const { taskId, executorId, evidence } = data

  // Get task to verify assignment and status
  const { data: task, error: taskError } = await supabase
    .from('tasks')
    .select('*')
    .eq('id', taskId)
    .single()

  if (taskError || !task) {
    throw new Error('Task not found')
  }

  // Verify executor is assigned
  if (task.executor_id !== executorId) {
    throw new Error('You are not assigned to this task')
  }

  // Verify task status
  const validStatuses = ['accepted', 'in_progress']
  if (!validStatuses.includes(task.status)) {
    throw new Error(`Task is not in a submittable state (status: ${task.status})`)
  }

  // Validate required evidence
  const evidenceSchema = task.evidence_schema || { required: [], optional: [] }
  const required: string[] = evidenceSchema.required || []
  const missing = required.filter((r: string) => !evidence[r])

  if (missing.length > 0) {
    throw new Error(`Missing required evidence: ${missing.join(', ')}`)
  }

  // Extract file URLs from evidence
  const evidenceFiles: string[] = []
  Object.values(evidence).forEach((ev: Evidence) => {
    if (ev.fileUrl) {
      evidenceFiles.push(ev.fileUrl)
    }
  })

  // Create submission
  const submissionData = {
    task_id: taskId,
    executor_id: executorId,
    evidence,
    evidence_files: evidenceFiles,
    submitted_at: new Date().toISOString(),
    agent_verdict: null,
  }

  const { data: submission, error } = await supabase
    .from('submissions')
    .insert(submissionData)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to submit work: ${error.message}`)
  }

  // Update task status to submitted
  await supabase
    .from('tasks')
    .update({ status: 'submitted' })
    .eq('id', taskId)

  return {
    submission,
    task: {
      id: task.id,
      title: task.title,
    },
  }
}

// ============== SUBMIT WORK ==============

/**
 * Submit work evidence for a task
 */
export async function submitWork(data: SubmitWorkData): Promise<{ submission: Submission; task: { id: string; title: string } }> {
  const { taskId, executorId, evidence, notes } = data
  try {
    const response = await fetch(buildWorkerSubmitUrl(taskId), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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

    const payload = await response.json() as { data?: { submission_id?: string } }
    const submissionId = payload?.data?.submission_id
    if (!submissionId) {
      throw new Error('Submission succeeded but no submission_id was returned by API')
    }

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
    }
  } catch (error) {
    if (!ALLOW_DIRECT_SUPABASE_MUTATIONS) {
      throw error instanceof Error ? error : new Error('Failed to submit work via API')
    }
    // Explicit fallback for local/dev troubleshooting only.
    return submitWorkDirect(data)
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

  const taskIds = tasks.map((t: any) => t.id)

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
 * Approve a submission
 */
export async function approveSubmission(data: ApproveSubmissionData): Promise<Submission> {
  const { submissionId, agentId, verdict, notes, rating } = data

  // Get submission with task
  const submission = await getSubmission(submissionId)
  if (!submission) {
    throw new Error('Submission not found')
  }

  // Verify agent owns the task
  const task = submission.task
  if (!task || task.agent_id !== agentId) {
    throw new Error('Not authorized to approve this submission')
  }

  // Update submission
  const updates: Record<string, unknown> = {
    agent_verdict: verdict,
    agent_notes: notes,
  }

  if (verdict === 'accepted') {
    updates.verified_at = new Date().toISOString()
  }

  const { data: updatedSubmission, error } = await supabase
    .from('submissions')
    .update(updates)
    .eq('id', submissionId)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to update submission: ${error.message}`)
  }

  // If accepted, update task status and reputation
  if (verdict === 'accepted') {
    // Update task to completed
    await supabase
      .from('tasks')
      .update({
        status: 'completed',
        completed_at: new Date().toISOString(),
      })
      .eq('id', task.id)

    // Update executor reputation
    if (submission.executor_id) {
      await updateExecutorReputation(
        submission.executor_id,
        task.id,
        10, // +10 for completed task
        'Task completed successfully',
        rating
      )
    }
  }

  return updatedSubmission
}

/**
 * Reject a submission
 */
export async function rejectSubmission(data: RejectSubmissionData): Promise<Submission> {
  const { submissionId, agentId, feedback } = data

  // Get submission with task
  const submission = await getSubmission(submissionId)
  if (!submission) {
    throw new Error('Submission not found')
  }

  // Verify agent owns the task
  const task = submission.task
  if (!task || task.agent_id !== agentId) {
    throw new Error('Not authorized to reject this submission')
  }

  // Update submission
  const { data: updatedSubmission, error } = await supabase
    .from('submissions')
    .update({
      agent_verdict: 'disputed',
      agent_notes: feedback,
    })
    .eq('id', submissionId)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to reject submission: ${error.message}`)
  }

  // Update task status
  await supabase
    .from('tasks')
    .update({ status: 'disputed' })
    .eq('id', task.id)

  return updatedSubmission
}

/**
 * Request more information on a submission
 */
export async function requestMoreInfo(submissionId: string, agentId: string, notes: string): Promise<Submission> {
  // Get submission with task
  const submission = await getSubmission(submissionId)
  if (!submission) {
    throw new Error('Submission not found')
  }

  // Verify agent owns the task
  const task = submission.task
  if (!task || task.agent_id !== agentId) {
    throw new Error('Not authorized to update this submission')
  }

  // Update submission
  const { data: updatedSubmission, error } = await supabase
    .from('submissions')
    .update({
      agent_verdict: 'more_info_requested',
      agent_notes: notes,
    })
    .eq('id', submissionId)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to update submission: ${error.message}`)
  }

  // Update task status back to in_progress so worker can resubmit
  await supabase
    .from('tasks')
    .update({ status: 'in_progress' })
    .eq('id', task.id)

  return updatedSubmission
}

// ============== HELPER FUNCTIONS ==============

/**
 * Update executor reputation
 */
async function updateExecutorReputation(
  executorId: string,
  taskId: string,
  delta: number,
  reason: string,
  rating?: number
): Promise<void> {
  // Get current score
  const { data: executor } = await supabase
    .from('executors')
    .select('reputation_score, tasks_completed')
    .eq('id', executorId)
    .single()

  if (!executor) {
    return
  }

  const currentScore = executor.reputation_score || 0
  const newScore = Math.max(0, currentScore + delta)
  const tasksCompleted = (executor.tasks_completed || 0) + (delta > 0 ? 1 : 0)

  // Update executor
  const updates: Record<string, unknown> = {
    reputation_score: newScore,
    tasks_completed: tasksCompleted,
    last_active_at: new Date().toISOString(),
  }

  // Update average rating if provided
  if (rating !== undefined) {
    const { data: existingRatings } = await supabase
      .from('reputation_log')
      .select('delta')
      .eq('executor_id', executorId)
      .not('delta', 'is', null)

    const ratingCount = existingRatings?.length || 0
    const currentAvg = executor.avg_rating || 0
    const newAvg = ratingCount > 0
      ? (currentAvg * ratingCount + rating) / (ratingCount + 1)
      : rating

    updates.avg_rating = newAvg
  }

  await supabase
    .from('executors')
    .update(updates)
    .eq('id', executorId)

  // Log the change
  await supabase
    .from('reputation_log')
    .insert({
      executor_id: executorId,
      task_id: taskId,
      delta,
      new_score: newScore,
      reason,
    })
}

/**
 * Upload evidence file to storage
 */
export async function uploadEvidenceFile(
  taskId: string,
  executorId: string,
  file: File,
  evidenceType: string
): Promise<{ fileUrl: string; filename: string }> {
  const timestamp = Date.now()
  const sanitizedName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_')
  const filePath = `evidence/${taskId}/${executorId}/${timestamp}_${evidenceType}_${sanitizedName}`

  const { error } = await supabase.storage
    .from('evidence')
    .upload(filePath, file, {
      cacheControl: '3600',
      upsert: false,
    })

  if (error) {
    throw new Error(`Failed to upload file: ${error.message}`)
  }

  const { data: urlData } = supabase.storage
    .from('evidence')
    .getPublicUrl(filePath)

  return {
    fileUrl: urlData.publicUrl,
    filename: file.name,
  }
}
