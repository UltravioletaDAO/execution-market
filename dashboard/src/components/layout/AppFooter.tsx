import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

export function AppFooter() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const links = [
    { label: t('footer.about', 'About'), href: '/about' },
    { label: t('help.faq.title', 'FAQ'), href: '/faq' },
    { label: t('footer.terms', 'Terms'), href: '#' },
    { label: t('footer.privacy', 'Privacy'), href: '#' },
  ]

  return (
    <footer className="bg-gray-900 text-gray-400">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Logo + tagline */}
          <div className="flex items-center gap-3">
            <span className="w-7 h-7 rounded-md bg-emerald-500 flex items-center justify-center text-white font-black text-xs">
              CH
            </span>
            <span className="text-sm">
              <span className="text-white font-semibold">Chamba</span>
              {' '}&mdash; {t('landing.footerTagline', 'Real tasks. Real pay. No banks.')}
            </span>
          </div>

          {/* Links */}
          <nav className="flex items-center gap-4">
            {links.map((link) => (
              <button
                key={link.label}
                onClick={() => link.href.startsWith('/') ? navigate(link.href) : undefined}
                className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
              >
                {link.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Bottom */}
        <div className="mt-6 pt-4 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-600">
          <span>{t('footer.poweredBy', 'Powered by')} x402 &middot; Ultravioleta DAO</span>
          <span>Base Mainnet &middot; USDC</span>
        </div>
      </div>
    </footer>
  )
}
