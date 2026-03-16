/**
 * Leaderboard Page (Public)
 *
 * Shows top workers ranked by reputation score.
 * Fetches from GET /api/v1/reputation/leaderboard.
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { ReputationBadge } from '../components/ReputationBadge'

const API_BASE = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

interface LeaderboardEntry {
  id: string
  display_name: string
  reputation_score: number
  tasks_completed: number
  avg_rating: number | null
  wallet_address?: string
}

function getRankStyle(rank: number): { color: string; size: string } {
  if (rank === 1) return { color: '#FFD700', size: 'text-2xl' } // gold
  if (rank === 2) return { color: '#C0C0C0', size: 'text-xl' } // silver
  if (rank === 3) return { color: '#CD7F32', size: 'text-xl' } // bronze
  return { color: '#6B7280', size: 'text-base' } // gray
}

function StarRating({ score }: { score: number }) {
  // Convert 0-100 score to 1-5 stars
  const stars = Math.max(1, Math.min(5, Math.round(score / 20)))

  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <svg
          key={s}
          className={`w-3.5 h-3.5 ${s <= stars ? 'text-yellow-400' : 'text-gray-300'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  )
}

function SkeletonRows({ count = 8 }: { count?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-16 bg-gray-200 rounded-lg" />
      ))}
    </div>
  )
}

export function Leaderboard() {
  const { t } = useTranslation()
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchLeaderboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch(`${API_BASE}/api/v1/reputation/leaderboard?limit=50`, {
        headers: { 'X-Client-Info': 'execution-market-dashboard' },
        signal: AbortSignal.timeout(10000),
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      // API returns { entries: [...] } or array directly
      const list = Array.isArray(data) ? data : (data.entries || data.leaderboard || [])
      setEntries(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leaderboard')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLeaderboard()
  }, [fetchLeaderboard])

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          {t('leaderboard.title', 'Reputation Leaderboard')}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('leaderboard.subtitle', 'Top workers ranked by reputation score and tasks completed.')}
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={fetchLeaderboard}
            className="text-red-600 font-medium hover:text-red-800 ml-4"
          >
            {t('common.retry', 'Retry')}
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {/* Header row */}
        <div className="grid grid-cols-12 gap-2 px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider border-b border-slate-100 bg-slate-50">
          <div className="col-span-1">#</div>
          <div className="col-span-4">{t('leaderboard.worker', 'Worker')}</div>
          <div className="col-span-2">{t('leaderboard.reputation', 'Reputation')}</div>
          <div className="col-span-2">{t('leaderboard.tasksCompleted', 'Tasks')}</div>
          <div className="col-span-3">{t('leaderboard.avgRating', 'Avg Rating')}</div>
        </div>

        {loading ? (
          <div className="p-4"><SkeletonRows /></div>
        ) : entries.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-slate-400">
            {t('leaderboard.noWorkers', 'No workers on the leaderboard yet.')}
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {entries.map((entry, i) => {
              const rank = i + 1
              const rankStyle = getRankStyle(rank)

              return (
                <div
                  key={entry.id}
                  className="grid grid-cols-12 gap-2 px-4 py-3.5 items-center hover:bg-slate-50 transition-colors"
                >
                  {/* Rank */}
                  <div className="col-span-1">
                    <span
                      className={`font-bold ${rankStyle.size}`}
                      style={{ color: rankStyle.color }}
                    >
                      {rank}
                    </span>
                  </div>

                  {/* Name */}
                  <div className="col-span-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shrink-0">
                        {(entry.display_name || 'A')[0].toUpperCase()}
                      </div>
                      <span className="text-sm font-medium text-slate-900 truncate">
                        {entry.display_name || 'Anonymous'}
                      </span>
                    </div>
                  </div>

                  {/* Reputation badge */}
                  <div className="col-span-2">
                    <ReputationBadge score={entry.reputation_score} size="sm" />
                  </div>

                  {/* Tasks completed */}
                  <div className="col-span-2 text-sm text-slate-600">
                    {entry.tasks_completed}
                  </div>

                  {/* Avg rating */}
                  <div className="col-span-3">
                    {entry.avg_rating != null && entry.avg_rating > 0 ? (
                      <div className="flex items-center gap-2">
                        <StarRating
                          score={entry.avg_rating < 10 ? entry.avg_rating * 20 : entry.avg_rating}
                        />
                        <span className="text-xs text-slate-500">
                          {entry.avg_rating < 10
                            ? entry.avg_rating.toFixed(1)
                            : Math.round(entry.avg_rating)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">N/A</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default Leaderboard
