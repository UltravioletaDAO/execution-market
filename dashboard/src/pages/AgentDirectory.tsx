/**
 * AgentDirectory - Public page for browsing AI agents (publishers + executors)
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AgentDirectoryEntry } from '../types/database'
import { getAgentDirectory } from '../services/h2a'
import { ReputationBadge } from '../components/ReputationBadge'

const CAPS: { value: string; label: string; color: string }[] = [
  { value: 'data_processing', label: 'Procesamiento de Datos', color: 'bg-indigo-50 text-indigo-700' },
  { value: 'research', label: 'Investigacion', color: 'bg-emerald-50 text-emerald-700' },
  { value: 'content_creation', label: 'Creacion de Contenido', color: 'bg-pink-50 text-pink-700' },
  { value: 'content_generation', label: 'Generacion de Contenido', color: 'bg-pink-50 text-pink-700' },
  { value: 'code_generation', label: 'Generacion de Codigo', color: 'bg-amber-50 text-amber-700' },
  { value: 'code_execution', label: 'Ejecucion de Codigo', color: 'bg-amber-50 text-amber-700' },
  { value: 'analysis', label: 'Analisis', color: 'bg-cyan-50 text-cyan-700' },
  { value: 'automation', label: 'Automatizacion', color: 'bg-violet-50 text-violet-700' },
  { value: 'api_integration', label: 'Integracion de API', color: 'bg-orange-50 text-orange-700' },
  { value: 'web_scraping', label: 'Web Scraping', color: 'bg-teal-50 text-teal-700' },
]

function capMeta(c: string) {
  return CAPS.find(o => o.value === c) || { value: c, label: c, color: 'bg-gray-50 text-gray-700' }
}

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

function AgentCard({ agent, onClick }: { agent: AgentDirectoryEntry; onClick: () => void }) {
  const isPublisher = agent.role === 'publisher' || agent.role === 'both'
  const isExecutor = agent.role === 'executor' || agent.role === 'both'

  return (
    <div onClick={onClick} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg hover:border-blue-300 transition-all cursor-pointer">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-lg font-bold shrink-0">
          {agent.avatar_url ? <img src={agent.avatar_url} alt="" className="w-12 h-12 rounded-full object-cover" /> : agent.display_name[0].toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate">{agent.display_name}</h3>
          <div className="flex items-center gap-1.5 mt-0.5">
            {agent.verified && <span className="text-blue-600 text-xs">Verificado</span>}
            {agent.erc8004_agent_id && <span className="text-xs text-gray-400">#{agent.erc8004_agent_id}</span>}
          </div>
        </div>
      </div>

      <div className="mb-3"><RoleBadge role={agent.role} /></div>

      {agent.bio && <p className="text-sm text-gray-600 mb-3 line-clamp-2">{agent.bio}</p>}

      {agent.capabilities && agent.capabilities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {agent.capabilities.slice(0, 4).map(c => {
            const m = capMeta(c)
            return <span key={c} className={`text-xs px-2 py-0.5 rounded-full font-medium ${m.color}`}>{m.label}</span>
          })}
          {agent.capabilities.length > 4 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">+{agent.capabilities.length - 4}</span>
          )}
        </div>
      )}

      {agent.pricing && (agent.pricing.min_bounty_usd || agent.pricing.avg_response_minutes) && (
        <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
          {agent.pricing.min_bounty_usd != null && agent.pricing.max_bounty_usd != null && (
            <span>${agent.pricing.min_bounty_usd.toFixed(2)} - ${agent.pricing.max_bounty_usd.toFixed(2)}</span>
          )}
          {agent.pricing.avg_response_minutes != null && (
            <span>~{agent.pricing.avg_response_minutes} min respuesta</span>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
        {isExecutor && (
          <>
            {agent.rating > 0 && <ReputationBadge score={agent.rating} size="sm" />}
            <span>{agent.tasks_completed} completadas</span>
          </>
        )}
        {isPublisher && (
          <>
            <span>{agent.tasks_published} publicadas</span>
            <span>${agent.total_bounty_usd.toFixed(2)}</span>
            {agent.active_tasks > 0 && <span className="text-green-600">{agent.active_tasks} activas</span>}
          </>
        )}
      </div>
    </div>
  )
}

/** Detail modal shown when clicking an agent card */
function AgentDetailModal({ agent, onClose }: { agent: AgentDirectoryEntry; onClose: () => void }) {
  const nav = useNavigate()
  const isPublisher = agent.role === 'publisher' || agent.role === 'both'
  const isExecutor = agent.role === 'executor' || agent.role === 'both'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-start gap-4 p-6 pb-4 border-b">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold shrink-0">
            {agent.avatar_url ? <img src={agent.avatar_url} alt="" className="w-16 h-16 rounded-full object-cover" /> : agent.display_name[0].toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-bold text-gray-900 truncate">{agent.display_name}</h2>
            <div className="flex items-center gap-2 mt-1">
              {agent.verified && <span className="text-blue-600 text-sm">Verificado</span>}
              {agent.erc8004_agent_id && <span className="text-sm bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">ERC-8004 #{agent.erc8004_agent_id}</span>}
            </div>
            <div className="mt-2"><RoleBadge role={agent.role} /></div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-6 pb-4">
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-gray-900">{agent.tasks_completed}</div>
            <div className="text-xs text-gray-500">Completadas</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-gray-900">{agent.tasks_published}</div>
            <div className="text-xs text-gray-500">Publicadas</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-gray-900">{agent.avg_rating > 0 ? `${Math.round(agent.avg_rating < 10 ? agent.avg_rating * 20 : agent.avg_rating)}/100` : '-'}</div>
            <div className="text-xs text-gray-500">Calificacion</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-gray-900">{agent.rating > 0 ? <ReputationBadge score={agent.rating} size="sm" /> : '-'}</div>
            <div className="text-xs text-gray-500">Reputacion</div>
          </div>
        </div>

        {/* Bio */}
        {agent.bio && (
          <div className="px-6 pb-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Acerca de</h3>
            <p className="text-sm text-gray-700 leading-relaxed">{agent.bio}</p>
          </div>
        )}

        {/* Capabilities */}
        {agent.capabilities && agent.capabilities.length > 0 && (
          <div className="px-6 pb-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Capacidades</h3>
            <div className="flex flex-wrap gap-2">
              {agent.capabilities.map(c => {
                const m = capMeta(c)
                return <span key={c} className={`text-xs px-2.5 py-1 rounded-full font-medium ${m.color}`}>{m.label}</span>
              })}
            </div>
          </div>
        )}

        {/* Pricing */}
        {agent.pricing && (agent.pricing.min_bounty_usd || agent.pricing.avg_response_minutes) && (
          <div className="px-6 pb-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Precios</h3>
            <div className="flex flex-wrap gap-4 text-sm text-gray-700">
              {agent.pricing.min_bounty_usd != null && agent.pricing.max_bounty_usd != null && (
                <span>Rango: ${agent.pricing.min_bounty_usd.toFixed(2)} - ${agent.pricing.max_bounty_usd.toFixed(2)}</span>
              )}
              {agent.pricing.avg_response_minutes != null && (
                <span>Respuesta: ~{agent.pricing.avg_response_minutes} min</span>
              )}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 p-6 pt-4 border-t">
          {isExecutor && (
            <button
              onClick={() => { onClose(); nav(`/publisher/requests/new?agent=${agent.executor_id}`) }}
              className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
            >
              Crear Solicitud
            </button>
          )}
          {isPublisher && (
            <button
              onClick={() => { onClose(); nav(`/tasks?agent=${agent.executor_id}`) }}
              className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
            >
              Ver Tareas
            </button>
          )}
        </div>
      </div>
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
  const [selectedAgent, setSelectedAgent] = useState<AgentDirectoryEntry | null>(null)

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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b"><div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Directorio de Agentes IA</h1>
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
            {CAPS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
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
            <p className="text-lg font-medium">No hay agentes registrados aun</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {agents.map(a => <AgentCard key={a.executor_id} agent={a} onClick={() => setSelectedAgent(a)} />)}
          </div>
        )}

        {/* Pagination */}
        {Math.ceil(total / 20) > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">Anterior</button>
            <span className="px-3 py-1.5 text-sm text-gray-600">Pagina {page} de {Math.ceil(total / 20)}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 20)} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">Siguiente</button>
          </div>
        )}
      </div>

      {/* Agent Detail Modal */}
      {selectedAgent && <AgentDetailModal agent={selectedAgent} onClose={() => setSelectedAgent(null)} />}
    </div>
  )
}
export default AgentDirectory
