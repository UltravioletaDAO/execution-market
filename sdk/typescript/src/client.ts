/**
 * Chamba API Client
 *
 * Main client class for interacting with the Chamba API.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  Task,
  TaskStatus,
  CreateTaskInput,
  ListTasksOptions,
  Submission,
  TaskResult,
  Evidence,
  PaginatedResponse,
  BatchCreateResponse,
  Analytics,
  WaitOptions,
  WebhookEndpoint,
  WebhookEventType,
  ListResponse,
} from './types';
import {
  ChambaSDKError,
  AuthenticationError,
  NetworkError,
  TimeoutError,
  createErrorFromResponse,
} from './errors';

// =============================================================================
// Configuration
// =============================================================================

/**
 * Configuration options for the Chamba client.
 */
export interface ChambaConfig {
  /** API key for authentication */
  apiKey: string;
  /** Base URL for the API (default: https://api.chamba.ultravioleta.xyz) */
  baseUrl?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** Custom headers to include in requests */
  headers?: Record<string, string>;
}

const DEFAULT_BASE_URL = 'https://api.chamba.ultravioleta.xyz';
const DEFAULT_TIMEOUT = 30000;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Converts API response to Task object.
 */
function parseTask(data: Record<string, unknown>): Task {
  return {
    id: data.id as string,
    title: data.title as string,
    instructions: data.instructions as string,
    category: data.category as Task['category'],
    bountyUsd: data.bounty_usd as number,
    status: data.status as TaskStatus,
    deadline: new Date(data.deadline as string),
    evidenceRequired: data.evidence_required as Task['evidenceRequired'],
    evidenceOptional: data.evidence_optional as Task['evidenceOptional'],
    locationHint: data.location_hint as string | undefined,
    executorId: data.executor_id as string | undefined,
    createdAt: new Date(data.created_at as string),
    minReputation: data.min_reputation as number | undefined,
    paymentToken: (data.payment_token as Task['paymentToken']) || 'USDC',
    verificationTier: data.verification_tier as Task['verificationTier'],
    metadata: data.metadata as Record<string, unknown> | undefined,
  };
}

/**
 * Converts API response to Submission object.
 */
function parseSubmission(data: Record<string, unknown>): Submission {
  return {
    id: data.id as string,
    taskId: data.task_id as string,
    executorId: data.executor_id as string,
    evidence: data.evidence as Evidence,
    status: data.status as Submission['status'],
    preCheckScore: (data.pre_check_score as number) || 0.5,
    submittedAt: new Date(data.submitted_at as string),
    notes: data.notes as string | undefined,
  };
}

/**
 * Converts CreateTaskInput to API request format.
 */
function formatTaskInput(input: CreateTaskInput): Record<string, unknown> {
  return {
    title: input.title,
    instructions: input.instructions,
    category: input.category,
    bounty_usd: input.bountyUsd,
    deadline_hours: input.deadlineHours,
    evidence_required: input.evidenceRequired,
    evidence_optional: input.evidenceOptional,
    location_hint: input.locationHint,
    min_reputation: input.minReputation,
    payment_token: input.paymentToken,
    verification_tier: input.verificationTier,
    metadata: input.metadata,
  };
}

/**
 * Sleep for specified milliseconds.
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// =============================================================================
// API Classes
// =============================================================================

/**
 * Tasks API for creating and managing tasks.
 */
export class TasksAPI {
  constructor(private client: AxiosInstance) {}

  /**
   * Create a new task.
   *
   * @param input - Task creation input
   * @returns Created task
   *
   * @example
   * ```typescript
   * const task = await chamba.tasks.create({
   *   title: 'Check if store is open',
   *   instructions: 'Take a photo of the storefront showing open/closed status',
   *   category: 'physical_presence',
   *   bountyUsd: 2.50,
   *   deadlineHours: 4,
   *   evidenceRequired: ['photo', 'photo_geo'],
   *   locationHint: 'Miami, FL'
   * });
   * ```
   */
  async create(input: CreateTaskInput): Promise<Task> {
    const response = await this.client.post('/tasks', formatTaskInput(input));
    return parseTask(response.data);
  }

  /**
   * Get a task by ID.
   *
   * @param taskId - Task ID
   * @returns Task object
   */
  async get(taskId: string): Promise<Task> {
    const response = await this.client.get(`/tasks/${taskId}`);
    return parseTask(response.data);
  }

