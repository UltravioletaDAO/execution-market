import { useTranslation } from 'react-i18next'
import { useAuth } from '../../context/AuthContext'
import { TypingEffect } from './TypingEffect'
import { StatsBar } from './StatsBar'

interface HeroSectionProps {
  onConnectWallet: () => void
  onGoToDashboard: () => void
  onScrollToTasks: () => void
}

const TASK_EXAMPLES = [
  'Verify store is open. $0.50',
  'Deliver package downtown. $8',
  'Photograph menu prices. $1.50',
  'Notarize document. $15',
  'Check if ATM is working. $0.75',
]

export function HeroSection({ onConnectWallet, onGoToDashboard, onScrollToTasks }: HeroSectionProps) {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()

  return (
    <section className="py-16 md:py-24 text-center">
      <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-4 tracking-tight">
        Human Execution Layer
        <br />
        <span className="text-blue-600">for AI Agents</span>
      </h1>

      <p className="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto mb-6">
        {t('landing.heroTagline')}
      </p>

      <div className="h-8 mb-8 text-lg md:text-xl text-gray-700 font-medium">
        <TypingEffect phrases={TASK_EXAMPLES} />
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-center mb-8">
        {isAuthenticated ? (
          <button
            onClick={onGoToDashboard}
            className="px-8 py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-lg"
          >
            {t('nav.dashboard')}
          </button>
        ) : (
          <button
            onClick={onConnectWallet}
            className="px-8 py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-lg"
          >
            {t('auth.connectWallet')}
          </button>
        )}
        <button
          onClick={onScrollToTasks}
          className="px-8 py-3.5 bg-white text-gray-700 font-semibold rounded-xl border border-gray-200 hover:bg-gray-50 transition-colors"
        >
          {t('landing.browseTasks')}
        </button>
      </div>

      <StatsBar />
    </section>
  )
}
