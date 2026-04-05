import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { LanguageSwitcher } from '../LanguageSwitcher'

export function AppHeader() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, userType, executor, loading, openAuthModal } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const headerRef = useRef<HTMLElement>(null)

  // Close menu on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node
      // Ignore clicks inside the entire header (covers desktop dropdown,
      // mobile menu, and hamburger buttons on both breakpoints)
      if (headerRef.current?.contains(target)) {
        return
      }
      setMenuOpen(false)
    }
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [menuOpen])

  // Close menu on route change
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  // Primary nav — always visible on desktop
  const primaryLinks = [
    { label: t('nav.activity', 'Activity'), href: '/activity' },
    ...(isAuthenticated ? [
      { label: t('nav.publisherDashboard', 'Publish Task'), href: '/publisher/dashboard' },
      { label: t('nav.messages', 'Messages'), href: '/messages' },
      { label: t('nav.myTasks', 'My Tasks'), href: userType === 'agent' ? '/agent/dashboard' : '/tasks' },
    ] : []),
  ]

  // Hamburger menu items
  const menuLinks = [
    ...(isAuthenticated ? [
      { label: t('nav.ratings', 'Ratings'), href: '/ratings' },
      { label: t('nav.audit', 'Audit'), href: '/audit' },
    ] : []),
    { label: t('nav.leaderboard', 'Leaderboard'), href: '/leaderboard' },
    { label: t('nav.agentDirectory', 'Agent Directory'), href: '/agents/directory' },
    { type: 'divider' as const },
    { label: t('nav.agents', 'For Agents'), href: '/agents' },
    { label: t('nav.developers', 'Developers'), href: '/developers' },
    { label: t('nav.faq', 'FAQ'), href: '/faq' },
    { label: t('footer.about', 'About'), href: '/about' },
    ...(isAuthenticated ? [
      { type: 'divider' as const },
      { label: t('nav.settings', 'Settings'), href: '/settings' },
    ] : []),
  ]

  const isActive = (href: string) => location.pathname === href

  return (
    <header ref={headerRef} className="bg-gray-900 sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Left: Hamburger (mobile) + Logo */}
          <div className="flex items-center gap-2">
            {/* Mobile hamburger — left side */}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="md:hidden p-1.5 text-gray-400 hover:text-white transition-colors"
              aria-label="Menu"
            >
              {menuOpen ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>

            {/* Logo */}
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 group"
            >
              <img src="/logo.png" alt="EM" className="w-8 h-8 rounded-lg object-contain" />
              <span className="font-black text-lg text-white tracking-tight hidden sm:inline">
                Execution Market
              </span>
            </button>
          </div>

          {/* Center: Primary nav (desktop only) */}
          <nav className="hidden md:flex items-center gap-1">
            {primaryLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => navigate(link.href)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
                  isActive(link.href)
                    ? 'text-white bg-white/15'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                {link.label}
              </button>
            ))}
          </nav>

          {/* Right: Hamburger (desktop) + Profile/Auth */}
          <div className="flex items-center gap-2">
            {/* Desktop hamburger */}
            <div className="relative hidden md:block">
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className={`p-1.5 rounded-md transition-colors ${
                  menuOpen ? 'text-white bg-white/15' : 'text-gray-400 hover:text-white hover:bg-white/10'
                }`}
                aria-label="More"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>

              {/* Desktop dropdown */}
              {menuOpen && (
                <div className="absolute right-0 top-full mt-1 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 animate-fade-in">
                  {menuLinks.map((item, i) =>
                    'type' in item && item.type === 'divider' ? (
                      <div key={`div-${i}`} className="my-1 border-t border-gray-700" />
                    ) : (
                      <button
                        key={'href' in item ? item.href : i}
                        onClick={() => {
                          if ('href' in item) navigate(item.href!)
                          setMenuOpen(false)
                        }}
                        className={`block w-full text-left px-4 py-2 text-sm transition-colors ${
                          'href' in item && isActive(item.href!)
                            ? 'text-white bg-white/10'
                            : 'text-gray-300 hover:text-white hover:bg-white/5'
                        }`}
                      >
                        {'label' in item ? item.label : ''}
                      </button>
                    )
                  )}
                  <div className="my-1 border-t border-gray-700" />
                  <div className="px-4 py-2">
                    <LanguageSwitcher compact />
                  </div>
                </div>
              )}
            </div>

            {/* Profile / Auth */}
            {isAuthenticated ? (
              <button
                onClick={() => navigate('/profile')}
                className="flex items-center gap-2 px-2 py-1.5 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center text-xs text-white font-bold">
                  {(executor?.display_name || 'U')[0].toUpperCase()}
                </div>
                <span className="hidden sm:inline">{executor?.display_name || t('nav.profile', 'Profile')}</span>
              </button>
            ) : loading && localStorage.getItem('em_last_wallet_address') ? (
              <span className="px-4 py-1.5 text-sm text-gray-400 animate-pulse">
                {t('auth.restoringSession', 'Restoring session...')}
              </span>
            ) : (
              <button
                onClick={openAuthModal}
                disabled={loading}
                className="px-4 py-1.5 bg-emerald-500 text-white text-sm font-semibold rounded-md hover:bg-emerald-400 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? t('common.loading', 'Loading...') : t('landing.startEarning', 'Start Earning')}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Mobile menu — full dropdown */}
      {menuOpen && (
        <div className="md:hidden border-t border-gray-800 bg-gray-900 animate-slide-down">
          <div className="px-4 py-3 space-y-1">
            {/* Primary links */}
            {primaryLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => {
                  navigate(link.href)
                  setMenuOpen(false)
                }}
                className={`block w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                  isActive(link.href)
                    ? 'text-white bg-white/15 font-medium'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                {link.label}
              </button>
            ))}

            <div className="my-2 border-t border-gray-800" />

            {/* Secondary links */}
            {menuLinks.map((item, i) =>
              'type' in item && item.type === 'divider' ? (
                <div key={`div-${i}`} className="my-2 border-t border-gray-800" />
              ) : (
                <button
                  key={'href' in item ? item.href : i}
                  onClick={() => {
                    if ('href' in item) navigate(item.href!)
                    setMenuOpen(false)
                  }}
                  className={`block w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                    'href' in item && isActive(item.href!)
                      ? 'text-white bg-white/15'
                      : 'text-gray-400 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {'label' in item ? item.label : ''}
                </button>
              )
            )}

            {/* Profile & Settings in mobile */}
            {isAuthenticated && (
              <>
                <div className="my-2 border-t border-gray-800" />
                <button
                  onClick={() => {
                    navigate('/profile')
                    setMenuOpen(false)
                  }}
                  className="block w-full text-left px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                >
                  {t('nav.profile', 'Profile')}
                </button>
              </>
            )}

            <div className="my-2 border-t border-gray-800" />
            <div className="px-3 py-1">
              <LanguageSwitcher />
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
