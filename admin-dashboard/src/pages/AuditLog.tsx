import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet } from '../lib/api'

interface AuditLogProps {
  adminKey: string
}

// ---------------------------------------------------------------------------
// Config Changes (existing)
// ---------------------------------------------------------------------------

async function fetchAuditLog(adminKey: string, page: number = 1, category?: string) {
  const params: Record<string, string> = {
    limit: '50',
    offset: String((page - 1) * 50),
  }
  if (category) params.category = category
  return adminGet('/api/v1/admin/config/audit', adminKey, params)
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') return value.toString()
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function DiffView({ oldValue, newValue }: { oldValue: any; newValue: any }) {
  const oldStr = formatValue(oldValue)
  const newStr = formatValue(newValue)

  return (
    <div className="flex items-center gap-2 text-sm font-mono">
      <span className="text-red-400 line-through">{oldStr}</span>
      <span className="text-gray-500">&rarr;</span>
      <span className="text-green-400">{newStr}</span>
    </div>
  )
}

function ConfigChangesTab({ adminKey }: { adminKey: string }) {
  const [page, setPage] = useState(1)
  const [category, setCategory] = useState<string>('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['auditLog', adminKey, page, category],
    queryFn: () => fetchAuditLog(adminKey, page, category || undefined),
    enabled: !!adminKey,
  })

  if (isLoading) {
    return <div className="text-gray-400">Loading audit log...</div>
  }

  if (error) {
    return (
      <div className="text-red-400">
        Failed to load audit log. The audit endpoint may not be implemented yet.
      </div>
    )
  }

  const entries = data?.entries || []
  const count = data?.count || 0

  return (
    <div>
      <div className="flex justify-end mb-4">
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1) }}
          className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
        >
          <option value="">All Categories</option>
          <option value="fees">Fees</option>
          <option value="bounty">Bounty Limits</option>
          <option value="timeout">Timeouts</option>
          <option value="limits">Limits</option>
          <option value="feature">Features</option>
          <option value="x402">Payments (x402)</option>
        </select>
      </div>

      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Timestamp</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Config Key</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Change</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Reason</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Changed By</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry: any, index: number) => (
              <tr key={entry.id || index} className="border-t border-gray-700 hover:bg-gray-750">
                <td className="px-6 py-4 text-gray-400 text-sm">
                  {entry.changed_at ? new Date(entry.changed_at).toLocaleString() : 'N/A'}
                </td>
                <td className="px-6 py-4">
                  <span className="text-em-400 font-mono text-sm">{entry.config_key}</span>
                </td>
                <td className="px-6 py-4">
                  <DiffView oldValue={entry.old_value} newValue={entry.new_value} />
                </td>
                <td className="px-6 py-4 text-gray-300 text-sm max-w-xs truncate">
                  {entry.reason || <span className="text-gray-500 italic">No reason provided</span>}
                </td>
                <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                  {entry.changed_by?.slice(0, 8) || 'system'}
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                  No audit entries found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {count > 50 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-400">
            Page {page} of {Math.ceil(count / 50)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page * 50 >= count}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      <div className="mt-6 text-gray-500 text-sm">
        Showing {entries.length} of {count} entries
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Admin Actions (new)
// ---------------------------------------------------------------------------

const ACTION_TYPES = [
  'cancel_task',
  'update_user_status',
  'sweep_fees',
  'retry_payment',
  'update_task',
] as const

const ACTION_BADGE_STYLES: Record<string, string> = {
  cancel_task: 'bg-red-900/60 text-red-300 border-red-700',
  update_user_status: 'bg-yellow-900/60 text-yellow-300 border-yellow-700',
  sweep_fees: 'bg-blue-900/60 text-blue-300 border-blue-700',
  retry_payment: 'bg-purple-900/60 text-purple-300 border-purple-700',
  update_task: 'bg-gray-700 text-gray-300 border-gray-600',
}

const RESULT_BADGE_STYLES: Record<string, string> = {
  success: 'bg-green-900/60 text-green-300 border-green-700',
  error: 'bg-red-900/60 text-red-300 border-red-700',
}

async function fetchAdminActions(
  adminKey: string,
  page: number = 1,
  actionType?: string,
) {
  const params: Record<string, string> = {
    limit: '50',
    offset: String((page - 1) * 50),
  }
  if (actionType) params.action_type = actionType
  return adminGet('/api/v1/admin/actions/log', adminKey, params)
}

function truncateId(id: string | null | undefined, len = 8): string {
  if (!id) return '--'
  return id.length > len ? `${id.slice(0, len)}...` : id
}

function AdminActionsTab({ adminKey }: { adminKey: string }) {
  const [page, setPage] = useState(1)
  const [actionType, setActionType] = useState<string>('')
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['adminActions', adminKey, page, actionType],
    queryFn: () => fetchAdminActions(adminKey, page, actionType || undefined),
    enabled: !!adminKey,
  })

  if (isLoading) {
    return <div className="text-gray-400">Loading admin actions...</div>
  }

  if (error) {
    return (
      <div className="text-red-400">
        Failed to load admin actions log. The endpoint may not be deployed yet.
      </div>
    )
  }

  const entries = data?.entries || []
  const count = data?.count || 0

  return (
    <div>
      <div className="flex justify-end mb-4">
        <select
          value={actionType}
          onChange={(e) => { setActionType(e.target.value); setPage(1) }}
          className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
        >
          <option value="">All Actions</option>
          {ACTION_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Timestamp</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Action</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Target</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Actor</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Result</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry: any, index: number) => {
              const isExpanded = expandedRow === (entry.id || index)
              const badgeStyle =
                ACTION_BADGE_STYLES[entry.action_type] ||
                'bg-gray-700 text-gray-300 border-gray-600'
              const resultStyle =
                RESULT_BADGE_STYLES[entry.result] ||
                'bg-gray-700 text-gray-300 border-gray-600'
              const hasDetails =
                entry.details && Object.keys(entry.details).length > 0

              return (
                <tr
                  key={entry.id || index}
                  className="border-t border-gray-700 hover:bg-gray-750"
                >
                  <td className="px-6 py-4 text-gray-400 text-sm whitespace-nowrap">
                    {entry.created_at
                      ? new Date(entry.created_at).toLocaleString()
                      : 'N/A'}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${badgeStyle}`}
                    >
                      {entry.action_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {entry.target_type && (
                      <span className="text-gray-500 mr-1">{entry.target_type}:</span>
                    )}
                    <span className="text-gray-300 font-mono">
                      {truncateId(entry.target_id)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                    {truncateId(entry.actor_id)}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${resultStyle}`}
                    >
                      {entry.result}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {hasDetails ? (
                      <button
                        onClick={() =>
                          setExpandedRow(isExpanded ? null : (entry.id || String(index)))
                        }
                        className="text-em-400 hover:text-em-300 text-sm underline"
                      >
                        {isExpanded ? 'Hide' : 'View'}
                      </button>
                    ) : (
                      <span className="text-gray-600 text-sm">--</span>
                    )}
                    {isExpanded && hasDetails && (
                      <pre className="mt-2 p-3 bg-gray-900 rounded text-xs text-gray-300 font-mono overflow-x-auto max-w-md">
                        {JSON.stringify(entry.details, null, 2)}
                      </pre>
                    )}
                  </td>
                </tr>
              )
            })}
            {entries.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                  No admin action entries found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {count > 50 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-400">
            Page {page} of {Math.ceil(count / 50)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * 50 >= count}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      <div className="mt-6 text-gray-500 text-sm">
        Showing {entries.length} of {count} entries
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Lifecycle Audit (new)
// ---------------------------------------------------------------------------

interface LifecycleCheckpointGroup {
  done: number
  total: number
  items: Record<string, { done: boolean; at?: string; tx?: string }>
}

interface LifecycleTask {
  task_id: string
  title: string
  status: string
  skill_version: string | null
  network: string
  bounty_usdc: number
  created_at: string
  completion_pct: number
  checkpoints: {
    auth: LifecycleCheckpointGroup
    payment: LifecycleCheckpointGroup
    execution: LifecycleCheckpointGroup
    reputation: LifecycleCheckpointGroup
    cancelled: { done: boolean; at?: string }
    refunded: { done: boolean; at?: string; tx?: string }
    expired: { done: boolean; at?: string }
    fees_distributed: { done: boolean; at?: string; tx?: string }
  }
}

function GroupDotsAdmin({ done, total }: { done: number; total: number }) {
  const dots = []
  for (let i = 0; i < total; i++) {
    dots.push(
      <span
        key={i}
        className={`inline-block w-2 h-2 rounded-full ${i < done ? 'bg-green-400' : 'bg-gray-600'}`}
      />
    )
  }
  return (
    <div className="flex gap-0.5 items-center justify-center">
      {dots}
      <span className="ml-1 text-gray-500 text-xs">{done}/{total}</span>
    </div>
  )
}

function CompletionBarAdmin({ pct }: { pct: number }) {
  const color = pct >= 100 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-12 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-gray-400 text-xs w-7">{pct}%</span>
    </div>
  )
}

const ANOMALY_CHECKS = [
  {
    label: 'Payment released, no reputation',
    test: (t: LifecycleTask) =>
      t.checkpoints.payment.items.payment_released?.done &&
      !t.checkpoints.reputation.items.agent_rated_worker?.done &&
      t.status === 'completed',
  },
  {
    label: 'Escrow locked, no assignment',
    test: (t: LifecycleTask) =>
      t.checkpoints.payment.items.escrow_locked?.done &&
      !t.checkpoints.execution.items.worker_assigned?.done &&
      !['cancelled', 'expired'].includes(t.status),
  },
  {
    label: 'Stuck > terminal incomplete',
    test: (t: LifecycleTask) =>
      ['completed', 'cancelled', 'expired'].includes(t.status) &&
      t.completion_pct < 100,
  },
]

function LifecycleAuditTab({ adminKey }: { adminKey: string }) {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [issuesOnly, setIssuesOnly] = useState(false)

  const { data, isLoading, error, refetch, isFetching } = useQuery<{
    tasks: LifecycleTask[]
    total: number
  }>({
    queryKey: ['lifecycle-audit', adminKey, page, statusFilter, issuesOnly],
    queryFn: () => {
      const params: Record<string, string> = {
        page: String(page),
        limit: '50',
      }
      if (statusFilter) params.status = statusFilter
      if (issuesOnly) params.has_issue = 'true'
      return adminGet('/api/v1/tasks/audit-grid', adminKey, params)
    },
    enabled: !!adminKey,
    staleTime: 30_000,
  })

  const tasks = data?.tasks || []
  const total = data?.total || 0

  // Detect anomalies
  const anomalies = tasks.filter((t) =>
    ANOMALY_CHECKS.some((check) => check.test(t))
  )

  return (
    <div>
      {/* Anomaly Alert */}
      {anomalies.length > 0 && (
        <div className="mb-4 bg-red-900/20 border border-red-700 rounded-lg p-4">
          <p className="text-red-400 font-medium text-sm mb-2">
            {anomalies.length} anomal{anomalies.length === 1 ? 'y' : 'ies'} detected
          </p>
          <ul className="space-y-1">
            {anomalies.slice(0, 5).map((t) => {
              const issues = ANOMALY_CHECKS.filter((c) => c.test(t)).map((c) => c.label)
              return (
                <li key={t.task_id} className="text-sm">
                  <span className="text-gray-400 font-mono text-xs">{t.task_id.slice(0, 8)}...</span>
                  <span className="text-gray-500 mx-1">|</span>
                  <span className="text-red-300">{issues.join(', ')}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="bg-gray-700 text-white px-3 py-1.5 rounded border border-gray-600 text-sm"
        >
          <option value="">All Statuses</option>
          {['published', 'accepted', 'in_progress', 'submitted', 'completed', 'cancelled', 'expired'].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
          <input
            type="checkbox"
            checked={issuesOnly}
            onChange={(e) => { setIssuesOnly(e.target.checked); setPage(1) }}
            className="rounded border-gray-600 bg-gray-700"
          />
          Issues only
        </label>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="ml-auto px-3 py-1.5 bg-em-600 hover:bg-em-700 text-white text-sm rounded disabled:opacity-50"
        >
          {isFetching ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {isLoading ? (
        <div className="text-gray-400">Loading lifecycle audit...</div>
      ) : error ? (
        <div className="text-red-400">Failed to load lifecycle audit.</div>
      ) : (
        <>
          <div className="bg-gray-800 rounded-lg overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-700">
                <tr>
                  <th className="text-left px-4 py-3 text-gray-300 font-medium">Task</th>
                  <th className="text-left px-3 py-3 text-gray-300 font-medium">Skill</th>
                  <th className="text-left px-3 py-3 text-gray-300 font-medium">Net</th>
                  <th className="text-center px-3 py-3 text-gray-300 font-medium">Auth</th>
                  <th className="text-center px-3 py-3 text-gray-300 font-medium">Payment</th>
                  <th className="text-center px-3 py-3 text-gray-300 font-medium">Execution</th>
                  <th className="text-center px-3 py-3 text-gray-300 font-medium">Reputation</th>
                  <th className="text-center px-3 py-3 text-gray-300 font-medium">Progress</th>
                  <th className="text-center px-3 py-3 text-gray-300 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.task_id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="px-4 py-3">
                      <div className="text-gray-200 truncate max-w-[180px]" title={task.title}>{task.title}</div>
                      <div className="text-gray-500 font-mono text-xs">{task.task_id.slice(0, 8)}...</div>
                    </td>
                    <td className="px-3 py-3">
                      {task.skill_version ? (
                        <span className="text-em-400 font-mono text-xs">{task.skill_version}</span>
                      ) : (
                        <span className="text-gray-600 text-xs">--</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-gray-400 text-xs capitalize">{task.network}</td>
                    <td className="px-3 py-3"><GroupDotsAdmin done={task.checkpoints.auth.done} total={task.checkpoints.auth.total} /></td>
                    <td className="px-3 py-3"><GroupDotsAdmin done={task.checkpoints.payment.done} total={task.checkpoints.payment.total} /></td>
                    <td className="px-3 py-3"><GroupDotsAdmin done={task.checkpoints.execution.done} total={task.checkpoints.execution.total} /></td>
                    <td className="px-3 py-3"><GroupDotsAdmin done={task.checkpoints.reputation.done} total={task.checkpoints.reputation.total} /></td>
                    <td className="px-3 py-3"><CompletionBarAdmin pct={task.completion_pct} /></td>
                    <td className="px-3 py-3 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        task.status === 'completed' ? 'bg-green-900/60 text-green-300' :
                        task.status === 'cancelled' ? 'bg-red-900/60 text-red-300' :
                        task.status === 'expired' ? 'bg-gray-700 text-gray-300' :
                        'bg-blue-900/60 text-blue-300'
                      }`}>
                        {task.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {tasks.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-12 text-center text-gray-400">No tasks found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {total > 50 && (
            <div className="flex justify-center gap-2 mt-4">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1.5 bg-gray-700 text-white rounded disabled:opacity-50 text-sm">Previous</button>
              <span className="px-3 py-1.5 text-gray-400 text-sm">Page {page} of {Math.ceil(total / 50)}</span>
              <button onClick={() => setPage((p) => p + 1)} disabled={page * 50 >= total} className="px-3 py-1.5 bg-gray-700 text-white rounded disabled:opacity-50 text-sm">Next</button>
            </div>
          )}

          <div className="mt-4 text-gray-500 text-sm">
            Showing {tasks.length} of {total} tasks
          </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Component with Tab Bar
// ---------------------------------------------------------------------------

type AuditTab = 'config' | 'actions' | 'lifecycle'

export default function AuditLog({ adminKey }: AuditLogProps) {
  const [activeTab, setActiveTab] = useState<AuditTab>('lifecycle')

  const tabs: { id: AuditTab; label: string }[] = [
    { id: 'lifecycle', label: 'Lifecycle Audit' },
    { id: 'config', label: 'Config Changes' },
    { id: 'actions', label: 'Admin Actions' },
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-white">Audit Log</h1>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-2.5 text-sm font-medium rounded-t transition-colors ${
              activeTab === tab.id
                ? 'bg-gray-800 text-white border-b-2 border-em-400'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'lifecycle' && <LifecycleAuditTab adminKey={adminKey} />}
      {activeTab === 'config' && <ConfigChangesTab adminKey={adminKey} />}
      {activeTab === 'actions' && <AdminActionsTab adminKey={adminKey} />}
    </div>
  )
}
