import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { adminPut } from '../../lib/api'

interface DescribeNetPanelProps {
  adminKey: string
  config: Record<string, any>
  onConfigUpdate: () => void
}

const WORKER_SEALS = [
  {
    name: 'Skillful',
    key: 'skillful',
    description: 'Consistently delivers high-quality work that meets or exceeds task requirements.',
  },
  {
    name: 'Reliable',
    key: 'reliable',
    description: 'Completes tasks on time with minimal cancellations or missed deadlines.',
  },
  {
    name: 'Fast',
    key: 'fast',
    description: 'Completes tasks significantly ahead of the deadline without sacrificing quality.',
  },
  {
    name: 'Quality',
    key: 'quality',
    description: 'Evidence submissions are thorough, well-documented, and rarely require resubmission.',
  },
]

const REQUESTER_SEALS = [
  {
    name: 'Fair Payer',
    key: 'fair-payer',
    description: 'Sets reasonable bounties relative to task complexity and approves work promptly.',
  },
  {
    name: 'Clear Instructions',
    key: 'clear-instructions',
    description: 'Provides detailed, unambiguous task descriptions and evidence requirements.',
  },
  {
    name: 'Responsive',
    key: 'responsive',
    description: 'Reviews submissions quickly and communicates clearly during disputes.',
  },
]

const ENV_VARS = [
  { name: 'DESCRIBENET_API_URL', description: 'Base URL for the describe.net API' },
  { name: 'DESCRIBENET_API_KEY', description: 'API key for authentication' },
  { name: 'DESCRIBENET_API_SECRET', description: 'API secret for request signing' },
  { name: 'DESCRIBENET_ORG_ID', description: 'Organization identifier on describe.net' },
]

export default function DescribeNetPanel({
  adminKey,
  config,
  onConfigUpdate,
}: DescribeNetPanelProps) {
  const queryClient = useQueryClient()
  const isEnabled = config['feature.describenet_enabled'] ?? false
  const [reason, setReason] = useState('')
  const [showReason, setShowReason] = useState(false)

  const toggleMutation = useMutation({
    mutationFn: () =>
      adminPut(`/api/v1/admin/config/feature.describenet_enabled`, adminKey, {
        value: !isEnabled,
        reason: reason || undefined,
      }),
    onSuccess: () => {
      setReason('')
      setShowReason(false)
      queryClient.invalidateQueries({ queryKey: ['config'] })
      onConfigUpdate()
    },
  })

  const handleToggle = () => {
    if (isEnabled) {
      // Disabling -- show reason input
      setShowReason(true)
    } else {
      // Enabling -- just do it
      toggleMutation.mutate()
    }
  }

  const confirmDisable = () => {
    toggleMutation.mutate()
  }

  return (
    <div className="space-y-6">
      {/* Header + Master Toggle */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-white">describe.net Integration</h2>
            <p className="text-gray-400 text-sm mt-1">
              describe.net provides on-chain skill seals and reputation badges for workers and
              requesters.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                isEnabled
                  ? 'bg-green-900/50 text-green-400 border border-green-700'
                  : 'bg-gray-700 text-gray-400 border border-gray-600'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${isEnabled ? 'bg-green-400' : 'bg-gray-500'}`}
              />
              {isEnabled ? 'Active' : 'Inactive'}
            </span>
            <button
              onClick={handleToggle}
              disabled={toggleMutation.isPending}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-em-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 ${
                isEnabled ? 'bg-em-600' : 'bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                  isEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Disable reason input */}
        {showReason && (
          <div className="mt-4 pt-4 border-t border-gray-700 space-y-3">
            <p className="text-gray-300 text-sm">
              Disabling will stop all seal and badge issuance. Existing seals remain on-chain.
            </p>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason for disabling (optional)"
              className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 text-sm"
            />
            <div className="flex gap-2">
              <button
                onClick={confirmDisable}
                disabled={toggleMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-1.5 rounded text-sm disabled:opacity-50"
              >
                {toggleMutation.isPending ? 'Saving...' : 'Confirm Disable'}
              </button>
              <button
                onClick={() => {
                  setShowReason(false)
                  setReason('')
                }}
                className="text-gray-400 hover:text-white px-4 py-1.5 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {toggleMutation.isError && (
          <p className="text-red-400 text-sm mt-3">
            Failed to update: {(toggleMutation.error as Error)?.message || 'Unknown error'}
          </p>
        )}
      </div>

      {/* API Configuration */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-md font-semibold text-white mb-4">API Configuration</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-gray-700">
            <span className="text-gray-300 text-sm">API URL</span>
            <span className="text-white font-mono text-sm">
              {config['describenet_api_url'] || 'https://api.describe.net/v1'}
            </span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-700">
            <span className="text-gray-300 text-sm">Organization ID</span>
            <span className="text-white font-mono text-sm">
              {config['describenet_org_id'] || 'execution-market'}
            </span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-700">
            <span className="text-gray-300 text-sm">Connection Status</span>
            <span className="text-gray-500 text-sm italic">
              {isEnabled ? 'Check connection when enabled' : 'Enable integration to test connection'}
            </span>
          </div>
        </div>
        <p className="text-gray-500 text-xs mt-4">
          API credentials are managed via environment variables for security.
        </p>
      </div>

      {/* Seal & Badge Overview */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-md font-semibold text-white mb-4">Seal & Badge Overview</h3>

        {isEnabled ? (
          <div className="bg-gray-700/30 rounded p-4 mb-6 text-center">
            <p className="text-gray-400 text-sm">
              Seal statistics available when integration is active and tasks have been completed.
            </p>
          </div>
        ) : (
          <div className="bg-gray-700/30 rounded p-4 mb-6 text-center">
            <p className="text-gray-400 text-sm">
              Enable the integration to start issuing seals and badges.
            </p>
          </div>
        )}

        {/* Worker Seals */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-300 mb-3 uppercase tracking-wide">
            Worker Seals
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {WORKER_SEALS.map((seal) => (
              <div
                key={seal.key}
                className="bg-gray-700/50 border border-gray-600 rounded-lg p-3"
              >
                <div className="text-white text-sm font-medium">{seal.name}</div>
                <p className="text-gray-400 text-xs mt-1">{seal.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Requester Seals */}
        <div>
          <h4 className="text-sm font-medium text-gray-300 mb-3 uppercase tracking-wide">
            Requester Seals
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {REQUESTER_SEALS.map((seal) => (
              <div
                key={seal.key}
                className="bg-gray-700/50 border border-gray-600 rounded-lg p-3"
              >
                <div className="text-white text-sm font-medium">{seal.name}</div>
                <p className="text-gray-400 text-xs mt-1">{seal.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Configuration Notes */}
      <div className="bg-gray-700/30 border border-gray-700 rounded-lg p-6">
        <h3 className="text-md font-semibold text-gray-300 mb-3">Configuration Notes</h3>
        <p className="text-gray-400 text-sm mb-4">
          To modify API credentials, update the following environment variables in the ECS task
          definition:
        </p>
        <div className="space-y-2">
          {ENV_VARS.map((envVar) => (
            <div
              key={envVar.name}
              className="flex items-start gap-3 py-1.5"
            >
              <code className="text-em-400 font-mono text-sm whitespace-nowrap bg-gray-800 px-2 py-0.5 rounded">
                {envVar.name}
              </code>
              <span className="text-gray-500 text-sm">{envVar.description}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
