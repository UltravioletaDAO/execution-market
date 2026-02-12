/**
 * TaskDetailPage - Individual Task Page
 *
 * Features:
 * - Full task description
 * - Map showing location (placeholder)
 * - Bounty amount with fee breakdown
 * - Deadline countdown
 * - Evidence requirements list
 * - Apply button (if not applied)
 * - Status if already applied/assigned
 * - Submit evidence form (if assigned)
 */

import { useState, useMemo, useEffect } from 'react'
import { SubmissionForm } from '../components/SubmissionForm'
import { TxHashLink } from '../components/TxHashLink'
import { PaymentStatusBadge } from '../components/PaymentStatusBadge'
import { useTaskPayment } from '../hooks/useTaskPayment'
import { PaymentStatus } from '../components/PaymentStatus'
import type { Task, TaskCategory, TaskStatus, Executor, TaskApplication } from '../types/database'

// ============================================================================
// TYPES
// ============================================================================

export interface TaskDetailPageProps {
  task: Task
  executor: Executor | null
  application: TaskApplication | null
  onBack: () => void
  onApply: (message?: string) => Promise<void>
  onSubmitEvidence?: () => void
  loading?: boolean
}

// ============================================================================
// CONSTANTS
// ============================================================================

const CATEGORY_LABELS: Record<TaskCategory, string> = {
  physical_presence: 'Presencia Fisica',
  knowledge_access: 'Acceso a Conocimiento',
  human_authority: 'Autoridad Humana',
  simple_action: 'Accion Simple',
  digital_physical: 'Digital-Fisico',
}

const CATEGORY_ICONS: Record<TaskCategory, string> = {
  physical_presence: '📍',
  knowledge_access: '📚',
  human_authority: '📋',
  simple_action: '✋',
  digital_physical: '🔗',
}

const STATUS_COLORS: Record<TaskStatus, string> = {
  published: 'bg-green-100 text-green-800',
  accepted: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  submitted: 'bg-purple-100 text-purple-800',
  verifying: 'bg-indigo-100 text-indigo-800',
  completed: 'bg-gray-100 text-gray-800',
  disputed: 'bg-red-100 text-red-800',
  expired: 'bg-gray-100 text-gray-500',
  cancelled: 'bg-gray-100 text-gray-400',
}

const STATUS_LABELS: Record<TaskStatus, string> = {
  published: 'Disponible',
  accepted: 'Aceptada',
  in_progress: 'En Progreso',
  submitted: 'Enviada',
  verifying: 'Verificando',
  completed: 'Completada',
  disputed: 'En Disputa',
  expired: 'Expirada',
  cancelled: 'Cancelada',
}

const EVIDENCE_TYPE_LABELS: Record<string, { label: string; icon: string }> = {
  photo: { label: 'Foto', icon: '📷' },
  photo_geo: { label: 'Foto con ubicacion', icon: '📍' },
  video: { label: 'Video', icon: '🎥' },
  document: { label: 'Documento', icon: '📄' },
  receipt: { label: 'Recibo', icon: '🧾' },
  signature: { label: 'Firma', icon: '✍️' },
  notarized: { label: 'Notarizado', icon: '📋' },
  timestamp_proof: { label: 'Prueba de tiempo', icon: '⏰' },
  text_response: { label: 'Respuesta de texto', icon: '📝' },
  measurement: { label: 'Medicion', icon: '📏' },
  screenshot: { label: 'Captura de pantalla', icon: '🖥️' },
}

const PLATFORM_FEE_PERCENT = 13 // 13% platform fee

