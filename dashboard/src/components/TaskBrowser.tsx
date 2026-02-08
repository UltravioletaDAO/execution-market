/**
 * TaskBrowser - Advanced task browsing with filters
 *
 * Features:
 * - Category filtering
 * - Location-based filtering
 * - Pay range filtering
 * - Skill matching
 * - Sort options
 * - Infinite scroll
 */

import { useState, useCallback, useMemo, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAvailableTasks } from '../hooks/useTasks'
import { TaskCard } from './TaskCard'
import { LocationFilter, type GPSCoordinates } from './LocationFilter'
import type { TaskCategory } from '../types/database'

// Types
interface TaskFilters {
  category: string | null
  minPay: number | null
  maxPay: number | null
  maxDistance: number | null
  location: GPSCoordinates | null
  skills: string[]
  sortBy: 'newest' | 'highest_pay' | 'nearest' | 'deadline'
}

interface TaskBrowserProps {
  executorId?: string
  executorSkills?: string[]
  onTaskSelect: (taskId: string) => void
}

// Categories — must match DB task categories exactly
const TASK_CATEGORIES = [
  { id: 'all', label: 'Todas', icon: '📋' },
  { id: 'physical_presence', label: 'Presencia Fisica', icon: '📍' },
  { id: 'knowledge_access', label: 'Acceso a Info', icon: '📚' },
  { id: 'human_authority', label: 'Autoridad Humana', icon: '📜' },
  { id: 'simple_action', label: 'Accion Simple', icon: '✅' },
  { id: 'digital_physical', label: 'Digital-Fisico', icon: '🔗' },
]

// Pay ranges
const PAY_RANGES = [
  { id: 'any', label: 'Cualquier pago', min: null, max: null },
  { id: 'micro', label: '$0.10 - $1', min: 0.1, max: 1 },
  { id: 'small', label: '$1 - $5', min: 1, max: 5 },
  { id: 'medium', label: '$5 - $20', min: 5, max: 20 },
  { id: 'large', label: '$20+', min: 20, max: null },
]

// Sort options
const SORT_OPTIONS = [
  { id: 'newest', label: 'Mas recientes' },
  { id: 'highest_pay', label: 'Mayor pago' },
  { id: 'nearest', label: 'Mas cercanos' },
  { id: 'deadline', label: 'Por vencer' },
]

