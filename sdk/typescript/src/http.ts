/**
 * HTTP Client for Execution Market API
 *
 * Alternative HTTP client using native fetch (no axios dependency).
 * Use this for lightweight deployments or environments without axios.
 */

import {
  ExecutionMarketSDKError,
  AuthenticationError,
  ValidationFailedError,
  NetworkError,
  TimeoutError,
  createErrorFromResponse,
} from './errors';

interface HttpConfig {
  baseUrl: string;
  apiKey: string;
  timeout: number;
  retries: number;
}

/**
 * Lightweight HTTP client using native fetch.
 */
export class HttpClient {
  private readonly config: HttpConfig;

  constructor(config: HttpConfig) {
    this.config = config;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: Record<string, unknown>,
    params?: Record<string, unknown>
  ): Promise<T> {
    const url = new URL(path, this.config.baseUrl);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.set(key, String(value));
        }
      });
    }

    const headers: Record<string, string> = {
      'Authorization': `Bearer ${this.config.apiKey}`,
      'Content-Type': 'application/json',
      'User-Agent': '@execution-market/sdk-typescript/0.1.0',
    };

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.config.retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), this.config.timeout);

        const response = await fetch(url.toString(), {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });

        clearTimeout(timeout);

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({})) as Record<string, unknown>;
          throw createErrorFromResponse(response.status, errorData);
        }

        return await response.json() as T;
      } catch (error) {
        lastError = error as Error;

        // Don't retry auth or validation errors
        if (
          error instanceof AuthenticationError ||
          error instanceof ValidationFailedError
        ) {
          throw error;
        }

        // Handle abort/timeout
        if (error instanceof Error && error.name === 'AbortError') {
          throw new TimeoutError('request', this.config.timeout);
        }

        // Exponential backoff for retries
        if (attempt < this.config.retries) {
          await this.sleep(Math.pow(2, attempt) * 100);
        }
      }
    }

    // If we get here, all retries failed
    if (lastError instanceof ExecutionMarketSDKError) {
      throw lastError;
    }

    throw new NetworkError(
      lastError?.message || 'Request failed after retries',
      lastError || undefined
    );
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    return this.request('GET', path, undefined, params);
  }

  async post<T>(path: string, body?: Record<string, unknown>): Promise<T> {
    return this.request('POST', path, body);
  }

  async put<T>(path: string, body?: Record<string, unknown>): Promise<T> {
    return this.request('PUT', path, body);
  }

  async delete<T>(path: string): Promise<T> {
    return this.request('DELETE', path);
  }
}
