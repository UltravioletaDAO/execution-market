/**
 * Human Publisher Dashboard - Manage H2A tasks
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useDynamicContext } from '@dynamic-labs/sdk-react-core'
import { isEthereumWallet } from '@dynamic-labs/ethereum'
import type { Task, H2AApplication } from '../../types/database'
import {
  listH2ATasks,
  cancelH2ATask,
  getH2AApplications,
  getH2ATask,
  getH2APaymentConfig,
  assignH2AWorker,
} from '../../services/h2a'
import { buildEscrowPreAuth } from '../../services/h2aSigning'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { useAuth } from '../../context/AuthContext'
import { DepositModal } from '../../components/DepositModal'
import { readEvmUsdcBalance, resolveEvmRpc } from '../../services/evm-balance'

type Tab = 'active' | 'review' | 'history'

/**
 * Feature flag: escrow sign-on-assignment for human publishers. When ON and
 * the task has a publish-time escrow marker (escrow_status='pending_assignment'),
 * assigning an applicant signs an EIP-3009 escrow lock for THAT worker (the
 * nonce commits to the receiver) and sends it as X-Payment-Auth. Tasks without
 * a marker keep the legacy status-only assign.
 */
const H2A_ESCROW_ENABLED = import.meta.env.VITE_H2A_ESCROW_ENABLED === 'true'

/** True when the user cancelled the wallet signature prompt. */
function isSignatureRejection(e: unknown): boolean {
  const msg = e instanceof Error ? e.message : String(e)
  return /reject|denied|cancel/i.test(msg)
}

const STATUS_ICON: Record<string, string> = {
  published: '🔍',
  accepted: '🤝',
  in_progress: '⚡',
  submitted: '📬',
  completed: '✅',
  expired: '⏰',
  cancelled: '❌',
}

function shortWallet(w: string | null): string {
  if (!w || w.length < 10) return w || '—'
  return `${w.slice(0, 6)}…${w.slice(-4)}`
}

