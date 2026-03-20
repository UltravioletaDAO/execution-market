import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useTranslation as useCustomTranslation } from '../../i18n/hooks/useTranslation'
import type { Task, TaskCategory } from '../../types/database'
import { PaymentStatus } from '../PaymentStatus'
import { useTaskPayment } from '../../hooks/useTaskPayment'
import { getExplorerUrl } from '../../utils/blockchain'
import { TxHashLink } from '../TxLink'

interface TaskDetailPanelProps {
  task: Task
  isAuthenticated: boolean
  onClose: () => void
  onApply: () => void
}

const CATEGORY_ICONS: Record<TaskCategory, string> = {
  physical_presence: '📍',
  knowledge_access: '📚',
  human_authority: '📋',
  simple_action: '✋',
  digital_physical: '🔗',
  data_processing: '🔄',
  research: '🔍',
  content_generation: '✍️',
  code_execution: '💻',
  api_integration: '🔌',
  multi_step_workflow: '📊',
}

const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  photo: 'Photo',
  photo_geo: 'Geotagged Photo',
  video: 'Video',
  document: 'Document',
  receipt: 'Receipt',
  signature: 'Signature',
  notarized: 'Notarized',
  timestamp_proof: 'Timestamp Proof',
  text_response: 'Text Response',
  measurement: 'Measurement',
  screenshot: 'Screenshot',
}

export function TaskDetailPanel({ task, isAuthenticated, onClose, onApply }: TaskDetailPanelProps) {
  const { t } = useTranslation()
  const { formatCurrency, formatTimeRemaining } = useCustomTranslation()
  const isAcceptable = task.status === 'published'

  // Fetch payment data when escrow exists or task has reached payment-sensitive states
  const hasEscrow = Boolean(task.escrow_tx || task.escrow_id)
  const shouldLoadPayment =
    hasEscrow ||
    task.status === 'submitted' ||
    task.status === 'completed' ||
    task.status === 'expired' ||
    task.status === 'cancelled'
  const { payment, loading: paymentLoading } = useTaskPayment(shouldLoadPayment ? task.id : null)

  // Close on escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose])

  // Prevent body scroll when panel is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  const categoryLabel = t(`tasks.categories.${task.category}`)
  const deadlineText = formatTimeRemaining(task.deadline)
  const bountyText = formatCurrency(task.bounty_usd)

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-2xl max-h-[85vh] bg-white rounded-t-2xl shadow-2xl animate-slide-up overflow-hidden flex flex-col">
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 bg-gray-300 rounded-full" />
        </div>

        {/* Header */}
        <div className="px-6 pb-4 border-b border-gray-100">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xl">{CATEGORY_ICONS[task.category]}</span>
                <span className="text-xs text-gray-500 uppercase tracking-wide">
                  {categoryLabel}
                </span>
              </div>
              <h2 className="text-xl font-bold text-gray-900">{task.title}</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="flex items-center gap-4 mt-3">
            <div className="text-2xl font-bold text-green-600">{bountyText}</div>
            <span className="text-xs text-gray-400">{task.payment_token}</span>
            <div className="ml-auto flex items-center gap-1 text-sm text-gray-500">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{deadlineText}</span>
            </div>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {/* Instructions */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              {t('tasks.instructions')}
            </h3>
            <pre className="whitespace-pre-wrap font-sans text-gray-700 bg-gray-50 p-4 rounded-lg text-sm">
              {task.instructions}
            </pre>
          </section>

          {/* Evidence requirements */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              {t('submission.requiredEvidence')}
            </h3>
            <div className="flex flex-wrap gap-2">
              {task.evidence_schema.required.map((type) => (
                <span
                  key={type}
                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-700 text-sm rounded-full"
                >
                  <span className="w-1.5 h-1.5 bg-red-500 rounded-full" />
                  {EVIDENCE_TYPE_LABELS[type] || type}
                </span>
              ))}
              {task.evidence_schema.optional?.map((type) => (
                <span
                  key={type}
                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-100 text-gray-600 text-sm rounded-full"
                >
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full" />
                  {EVIDENCE_TYPE_LABELS[type] || type}
                </span>
              ))}
            </div>
          </section>

          {/* Location */}
          {task.location_hint && (
            <section>
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
                {t('tasks.location')}
              </h3>
              <div className="flex items-center gap-2 text-gray-700">
                <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>{task.location_hint}</span>
                {task.location_radius_km && (
                  <span className="text-sm text-gray-500">
                    ({task.location_radius_km} km)
                  </span>
                )}
              </div>
            </section>
          )}

          {/* Requirements */}
          {(task.min_reputation > 0 || task.required_roles.length > 0) && (
            <section>
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
                {t('tasks.requirements')}
              </h3>
              <ul className="space-y-2">
                {task.min_reputation > 0 && (
                  <li className="flex items-center gap-2 text-gray-700 text-sm">
                    <svg className="w-4 h-4 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    {t('tasks.requiresReputation', { score: task.min_reputation })}
                  </li>
                )}
                {task.required_roles.map((role) => (
                  <li key={role} className="flex items-center gap-2 text-gray-700 text-sm">
                    <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                    </svg>
                    {role}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Payment / Escrow Status */}
          {shouldLoadPayment && (
            <section>
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
                {t('payment.status', 'Estado del Pago')}
              </h3>

              {paymentLoading && (
                <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {t('common.loading', 'Cargando...')}
                </div>
              )}

              {!paymentLoading && payment && (
                <>
                  <PaymentStatus
                    payment={payment}
                    showTimeline={true}
                    bountyAmount={task.bounty_usd}
                  />

                  {/* Prominent refund confirmation banner */}
                  {payment.status === 'refunded' && (
                    <div className="mt-3 p-4 bg-green-50 border border-green-200 rounded-lg">
                      <div className="flex items-center gap-3">
                        <svg className="w-6 h-6 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <div>
                          <p className="text-sm font-semibold text-green-800">
                            {t('payment.refundConfirmed', 'Reembolso Confirmado')}
                          </p>
                          <p className="text-xs text-green-700 mt-0.5">
                            {t('payment.refundConfirmedDesc', 'Los fondos han sido devueltos al agente. Esta tarea ha expirado.')}
                          </p>
                          {payment.escrow_tx && (
                            <div className="mt-1.5">
                              <TxHashLink txHash={payment.escrow_tx} network={payment.network || 'base'} className="text-xs" />
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}

              {!paymentLoading && !payment && (
                <p className="text-sm text-gray-400 italic">
                  {hasEscrow
                    ? t('payment.syncingData', 'Escrow detectado. Esperando sincronizacion de transacciones x402.')
                    : t('payment.noData', 'No hay datos de pago disponibles.')}
                </p>
              )}
            </section>
          )}
        </div>

        {/* Action footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50">
          {!isAcceptable ? (
            <button
              disabled
              className="w-full py-3 bg-gray-300 text-gray-700 font-semibold rounded-xl cursor-not-allowed"
            >
              {task.status === 'expired'
                ? t('tasks.expired', 'Task expired')
                : t('tasks.unavailable', 'Task not available')}
            </button>
          ) : isAuthenticated ? (
            <button
              onClick={onApply}
              className="w-full py-3 bg-green-600 text-white font-semibold rounded-xl hover:bg-green-700 transition-colors"
            >
              {t('tasks.acceptTask')} - {bountyText}
            </button>
          ) : (
            <button
              onClick={onApply}
              className="w-full py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors"
            >
              {t('landing.connectToApply')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
