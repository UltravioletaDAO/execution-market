/**
 * Tasks - Task List Page for Workers
 *
 * Features:
 * - Filter tabs: All Available, Near Me, My Applications
 * - Task cards showing: title, bounty, location, deadline, evidence required
 * - Search/filter by bounty range, distance
 * - Click to open TaskDetail
 * - Empty states when no tasks
 */

import { useState, useMemo, useCallback } from 'react'
import { TaskCard } from '../components/TaskCard'
import { CategoryFilter } from '../components/TaskList'
import type { Task, TaskCategory, Executor, TaskApplication } from '../types/database'

// ============================================================================
// TYPES
// ============================================================================

export type TaskFilterTab = 'all' | 'near_me' | 'my_applications'

export interface TasksPageProps {
  tasks: Task[]
  applications: TaskApplication[]
  executor: Executor | null
  loading?: boolean
  error?: Error | null
  onTaskClick: (task: Task) => void
  onRefresh?: () => void
}

interface FilterState {
  tab: TaskFilterTab
  category: TaskCategory | null
  minBounty: number | null
  maxBounty: number | null
  maxDistance: number | null
  searchQuery: string
}

// ============================================================================
// CONSTANTS
// ============================================================================

const TAB_OPTIONS: { value: TaskFilterTab; label: string; icon: JSX.Element }[] = [
  {
    value: 'all',
    label: 'Disponibles',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
        />
      </svg>
    ),
  },
  {
    value: 'near_me',
    label: 'Cerca de mi',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
    ),
  },
  {
    value: 'my_applications',
    label: 'Mis Solicitudes',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
      </svg>
    ),
  },
]

const BOUNTY_PRESETS = [
  { label: 'Cualquier', min: null, max: null },
  { label: '$0 - $10', min: 0, max: 10 },
  { label: '$10 - $25', min: 10, max: 25 },
  { label: '$25 - $50', min: 25, max: 50 },
  { label: '$50+', min: 50, max: null },
]

