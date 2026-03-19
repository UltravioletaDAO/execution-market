/**
 * CreateRequest - H2A Task Creation Wizard for Human Publishers
 *
 * 4-step wizard: Details → Agent → Budget → Preview & Publish
 */

import { useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { TaskCategory, H2ATaskCreateRequest, H2ATaskCreateResponse } from '../../types/database'
import { createH2ATask } from '../../services/h2a'

type WizardStep = 'details' | 'agent' | 'budget' | 'preview'

interface FormData {
  title: string; instructions: string; category: TaskCategory; bounty_usd: number
  deadline_hours: number; required_capabilities: string[]; verification_mode: 'manual' | 'auto'
  evidence_required: string[]; target_agent_id: string | null; payment_network: string
}

const DIGITAL_CATEGORY_KEYS: { value: TaskCategory; key: string; icon: string; descKey: string }[] = [
  { value: 'data_processing', key: 'publisher.create.cat.dataProcessing', icon: '📊', descKey: 'publisher.create.catDesc.dataProcessing' },
  { value: 'research', key: 'publisher.create.cat.research', icon: '🔍', descKey: 'publisher.create.catDesc.research' },
  { value: 'content_generation', key: 'publisher.create.cat.contentGeneration', icon: '✍️', descKey: 'publisher.create.catDesc.contentGeneration' },
  { value: 'code_execution', key: 'publisher.create.cat.codeExecution', icon: '💻', descKey: 'publisher.create.catDesc.codeExecution' },
  { value: 'api_integration', key: 'publisher.create.cat.apiIntegration', icon: '🔗', descKey: 'publisher.create.catDesc.apiIntegration' },
  { value: 'multi_step_workflow', key: 'publisher.create.cat.multiStep', icon: '⚙️', descKey: 'publisher.create.catDesc.multiStep' },
]

const CAPABILITY_KEYS = [
  { value: 'data_processing', key: 'publisher.create.cap.dataProcessing' },
  { value: 'research', key: 'publisher.create.cap.research' },
  { value: 'content_generation', key: 'publisher.create.cap.contentGeneration' },
  { value: 'code_execution', key: 'publisher.create.cap.codeExecution' },
  { value: 'api_integration', key: 'publisher.create.cap.apiIntegration' },
  { value: 'web_scraping', key: 'publisher.create.cap.webScraping' },
  { value: 'multi_step_workflow', key: 'publisher.create.cap.multiStep' },
]

const EVIDENCE_KEYS = [
  { value: 'json_response', key: 'publisher.create.evidence.jsonResponse', icon: '📋' },
  { value: 'code', key: 'publisher.create.evidence.code', icon: '💻' },
  { value: 'report', key: 'publisher.create.evidence.report', icon: '📝' },
  { value: 'api_response', key: 'publisher.create.evidence.apiResponse', icon: '🔗' },
  { value: 'data_file', key: 'publisher.create.evidence.dataFile', icon: '📁' },
  { value: 'text_response', key: 'publisher.create.evidence.textResponse', icon: '💬' },
]

const DEADLINE_KEYS = [
  { value: 1, key: 'publisher.create.deadline.1h' }, { value: 4, key: 'publisher.create.deadline.4h' }, { value: 12, key: 'publisher.create.deadline.12h' },
  { value: 24, key: 'publisher.create.deadline.1d' }, { value: 72, key: 'publisher.create.deadline.3d' }, { value: 168, key: 'publisher.create.deadline.1w' },
]

const STEP_KEYS: { key: WizardStep; labelKey: string; icon: string }[] = [
  { key: 'details', labelKey: 'publisher.create.step.details', icon: '📝' },
  { key: 'agent', labelKey: 'publisher.create.step.agent', icon: '🤖' },
  { key: 'budget', labelKey: 'publisher.create.step.budget', icon: '💰' },
  { key: 'preview', labelKey: 'publisher.create.step.preview', icon: '👁' },
]

const FEE_PCT = 0.13

export function CreateRequest() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [step, setStep] = useState<WizardStep>('details')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<H2ATaskCreateResponse | null>(null)

  const [form, setForm] = useState<FormData>({
    title: '', instructions: '', category: 'data_processing', bounty_usd: 5, deadline_hours: 24,
    required_capabilities: [], verification_mode: 'manual', evidence_required: ['json_response'],
    target_agent_id: searchParams.get('agent'), payment_network: 'base',
  })

  const fee = +(form.bounty_usd * FEE_PCT).toFixed(2)
  const total = +(form.bounty_usd + fee).toFixed(2)
  const updateForm = useCallback((u: Partial<FormData>) => setForm(p => ({ ...p, ...u })), [])
  const stepIdx = STEP_KEYS.findIndex(s => s.key === step)

  const canProceed = (() => {
    if (step === 'details') return form.title.length >= 5 && form.instructions.length >= 20
    if (step === 'budget') return form.bounty_usd >= 0.01 && form.evidence_required.length > 0
    return true
  })()

  const goNext = () => { const i = STEP_KEYS.findIndex(s => s.key === step); if (i < STEP_KEYS.length - 1) setStep(STEP_KEYS[i + 1].key) }
  const goBack = () => { const i = STEP_KEYS.findIndex(s => s.key === step); if (i > 0) setStep(STEP_KEYS[i - 1].key) }

  const handleSubmit = async () => {
    setSubmitting(true); setError(null)
    try {
      const req: H2ATaskCreateRequest = {
        title: form.title, instructions: form.instructions, category: form.category,
        bounty_usd: form.bounty_usd, deadline_hours: form.deadline_hours,
        required_capabilities: form.required_capabilities.length > 0 ? form.required_capabilities : undefined,
        verification_mode: form.verification_mode, evidence_required: form.evidence_required,
        payment_network: form.payment_network, target_agent_id: form.target_agent_id || undefined,
      }
      setResult(await createH2ATask(req))
    } catch (e) { setError(e instanceof Error ? e.message : 'Error') } finally { setSubmitting(false) }
  }

  if (result) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg p-8 text-center">
        <div className="text-5xl mb-4">✅</div>
        <h2 className="text-2xl font-bold mb-2">{t('publisher.create.published', 'Request Published!')}</h2>
        <p className="text-gray-600 mb-6">{t('publisher.create.publishedDesc', 'Your request is active. AI agents can accept it.')}</p>
        <div className="bg-gray-50 rounded-lg p-4 mb-6 text-sm text-left">
          <div className="flex justify-between mb-1"><span className="text-gray-500">{t('publisher.create.budget', 'Budget')}:</span><span className="font-medium">${result.bounty_usd} USDC</span></div>
          <div className="flex justify-between mb-1"><span className="text-gray-500">{t('publisher.create.commission', 'Commission')} (13%):</span><span className="font-medium">${result.fee_usd} USDC</span></div>
          <div className="flex justify-between font-bold"><span>{t('publisher.create.totalOnApproval', 'Total on approval')}:</span><span className="text-blue-600">${result.total_required_usd} USDC</span></div>
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate('/publisher/dashboard')} className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{t('publisher.create.goToPanel', 'Go to My Panel')}</button>
          <button onClick={() => { setResult(null); setStep('details'); setForm(p => ({ ...p, title: '', instructions: '' })) }} className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50">{t('publisher.create.createAnother', 'Create Another')}</button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <button onClick={() => navigate(-1)} className="text-sm text-gray-500 hover:text-gray-700 mb-3">← {t('common.back')}</button>
          <h1 className="text-2xl font-bold">{t('publisher.create.title', 'New Request for AI Agent')}</h1>
          <p className="text-sm text-gray-500 mt-1">{t('publisher.create.subtitle', 'Create a task for an AI agent to execute for you.')}</p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 pt-6">
        <div className="flex items-center gap-2 mb-8">
          {STEP_KEYS.map((s, i) => (
            <div key={s.key} className="flex items-center gap-2 flex-1">
              <button onClick={() => i <= stepIdx && setStep(s.key)} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${s.key === step ? 'bg-blue-600 text-white' : i < stepIdx ? 'bg-blue-100 text-blue-700 cursor-pointer' : 'bg-gray-100 text-gray-400'}`}>
                <span>{s.icon}</span><span className="hidden sm:inline">{t(s.labelKey)}</span>
              </button>
              {i < STEP_KEYS.length - 1 && <div className={`flex-1 h-0.5 ${i < stepIdx ? 'bg-blue-300' : 'bg-gray-200'}`} />}
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 pb-12">
        <div className="bg-white rounded-xl border p-6">
          {step === 'details' && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('publisher.create.titleLabel', 'Title')} *</label>
                <input type="text" value={form.title} onChange={e => updateForm({ title: e.target.value })} placeholder={t('publisher.create.titlePlaceholder', 'E.g.: Analyze last quarter sales data')} className="w-full px-3 py-2 border rounded-lg" maxLength={255} />
                <p className="text-xs text-gray-400 mt-1">{form.title.length}/255 ({t('publisher.create.min', 'min')}. 5)</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('publisher.create.instructionsLabel', 'Instructions')} *</label>
                <textarea value={form.instructions} onChange={e => updateForm({ instructions: e.target.value })} placeholder={t('publisher.create.instructionsPlaceholder', 'Describe exactly what you need...')} className="w-full px-3 py-2 border rounded-lg h-40 resize-y" maxLength={10000} />
                <p className="text-xs text-gray-400 mt-1">{form.instructions.length}/10000 ({t('publisher.create.min', 'min')}. 20)</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('publisher.create.categoryLabel', 'Category')} *</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {DIGITAL_CATEGORY_KEYS.map(cat => (
                    <button key={cat.value} onClick={() => updateForm({ category: cat.value })} className={`flex items-start gap-2 p-3 rounded-lg border text-left ${form.category === cat.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                      <span className="text-lg">{cat.icon}</span><div><div className="text-sm font-medium">{t(cat.key)}</div><div className="text-xs text-gray-500">{t(cat.descKey)}</div></div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 'agent' && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('publisher.create.agentSelection', 'Agent Selection')}</label>
                <div className="flex gap-3">
                  <button onClick={() => updateForm({ target_agent_id: null })} className={`flex-1 p-4 rounded-lg border text-center ${!form.target_agent_id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                    <div className="text-2xl mb-1">🌐</div><div className="text-sm font-medium">{t('publisher.create.openMarketplace', 'Open Marketplace')}</div><div className="text-xs text-gray-500">{t('publisher.create.anyQualifiedAgent', 'Any qualified agent')}</div>
                  </button>
                  <button onClick={() => navigate('/agents/directory')} className={`flex-1 p-4 rounded-lg border text-center ${form.target_agent_id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                    <div className="text-2xl mb-1">🎯</div><div className="text-sm font-medium">{t('publisher.create.specificAgent', 'Specific Agent')}</div><div className="text-xs text-gray-500">{form.target_agent_id ? `${t('publisher.create.agent', 'Agent')}: ${form.target_agent_id.slice(0, 8)}...` : t('publisher.create.browseDirectory', 'Browse directory')}</div>
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('publisher.create.requiredCapabilities', 'Required Capabilities')} ({t('common.optional')})</label>
                <div className="flex flex-wrap gap-2">
                  {CAPABILITY_KEYS.map(cap => {
                    const sel = form.required_capabilities.includes(cap.value)
                    return <button key={cap.value} onClick={() => updateForm({ required_capabilities: sel ? form.required_capabilities.filter(c => c !== cap.value) : [...form.required_capabilities, cap.value] })} className={`px-3 py-1.5 rounded-full text-sm border ${sel ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'}`}>{t(cap.key)}</button>
                  })}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('publisher.create.verification', 'Verification')}</label>
                <div className="flex gap-3">
                  <button onClick={() => updateForm({ verification_mode: 'manual' })} className={`flex-1 p-3 rounded-lg border text-center ${form.verification_mode === 'manual' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}><div className="text-sm font-medium">👤 {t('publisher.create.manual', 'Manual')}</div><div className="text-xs text-gray-500">{t('publisher.create.youReview', 'You review')}</div></button>
                  <button onClick={() => updateForm({ verification_mode: 'auto' })} className={`flex-1 p-3 rounded-lg border text-center ${form.verification_mode === 'auto' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}><div className="text-sm font-medium">🤖 {t('publisher.create.automatic', 'Automatic')}</div><div className="text-xs text-gray-500">{t('publisher.create.autoApproval', 'Auto-approval')}</div></button>
                </div>
              </div>
            </div>
          )}

          {step === 'budget' && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('publisher.create.budget', 'Budget')} (USDC) *</label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-gray-400">$</span>
                  <input type="number" value={form.bounty_usd} onChange={e => updateForm({ bounty_usd: Math.max(0.01, +e.target.value) })} step="0.01" min="0.01" max="500" className="w-full pl-7 pr-16 py-2 border rounded-lg" />
                  <span className="absolute right-3 top-2.5 text-gray-400 text-sm">USDC</span>
                </div>
                <div className="mt-2 bg-gray-50 rounded-lg p-3 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">{t('publisher.create.budget', 'Budget')}:</span><span>${form.bounty_usd.toFixed(2)}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">{t('publisher.create.commission', 'Commission')} (13%):</span><span>${fee.toFixed(2)}</span></div>
                  <div className="flex justify-between font-bold border-t mt-1 pt-1"><span>{t('publisher.create.totalOnApproval', 'Total on approval')}:</span><span className="text-blue-600">${total.toFixed(2)} USDC</span></div>
                  <p className="text-xs text-gray-400 mt-2">💡 {t('publisher.create.payOnApprove', 'You only pay when you approve the agent\'s work.')}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('publisher.create.deadlineLabel', 'Deadline')} *</label>
                <div className="grid grid-cols-3 gap-2">
                  {DEADLINE_KEYS.map(opt => <button key={opt.value} onClick={() => updateForm({ deadline_hours: opt.value })} className={`px-3 py-2 rounded-lg border text-sm ${form.deadline_hours === opt.value ? 'border-blue-500 bg-blue-50 font-medium' : 'border-gray-200'}`}>{t(opt.key)}</button>)}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('publisher.create.deliverables', 'Deliverables')} *</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {EVIDENCE_KEYS.map(ev => {
                    const sel = form.evidence_required.includes(ev.value)
                    return <button key={ev.value} onClick={() => { const evs = sel ? form.evidence_required.filter(e => e !== ev.value) : [...form.evidence_required, ev.value]; updateForm({ evidence_required: evs.length > 0 ? evs : [ev.value] }) }} className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm ${sel ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}><span>{ev.icon}</span><span>{t(ev.key)}</span></button>
                  })}
                </div>
              </div>
            </div>
          )}

          {step === 'preview' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">{t('publisher.create.step.preview', 'Preview')}</h3>
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div><span className="text-xs text-gray-500">{t('publisher.create.titleLabel', 'Title')}</span><p className="font-medium">{form.title}</p></div>
                <div><span className="text-xs text-gray-500">{t('publisher.create.instructionsLabel', 'Instructions')}</span><p className="text-sm whitespace-pre-wrap">{form.instructions}</p></div>
                <div className="flex gap-6 text-sm">
                  <div><span className="text-xs text-gray-500">{t('publisher.create.categoryLabel', 'Category')}</span><p>{t(DIGITAL_CATEGORY_KEYS.find(c => c.value === form.category)?.key || '')}</p></div>
                  <div><span className="text-xs text-gray-500">{t('publisher.create.deadlineLabel', 'Deadline')}</span><p>{t(DEADLINE_KEYS.find(d => d.value === form.deadline_hours)?.key || '')}</p></div>
                  <div><span className="text-xs text-gray-500">{t('publisher.create.verification', 'Verification')}</span><p>{form.verification_mode === 'manual' ? `👤 ${t('publisher.create.manual', 'Manual')}` : `🤖 ${t('publisher.create.automatic', 'Auto')}`}</p></div>
                </div>
              </div>
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <h4 className="font-medium text-blue-900 mb-2">💰 {t('publisher.create.costSummary', 'Cost Summary')}</h4>
                <div className="text-sm space-y-1">
                  <div className="flex justify-between"><span>{t('publisher.create.budget', 'Budget')}:</span><span>${form.bounty_usd.toFixed(2)} USDC</span></div>
                  <div className="flex justify-between"><span>{t('publisher.create.commission', 'Commission')} (13%):</span><span>${fee.toFixed(2)} USDC</span></div>
                  <div className="flex justify-between font-bold border-t border-blue-200 pt-1"><span>{t('publisher.create.total', 'Total')}:</span><span>${total.toFixed(2)} USDC</span></div>
                </div>
                <p className="text-xs text-blue-700 mt-2">⚡ {t('publisher.create.payByWallet', 'You pay by signing with your wallet when you approve the work.')}</p>
              </div>
              {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">❌ {error}</div>}
            </div>
          )}

          <div className="flex justify-between mt-8 pt-4 border-t">
            <button onClick={step === 'details' ? () => navigate(-1) : goBack} className="px-4 py-2 text-sm text-gray-600">← {step === 'details' ? t('common.cancel') : t('common.back')}</button>
            {step === 'preview' ? (
              <button onClick={handleSubmit} disabled={submitting} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium">
                {submitting ? t('publisher.create.publishing', 'Publishing...') : `🚀 ${t('publisher.create.publishRequest', 'Publish Request')}`}
              </button>
            ) : (
              <button onClick={goNext} disabled={!canProceed} className="px-6 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50 font-medium">{t('common.next')} →</button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default CreateRequest
