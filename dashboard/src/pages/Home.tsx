import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AuthModal } from '../components/AuthModal'
import { ProfileCompletionModal } from '../components/ProfileCompletionModal'
import { AppHeader } from '../components/layout/AppHeader'
import { AppFooter } from '../components/layout/AppFooter'
import { HeroSection } from '../components/landing/HeroSection'
import { PublicTaskBrowser } from '../components/landing/PublicTaskBrowser'
import { HowItWorks } from '../components/landing/HowItWorks'

export function Home() {
  const navigate = useNavigate()
  const { userType, setUserType, isAuthenticated, isProfileComplete } = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [showProfileCompletion, setShowProfileCompletion] = useState(false)
  const taskSectionRef = useRef<HTMLElement>(null)
  const howItWorksRef = useRef<HTMLElement>(null)

  const handleConnectWallet = useCallback(() => {
    setShowAuthModal(true)
  }, [])

  const handleGoToDashboard = useCallback(() => {
    navigate(userType === 'agent' ? '/agent/dashboard' : '/tasks')
  }, [navigate, userType])

  const handleScrollToTasks = useCallback(() => {
    taskSectionRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const handleScrollToHowItWorks = useCallback(() => {
    howItWorksRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const handleAuthSuccess = useCallback(() => {
    setShowAuthModal(false)
    setUserType('worker')
    setShowProfileCompletion(true)
  }, [setUserType])

  const handleProfileComplete = useCallback(() => {
    setShowProfileCompletion(false)
    navigate('/tasks')
  }, [navigate])

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

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
      />

      {shouldShowProfileCompletion && (
        <ProfileCompletionModal
          onComplete={handleProfileComplete}
          onSkip={handleProfileSkip}
        />
      )}
    </div>
  )
}
