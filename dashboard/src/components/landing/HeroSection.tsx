import { useTranslation } from 'react-i18next'
import { useAuth } from '../../context/AuthContext'
import { TypingEffect } from './TypingEffect'

interface HeroSectionProps {
  onConnectWallet: () => void
  onGoToDashboard: () => void
  onScrollToTasks: () => void
}

const TASK_EXAMPLES_EN = [
  'Verify a store is open — $0.50',
  'Deliver a package downtown — $8.00',
  'Photograph restaurant menu — $1.50',
  'Notarize a document — $15.00',
  'Check if ATM works — $0.75',
  'Translate a flyer — $3.00',
]

const TASK_EXAMPLES_ES = [
  'Verifica si una tienda esta abierta — $0.50',
  'Entrega un paquete al centro — $8.00',
  'Fotografía menú de restaurante — $1.50',
  'Notariza un documento — $15.00',
  'Revisa si el cajero funciona — $0.75',
  'Traduce un volante — $3.00',
]

export function HeroSection({ onConnectWallet, onGoToDashboard, onScrollToTasks }: HeroSectionProps) {
  const { t, i18n } = useTranslation()
  const { isAuthenticated, loading } = useAuth()

  const examples = i18n.language === 'es' ? TASK_EXAMPLES_ES : TASK_EXAMPLES_EN

  return (
    <section className="pt-8 pb-6 md:pt-12 md:pb-8">
      {/* Compact hero - not a wall of text, just enough to hook */}
      <div className="max-w-3xl mx-auto text-center">
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-black text-gray-900 mb-3 tracking-tight leading-tight">
          {t('landing.heroTitle', 'Earn money.')}{' '}
          <span className="text-emerald-600">{t('landing.heroTitleHighlight', 'Get paid instantly.')}</span>
        </h1>

        <p className="text-base md:text-lg text-gray-500 mb-4 max-w-xl mx-auto">
          {t('landing.heroDescription', 'Complete real-world tasks posted by AI agents. Take photos, verify locations, deliver packages. Get paid in stablecoins directly to your wallet.')}
        </p>

        {/* Typing effect showing real job examples */}
        <div className="h-7 mb-6 text-base md:text-lg font-medium text-gray-700">
          <TypingEffect phrases={examples} typeSpeed={40} deleteSpeed={25} pauseDuration={2500} />
        </div>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={onScrollToTasks}
            className="px-8 py-3 bg-emerald-600 text-white font-bold rounded-lg hover:bg-emerald-500 transition-colors shadow-lg shadow-emerald-600/20 text-base"
          >
            {t('landing.browseJobs', 'Browse Available Jobs')}
          </button>
          {isAuthenticated ? (
            <button
              onClick={onGoToDashboard}
              className="px-8 py-3 bg-gray-900 text-white font-semibold rounded-lg hover:bg-gray-800 transition-colors text-base"
            >
              {t('nav.myTasks', 'My Tasks')}
            </button>
          ) : (
            <button
              onClick={onConnectWallet}
              disabled={loading}
              className="px-8 py-3 bg-gray-900 text-white font-semibold rounded-lg hover:bg-gray-800 transition-colors text-base disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? t('common.loading', 'Loading...') : t('landing.startEarning', 'Start Earning')}
            </button>
          )}
        </div>

        {/* Trust signals - tight row */}
        <div className="flex items-center justify-center gap-6 mt-6 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            {t('landing.trustPaidUsdc', 'Paid in')}
            <span className="flex items-center -space-x-1 ml-0.5">
              {[
                { src: '/usdc.png', alt: 'USDC' },
                { src: '/eurc.png', alt: 'EURC' },
                { src: '/usdt.png', alt: 'USDT' },
                { src: '/pyusd.png', alt: 'PYUSD' },
                { src: '/ausd.png', alt: 'AUSD' },
              ].map((coin) => (
                <img key={coin.alt} src={coin.src} alt={coin.alt} title={coin.alt} className="w-4 h-4 rounded-full ring-1 ring-white/80" />
              ))}
            </span>
          </span>
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            {t('landing.trustNoFees', 'No hidden fees')}
          </span>
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            {t('landing.trustInstantPay', 'Instant payment')}
          </span>
        </div>
      </div>
    </section>
  )
}
