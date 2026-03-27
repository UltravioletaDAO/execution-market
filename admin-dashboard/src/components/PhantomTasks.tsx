import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import TaskDetailModal from './TaskDetailModal'
import { adminGet } from '../lib/api'

interface PhantomTasksProps {
  adminKey: string
}

interface PhantomTask {
  task_id: string
  title: string | null
  bounty_usd: number
  task_status: string
  escrow_status: string | null
  created_at: string | null
  agent_id: string | null
}

interface PhantomTasksResponse {
  phantom_tasks: PhantomTask[]
  count: number
}

async function fetchPhantomTasks(adminKey: string): Promise<PhantomTasksResponse> {
  return adminGet('/api/v1/admin/tasks/phantom', adminKey)
}

const escrowStatusColors: Record<string, string> = {
  pending: 'bg-yellow-600',
  created: 'bg-yellow-500',
  expired: 'bg-gray-500',
  refunded: 'bg-orange-500',
  failed: 'bg-red-600',
}

const taskStatusColors: Record<string, string> = {
  submitted: 'bg-purple-500',
  completed: 'bg-green-500',
  verifying: 'bg-blue-500',
}

function SkeletonRow() {
  return (
    <tr className="border-t border-gray-700">
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i} className="px-6 py-4">
          <div className="h-4 bg-gray-700 rounded animate-pulse" />
        </td>
      ))}
    </tr>
  )
}

export function PhantomTasksBadge({ adminKey }: { adminKey: string }) {
  const { data } = useQuery({
    queryKey: ['phantom-tasks', adminKey],
    queryFn: () => fetchPhantomTasks(adminKey),
    enabled: !!adminKey,
    refetchInterval: 60_000,
  })

  const count = data?.count ?? 0
  if (count === 0) return null

  return (
    <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-bold text-white bg-red-600 rounded-full">
      {count}
    </span>
  )
}

export default function PhantomTasks({ adminKey }: PhantomTasksProps) {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['phantom-tasks', adminKey],
    queryFn: () => fetchPhantomTasks(adminKey),
    enabled: !!adminKey,
    refetchInterval: 60_000,
  })

  if (isLoading) {
    return (
      <div>
        <div className="flex items-center gap-3 mb-8">
          <h1 className="text-2xl font-bold text-white">Phantom Tasks Inspector</h1>
          <span className="h-6 w-12 bg-gray-700 rounded-full animate-pulse" />
        </div>
        <p className="text-gray-400 text-sm mb-6">
          Tasks in advanced lifecycle states (submitted, verifying, completed) with missing or unfunded escrows.
        </p>
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-700">
              <tr>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Task ID</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Title</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Agent</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Bounty</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Task Status</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Escrow Status</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-white mb-4">Phantom Tasks Inspector</h1>
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300">
          Failed to load phantom tasks: {(error as Error).message}
        </div>
      </div>
    )
  }

  const phantomTasks = data?.phantom_tasks ?? []
  const count = data?.count ?? 0

  return (
    <div>
      <div className="flex items-center gap-3 mb-2">
        <h1 className="text-2xl font-bold text-white">Phantom Tasks Inspector</h1>
        {count > 0 ? (
          <span className="inline-flex items-center justify-center min-w-[24px] h-6 px-2 text-sm font-bold text-white bg-red-600 rounded-full">
            {count}
          </span>
        ) : (
          <span className="inline-flex items-center justify-center h-6 px-2 text-sm font-bold text-white bg-green-600 rounded-full">
            0
          </span>
        )}
      </div>
      <p className="text-gray-400 text-sm mb-6">
        Tasks in advanced lifecycle states (submitted, verifying, completed) with missing or unfunded escrows.
      </p>

      {count === 0 ? (
        <div className="bg-green-900/20 border border-green-700/50 rounded-lg p-8 text-center">
          <div className="text-green-400 text-lg font-semibold mb-2">
            No phantom tasks detected
          </div>
          <p className="text-green-500/70 text-sm">
            All tasks in advanced states have properly funded escrows.
          </p>
        </div>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-700">
              <tr>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Task ID</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Title</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Agent</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Bounty</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Task Status</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Escrow Status</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {phantomTasks.map((task) => (
                <tr
                  key={task.task_id}
                  className="border-t border-gray-700 hover:bg-gray-750 cursor-pointer transition-colors"
                  onClick={() => setSelectedTaskId(task.task_id)}
                >
                  <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                    {task.task_id.slice(0, 8)}...
                  </td>
                  <td className="px-6 py-4 text-white">
                    {task.title
                      ? `${task.title.slice(0, 40)}${task.title.length > 40 ? '...' : ''}`
                      : <span className="text-gray-600">Untitled</span>
                    }
                  </td>
                  <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                    {task.agent_id
                      ? `${task.agent_id.slice(0, 6)}...${task.agent_id.slice(-4)}`
                      : <span className="text-gray-600">--</span>
                    }
                  </td>
                  <td className="px-6 py-4 text-white font-mono">
                    ${task.bounty_usd.toFixed(2)}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs text-white ${taskStatusColors[task.task_status] || 'bg-gray-500'}`}>
                      {task.task_status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {task.escrow_status ? (
                      <span className={`px-2 py-1 rounded text-xs text-white ${escrowStatusColors[task.escrow_status] || 'bg-red-700'}`}>
                        {task.escrow_status}
                      </span>
                    ) : (
                      <span className="px-2 py-1 rounded text-xs text-red-300 bg-red-900/50 border border-red-700/50">
                        MISSING
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-400 text-sm">
                    {task.created_at
                      ? new Date(task.created_at).toLocaleDateString()
                      : 'N/A'
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
