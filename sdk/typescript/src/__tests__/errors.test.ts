/**
 * Error Classes Tests
 */

import { describe, it, expect } from 'vitest';
import {
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
  createErrorFromResponse,
} from '../errors';

describe('Error Classes', () => {
  describe('ExecutionMarketSDKError', () => {
    it('should create error with correct properties', () => {
      const error = new ExecutionMarketSDKError({
        code: 'TEST_ERROR',
        message: 'Test message',
        statusCode: 500,
        details: { key: 'value' },
      });

      expect(error.name).toBe('ExecutionMarketSDKError');
      expect(error.code).toBe('TEST_ERROR');
      expect(error.message).toBe('Test message');
      expect(error.statusCode).toBe(500);
      expect(error.details).toEqual({ key: 'value' });
    });

    it('should be instanceof Error', () => {
      const error = new ExecutionMarketSDKError({
        code: 'TEST',
        message: 'Test',
        statusCode: 500,
      });

      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(ExecutionMarketSDKError);
    });
  });

  describe('AuthenticationError', () => {
    it('should have correct defaults', () => {
      const error = new AuthenticationError();

      expect(error.name).toBe('AuthenticationError');
      expect(error.code).toBe('AUTHENTICATION_ERROR');
      expect(error.statusCode).toBe(401);
    });

    it('should accept custom message', () => {
      const error = new AuthenticationError('Custom message');

      expect(error.message).toBe('Custom message');
    });
  });

  describe('AuthorizationError', () => {
    it('should have correct defaults', () => {
      const error = new AuthorizationError();

      expect(error.name).toBe('AuthorizationError');
      expect(error.code).toBe('AUTHORIZATION_ERROR');
      expect(error.statusCode).toBe(403);
    });
  });

  describe('NotFoundError', () => {
    it('should include resource info', () => {
      const error = new NotFoundError('Task', 'task_123');

      expect(error.name).toBe('NotFoundError');
      expect(error.code).toBe('NOT_FOUND');
      expect(error.statusCode).toBe(404);
      expect(error.resourceType).toBe('Task');
      expect(error.resourceId).toBe('task_123');
      expect(error.message).toContain('Task');
      expect(error.message).toContain('task_123');
    });
  });

  describe('ValidationFailedError', () => {
    it('should include validation errors', () => {
      const errors = [
        { field: 'title', message: 'Required' },
        { field: 'bountyUsd', message: 'Must be positive' },
      ];
      const error = new ValidationFailedError(errors);

      expect(error.name).toBe('ValidationFailedError');
      expect(error.code).toBe('VALIDATION_ERROR');
      expect(error.statusCode).toBe(400);
      expect(error.errors).toEqual(errors);
      expect(error.message).toContain('title');
      expect(error.message).toContain('bountyUsd');
    });
  });

  describe('RateLimitError', () => {
    it('should include retry info', () => {
      const error = new RateLimitError(60);

      expect(error.name).toBe('RateLimitError');
      expect(error.code).toBe('RATE_LIMIT_EXCEEDED');
      expect(error.statusCode).toBe(429);
      expect(error.retryAfter).toBe(60);
    });
  });

  describe('InvalidStateError', () => {
    it('should include state info', () => {
      const error = new InvalidStateError('cancel', 'completed', ['published', 'accepted']);

      expect(error.name).toBe('InvalidStateError');
      expect(error.code).toBe('INVALID_STATE');
      expect(error.statusCode).toBe(409);
      expect(error.currentState).toBe('completed');
      expect(error.requiredStates).toEqual(['published', 'accepted']);
    });
  });

  describe('InsufficientFundsError', () => {
    it('should include funds info', () => {
      const error = new InsufficientFundsError(100, 50, 'USDC');

      expect(error.name).toBe('InsufficientFundsError');
      expect(error.code).toBe('INSUFFICIENT_FUNDS');
      expect(error.statusCode).toBe(402);
      expect(error.required).toBe(100);
      expect(error.available).toBe(50);
      expect(error.token).toBe('USDC');
    });
  });

  describe('TimeoutError', () => {
    it('should include timeout info', () => {
      const error = new TimeoutError('waitForCompletion', 30000);

      expect(error.name).toBe('TimeoutError');
      expect(error.code).toBe('TIMEOUT');
      expect(error.statusCode).toBe(408);
      expect(error.operation).toBe('waitForCompletion');
      expect(error.timeoutMs).toBe(30000);
    });
  });

  describe('NetworkError', () => {
    it('should include original error', () => {
      const originalError = new Error('Connection refused');
      const error = new NetworkError('Failed to connect', originalError);

      expect(error.name).toBe('NetworkError');
      expect(error.code).toBe('NETWORK_ERROR');
      expect(error.statusCode).toBe(0);
      expect(error.originalError).toBe(originalError);
    });
  });

  describe('createErrorFromResponse', () => {
    it('should create ValidationFailedError for 400 with errors', () => {
      const error = createErrorFromResponse(400, {
        code: 'VALIDATION_ERROR',
        message: 'Validation failed',
        errors: [{ field: 'title', message: 'Required' }],
      });

      expect(error).toBeInstanceOf(ValidationFailedError);
    });

    it('should create AuthenticationError for 401', () => {
      const error = createErrorFromResponse(401, {
        code: 'UNAUTHORIZED',
        message: 'Invalid API key',
      });

      expect(error).toBeInstanceOf(AuthenticationError);
    });

    it('should create InsufficientFundsError for 402', () => {
      const error = createErrorFromResponse(402, {
        code: 'INSUFFICIENT_FUNDS',
        message: 'Not enough funds',
        details: { required: 100, available: 50, token: 'USDC' },
      });

      expect(error).toBeInstanceOf(InsufficientFundsError);
    });

    it('should create AuthorizationError for 403', () => {
      const error = createErrorFromResponse(403, {
        code: 'FORBIDDEN',
        message: 'Access denied',
      });

      expect(error).toBeInstanceOf(AuthorizationError);
    });

    it('should create NotFoundError for 404', () => {
      const error = createErrorFromResponse(404, {
        code: 'NOT_FOUND',
        message: 'Not found',
        details: { resourceType: 'Task', resourceId: 'task_123' },
      });

      expect(error).toBeInstanceOf(NotFoundError);
    });

    it('should create InvalidStateError for 409', () => {
      const error = createErrorFromResponse(409, {
        code: 'INVALID_STATE',
        message: 'Invalid state',
        details: { currentState: 'completed', requiredStates: ['published'] },
      });

      expect(error).toBeInstanceOf(InvalidStateError);
    });

    it('should create RateLimitError for 429', () => {
      const error = createErrorFromResponse(429, {
        code: 'RATE_LIMITED',
        message: 'Rate limited',
        details: { retryAfter: 60 },
      });

      expect(error).toBeInstanceOf(RateLimitError);
    });

    it('should create generic ExecutionMarketSDKError for unknown status', () => {
      const error = createErrorFromResponse(500, {
        code: 'INTERNAL_ERROR',
        message: 'Server error',
      });

      expect(error).toBeInstanceOf(ExecutionMarketSDKError);
      expect(error.statusCode).toBe(500);
    });
  });
});
