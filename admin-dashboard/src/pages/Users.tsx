import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet, adminPut } from '../lib/api'

interface UsersProps {
  adminKey: string
}

type UserType = 'agents' | 'workers'

async function fetchUsers(adminKey: string, type: UserType, page: number = 1) {
  return adminGet(`/api/v1/admin/users/${type}`, adminKey, {
    limit: '20',
    offset: String((page - 1) * 20),
  })
}

async function updateUserStatus(adminKey: string, userId: string, status: string) {
  return adminPut(`/api/v1/admin/users/${userId}/status`, adminKey, { status })
}

function UserCard({
  user,
  type,
  adminKey,
  onStatusChange,
}: {
  user: any
  type: UserType
  adminKey: string
  onStatusChange: () => void
}) {
  const queryClient = useQueryClient()
  const [showActions, setShowActions] = useState(false)

  const mutation = useMutation({
    mutationFn: (newStatus: string) => updateUserStatus(adminKey, user.id, newStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      onStatusChange()
      setShowActions(false)
    },
  })

  const isAgent = type === 'agents'

  return (
    <div className="bg-gray-700 rounded-lg p-4 relative">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center text-lg">
            {isAgent ? '🤖' : '👷'}
          </div>
          <div>
            <p className="text-white text-sm font-medium">
              {user.name || user.wallet_address?.slice(0, 6) + '...' + user.wallet_address?.slice(-4)}
            </p>
            <p className="text-gray-400 text-xs font-mono">
              {user.wallet_address?.slice(0, 6)}...{user.wallet_address?.slice(-4)}
            </p>
          </div>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowActions(!showActions)}
            className="text-gray-400 hover:text-white p-1"
          >
            ⋮
          </button>
          {showActions && (
            <div className="absolute right-0 top-8 bg-gray-800 border border-gray-600 rounded shadow-lg z-10 min-w-32">
              {user.status === 'active' ? (
                <button
                  onClick={() => mutation.mutate('suspended')}
                  className="block w-full text-left px-4 py-2 text-red-400 hover:bg-gray-700 text-sm"
                >
                  Suspend
                </button>
              ) : (
                <button
                  onClick={() => mutation.mutate('active')}
                  className="block w-full text-left px-4 py-2 text-green-400 hover:bg-gray-700 text-sm"
                >
                  Activate
                </button>
              )}
              <button
                onClick={() => setShowActions(false)}
                className="block w-full text-left px-4 py-2 text-gray-400 hover:bg-gray-700 text-sm"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-400">Tasks</p>
          <p className="text-white font-semibold">{user.task_count || 0}</p>
        </div>
        <div>
          <p className="text-gray-400">{isAgent ? 'Spent' : 'Earned'}</p>
          <p className="text-white font-semibold">
            ${(isAgent ? user.total_spent_usd : user.total_earned_usd || 0).toFixed(2)}
          </p>
        </div>
        {!isAgent && (
          <>
            <div>
              <p className="text-gray-400">Reputation</p>
              <p className="text-yellow-400 font-semibold">
                ⭐ {user.reputation_score?.toFixed(0) || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-gray-400">Success Rate</p>
              <p className="text-green-400 font-semibold">
                {user.success_rate ? `${(user.success_rate * 100).toFixed(0)}%` : 'N/A'}
              </p>
            </div>
          </>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <span className={`px-2 py-1 rounded text-xs ${
          user.status === 'active' ? 'bg-green-500/20 text-green-400' :
          user.status === 'suspended' ? 'bg-red-500/20 text-red-400' :
          'bg-gray-500/20 text-gray-400'
        }`}>
          {user.status || 'active'}
        </span>
        <span className="text-gray-500 text-xs">
          Joined {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
        </span>
      </div>
    </div>
  )
}

export default function Users({ adminKey }: UsersProps) {
  const [userType, setUserType] = useState<UserType>('agents')
  const [page, setPage] = useState(1)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['users', adminKey, userType, page],
    queryFn: () => fetchUsers(adminKey, userType, page),
    enabled: !!adminKey,
  })

  if (isLoading) {
    return <div className="text-gray-400">Loading users...</div>
  }

  if (error) {
    return (
      <div className="text-red-400">
        Failed to load users. The admin users endpoint may not be implemented yet.
      </div>
    )
  }

  const users = data?.users || []
  const count = data?.count || 0
  const stats = data?.stats || {}

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-white">Users Management</h1>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Total Agents</p>
          <p className="text-2xl font-bold text-white">{stats.total_agents || 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Active Agents</p>
          <p className="text-2xl font-bold text-green-400">{stats.active_agents || 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Total Workers</p>
          <p className="text-2xl font-bold text-white">{stats.total_workers || 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Active Workers</p>
          <p className="text-2xl font-bold text-green-400">{stats.active_workers || 0}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={() => { setUserType('agents'); setPage(1) }}
          className={`px-6 py-2 rounded-lg font-medium transition-colors ${
            userType === 'agents'
              ? 'bg-em-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          🤖 Agents
        </button>
        <button
          onClick={() => { setUserType('workers'); setPage(1) }}
          className={`px-6 py-2 rounded-lg font-medium transition-colors ${
            userType === 'workers'
              ? 'bg-em-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          👷 Workers
        </button>
      </div>

      {/* Users Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {users.map((user: any) => (
          <UserCard
            key={user.id}
            user={user}
            type={userType}
            adminKey={adminKey}
            onStatusChange={() => refetch()}
          />
        ))}
        {users.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-400">
            No {userType} found
          </div>
        )}
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
    </div>
  )
}