// ============================================================================
// UTILITIES
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatFullDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-MX', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getTimeRemaining(deadline: string): {
  expired: boolean
  text: string
  urgent: boolean
} {
  const now = new Date()
  const deadlineDate = new Date(deadline)
  const diffMs = deadlineDate.getTime() - now.getTime()

  if (diffMs < 0) {
    return { expired: true, text: 'Expirada', urgent: false }
  }

  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffMinutes < 60) {
    return { expired: false, text: `${diffMinutes} minutos`, urgent: true }
  }
  if (diffHours < 24) {
    return { expired: false, text: `${diffHours} horas`, urgent: diffHours < 6 }
  }
  if (diffDays === 1) {
    return { expired: false, text: '1 dia', urgent: false }
  }
  return { expired: false, text: `${diffDays} dias`, urgent: false }
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
      </svg>
      Volver
    </button>
  )
}

function DeadlineCountdown({ deadline }: { deadline: string }) {
  const [timeRemaining, setTimeRemaining] = useState(() => getTimeRemaining(deadline))

  useEffect(() => {
    const interval = setInterval(() => {
      setTimeRemaining(getTimeRemaining(deadline))
    }, 60000) // Update every minute

    return () => clearInterval(interval)
  }, [deadline])

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
        timeRemaining.expired
          ? 'bg-gray-100 text-gray-600'
          : timeRemaining.urgent
            ? 'bg-red-100 text-red-700'
            : 'bg-blue-50 text-blue-700'
      }`}
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <div>
        <div className="text-xs opacity-75">Tiempo restante</div>
        <div className="font-semibold">{timeRemaining.text}</div>
      </div>
    </div>
  )
}

function BountyBreakdown({ bountyUsd, paymentToken }: { bountyUsd: number; paymentToken: string }) {
  const platformFee = bountyUsd * (PLATFORM_FEE_PERCENT / 100)
  const netEarnings = bountyUsd - platformFee

  return (
    <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl p-5 text-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-green-100 text-sm font-medium">Recompensa</h3>
        <span className="text-green-200 text-xs">{paymentToken}</span>
      </div>

      <div className="text-3xl font-bold mb-4">{formatCurrency(bountyUsd)}</div>

      <div className="space-y-2 pt-3 border-t border-green-500/30">
        <div className="flex justify-between text-sm">
          <span className="text-green-200">Monto total</span>
          <span>{formatCurrency(bountyUsd)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-green-200">Comision plataforma ({PLATFORM_FEE_PERCENT}%)</span>
          <span>-{formatCurrency(platformFee)}</span>
        </div>
        <div className="flex justify-between text-sm font-semibold pt-2 border-t border-green-500/30">
          <span>Tu ganancia neta</span>
          <span>{formatCurrency(netEarnings)}</span>
        </div>
      </div>
    </div>
  )
}

function LocationMap({ task }: { task: Task }) {
  // Placeholder map component - in production, use a real map library
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900">Ubicacion</h3>
      </div>

      {/* Map placeholder */}
      <div className="h-48 bg-gray-100 flex items-center justify-center relative">
        <div className="text-center text-gray-400">
          <svg className="w-8 h-8 mx-auto mb-2" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-sm">Mapa no disponible</span>
        </div>

        {task.location && (
          <div className="absolute bottom-2 left-2 bg-white/90 backdrop-blur px-2 py-1 rounded text-xs text-gray-600">
            {task.location.lat.toFixed(4)}, {task.location.lng.toFixed(4)}
          </div>
        )}
      </div>

      {/* Location details */}
      <div className="p-4 space-y-2">
        {task.location_hint && (
          <div className="flex items-start gap-2">
            <svg className="w-4 h-4 text-gray-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-sm text-gray-700">{task.location_hint}</span>
          </div>
        )}
        {task.location_radius_km && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
              />
            </svg>
            <span>Radio: {task.location_radius_km} km</span>
          </div>
        )}
      </div>
    </div>
  )
}

function EvidenceRequirements({ task }: { task: Task }) {
  const required = task.evidence_schema.required || []
  const optional = task.evidence_schema.optional || []

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900">Evidencia Requerida</h3>
        <p className="text-sm text-gray-500 mt-1">
          Debes proporcionar esta evidencia al completar la tarea
        </p>
      </div>

      <div className="p-4 space-y-4">
        {/* Required evidence */}
        {required.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Obligatoria
            </h4>
            <div className="space-y-2">
              {required.map((type) => {
                const config = EVIDENCE_TYPE_LABELS[type]
                return (
                  <div
                    key={type}
                    className="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-100"
                  >
                    <span className="text-xl">{config?.icon || '📎'}</span>
                    <div className="flex-1">
                      <span className="font-medium text-gray-900">
                        {config?.label || type}
                      </span>
                    </div>
                    <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded">
                      Requerida
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Optional evidence */}
        {optional.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Opcional
            </h4>
            <div className="space-y-2">
              {optional.map((type) => {
                const config = EVIDENCE_TYPE_LABELS[type]
                return (
                  <div
                    key={type}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100"
                  >
                    <span className="text-xl">{config?.icon || '📎'}</span>
                    <div className="flex-1">
                      <span className="font-medium text-gray-700">
                        {config?.label || type}
                      </span>
                    </div>
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs font-medium rounded">
                      Opcional
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Requirements({ task, executor }: { task: Task; executor: Executor | null }) {
  const meetsReputation = !executor || executor.reputation_score >= task.min_reputation

  if (task.min_reputation === 0 && task.required_roles.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900">Requisitos</h3>
      </div>

      <div className="p-4 space-y-3">
        {task.min_reputation > 0 && (
          <div
            className={`flex items-center gap-3 p-3 rounded-lg ${
              meetsReputation ? 'bg-green-50' : 'bg-amber-50'
            }`}
          >
            <svg
              className={`w-5 h-5 ${meetsReputation ? 'text-green-600' : 'text-amber-600'}`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            <div className="flex-1">
              <span className="font-medium text-gray-900">
                Reputacion minima: {task.min_reputation}
              </span>
              {executor && (
                <span
                  className={`ml-2 text-sm ${
                    meetsReputation ? 'text-green-600' : 'text-amber-600'
                  }`}
                >
                  (tu: {executor.reputation_score})
                </span>
              )}
            </div>
            {meetsReputation ? (
              <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </div>
        )}

        {task.required_roles.map((role) => {
          const hasRole = executor?.roles.includes(role)
          return (
            <div
              key={role}
              className={`flex items-center gap-3 p-3 rounded-lg ${
                hasRole ? 'bg-green-50' : 'bg-amber-50'
              }`}
            >
              <svg
                className={`w-5 h-5 ${hasRole ? 'text-green-600' : 'text-amber-600'}`}
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="font-medium text-gray-900">Rol requerido: {role}</span>
              {hasRole ? (
                <svg className="w-5 h-5 text-green-600 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg className="w-5 h-5 text-amber-600 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ApplicationStatus({ application }: { application: TaskApplication }) {
  const statusConfig = {
    pending: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      icon: 'text-yellow-600',
      title: 'Solicitud Pendiente',
      description: 'Tu solicitud esta siendo revisada por el agente',
    },
    accepted: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: 'text-green-600',
      title: 'Solicitud Aceptada',
      description: 'Has sido asignado a esta tarea. Puedes comenzar a trabajar.',
    },
    rejected: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: 'text-red-600',
      title: 'Solicitud Rechazada',
      description: 'El agente ha rechazado tu solicitud para esta tarea.',
    },
  }

  const config = statusConfig[application.status]

  return (
    <div className={`p-4 rounded-xl border ${config.bg} ${config.border}`}>
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-full ${config.bg}`}>
          <svg className={`w-5 h-5 ${config.icon}`} fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div>
          <h4 className="font-semibold text-gray-900">{config.title}</h4>
          <p className="text-sm text-gray-600 mt-1">{config.description}</p>
          {application.message && (
            <p className="text-sm text-gray-500 mt-2 italic">
              "{application.message}"
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function ApplyForm({
  onApply,
  loading,
  canApply,
  reason,
}: {
  onApply: (message?: string) => void
  loading: boolean
  canApply: boolean
  reason?: string
}) {
  const [message, setMessage] = useState('')
  const [showForm, setShowForm] = useState(false)

  if (!canApply) {
    return (
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
        <div className="flex items-start gap-3">
          <svg
            className="w-5 h-5 text-amber-600 flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <h4 className="font-semibold text-amber-800">No puedes aplicar</h4>
            <p className="text-sm text-amber-700 mt-1">{reason}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        className="w-full py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors"
      >
        Aplicar a esta tarea
      </button>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
      <h4 className="font-semibold text-gray-900">Aplicar a esta tarea</h4>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Mensaje (opcional)
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Escribe un mensaje al agente explicando por que eres un buen candidato..."
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => setShowForm(false)}
          disabled={loading}
          className="flex-1 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Cancelar
        </button>
        <button
          onClick={() => onApply(message || undefined)}
          disabled={loading}
          className="flex-1 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {loading ? 'Enviando...' : 'Enviar Solicitud'}
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function TaskDetailPage({
  task,
  executor,
  application,
  onBack,
  onApply,
  onSubmitEvidence,
}: TaskDetailPageProps) {
  const [showSubmissionForm, setShowSubmissionForm] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load payment data when task has escrow context or is in a terminal state
  const hasEscrowContext = Boolean(task.escrow_tx || task.escrow_id)
  const showPaymentSection =
    hasEscrowContext ||
    task.status === 'completed' ||
    task.status === 'submitted' ||
    task.status === 'expired' ||
    task.status === 'cancelled'
  const { payment, loading: paymentLoading } = useTaskPayment(showPaymentSection ? task.id : null)

  const isAssigned = task.executor_id === executor?.id
  const canApply = useMemo(() => {
    if (!executor) return { can: false, reason: 'Debes iniciar sesion para aplicar' }
    if (task.status !== 'published')
      return { can: false, reason: 'Esta tarea ya no esta disponible' }
    if (application) return { can: false, reason: 'Ya has aplicado a esta tarea' }
    if (executor.reputation_score < task.min_reputation)
      return {
        can: false,
        reason: `Necesitas ${task.min_reputation} de reputacion (tienes ${executor.reputation_score})`,
      }
    if (
      task.required_roles.length > 0 &&
      !task.required_roles.every((role) => executor.roles.includes(role))
    )
      return { can: false, reason: 'No tienes los roles requeridos' }
    return { can: true, reason: undefined }
  }, [executor, task, application])

  const handleApply = async (message?: string) => {
    setApplying(true)
    setError(null)
    try {
      await onApply(message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al aplicar')
    } finally {
      setApplying(false)
    }
  }

  // Show submission form if assigned
  if (showSubmissionForm && isAssigned && executor) {
    return (
      <div className="space-y-4">
        <BackButton onClick={() => setShowSubmissionForm(false)} />
        <SubmissionForm
          task={task}
          executor={executor}
          onSubmit={() => {
            setShowSubmissionForm(false)
            onSubmitEvidence?.()
          }}
          onCancel={() => setShowSubmissionForm(false)}
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Back button */}
      <BackButton onClick={onBack} />

      {/* Header Card */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* Category & Status */}
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{CATEGORY_ICONS[task.category]}</span>
              <span className="text-sm text-gray-500 uppercase tracking-wide">
                {CATEGORY_LABELS[task.category]}
              </span>
            </div>
            <span
              className={`px-3 py-1 text-sm font-medium rounded-full ${STATUS_COLORS[task.status]}`}
            >
              {STATUS_LABELS[task.status]}
            </span>
          </div>
        </div>

        {/* Title & Instructions */}
        <div className="p-4">
          <h1 className="text-xl font-bold text-gray-900 mb-3">{task.title}</h1>
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-gray-700 bg-gray-50 p-4 rounded-lg text-sm">
              {task.instructions}
            </pre>
          </div>
        </div>

        {/* Deadline */}
        <div className="px-4 pb-4">
          <div className="flex items-center justify-between">
            <DeadlineCountdown deadline={task.deadline} />
            <div className="text-right text-sm text-gray-500">
              <div>Fecha limite:</div>
              <div>{formatFullDate(task.deadline)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bounty Breakdown */}
      <BountyBreakdown bountyUsd={task.bounty_usd} paymentToken={task.payment_token} />

      {/* Payment / Escrow Status */}
      {showPaymentSection && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            {task.status === 'cancelled' ? 'Reembolso' : 'Escrow y Pago'}
          </h3>
          {paymentLoading ? (
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-gray-600">Cargando estado de pago...</span>
            </div>
          ) : payment ? (
            <PaymentStatus payment={payment} compact={false} showTimeline={true} />
          ) : hasEscrowContext ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <PaymentStatusBadge status="authorized" txHash={task.escrow_tx} />
                  <span className="text-sm text-blue-700">Fondos en escrow</span>
                </div>
              </div>
              {task.escrow_tx && (
                <div className="flex items-center gap-2 text-sm text-gray-600 pl-1">
                  <span className="text-gray-400">Escrow tx:</span>
                  <TxHashLink txHash={task.escrow_tx} />
                </div>
              )}
            </div>
          ) : task.status === 'cancelled' ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 p-3 bg-red-50 rounded-lg">
                <PaymentStatusBadge status={task.refund_tx ? 'refunded' : 'cancelled'} txHash={task.refund_tx} />
                <span className="text-sm text-red-700">
                  {task.refund_tx
                    ? 'Fondos reembolsados al agente'
                    : 'Autorizacion expirada - fondos no fueron movidos'}
                </span>
              </div>
              {task.refund_tx && (
                <div className="flex items-center gap-2 text-sm text-gray-600 pl-1">
                  <span className="text-gray-400">Refund tx:</span>
                  <TxHashLink txHash={task.refund_tx} />
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500 p-3 bg-gray-50 rounded-lg">
              Sin registros de pago para esta tarea.
            </p>
          )}
        </div>
      )}

      {/* Location Map (if location exists) */}
      {(task.location || task.location_hint) && <LocationMap task={task} />}

      {/* Evidence Requirements */}
      <EvidenceRequirements task={task} />

      {/* Requirements */}
      <Requirements task={task} executor={executor} />

      {/* Agent Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h3 className="font-semibold text-gray-900 mb-3">Publicado por</h3>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M13 7H7v6h6V7z" />
              <path
                fillRule="evenodd"
                d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2zM5 5h10v10H5V5z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div>
            <div className="font-medium text-gray-900">{task.agent_id}</div>
            <div className="text-xs text-gray-500">Agente verificado</div>
          </div>
        </div>
      </div>

      {/* Action Section */}
      <div className="space-y-3">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Application status if already applied */}
        {application && <ApplicationStatus application={application} />}

        {/* If assigned, show submit evidence button */}
        {isAssigned && ['accepted', 'in_progress'].includes(task.status) && (
          <button
            onClick={() => setShowSubmissionForm(true)}
            className="w-full py-3 bg-green-600 text-white font-medium rounded-xl hover:bg-green-700 transition-colors"
          >
            Enviar Evidencia
          </button>
        )}

        {/* If not applied and can apply, show apply form */}
        {!application && !isAssigned && task.status === 'published' && (
          <ApplyForm
            onApply={handleApply}
            loading={applying}
            canApply={canApply.can}
            reason={canApply.reason}
          />
        )}

        {/* Login prompt if not logged in */}
        {!executor && task.status === 'published' && (
          <div className="text-center p-4 bg-gray-50 rounded-xl">
            <p className="text-gray-600 mb-3">Inicia sesion para aplicar a esta tarea</p>
            <button className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors">
              Iniciar sesion
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default TaskDetailPage
