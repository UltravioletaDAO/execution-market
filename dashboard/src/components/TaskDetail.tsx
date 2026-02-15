// Execution Market: Task Detail Component
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'
import { useTaskPayment } from '../hooks/useTaskPayment'
import { PaymentStatus } from './PaymentStatus'
import type { Task, TaskCategory, Executor } from '../types/database'
import { CATEGORY_ICONS } from '../constants/categories'
import { getNetworkDisplayName } from '../utils/blockchain'
import { TxHashLink } from './TxHashLink'
import { useAgentReputation, getReputationTier, getTierColor } from '../hooks/useAgentReputation'
import { AgentStandardCard } from './agents/AgentStandardCard'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

interface TaskDetailProps {
  task: Task
  currentExecutor: Executor | null
  onBack: () => void
  onAccept?: () => void
}

// Category labels resolved via i18n (see tasks.categories in locale files)
const CATEGORY_KEYS: Record<TaskCategory, string> = {
  physical_presence: 'physical_presence',
  knowledge_access: 'knowledge_access',
  human_authority: 'human_authority',
  simple_action: 'simple_action',
  digital_physical: 'digital_physical',
}

// Evidence type labels resolved via i18n (see tasks.evidenceTypes in locale files)
const EVIDENCE_TYPE_KEYS: Record<string, string> = {
  photo: 'photo',
  photo_geo: 'photo_geo',
  video: 'video',
  document: 'document',
  receipt: 'receipt',
  signature: 'signature',
  notarized: 'notarized',
  timestamp_proof: 'timestamp_proof',
  text_response: 'text_response',
  measurement: 'measurement',
  screenshot: 'screenshot',
}

