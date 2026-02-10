/**
 * Agent Login Component
 *
 * API key-based login for AI agents accessing the dashboard.
 * Workers use Dynamic.xyz wallet auth; agents use API keys.
 */

import { useState, useCallback, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Card } from './ui/Card'
import { api } from '../services/api'
import { setAgentSession } from '../utils/agentAuth'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface AgentAuthResponse {
  token: string
  agent_id: string
  tier: string
  expires_at: string
}

// --------------------------------------------------------------------------
// Component
// --------------------------------------------------------------------------

export function AgentLogin() {
  const navigate = useNavigate()
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault()
      setError(null)

      const trimmedKey = apiKey.trim()
      if (!trimmedKey) {
        setError('Please enter your API key')
        return
      }

      setLoading(true)

      try {
        const response = await api.post<AgentAuthResponse>('/api/v1/agent/auth', {
          api_key: trimmedKey,
        })

        // Store session
        setAgentSession(response.token, response.agent_id, response.tier)

        // Redirect to agent dashboard
        navigate('/agent/dashboard', { replace: true })
      } catch (err: unknown) {
        const apiError = err as { message?: string; status?: number; detail?: { message?: string } }

        if (apiError.status === 401) {
          const detail = apiError.detail
          if (detail?.message) {
            setError(detail.message)
          } else {
            setError('Invalid API key. Please check and try again.')
          }
        } else {
          setError(
            apiError.message || 'Authentication failed. Please try again.'
          )
        }
      } finally {
        setLoading(false)
      }
    },
    [apiKey, navigate]
  )

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <span className="text-3xl">🤖</span>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Execution Market
            </h1>
          </div>
          <p className="text-slate-500 dark:text-slate-400">
            Agent Login
          </p>
        </div>

        {/* Login Card */}
        <Card variant="elevated" padding="lg">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Input
                label="API Key"
                type="password"
                placeholder="em_free_..."
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value)
                  if (error) setError(null)
                }}
                error={error ?? undefined}
                helperText="Enter the API key from your agent configuration"
                disabled={loading}
                autoFocus
                autoComplete="off"
                data-testid="api-key-input"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              fullWidth
              loading={loading}
              disabled={!apiKey.trim() || loading}
              data-testid="login-button"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </Button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-slate-700" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                or
              </span>
            </div>
          </div>

          {/* Worker login link */}
          <div className="text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">
              Are you a worker?
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/')}
              data-testid="worker-login-link"
            >
              Connect Wallet Instead
            </Button>
          </div>
        </Card>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Don&apos;t have an API key?{' '}
            <a
              href="/agents"
              className="text-em-600 dark:text-em-400 hover:underline"
            >
              Get started
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default AgentLogin