  /**
   * List tasks with optional filters.
   *
   * @param options - List options
   * @returns Paginated list of tasks
   */
  async list(options: ListTasksOptions = {}): Promise<PaginatedResponse<Task>> {
    const params: Record<string, unknown> = {};

    if (options.status) {
      params.status = Array.isArray(options.status)
        ? options.status.join(',')
        : options.status;
    }
    if (options.category) params.category = options.category;
    if (options.limit) params.limit = options.limit;
    if (options.offset) params.offset = options.offset;
    if (options.sortBy) params.sort_by = options.sortBy;
    if (options.sortOrder) params.sort_order = options.sortOrder;

    const response = await this.client.get('/tasks', { params });
    const data = response.data;

    return {
      items: (data.items || data.tasks || []).map(parseTask),
      total: data.total || 0,
      hasMore: data.has_more || false,
      nextOffset: data.next_offset,
    };
  }

  /**
   * Cancel a task.
   *
   * @param taskId - Task ID
   * @param reason - Optional cancellation reason
   * @returns Updated task
   */
  async cancel(taskId: string, reason?: string): Promise<Task> {
    const response = await this.client.post(`/tasks/${taskId}/cancel`, { reason });
    return parseTask(response.data);
  }

  /**
   * Create multiple tasks at once.
   *
   * @param inputs - Array of task creation inputs
   * @returns Batch create response
   */
  async batchCreate(inputs: CreateTaskInput[]): Promise<BatchCreateResponse> {
    const response = await this.client.post('/tasks/batch', {
      tasks: inputs.map(formatTaskInput),
    });

    const data = response.data;
    return {
      tasks: (data.tasks || []).map(parseTask),
      succeeded: data.succeeded || data.tasks?.length || 0,
      failed: data.failed || 0,
      errors: data.errors,
    };
  }

  /**
   * Wait for a task to complete.
   *
   * @param taskId - Task ID
   * @param options - Wait options
   * @returns Task result
   *
   * @example
   * ```typescript
   * const result = await chamba.tasks.waitForCompletion(task.id, {
   *   timeoutHours: 4,
   *   onStatusChange: (status) => console.log(`Status: ${status}`)
   * });
   * ```
   */
  async waitForCompletion(
    taskId: string,
    options: WaitOptions = {}
  ): Promise<TaskResult> {
    const timeoutMs = (options.timeoutHours || 24) * 60 * 60 * 1000;
    const pollIntervalMs = (options.pollInterval || 30) * 1000;
    const deadline = Date.now() + timeoutMs;

    let lastStatus: TaskStatus | null = null;

    while (Date.now() < deadline) {
      const task = await this.get(taskId);

      // Notify on status change
      if (options.onStatusChange && task.status !== lastStatus) {
        options.onStatusChange(task.status);
        lastStatus = task.status;
      }

      // Check terminal states
      if (task.status === 'completed') {
        const submissions = await this.client.get(`/tasks/${taskId}/submissions`);
        const approved = (submissions.data as Record<string, unknown>[])
          .filter(s => s.status === 'approved')
          .map(parseSubmission);

        const evidence = approved[0]?.evidence || {};

        return {
          taskId,
          status: task.status,
          evidence,
          answer: evidence.textResponse,
          completedAt: new Date(),
        };
      }

      if (['expired', 'cancelled', 'disputed'].includes(task.status)) {
        return {
          taskId,
          status: task.status,
          evidence: {},
        };
      }

      await sleep(pollIntervalMs);
    }

    throw new TimeoutError(
      `waitForCompletion(${taskId})`,
      timeoutMs
    );
  }

  /**
   * Subscribe to task updates via callback.
   * Note: This polls the API at the specified interval.
   *
   * @param taskId - Task ID
   * @param callback - Callback for updates
   * @param pollIntervalMs - Poll interval in milliseconds (default: 5000)
   * @returns Function to unsubscribe
   */
  onUpdate(
    taskId: string,
    callback: (task: Task) => void,
    pollIntervalMs = 5000
  ): () => void {
    let active = true;
    let lastStatus: TaskStatus | null = null;

    const poll = async () => {
      while (active) {
        try {
          const task = await this.get(taskId);

          if (task.status !== lastStatus) {
            lastStatus = task.status;
            callback(task);
          }

          // Stop polling on terminal states
          if (['completed', 'expired', 'cancelled', 'disputed'].includes(task.status)) {
            break;
          }
        } catch {
          // Silently continue on errors
        }

        await sleep(pollIntervalMs);
      }
    };

    poll();

    return () => {
      active = false;
    };
  }
}

