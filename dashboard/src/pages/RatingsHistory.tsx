/**
 * RatingsHistory - Worker Ratings History Page
 *
 * Features:
 * - Tabs: Received / Given
 * - Score display (0-100 scale), comment, date, task title
 * - Query Supabase `ratings` table
 * - Empty states
 * - i18n EN/ES
 */

import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { supabase } from '../lib/supabase'
import { useQuery } from '@tanstack/react-query'
import { TxLink } from '../components/TxLink'

// ============================================================================
// TYPES
// ============================================================================

type TabType = 'received' | 'given'

interface RatingEntry {
  id: string
  executor_id: string
  task_id: string
  rater_id: string
  rater_type: string | null
  rating: number
  stars: number | null
  comment: string | null
  created_at: string
  task_title: string | null
  reputation_tx: string | null
  payment_network: string | null
}

// ============================================================================
// HOOKS
// ============================================================================

function useRatingsReceived(executorId: string | undefined) {
  return useQuery<RatingEntry[]>({
    queryKey: ['ratings', 'received', executorId],
    queryFn: async () => {
      if (!executorId) return []

      const { data, error } = await supabase
        .from('ratings')
        .select(
          'id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at, tasks:task_id(title, payment_network)'
        )
        .eq('executor_id', executorId)
        .eq('rater_type', 'agent')
        .eq('is_public', true)
        .order('created_at', { ascending: false })
        .limit(50)

      if (error) {
        // Fallback: plain query without join
        const { data: plain, error: plainErr } = await supabase
          .from('ratings')
          .select('id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at')
          .eq('executor_id', executorId)
          .eq('rater_type', 'agent')
          .eq('is_public', true)
          .order('created_at', { ascending: false })
          .limit(50)
        if (plainErr) return []
        return (plain || []).map((row: Record<string, unknown>) => ({
          ...(row as unknown as RatingEntry),
          task_title: null,
          reputation_tx: null,
          payment_network: null,
        }))
      }

      // Fetch reputation_tx from feedback_documents (any type with a tx)
      const taskIds = [...new Set((data || []).map((r: Record<string, unknown>) => r.task_id as string))]
      const feedbackMap: Record<string, string> = {}
      if (taskIds.length > 0) {
        const { data: fbDocs } = await supabase
          .from('feedback_documents')
          .select('task_id, reputation_tx, feedback_type')
          .in('task_id', taskIds)
          .not('reputation_tx', 'is', null)
        for (const fb of fbDocs || []) {
          if (fb.reputation_tx && !feedbackMap[fb.task_id]) {
            feedbackMap[fb.task_id] = fb.reputation_tx
          }
        }
      }

      return (data || []).map((row: Record<string, unknown>) => {
        const task = (row.tasks || {}) as { title?: string; payment_network?: string }
        return {
          id: row.id as string,
          executor_id: row.executor_id as string,
          task_id: row.task_id as string,
          rater_id: row.rater_id as string,
          rater_type: row.rater_type as string | null,
          rating: row.rating as number,
          stars: row.stars as number | null,
          comment: row.comment as string | null,
          created_at: row.created_at as string,
          task_title: task.title || null,
          reputation_tx: feedbackMap[row.task_id as string] || null,
          payment_network: task.payment_network || null,
        }
      })
    },
    enabled: !!executorId,
    staleTime: 60_000,
  })
}

function useRatingsGiven(executorId: string | undefined) {
  return useQuery<RatingEntry[]>({
    queryKey: ['ratings', 'given', executorId],
    queryFn: async () => {
      if (!executorId) return []

      const { data, error } = await supabase
        .from('ratings')
        .select(
          'id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at, tasks:task_id(title, payment_network)'
        )
        .eq('rater_id', executorId)
        .eq('is_public', true)
        .order('created_at', { ascending: false })
        .limit(50)

      if (error) {
        const { data: plain, error: plainErr } = await supabase
          .from('ratings')
          .select('id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at')
          .eq('rater_id', executorId)
          .eq('is_public', true)
          .order('created_at', { ascending: false })
          .limit(50)
        if (plainErr) return []
        return (plain || []).map((row: Record<string, unknown>) => ({
          ...(row as unknown as RatingEntry),
          task_title: null,
          reputation_tx: null,
          payment_network: null,
        }))
      }

      // Fetch reputation_tx for given ratings (any type with a tx)
      const taskIds = [...new Set((data || []).map((r: Record<string, unknown>) => r.task_id as string))]
      const feedbackMap: Record<string, string> = {}
      if (taskIds.length > 0) {
        const { data: fbDocs } = await supabase
          .from('feedback_documents')
          .select('task_id, reputation_tx, feedback_type')
          .in('task_id', taskIds)
          .not('reputation_tx', 'is', null)
        for (const fb of fbDocs || []) {
          if (fb.reputation_tx && !feedbackMap[fb.task_id]) {
            feedbackMap[fb.task_id] = fb.reputation_tx
          }
        }
      }

      return (data || []).map((row: Record<string, unknown>) => {
        const task = (row.tasks || {}) as { title?: string; payment_network?: string }
        return {
          id: row.id as string,
          executor_id: row.executor_id as string,
          task_id: row.task_id as string,
          rater_id: row.rater_id as string,
          rater_type: row.rater_type as string | null,
          rating: row.rating as number,
          stars: row.stars as number | null,
          comment: row.comment as string | null,
          created_at: row.created_at as string,
          task_title: task.title || null,
          reputation_tx: feedbackMap[row.task_id as string] || null,
          payment_network: task.payment_network || null,
        }
      })
    },
    enabled: !!executorId,
    staleTime: 60_000,
  })
}

