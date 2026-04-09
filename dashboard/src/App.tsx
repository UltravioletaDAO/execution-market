// Execution Market Dashboard - Main App Component with Routing
import { useState, useCallback, lazy, Suspense, type ReactNode } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useSearchParams } from 'react-router-dom'

// Auth
import { AuthProvider, useAuth } from './context/AuthContext'
import { XMTPProvider } from './context/XMTPContext'
import { AuthGuard, WorkerGuard, AgentGuard } from './components/guards'

// Dynamic.xyz widget — must be rendered in the tree for the auth modal to work
import { DynamicWidget, useDynamicContext } from '@dynamic-labs/sdk-react-core'

// Layout
import { AppLayout } from './components/layout/AppLayout'

// Lazy-loaded page components for code splitting
const Home = lazy(() => import('./pages/Home').then(m => ({ default: m.Home })))
const WorkerTasks = lazy(() => import('./pages/WorkerTasks').then(m => ({ default: m.WorkerTasks })))
const About = lazy(() => import('./pages/About').then(m => ({ default: m.About })))
const FAQ = lazy(() => import('./pages/FAQ').then(m => ({ default: m.FAQ })))
const AgentOnboarding = lazy(() => import('./pages/AgentOnboarding').then(m => ({ default: m.AgentOnboarding })))
const AgentLogin = lazy(() => import('./components/AgentLogin').then(m => ({ default: m.AgentLogin })))
const Developers = lazy(() => import('./pages/Developers').then(m => ({ default: m.Developers })))
const FeedbackPage = lazy(() => import('./pages/FeedbackPage').then(m => ({ default: m.FeedbackPage })))
const DisputesPage = lazy(() => import('./pages/DisputesPage'))
const TaskManagement = lazy(() => import('./pages/agent/TaskManagement').then(m => ({ default: m.TaskManagement })))
const CreateTask = lazy(() => import('./pages/agent/CreateTask').then(m => ({ default: m.CreateTask })))
const PublicProfile = lazy(() => import('./pages/PublicProfile').then(m => ({ default: m.PublicProfile })))
const Activity = lazy(() => import('./pages/Activity').then(m => ({ default: m.Activity })))
const AgentDirectory = lazy(() => import('./pages/AgentDirectory').then(m => ({ default: m.AgentDirectory })))
const TradingLeaderboard = lazy(() => import('./pages/TradingLeaderboard').then(m => ({ default: m.TradingLeaderboard })))
const Leaderboard = lazy(() => import('./pages/Leaderboard').then(m => ({ default: m.Leaderboard })))
const PublisherDashboard = lazy(() => import('./pages/publisher/Dashboard').then(m => ({ default: m.default })))
const PublisherCreateRequest = lazy(() => import('./pages/publisher/CreateRequest').then(m => ({ default: m.default })))
const PublisherReviewSubmission = lazy(() => import('./pages/publisher/ReviewSubmission').then(m => ({ default: m.default })))
const RatingsHistory = lazy(() => import('./pages/RatingsHistory').then(m => ({ default: m.RatingsHistory })))
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })))
const Messages = lazy(() => import('./pages/Messages').then(m => ({ default: m.Messages })))
const AuditGrid = lazy(() => import('./pages/AuditGrid').then(m => ({ default: m.AuditGrid })))

// Legal pages (public, required for App Store / Google Play)
const PrivacyPolicy = lazy(() => import('./pages/legal/PrivacyPolicy').then(m => ({ default: m.PrivacyPolicy })))
const TermsOfService = lazy(() => import('./pages/legal/TermsOfService').then(m => ({ default: m.TermsOfService })))
const SupportPage = lazy(() => import('./pages/legal/Support').then(m => ({ default: m.Support })))
const DeleteAccount = lazy(() => import('./pages/legal/DeleteAccount').then(m => ({ default: m.DeleteAccount })))

// Extracted page wrappers (previously inline in this file)
const ProfilePageWrapper = lazy(() => import('./pages/ProfilePageWrapper'))
const EarningsPage = lazy(() => import('./pages/EarningsPage'))
const AgentDashboardPage = lazy(() => import('./pages/AgentDashboardPage'))

// Lazy-loaded heavy components (modals)
const TaskDetailModal = lazy(() => import('./components/TaskDetailModal').then(m => ({ default: m.TaskDetailModal })))
const SubmissionReviewModal = lazy(() => import('./components/SubmissionReviewModal').then(m => ({ default: m.SubmissionReviewModal })))

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
// XMTP Provider Wrapper (reads wallet from AuthContext)
// --------------------------------------------------------------------------

function XMTPProviderWrapper({ children }: { children: ReactNode }) {
  const { walletAddress } = useAuth()
  const { primaryWallet } = useDynamicContext()
  const signer = primaryWallet ?? null

  return (
    <XMTPProvider walletAddress={walletAddress} signer={signer}>
      {children}
    </XMTPProvider>
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
        <Route path="/privacy" element={<PrivacyPolicy />} />
        <Route path="/terms" element={<TermsOfService />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/delete-account" element={<DeleteAccount />} />
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
        <Route path="/disputes" element={<DisputesPage />} />
        <Route path="/agents/directory" element={<AgentDirectory />} />
        <Route path="/trading" element={<TradingLeaderboard />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route
          path="/audit"
          element={
            <AuthGuard>
              <AuditGrid />
            </AuthGuard>
          }
        />
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
        <Route
          path="/ratings"
          element={
            <WorkerGuard>
              <RatingsHistory />
            </WorkerGuard>
          }
        />
        <Route
          path="/settings"
          element={
            <AuthGuard>
              <Settings />
            </AuthGuard>
          }
        />
        <Route
          path="/messages"
          element={
            <AuthGuard>
              <Messages />
            </AuthGuard>
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
        <XMTPProviderWrapper>
          <AppRoutes />
        </XMTPProviderWrapper>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
