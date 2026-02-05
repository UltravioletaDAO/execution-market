import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet } from '../lib/api'

interface AuditLogProps {
  adminKey: string
}

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
      <span className="text-gray-500">→</span>
      <span className="text-green-400">{newStr}</span>
    </div>
  )
}

export default function AuditLog({ adminKey }: AuditLogProps) {
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
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-white">Configuration Audit Log</h1>
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
