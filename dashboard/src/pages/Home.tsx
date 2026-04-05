import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { ProfileCompletionModal } from '../components/ProfileCompletionModal'
import { HeroSection } from '../components/landing/HeroSection'
import { ProtocolStack } from '../components/landing/ProtocolStack'
import { StatsBar } from '../components/landing/StatsBar'
import { PublicTaskBrowser } from '../components/landing/PublicTaskBrowser'
import { HowItWorks } from '../components/landing/HowItWorks'
import { A2ASection } from '../components/landing/A2ASection'
import { AgentIntegration } from '../components/landing/AgentIntegration'
import { ERC8128Section } from '../components/landing/ERC8128Section'
import { OWSSection } from '../components/landing/OWSSection'
import { H2ASection } from '../components/landing/H2ASection'
import { ActivityFeed } from '../components/feed'

export function Home() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const {
    userType,
    setUserType,
    isAuthenticated,
    isProfileComplete,
    loading,
    openAuthModal,
    refreshExecutor,
    executor,
  } = useAuth()
  const [showProfileCompletion, setShowProfileCompletion] = useState(false)
  const [wasAuthenticated, setWasAuthenticated] = useState(false)
  const taskSectionRef = useRef<HTMLElement>(null)
  const agentSectionRef = useRef<HTMLElement>(null)

  // Handle auth state changes - wait for loading to complete before making navigation decisions
  useEffect(() => {
    // Don't make decisions while still loading executor data
    if (loading) {
      return
    }

    // Detect when user just authenticated (transition from not-auth to auth)
    if (isAuthenticated && !wasAuthenticated) {
      console.log('[Home] User authenticated, isProfileComplete:', isProfileComplete, 'loading:', loading)
      setUserType('worker')

      if (isProfileComplete) {
        // Returning user with complete profile — go straight to tasks
        navigate('/tasks')
      } else {
        // New user or incomplete profile — show completion modal
        setShowProfileCompletion(true)
      }
    }
    setWasAuthenticated(isAuthenticated)
  }, [isAuthenticated, wasAuthenticated, isProfileComplete, loading, setUserType, navigate])

  const handleConnectWallet = useCallback(() => {
    openAuthModal()
  }, [openAuthModal])

  const handleGoToDashboard = useCallback(() => {
    navigate(userType === 'agent' ? '/agent/dashboard' : '/tasks')
  }, [navigate, userType])

  const handleScrollToTasks = useCallback(() => {
    taskSectionRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const handleProfileComplete = useCallback(async () => {
    setShowProfileCompletion(false)
    await refreshExecutor()
    navigate('/tasks')
  }, [navigate, refreshExecutor])

  const handleProfileSkip = useCallback(() => {
    setShowProfileCompletion(false)
    navigate('/tasks')
  }, [navigate])

  const shouldShowProfileCompletion =
    showProfileCompletion && isAuthenticated && !isProfileComplete

  // Show transition screen when authenticated but still loading executor data
  // Prevents showing the full landing page (with "Start Earning" hero) after login
  if (isAuthenticated && loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-12 h-12 mx-auto mb-4">
            <div className="absolute inset-0 border-4 border-gray-200 rounded-full" />
            <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin" />
          </div>
          <p className="text-gray-500 text-sm">{t('common.loading', 'Loading...')}</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="max-w-6xl mx-auto px-4 w-full">
        <HeroSection
          onConnectWallet={handleConnectWallet}
          onGoToDashboard={handleGoToDashboard}
          onScrollToTasks={handleScrollToTasks}
        />

        <ProtocolStack />

        <StatsBar />

        {/* Live Activity Feed — full rich cards, public mode (no auth required) */}
        <section className="my-12">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
            {t('feed.liveActivity', 'Live Activity')}
          </h2>
          <ActivityFeed limit={8} mode="public" />
        </section>

        <PublicTaskBrowser
          ref={taskSectionRef}
          onAuthRequired={handleConnectWallet}
        />

        <HowItWorks
          onConnectWallet={handleConnectWallet}
        />

        <ERC8128Section />

        <OWSSection />

        <A2ASection />

        <H2ASection />

        <AgentIntegration ref={agentSectionRef} />
      </div>

      {shouldShowProfileCompletion && (
        <ProfileCompletionModal
          onComplete={handleProfileComplete}
          onSkip={handleProfileSkip}
          executor={executor}
        />
      )}
    </>
  )
}
