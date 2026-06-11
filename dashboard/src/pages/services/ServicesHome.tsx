/**
 * ServicesHome — the Rappi-style "¿qué necesitas hoy?" catalog (web).
 *
 * Category tiles → /services/:key (RequestService). Header shows the user's
 * Base USDC balance with a one-tap "Depositar" (DepositModal). This is the
 * consumer face of the human-hires-human loop. B&W canonical styling.
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { SERVICES } from '../../constants/services'
import { useAuth } from '../../context/AuthContext'
import { DepositModal } from '../../components/DepositModal'
import { readEvmUsdcBalance, resolveEvmRpc } from '../../services/evm-balance'

export function ServicesHome() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { walletAddress, executor } = useAuth()
  const [balance, setBalance] = useState<number | null>(null)
  const [showDeposit, setShowDeposit] = useState(false)

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

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2">
            <span className="text-sm">📍</span>
            <span className="font-mono text-sm font-medium text-zinc-900">{t('services.home.yourZone', 'Tu zona')}</span>
          </div>
          {walletAddress && (
            <button
              onClick={() => setShowDeposit(true)}
              className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 hover:border-zinc-900"
            >
              <span className="font-mono text-sm font-bold text-zinc-900">
                {balance === null ? '—' : `$${balance.toFixed(2)}`}
              </span>
              <span className="text-xs text-zinc-600">USDC</span>
              <span className="text-xs text-zinc-900">▾</span>
            </button>
          )}
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="mb-1 text-2xl font-bold text-zinc-900">{t('services.home.title', '¿Qué necesitas hoy?')}</h1>
        <p className="mb-6 text-sm text-zinc-500">
          {t('services.home.subtitle', 'Publica una tarea y un humano cercano la ejecuta. Pago seguro en USDC.')}
        </p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {SERVICES.map((s) => (
            <button
              key={s.key}
              onClick={() => navigate(`/services/${s.key}`)}
              className="flex flex-col items-center gap-2 rounded-xl border border-zinc-200 bg-white p-5 transition hover:border-zinc-900 hover:shadow-md"
            >
              <span className="text-3xl">{s.icon}</span>
              <span className="text-sm font-medium text-zinc-900">{t(`services.catalog.${s.key}.label`, s.label)}</span>
              <span className="text-center text-xs text-zinc-500">{t(`services.catalog.${s.key}.desc`, s.desc)}</span>
            </button>
          ))}
        </div>

        <div className="mt-8 rounded-xl border border-zinc-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-bold text-zinc-900">{t('services.home.executorPrompt', '¿Eres ejecutor?')}</h2>
          <p className="mb-3 text-xs text-zinc-500">
            {t('services.home.executorDesc', 'Encuentra tareas cerca de ti y gana USDC.')}
          </p>
          <button
            onClick={() => navigate('/tasks')}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
          >
            {t('services.home.seeTasks', 'Ver tareas disponibles')}
          </button>
        </div>
      </div>

      {walletAddress && (
        <DepositModal
          open={showDeposit}
          walletAddress={walletAddress}
          depositAmountUsdc={20}
          targetBalanceUsdc={(balance ?? 0) + 20}
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

export default ServicesHome
