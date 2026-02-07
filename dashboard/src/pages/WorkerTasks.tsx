import { useState, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { useAvailableTasks, useMyTasks } from '../hooks/useTasks'
import { useTaskPayment } from '../hooks/useTaskPayment'
import { usePublicMetrics } from '../hooks/usePublicMetrics'
import { TaskList, CategoryFilter } from '../components/TaskList'
import { TaskDetail } from '../components/TaskDetail'
import { SubmissionForm } from '../components/SubmissionForm'
import { PaymentStatus } from '../components/PaymentStatus'
import { LanguageSwitcher } from '../components/LanguageSwitcher'
import type { Task, TaskCategory } from '../types/database'

type TasksView = 'list' | 'detail' | 'submit' | 'submitted'

function SubmissionConfirmation({
  task,
  onBack,
}: {
  task: Task
  onBack: () => void
}) {
  const { t } = useTranslation()
  const { payment, loading } = useTaskPayment(task.id)

  return (
    <div className="space-y-4">
      {/* Success header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">
          {t('tasks.evidenceSubmitted', 'Evidencia enviada')}
        </h2>
        <p className="text-gray-500 text-sm">
          {task.title}
        </p>
      </div>

      {/* Payment status */}
      {loading ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-gray-600">
              {t('payment.processing', 'Procesando pago...')}
            </span>
          </div>
        </div>
      ) : payment ? (
        <PaymentStatus payment={payment} showTimeline={true} />
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-gray-600">
              {t('payment.awaitingRecord', 'Esperando confirmacion de pago...')}
            </span>
          </div>
        </div>
      )}

      {/* Back button */}
      <button
        onClick={onBack}
        className="w-full py-3 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 transition-colors"
      >
        {t('tasks.backToMyTasks', 'Volver a mis tareas')}
      </button>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className="text-lg font-bold text-gray-900 mt-1">{value}</div>
    </div>
  )
}

export function WorkerTasks() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [view, setView] = useState<TasksView>('list')
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [category, setCategory] = useState<TaskCategory | null>(null)
  const location = useLocation()
  const [activeTab, setActiveTab] = useState<'available' | 'mine'>(
    location.state?.tab === 'mine' ? 'mine' : 'available'
  )

  const { executor, isAuthenticated, loading: authLoading, logout } = useAuth()

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
  const { metrics: platformMetrics, loading: metricsLoading } = usePublicMetrics()

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
    setView('submitted')
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

    if (view === 'submitted' && selectedTask) {
      return (
        <SubmissionConfirmation
          task={selectedTask}
          onBack={() => {
            setView('list')
            setSelectedTask(null)
            setActiveTab('mine')
          }}
        />
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
        {/* Platform metrics */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <MetricCard
            label={t('metrics.registeredUsers', 'Registered Users')}
            value={metricsLoading ? '...' : platformMetrics ? new Intl.NumberFormat('en-US').format(platformMetrics.users.registered_workers) : '0'}
          />
          <MetricCard
            label={t('metrics.activeWorkers', 'Workers Taking Tasks')}
            value={metricsLoading ? '...' : platformMetrics ? new Intl.NumberFormat('en-US').format(platformMetrics.activity.workers_with_active_tasks) : '0'}
          />
          <MetricCard
            label={t('metrics.activeAgents', 'Active Agents')}
            value={metricsLoading ? '...' : platformMetrics ? new Intl.NumberFormat('en-US').format(platformMetrics.activity.agents_with_live_tasks) : '0'}
          />
          <MetricCard
            label={t('metrics.completedTasks', 'Completed Tasks')}
            value={metricsLoading ? '...' : platformMetrics ? new Intl.NumberFormat('en-US').format(platformMetrics.tasks.completed) : '0'}
          />
        </div>

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
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex items-center justify-between h-14">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 hover:opacity-80 transition-opacity"
              aria-label="Execution Market"
            >
              <img src="/logo.png" alt="EM" className="w-8 h-8 rounded-lg object-contain" />
              <span className="font-bold text-lg text-gray-900 hidden sm:inline">Execution Market</span>
            </button>

            <div className="flex items-center gap-2">
              <div className="hidden sm:block">
                <LanguageSwitcher compact />
              </div>

              {authLoading ? (
                <div className="w-6 h-6 bg-gray-200 rounded-full animate-pulse" />
              ) : isAuthenticated ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate('/profile')}
                    className="flex items-center gap-2 hover:bg-gray-50 rounded-lg px-3 py-1.5 transition-colors"
                  >
                    <div className="w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs font-bold">
                        {(executor?.display_name || 'U')[0].toUpperCase()}
                      </span>
                    </div>
                    <span className="text-sm font-medium text-gray-700 hidden sm:inline">
                      {executor?.display_name || t('nav.profile', 'Profile')}
                    </span>
                  </button>
                  <button
                    onClick={() => logout()}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    title={t('auth.logout')}
                  >
                    <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
      <main className="max-w-3xl mx-auto px-4 py-6">{renderContent()}</main>

      {/* Footer */}
      <footer className="max-w-3xl mx-auto px-4 py-6 text-center text-sm text-gray-400">
        <p>Execution Market - Human Execution Layer for AI Agents</p>
        <p className="mt-1">{t('footer.poweredBy')} Ultravioleta DAO</p>
      </footer>
    </div>
  )
}
