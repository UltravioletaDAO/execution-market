/**
 * Execution Market Task API Service
 *
 * API service for task operations including listing, creating,
 * applying, cancelling, and managing tasks.
 */

import { supabase } from '../lib/supabase'
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

const db = supabase as any
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
const ALLOW_DIRECT_SUPABASE_MUTATIONS = import.meta.env.VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS === 'true'

function buildApplyTaskUrl(taskId: string): string {
  if (API_BASE_URL.endsWith('/api')) {
    return `${API_BASE_URL}/v1/tasks/${taskId}/apply`
  }
  return `${API_BASE_URL}/api/v1/tasks/${taskId}/apply`
}

async function parseApiError(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json() as { detail?: string; message?: string; error?: string }
    return data.detail || data.message || data.error || fallback
  } catch {
    return fallback
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
 * Create a new task
 */
export async function createTask(data: CreateTaskData): Promise<Task> {
  const deadline = new Date()
  deadline.setHours(deadline.getHours() + data.deadlineHours)

  const taskData = {
    agent_id: data.agentId,
    title: data.title,
    instructions: data.instructions,
    category: data.category,
    bounty_usd: data.bountyUsd,
    deadline: deadline.toISOString(),
    evidence_schema: {
      required: data.evidenceRequired,
      optional: data.evidenceOptional || [],
    },
    location_hint: data.locationHint,
    min_reputation: data.minReputation || 0,
    payment_token: data.paymentToken || 'USDC',
    status: 'published',
  }

  const { data: task, error } = await db
    .from('tasks')
    .insert(taskData)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to create task: ${error.message}`)
  }

  return task
}

// ============== TASK APPLICATION (WORKER) ==============

/**
 * Apply to a task as a worker
 */
async function applyToTaskDirect(data: ApplyToTaskData): Promise<{ application: ApplicationWithTask; task: TaskWithExecutor }> {
  const { taskId, executorId, message, proposedDeadline } = data

  // Get task to verify availability
  const task = await getTask(taskId)
  if (!task) {
    throw new Error('Task not found')
  }

  if (task.status !== 'published') {
    throw new Error(`Task is not available (status: ${task.status})`)
  }

  // Get executor to check reputation
  const { data: executor, error: executorError } = await db
    .from('executors')
    .select('*')
    .eq('id', executorId)
    .single()

  if (executorError || !executor) {
    throw new Error('Executor not found')
  }

  // Check minimum reputation
  const minRep = task.min_reputation || 0
  if (executor.reputation_score < minRep) {
    throw new Error(`Insufficient reputation. Required: ${minRep}, yours: ${executor.reputation_score}`)
  }

  // Check for existing application
  const { data: existing } = await db
    .from('task_applications')
    .select('*')
    .eq('task_id', taskId)
    .eq('executor_id', executorId)

  if (existing && existing.length > 0) {
    throw new Error('Already applied to this task')
  }

  // Create application
  const applicationData = {
    task_id: taskId,
    executor_id: executorId,
    message,
    proposed_deadline: proposedDeadline,
    status: 'pending' as const,
  }

  const { data: application, error } = await db
    .from('task_applications')
    .insert(applicationData)
    .select('*, task:tasks(*)')
    .single()

  if (error) {
    throw new Error(`Failed to apply to task: ${error.message}`)
  }

  return {
    application,
    task,
  }
}

export async function applyToTask(data: ApplyToTaskData): Promise<{ application: ApplicationWithTask; task: TaskWithExecutor }> {
  const { taskId, executorId, message } = data

  try {
    const response = await fetch(buildApplyTaskUrl(taskId), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        executor_id: executorId,
        message,
      }),
    })

    if (!response.ok) {
      const fallback = `Failed to apply to task via API (${response.status})`
      throw new Error(await parseApiError(response, fallback))
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
  } catch (error) {
    if (!ALLOW_DIRECT_SUPABASE_MUTATIONS) {
      throw error instanceof Error ? error : new Error('Failed to apply to task via API')
    }
    // Explicit fallback for local/dev troubleshooting only.
    return applyToTaskDirect(data)
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

// ============== TASK CANCELLATION (AGENT) ==============

/**
 * Cancel a published task
 */
export async function cancelTask(data: CancelTaskData): Promise<Task> {
  const { taskId, agentId, reason: _reason } = data

  // Get task to verify ownership and status
  const task = await getTask(taskId)
  if (!task) {
    throw new Error('Task not found')
  }

  if (task.agent_id !== agentId) {
    throw new Error('Not authorized to cancel this task')
  }

  if (task.status !== 'published') {
    throw new Error(`Cannot cancel task with status: ${task.status}`)
  }

  // Update task status
  const { data: updatedTask, error } = await db
    .from('tasks')
    .update({
      status: 'cancelled',
      // Store cancellation reason in a metadata field if needed
    })
    .eq('id', taskId)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to cancel task: ${error.message}`)
  }

  return updatedTask
}

