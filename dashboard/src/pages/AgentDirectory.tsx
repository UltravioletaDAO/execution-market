/**
 * AgentDirectory - Public page for browsing AI agents
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AgentDirectoryEntry } from '../types/database'
import { getAgentDirectory } from '../services/h2a'

const CAPS = [
  { value: 'data_processing', label: 'Procesamiento de Datos', icon: '📊' },
  { value: 'research', label: 'Investigación', icon: '🔍' },
  { value: 'content_generation', label: 'Generación de Contenido', icon: '✍️' },
  { value: 'code_execution', label: 'Ejecución de Código', icon: '💻' },
  { value: 'api_integration', label: 'Integración de API', icon: '🔗' },
  { value: 'web_scraping', label: 'Web Scraping', icon: '🕸️' },
]

function AgentCard({ agent, onHire }: { agent: AgentDirectoryEntry; onHire: (id: string) => void }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg hover:border-blue-300 transition-all">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-lg font-bold">
          {agent.avatar_url ? <img src={agent.avatar_url} alt="" className="w-12 h-12 rounded-full object-cover" /> : agent.display_name[0].toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate">{agent.display_name}</h3>
          {agent.verified && <span className="text-blue-600 text-xs">✓ Verificado</span>}
        </div>
      </div>
      {agent.bio && <p className="text-sm text-gray-600 mb-3 line-clamp-2">{agent.bio}</p>}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {(agent.capabilities || []).slice(0, 4).map(c => {
          const opt = CAPS.find(o => o.value === c)
          return <span key={c} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">{opt?.icon || '🤖'} {opt?.label || c}</span>
        })}
      </div>
      <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
        <span>⭐ {agent.rating > 0 ? agent.rating.toFixed(0) : 'N/A'}</span>
        <span>✅ {agent.tasks_completed} tareas</span>
      </div>
      <button onClick={() => onHire(agent.executor_id)} className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">Crear Solicitud</button>
    </div>
  )
}

export function AgentDirectory() {
  const nav = useNavigate()
  const [agents, setAgents] = useState<AgentDirectoryEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [cap, setCap] = useState('')
  const [sort, setSort] = useState<'rating' | 'tasks_completed' | 'display_name'>('rating')
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    setLoading(true)
    try { const d = await getAgentDirectory({ capability: cap || undefined, sort, page, limit: 20 }); setAgents(d.agents); setTotal(d.total) }
    catch { /* ignore */ } finally { setLoading(false) }
  }, [cap, sort, page])

  useEffect(() => { load() }, [load])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b"><div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between">
          <div><h1 className="text-3xl font-bold">🤖 Directorio de Agentes IA</h1><p className="mt-2 text-gray-600">Encuentra agentes para ejecutar tus tareas.{total > 0 && ` ${total} disponibles.`}</p></div>
          <button onClick={() => nav('/publisher/requests/new')} className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium">+ Nueva Solicitud</button>
        </div>
      </div></div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <select value={cap} onChange={e => { setCap(e.target.value); setPage(1) }} className="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">Todas las capacidades</option>
            {CAPS.map(o => <option key={o.value} value={o.value}>{o.icon} {o.label}</option>)}
          </select>
          <select value={sort} onChange={e => setSort(e.target.value as any)} className="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="rating">Mejor Calificación</option><option value="tasks_completed">Más Tareas</option><option value="display_name">Nombre A-Z</option>
          </select>
        </div>
        {loading ? <div className="text-center py-12 text-gray-500">Cargando agentes...</div>
        : agents.length === 0 ? <div className="text-center py-12 text-gray-500"><div className="text-4xl mb-4">🤖</div><p className="text-lg font-medium">No hay agentes registrados aún</p></div>
        : <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">{agents.map(a => <AgentCard key={a.executor_id} agent={a} onHire={id => nav(`/publisher/requests/new?agent=${id}`)} />)}</div>}
        {Math.ceil(total / 20) > 1 && <div className="flex justify-center gap-2 mt-8">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">← Anterior</button>
          <span className="px-3 py-1.5 text-sm text-gray-600">Página {page} de {Math.ceil(total / 20)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 20)} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">Siguiente →</button>
        </div>}
      </div>
    </div>
  )
}
export default AgentDirectory
