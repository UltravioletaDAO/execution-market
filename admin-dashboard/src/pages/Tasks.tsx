import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import TaskDetailModal from '../components/TaskDetailModal'

interface TasksProps {
  adminKey: string
}

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

async function fetchTasks(adminKey: string, status?: string, page: number = 1, search?: string) {
  const params = new URLSearchParams({
    admin_key: adminKey,
    limit: '20',
    offset: String((page - 1) * 20),
  })
  if (status) params.set('status', status)
  if (search) params.set('search', search)

  const response = await fetch(`${API_BASE}/api/v1/admin/tasks?${params}`)
  if (!response.ok) {
    throw new Error('Failed to fetch tasks')
  }
  return response.json()
}

const statusColors: Record<string, string> = {
  published: 'bg-blue-500',
  accepted: 'bg-yellow-500',
  submitted: 'bg-purple-500',
  completed: 'bg-green-500',
  expired: 'bg-gray-500',
  cancelled: 'bg-red-500',
  disputed: 'bg-red-600',
  partial: 'bg-teal-500',
}

export default function Tasks({ adminKey }: TasksProps) {
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [page, setPage] = useState(1)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['tasks', adminKey, statusFilter, page, search],
    queryFn: () => fetchTasks(adminKey, statusFilter, page, search),
    enabled: !!adminKey,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  if (isLoading) {
    return <div className="text-gray-400">Loading tasks...</div>
  }

  if (error) {
    return (
      <div className="text-red-400">
        Failed to load tasks. The admin tasks endpoint may not be implemented yet.
      </div>
    )
  }

  const tasks = data?.tasks || []
  const count = data?.count || 0
  const stats = data?.stats || {}

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-white">Tasks Manager</h1>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
        {Object.entries(stats).map(([status, count]) => (
          <button
            key={status}
            onClick={() => { setStatusFilter(status === statusFilter ? '' : status); setPage(1) }}
            className={`p-3 rounded-lg text-center transition-all ${
              status === statusFilter
                ? 'ring-2 ring-em-500 bg-gray-700'
                : 'bg-gray-800 hover:bg-gray-700'
            }`}
          >
            <p className="text-gray-400 text-xs capitalize">{status}</p>
            <p className="text-xl font-bold text-white">{count as number}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
        >
          <option value="">All Statuses</option>
          <option value="published">Published</option>
          <option value="accepted">Accepted</option>
          <option value="submitted">Submitted</option>
          <option value="completed">Completed</option>
          <option value="expired">Expired</option>
          <option value="cancelled">Cancelled</option>
          <option value="disputed">Disputed</option>
        </select>

        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search tasks..."
            className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 w-64"
          />
          <button
            type="submit"
            className="bg-em-600 hover:bg-em-700 text-white px-4 py-2 rounded"
          >
            Search
          </button>
          {search && (
            <button
              type="button"
              onClick={() => { setSearch(''); setSearchInput(''); setPage(1) }}
              className="text-gray-400 hover:text-white px-2"
            >
              Clear
            </button>
          )}
        </form>
      </div>

      {/* Tasks Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">ID</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Title</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Agent</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Worker</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Bounty</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Tier</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Status</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Created</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task: any) => (
              <tr
                key={task.id}
                className="border-t border-gray-700 hover:bg-gray-750 cursor-pointer"
                onClick={() => setSelectedTaskId(task.id)}
              >
                <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                  {task.id?.slice(0, 8)}...
                </td>
                <td className="px-6 py-4 text-white">
                  {task.title?.slice(0, 40)}{task.title?.length > 40 ? '...' : ''}
                </td>
                <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                  {task.agent_id?.slice(0, 6)}...{task.agent_id?.slice(-4)}
                </td>
                <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                  {task.worker_id
                    ? `${task.worker_id?.slice(0, 6)}...${task.worker_id?.slice(-4)}`
                    : <span className="text-gray-600">—</span>
                  }
                </td>
                <td className="px-6 py-4 text-white font-mono">
                  ${task.bounty_usd?.toFixed(2)}
                </td>
                <td className="px-6 py-4 text-gray-400 text-xs">
                  {task.bounty_usd < 5 ? 'Micro' : task.bounty_usd < 50 ? 'Standard' : task.bounty_usd < 200 ? 'Premium' : 'Enterprise'}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs text-white ${statusColors[task.status] || 'bg-gray-500'}`}>
                    {task.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-400 text-sm">
                  {task.created_at ? new Date(task.created_at).toLocaleDateString() : 'N/A'}
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedTaskId(task.id) }}
                    className="text-em-400 hover:text-em-300 text-sm"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr>
                <td colSpan={9} className="px-6 py-8 text-center text-gray-400">
                  No tasks found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {count > 20 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-400">
            Page {page} of {Math.ceil(count / 20)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page * 20 >= count}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Task Detail Modal */}
      {selectedTaskId && (
        <TaskDetailModal
          taskId={selectedTaskId}
          adminKey={adminKey}
          onClose={() => setSelectedTaskId(null)}
        />
      )}
    </div>
  )
}
