/**
 * Tasks API
 *
 * Modular tasks API for use with HttpClient.
 */

import { HttpClient } from '../http';
import type {
  Task,
  TaskCreateParams,
  TaskUpdateParams,
  TaskResult,
  TaskStatus,
  ListResponse,
  PaginationParams,
  Evidence,
} from '../types';
import { TimeoutError } from '../errors';

/**
 * Tasks API for creating and managing Execution Market tasks.
 */
export class TasksAPI {
  constructor(private readonly http: HttpClient) {}

  /**
   * Create a new task.
   *
   * @param params - Task creation parameters
   * @returns Created task
   *
   * @example
   * ```typescript
   * const task = await tasks.create({
   *   title: 'Check store hours',
   *   instructions: 'Take a photo of the posted hours',
   *   category: 'knowledge_access',
   *   bountyUsd: 2.00,
   *   deadlineHours: 4,
   *   evidenceRequired: ['photo'],
   *   locationHint: 'Miami, FL'
   * });
   * ```
   */
  async create(params: TaskCreateParams): Promise<Task> {
    const response = await this.http.post<Record<string, unknown>>('/tasks', {
      title: params.title,
      instructions: params.instructions,
      category: params.category,
      bounty_usd: params.bountyUsd,
      deadline_hours: params.deadlineHours,
      evidence_required: params.evidenceRequired,
      evidence_optional: params.evidenceOptional,
      location_hint: params.locationHint,
      min_reputation: params.minReputation,
      payment_token: params.paymentToken,
      verification_tier: params.verificationTier,
      metadata: params.metadata,
    });

    return this.transformTask(response);
  }

  /**
   * Get a task by ID.
   *
   * @param taskId - Task ID
   * @returns Task object
   */
  async get(taskId: string): Promise<Task> {
    const response = await this.http.get<Record<string, unknown>>(`/tasks/${taskId}`);
    return this.transformTask(response);
  }

  /**
   * List tasks with optional filters.
   *
   * @param params - Pagination and filter parameters
   * @returns Paginated list of tasks
   */
  async list(params?: PaginationParams & { status?: TaskStatus }): Promise<ListResponse<Task>> {
    const response = await this.http.get<{
      data?: Record<string, unknown>[];
      items?: Record<string, unknown>[];
      tasks?: Record<string, unknown>[];
      total: number;
      hasMore?: boolean;
      has_more?: boolean;
      nextCursor?: string;
      next_cursor?: string;
    }>('/tasks', params as Record<string, unknown>);

    const items = response.data || response.items || response.tasks || [];

    return {
      data: items.map(t => this.transformTask(t)),
      total: response.total || 0,
      hasMore: response.hasMore || response.has_more || false,
      nextCursor: response.nextCursor || response.next_cursor,
    };
  }

  /**
   * Update a task (only while in 'published' status).
   *
   * @param taskId - Task ID
   * @param params - Update parameters
   * @returns Updated task
   */
  async update(taskId: string, params: TaskUpdateParams): Promise<Task> {
    const response = await this.http.put<Record<string, unknown>>(`/tasks/${taskId}`, {
      title: params.title,
      instructions: params.instructions,
      bounty_usd: params.bountyUsd,
      deadline_hours: params.deadlineHours,
      location_hint: params.locationHint,
      metadata: params.metadata,
    });
    return this.transformTask(response);
  }

  /**
   * Cancel a task.
   *
   * @param taskId - Task ID
   * @param reason - Optional cancellation reason
   * @returns Cancelled task
   */
  async cancel(taskId: string, reason?: string): Promise<Task> {
    const response = await this.http.post<Record<string, unknown>>(
      `/tasks/${taskId}/cancel`,
      { reason }
    );
    return this.transformTask(response);
  }

  /**
   * Create multiple tasks at once (batch operation).
   *
   * @param tasks - Array of task creation parameters
   * @returns Array of created tasks
   */
  async batchCreate(tasks: TaskCreateParams[]): Promise<Task[]> {
    const response = await this.http.post<{
      tasks: Record<string, unknown>[];
      succeeded?: number;
      failed?: number;
    }>('/tasks/batch', {
      tasks: tasks.map(t => ({
        title: t.title,
        instructions: t.instructions,
        category: t.category,
        bounty_usd: t.bountyUsd,
        deadline_hours: t.deadlineHours,
        evidence_required: t.evidenceRequired,
        evidence_optional: t.evidenceOptional,
        location_hint: t.locationHint,
        min_reputation: t.minReputation,
        payment_token: t.paymentToken,
        verification_tier: t.verificationTier,
        metadata: t.metadata,
      })),
    });
    return response.tasks.map(t => this.transformTask(t));
  }

