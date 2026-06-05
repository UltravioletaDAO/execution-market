/**
 * RequestService — consumer "pedir un servicio" form for a single category.
 *
 * Publishes an H2A task with target_executor_type='human' (H2H) via
 * createH2ATask, so a nearby human worker can pick it up. Enforces the O6 $5
 * minimum and offers DepositModal top-up if the wallet is short. Reuses the
 * existing publisher dashboard for status tracking (Task 4.3).
 */
import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getService } from '../../constants/services'
import { createH2ATask } from '../../services/h2a'
import type { H2ATaskCreateRequest, H2ATaskCreateResponse } from '../../types/database'
import { useAuth } from '../../context/AuthContext'
import { DepositModal } from '../../components/DepositModal'
import { readEvmUsdcBalance, resolveEvmRpc } from '../../services/evm-balance'

const FEE_PCT = 0.13
const DEADLINES = [
  { h: 1, l: '1 hora' },
  { h: 4, l: '4 horas' },
  { h: 24, l: '1 día' },
  { h: 72, l: '3 días' },
]

export function RequestService() {
  const { serviceKey } = useParams()
  const navigate = useNavigate()
  const svc = getService(serviceKey || '')
  const { walletAddress, executor, isAuthenticated, openAuthModal } = useAuth()

  const [instructions, setInstructions] = useState('')
  const [bounty, setBounty] = useState(10)
  const [deadlineHours, setDeadlineHours] = useState(24)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<H2ATaskCreateResponse | null>(null)
  const [balance, setBalance] = useState<number | null>(null)
  const [showDeposit, setShowDeposit] = useState(false)

  const fee = +(bounty * FEE_PCT).toFixed(2)
  const total = +(bounty + fee).toFixed(2)

  const loadBalance = useCallback(async () => {
    if (!walletAddress) {
      setBalance(null)
      return
    }
    try {
      setBalance(await readEvmUsdcBalance(walletAddress, resolveEvmRpc('base'), 'base'))
    } catch {
      setBalance(null)
    }
  }, [walletAddress])
  useEffect(() => {
    loadBalance()
  }, [loadBalance])

  if (!svc) {
    return (
      <div className="flex min-h-screen items-center justify-center text-zinc-500">
        Servicio no encontrado.
        <button className="ml-2 underline" onClick={() => navigate('/services')}>
          Volver
        </button>
      </div>
    )
  }

  const canSubmit = instructions.length >= 20 && bounty >= 5 && !submitting
  const needsFunds = balance !== null && balance < total

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const req: H2ATaskCreateRequest = {
        title: `${svc.label}: ${instructions.slice(0, 48)}`,
        instructions,
        category: svc.category,
        bounty_usd: bounty,
        deadline_hours: deadlineHours,
        verification_mode: 'manual',
        evidence_required: ['screenshot', 'text_response'],
        payment_network: 'base',
        target_executor_type: 'human',
      }
      setResult(await createH2ATask(req))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error')
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 p-4">
        <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-8 text-center shadow-lg">
          <div className="mb-4 text-5xl">✅</div>
          <h2 className="mb-2 text-2xl font-bold text-zinc-900">¡Servicio publicado!</h2>
          <p className="mb-6 text-zinc-500">
            Un humano cercano puede aceptarlo. Haz seguimiento desde tu panel.
          </p>
          <div className="mb-6 rounded-lg bg-zinc-50 p-4 text-left text-sm">
            <div className="mb-1 flex justify-between">
              <span className="text-zinc-500">Pago</span>
              <span className="font-medium">${result.bounty_usd} USDC</span>
            </div>
            <div className="flex justify-between font-bold">
              <span>Total al aprobar</span>
              <span>${result.total_required_usd} USDC</span>
            </div>
          </div>
          <button
            onClick={() => navigate('/publisher/dashboard')}
            className="w-full rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white hover:bg-zinc-800"
          >
            Ver mi panel
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="border-b border-zinc-200 bg-white">
        <div className="mx-auto max-w-2xl px-4 py-5">
          <button
            onClick={() => navigate('/services')}
            className="mb-2 text-sm text-zinc-500 hover:text-zinc-900"
          >
            ← Servicios
          </button>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-zinc-900">
            <span>{svc.icon}</span> {svc.label}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">{svc.desc}</p>
        </div>
      </div>

      <div className="mx-auto max-w-2xl space-y-5 px-4 py-6">
        <div>
          <label className="mb-1 block text-sm font-medium text-zinc-700">
            ¿Qué necesitas? *
          </label>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder={svc.placeholder}
            className="h-32 w-full resize-y rounded-lg border border-zinc-300 px-3 py-2"
            maxLength={10000}
          />
          <p className="mt-1 text-xs text-zinc-400">{instructions.length}/10000 (mín. 20)</p>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-zinc-700">Pago (USDC) *</label>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-zinc-400">$</span>
            <input
              type="number"
              value={bounty}
              onChange={(e) => setBounty(Math.max(5, +e.target.value))}
              step="1"
              min="5"
              max="500"
              className="w-full rounded-lg border border-zinc-300 py-2 pl-7 pr-16"
            />
            <span className="absolute right-3 top-2.5 text-sm text-zinc-400">USDC</span>
          </div>
          <div className="mt-2 rounded-lg bg-white border border-zinc-200 p-3 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-500">Pago al ejecutor</span>
              <span>${bounty.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Comisión (13%)</span>
              <span>${fee.toFixed(2)}</span>
            </div>
            <div className="mt-1 flex justify-between border-t border-zinc-200 pt-1 font-bold">
              <span>Total al aprobar</span>
              <span>${total.toFixed(2)} USDC</span>
            </div>
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-700">Plazo *</label>
          <div className="grid grid-cols-4 gap-2">
            {DEADLINES.map((d) => (
              <button
                key={d.h}
                onClick={() => setDeadlineHours(d.h)}
                className={`rounded-lg border px-3 py-2 text-sm ${deadlineHours === d.h ? 'border-zinc-900 bg-zinc-900 text-white' : 'border-zinc-200 text-zinc-700'}`}
              >
                {d.l}
              </button>
            ))}
          </div>
        </div>

        {walletAddress && (
          <div className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white p-3 text-sm">
            <span className="text-zinc-500">
              Tu saldo: {balance === null ? '—' : `$${balance.toFixed(2)} USDC`}
              {needsFunds && <span className="ml-2 text-zinc-900">· necesitas ${total.toFixed(2)}</span>}
            </span>
            <button
              onClick={() => setShowDeposit(true)}
              className="rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800"
            >
              + Depositar
            </button>
          </div>
        )}

        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">❌ {error}</div>}

        {isAuthenticated ? (
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full rounded-lg bg-zinc-900 px-6 py-3 font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            {submitting ? 'Publicando…' : '🚀 Publicar servicio'}
          </button>
        ) : (
          <div className="rounded-lg border border-zinc-200 bg-white p-4 text-center">
            <p className="mb-3 text-sm text-zinc-600">
              Inicia sesión para publicar tu servicio y pagar de forma segura.
            </p>
            <button
              onClick={openAuthModal}
              className="w-full rounded-lg bg-zinc-900 px-6 py-3 font-medium text-white hover:bg-zinc-800"
            >
              Iniciar sesión para publicar
            </button>
          </div>
        )}
      </div>

      {walletAddress && (
        <DepositModal
          open={showDeposit}
          walletAddress={walletAddress}
          depositAmountUsdc={Math.max(5, total - (balance ?? 0))}
          targetBalanceUsdc={total}
          currentBalanceUsdc={balance ?? 0}
          externalCustomerId={executor?.id}
          onClose={() => {
            setShowDeposit(false)
            loadBalance()
          }}
          onFunded={() => {
            setShowDeposit(false)
            loadBalance()
          }}
        />
      )}
    </div>
  )
}

export default RequestService
