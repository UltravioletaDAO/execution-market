/**
 * RequestService — consumer "pedir un servicio" form for a single category.
 *
 * Publishes an H2A task with target_executor_type='human' (H2H) via
 * createH2ATask, so a nearby human worker can pick it up. The bounty minimum is
 * $0.01 (the backend H2A limit, feature.h2a_min_bounty); the $5 floor lives only
 * on the MoonPay top-up (DepositModal) because MoonPay imposes it on card buys —
 * the two minimums are independent. Reuses the existing publisher dashboard for
 * status tracking (Task 4.3).
 */
import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getService } from '../../constants/services'
import { createH2ATask } from '../../services/h2a'
import type { H2ATaskCreateRequest, H2ATaskCreateResponse } from '../../types/database'
import { useAuth } from '../../context/AuthContext'
import { DepositModal } from '../../components/DepositModal'
import { readEvmStablecoinBalance } from '../../services/evm-balance'
import {
  PAYMENT_NETWORKS,
  getPaymentNetwork,
  resolvePaymentRpc,
} from '../../constants/payment-networks'

const FEE_PCT = 0.13
const DEADLINES = [
  { h: 1, k: '1h', l: '1 hora' },
  { h: 4, k: '4h', l: '4 horas' },
  { h: 24, k: '1d', l: '1 día' },
  { h: 72, k: '3d', l: '3 días' },
]

