/**
 * SubmissionReview - Review worker submissions for AI agents
 *
 * Features:
 * - Task details display
 * - Worker info and reputation
 * - Evidence viewer (photos, GPS data)
 * - Verification status badges
 * - Approve/Reject buttons with feedback
 * - Rating input
 */

import { useState, useCallback, useMemo } from 'react'
import { TxHashLink } from '../../components/TxHashLink'
import { PaymentStatusBadge } from '../../components/PaymentStatusBadge'
import type { Task, Submission, Executor, EvidenceType } from '../../types/database'

// ============================================================================
// Types
// ============================================================================

interface SubmissionReviewProps {
  submission: SubmissionWithContext
  onBack?: () => void
  onApprove?: (submissionId: string, rating: number, feedback: string) => Promise<void>
  onReject?: (submissionId: string, reason: string) => Promise<void>
  onDispute?: (submissionId: string, reason: string) => Promise<void>
}

interface SubmissionWithContext extends Submission {
  task?: Task
  executor?: Executor
}

interface EvidenceFile {
  type: EvidenceType
  url: string
  filename: string
  metadata?: {
    gps?: {
      latitude: number
      longitude: number
      accuracy?: number
    }
    timestamp?: string
    deviceInfo?: string
  }
}

type ReviewAction = 'approve' | 'reject' | 'dispute'

// ============================================================================
// Constants
// ============================================================================

const EVIDENCE_TYPE_LABELS: Record<EvidenceType, string> = {
  photo: 'Foto',
  photo_geo: 'Foto con GPS',
  video: 'Video',
  document: 'Documento',
  receipt: 'Recibo',
  signature: 'Firma',
  notarized: 'Notarizado',
  timestamp_proof: 'Prueba de Tiempo',
  text_response: 'Respuesta',
  measurement: 'Medicion',
  screenshot: 'Screenshot',
}

const RATING_LABELS: Record<number, string> = {
  1: 'Muy malo',
  2: 'Malo',
  3: 'Regular',
  4: 'Bueno',
  5: 'Excelente',
}

const REJECTION_REASONS = [
  'Evidencia incompleta',
  'Ubicacion incorrecta',
  'Calidad insuficiente',
  'No coincide con instrucciones',
  'Evidencia ilegible',
  'Tiempo de captura invalido',
  'Otro',
]

// ============================================================================
// Helper Functions
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('es-MX', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'Ahora'
  if (diffMins < 60) return `Hace ${diffMins} min`
  if (diffHours < 24) return `Hace ${diffHours}h`
  if (diffDays === 1) return 'Ayer'
  return `Hace ${diffDays} dias`
}

function getReputationTier(score: number): { label: string; color: string; bgColor: string } {
  if (score >= 90) return { label: 'Experto', color: 'text-purple-700', bgColor: 'bg-purple-100' }
  if (score >= 75) return { label: 'Confiable', color: 'text-blue-700', bgColor: 'bg-blue-100' }
  if (score >= 60) return { label: 'Fiable', color: 'text-green-700', bgColor: 'bg-green-100' }
  if (score >= 40) return { label: 'Estandar', color: 'text-gray-700', bgColor: 'bg-gray-100' }
  return { label: 'Nuevo', color: 'text-amber-700', bgColor: 'bg-amber-100' }
}

// ============================================================================
// Sub-Components
// ============================================================================

