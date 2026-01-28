// Chamba Dashboard - Main App Component with Routing
import { useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

// Auth
import { AuthProvider, useAuth } from './context/AuthContext'
import { AuthGuard, WorkerGuard, AgentGuard } from './components/guards'

// Components
import { TaskList, CategoryFilter } from './components/TaskList'
import { TaskDetail } from './components/TaskDetail'
import { SubmissionForm } from './components/SubmissionForm'
import { AuthModal } from './components/AuthModal'
import { LanguageSwitcher } from './components/LanguageSwitcher'
import { ProfilePage } from './components/profile'

// Pages
import { WorkerDashboard } from './pages/WorkerDashboard'
import { AgentDashboard } from './pages/AgentDashboard'

// Hooks
import { useAvailableTasks, useMyTasks } from './hooks/useTasks'

// Types
import type { Task, TaskCategory } from './types/database'

// --------------------------------------------------------------------------
// Landing Page (Public)
// --------------------------------------------------------------------------

function LandingPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { isAuthenticated, userType, setUserType } = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [pendingUserType, setPendingUserType] = useState<'worker' | 'agent' | null>(null)

  const handleGetStarted = (type: 'worker' | 'agent') => {
    if (isAuthenticated) {
      setUserType(type)
      navigate(type === 'worker' ? '/tasks' : '/agent/dashboard')
    } else {
      setPendingUserType(type)
      setShowAuthModal(true)
    }
  }

  const handleAuthSuccess = () => {
    setShowAuthModal(false)
    if (pendingUserType) {
      setUserType(pendingUserType)
      navigate(pendingUserType === 'worker' ? '/tasks' : '/agent/dashboard')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-white">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">&#128188;</span>
              <span className="font-bold text-lg text-gray-900">Chamba</span>
            </div>
            <div className="flex items-center gap-3">
              <LanguageSwitcher />
              {isAuthenticated ? (
                <button
                  onClick={() => navigate(userType === 'agent' ? '/agent/dashboard' : '/tasks')}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {t('nav.dashboard')}
                </button>
              ) : (
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {t('auth.login')}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-6xl mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Human Execution Layer for AI Agents
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-8">
            {t('landing.subtitle')}
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => handleGetStarted('worker')}
              className="px-8 py-4 bg-green-600 text-white font-semibold rounded-xl hover:bg-green-700 transition-colors shadow-lg"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {t('landing.iAmWorker')}
              </span>
              <span className="text-green-200 text-sm block mt-1">
                {t('landing.earnMoney')}
              </span>
            </button>

            <button
              onClick={() => handleGetStarted('agent')}
              className="px-8 py-4 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors shadow-lg"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {t('landing.iAmAgent')}
              </span>
              <span className="text-purple-200 text-sm block mt-1">
                {t('landing.delegateTasks')}
              </span>
            </button>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">{t('landing.feature1Title')}</h3>
            <p className="text-gray-600 text-sm">{t('landing.feature1Desc')}</p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">{t('landing.feature2Title')}</h3>
            <p className="text-gray-600 text-sm">{t('landing.feature2Desc')}</p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">{t('landing.feature3Title')}</h3>
            <p className="text-gray-600 text-sm">{t('landing.feature3Desc')}</p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-4 py-8 text-center text-sm text-gray-400 border-t border-gray-100">
        <p>Chamba - Human Execution Layer for AI Agents</p>
        <p className="mt-1">{t('footer.poweredBy')} Ultravioleta DAO</p>
      </footer>

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => {
          setShowAuthModal(false)
          setPendingUserType(null)
        }}
        onSuccess={handleAuthSuccess}
      />
    </div>
  )
}

// --------------------------------------------------------------------------
// Tasks Page (Worker - Protected)
// --------------------------------------------------------------------------

type TasksView = 'list' | 'detail' | 'submit'

function TasksPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [view, setView] = useState<TasksView>('list')
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [category, setCategory] = useState<TaskCategory | null>(null)
  const [activeTab, setActiveTab] = useState<'available' | 'mine'>('available')

  const { executor, loading: authLoading, logout } = useAuth()

  const {
    tasks: availableTasks,
    loading: availableLoading,
    error: availableError,
  } = useAvailableTasks({ category: category ?? undefined })

  const {
    tasks: myTasks,
    loading: myTasksLoading,
    error: myTasksError,
  } = useMyTasks(executor?.id)

  const handleTaskClick = useCallback((task: Task) => {
    setSelectedTask(task)
    setView('detail')
  }, [])

  const handleBack = useCallback(() => {
    setView('list')
    setSelectedTask(null)
  }, [])

  const handleTaskAccepted = useCallback(() => {
    setActiveTab('mine')
    setView('list')
    setSelectedTask(null)
  }, [])

  const handleStartSubmission = useCallback(() => {
    setView('submit')
  }, [])

  const handleSubmissionComplete = useCallback(() => {
    setView('list')
    setSelectedTask(null)
  }, [])

  const renderContent = () => {
    if (view === 'detail' && selectedTask) {
      return (
        <div className="space-y-4">
          <TaskDetail
            task={selectedTask}
            currentExecutor={executor}
            onBack={handleBack}
            onAccept={handleTaskAccepted}
          />

          {selectedTask.status === 'accepted' &&
            selectedTask.executor_id === executor?.id && (
              <button
                onClick={handleStartSubmission}
                className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('tasks.submitEvidence')}
              </button>
            )}
        </div>
      )
    }

    if (view === 'submit' && selectedTask && executor) {
      return (
        <SubmissionForm
          task={selectedTask}
          executor={executor}
          onSubmit={handleSubmissionComplete}
          onCancel={handleBack}
        />
      )
    }

    // List view
    return (
      <>
        {/* Tab selector */}
        <div className="flex border-b border-gray-200 mb-4">
          <button
            onClick={() => setActiveTab('available')}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'available'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t('tasks.title')}
          </button>
          <button
            onClick={() => setActiveTab('mine')}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'mine'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t('nav.myTasks')}
            {myTasks.length > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-full">
                {myTasks.length}
              </span>
            )}
          </button>
        </div>

        {/* Category filter (only for available tasks) */}
        {activeTab === 'available' && (
          <div className="mb-4">
            <CategoryFilter selected={category} onChange={setCategory} />
          </div>
        )}

        {/* Task list */}
        {activeTab === 'available' ? (
          <TaskList
            tasks={availableTasks}
            loading={availableLoading}
            error={availableError}
            onTaskClick={handleTaskClick}
            emptyMessage={t('tasks.noTasks')}
          />
        ) : (
          <TaskList
            tasks={myTasks}
            loading={myTasksLoading}
            error={myTasksError}
            onTaskClick={handleTaskClick}
            emptyMessage={t('tasks.noTasks')}
          />
        )}
      </>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">&#128188;</span>
              <span className="font-bold text-lg text-gray-900">Chamba</span>
            </div>

            <div className="flex items-center gap-3">
              <LanguageSwitcher />

              {authLoading ? (
                <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse" />
              ) : executor ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate('/profile')}
                    className="flex items-center gap-2 hover:bg-gray-50 rounded-lg px-2 py-1 transition-colors"
                  >
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">
                        {executor.display_name || 'Usuario'}
                      </div>
                      <div className="text-xs text-gray-500 flex items-center gap-1">
                        <svg
                          className="w-3 h-3 text-amber-500"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                        {executor.reputation_score}
                      </div>
                    </div>
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-blue-600 font-medium">
                        {(executor.display_name || 'U')[0].toUpperCase()}
                      </span>
                    </div>
                  </button>
                  <button
                    onClick={() => logout()}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    title={t('auth.logout')}
                  >
                    <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-2xl mx-auto px-4 py-6">{renderContent()}</main>

      {/* Footer */}
      <footer className="max-w-2xl mx-auto px-4 py-6 text-center text-sm text-gray-400">
        <p>Chamba - Human Execution Layer for AI Agents</p>
        <p className="mt-1">{t('footer.poweredBy')} Ultravioleta DAO</p>
      </footer>
    </div>
  )
}

