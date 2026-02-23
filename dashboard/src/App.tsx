// Execution Market Dashboard - Main App Component with Routing
import { useState, useCallback, useMemo, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useSearchParams } from 'react-router-dom'

// Auth
import { AuthProvider, useAuth } from './context/AuthContext'
import { AuthGuard, WorkerGuard, AgentGuard } from './components/guards'

// Dynamic.xyz widget — must be rendered in the tree for the auth modal to work
import { DynamicWidget } from '@dynamic-labs/sdk-react-core'

// Layout
import { AppLayout } from './components/layout/AppLayout'

// Lazy-loaded page components for code splitting
const Home = lazy(() => import('./pages/Home').then(m => ({ default: m.Home })))
const WorkerTasks = lazy(() => import('./pages/WorkerTasks').then(m => ({ default: m.WorkerTasks })))
const About = lazy(() => import('./pages/About').then(m => ({ default: m.About })))
const FAQ = lazy(() => import('./pages/FAQ').then(m => ({ default: m.FAQ })))
const AgentDashboard = lazy(() => import('./pages/AgentDashboard').then(m => ({ default: m.AgentDashboard })))
const AgentOnboarding = lazy(() => import('./pages/AgentOnboarding').then(m => ({ default: m.AgentOnboarding })))
const AgentLogin = lazy(() => import('./components/AgentLogin').then(m => ({ default: m.AgentLogin })))
const Developers = lazy(() => import('./pages/Developers').then(m => ({ default: m.Developers })))
const FeedbackPage = lazy(() => import('./pages/FeedbackPage').then(m => ({ default: m.FeedbackPage })))
const TaskManagement = lazy(() => import('./pages/agent/TaskManagement').then(m => ({ default: m.TaskManagement })))
const CreateTask = lazy(() => import('./pages/agent/CreateTask').then(m => ({ default: m.CreateTask })))
const PublicProfile = lazy(() => import('./pages/PublicProfile').then(m => ({ default: m.PublicProfile })))
const Activity = lazy(() => import('./pages/Activity').then(m => ({ default: m.Activity })))
const AgentDirectory = lazy(() => import('./pages/AgentDirectory').then(m => ({ default: m.AgentDirectory })))
const TradingLeaderboard = lazy(() => import('./pages/TradingLeaderboard').then(m => ({ default: m.TradingLeaderboard })))
const PublisherDashboard = lazy(() => import('./pages/publisher/Dashboard').then(m => ({ default: m.default })))
const PublisherCreateRequest = lazy(() => import('./pages/publisher/CreateRequest').then(m => ({ default: m.default })))
const PublisherReviewSubmission = lazy(() => import('./pages/publisher/ReviewSubmission').then(m => ({ default: m.default })))

// Lazy-loaded heavy components (modals, charts)
const ProfilePage = lazy(() => import('./components/profile').then(m => ({ default: m.ProfilePage })))
const ProfileEditModal = lazy(() => import('./components/profile/ProfileEditModal').then(m => ({ default: m.ProfileEditModal })))
const SubmissionReviewModal = lazy(() => import('./components/SubmissionReviewModal').then(m => ({ default: m.SubmissionReviewModal })))
const TaskDetailModal = lazy(() => import('./components/TaskDetailModal').then(m => ({ default: m.TaskDetailModal })))

// Type-only import (no runtime cost)
import type { ChartPeriod } from './pages/Earnings'

// Lazy load Earnings page (has chart dependencies)
const Earnings = lazy(() => import('./pages/Earnings').then(m => ({ default: m.Earnings })))

import { useEarnings, useTaskHistory } from './hooks/useProfile'

// Loading fallback component
function PageLoader() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="flex items-center gap-3">
        <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p className="text-gray-500">Loading...</p>
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------
// Profile Page (Worker - Protected)
// --------------------------------------------------------------------------

function ProfilePageWrapper() {
  const navigate = useNavigate()
  const { executor, loading, refreshExecutor, logout } = useAuth()
  const [showEditModal, setShowEditModal] = useState(false)

  const handleEditSaved = useCallback(() => {
    setShowEditModal(false)
    refreshExecutor()
  }, [refreshExecutor])

  // Show loading state while fetching executor
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
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
      <div className="flex items-center justify-center py-20">
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
        onLogout={() => { logout(); navigate('/') }}
      />
      {showEditModal && (
        <Suspense fallback={null}>
          <ProfileEditModal
            executor={executor}
            onClose={() => setShowEditModal(false)}
            onSaved={handleEditSaved}
          />
        </Suspense>
      )}
    </>
  )
}

