/**
 * ReviewSubmission - Review and approve/reject agent work for H2A tasks
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { Task, Submission } from '../../types/database'
import { getH2ATask, getH2ASubmissions, approveH2ASubmission } from '../../services/h2a'
import { safeHref } from '../../lib/safeHref'

/**
 * Feature flag: H2A on-chain signing.
 * The approval flow currently sends placeholder strings ('pending_browser_signature')
 * instead of real EIP-3009 signatures. The backend silently rejects them, causing
 * a false "success" state. Gate the entire approval UI behind this flag until
 * Phase 3 implements real viem signing.
 *
 * Set VITE_H2A_SIGNING_ENABLED=true in .env.local to re-enable during development.
 * See: FE-001, FE-002 in security audit.
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
  const navigate = useNavigate()
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
      await approveH2ASubmission(taskId!, {
        submission_id: latest.id, verdict, notes: notes || undefined,
        settlement_auth_worker: verdict === 'accepted' ? 'pending_browser_signature' : undefined,
        settlement_auth_fee: verdict === 'accepted' ? 'pending_browser_signature' : undefined,
      })
      navigate('/publisher/dashboard')
    } catch (e) { setSubmitError(e instanceof Error ? e.message : 'Error') }
    finally { setSubmitting(false) }
  }

  if (loading) return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-500">Cargando...</div>
  if (error || !task) return <div className="min-h-screen bg-gray-50 flex items-center justify-center"><div className="text-center"><p className="text-red-500 mb-4">{error || 'No encontrado'}</p><button onClick={() => navigate('/publisher/dashboard')} className="px-4 py-2 bg-blue-600 text-white rounded-lg">Volver</button></div></div>

  // FE-001/FE-002: H2A approval flow disabled until real EIP-3009 signing is implemented (Phase 3)
  if (!H2A_SIGNING_ENABLED) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md p-6 text-center">
          <h2 className="text-xl font-semibold mb-4">Approval Temporarily Disabled</h2>
          <p className="text-gray-600 mb-4">
            The on-chain approval flow is being upgraded for security.
            Approvals are currently processed via the API.
          </p>
          <p className="text-sm text-gray-400 mb-6">
            Phase 2 security hardening — FE-001
          </p>
          <button
            onClick={() => navigate('/publisher/dashboard')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <button onClick={() => navigate('/publisher/dashboard')} className="text-sm text-gray-500 hover:text-gray-700 mb-3">← Volver al Panel</button>
          <h1 className="text-2xl font-bold">Revisar Entrega</h1>
          <p className="text-sm text-gray-500 mt-1">{task.title}</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-medium mb-2">📋 Solicitud</h3>
          <p className="text-sm text-gray-600 mb-3">{task.instructions}</p>
          <div className="flex gap-4 text-sm text-gray-400">
            <span>💰 ${bounty.toFixed(2)} USDC</span>
            <span>📅 {new Date(task.deadline).toLocaleDateString('es')}</span>
          </div>
        </div>

        {submissions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No hay entregas aún.</div>
        ) : (
          <>
            {submissions.map(sub => (
              <div key={sub.id} className="bg-gray-50 rounded-lg border p-4">
                <h4 className="font-medium mb-3">📦 Entrega del Agente</h4>
                {Object.keys(sub.evidence || {}).length > 0 && (
                  <div className="mb-3">
                    <div className="flex justify-end mb-1">
                      <button
                        onClick={() => setShowRawCoords(prev => !prev)}
                        className="text-xs text-gray-400 hover:text-gray-200 bg-gray-800 px-2 py-1 rounded"
                      >
                        {showRawCoords ? 'Ocultar coordenadas' : 'Mostrar coordenadas'}
                      </button>
                    </div>
                    <pre className="bg-gray-900 text-green-400 p-3 rounded-lg text-xs overflow-auto max-h-96">
                      {JSON.stringify(showRawCoords ? sub.evidence : redactGps(sub.evidence), null, 2)}
                    </pre>
                  </div>
                )}
                {sub.evidence_files?.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-3">
                    {sub.evidence_files.map((f, i) => <a key={i} href={safeHref(f)} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline bg-white px-3 py-1 rounded border">📁 Archivo {i + 1}</a>)}
                  </div>
                )}
                <div className="text-xs text-gray-400">Entregado: {new Date(sub.submitted_at).toLocaleString('es')}</div>
              </div>
            ))}

            <div className="bg-white rounded-lg border p-6">
              <h3 className="font-semibold mb-4">🔍 Tu Veredicto</h3>
              <div className="grid grid-cols-3 gap-3 mb-4">
                {[
                  { v: 'accepted' as const, icon: '✅', label: 'Aprobar y Pagar' },
                  { v: 'needs_revision' as const, icon: '🔄', label: 'Solicitar Revisión' },
                  { v: 'rejected' as const, icon: '❌', label: 'Rechazar' },
                ].map(opt => (
                  <button key={opt.v} onClick={() => setVerdict(opt.v)} className={`p-3 rounded-lg border text-center ${verdict === opt.v ? `border-${opt.v === 'accepted' ? 'green' : opt.v === 'rejected' ? 'red' : 'yellow'}-500 bg-${opt.v === 'accepted' ? 'green' : opt.v === 'rejected' ? 'red' : 'yellow'}-50` : 'border-gray-200'}`}>
                    <div className="text-xl mb-1">{opt.icon}</div><div className="text-sm font-medium">{opt.label}</div>
                  </button>
                ))}
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Notas</label>
                <textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder={verdict === 'accepted' ? 'Comentarios opcionales...' : 'Describe qué necesita mejorar...'} className="w-full px-3 py-2 border rounded-lg h-24 resize-y" />
              </div>
              {verdict === 'accepted' && (
                <div className="bg-blue-50 rounded-lg p-4 mb-4 border border-blue-200 text-sm">
                  <h4 className="font-medium text-blue-900 mb-2">💰 Resumen de Pago</h4>
                  <div className="flex justify-between"><span>Pago al agente:</span><span>${bounty.toFixed(2)} USDC</span></div>
                  <div className="flex justify-between"><span>Comisión (13%):</span><span>${fee.toFixed(2)} USDC</span></div>
                  <div className="flex justify-between font-bold border-t border-blue-200 pt-1"><span>Total:</span><span>${total.toFixed(2)} USDC</span></div>
                  <p className="text-xs text-blue-700 mt-2">🔐 Firmarás 2 autorizaciones en tu wallet.</p>
                </div>
              )}
              {submitError && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm mb-4">❌ {submitError}</div>}
              <button onClick={handleSubmit} disabled={submitting} className={`w-full py-3 px-4 rounded-lg font-medium text-white ${verdict === 'accepted' ? 'bg-green-600 hover:bg-green-700' : verdict === 'needs_revision' ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-red-600 hover:bg-red-700'} disabled:opacity-50`}>
                {submitting ? 'Procesando...' : verdict === 'accepted' ? '✅ Aprobar y Pagar' : verdict === 'needs_revision' ? '🔄 Solicitar Revisión' : '❌ Rechazar'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default ReviewSubmission
