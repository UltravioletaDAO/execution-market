import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { safeHref } from '../lib/safeHref'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

interface FeedbackDocument {
  version: string
  type: string
  feedback_type: string
  created_at: string
  network: string
  task: {
    id: string
    title: string
    category: string
    bounty_usd: number
    submission_id?: string
  }
  rating: {
    score: number
    max_score: number
    rater_type: string
    rater_id: string
    target_type: string
    target_address: string
    target_agent_id?: number
  }
  transactions: {
    payment_tx: string
    reputation_tx: string
  }
  comment?: string
  rejection?: {
    reason: string
    severity: string
  }
  evidence?: string[]
}

function ScoreBadge({ score, maxScore }: { score: number; maxScore: number }) {
  const pct = (score / maxScore) * 100
  const color =
    pct >= 80
      ? 'bg-green-100 text-green-800 border-green-200'
      : pct >= 50
        ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
        : 'bg-red-100 text-red-800 border-red-200'

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${color}`}>
      {score} / {maxScore}
    </span>
  )
}

function TxLink({ hash, network }: { hash: string; network: string }) {
  if (!hash) return <span className="text-gray-400">-</span>

  const explorers: Record<string, string> = {
    base: 'https://basescan.org/tx/',
    ethereum: 'https://etherscan.io/tx/',
    polygon: 'https://polygonscan.com/tx/',
    arbitrum: 'https://arbiscan.io/tx/',
    avalanche: 'https://snowtrace.io/tx/',
    celo: 'https://celoscan.io/tx/',
    optimism: 'https://optimistic.etherscan.io/tx/',
  }
  const base = explorers[network] || explorers.base
  const short = `${hash.slice(0, 10)}...${hash.slice(-6)}`

  return (
    <a
      href={`${base}${hash}`}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 hover:text-blue-800 font-mono text-sm underline"
    >
      {short}
    </a>
  )
}

export function FeedbackPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const [doc, setDoc] = useState<FeedbackDocument | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!taskId) return

    setLoading(true)
    setError(null)

    fetch(`${API_BASE_URL}/api/v1/reputation/feedback/${taskId}`, {
      headers: { 'X-Client-Info': 'execution-market-dashboard' },
    })
      .then(async (res) => {
        if (!res.ok) {
          const text = await res.text()
          let msg = `Error ${res.status}`
          try {
            const data = JSON.parse(text)
            msg = data.detail || msg
          } catch { /* use default */ }
          throw new Error(msg)
        }
        return res.json()
      })
      .then(setDoc)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [taskId])

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 w-full">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <svg className="animate-spin h-6 w-6 text-blue-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-gray-500">Loading feedback...</span>
          </div>
        )}

        {error && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
            <div className="text-4xl mb-4">&#128269;</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Feedback not found
            </h2>
            <p className="text-gray-500 mb-6">{error}</p>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Go to Home
            </button>
          </div>
        )}

        {doc && (
          <div className="space-y-6">
            {/* Header */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    {doc.feedback_type === 'rejection'
                      ? 'Submission Rejected'
                      : doc.feedback_type === 'worker_rating'
                        ? 'Worker Rating'
                        : 'Agent Rating'}
                  </h1>
                  <p className="text-gray-500 text-sm mt-1">
                    ERC-8004 On-Chain Reputation Feedback
                  </p>
                </div>
                <ScoreBadge score={doc.rating.score} maxScore={doc.rating.max_score} />
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Network</span>
                  <p className="font-medium text-gray-900 capitalize">{doc.network}</p>
                </div>
                <div>
                  <span className="text-gray-500">Date</span>
                  <p className="font-medium text-gray-900">
                    {new Date(doc.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            </div>

            {/* Task Info */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Task Details</h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Task ID</span>
                  <p className="font-mono text-gray-900 text-xs break-all">{doc.task.id}</p>
                </div>
                {doc.task.title && (
                  <div>
                    <span className="text-gray-500">Title</span>
                    <p className="font-medium text-gray-900">{doc.task.title}</p>
                  </div>
                )}
                {doc.task.category && (
                  <div>
                    <span className="text-gray-500">Category</span>
                    <p className="font-medium text-gray-900 capitalize">
                      {doc.task.category.replace(/_/g, ' ')}
                    </p>
                  </div>
                )}
                {doc.task.bounty_usd > 0 && (
                  <div>
                    <span className="text-gray-500">Bounty</span>
                    <p className="font-medium text-gray-900">${doc.task.bounty_usd.toFixed(2)} USDC</p>
                  </div>
                )}
              </div>
            </div>

            {/* Rating Details */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Rating</h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Rater</span>
                  <p className="font-medium text-gray-900 capitalize">{doc.rating.rater_type}</p>
                </div>
                <div>
                  <span className="text-gray-500">Target</span>
                  <p className="font-medium text-gray-900 capitalize">{doc.rating.target_type}</p>
                </div>
                {doc.rating.target_address && (
                  <div className="col-span-2">
                    <span className="text-gray-500">Target Address</span>
                    <p className="font-mono text-gray-900 text-xs break-all">
                      {doc.rating.target_address}
                    </p>
                  </div>
                )}
                {doc.rating.target_agent_id && (
                  <div>
                    <span className="text-gray-500">Agent ID</span>
                    <p className="font-medium text-gray-900">#{doc.rating.target_agent_id}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Comment */}
            {doc.comment && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Comment</h2>
                <p className="text-gray-700 whitespace-pre-wrap">{doc.comment}</p>
              </div>
            )}

            {/* Rejection Details */}
            {doc.rejection && (
              <div className="bg-red-50 rounded-xl border border-red-200 p-6">
                <h2 className="text-lg font-semibold text-red-900 mb-3">Rejection</h2>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-red-600">Reason</span>
                    <p className="text-red-900 font-medium">{doc.rejection.reason}</p>
                  </div>
                  <div>
                    <span className="text-red-600">Severity</span>
                    <p className="text-red-900 font-medium capitalize">{doc.rejection.severity}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Evidence */}
            {doc.evidence && doc.evidence.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Evidence</h2>
                <ul className="space-y-2">
                  {doc.evidence.map((url, i) => (
                    <li key={i}>
                      <a
                        href={safeHref(url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 underline text-sm break-all"
                      >
                        {url}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Transactions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">On-Chain Transactions</h2>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Payment TX</span>
                  <TxLink hash={doc.transactions.payment_tx} network={doc.network} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Reputation TX</span>
                  <TxLink hash={doc.transactions.reputation_tx} network={doc.network} />
                </div>
              </div>
            </div>

            {/* Verification Notice */}
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 text-center text-sm text-gray-500">
              <p>
                This feedback document is stored off-chain and its keccak256 hash is recorded
                on-chain in the{' '}
                <a
                  href="https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  ERC-8004 Reputation Registry
                </a>
                .
              </p>
              <p className="mt-1">
                Document version: {doc.version} | Schema: {doc.type}
              </p>
            </div>
          </div>
        )}
    </div>
  )
}
