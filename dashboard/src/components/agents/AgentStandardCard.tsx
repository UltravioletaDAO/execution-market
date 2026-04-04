/**
 * AgentStandardCard - Larger agent card for task detail views
 *
 * Shows avatar, name, type, bio, reputation tier, member since, and a View Profile button.
 */

import { memo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn, truncateAddress, formatDate } from '../../lib/utils'
import { useAgentCard, preloadAgentCard } from '../../hooks/useAgentCard'
import { getReputationTier, getTierColor } from '../../hooks/useAgentReputation'
import { AgentAvatar } from './AgentAvatar'
import { AgentIdentityBadge } from './AgentIdentityBadge'
import { WorldHumanBadge } from './WorldHumanBadge'
import { ENSBadge } from './ENSBadge'
import { XBadge } from './XBadge'
import { Skeleton, SkeletonText } from '../ui/Skeleton'
import type { Executor, AgentType } from '../../types/database'

interface AgentStandardCardBaseProps {
  /** Card title label (e.g. "Posted by", "Accepted by") */
  label?: string
  /** Additional CSS classes */
  className?: string
  /** Override the erc8004_agent_id displayed (per-chain task ID takes priority over global executor ID) */
  erc8004AgentIdOverride?: number | string | null
  /** Fallback display name from task.agent_name (used when executor record has no display_name) */
  agentName?: string | null
}

interface AgentStandardCardByWallet extends AgentStandardCardBaseProps {
  walletAddress: string
  executor?: never
}

interface AgentStandardCardByExecutor extends AgentStandardCardBaseProps {
  executor: Executor
  walletAddress?: never
}

export type AgentStandardCardProps = AgentStandardCardByWallet | AgentStandardCardByExecutor

const AGENT_TYPE_EMOJI: Record<AgentType, string> = {
  human: '👤',
  ai: '🤖',
  organization: '🏢',
}

const AGENT_TYPE_LABEL_KEY: Record<AgentType, string> = {
  human: 'agents.typeHuman',
  ai: 'agents.typeAI',
  organization: 'agents.typeOrg',
}

function AgentStandardCardSkeleton({ label, className }: { label?: string; className?: string }) {
  return (
    <div className={cn('bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4', className)}>
      {label && (
        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          {label}
        </div>
      )}
      <div className="flex items-start gap-3">
        <Skeleton circle width={48} height={48} />
        <div className="flex-1">
          <Skeleton width="60%" height={18} />
          <Skeleton width="40%" height={14} className="mt-1.5" />
          <SkeletonText lines={2} height={12} className="mt-2" />
        </div>
      </div>
    </div>
  )
}

export const AgentStandardCard = memo(function AgentStandardCard(props: AgentStandardCardProps) {
  const { label, className, agentName } = props
  const { t } = useTranslation()
  const navigate = useNavigate()

  const directData = props.executor ? preloadAgentCard(props.executor) : null
  const walletToFetch = props.executor ? undefined : props.walletAddress
  const { data: fetchedData, loading } = useAgentCard(walletToFetch)

  const data = directData ?? fetchedData

  const handleViewProfile = useCallback(() => {
    if (!data) return
    navigate(`/profile/${data.wallet_address}`)
  }, [data, navigate])

  if (loading && !data) {
    return <AgentStandardCardSkeleton label={label} className={className} />
  }

  if (!data) {
    const wallet = props.executor?.wallet_address ?? props.walletAddress ?? ''
    return (
      <div className={cn('bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4', className)}>
        {label && (
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            {label}
          </div>
        )}
        <div className="flex items-center gap-3">
          <AgentAvatar walletAddress={wallet} size="md" showIndicator={false} />
          <span className="text-sm text-gray-500 dark:text-gray-400 font-mono">
            {truncateAddress(wallet)}
          </span>
        </div>
      </div>
    )
  }

  const agentType = data.agent_type ?? 'human'
  const displayName = data.display_name || agentName || truncateAddress(data.wallet_address)
  const tier = getReputationTier(data.reputation_score)
  const tierColor = getTierColor(tier)

  return (
    <div className={cn('bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4', className)}>
      {label && (
        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          {label}
        </div>
      )}

      <div className="flex items-start gap-3">
        <AgentAvatar
          walletAddress={data.wallet_address}
          avatarUrl={data.avatar_url}
          displayName={data.display_name}
          agentType={agentType}
          size="md"
        />

        <div className="flex-1 min-w-0">
          {/* Name + type */}
          <div className="flex items-center gap-1.5">
            <span className="font-medium text-gray-900 dark:text-gray-100 truncate">
              {displayName}
            </span>
            <span
              className="text-sm flex-shrink-0"
              title={t(AGENT_TYPE_LABEL_KEY[agentType], agentType)}
            >
              {AGENT_TYPE_EMOJI[agentType]}
            </span>
            {(props.erc8004AgentIdOverride ?? data.erc8004_agent_id) != null && (
              <AgentIdentityBadge agentId={Number(props.erc8004AgentIdOverride ?? data.erc8004_agent_id)} compact />
            )}
            {data.social_links?.x && (
              <XBadge handle={data.social_links.x.handle} verified={data.social_links.x.verified} size="md" />
            )}
            <WorldHumanBadge worldHumanId={data.world_human_id ?? null} />
            <ENSBadge ensName={data.ens_name || data.ens_subname} size="md" />
          </div>

          {/* Reputation tier + rating */}
          <div className="flex items-center gap-2 mt-1">
            <span className={cn('text-xs px-1.5 py-0.5 rounded border font-medium', tierColor)}>
              {tier}
            </span>
            {data.avg_rating != null && data.avg_rating > 0 && (
              <span className="flex items-center gap-0.5 text-xs text-gray-500 dark:text-gray-400">
                <svg className="w-3 h-3 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                {data.avg_rating.toFixed(1)}
              </span>
            )}
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {data.tasks_completed} {t('agents.tasksCompleted', 'completed')}
            </span>
          </div>

          {/* Bio (truncated) */}
          {data.bio && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 line-clamp-2">
              {data.bio}
            </p>
          )}

          {/* Member since */}
          <div className="text-xs text-gray-400 dark:text-gray-500 mt-2">
            {t('agents.memberSince', 'Member since')} {formatDate(data.member_since)}
          </div>
        </div>
      </div>

      {/* View Profile button */}
      <button
        onClick={handleViewProfile}
        className="mt-3 w-full text-center text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 py-2 rounded-lg border border-blue-200 dark:border-blue-800 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
      >
        {t('agents.viewProfile', 'View Profile')}
      </button>
    </div>
  )
})

export default AgentStandardCard
