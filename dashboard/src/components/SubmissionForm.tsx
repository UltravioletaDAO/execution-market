// Chamba: Evidence Submission Form
import { useState, useCallback, useRef } from 'react'
import { supabase } from '../lib/supabase'
import type { Task, EvidenceType, Executor } from '../types/database'

interface SubmissionFormProps {
  task: Task
  executor: Executor
  onSubmit?: () => void
  onCancel?: () => void
}

interface EvidenceFile {
  type: EvidenceType
  file: File
  preview?: string
  uploading: boolean
  uploaded: boolean
  error?: string
}

const EVIDENCE_TYPE_LABELS: Record<string, { label: string; accept: string; icon: string }> = {
  photo: { label: 'Foto', accept: 'image/*', icon: '📷' },
  photo_geo: { label: 'Foto con ubicacion', accept: 'image/*', icon: '📍' },
  video: { label: 'Video', accept: 'video/*', icon: '🎥' },
  document: { label: 'Documento', accept: '.pdf,.doc,.docx', icon: '📄' },
  receipt: { label: 'Recibo', accept: 'image/*,.pdf', icon: '🧾' },
  signature: { label: 'Firma', accept: 'image/*', icon: '✍️' },
  notarized: { label: 'Notarizado', accept: '.pdf,image/*', icon: '📋' },
  timestamp_proof: { label: 'Prueba de tiempo', accept: 'image/*,.pdf', icon: '⏰' },
  screenshot: { label: 'Captura de pantalla', accept: 'image/*', icon: '🖥️' },
  text_response: { label: 'Respuesta de texto', accept: '', icon: '📝' },
  measurement: { label: 'Medicion', accept: '', icon: '📏' },
}

export function SubmissionForm({
  task,
  executor,
  onSubmit,
  onCancel,
}: SubmissionFormProps) {
  const [files, setFiles] = useState<Map<EvidenceType, EvidenceFile>>(new Map())
  const [textResponses, setTextResponses] = useState<Map<string, string>>(new Map())
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRefs = useRef<Map<string, HTMLInputElement>>(new Map())

  const allRequired = task.evidence_schema.required
  const allOptional = task.evidence_schema.optional || []

  const isTextType = (type: EvidenceType) =>
    type === 'text_response' || type === 'measurement'

  const handleFileSelect = useCallback(
    (type: EvidenceType, file: File) => {
      // Create preview for images
      let preview: string | undefined
      if (file.type.startsWith('image/')) {
        preview = URL.createObjectURL(file)
      }

      setFiles((prev) => {
        const next = new Map(prev)
        next.set(type, {
          type,
          file,
          preview,
          uploading: false,
          uploaded: false,
        })
        return next
      })
    },
    []
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
  }, [])

  const uploadFile = async (evidenceFile: EvidenceFile): Promise<string> => {
    const path = `${executor.user_id}/${task.id}/${evidenceFile.type}_${Date.now()}`
    const { error: uploadError } = await supabase.storage
      .from('evidence')
      .upload(path, evidenceFile.file)

    if (uploadError) throw uploadError
    return path
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)

    try {
      // Validate required evidence
      const missingRequired = allRequired.filter((type) => {
        if (isTextType(type)) {
          return !textResponses.get(type)?.trim()
        }
        return !files.has(type)
      })

      if (missingRequired.length > 0) {
        throw new Error(
          `Falta evidencia requerida: ${missingRequired
            .map((t) => EVIDENCE_TYPE_LABELS[t]?.label || t)
            .join(', ')}`
        )
      }

      // Upload files
      const evidenceData: Record<string, unknown> = {}
      const uploadedPaths: string[] = []

      for (const [type, evidenceFile] of files) {
        setFiles((prev) => {
          const next = new Map(prev)
          const file = next.get(type)
          if (file) {
            next.set(type, { ...file, uploading: true })
          }
          return next
        })

        try {
          const path = await uploadFile(evidenceFile)
          uploadedPaths.push(path)
          evidenceData[type] = {
            file: path,
            filename: evidenceFile.file.name,
            size: evidenceFile.file.size,
            type: evidenceFile.file.type,
          }

          setFiles((prev) => {
            const next = new Map(prev)
            const file = next.get(type)
            if (file) {
              next.set(type, { ...file, uploading: false, uploaded: true })
            }
            return next
          })
        } catch (err) {
          setFiles((prev) => {
            const next = new Map(prev)
            const file = next.get(type)
            if (file) {
              next.set(type, {
                ...file,
                uploading: false,
                error: 'Error al subir',
              })
            }
            return next
          })
          throw new Error(`Error al subir ${EVIDENCE_TYPE_LABELS[type]?.label || type}`)
        }
      }

      // Add text responses
      for (const [type, value] of textResponses) {
        if (value.trim()) {
          evidenceData[type] = { value: value.trim() }
        }
      }

      // Create submission
      const { error: submissionError } = await supabase.from('submissions').insert({
        task_id: task.id,
        executor_id: executor.id,
        evidence: evidenceData,
        evidence_files: uploadedPaths,
      } as never)

      if (submissionError) throw submissionError

      // Update task status
      const { error: taskError } = await supabase
        .from('tasks')
        .update({ status: 'submitted' as const } as never)
        .eq('id', task.id)

      if (taskError) throw taskError

      onSubmit?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al enviar evidencia')
    } finally {
      setSubmitting(false)
    }
  }

  const renderEvidenceInput = (type: EvidenceType, required: boolean) => {
    const config = EVIDENCE_TYPE_LABELS[type]
    const evidenceFile = files.get(type)
    const textValue = textResponses.get(type) || ''

    if (isTextType(type)) {
      return (
        <div key={type} className="p-4 border border-gray-200 rounded-lg">
          <label className="block">
            <span className="flex items-center gap-2 font-medium text-gray-700 mb-2">
              <span>{config?.icon}</span>
              <span>{config?.label || type}</span>
              {required && <span className="text-red-500">*</span>}
            </span>
            <textarea
              value={textValue}
              onChange={(e) => handleTextChange(type, e.target.value)}
              placeholder={type === 'measurement' ? 'Ej: 2.5 metros' : 'Escribe tu respuesta...'}
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
            <span>{config?.label || type}</span>
            {required && <span className="text-red-500">*</span>}
          </span>
          {evidenceFile?.uploaded && (
            <span className="text-green-600 text-sm">Subido</span>
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
              <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center">
                <div className="text-white">Subiendo...</div>
              </div>
            )}

            {evidenceFile.error && (
              <div className="mt-2 text-sm text-red-600">{evidenceFile.error}</div>
            )}

            {!evidenceFile.uploading && !evidenceFile.uploaded && (
              <button
                onClick={() => removeFile(type)}
                className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
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
            <span className="text-gray-500">Seleccionar archivo</span>
          </label>
        )}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Enviar Evidencia</h2>
        <p className="text-sm text-gray-500 mt-1">{task.title}</p>
      </div>

      <div className="p-4 space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Required evidence */}
        {allRequired.length > 0 && (
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              Evidencia Requerida
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
              Evidencia Opcional
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
          Cancelar
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="flex-1 py-2 px-4 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? 'Enviando...' : 'Enviar Evidencia'}
        </button>
      </div>
    </div>
  )
}