function formatDeadline(deadline: string, lang = 'en'): string {
  const localeMap: Record<string, string> = { en: 'en-US', es: 'es-MX', pt: 'pt-BR' }
  const date = new Date(deadline)
  return date.toLocaleDateString(localeMap[lang] || lang, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatBounty(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount)
}

export function TaskDetail({
  task,
  currentExecutor,
  onBack,
  onAccept,
}: TaskDetailProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [accepting, setAccepting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasEscrowContext = Boolean(task.escrow_tx || task.escrow_id)
  const showPayment =
    hasEscrowContext ||
    task.status === 'completed' ||
    task.status === 'submitted' ||
    task.status === 'expired' ||
    task.status === 'cancelled'
  const { payment, loading: paymentLoading } = useTaskPayment(showPayment ? task.id : null)
  const { data: agentReputation } = useAgentReputation()

  const canAccept =
    task.status === 'published' &&
    currentExecutor &&
    currentExecutor.reputation_score >= task.min_reputation

  const handleAccept = async () => {
    if (!currentExecutor) return

    setAccepting(true)
    setError(null)

    try {
      // Get fresh session to avoid stale token / RLS mismatch
      const { data: { session: currentSession } } = await supabase.auth.getSession()

      const headers: Record<string, string> = {
        apikey: SUPABASE_KEY,
        'Content-Type': 'application/json',
      }

      if (currentSession?.access_token) {
        headers['Authorization'] = `Bearer ${currentSession.access_token}`
      }

      // Use the apply_to_task RPC for atomic acceptance
      const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/apply_to_task`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          p_task_id: task.id,
          p_executor_id: currentExecutor.id,
          p_message: null,
        }),
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `Failed: ${response.status}`)
      }

      const result = await response.json()
      if (result && result.success === false) {
        throw new Error(result.error || 'La tarea ya no esta disponible')
      }

      onAccept?.()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'No se pudo aceptar la tarea. Intenta de nuevo.'
      )
    } finally {
      setAccepting(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onBack}
          aria-label="Volver a la lista de tareas"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Volver a lista
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{CATEGORY_ICONS[task.category]}</span>
              <span className="text-sm text-gray-500 uppercase tracking-wide">
                {t(`tasks.categories.${CATEGORY_KEYS[task.category]}`, task.category)}
              </span>
            </div>
            <h1 className="text-xl font-bold text-gray-900">{task.title}</h1>
          </div>

          <div className="text-right">
            <div className="text-2xl font-bold text-green-600">
              {formatBounty(task.bounty_usd)}
            </div>
            <div className="text-xs text-gray-400">
              {task.payment_token}{task.payment_network ? ` on ${getNetworkDisplayName(task.payment_network)}` : ''}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Instructions */}
        <section>
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
            Instrucciones
          </h2>
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-gray-700 bg-gray-50 p-4 rounded-lg">
              {task.instructions}
            </pre>
          </div>
        </section>

        {/* Evidence requirements */}
        <section>
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
            Evidencia Requerida
          </h2>
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {task.evidence_schema.required.map((type) => (
                <span
                  key={type}
                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-700 text-sm rounded-full"
                >
                  <span className="w-1.5 h-1.5 bg-red-500 rounded-full" />
                  {t(`tasks.evidenceTypes.${EVIDENCE_TYPE_KEYS[type] || type}`, type)}
                </span>
              ))}
            </div>
            {task.evidence_schema.optional && task.evidence_schema.optional.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {task.evidence_schema.optional.map((type) => (
                  <span
                    key={type}
                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-100 text-gray-600 text-sm rounded-full"
                  >
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full" />
                    {t(`tasks.evidenceTypes.${EVIDENCE_TYPE_KEYS[type] || type}`, type)} ({t('common.optional', 'optional')})
                  </span>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Location */}
        {task.location_hint && (
          <section>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              Ubicacion
            </h2>
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
                  (radio: {task.location_radius_km} km)
                </span>
              )}
            </div>
          </section>
        )}

        {/* Deadline */}
        <section>
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
            Fecha Limite
          </h2>
          <div className="flex items-center gap-2 text-gray-700">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{formatDeadline(task.deadline)}</span>
          </div>
        </section>

        {/* Requirements */}
        {(task.min_reputation > 0 || task.required_roles.length > 0) && (
          <section>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              Requisitos
            </h2>
            <ul className="space-y-2">
              {task.min_reputation > 0 && (
                <li className="flex items-center gap-2 text-gray-700">
                  <svg className="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <span>Reputacion minima: {task.min_reputation}</span>
                  {currentExecutor && (
                    <span
                      className={`text-sm ${
                        currentExecutor.reputation_score >= task.min_reputation
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      (tu: {currentExecutor.reputation_score})
                    </span>
                  )}
                </li>
              )}
              {task.required_roles.map((role) => (
                <li key={role} className="flex items-center gap-2 text-gray-700">
                  <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Rol requerido: {role}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Posted by - Agent Card */}
        <section>
          <AgentStandardCard
            walletAddress={task.agent_id}
            label={t('tasks.postedBy', 'Posted by')}
          />
        </section>

        {/* Accepted by - Worker Card (if assigned) */}
        {task.executor_id && (
          <section>
            <AgentStandardCard
              walletAddress={task.executor_id}
              label={t('tasks.acceptedBy', 'Accepted by')}
            />
          </section>
        )}

        {/* Transaction Details */}
        {(task.escrow_tx || task.refund_tx || task.payment_network) && (
          <section>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              {t('tasks.transactionDetails', 'Transaction Details')}
            </h2>
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              {task.payment_network && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">{t('tasks.network', 'Network')}</span>
                  <span className="text-sm font-medium text-gray-900">
                    {getNetworkDisplayName(task.payment_network)}
                  </span>
                </div>
              )}
              {task.payment_token && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">{t('tasks.token', 'Token')}</span>
                  <span className="text-sm font-medium text-gray-900">
                    {task.payment_token}
                  </span>
                </div>
              )}
              {task.escrow_tx && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">{t('tasks.escrowTx', 'Escrow')}</span>
                  <TxHashLink txHash={task.escrow_tx} network={task.payment_network || 'base'} />
                </div>
              )}
              {task.refund_tx && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">{t('tasks.refundTx', 'Refund')}</span>
                  <TxHashLink txHash={task.refund_tx} network={task.payment_network || 'base'} />
                </div>
              )}
            </div>
          </section>
        )}

        {/* Payment / Refund status */}
        {showPayment && (
          <section>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              {task.status === 'expired' || task.status === 'cancelled'
                ? 'Reembolso'
                : hasEscrowContext
                ? 'Escrow y Pago'
                : 'Pago'}
            </h2>
            {paymentLoading ? (
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-gray-600">Cargando estado de pago...</span>
              </div>
            ) : payment ? (
              <PaymentStatus payment={payment} compact={false} showTimeline={true} />
            ) : task.status === 'submitted' ? (
              <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg">
                <div className="w-4 h-4 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-yellow-700">Procesando pago...</span>
              </div>
            ) : hasEscrowContext ? (
              <p className="text-sm text-blue-700 p-3 bg-blue-50 rounded-lg">
                Escrow detectado. Esperando sincronizacion de transacciones x402.
              </p>
            ) : (
              <p className="text-sm text-gray-500 p-3 bg-gray-50 rounded-lg">
                No hay registros de pago para esta tarea.
              </p>
            )}
          </section>
        )}
      </div>

      {/* Actions */}
      {task.status === 'published' && (
        <div className="p-4 bg-gray-50 border-t border-gray-200">
          {error && (
            <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
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
                    Cerrar e intentar de nuevo
                  </button>
                </div>
              </div>
            </div>
          )}

          {!currentExecutor ? (
            <div className="text-center">
              <p className="text-gray-600 mb-2">Inicia sesion para aceptar esta tarea</p>
              <button
                onClick={() => navigate('/')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Iniciar sesion
              </button>
            </div>
          ) : !canAccept ? (
            <div className="text-center">
              <p className="text-amber-600">
                No cumples con los requisitos para esta tarea
              </p>
            </div>
          ) : (
            <button
              onClick={handleAccept}
              disabled={accepting}
              className="w-full py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {accepting ? 'Aceptando...' : `Aceptar tarea - ${formatBounty(task.bounty_usd)}`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
