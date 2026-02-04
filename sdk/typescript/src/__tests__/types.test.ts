/**
 * Type Tests
 *
 * These tests verify that types are correctly exported and can be used.
 */

import { describe, it, expect } from 'vitest';
import type {
  Task,
  TaskStatus,
  TaskCategory,
  EvidenceType,
  VerificationTier,
  PaymentToken,
  Submission,
  Evidence,
  TaskResult,
  CreateTaskInput,
  ListTasksOptions,
  WaitOptions,
  PaginatedResponse,
  BatchCreateResponse,
  Analytics,
  WebhookEventType,
  WebhookEvent,
  WebhookEndpoint,
  ExecutionMarketError,
  ValidationError,
} from '../types';

describe('Type Exports', () => {
  it('should allow creating Task-like objects', () => {
    const task: Task = {
      id: 'task_123',
      title: 'Test task',
      instructions: 'Do something',
      category: 'physical_presence',
      bountyUsd: 5.0,
      status: 'published',
      deadline: new Date(),
      evidenceRequired: ['photo'],
      createdAt: new Date(),
      paymentToken: 'USDC',
    };

    expect(task.id).toBe('task_123');
  });

  it('should allow all TaskStatus values', () => {
    const statuses: TaskStatus[] = [
      'published',
      'accepted',
      'in_progress',
      'submitted',
      'verifying',
      'completed',
      'disputed',
      'expired',
      'cancelled',
    ];

    expect(statuses.length).toBe(9);
  });

  it('should allow all TaskCategory values', () => {
    const categories: TaskCategory[] = [
      'physical_presence',
      'knowledge_access',
      'human_authority',
      'simple_action',
      'digital_physical',
    ];

    expect(categories.length).toBe(5);
  });

  it('should allow all EvidenceType values', () => {
    const types: EvidenceType[] = [
      'photo',
      'photo_geo',
      'video',
      'document',
      'signature',
      'text_response',
    ];

    expect(types.length).toBe(6);
  });

  it('should allow all VerificationTier values', () => {
    const tiers: VerificationTier[] = ['auto', 'ai', 'manual'];

    expect(tiers.length).toBe(3);
  });

  it('should allow all PaymentToken values', () => {
    const tokens: PaymentToken[] = ['USDC', 'USDT', 'DAI'];

    expect(tokens.length).toBe(3);
  });

  it('should allow creating Submission objects', () => {
    const submission: Submission = {
      id: 'sub_123',
      taskId: 'task_123',
      executorId: 'user_456',
      evidence: { photo: 'https://example.com/photo.jpg' },
      status: 'pending',
      preCheckScore: 0.85,
      submittedAt: new Date(),
    };

    expect(submission.preCheckScore).toBe(0.85);
  });

  it('should allow creating Evidence objects', () => {
    const evidence: Evidence = {
      photo: 'https://example.com/photo.jpg',
      photoGeo: {
        url: 'https://example.com/geo.jpg',
        latitude: 25.7617,
        longitude: -80.1918,
      },
      textResponse: 'The store is open',
    };

    expect(evidence.photoGeo?.latitude).toBe(25.7617);
  });

  it('should allow creating TaskResult objects', () => {
    const result: TaskResult = {
      taskId: 'task_123',
      status: 'completed',
      evidence: { textResponse: 'Done' },
      answer: 'Done',
      completedAt: new Date(),
    };

    expect(result.status).toBe('completed');
  });

  it('should allow creating CreateTaskInput objects', () => {
    const input: CreateTaskInput = {
      title: 'Check store',
      instructions: 'Take a photo of the store',
      category: 'physical_presence',
      bountyUsd: 2.5,
      deadlineHours: 4,
      evidenceRequired: ['photo', 'photo_geo'],
      locationHint: 'Miami, FL',
    };

    expect(input.bountyUsd).toBe(2.5);
  });

  it('should allow creating ListTasksOptions objects', () => {
    const options: ListTasksOptions = {
      status: ['published', 'accepted'],
      category: 'physical_presence',
      limit: 10,
      offset: 0,
      sortBy: 'createdAt',
      sortOrder: 'desc',
    };

    expect(options.limit).toBe(10);
  });

  it('should allow creating WaitOptions objects', () => {
    const options: WaitOptions = {
      timeoutHours: 4,
      pollInterval: 30,
      onStatusChange: (status) => console.log(status),
    };

    expect(options.timeoutHours).toBe(4);
  });

  it('should allow creating PaginatedResponse objects', () => {
    const response: PaginatedResponse<Task> = {
      items: [],
      total: 0,
      hasMore: false,
    };

    expect(response.total).toBe(0);
  });

  it('should allow creating BatchCreateResponse objects', () => {
    const response: BatchCreateResponse = {
      tasks: [],
      succeeded: 3,
      failed: 0,
    };

    expect(response.succeeded).toBe(3);
  });

  it('should allow creating Analytics objects', () => {
    const analytics: Analytics = {
      periodDays: 30,
      tasksCreated: 100,
      tasksCompleted: 85,
      completionRate: 0.85,
      avgCompletionTimeHours: 2.5,
      totalSpentUsd: 250.0,
      byStatus: { completed: 85, expired: 10, cancelled: 5 } as Record<TaskStatus, number>,
      byCategory: { physical_presence: 50, knowledge_access: 50 } as Record<TaskCategory, number>,
    };

    expect(analytics.completionRate).toBe(0.85);
  });

  it('should allow all WebhookEventType values', () => {
    const types: WebhookEventType[] = [
      'task.created',
      'task.accepted',
      'task.submitted',
      'task.completed',
      'task.disputed',
      'task.expired',
      'task.cancelled',
      'payment.sent',
    ];

    expect(types.length).toBe(8);
  });

  it('should allow creating WebhookEndpoint objects', () => {
    const endpoint: WebhookEndpoint = {
      id: 'wh_123',
      url: 'https://example.com/webhook',
      events: ['task.completed', 'task.submitted'],
      active: true,
      secret: 'whsec_xxx',
      createdAt: new Date(),
    };

    expect(endpoint.active).toBe(true);
  });

  it('should allow creating ExecutionMarketError objects', () => {
    const error: ExecutionMarketError = {
      code: 'VALIDATION_ERROR',
      message: 'Invalid input',
      statusCode: 400,
    };

    expect(error.statusCode).toBe(400);
  });

  it('should allow creating ValidationError objects', () => {
    const error: ValidationError = {
      field: 'title',
      message: 'Title is required',
    };

    expect(error.field).toBe('title');
  });
});
