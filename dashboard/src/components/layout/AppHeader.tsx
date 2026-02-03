import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { LanguageSwitcher } from '../LanguageSwitcher'

interface AppHeaderProps {
  onConnectWallet: () => void
  onScrollToHowItWorks?: () => void
}

export function AppHeader({ onConnectWallet, onScrollToHowItWorks }: AppHeaderProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { isAuthenticated, userType, executor } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const navLinks = [
    { label: t('nav.home', 'Jobs'), href: '/' },
    { label: t('footer.about', 'About'), href: '/about' },
    { label: t('help.faq.title', 'FAQ'), href: '/faq' },
  ]

  return (
    <header className="bg-gray-900 sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 group"
          >
            <span className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center text-white font-black text-sm tracking-tighter">
              CH
            </span>
            <span className="font-black text-lg text-white tracking-tight">
              Chamba
            </span>
          </button>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => navigate(link.href)}
                className="px-3 py-1.5 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              >
                {link.label}
              </button>
            ))}
            {onScrollToHowItWorks && (
              <button
                onClick={onScrollToHowItWorks}
                className="px-3 py-1.5 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              >
                {t('landing.howItWorks', 'How it Works')}
              </button>
            )}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:block">
              <LanguageSwitcher compact />
            </div>

            {isAuthenticated ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate('/profile')}
                  className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                >
                  <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center text-[10px] text-white font-bold">
                    {(executor?.display_name || 'U')[0].toUpperCase()}
                  </div>
                  {executor?.display_name || t('nav.profile', 'Profile')}
                </button>
                <button
                  onClick={() => navigate(userType === 'agent' ? '/agent/dashboard' : '/tasks')}
                  className="px-4 py-1.5 bg-emerald-500 text-white text-sm font-semibold rounded-md hover:bg-emerald-400 transition-colors"
                >
                  {t('nav.myTasks', 'My Tasks')}
                </button>
              </div>
            ) : (
              <button
                onClick={onConnectWallet}
                className="px-4 py-1.5 bg-emerald-500 text-white text-sm font-semibold rounded-md hover:bg-emerald-400 transition-colors"
              >
                {t('landing.startEarning', 'Start Earning')}
              </button>
            )}

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1.5 text-gray-400 hover:text-white transition-colors"
              aria-label="Menu"
            >
              {mobileMenuOpen ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-800 bg-gray-900 animate-slide-down">
          <div className="px-4 py-3 space-y-1">
            {navLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => {
                  navigate(link.href)
                  setMobileMenuOpen(false)
                }}
                className="block w-full text-left px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              >
                {link.label}
              </button>
            ))}
            {onScrollToHowItWorks && (
              <button
                onClick={() => {
                  onScrollToHowItWorks()
                  setMobileMenuOpen(false)
                }}
                className="block w-full text-left px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              >
                {t('landing.howItWorks', 'How it Works')}
              </button>
            )}
            <div className="pt-2 px-3">
              <LanguageSwitcher />
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
