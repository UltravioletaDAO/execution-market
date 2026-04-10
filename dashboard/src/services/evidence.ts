/**
 * Evidence Upload Service
 *
 * Supports two backends:
 * 1. S3 presigned URLs via evidence Lambda (when VITE_EVIDENCE_API_URL is set)
 * 2. Supabase Storage direct upload (fallback)
 *
 * Also computes SHA-256 checksums and collects forensic metadata.
 */

const EVIDENCE_API_URL = import.meta.env.VITE_EVIDENCE_API_URL || ''

export interface EvidenceMetadata {
  gps?: {
    latitude: number
    longitude: number
    accuracy: number
    altitude?: number | null
    timestamp: number
  }
  device?: {
    userAgent: string
    platform: string
  }
  exif?: Record<string, unknown>
  source?: 'camera' | 'gallery' | 'unknown'
  capture_timestamp?: string
  checksums?: {
    sha256: string
  }
}

export interface PresignedUploadResult {
  mode: 'put' | 'post'
  key: string
  upload_url: string
  fields?: Record<string, string>  // only for POST mode
  content_type: string
  expires_in: number
  nonce: string
  public_url: string | null
  max_upload_mb: number
  metadata?: Record<string, string>
}

export interface UploadResult {
  key: string
  public_url: string | null
  backend: 's3' | 'supabase'
  checksum: string
  nonce?: string
}

/** Compute SHA-256 hex digest of a File. */
export async function computeChecksum(file: File): Promise<string> {
  const buffer = await file.arrayBuffer()
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

/** Check if S3 evidence pipeline is available. */
export function isS3PipelineEnabled(): boolean {
  return !!EVIDENCE_API_URL
}

/** Get a presigned upload URL from the evidence Lambda. */
async function getPresignedUrl(params: {
  taskId: string
  submissionId?: string
  actorId: string
  filename: string
  contentType: string
  evidenceType: string
  checksum?: string
}): Promise<PresignedUploadResult> {
  const qs = new URLSearchParams({
    taskId: params.taskId,
    actorId: params.actorId,
    filename: params.filename,
    contentType: params.contentType,
    evidenceType: params.evidenceType,
    mode: 'put',
  })
  if (params.submissionId) qs.set('submissionId', params.submissionId)
  if (params.checksum) qs.set('checksum', params.checksum)

  const res = await fetch(`${EVIDENCE_API_URL}/upload-url?${qs.toString()}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || `Presigned URL request failed: ${res.status}`)
  }
  return res.json()
}

/** Upload a file to S3 using a presigned PUT URL. */
async function uploadToS3(
  presigned: PresignedUploadResult,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve()
      } else {
        reject(new Error(`S3 upload failed: ${xhr.status} ${xhr.statusText}`))
      }
    })

    xhr.addEventListener('error', () => reject(new Error('Network error during S3 upload')))
    xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')))

    xhr.open('PUT', presigned.upload_url)
    xhr.setRequestHeader('Content-Type', presigned.content_type)

    // Add metadata headers for PUT mode
    if (presigned.metadata) {
      for (const [k, v] of Object.entries(presigned.metadata)) {
        xhr.setRequestHeader(`x-amz-meta-${k}`, v)
      }
    }

    xhr.send(file)
  })
}

/**
 * Upload evidence file via S3 presigned URLs.
 * Direct Supabase Storage uploads are no longer allowed (DB-008 security lockdown).
 * The S3 presigned URL pipeline (VITE_EVIDENCE_API_URL) is required.
 */
export async function uploadEvidenceFile(params: {
  file: File
  taskId: string
  executorId: string
  evidenceType: string
  submissionId?: string
  onProgress?: (pct: number) => void
}): Promise<UploadResult> {
  const { file, taskId, executorId, evidenceType, submissionId, onProgress } = params

  if (!isS3PipelineEnabled()) {
    throw new Error(
      'Evidence upload requires VITE_EVIDENCE_API_URL to be configured. ' +
      'Direct Supabase Storage uploads are disabled for security (DB-008).'
    )
  }

  // Compute checksum
  const checksum = await computeChecksum(file)

  // S3 presigned URL flow
  const presigned = await getPresignedUrl({
    taskId,
    submissionId,
    actorId: executorId,
    filename: file.name,
    contentType: file.type || 'application/octet-stream',
    evidenceType,
    checksum,
  })

  await uploadToS3(presigned, file, onProgress)

  return {
    key: presigned.key,
    public_url: presigned.public_url,
    backend: 's3',
    checksum,
    nonce: presigned.nonce,
  }
}

/** Collect forensic metadata from the browser environment. */
export async function collectForensicMetadata(): Promise<EvidenceMetadata> {
  const metadata: EvidenceMetadata = {
    device: {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
    },
    source: 'unknown',
  }

  // Try to get GPS
  try {
    const position = await new Promise<GeolocationPosition>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      })
    })
    metadata.gps = {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy,
      altitude: position.coords.altitude,
      timestamp: position.timestamp,
    }
  } catch {
    // GPS not available — that's fine, not all tasks require it
  }

  metadata.capture_timestamp = new Date().toISOString()
  return metadata
}
