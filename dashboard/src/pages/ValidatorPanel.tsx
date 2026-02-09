/**
 * ValidatorPanel Page (NOW-035, NOW-126)
 *
 * Interface for validators to review disputes and vote.
 * Features:
 * - Queue of disputes pending validation
 * - Voting interface (approve/reject with reason)
 * - Evidence viewer (photos, GPS, timestamps)
 * - Validator stats (accuracy rate, earnings)
 * - Stake management
 */

import { useState, useMemo, useCallback } from 'react'

// ============================================================================
// TYPES
// ============================================================================

export interface Evidence {
  id: string
  type: 'photo' | 'document' | 'video' | 'screenshot' | 'text'
  url: string
  description?: string
  uploadedAt: string
  metadata?: {
    gps?: { lat: number; lng: number }
    deviceInfo?: string
    originalFilename?: string
    fileSize?: number
  }
}

export interface Vote {
  validatorId: string
  validatorName?: string
  validatorAddress: string
  outcome: 'approve_worker' | 'approve_agent' | 'split'
  reason: string
  votedAt: string
  stakeAmount: number
}

export interface Dispute {
  id: string
  taskId: string
  taskTitle: string
  taskCategory: string
  bountyUsd: number
  workerEvidence: Evidence[]
  agentEvidence: Evidence[]
  agentClaim: string
  workerClaim: string
  workerAddress: string
  workerName?: string
  agentAddress: string
  agentName?: string
  createdAt: string
  deadline: string
  votes: Vote[]
  requiredVotes: number
  status: 'pending' | 'voting' | 'resolved' | 'escalated'
}

export interface ValidatorStats {
  totalVotes: number
  correctVotes: number
  accuracyRate: number
  totalEarnings: number
  pendingEarnings: number
  currentStake: number
  availableBalance: number
  disputesValidated: number
  averageResponseTime: number // in hours
  streak: number // consecutive correct votes
}

export interface ValidatorPanelProps {
  validatorAddress: string
  validatorName?: string
  onBack?: () => void
}

// ============================================================================
// CONSTANTS
// ============================================================================

const MIN_STAKE_USD = 5.0
const VOTE_REWARD_PERCENT = 10 // 10% of losing side's stake

// ============================================================================
// MOCK DATA
// ============================================================================

const MOCK_VALIDATOR_STATS: ValidatorStats = {
  totalVotes: 47,
  correctVotes: 43,
  accuracyRate: 91.5,
  totalEarnings: 234.50,
  pendingEarnings: 15.00,
  currentStake: 50.00,
  availableBalance: 125.00,
  disputesValidated: 47,
  averageResponseTime: 2.3,
  streak: 8,
}