export function RequestService() {
  const { t } = useTranslation()
  const { serviceKey } = useParams()
  const navigate = useNavigate()
  const svc = getService(serviceKey || '')
  const { walletAddress, executor, isAuthenticated, openAuthModal } = useAuth()

  const [instructions, setInstructions] = useState('')
  // Free-text bounty: keep the raw string so the user can clear the field and
  // type intermediate states like "0." or "0.05" without it snapping back. The
  // previous numeric state clamped every keystroke to Math.max(0.01, +value),
  // which made the field unwritable (only the spinner arrows worked).
  const [bountyInput, setBountyInput] = useState('10')
  const [deadlineHours, setDeadlineHours] = useState(24)
  const [network, setNetwork] = useState('base')
  const [stablecoin, setStablecoin] = useState('USDC')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<H2ATaskCreateResponse | null>(null)
  const [balance, setBalance] = useState<number | null>(null)
  const [showDeposit, setShowDeposit] = useState(false)

  const bounty = parseFloat(bountyInput)
  const bountyValid = Number.isFinite(bounty) && bounty >= 0.01 && bounty <= 500
  const fee = bountyValid ? +(bounty * FEE_PCT).toFixed(2) : 0
  const total = bountyValid ? +(bounty + fee).toFixed(2) : 0

  const netInfo = getPaymentNetwork(network)
  const coinInfo =
    netInfo.stablecoins.find((c) => c.symbol === stablecoin) ?? netInfo.stablecoins[0]
  // MoonPay only sells USDC on Base, so the in-app deposit is offered only there.
  // On any other network/token the publisher must already hold the stablecoin.
  const canDeposit = network === 'base' && coinInfo.symbol === 'USDC'

  // Switching networks may strand the chosen stablecoin (e.g. PYUSD only on
  // Ethereum); fall back to the network's first coin (always USDC).
  const handleNetworkChange = (key: string) => {
    setNetwork(key)
    const next = getPaymentNetwork(key)
    if (!next.stablecoins.some((c) => c.symbol === stablecoin)) {
      setStablecoin(next.stablecoins[0].symbol)
    }
  }

  const loadBalance = useCallback(async () => {
    if (!walletAddress) {
      setBalance(null)
      return
    }
    try {
      setBalance(
        await readEvmStablecoinBalance(
          walletAddress,
          netInfo.key,
          coinInfo.address,
          coinInfo.decimals,
          resolvePaymentRpc(netInfo),
        ),
      )
    } catch {
      setBalance(null)
    }
  }, [walletAddress, netInfo, coinInfo])
  useEffect(() => {
    loadBalance()
  }, [loadBalance])

  if (!svc) {
    return (
      <div className="flex min-h-screen items-center justify-center text-zinc-500">
        {t('services.request.notFound', 'Servicio no encontrado.')}
        <button className="ml-2 underline" onClick={() => navigate('/services')}>
          {t('services.request.back', 'Volver')}
        </button>
      </div>
    )
  }

  const canSubmit =
    instructions.length >= 10 && bountyValid && !submitting && !!walletAddress
  const needsFunds = balance !== null && balance < total

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const req: H2ATaskCreateRequest = {
        title: `${t(`services.catalog.${svc.key}.label`, svc.label)}: ${instructions.slice(0, 48)}`,
        instructions,
        category: svc.category,
        bounty_usd: bounty,
        deadline_hours: deadlineHours,
        verification_mode: 'manual',
        evidence_required: ['screenshot', 'text_response'],
        payment_network: netInfo.key,
        payment_token: coinInfo.symbol,
        target_executor_type: 'human',
        publisher_wallet: walletAddress ?? undefined,
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
          <h2 className="mb-2 text-2xl font-bold text-zinc-900">{t('services.request.publishedTitle', '¡Servicio publicado!')}</h2>
          <p className="mb-6 text-zinc-500">
            {t('services.request.publishedDesc', 'Un humano cercano puede aceptarlo. Haz seguimiento desde tu panel.')}
          </p>
          <div className="mb-6 rounded-lg bg-zinc-50 p-4 text-left text-sm">
            <div className="mb-1 flex justify-between">
              <span className="text-zinc-600">{t('services.request.payment', 'Pago')}</span>
              <span className="font-medium text-zinc-900">
                ${result.bounty_usd} {coinInfo.symbol} · {netInfo.label}
              </span>
            </div>
            <div className="flex justify-between font-bold text-zinc-900">
              <span>{t('services.request.totalOnApproval', 'Total al aprobar')}</span>
              <span>${result.total_required_usd} {coinInfo.symbol}</span>
            </div>
          </div>
          <button
            onClick={() => navigate('/publisher/dashboard')}
            className="w-full rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white hover:bg-zinc-800"
          >
            {t('services.request.viewPanel', 'Ver mi panel')}
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
            {t('services.request.backToServices', '← Servicios')}
          </button>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-zinc-900">
            <span>{svc.icon}</span> {t(`services.catalog.${svc.key}.label`, svc.label)}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">{t(`services.catalog.${svc.key}.desc`, svc.desc)}</p>
        </div>
      </div>

      <div className="mx-auto max-w-2xl space-y-5 px-4 py-6">
        <div>
          <label className="mb-1 block text-sm font-medium text-zinc-700">
            {t('services.request.whatNeed', '¿Qué necesitas?')} *
          </label>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder={t(`services.catalog.${svc.key}.placeholder`, svc.placeholder)}
            className="h-32 w-full resize-y rounded-lg border border-zinc-300 bg-white px-3 py-2 text-zinc-900 placeholder:text-zinc-400"
            maxLength={10000}
          />
          <p className="mt-1 text-xs text-zinc-600">{instructions.length}/10000 {t('services.request.charHint', '(mín. 10)')}</p>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-zinc-700">
            {t('services.request.payment', 'Pago')} ({coinInfo.symbol}) *
          </label>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-zinc-500">$</span>
            <input
              type="text"
              inputMode="decimal"
              value={bountyInput}
              onChange={(e) => {
                const v = e.target.value
                // Allow empty + free decimal typing ("", "0.", "0.05"); reject
                // anything that isn't a plain decimal so we never store garbage.
                if (v === '' || /^\d*\.?\d*$/.test(v)) setBountyInput(v)
              }}
              placeholder="0.10"
              className="w-full rounded-lg border border-zinc-300 bg-white py-2 pl-7 pr-16 text-zinc-900 placeholder:text-zinc-400"
            />
            <span className="absolute right-3 top-2.5 text-sm text-zinc-500">
              {coinInfo.symbol}
            </span>
          </div>
          {!bountyValid && bountyInput !== '' && (
            <p className="mt-1 text-xs text-red-600">{t('services.request.bountyRange', 'El pago debe estar entre $0.01 y $500.')}</p>
          )}

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-zinc-500">{t('services.request.network', 'Red')}</label>
              <select
                value={network}
                onChange={(e) => handleNetworkChange(e.target.value)}
                className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
              >
                {PAYMENT_NETWORKS.map((n) => (
                  <option key={n.key} value={n.key}>
                    {n.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-zinc-500">{t('services.request.stablecoin', 'Stablecoin')}</label>
              <select
                value={coinInfo.symbol}
                onChange={(e) => setStablecoin(e.target.value)}
                className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
              >
                {netInfo.stablecoins.map((c) => (
                  <option key={c.symbol} value={c.symbol}>
                    {c.symbol}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-2 rounded-lg bg-white border border-zinc-200 p-3 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-700">{t('services.request.payExecutor', 'Pago al ejecutor')}</span>
              <span className="font-medium text-zinc-900">${(bountyValid ? bounty : 0).toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-700">{t('services.request.commission', 'Comisión (13%)')}</span>
              <span className="font-medium text-zinc-900">${fee.toFixed(2)}</span>
            </div>
            <div className="mt-1 flex justify-between border-t border-zinc-200 pt-1 font-bold text-zinc-900">
              <span>{t('services.request.totalOnApproval', 'Total al aprobar')}</span>
              <span>${total.toFixed(2)} {coinInfo.symbol}</span>
            </div>
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-700">{t('services.request.deadline', 'Plazo')} *</label>
          <div className="grid grid-cols-4 gap-2">
            {DEADLINES.map((d) => (
              <button
                key={d.h}
                onClick={() => setDeadlineHours(d.h)}
                className={`rounded-lg border px-3 py-2 text-sm ${deadlineHours === d.h ? 'border-zinc-900 bg-zinc-900 text-white' : 'border-zinc-200 text-zinc-700'}`}
              >
                {t(`services.deadlines.${d.k}`, d.l)}
              </button>
            ))}
          </div>
        </div>

        {walletAddress && (
          <div className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white p-3 text-sm">
            <span className="text-zinc-500">
              {t('services.request.balance', 'Tu saldo:')} {balance === null ? '—' : `$${balance.toFixed(2)} ${coinInfo.symbol}`}
              <span className="ml-1 text-zinc-600">· {netInfo.label}</span>
              {needsFunds && (
                <span className="ml-2 text-zinc-900">· {t('services.request.needs', 'necesitas')} ${total.toFixed(2)}</span>
              )}
            </span>
            {canDeposit ? (
              <button
                onClick={() => setShowDeposit(true)}
                className="rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800"
              >
                + {t('services.request.deposit', 'Depositar')}
              </button>
            ) : (
              <span className="text-xs text-zinc-600">{t('services.request.depositOnBase', 'Deposita en Base/USDC')}</span>
            )}
          </div>
        )}

        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">❌ {error}</div>}

        {isAuthenticated ? (
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full rounded-lg bg-zinc-900 px-6 py-3 font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            {submitting ? t('services.request.publishing', 'Publicando…') : `🚀 ${t('services.request.publish', 'Publicar servicio')}`}
          </button>
        ) : (
          <div className="rounded-lg border border-zinc-200 bg-white p-4 text-center">
            <p className="mb-3 text-sm text-zinc-600">
              {t('services.request.loginPrompt', 'Inicia sesión para publicar tu servicio y pagar de forma segura.')}
            </p>
            <button
              onClick={openAuthModal}
              className="w-full rounded-lg bg-zinc-900 px-6 py-3 font-medium text-white hover:bg-zinc-800"
            >
              {t('services.request.loginButton', 'Iniciar sesión para publicar')}
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