// ============== TASK ASSIGNMENT (AGENT) ==============

/**
 * Assign a task to a specific executor
 */
export async function assignTask(data: AssignTaskData): Promise<{ task: Task; executor: { id: string; display_name: string | null } }> {
  const { taskId, agentId, executorId, notes: _notes } = data

  // Get task to verify ownership
  const task = await getTask(taskId)
  if (!task) {
    throw new Error('Task not found')
  }

  if (task.agent_id !== agentId) {
    throw new Error('Not authorized to assign this task')
  }

  if (task.status !== 'published') {
    throw new Error(`Task cannot be assigned (status: ${task.status})`)
  }

  // Get executor to verify existence and reputation
  const { data: executor, error: executorError } = await db
    .from('executors')
    .select('*')
    .eq('id', executorId)
    .single()

  if (executorError || !executor) {
    throw new Error('Executor not found')
  }

  // Check minimum reputation
  const minRep = task.min_reputation || 0
  if (executor.reputation_score < minRep) {
    throw new Error(`Executor has insufficient reputation. Required: ${minRep}`)
  }

  // Update task
  const { data: updatedTask, error } = await db
    .from('tasks')
    .update({
      executor_id: executorId,
      status: 'accepted',
      accepted_at: new Date().toISOString(),
    })
    .eq('id', taskId)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to assign task: ${error.message}`)
  }

  // Update the accepted application
  await db
    .from('task_applications')
    .update({ status: 'accepted' })
    .eq('task_id', taskId)
    .eq('executor_id', executorId)

  // Reject other applications
  await db
    .from('task_applications')
    .update({ status: 'rejected' })
    .eq('task_id', taskId)
    .neq('executor_id', executorId)
    .eq('status', 'pending')

  return {
    task: updatedTask,
    executor: {
      id: executor.id,
      display_name: executor.display_name,
    },
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

  taskList.forEach((task: any) => {
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
  const completedTasks = taskList.filter((t: any) => t.status === 'completed')
  const executorIds = [...new Set(completedTasks.map((t: any) => t.executor_id).filter(Boolean))]

  let topWorkers: AgentAnalytics['topWorkers'] = []

  if (executorIds.length > 0) {
    const { data: workers } = await db
      .from('executors')
      .select('id, display_name, reputation_score')
      .in('id', executorIds.slice(0, 10))

    if (workers) {
      // Count tasks per worker
      const workerCounts: Record<string, number> = {}
      completedTasks.forEach((t: any) => {
        if (t.executor_id) {
          workerCounts[t.executor_id] = (workerCounts[t.executor_id] || 0) + 1
        }
      })

      topWorkers = workers
        .map((w: any) => ({
          id: w.id,
          displayName: w.display_name,
          reputation: w.reputation_score || 0,
          tasksCompleted: workerCounts[w.id] || 0,
        }))
        .sort((a: any, b: any) => b.tasksCompleted - a.tasksCompleted)
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


