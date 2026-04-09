/**
 * Execution Market Task API Service
 *
 * API service for task operations including listing, creating,
 * applying, cancelling, and managing tasks.
 */

import { supabase } from '../lib/supabase'
import { buildAuthHeaders } from '../lib/auth'
import type {
  Task,
  TaskFilters,
  CreateTaskData,
  ApplyToTaskData,
  CancelTaskData,
  AssignTaskData,
  PaginatedResponse,
  TaskWithExecutor,
  ApplicationWithTask,
  WorkerTasksResponse,
  AgentAnalytics,
} from './types'

const db = supabase
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
import { getRequireApiKey } from '../hooks/usePlatformConfig'
const AGENT_API_KEY = import.meta.env.VITE_API_KEY as string | undefined

function buildApplyTaskUrl(taskId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/tasks/${taskId}/apply`
  }
  return `${API_BASE_URL}/api/v1/tasks/${taskId}/apply`
}

function buildAgentCreateTaskUrl(): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/tasks`
  }
  return `${API_BASE_URL}/api/v1/tasks`
}

function buildAgentCancelTaskUrl(taskId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/tasks/${taskId}/cancel`
  }
  return `${API_BASE_URL}/api/v1/tasks/${taskId}/cancel`
}

function buildAgentAssignTaskUrl(taskId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/tasks/${taskId}/assign`
  }
  return `${API_BASE_URL}/api/v1/tasks/${taskId}/assign`
}