/** Applicants list + assign action, shown only for published H2A tasks. */
function Applicants({ task, onAssigned }: { task: Task; onAssigned: () => void }) {
  const { t } = useTranslation()
  const { primaryWallet } = useDynamicContext()
  const taskId = task.id
  const [apps, setApps] = useState<H2AApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [assigning, setAssigning] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setApps((await getH2AApplications(taskId)).applications) }
    catch (e) { setErr(e instanceof Error ? e.message : 'Error') }
    finally { setLoading(false) }
  }, [taskId])
  useEffect(() => { load() }, [load])

  /** Sign the escrow lock for this applicant (receiver = worker wallet). */
  const signEscrowLock = async (detail: Task, app: H2AApplication): Promise<string> => {
    const workerWallet = app.executor?.wallet_address
    if (!workerWallet) throw new Error(t('publisher.dashboard.escrow.noWorkerWallet', 'This applicant has no wallet address linked.'))
    if (!primaryWallet || !isEthereumWallet(primaryWallet)) {
      throw new Error(t('publisher.dashboard.escrow.connectWallet', 'Connect an EVM wallet to sign the escrow lock.'))
    }
    const network = detail.payment_network || 'base'
    const cfg = await getH2APaymentConfig()
    const netCfg = cfg.escrow_networks?.[network]
    if (!netCfg) throw new Error(t('publisher.dashboard.escrow.configUnavailable', 'Escrow configuration is not available for this network.'))
    // External wallets may sit on another chain; viem refuses typed data whose
    // domain.chainId differs from the client's current chain ("chainId should
    // be same as current chainId"). Switch to the task's network first.
    try {
      if (primaryWallet.connector?.supportsNetworkSwitching?.()) {
        await primaryWallet.switchNetwork(netCfg.chain_id)
      }
    } catch {
      throw new Error(t('publisher.dashboard.escrow.switchNetwork',
        'Switch your wallet to {{network}} (chain {{chainId}}) and retry.',
        { network, chainId: netCfg.chain_id }))
    }
    const walletClient = await primaryWallet.getWalletClient(String(netCfg.chain_id))
    if (!walletClient) throw new Error(t('review.errors.walletClientUnavailable', 'Wallet client unavailable for this network.'))
    const bounty = detail.bounty_usd || 0
    return buildEscrowPreAuth(walletClient, {
      networkConfig: netCfg,
      payerWallet: primaryWallet.address as `0x${string}`,
      workerWallet: workerWallet as `0x${string}`,
      bountyAtomic: BigInt(Math.round(bounty * 1_000_000)).toString(),
      // SDK tier semantics: MICRO $0.50-$5, STANDARD $5-$50 (longer windows).
      tier: bounty >= 5 ? 'standard' : 'micro',
    })
  }

  // App-styled confirm (replaces window.confirm): holds the applicant +
  // resolved task detail while the user decides.
  const [confirmState, setConfirmState] = useState<{
    app: H2AApplication
    detail: Task
    escrowMode: boolean
  } | null>(null)

  const requestAssign = async (app: H2AApplication) => {
    setErr(null)
    try {
      // Escrow-mode detection needs the task detail (escrow_status comes from
      // the H2A detail endpoint, not the list). Only fetched when the flag is on.
      const detail = H2A_ESCROW_ENABLED ? await getH2ATask(taskId) : task
      const escrowMode = H2A_ESCROW_ENABLED && detail.escrow_status === 'pending_assignment'
      setConfirmState({ app, detail, escrowMode })
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Error')
    }
  }

  const confirmAssign = async () => {
    if (!confirmState) return
    const { app, detail, escrowMode } = confirmState
    setConfirmState(null)
    try {
      let xPaymentAuth: string | undefined
      setAssigning(app.executor_id)
      if (escrowMode) {
        try {
          xPaymentAuth = await signEscrowLock(detail, app)
        } catch (se) {
          // Friendly abort when the user dismissed the wallet prompt; on a
          // 402 lock failure (later) the task simply remains published.
          if (isSignatureRejection(se)) {
            throw new Error(t('publisher.dashboard.escrow.signRejected', 'Signature cancelled — no funds were locked and the worker was not assigned.'))
          }
          throw se
        }
      }
      await assignH2AWorker(taskId, app.executor_id, xPaymentAuth)
      onAssigned()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Error')
      setAssigning(null)
    }
  }

  return (
    <div className="mt-3 border-t border-zinc-100 pt-3">
      <p className="text-xs font-medium text-zinc-500 mb-2">
        {t('publisher.dashboard.applicants', 'Aplicantes')} {apps.length > 0 && `(${apps.length})`}
      </p>
      {loading ? (
        <p className="text-xs text-zinc-600">{t('common.loading')}</p>
      ) : apps.length === 0 ? (
        <p className="text-xs text-zinc-600">{t('publisher.dashboard.noApplicants', 'Aún no hay aplicantes')}</p>
      ) : (
        <ul className="space-y-2">
          {apps.map((a) => (
            <li key={a.id} className="flex items-center justify-between gap-2 rounded-md bg-zinc-50 px-2.5 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-zinc-900">
                  {a.executor?.display_name || shortWallet(a.executor?.wallet_address ?? null)}
                </p>
                <p className="text-xs text-zinc-500">
                  ⭐ {(a.executor?.avg_rating ?? 0).toFixed(1)} · {a.executor?.tasks_completed ?? 0} {t('publisher.dashboard.tasksDone', 'tareas')}
                </p>
              </div>
              <button
                onClick={() => requestAssign(a)}
                disabled={assigning !== null}
                className="shrink-0 rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
              >
                {assigning === a.executor_id ? t('publisher.dashboard.assigning', 'Asignando…') : t('publisher.dashboard.assign', 'Asignar')}
              </button>
            </li>
          ))}
        </ul>
      )}
      {err && <p className="mt-2 text-xs text-red-600">{err}</p>}
      {confirmState && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-zinc-900">
              {t('publisher.dashboard.confirmAssignTitle', 'Asignar worker')}
            </h3>
            <p className="mt-2 text-sm text-zinc-600">
              {confirmState.escrowMode
                ? t('publisher.dashboard.escrow.confirmAssign',
                    'Assign this worker? ${{amount}} USDC will be locked in escrow for them until you approve the work.',
                    { amount: (confirmState.detail.bounty_usd || 0).toFixed(2) })
                : t('publisher.dashboard.confirmAssign', '¿Asignar a este worker?')}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setConfirmState(null)}
                className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
              >
                {t('common.cancel', 'Cancelar')}
              </button>
              <button
                onClick={confirmAssign}
                className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
              >
                {t('publisher.dashboard.assign', 'Asignar')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function TaskCard({ task, onReview, onCancel, onAssigned }: { task: Task; onReview?: (id: string) => void; onCancel?: (id: string) => void; onAssigned?: () => void }) {
  const { t } = useTranslation()
  const icon = STATUS_ICON[task.status] || '❓'
  const statusLabel = t(`publisher.dashboard.status.${task.status}`, task.status)
  return (
    <div className="bg-white rounded-lg border border-zinc-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium text-zinc-900 flex-1 pr-2 truncate">{task.title}</h3>
        <StatusBadge status={task.status} size="sm" label={`${icon} ${statusLabel}`} />
      </div>
      <p className="text-sm text-zinc-500 line-clamp-2 mb-3">{task.instructions}</p>
      <div className="flex items-center gap-4 text-sm text-zinc-600 mb-3">
        <span>💰 ${(task.bounty_usd || 0).toFixed(2)} USDC</span>
        <span>📅 {new Date(task.deadline).toLocaleDateString()}</span>
      </div>
      <div className="flex gap-2">
        {task.status === 'submitted' && onReview && <button onClick={() => onReview(task.id)} className="flex-1 px-3 py-1.5 bg-zinc-900 text-white text-sm rounded-lg hover:bg-zinc-800">⚡ {t('publisher.dashboard.review', 'Review')}</button>}
        {['published', 'accepted'].includes(task.status) && onCancel && <button onClick={() => onCancel(task.id)} className="px-3 py-1.5 border border-red-300 text-red-700 text-sm rounded-lg hover:bg-red-50">{t('common.cancel')}</button>}
      </div>
      {task.status === 'published' && onAssigned && <Applicants task={task} onAssigned={onAssigned} />}
    </div>
  )
}

export function PublisherDashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('active')
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { walletAddress, executor } = useAuth()
  const [balance, setBalance] = useState<number | null>(null)
  const [showDeposit, setShowDeposit] = useState(false)

  const loadTasks = useCallback(async () => {
    setLoading(true); setError(null)
    try { setTasks((await listH2ATasks({ my_tasks: true, limit: 50 })).tasks) }
    catch (e) { setError(e instanceof Error ? e.message : 'Error') }
    finally { setLoading(false) }
  }, [])

  const loadBalance = useCallback(async () => {
    if (!walletAddress) { setBalance(null); return }
    try { setBalance(await readEvmUsdcBalance(walletAddress, resolveEvmRpc('base'), 'base')) }
    catch { setBalance(null) }
  }, [walletAddress])

  useEffect(() => { loadTasks() }, [loadTasks])
  useEffect(() => { loadBalance() }, [loadBalance])

  const active = tasks.filter(t => ['published', 'accepted', 'in_progress'].includes(t.status))
  const review = tasks.filter(t => ['submitted', 'verifying'].includes(t.status))
  const history = tasks.filter(t => ['completed', 'expired', 'cancelled', 'disputed'].includes(t.status))
  const displayed = tab === 'active' ? active : tab === 'review' ? review : history
  const totalSpent = tasks.filter(t => t.status === 'completed').reduce((s, t) => s + (t.bounty_usd || 0), 0)

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="bg-white border-b border-zinc-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div><h1 className="text-2xl font-bold text-zinc-900">📋 {t('publisher.dashboard.title', 'Publisher Panel')}</h1><p className="text-sm text-zinc-500 mt-1">{t('publisher.dashboard.subtitle', 'Manage your requests for AI agents')}</p></div>
            <div className="flex items-center gap-3">
              {walletAddress && (
                <div className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2">
                  <span className="text-xs text-zinc-500">{t('publisher.dashboard.balance', 'Saldo')}</span>
                  <span className="font-mono text-sm font-bold text-zinc-900">{balance === null ? '—' : `$${balance.toFixed(2)}`}</span>
                  <span className="hidden sm:inline text-xs text-zinc-600">USDC · Base</span>
                  <button onClick={() => setShowDeposit(true)} className="ml-1 rounded-md bg-zinc-900 px-2.5 py-1 text-xs font-medium text-white hover:bg-zinc-800">+ {t('publisher.dashboard.deposit', 'Depositar')}</button>
                </div>
              )}
              <button onClick={() => navigate('/publisher/requests/new')} className="px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 font-medium">+ {t('publisher.dashboard.newRequest', 'New Request')}</button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[{ n: active.length, l: t('publisher.dashboard.active', 'Active'), c: 'text-zinc-900' }, { n: review.length, l: t('publisher.dashboard.toReview', 'To Review'), c: 'text-amber-700' }, { n: tasks.filter(t => t.status === 'completed').length, l: t('publisher.dashboard.completed', 'Completed'), c: 'text-zinc-900' }, { n: totalSpent, l: t('publisher.dashboard.spent', 'Spent'), c: 'text-zinc-900', fmt: (v: number) => `$${v.toFixed(2)}` }].map((s, i) => (
            <div key={i} className="bg-white rounded-lg border border-zinc-200 p-4 text-center">
              <div className={`text-2xl font-bold ${s.c}`}>{s.fmt ? s.fmt(s.n) : s.n}</div>
              <div className="text-sm text-zinc-500">{s.l}</div>
            </div>
          ))}
        </div>

        {review.length > 0 && (
          <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-6 flex items-center gap-3">
            <span className="text-2xl">📬</span>
            <div className="flex-1"><p className="font-medium text-zinc-900">{t('publisher.dashboard.pendingDeliveries', '{{count}} pending delivery(s)', { count: review.length })}</p><p className="text-sm text-amber-800">{t('publisher.dashboard.reviewAndApprove', 'Review and approve to complete payment.')}</p></div>
            <button onClick={() => setTab('review')} className="px-4 py-2 bg-zinc-900 text-white rounded-lg text-sm hover:bg-zinc-800">{t('publisher.dashboard.review', 'Review')}</button>
          </div>
        )}

        <div className="flex gap-1 mb-6 bg-zinc-100 rounded-lg p-1 w-fit">
          {([{ key: 'active' as Tab, label: t('publisher.dashboard.active', 'Active'), count: active.length }, { key: 'review' as Tab, label: t('publisher.dashboard.toReview', 'To Review'), count: review.length }, { key: 'history' as Tab, label: t('publisher.dashboard.history', 'History'), count: history.length }]).map(tb => (
            <button key={tb.key} onClick={() => setTab(tb.key)} className={`px-4 py-2 rounded-md text-sm font-medium ${tab === tb.key ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500'}`}>
              {tb.label} {tb.count > 0 && <span className="ml-1.5 bg-zinc-200 text-zinc-700 px-1.5 py-0.5 rounded-full text-xs">{tb.count}</span>}
            </button>
          ))}
        </div>

        {loading ? <div className="flex justify-center py-12 text-zinc-500">{t('common.loading')}</div>
        : error ? <div className="text-center py-12"><p className="text-red-600 mb-4">{error}</p><button onClick={loadTasks} className="px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800">{t('common.retry')}</button></div>
        : displayed.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">
            <div className="text-4xl mb-4">{tab === 'active' ? '📋' : tab === 'review' ? '📬' : '📚'}</div>
            <p className="text-lg font-medium">{tab === 'active' ? t('publisher.dashboard.noActiveRequests', 'No active requests') : tab === 'review' ? t('publisher.dashboard.noPendingDeliveries', 'No pending deliveries') : t('publisher.dashboard.noHistory', 'No history')}</p>
            {tab === 'active' && <button onClick={() => navigate('/publisher/requests/new')} className="mt-4 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800">{t('publisher.dashboard.createFirstRequest', 'Create First Request')}</button>}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {displayed.map(task => <TaskCard key={task.id} task={task} onReview={id => navigate(`/publisher/requests/${id}/review`)} onCancel={async id => { if (confirm(t('publisher.dashboard.confirmCancel', 'Cancel?'))) { await cancelH2ATask(id); loadTasks() } }} onAssigned={loadTasks} />)}
          </div>
        )}
      </div>

      {walletAddress && (
        <DepositModal
          open={showDeposit}
          walletAddress={walletAddress}
          depositAmountUsdc={20}
          targetBalanceUsdc={(balance ?? 0) + 20}
          currentBalanceUsdc={balance ?? 0}
          externalCustomerId={executor?.id}
          onClose={() => { setShowDeposit(false); loadBalance() }}
          onFunded={() => { setShowDeposit(false); loadBalance() }}
        />
      )}
    </div>
  )
}

export default PublisherDashboard
