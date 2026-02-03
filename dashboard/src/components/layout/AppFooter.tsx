import { useTranslation } from 'react-i18next'

export function AppFooter() {
  const { t } = useTranslation()

  return (
    <footer className="max-w-6xl mx-auto px-4 py-8 text-center text-sm text-gray-400 border-t border-gray-100">
      <p>Chamba - Human Execution Layer for AI Agents</p>
      <p className="mt-1">{t('footer.poweredBy')} Ultravioleta DAO</p>
    </footer>
  )
}
