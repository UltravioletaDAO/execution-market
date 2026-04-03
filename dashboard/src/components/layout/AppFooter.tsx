import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

export function AppFooter() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const links = [
    { label: t('footer.about', 'About'), href: '/about' },
    { label: t('help.faq.title', 'FAQ'), href: '/faq' },
    { label: t('nav.agents', 'For Agents'), href: '/agents' },
    { label: t('nav.developers', 'Developers'), href: '/developers' },
    { label: t('nav.apiDocs', 'API Docs'), href: 'https://api.execution.market/docs', external: true },
  ]

  return (
    <footer className="bg-gray-900 text-gray-400">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Logo + tagline */}
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="EM" className="w-7 h-7 rounded-md object-contain" />
            <span className="text-sm">
              <span className="text-white font-semibold">Execution Market</span>
              {' '}&mdash; {t('landing.footerTagline', 'Real tasks. Real pay. No banks.')}
            </span>
          </div>

          {/* Links */}
          <nav className="flex items-center gap-4">
            {links.map((link) => (
              link.external ? (
                <a
                  key={link.label}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {link.label}
                </a>
              ) : (
                <button
                  key={link.label}
                  onClick={() => navigate(link.href)}
                  className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {link.label}
                </button>
              )
            ))}
          </nav>
        </div>

        {/* Partners */}
        <div className="mt-6 pt-4 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-xs text-gray-600">{t('footer.poweredBy', 'Powered by')} Ultravioleta DAO</span>
          <div className="flex items-center gap-4">
            <a href="https://openwallet.sh" target="_blank" rel="noopener noreferrer" className="opacity-50 hover:opacity-80 transition-opacity" title="Open Wallet Standard">
              <img src="/ows-logo.svg" alt="OWS" className="h-5 w-auto invert" />
            </a>
            <a href="https://worldcoin.org" target="_blank" rel="noopener noreferrer" className="opacity-50 hover:opacity-80 transition-opacity" title="World ID">
              <img src="/worldcoin.png" alt="World ID" className="h-5 w-auto invert" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