const DISTANCE_PRESETS = [
  { label: 'Cualquier', value: null },
  { label: '1 km', value: 1 },
  { label: '5 km', value: 5 },
  { label: '10 km', value: 10 },
  { label: '25 km', value: 25 },
]

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function TabSelector({
  selected,
  onChange,
  applicationCount,
}: {
  selected: TaskFilterTab
  onChange: (tab: TaskFilterTab) => void
  applicationCount: number
}) {
  return (
    <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
      {TAB_OPTIONS.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-all ${
            selected === tab.value
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {tab.icon}
          <span className="hidden sm:inline">{tab.label}</span>
          {tab.value === 'my_applications' && applicationCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
              {applicationCount}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

function SearchBar({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="relative">
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Buscar tareas..."
        className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  )
}

function FilterDropdown({
  label,
  options,
  selectedLabel,
  onSelect,
}: {
  label: string
  options: { label: string; value: unknown }[]
  selectedLabel: string
  onSelect: (option: { label: string; value: unknown }) => void
}) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm hover:border-gray-300 transition-colors"
      >
        <span className="text-gray-500">{label}:</span>
        <span className="font-medium text-gray-900">{selectedLabel}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 mt-1 w-40 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
            {options.map((option) => (
              <button
                key={option.label}
                onClick={() => {
                  onSelect(option)
                  setIsOpen(false)
                }}
                className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 ${
                  selectedLabel === option.label ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
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
}

function EmptyState({
  tab,
  hasFilters,
  onClearFilters,
}: {
  tab: TaskFilterTab
  hasFilters: boolean
  onClearFilters: () => void
}) {
  const config = {
    all: {
      icon: (
        <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
      ),
      title: hasFilters ? 'No hay tareas con estos filtros' : 'No hay tareas disponibles',
      description: hasFilters
        ? 'Intenta ajustar los filtros para ver mas resultados'
        : 'Vuelve mas tarde para ver nuevas tareas',
    },
    near_me: {
      icon: (
        <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
          />
        </svg>
      ),
      title: 'No hay tareas cerca de ti',
      description: 'Amplia el radio de busqueda o revisa mas tarde',
    },
    my_applications: {
      icon: (
        <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
      title: 'No tienes solicitudes activas',
      description: 'Explora las tareas disponibles y aplica a las que te interesen',
    },
  }

  const { icon, title, description } = config[tab]

  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
        {icon}
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
      <p className="text-gray-500 mb-4">{description}</p>
      {hasFilters && (
        <button
          onClick={onClearFilters}
          className="px-4 py-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
        >
          Limpiar filtros
        </button>
      )}
    </div>
  )
}

function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">Error al cargar tareas</h3>
      <p className="text-gray-500 mb-4">{error.message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}

function ResultsCount({ count, total }: { count: number; total: number }) {
  if (count === total) {
    return (
      <p className="text-sm text-gray-500">
        {count} tarea{count !== 1 ? 's' : ''} disponible{count !== 1 ? 's' : ''}
      </p>
    )
  }
  return (
    <p className="text-sm text-gray-500">
      Mostrando {count} de {total} tareas
    </p>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function Tasks({
  tasks,
  applications,
  executor,
  loading = false,
  error = null,
  onTaskClick,
  onRefresh,
}: TasksPageProps) {
  const [filters, setFilters] = useState<FilterState>({
    tab: 'all',
    category: null,
    minBounty: null,
    maxBounty: null,
    maxDistance: null,
    searchQuery: '',
  })

  const [showFilters, setShowFilters] = useState(false)

  // Get applied task IDs
  const appliedTaskIds = useMemo(
    () => new Set(applications.map((app) => app.task_id)),
    [applications]
  )

  // Filter tasks based on current filters
  const filteredTasks = useMemo(() => {
    let result = [...tasks]

    // Tab filter
    if (filters.tab === 'my_applications') {
      result = result.filter((task) => appliedTaskIds.has(task.id))
    } else if (filters.tab === 'near_me') {
      // For "near me", we'd need geolocation - for now, filter tasks with location
      result = result.filter((task) => task.location || task.location_hint)

      // Apply distance filter if set
      if (filters.maxDistance && executor?.default_location) {
        // In production, calculate actual distance using Haversine formula
        // For now, just filter by location_radius_km as approximation
        result = result.filter(
          (task) =>
            !task.location_radius_km || task.location_radius_km <= (filters.maxDistance || 100)
        )
      }
    }

    // Category filter
    if (filters.category) {
      result = result.filter((task) => task.category === filters.category)
    }

    // Bounty filter
    if (filters.minBounty !== null) {
      result = result.filter((task) => task.bounty_usd >= (filters.minBounty || 0))
    }
    if (filters.maxBounty !== null) {
      result = result.filter((task) => task.bounty_usd <= (filters.maxBounty || Infinity))
    }

    // Search query
    if (filters.searchQuery.trim()) {
      const query = filters.searchQuery.toLowerCase()
      result = result.filter(
        (task) =>
          task.title.toLowerCase().includes(query) ||
          task.instructions.toLowerCase().includes(query) ||
          task.location_hint?.toLowerCase().includes(query)
      )
    }

    return result
  }, [tasks, applications, filters, appliedTaskIds, executor])

  // Check if any filters are active
  const hasActiveFilters =
    filters.category !== null ||
    filters.minBounty !== null ||
    filters.maxBounty !== null ||
    filters.maxDistance !== null ||
    filters.searchQuery.trim() !== ''

  // Get current bounty preset label
  const currentBountyLabel = useMemo(() => {
    const preset = BOUNTY_PRESETS.find(
      (p) => p.min === filters.minBounty && p.max === filters.maxBounty
    )
    return preset?.label || 'Personalizado'
  }, [filters.minBounty, filters.maxBounty])

  // Get current distance preset label
  const currentDistanceLabel = useMemo(() => {
    const preset = DISTANCE_PRESETS.find((p) => p.value === filters.maxDistance)
    return preset?.label || 'Personalizado'
  }, [filters.maxDistance])

  const clearFilters = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      category: null,
      minBounty: null,
      maxBounty: null,
      maxDistance: null,
      searchQuery: '',
    }))
  }, [])

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Buscar Tareas</h1>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            <svg
              className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Tab Selector */}
      <TabSelector
        selected={filters.tab}
        onChange={(tab) => setFilters((prev) => ({ ...prev, tab }))}
        applicationCount={applications.filter((a) => a.status === 'pending').length}
      />

      {/* Search */}
      <SearchBar
        value={filters.searchQuery}
        onChange={(searchQuery) => setFilters((prev) => ({ ...prev, searchQuery }))}
      />

      {/* Filter Toggle */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          <span>Filtros</span>
          {hasActiveFilters && (
            <span className="w-2 h-2 bg-blue-600 rounded-full" />
          )}
        </button>

        <ResultsCount count={filteredTasks.length} total={tasks.length} />
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-4">
          {/* Category Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Categoria</label>
            <CategoryFilter
              selected={filters.category}
              onChange={(category) => setFilters((prev) => ({ ...prev, category }))}
            />
          </div>

          {/* Bounty and Distance Filters */}
          <div className="flex flex-wrap gap-3">
            <FilterDropdown
              label="Recompensa"
              options={BOUNTY_PRESETS.map((p) => ({ label: p.label, value: p }))}
              selectedLabel={currentBountyLabel}
              onSelect={(option) => {
                const preset = option.value as (typeof BOUNTY_PRESETS)[number]
                setFilters((prev) => ({
                  ...prev,
                  minBounty: preset.min,
                  maxBounty: preset.max,
                }))
              }}
            />

            {filters.tab === 'near_me' && (
              <FilterDropdown
                label="Distancia"
                options={DISTANCE_PRESETS.map((p) => ({ label: p.label, value: p.value }))}
                selectedLabel={currentDistanceLabel}
                onSelect={(option) =>
                  setFilters((prev) => ({
                    ...prev,
                    maxDistance: option.value as number | null,
                  }))
                }
              />
            )}
          </div>

          {/* Clear filters */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Limpiar todos los filtros
            </button>
          )}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={onRefresh} />
      ) : filteredTasks.length === 0 ? (
        <EmptyState
          tab={filters.tab}
          hasFilters={hasActiveFilters}
          onClearFilters={clearFilters}
        />
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((task) => (
            <TaskCard key={task.id} task={task} onClick={() => onTaskClick(task)} />
          ))}
        </div>
      )}
    </div>
  )
}

export default Tasks
