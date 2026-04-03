import { useState, useCallback, useMemo } from 'react'
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
import type { VerificationResponse } from '../services/submissions'
import type { Task, TaskCategory } from '../types/database'
import { getCheckLabel } from '../constants/checkLabels'

type TasksView = 'list' | 'detail' | 'submit' | 'submitted'

function SubmissionConfirmation({
  task,
  verification,
  onBack,
}: {
  task: Task
  verification?: VerificationResponse | null
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
          {t('tasks.evidenceSubmitted', 'Evidence submitted')}
        </h2>
        <p className="text-gray-500 text-sm">
          {task.title}
        </p>
      </div>

      {/* Verification results */}
      {verification && (
        <div className={`bg-white rounded-lg border p-4 ${verification.passed ? 'border-green-200' : 'border-orange-200'}`}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-700">
              {t('autoCheck.title', 'Automatic verification')}
            </span>
            <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${
              verification.passed ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'
            }`}>
              {Math.round(verification.score * 100)}%
            </span>
          </div>
          {verification.summary && (
            <p className="text-sm text-gray-600 mb-3">{verification.summary}</p>
          )}
          <div className="space-y-1">
            {verification.checks.map(check => (
              <div key={check.name} className="flex items-center gap-2 text-xs">
                <span className={check.passed ? 'text-green-600' : 'text-red-500'}>
                  {check.passed ? '\u2713' : '\u2717'}
                </span>
                <span className="text-gray-600 w-28">
                  {getCheckLabel(check.name, t)}
                </span>
                <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${
                      check.score >= 0.7 ? 'bg-green-500' : check.score >= 0.4 ? 'bg-yellow-500' : 'bg-red-400'
                    }`}
                    style={{ width: `${Math.round(check.score * 100)}%` }}
                  />
                </div>
                <span className="text-gray-400 font-mono w-8 text-right">
                  {Math.round(check.score * 100)}%
                </span>
              </div>
            ))}
          </div>
          {verification.phase_b_status === 'pending' && (
            <p className="text-xs text-blue-600 mt-2">
              {t('autoCheck.phaseBPending', 'AI verification in progress. Results will update automatically.')}
            </p>
          )}
        </div>
      )}

      {/* Payment status */}
      {loading ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-gray-600">
              {t('payment.processing', 'Processing payment...')}
            </span>
          </div>
        </div>
      ) : payment ? (
        <PaymentStatus payment={payment} showTimeline={true} bountyAmount={task.bounty_usd} />
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-gray-600">
              {t('payment.awaitingRecord', 'Awaiting payment confirmation...')}
            </span>
          </div>
        </div>
      )}

      {/* Back button */}
      <button
        onClick={onBack}
        className="w-full py-3 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 transition-colors"
      >
        {t('tasks.backToMyTasks', 'Back to my tasks')}
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

  const { executor } = useAuth()
  const [showOnlyEligible, setShowOnlyEligible] = useState(false)

  const {
    tasks: availableTasks,
    loading: availableLoading,
    error: availableError,
  } = useAvailableTasks({ category: category ?? undefined })

  // When "only eligible" is checked and user lacks World ID, hide tasks >= $5
  const filteredAvailableTasks = useMemo(() => {
    if (!showOnlyEligible || executor?.world_id_verified) return availableTasks
    return availableTasks.filter((task) => task.bounty_usd < 5.0)
  }, [availableTasks, showOnlyEligible, executor?.world_id_verified])

  const {
    tasks: myTasks,
    loading: myTasksLoading,
    error: myTasksError,
    refetch: refetchMyTasks,
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
    // Immediately refetch so the accepted task appears without manual refresh
    refetchMyTasks()
  }, [refetchMyTasks])

  const handleStartSubmission = useCallback(() => {
    setView('submit')
  }, [])

  const [verification, setVerification] = useState<VerificationResponse | null>(null)

  const handleSubmissionComplete = useCallback((v?: VerificationResponse | null) => {
    setVerification(v ?? null)
    // Update local task status so "Submit Evidence" button hides on back-navigation
    if (selectedTask) {
      setSelectedTask({ ...selectedTask, status: 'submitted' })
    }
    setView('submitted')
    // Refresh task list to reflect new status
    refetchMyTasks()
  }, [selectedTask, refetchMyTasks])

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

          {['accepted', 'in_progress'].includes(selectedTask.status) &&
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
          verification={verification}
          onBack={() => {
            setView('list')
            setSelectedTask(null)
            setActiveTab('mine')
            setVerification(null)
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
          <div className="mb-4 space-y-3">
            <CategoryFilter selected={category} onChange={setCategory} />
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={showOnlyEligible}
                onChange={(e) => setShowOnlyEligible(e.target.checked)}
                className="rounded border-gray-300 text-gray-900 focus:ring-gray-900"
              />
              {t('tasks.showEligible', 'Only tasks I can apply to')}
            </label>
          </div>
        )}

        {/* Task list */}
        {activeTab === 'available' ? (
          <TaskList
            tasks={filteredAvailableTasks}
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
    <div className="max-w-3xl mx-auto px-4 py-6">{renderContent()}</div>
  )
}
