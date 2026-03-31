/**
 * PublicProfile - Full public profile page at /profile/:wallet
 *
 * Shows agent identity, reputation, stats, recent task history, and feedback.
 * Accessible without authentication.
 */

import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'
import { useAgentCard } from '../hooks/useAgentCard'
import { useAgentReputation, getReputationTier, getTierColor } from '../hooks/useAgentReputation'
import { AgentAvatar } from '../components/agents/AgentAvatar'
import { XBadge } from '../components/agents/XBadge'
import { Skeleton, SkeletonText } from '../components/ui/Skeleton'
import { cn, truncateAddress, formatDate, copyToClipboard } from '../lib/utils'
import type { Task, Submission } from '../types/database'

interface RecentTask {
  id: string
  title: string
  status: string
  bounty_usd: number
  category: string
  created_at: string
  completed_at: string | null
}

interface RecentFeedback {
  id: string
  task_title: string
  verdict: string
  notes: string | null
  submitted_at: string
}

export function PublicProfile() {
  const { wallet } = useParams<{ wallet: string }>()
  const { t } = useTranslation()
  const navigate = useNavigate()

  const { data: agent, loading: agentLoading, error: agentError } = useAgentCard(wallet)

  // Fetch on-chain reputation if agent has erc8004_agent_id
  // For now we use the profile reputation_score
  const { data: onChainRep } = useAgentReputation()

  const [recentTasks, setRecentTasks] = useState<RecentTask[]>([])
  const [recentFeedback, setRecentFeedback] = useState<RecentFeedback[]>([])
  const [tasksLoading, setTasksLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  // Fetch recent tasks
  useEffect(() => {
    if (!wallet) return

    let cancelled = false

    async function fetchTasks() {
      setTasksLoading(true)

      try {
        // Tasks posted by this wallet
        const { data: posted } = await supabase
          .from('tasks')
          .select('id, title, status, bounty_usd, category, created_at, completed_at')
          .eq('agent_id', wallet)
          .order('created_at', { ascending: false })
          .limit(10)

        // Tasks completed by this wallet (need to find executor by wallet)
        const { data: executor } = await supabase
          .from('executors')
          .select('id')
          .eq('wallet_address', wallet)
          .single()

        let completed: RecentTask[] = []
        if (executor?.id) {
          const { data: workedOn } = await supabase
            .from('tasks')
            .select('id, title, status, bounty_usd, category, created_at, completed_at')
            .eq('executor_id', executor.id)
            .order('created_at', { ascending: false })
            .limit(10)

          completed = (workedOn ?? []) as RecentTask[]
        }

        if (!cancelled) {
          // Merge and deduplicate, sort by date
          const all = [...((posted ?? []) as RecentTask[]), ...completed]
          const unique = Array.from(new Map(all.map(t => [t.id, t])).values())
          unique.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          setRecentTasks(unique.slice(0, 10))
        }

        // Fetch recent feedback (submissions with agent_verdict)
        if (executor?.id) {
          const { data: submissions } = await supabase
            .from('submissions')
            .select('id, submitted_at, agent_verdict, agent_notes, task:tasks(title)')
            .eq('executor_id', executor.id)
            .not('agent_verdict', 'is', null)
            .order('submitted_at', { ascending: false })
            .limit(5)

          if (!cancelled && submissions) {
            setRecentFeedback(
              submissions.map((s: Record<string, unknown>) => ({
                id: s.id as string,
                task_title: ((s.task as Record<string, unknown>)?.title as string) ?? 'Unknown',
                verdict: s.agent_verdict as string,
                notes: s.agent_notes as string | null,
                submitted_at: s.submitted_at as string,
              }))
            )
          }
        }
      } catch {
        // Silent fail for task history
      } finally {
        if (!cancelled) setTasksLoading(false)
      }
    }

    fetchTasks()
    return () => { cancelled = true }
  }, [wallet])

  const handleCopyWallet = useCallback(async () => {
    if (!wallet) return
    const ok = await copyToClipboard(wallet)
    if (ok) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [wallet])

  // Loading state
  if (agentLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-3xl mx-auto px-4 py-8">
          <Skeleton width={80} height={32} className="mb-6" />
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-4">
              <Skeleton circle width={80} height={80} />
              <div className="flex-1">
                <Skeleton width="50%" height={24} />
                <Skeleton width="30%" height={16} className="mt-2" />
                <Skeleton width="40%" height={14} className="mt-2" />
              </div>
            </div>
            <div className="grid grid-cols-4 gap-4 mt-6">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="text-center">
                  <Skeleton width={60} height={28} className="mx-auto" />
                  <Skeleton width={80} height={14} className="mx-auto mt-1" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (agentError || !agent) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            {t('agents.profileNotFound', 'Agent profile not found')}
          </p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            {t('common.goBack', 'Go Back')}
          </button>
        </div>
      </div>
    )
  }

  const agentType = agent.agent_type ?? 'human'
  const tier = getReputationTier(agent.reputation_score)
  const tierColor = getTierColor(tier)
  const completionRate = agent.tasks_completed > 0
    ? ((agent.tasks_completed / (agent.tasks_completed + agent.tasks_disputed)) * 100).toFixed(0)
    : '0'

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* Back button */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-6 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="text-sm font-medium">{t('common.back', 'Back')}</span>
        </button>

        {/* Profile header card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-start gap-4">
            <AgentAvatar
              walletAddress={agent.wallet_address}
              avatarUrl={agent.avatar_url}
              displayName={agent.display_name}
              agentType={agentType}
              size="lg"
            />

            <div className="flex-1 min-w-0">
              {/* Name */}
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 truncate">
                {agent.display_name || truncateAddress(agent.wallet_address)}
              </h1>

              {/* Wallet + copy */}
              <div className="flex items-center gap-2 mt-1">
                <code className="text-sm font-mono text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                  {truncateAddress(agent.wallet_address)}
                </code>
                <button
                  onClick={handleCopyWallet}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                  title={t('common.copy', 'Copy')}
                >
                  {copied ? (
                    <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                  )}
                </button>
              </div>

              {/* Agent type + member since */}
              <div className="flex items-center gap-3 mt-2 text-sm text-gray-500 dark:text-gray-400">
                <span className="flex items-center gap-1">
                  {agentType === 'ai' ? '🤖' : agentType === 'organization' ? '🏢' : '👤'}
                  {t(`agents.type_${agentType}`, agentType.charAt(0).toUpperCase() + agentType.slice(1))}
                </span>
                <span>•</span>
                <span>
                  {t('agents.memberSince', 'Member since')} {formatDate(agent.member_since)}
                </span>
              </div>

              {/* Bio */}
              {agent.bio && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-3">
                  {agent.bio}
                </p>
              )}

              {/* Social links */}
              {agent.social_links?.x && (
                <div className="mt-3">
                  <XBadge handle={agent.social_links.x.handle} verified={agent.social_links.x.verified} size="md" />
                </div>
              )}
            </div>
          </div>

          {/* Reputation score */}
          <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                  {agent.reputation_score}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {t('agents.reputationScore', 'Reputation')}
                </div>
              </div>
              <span className={cn('text-sm px-2.5 py-1 rounded border font-medium', tierColor)}>
                {tier}
              </span>
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-100 dark:border-gray-700">
            <div className="text-center">
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {agent.tasks_completed}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {t('agents.completed', 'Completed')}
              </div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {agent.tasks_posted}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {t('agents.posted', 'Posted')}
              </div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {agent.avg_rating ? agent.avg_rating.toFixed(1) : '—'}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {t('agents.avgRating', 'Avg Rating')}
              </div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {completionRate}%
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {t('agents.completionRate', 'Completion')}
              </div>
            </div>
          </div>

          {/* Skills */}
          {agent.skills && agent.skills.length > 0 && (
            <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-700">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                {t('profile.skills', 'Skills')}
              </div>
              <div className="flex flex-wrap gap-2">
                {agent.skills.map(skill => (
                  <span
                    key={skill}
                    className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-full text-sm"
                  >
                    {skill.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Recent Task History */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mt-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            {t('agents.recentTasks', 'Recent Tasks')}
          </h2>

          {tasksLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0">
                  <div className="flex-1">
                    <Skeleton width="70%" height={16} />
                    <Skeleton width="40%" height={12} className="mt-1" />
                  </div>
                  <Skeleton width={60} height={20} className="rounded-full" />
                </div>
              ))}
            </div>
          ) : recentTasks.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
              {t('agents.noTasks', 'No task history yet')}
            </p>
          ) : (
            <div className="space-y-1">
              {recentTasks.map(task => (
                <div
                  key={task.id}
                  className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {task.title}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {formatDate(task.created_at)} · ${task.bounty_usd.toFixed(2)}
                    </div>
                  </div>
                  <span className={cn(
                    'text-xs px-2 py-0.5 rounded-full font-medium ml-3 flex-shrink-0',
                    task.status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                    task.status === 'published' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                    task.status === 'disputed' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                    'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  )}>
                    {task.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Feedback */}
        {recentFeedback.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mt-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              {t('agents.recentFeedback', 'Recent Feedback')}
            </h2>
            <div className="space-y-3">
              {recentFeedback.map(fb => (
                <div
                  key={fb.id}
                  className="py-3 border-b border-gray-100 dark:border-gray-700 last:border-0"
                >
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      'text-xs px-2 py-0.5 rounded-full font-medium',
                      fb.verdict === 'approved'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    )}>
                      {fb.verdict}
                    </span>
                    <span className="text-sm text-gray-900 dark:text-gray-100 font-medium truncate">
                      {fb.task_title}
                    </span>
                  </div>
                  {fb.notes && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                      {fb.notes}
                    </p>
                  )}
                  <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    {formatDate(fb.submitted_at)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default PublicProfile
