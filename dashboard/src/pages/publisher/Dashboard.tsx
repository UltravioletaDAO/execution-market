/**
 * Human Publisher Dashboard - Manage H2A tasks
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { Task } from '../../types/database'
import { listH2ATasks, cancelH2ATask } from '../../services/h2a'

type Tab = 'active' | 'review' | 'history'

const STATUS_COLORS: Record<string, { color: string; icon: string }> = {
  published: { color: 'bg-yellow-100 text-yellow-800', icon: '🔍' },
  accepted: { color: 'bg-blue-100 text-blue-800', icon: '🤝' },
  in_progress: { color: 'bg-purple-100 text-purple-800', icon: '⚡' },
  submitted: { color: 'bg-orange-100 text-orange-800', icon: '📬' },
  completed: { color: 'bg-green-100 text-green-800', icon: '✅' },
  expired: { color: 'bg-gray-100 text-gray-800', icon: '⏰' },
  cancelled: { color: 'bg-red-100 text-red-800', icon: '❌' },
}

function TaskCard({ task, onReview, onCancel }: { task: Task; onReview?: (id: string) => void; onCancel?: (id: string) => void }) {
  const { t } = useTranslation()
  const meta = STATUS_COLORS[task.status] || { color: 'bg-gray-100 text-gray-800', icon: '❓' }
  const statusLabel = t(`publisher.dashboard.status.${task.status}`, task.status)
  return (
    <div className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium text-gray-900 flex-1 pr-2 truncate">{task.title}</h3>
        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${meta.color}`}>{meta.icon} {statusLabel}</span>
      </div>
      <p className="text-sm text-gray-500 line-clamp-2 mb-3">{task.instructions}</p>
      <div className="flex items-center gap-4 text-sm text-gray-400 mb-3">
        <span>💰 ${(task.bounty_usd || 0).toFixed(2)} USDC</span>
        <span>📅 {new Date(task.deadline).toLocaleDateString()}</span>
      </div>
      <div className="flex gap-2">
        {task.status === 'submitted' && onReview && <button onClick={() => onReview(task.id)} className="flex-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">⚡ {t('publisher.dashboard.review', 'Review')}</button>}
        {['published', 'accepted'].includes(task.status) && onCancel && <button onClick={() => onCancel(task.id)} className="px-3 py-1.5 border border-red-300 text-red-600 text-sm rounded-lg hover:bg-red-50">{t('common.cancel')}</button>}
      </div>
    </div>
  )
}

export function PublisherDashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('active')
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadTasks = useCallback(async () => {
    setLoading(true); setError(null)
    try { setTasks((await listH2ATasks({ my_tasks: true, limit: 50 })).tasks) }
    catch (e) { setError(e instanceof Error ? e.message : 'Error') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadTasks() }, [loadTasks])

  const active = tasks.filter(t => ['published', 'accepted', 'in_progress'].includes(t.status))
  const review = tasks.filter(t => ['submitted', 'verifying'].includes(t.status))
  const history = tasks.filter(t => ['completed', 'expired', 'cancelled', 'disputed'].includes(t.status))
  const displayed = tab === 'active' ? active : tab === 'review' ? review : history
  const totalSpent = tasks.filter(t => t.status === 'completed').reduce((s, t) => s + (t.bounty_usd || 0), 0)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div><h1 className="text-2xl font-bold">📋 {t('publisher.dashboard.title', 'Publisher Panel')}</h1><p className="text-sm text-gray-500 mt-1">{t('publisher.dashboard.subtitle', 'Manage your requests for AI agents')}</p></div>
            <button onClick={() => navigate('/publisher/requests/new')} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">+ {t('publisher.dashboard.newRequest', 'New Request')}</button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[{ n: active.length, l: t('publisher.dashboard.active', 'Active'), c: 'text-blue-600' }, { n: review.length, l: t('publisher.dashboard.toReview', 'To Review'), c: 'text-orange-600' }, { n: tasks.filter(t => t.status === 'completed').length, l: t('publisher.dashboard.completed', 'Completed'), c: 'text-green-600' }, { n: totalSpent, l: t('publisher.dashboard.spent', 'Spent'), c: 'text-gray-900', fmt: (v: number) => `$${v.toFixed(2)}` }].map((s, i) => (
            <div key={i} className="bg-white rounded-lg border p-4 text-center">
              <div className={`text-2xl font-bold ${s.c}`}>{s.fmt ? s.fmt(s.n) : s.n}</div>
              <div className="text-sm text-gray-500">{s.l}</div>
            </div>
          ))}
        </div>

        {review.length > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6 flex items-center gap-3">
            <span className="text-2xl">📬</span>
            <div className="flex-1"><p className="font-medium text-orange-900">{t('publisher.dashboard.pendingDeliveries', '{{count}} pending delivery(s)', { count: review.length })}</p><p className="text-sm text-orange-700">{t('publisher.dashboard.reviewAndApprove', 'Review and approve to complete payment.')}</p></div>
            <button onClick={() => setTab('review')} className="px-4 py-2 bg-orange-600 text-white rounded-lg text-sm">{t('publisher.dashboard.review', 'Review')}</button>
          </div>
        )}

        <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
          {([{ key: 'active' as Tab, label: t('publisher.dashboard.active', 'Active'), count: active.length }, { key: 'review' as Tab, label: t('publisher.dashboard.toReview', 'To Review'), count: review.length }, { key: 'history' as Tab, label: t('publisher.dashboard.history', 'History'), count: history.length }]).map(tb => (
            <button key={tb.key} onClick={() => setTab(tb.key)} className={`px-4 py-2 rounded-md text-sm font-medium ${tab === tb.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>
              {tb.label} {tb.count > 0 && <span className="ml-1.5 bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full text-xs">{tb.count}</span>}
            </button>
          ))}
        </div>

        {loading ? <div className="flex justify-center py-12 text-gray-500">{t('common.loading')}</div>
        : error ? <div className="text-center py-12"><p className="text-red-500 mb-4">{error}</p><button onClick={loadTasks} className="px-4 py-2 bg-blue-600 text-white rounded-lg">{t('common.retry')}</button></div>
        : displayed.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <div className="text-4xl mb-4">{tab === 'active' ? '📋' : tab === 'review' ? '📬' : '📚'}</div>
            <p className="text-lg font-medium">{tab === 'active' ? t('publisher.dashboard.noActiveRequests', 'No active requests') : tab === 'review' ? t('publisher.dashboard.noPendingDeliveries', 'No pending deliveries') : t('publisher.dashboard.noHistory', 'No history')}</p>
            {tab === 'active' && <button onClick={() => navigate('/publisher/requests/new')} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg">{t('publisher.dashboard.createFirstRequest', 'Create First Request')}</button>}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {displayed.map(task => <TaskCard key={task.id} task={task} onReview={id => navigate(`/publisher/requests/${id}/review`)} onCancel={async id => { if (confirm(t('publisher.dashboard.confirmCancel', 'Cancel?'))) { await cancelH2ATask(id); loadTasks() } }} />)}
          </div>
        )}
      </div>
    </div>
  )
}

export default PublisherDashboard
