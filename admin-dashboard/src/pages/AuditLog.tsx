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
// Main Component with Tab Bar
// ---------------------------------------------------------------------------

type AuditTab = 'config' | 'actions'

export default function AuditLog({ adminKey }: AuditLogProps) {
  const [activeTab, setActiveTab] = useState<AuditTab>('config')

  const tabs: { id: AuditTab; label: string }[] = [
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
      {activeTab === 'config' && <ConfigChangesTab adminKey={adminKey} />}
      {activeTab === 'actions' && <AdminActionsTab adminKey={adminKey} />}
    </div>
  )
}
