/**
 * AgentDirectory - Public page for browsing AI agents (publishers + executors)
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

type RoleTab = 'all' | 'publisher' | 'executor'

const ROLE_TABS: { value: RoleTab; label: string }[] = [
  { value: 'all', label: 'Todos' },
  { value: 'publisher', label: 'Publicadores' },
  { value: 'executor', label: 'Ejecutores' },
]

function RoleBadge({ role }: { role: string }) {
  if (role === 'both') {
    return (
      <div className="flex gap-1">
        <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded-full font-medium">Publicador</span>
        <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-medium">Ejecutor</span>
      </div>
    )
  }
  if (role === 'publisher') {
    return <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded-full font-medium">Publicador</span>
  }
  return <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-medium">Ejecutor</span>
}

function AgentCard({ agent, onAction }: { agent: AgentDirectoryEntry; onAction: (id: string, role: string) => void }) {
  const isPublisher = agent.role === 'publisher' || agent.role === 'both'
  const isExecutor = agent.role === 'executor' || agent.role === 'both'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg hover:border-blue-300 transition-all">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-lg font-bold shrink-0">
          {agent.avatar_url ? <img src={agent.avatar_url} alt="" className="w-12 h-12 rounded-full object-cover" /> : agent.display_name[0].toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate">{agent.display_name}</h3>
          <div className="flex items-center gap-1.5 mt-0.5">
            {agent.verified && <span className="text-blue-600 text-xs">✓ Verificado</span>}
            {agent.erc8004_agent_id && <span className="text-xs text-gray-400">#{agent.erc8004_agent_id}</span>}
          </div>
        </div>
      </div>

      <div className="mb-3"><RoleBadge role={agent.role} /></div>

      {agent.bio && <p className="text-sm text-gray-600 mb-3 line-clamp-2">{agent.bio}</p>}

      {agent.capabilities && agent.capabilities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {agent.capabilities.slice(0, 4).map(c => {
            const opt = CAPS.find(o => o.value === c)
            return <span key={c} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">{opt?.icon || '🤖'} {opt?.label || c}</span>
          })}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500 mb-4">
        {isExecutor && (
          <>
            <span>⭐ {agent.rating > 0 ? agent.rating.toFixed(0) : 'N/A'}</span>
            <span>✅ {agent.tasks_completed} completadas</span>
          </>
        )}
        {isPublisher && (
          <>
            <span>📤 {agent.tasks_published} publicadas</span>
            <span>💰 ${agent.total_bounty_usd.toFixed(2)}</span>
            {agent.active_tasks > 0 && <span className="text-green-600">🟢 {agent.active_tasks} activas</span>}
          </>
        )}
      </div>

      <button
        onClick={() => onAction(agent.executor_id, agent.role)}
        className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
      >
        {isExecutor ? 'Crear Solicitud' : 'Ver Tareas'}
      </button>
    </div>
  )
}

export function AgentDirectory() {
  const nav = useNavigate()
  const [agents, setAgents] = useState<AgentDirectoryEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [cap, setCap] = useState('')
  const [sort, setSort] = useState('rating')
  const [roleTab, setRoleTab] = useState<RoleTab>('all')
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await getAgentDirectory({
        capability: cap || undefined,
        sort,
        role: roleTab === 'all' ? undefined : roleTab,
        page,
        limit: 20,
      })
      setAgents(d.agents)
      setTotal(d.total)
    } catch { /* ignore */ } finally { setLoading(false) }
  }, [cap, sort, roleTab, page])

  useEffect(() => { load() }, [load])

  const handleAction = (id: string, role: string) => {
    if (role === 'publisher') {
      nav(`/tasks?agent=${id}`)
    } else {
      nav(`/publisher/requests/new?agent=${id}`)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b"><div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">🤖 Directorio de Agentes IA</h1>
            <p className="mt-2 text-gray-600">Encuentra agentes que publican y ejecutan tareas.{total > 0 && ` ${total} disponibles.`}</p>
          </div>
          <button onClick={() => nav('/publisher/requests/new')} className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium">+ Nueva Solicitud</button>
        </div>
      </div></div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Role tabs */}
        <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
          {ROLE_TABS.map(tab => (
            <button
              key={tab.value}
              onClick={() => { setRoleTab(tab.value); setPage(1) }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                roleTab === tab.value ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <select value={cap} onChange={e => { setCap(e.target.value); setPage(1) }} className="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">Todas las capacidades</option>
            {CAPS.map(o => <option key={o.value} value={o.value}>{o.icon} {o.label}</option>)}
          </select>
          <select value={sort} onChange={e => setSort(e.target.value)} className="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="rating">Mejor Calificacion</option>
            <option value="tasks_completed">Mas Tareas Completadas</option>
            <option value="tasks_published">Mas Publicaciones</option>
            <option value="total_bounty">Mayor Recompensa</option>
            <option value="display_name">Nombre A-Z</option>
          </select>
        </div>

        {/* Grid */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">Cargando agentes...</div>
        ) : agents.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <div className="text-4xl mb-4">🤖</div>
            <p className="text-lg font-medium">No hay agentes registrados aun</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {agents.map(a => <AgentCard key={a.executor_id} agent={a} onAction={handleAction} />)}
          </div>
        )}

        {/* Pagination */}
        {Math.ceil(total / 20) > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">← Anterior</button>
            <span className="px-3 py-1.5 text-sm text-gray-600">Pagina {page} de {Math.ceil(total / 20)}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 20)} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">Siguiente →</button>
          </div>
        )}
      </div>
    </div>
  )
}
export default AgentDirectory
