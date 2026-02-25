/**
 * SubmissionReviewModal: Modal for agents to review, approve, or reject submissions.
 *
 * Shows submission evidence, worker info, and provides actions:
 * - Approve (triggers payment via API)
 * - Reject (with feedback)
 * - Request More Info
 */

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { getSubmission, approveSubmission, rejectSubmission, requestMoreInfo } from '../services/submissions'
import type { SubmissionWithDetails } from '../services/types'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface SubmissionReviewModalProps {
  submissionId: string
  onClose: () => void
  onSuccess?: () => void
}

type ReviewAction = 'idle' | 'approving' | 'rejecting' | 'requesting_info'

// --------------------------------------------------------------------------
// Component
// --------------------------------------------------------------------------

export function SubmissionReviewModal({ submissionId, onClose, onSuccess }: SubmissionReviewModalProps) {
  const { executor } = useAuth()
  const [submission, setSubmission] = useState<SubmissionWithDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [action, setAction] = useState<ReviewAction>('idle')
  const [feedback, setFeedback] = useState('')
  const [approveNotes, setApproveNotes] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [showInfoForm, setShowInfoForm] = useState(false)
  const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Load submission data
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        setError(null)
        const data = await getSubmission(submissionId)
        if (!cancelled) {
          if (!data) {
            setError('Submission not found')
          } else {
            setSubmission(data)
          }
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load submission')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [submissionId])

  const handleApprove = useCallback(async () => {
    if (!executor?.id || !submission) return
    setAction('approving')
    setResult(null)
    try {
      await approveSubmission({
        submissionId: submission.id,
        agentId: executor.id,
        verdict: 'accepted',
        notes: approveNotes || undefined,
      })
      setResult({ type: 'success', message: 'Submission approved. Payment is being processed.' })
      onSuccess?.()
    } catch (err: unknown) {
      setResult({ type: 'error', message: err instanceof Error ? err.message : 'Failed to approve submission' })
    } finally {
      setAction('idle')
    }
  }, [executor?.id, submission, approveNotes, onSuccess])

  const handleReject = useCallback(async () => {
    if (!executor?.id || !submission || !feedback.trim()) return
    setAction('rejecting')
    setResult(null)
    try {
      await rejectSubmission({
        submissionId: submission.id,
        agentId: executor.id,
        feedback: feedback.trim(),
      })
      setResult({ type: 'success', message: 'Submission rejected.' })
      onSuccess?.()
    } catch (err: unknown) {
      setResult({ type: 'error', message: err instanceof Error ? err.message : 'Failed to reject submission' })
    } finally {
      setAction('idle')
    }
  }, [executor?.id, submission, feedback, onSuccess])

  const handleRequestInfo = useCallback(async () => {
    if (!executor?.id || !submission || !feedback.trim()) return
    setAction('requesting_info')
    setResult(null)
    try {
      await requestMoreInfo(submission.id, executor.id, feedback.trim())
      setResult({ type: 'success', message: 'More information requested. Worker will be notified.' })
      onSuccess?.()
    } catch (err: unknown) {
      setResult({ type: 'error', message: err instanceof Error ? err.message : 'Failed to request more info' })
    } finally {
      setAction('idle')
    }
  }, [executor?.id, submission, feedback, onSuccess])

  const isProcessing = action !== 'idle'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-xl z-10">
          <h2 className="text-lg font-semibold text-gray-900">Revisar Entrega</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-4 space-y-5">
          {/* Loading state */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <svg className="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="ml-3 text-gray-500">Cargando entrega...</span>
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {/* Submission content */}
          {submission && !loading && (
            <>
              {/* Task info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Tarea</p>
                    <p className="font-medium text-gray-900">{submission.task?.title || 'Unknown Task'}</p>
                    {submission.task?.bounty_usd && (
                      <p className="text-sm text-emerald-600 mt-1">
                        ${submission.task.bounty_usd.toFixed(2)} USDC
                      </p>
                    )}
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    submission.agent_verdict === 'accepted'
                      ? 'bg-green-100 text-green-700'
                      : submission.agent_verdict === 'disputed'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {submission.agent_verdict || 'Pendiente'}
                  </span>
                </div>
              </div>

              {/* Worker info */}
              {submission.executor && (
                <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                  <div className="w-10 h-10 bg-blue-200 rounded-full flex items-center justify-center text-blue-700 font-bold text-sm">
                    {submission.executor.display_name?.[0]?.toUpperCase() || 'W'}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 text-sm">
                      {submission.executor.display_name || 'Anonymous Worker'}
                    </p>
                    <p className="text-xs text-gray-500">
                      Rep: {submission.executor.reputation_score ?? 0} | {submission.executor.wallet_address?.slice(0, 6)}...{submission.executor.wallet_address?.slice(-4)}
                    </p>
                  </div>
                </div>
              )}

              {/* Evidence */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Evidencia</h3>
                {submission.evidence && typeof submission.evidence === 'object' ? (
                  <div className="space-y-3">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {Object.entries(submission.evidence as Record<string, any>).map(([key, ev]) => (
                      <div key={key} className="border border-gray-200 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-gray-500 uppercase tracking-wide">{key}</p>
                          {ev?.type && (
                            <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                              {ev.type}
                            </span>
                          )}
                        </div>
                        {ev?.fileUrl ? (
                          <div>
                            {ev.mimeType?.startsWith('image/') || ev.fileUrl?.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                              <a href={ev.fileUrl} target="_blank" rel="noopener noreferrer">
                                <img
                                  src={ev.fileUrl}
                                  alt={key}
                                  className="max-w-full max-h-64 rounded-lg object-contain hover:opacity-90 transition-opacity cursor-zoom-in"
                                />
                              </a>
                            ) : ev.mimeType?.startsWith('video/') ? (
                              <video
                                src={ev.fileUrl}
                                controls
                                className="max-w-full max-h-64 rounded-lg"
                              />
                            ) : (
                              <a
                                href={ev.fileUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 text-blue-600 hover:underline text-sm"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                {ev.filename || 'Descargar archivo'}
                              </a>
                            )}
                          </div>
                        ) : ev?.value ? (
                          <p className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 rounded p-2">{ev.value}</p>
                        ) : (
                          <p className="text-sm text-gray-400 italic">
                            {typeof ev === 'string' ? ev : JSON.stringify(ev)}
                          </p>
                        )}
                        {/* Metadata badges */}
                        {ev?.metadata && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {ev.metadata.gps && (
                              <span className="inline-flex items-center gap-1 text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                                GPS: {Number(ev.metadata.gps.latitude || ev.metadata.gps.lat).toFixed(4)}, {Number(ev.metadata.gps.longitude || ev.metadata.gps.lng).toFixed(4)}
                              </span>
                            )}
                            {ev.metadata.captureTimestamp && (
                              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                                {new Date(ev.metadata.captureTimestamp).toLocaleString()}
                              </span>
                            )}
                            {ev.metadata.source && (
                              <span className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full">
                                {ev.metadata.source === 'camera' ? 'Camara' : ev.metadata.source === 'gallery' ? 'Galeria' : ev.metadata.source}
                              </span>
                            )}
                            {ev.metadata.deviceInfo?.model && (
                              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                                {ev.metadata.deviceInfo.model}
                              </span>
                            )}
                            {ev.metadata.size && (
                              <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                                {ev.metadata.size > 1048576
                                  ? `${(ev.metadata.size / 1048576).toFixed(1)} MB`
                                  : `${Math.round(ev.metadata.size / 1024)} KB`}
                              </span>
                            )}
                            {ev.metadata.checksum && (
                              <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded-full" title={ev.metadata.checksum}>
                                SHA: {String(ev.metadata.checksum).slice(0, 8)}...
                              </span>
                            )}
                            {ev.metadata.ai_verification?.verified !== undefined && (
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                ev.metadata.ai_verification.verified
                                  ? 'bg-green-50 text-green-700'
                                  : 'bg-yellow-50 text-yellow-700'
                              }`}>
                                AI: {ev.metadata.ai_verification.verified ? 'Verificado' : 'Revision'}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 italic">No evidence provided</p>
                )}
              </div>

              {/* Evidence files */}
              {submission.evidence_files && (submission.evidence_files as string[]).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Archivos</h3>
                  <div className="flex flex-wrap gap-2">
                    {(submission.evidence_files as string[]).map((url, idx) => (
                      <a
                        key={idx}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-blue-600 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                        File {idx + 1}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              {submission.agent_notes && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-1">Notas del Agente</h3>
                  <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{submission.agent_notes}</p>
                </div>
              )}

              {/* Auto-check verification results */}
              {submission.auto_check_passed !== null && submission.auto_check_passed !== undefined && (() => {
                /* eslint-disable @typescript-eslint/no-explicit-any */
                const details = submission.auto_check_details as any
                const score = details?.score ?? 0
                const phase = details?.phase
                const CHECK_LABELS: Record<string, string> = {
                  schema: 'Campos requeridos',
                  gps: 'Ubicacion GPS',
                  timestamp: 'Tiempo de entrega',
                  evidence_hash: 'Integridad',
                  metadata: 'Metadatos',
                  ai_semantic: 'IA: Coincidencia',
                  tampering: 'Manipulacion',
                  genai_detection: 'Deteccion IA',
                  photo_source: 'Origen de foto',
                  duplicate: 'Duplicados',
                }
                /* eslint-enable @typescript-eslint/no-explicit-any */
                return (
                <div className={`rounded-lg border ${
                  submission.auto_check_passed ? 'bg-green-50 border-green-200' : 'bg-orange-50 border-orange-200'
                }`}>
                  <div className="flex items-center justify-between gap-2 p-3 flex-wrap">
                    <span className={`text-sm font-medium ${
                      submission.auto_check_passed ? 'text-green-700' : 'text-orange-700'
                    }`}>
                      {submission.auto_check_passed
                        ? 'Verificacion automatica: Aprobada'
                        : 'Verificacion automatica: Requiere revision'}
                    </span>
                    <div className="flex items-center gap-2">
                      {phase && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          phase === 'AB'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {phase === 'AB'
                            ? 'Verificacion completa'
                            : 'Verificacion parcial — IA pendiente'}
                        </span>
                      )}
                      {score !== undefined && (
                        <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${
                          submission.auto_check_passed ? 'bg-green-200 text-green-800' : 'bg-orange-200 text-orange-800'
                        }`}>
                          Score: {(score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                  {/* Individual check details */}
                  {Array.isArray(details?.checks) && (
                    <div className="px-3 pb-3 space-y-1">
                      {(details.checks as Array<{name: string; passed: boolean; score: number; reason?: string}>).map((check) => (
                        <div key={check.name}>
                          <div className="flex items-center gap-2 text-xs">
                            <span className={check.passed ? 'text-green-600' : 'text-red-500'}>
                              {check.passed ? '\u2713' : '\u2717'}
                            </span>
                            <span className="text-gray-600 w-28">{CHECK_LABELS[check.name] || check.name}</span>
                            <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                              <div
                                className={`h-1.5 rounded-full ${
                                  check.score >= 0.7 ? 'bg-green-500' : check.score >= 0.4 ? 'bg-yellow-500' : 'bg-red-400'
                                }`}
                                style={{ width: `${Math.round(check.score * 100)}%` }}
                              />
                            </div>
                            <span className="text-gray-400 font-mono w-8 text-right">
                              {Math.round(check.score * 100)}%
                            </span>
                          </div>
                          {check.reason && (
                            <p className="text-xs text-gray-400 ml-5 mt-0.5">{check.reason}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {/* Warnings */}
                  {Array.isArray(details?.warnings) &&
                    (details.warnings as string[]).length > 0 && (
                    <div className="px-3 pb-3">
                      {(details.warnings as string[]).map((w: string, i: number) => (
                        <p key={i} className="text-xs text-amber-600">{w}</p>
                      ))}
                    </div>
                  )}
                  {/* Score guidance */}
                  <div className="px-3 pb-3 text-xs text-gray-500">
                    {score >= 0.95 ? 'Todos los checks pasaron. Puedes aprobar con confianza.' :
                     score >= 0.70 ? 'La mayoria de checks pasaron. Revisa las advertencias antes de aprobar.' :
                     score >= 0.40 ? 'Varios checks fallaron. Revisa la evidencia cuidadosamente.' :
                     'Score bajo. Revisa cada check antes de tomar una decision.'}
                  </div>
                </div>
                )
              })()}

              {/* Result message */}
              {result && (
                <div className={`p-3 rounded-lg ${
                  result.type === 'success'
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-red-50 border border-red-200'
                }`}>
                  <p className={`text-sm ${
                    result.type === 'success' ? 'text-green-700' : 'text-red-700'
                  }`}>{result.message}</p>
                </div>
              )}

              {/* Actions - only show if no verdict yet */}
              {!submission.agent_verdict && !result?.type && (
                <div className="space-y-3">
                  {/* Reject/Request info forms */}
                  {(showRejectForm || showInfoForm) && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {showRejectForm ? 'Motivo del rechazo' : 'Que informacion necesitas?'}
                      </label>
                      <textarea
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                        rows={3}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder={showRejectForm
                          ? 'Explica por que rechazas esta entrega...'
                          : 'Describe que informacion adicional necesitas...'}
                      />
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          onClick={showRejectForm ? handleReject : handleRequestInfo}
                          disabled={isProcessing || !feedback.trim()}
                          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 ${
                            showRejectForm
                              ? 'bg-red-600 text-white hover:bg-red-700'
                              : 'bg-yellow-600 text-white hover:bg-yellow-700'
                          }`}
                        >
                          {isProcessing
                            ? 'Procesando...'
                            : showRejectForm ? 'Confirmar Rechazo' : 'Enviar Solicitud'}
                        </button>
                        <button
                          onClick={() => { setShowRejectForm(false); setShowInfoForm(false); setFeedback('') }}
                          className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Main action buttons */}
                  {!showRejectForm && !showInfoForm && (
                    <div>
                      {/* Optional notes for approval */}
                      <div className="mb-3">
                        <input
                          type="text"
                          value={approveNotes}
                          onChange={(e) => setApproveNotes(e.target.value)}
                          placeholder="Notas de aprobacion (opcional)"
                          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleApprove}
                          disabled={isProcessing}
                          className="flex-1 px-4 py-2.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                        >
                          {action === 'approving' ? 'Aprobando...' : 'Aprobar y Pagar'}
                        </button>
                        <button
                          onClick={() => setShowRejectForm(true)}
                          disabled={isProcessing}
                          className="px-4 py-2.5 bg-red-100 text-red-700 text-sm font-medium rounded-lg hover:bg-red-200 disabled:opacity-50 transition-colors"
                        >
                          Rechazar
                        </button>
                        <button
                          onClick={() => setShowInfoForm(true)}
                          disabled={isProcessing}
                          className="px-4 py-2.5 bg-yellow-100 text-yellow-700 text-sm font-medium rounded-lg hover:bg-yellow-200 disabled:opacity-50 transition-colors"
                        >
                          Pedir Info
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Already decided */}
              {submission.agent_verdict && !result?.type && (
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-sm text-gray-600">
                    Esta entrega ya fue{' '}
                    <span className="font-medium">
                      {submission.agent_verdict === 'accepted' ? 'aprobada' :
                       submission.agent_verdict === 'disputed' ? 'rechazada' : 'marcada para mas info'}
                    </span>
                    {submission.agent_notes && <> &mdash; {submission.agent_notes}</>}
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-3 rounded-b-xl">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-400">
              ID: {submissionId.slice(0, 8)}...
              {submission?.submitted_at && (
                <> | {new Date(submission.submitted_at).toLocaleString()}</>
              )}
            </p>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
