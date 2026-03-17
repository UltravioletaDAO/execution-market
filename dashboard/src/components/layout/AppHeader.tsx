import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { LanguageSwitcher } from '../LanguageSwitcher'

export function AppHeader() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, userType, executor, loading, openAuthModal } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const mainNavLinks = [
    { label: t('nav.activity', 'Activity'), href: '/activity' },
    { label: t('nav.leaderboard', 'Leaderboard'), href: '/leaderboard' },
    { label: t('nav.faq', 'FAQ'), href: '/faq' },
  ]

  const secondaryNavLinks = [
    { label: t('footer.about', 'About'), href: '/about' },
    { label: t('nav.agents', 'For Agents'), href: '/agents' },
    { label: t('nav.developers', 'Developers'), href: '/developers' },
    { label: t('nav.agentDirectory', 'Agent Directory'), href: '/agents/directory' },
    ...(isAuthenticated ? [
      { label: t('nav.publisherDashboard', 'Publish Task'), href: '/publisher/dashboard' },
      { label: t('nav.ratings', 'Ratings'), href: '/ratings' },
      { label: t('nav.messages', 'Messages'), href: '/messages' },
    ] : []),
  ]

  const allNavLinks = [...mainNavLinks, ...secondaryNavLinks]

  const isActive = (href: string) => location.pathname === href

  return (
    <header className="bg-gray-900 sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 group"
          >
            <img src="/logo.png" alt="EM" className="w-8 h-8 rounded-lg object-contain" />
            <span className="font-black text-lg text-white tracking-tight">
              Execution Market
            </span>
          </button>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {mainNavLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => navigate(link.href)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  isActive(link.href)
                    ? 'text-white bg-white/15'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                {link.label}
              </button>
            ))}
            {/* Secondary links - smaller */}
            {secondaryNavLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => navigate(link.href)}
                className={`px-2.5 py-1.5 text-xs rounded-md transition-colors ${
                  isActive(link.href)
                    ? 'text-white bg-white/15'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/10'
                }`}
              >
                {link.label}
              </button>
            ))}
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
                  onClick={() => navigate('/settings')}
                  className="hidden sm:flex items-center px-2 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                  title={t('nav.settings', 'Settings')}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
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
                onClick={openAuthModal}
                disabled={loading}
                className="px-4 py-1.5 bg-emerald-500 text-white text-sm font-semibold rounded-md hover:bg-emerald-400 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? t('common.loading', 'Loading...') : t('landing.startEarning', 'Start Earning')}
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
            {allNavLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => {
                  navigate(link.href)
                  setMobileMenuOpen(false)
                }}
                className={`block w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                  isActive(link.href)
                    ? 'text-white bg-white/15'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                {link.label}
              </button>
            ))}
            {isAuthenticated && (
              <>
                <button
                  onClick={() => {
                    navigate('/profile')
                    setMobileMenuOpen(false)
                  }}
                  className="block w-full text-left px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                >
                  {t('nav.profile', 'Profile')}
                </button>
                <button
                  onClick={() => {
                    navigate('/settings')
                    setMobileMenuOpen(false)
                  }}
                  className="block w-full text-left px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                >
                  {t('nav.settings', 'Settings')}
                </button>
                <button
                  onClick={() => {
                    navigate(userType === 'agent' ? '/agent/dashboard' : '/tasks')
                    setMobileMenuOpen(false)
                  }}
                  className="block w-full text-left px-3 py-2 text-sm text-emerald-400 hover:text-emerald-300 hover:bg-white/10 rounded-md transition-colors"
                >
                  {t('nav.myTasks', 'My Tasks')}
                </button>
              </>
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