const MOCK_DISPUTES: Dispute[] = [
  {
    id: 'disp_v001',
    taskId: 'task_101',
    taskTitle: 'Verificar precio de producto en supermercado',
    taskCategory: 'physical_presence',
    bountyUsd: 12.00,
    workerEvidence: [
      {
        id: 'ev_001',
        type: 'photo',
        url: 'https://images.unsplash.com/photo-1604719312566-8912e9227c6a?w=800',
        description: 'Foto del producto en estante',
        uploadedAt: '2026-01-25T10:30:00Z',
        metadata: {
          gps: { lat: 4.6097, lng: -74.0817 },
          deviceInfo: 'iPhone 14 Pro',
        },
      },
      {
        id: 'ev_002',
        type: 'photo',
        url: 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800',
        description: 'Etiqueta de precio',
        uploadedAt: '2026-01-25T10:31:00Z',
        metadata: {
          gps: { lat: 4.6097, lng: -74.0817 },
        },
      },
    ],
    agentEvidence: [
      {
        id: 'ev_003',
        type: 'screenshot',
        url: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800',
        description: 'Analisis de imagen mostrando discrepancia',
        uploadedAt: '2026-01-25T11:00:00Z',
      },
    ],
    agentClaim: 'La foto del precio no corresponde al producto solicitado. El codigo de barras visible no coincide con el SKU requerido.',
    workerClaim: 'El producto es correcto, solo cambiaron el empaque recientemente. El precio es el solicitado.',
    workerAddress: '0x1234...5678',
    workerName: 'Carlos M.',
    agentAddress: '0xagent...1234',
    agentName: 'VerifyBot #12',
    createdAt: '2026-01-25T11:00:00Z',
    deadline: '2026-01-27T11:00:00Z',
    votes: [
      {
        validatorId: 'val_001',
        validatorName: 'Validator Alpha',
        validatorAddress: '0xval1...aaaa',
        outcome: 'approve_worker',
        reason: 'El empaque nuevo es visible en la foto, producto correcto',
        votedAt: '2026-01-25T14:00:00Z',
        stakeAmount: 5.00,
      },
    ],
    requiredVotes: 3,
    status: 'voting',
  },
  {
    id: 'disp_v002',
    taskId: 'task_102',
    taskTitle: 'Encuesta de satisfaccion en restaurante',
    taskCategory: 'knowledge_access',
    bountyUsd: 8.00,
    workerEvidence: [
      {
        id: 'ev_004',
        type: 'document',
        url: 'https://example.com/survey.pdf',
        description: 'Formulario de encuesta completado',
        uploadedAt: '2026-01-24T15:00:00Z',
      },
      {
        id: 'ev_005',
        type: 'photo',
        url: 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800',
        description: 'Foto del restaurante',
        uploadedAt: '2026-01-24T15:05:00Z',
        metadata: {
          gps: { lat: 4.6486, lng: -74.0628 },
        },
      },
    ],
    agentEvidence: [],
    agentClaim: 'Las respuestas de la encuesta son inconsistentes. Pregunta 3 dice "excelente servicio" pero pregunta 7 indica "no volveria".',
    workerClaim: 'La encuesta refleja la opinion real del cliente. Le gusto la comida pero tuvo problemas con el cobro.',
    workerAddress: '0x9876...5432',
    workerName: 'Maria L.',
    agentAddress: '0xagent...5678',
    agentName: 'SurveyBot #5',
    createdAt: '2026-01-24T16:00:00Z',
    deadline: '2026-01-26T16:00:00Z',
    votes: [],
    requiredVotes: 3,
    status: 'pending',
  },
  {
    id: 'disp_v003',
    taskId: 'task_103',
    taskTitle: 'Verificar horario de atencion de farmacia',
    taskCategory: 'physical_presence',
    bountyUsd: 5.00,
    workerEvidence: [
      {
        id: 'ev_006',
        type: 'photo',
        url: 'https://images.unsplash.com/photo-1576602976047-174e57a47881?w=800',
        description: 'Letrero de horarios en la puerta',
        uploadedAt: '2026-01-25T09:00:00Z',
        metadata: {
          gps: { lat: 4.5981, lng: -74.0758 },
          deviceInfo: 'Samsung Galaxy S23',
        },
      },
    ],
    agentEvidence: [
      {
        id: 'ev_007',
        type: 'screenshot',
        url: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800',
        description: 'GPS muestra ubicacion diferente a la farmacia',
        uploadedAt: '2026-01-25T10:00:00Z',
      },
    ],
    agentClaim: 'La ubicacion GPS de la foto no corresponde a la direccion de la farmacia solicitada.',
    workerClaim: 'Es la farmacia correcta. El GPS puede tener variacion de algunos metros en interiores.',
    workerAddress: '0xaaaa...bbbb',
    workerName: 'Juan P.',
    agentAddress: '0xagent...9012',
    agentName: 'LocationBot #3',
    createdAt: '2026-01-25T10:00:00Z',
    deadline: '2026-01-27T10:00:00Z',
    votes: [
      {
        validatorId: 'val_002',
        validatorName: 'Validator Beta',
        validatorAddress: '0xval2...bbbb',
        outcome: 'approve_agent',
        reason: 'La diferencia de GPS es de mas de 200m, no es variacion normal',
        votedAt: '2026-01-25T12:00:00Z',
        stakeAmount: 5.00,
      },
      {
        validatorId: 'val_003',
        validatorName: 'Validator Gamma',
        validatorAddress: '0xval3...cccc',
        outcome: 'approve_worker',
        reason: 'El letrero muestra el nombre correcto de la farmacia',
        votedAt: '2026-01-25T13:00:00Z',
        stakeAmount: 5.00,
      },
    ],
    requiredVotes: 3,
    status: 'voting',
  },
]

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

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

function truncateAddress(address: string): string {
  if (address.length <= 13) return address
  return `${address.slice(0, 6)}...${address.slice(-4)}`
}

