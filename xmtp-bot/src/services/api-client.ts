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
    taskId: string,
    executorId: string,
  ): Promise<{ upload_url: string; key: string; public_url: string | null; content_type: string }> {
    return this.get("/api/v1/evidence/presign-upload", {
      params: {
        task_id: taskId,
        executor_id: executorId,
        filename,
        content_type: contentType,
      },
    });
  }

  /**
   * Uploads a file buffer to S3 using a presigned PUT URL.
   * Returns the public CDN URL for the uploaded file.
   */
  async uploadToS3(
    presigned: { upload_url: string; key: string; public_url: string | null; content_type: string },
    data: Buffer,
    contentType: string,
  ): Promise<string> {
    await axios.put(presigned.upload_url, data, {
      headers: {
        "Content-Type": contentType,
        "Content-Length": data.byteLength.toString(),
      },
      timeout: 60_000,
      maxBodyLength: 30 * 1024 * 1024,
    });

    // Return the CDN URL if available, otherwise derive from key
    return presigned.public_url ?? presigned.upload_url.split("?")[0];
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