function hasAgentApiKey(): boolean {
  return Boolean(AGENT_API_KEY)
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

/** Typed error for application failures that need special UI handling */
export type ApplicationErrorType = 'world_id_required' | 'already_applied' | 'generic'

export class ApplicationError extends Error {
  type: ApplicationErrorType
  status: number
  detail: Record<string, unknown>

  constructor(type: ApplicationErrorType, message: string, status: number, detail: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApplicationError'
    this.type = type
    this.status = status
    this.detail = detail
  }
}

// ============== TASK LISTING ==============

/**
 * Get tasks with optional filters
 */
export async function getTasks(filters: TaskFilters = {}): Promise<PaginatedResponse<TaskWithExecutor>> {
  const {
    agentId,
    executorId,
    status,
    category,
    minBounty,
    maxBounty,
    limit = 20,
    offset = 0,
  } = filters

  // Build query
  let query = db
    .from('tasks')
    .select('*, executor:executors(id, display_name, wallet_address, reputation_score)', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1)

  // Apply filters
  if (agentId) {
    query = query.eq('agent_id', agentId)
  }

  if (executorId) {
    query = query.eq('executor_id', executorId)
  }

  if (status) {
    if (Array.isArray(status)) {
      query = query.in('status', status)
    } else {
      query = query.eq('status', status)
    }
  }

  if (category) {
    query = query.eq('category', category)
  }

  if (minBounty !== undefined) {
    query = query.gte('bounty_usd', minBounty)
  }

  if (maxBounty !== undefined) {
    query = query.lte('bounty_usd', maxBounty)
  }

  const { data, error, count } = await query

  if (error) {
    throw new Error(`Failed to fetch tasks: ${error.message}`)
  }

  const total = count || 0

  return {
    data: data || [],
    total,
    count: data?.length || 0,
    offset,
    hasMore: total > offset + (data?.length || 0),
  }
}

/**
 * Get a single task by ID
 */
export async function getTask(taskId: string): Promise<TaskWithExecutor | null> {
  const { data, error } = await db
    .from('tasks')
    .select('*, executor:executors(id, display_name, wallet_address, reputation_score)')
    .eq('id', taskId)
    .single()

  if (error) {
    if (error.code === 'PGRST116') {
      return null // Not found
    }
    throw new Error(`Failed to fetch task: ${error.message}`)
  }

  return data
}

/**
 * Get available tasks (published, not yet accepted)
 */
export async function getAvailableTasks(filters: Omit<TaskFilters, 'status'> = {}): Promise<PaginatedResponse<TaskWithExecutor>> {
  return getTasks({ ...filters, status: 'published' })
}

// ============== TASK CREATION (AGENT) ==============

/**
 * Create a new task (always via REST API)
 */
export async function createTask(data: CreateTaskData): Promise<Task> {
  if (!hasAgentApiKey()) {
    throw new Error(
      getRequireApiKey()
        ? 'VITE_API_KEY is required for agent task creation'
        : 'VITE_API_KEY must be configured for task creation.'
    )
  }

  const response = await fetch(buildAgentCreateTaskUrl(), {
    method: 'POST',
    headers: buildAgentJsonHeaders(),
    body: JSON.stringify({
      title: data.title,
      instructions: data.instructions,
      category: data.category,
      bounty_usd: data.bountyUsd,
      deadline_hours: data.deadlineHours,
      evidence_required: data.evidenceRequired,
      evidence_optional: data.evidenceOptional || [],
      location_hint: data.locationHint,
      min_reputation: data.minReputation || 0,
      payment_token: data.paymentToken || 'USDC',
      payment_network: data.paymentNetwork || 'base',
      arbiter_mode: data.arbiterMode || 'manual',
    }),
  })

  if (!response.ok) {
    const fallback = `Failed to create task via API (${response.status})`
    throw new Error(await parseApiError(response, fallback))
  }

  const payload = await response.json() as { id?: string }
  if (!payload?.id) {
    throw new Error('Task created via API but response did not include task id')
  }

  const { data: task, error } = await db
    .from('tasks')
    .select('*')
    .eq('id', payload.id)
    .single()

  if (error || !task) {
    throw new Error(
      `Task created via API but could not load row: ${error?.message || 'unknown error'}`
    )
  }

  return task
}

// ============== TASK APPLICATION (WORKER) ==============

/**
 * Apply to a task as a worker (always via REST API)
 */
export async function applyToTask(data: ApplyToTaskData): Promise<{ application: ApplicationWithTask; task: TaskWithExecutor }> {
  const { taskId, executorId, message } = data

  const authHeaders = await buildAuthHeaders({ 'Content-Type': 'application/json' })
  const response = await fetch(buildApplyTaskUrl(taskId), {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify({
      executor_id: executorId,
      message,
    }),
  })

  if (!response.ok) {
    // Parse structured error for special handling
    let body: Record<string, unknown> = {}
    try {
      body = await response.json() as Record<string, unknown>
    } catch { /* fallback to empty */ }

    const detail = body.detail as Record<string, unknown> | string | undefined

    // 403 World ID required
    if (response.status === 403) {
      const detailObj = typeof detail === 'object' && detail !== null ? detail : body
      if (detailObj.error === 'world_id_orb_required' || String(detail).includes('world_id')) {
        throw new ApplicationError(
          'world_id_required',
          String(detailObj.message || 'World ID verification required'),
          403,
          detailObj as Record<string, unknown>,
        )
      }
    }

    // 409 — distinguish "already applied" from "task not available"
    if (response.status === 409) {
      const detailStr = typeof detail === 'string' ? detail : String(body.detail || body.message || '')
      const isAlreadyApplied = detailStr.toLowerCase().includes('already applied')
      throw new ApplicationError(
        isAlreadyApplied ? 'already_applied' : 'generic',
        detailStr || (isAlreadyApplied ? 'Already applied to this task' : 'Task is no longer available'),
        409,
      )
    }

    // Generic error
    const msg = typeof detail === 'string' ? detail
      : (typeof detail === 'object' && detail !== null ? String((detail as Record<string, string>).message || (detail as Record<string, string>).error || '') : '')
      || String(body.message || body.error || `Failed to apply (${response.status})`)
    throw new ApplicationError('generic', msg, response.status, body)
  }

  const payload = await response.json() as { data?: { application_id?: string } }
  const applicationId = payload?.data?.application_id
  if (!applicationId) {
    throw new Error('Application succeeded but no application_id was returned by API')
  }

  const [{ data: application, error: applicationError }, task] = await Promise.all([
    db
      .from('task_applications')
      .select('*, task:tasks(*)')
      .eq('id', applicationId)
      .single(),
    getTask(taskId),
  ])

  if (applicationError || !application) {
    throw new Error(
      `Application created via API but could not load row: ${applicationError?.message || 'unknown error'}`
    )
  }

  if (!task) {
    throw new Error('Task not found after successful application')
  }

  return {
    application,
    task,
  }
}

/**
 * Cancel application to a task
 */
export async function cancelApplication(applicationId: string, executorId: string): Promise<void> {
  const { error } = await db
    .from('task_applications')
    .delete()
    .eq('id', applicationId)
    .eq('executor_id', executorId)
    .eq('status', 'pending')

  if (error) {
    throw new Error(`Failed to cancel application: ${error.message}`)
  }
}

/**
 * Get the set of task IDs where this executor has already applied
 */
export async function getMyApplicationTaskIds(executorId: string): Promise<Set<string>> {
  const { data, error } = await db
    .from('task_applications')
    .select('task_id')
    .eq('executor_id', executorId)

  if (error) {
    console.warn('Failed to fetch application task IDs:', error.message)
    return new Set()
  }

  return new Set((data || []).map((row: { task_id: string }) => row.task_id))
}

// ============== TASK CANCELLATION (AGENT) ==============

/**
 * Cancel a published task (always via REST API)
 */
export async function cancelTask(data: CancelTaskData): Promise<Task> {
  const { taskId, reason } = data

  if (!hasAgentApiKey()) {
    throw new Error(
      getRequireApiKey()
        ? 'VITE_API_KEY is required for agent task cancellation'
        : 'VITE_API_KEY must be configured for task cancellation.'
    )
  }

  const response = await fetch(buildAgentCancelTaskUrl(taskId), {
    method: 'POST',
    headers: buildAgentJsonHeaders(),
    body: JSON.stringify({ reason }),
  })

  if (!response.ok) {
    const fallback = `Failed to cancel task via API (${response.status})`
    throw new Error(await parseApiError(response, fallback))
  }

  const { data: task, error } = await db
    .from('tasks')
    .select('*')
    .eq('id', taskId)
    .single()

  if (error || !task) {
    throw new Error(
      `Task cancelled via API but row could not be reloaded: ${error?.message || 'unknown error'}`
    )
  }

  return task
}

// ============== TASK ASSIGNMENT (AGENT) ==============

/**
 * Assign a task to a specific executor (always via REST API)
 */
export async function assignTask(data: AssignTaskData): Promise<{ task: Task; executor: { id: string; display_name: string | null } }> {
  const { taskId, executorId, notes } = data

  if (!hasAgentApiKey()) {
    throw new Error(
      getRequireApiKey()
        ? 'VITE_API_KEY is required for agent task assignment'
        : 'VITE_API_KEY must be configured for task assignment.'
    )
  }

  const response = await fetch(buildAgentAssignTaskUrl(taskId), {
    method: 'POST',
    headers: buildAgentJsonHeaders(),
    body: JSON.stringify({
      executor_id: executorId,
      notes,
    }),
  })

  if (!response.ok) {
    const fallback = `Failed to assign task via API (${response.status})`
    throw new Error(await parseApiError(response, fallback))
  }

  const [{ data: task, error: taskError }, { data: executor, error: executorError }] = await Promise.all([
    db
      .from('tasks')
      .select('*')
      .eq('id', taskId)
      .single(),
    db
      .from('executors')
      .select('id, display_name')
      .eq('id', executorId)
      .single(),
  ])

  if (taskError || !task) {
    throw new Error(
      `Task assigned via API but task could not be reloaded: ${taskError?.message || 'unknown error'}`
    )
  }

  if (executorError || !executor) {
    throw new Error(
      `Task assigned via API but executor could not be loaded: ${executorError?.message || 'unknown error'}`
    )
  }

  return {
    task,
    executor,
  }
}

// ============== WORKER TASKS ==============

/**
 * Get tasks for a worker (assigned tasks + applications)
 */
export async function getMyTasks(executorId: string): Promise<WorkerTasksResponse> {
  // Get assigned tasks
  const { data: assignedTasks, error: tasksError } = await db
    .from('tasks')
    .select('*, executor:executors(id, display_name, wallet_address, reputation_score)')
    .eq('executor_id', executorId)
    .order('updated_at', { ascending: false })

  if (tasksError) {
    throw new Error(`Failed to fetch assigned tasks: ${tasksError.message}`)
  }

  // Get pending applications
  const { data: applications, error: appsError } = await db
    .from('task_applications')
    .select('*, task:tasks(*)')
    .eq('executor_id', executorId)
    .eq('status', 'pending')
    .order('created_at', { ascending: false })

  if (appsError) {
    throw new Error(`Failed to fetch applications: ${appsError.message}`)
  }

  // Get recent submissions
  const { data: submissions, error: subsError } = await db
    .from('submissions')
    .select('*, task:tasks(*)')
    .eq('executor_id', executorId)
    .order('submitted_at', { ascending: false })
    .limit(10)

  if (subsError) {
    throw new Error(`Failed to fetch submissions: ${subsError.message}`)
  }

  return {
    assignedTasks: assignedTasks || [],
    applications: applications || [],
    recentSubmissions: submissions || [],
    totals: {
      assigned: assignedTasks?.length || 0,
      pendingApplications: applications?.length || 0,
      submissions: submissions?.length || 0,
    },
  }
}

/**
 * Get agent's tasks (tasks created by the agent)
 */
export async function getAgentTasks(agentId: string, filters: Omit<TaskFilters, 'agentId'> = {}): Promise<PaginatedResponse<TaskWithExecutor>> {
  return getTasks({ ...filters, agentId })
}

// ============== AGENT ANALYTICS ==============

/**
 * Get analytics for an agent's tasks
 */
export async function getTaskAnalytics(agentId: string, days: number = 30): Promise<AgentAnalytics> {
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days)

  // Get all tasks for agent in date range
  const { data: tasks, error } = await db
    .from('tasks')
    .select('*')
    .eq('agent_id', agentId)
    .gte('created_at', startDate.toISOString())

  if (error) {
    throw new Error(`Failed to fetch analytics: ${error.message}`)
  }

  const taskList = tasks || []
  const total = taskList.length

  // Calculate totals
  const byStatus: Record<string, number> = {}
  const byCategory: Record<string, number> = {}
  let totalPaid = 0

  interface TaskListItem {
    status?: string
    category?: string
    bounty_usd?: number
    executor_id?: string | null
  }

  taskList.forEach((task: TaskListItem) => {
    // Count by status
    const status = task.status || 'unknown'
    byStatus[status] = (byStatus[status] || 0) + 1

    // Count by category
    const category = task.category || 'unknown'
    byCategory[category] = (byCategory[category] || 0) + 1

    // Sum bounties for completed tasks
    if (status === 'completed') {
      totalPaid += task.bounty_usd || 0
    }
  })

  const completed = byStatus['completed'] || 0
  const completionRate = total > 0 ? (completed / total) * 100 : 0
  const avgBounty = completed > 0 ? totalPaid / completed : 0

  // Get top workers
  const completedTasks = taskList.filter((t: TaskListItem) => t.status === 'completed')
  const executorIds = [...new Set(completedTasks.map((t: TaskListItem) => t.executor_id).filter(Boolean))]

  let topWorkers: AgentAnalytics['topWorkers'] = []

  if (executorIds.length > 0) {
    const { data: workers } = await db
      .from('executors')
      .select('id, display_name, reputation_score')
      .in('id', executorIds.slice(0, 10))

    if (workers) {
      // Count tasks per worker
      const workerCounts: Record<string, number> = {}
      completedTasks.forEach((t: TaskListItem) => {
        if (t.executor_id) {
          workerCounts[t.executor_id] = (workerCounts[t.executor_id] || 0) + 1
        }
      })

      interface WorkerRecord {
        id: string
        display_name?: string
        reputation_score?: number
      }

      interface TopWorker {
        id: string
        displayName?: string
        reputation: number
        tasksCompleted: number
      }

      topWorkers = workers
        .map((w: WorkerRecord) => ({
          id: w.id,
          displayName: w.display_name,
          reputation: w.reputation_score || 0,
          tasksCompleted: workerCounts[w.id] || 0,
        }))
        .sort((a: TopWorker, b: TopWorker) => b.tasksCompleted - a.tasksCompleted)
        .slice(0, 5)
    }
  }

  return {
    totals: {
      total,
      completed,
      completionRate,
      totalPaid,
      avgBounty,
    },
    byStatus,
    byCategory,
    averageTimes: {
      toAccept: '~2 hours',
      toComplete: '~6 hours',
      toApprove: '~30 minutes',
    },
    topWorkers,
    periodDays: days,
  }
}


