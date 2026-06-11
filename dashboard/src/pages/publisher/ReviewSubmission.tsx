/**
 * ReviewSubmission - Review and approve/reject agent work for H2A tasks
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useDynamicContext } from '@dynamic-labs/sdk-react-core'
import { isEthereumWallet } from '@dynamic-labs/ethereum'
import type { Task, Submission } from '../../types/database'
import {
  getH2ATask,
  getH2ASubmissions,
  approveH2ASubmission,
  getH2APaymentConfig,
} from '../../services/h2a'
import { buildEip3009XPayment } from '../../services/h2aSigning'
import { getPaymentNetwork } from '../../constants/payment-networks'
import { createDispute, type DisputeReason } from '../../services/disputes'
import { safeHref } from '../../lib/safeHref'

const DISPUTE_REASONS: { value: DisputeReason; label: string }[] = [
  { value: 'incomplete_work', label: 'Trabajo incompleto' },
  { value: 'poor_quality', label: 'Calidad insuficiente' },
  { value: 'wrong_deliverable', label: 'Entregable incorrecto' },
  { value: 'late_delivery', label: 'Entrega tardía' },
  { value: 'fake_evidence', label: 'Evidencia falsa / manipulada' },
  { value: 'no_response', label: 'Sin respuesta del worker' },
  { value: 'payment_issue', label: 'Problema de pago' },
  { value: 'unfair_rejection', label: 'Rechazo injusto (apelación)' },
  { value: 'other', label: 'Otro' },
]

/**
 * Feature flag: H2A on-chain signing.
 * Real EIP-3009 signing IS now implemented (handleSubmit signs worker + fee
 * authorizations with the publisher's Dynamic wallet via h2aSigning.ts,
 * mirroring the agent flow). This flag is now the on-chain-testing safety
 * switch: keep it off in prod until the full flow has been verified on-chain
 * with small amounts (< $0.30), then set VITE_H2A_SIGNING_ENABLED=true in the
 * deploy env to go live. See MASTER_PLAN_H2H_WEB_SIGNING.md.
 */
const H2A_SIGNING_ENABLED = import.meta.env.VITE_H2A_SIGNING_ENABLED === 'true'

const FEE_PCT = 0.13

const GPS_KEYS = new Set(['latitude', 'longitude', 'lat', 'lng', 'lon'])

function redactGps(obj: unknown): unknown {
  if (typeof obj !== 'object' || obj === null) return obj
  if (Array.isArray(obj)) return obj.map(redactGps)
  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(obj)) {
    if (GPS_KEYS.has(key.toLowerCase()) && typeof value === 'number') {
      result[key] = '[hidden]'
    } else {
      result[key] = redactGps(value)
    }
  }
  return result
}

