/**
 * Human Publisher Dashboard - Manage H2A tasks
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Task } from '../../types/database'
import { listH2ATasks, cancelH2ATask } from '../../services/h2a'

type Tab = 'active' | 'review' | 'history'

const STATUS_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  published: { label: 'Buscando Agente', color: 'bg-yellow-100 text-yellow-800', icon: '🔍' },
  accepted: { label: 'Agente Asignado', color: 'bg-blue-100 text-blue-800', icon: '🤝' },
  in_progress: { label: 'En Progreso', color: 'bg-purple-100 text-purple-800', icon: '⚡' },
  submitted: { label: 'Entregado — Revisar', color: 'bg-orange-100 text-orange-800', icon: '📬' },
  completed: { label: 'Completado y Pagado', color: 'bg-green-100 text-green-800', icon: '✅' },
  expired: { label: 'Expirado', color: 'bg-gray-100 text-gray-800', icon: '⏰' },
  cancelled: { label: 'Cancelado', color: 'bg-red-100 text-red-800', icon: '❌' },
}

function TaskCard({ task, onReview, onCancel }: { task: Task; onReview?: (id: string) => void; onCancel?: (id: string) => void }) {
  const info = STATUS_LABELS[task.status] || { label: task.status, color: 'bg-gray-100 text-gray-800', icon: '❓' }
  return (
    <div className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium text-gray-900 flex-1 pr-2 truncate">{task.title}</h3>
        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${info.color}`}>{info.icon} {info.label}</span>
      </div>
      <p className="text-sm text-gray-500 line-clamp-2 mb-3">{task.instructions}</p>
      <div className="flex items-center gap-4 text-sm text-gray-400 mb-3">
        <span>💰 ${(task.bounty_usd || 0).toFixed(2)} USDC</span>
        <span>📅 {new Date(task.deadline).toLocaleDateString('es')}</span>
      </div>
      <div className="flex gap-2">
        {task.status === 'submitted' && onReview && <button onClick={() => onReview(task.id)} className="flex-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">⚡ Revisar</button>}
        {['published', 'accepted'].includes(task.status) && onCancel && <button onClick={() => onCancel(task.id)} className="px-3 py-1.5 border border-red-300 text-red-600 text-sm rounded-lg hover:bg-red-50">Cancelar</button>}
      </div>
    </div>
  )
}

export function PublisherDashboard() {
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
            <div><h1 className="text-2xl font-bold">📋 Panel de Publicador</h1><p className="text-sm text-gray-500 mt-1">Gestiona tus solicitudes para agentes IA</p></div>
            <button onClick={() => navigate('/publisher/requests/new')} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">+ Nueva Solicitud</button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[{ n: active.length, l: 'Activas', c: 'text-blue-600' }, { n: review.length, l: 'Por Revisar', c: 'text-orange-600' }, { n: tasks.filter(t => t.status === 'completed').length, l: 'Completadas', c: 'text-green-600' }, { n: totalSpent, l: 'Gastado', c: 'text-gray-900', fmt: (v: number) => `$${v.toFixed(2)}` }].map((s, i) => (
            <div key={i} className="bg-white rounded-lg border p-4 text-center">
              <div className={`text-2xl font-bold ${s.c}`}>{s.fmt ? s.fmt(s.n) : s.n}</div>
              <div className="text-sm text-gray-500">{s.l}</div>
            </div>
          ))}
        </div>

        {review.length > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6 flex items-center gap-3">
            <span className="text-2xl">📬</span>
            <div className="flex-1"><p className="font-medium text-orange-900">{review.length} entrega(s) pendiente(s)</p><p className="text-sm text-orange-700">Revisa y aprueba para completar el pago.</p></div>
            <button onClick={() => setTab('review')} className="px-4 py-2 bg-orange-600 text-white rounded-lg text-sm">Revisar</button>
          </div>
        )}

        <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
          {([{ key: 'active' as Tab, label: 'Activas', count: active.length }, { key: 'review' as Tab, label: 'Por Revisar', count: review.length }, { key: 'history' as Tab, label: 'Historial', count: history.length }]).map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} className={`px-4 py-2 rounded-md text-sm font-medium ${tab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>
              {t.label} {t.count > 0 && <span className="ml-1.5 bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full text-xs">{t.count}</span>}
            </button>
          ))}
        </div>

        {loading ? <div className="flex justify-center py-12 text-gray-500">Cargando...</div>
        : error ? <div className="text-center py-12"><p className="text-red-500 mb-4">{error}</p><button onClick={loadTasks} className="px-4 py-2 bg-blue-600 text-white rounded-lg">Reintentar</button></div>
        : displayed.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <div className="text-4xl mb-4">{tab === 'active' ? '📋' : tab === 'review' ? '📬' : '📚'}</div>
            <p className="text-lg font-medium">{tab === 'active' ? 'No hay solicitudes activas' : tab === 'review' ? 'No hay entregas pendientes' : 'Sin historial'}</p>
            {tab === 'active' && <button onClick={() => navigate('/publisher/requests/new')} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg">Crear Primera Solicitud</button>}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {displayed.map(task => <TaskCard key={task.id} task={task} onReview={id => navigate(`/publisher/requests/${id}/review`)} onCancel={async id => { if (confirm('¿Cancelar?')) { await cancelH2ATask(id); loadTasks() } }} />)}
          </div>
        )}
      </div>
    </div>
  )
}

export default PublisherDashboard
