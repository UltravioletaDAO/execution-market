import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

interface TaskDetailModalProps {
  taskId: string
  adminKey: string
  onClose: () => void
}

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

async function fetchTaskDetail(adminKey: string, taskId: string) {
  const response = await fetch(`${API_BASE}/api/v1/admin/tasks/${taskId}?admin_key=${adminKey}`)
  if (!response.ok) {
    throw new Error('Failed to fetch task')
  }
  return response.json()
}

async function updateTask(adminKey: string, taskId: string, updates: any) {
  const response = await fetch(`${API_BASE}/api/v1/admin/tasks/${taskId}?admin_key=${adminKey}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!response.ok) {
    throw new Error('Failed to update task')
  }
  return response.json()
}

async function cancelTask(adminKey: string, taskId: string, reason: string) {
  const response = await fetch(`${API_BASE}/api/v1/admin/tasks/${taskId}/cancel?admin_key=${adminKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
  if (!response.ok) {
    throw new Error('Failed to cancel task')
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
}

const strategyLabels: Record<string, string> = {
  escrow_capture: 'Full Payment (AUTHORIZE -> RELEASE)',
  escrow_cancel: 'Cancellation (AUTHORIZE -> REFUND)',
  instant_payment: 'Instant Payment (CHARGE)',
  partial_payment: 'Partial (AUTHORIZE -> partial RELEASE + REFUND)',
  dispute_resolution: 'Dispute (AUTHORIZE -> RELEASE -> REFUND POST ESCROW)',
}

const tierInfo: Record<string, { label: string; preApproval: string; workDeadline: string; disputeWindow: string }> = {
  micro: { label: 'Micro (<$5)', preApproval: '1 hour', workDeadline: '2 hours', disputeWindow: '24 hours' },
  standard: { label: 'Standard ($5-$50)', preApproval: '2 hours', workDeadline: '24 hours', disputeWindow: '7 days' },
  premium: { label: 'Premium ($50-$200)', preApproval: '4 hours', workDeadline: '48 hours', disputeWindow: '14 days' },
  enterprise: { label: 'Enterprise ($200+)', preApproval: '24 hours', workDeadline: '7 days', disputeWindow: '30 days' },
}

function getTierFromAmount(amount: number): string {
  if (amount < 5) return 'micro'
  if (amount < 50) return 'standard'
  if (amount < 200) return 'premium'
  return 'enterprise'
}

export default function TaskDetailModal({ taskId, adminKey, onClose }: TaskDetailModalProps) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const [cancelReason, setCancelReason] = useState('')
  const [editForm, setEditForm] = useState<any>({})

  const { data: task, isLoading, error } = useQuery({
    queryKey: ['taskDetail', taskId],
    queryFn: () => fetchTaskDetail(adminKey, taskId),
    enabled: !!taskId,
  })

  const updateMutation = useMutation({
    mutationFn: (updates: any) => updateTask(adminKey, taskId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['taskDetail', taskId] })
      setEditing(false)
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (reason: string) => cancelTask(adminKey, taskId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      onClose()
    },
  })

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-gray-800 rounded-lg p-8">
          <div className="text-gray-400">Loading task...</div>
        </div>
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-gray-800 rounded-lg p-8">
          <div className="text-red-400">Failed to load task</div>
          <button onClick={onClose} className="mt-4 text-gray-400 hover:text-white">
            Close
          </button>
        </div>
      </div>
    )
  }

  const handleStartEdit = () => {
    setEditForm({
      title: task.title,
      description: task.description,
      bounty_usd: task.bounty_usd,
      deadline: task.deadline,
    })
    setEditing(true)
  }

  const handleSaveEdit = () => {
    updateMutation.mutate(editForm)
  }

  const handleCancel = () => {
    if (cancelReason.trim()) {
      cancelMutation.mutate(cancelReason)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <span className={`px-2 py-1 rounded text-xs text-white ${statusColors[task.status] || 'bg-gray-500'}`}>
              {task.status}
            </span>
            <span className="text-gray-400 text-sm font-mono">{task.id?.slice(0, 12)}...</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {editing ? (
            <>
              <div>
                <label className="block text-gray-400 text-sm mb-2">Title</label>
                <input
                  type="text"
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-2">Description</label>
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 h-32"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Bounty (USD)</label>
                  <input
                    type="number"
                    value={editForm.bounty_usd}
                    onChange={(e) => setEditForm({ ...editForm, bounty_usd: parseFloat(e.target.value) })}
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Deadline</label>
                  <input
                    type="datetime-local"
                    value={editForm.deadline?.slice(0, 16)}
                    onChange={(e) => setEditForm({ ...editForm, deadline: e.target.value })}
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
                  />
                </div>
              </div>
            </>
          ) : (
            <>
              <div>
                <h2 className="text-xl font-bold text-white">{task.title}</h2>
                <p className="text-gray-400 mt-2 whitespace-pre-wrap">{task.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-700/50 rounded p-4">
                  <p className="text-gray-400 text-sm">Bounty</p>
                  <p className="text-2xl font-bold text-white">${task.bounty_usd?.toFixed(2)}</p>
                </div>
                <div className="bg-gray-700/50 rounded p-4">
                  <p className="text-gray-400 text-sm">Deadline</p>
                  <p className="text-white">
                    {task.deadline ? new Date(task.deadline).toLocaleString() : 'No deadline'}
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b border-gray-700">
                  <span className="text-gray-400">Agent</span>
                  <span className="text-white font-mono text-sm">
                    {task.agent_id?.slice(0, 10)}...{task.agent_id?.slice(-6)}
                  </span>
                </div>
                {task.worker_id && (
                  <div className="flex justify-between py-2 border-b border-gray-700">
                    <span className="text-gray-400">Worker</span>
                    <span className="text-white font-mono text-sm">
                      {task.worker_id?.slice(0, 10)}...{task.worker_id?.slice(-6)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between py-2 border-b border-gray-700">
                  <span className="text-gray-400">Created</span>
                  <span className="text-white">
                    {task.created_at ? new Date(task.created_at).toLocaleString() : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-700">
                  <span className="text-gray-400">Location</span>
                  <span className="text-white">
                    {task.location ? `${task.location.lat?.toFixed(4)}, ${task.location.lng?.toFixed(4)}` : 'No location'}
                  </span>
                </div>
                {task.escrow_tx_hash && (
                  <div className="flex justify-between py-2 border-b border-gray-700">
                    <span className="text-gray-400">Escrow TX</span>
                    <a
                      href={`https://basescan.org/tx/${task.escrow_tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-em-400 hover:text-em-300 font-mono text-sm"
                    >
                      {task.escrow_tx_hash?.slice(0, 12)}...
                    </a>
                  </div>
                )}
              </div>

              {/* Payment Strategy & Tier Info */}
              {task.bounty_usd && (
                <div className="bg-gray-700/30 rounded-lg p-4 space-y-3">
                  <h3 className="text-gray-300 text-sm font-semibold">Payment Info</h3>
                  <div className="flex justify-between py-1">
                    <span className="text-gray-400 text-sm">Strategy</span>
                    <span className="text-white text-sm">
                      {task.payment_strategy
                        ? strategyLabels[task.payment_strategy] || task.payment_strategy
                        : strategyLabels[getTierFromAmount(task.bounty_usd) === 'enterprise' ? 'dispute_resolution' : 'escrow_capture'] + ' (auto)'}
                    </span>
                  </div>
                  {(() => {
                    const tier = task.payment_tier || getTierFromAmount(task.bounty_usd)
                    const info = tierInfo[tier]
                    if (!info) return null
                    return (
                      <>
                        <div className="flex justify-between py-1">
                          <span className="text-gray-400 text-sm">Tier</span>
                          <span className="text-white text-sm">{info.label}</span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-gray-400 text-sm">Pre-Approval</span>
                          <span className="text-white text-sm">{info.preApproval}</span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-gray-400 text-sm">Work Deadline</span>
                          <span className="text-white text-sm">{info.workDeadline}</span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-gray-400 text-sm">Dispute Window</span>
                          <span className="text-white text-sm">{info.disputeWindow}</span>
                        </div>
                      </>
                    )
                  })()}
                </div>
              )}

              {task.evidence_urls?.length > 0 && (
                <div>
                  <h3 className="text-gray-400 text-sm mb-2">Evidence</h3>
                  <div className="grid grid-cols-3 gap-2">
                    {task.evidence_urls.map((url: string, i: number) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-gray-700 rounded p-2 text-center text-em-400 hover:text-em-300 text-sm"
                      >
                        Evidence {i + 1}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Cancel Dialog */}
        {showCancelDialog && (
          <div className="p-6 border-t border-gray-700 bg-red-900/20">
            <h3 className="text-red-400 font-semibold mb-3">Cancel Task</h3>
            <p className="text-gray-400 text-sm mb-3">
              This will cancel the task and refund any escrowed funds to the agent.
            </p>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Reason for cancellation (required)"
              className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 h-20 mb-3"
            />
            <div className="flex gap-2">
              <button
                onClick={handleCancel}
                disabled={!cancelReason.trim() || cancelMutation.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded disabled:opacity-50"
              >
                {cancelMutation.isPending ? 'Cancelling...' : 'Confirm Cancel'}
              </button>
              <button
                onClick={() => setShowCancelDialog(false)}
                className="px-4 py-2 bg-gray-700 text-white rounded"
              >
                Back
              </button>
            </div>
          </div>
        )}

        {/* Actions */}
        {!showCancelDialog && (
          <div className="p-6 border-t border-gray-700 flex gap-3">
            {editing ? (
              <>
                <button
                  onClick={handleSaveEdit}
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 bg-em-600 hover:bg-em-700 text-white rounded disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="px-4 py-2 bg-gray-700 text-white rounded"
                >
                  Cancel
                </button>
              </>
            ) : (
              <>
                {['published', 'accepted'].includes(task.status) && (
                  <button
                    onClick={handleStartEdit}
                    className="px-4 py-2 bg-em-600 hover:bg-em-700 text-white rounded"
                  >
                    Edit Task
                  </button>
                )}
                {!['completed', 'cancelled', 'expired'].includes(task.status) && (
                  <button
                    onClick={() => setShowCancelDialog(true)}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded"
                  >
                    Cancel Task
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-700 text-white rounded ml-auto"
                >
                  Close
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
