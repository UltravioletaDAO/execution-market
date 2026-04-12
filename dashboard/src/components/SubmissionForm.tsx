// Execution Market: Evidence Submission Form
// Uses the full EvidenceUpload component (camera, GPS, EXIF) for photo types
// and file inputs for non-photo types (video, document, etc.)
import { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import type { Task, EvidenceType, TaskCategory, Executor } from '../types/database'
import {
  uploadEvidenceFile,
  collectForensicMetadata,
  type EvidenceMetadata,
  type UploadResult,
} from '../services/evidence'
import { submitWork, type VerificationResponse } from '../services/submissions'
import { getTask } from '../services/tasks'
import type { Evidence } from '../services/types'
import {
  EvidenceUpload,
  type UploadedEvidence,
} from './evidence/EvidenceUpload'
import { GeofenceAlert } from './GeofenceAlert'
import { EvidenceVerificationPanel } from './EvidenceVerificationPanel'
import { AIAnalysisDetails } from './AIAnalysisDetails'
import type { AIAnalysisResult } from './AIAnalysisDetails'
import { supabase } from '../lib/supabase'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const API_URL = import.meta.env.VITE_API_URL || 'https://api.execution.market'

interface SubmissionFormProps {
  task: Task
  executor: Executor
  onSubmit?: (verification?: VerificationResponse | null) => void
  onCancel?: () => void
}

interface VerificationResult {
  verified: boolean
  confidence: number
  decision: string
  explanation: string
  issues: string[]
}

interface EvidenceFile {
  type: EvidenceType
  file: File
  preview?: string
  uploading: boolean
  uploaded: boolean
  uploadedPath?: string
  uploadResult?: UploadResult
  progress: number // 0-100
  error?: string
  verifying?: boolean
  verification?: VerificationResult
}

// Task categories where camera + GPS are the primary evidence mode
const PHYSICAL_TASK_CATEGORIES: TaskCategory[] = [
  'physical_presence',
  'simple_action',
]

// Determine if photo types should use camera (physical tasks) or file upload (digital tasks)
function isCameraType(type: EvidenceType, category?: TaskCategory): boolean {
  if (type === 'photo_geo') return true // Always camera + GPS
  if (type === 'photo') {
    return category ? PHYSICAL_TASK_CATEGORIES.includes(category) : false
  }
  return false
}

const EVIDENCE_TYPE_CONFIG: Record<string, { accept: string; icon: string }> = {
  photo: { accept: 'image/*', icon: '📷' },
  video: { accept: 'video/*', icon: '🎥' },
  document: { accept: '.pdf,.doc,.docx', icon: '📄' },
  receipt: { accept: 'image/*,.pdf', icon: '🧾' },
  signature: { accept: 'image/*', icon: '✍️' },
  notarized: { accept: '.pdf,image/*', icon: '📋' },
  timestamp_proof: { accept: 'image/*,.pdf', icon: '⏰' },
  screenshot: { accept: 'image/*', icon: '🖥️' },
  text_response: { accept: '', icon: '📝' },
  measurement: { accept: '', icon: '📏' },
  json_response: { accept: '', icon: '{}' },
  api_response: { accept: '', icon: '🔌' },
  code_output: { accept: '', icon: '💻' },
  file_artifact: { accept: '*/*', icon: '📦' },
  url_reference: { accept: '', icon: '🔗' },
  structured_data: { accept: '.json,.csv,.xml', icon: '📊' },
  text_report: { accept: '', icon: '📄' },
}

// Category-specific guidance messages (Spanish)
const CATEGORY_GUIDANCE: Partial<Record<TaskCategory, string>> = {
  physical_presence: 'Esta tarea requiere presencia fisica. Usa la camara y GPS para verificar tu ubicacion.',
  simple_action: 'Documenta la accion con fotos o video. GPS ayuda a verificar la entrega.',
  knowledge_access: 'Sube capturas de pantalla, documentos o texto desde tu computador.',
  digital_physical: 'Puedes subir fotos, archivos o capturas de pantalla desde cualquier dispositivo.',
  research: 'Envia tu investigacion como texto, documentos o enlaces.',
  content_generation: 'Sube el contenido generado como archivo, texto o enlace.',
  code_execution: 'Envia el output del codigo, logs o archivos resultantes.',
  data_processing: 'Sube los datos procesados como archivo o respuesta estructurada.',
  api_integration: 'Envia capturas, logs de API o respuestas JSON.',
  human_authority: 'Sube documentos firmados, notarizados o certificados.',
}

const isImageType = (fileType: string) => fileType.startsWith('image/')

export function SubmissionForm({
  task,
  executor,
  onSubmit,
  onCancel,
}: SubmissionFormProps) {
  const { t } = useTranslation()
  // File-based evidence (non-camera types)
  const [files, setFiles] = useState<Map<EvidenceType, EvidenceFile>>(new Map())
  // Text evidence
  const [textResponses, setTextResponses] = useState<Map<string, string>>(new Map())
  // Camera evidence from EvidenceUpload component
  const [cameraEvidence, setCameraEvidence] = useState<UploadedEvidence[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [pollingStatus, setPollingStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isOutsideGeofence, setIsOutsideGeofence] = useState(false)
  const [verificationDetails, setVerificationDetails] = useState<Record<string, unknown> | null>(null)
  const [aiVerificationResult, setAiVerificationResult] = useState<Record<string, unknown> | null>(null)
  const [submissionId, setSubmissionId] = useState<string | null>(null)
  const fileInputRefs = useRef<Map<string, HTMLInputElement>>(new Map())
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const phaseBPollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const allRequired = task.evidence_schema.required
  const allOptional = task.evidence_schema.optional || []
  const [forensicMetadata, setForensicMetadata] = useState<EvidenceMetadata | null>(null)

  // Categorize evidence types based on task category
  const category = task.category as TaskCategory
  const cameraRequired = allRequired.filter((t) => isCameraType(t, category))
  const cameraOptional = allOptional.filter((t) => isCameraType(t, category))
  const fileRequired = allRequired.filter((t) => !isCameraType(t, category) && !isTextType(t))
  const fileOptional = allOptional.filter((t) => !isCameraType(t, category) && !isTextType(t))
  const textRequired = allRequired.filter(isTextType)
  const textOptional = allOptional.filter(isTextType)

  const hasCameraTypes = cameraRequired.length > 0 || cameraOptional.length > 0

  // Collect forensic metadata once on mount
  useEffect(() => {
    collectForensicMetadata().then(setForensicMetadata).catch(() => {})
  }, [])

  // Post-submission polling: check task status every 5s until it changes from "submitted"
  useEffect(() => {
    if (!submitted) return

    pollIntervalRef.current = setInterval(async () => {
      try {
        const updatedTask = await getTask(task.id)
        if (updatedTask && updatedTask.status !== 'submitted') {
          setPollingStatus(updatedTask.status)
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
        }
      } catch {
        // Silently retry on next interval
      }
    }, 5000)

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
  }, [submitted, task.id])

  // Refresh callback for EvidenceVerificationPanel auto-poll
  const refreshVerificationDetails = useCallback(async () => {
    if (!submissionId) return
    try {
      const { data } = await supabase
        .from('submissions')
        .select('auto_check_details, ai_verification_result')
        .eq('id', submissionId)
        .single()
      if (data?.auto_check_details) {
        setVerificationDetails(data.auto_check_details as Record<string, unknown>)
        if (data.ai_verification_result) {
          setAiVerificationResult(data.ai_verification_result as Record<string, unknown>)
        }
      }
    } catch {
      // Silently ignore
    }
  }, [submissionId])

  // Phase B polling: fetch submission auto_check_details until phase === 'AB' (max 60s)
  useEffect(() => {
    if (!submitted || !submissionId) return

    let iterations = 0
    const MAX_ITERATIONS = 12 // 12 * 5s = 60s

    phaseBPollRef.current = setInterval(async () => {
      iterations++
      try {
        const { data } = await supabase
          .from('submissions')
          .select('auto_check_details, ai_verification_result')
          .eq('id', submissionId)
          .single()

        if (data?.auto_check_details) {
          const details = data.auto_check_details as Record<string, unknown>
          // Always update with latest details (Phase A or AB)
          setVerificationDetails(details)
          if (data.ai_verification_result) {
            setAiVerificationResult(data.ai_verification_result as Record<string, unknown>)
          }

          // Stop polling when Phase B is complete or forensic events are done
          const vEvents = details.verification_events as Array<{ step: string; status: string; ring: number }> | undefined
          const forensicDone = Array.isArray(vEvents) && vEvents.length > 0 &&
            vEvents.some((e) => e.step === 'ring1_complete' && (e.status === 'complete' || e.status === 'failed')) &&
            (!vEvents.some((e) => e.ring === 2) ||
              vEvents.some((e) => e.step === 'ring2_complete' && (e.status === 'complete' || e.status === 'failed')))

          if (details.phase === 'AB' || forensicDone) {
            if (phaseBPollRef.current) {
              clearInterval(phaseBPollRef.current)
              phaseBPollRef.current = null
            }
          }
        }
      } catch {
        // Silently retry on next interval
      }

      // Stop after max iterations to avoid infinite polling
      if (iterations >= MAX_ITERATIONS && phaseBPollRef.current) {
        clearInterval(phaseBPollRef.current)
        phaseBPollRef.current = null
      }
    }, 5000)

    return () => {
      if (phaseBPollRef.current) {
        clearInterval(phaseBPollRef.current)
        phaseBPollRef.current = null
      }
    }
  }, [submitted, submissionId])

  // Parse task location hint into coordinates if available
  const taskLocation = (() => {
    const hint = task.location_hint
    if (!hint) return undefined
    // Try to parse "lat,lng" or "lat, lng" format
    const match = hint.match(/(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)/)
    if (match) {
      return { lat: parseFloat(match[1]), lng: parseFloat(match[2]), radiusKm: 1 }
    }
    return undefined
  })()

  // Camera evidence handlers
  const handleCameraComplete = useCallback((evidence: UploadedEvidence[]) => {
    setCameraEvidence(evidence)
  }, [])

  const handleCameraEvidenceAdded = useCallback((ev: UploadedEvidence) => {
    setCameraEvidence((prev) => [...prev.filter((e) => e.evidenceType !== ev.evidenceType), ev])
  }, [])

  // File-based evidence handlers
  const doUpload = useCallback(async (evidenceFile: EvidenceFile): Promise<UploadResult> => {
    return uploadEvidenceFile({
      file: evidenceFile.file,
      taskId: task.id,
      executorId: executor.id,
      evidenceType: evidenceFile.type,
      onProgress: (pct) => {
        setFiles((prev) => {
          const next = new Map(prev)
          const f = next.get(evidenceFile.type)
          if (f) next.set(evidenceFile.type, { ...f, progress: pct })
          return next
        })
      },
    })
  }, [task.id, executor.id])

  const verifyEvidence = useCallback(async (path: string, evidenceType: EvidenceType) => {
    try {
      const publicUrl = `${SUPABASE_URL}/storage/v1/object/public/evidence/${path}`
      const res = await fetch(`${API_URL}/api/v1/evidence/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: task.id,
          evidence_url: publicUrl,
          evidence_type: evidenceType,
        }),
      })
      if (res.ok) {
        return (await res.json()) as VerificationResult
      }
      return null
    } catch {
      return null
    }
  }, [task.id])

  const handleFileSelect = useCallback(
    async (type: EvidenceType, file: File) => {
      let preview: string | undefined
      if (file.type.startsWith('image/')) {
        preview = URL.createObjectURL(file)
      }

      const evidenceFile: EvidenceFile = {
        type, file, preview,
        uploading: true, uploaded: false, progress: 0,
      }

      setFiles((prev) => new Map(prev).set(type, evidenceFile))

      try {
        const result = await doUpload(evidenceFile)
        const path = result.key

        setFiles((prev) => {
          const next = new Map(prev)
          next.set(type, { ...evidenceFile, uploading: false, uploaded: true, uploadedPath: path, uploadResult: result, progress: 100 })
          return next
        })

        if (isImageType(file.type)) {
          setFiles((prev) => {
            const next = new Map(prev)
            const f = next.get(type)
            if (f) next.set(type, { ...f, verifying: true })
            return next
          })

          const verification = await verifyEvidence(path, type)

          setFiles((prev) => {
            const next = new Map(prev)
            const f = next.get(type)
            if (f) next.set(type, { ...f, verifying: false, verification: verification || undefined })
            return next
          })
        }
      } catch {
        setFiles((prev) => {
          const next = new Map(prev)
          const f = next.get(type)
          if (f) next.set(type, { ...f, uploading: false, error: t('submission.uploadError') })
          return next
        })
      }
    },
    [t, doUpload, verifyEvidence],
  )

  const handleTextChange = useCallback((type: string, value: string) => {
    setTextResponses((prev) => {
      const next = new Map(prev)
      next.set(type, value)
      return next
    })
  }, [])

  const removeFile = useCallback((type: EvidenceType) => {
    setFiles((prev) => {
      const next = new Map(prev)
      const existing = next.get(type)
      if (existing?.preview) {
        URL.revokeObjectURL(existing.preview)
      }
      next.delete(type)
      return next
    })
    const input = fileInputRefs.current.get(type)
    if (input) input.value = ''
  }, [])

  const FUNDED_STATUSES = ['funded', 'locked', 'deposited', 'active', 'partial_released']
  const escrowReady = !task.escrow_status || FUNDED_STATUSES.includes(task.escrow_status)

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)

    try {
      // Block submission if escrow is not funded on-chain
      if (task.escrow_status && !FUNDED_STATUSES.includes(task.escrow_status)) {
        throw new Error(
          `Escrow not confirmed on-chain (status: ${task.escrow_status}). Wait for the agent to fund this task.`,
        )
      }

      // Validate required evidence across all sources
      const cameraEvidenceTypes = new Set(cameraEvidence.map((e) => e.evidenceType))
      const missingRequired = allRequired.filter((evType) => {
        if (isTextType(evType)) return !textResponses.get(evType)?.trim()
        if (isCameraType(evType, category)) return !cameraEvidenceTypes.has(evType)
        return !files.has(evType)
      })

      if (missingRequired.length > 0) {
        const items = missingRequired
          .map((evType) => t(`tasks.evidenceTypes.${evType}`, evType))
          .join(', ')
        throw new Error(t('submission.missingEvidence', { items }))
      }

      // Check all file-based evidence is uploaded
      const notUploaded = [...files.values()].filter((f) => !f.uploaded)
      if (notUploaded.length > 0) {
        throw new Error(t('submission.uploadError'))
      }

      // Build evidence record from all sources
      const evidence: Record<string, Evidence> = {}

      // 1. Camera evidence (from EvidenceUpload component)
      for (const uploaded of cameraEvidence) {
        evidence[uploaded.evidenceType] = {
          type: uploaded.evidenceType,
          fileUrl: uploaded.url,
          filename: uploaded.metadata.filename,
          mimeType: uploaded.metadata.mimeType,
          metadata: {
            size: uploaded.metadata.size,
            storagePath: uploaded.path,
            source: uploaded.metadata.source,
            gps: uploaded.metadata.gps,
            captureTimestamp: uploaded.metadata.captureTimestamp,
            deviceInfo: uploaded.metadata.deviceInfo,
            imageWidth: uploaded.metadata.imageWidth,
            imageHeight: uploaded.metadata.imageHeight,
            verification: uploaded.verification,
          },
        }
      }

      // 2. File-based evidence
      for (const [type, evidenceFile] of files) {
        if (evidenceFile.uploadedPath) {
          const entry: Evidence = {
            type,
            fileUrl: evidenceFile.uploadResult?.public_url || evidenceFile.uploadedPath,
            filename: evidenceFile.file.name,
            mimeType: evidenceFile.file.type,
            metadata: {
              size: evidenceFile.file.size,
              storagePath: evidenceFile.uploadedPath,
              backend: evidenceFile.uploadResult?.backend,
              checksum: evidenceFile.uploadResult?.checksum,
            },
          }
          if (evidenceFile.uploadResult?.nonce) {
            entry.metadata!.nonce = evidenceFile.uploadResult.nonce
          }
          if (evidenceFile.verification) {
            entry.metadata!.ai_verification = {
              verified: evidenceFile.verification.verified,
              confidence: evidenceFile.verification.confidence,
              decision: evidenceFile.verification.decision,
            }
          }
          if (forensicMetadata) {
            entry.metadata!.forensic = forensicMetadata
          }
          evidence[type] = entry
        }
      }

      // 3. Text responses
      for (const [type, value] of textResponses) {
        if (value.trim()) {
          evidence[type] = {
            type,
            value: value.trim(),
          }
        }
      }

      const result = await submitWork({
        taskId: task.id,
        executorId: executor.id,
        evidence,
      })

      setSubmitted(true)
      setSubmissionId(result.submission.id)
      setVerificationDetails(result.verification as Record<string, unknown> | null)
      onSubmit?.(result.verification)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('submission.submitError'))
    } finally {
      setSubmitting(false)
    }
  }

  const renderVerificationBadge = (evidenceFile: EvidenceFile) => {
    if (evidenceFile.verifying) {
      return (
        <div className="mt-2 flex items-center gap-2 text-sm text-blue-600">
          <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>{t('submission.verifying')}</span>
        </div>
      )
    }

    if (!evidenceFile.verification) return null

    const v = evidenceFile.verification
    if (v.verified) {
      return (
        <div className="mt-2 flex items-center gap-2 text-sm text-green-600">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          <span>{t('submission.verifyPass')}</span>
        </div>
      )
    }

    if (v.decision === 'needs_human' && v.confidence === 0) {
      return null
    }

    return (
      <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="flex items-center gap-2 text-sm text-yellow-700">
          <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span className="font-medium">{t('submission.verifyFail')}</span>
        </div>
        {v.explanation && (
          <p className="text-xs text-yellow-600 mt-1 ml-6">{v.explanation}</p>
        )}
        {v.issues.length > 0 && (
          <ul className="text-xs text-yellow-600 mt-1 ml-6 list-disc list-inside">
            {v.issues.map((issue, i) => <li key={i}>{issue}</li>)}
          </ul>
        )}
      </div>
    )
  }

  const renderFileInput = (type: EvidenceType, required: boolean) => {
    const config = EVIDENCE_TYPE_CONFIG[type]
    const evidenceFile = files.get(type)
    const label = t(`tasks.evidenceTypes.${type}`, type)

    return (
      <div key={type} className="p-4 border border-gray-200 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="flex items-center gap-2 font-medium text-gray-700">
            <span>{config?.icon}</span>
            <span>{label}</span>
            {required && <span className="text-red-500">*</span>}
          </span>
          {evidenceFile?.uploaded && !evidenceFile.uploading && (
            <span className="flex items-center gap-2">
              <span className="text-green-600 text-sm">✓</span>
              <button
                onClick={() => removeFile(type)}
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                {t('submission.change')}
              </button>
            </span>
          )}
        </div>

        {evidenceFile ? (
          <div className="relative">
            {evidenceFile.preview ? (
              // NOTE: evidenceFile.preview is a blob: URL created locally by
              // URL.createObjectURL() on the user's just-picked File. It is
              // NOT user-supplied data from the network, so it must NOT be
              // passed through safeSrc() (which would block blob:).
              // See dashboard/src/lib/safeHref.ts and FE-005.
              <img
                src={evidenceFile.preview}
                alt={`Preview ${type}`}
                className="w-full h-48 object-cover rounded-lg"
              />
            ) : (
              <div className="w-full h-24 bg-gray-100 rounded-lg flex items-center justify-center">
                <span className="text-gray-500">{evidenceFile.file.name}</span>
              </div>
            )}

            {evidenceFile.uploading && (
              <div className="absolute inset-0 bg-black/70 rounded-lg flex flex-col items-center justify-center p-4">
                <div className="w-full max-w-[200px] mb-2">
                  <div className="h-2 bg-white/30 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-white rounded-full transition-all duration-300"
                      style={{ width: `${evidenceFile.progress}%` }}
                    />
                  </div>
                </div>
                <div className="text-white text-sm font-medium">
                  {t('submission.uploading', { progress: evidenceFile.progress })}
                </div>
              </div>
            )}

            {evidenceFile.error && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-sm text-red-600">{evidenceFile.error}</span>
                <button
                  onClick={() => {
                    const file = evidenceFile.file
                    removeFile(type)
                    handleFileSelect(type, file)
                  }}
                  className="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  {t('submission.retry')}
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={() => removeFile(type)}
                  className="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  {t('submission.changeFile')}
                </button>
              </div>
            )}

            {!evidenceFile.uploading && !evidenceFile.uploaded && !evidenceFile.error && (
              <button
                onClick={() => removeFile(type)}
                className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}

            {evidenceFile.uploaded && renderVerificationBadge(evidenceFile)}
          </div>
        ) : (
          <label className="block w-full p-6 border-2 border-dashed border-gray-300 rounded-lg text-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors">
            <input
              type="file"
              accept={config?.accept}
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleFileSelect(type, file)
              }}
              className="hidden"
              ref={(el) => {
                if (el) fileInputRefs.current.set(type, el)
              }}
            />
            <svg
              className="w-8 h-8 mx-auto text-gray-400 mb-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            <span className="text-gray-500">{t('submission.selectFile')}</span>
          </label>
        )}
      </div>
    )
  }

  const renderTextInput = (type: EvidenceType, required: boolean) => {
    const config = EVIDENCE_TYPE_CONFIG[type]
    const textValue = textResponses.get(type) || ''
    const label = t(`tasks.evidenceTypes.${type}`, type)

    return (
      <div key={type} className="p-4 border border-gray-200 rounded-lg">
        <label className="block">
          <span className="flex items-center gap-2 font-medium text-gray-700 mb-2">
            <span>{config?.icon}</span>
            <span>{label}</span>
            {required && <span className="text-red-500">*</span>}
          </span>
          <textarea
            value={textValue}
            onChange={(e) => handleTextChange(type, e.target.value)}
            placeholder={type === 'measurement' ? t('submission.measurementPlaceholder') : t('submission.textPlaceholder')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            rows={3}
          />
        </label>
      </div>
    )
  }

  // Check if any file is still uploading or verifying
  const anyFilePending = [...files.values()].some((f) => f.uploading || f.verifying)
  // Camera types: check if required camera types are missing from uploaded evidence
  // (each uploaded item via onEvidenceAdded populates cameraEvidence)
  const uploadedCameraTypes = new Set(cameraEvidence.map((e) => e.evidenceType))
  const anyCameraPending = cameraRequired.some((t) => !uploadedCameraTypes.has(t))
  const anyPending = anyFilePending || anyCameraPending

  // Parse task location for geofence check
  const geofenceLocation = (() => {
    if (task.location) return { lat: task.location.lat, lng: task.location.lng }
    // Fallback: try location_hint "lat,lng" format
    if (task.location_hint) {
      const match = task.location_hint.match(/(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)/)
      if (match) return { lat: parseFloat(match[1]), lng: parseFloat(match[2]) }
    }
    return null
  })()

  const geofenceRadius = task.location_radius_km ?? 0.5

  // Post-submission polling view
  if (submitted) {
    return (
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 text-center space-y-4">
          {pollingStatus ? (
            <>
              <div className="w-16 h-16 mx-auto rounded-full bg-green-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">
                {t('submission.statusUpdated', 'Status Updated')}
              </h3>
              <p className="text-sm text-gray-600">
                {t('submission.newStatus', 'Task status: {{status}}', { status: pollingStatus })}
              </p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 mx-auto rounded-full bg-green-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">
                {t('submission.submitted', 'Evidence Submitted')}
              </h3>
              <p className="text-sm text-gray-600">
                {t('submission.waitingReview', 'Waiting for review. Checking status automatically...')}
              </p>
              <div className="flex items-center justify-center gap-1.5 text-xs text-gray-400">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                {t('submission.polling', 'Auto-refreshing every 5s')}
              </div>
            </>
          )}
        </div>

        {/* Verification panel — always show when available */}
        {verificationDetails && (
          <div className="border-t border-gray-200 p-4 space-y-3">
            <EvidenceVerificationPanel details={verificationDetails} onRefresh={refreshVerificationDetails} />
            {(() => {
              // Prefer the dedicated ai_verification_result (populated by Phase B)
              if (aiVerificationResult) {
                return <AIAnalysisDetails result={aiVerificationResult as AIAnalysisResult} />
              }
              // Fallback: check auto_check_details.checks for ai_semantic entry
              const checks = (verificationDetails as { checks?: Array<{ name: string }> }).checks
              const aiCheck = Array.isArray(checks) ? checks.find((c) => c.name === 'ai_semantic') : undefined
              return aiCheck ? <AIAnalysisDetails result={aiCheck as unknown as AIAnalysisResult} /> : null
            })()}
          </div>
        )}

        {/* Awaiting agent review — show after verification panel, hide once status updated */}
        {verificationDetails && !pollingStatus && (
          <div className="border-t border-gray-200 p-4">
            <div className="flex items-center gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex-shrink-0">
                <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-amber-800">
                  {t('submission.awaitingReview', 'Awaiting agent review')}
                </p>
                <p className="text-xs text-amber-600 mt-0.5">
                  {t('submission.awaitingReviewDesc', 'Your evidence has been submitted and is pending approval by the task publisher.')}
                </p>
              </div>
              <div className="flex-shrink-0 ml-auto">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse inline-block" />
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">{t('submission.title')}</h2>
        <p className="text-sm text-gray-500 mt-1">{task.title}</p>
      </div>

      <div className="p-4 space-y-4">
        {/* Geofence alert — only show if NOT using EvidenceUpload (which has its own GPS) */}
        {geofenceLocation && !hasCameraTypes && (
          <GeofenceAlert
            taskLocation={geofenceLocation}
            radiusKm={geofenceRadius}
            onStatusChange={(inside) => setIsOutsideGeofence(!inside)}
          />
        )}

        {/* Category-specific guidance */}
        {CATEGORY_GUIDANCE[category] && (
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-700">{CATEGORY_GUIDANCE[category]}</p>
          </div>
        )}

        {/* Escrow not funded warning */}
        {!escrowReady && (
          <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-3">
            <p className="text-yellow-400 text-sm">
              Escrow not confirmed on-chain (status: {task.escrow_status}).
              You cannot submit evidence until the agent funds this task.
            </p>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <p className="text-sm text-red-700">{error}</p>
                <button
                  onClick={() => setError(null)}
                  className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
                >
                  {t('submission.closeRetry')}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Camera evidence (photo, photo_geo) — uses full EvidenceUpload with camera + GPS */}
        {hasCameraTypes && (
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              {t('submission.photoEvidence', 'Photo Evidence')}
            </h3>
            <EvidenceUpload
              taskId={task.id}
              executorId={executor.id}
              requiredTypes={cameraRequired}
              optionalTypes={cameraOptional}
              onComplete={handleCameraComplete}
              onEvidenceAdded={handleCameraEvidenceAdded}
              onError={(err) => setError(err)}
              requireCamera={false}
              requireGps={cameraRequired.includes('photo_geo' as EvidenceType)}
              taskLocation={taskLocation}
              className="border border-gray-200 rounded-lg p-4"
            />
          </section>
        )}

        {/* File-based evidence (video, document, receipt, etc.) */}
        {(fileRequired.length > 0 || fileOptional.length > 0) && (
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              {t('submission.fileEvidence', 'File Evidence')}
            </h3>
            <div className="space-y-3">
              {fileRequired.map((type) => renderFileInput(type, true))}
              {fileOptional.map((type) => renderFileInput(type, false))}
            </div>
          </section>
        )}

        {/* Text responses (text_response, measurement) */}
        {(textRequired.length > 0 || textOptional.length > 0) && (
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              {t('submission.textEvidence', 'Text Responses')}
            </h3>
            <div className="space-y-3">
              {textRequired.map((type) => renderTextInput(type, true))}
              {textOptional.map((type) => renderTextInput(type, false))}
            </div>
          </section>
        )}
      </div>

      <div className="p-4 bg-gray-50 border-t border-gray-200 flex gap-3">
        <button
          onClick={onCancel}
          disabled={submitting}
          className="flex-1 py-2 px-4 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
        >
          {t('common.cancel')}
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting || anyPending}
          className="flex-1 py-2 px-4 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? t('submission.submitting') : t('submission.submitButton')}
        </button>
      </div>
    </div>
  )
}

function isTextType(type: EvidenceType): boolean {
  return (
    type === 'text_response' ||
    type === 'measurement' ||
    type === 'json_response' ||
    type === 'code_output' ||
    type === 'url_reference' ||
    type === 'text_report'
  )
}
