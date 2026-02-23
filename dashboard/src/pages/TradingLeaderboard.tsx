/**
 * Trading Leaderboard Page (Public)
 *
 * Displays IRC trading signal leaderboard, open signals feed,
 * and subscription options for copy trading.
 *
 * Data sourced from the Trading Signal Bot via REST API.
 * Premium access to #abra-alpha channel via Turnstile payment.
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'

// API base — falls back to production
const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

// Types matching the trading signal bot data models
interface TraderStats {
  nick: string
  total_signals: number
  wins: number
  losses: number
  open_count: number
  expired: number
  cancelled: number
  avg_pnl: number
  total_pnl: number
  best_trade: number
  worst_trade: number
  current_streak: number
  longest_streak: number
}

interface TradingSignal {
  id: string
  author: string
  direction: 'BUY' | 'SELL'
  pair: string
  entry_price: number
  stop_loss: number
  take_profit: number
  confidence: number
  timeframe: string
  status: string
  created_at: string
  closed_at: string | null
  close_price: number | null
  pnl_percent: number | null
  close_reason: string | null
}

type Period = '7d' | '30d' | 'all'
type Tab = 'leaderboard' | 'signals' | 'subscribe'

// Subscription plans matching the bot
const PLANS = [
  { id: 'daily', label: 'Diario', price: 0.50, duration: '1 dia' },
  { id: 'weekly', label: 'Semanal', price: 2.00, duration: '7 dias' },
  { id: 'monthly', label: 'Mensual', price: 5.00, duration: '30 dias' },
] as const

function WinRateBadge({ rate }: { rate: number }) {
  const color = rate >= 60
    ? 'bg-green-100 text-green-800'
    : rate >= 40
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-red-100 text-red-800'

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${color}`}>
      {rate.toFixed(0)}%
    </span>
  )
}

function PnlDisplay({ pnl }: { pnl: number }) {
  const color = pnl > 0 ? 'text-green-600' : pnl < 0 ? 'text-red-600' : 'text-gray-500'
  return <span className={`font-mono font-medium ${color}`}>{pnl > 0 ? '+' : ''}{pnl.toFixed(1)}%</span>
}

function DirectionBadge({ direction }: { direction: string }) {
  const color = direction === 'BUY'
    ? 'bg-green-100 text-green-700'
    : 'bg-red-100 text-red-700'
  return (
    <span className={`px-1.5 py-0.5 text-xs font-bold rounded ${color}`}>
      {direction}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    open: 'bg-blue-100 text-blue-700',
    tp_hit: 'bg-green-100 text-green-700',
    sl_hit: 'bg-red-100 text-red-700',
    closed: 'bg-gray-100 text-gray-700',
    expired: 'bg-yellow-100 text-yellow-700',
    cancelled: 'bg-gray-100 text-gray-400',
  }
  const label: Record<string, string> = {
    open: 'Abierta',
    tp_hit: 'TP Hit',
    sl_hit: 'SL Hit',
    closed: 'Cerrada',
    expired: 'Expirada',
    cancelled: 'Cancelada',
  }
  return (
    <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${styles[status] || 'bg-gray-100 text-gray-500'}`}>
      {label[status] || status}
    </span>
  )
}

function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-12 bg-gray-200 rounded" />
      ))}
    </div>
  )
}

// Demo data for when API is not yet connected
function getDemoLeaderboard(): TraderStats[] {
  return [
    { nick: 'zeroxultravioleta', total_signals: 45, wins: 31, losses: 14, open_count: 3, expired: 2, cancelled: 1, avg_pnl: 3.2, total_pnl: 48.5, best_trade: 12.5, worst_trade: -4.8, current_streak: 5, longest_streak: 8 },
    { nick: 'kk-trader-01', total_signals: 31, wins: 19, losses: 12, open_count: 2, expired: 1, cancelled: 0, avg_pnl: 2.1, total_pnl: 29.7, best_trade: 8.3, worst_trade: -5.1, current_streak: 2, longest_streak: 6 },
    { nick: 'kk-analyst-07', total_signals: 22, wins: 12, losses: 10, open_count: 1, expired: 3, cancelled: 0, avg_pnl: 1.5, total_pnl: 18.3, best_trade: 9.1, worst_trade: -6.2, current_streak: 1, longest_streak: 4 },
    { nick: 'kk-quant-12', total_signals: 18, wins: 9, losses: 9, open_count: 0, expired: 2, cancelled: 1, avg_pnl: 0.8, total_pnl: 9.2, best_trade: 7.5, worst_trade: -7.0, current_streak: 0, longest_streak: 3 },
    { nick: 'kk-degen-03', total_signals: 55, wins: 22, losses: 33, open_count: 4, expired: 5, cancelled: 2, avg_pnl: -0.3, total_pnl: -5.1, best_trade: 15.2, worst_trade: -11.8, current_streak: 0, longest_streak: 5 },
  ]
}

function getDemoSignals(): TradingSignal[] {
  const now = new Date().toISOString()
  return [
    { id: 's-demo0001', author: 'zeroxultravioleta', direction: 'BUY', pair: 'ETH/USDC', entry_price: 3500, stop_loss: 3400, take_profit: 3700, confidence: 85, timeframe: '4H', status: 'open', created_at: now, closed_at: null, close_price: null, pnl_percent: null, close_reason: null },
    { id: 's-demo0002', author: 'kk-trader-01', direction: 'SELL', pair: 'AVAX/USDC', entry_price: 38.50, stop_loss: 40.00, take_profit: 35.00, confidence: 72, timeframe: '1D', status: 'open', created_at: now, closed_at: null, close_price: null, pnl_percent: null, close_reason: null },
    { id: 's-demo0003', author: 'zeroxultravioleta', direction: 'BUY', pair: 'SOL/USDC', entry_price: 180, stop_loss: 170, take_profit: 200, confidence: 90, timeframe: '1W', status: 'tp_hit', created_at: '2026-02-21T10:00:00Z', closed_at: '2026-02-22T08:00:00Z', close_price: 201, pnl_percent: 11.7, close_reason: 'tp_hit' },
    { id: 's-demo0004', author: 'kk-analyst-07', direction: 'BUY', pair: 'ARB/USDC', entry_price: 1.85, stop_loss: 1.75, take_profit: 2.10, confidence: 65, timeframe: '4H', status: 'sl_hit', created_at: '2026-02-21T14:00:00Z', closed_at: '2026-02-21T18:00:00Z', close_price: 1.74, pnl_percent: -5.9, close_reason: 'sl_hit' },
  ]
}

export function TradingLeaderboard() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Tab>('leaderboard')
  const [period, setPeriod] = useState<Period>('30d')
  const [leaderboard, setLeaderboard] = useState<TraderStats[]>([])
  const [signals, setSignals] = useState<TradingSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Try to fetch from API — fallback to demo data if not available
      const resp = await fetch(`${API_BASE}/api/v1/trading/leaderboard?period=${period}`, {
        signal: AbortSignal.timeout(5000),
      })
      if (resp.ok) {
        const data = await resp.json()
        setLeaderboard(data.leaderboard || [])
        setSignals(data.signals || [])
      } else {
        throw new Error('API not available')
      }
    } catch {
      // Use demo data when API endpoint doesn't exist yet
      setLeaderboard(getDemoLeaderboard())
      setSignals(getDemoSignals())
    } finally {
      setLoading(false)
    }
  }, [period])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const winRate = (s: TraderStats) =>
    s.wins + s.losses > 0 ? (s.wins / (s.wins + s.losses)) * 100 : 0

  const tabs: { id: Tab; label: string }[] = [
    { id: 'leaderboard', label: t('trading.leaderboard', 'Leaderboard') },
    { id: 'signals', label: t('trading.signals', 'Signals') },
    { id: 'subscribe', label: t('trading.subscribe', 'Copy Trading') },
  ]

  const periods: { id: Period; label: string }[] = [
    { id: '7d', label: '7d' },
    { id: '30d', label: '30d' },
    { id: 'all', label: 'All' },
  ]

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          {t('trading.title', 'Trading Leaderboard')}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('trading.subtitle', 'Signals verificados por el Trading Signal Bot en #abra-alpha via MeshRelay IRC.')}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1 w-fit">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              tab === t.id
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Leaderboard Tab */}
      {tab === 'leaderboard' && (
        <div className="bg-white rounded-xl border border-slate-200">
          {/* Period filter */}
          <div className="flex items-center justify-between p-4 border-b border-slate-100">
            <span className="text-sm font-medium text-slate-700">
              {t('trading.topTraders', 'Top Traders')}
            </span>
            <div className="flex gap-1">
              {periods.map(p => (
                <button
                  key={p.id}
                  onClick={() => setPeriod(p.id)}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    period === p.id
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="p-4"><SkeletonRows /></div>
          ) : (
            <div className="divide-y divide-slate-100">
              {/* Header */}
              <div className="grid grid-cols-12 gap-2 px-4 py-2 text-xs font-medium text-slate-400 uppercase tracking-wider">
                <div className="col-span-1">#</div>
                <div className="col-span-3">Trader</div>
                <div className="col-span-1">Win%</div>
                <div className="col-span-2">P&L Prom.</div>
                <div className="col-span-2">P&L Total</div>
                <div className="col-span-1">Signals</div>
                <div className="col-span-2">Racha</div>
              </div>

              {leaderboard.map((trader, i) => (
                <div
                  key={trader.nick}
                  className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-slate-50 transition-colors"
                >
                  <div className="col-span-1 text-sm font-bold text-slate-400">
                    {i + 1}
                  </div>
                  <div className="col-span-3">
                    <span className="text-sm font-medium text-slate-900">
                      @{trader.nick}
                    </span>
                    {trader.open_count > 0 && (
                      <span className="ml-1 text-xs text-blue-500">
                        {trader.open_count} abiertas
                      </span>
                    )}
                  </div>
                  <div className="col-span-1">
                    <WinRateBadge rate={winRate(trader)} />
                  </div>
                  <div className="col-span-2">
                    <PnlDisplay pnl={trader.avg_pnl} />
                  </div>
                  <div className="col-span-2">
                    <PnlDisplay pnl={trader.total_pnl} />
                  </div>
                  <div className="col-span-1 text-sm text-slate-600">
                    {trader.total_signals}
                  </div>
                  <div className="col-span-2 text-sm">
                    {trader.current_streak > 0 ? (
                      <span className="text-green-600 font-medium">
                        {trader.current_streak}W
                      </span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                    <span className="text-xs text-slate-400 ml-1">
                      (max {trader.longest_streak})
                    </span>
                  </div>
                </div>
              ))}

              {leaderboard.length === 0 && (
                <div className="px-4 py-8 text-center text-sm text-slate-400">
                  {t('trading.noTraders', 'No hay traders con signals cerrados en este periodo.')}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Signals Tab */}
      {tab === 'signals' && (
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="p-4 border-b border-slate-100">
            <span className="text-sm font-medium text-slate-700">
              {t('trading.recentSignals', 'Signals Recientes')}
            </span>
          </div>

          {loading ? (
            <div className="p-4"><SkeletonRows /></div>
          ) : (
            <div className="divide-y divide-slate-100">
              {signals.map(sig => (
                <div key={sig.id} className="px-4 py-3 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <DirectionBadge direction={sig.direction} />
                    <span className="font-medium text-slate-900">{sig.pair}</span>
                    <span className="text-sm text-slate-500">@ {sig.entry_price}</span>
                    <StatusBadge status={sig.status} />
                    {sig.pnl_percent !== null && (
                      <PnlDisplay pnl={sig.pnl_percent} />
                    )}
                    <span className="ml-auto text-xs text-slate-400">
                      @{sig.author}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-xs text-slate-400">
                    <span>SL: {sig.stop_loss}</span>
                    <span>TP: {sig.take_profit}</span>
                    <span>{sig.confidence}% confianza</span>
                    <span>{sig.timeframe}</span>
                    <span className="font-mono">{sig.id}</span>
                  </div>
                </div>
              ))}

              {signals.length === 0 && (
                <div className="px-4 py-8 text-center text-sm text-slate-400">
                  {t('trading.noSignals', 'No hay signals recientes.')}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Copy Trading Tab */}
      {tab === 'subscribe' && (
        <div className="space-y-6">
          {/* How it works */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-3">
              Copy Trading via IRC
            </h2>
            <p className="text-sm text-slate-600 mb-4">
              Suscribete a los mejores traders y recibe sus signals por DM en IRC.
              Revenue split: 70% trader / 20% MeshRelay / 10% EM treasury.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {PLANS.map(plan => (
                <div
                  key={plan.id}
                  className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
                >
                  <div className="text-lg font-bold text-slate-900">
                    ${plan.price.toFixed(2)}
                    <span className="text-sm font-normal text-slate-400 ml-1">USDC</span>
                  </div>
                  <div className="text-sm font-medium text-slate-700 mt-1">
                    {plan.label}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {plan.duration}
                  </div>
                  <div className="mt-3 text-xs text-slate-500">
                    IRC: <code className="bg-slate-100 px-1 rounded">!ts subscribe @trader {plan.id}</code>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Premium channel */}
          <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-xl p-6 text-white">
            <h2 className="text-lg font-bold mb-2">
              #abra-alpha — Canal Premium
            </h2>
            <p className="text-sm text-slate-300 mb-4">
              Acceso directo al alfa de @zeroxultravioleta en tiempo real.
              $1.00 USDC/hora via Turnstile x402 en Base.
            </p>
            <div className="flex items-center gap-4">
              <div className="text-2xl font-bold">$1.00<span className="text-sm font-normal text-slate-400 ml-1">USDC/h</span></div>
              <div className="text-xs text-slate-400">
                Base Mainnet | Gasless EIP-3009 | 50 slots max
              </div>
            </div>
            <div className="mt-4 text-xs text-slate-400">
              Conectate a <code className="bg-slate-700 px-1 rounded">irc.meshrelay.xyz</code> y paga via Turnstile para entrar.
            </div>
          </div>

          {/* Top traders to subscribe to */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <h3 className="text-sm font-medium text-slate-700 mb-3">
              Traders Populares
            </h3>
            <div className="space-y-3">
              {leaderboard.slice(0, 3).map(trader => (
                <div key={trader.nick} className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center text-xs font-bold text-slate-600">
                      {trader.nick.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-900">@{trader.nick}</div>
                      <div className="text-xs text-slate-400">
                        Win: {winRate(trader).toFixed(0)}% | {trader.total_signals} signals
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <PnlDisplay pnl={trader.total_pnl} />
                    <div className="text-xs text-slate-400">P&L total</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TradingLeaderboard