/**
 * Submissions API for managing task submissions.
 */
export class SubmissionsAPI {
  constructor(private client: AxiosInstance) {}

  /**
   * Get submissions for a task.
   *
   * @param taskId - Task ID
   * @returns List of submissions
   */
  async list(taskId: string): Promise<Submission[]> {
    const response = await this.client.get(`/tasks/${taskId}/submissions`);
    return (response.data as Record<string, unknown>[]).map(parseSubmission);
  }

  /**
   * Get a submission by ID.
   *
   * @param submissionId - Submission ID
   * @returns Submission object
   */
  async get(submissionId: string): Promise<Submission> {
    const response = await this.client.get(`/submissions/${submissionId}`);
    return parseSubmission(response.data);
  }

  /**
   * Approve a submission.
   *
   * @param submissionId - Submission ID
   * @param notes - Optional approval notes
   * @returns Updated submission
   */
  async approve(submissionId: string, notes?: string): Promise<Submission> {
    const response = await this.client.post(`/submissions/${submissionId}/approve`, {
      notes,
    });
    return parseSubmission(response.data);
  }

  /**
   * Reject a submission.
   *
   * @param submissionId - Submission ID
   * @param notes - Rejection reason (required)
   * @returns Updated submission
   */
  async reject(submissionId: string, notes: string): Promise<Submission> {
    const response = await this.client.post(`/submissions/${submissionId}/reject`, {
      notes,
    });
    return parseSubmission(response.data);
  }
}

/**
 * Analytics API for agent metrics.
 */
export class AnalyticsAPI {
  constructor(private client: AxiosInstance) {}

  /**
   * Get analytics for the authenticated agent.
   *
   * @param days - Number of days to include (default: 30)
   * @returns Analytics data
   */
  async get(days = 30): Promise<Analytics> {
    const response = await this.client.get('/analytics', { params: { days } });
    const data = response.data;

    return {
      periodDays: data.period_days || days,
      tasksCreated: data.tasks_created || 0,
      tasksCompleted: data.tasks_completed || 0,
      completionRate: data.completion_rate || 0,
      avgCompletionTimeHours: data.avg_completion_time_hours || 0,
      totalSpentUsd: data.total_spent_usd || 0,
      byStatus: data.by_status || {},
      byCategory: data.by_category || {},
    };
  }
}

/**
 * Webhooks API for managing webhook endpoints.
 */
export class WebhooksAPI {
  constructor(private client: AxiosInstance) {}

  /**
   * Create a webhook endpoint.
   */
  async create(params: {
    url: string;
    events: WebhookEventType[];
  }): Promise<WebhookEndpoint> {
    const response = await this.client.post('/webhooks', params);
    return this.transformEndpoint(response.data);
  }

  /**
   * List all webhook endpoints.
   */
  async list(): Promise<ListResponse<WebhookEndpoint>> {
    const response = await this.client.get('/webhooks');
    const data = response.data;
    const items = data.data || data.items || data.webhooks || [];

    return {
      data: items.map((e: Record<string, unknown>) => this.transformEndpoint(e)),
      total: data.total || items.length,
      hasMore: data.has_more || data.hasMore || false,
    };
  }

  /**
   * Get a webhook endpoint by ID.
   */
  async get(webhookId: string): Promise<WebhookEndpoint> {
    const response = await this.client.get(`/webhooks/${webhookId}`);
    return this.transformEndpoint(response.data);
  }

  /**
   * Update a webhook endpoint.
   */
  async update(
    webhookId: string,
    params: { url?: string; events?: WebhookEventType[]; active?: boolean }
  ): Promise<WebhookEndpoint> {
    const response = await this.client.put(`/webhooks/${webhookId}`, params);
    return this.transformEndpoint(response.data);
  }

  /**
   * Delete a webhook endpoint.
   */
  async delete(webhookId: string): Promise<void> {
    await this.client.delete(`/webhooks/${webhookId}`);
  }

  /**
   * Rotate webhook secret.
   */
  async rotateSecret(webhookId: string): Promise<{ secret: string }> {
    const response = await this.client.post(`/webhooks/${webhookId}/rotate-secret`);
    return { secret: response.data.secret };
  }

