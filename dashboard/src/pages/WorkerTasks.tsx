import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { useAvailableTasks, useMyTasks } from '../hooks/useTasks'
import { TaskList, CategoryFilter } from '../components/TaskList'
import { TaskDetail } from '../components/TaskDetail'
import { SubmissionForm } from '../components/SubmissionForm'
import { LanguageSwitcher } from '../components/LanguageSwitcher'
import type { Task, TaskCategory } from '../types/database'

type TasksView = 'list' | 'detail' | 'submit'

export function WorkerTasks() {
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
