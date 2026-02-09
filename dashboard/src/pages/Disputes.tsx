/**
 * Disputes - Pagina completa de gestion de disputas
 *
 * Features:
 * - Lista de disputas activas con contador de votos y tiempo restante
 * - Vista detallada con evidencia, timeline, submission del worker
 * - Interfaz de votacion para validadores (stake requerido)
 * - Seccion de apelacion con escalado a Gnosis Safe multisig
 */

import { useState, useCallback, useMemo } from 'react'

// ============================================================================
// TYPES
// ============================================================================

export interface DisputeEvidence {
  type: 'photo' | 'document' | 'screenshot' | 'video' | 'text'
  url: string
  description?: string
  uploadedAt: string
  metadata?: Record<string, unknown>
}

export interface TimelineEvent {
  id: string
  type: 'created' | 'evidence_submitted' | 'vote_cast' | 'escalated' | 'resolved' | 'appealed'
  actor: 'worker' | 'agent' | 'validator' | 'system'
  actorAddress?: string
  description: string
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface Vote {
  validatorAddress: string
  validatorName?: string
  side: 'worker' | 'agent'
  stakeAmount: number
  timestamp: string
  reason?: string
}

export interface WorkerSubmission {
  id: string
  evidence: DisputeEvidence[]
  notes: string
  submittedAt: string
  gpsLocation?: { lat: number; lng: number }
  deviceInfo?: string
}

export interface DisputeTask {
  id: string
  title: string
  bountyUsd: number
  category: string
  instructions: string
  deadline: string
}

export interface Dispute {
  id: string
  task: DisputeTask
  status: 'open' | 'voting' | 'escalated' | 'resolved' | 'appealed'
  reason: string
  agentRejectionReason: string
  workerAddress: string
  workerName?: string
  agentAddress: string
  agentName?: string
  workerSubmission: WorkerSubmission
  agentEvidence: DisputeEvidence[]
  workerEvidence: DisputeEvidence[]
  timeline: TimelineEvent[]
  votes: Vote[]
  votesForWorker: number
  votesForAgent: number
  requiredVotes: number
  resolutionDeadline: string
  createdAt: string
  resolvedAt?: string
  winner?: 'worker' | 'agent'
  canAppeal: boolean
  appealDeadline?: string
  appealCostUsd: number
  gnosisSafeAddress?: string
}

export interface DisputesPageProps {
  userAddress: string
  userRole: 'worker' | 'agent' | 'validator'
  isValidator?: boolean
  validatorStake?: number
  onBack?: () => void
}

// ============================================================================
// MOCK DATA (Para desarrollo - reemplazar con hooks reales)
// ============================================================================

const MOCK_DISPUTES: Dispute[] = [
  {
    id: 'disp_001',
    task: {
      id: 'task_001',
      title: 'Verificar existencia de producto en tienda',
      bountyUsd: 15.00,
      category: 'physical_presence',
      instructions: 'Tomar foto del producto X en el estante de la tienda Y con precio visible',
      deadline: '2026-01-26T18:00:00Z',
    },
    status: 'voting',
    reason: 'Foto borrosa, no se puede verificar el producto',
    agentRejectionReason: 'La imagen no muestra claramente el producto solicitado. El angulo de la foto no permite ver el precio.',
    workerAddress: '0x1234...5678',
    workerName: 'Carlos M.',
    agentAddress: '0xabcd...efgh',
    agentName: 'AgentBot #42',
    workerSubmission: {
      id: 'sub_001',
      evidence: [
        {
          type: 'photo',
          url: 'https://example.com/evidence/photo1.jpg',
          description: 'Foto del producto en estante',
          uploadedAt: '2026-01-25T14:30:00Z',
          metadata: { gps: { lat: 4.6097, lng: -74.0817 } },
        },
      ],
      notes: 'El producto estaba en el estante inferior. Tome la foto desde el angulo disponible.',
      submittedAt: '2026-01-25T14:30:00Z',
      gpsLocation: { lat: 4.6097, lng: -74.0817 },
    },
    agentEvidence: [
      {
        type: 'screenshot',
        url: 'https://example.com/evidence/agent_analysis.png',
        description: 'Analisis de imagen mostrando baja calidad',
        uploadedAt: '2026-01-25T15:00:00Z',
      },
    ],
    workerEvidence: [
      {
        type: 'photo',
        url: 'https://example.com/evidence/photo2.jpg',
        description: 'Foto adicional con mejor angulo',
        uploadedAt: '2026-01-25T16:00:00Z',
      },
    ],
    timeline: [
      {
        id: 'evt_001',
        type: 'created',
        actor: 'agent',
        description: 'Disputa iniciada por el agente',
        timestamp: '2026-01-25T15:00:00Z',
      },
      {
        id: 'evt_002',
        type: 'evidence_submitted',
        actor: 'worker',
        description: 'Worker envio evidencia adicional',
        timestamp: '2026-01-25T16:00:00Z',
      },
      {
        id: 'evt_003',
        type: 'vote_cast',
        actor: 'validator',
        actorAddress: '0xval1...1234',
        description: 'Voto a favor del worker',
        timestamp: '2026-01-25T17:00:00Z',
      },
    ],
    votes: [
      {
        validatorAddress: '0xval1...1234',
        validatorName: 'Validator Alpha',
        side: 'worker',
        stakeAmount: 10,
        timestamp: '2026-01-25T17:00:00Z',
        reason: 'La foto muestra claramente el producto',
      },
    ],
    votesForWorker: 1,
    votesForAgent: 0,
    requiredVotes: 3,
    resolutionDeadline: '2026-01-27T15:00:00Z',
    createdAt: '2026-01-25T15:00:00Z',
    canAppeal: false,
    appealCostUsd: 25.00,
    gnosisSafeAddress: '0xsafe...multisig',
  },
  {
    id: 'disp_002',
    task: {
      id: 'task_002',
      title: 'Encuesta de satisfaccion en restaurante',
      bountyUsd: 8.00,
      category: 'knowledge_access',
      instructions: 'Realizar encuesta de 5 preguntas a cliente del restaurante',
      deadline: '2026-01-25T20:00:00Z',
    },
    status: 'open',
    reason: 'Respuestas inconsistentes, posible fabricacion',
    agentRejectionReason: 'Las respuestas de la encuesta contienen contradicciones que sugieren que no fue realizada en persona.',
    workerAddress: '0x9876...5432',
    workerName: 'Maria L.',
    agentAddress: '0xabcd...efgh',
    agentName: 'AgentBot #42',
    workerSubmission: {
      id: 'sub_002',
      evidence: [
        {
          type: 'document',
          url: 'https://example.com/evidence/survey.pdf',
          description: 'Formulario de encuesta completado',
          uploadedAt: '2026-01-25T12:00:00Z',
        },
      ],
      notes: 'Encuesta realizada a cliente en mesa 5',
      submittedAt: '2026-01-25T12:00:00Z',
    },
    agentEvidence: [],
    workerEvidence: [],
    timeline: [
      {
        id: 'evt_004',
        type: 'created',
        actor: 'agent',
        description: 'Disputa iniciada por el agente',
        timestamp: '2026-01-25T13:00:00Z',
      },
    ],
    votes: [],
    votesForWorker: 0,
    votesForAgent: 0,
    requiredVotes: 3,
    resolutionDeadline: '2026-01-28T13:00:00Z',
    createdAt: '2026-01-25T13:00:00Z',
    canAppeal: false,
    appealCostUsd: 20.00,
    gnosisSafeAddress: '0xsafe...multisig',
  },
]

const REQUIRED_STAKE_USD = 5.00

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatTimeRemaining(deadlineStr: string): string {
  const deadline = new Date(deadlineStr)
  const now = new Date()
  const diffMs = deadline.getTime() - now.getTime()

  if (diffMs <= 0) return 'Expirado'

  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

  if (hours > 24) {
    const days = Math.floor(hours / 24)
    return `${days}d ${hours % 24}h`
  }

  return `${hours}h ${minutes}m`
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function truncateAddress(address: string): string {
  if (address.length <= 13) return address
  return `${address.slice(0, 6)}...${address.slice(-4)}`
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

// Status Badge
function StatusBadge({ status }: { status: Dispute['status'] }) {
  const config = {
    open: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Abierta' },
    voting: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'En Votacion' },
    escalated: { bg: 'bg-red-100', text: 'text-red-800', label: 'Escalada' },
    resolved: { bg: 'bg-green-100', text: 'text-green-800', label: 'Resuelta' },
    appealed: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Apelada' },
  }

  const { bg, text, label } = config[status]

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${bg} ${text}`}>
      {label}
    </span>
  )
}

// Vote Progress Bar
function VoteProgressBar({
  votesForWorker,
  votesForAgent,
  requiredVotes,
}: {
  votesForWorker: number
  votesForAgent: number
  requiredVotes: number
}) {
  const totalVotes = votesForWorker + votesForAgent
  const workerPercent = totalVotes > 0 ? (votesForWorker / totalVotes) * 100 : 50
  const agentPercent = totalVotes > 0 ? (votesForAgent / totalVotes) * 100 : 50

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs">
        <span className="text-blue-600 font-medium">Worker: {votesForWorker}</span>
        <span className="text-gray-500">{totalVotes}/{requiredVotes} votos</span>
        <span className="text-red-600 font-medium">Agente: {votesForAgent}</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
        <div
          className="bg-blue-500 transition-all duration-300"
          style={{ width: `${workerPercent}%` }}
        />
        <div
          className="bg-red-500 transition-all duration-300"
          style={{ width: `${agentPercent}%` }}
        />
      </div>
    </div>
  )
}

// Dispute List Item
function DisputeListItem({
  dispute,
  onClick,
}: {
  dispute: Dispute
  onClick: () => void
}) {
  const timeRemaining = formatTimeRemaining(dispute.resolutionDeadline)
  const isUrgent = timeRemaining.includes('h') && !timeRemaining.includes('d')

  return (
    <button
      onClick={onClick}
      className="w-full bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all text-left"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-gray-900 truncate">
              {dispute.task.title}
            </h3>
            <StatusBadge status={dispute.status} />
          </div>
          <p className="text-sm text-gray-500 line-clamp-2 mb-2">
            {dispute.reason}
          </p>
          <VoteProgressBar
            votesForWorker={dispute.votesForWorker}
            votesForAgent={dispute.votesForAgent}
            requiredVotes={dispute.requiredVotes}
          />
        </div>

        <div className="text-right flex-shrink-0">
          <p className="text-lg font-semibold text-gray-900">
            {formatCurrency(dispute.task.bountyUsd)}
          </p>
          <p className={`text-xs mt-1 flex items-center gap-1 justify-end ${
            isUrgent ? 'text-red-600' : 'text-gray-500'
          }`}>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {timeRemaining}
          </p>
        </div>
      </div>
    </button>
  )
}

// Evidence Viewer
function EvidenceViewer({
  evidence,
  title,
}: {
  evidence: DisputeEvidence[]
  title: string
}) {
  const [selectedEvidence, setSelectedEvidence] = useState<DisputeEvidence | null>(null)

  if (evidence.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-4 text-center">
        <p className="text-sm text-gray-500">Sin evidencia</p>
      </div>
    )
  }

  const getIcon = (type: DisputeEvidence['type']) => {
    switch (type) {
      case 'photo':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        )
      case 'document':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        )
      case 'video':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        )
      case 'screenshot':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        )
      default:
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        )
    }
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium text-gray-700">{title}</h4>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {evidence.map((item, index) => (
          <button
            key={index}
            onClick={() => setSelectedEvidence(item)}
            className="aspect-square bg-gray-100 rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-500 transition-all relative group"
          >
            {item.type === 'photo' || item.type === 'screenshot' ? (
              <img
                src={item.url}
                alt={item.description || `Evidencia ${index + 1}`}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-gray-400">
                {getIcon(item.type)}
                <span className="text-xs mt-2 capitalize">{item.type}</span>
              </div>
            )}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
              <svg className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
            </div>
          </button>
        ))}
      </div>

      {/* Evidence Modal */}
      {selectedEvidence && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                {selectedEvidence.description || 'Evidencia'}
              </h3>
              <button
                onClick={() => setSelectedEvidence(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 overflow-auto max-h-[70vh]">
              {selectedEvidence.type === 'photo' || selectedEvidence.type === 'screenshot' ? (
                <img
                  src={selectedEvidence.url}
                  alt={selectedEvidence.description}
                  className="w-full rounded-lg"
                />
              ) : selectedEvidence.type === 'video' ? (
                <video
                  src={selectedEvidence.url}
                  controls
                  className="w-full rounded-lg"
                />
              ) : (
                <div className="text-center py-8">
                  <a
                    href={selectedEvidence.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Descargar Documento
                  </a>
                </div>
              )}
              <div className="mt-4 text-sm text-gray-500">
                <p>Subido: {formatDate(selectedEvidence.uploadedAt)}</p>
                {!!selectedEvidence.metadata?.gps && (
                  <p>
                    GPS: {(selectedEvidence.metadata.gps as { lat: number; lng: number }).lat.toFixed(4)},
                    {(selectedEvidence.metadata.gps as { lat: number; lng: number }).lng.toFixed(4)}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Timeline Component
function Timeline({ events }: { events: TimelineEvent[] }) {
  const getEventIcon = (event: TimelineEvent) => {
    switch (event.type) {
      case 'created':
        return (
          <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
        )
      case 'evidence_submitted':
        return (
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        )
      case 'vote_cast':
        return (
          <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
          </div>
        )
      case 'escalated':
        return (
          <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
        )
      case 'resolved':
        return (
          <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )
      case 'appealed':
        return (
          <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
        )
      default:
        return (
          <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
            <div className="w-3 h-3 bg-gray-400 rounded-full" />
          </div>
        )
    }
  }

  return (
    <div className="space-y-4">
      {events.map((event, index) => (
        <div key={event.id} className="flex gap-3">
          <div className="relative">
            {getEventIcon(event)}
            {index < events.length - 1 && (
              <div className="absolute top-8 left-1/2 w-0.5 h-full -translate-x-1/2 bg-gray-200" />
            )}
          </div>
          <div className="flex-1 pb-4">
            <p className="font-medium text-gray-900">{event.description}</p>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
              <span>{formatDate(event.timestamp)}</span>
              {event.actorAddress && (
                <>
                  <span>-</span>
                  <span className="font-mono">{truncateAddress(event.actorAddress)}</span>
                </>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// Voting Interface
function VotingInterface({
  dispute,
  userAddress: _userAddress,
  requiredStake,
  onVote,
  hasVoted,
}: {
  dispute: Dispute
  userAddress: string
  requiredStake: number
  onVote: (side: 'worker' | 'agent', reason: string) => void
  hasVoted: boolean
}) {
  const [selectedSide, setSelectedSide] = useState<'worker' | 'agent' | null>(null)
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmitVote = async () => {
    if (!selectedSide) return

    setIsSubmitting(true)
    try {
      await onVote(selectedSide, reason)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (hasVoted) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-green-700">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="font-medium">Ya has votado en esta disputa</span>
        </div>
      </div>
    )
  }

  if (dispute.status !== 'voting' && dispute.status !== 'open') {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
        <p className="text-gray-500">La votacion no esta activa para esta disputa</p>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Votar en Disputa</h3>
        <span className="text-sm text-gray-500">
          Stake requerido: <span className="font-medium text-gray-900">{formatCurrency(requiredStake)}</span>
        </span>
      </div>

      {/* Vote Options */}
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => setSelectedSide('worker')}
          className={`p-4 rounded-lg border-2 transition-all ${
            selectedSide === 'worker'
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-blue-300'
          }`}
        >
          <div className="flex flex-col items-center gap-2">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              selectedSide === 'worker' ? 'bg-blue-500 text-white' : 'bg-blue-100 text-blue-600'
            }`}>
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <span className="font-medium text-gray-900">Votar por Worker</span>
            <span className="text-xs text-gray-500">{dispute.workerName || truncateAddress(dispute.workerAddress)}</span>
          </div>
        </button>

        <button
          onClick={() => setSelectedSide('agent')}
          className={`p-4 rounded-lg border-2 transition-all ${
            selectedSide === 'agent'
              ? 'border-red-500 bg-red-50'
              : 'border-gray-200 hover:border-red-300'
          }`}
        >
          <div className="flex flex-col items-center gap-2">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              selectedSide === 'agent' ? 'bg-red-500 text-white' : 'bg-red-100 text-red-600'
            }`}>
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="font-medium text-gray-900">Votar por Agente</span>
            <span className="text-xs text-gray-500">{dispute.agentName || truncateAddress(dispute.agentAddress)}</span>
          </div>
        </button>
      </div>

      {/* Reason Input */}
      {selectedSide && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Razon del voto (opcional)
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explica brevemente por que votas asi..."
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
          />
        </div>
      )}

      {/* Submit Button */}
      <button
        onClick={handleSubmitVote}
        disabled={!selectedSide || isSubmitting}
        className={`w-full py-3 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
          selectedSide === 'worker'
            ? 'bg-blue-600 hover:bg-blue-700 text-white'
            : selectedSide === 'agent'
            ? 'bg-red-600 hover:bg-red-700 text-white'
            : 'bg-gray-200 text-gray-500'
        }`}
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Procesando voto...
          </span>
        ) : selectedSide ? (
          `Confirmar Voto + Stake ${formatCurrency(requiredStake)}`
        ) : (
          'Selecciona una opcion'
        )}
      </button>

      {/* Warning */}
      <p className="text-xs text-gray-500 text-center">
        Al votar, depositas {formatCurrency(requiredStake)} USDC. Si tu voto coincide con la resolucion final, recuperas tu stake + una parte del stake perdedor.
      </p>
    </div>
  )
}

// Appeal Section
function AppealSection({
  dispute,
  onAppeal,
}: {
  dispute: Dispute
  onAppeal: () => void
}) {
  const [showConfirm, setShowConfirm] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!dispute.canAppeal || dispute.status === 'appealed' || dispute.status === 'escalated') {
    if (dispute.status === 'escalated') {
      return (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div>
              <h4 className="font-medium text-red-900">Disputa Escalada a Gnosis Safe</h4>
              <p className="text-sm text-red-700 mt-1">
                Esta disputa fue escalada al multisig para resolucion manual.
              </p>
              {dispute.gnosisSafeAddress && (
                <a
                  href={`https://app.safe.global/transactions/queue?safe=base:${dispute.gnosisSafeAddress}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-red-600 hover:text-red-700 mt-2"
                >
                  <span>Ver en Gnosis Safe</span>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
            </div>
          </div>
        </div>
      )
    }

    if (dispute.status === 'appealed') {
      return (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-purple-700">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span className="font-medium">Apelacion en proceso</span>
          </div>
        </div>
      )
    }

    return null
  }

  const handleAppeal = async () => {
    setIsSubmitting(true)
    try {
      await onAppeal()
    } finally {
      setIsSubmitting(false)
      setShowConfirm(false)
    }
  }

  return (
    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div className="flex-1">
          <h4 className="font-medium text-orange-900">Apelar Resolucion</h4>
          <p className="text-sm text-orange-700 mt-1">
            Si no estas de acuerdo con la resolucion, puedes apelar. La disputa sera escalada a un multisig de Gnosis Safe para revision manual.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-orange-200">
        <div>
          <p className="text-sm text-gray-500">Costo de apelacion</p>
          <p className="text-lg font-semibold text-gray-900">{formatCurrency(dispute.appealCostUsd)}</p>
        </div>
        {dispute.appealDeadline && (
          <div className="text-right">
            <p className="text-sm text-gray-500">Tiempo restante</p>
            <p className="text-lg font-semibold text-orange-600">
              {formatTimeRemaining(dispute.appealDeadline)}
            </p>
          </div>
        )}
      </div>

      {!showConfirm ? (
        <button
          onClick={() => setShowConfirm(true)}
          className="w-full py-3 bg-orange-600 text-white font-medium rounded-lg hover:bg-orange-700 transition-colors"
        >
          Iniciar Apelacion
        </button>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-orange-800 font-medium">
            Confirmar apelacion? Se cobrara {formatCurrency(dispute.appealCostUsd)} de tu wallet.
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setShowConfirm(false)}
              disabled={isSubmitting}
              className="flex-1 py-2 border border-orange-300 text-orange-700 font-medium rounded-lg hover:bg-orange-50 transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              onClick={handleAppeal}
              disabled={isSubmitting}
              className="flex-1 py-2 bg-orange-600 text-white font-medium rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Procesando...
                </span>
              ) : (
                'Confirmar Apelacion'
              )}
            </button>
          </div>
        </div>
      )}

      <p className="text-xs text-orange-600 text-center">
        Las apelaciones son revisadas por el Gnosis Safe multisig de Execution Market ({truncateAddress(dispute.gnosisSafeAddress || '0x...')})
      </p>
    </div>
  )
}

