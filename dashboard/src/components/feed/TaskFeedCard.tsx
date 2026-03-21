/**
 * TaskFeedCard Component
 *
 * Rich news feed card showing the full lifecycle of a task:
 *   [Agent]  ←  Task Details  →  [Worker]
 *
 * Includes: both identities with scores, task description, category,
 * escrow TX, payment/refund TX, reputation TXs, bounty, time taken.
 *
 * This is the "match card" view — agent on the left, worker on the right,
 * task info in the center.
 */

import { memo, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { cn } from '../../lib/utils'
import { formatRelativeTime } from '../../lib/formatRelativeTime'
import { AgentAvatar } from '../agents/AgentAvatar'
import { TxHashLink } from '../TxLink'
import { NetworkBadge } from '../ui/NetworkBadge'
import type { ActivityEventType } from '../../hooks/useActivityFeed'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TaskFeedParticipant {
  wallet: string | null
  name: string | null
  type: 'human' | 'ai' | 'organization' | string | null
  reputation_score: number | null
  tasks_completed: number | null
  avatar_url?: string | null
}

export interface TaskFeedTransaction {
  label: string
  hash: string | null
  network?: string
}

export interface FeedbackData {
  score: number | null          // 0-100 scale
  reputation_tx: string | null  // on-chain TX hash
  comment: string | null        // optional feedback text
  status: 'completed' | 'pending'
}

export interface TaskFeedCardData {
  id: string
  event_type: ActivityEventType
  /** The agent/requester who posted the task */
  agent: TaskFeedParticipant
  /** The worker who accepted/completed the task */
  worker: TaskFeedParticipant | null
  /** Task info */
  task_id: string | null
  task_title: string | null
  task_category: string | null
  bounty_usd: number | null
  payment_token: string | null
  payment_network: string | null
  /** Time metrics */
  created_at: string
  completed_at: string | null
  time_taken_seconds: number | null
  /** Transactions */
  escrow_tx: string | null
  payment_tx: string | null
  refund_tx: string | null
  /** Bidirectional reputation */
  agent_to_worker_feedback: FeedbackData | null  // agent rates worker
  worker_to_agent_feedback: FeedbackData | null  // worker rates agent
}

export interface TaskFeedCardProps {
  data: TaskFeedCardData
  /** Compact mode for landing page */
  compact?: boolean
  /** Highlight as newly arrived */
  isNew?: boolean
  className?: string
}

// ---------------------------------------------------------------------------
// Event styling
// ---------------------------------------------------------------------------

const EVENT_STYLES: Record<string, { label: string; color: string; icon: string }> = {
  task_created: { label: 'Task Posted', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300', icon: '📝' },
  task_accepted: { label: 'Assigned to Executor', color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300', icon: '🤝' },
  task_in_progress: { label: 'In Progress', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300', icon: '⚙️' },
  task_submitted: { label: 'Work Submitted', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300', icon: '📤' },
  task_completed: { label: 'Task Completed', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300', icon: '🎉' },
  feedback_given: { label: 'Reputation Scored', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300', icon: '⭐' },
  dispute_opened: { label: 'Dispute Opened', color: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300', icon: '⚠️' },
  dispute_resolved: { label: 'Dispute Resolved', color: 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300', icon: '⚖️' },
  worker_joined: { label: 'New Executor', color: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300', icon: '👋' },
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function truncateWallet(wallet: string): string {
  if (!wallet) return ''
  if (wallet.includes('.')) return wallet
  if (wallet.length <= 12) return wallet
  return `${wallet.slice(0, 6)}…${wallet.slice(-4)}`
}

function getReputationTier(score: number): { name: string; color: string } {
  if (score >= 81) return { name: 'Diamante', color: 'text-purple-600 dark:text-purple-400' }
  if (score >= 61) return { name: 'Oro', color: 'text-yellow-600 dark:text-yellow-400' }
  if (score >= 31) return { name: 'Plata', color: 'text-slate-500 dark:text-slate-400' }
  return { name: 'Bronce', color: 'text-orange-600 dark:text-orange-400' }
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  if (seconds < 86400) {
    const h = Math.floor(seconds / 3600)
    const m = Math.round((seconds % 3600) / 60)
    return m > 0 ? `${h}h ${m}m` : `${h}h`
  }
  const d = Math.floor(seconds / 86400)
  const h = Math.round((seconds % 86400) / 3600)
  return h > 0 ? `${d}d ${h}h` : `${d}d`
}

const CATEGORY_ICONS: Record<string, string> = {
  physical_presence: '📍',
  knowledge_access: '🧠',
  human_authority: '🏛️',
  simple_action: '⚡',
  digital_physical: '🔗',
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Participant identity panel (left = agent, right = worker) */
const ParticipantPanel = memo(function ParticipantPanel({
  participant,
  role,
  align,
  onClick,
}: {
  participant: TaskFeedParticipant | null
  role: string
  align: 'left' | 'right'
  onClick?: () => void
}) {
  const { t } = useTranslation()

  if (!participant || !participant.wallet) {
    return (
      <div className={cn(
        'flex flex-col items-center gap-1.5 w-28 sm:w-32 flex-shrink-0',
        align === 'right' && 'items-center',
      )}>
        <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
          <span className="text-slate-400 text-lg">?</span>
        </div>
        <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wide">
          {t('feed.awaitingWorker', 'Awaiting Worker')}
        </span>
      </div>
    )
  }

  const displayName = participant.name || truncateWallet(participant.wallet)
  const typeEmoji = participant.type === 'ai' ? '🤖' : participant.type === 'organization' ? '🏢' : '👤'
  const score = participant.reputation_score ?? 0
  const tier = getReputationTier(score)

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex flex-col items-center gap-1.5 w-28 sm:w-32 flex-shrink-0 group/panel',
        'hover:opacity-80 transition-opacity cursor-pointer',
      )}
    >
      {/* Role label */}
      <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider font-medium">
        {role}
      </span>

      {/* Avatar */}
      <AgentAvatar
        walletAddress={participant.wallet}
        avatarUrl={participant.avatar_url}
        agentType={(participant.type as 'human' | 'ai' | 'organization') || 'human'}
        size="md"
      />

      {/* Name + type */}
      <div className="flex items-center gap-1">
        <span className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate max-w-[100px] group-hover/panel:text-blue-600 dark:group-hover/panel:text-blue-400 transition-colors">
          {displayName}
        </span>
        <span className="text-xs" title={participant.type || 'human'}>{typeEmoji}</span>
      </div>

      {/* Score */}
      <div className="flex items-center gap-1">
        <span className={cn('text-xs font-bold', tier.color)}>
          {score > 0 ? score.toFixed(0) : '—'}
        </span>
        <span className={cn('text-[10px]', tier.color)}>{tier.name}</span>
      </div>

      {/* Tasks completed */}
      {participant.tasks_completed != null && participant.tasks_completed > 0 && (
        <span className="text-[10px] text-slate-500 dark:text-slate-400">
          {participant.tasks_completed} tasks
        </span>
      )}
    </button>
  )
})

/** Score display — 0 to 100 scale */
function ScoreDisplay({ score }: { score: number }) {
  const clamped = Math.round(Math.min(100, Math.max(0, score)))
  const color = clamped >= 80 ? 'text-emerald-500' : clamped >= 60 ? 'text-amber-500' : clamped >= 40 ? 'text-orange-500' : 'text-red-500'
  return (
    <span className="inline-flex items-center gap-1.5" aria-label={`Score ${clamped} out of 100`}>
      <span className={cn('text-sm font-bold', color)}>{clamped}</span>
      <span className="text-[10px] text-slate-400 dark:text-slate-500">/100</span>
    </span>
  )
}

/** Feedback panel for one direction of reputation */
function FeedbackPanel({
  label,
  feedback,
  network,
}: {
  label: string
  feedback: FeedbackData | null
  network: string
}) {
  if (!feedback || feedback.status === 'pending') {
    return (
      <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-2">
        <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium mb-1">{label}</p>
        <div className="flex items-center gap-1.5">
          <span className="text-amber-400 text-sm">⏳</span>
          <span className="text-xs text-slate-500 dark:text-slate-400 italic">Pending</span>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-2">
      <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium mb-1">{label}</p>
      {feedback.score != null && (
        <ScoreDisplay score={feedback.score} />
      )}
      {feedback.comment && (
        <p className="text-[10px] text-slate-600 dark:text-slate-400 mt-1 italic line-clamp-2">
          &ldquo;{feedback.comment}&rdquo;
        </p>
      )}
      {feedback.reputation_tx && (
        <div className="mt-1">
          <TxHashLink txHash={feedback.reputation_tx} network={network} className="text-[10px]" />
        </div>
      )}
    </div>
  )
}

/** Task center content — shared between mobile and desktop layouts */
function TaskCenterContent({
  data,
  categoryIcon,
  hasFeedback,
  isCompleted,
  transactions,
  onTaskClick,
  t,
}: {
  data: TaskFeedCardData
  categoryIcon: string
  hasFeedback: boolean
  isCompleted: boolean
  transactions: TaskFeedTransaction[]
  onTaskClick: () => void
  t: (key: string, fallback: string, opts?: Record<string, unknown>) => string
}) {
  return (
    <>
      {/* Task title + category */}
      <div className="flex items-start gap-2 mb-3">
        <span className="text-lg flex-shrink-0">{categoryIcon}</span>
        <div className="min-w-0">
          {data.task_title ? (
            <button
              onClick={onTaskClick}
              className="text-sm font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors text-left leading-snug"
            >
              {data.task_title}
            </button>
          ) : (
            <span className="text-sm text-slate-400 italic">{t('feed.untitledTask', 'Untitled task')}</span>
          )}
          {data.task_category && (
            <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              {t(`tasks.categories.${data.task_category}`, data.task_category.replace(/_/g, ' '))}
            </p>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-3 mb-3">
        {data.bounty_usd != null && data.bounty_usd > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-xs text-slate-500 dark:text-slate-400">💰</span>
            <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
              ${data.bounty_usd.toFixed(2)}
            </span>
            {data.payment_token && (
              <span className="text-[10px] text-slate-400">{data.payment_token}</span>
            )}
          </div>
        )}
        {data.payment_network && (
          <NetworkBadge 
            network={data.payment_network}
            size="sm"
          />
        )}
        {data.time_taken_seconds != null && data.time_taken_seconds > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-xs text-slate-500 dark:text-slate-400">⏱️</span>
            <span className="text-xs text-slate-600 dark:text-slate-300">{formatDuration(data.time_taken_seconds)}</span>
          </div>
        )}
      </div>

      {/* Reputation Exchange */}
      {(hasFeedback || isCompleted) && (
        <div className="border-t border-slate-100 dark:border-slate-700/50 pt-2 mb-2">
          <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider font-medium mb-2">
            {t('feed.reputationExchange', 'Reputation Exchange')}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <FeedbackPanel
              label={t('feed.agentToWorker', 'Requester → Executor')}
              feedback={data.agent_to_worker_feedback}
              network={data.payment_network || 'base'}
            />
            <FeedbackPanel
              label={t('feed.workerToAgent', 'Executor → Requester')}
              feedback={data.worker_to_agent_feedback}
              network={data.payment_network || 'base'}
            />
          </div>
        </div>
      )}

      {/* Transactions */}
      {transactions.length > 0 && (
        <div className="border-t border-slate-100 dark:border-slate-700/50 pt-2 space-y-0.5">
          <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider font-medium mb-1">
            {t('feed.transactions', 'Transactions')}
          </p>
          {transactions.map((tx) => (
            <TxRow key={tx.label} label={tx.label} hash={tx.hash} network={tx.network} />
          ))}
        </div>
      )}
    </>
  )
}

/** Transaction row */
function TxRow({ label, hash, network }: { label: string; hash: string | null | undefined; network?: string }) {
  if (!hash) return null
  return (
    <div className="flex items-center justify-between gap-2 py-0.5">
      <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wide flex-shrink-0">
        {label}
      </span>
      <TxHashLink txHash={hash} network={network || 'base'} className="text-xs" />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const TaskFeedCard = memo(function TaskFeedCard({
  data,
  compact = false,
  isNew = false,
  className,
}: TaskFeedCardProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const eventStyle = EVENT_STYLES[data.event_type] || EVENT_STYLES.task_created
  const categoryIcon = data.task_category ? CATEGORY_ICONS[data.task_category] || '📋' : '📋'

  const transactions = useMemo<TaskFeedTransaction[]>(() => {
    const txs: TaskFeedTransaction[] = []
    const net = data.payment_network || 'base'
    if (data.escrow_tx) txs.push({ label: 'Escrow', hash: data.escrow_tx, network: net })
    if (data.payment_tx) txs.push({ label: 'Payment', hash: data.payment_tx, network: net })
    if (data.refund_tx) txs.push({ label: 'Refund', hash: data.refund_tx, network: net })
    if (data.agent_to_worker_feedback?.reputation_tx) txs.push({ label: 'Rep (Agent→Worker)', hash: data.agent_to_worker_feedback.reputation_tx, network: net })
    if (data.worker_to_agent_feedback?.reputation_tx) txs.push({ label: 'Rep (Worker→Agent)', hash: data.worker_to_agent_feedback.reputation_tx, network: net })
    return txs
  }, [data])

  const hasFeedback = Boolean(data.agent_to_worker_feedback || data.worker_to_agent_feedback)
  const isCompleted = data.event_type === 'task_completed'

  const handleTaskClick = () => {
    if (data.task_id) navigate(`/?task=${data.task_id}`)
  }

  // ------------------------------------------------------------------
  // Compact variant (landing page) — simplified single-line
  // ------------------------------------------------------------------
  if (compact) {
    return (
      <div className={cn(
        'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
        'hover:bg-slate-100 dark:hover:bg-slate-700',
        isNew && 'animate-feed-in bg-blue-50/50 dark:bg-blue-900/20',
        className,
      )}>
        <span className="text-sm flex-shrink-0">{eventStyle.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-slate-800 dark:text-slate-100 truncate">
            <span className="font-medium">{data.agent.name || truncateWallet(data.agent.wallet || '')}</span>
            {' → '}
            {data.task_title || t('feed.aTask', 'a task')}
            {data.bounty_usd != null && data.bounty_usd > 0 && (
              <span className="text-emerald-600 dark:text-emerald-300 font-medium"> ${data.bounty_usd.toFixed(2)}</span>
            )}
          </p>
        </div>
        <span className="text-[10px] text-slate-500 dark:text-slate-400 flex-shrink-0">{formatRelativeTime(data.created_at)}</span>
      </div>
    )
  }

  // ------------------------------------------------------------------
  // Full card variant (authenticated feed)
  // ------------------------------------------------------------------
  return (
    <div className={cn(
      'rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 overflow-hidden transition-all duration-300',
      'hover:shadow-md hover:border-slate-300 dark:hover:border-slate-500',
      isNew && 'animate-feed-in ring-2 ring-blue-300 dark:ring-blue-600',
      className,
    )}>
      {/* Header bar — event type + chain badge + timestamp */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-100 dark:border-slate-600/50">
        <div className="flex items-center gap-2">
          <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium', eventStyle.color)}>
            {eventStyle.icon} {t(`feed.event.${data.event_type}`, eventStyle.label)}
          </span>
          {/* Chain + token badge */}
          {data.payment_network && (
            <NetworkBadge 
              network={data.payment_network}
              token={data.payment_token || undefined}
              size="sm"
            />
          )}
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400" title={new Date(data.created_at).toLocaleString()}>
          {formatRelativeTime(data.created_at)}
        </span>
      </div>

      {/* Participants row — horizontal on mobile, flanking on desktop */}
      <div className="flex items-center justify-around gap-2 px-4 pt-3 pb-2 sm:hidden">
        <ParticipantPanel
          participant={data.agent}
          role={t('feed.requester', 'Requester')}
          align="left"
          onClick={() => data.agent.wallet && navigate(`/profile/${data.agent.wallet}`)}
        />
        <div className="text-slate-300 dark:text-slate-600 text-lg">→</div>
        <ParticipantPanel
          participant={data.worker}
          role={t('feed.worker', 'Worker')}
          align="right"
          onClick={() => data.worker?.wallet && navigate(`/profile/${data.worker.wallet}`)}
        />
      </div>

      {/* Desktop: 3-column layout */}
      <div className="hidden sm:flex items-stretch">
        {/* Left — Agent (requester) */}
        <div className="flex items-center justify-center p-4 border-r border-slate-100 dark:border-slate-700/50">
          <ParticipantPanel
            participant={data.agent}
            role={t('feed.requester', 'Requester')}
            align="left"
            onClick={() => data.agent.wallet && navigate(`/profile/${data.agent.wallet}`)}
          />
        </div>

        {/* Center — Task details (desktop) */}
        <div className="flex-1 p-4 min-w-0">
          <TaskCenterContent
            data={data}
            categoryIcon={categoryIcon}
            hasFeedback={hasFeedback}
            isCompleted={isCompleted}
            transactions={transactions}
            onTaskClick={handleTaskClick}
            t={t}
          />
        </div>

        {/* Right — Worker */}
        <div className="flex items-center justify-center p-4 border-l border-slate-100 dark:border-slate-700/50">
          <ParticipantPanel
            participant={data.worker}
            role={t('feed.worker', 'Worker')}
            align="right"
            onClick={() => data.worker?.wallet && navigate(`/profile/${data.worker.wallet}`)}
          />
        </div>
      </div>

      {/* Mobile: task details below participants */}
      <div className="sm:hidden px-4 pb-4">
        <TaskCenterContent
          data={data}
          categoryIcon={categoryIcon}
          hasFeedback={hasFeedback}
          isCompleted={isCompleted}
          transactions={transactions}
          onTaskClick={handleTaskClick}
          t={t}
        />
      </div>
    </div>
  )
})

export default TaskFeedCard
