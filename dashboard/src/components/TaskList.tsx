// Execution Market: Task List Component
import { useTranslation } from 'react-i18next'
import { TaskCard } from './TaskCard'
import type { Task, TaskCategory } from '../types/database'

interface TaskListProps {
  tasks: Task[]
  loading: boolean
  error: Error | null
  onTaskClick?: (task: Task) => void
  emptyMessage?: string
}

// Hoisted static elements (React best practice: rendering-hoist-jsx)
const LOADING_SKELETON = (
  <div className="space-y-4">
    {[1, 2, 3].map((i) => (
      <div
        key={i}
        className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse"
      >
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 bg-gray-200 rounded" />
          <div className="w-24 h-3 bg-gray-200 rounded" />
        </div>
        <div className="w-3/4 h-5 bg-gray-200 rounded mb-2" />
        <div className="w-full h-4 bg-gray-200 rounded mb-1" />
        <div className="w-2/3 h-4 bg-gray-200 rounded mb-3" />
        <div className="flex justify-between pt-3 border-t border-gray-100">
          <div className="w-16 h-6 bg-gray-200 rounded" />
          <div className="w-20 h-4 bg-gray-200 rounded" />
        </div>
      </div>
    ))}
  </div>
)

const ERROR_ICON = (
  <svg
    className="w-12 h-12 text-red-400 mx-auto mb-4"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
    />
  </svg>
)

const EMPTY_ICON = (
  <svg
    className="w-12 h-12 text-gray-400 mx-auto mb-4"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
    />
  </svg>
)

export function TaskList({
  tasks,
  loading,
  error,
  onTaskClick,
  emptyMessage,
}: TaskListProps) {
  const { t } = useTranslation()

  if (loading) {
    return LOADING_SKELETON
  }

  if (error) {
    return (
      <div className="text-center py-12">
        {ERROR_ICON}
        <h3 className="text-lg font-medium text-gray-900 mb-1">
          {t('tasks.loadError')}
        </h3>
        <p className="text-gray-500">{error.message}</p>
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-12">
        {EMPTY_ICON}
        <h3 className="text-lg font-medium text-gray-900 mb-1">{emptyMessage || t('tasks.noTasks')}</h3>
        <p className="text-gray-500">{t('tasks.emptyHint')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} onClick={() => onTaskClick?.(task)} />
      ))}
    </div>
  )
}

// Category filter component
interface CategoryFilterProps {
  selected: TaskCategory | null
  onChange: (category: TaskCategory | null) => void
}

const CATEGORIES: { value: TaskCategory | null; key: string; icon: string }[] = [
  { value: null, key: 'all', icon: '🏠' },
  { value: 'physical_presence', key: 'physical_presence', icon: '📍' },
  { value: 'knowledge_access', key: 'knowledge_access', icon: '📚' },
  { value: 'human_authority', key: 'human_authority', icon: '📋' },
  { value: 'simple_action', key: 'simple_action', icon: '✋' },
  { value: 'digital_physical', key: 'digital_physical', icon: '🔗' },
]

export function CategoryFilter({ selected, onChange }: CategoryFilterProps) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap gap-2">
      {CATEGORIES.map(({ value, key, icon }) => (
        <button
          key={value ?? 'all'}
          onClick={() => onChange(value)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            selected === value
              ? 'bg-blue-100 text-blue-800'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          <span>{icon}</span>
          <span>{t(`tasks.categories.${key}`, key)}</span>
        </button>
      ))}
    </div>
  )
}
