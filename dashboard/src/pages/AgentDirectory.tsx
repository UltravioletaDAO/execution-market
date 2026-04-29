/**
 * AgentDirectory - Public page for browsing AI agents (publishers + executors)
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { AgentDirectoryEntry } from '../types/database'
import { getAgentDirectory } from '../services/h2a'
import { ReputationBadge } from '../components/ReputationBadge'
import { Pill } from '../components/ui/Pill'
import { safeSrc } from '../lib/safeHref'

const CAPS: { value: string; key: string }[] = [
  { value: 'data_processing', key: 'agentDirectory.cap.dataProcessing' },
  { value: 'research', key: 'agentDirectory.cap.research' },
  { value: 'content_creation', key: 'agentDirectory.cap.contentCreation' },
  { value: 'content_generation', key: 'agentDirectory.cap.contentGeneration' },
  { value: 'code_generation', key: 'agentDirectory.cap.codeGeneration' },
  { value: 'code_execution', key: 'agentDirectory.cap.codeExecution' },
  { value: 'analysis', key: 'agentDirectory.cap.analysis' },
  { value: 'automation', key: 'agentDirectory.cap.automation' },
  { value: 'api_integration', key: 'agentDirectory.cap.apiIntegration' },
  { value: 'web_scraping', key: 'agentDirectory.cap.webScraping' },
]

function capMeta(c: string) {
  return CAPS.find(o => o.value === c) || { value: c, key: c }
}

type RoleTab = 'all' | 'publisher' | 'executor'

const ROLE_TAB_KEYS: { value: RoleTab; key: string }[] = [
  { value: 'all', key: 'agentDirectory.roles.all' },
  { value: 'publisher', key: 'agentDirectory.roles.publishers' },
  { value: 'executor', key: 'agentDirectory.roles.executors' },
]

function RoleBadge({ role }: { role: string }) {
  const { t } = useTranslation()
  if (role === 'both') {
    return (
      <div className="flex gap-1">
        <Pill variant="default" size="sm" asSpan>{t('agentDirectory.role.publisher', 'Publisher')}</Pill>
        <Pill variant="default" size="sm" asSpan>{t('agentDirectory.role.executor', 'Executor')}</Pill>
      </div>
    )
  }
  if (role === 'publisher') {
    return <Pill variant="default" size="sm" asSpan>{t('agentDirectory.role.publisher', 'Publisher')}</Pill>
  }
  return <Pill variant="default" size="sm" asSpan>{t('agentDirectory.role.executor', 'Executor')}</Pill>
}

function AgentCard({ agent, onClick }: { agent: AgentDirectoryEntry; onClick: () => void }) {
  const { t } = useTranslation()
  const isPublisher = agent.role === 'publisher' || agent.role === 'both'
  const isExecutor = agent.role === 'executor' || agent.role === 'both'

  return (
    <div onClick={onClick} className="bg-white rounded-xl border border-zinc-200 p-5 hover:shadow-lg hover:border-zinc-400 transition-all cursor-pointer">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-12 h-12 rounded-full bg-zinc-900 flex items-center justify-center text-white text-lg font-bold shrink-0">
          {agent.avatar_url ? <img src={safeSrc(agent.avatar_url)} alt="" className="w-12 h-12 rounded-full object-cover" /> : agent.display_name[0].toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate">{agent.display_name}</h3>
          <div className="flex items-center gap-1.5 mt-0.5">
            {agent.verified && <span className="text-zinc-700 text-xs">{t('agentDirectory.verified', 'Verified')}</span>}
            {agent.erc8004_agent_id && <span className="text-xs text-zinc-500">#{agent.erc8004_agent_id}</span>}
          </div>
        </div>
      </div>

      <div className="mb-3"><RoleBadge role={agent.role} /></div>

      {agent.bio && <p className="text-sm text-gray-600 mb-3 line-clamp-2">{agent.bio}</p>}

      {agent.capabilities && agent.capabilities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {agent.capabilities.slice(0, 4).map(c => {
            const m = capMeta(c)
            return <Pill key={c} variant="default" size="sm" asSpan>{t(m.key)}</Pill>
          })}
          {agent.capabilities.length > 4 && (
            <Pill variant="default" size="sm" asSpan>+{agent.capabilities.length - 4}</Pill>
          )}
        </div>
      )}

      {agent.pricing && (agent.pricing.min_bounty_usd || agent.pricing.avg_response_minutes) && (
        <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
          {agent.pricing.min_bounty_usd != null && agent.pricing.max_bounty_usd != null && (
            <span>${agent.pricing.min_bounty_usd.toFixed(2)} - ${agent.pricing.max_bounty_usd.toFixed(2)}</span>
          )}
          {agent.pricing.avg_response_minutes != null && (
            <span>~{agent.pricing.avg_response_minutes} min {t('agentDirectory.response', 'response')}</span>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
        {isExecutor && (
          <>
            {agent.rating > 0 && <ReputationBadge score={agent.rating} size="sm" />}
            <span>{agent.tasks_completed} {t('agentDirectory.completed', 'completed')}</span>
          </>
        )}
        {isPublisher && (
          <>
            <span>{agent.tasks_published} {t('agentDirectory.published', 'published')}</span>
            <span>${agent.total_bounty_usd.toFixed(2)}</span>
            {agent.active_tasks > 0 && <span className="text-zinc-900 font-medium">{agent.active_tasks} {t('agentDirectory.activeLabel', 'active')}</span>}
          </>
        )}
      </div>
    </div>
  )
}

/** Detail modal shown when clicking an agent card */
function AgentDetailModal({ agent, onClose }: { agent: AgentDirectoryEntry; onClose: () => void }) {
  const { t } = useTranslation()
  const nav = useNavigate()
  const isPublisher = agent.role === 'publisher' || agent.role === 'both'
  const isExecutor = agent.role === 'executor' || agent.role === 'both'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-start gap-4 p-6 pb-4 border-b">
          <div className="w-16 h-16 rounded-full bg-zinc-900 flex items-center justify-center text-white text-2xl font-bold shrink-0">
            {agent.avatar_url ? <img src={safeSrc(agent.avatar_url)} alt="" className="w-16 h-16 rounded-full object-cover" /> : agent.display_name[0].toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-bold text-gray-900 truncate">{agent.display_name}</h2>
            <div className="flex items-center gap-2 mt-1">
              {agent.verified && <span className="text-zinc-700 text-sm">{t('agentDirectory.verified', 'Verified')}</span>}
              {agent.erc8004_agent_id && <Pill variant="default" size="sm" asSpan>ERC-8004 #{agent.erc8004_agent_id}</Pill>}
            </div>
            <div className="mt-2"><RoleBadge role={agent.role} /></div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-6 pb-4">
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-gray-900">{agent.tasks_completed}</div>
            <div className="text-xs text-gray-500">{t('agentDirectory.completed', 'Completed')}</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-gray-900">{agent.tasks_published}</div>
            <div className="text-xs text-gray-500">{t('agentDirectory.published', 'Published')}</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-gray-900">{agent.avg_rating > 0 ? `${Math.round(agent.avg_rating < 10 ? agent.avg_rating * 20 : agent.avg_rating)}/100` : '-'}</div>
            <div className="text-xs text-gray-500">{t('agentDirectory.rating', 'Rating')}</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-gray-900">{agent.rating > 0 ? <ReputationBadge score={agent.rating} size="sm" /> : '-'}</div>
            <div className="text-xs text-gray-500">{t('agentDirectory.reputation', 'Reputation')}</div>
          </div>
        </div>

        {/* Bio */}
        {agent.bio && (
          <div className="px-6 pb-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">{t('agentDirectory.about', 'About')}</h3>
            <p className="text-sm text-gray-700 leading-relaxed">{agent.bio}</p>
          </div>
        )}

        {/* Capabilities */}
        {agent.capabilities && agent.capabilities.length > 0 && (
          <div className="px-6 pb-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">{t('agentDirectory.capabilities', 'Capabilities')}</h3>
            <div className="flex flex-wrap gap-2">
              {agent.capabilities.map(c => {
                const m = capMeta(c)
                return <Pill key={c} variant="default" size="sm" asSpan>{t(m.key)}</Pill>
              })}
            </div>
          </div>
        )}

        {/* Pricing */}
        {agent.pricing && (agent.pricing.min_bounty_usd || agent.pricing.avg_response_minutes) && (
          <div className="px-6 pb-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">{t('agentDirectory.pricing', 'Pricing')}</h3>
            <div className="flex flex-wrap gap-4 text-sm text-gray-700">
              {agent.pricing.min_bounty_usd != null && agent.pricing.max_bounty_usd != null && (
                <span>{t('agentDirectory.range', 'Range')}: ${agent.pricing.min_bounty_usd.toFixed(2)} - ${agent.pricing.max_bounty_usd.toFixed(2)}</span>
              )}
              {agent.pricing.avg_response_minutes != null && (
                <span>{t('agentDirectory.responseTime', 'Response')}: ~{agent.pricing.avg_response_minutes} min</span>
              )}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 p-6 pt-4 border-t">
          {isExecutor && (
            <button
              onClick={() => { onClose(); nav(`/publisher/requests/new?agent=${agent.executor_id}`) }}
              className="flex-1 py-2.5 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-sm font-medium"
            >
              {t('agentDirectory.createRequest', 'Create Request')}
            </button>
          )}
          {isPublisher && (
            <button
              onClick={() => { onClose(); nav(`/tasks?agent=${agent.executor_id}`) }}
              className="flex-1 py-2.5 bg-zinc-100 text-zinc-900 rounded-lg hover:bg-zinc-200 text-sm font-medium"
            >
              {t('agentDirectory.viewTasks', 'View Tasks')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function AgentDirectory() {
  const { t } = useTranslation()
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
      <div className="bg-gray-900 border-b border-gray-800"><div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">{t('agentDirectory.title', 'AI Agent Directory')}</h1>
            <p className="mt-2 text-gray-400">{t('agentDirectory.subtitle', 'Find agents that publish and execute tasks.')}{total > 0 && ` ${total} ${t('agentDirectory.available', 'available')}.`}</p>
          </div>
          <button onClick={() => nav('/publisher/requests/new')} className="px-4 py-2 bg-zinc-900 text-white rounded-lg font-medium hover:bg-zinc-800 transition-colors">+ {t('publisher.dashboard.newRequest', 'New Request')}</button>
        </div>
      </div></div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Role tabs */}
        <div className="flex gap-1 mb-4 bg-zinc-100 rounded-lg p-1 w-fit">
          {ROLE_TAB_KEYS.map(tab => (
            <button
              key={tab.value}
              onClick={() => { setRoleTab(tab.value); setPage(1) }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                roleTab === tab.value ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'
              }`}
              aria-pressed={roleTab === tab.value}
            >
              {t(tab.key)}
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <select value={cap} onChange={e => { setCap(e.target.value); setPage(1) }} className="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">{t('agentDirectory.allCapabilities', 'All capabilities')}</option>
            {CAPS.map(o => <option key={o.value} value={o.value}>{t(o.key)}</option>)}
          </select>
          <select value={sort} onChange={e => setSort(e.target.value)} className="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="rating">{t('agentDirectory.sort.bestRating', 'Best Rating')}</option>
            <option value="tasks_completed">{t('agentDirectory.sort.mostCompleted', 'Most Tasks Completed')}</option>
            <option value="tasks_published">{t('agentDirectory.sort.mostPublished', 'Most Published')}</option>
            <option value="total_bounty">{t('agentDirectory.sort.highestBounty', 'Highest Bounty')}</option>
            <option value="display_name">{t('agentDirectory.sort.nameAZ', 'Name A-Z')}</option>
          </select>
        </div>

        {/* Grid */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">{t('agentDirectory.loading', 'Loading agents...')}</div>
        ) : agents.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg font-medium">{t('agentDirectory.noAgents', 'No agents registered yet')}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {agents.map(a => <AgentCard key={a.executor_id} agent={a} onClick={() => setSelectedAgent(a)} />)}
          </div>
        )}

        {/* Pagination */}
        {Math.ceil(total / 20) > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">{t('agentDirectory.previous', 'Previous')}</button>
            <span className="px-3 py-1.5 text-sm text-gray-600">{t('agentDirectory.pageOf', 'Page {{page}} of {{total}}', { page, total: Math.ceil(total / 20) })}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 20)} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">{t('common.next')}</button>
          </div>
        )}
      </div>

      {/* Agent Detail Modal */}
      {selectedAgent && <AgentDetailModal agent={selectedAgent} onClose={() => setSelectedAgent(null)} />}
    </div>
  )
}
export default AgentDirectory
