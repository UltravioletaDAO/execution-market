/**
 * Chamba SDK Error Classes
 */

import type { ChambaError, ValidationError } from './types';

/**
 * Base error class for all Chamba SDK errors.
 */
export class ChambaSDKError extends Error {
  public readonly code: string;
  public readonly statusCode: number;
  public readonly details?: Record<string, unknown>;

  constructor(error: ChambaError) {
    super(error.message);
    this.name = 'ChambaSDKError';
    this.code = error.code;
    this.statusCode = error.statusCode;
    this.details = error.details;

    // Maintains proper stack trace for where error was thrown
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ChambaSDKError);
    }
  }
}

/**
 * Error thrown when authentication fails.
 */
export class AuthenticationError extends ChambaSDKError {
  constructor(message = 'Authentication failed. Check your API key.') {
    super({
      code: 'AUTHENTICATION_ERROR',
      message,
      statusCode: 401,
    });
    this.name = 'AuthenticationError';
  }
}

/**
 * Error thrown when authorization fails.
 */
export class AuthorizationError extends ChambaSDKError {
  constructor(message = 'You do not have permission to perform this action.') {
    super({
      code: 'AUTHORIZATION_ERROR',
      message,
      statusCode: 403,
    });
    this.name = 'AuthorizationError';
  }
}

/**
 * Error thrown when a resource is not found.
 */
export class NotFoundError extends ChambaSDKError {
  public readonly resourceType: string;
  public readonly resourceId: string;

  constructor(resourceType: string, resourceId: string) {
    super({
      code: 'NOT_FOUND',
      message: `${resourceType} with ID '${resourceId}' not found.`,
      statusCode: 404,
      details: { resourceType, resourceId },
    });
    this.name = 'NotFoundError';
    this.resourceType = resourceType;
    this.resourceId = resourceId;
  }
}

/**
 * Error thrown when request validation fails.
 */
export class ValidationFailedError extends ChambaSDKError {
  public readonly errors: ValidationError[];

  constructor(errors: ValidationError[]) {
    super({
      code: 'VALIDATION_ERROR',
      message: `Validation failed: ${errors.map(e => `${e.field}: ${e.message}`).join(', ')}`,
      statusCode: 400,
      details: { errors },
    });
    this.name = 'ValidationFailedError';
    this.errors = errors;
  }
}

/**
 * Error thrown when rate limit is exceeded.
 */
export class RateLimitError extends ChambaSDKError {
  public readonly retryAfter: number;

  constructor(retryAfter: number) {
    super({
      code: 'RATE_LIMIT_EXCEEDED',
      message: `Rate limit exceeded. Retry after ${retryAfter} seconds.`,
      statusCode: 429,
      details: { retryAfter },
    });
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

/**
 * Error thrown when task is in invalid state for operation.
 */
export class InvalidStateError extends ChambaSDKError {
  public readonly currentState: string;
  public readonly requiredStates: string[];

  constructor(operation: string, currentState: string, requiredStates: string[]) {
    super({
      code: 'INVALID_STATE',
      message: `Cannot ${operation}. Task is '${currentState}', but must be one of: ${requiredStates.join(', ')}.`,
      statusCode: 409,
      details: { currentState, requiredStates },
    });
    this.name = 'InvalidStateError';
    this.currentState = currentState;
    this.requiredStates = requiredStates;
  }
}

/**
 * Error thrown when insufficient funds for operation.
 */
export class InsufficientFundsError extends ChambaSDKError {
  public readonly required: number;
  public readonly available: number;
  public readonly token: string;

  constructor(required: number, available: number, token: string) {
    super({
      code: 'INSUFFICIENT_FUNDS',
      message: `Insufficient funds. Required: ${required} ${token}, Available: ${available} ${token}.`,
      statusCode: 402,
      details: { required, available, token },
    });
    this.name = 'InsufficientFundsError';
    this.required = required;
    this.available = available;
    this.token = token;
  }
}

/**
 * Error thrown when operation times out.
 */
export class TimeoutError extends ChambaSDKError {
  public readonly operation: string;
  public readonly timeoutMs: number;

  constructor(operation: string, timeoutMs: number) {
    super({
      code: 'TIMEOUT',
      message: `Operation '${operation}' timed out after ${timeoutMs}ms.`,
      statusCode: 408,
      details: { operation, timeoutMs },
    });
    this.name = 'TimeoutError';
    this.operation = operation;
    this.timeoutMs = timeoutMs;
  }
}

/**
 * Error thrown when network request fails.
 */
export class NetworkError extends ChambaSDKError {
  public readonly originalError?: Error;

  constructor(message: string, originalError?: Error) {
    super({
      code: 'NETWORK_ERROR',
      message,
      statusCode: 0,
      details: { originalError: originalError?.message },
    });
    this.name = 'NetworkError';
    this.originalError = originalError;
  }
}

/**
 * Converts API error response to appropriate error class.
 */
export function createErrorFromResponse(
  statusCode: number,
  data: Record<string, unknown>
): ChambaSDKError {
  const code = (data.code as string) || 'UNKNOWN_ERROR';
  const message = (data.message as string) || 'An unknown error occurred.';
  const details = data.details as Record<string, unknown> | undefined;

  switch (statusCode) {
    case 400:
      if (data.errors && Array.isArray(data.errors)) {
        return new ValidationFailedError(data.errors as ValidationError[]);
      }
      return new ChambaSDKError({ code, message, statusCode, details });

    case 401:
      return new AuthenticationError(message);

    case 402:
      return new InsufficientFundsError(
        (details?.required as number) || 0,
        (details?.available as number) || 0,
        (details?.token as string) || 'USDC'
      );

    case 403:
      return new AuthorizationError(message);

    case 404:
      return new NotFoundError(
        (details?.resourceType as string) || 'Resource',
        (details?.resourceId as string) || 'unknown'
      );

    case 409:
      return new InvalidStateError(
        'perform operation',
        (details?.currentState as string) || 'unknown',
        (details?.requiredStates as string[]) || []
      );

    case 429:
      return new RateLimitError((details?.retryAfter as number) || 60);

    default:
      return new ChambaSDKError({ code, message, statusCode, details });
  }
}
