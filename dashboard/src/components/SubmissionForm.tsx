// Execution Market: Evidence Submission Form
import { useState, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'
import type { Task, EvidenceType, Executor } from '../types/database'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY
const API_URL = import.meta.env.VITE_API_URL || 'https://api.execution.market'

interface SubmissionFormProps {
  task: Task
  executor: Executor
  onSubmit?: () => void
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
  progress: number // 0-100
  error?: string
  verifying?: boolean
  verification?: VerificationResult
}

const EVIDENCE_TYPE_CONFIG: Record<string, { accept: string; icon: string }> = {
  photo: { accept: 'image/*', icon: '📷' },
  photo_geo: { accept: 'image/*', icon: '📍' },
  video: { accept: 'video/*', icon: '🎥' },
  document: { accept: '.pdf,.doc,.docx', icon: '📄' },
  receipt: { accept: 'image/*,.pdf', icon: '🧾' },
  signature: { accept: 'image/*', icon: '✍️' },
  notarized: { accept: '.pdf,image/*', icon: '📋' },
  timestamp_proof: { accept: 'image/*,.pdf', icon: '⏰' },
  screenshot: { accept: 'image/*', icon: '🖥️' },
  text_response: { accept: '', icon: '📝' },
  measurement: { accept: '', icon: '📏' },
}

const isImageType = (fileType: string) => fileType.startsWith('image/')

export function SubmissionForm({
  task,
  executor,
  onSubmit,
  onCancel,
}: SubmissionFormProps) {
  const { t } = useTranslation()
  const [files, setFiles] = useState<Map<EvidenceType, EvidenceFile>>(new Map())
  const [textResponses, setTextResponses] = useState<Map<string, string>>(new Map())
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRefs = useRef<Map<string, HTMLInputElement>>(new Map())

  const allRequired = task.evidence_schema.required
  const allOptional = task.evidence_schema.optional || []

  const isTextType = (type: EvidenceType) =>
    type === 'text_response' || type === 'measurement'

  const uploadFile = async (evidenceFile: EvidenceFile): Promise<string> => {
    const path = `${executor.id}/${task.id}/${evidenceFile.type}_${Date.now()}`
    const { data: { session } } = await supabase.auth.getSession()
    const authToken = session?.access_token || SUPABASE_KEY

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      const uploadUrl = `${SUPABASE_URL}/storage/v1/object/evidence/${path}`

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100)
          setFiles((prev) => {
            const next = new Map(prev)
            const file = next.get(evidenceFile.type)
            if (file) {
              next.set(evidenceFile.type, { ...file, progress })
            }
            return next
          })
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(path)
        } else {
          reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`))
        }
      })

      xhr.addEventListener('error', () => reject(new Error('Network error during upload')))
      xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')))

      xhr.open('POST', uploadUrl)
      xhr.setRequestHeader('apikey', SUPABASE_KEY)
      xhr.setRequestHeader('Authorization', `Bearer ${authToken}`)
      xhr.setRequestHeader('Content-Type', evidenceFile.file.type || 'application/octet-stream')
      xhr.setRequestHeader('x-upsert', 'true')
      xhr.send(evidenceFile.file)
    })
  }

  const verifyEvidence = async (path: string, evidenceType: EvidenceType) => {
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
  }

  // Upload immediately when file is selected, then verify
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
        const path = await uploadFile(evidenceFile)

        setFiles((prev) => {
          const next = new Map(prev)
          next.set(type, { ...evidenceFile, uploading: false, uploaded: true, uploadedPath: path, progress: 100 })
          return next
        })

        // Run AI verification for image types
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
    [executor.id, task.id, t]
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
    // Reset the input so the same file can be re-selected
    const input = fileInputRefs.current.get(type)
    if (input) input.value = ''
  }, [])

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)

    try {
      // Validate required evidence
      const missingRequired = allRequired.filter((evType) => {
        if (isTextType(evType)) {
          return !textResponses.get(evType)?.trim()
        }
        return !files.has(evType)
      })

      if (missingRequired.length > 0) {
        const items = missingRequired
          .map((evType) => t(`tasks.evidenceTypes.${evType}`, evType))
          .join(', ')
        throw new Error(t('submission.missingEvidence', { items }))
      }

      // Check all files are uploaded (they should be, since we upload on select)
      const notUploaded = [...files.values()].filter(f => !f.uploaded)
      if (notUploaded.length > 0) {
        throw new Error(t('submission.uploadError'))
      }

      // Build evidence data from already-uploaded files
      const evidenceData: Record<string, unknown> = {}
      const uploadedPaths: string[] = []

      for (const [type, evidenceFile] of files) {
        if (evidenceFile.uploadedPath) {
          uploadedPaths.push(evidenceFile.uploadedPath)
          evidenceData[type] = {
            file: evidenceFile.uploadedPath,
            filename: evidenceFile.file.name,
            size: evidenceFile.file.size,
            type: evidenceFile.file.type,
          }
          // Include verification result if available
          if (evidenceFile.verification) {
            (evidenceData[type] as Record<string, unknown>).ai_verification = {
              verified: evidenceFile.verification.verified,
              confidence: evidenceFile.verification.confidence,
              decision: evidenceFile.verification.decision,
            }
          }
        }
      }

      // Add text responses
      for (const [type, value] of textResponses) {
        if (value.trim()) {
          evidenceData[type] = { value: value.trim() }
        }
      }

      // Get fresh session
      const { data: { session: currentSession } } = await supabase.auth.getSession()

      const headers: Record<string, string> = {
        apikey: SUPABASE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'return=representation',
      }

      if (currentSession?.access_token) {
        headers['Authorization'] = `Bearer ${currentSession.access_token}`
      }

      // Create submission
      const submitResponse = await fetch(`${SUPABASE_URL}/rest/v1/submissions`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          task_id: task.id,
          executor_id: executor.id,
          evidence: evidenceData,
          evidence_files: uploadedPaths,
          submitted_at: new Date().toISOString(),
        }),
      })

      if (!submitResponse.ok) {
        const text = await submitResponse.text()
        throw new Error(text || `Submission failed: ${submitResponse.status}`)
      }

      // Update task status
      const statusResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/tasks?id=eq.${task.id}`,
        {
          method: 'PATCH',
          headers: { ...headers, Prefer: 'return=minimal' },
          body: JSON.stringify({ status: 'submitted' }),
        }
      )

      if (!statusResponse.ok) {
        console.warn('Could not update task status:', statusResponse.status)
      }

      onSubmit?.()
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

    // "needs_human" = AI unavailable, don't show warning
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

  const renderEvidenceInput = (type: EvidenceType, required: boolean) => {
    const config = EVIDENCE_TYPE_CONFIG[type]
    const evidenceFile = files.get(type)
    const textValue = textResponses.get(type) || ''
    const label = t(`tasks.evidenceTypes.${type}`, type)

    if (isTextType(type)) {
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
                    // Re-upload the same file
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

            {/* AI Verification result */}
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

  // Check if any file is still uploading or verifying
  const anyPending = [...files.values()].some(f => f.uploading || f.verifying)

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">{t('submission.title')}</h2>
        <p className="text-sm text-gray-500 mt-1">{task.title}</p>
      </div>

      <div className="p-4 space-y-4">
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

        {/* Required evidence */}
        {allRequired.length > 0 && (
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              {t('submission.requiredEvidence')}
            </h3>
            <div className="space-y-3">
              {allRequired.map((type) => renderEvidenceInput(type, true))}
            </div>
          </section>
        )}

        {/* Optional evidence */}
        {allOptional.length > 0 && (
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              {t('submission.optionalEvidence')}
            </h3>
            <div className="space-y-3">
              {allOptional.map((type) => renderEvidenceInput(type, false))}
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
