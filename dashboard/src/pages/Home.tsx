import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AuthModal } from '../components/AuthModal'
import { ProfileCompletionModal } from '../components/ProfileCompletionModal'
import { AppHeader } from '../components/layout/AppHeader'
import { AppFooter } from '../components/layout/AppFooter'
import { HeroSection } from '../components/landing/HeroSection'
import { PublicTaskBrowser } from '../components/landing/PublicTaskBrowser'

export function Home() {
  const navigate = useNavigate()
  const { userType, setUserType, isAuthenticated, isProfileComplete } = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [showProfileCompletion, setShowProfileCompletion] = useState(false)
  const taskSectionRef = useRef<HTMLElement>(null)

  const handleConnectWallet = useCallback(() => {
    setShowAuthModal(true)
  }, [])

  const handleGoToDashboard = useCallback(() => {
    navigate(userType === 'agent' ? '/agent/dashboard' : '/tasks')
  }, [navigate, userType])

  const handleScrollToTasks = useCallback(() => {
    taskSectionRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const handleAuthSuccess = useCallback(() => {
    setShowAuthModal(false)
    setUserType('worker')
    // Check if profile needs completion
    // isProfileComplete may not be updated yet since executor was just fetched,
    // so we show the modal and let it close if already complete
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

  // If user is already authenticated and profile incomplete, show modal
  // (handles returning to / with incomplete profile)
  const shouldShowProfileCompletion =
    showProfileCompletion && isAuthenticated && !isProfileComplete

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-white">
      <AppHeader onConnectWallet={handleConnectWallet} />

      <main className="max-w-6xl mx-auto px-4">
        <HeroSection
          onConnectWallet={handleConnectWallet}
          onGoToDashboard={handleGoToDashboard}
          onScrollToTasks={handleScrollToTasks}
        />

        <PublicTaskBrowser
          ref={taskSectionRef}
          onAuthRequired={handleConnectWallet}
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
