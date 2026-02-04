/**
 * Webhooks API
 *
 * Modular webhooks API for use with HttpClient.
 */

import { HttpClient } from '../http';
import type { WebhookEndpoint, WebhookEventType, ListResponse } from '../types';

/**
 * Webhooks API for managing webhook endpoints.
 */
export class WebhooksAPI {
  constructor(private readonly http: HttpClient) {}

  /**
   * Create a webhook endpoint.
   *
   * @param params - Webhook configuration
   * @returns Created webhook endpoint with secret
   *
   * @example
   * ```typescript
   * const webhook = await webhooks.create({
   *   url: 'https://myserver.com/webhooks/execution-market',
   *   events: ['task.completed', 'task.submitted']
   * });
   * // Save webhook.secret for verification!
   * ```
   */
  async create(params: {
    url: string;
    events: WebhookEventType[];
  }): Promise<WebhookEndpoint> {
    const response = await this.http.post<Record<string, unknown>>('/webhooks', params);
    return this.transformEndpoint(response);
  }

  /**
   * List all webhook endpoints.
   *
   * @returns List of webhook endpoints
   */
  async list(): Promise<ListResponse<WebhookEndpoint>> {
    const response = await this.http.get<{
      data?: Record<string, unknown>[];
      items?: Record<string, unknown>[];
      webhooks?: Record<string, unknown>[];
      total: number;
      hasMore?: boolean;
      has_more?: boolean;
    }>('/webhooks');

    const items = response.data || response.items || response.webhooks || [];

    return {
      data: items.map(e => this.transformEndpoint(e)),
      total: response.total || items.length,
      hasMore: response.hasMore || response.has_more || false,
    };
  }

  /**
   * Get a webhook endpoint by ID.
   *
   * @param webhookId - Webhook ID
   * @returns Webhook endpoint
   */
  async get(webhookId: string): Promise<WebhookEndpoint> {
    const response = await this.http.get<Record<string, unknown>>(
      `/webhooks/${webhookId}`
    );
    return this.transformEndpoint(response);
  }

  /**
   * Update a webhook endpoint.
   *
   * @param webhookId - Webhook ID
   * @param params - Update parameters
   * @returns Updated webhook endpoint
   */
  async update(
    webhookId: string,
    params: { url?: string; events?: WebhookEventType[]; active?: boolean }
  ): Promise<WebhookEndpoint> {
    const response = await this.http.put<Record<string, unknown>>(
      `/webhooks/${webhookId}`,
      params
    );
    return this.transformEndpoint(response);
  }

  /**
   * Delete a webhook endpoint.
   *
   * @param webhookId - Webhook ID
   */
  async delete(webhookId: string): Promise<void> {
    await this.http.delete(`/webhooks/${webhookId}`);
  }

  /**
   * Rotate webhook secret.
   *
   * @param webhookId - Webhook ID
   * @returns New secret
   */
  async rotateSecret(webhookId: string): Promise<{ secret: string }> {
    return this.http.post(`/webhooks/${webhookId}/rotate-secret`);
  }

  /**
   * Verify webhook signature using HMAC-SHA256.
   * Use this in your webhook handler to verify the request came from Execution Market.
   *
   * @param payload - Raw request body as string
   * @param signature - Value of X-EM-Signature header
   * @param secret - Webhook secret
   * @returns True if signature is valid
   *
   * @example
   * ```typescript
   * // Express.js example
   * app.post('/webhooks/execution-market', express.raw({ type: 'application/json' }), (req, res) => {
   *   const signature = req.headers['x-em-signature'] as string;
   *   const payload = req.body.toString();
   *
   *   if (!webhooks.verifySignature(payload, signature, WEBHOOK_SECRET)) {
   *     return res.status(401).send('Invalid signature');
   *   }
   *
   *   const event = JSON.parse(payload);
   *   // Process event...
   *   res.status(200).send('OK');
   * });
   * ```
   */
  verifySignature(payload: string, signature: string, secret: string): boolean {
    // Dynamic import to support both Node.js and browser environments
    try {
      // Node.js environment
      const crypto = require('crypto');
      const expected = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');

      const expectedSignature = `sha256=${expected}`;

      // Use timing-safe comparison to prevent timing attacks
      if (signature.length !== expectedSignature.length) {
        return false;
      }

      return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
      );
    } catch {
      // Browser environment - use SubtleCrypto
      // Note: This is synchronous fallback; for async use verifySignatureAsync
      console.warn(
        'verifySignature requires Node.js crypto module. ' +
        'Use verifySignatureAsync for browser environments.'
      );
      return false;
    }
  }

  /**
   * Verify webhook signature asynchronously (works in browsers).
   *
   * @param payload - Raw request body as string
   * @param signature - Value of X-EM-Signature header
   * @param secret - Webhook secret
   * @returns Promise resolving to true if signature is valid
   */
  async verifySignatureAsync(
    payload: string,
    signature: string,
    secret: string
  ): Promise<boolean> {
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );

    const signatureBytes = await crypto.subtle.sign(
      'HMAC',
      key,
      encoder.encode(payload)
    );

    const expected = `sha256=${Array.from(new Uint8Array(signatureBytes))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')}`;

    // Timing-safe comparison
    if (signature.length !== expected.length) {
      return false;
    }

    let result = 0;
    for (let i = 0; i < signature.length; i++) {
      result |= signature.charCodeAt(i) ^ expected.charCodeAt(i);
    }
    return result === 0;
  }

  /**
   * Transform API response to WebhookEndpoint object.
   */
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