export function ReviewSubmission() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { primaryWallet } = useDynamicContext()
  const { taskId } = useParams<{ taskId: string }>()
  const [task, setTask] = useState<Task | null>(null)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [verdict, setVerdict] = useState<'accepted' | 'rejected' | 'needs_revision'>('accepted')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [showRawCoords, setShowRawCoords] = useState(false)
  const [disputeOpen, setDisputeOpen] = useState(false)
  const [disputeReason, setDisputeReason] = useState<DisputeReason>('incomplete_work')
  const [disputeDescription, setDisputeDescription] = useState('')
  const [disputeSubmitting, setDisputeSubmitting] = useState(false)
  const [disputeError, setDisputeError] = useState<string | null>(null)
  const [disputeSuccess, setDisputeSuccess] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    if (!taskId) return
    setLoading(true)
    try {
      const [t, s] = await Promise.all([getH2ATask(taskId), getH2ASubmissions(taskId)])
      setTask(t); setSubmissions(s.submissions || [])
    } catch (e) { setError(e instanceof Error ? e.message : 'Error') }
    finally { setLoading(false) }
  }, [taskId])

  useEffect(() => { loadData() }, [loadData])

  const latest = submissions[0]
  const bounty = task?.bounty_usd || 0
  const fee = +(bounty * FEE_PCT).toFixed(2)
  const total = +(bounty + fee).toFixed(2)

  const handleSubmit = async () => {
    if (!task || !latest) return
    setSubmitting(true); setSubmitError(null)
    try {
      let authWorker: string | undefined
      let authFee: string | undefined

      if (verdict === 'accepted') {
        // Imitate the agent flow from the browser: the publisher signs two
        // EIP-3009 authorizations with their Dynamic wallet — worker (bounty)
        // and treasury (fee) — which the backend settles gasless via the
        // Facilitator, exactly like a programmatic agent.
        if (!primaryWallet || !isEthereumWallet(primaryWallet)) {
          throw new Error(t('review.errors.connectWallet', 'Conecta una wallet EVM para firmar el pago.'))
        }
        const workerWallet = latest.executor?.wallet_address
        if (!workerWallet) {
          throw new Error(t('review.errors.noWorkerWallet', 'No se encontró la wallet del worker en la entrega.'))
        }
        const fromAddress = primaryWallet.address as `0x${string}`
        if (workerWallet.toLowerCase() === fromAddress.toLowerCase()) {
          throw new Error(t('review.errors.selfPayment', 'No puedes pagarte a ti mismo (worker == publisher).'))
        }

        const network = task.payment_network || 'base'
        const coin = task.payment_token || 'USDC'
        const net = getPaymentNetwork(network)
        const walletClient = await primaryWallet.getWalletClient(String(net.chainId))
        if (!walletClient) throw new Error(t('review.errors.walletClientUnavailable', 'Wallet client no disponible para esta red.'))

        // Fee precision must match the backend (6-decimal USDC), not the 2-dp
        // display value — the SIGNED amount is what transfers on-chain.
        const cfg = await getH2APaymentConfig()
        const feeAmount = +(bounty * cfg.fee_pct).toFixed(6)

        authWorker = await buildEip3009XPayment(walletClient, {
          from: fromAddress,
          to: workerWallet as `0x${string}`,
          amountUsd: bounty,
          network,
          coinSymbol: coin,
        })
        authFee = await buildEip3009XPayment(walletClient, {
          from: fromAddress,
          to: cfg.treasury as `0x${string}`,
          amountUsd: feeAmount,
          network,
          coinSymbol: coin,
        })
      }

      await approveH2ASubmission(taskId!, {
        submission_id: latest.id, verdict, notes: notes || undefined,
        settlement_auth_worker: authWorker,
        settlement_auth_fee: authFee,
      })
      navigate('/publisher/dashboard')
    } catch (e) { setSubmitError(e instanceof Error ? e.message : 'Error') }
    finally { setSubmitting(false) }
  }

  const handleDispute = async () => {
    if (!latest) return
    if (disputeDescription.trim().length < 5) {
      setDisputeError(t('review.dispute.minDescription', 'La descripción debe tener al menos 5 caracteres'))
      return
    }
    setDisputeSubmitting(true); setDisputeError(null); setDisputeSuccess(null)
    try {
      const created = await createDispute({
        submission_id: latest.id,
        reason: disputeReason,
        description: disputeDescription.trim(),
      })
      setDisputeSuccess(t('review.dispute.opened', 'Disputa abierta (id={{id}}…)', { id: created.id.slice(0, 8) }))
      setDisputeOpen(false)
      setDisputeDescription('')
      await loadData()
    } catch (e) {
      setDisputeError(e instanceof Error ? e.message : 'Error al abrir disputa')
    } finally {
      setDisputeSubmitting(false)
    }
  }

  if (loading) return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-500">{t('common.loading')}</div>
  if (error || !task) return <div className="min-h-screen bg-gray-50 flex items-center justify-center"><div className="text-center"><p className="text-red-500 mb-4">{error || t('review.notFound', 'No encontrado')}</p><button onClick={() => navigate('/publisher/dashboard')} className="px-4 py-2 bg-blue-600 text-white rounded-lg">{t('common.back')}</button></div></div>

  // FE-001/FE-002: H2A approval flow disabled until real EIP-3009 signing is implemented (Phase 3)
  if (!H2A_SIGNING_ENABLED) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md p-6 text-center">
          <h2 className="text-xl font-semibold mb-4">{t('review.disabled.title', 'Approval Temporarily Disabled')}</h2>
          <p className="text-gray-600 mb-4">
            {t('review.disabled.body', 'The on-chain approval flow is being upgraded for security. Approvals are currently processed via the API.')}
          </p>
          <p className="text-sm text-zinc-600 mb-6">
            {t('review.disabled.meta', 'Phase 2 security hardening — FE-001')}
          </p>
          <button
            onClick={() => navigate('/publisher/dashboard')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            {t('review.disabled.back', 'Back to Dashboard')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <button onClick={() => navigate('/publisher/dashboard')} className="text-sm text-gray-500 hover:text-gray-700 mb-3">{t('review.backToPanel', '← Volver al Panel')}</button>
          <h1 className="text-2xl font-bold">{t('review.title', 'Revisar Entrega')}</h1>
          <p className="text-sm text-gray-500 mt-1">{task.title}</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-medium mb-2">📋 {t('review.request', 'Solicitud')}</h3>
          <p className="text-sm text-gray-600 mb-3">{task.instructions}</p>
          <div className="flex gap-4 text-sm text-zinc-600">
            <span>💰 ${bounty.toFixed(2)} USDC</span>
            <span>📅 {new Date(task.deadline).toLocaleDateString('es')}</span>
          </div>
        </div>

        {submissions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">{t('review.noSubmissions', 'No hay entregas aún.')}</div>
        ) : (
          <>
            {submissions.map(sub => (
              <div key={sub.id} className="bg-gray-50 rounded-lg border p-4">
                <h4 className="font-medium mb-3">📦 {t('review.agentDelivery', 'Entrega del Agente')}</h4>
                {Object.keys(sub.evidence || {}).length > 0 && (
                  <div className="mb-3">
                    <div className="flex justify-end mb-1">
                      <button
                        onClick={() => setShowRawCoords(prev => !prev)}
                        className="text-xs text-gray-400 hover:text-gray-200 bg-gray-800 px-2 py-1 rounded"
                      >
                        {showRawCoords ? t('review.coords.hide', 'Ocultar coordenadas') : t('review.coords.show', 'Mostrar coordenadas')}
                      </button>
                    </div>
                    <pre className="bg-gray-900 text-green-400 p-3 rounded-lg text-xs overflow-auto max-h-96">
                      {JSON.stringify(showRawCoords ? sub.evidence : redactGps(sub.evidence), null, 2)}
                    </pre>
                  </div>
                )}
                {sub.evidence_files?.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-3">
                    {sub.evidence_files.map((f, i) => <a key={i} href={safeHref(f)} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline bg-white px-3 py-1 rounded border">📁 {t('review.fileN', 'Archivo {{n}}', { n: i + 1 })}</a>)}
                  </div>
                )}
                <div className="text-xs text-zinc-500">Entregado: {new Date(sub.submitted_at).toLocaleString('es')}</div>
              </div>
            ))}

            <div className="bg-white rounded-lg border p-6">
              <h3 className="font-semibold mb-4">🔍 {t('review.verdictHeading', 'Tu Veredicto')}</h3>
              <div className="grid grid-cols-3 gap-3 mb-4">
                {[
                  { v: 'accepted' as const, icon: '✅', label: t('review.verdict.approve', 'Aprobar y Pagar') },
                  { v: 'needs_revision' as const, icon: '🔄', label: t('review.verdict.revision', 'Solicitar Revisión') },
                  { v: 'rejected' as const, icon: '❌', label: t('review.verdict.reject', 'Rechazar') },
                ].map(opt => (
                  <button key={opt.v} onClick={() => setVerdict(opt.v)} className={`p-3 rounded-lg border text-center ${verdict === opt.v ? 'border-zinc-900 bg-zinc-100' : 'border-gray-200'}`}>
                    <div className="text-xl mb-1">{opt.icon}</div><div className="text-sm font-medium">{opt.label}</div>
                  </button>
                ))}
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('review.notes', 'Notas')}</label>
                <textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder={verdict === 'accepted' ? t('review.notesPlaceholderApprove', 'Comentarios opcionales...') : t('review.notesPlaceholderRevise', 'Describe qué necesita mejorar...')} className="w-full px-3 py-2 border rounded-lg h-24 resize-y bg-white text-zinc-900" />
              </div>
              {verdict === 'accepted' && (
                <div className="bg-blue-50 rounded-lg p-4 mb-4 border border-blue-200 text-sm">
                  <h4 className="font-medium text-blue-900 mb-2">💰 {t('review.payment.summary', 'Resumen de Pago')}</h4>
                  <div className="flex justify-between"><span>{t('review.payment.toAgent', 'Pago al agente:')}</span><span>${bounty.toFixed(2)} USDC</span></div>
                  <div className="flex justify-between"><span>{t('review.payment.commission', 'Comisión (13%):')}</span><span>${fee.toFixed(2)} USDC</span></div>
                  <div className="flex justify-between font-bold border-t border-blue-200 pt-1"><span>{t('review.payment.total', 'Total:')}</span><span>${total.toFixed(2)} USDC</span></div>
                  <p className="text-xs text-blue-700 mt-2">🔐 {t('review.payment.signTwo', 'Firmarás 2 autorizaciones en tu wallet.')}</p>
                </div>
              )}
              {submitError && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm mb-4">❌ {submitError}</div>}
              {disputeSuccess && <div className="bg-green-50 text-green-800 p-3 rounded-lg text-sm mb-4">✅ {disputeSuccess}</div>}
              <button onClick={handleSubmit} disabled={submitting} className={`w-full py-3 px-4 rounded-lg font-medium text-white ${verdict === 'accepted' ? 'bg-green-600 hover:bg-green-700' : verdict === 'needs_revision' ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-red-600 hover:bg-red-700'} disabled:opacity-50`}>
                {submitting ? t('review.processing', 'Procesando...') : verdict === 'accepted' ? `✅ ${t('review.verdict.approve', 'Aprobar y Pagar')}` : verdict === 'needs_revision' ? `🔄 ${t('review.verdict.revision', 'Solicitar Revisión')}` : `❌ ${t('review.verdict.reject', 'Rechazar')}`}
              </button>

              <div className="mt-4 pt-4 border-t border-gray-200">
                {!disputeOpen ? (
                  <button
                    type="button"
                    onClick={() => { setDisputeOpen(true); setDisputeError(null); setDisputeSuccess(null) }}
                    className="w-full py-2 px-4 rounded-lg border border-orange-300 text-orange-700 bg-orange-50 hover:bg-orange-100 text-sm font-medium"
                  >
                    ⚠️ {t('review.dispute.start', 'Iniciar disputa formal')}
                  </button>
                ) : (
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                    <h4 className="font-semibold text-orange-900 mb-3">⚠️ {t('review.dispute.heading', 'Abrir disputa')}</h4>
                    <p className="text-xs text-orange-800 mb-3">
                      {t('review.dispute.explainer', 'Una disputa formal marca esta entrega como impugnada y la envía al arbitraje humano. Usa esta opción solo si crees que la evidencia es fraudulenta, incompleta o no cumple con el brief.')}
                    </p>
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-orange-900 mb-1">{t('review.dispute.reason', 'Motivo')}</label>
                      <select
                        value={disputeReason}
                        onChange={e => setDisputeReason(e.target.value as DisputeReason)}
                        className="w-full px-3 py-2 border border-orange-300 rounded-lg bg-white text-sm"
                      >
                        {DISPUTE_REASONS.map(r => (
                          <option key={r.value} value={r.value}>{t(`review.dispute.reasons.${r.value}`, r.label)}</option>
                        ))}
                      </select>
                    </div>
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-orange-900 mb-1">
                        {t('review.dispute.descLabel', 'Descripción')} <span className="text-xs text-orange-700">{t('review.dispute.descHint', '(5-2000 caracteres)')}</span>
                      </label>
                      <textarea
                        value={disputeDescription}
                        onChange={e => setDisputeDescription(e.target.value)}
                        maxLength={2000}
                        placeholder={t('review.dispute.descPlaceholder', 'Explica por qué esta entrega debe ser disputada. Sé específico: qué falta, qué no cumple, qué evidencia consideras falsa...')}
                        className="w-full px-3 py-2 border border-orange-300 rounded-lg h-28 resize-y bg-white text-sm"
                      />
                      <div className="text-xs text-orange-700 mt-1 text-right">
                        {disputeDescription.length} / 2000
                      </div>
                    </div>
                    {disputeError && (
                      <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm mb-3">
                        ❌ {disputeError}
                      </div>
                    )}
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={handleDispute}
                        disabled={disputeSubmitting || disputeDescription.trim().length < 5}
                        className="flex-1 py-2 px-4 rounded-lg font-medium text-white bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                      >
                        {disputeSubmitting ? t('review.dispute.submitting', 'Enviando...') : t('review.dispute.submit', 'Abrir disputa')}
                      </button>
                      <button
                        type="button"
                        onClick={() => { setDisputeOpen(false); setDisputeError(null) }}
                        disabled={disputeSubmitting}
                        className="py-2 px-4 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-sm"
                      >
                        {t('common.cancel')}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default ReviewSubmission
