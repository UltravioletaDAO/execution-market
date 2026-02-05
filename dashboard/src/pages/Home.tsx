import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ProfileCompletionModal } from '../components/ProfileCompletionModal'
import { AppHeader } from '../components/layout/AppHeader'
import { AppFooter } from '../components/layout/AppFooter'
import { HeroSection } from '../components/landing/HeroSection'
import { StatsBar } from '../components/landing/StatsBar'
import { PublicTaskBrowser } from '../components/landing/PublicTaskBrowser'
import { HowItWorks } from '../components/landing/HowItWorks'
import { AgentIntegration } from '../components/landing/AgentIntegration'

export function Home() {
  const navigate = useNavigate()
  const {
    userType,
    setUserType,
    isAuthenticated,
    isProfileComplete,
    loading,
    openAuthModal,
    refreshExecutor,
  } = useAuth()
  const [showProfileCompletion, setShowProfileCompletion] = useState(false)
  const [wasAuthenticated, setWasAuthenticated] = useState(false)
  const taskSectionRef = useRef<HTMLElement>(null)
  const howItWorksRef = useRef<HTMLElement>(null)
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

  const handleScrollToHowItWorks = useCallback(() => {
    howItWorksRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const handleProfileComplete = useCallback(() => {
    setShowProfileCompletion(false)
    refreshExecutor()
    navigate('/tasks')
  }, [navigate, refreshExecutor])

  const handleProfileSkip = useCallback(() => {
    setShowProfileCompletion(false)
    navigate('/tasks')
  }, [navigate])

  const shouldShowProfileCompletion =
    showProfileCompletion && isAuthenticated && !isProfileComplete

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <AppHeader
        onConnectWallet={handleConnectWallet}
        onScrollToHowItWorks={handleScrollToHowItWorks}
      />

      <main className="flex-1 max-w-6xl mx-auto px-4 w-full">
        <HeroSection
          onConnectWallet={handleConnectWallet}
          onGoToDashboard={handleGoToDashboard}
          onScrollToTasks={handleScrollToTasks}
        />

        <StatsBar />

        <PublicTaskBrowser
          ref={taskSectionRef}
          onAuthRequired={handleConnectWallet}
        />

        <HowItWorks
          ref={howItWorksRef}
          onConnectWallet={handleConnectWallet}
        />

        <AgentIntegration ref={agentSectionRef} />
      </main>

      <AppFooter />

      {shouldShowProfileCompletion && (
        <ProfileCompletionModal
          onComplete={handleProfileComplete}
          onSkip={handleProfileSkip}
        />
      )}
    </div>
  )
}