// Dispute Detail View
function DisputeDetail({
  dispute,
  userAddress,
  isValidator,
  onBack,
  onVote,
  onAppeal,
}: {
  dispute: Dispute
  userAddress: string
  isValidator: boolean
  onBack: () => void
  onVote: (side: 'worker' | 'agent', reason: string) => void
  onAppeal: () => void
}) {
  const [activeTab, setActiveTab] = useState<'evidence' | 'timeline' | 'votes'>('evidence')

  const hasVoted = useMemo(() => {
    return dispute.votes.some((v) => v.validatorAddress === userAddress)
  }, [dispute.votes, userAddress])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-gray-900">
              Detalle de Disputa
            </h1>
            <StatusBadge status={dispute.status} />
          </div>
          <p className="text-sm text-gray-500">{dispute.task.title}</p>
        </div>
      </div>

      {/* Summary Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-sm text-gray-500">Bounty</p>
            <p className="text-lg font-semibold text-gray-900">
              {formatCurrency(dispute.task.bountyUsd)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Tiempo Restante</p>
            <p className="text-lg font-semibold text-orange-600">
              {formatTimeRemaining(dispute.resolutionDeadline)}
            </p>
          </div>
        </div>
        <VoteProgressBar
          votesForWorker={dispute.votesForWorker}
          votesForAgent={dispute.votesForAgent}
          requiredVotes={dispute.requiredVotes}
        />
      </div>

      {/* Rejection Reason */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="font-medium text-red-900 mb-2">Razon de Rechazo del Agente</h3>
        <p className="text-red-700">{dispute.agentRejectionReason}</p>
      </div>

      {/* Worker Submission */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="font-medium text-gray-900 mb-3">Submission del Worker</h3>
        <div className="space-y-3">
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-700">{dispute.workerSubmission.notes}</p>
            <p className="text-xs text-gray-500 mt-2">
              Enviado: {formatDate(dispute.workerSubmission.submittedAt)}
            </p>
          </div>
          <EvidenceViewer
            evidence={dispute.workerSubmission.evidence}
            title="Evidencia Original"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {(['evidence', 'timeline', 'votes'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'evidence' && 'Evidencia'}
              {tab === 'timeline' && 'Timeline'}
              {tab === 'votes' && `Votos (${dispute.votes.length})`}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'evidence' && (
        <div className="space-y-6">
          <EvidenceViewer
            evidence={dispute.agentEvidence}
            title="Evidencia del Agente"
          />
          <EvidenceViewer
            evidence={dispute.workerEvidence}
            title="Evidencia Adicional del Worker"
          />
        </div>
      )}

      {activeTab === 'timeline' && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <Timeline events={dispute.timeline} />
        </div>
      )}

      {activeTab === 'votes' && (
        <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">
          {dispute.votes.length === 0 ? (
            <div className="p-8 text-center">
              <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="text-gray-500">Aun no hay votos</p>
            </div>
          ) : (
            dispute.votes.map((vote, index) => (
              <div key={index} className="p-4 flex items-start gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  vote.side === 'worker' ? 'bg-blue-100' : 'bg-red-100'
                }`}>
                  <span className={`text-sm font-medium ${
                    vote.side === 'worker' ? 'text-blue-600' : 'text-red-600'
                  }`}>
                    {vote.side === 'worker' ? 'W' : 'A'}
                  </span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-gray-900">
                      {vote.validatorName || truncateAddress(vote.validatorAddress)}
                    </p>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                      vote.side === 'worker'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {vote.side === 'worker' ? 'Worker' : 'Agente'}
                    </span>
                  </div>
                  {vote.reason && (
                    <p className="text-sm text-gray-600 mt-1">{vote.reason}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    Stake: {formatCurrency(vote.stakeAmount)} - {formatDate(vote.timestamp)}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Voting Interface (for validators) */}
      {isValidator && (
        <VotingInterface
          dispute={dispute}
          userAddress={userAddress}
          requiredStake={REQUIRED_STAKE_USD}
          onVote={onVote}
          hasVoted={hasVoted}
        />
      )}

      {/* Appeal Section */}
      <AppealSection dispute={dispute} onAppeal={onAppeal} />
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function Disputes({
  userAddress,
  userRole: _userRole,
  isValidator = false,
  validatorStake = 0,
  onBack,
}: DisputesPageProps) {
  const [selectedDisputeId, setSelectedDisputeId] = useState<string | null>(null)
  const [filter, setFilter] = useState<Dispute['status'] | 'all'>('all')

  // In production, replace with actual data fetching hook
  const [disputes, setDisputes] = useState<Dispute[]>(MOCK_DISPUTES)
  const [loading] = useState(false)

  // Filter disputes
  const filteredDisputes = useMemo(() => {
    if (filter === 'all') return disputes
    return disputes.filter((d) => d.status === filter)
  }, [disputes, filter])

  // Get selected dispute
  const selectedDispute = useMemo(() => {
    return disputes.find((d) => d.id === selectedDisputeId) || null
  }, [disputes, selectedDisputeId])

  // Handlers
  const handleDisputeClick = useCallback((disputeId: string) => {
    setSelectedDisputeId(disputeId)
  }, [])

  const handleBack = useCallback(() => {
    if (selectedDisputeId) {
      setSelectedDisputeId(null)
    } else {
      onBack?.()
    }
  }, [selectedDisputeId, onBack])

  const handleVote = useCallback(async (side: 'worker' | 'agent', reason: string) => {
    if (!selectedDisputeId) return

    // In production, call actual voting contract/API
    console.log('Vote submitted:', { disputeId: selectedDisputeId, side, reason })

    // Mock update
    setDisputes((prev) =>
      prev.map((d) => {
        if (d.id !== selectedDisputeId) return d
        return {
          ...d,
          votes: [
            ...d.votes,
            {
              validatorAddress: userAddress,
              side,
              stakeAmount: REQUIRED_STAKE_USD,
              timestamp: new Date().toISOString(),
              reason,
            },
          ],
          votesForWorker: side === 'worker' ? d.votesForWorker + 1 : d.votesForWorker,
          votesForAgent: side === 'agent' ? d.votesForAgent + 1 : d.votesForAgent,
          status: 'voting' as const,
        }
      })
    )
  }, [selectedDisputeId, userAddress])

  const handleAppeal = useCallback(async () => {
    if (!selectedDisputeId) return

    // In production, call actual appeal contract/API
    console.log('Appeal submitted:', { disputeId: selectedDisputeId })

    // Mock update
    setDisputes((prev) =>
      prev.map((d) => {
        if (d.id !== selectedDisputeId) return d
        return {
          ...d,
          status: 'escalated' as const,
          timeline: [
            ...d.timeline,
            {
              id: `evt_${Date.now()}`,
              type: 'escalated' as const,
              actor: 'system' as const,
              description: 'Disputa escalada a Gnosis Safe multisig',
              timestamp: new Date().toISOString(),
            },
          ],
        }
      })
    )
  }, [selectedDisputeId])

  // Detail view
  if (selectedDispute) {
    return (
      <DisputeDetail
        dispute={selectedDispute}
        userAddress={userAddress}
        isValidator={isValidator}
        onBack={handleBack}
        onVote={handleVote}
        onAppeal={handleAppeal}
      />
    )
  }

  // List view
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        {onBack && (
          <button
            onClick={handleBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}
        <div className="flex-1">
          <h1 className="text-xl font-semibold text-gray-900">Disputas</h1>
          <p className="text-sm text-gray-500">
            {filteredDisputes.length} disputa{filteredDisputes.length !== 1 && 's'} activa{filteredDisputes.length !== 1 && 's'}
          </p>
        </div>
        {isValidator && (
          <div className="text-right">
            <p className="text-xs text-gray-500">Tu stake</p>
            <p className="font-semibold text-gray-900">{formatCurrency(validatorStake)}</p>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {(['all', 'open', 'voting', 'escalated', 'resolved'] as const).map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
              filter === status
                ? 'bg-gray-800 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {status === 'all' && 'Todas'}
            {status === 'open' && 'Abiertas'}
            {status === 'voting' && 'En Votacion'}
            {status === 'escalated' && 'Escaladas'}
            {status === 'resolved' && 'Resueltas'}
          </button>
        ))}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Empty state */}
      {!loading && filteredDisputes.length === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="font-medium text-gray-900">Sin Disputas</h3>
          <p className="text-sm text-gray-500 mt-1">
            {filter === 'all'
              ? 'No hay disputas en este momento'
              : `No hay disputas con estado "${filter}"`}
          </p>
        </div>
      )}

      {/* Disputes list */}
      {!loading && filteredDisputes.length > 0 && (
        <div className="space-y-3">
          {filteredDisputes.map((dispute) => (
            <DisputeListItem
              key={dispute.id}
              dispute={dispute}
              onClick={() => handleDisputeClick(dispute.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default Disputes
