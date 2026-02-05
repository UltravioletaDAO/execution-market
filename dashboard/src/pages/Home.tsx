import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ProfileCompletionModal } from '../components/ProfileCompletionModal'
import { AppHeader } from '../components/layout/AppHeader'
import { AppFooter } from '../components/layout/AppFooter'
import { HeroSection } from '../components/landing/HeroSection'
import { PublicTaskBrowser } from '../components/landing/PublicTaskBrowser'
import { HowItWorks } from '../components/landing/HowItWorks'

export function Home() {
  const navigate = useNavigate()
  const {
    userType,
    setUserType,
    isAuthenticated,
    isProfileComplete,
    openAuthModal,
    refreshExecutor,
  } = useAuth()
  const [showProfileCompletion, setShowProfileCompletion] = useState(false)
  const [wasAuthenticated, setWasAuthenticated] = useState(false)
  const taskSectionRef = useRef<HTMLElement>(null)
  const howItWorksRef = useRef<HTMLElement>(null)

  // Handle auth state changes
  useEffect(() => {
    // Detect when user just authenticated (transition from not-auth to auth)
    if (isAuthenticated && !wasAuthenticated) {
      console.log('[Home] User just authenticated, isProfileComplete:', isProfileComplete)
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
  }, [isAuthenticated, wasAuthenticated, isProfileComplete, setUserType, navigate])

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

        <PublicTaskBrowser
          ref={taskSectionRef}
          onAuthRequired={handleConnectWallet}
        />

        <HowItWorks
          ref={howItWorksRef}
          onConnectWallet={handleConnectWallet}
        />
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
