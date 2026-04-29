/**
 * AuditGrid — Task Lifecycle Audit Grid page.
 *
 * Shows a table of tasks with grouped lifecycle checkpoints:
 *   Auth | Payment | Execution | Reputation
 * Each group is expandable to show individual checkpoint items.
 * Real-time updates via WebSocket.
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { StatusBadge } from '../components/ui/StatusBadge'

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

// ─── Types ────────────────────────────────────────────────────────

interface CheckpointItem {
  done: boolean
  at?: string
  tx?: string
  agent_id?: string
  amount?: number
  worker_id?: string
  count?: number
  verdict?: string
  worker_amount?: number
  fee_amount?: number
}

interface CheckpointGroup {
  done: number
  total: number
  items: Record<string, CheckpointItem>
}

interface TerminalCheckpoint {
  done: boolean
  at?: string
  tx?: string
}

interface TaskCheckpoints {
  auth: CheckpointGroup
  payment: CheckpointGroup
  execution: CheckpointGroup
  reputation: CheckpointGroup
  cancelled: TerminalCheckpoint
  refunded: TerminalCheckpoint
  expired: TerminalCheckpoint
  fees_distributed: TerminalCheckpoint
}

interface AuditTask {
  task_id: string
  title: string
  status: string
  skill_version: string | null
  network: string
  token: string
  bounty_usdc: number
  agent_id: string
  erc8004_agent_id: string | null
  created_at: string
  checkpoints: TaskCheckpoints
  completion_pct: number
}

interface AuditGridResponse {
  tasks: AuditTask[]
  total: number
  page: number
  limit: number
  error?: string
}

// ─── Helpers ──────────────────────────────────────────────────────

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function GroupDots({ group }: { group: CheckpointGroup }) {
  const dots = []
  for (let i = 0; i < group.total; i++) {
    const done = i < group.done
    dots.push(
      <span
        key={i}
        className={`inline-block w-2.5 h-2.5 rounded-full ${
          done ? 'bg-zinc-900' : 'bg-zinc-300'
        }`}
        title={done ? 'Completed' : 'Pending'}
      />
    )
  }
  return <div className="flex gap-1 items-center">{dots}</div>
}

function CheckIcon() {
  return (
    <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

function XIcon() {
  return (
    <svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M18 12H6" />
    </svg>
  )
}

// ─── Expanded Group Detail ────────────────────────────────────────

const GROUP_LABELS: Record<string, Record<string, string>> = {
  auth: {
    auth_erc8128: 'ERC-8128 Wallet Auth',
    identity_erc8004: 'ERC-8004 Identity',
  },
  payment: {
    balance_sufficient: 'Balance Check',
    payment_auth_signed: 'Payment Auth Signed',
    escrow_locked: 'Escrow Locked',
    payment_released: 'Payment Released',
  },
  execution: {
    task_created: 'Task Created',
    worker_assigned: 'Worker Assigned',
    evidence_submitted: 'Evidence Submitted',
    ai_verified: 'AI Verified',
    approved: 'Approved',
  },
  reputation: {
    agent_rated_worker: 'Agent Rated Worker',
    worker_rated_agent: 'Worker Rated Agent',
  },
}

function ExpandedGroup({ group, groupKey }: { group: CheckpointGroup; groupKey: string }) {
  const labels = GROUP_LABELS[groupKey] || {}
  return (
    <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-zinc-200">
      {Object.entries(group.items).map(([key, item]) => (
        <div key={key} className="flex items-center gap-2 text-xs">
          {item.done ? <CheckIcon /> : <XIcon />}
          <span className={item.done ? 'text-zinc-900' : 'text-zinc-500'}>
            {labels[key] || key}
          </span>
          {item.at && (
            <span className="text-zinc-500 ml-auto">{formatDate(item.at)}</span>
          )}
          {item.tx && (
            <span className="text-zinc-700 font-mono text-[10px]" title={item.tx}>
              {item.tx.slice(0, 10)}...
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Completion Bar ───────────────────────────────────────────────

function CompletionBar({ pct }: { pct: number }) {
  const color = pct >= 100 ? 'bg-zinc-900' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-zinc-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs text-zinc-700 font-medium w-8">{pct}%</span>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────

export function AuditGrid() {
  const { t } = useTranslation()
  const { walletAddress } = useAuth()

  const [data, setData] = useState<AuditGridResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [networkFilter, setNetworkFilter] = useState('')
  const [versionFilter, setVersionFilter] = useState('')
  const [issuesOnly, setIssuesOnly] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState<Record<string, Set<string>>>({})

  const toggleGroup = useCallback((taskId: string, groupKey: string) => {
    setExpandedGroups(prev => {
      const taskGroups = new Set(prev[taskId] || [])
      if (taskGroups.has(groupKey)) {
        taskGroups.delete(groupKey)
      } else {
        taskGroups.add(groupKey)
      }
      return { ...prev, [taskId]: taskGroups }
    })
  }, [])

  const fetchGrid = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('limit', '50')
      if (statusFilter) params.set('status', statusFilter)
      if (networkFilter) params.set('network', networkFilter)
      if (versionFilter) params.set('skill_version', versionFilter)
      if (issuesOnly) params.set('has_issue', 'true')

      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (walletAddress) headers['X-Agent-Wallet'] = walletAddress

      const res = await fetch(`${API_BASE}/api/v1/tasks/audit-grid?${params}`, { headers })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json: AuditGridResponse = await res.json()
      setData(json)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter, networkFilter, versionFilter, issuesOnly, walletAddress])

  useEffect(() => { fetchGrid() }, [fetchGrid])

  // WebSocket: listen for CheckpointUpdated events → debounced refresh
  useEffect(() => {
    const WS_BASE = (API_BASE || '').replace(/^http/, 'ws')
    if (!WS_BASE || !walletAddress) return

    let ws: WebSocket | null = null
    let refreshTimer: ReturnType<typeof setTimeout> | null = null

    try {
      ws = new WebSocket(`${WS_BASE}/ws?user_id=${walletAddress}&user_type=agent`)
      ws.onmessage = (msg) => {
        try {
          const evt = JSON.parse(msg.data)
          if (evt.event === 'CheckpointUpdated') {
            // Debounce: batch rapid checkpoint updates into one refresh
            if (refreshTimer) clearTimeout(refreshTimer)
            refreshTimer = setTimeout(() => fetchGrid(), 2000)
          }
        } catch { /* ignore parse errors */ }
      }
      ws.onerror = () => {} // Silent — WS is optional
    } catch { /* WS unavailable */ }

    return () => {
      if (refreshTimer) clearTimeout(refreshTimer)
      if (ws && ws.readyState === WebSocket.OPEN) ws.close()
    }
  }, [walletAddress, fetchGrid])

  // Fallback: auto-refresh every 60s
  useEffect(() => {
    const interval = setInterval(fetchGrid, 60_000)
    return () => clearInterval(interval)
  }, [fetchGrid])

  const totalPages = data ? Math.ceil(data.total / 50) : 0

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">
            {t('auditGrid.title', 'Task Lifecycle Audit')}
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {data ? `${data.total} tasks` : 'Loading...'}
          </p>
        </div>
        <button
          onClick={fetchGrid}
          disabled={loading}
          className="px-4 py-2 bg-zinc-900 text-white text-sm rounded-lg hover:bg-zinc-800 disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          className="px-3 py-1.5 text-sm border border-zinc-300 rounded-lg bg-white"
        >
          <option value="">All Statuses</option>
          {['published', 'accepted', 'in_progress', 'submitted', 'verifying', 'completed', 'cancelled', 'expired'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={networkFilter}
          onChange={e => { setNetworkFilter(e.target.value); setPage(1) }}
          className="px-3 py-1.5 text-sm border border-zinc-300 rounded-lg bg-white"
        >
          <option value="">All Networks</option>
          {['base', 'ethereum', 'polygon', 'arbitrum', 'optimism', 'avalanche', 'celo', 'monad', 'skale', 'solana'].map(n => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
        <input
          type="text"
          value={versionFilter}
          onChange={e => { setVersionFilter(e.target.value); setPage(1) }}
          placeholder="Skill version (e.g. 4.1.0)"
          className="px-3 py-1.5 text-sm border border-zinc-300 rounded-lg bg-white w-40"
        />
        <label className="flex items-center gap-2 text-sm text-zinc-700 cursor-pointer">
          <input
            type="checkbox"
            checked={issuesOnly}
            onChange={e => { setIssuesOnly(e.target.checked); setPage(1) }}
            className="rounded border-zinc-300"
          />
          Issues only
        </label>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {/* Grid Table */}
      <div className="bg-white rounded-xl shadow-sm border border-zinc-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-200 bg-zinc-50">
              <th className="text-left px-4 py-3 font-medium text-zinc-700 w-52">Task</th>
              <th className="text-left px-3 py-3 font-medium text-zinc-700 w-16">Skill</th>
              <th className="text-left px-3 py-3 font-medium text-zinc-700 w-20">Network</th>
              <th className="text-right px-3 py-3 font-medium text-zinc-700 w-16">Bounty</th>
              <th className="text-center px-3 py-3 font-medium text-zinc-700 w-24">
                <button className="hover:text-zinc-900">Auth</button>
              </th>
              <th className="text-center px-3 py-3 font-medium text-zinc-700 w-28">
                <button className="hover:text-zinc-900">Payment</button>
              </th>
              <th className="text-center px-3 py-3 font-medium text-zinc-700 w-32">
                <button className="hover:text-zinc-900">Execution</button>
              </th>
              <th className="text-center px-3 py-3 font-medium text-zinc-700 w-24">
                <button className="hover:text-zinc-900">Reputation</button>
              </th>
              <th className="text-center px-3 py-3 font-medium text-zinc-700 w-20">Progress</th>
              <th className="text-center px-3 py-3 font-medium text-zinc-700 w-24">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data && (
              <tr>
                <td colSpan={10} className="px-4 py-12 text-center text-zinc-500">
                  Loading audit grid...
                </td>
              </tr>
            )}
            {data && data.tasks.length === 0 && (
              <tr>
                <td colSpan={10} className="px-4 py-12 text-center text-zinc-500">
                  No tasks found
                </td>
              </tr>
            )}
            {data?.tasks.map(task => {
              const taskExpanded = expandedGroups[task.task_id] || new Set()
              return (
                <tr key={task.task_id} className="border-b border-zinc-100 hover:bg-zinc-50">
                  {/* Task Title */}
                  <td className="px-4 py-3">
                    <div className="font-medium text-zinc-900 truncate max-w-[200px]" title={task.title}>
                      {task.title}
                    </div>
                    <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                      {task.task_id.slice(0, 8)}...
                    </div>
                  </td>
                  {/* Skill Version */}
                  <td className="px-3 py-3">
                    {task.skill_version ? (
                      <span className="inline-block px-1.5 py-0.5 bg-zinc-100 text-zinc-700 rounded text-xs font-mono">
                        {task.skill_version}
                      </span>
                    ) : (
                      <span className="text-zinc-300 text-xs">--</span>
                    )}
                  </td>
                  {/* Network */}
                  <td className="px-3 py-3 text-xs text-zinc-700 capitalize">{task.network}</td>
                  {/* Bounty */}
                  <td className="px-3 py-3 text-right text-xs font-medium">${task.bounty_usdc.toFixed(2)}</td>
                  {/* Auth Group */}
                  <td className="px-3 py-3 text-center">
                    <button onClick={() => toggleGroup(task.task_id, 'auth')} className="hover:bg-zinc-100 rounded p-1">
                      <GroupDots group={task.checkpoints.auth} />
                    </button>
                    {taskExpanded.has('auth') && (
                      <ExpandedGroup group={task.checkpoints.auth} groupKey="auth" />
                    )}
                  </td>
                  {/* Payment Group */}
                  <td className="px-3 py-3 text-center">
                    <button onClick={() => toggleGroup(task.task_id, 'payment')} className="hover:bg-zinc-100 rounded p-1">
                      <GroupDots group={task.checkpoints.payment} />
                    </button>
                    {taskExpanded.has('payment') && (
                      <ExpandedGroup group={task.checkpoints.payment} groupKey="payment" />
                    )}
                  </td>
                  {/* Execution Group */}
                  <td className="px-3 py-3 text-center">
                    <button onClick={() => toggleGroup(task.task_id, 'execution')} className="hover:bg-zinc-100 rounded p-1">
                      <GroupDots group={task.checkpoints.execution} />
                    </button>
                    {taskExpanded.has('execution') && (
                      <ExpandedGroup group={task.checkpoints.execution} groupKey="execution" />
                    )}
                  </td>
                  {/* Reputation Group */}
                  <td className="px-3 py-3 text-center">
                    <button onClick={() => toggleGroup(task.task_id, 'reputation')} className="hover:bg-zinc-100 rounded p-1">
                      <GroupDots group={task.checkpoints.reputation} />
                    </button>
                    {taskExpanded.has('reputation') && (
                      <ExpandedGroup group={task.checkpoints.reputation} groupKey="reputation" />
                    )}
                  </td>
                  {/* Completion */}
                  <td className="px-3 py-3">
                    <CompletionBar pct={task.completion_pct} />
                  </td>
                  {/* Status */}
                  <td className="px-3 py-3 text-center">
                    <StatusBadge status={task.status} size="sm" label={task.status} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm bg-white border border-zinc-300 rounded-lg disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-zinc-700">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1.5 text-sm bg-white border border-zinc-300 rounded-lg disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

export default AuditGrid