  /**
   * Wait for a task to reach a terminal state.
   *
   * @param taskId - Task ID to wait for
   * @param options - Wait options
   * @returns Task result with evidence
   *
   * @example
   * ```typescript
   * const result = await tasks.waitForCompletion(task.id, {
   *   timeoutHours: 4,
   *   pollInterval: 30000
   * });
   *
   * if (result.status === 'completed') {
   *   console.log('Answer:', result.answer);
   * }
   * ```
   */
  async waitForCompletion(
    taskId: string,
    options?: { timeoutHours?: number; pollInterval?: number }
  ): Promise<TaskResult> {
    const timeoutHours = options?.timeoutHours ?? 24;
    const pollInterval = options?.pollInterval ?? 30000; // 30 seconds
    const deadline = Date.now() + timeoutHours * 60 * 60 * 1000;

    const terminalStatuses: TaskStatus[] = ['completed', 'expired', 'cancelled', 'disputed'];

    while (Date.now() < deadline) {
      const task = await this.get(taskId);

      if (terminalStatuses.includes(task.status)) {
        if (task.status === 'completed') {
          // Fetch submission evidence
          const submissions = await this.http.get<Record<string, unknown>[]>(
            `/tasks/${taskId}/submissions`
          );
          const approved = submissions.find(s => s.status === 'approved');
          const evidence = (approved?.evidence as Evidence) || {};

          return {
            taskId,
            status: task.status,
            evidence,
            answer: evidence.textResponse,
            completedAt: new Date(),
          };
        }

        return {
          taskId,
          status: task.status,
          evidence: {},
        };
      }

      await this.sleep(pollInterval);
    }

    throw new TimeoutError(
      `waitForCompletion(${taskId})`,
      timeoutHours * 60 * 60 * 1000
    );
  }

  /**
   * Subscribe to task status updates via polling.
   *
   * @param taskId - Task ID to watch
   * @param callback - Called when status changes
   * @param options - Polling options
   * @returns Unsubscribe function
   *
   * @example
   * ```typescript
   * const unsubscribe = tasks.onUpdate(task.id, (task) => {
   *   console.log('Status:', task.status);
   * });
   *
   * // Later: stop watching
   * unsubscribe();
   * ```
   */
  onUpdate(
    taskId: string,
    callback: (task: Task) => void,
    options?: { pollInterval?: number }
  ): () => void {
    const pollInterval = options?.pollInterval ?? 5000;
    let lastStatus: TaskStatus | null = null;
    let stopped = false;

    const poll = async () => {
      if (stopped) return;

      try {
        const task = await this.get(taskId);

        if (task.status !== lastStatus) {
          lastStatus = task.status;
          callback(task);
        }

        const terminalStatuses: TaskStatus[] = ['completed', 'expired', 'cancelled', 'disputed'];
        if (!terminalStatuses.includes(task.status)) {
          setTimeout(poll, pollInterval);
        }
      } catch (error) {
        // Log but continue polling
        console.error('Poll error:', error);
        if (!stopped) {
          setTimeout(poll, pollInterval);
        }
      }
    };

    poll();

    return () => {
      stopped = true;
    };
  }

  /**
   * Transform API response to Task object.
   */
  private transformTask(raw: Record<string, unknown>): Task {
    return {
      id: raw.id as string,
      title: raw.title as string,
      instructions: raw.instructions as string,
      category: raw.category as Task['category'],
      bountyUsd: (raw.bounty_usd ?? raw.bountyUsd) as number,
      status: raw.status as TaskStatus,
      deadline: new Date(raw.deadline as string),
      evidenceRequired: (raw.evidence_required ?? raw.evidenceRequired) as Task['evidenceRequired'],
      evidenceOptional: (raw.evidence_optional ?? raw.evidenceOptional) as Task['evidenceOptional'],
      locationHint: (raw.location_hint ?? raw.locationHint) as string | undefined,
      executorId: (raw.executor_id ?? raw.executorId) as string | undefined,
      createdAt: new Date((raw.created_at ?? raw.createdAt) as string),
      minReputation: (raw.min_reputation ?? raw.minReputation) as number | undefined,
      paymentToken: ((raw.payment_token ?? raw.paymentToken) as Task['paymentToken']) || 'USDC',
      verificationTier: (raw.verification_tier ?? raw.verificationTier) as Task['verificationTier'],
      metadata: raw.metadata as Record<string, unknown> | undefined,
    };
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
