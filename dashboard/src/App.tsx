// Execution Market Dashboard - Main App Component with Routing
import { useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'

// Auth
import { AuthProvider, useAuth } from './context/AuthContext'
import { WorkerGuard, AgentGuard } from './components/guards'

// Components
import { LanguageSwitcher } from './components/LanguageSwitcher'
import { ProfilePage } from './components/profile'
import { ProfileEditModal } from './components/profile/ProfileEditModal'

// Pages
import { Home } from './pages/Home'
import { WorkerTasks } from './pages/WorkerTasks'
import { About } from './pages/About'
import { FAQ } from './pages/FAQ'
import { AgentDashboard } from './pages/AgentDashboard'

// --------------------------------------------------------------------------
// Profile Page (Worker - Protected)
// --------------------------------------------------------------------------

function ProfilePageWrapper() {
  const navigate = useNavigate()
  const { executor, loading, refreshExecutor } = useAuth()
  const [showEditModal, setShowEditModal] = useState(false)

  const handleEditSaved = useCallback(() => {
    setShowEditModal(false)
    refreshExecutor()
  }, [refreshExecutor])

  // Show loading state while fetching executor
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center gap-3">
          <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-gray-500">Cargando perfil...</p>
        </div>
      </div>
    )
  }

  // If not loading but no executor, show error with retry option
  if (!executor) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">No se pudo cargar tu perfil.</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => refreshExecutor()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Reintentar
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Volver al inicio
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <ProfilePage
        executor={executor}
        onBack={() => navigate('/tasks')}
        onEditProfile={() => setShowEditModal(true)}
      />
      {showEditModal && (
        <ProfileEditModal
          executor={executor}
          onClose={() => setShowEditModal(false)}
          onSaved={handleEditSaved}
        />
      )}
    </>
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
  const { executor } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">&#128188;</span>
              <span className="font-bold text-lg text-gray-900">Execution Market</span>
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
          agentId={executor?.id ?? ''}
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
// App Router
// --------------------------------------------------------------------------

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Home />} />
      <Route path="/about" element={<About />} />
      <Route path="/faq" element={<FAQ />} />

      {/* Worker Routes (Protected - Workers Only) */}
      <Route
        path="/tasks"
        element={
          <WorkerGuard>
            <WorkerTasks />
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