export function TaskBrowser({
  executorId: _executorId,
  executorSkills = [],
  onTaskSelect,
}: TaskBrowserProps) {
  const { t } = useTranslation()
  const [filters, setFilters] = useState<TaskFilters>({
    category: null,
    minPay: null,
    maxPay: null,
    maxDistance: 25,
    location: null,
    skills: [],
    sortBy: 'newest',
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [showLocationFilter, setShowLocationFilter] = useState(false)

  // Fetch tasks - note: useAvailableTasks doesn't have pagination yet
  const { tasks, loading, error, refetch } = useAvailableTasks({
    category: (filters.category as TaskCategory) || undefined,
  })

  // Pagination not implemented yet in useTasks
  const hasMore = false
  const loadMore = () => {}

  // Filter and sort tasks
  const filteredTasks = useMemo(() => {
    let result = [...tasks]

    // Filter by search query
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter((task) =>
        task.title?.toLowerCase().includes(q) ||
        task.instructions?.toLowerCase().includes(q)
      )
    }

    // Filter by pay range
    if (filters.minPay !== null) {
      result = result.filter((task) => task.bounty_usd >= filters.minPay!)
    }
    if (filters.maxPay !== null) {
      result = result.filter((task) => task.bounty_usd <= filters.maxPay!)
    }

    // Filter by skills (if executor has skills defined)
    if (filters.skills.length > 0) {
      result = result.filter((task) => {
        const taskSkills = (task.required_roles as string[]) || []
        return filters.skills.some((skill) => taskSkills.includes(skill))
      })
    }

    // Sort
    switch (filters.sortBy) {
      case 'highest_pay':
        result.sort((a, b) => b.bounty_usd - a.bounty_usd)
        break
      case 'nearest':
        // Would need distance calculation from location
        break
      case 'deadline':
        result.sort((a, b) => {
          const deadlineA = new Date(a.deadline || '9999-12-31').getTime()
          const deadlineB = new Date(b.deadline || '9999-12-31').getTime()
          return deadlineA - deadlineB
        })
        break
      case 'newest':
      default:
        result.sort((a, b) => {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        })
    }

    return result
  }, [tasks, filters, searchQuery])

  // Count matching skills for each task
  const getSkillMatch = useCallback((taskSkills: string[]) => {
    if (!executorSkills.length || !taskSkills.length) return null
    const matching = taskSkills.filter((skill) => executorSkills.includes(skill))
    return {
      matching: matching.length,
      total: taskSkills.length,
      percentage: Math.round((matching.length / taskSkills.length) * 100),
    }
  }, [executorSkills])

  // Handle filter changes
  const updateFilter = useCallback(<K extends keyof TaskFilters>(
    key: K,
    value: TaskFilters[K]
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }, [])

  // Handle category change
  const handleCategoryChange = useCallback((categoryId: string) => {
    updateFilter('category', categoryId === 'all' ? null : categoryId)
  }, [updateFilter])

  // Handle pay range change
  const handlePayRangeChange = useCallback((rangeId: string) => {
    const range = PAY_RANGES.find((r) => r.id === rangeId)
    if (range) {
      updateFilter('minPay', range.min)
      updateFilter('maxPay', range.max)
    }
  }, [updateFilter])

  // Handle location change
  const handleLocationChange = useCallback((location: GPSCoordinates | null) => {
    updateFilter('location', location)
  }, [updateFilter])

  // Handle distance change
  const handleDistanceChange = useCallback((distance: number) => {
    updateFilter('maxDistance', distance)
  }, [updateFilter])

  // Reset filters
  const resetFilters = useCallback(() => {
    setFilters({
      category: null,
      minPay: null,
      maxPay: null,
      maxDistance: 25,
      location: null,
      skills: [],
      sortBy: 'newest',
    })
  }, [])

  // Active filter count
  const activeFilterCount = useMemo(() => {
    let count = 0
    if (filters.category) count++
    if (filters.minPay !== null || filters.maxPay !== null) count++
    if (filters.skills.length > 0) count++
    if (filters.location) count++
    return count
  }, [filters])

  // Pull to refresh
  const handleRefresh = useCallback(async () => {
    await refetch()
  }, [refetch])

  // Infinite scroll
  useEffect(() => {
    const handleScroll = () => {
      if (
        window.innerHeight + document.documentElement.scrollTop >=
        document.documentElement.offsetHeight - 1000
      ) {
        if (hasMore && !loading) {
          loadMore()
        }
      }
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [hasMore, loading, loadMore])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 z-30">
        {/* Search and filter bar */}
        <div className="px-4 py-3 flex items-center gap-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('tasks.search', 'Buscar tareas...')}
              className="w-full pl-10 pr-4 py-2.5 bg-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
            />
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          {/* Filter button */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`relative p-2.5 rounded-lg transition-colors ${
              showFilters || activeFilterCount > 0
                ? 'bg-blue-100 text-blue-600'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            {activeFilterCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-blue-600 text-white text-xs font-medium rounded-full flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>

          {/* Location button */}
          <button
            onClick={() => setShowLocationFilter(!showLocationFilter)}
            className={`p-2.5 rounded-lg transition-colors ${
              filters.location
                ? 'bg-green-100 text-green-600'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>

        {/* Category tabs */}
        <div className="px-4 pb-3 overflow-x-auto scrollbar-hide">
          <div className="flex gap-2">
            {TASK_CATEGORIES.map((category) => (
              <button
                key={category.id}
                onClick={() => handleCategoryChange(category.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
                  (filters.category === category.id) || (category.id === 'all' && !filters.category)
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span>{category.icon}</span>
                <span>{t(`categories.${category.id}`, category.label)}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Expanded filters */}
        {showFilters && (
          <div className="px-4 pb-4 pt-2 border-t border-gray-100 animate-slide-down">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-900">
                {t('filters.title', 'Filtros')}
              </span>
              <button
                onClick={resetFilters}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                {t('filters.reset', 'Limpiar filtros')}
              </button>
            </div>

            {/* Pay range */}
            <div className="mb-4">
              <label className="text-xs text-gray-500 uppercase tracking-wider">
                {t('filters.payRange', 'Rango de pago')}
              </label>
              <div className="flex flex-wrap gap-2 mt-2">
                {PAY_RANGES.map((range) => {
                  const isActive = filters.minPay === range.min && filters.maxPay === range.max
                  return (
                    <button
                      key={range.id}
                      onClick={() => handlePayRangeChange(range.id)}
                      className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                        isActive
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {t(`payRanges.${range.id}`, range.label)}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Sort */}
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">
                {t('filters.sortBy', 'Ordenar por')}
              </label>
              <div className="flex flex-wrap gap-2 mt-2">
                {SORT_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => updateFilter('sortBy', option.id as TaskFilters['sortBy'])}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      filters.sortBy === option.id
                        ? 'bg-gray-800 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {t(`sortOptions.${option.id}`, option.label)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Location filter */}
        {showLocationFilter && (
          <div className="px-4 pb-4 pt-2 border-t border-gray-100 animate-slide-down">
            <LocationFilter
              maxDistance={100}
              initialDistance={filters.maxDistance || 25}
              onDistanceChange={handleDistanceChange}
              onLocationChange={handleLocationChange}
              showLocationButton
            />
          </div>
        )}
      </div>

      {/* Results info */}
      <div className="px-4 py-3 flex items-center justify-between">
        <span className="text-sm text-gray-500">
          {filteredTasks.length} {t('tasks.found', 'tareas encontradas')}
        </span>
        {filters.location && (
          <span className="text-sm text-gray-500">
            {t('tasks.within', 'Dentro de')} {filters.maxDistance} km
          </span>
        )}
      </div>

      {/* Task list */}
      <div className="px-4 pb-4 space-y-3">
        {loading && filteredTasks.length === 0 ? (
          // Loading skeletons
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-white rounded-lg p-4 border border-gray-200">
              <div className="skeleton h-5 w-3/4 rounded mb-2" />
              <div className="skeleton h-4 w-1/2 rounded mb-3" />
              <div className="flex gap-2">
                <div className="skeleton h-6 w-16 rounded-full" />
                <div className="skeleton h-6 w-20 rounded-full" />
              </div>
            </div>
          ))
        ) : error ? (
          // Error state
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <svg className="w-12 h-12 text-red-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-red-600 font-medium mb-2">
              {t('tasks.error', 'Error al cargar tareas')}
            </p>
            <button
              onClick={handleRefresh}
              className="text-red-600 hover:text-red-700 text-sm"
            >
              {t('common.retry', 'Reintentar')}
            </button>
          </div>
        ) : filteredTasks.length === 0 ? (
          // Empty state
          <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
            <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-gray-600 font-medium mb-2">
              {t('tasks.empty', 'No hay tareas disponibles')}
            </p>
            <p className="text-sm text-gray-500 mb-4">
              {t('tasks.emptyHint', 'Intenta cambiar los filtros o revisa mas tarde')}
            </p>
            <button
              onClick={resetFilters}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              {t('filters.reset', 'Limpiar filtros')}
            </button>
          </div>
        ) : (
          // Task cards
          <>
            {filteredTasks.map((task) => {
              const skillMatch = getSkillMatch((task.required_roles as string[]) || [])
              return (
                <div key={task.id} className="relative">
                  <TaskCard
                    task={task}
                    onClick={() => onTaskSelect(task.id)}
                  />
                  {/* Skill match indicator */}
                  {skillMatch && skillMatch.percentage >= 50 && (
                    <div className="absolute top-2 right-2 px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                      {skillMatch.percentage}% {t('tasks.match', 'compatible')}
                    </div>
                  )}
                </div>
              )
            })}

            {/* Load more indicator */}
            {hasMore && (
              <div className="py-4 text-center">
                {loading ? (
                  <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                ) : (
                  <button
                    onClick={loadMore}
                    className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                  >
                    {t('tasks.loadMore', 'Cargar mas')}
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default TaskBrowser
