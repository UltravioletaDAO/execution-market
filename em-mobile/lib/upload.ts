import * as FileSystem from "expo-file-system/legacy";
import { apiClient } from "./api";

interface UploadResult {
  url: string;
  key: string;
  filename: string;
}

interface PresignResponse {
  upload_url: string;
  key: string;
  public_url: string | null;
  content_type: string;
  expires_in: number;
  nonce: string;
}

/**
 * Upload evidence file to S3 via presigned URL.
 *
 * Flow:
 *   1. Call backend GET /api/v1/evidence/presign-upload → get presigned PUT URL
 *   2. Read file as base64 → convert to blob
 *   3. PUT directly to S3 using presigned URL
 *   4. Return CloudFront public URL (or S3 key for presigned download)
 *
 * Uses legacy expo-file-system import for readAsStringAsync (base64 reading).
 * SDK 54 deprecated the top-level API; new File class doesn't have base64 read yet.
 */
export async function uploadEvidence(
  fileUri: string,
  taskId: string,
  evidenceType: string,
  executorId: string,
  contentType: string = "image/jpeg"
): Promise<UploadResult> {
  const timestamp = Date.now();
  const extension = contentType.includes("png") ? "png" : contentType.includes("webp") ? "webp" : "jpg";
  const filename = `${evidenceType}_${timestamp}.${extension}`;

  __DEV__ && console.log("[Upload] Starting S3 presigned upload:", { fileUri: fileUri.slice(0, 80), filename });

  // Step 1: Get presigned upload URL from backend
  const params = new URLSearchParams({
    task_id: taskId,
    executor_id: executorId,
    filename,
    evidence_type: evidenceType,
    content_type: contentType,
  });

  let presign: PresignResponse;
  try {
    presign = await apiClient<PresignResponse>(`/api/v1/evidence/presign-upload?${params}`);
  } catch (err) {
    __DEV__ && console.error("[Upload] Failed to get presigned URL:", err);
    throw new Error(`Failed to get upload URL: ${(err as Error).message}`);
  }

  __DEV__ && console.log("[Upload] Got presigned URL, key:", presign.key);

  // Step 2: Read file as base64
  let base64: string;
  try {
    base64 = await FileSystem.readAsStringAsync(fileUri, {
      encoding: FileSystem.EncodingType.Base64,
    });
  } catch (readErr) {
    __DEV__ && console.error("[Upload] readAsStringAsync failed:", readErr);
    throw new Error(`Failed to read photo: ${(readErr as Error).message}`);
  }

  if (!base64 || base64.length === 0) {
    throw new Error("Photo file is empty or unreadable");
  }

  __DEV__ && console.log("[Upload] Read base64, length:", base64.length);

  // Step 3: Convert base64 to Uint8Array for fetch body
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  __DEV__ && console.log("[Upload] Converted to binary, size:", bytes.byteLength);

  // Step 4: PUT directly to S3
  try {
    const response = await fetch(presign.upload_url, {
      method: "PUT",
      headers: {
        "Content-Type": contentType,
      },
      body: bytes,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      __DEV__ && console.error("[Upload] S3 PUT failed:", response.status, text.slice(0, 200));
      throw new Error(`S3 upload failed: ${response.status}`);
    }
  } catch (putErr) {
    __DEV__ && console.error("[Upload] PUT to S3 failed:", putErr);
    throw new Error(`Upload failed: ${(putErr as Error).message}`);
  }

  __DEV__ && console.log("[Upload] S3 upload success, key:", presign.key);

  // Use public URL (CloudFront) if available, otherwise construct key-based URL
  const url = presign.public_url || presign.key;

  return {
    url,
    key: presign.key,
    filename,
  };
}

export async function uploadMultipleEvidence(
  files: Array<{
    uri: string;
    taskId: string;
    evidenceType: string;
    executorId: string;
    contentType?: string;
  }>
): Promise<UploadResult[]> {
  return Promise.all(
    files.map((f) =>
      uploadEvidence(f.uri, f.taskId, f.evidenceType, f.executorId, f.contentType || "image/jpeg")
    )
  );
}