function getVoteCounts(votes: Vote[]): { worker: number; agent: number; split: number } {
  return votes.reduce(
    (acc, vote) => {
      if (vote.outcome === 'approve_worker') acc.worker++
      else if (vote.outcome === 'approve_agent') acc.agent++
      else acc.split++
      return acc
    },
    { worker: 0, agent: 0, split: 0 }
  )
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

/**
 * ValidatorStatsCard - Shows validator performance metrics
 */
function ValidatorStatsCard({ stats }: { stats: ValidatorStats }) {
  return (
    <div className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-xl shadow-lg p-5 text-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-indigo-100 text-sm font-medium">Mis Estadisticas de Validador</h3>
        <div className="flex items-center gap-1">
          <svg className="w-4 h-4 text-yellow-300" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          <span className="text-sm font-medium">{stats.streak} racha</span>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-indigo-200 text-xs mb-1">Precision</div>
          <div className="text-2xl font-bold">{stats.accuracyRate.toFixed(1)}%</div>
          <div className="text-xs text-indigo-200">
            {stats.correctVotes}/{stats.totalVotes} correctos
          </div>
        </div>
        <div>
          <div className="text-indigo-200 text-xs mb-1">Ganancias Totales</div>
          <div className="text-2xl font-bold">{formatCurrency(stats.totalEarnings)}</div>
          {stats.pendingEarnings > 0 && (
            <div className="text-xs text-indigo-200">
              +{formatCurrency(stats.pendingEarnings)} pendiente
            </div>
          )}
        </div>
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-3 gap-3 py-3 border-t border-indigo-400/30">
        <div className="text-center">
          <div className="text-xs text-indigo-200 mb-0.5">Disputas</div>
          <div className="text-lg font-semibold">{stats.disputesValidated}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-indigo-200 mb-0.5">Tiempo Resp.</div>
          <div className="text-lg font-semibold">{stats.averageResponseTime.toFixed(1)}h</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-indigo-200 mb-0.5">Mi Stake</div>
          <div className="text-lg font-semibold">{formatCurrency(stats.currentStake)}</div>
        </div>
      </div>
    </div>
  )
}

/**
 * StakeManagementCard - Manage validator stake
 */
function StakeManagementCard({
  stats,
  onDeposit,
  onWithdraw,
}: {
  stats: ValidatorStats
  onDeposit: (amount: number) => void
  onWithdraw: (amount: number) => void
}) {
  const [showDepositModal, setShowDepositModal] = useState(false)
  const [showWithdrawModal, setShowWithdrawModal] = useState(false)
  const [amount, setAmount] = useState('')

  const handleDeposit = () => {
    const value = parseFloat(amount)
    if (value > 0) {
      onDeposit(value)
      setAmount('')
      setShowDepositModal(false)
    }
  }

  const handleWithdraw = () => {
    const value = parseFloat(amount)
    if (value > 0 && value <= stats.currentStake) {
      onWithdraw(value)
      setAmount('')
      setShowWithdrawModal(false)
    }
  }

  return (
    <>
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-4">Gestion de Stake</h3>

        {/* Balance Display */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-500 mb-1">Stake Actual</div>
            <div className="text-xl font-bold text-gray-900">
              {formatCurrency(stats.currentStake)}
            </div>
          </div>
          <div className="p-3 bg-green-50 rounded-lg">
            <div className="text-xs text-gray-500 mb-1">Balance Disponible</div>
            <div className="text-xl font-bold text-green-600">
              {formatCurrency(stats.availableBalance)}
            </div>
          </div>
        </div>

        {/* Stake Info */}
        <div className="p-3 bg-blue-50 rounded-lg mb-4">
          <div className="flex items-start gap-2">
            <svg className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div className="text-xs text-blue-800">
              <p className="font-medium">Stake minimo por voto: {formatCurrency(MIN_STAKE_USD)}</p>
              <p className="mt-1">Si votas correctamente, ganas el {VOTE_REWARD_PERCENT}% del stake perdedor.</p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setShowDepositModal(true)}
            className="flex-1 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Depositar
          </button>
          <button
            onClick={() => setShowWithdrawModal(true)}
            disabled={stats.currentStake <= 0}
            className={`flex-1 py-2.5 font-medium rounded-lg transition-colors ${
              stats.currentStake > 0
                ? 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Retirar
          </button>
        </div>
      </div>

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-sm w-full p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Depositar Stake</h3>
            <div className="mb-4">
              <label className="block text-sm text-gray-600 mb-2">Cantidad (USD)</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                min="0"
                step="0.01"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              />
              <p className="text-xs text-gray-500 mt-2">
                Balance disponible: {formatCurrency(stats.availableBalance)}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowDepositModal(false)}
                className="flex-1 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleDeposit}
                disabled={!amount || parseFloat(amount) <= 0}
                className="flex-1 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Depositar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Withdraw Modal */}
      {showWithdrawModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-sm w-full p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Retirar Stake</h3>
            <div className="mb-4">
              <label className="block text-sm text-gray-600 mb-2">Cantidad (USD)</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                min="0"
                max={stats.currentStake}
                step="0.01"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              />
              <p className="text-xs text-gray-500 mt-2">
                Stake actual: {formatCurrency(stats.currentStake)}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowWithdrawModal(false)}
                className="flex-1 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleWithdraw}
                disabled={!amount || parseFloat(amount) <= 0 || parseFloat(amount) > stats.currentStake}
                className="flex-1 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Retirar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

/**
 * DisputeQueueItem - Single dispute in the queue
 */
function DisputeQueueItem({
  dispute,
  onClick,
  hasVoted,
}: {
  dispute: Dispute
  onClick: () => void
  hasVoted: boolean
}) {
  const timeRemaining = formatTimeRemaining(dispute.deadline)
  const isUrgent = timeRemaining.includes('h') && !timeRemaining.includes('d')
  const voteCounts = getVoteCounts(dispute.votes)

  return (
    <button
      onClick={onClick}
      className={`w-full text-left bg-white border rounded-lg p-4 hover:shadow-sm transition-all ${
        hasVoted ? 'border-green-200 bg-green-50/30' : 'border-gray-200 hover:border-indigo-300'
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Status indicator */}
        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
          hasVoted ? 'bg-green-100' : isUrgent ? 'bg-red-100' : 'bg-indigo-100'
        }`}>
          {hasVoted ? (
            <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className={`w-5 h-5 ${isUrgent ? 'text-red-600' : 'text-indigo-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
            </svg>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className="font-medium text-gray-900 text-sm line-clamp-1">
              {dispute.taskTitle}
            </h4>
            <span className="text-sm font-semibold text-green-600 flex-shrink-0">
              {formatCurrency(dispute.bountyUsd)}
            </span>
          </div>

          <p className="text-xs text-gray-500 mt-1 line-clamp-2">
            {dispute.agentClaim}
          </p>

          <div className="flex items-center gap-3 mt-2">
            {/* Vote progress */}
            <div className="flex items-center gap-1">
              <span className="text-xs text-blue-600 font-medium">W:{voteCounts.worker}</span>
              <span className="text-xs text-gray-400">/</span>
              <span className="text-xs text-red-600 font-medium">A:{voteCounts.agent}</span>
              <span className="text-xs text-gray-400">
                ({dispute.votes.length}/{dispute.requiredVotes})
              </span>
            </div>

            {/* Time remaining */}
            <div className={`flex items-center gap-1 text-xs ${
              isUrgent ? 'text-red-600' : 'text-gray-500'
            }`}>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {timeRemaining}
            </div>

            {/* Voted badge */}
            {hasVoted && (
              <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                Votado
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  )
}

/**
 * EvidenceViewer - Advanced evidence viewer with photo zoom and GPS map
 */
function EvidenceViewer({
  evidence,
  title,
  side,
}: {
  evidence: Evidence[]
  title: string
  side: 'worker' | 'agent'
}) {
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null)
  const [zoomLevel, setZoomLevel] = useState(1)

  const sideColor = side === 'worker' ? 'blue' : 'red'

  if (evidence.length === 0) {
    return (
      <div className={`bg-${sideColor}-50 rounded-lg p-4`}>
        <h4 className={`text-sm font-medium text-${sideColor}-900 mb-2`}>{title}</h4>
        <p className="text-sm text-gray-500">Sin evidencia</p>
      </div>
    )
  }

  const getIcon = (type: Evidence['type']) => {
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
    <div>
      <h4 className={`text-sm font-medium mb-3 ${
        side === 'worker' ? 'text-blue-900' : 'text-red-900'
      }`}>{title}</h4>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {evidence.map((item) => (
          <button
            key={item.id}
            onClick={() => setSelectedEvidence(item)}
            className="aspect-square bg-gray-100 rounded-lg overflow-hidden hover:ring-2 hover:ring-indigo-500 transition-all relative group"
          >
            {item.type === 'photo' || item.type === 'screenshot' ? (
              <img
                src={item.url}
                alt={item.description || 'Evidencia'}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-gray-400">
                {getIcon(item.type)}
                <span className="text-xs mt-2 capitalize">{item.type}</span>
              </div>
            )}

            {/* GPS indicator */}
            {item.metadata?.gps && (
              <div className="absolute top-2 right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                </svg>
              </div>
            )}

            {/* Hover overlay */}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
              <svg className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
            </div>
          </button>
        ))}
      </div>

      {/* Evidence Detail Modal with Zoom and GPS Map */}
      {selectedEvidence && (
        <div className="fixed inset-0 bg-black/90 z-50 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 bg-black/50">
            <div className="text-white">
              <h3 className="font-semibold">{selectedEvidence.description || 'Evidencia'}</h3>
              <p className="text-sm text-gray-300">{formatDate(selectedEvidence.uploadedAt)}</p>
            </div>
            <div className="flex items-center gap-2">
              {/* Zoom controls */}
              <button
                onClick={() => setZoomLevel(Math.max(0.5, zoomLevel - 0.25))}
                className="p-2 bg-white/20 rounded-lg text-white hover:bg-white/30"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
              </button>
              <span className="text-white text-sm min-w-[50px] text-center">{Math.round(zoomLevel * 100)}%</span>
              <button
                onClick={() => setZoomLevel(Math.min(3, zoomLevel + 0.25))}
                className="p-2 bg-white/20 rounded-lg text-white hover:bg-white/30"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
              <button
                onClick={() => setZoomLevel(1)}
                className="p-2 bg-white/20 rounded-lg text-white hover:bg-white/30 ml-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
              <button
                onClick={() => {
                  setSelectedEvidence(null)
                  setZoomLevel(1)
                }}
                className="p-2 bg-white/20 rounded-lg text-white hover:bg-white/30 ml-4"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto flex items-center justify-center p-4">
            <div
              className="relative transition-transform duration-200"
              style={{ transform: `scale(${zoomLevel})` }}
            >
              {selectedEvidence.type === 'photo' || selectedEvidence.type === 'screenshot' ? (
                <img
                  src={selectedEvidence.url}
                  alt={selectedEvidence.description}
                  className="max-h-[70vh] rounded-lg"
                  draggable={false}
                />
              ) : selectedEvidence.type === 'video' ? (
                <video
                  src={selectedEvidence.url}
                  controls
                  className="max-h-[70vh] rounded-lg"
                />
              ) : (
                <div className="bg-white rounded-lg p-8 text-center">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    {getIcon(selectedEvidence.type)}
                  </div>
                  <p className="text-gray-600 mb-4">{selectedEvidence.type.toUpperCase()}</p>
                  <a
                    href={selectedEvidence.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Descargar
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Metadata Footer with GPS Map */}
          <div className="bg-black/50 p-4">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Metadata */}
                <div className="space-y-2 text-sm text-gray-300">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Subido: {formatDate(selectedEvidence.uploadedAt)}</span>
                  </div>
                  {selectedEvidence.metadata?.deviceInfo && (
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      <span>Dispositivo: {selectedEvidence.metadata.deviceInfo}</span>
                    </div>
                  )}
                  {selectedEvidence.metadata?.gps && (
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                      </svg>
                      <span>
                        GPS: {selectedEvidence.metadata.gps.lat.toFixed(6)}, {selectedEvidence.metadata.gps.lng.toFixed(6)}
                      </span>
                    </div>
                  )}
                </div>

                {/* GPS Map */}
                {selectedEvidence.metadata?.gps && (
                  <div className="rounded-lg overflow-hidden h-32">
                    <iframe
                      title="GPS Location"
                      width="100%"
                      height="100%"
                      frameBorder="0"
                      style={{ border: 0 }}
                      src={`https://www.openstreetmap.org/export/embed.html?bbox=${selectedEvidence.metadata.gps.lng - 0.005}%2C${selectedEvidence.metadata.gps.lat - 0.003}%2C${selectedEvidence.metadata.gps.lng + 0.005}%2C${selectedEvidence.metadata.gps.lat + 0.003}&layer=mapnik&marker=${selectedEvidence.metadata.gps.lat}%2C${selectedEvidence.metadata.gps.lng}`}
                      allowFullScreen
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * VotingInterface - Interface for casting a vote
 */
function VotingInterface({
  dispute: _dispute,
  validatorAddress: _validatorAddress,
  minStake,
  onVote,
  hasVoted,
  existingVote,
}: {
  dispute: Dispute
  validatorAddress: string
  minStake: number
  onVote: (outcome: Vote['outcome'], reason: string) => void
  hasVoted: boolean
  existingVote?: Vote
}) {
  const [selectedOutcome, setSelectedOutcome] = useState<Vote['outcome'] | null>(null)
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmitVote = async () => {
    if (!selectedOutcome) return

    setIsSubmitting(true)
    try {
      await onVote(selectedOutcome, reason)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (hasVoted && existingVote) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <h4 className="font-medium text-green-900">Ya has votado en esta disputa</h4>
            <p className="text-sm text-green-700 mt-1">
              Tu voto: {' '}
              <span className="font-medium">
                {existingVote.outcome === 'approve_worker' ? 'A favor del Worker' :
                 existingVote.outcome === 'approve_agent' ? 'A favor del Agente' : 'Dividir'}
              </span>
            </p>
            {existingVote.reason && (
              <p className="text-sm text-green-600 mt-1 italic">"{existingVote.reason}"</p>
            )}
            <p className="text-xs text-green-500 mt-2">
              Votado: {formatDate(existingVote.votedAt)} - Stake: {formatCurrency(existingVote.stakeAmount)}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Tu Voto</h3>
        <span className="text-sm text-gray-500">
          Stake requerido: <span className="font-medium text-gray-900">{formatCurrency(minStake)}</span>
        </span>
      </div>

      {/* Vote Options */}
      <div className="grid grid-cols-3 gap-3">
        <button
          onClick={() => setSelectedOutcome('approve_worker')}
          className={`p-3 rounded-lg border-2 transition-all ${
            selectedOutcome === 'approve_worker'
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-blue-300'
          }`}
        >
          <div className="flex flex-col items-center gap-2">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              selectedOutcome === 'approve_worker' ? 'bg-blue-500 text-white' : 'bg-blue-100 text-blue-600'
            }`}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <span className="text-xs font-medium text-gray-900">Worker</span>
          </div>
        </button>

        <button
          onClick={() => setSelectedOutcome('split')}
          className={`p-3 rounded-lg border-2 transition-all ${
            selectedOutcome === 'split'
              ? 'border-yellow-500 bg-yellow-50'
              : 'border-gray-200 hover:border-yellow-300'
          }`}
        >
          <div className="flex flex-col items-center gap-2">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              selectedOutcome === 'split' ? 'bg-yellow-500 text-white' : 'bg-yellow-100 text-yellow-600'
            }`}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            </div>
            <span className="text-xs font-medium text-gray-900">Dividir</span>
          </div>
        </button>

        <button
          onClick={() => setSelectedOutcome('approve_agent')}
          className={`p-3 rounded-lg border-2 transition-all ${
            selectedOutcome === 'approve_agent'
              ? 'border-red-500 bg-red-50'
              : 'border-gray-200 hover:border-red-300'
          }`}
        >
          <div className="flex flex-col items-center gap-2">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              selectedOutcome === 'approve_agent' ? 'bg-red-500 text-white' : 'bg-red-100 text-red-600'
            }`}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="text-xs font-medium text-gray-900">Agente</span>
          </div>
        </button>
      </div>

      {/* Reason Input */}
      {selectedOutcome && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Razon del voto <span className="text-gray-400">(recomendado)</span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explica brevemente por que votas asi..."
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none"
          />
        </div>
      )}

      {/* Submit Button */}
      <button
        onClick={handleSubmitVote}
        disabled={!selectedOutcome || isSubmitting}
        className={`w-full py-3 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
          selectedOutcome === 'approve_worker'
            ? 'bg-blue-600 hover:bg-blue-700 text-white'
            : selectedOutcome === 'approve_agent'
            ? 'bg-red-600 hover:bg-red-700 text-white'
            : selectedOutcome === 'split'
            ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
            : 'bg-gray-200 text-gray-500'
        }`}
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Procesando voto...
          </span>
        ) : selectedOutcome ? (
          `Confirmar Voto + Stake ${formatCurrency(minStake)}`
        ) : (
          'Selecciona una opcion'
        )}
      </button>

      {/* Warning */}
      <p className="text-xs text-gray-500 text-center">
        Al votar, depositas {formatCurrency(minStake)} USDC. Si tu voto coincide con la resolucion final, recuperas tu stake + ganancias.
      </p>
    </div>
  )
}

/**
 * DisputeDetail - Full dispute detail view for validators
 */
function DisputeDetail({
  dispute,
  validatorAddress,
  onBack,
  onVote,
}: {
  dispute: Dispute
  validatorAddress: string
  onBack: () => void
  onVote: (outcome: Vote['outcome'], reason: string) => void
}) {
  const [activeTab, setActiveTab] = useState<'evidence' | 'claims' | 'votes'>('evidence')

  const existingVote = useMemo(() => {
    return dispute.votes.find((v) => v.validatorAddress === validatorAddress)
  }, [dispute.votes, validatorAddress])

  const hasVoted = !!existingVote
  const voteCounts = getVoteCounts(dispute.votes)
  const timeRemaining = formatTimeRemaining(dispute.deadline)
  const isUrgent = timeRemaining.includes('h') && !timeRemaining.includes('d')

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
          <h1 className="text-xl font-semibold text-gray-900">
            Revisar Disputa
          </h1>
          <p className="text-sm text-gray-500 line-clamp-1">{dispute.taskTitle}</p>
        </div>
      </div>

      {/* Summary Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-500">Bounty</p>
            <p className="text-lg font-semibold text-green-600">
              {formatCurrency(dispute.bountyUsd)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Votos</p>
            <p className="text-lg font-semibold text-gray-900">
              {dispute.votes.length}/{dispute.requiredVotes}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Tiempo</p>
            <p className={`text-lg font-semibold ${isUrgent ? 'text-red-600' : 'text-gray-900'}`}>
              {timeRemaining}
            </p>
          </div>
        </div>

        {/* Vote Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-blue-600 font-medium">Worker: {voteCounts.worker}</span>
            <span className="text-yellow-600 font-medium">Split: {voteCounts.split}</span>
            <span className="text-red-600 font-medium">Agente: {voteCounts.agent}</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
            {voteCounts.worker > 0 && (
              <div
                className="bg-blue-500 transition-all duration-300"
                style={{ width: `${(voteCounts.worker / dispute.requiredVotes) * 100}%` }}
              />
            )}
            {voteCounts.split > 0 && (
              <div
                className="bg-yellow-500 transition-all duration-300"
                style={{ width: `${(voteCounts.split / dispute.requiredVotes) * 100}%` }}
              />
            )}
            {voteCounts.agent > 0 && (
              <div
                className="bg-red-500 transition-all duration-300"
                style={{ width: `${(voteCounts.agent / dispute.requiredVotes) * 100}%` }}
              />
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {(['evidence', 'claims', 'votes'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'evidence' && 'Evidencia'}
              {tab === 'claims' && 'Argumentos'}
              {tab === 'votes' && `Votos (${dispute.votes.length})`}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'evidence' && (
        <div className="space-y-6">
          <EvidenceViewer
            evidence={dispute.workerEvidence}
            title={`Evidencia del Worker (${dispute.workerName || truncateAddress(dispute.workerAddress)})`}
            side="worker"
          />
          <EvidenceViewer
            evidence={dispute.agentEvidence}
            title={`Evidencia del Agente (${dispute.agentName || truncateAddress(dispute.agentAddress)})`}
            side="agent"
          />
        </div>
      )}

      {activeTab === 'claims' && (
        <div className="space-y-4">
          {/* Agent Claim */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h4 className="font-medium text-red-900">
                Argumento del Agente
              </h4>
            </div>
            <p className="text-red-800">{dispute.agentClaim}</p>
            <p className="text-xs text-red-600 mt-2">
              {dispute.agentName || truncateAddress(dispute.agentAddress)}
            </p>
          </div>

          {/* Worker Claim */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <h4 className="font-medium text-blue-900">
                Respuesta del Worker
              </h4>
            </div>
            <p className="text-blue-800">{dispute.workerClaim}</p>
            <p className="text-xs text-blue-600 mt-2">
              {dispute.workerName || truncateAddress(dispute.workerAddress)}
            </p>
          </div>
        </div>
      )}

      {activeTab === 'votes' && (
        <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">
          {dispute.votes.length === 0 ? (
            <div className="p-8 text-center">
              <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="text-gray-500">Aun no hay votos. Se el primero en votar.</p>
            </div>
          ) : (
            dispute.votes.map((vote, index) => (
              <div key={index} className="p-4 flex items-start gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  vote.outcome === 'approve_worker' ? 'bg-blue-100' :
                  vote.outcome === 'approve_agent' ? 'bg-red-100' : 'bg-yellow-100'
                }`}>
                  <span className={`text-sm font-medium ${
                    vote.outcome === 'approve_worker' ? 'text-blue-600' :
                    vote.outcome === 'approve_agent' ? 'text-red-600' : 'text-yellow-600'
                  }`}>
                    {vote.outcome === 'approve_worker' ? 'W' :
                     vote.outcome === 'approve_agent' ? 'A' : 'S'}
                  </span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-gray-900">
                      {vote.validatorName || truncateAddress(vote.validatorAddress)}
                      {vote.validatorAddress === validatorAddress && (
                        <span className="ml-2 text-xs text-indigo-600">(tu)</span>
                      )}
                    </p>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                      vote.outcome === 'approve_worker' ? 'bg-blue-100 text-blue-700' :
                      vote.outcome === 'approve_agent' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {vote.outcome === 'approve_worker' ? 'Worker' :
                       vote.outcome === 'approve_agent' ? 'Agente' : 'Split'}
                    </span>
                  </div>
                  {vote.reason && (
                    <p className="text-sm text-gray-600 mt-1">{vote.reason}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    Stake: {formatCurrency(vote.stakeAmount)} - {formatDate(vote.votedAt)}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Voting Interface */}
      <VotingInterface
        dispute={dispute}
        validatorAddress={validatorAddress}
        minStake={MIN_STAKE_USD}
        onVote={onVote}
        hasVoted={hasVoted}
        existingVote={existingVote}
      />
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function ValidatorPanel({
  validatorAddress,
  validatorName,
  onBack,
}: ValidatorPanelProps) {
  const [selectedDisputeId, setSelectedDisputeId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'pending' | 'voted'>('all')
  const [stats, setStats] = useState<ValidatorStats>(MOCK_VALIDATOR_STATS)
  const [disputes, setDisputes] = useState<Dispute[]>(MOCK_DISPUTES)

  // Filter disputes
  const filteredDisputes = useMemo(() => {
    if (filter === 'all') return disputes
    if (filter === 'pending') {
      return disputes.filter((d) => !d.votes.some((v) => v.validatorAddress === validatorAddress))
    }
    return disputes.filter((d) => d.votes.some((v) => v.validatorAddress === validatorAddress))
  }, [disputes, filter, validatorAddress])

  // Get selected dispute
  const selectedDispute = useMemo(() => {
    return disputes.find((d) => d.id === selectedDisputeId) || null
  }, [disputes, selectedDisputeId])

  // Check if validator has voted on a dispute
  const hasVotedOn = useCallback((disputeId: string) => {
    const dispute = disputes.find((d) => d.id === disputeId)
    return dispute?.votes.some((v) => v.validatorAddress === validatorAddress) ?? false
  }, [disputes, validatorAddress])

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

  const handleVote = useCallback(async (outcome: Vote['outcome'], reason: string) => {
    if (!selectedDisputeId) return

    // In production, call actual voting contract/API
    console.log('Vote submitted:', { disputeId: selectedDisputeId, outcome, reason })

    // Mock update
    const newVote: Vote = {
      validatorId: `val_${Date.now()}`,
      validatorName: validatorName,
      validatorAddress,
      outcome,
      reason,
      votedAt: new Date().toISOString(),
      stakeAmount: MIN_STAKE_USD,
    }

    setDisputes((prev) =>
      prev.map((d) => {
        if (d.id !== selectedDisputeId) return d
        return {
          ...d,
          votes: [...d.votes, newVote],
          status: 'voting' as const,
        }
      })
    )

    // Update stats
    setStats((prev) => ({
      ...prev,
      totalVotes: prev.totalVotes + 1,
      currentStake: prev.currentStake - MIN_STAKE_USD,
      pendingEarnings: prev.pendingEarnings + MIN_STAKE_USD * (VOTE_REWARD_PERCENT / 100),
    }))
  }, [selectedDisputeId, validatorAddress, validatorName])

  const handleDeposit = useCallback((amount: number) => {
    // In production, call deposit contract
    console.log('Deposit:', amount)
    setStats((prev) => ({
      ...prev,
      currentStake: prev.currentStake + amount,
      availableBalance: prev.availableBalance - amount,
    }))
  }, [])

  const handleWithdraw = useCallback((amount: number) => {
    // In production, call withdraw contract
    console.log('Withdraw:', amount)
    setStats((prev) => ({
      ...prev,
      currentStake: prev.currentStake - amount,
      availableBalance: prev.availableBalance + amount,
    }))
  }, [])

  // Detail view
  if (selectedDispute) {
    return (
      <DisputeDetail
        dispute={selectedDispute}
        validatorAddress={validatorAddress}
        onBack={handleBack}
        onVote={handleVote}
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
          <h1 className="text-xl font-semibold text-gray-900">Panel de Validador</h1>
          <p className="text-sm text-gray-500">
            {filteredDisputes.length} disputa{filteredDisputes.length !== 1 && 's'} pendiente{filteredDisputes.length !== 1 && 's'}
          </p>
        </div>
      </div>

      {/* Stats Card */}
      <ValidatorStatsCard stats={stats} />

      {/* Stake Management */}
      <StakeManagementCard
        stats={stats}
        onDeposit={handleDeposit}
        onWithdraw={handleWithdraw}
      />

      {/* Filters */}
      <div className="flex gap-2">
        {(['all', 'pending', 'voted'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
              filter === f
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {f === 'all' && 'Todas'}
            {f === 'pending' && 'Sin votar'}
            {f === 'voted' && 'Votadas'}
          </button>
        ))}
      </div>

      {/* Dispute Queue */}
      {filteredDisputes.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="font-medium text-gray-900">Sin Disputas</h3>
          <p className="text-sm text-gray-500 mt-1">
            {filter === 'pending'
              ? 'Has votado en todas las disputas disponibles'
              : filter === 'voted'
              ? 'Aun no has votado en ninguna disputa'
              : 'No hay disputas pendientes de validacion'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredDisputes.map((dispute) => (
            <DisputeQueueItem
              key={dispute.id}
              dispute={dispute}
              onClick={() => handleDisputeClick(dispute.id)}
              hasVoted={hasVotedOn(dispute.id)}
            />
          ))}
        </div>
      )}

      {/* Tips for new validators */}
      {stats.totalVotes < 10 && (
        <div className="bg-indigo-50 rounded-xl p-5 border border-indigo-100">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h4 className="font-semibold text-indigo-900 mb-1">
                Consejos para Validadores
              </h4>
              <ul className="text-sm text-indigo-800 space-y-1">
                <li>- Revisa toda la evidencia antes de votar</li>
                <li>- Verifica las coordenadas GPS cuando esten disponibles</li>
                <li>- Lee los argumentos de ambas partes cuidadosamente</li>
                <li>- Tu precision afecta tus ganancias futuras</li>
                <li>- Mantener alta precision desbloquea disputas de mayor valor</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ValidatorPanel
