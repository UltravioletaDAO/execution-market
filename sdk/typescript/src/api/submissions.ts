/**
 * Submissions API
 *
 * Modular submissions API for use with HttpClient.
 */

import { HttpClient } from '../http';
import type { Submission, Evidence, ListResponse, PaginationParams } from '../types';

/**
 * Submissions API for managing task submissions.
 */
export class SubmissionsAPI {
  constructor(private readonly http: HttpClient) {}

  /**
   * Get submissions for a task.
   *
   * @param taskId - Task ID
   * @param params - Pagination parameters
   * @returns Paginated list of submissions
   */
  async listForTask(
    taskId: string,
    params?: PaginationParams
  ): Promise<ListResponse<Submission>> {
    const response = await this.http.get<{
      data?: Record<string, unknown>[];
      items?: Record<string, unknown>[];
      submissions?: Record<string, unknown>[];
      total: number;
      hasMore?: boolean;
      has_more?: boolean;
      nextCursor?: string;
      next_cursor?: string;
    }>(`/tasks/${taskId}/submissions`, params as Record<string, unknown>);

    const items = response.data || response.items || response.submissions || [];

    return {
      data: items.map(s => this.transformSubmission(s)),
      total: response.total || items.length,
      hasMore: response.hasMore || response.has_more || false,
      nextCursor: response.nextCursor || response.next_cursor,
    };
  }

  /**
   * Get a submission by ID.
   *
   * @param submissionId - Submission ID
   * @returns Submission object
   */
  async get(submissionId: string): Promise<Submission> {
    const response = await this.http.get<Record<string, unknown>>(
      `/submissions/${submissionId}`
    );
    return this.transformSubmission(response);
  }

  /**
   * Approve a submission (triggers payment to executor).
   *
   * @param submissionId - Submission ID
   * @param notes - Optional approval notes
   * @returns Updated submission
   *
   * @example
   * ```typescript
   * await submissions.approve(sub.id, 'Great work, thanks!');
   * ```
   */
  async approve(submissionId: string, notes?: string): Promise<Submission> {
    const response = await this.http.post<Record<string, unknown>>(
      `/submissions/${submissionId}/approve`,
      { notes }
    );
    return this.transformSubmission(response);
  }

  /**
   * Reject a submission.
   *
   * @param submissionId - Submission ID
   * @param notes - Rejection reason (required)
   * @returns Updated submission
   *
   * @example
   * ```typescript
   * await submissions.reject(sub.id, 'Photo is blurry, please retake');
   * ```
   */
  async reject(submissionId: string, notes: string): Promise<Submission> {
    const response = await this.http.post<Record<string, unknown>>(
      `/submissions/${submissionId}/reject`,
      { notes }
    );
    return this.transformSubmission(response);
  }

  /**
   * Request revision on a submission without rejecting.
   *
   * @param submissionId - Submission ID
   * @param feedback - Revision feedback
   * @returns Updated submission
   *
   * @example
   * ```typescript
   * await submissions.requestRevision(sub.id, 'Please include the full sign');
   * ```
   */
  async requestRevision(submissionId: string, feedback: string): Promise<Submission> {
    const response = await this.http.post<Record<string, unknown>>(
      `/submissions/${submissionId}/revision`,
      { feedback }
    );
    return this.transformSubmission(response);
  }

  /**
   * Transform API response to Submission object.
   */
  private transformSubmission(raw: Record<string, unknown>): Submission {
    return {
      id: raw.id as string,
      taskId: (raw.task_id ?? raw.taskId) as string,
      executorId: (raw.executor_id ?? raw.executorId) as string,
      evidence: (raw.evidence as Evidence) || {},
      status: raw.status as Submission['status'],
      preCheckScore: (raw.pre_check_score ?? raw.preCheckScore ?? 0.5) as number,
      submittedAt: new Date((raw.submitted_at ?? raw.submittedAt) as string),
      notes: raw.notes as string | undefined,
    };
  }
}
