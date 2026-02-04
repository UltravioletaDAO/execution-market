// Execution Market: Task History Component
import { useTranslation } from 'react-i18next'
import type { TaskHistoryItem } from '../../hooks/useProfile'

interface TaskHistoryProps {
  history: TaskHistoryItem[]
  loading: boolean
  hasMore: boolean
  onLoadMore: () => void
}

// Category icons
const categoryIcons: Record<string, string> = {
  physical_presence: '📍',
  knowledge_access: '📚',
  human_authority: '✍️',
  simple_action: '✅',
  digital_physical: '🔗',
}

// Status badges
function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()

  const configs: Record<string, { bg: string; text: string; label: string }> = {
    approved: { bg: 'bg-green-100', text: 'text-green-700', label: t('status.approved', 'Approved') },
    rejected: { bg: 'bg-red-100', text: 'text-red-700', label: t('status.rejected', 'Rejected') },
    pending: { bg: 'bg-amber-100', text: 'text-amber-700', label: t('status.pending', 'Pending') },
  }

  const config = configs[status] || configs.pending

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  )
}

// Format relative time
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
  return `${Math.floor(diffDays / 365)} years ago`
}

export function TaskHistory({ history, loading, hasMore, onLoadMore }: TaskHistoryProps) {
  const { t } = useTranslation()

  if (loading && history.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          {[1, 2, 3].map(i => (
            <div key={i} className="flex gap-4">
              <div className="w-10 h-10 bg-gray-200 rounded-lg"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-2/3 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/3"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100">
        <h3 className="text-gray-900 font-semibold">
          {t('profile.taskHistory', 'Task History')}
        </h3>
      </div>

      {/* History list */}
      {history.length === 0 ? (
        <div className="p-6 text-center">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <p className="text-gray-500 text-sm">
            {t('profile.noHistory', 'No completed tasks yet')}
          </p>
          <p className="text-gray-400 text-xs mt-1">
            {t('profile.startEarning', 'Accept a task to start earning')}
          </p>
        </div>
      ) : (
        <div className="divide-y divide-gray-50">
          {history.map(item => (
            <div key={item.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
              <div className="flex items-start gap-3">
                {/* Category icon */}
                <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center text-lg flex-shrink-0">
                  {categoryIcons[item.task_category] || '📋'}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-gray-900 font-medium text-sm truncate">
                      {item.task_title}
                    </h4>
                    <StatusBadge status={item.status} />
                  </div>

                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-gray-500 text-xs">
                      {formatRelativeTime(item.submitted_at)}
                    </span>

                    {/* Payment amount */}
                    {item.status === 'approved' && (
                      <span className="text-green-600 text-xs font-medium">
                        +${(item.payment_amount || item.bounty_usd).toFixed(2)}
                      </span>
                    )}

                    {/* Bounty for pending/rejected */}
                    {item.status !== 'approved' && (
                      <span className="text-gray-400 text-xs">
                        ${item.bounty_usd.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Load more button */}
      {hasMore && (
        <div className="px-6 py-4 border-t border-gray-100">
          <button
            onClick={onLoadMore}
            disabled={loading}
            className="w-full py-2 text-blue-600 text-sm font-medium hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {t('common.loading', 'Loading...')}
              </span>
            ) : (
              t('common.loadMore', 'Load More')
            )}
          </button>
        </div>
      )}
    </div>
  )
}
