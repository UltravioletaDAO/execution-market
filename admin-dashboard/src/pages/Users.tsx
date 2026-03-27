import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useMemo } from 'react'
import { adminGet, adminPut } from '../lib/api'

interface UsersProps {
  adminKey: string
}

type UserType = 'agents' | 'workers'

interface AgentUser {
  id: string
  wallet_address: string
  name: string
  tier: string
  created_at: string | null
  task_count: number
  total_spent_usd: number
  status: 'active' | 'suspended'
  usage_count: number
}

interface WorkerUser {
  id: string
  wallet_address: string
  name: string
  created_at: string | null
  task_count: number
  total_earned_usd: number
  reputation_score: number
  status: 'active' | 'suspended'
  success_rate: number | null
}

type User = AgentUser | WorkerUser

interface UsersResponse {
  users: User[]
  count: number
  offset: number
  stats: {
    total_agents?: number
    active_agents?: number
    total_workers?: number
    active_workers?: number
  }
}

function isWorkerUser(_user: User, type: UserType): _user is WorkerUser {
  return type === 'workers'
}

async function fetchUsers(adminKey: string, type: UserType, page: number = 1): Promise<UsersResponse> {
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
  user: User
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
  const displayName = user.name || (
    user.wallet_address
      ? `${user.wallet_address.slice(0, 6)}...${user.wallet_address.slice(-4)}`
      : 'Unknown'
  )
  const walletShort = user.wallet_address
    ? `${user.wallet_address.slice(0, 6)}...${user.wallet_address.slice(-4)}`
    : 'No wallet'

  return (
    <div className="bg-gray-700 rounded-lg p-4 relative">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center text-lg">
            {isAgent ? '\u{1F916}' : '\u{1F477}'}
          </div>
          <div>
            <p className="text-white text-sm font-medium">{displayName}</p>
            <p className="text-gray-400 text-xs font-mono">{walletShort}</p>
          </div>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowActions(!showActions)}
            className="text-gray-400 hover:text-white p-1"
          >
            \u22EE
          </button>
          {showActions && (
            <div className="absolute right-0 top-8 bg-gray-800 border border-gray-600 rounded shadow-lg z-10 min-w-32">
              {user.status === 'active' ? (
                <button
                  onClick={() => mutation.mutate('suspended')}
                  disabled={mutation.isPending}
                  className="block w-full text-left px-4 py-2 text-red-400 hover:bg-gray-700 text-sm disabled:opacity-50"
                >
                  {mutation.isPending ? 'Updating...' : 'Suspend'}
                </button>
              ) : (
                <button
                  onClick={() => mutation.mutate('active')}
                  disabled={mutation.isPending}
                  className="block w-full text-left px-4 py-2 text-green-400 hover:bg-gray-700 text-sm disabled:opacity-50"
                >
                  {mutation.isPending ? 'Updating...' : 'Activate'}
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
            ${isAgent
              ? ((user as AgentUser).total_spent_usd || 0).toFixed(2)
              : ((user as WorkerUser).total_earned_usd || 0).toFixed(2)
            }
          </p>
        </div>
        {isWorkerUser(user, type) && (
          <>
            <div>
              <p className="text-gray-400">Reputation</p>
              <p className="text-yellow-400 font-semibold">
                \u2B50 {user.reputation_score != null ? user.reputation_score.toFixed(0) : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-gray-400">Success Rate</p>
              <p className="text-green-400 font-semibold">
                {user.success_rate != null ? `${(user.success_rate * 100).toFixed(0)}%` : 'N/A'}
              </p>
            </div>
          </>
        )}
        {isAgent && (
          <div>
            <p className="text-gray-400">Tier</p>
            <p className="text-blue-400 font-semibold capitalize">{(user as AgentUser).tier || 'free'}</p>
          </div>
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

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="bg-gray-700 rounded-lg p-4 animate-pulse">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-600" />
            <div className="flex-1">
              <div className="h-4 bg-gray-600 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-600 rounded w-1/2" />
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="h-8 bg-gray-600 rounded" />
            <div className="h-8 bg-gray-600 rounded" />
          </div>
          <div className="mt-4 flex justify-between">
            <div className="h-5 bg-gray-600 rounded w-16" />
            <div className="h-4 bg-gray-600 rounded w-24" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function Users({ adminKey }: UsersProps) {
  const [userType, setUserType] = useState<UserType>('agents')
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch both agents and workers stats in parallel
  const agentsQuery = useQuery<UsersResponse>({
    queryKey: ['users', adminKey, 'agents', page],
    queryFn: () => fetchUsers(adminKey, 'agents', userType === 'agents' ? page : 1),
    enabled: !!adminKey,
  })

  const workersQuery = useQuery<UsersResponse>({
    queryKey: ['users', adminKey, 'workers', page],
    queryFn: () => fetchUsers(adminKey, 'workers', userType === 'workers' ? page : 1),
    enabled: !!adminKey,
  })

  const activeQuery = userType === 'agents' ? agentsQuery : workersQuery
  const { data, isLoading, error, refetch } = activeQuery

  // Combine stats from both queries
  const agentStats = agentsQuery.data?.stats || {}
  const workerStats = workersQuery.data?.stats || {}

  const users = data?.users || []
  const count = data?.count || 0

  // Client-side search filter
  const filteredUsers = useMemo(() => {
    if (!searchQuery.trim()) return users
    const q = searchQuery.toLowerCase()
    return users.filter((user) =>
      (user.name && user.name.toLowerCase().includes(q)) ||
      (user.wallet_address && user.wallet_address.toLowerCase().includes(q))
    )
  }, [users, searchQuery])

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-white">Users Management</h1>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Total Agents</p>
          <p className="text-2xl font-bold text-white">
            {agentsQuery.isLoading ? '\u2014' : agentStats.total_agents || 0}
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Active Agents</p>
          <p className="text-2xl font-bold text-green-400">
            {agentsQuery.isLoading ? '\u2014' : agentStats.active_agents || 0}
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Total Workers</p>
          <p className="text-2xl font-bold text-white">
            {workersQuery.isLoading ? '\u2014' : workerStats.total_workers || 0}
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Active Workers</p>
          <p className="text-2xl font-bold text-green-400">
            {workersQuery.isLoading ? '\u2014' : workerStats.active_workers || 0}
          </p>
        </div>
      </div>

      {/* Tabs + Search */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => { setUserType('agents'); setPage(1); setSearchQuery('') }}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              userType === 'agents'
                ? 'bg-em-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Agents
          </button>
          <button
            onClick={() => { setUserType('workers'); setPage(1); setSearchQuery('') }}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              userType === 'workers'
                ? 'bg-em-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Workers
          </button>
        </div>
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search by name or wallet address..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full sm:max-w-sm px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-em-500 text-sm"
          />
        </div>
      </div>

      {/* Users Grid */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : error ? (
        <div className="text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-6 text-center">
          Failed to load {userType}. Check that the admin API is reachable.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredUsers.map((user) => (
              <UserCard
                key={user.id}
                user={user}
                type={userType}
                adminKey={adminKey}
                onStatusChange={() => refetch()}
              />
            ))}
            {filteredUsers.length === 0 && (
              <div className="col-span-full text-center py-12 text-gray-400">
                {searchQuery
                  ? `No ${userType} matching "${searchQuery}"`
                  : `No ${userType} found`
                }
              </div>
            )}
          </div>

          {!searchQuery && count > 20 && (
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
        </>
      )}
    </div>
  )
}