// --------------------------------------------------------------------------
// Earnings Page (Worker - Protected)
// --------------------------------------------------------------------------

function EarningsPage() {
  const navigate = useNavigate()
  const { executor } = useAuth()
  const [chartPeriod, setChartPeriod] = useState<ChartPeriod>('month')

  const { earnings, loading: earningsLoading, error } = useEarnings(executor?.id)
  const { history, loading: historyLoading } = useTaskHistory(executor?.id, 20)

  const thisWeekUsdc = useMemo(() => {
    const cutoff = Date.now() - (7 * 24 * 60 * 60 * 1000)
    return history
      .filter((item) => item.status === 'approved' && new Date(item.submitted_at).getTime() >= cutoff)
      .reduce((sum, item) => sum + (item.payment_amount ?? item.bounty_usd ?? 0), 0)
  }, [history])

  const summary = useMemo(() => {
    if (!earnings) return null
    return {
      total_earned_usdc: earnings.total_earned_usdc ?? 0,
      available_balance_usdc: earnings.balance_usdc ?? 0,
      pending_usdc: earnings.pending_earnings_usdc ?? 0,
      this_month_usdc: earnings.this_month_usdc ?? 0,
      last_month_usdc: earnings.last_month_usdc ?? 0,
      this_week_usdc: thisWeekUsdc,
    }
  }, [earnings, thisWeekUsdc])

  const transactions = useMemo(() => {
    return history.map((item) => ({
      id: item.id,
      type: 'task_payment' as const,
      amount_usdc: item.payment_amount ?? item.bounty_usd ?? 0,
      status: (item.status === 'approved'
        ? 'completed'
        : item.status === 'rejected'
          ? 'failed'
          : 'pending') as 'completed' | 'failed' | 'pending',
      tx_hash: null,
      network: 'base',
      created_at: item.verified_at ?? item.submitted_at,
      task_title: item.task_title,
      task_id: item.task_id,
    }))
  }, [history])

  const pendingPayments = useMemo(() => {
    return history
      .filter((item) => item.status === 'pending')
      .map((item) => ({
        id: item.id,
        task_id: item.task_id,
        task_title: item.task_title,
        bounty_usd: item.bounty_usd ?? 0,
        submitted_at: item.submitted_at,
        expected_payout_date: new Date(new Date(item.submitted_at).getTime() + (48 * 60 * 60 * 1000)).toISOString(),
        status: 'awaiting_review' as const,
      }))
  }, [history])

  const chartData = useMemo(() => {
    if (!summary) return []

    if (chartPeriod === 'week') {
      return [
        { label: 'Ultimos 7 dias', value: summary.this_week_usdc },
        { label: 'Pendiente', value: summary.pending_usdc },
      ]
    }

    if (chartPeriod === 'year') {
      return [
        { label: 'Q1', value: summary.this_month_usdc },
        { label: 'Q2', value: summary.this_month_usdc },
        { label: 'Q3', value: summary.last_month_usdc },
        { label: 'Q4', value: summary.last_month_usdc },
      ]
    }

    return [
      { label: 'Mes actual', value: summary.this_month_usdc },
      { label: 'Mes pasado', value: summary.last_month_usdc },
      { label: 'Pendiente', value: summary.pending_usdc },
    ]
  }, [summary, chartPeriod])

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
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
      <Earnings
        summary={summary}
        transactions={transactions}
        pendingPayments={pendingPayments}
        chartData={chartData}
        loading={earningsLoading || historyLoading}
        error={error}
        onWithdraw={() => navigate('/profile')}
        onChartPeriodChange={setChartPeriod}
        chartPeriod={chartPeriod}
      />
    </div>
  )
}

// --------------------------------------------------------------------------
// Agent Dashboard Page (Agent - Protected)
// --------------------------------------------------------------------------

function AgentDashboardPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { executor } = useAuth()

  const reviewSubmissionId = searchParams.get('review')

  const closeReview = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('review')
      return next
    })
  }, [setSearchParams])

  return (
    <>
      <div className="max-w-6xl mx-auto px-4 py-6">
        <AgentDashboard
          agentId={executor?.id ?? ''}
          onBack={() => navigate('/')}
          onCreateTask={() => navigate('/agent/tasks/new')}
          onViewTask={(task) => navigate(`/agent/tasks?view=${task.id}`)}
          onReviewSubmission={(submission) => setSearchParams({ review: submission.id })}
        />
      </div>
      {reviewSubmissionId && (
        <Suspense fallback={null}>
          <SubmissionReviewModal
            submissionId={reviewSubmissionId}
            onClose={closeReview}
            onSuccess={closeReview}
          />
        </Suspense>
      )}
    </>
  )
}

// --------------------------------------------------------------------------
// Agent Tasks Page (Agent - Protected)
// --------------------------------------------------------------------------

function AgentTasksPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { executor } = useAuth()

  const viewTaskId = searchParams.get('view')
  const reviewSubmissionId = searchParams.get('review')

  const closeModal = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('view')
      next.delete('review')
      return next
    })
  }, [setSearchParams])

  return (
    <>
      <div className="max-w-6xl mx-auto px-4 py-6">
        <TaskManagement
          agentId={executor?.id ?? ''}
          onBack={() => navigate('/agent/dashboard')}
          onCreateTask={() => navigate('/agent/tasks/new')}
          onViewTask={(task) => setSearchParams({ view: task.id })}
          onEditTask={(task) => navigate(`/agent/tasks/new?edit=${task.id}`)}
          onViewApplicants={(task) => setSearchParams({ view: task.id })}
        />
      </div>
      {viewTaskId && (
        <Suspense fallback={null}>
          <TaskDetailModal
            taskId={viewTaskId}
            onClose={closeModal}
            onReviewSubmission={(subId) => setSearchParams({ review: subId })}
          />
        </Suspense>
      )}
      {reviewSubmissionId && (
        <Suspense fallback={null}>
          <SubmissionReviewModal
            submissionId={reviewSubmissionId}
            onClose={closeModal}
            onSuccess={closeModal}
          />
        </Suspense>
      )}
    </>
  )
}

function AgentCreateTaskPage() {
  const navigate = useNavigate()
  const { executor } = useAuth()

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <CreateTask
        agentId={executor?.id ?? ''}
        onBack={() => navigate('/agent/tasks')}
        onSuccess={() => navigate('/agent/tasks')}
      />
    </div>
  )
}

// --------------------------------------------------------------------------
// App Router
// --------------------------------------------------------------------------

function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
    <Routes>
      <Route element={<AppLayout />}>
        {/* Public Routes */}
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/faq" element={<FAQ />} />
        <Route path="/agents" element={<AgentOnboarding />} />
        <Route path="/agent/login" element={<AgentLogin />} />
        <Route path="/developers" element={<Developers />} />
        <Route
          path="/activity"
          element={
            <AuthGuard>
              <Activity />
            </AuthGuard>
          }
        />
        <Route path="/profile/:wallet" element={<PublicProfile />} />
        <Route path="/feedback/:taskId" element={<FeedbackPage />} />
        <Route path="/agents/directory" element={<AgentDirectory />} />
        <Route path="/trading" element={<TradingLeaderboard />} />
        <Route
          path="/publisher/dashboard"
          element={
            <AuthGuard>
              <PublisherDashboard />
            </AuthGuard>
          }
        />
        <Route
          path="/publisher/requests/new"
          element={
            <AuthGuard>
              <PublisherCreateRequest />
            </AuthGuard>
          }
        />
        <Route
          path="/publisher/requests/:taskId/review"
          element={
            <AuthGuard>
              <PublisherReviewSubmission />
            </AuthGuard>
          }
        />

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
              <AgentCreateTaskPage />
            </AgentGuard>
          }
        />
      </Route>
    </Routes>
    </Suspense>
  )
}

// --------------------------------------------------------------------------
// Main App Component
// --------------------------------------------------------------------------

function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        {/* DynamicWidget — rendered off-screen but in DOM so auth modal can open.
            display:none prevents Dynamic from initializing, so we use sr-only instead. */}
        <div className="sr-only" aria-hidden="true">
          <DynamicWidget />
        </div>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