// --------------------------------------------------------------------------
// Profile Page (Worker - Protected)
// --------------------------------------------------------------------------

function ProfilePageWrapper() {
  const navigate = useNavigate()
  const { executor } = useAuth()

  if (!executor) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Cargando perfil...</p>
      </div>
    )
  }

  return (
    <ProfilePage
      executor={executor}
      onBack={() => navigate('/tasks')}
      onEditProfile={() => {
        // TODO: Implement profile edit
        console.log('Edit profile')
      }}
    />
  )
}

// --------------------------------------------------------------------------
// Earnings Page (Worker - Protected) - Placeholder
// --------------------------------------------------------------------------

function EarningsPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/tasks')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="font-bold text-lg text-gray-900">Mis Ganancias</h1>
          </div>
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Pagina de Ganancias</h2>
          <p className="text-gray-500">Esta pagina esta en desarrollo.</p>
        </div>
      </main>
    </div>
  )
}

// --------------------------------------------------------------------------
// Agent Dashboard Page (Agent - Protected)
// --------------------------------------------------------------------------

function AgentDashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">&#128188;</span>
              <span className="font-bold text-lg text-gray-900">Chamba</span>
              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                Agent
              </span>
            </div>
            <LanguageSwitcher />
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <AgentDashboard
          agentId={user?.id ?? ''}
          onBack={() => navigate('/')}
          onCreateTask={() => navigate('/agent/tasks/new')}
          onViewTask={(task) => console.log('View task:', task.id)}
          onReviewSubmission={(submission) => console.log('Review submission:', submission.id)}
        />
      </main>
    </div>
  )
}