function VerificationBadge({
  passed,
  label,
  details,
}: {
  passed: boolean | null
  label: string
  details?: string
}) {
  if (passed === null) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg">
        <div className="w-2 h-2 bg-gray-400 rounded-full" />
        <span className="text-sm text-gray-600">{label}: Pendiente</span>
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${passed ? 'bg-green-100' : 'bg-red-100'}`}>
      {passed ? (
        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
      <div>
        <span className={`text-sm font-medium ${passed ? 'text-green-700' : 'text-red-700'}`}>
          {label}: {passed ? 'Verificado' : 'Fallido'}
        </span>
        {details && (
          <p className={`text-xs ${passed ? 'text-green-600' : 'text-red-600'}`}>{details}</p>
        )}
      </div>
    </div>
  )
}

function WorkerInfoCard({ executor }: { executor: Executor }) {
  const tier = getReputationTier(executor.reputation_score)

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Informacion del Trabajador</h3>

      <div className="flex items-center gap-3 mb-4">
        {/* Avatar */}
        <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
          {executor.avatar_url ? (
            <img
              src={executor.avatar_url}
              alt={executor.display_name || 'Trabajador'}
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            <span className="text-blue-700 font-semibold text-lg">
              {(executor.display_name || 'T')[0].toUpperCase()}
            </span>
          )}
        </div>

        {/* Name and tier */}
        <div>
          <p className="font-medium text-gray-900">{executor.display_name || 'Trabajador Anonimo'}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${tier.bgColor} ${tier.color}`}>
              {tier.label}
            </span>
            {executor.location_city && (
              <span className="text-xs text-gray-500">{executor.location_city}</span>
            )}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="text-center p-2 bg-gray-50 rounded-lg">
          <p className="text-xl font-bold text-gray-900">{executor.reputation_score}</p>
          <p className="text-xs text-gray-500">Reputacion</p>
        </div>
        <div className="text-center p-2 bg-gray-50 rounded-lg">
          <p className="text-xl font-bold text-gray-900">{executor.tasks_completed}</p>
          <p className="text-xs text-gray-500">Completadas</p>
        </div>
        <div className="text-center p-2 bg-gray-50 rounded-lg">
          <p className="text-xl font-bold text-gray-900">
            {executor.avg_rating?.toFixed(1) || '-'}
          </p>
          <p className="text-xs text-gray-500">Rating</p>
        </div>
      </div>

      {/* Disputes */}
      {executor.tasks_disputed > 0 && (
        <div className="mt-3 p-2 bg-amber-50 rounded-lg">
          <p className="text-xs text-amber-700">
            {executor.tasks_disputed} disputa{executor.tasks_disputed !== 1 ? 's' : ''} previas
          </p>
        </div>
      )}

      {/* Wallet */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <p className="text-xs text-gray-400">Wallet</p>
        <p className="text-sm text-gray-600 font-mono truncate">{executor.wallet_address}</p>
      </div>
    </div>
  )
}

function EvidenceViewer({ evidence, evidenceFiles, schema }: { evidence: Record<string, unknown>; evidenceFiles: string[]; schema: { required: EvidenceType[]; optional?: EvidenceType[] } }) {
  const [selectedEvidence, setSelectedEvidence] = useState<string | null>(null)

  // Build evidence files from real submission data
  const files: EvidenceFile[] = useMemo(() => {
    const result: EvidenceFile[] = []
    const allTypes = [...schema.required, ...(schema.optional || [])]

    // Map evidence_files URLs to evidence types
    evidenceFiles.forEach((url, index) => {
      const type = allTypes[index] || 'photo'
      const filename = url.split('/').pop() || `evidence_${index}`
      const meta = evidence as Record<string, Record<string, unknown>>
      const typeMeta = meta?.[type] as Record<string, unknown> | undefined

      result.push({
        type: type as EvidenceType,
        url,
        filename,
        metadata: typeMeta?.gps ? {
          gps: typeMeta.gps as EvidenceFile['metadata'] extends undefined ? never : NonNullable<EvidenceFile['metadata']>['gps'],
          timestamp: typeMeta.timestamp as string | undefined,
          deviceInfo: typeMeta.deviceInfo as string | undefined,
        } : undefined,
      })
    })

    return result
  }, [evidence, evidenceFiles, schema])

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">Evidencia Enviada</h3>

      {/* Evidence grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {files.map((file, index) => (
          <button
            key={index}
            onClick={() => setSelectedEvidence(file.url)}
            className="relative aspect-square rounded-lg overflow-hidden bg-gray-100 hover:ring-2 hover:ring-blue-500 transition-all group"
          >
            <img
              src={file.url}
              alt={file.filename}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="absolute bottom-0 left-0 right-0 p-2">
              <span className="px-2 py-0.5 bg-black/50 text-white text-xs rounded-full">
                {EVIDENCE_TYPE_LABELS[file.type]}
              </span>
            </div>
            {file.metadata?.gps && (
              <div className="absolute top-2 right-2">
                <span className="px-2 py-0.5 bg-green-500 text-white text-xs rounded-full flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                  </svg>
                  GPS
                </span>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Evidence details */}
      {files.map((file, index) => (
        <div key={index} className="p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-900">
              {EVIDENCE_TYPE_LABELS[file.type]}
            </span>
            <span className="text-xs text-gray-500">{file.filename}</span>
          </div>
          {file.metadata && (
            <div className="space-y-1 text-xs text-gray-600">
              {file.metadata.gps && (
                <p>
                  <span className="font-medium">GPS:</span>{' '}
                  {file.metadata.gps.latitude.toFixed(6)}, {file.metadata.gps.longitude.toFixed(6)}
                  {file.metadata.gps.accuracy && ` (+/- ${file.metadata.gps.accuracy.toFixed(0)}m)`}
                </p>
              )}
              {file.metadata.timestamp && (
                <p>
                  <span className="font-medium">Capturado:</span> {formatDate(file.metadata.timestamp)}
                </p>
              )}
              {file.metadata.deviceInfo && (
                <p>
                  <span className="font-medium">Dispositivo:</span> {file.metadata.deviceInfo}
                </p>
              )}
            </div>
          )}
        </div>
      ))}

      {/* Fullscreen viewer modal */}
      {selectedEvidence && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedEvidence(null)}
        >
          <button
            className="absolute top-4 right-4 p-2 bg-white/20 rounded-full text-white hover:bg-white/30 transition-colors"
            onClick={() => setSelectedEvidence(null)}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <img
            src={selectedEvidence}
            alt="Evidence fullscreen"
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}

