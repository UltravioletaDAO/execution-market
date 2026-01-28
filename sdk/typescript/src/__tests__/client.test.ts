/**
 * Chamba SDK Client Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { Chamba, createClient, AuthenticationError } from '../index';

describe('Chamba Client', () => {
  describe('initialization', () => {
    it('should throw AuthenticationError when no API key provided', () => {
      // Clear env var if set
      const originalKey = process.env.CHAMBA_API_KEY;
      delete process.env.CHAMBA_API_KEY;

      expect(() => new Chamba({ apiKey: '' })).toThrow(AuthenticationError);
      expect(() => createClient()).toThrow(AuthenticationError);

      // Restore
      if (originalKey) {
        process.env.CHAMBA_API_KEY = originalKey;
      }
    });

    it('should create client with valid API key', () => {
      const chamba = new Chamba({ apiKey: 'test_key_123' });

      expect(chamba).toBeInstanceOf(Chamba);
      expect(chamba.tasks).toBeDefined();
      expect(chamba.submissions).toBeDefined();
      expect(chamba.analytics).toBeDefined();
      expect(chamba.webhooks).toBeDefined();
    });

    it('should use custom base URL', () => {
      const chamba = new Chamba({
        apiKey: 'test_key_123',
        baseUrl: 'https://custom.api.com',
      });

      expect(chamba).toBeInstanceOf(Chamba);
    });

    it('should read API key from environment', () => {
      process.env.CHAMBA_API_KEY = 'env_key_456';

      const chamba = createClient();
      expect(chamba).toBeInstanceOf(Chamba);

      delete process.env.CHAMBA_API_KEY;
    });
  });

  describe('TasksAPI', () => {
    let chamba: Chamba;

    beforeEach(() => {
      chamba = new Chamba({ apiKey: 'test_key' });
    });

    it('should have create method', () => {
      expect(typeof chamba.tasks.create).toBe('function');
    });

    it('should have get method', () => {
      expect(typeof chamba.tasks.get).toBe('function');
    });

    it('should have list method', () => {
      expect(typeof chamba.tasks.list).toBe('function');
    });

    it('should have cancel method', () => {
      expect(typeof chamba.tasks.cancel).toBe('function');
    });

    it('should have batchCreate method', () => {
      expect(typeof chamba.tasks.batchCreate).toBe('function');
    });

    it('should have waitForCompletion method', () => {
      expect(typeof chamba.tasks.waitForCompletion).toBe('function');
    });

    it('should have onUpdate method', () => {
      expect(typeof chamba.tasks.onUpdate).toBe('function');
    });
  });

  describe('SubmissionsAPI', () => {
    let chamba: Chamba;

    beforeEach(() => {
      chamba = new Chamba({ apiKey: 'test_key' });
    });

    it('should have list method', () => {
      expect(typeof chamba.submissions.list).toBe('function');
    });

    it('should have get method', () => {
      expect(typeof chamba.submissions.get).toBe('function');
    });

    it('should have approve method', () => {
      expect(typeof chamba.submissions.approve).toBe('function');
    });

    it('should have reject method', () => {
      expect(typeof chamba.submissions.reject).toBe('function');
    });
  });

  describe('AnalyticsAPI', () => {
    let chamba: Chamba;

    beforeEach(() => {
      chamba = new Chamba({ apiKey: 'test_key' });
    });

    it('should have get method', () => {
      expect(typeof chamba.analytics.get).toBe('function');
    });
  });

  describe('WebhooksAPI', () => {
    let chamba: Chamba;

    beforeEach(() => {
      chamba = new Chamba({ apiKey: 'test_key' });
    });

    it('should have create method', () => {
      expect(typeof chamba.webhooks.create).toBe('function');
    });

    it('should have list method', () => {
      expect(typeof chamba.webhooks.list).toBe('function');
    });

    it('should have get method', () => {
      expect(typeof chamba.webhooks.get).toBe('function');
    });

    it('should have update method', () => {
      expect(typeof chamba.webhooks.update).toBe('function');
    });

    it('should have delete method', () => {
      expect(typeof chamba.webhooks.delete).toBe('function');
    });

    it('should have rotateSecret method', () => {
      expect(typeof chamba.webhooks.rotateSecret).toBe('function');
    });

    it('should have verifySignature method', () => {
      expect(typeof chamba.webhooks.verifySignature).toBe('function');
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

      expect(chamba.webhooks.verifySignature(payload, signature, secret)).toBe(true);
    });

    it('should reject invalid signature', () => {
      const payload = '{"event":"test"}';
      const secret = 'test_secret';
      const invalidSignature = 'sha256=invalid_signature';

      expect(chamba.webhooks.verifySignature(payload, invalidSignature, secret)).toBe(false);
    });
  });
});