// --------------------------------------------------------------------------
// Agent Tasks Page (Agent - Protected) - Placeholder
// --------------------------------------------------------------------------

function AgentTasksPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/agent/dashboard')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="font-bold text-lg text-gray-900">Gestionar Tareas</h1>
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Gestion de Tareas</h2>
          <p className="text-gray-500">Esta pagina esta en desarrollo.</p>
        </div>
      </main>
    </div>
  )
}

// --------------------------------------------------------------------------
// About Page (Public) - Placeholder
// --------------------------------------------------------------------------

function AboutPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="font-bold text-lg text-gray-900">Acerca de Chamba</h1>
          </div>
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Que es Chamba?</h2>
          <p className="text-gray-600 mb-4">
            Chamba es la capa de ejecucion humana para agentes de IA. Conectamos agentes
            autonomos con trabajadores humanos para completar tareas que requieren presencia
            fisica, autoridad humana o conocimiento local.
          </p>
          <p className="text-gray-600">
            Construido por Ultravioleta DAO.
          </p>
        </div>
      </main>
    </div>
  )
}

// --------------------------------------------------------------------------
// FAQ Page (Public) - Placeholder
// --------------------------------------------------------------------------

function FAQPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="font-bold text-lg text-gray-900">Preguntas Frecuentes</h1>
          </div>
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-2">Como funciona el pago?</h3>
            <p className="text-gray-600 text-sm">
              Los pagos se realizan en USDC a traves del protocolo x402. El dinero se
              deposita en escrow cuando se crea la tarea y se libera automaticamente
              al completarla.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-2">Que pasa si hay una disputa?</h3>
            <p className="text-gray-600 text-sm">
              Las disputas son resueltas por un panel de arbitros. Ambas partes pueden
              presentar evidencia y el panel vota para determinar el resultado.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-2">Como construyo mi reputacion?</h3>
            <p className="text-gray-600 text-sm">
              Tu reputacion aumenta al completar tareas exitosamente. Las tareas con
              mayor valor y complejidad otorgan mas puntos de reputacion.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

// --------------------------------------------------------------------------
// App Router
// --------------------------------------------------------------------------

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/faq" element={<FAQPage />} />

      {/* Worker Routes (Protected - Workers Only) */}
      <Route
        path="/tasks"
        element={
          <WorkerGuard>
            <TasksPage />
          </WorkerGuard>
        }
      />
      <Route
        path="/profile"
        element={
          <WorkerGuard>
            <ProfilePageWrapper />
          </WorkerGuard>
        }
      />
      <Route
        path="/earnings"
        element={
          <WorkerGuard>
            <EarningsPage />
          </WorkerGuard>
        }
      />

      {/* Agent Routes (Protected - Agents Only) */}
      <Route
        path="/agent/dashboard"
        element={
          <AgentGuard>
            <AgentDashboardPage />
          </AgentGuard>
        }
      />
      <Route
        path="/agent/tasks"
        element={
          <AgentGuard>
            <AgentTasksPage />
          </AgentGuard>
        }
      />
      <Route
        path="/agent/tasks/new"
        element={
          <AgentGuard>
            <AgentTasksPage />
          </AgentGuard>
        }
      />
    </Routes>
  )
}

// --------------------------------------------------------------------------
// Main App Component
// --------------------------------------------------------------------------

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