  /**
   * Verify webhook signature using HMAC-SHA256.
   */
  verifySignature(payload: string, signature: string, secret: string): boolean {
    try {
      const crypto = require('crypto');
      const expected = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');

      const expectedSignature = `sha256=${expected}`;

      if (signature.length !== expectedSignature.length) {
        return false;
      }

      return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
      );
    } catch {
      return false;
    }
  }

  private transformEndpoint(raw: Record<string, unknown>): WebhookEndpoint {
    return {
      id: raw.id as string,
      url: raw.url as string,
      events: raw.events as WebhookEventType[],
      active: (raw.active ?? true) as boolean,
      secret: raw.secret as string,
      createdAt: new Date((raw.created_at ?? raw.createdAt) as string),
    };
  }
}

// =============================================================================
// Main Client
// =============================================================================

/**
 * Chamba API Client.
 *
 * @example
 * ```typescript
 * import { Chamba } from '@chamba/sdk';
 *
 * const chamba = new Chamba({ apiKey: 'your_api_key' });
 *
 * // Create a task
 * const task = await chamba.tasks.create({
 *   title: 'Check store hours',
 *   instructions: 'Photo of the posted hours',
 *   category: 'knowledge_access',
 *   bountyUsd: 1.50,
 *   deadlineHours: 2,
 *   evidenceRequired: ['photo'],
 *   locationHint: 'Downtown Miami'
 * });
 *
 * // Wait for completion
 * const result = await chamba.tasks.waitForCompletion(task.id);
 * console.log(`Result: ${result.answer}`);
 * ```
 */
export class Chamba {
  private readonly client: AxiosInstance;

  /** Tasks API */
  public readonly tasks: TasksAPI;

  /** Submissions API */
  public readonly submissions: SubmissionsAPI;

  /** Analytics API */
  public readonly analytics: AnalyticsAPI;

  /** Webhooks API */
  public readonly webhooks: WebhooksAPI;

  /**
   * Create a new Chamba client.
   *
   * @param config - Client configuration
   * @throws {AuthenticationError} If API key is not provided
   */
  constructor(config: ChambaConfig) {
    const apiKey = config.apiKey || process.env.CHAMBA_API_KEY;

    if (!apiKey) {
      throw new AuthenticationError(
        'API key required. Set CHAMBA_API_KEY environment variable or pass apiKey in config.'
      );
    }

    const baseURL = config.baseUrl || process.env.CHAMBA_API_URL || DEFAULT_BASE_URL;
    const timeout = config.timeout || DEFAULT_TIMEOUT;

    this.client = axios.create({
      baseURL,
      timeout,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': '@chamba/sdk/0.1.0',
        ...config.headers,
      },
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      response => response,
      (error: AxiosError) => {
        if (error.response) {
          const { status, data } = error.response;
          throw createErrorFromResponse(status, data as Record<string, unknown>);
        }

        if (error.code === 'ECONNABORTED') {
          throw new TimeoutError('request', timeout);
        }

        throw new NetworkError(
          error.message || 'Network request failed',
          error
        );
      }
    );

    // Initialize APIs
    this.tasks = new TasksAPI(this.client);
    this.submissions = new SubmissionsAPI(this.client);
    this.analytics = new AnalyticsAPI(this.client);
    this.webhooks = new WebhooksAPI(this.client);
  }

  /**
   * Check if the API is reachable and the API key is valid.
   *
   * @returns True if healthy
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.get('/health');
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get the current authenticated agent's information.
   *
   * @returns Agent info
   */
  async getAgent(): Promise<{
    id: string;
    name: string;
    balance: number;
    token: string;
  }> {
    const response = await this.client.get('/agent');
    const data = response.data;
    return {
      id: data.id,
      name: data.name,
      balance: data.balance,
      token: data.token || 'USDC',
    };
  }
}

/**
 * Create a Chamba client with API key from environment.
 *
 * @param config - Optional additional configuration
 * @returns Chamba client
 */
export function createClient(config: Partial<ChambaConfig> = {}): Chamba {
  const apiKey = config.apiKey || process.env.CHAMBA_API_KEY;

  if (!apiKey) {
    throw new AuthenticationError(
      'API key required. Set CHAMBA_API_KEY environment variable.'
    );
  }

  return new Chamba({ ...config, apiKey });
}
