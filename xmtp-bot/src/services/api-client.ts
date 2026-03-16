// src/services/api-client.ts
import axios, { type AxiosInstance, type AxiosRequestConfig } from "axios";
import { config } from "../config.js";
import { logger } from "../utils/logger.js";

class EMApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.em.apiUrl,
      timeout: 15_000,
      headers: {
        "X-API-Key": config.em.apiKey,
        "Content-Type": "application/json",
      },
    });

    // Retry interceptor for 5xx errors
    this.client.interceptors.response.use(undefined, async (error) => {
      const cfg = error.config as AxiosRequestConfig & { __retryCount?: number };
      const status = error?.response?.status ?? 0;
      const retryCount = cfg.__retryCount ?? 0;

      if (status >= 500 && retryCount < 2) {
        cfg.__retryCount = retryCount + 1;
        const delay = 1000 * Math.pow(2, retryCount);
        logger.warn({ status, retry: retryCount + 1, delay }, "Retrying API request");
        await new Promise((r) => setTimeout(r, delay));
        return this.client.request(cfg);
      }

      throw error;
    });
  }

  async get<T>(path: string, cfg?: AxiosRequestConfig): Promise<T> {
    const res = await this.client.get(path, cfg);
    return res.data;
  }

  async post<T>(path: string, data?: unknown): Promise<T> {
    const res = await this.client.post(path, data);
    return res.data;
  }

  async resolveTask(idOrPartial: string): Promise<any | null> {
    // Try full UUID first
    try {
      return await this.get(`/api/v1/tasks/${idOrPartial}`);
    } catch {
      // Try partial match on task list
      try {
        const all = await this.get<any>("/api/v1/tasks", {
          params: { limit: "50" },
        });
        const tasks = Array.isArray(all) ? all : all.tasks ?? [];
        const match = tasks.find((t: any) =>
          t.id.toLowerCase().startsWith(idOrPartial.toLowerCase())
        );
        return match ?? null;
      } catch {
        return null;
      }
    }
  }

  async getPresignedUploadUrl(
    filename: string,
    contentType: string,
    taskId: string
  ): Promise<{ url: string; fields: Record<string, string>; cdnUrl: string }> {
    return this.post("/api/v1/uploads/presign", {
      filename,
      content_type: contentType,
      task_id: taskId,
    });
  }

  async submitEvidence(
    taskId: string,
    executorId: string,
    evidence: Record<string, unknown>
  ): Promise<any> {
    return this.post(`/api/v1/tasks/${taskId}/submit`, {
      executor_id: executorId,
      evidence,
    });
  }
}

export const apiClient = new EMApiClient();
