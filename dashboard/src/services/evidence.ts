/**
 * Evidence Upload Service
 *
 * Supports two backends:
 * 1. S3 presigned URLs via /api/v1/evidence/presign-upload (primary)
 * 2. Supabase Storage direct upload (fallback when S3 fails)
 *
 * Also computes SHA-256 checksums and collects forensic metadata.
 */

import { supabase } from '../lib/supabase'

const EVIDENCE_API_URL = import.meta.env.VITE_EVIDENCE_API_URL || ''
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || ''

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

/** Get a presigned upload URL from the backend. */
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
    task_id: params.taskId,
    executor_id: params.actorId,
    filename: params.filename,
    content_type: params.contentType,
    evidence_type: params.evidenceType,
  })
  if (params.checksum) qs.set('checksum', params.checksum)

  const res = await fetch(`${EVIDENCE_API_URL}/presign-upload?${qs.toString()}`)
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

    if (presigned.metadata) {
      for (const [k, v] of Object.entries(presigned.metadata)) {
        xhr.setRequestHeader(`x-amz-meta-${k}`, v)
      }
    }

    xhr.send(file)
  })
}

/**
 * Upload evidence file to Supabase Storage (fallback).
 * Path is scoped to executor/task so RLS can enforce ownership.
 */
async function uploadToSupabase(
  file: File,
  executorId: string,
  taskId: string,
  evidenceType: string,
  onProgress?: (pct: number) => void,
): Promise<{ path: string; public_url: string | null }> {
  const ext = file.name.includes('.') ? file.name.split('.').pop() : 'bin'
  const path = `${executorId}/${taskId}/${evidenceType}_${Date.now()}.${ext}`

  // Use Supabase Storage JS client — respects RLS policies on the bucket
  const { data, error } = await supabase.storage
    .from('evidence')
    .upload(path, file, {
      contentType: file.type || 'application/octet-stream',
      upsert: false,
    })

  if (error) throw new Error(`Supabase upload failed: ${error.message}`)

  onProgress?.(100)

  const { data: urlData } = supabase.storage.from('evidence').getPublicUrl(data.path)
  const public_url = urlData?.publicUrl || `${SUPABASE_URL}/storage/v1/object/public/evidence/${data.path}`

  return { path: data.path, public_url }
}

/**
 * Upload evidence file.
 * Primary: S3 via presigned URL.
 * Fallback: Supabase Storage (when S3 is unavailable or fails).
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

  const checksum = await computeChecksum(file)

  // --- Primary: S3 presigned URL pipeline ---
  if (isS3PipelineEnabled()) {
    try {
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
    } catch (s3Error) {
      console.warn('[Evidence] S3 upload failed, falling back to Supabase Storage:', s3Error)
    }
  }

  // --- Fallback: Supabase Storage ---
  const { path, public_url } = await uploadToSupabase(file, executorId, taskId, evidenceType, onProgress)

  return {
    key: path,
    public_url,
    backend: 'supabase',
    checksum,
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
    // GPS not available — that's fine
  }

  metadata.capture_timestamp = new Date().toISOString()
  return metadata
}