function RatingInput({
  value,
  onChange,
}: {
  value: number
  onChange: (rating: number) => void
}) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Calificar al trabajador
      </label>
      <div className="flex items-center gap-2">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className="p-1 transition-transform hover:scale-110"
          >
            <svg
              className={`w-8 h-8 ${star <= value ? 'text-amber-400' : 'text-gray-300'}`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          </button>
        ))}
        <span className="text-sm text-gray-600 ml-2">
          {value > 0 ? RATING_LABELS[value] : 'Sin calificar'}
        </span>
      </div>
    </div>
  )
}

function ActionModal({
  action,
  onClose,
  onConfirm,
  isLoading,
}: {
  action: ReviewAction
  onClose: () => void
  onConfirm: (data: { rating?: number; feedback: string }) => void
  isLoading: boolean
}) {
  const [rating, setRating] = useState(5)
  const [feedback, setFeedback] = useState('')
  const [selectedReason, setSelectedReason] = useState('')

  const config = {
    approve: {
      title: 'Aprobar Entrega',
      description: 'Al aprobar, el pago se liberara automaticamente al trabajador.',
      buttonText: 'Aprobar y Pagar',
      buttonColor: 'bg-green-600 hover:bg-green-700',
      showRating: true,
    },
    reject: {
      title: 'Rechazar Entrega',
      description: 'El trabajador podra volver a enviar evidencia o disputar la decision.',
      buttonText: 'Rechazar',
      buttonColor: 'bg-red-600 hover:bg-red-700',
      showRating: false,
    },
    dispute: {
      title: 'Abrir Disputa',
      description: 'Se iniciara un proceso de arbitraje para resolver el desacuerdo.',
      buttonText: 'Abrir Disputa',
      buttonColor: 'bg-amber-600 hover:bg-amber-700',
      showRating: false,
    },
  }[action]

  const handleSubmit = () => {
    onConfirm({
      rating: action === 'approve' ? rating : undefined,
      feedback: action === 'reject' && selectedReason !== 'Otro' ? selectedReason : feedback,
    })
  }

  const canSubmit = action === 'approve' ? rating > 0 : feedback.trim().length > 0 || selectedReason !== ''

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{config.title}</h3>
        <p className="text-sm text-gray-500 mb-4">{config.description}</p>

        <div className="space-y-4">
          {/* Rating (only for approve) */}
          {config.showRating && (
            <RatingInput value={rating} onChange={setRating} />
          )}

          {/* Rejection reasons */}
          {action === 'reject' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Razon del rechazo
              </label>
              <div className="grid grid-cols-2 gap-2">
                {REJECTION_REASONS.map((reason) => (
                  <button
                    key={reason}
                    type="button"
                    onClick={() => setSelectedReason(reason)}
                    className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                      selectedReason === reason
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 hover:border-gray-300 text-gray-700'
                    }`}
                  >
                    {reason}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Feedback textarea */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {action === 'approve' ? 'Comentario (opcional)' : 'Explicacion'}
              {action !== 'approve' && <span className="text-red-500"> *</span>}
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={
                action === 'approve'
                  ? 'Agrega un comentario para el trabajador...'
                  : 'Explica el motivo...'
              }
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 mt-6">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 px-4 py-2.5 text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit || isLoading}
            className={`flex-1 px-4 py-2.5 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2 ${config.buttonColor}`}
          >
            {isLoading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Procesando...
              </>
            ) : (
              config.buttonText
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function SubmissionReview({
  submission,
  onBack,
  onApprove,
  onReject,
  onDispute,
}: SubmissionReviewProps) {
  const [activeAction, setActiveAction] = useState<ReviewAction | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const task = submission.task
  const executor = submission.executor

  // Auto-check details
  const autoCheckDetails = submission.auto_check_details as {
    gps_verified?: boolean
    timestamp_valid?: boolean
    evidence_complete?: boolean
    reason?: string
  } | null

  const handleActionConfirm = useCallback(async (data: { rating?: number; feedback: string }) => {
    if (!activeAction) return

    setIsProcessing(true)

    try {
      switch (activeAction) {
        case 'approve':
          await onApprove?.(submission.id, data.rating || 5, data.feedback)
          break
        case 'reject':
          await onReject?.(submission.id, data.feedback)
          break
        case 'dispute':
          await onDispute?.(submission.id, data.feedback)
          break
      }
      setActiveAction(null)
    } catch (error) {
      console.error('Action failed:', error)
    } finally {
      setIsProcessing(false)
    }
  }, [activeAction, submission.id, onApprove, onReject, onDispute])

  if (!task || !executor) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Informacion de la entrega no disponible</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          <div>
            <h1 className="text-xl font-bold text-gray-900">Revisar Entrega</h1>
            <p className="text-sm text-gray-500">
              Enviada {formatRelativeTime(submission.submitted_at)}
            </p>
          </div>
        </div>

        {/* Payment info */}
        <div className="text-right">
          <p className="text-2xl font-bold text-green-600">{formatCurrency(task.bounty_usd)}</p>
          <p className="text-xs text-gray-500">USDC en escrow</p>
        </div>
      </div>

      {/* Task Summary */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Tarea</h3>
        <h4 className="font-medium text-gray-900">{task.title}</h4>
        <p className="text-sm text-gray-600 mt-1">{task.instructions}</p>
        {task.location_hint && (
          <div className="flex items-center gap-1 mt-2 text-sm text-gray-500">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
            {task.location_hint}
          </div>
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Evidence and verification */}
        <div className="lg:col-span-2 space-y-6">
          {/* Verification Status */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Verificacion Automatica</h3>

            <div className="flex flex-wrap gap-2">
              <VerificationBadge
                passed={submission.auto_check_passed}
                label="General"
                details={submission.auto_check_passed ? 'Todas las verificaciones pasaron' : autoCheckDetails?.reason}
              />
              {autoCheckDetails?.gps_verified !== undefined && (
                <VerificationBadge
                  passed={autoCheckDetails.gps_verified}
                  label="GPS"
                  details={autoCheckDetails.gps_verified ? 'Ubicacion verificada' : 'Fuera de rango'}
                />
              )}
              {autoCheckDetails?.timestamp_valid !== undefined && (
                <VerificationBadge
                  passed={autoCheckDetails.timestamp_valid}
                  label="Timestamp"
                  details={autoCheckDetails.timestamp_valid ? 'Tiempo valido' : 'Timestamp invalido'}
                />
              )}
              {autoCheckDetails?.evidence_complete !== undefined && (
                <VerificationBadge
                  passed={autoCheckDetails.evidence_complete}
                  label="Evidencia"
                  details={autoCheckDetails.evidence_complete ? 'Completa' : 'Incompleta'}
                />
              )}
            </div>

            {!submission.auto_check_passed && autoCheckDetails?.reason && (
              <div className="mt-3 p-3 bg-red-50 rounded-lg">
                <p className="text-sm text-red-700">
                  <span className="font-medium">Nota:</span> {autoCheckDetails.reason}
                </p>
              </div>
            )}
          </div>

          {/* Evidence Viewer */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <EvidenceViewer
              evidence={submission.evidence}
              evidenceFiles={submission.evidence_files}
              schema={task.evidence_schema}
            />
          </div>

          {/* Submission metadata */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Detalles de la Entrega</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500">ID de Entrega</p>
                <p className="font-mono text-gray-900">{submission.id.slice(0, 12)}...</p>
              </div>
              <div>
                <p className="text-gray-500">Fecha de Envio</p>
                <p className="text-gray-900">{formatDate(submission.submitted_at)}</p>
              </div>
              {submission.evidence_ipfs_cid && (
                <div>
                  <p className="text-gray-500">IPFS CID</p>
                  <p className="font-mono text-gray-900">{submission.evidence_ipfs_cid.slice(0, 12)}...</p>
                </div>
              )}
              {submission.evidence_hash && (
                <div>
                  <p className="text-gray-500">Hash de Evidencia</p>
                  <p className="font-mono text-gray-900">{submission.evidence_hash.slice(0, 12)}...</p>
                </div>
              )}
              {submission.agent_verdict && (
                <div>
                  <p className="text-gray-500">Veredicto</p>
                  <PaymentStatusBadge
                    status={submission.agent_verdict === 'accepted' ? 'released' : submission.agent_verdict === 'rejected' ? 'cancelled' : submission.agent_verdict}
                    txHash={submission.payment_tx}
                  />
                </div>
              )}
              {submission.payment_tx && (
                <div>
                  <p className="text-gray-500">Transaccion de Pago</p>
                  <TxHashLink txHash={submission.payment_tx} />
                </div>
              )}
              {submission.paid_at && (
                <div>
                  <p className="text-gray-500">Fecha de Pago</p>
                  <p className="text-gray-900">{formatDate(submission.paid_at)}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Worker info and actions */}
        <div className="space-y-6">
          {/* Worker Info */}
          <WorkerInfoCard executor={executor} />

          {/* Action Buttons */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Tomar Decision</h3>

            <div className="space-y-3">
              <button
                onClick={() => setActiveAction('approve')}
                className="w-full py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Aprobar y Pagar
              </button>

              <button
                onClick={() => setActiveAction('reject')}
                className="w-full py-3 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Rechazar
              </button>

              <button
                onClick={() => setActiveAction('dispute')}
                className="w-full py-2.5 border border-amber-500 text-amber-600 font-medium rounded-lg hover:bg-amber-50 transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Abrir Disputa
              </button>
            </div>

            <p className="text-xs text-gray-500 mt-3 text-center">
              Al aprobar, {formatCurrency(task.bounty_usd)} se transferiran automaticamente.
            </p>
          </div>

          {/* Help */}
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex gap-3">
              <svg className="w-5 h-5 text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm text-blue-900">
                <p className="font-medium">Consejos para revisar:</p>
                <ul className="mt-1 space-y-1 text-blue-700">
                  <li>- Verifica que la ubicacion GPS coincida</li>
                  <li>- Revisa la calidad de las fotos</li>
                  <li>- Confirma que las instrucciones se cumplieron</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Modal */}
      {activeAction && (
        <ActionModal
          action={activeAction}
          onClose={() => setActiveAction(null)}
          onConfirm={handleActionConfirm}
          isLoading={isProcessing}
        />
      )}
    </div>
  )
}

export default SubmissionReview
