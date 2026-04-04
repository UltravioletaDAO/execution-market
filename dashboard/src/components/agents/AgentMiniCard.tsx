/**
 * AgentMiniCard - Compact inline agent card
 *
 * Used in task lists, feeds, and anywhere a small agent reference is needed.
 * Clickable → navigates to /profile/:wallet
 */

import { memo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn, truncateAddress } from '../../lib/utils'
import { useAgentCard, preloadAgentCard } from '../../hooks/useAgentCard'
import { AgentAvatar } from './AgentAvatar'
import { AgentIdentityBadge } from './AgentIdentityBadge'
import { WorldHumanBadge } from './WorldHumanBadge'
import { ENSBadge } from './ENSBadge'
import { XBadge } from './XBadge'
import { Skeleton } from '../ui/Skeleton'
import type { Executor, AgentType } from '../../types/database'

interface AgentMiniCardBaseProps {
  /** Additional CSS classes */
  className?: string
  /** Whether clicking navigates to profile */
  clickable?: boolean
  /** Override the erc8004_agent_id displayed (per-chain task ID takes priority over global executor ID) */
  erc8004AgentIdOverride?: number | string | null
  /** Fallback display name from task.agent_name (used when executor record has no display_name) */
  agentName?: string | null
}

interface AgentMiniCardByWallet extends AgentMiniCardBaseProps {
  /** Wallet address - fetches data via useAgentCard */
  walletAddress: string
  executor?: never
}

interface AgentMiniCardByExecutor extends AgentMiniCardBaseProps {
  /** Direct executor data */
  executor: Executor
  walletAddress?: never
}

export type AgentMiniCardProps = AgentMiniCardByWallet | AgentMiniCardByExecutor

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

function AgentMiniCardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2 p-2 rounded-lg', className)}>
      <Skeleton circle width={32} height={32} />
      <div className="flex-1 min-w-0">
        <Skeleton width="70%" height={14} />
        <Skeleton width="40%" height={12} className="mt-1" />
      </div>
    </div>
  )
}

export const AgentMiniCard = memo(function AgentMiniCard(props: AgentMiniCardProps) {
  const { className, clickable = true, agentName } = props
  const { t } = useTranslation()
  const navigate = useNavigate()

  // If executor is provided directly, preload it into cache
  const directData = props.executor
    ? preloadAgentCard(props.executor)
    : null

  const walletToFetch = props.executor ? undefined : props.walletAddress
  const { data: fetchedData, loading } = useAgentCard(walletToFetch)

  const data = directData ?? fetchedData

  const handleClick = useCallback(() => {
    if (!clickable || !data) return
    navigate(`/profile/${data.wallet_address}`)
  }, [clickable, data, navigate])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        handleClick()
      }
    },
    [handleClick]
  )

  if (loading && !data) {
    return <AgentMiniCardSkeleton className={className} />
  }

  if (!data) {
    // Fallback: show truncated wallet
    const wallet = props.executor?.wallet_address ?? props.walletAddress ?? ''
    return (
      <div className={cn('flex items-center gap-2 p-2 rounded-lg', className)}>
        <AgentAvatar walletAddress={wallet} size="sm" showIndicator={false} />
        <span className="text-sm text-gray-500 dark:text-gray-400 font-mono">
          {truncateAddress(wallet)}
        </span>
      </div>
    )
  }

  const agentType = data.agent_type ?? 'human'
  const displayName = data.display_name || agentName || truncateAddress(data.wallet_address)

  return (
    <div
      className={cn(
        'flex items-center gap-2 p-2 rounded-lg transition-colors',
        clickable && 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50',
        className
      )}
      onClick={handleClick}
      onKeyDown={clickable ? handleKeyDown : undefined}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      <AgentAvatar
        walletAddress={data.wallet_address}
        avatarUrl={data.avatar_url}
        displayName={data.display_name}
        agentType={agentType}
        size="sm"
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {displayName}
          </span>
          <span className="text-xs flex-shrink-0" title={t(AGENT_TYPE_LABEL_KEY[agentType], agentType)}>
            {AGENT_TYPE_EMOJI[agentType]}
          </span>
          {(props.erc8004AgentIdOverride ?? data.erc8004_agent_id) != null && (
            <AgentIdentityBadge agentId={Number(props.erc8004AgentIdOverride ?? data.erc8004_agent_id)} compact />
          )}
          {data.social_links?.x && (
            <XBadge handle={data.social_links.x.handle} verified={data.social_links.x.verified} size="sm" />
          )}
          <WorldHumanBadge worldHumanId={data.world_human_id} />
          <ENSBadge ensName={data.ens_name || data.ens_subname} size="sm" />
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          {/* Star rating */}
          {data.avg_rating != null && data.avg_rating > 0 && (
            <span className="flex items-center gap-0.5">
              <svg className="w-3 h-3 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              {data.avg_rating.toFixed(1)}
            </span>
          )}
          {/* Tasks completed */}
          <span>
            {data.tasks_completed} {t('agents.tasksCompleted', 'completed')}
          </span>
        </div>
      </div>
    </div>
  )
})

export default AgentMiniCard