// ============================================================================
// UTILITIES
// ============================================================================

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function ScoreDisplay({ score }: { score: number }) {
  const value = Math.round(Math.min(100, Math.max(0, score)))
  const color = value >= 80 ? 'text-emerald-600' : value >= 60 ? 'text-amber-600' : value >= 40 ? 'text-orange-600' : 'text-red-600'
  return (
    <div className="flex items-center gap-1">
      <span className={`text-lg font-bold ${color}`}>{value}</span>
      <span className="text-xs text-gray-400">/100</span>
    </div>
  )
}

function RatingCard({ entry, t }: { entry: RatingEntry; t: (key: string) => string }) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-gray-900 dark:text-white">{entry.rating}</span>
            <span className="text-sm text-gray-400">/100</span>
          </div>
          {entry.task_title && (
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mt-2 truncate">{entry.task_title}</p>
          )}
          {entry.comment && (
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 italic">"{entry.comment}"</p>
          )}
          {entry.rater_type && (
            <span className="text-xs text-gray-400 mt-1 inline-block">
              {entry.rater_type === 'agent'
                ? t('ratingsHistory.ratedByAgent')
                : t('ratingsHistory.ratedByWorker')}
            </span>
          )}
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs text-gray-400">{formatDate(entry.created_at)}</p>
        </div>
      </div>
      {entry.reputation_tx && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <TxLink txHash={entry.reputation_tx} network={entry.payment_network || "base"} />
        </div>
      )}
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
          />
        </svg>
      </div>
      <p className="text-gray-500 text-sm">{message}</p>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
          <div className="h-3 bg-gray-200 rounded w-2/3 mb-2" />
          <div className="h-3 bg-gray-200 rounded w-1/2" />
        </div>
      ))}
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function RatingsHistory() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { executor } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('received')

  const {
    data: ratingsReceived,
    isLoading: isLoadingReceived,
  } = useRatingsReceived(executor?.id)

  const {
    data: ratingsGiven,
    isLoading: isLoadingGiven,
  } = useRatingsGiven(executor?.id)

  const isLoading = activeTab === 'received' ? isLoadingReceived : isLoadingGiven
  const ratings = activeTab === 'received' ? ratingsReceived : ratingsGiven

  // Summary stats from received ratings
  const totalRatings = ratingsReceived?.length ?? 0
  const avgScore = useMemo(() => {
    if (!ratingsReceived || ratingsReceived.length === 0) return 0
    return ratingsReceived.reduce((sum, r) => sum + r.rating, 0) / ratingsReceived.length
  }, [ratingsReceived])

  const emptyMessage =
    activeTab === 'received'
      ? t('ratingsHistory.emptyReceived')
      : t('ratingsHistory.emptyGiven')

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div>
          <h1 className="font-bold text-lg text-gray-900">{t('ratingsHistory.title')}</h1>
          <p className="text-sm text-gray-500">{t('ratingsHistory.subtitle')}</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">
            {avgScore > 0 ? Math.round(avgScore) : '\u2014'}
            {avgScore > 0 && <span className="text-sm font-normal text-gray-400">/100</span>}
          </div>
          <div className="text-xs text-gray-500 mt-1">{t('ratingsHistory.avgRating')}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">{totalRatings}</div>
          <div className="text-xs text-gray-500 mt-1">{t('ratingsHistory.totalRatings')}</div>
        </div>
      </div>

      {/* Tab Selector */}
      <div className="flex gap-1 p-0.5 bg-gray-100 rounded-lg mb-6">
        <button
          onClick={() => setActiveTab('received')}
          className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === 'received'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {t('ratingsHistory.tabReceived')}
        </button>
        <button
          onClick={() => setActiveTab('given')}
          className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === 'given'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {t('ratingsHistory.tabGiven')}
        </button>
      </div>

      {/* Ratings List */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : !ratings || ratings.length === 0 ? (
        <EmptyState message={emptyMessage} />
      ) : (
        <div className="space-y-3">
          {ratings.map((entry) => (
            <RatingCard key={entry.id} entry={entry} t={t} />
          ))}
        </div>
      )}
    </div>
  )
}

export default RatingsHistory
