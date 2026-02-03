import { useState, forwardRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAvailableTasks } from '../../hooks/useTasks'
import { useAuth } from '../../context/AuthContext'
import { TaskList, CategoryFilter } from '../TaskList'
import { TaskDetailPanel } from './TaskDetailPanel'
import { TaskApplicationModal } from '../TaskApplicationModal'
import type { Task, TaskCategory } from '../../types/database'

interface PublicTaskBrowserProps {
  onAuthRequired: () => void
}

export const PublicTaskBrowser = forwardRef<HTMLElement, PublicTaskBrowserProps>(
  function PublicTaskBrowser({ onAuthRequired }, ref) {
    const { t } = useTranslation()
    const { isAuthenticated } = useAuth()
    const [category, setCategory] = useState<TaskCategory | null>(null)
    const [selectedTask, setSelectedTask] = useState<Task | null>(null)
    const [applyingTask, setApplyingTask] = useState<Task | null>(null)

    const {
      tasks,
      loading,
      error,
    } = useAvailableTasks({ category: category ?? undefined })

    const handleTaskClick = (task: Task) => {
      setSelectedTask(task)
    }

    const handleApply = () => {
      if (!isAuthenticated) {
        setSelectedTask(null)
        onAuthRequired()
      } else if (selectedTask) {
        // Authenticated user - show application modal
        setApplyingTask(selectedTask)
        setSelectedTask(null)
      }
    }

    const handleApplicationSuccess = () => {
      setApplyingTask(null)
    }

    return (
      <section ref={ref} className="py-12">
        <div className="text-center mb-8">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
            {t('landing.liveTasksTitle')}
          </h2>
          <p className="text-gray-500">
            {t('landing.liveTasksSubtitle')}
          </p>
        </div>

        <div className="mb-6">
          <CategoryFilter selected={category} onChange={setCategory} />
        </div>

        <TaskList
          tasks={tasks}
          loading={loading}
          error={error}
          onTaskClick={handleTaskClick}
          emptyMessage={t('tasks.noTasks')}
        />

        {selectedTask && (
          <TaskDetailPanel
            task={selectedTask}
            isAuthenticated={isAuthenticated}
            onClose={() => setSelectedTask(null)}
            onApply={handleApply}
          />
        )}

        {applyingTask && (
          <TaskApplicationModal
            task={applyingTask}
            onClose={() => setApplyingTask(null)}
            onSuccess={handleApplicationSuccess}
          />
        )}
      </section>
    )
  }
)
