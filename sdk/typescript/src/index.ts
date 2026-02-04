/**
 * Execution Market SDK for TypeScript
 *
 * Build AI agents that hire humans for physical tasks.
 *
 * @packageDocumentation
 *
 * @example
 * ```typescript
 * import { ExecutionMarket } from '@execution-market/sdk';
 *
 * const em = new ExecutionMarket({ apiKey: 'your_api_key' });
 *
 * // Create a task
 * const task = await em.tasks.create({
 *   title: 'Check if Walmart is open',
 *   instructions: 'Take a photo of the store entrance',
 *   category: 'physical_presence',
 *   bountyUsd: 2.50,
 *   deadlineHours: 4,
 *   evidenceRequired: ['photo', 'photo_geo'],
 *   locationHint: 'Miami, FL'
 * });
 *
 * // Wait for completion
 * const result = await em.tasks.waitForCompletion(task.id);
 * console.log(`Result: ${result.answer}`);
 * ```
 */

// Main client (uses axios)
export { ExecutionMarket, createClient } from './client';
export type { ExecutionMarketConfig, TasksAPI, SubmissionsAPI, AnalyticsAPI, WebhooksAPI } from './client';

// Alternative HTTP client (uses native fetch, no dependencies)
export { HttpClient } from './http';

// Modular API classes for use with HttpClient
export {
  TasksAPI as ModularTasksAPI,
  SubmissionsAPI as ModularSubmissionsAPI,
  WebhooksAPI as ModularWebhooksAPI,
} from './api';

// Types
export type {
  // Enums
  TaskStatus,
  TaskCategory,
  EvidenceType,
  VerificationTier,
  PaymentToken,
  // Core entities
  Task,
  Submission,
  Evidence,
  TaskResult,
  // Input types
  CreateTaskInput,
  TaskCreateParams,
  TaskUpdateParams,
  ListTasksOptions,
  WaitOptions,
  // Response types
  PaginatedResponse,
  ListResponse,
  PaginationParams,
  BatchCreateResponse,
  Analytics,
  // Webhook types
  WebhookEventType,
  WebhookEvent,
  WebhookEventData,
  WebhookEndpoint,
  // Error types
  ExecutionMarketError,
  ValidationError,
} from './types';

// Errors
export {
  ExecutionMarketSDKError,
  AuthenticationError,
  AuthorizationError,
  NotFoundError,
  ValidationFailedError,
  RateLimitError,
  InvalidStateError,
  InsufficientFundsError,
  TimeoutError,
  NetworkError,
} from './errors';

// Utilities
export {
  // Bounty formatting
  formatBounty,
  parseBounty,
  isValidBounty,
  // Location utilities
  calculateDistance,
  calculateDistanceMiles,
  isWithinRadius,
  // Evidence validation
  validateEvidence,
  // Task utilities
  calculateDeadline,
  isExpired,
  timeRemaining,
  formatTimeRemaining,
  // Retry utilities
  retryWithBackoff,
} from './utils';

export type {
  Coordinates,
  EvidenceValidationResult,
  RetryOptions,
} from './utils';

// Version
export const VERSION = '0.1.0';
