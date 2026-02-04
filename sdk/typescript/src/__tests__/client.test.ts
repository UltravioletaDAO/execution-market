/**
 * Execution Market SDK Client Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { ExecutionMarket, createClient, AuthenticationError } from '../index';

describe('ExecutionMarket Client', () => {
  describe('initialization', () => {
    it('should throw AuthenticationError when no API key provided', () => {
      // Clear env var if set
      const originalKey = process.env.EM_API_KEY;
      delete process.env.EM_API_KEY;

      expect(() => new ExecutionMarket({ apiKey: '' })).toThrow(AuthenticationError);
      expect(() => createClient()).toThrow(AuthenticationError);

      // Restore
      if (originalKey) {
        process.env.EM_API_KEY = originalKey;
      }
    });

    it('should create client with valid API key', () => {
      const em = new ExecutionMarket({ apiKey: 'test_key_123' });

      expect(em).toBeInstanceOf(ExecutionMarket);
      expect(em.tasks).toBeDefined();
      expect(em.submissions).toBeDefined();
      expect(em.analytics).toBeDefined();
      expect(em.webhooks).toBeDefined();
    });

    it('should use custom base URL', () => {
      const em = new ExecutionMarket({
        apiKey: 'test_key_123',
        baseUrl: 'https://custom.api.com',
      });

      expect(em).toBeInstanceOf(ExecutionMarket);
    });

    it('should read API key from environment', () => {
      process.env.EM_API_KEY = 'env_key_456';

      const em = createClient();
      expect(em).toBeInstanceOf(ExecutionMarket);

      delete process.env.EM_API_KEY;
    });
  });

  describe('TasksAPI', () => {
    let em: ExecutionMarket;

    beforeEach(() => {
      em = new ExecutionMarket({ apiKey: 'test_key' });
    });

    it('should have create method', () => {
      expect(typeof em.tasks.create).toBe('function');
    });

    it('should have get method', () => {
      expect(typeof em.tasks.get).toBe('function');
    });

    it('should have list method', () => {
      expect(typeof em.tasks.list).toBe('function');
    });

    it('should have cancel method', () => {
      expect(typeof em.tasks.cancel).toBe('function');
    });

    it('should have batchCreate method', () => {
      expect(typeof em.tasks.batchCreate).toBe('function');
    });

    it('should have waitForCompletion method', () => {
      expect(typeof em.tasks.waitForCompletion).toBe('function');
    });

    it('should have onUpdate method', () => {
      expect(typeof em.tasks.onUpdate).toBe('function');
    });
  });

  describe('SubmissionsAPI', () => {
    let em: ExecutionMarket;

    beforeEach(() => {
      em = new ExecutionMarket({ apiKey: 'test_key' });
    });

    it('should have list method', () => {
      expect(typeof em.submissions.list).toBe('function');
    });

    it('should have get method', () => {
      expect(typeof em.submissions.get).toBe('function');
    });

    it('should have approve method', () => {
      expect(typeof em.submissions.approve).toBe('function');
    });

    it('should have reject method', () => {
      expect(typeof em.submissions.reject).toBe('function');
    });
  });

  describe('AnalyticsAPI', () => {
    let em: ExecutionMarket;

    beforeEach(() => {
      em = new ExecutionMarket({ apiKey: 'test_key' });
    });

    it('should have get method', () => {
      expect(typeof em.analytics.get).toBe('function');
    });
  });

  describe('WebhooksAPI', () => {
    let em: ExecutionMarket;

    beforeEach(() => {
      em = new ExecutionMarket({ apiKey: 'test_key' });
    });

    it('should have create method', () => {
      expect(typeof em.webhooks.create).toBe('function');
    });

    it('should have list method', () => {
      expect(typeof em.webhooks.list).toBe('function');
    });

    it('should have get method', () => {
      expect(typeof em.webhooks.get).toBe('function');
    });

    it('should have update method', () => {
      expect(typeof em.webhooks.update).toBe('function');
    });

    it('should have delete method', () => {
      expect(typeof em.webhooks.delete).toBe('function');
    });

    it('should have rotateSecret method', () => {
      expect(typeof em.webhooks.rotateSecret).toBe('function');
    });

    it('should have verifySignature method', () => {
      expect(typeof em.webhooks.verifySignature).toBe('function');
    });

    it('should verify valid signature', () => {
      const payload = '{"event":"test"}';
      const secret = 'test_secret';

      // Generate expected signature
      const crypto = require('crypto');
      const expected = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');
      const signature = `sha256=${expected}`;

      expect(em.webhooks.verifySignature(payload, signature, secret)).toBe(true);
    });

    it('should reject invalid signature', () => {
      const payload = '{"event":"test"}';
      const secret = 'test_secret';
      const invalidSignature = 'sha256=invalid_signature';

      expect(em.webhooks.verifySignature(payload, invalidSignature, secret)).toBe(false);
    });
  });
});
