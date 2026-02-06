// Execution Market: Profile Page (NOW-029)
// Comprehensive worker profile with reputation, earnings, task history, and settings
// Uses Bayesian score display, task history filters, earnings summary, and skill selector

import { useState, useCallback, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { Executor, TaskCategory } from '../types/database'
import type { EarningsData, ReputationData, TaskHistoryItem } from '../hooks/useProfile'
import { useEarnings, useReputation, useTaskHistory, useWithdrawal } from '../hooks/useProfile'
import { useIdentity } from '../hooks/useIdentity'
import { SkillSelector } from '../components/SkillSelector'

// --------------------------------------------------------------------------
// Types & Interfaces
// --------------------------------------------------------------------------

interface ProfilePageProps {
  executor: Executor
  onBack?: () => void
  onLogout?: () => void
}

interface NotificationPreferences {
  newTasks: boolean
  taskUpdates: boolean
  payments: boolean
  disputes: boolean
}

interface TaskHistoryFilter {
  status: 'all' | 'approved' | 'rejected' | 'pending'
  category: TaskCategory | 'all'
  dateRange: 'all' | 'week' | 'month' | '3months'
}

// --------------------------------------------------------------------------
// Constants
// --------------------------------------------------------------------------

const PAYMENT_TOKENS = [
  { value: 'USDC', label: 'USDC', icon: 'usdc' },
  { value: 'USDT', label: 'USDT', icon: 'usdt' },
  { value: 'DAI', label: 'DAI', icon: 'dai' },
]

const CATEGORY_LABELS: Record<TaskCategory | 'all', string> = {
  all: 'Todas',
  physical_presence: 'Presencia Fisica',
  knowledge_access: 'Acceso a Conocimiento',
  human_authority: 'Autoridad Humana',
  simple_action: 'Accion Simple',
  digital_physical: 'Digital-Fisico',
}

const DATE_RANGE_LABELS: Record<TaskHistoryFilter['dateRange'], string> = {
  all: 'Todo el tiempo',
  week: 'Ultima semana',
  month: 'Ultimo mes',
  '3months': 'Ultimos 3 meses',
}

// --------------------------------------------------------------------------
// Helper Functions
// --------------------------------------------------------------------------

function shortenAddress(address: string): string {
  if (!address) return ''
  return `${address.slice(0, 6)}...${address.slice(-4)}`
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('es-MX', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Hoy'
  if (diffDays === 1) return 'Ayer'
  if (diffDays < 7) return `Hace ${diffDays} dias`
  if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`
  return formatDate(dateStr)
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-500'
  if (score >= 60) return 'text-blue-500'
  if (score >= 40) return 'text-amber-500'
  return 'text-red-500'
}

function getScoreBgColor(score: number): string {
  if (score >= 80) return 'bg-green-500'
  if (score >= 60) return 'bg-blue-500'
  if (score >= 40) return 'bg-amber-500'
  return 'bg-red-500'
}

function getReputationTier(score: number): { name: string; nameEs: string; color: string; bgColor: string } {
  if (score >= 90) return { name: 'Expert', nameEs: 'Experto', color: 'text-purple-600', bgColor: 'bg-purple-100' }
  if (score >= 75) return { name: 'Trusted', nameEs: 'Confiable', color: 'text-blue-600', bgColor: 'bg-blue-100' }
  if (score >= 60) return { name: 'Reliable', nameEs: 'Responsable', color: 'text-green-600', bgColor: 'bg-green-100' }
  if (score >= 40) return { name: 'Standard', nameEs: 'Estandar', color: 'text-gray-600', bgColor: 'bg-gray-100' }
  return { name: 'New', nameEs: 'Nuevo', color: 'text-amber-600', bgColor: 'bg-amber-100' }
}

// --------------------------------------------------------------------------
// Sub-Components
// --------------------------------------------------------------------------

// Bayesian Score Gauge Component
function BayesianScoreGauge({ score, size = 'lg' }: { score: number; size?: 'sm' | 'md' | 'lg' }) {
  const { t } = useTranslation()
  const tier = getReputationTier(score)

  const dimensions = {
    sm: { width: 80, strokeWidth: 8, fontSize: 'text-xl' },
    md: { width: 100, strokeWidth: 10, fontSize: 'text-2xl' },
    lg: { width: 128, strokeWidth: 12, fontSize: 'text-3xl' },
  }

  const { width, strokeWidth, fontSize } = dimensions[size]
  const radius = (width - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width, height: width }}>
        {/* Background circle */}
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="none"
            className="text-gray-100"
          />
          {/* Progress circle */}
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="none"
            strokeDasharray={`${progress} ${circumference}`}
            strokeLinecap="round"
            className={getScoreColor(score)}
            style={{ transition: 'stroke-dasharray 0.5s ease-out' }}
          />
        </svg>
        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${fontSize} font-bold text-gray-900`}>{score}</span>
          <span className="text-xs text-gray-500">/ 100</span>
        </div>
      </div>
      {/* Tier badge */}
      <span className={`mt-2 px-3 py-1 rounded-full text-xs font-medium ${tier.bgColor} ${tier.color}`}>
        {t(`profile.tier.${tier.name.toLowerCase()}`, tier.nameEs)}
      </span>
    </div>
  )
}

// Status Badge Component
function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()

  const configs: Record<string, { bg: string; text: string; labelKey: string; labelDefault: string }> = {
    approved: { bg: 'bg-green-100', text: 'text-green-700', labelKey: 'status.approved', labelDefault: 'Aprobada' },
    rejected: { bg: 'bg-red-100', text: 'text-red-700', labelKey: 'status.rejected', labelDefault: 'Rechazada' },
    pending: { bg: 'bg-amber-100', text: 'text-amber-700', labelKey: 'status.pending', labelDefault: 'Pendiente' },
  }

  const config = configs[status] || configs.pending

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      {t(config.labelKey, config.labelDefault)}
    </span>
  )
}

// Category icons
const CATEGORY_ICONS: Record<string, string> = {
  physical_presence: '📍',
  knowledge_access: '📚',
  human_authority: '✍️',
  simple_action: '✅',
  digital_physical: '🔗',
}

// --------------------------------------------------------------------------
// Reputation Card Section
// --------------------------------------------------------------------------

function ReputationSection({
  reputation,
  loading,
  memberSince
}: {
  reputation: ReputationData | null
  loading: boolean
  memberSince: string
}) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="h-5 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="flex justify-center mb-4">
            <div className="w-32 h-32 bg-gray-200 rounded-full"></div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        </div>
      </section>
    )
  }

  const score = reputation?.current_score || 50
  const approvalRate = reputation?.approval_rate || 0

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900">
          {t('profile.reputation', 'Reputacion')}
        </h2>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span>{t('profile.memberSince', 'Miembro desde')} {formatDate(memberSince)}</span>
        </div>
      </div>

      {/* Bayesian Score Gauge */}
      <div className="flex justify-center mb-6">
        <BayesianScoreGauge score={score} size="lg" />
      </div>

      {/* Bayesian explanation */}
      <div className="bg-gray-50 rounded-lg p-3 mb-6">
        <p className="text-xs text-gray-600 text-center">
          {t('profile.bayesianExplanation', 'El puntaje bayesiano combina tu historial con el promedio de la comunidad para una evaluacion justa, incluso con pocas tareas.')}
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-gray-900">{reputation?.total_tasks || 0}</div>
          <div className="text-xs text-gray-500">{t('profile.totalTasks', 'Total')}</div>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-green-600">{reputation?.approved_tasks || 0}</div>
          <div className="text-xs text-gray-500">{t('profile.approved', 'Aprobadas')}</div>
        </div>
        <div className="bg-red-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-red-600">{reputation?.rejected_tasks || 0}</div>
          <div className="text-xs text-gray-500">{t('profile.rejected', 'Rechazadas')}</div>
        </div>
        <div className="bg-amber-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-amber-600">{reputation?.disputed_tasks || 0}</div>
          <div className="text-xs text-gray-500">{t('profile.disputed', 'Disputas')}</div>
        </div>
      </div>

      {/* Approval rate bar */}
      <div>
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-600">{t('profile.approvalRate', 'Tasa de Aprobacion')}</span>
          <span className="font-semibold text-gray-900">{approvalRate.toFixed(1)}%</span>
        </div>
        <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${getScoreBgColor(approvalRate)}`}
            style={{ width: `${approvalRate}%` }}
          />
        </div>
      </div>

      {/* Disputes warning */}
      {(reputation?.disputed_tasks || 0) > 0 && (
        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
          <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div className="text-sm">
            <span className="font-medium text-amber-800">
              {reputation?.disputed_tasks} {t('profile.openDisputes', 'disputa(s) abierta(s)')}
            </span>
            <p className="text-amber-700 text-xs mt-0.5">
              {t('profile.disputeWarning', 'Las disputas pueden afectar tu puntaje de reputacion')}
            </p>
          </div>
        </div>
      )}
    </section>
  )
}

// --------------------------------------------------------------------------
// Earnings Summary Section
// --------------------------------------------------------------------------

function EarningsSection({
  earnings,
  loading,
  onWithdraw,
}: {
  earnings: EarningsData | null
  loading: boolean
  onWithdraw: () => void
}) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <section className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-6 text-white">
        <div className="animate-pulse">
          <div className="h-4 bg-blue-400/50 rounded w-1/3 mb-4"></div>
          <div className="h-10 bg-blue-400/50 rounded w-1/2 mb-6"></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="h-16 bg-blue-400/50 rounded"></div>
            <div className="h-16 bg-blue-400/50 rounded"></div>
          </div>
        </div>
      </section>
    )
  }

  const balance = earnings?.balance_usdc || 0
  const totalEarned = earnings?.total_earned_usdc || 0
  const pending = earnings?.pending_earnings_usdc || 0
  const thisMonth = earnings?.this_month_usdc || 0
  const lastMonth = earnings?.last_month_usdc || 0

  // Calculate month-over-month change
  const monthChange = lastMonth > 0
    ? ((thisMonth - lastMonth) / lastMonth) * 100
    : thisMonth > 0 ? 100 : 0

  return (
    <section className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl shadow-lg p-6 text-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-blue-100 text-sm font-medium">
          {t('profile.availableBalance', 'Saldo Disponible')}
        </h2>
        <div className="flex items-center gap-1 text-blue-200">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          <span className="text-xs">USDC</span>
        </div>
      </div>

      {/* Balance */}
      <div className="mb-6">
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-bold">{formatCurrency(balance)}</span>
          {pending > 0 && (
            <span className="text-blue-200 text-sm">
              +{formatCurrency(pending)} {t('profile.pending', 'pendiente')}
            </span>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-blue-200 text-xs mb-1">
            {t('profile.totalEarned', 'Total Ganado')}
          </div>
          <div className="text-lg font-semibold">{formatCurrency(totalEarned)}</div>
        </div>
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-blue-200 text-xs mb-1">
            {t('profile.thisMonth', 'Este Mes')}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold">{formatCurrency(thisMonth)}</span>
            {monthChange !== 0 && (
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                monthChange > 0
                  ? 'bg-green-400/20 text-green-200'
                  : 'bg-red-400/20 text-red-200'
              }`}>
                {monthChange > 0 ? '+' : ''}{monthChange.toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Withdraw button */}
      <button
        onClick={onWithdraw}
        disabled={balance <= 0}
        className={`w-full py-3 rounded-lg font-medium transition-all ${
          balance > 0
            ? 'bg-white text-blue-600 hover:bg-blue-50 active:scale-[0.98]'
            : 'bg-white/20 text-blue-200 cursor-not-allowed'
        }`}
      >
        {t('profile.withdraw', 'Retirar Fondos')}
      </button>
    </section>
  )
}

// --------------------------------------------------------------------------
// Task History Section with Filters
// --------------------------------------------------------------------------

function TaskHistorySection({
  history,
  loading,
  hasMore,
  onLoadMore,
  filter,
  onFilterChange,
}: {
  history: TaskHistoryItem[]
  loading: boolean
  hasMore: boolean
  onLoadMore: () => void
  filter: TaskHistoryFilter
  onFilterChange: (filter: TaskHistoryFilter) => void
}) {
  const { t } = useTranslation()
  const [showFilters, setShowFilters] = useState(false)

  // Filter the history based on current filters
  const filteredHistory = useMemo(() => {
    return history.filter(item => {
      // Status filter
      if (filter.status !== 'all' && item.status !== filter.status) return false

      // Category filter
      if (filter.category !== 'all' && item.task_category !== filter.category) return false

      // Date range filter
      if (filter.dateRange !== 'all') {
        const submittedDate = new Date(item.submitted_at)
        const now = new Date()
        const diffDays = Math.floor((now.getTime() - submittedDate.getTime()) / (1000 * 60 * 60 * 24))

        if (filter.dateRange === 'week' && diffDays > 7) return false
        if (filter.dateRange === 'month' && diffDays > 30) return false
        if (filter.dateRange === '3months' && diffDays > 90) return false
      }

      return true
    })
  }, [history, filter])

  const activeFiltersCount = (filter.status !== 'all' ? 1 : 0)
    + (filter.category !== 'all' ? 1 : 0)
    + (filter.dateRange !== 'all' ? 1 : 0)

  if (loading && history.length === 0) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="h-5 bg-gray-200 rounded w-1/3 animate-pulse"></div>
        </div>
        <div className="p-6">
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex gap-4">
                <div className="w-10 h-10 bg-gray-200 rounded-lg"></div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded w-2/3 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/3"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header with filter toggle */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          {t('profile.taskHistory', 'Historial de Tareas')}
        </h2>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            showFilters || activeFiltersCount > 0
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          {t('common.filters', 'Filtros')}
          {activeFiltersCount > 0 && (
            <span className="bg-blue-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {activeFiltersCount}
            </span>
          )}
        </button>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-100 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Status filter */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">
                {t('filter.status', 'Estado')}
              </label>
              <select
                value={filter.status}
                onChange={(e) => onFilterChange({ ...filter, status: e.target.value as TaskHistoryFilter['status'] })}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">{t('filter.allStatuses', 'Todos los estados')}</option>
                <option value="approved">{t('status.approved', 'Aprobadas')}</option>
                <option value="rejected">{t('status.rejected', 'Rechazadas')}</option>
                <option value="pending">{t('status.pending', 'Pendientes')}</option>
              </select>
            </div>

            {/* Category filter */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">
                {t('filter.category', 'Categoria')}
              </label>
              <select
                value={filter.category}
                onChange={(e) => onFilterChange({ ...filter, category: e.target.value as TaskHistoryFilter['category'] })}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            {/* Date range filter */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">
                {t('filter.dateRange', 'Periodo')}
              </label>
              <select
                value={filter.dateRange}
                onChange={(e) => onFilterChange({ ...filter, dateRange: e.target.value as TaskHistoryFilter['dateRange'] })}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {Object.entries(DATE_RANGE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Clear filters */}
          {activeFiltersCount > 0 && (
            <button
              onClick={() => onFilterChange({ status: 'all', category: 'all', dateRange: 'all' })}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {t('filter.clearAll', 'Limpiar filtros')}
            </button>
          )}
        </div>
      )}

      {/* History list */}
      {filteredHistory.length === 0 ? (
        <div className="p-8 text-center">
          <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <p className="text-gray-600 font-medium">
            {activeFiltersCount > 0
              ? t('profile.noFilteredHistory', 'No hay tareas con estos filtros')
              : t('profile.noHistory', 'Aun no has completado ninguna tarea')
            }
          </p>
          <p className="text-gray-400 text-sm mt-1">
            {activeFiltersCount > 0
              ? t('profile.tryDifferentFilters', 'Prueba con otros filtros')
              : t('profile.startEarning', 'Acepta una tarea para empezar a ganar')
            }
          </p>
        </div>
      ) : (
        <div className="divide-y divide-gray-50">
          {filteredHistory.map(item => (
            <div key={item.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
              <div className="flex items-start gap-3">
                {/* Category icon */}
                <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center text-lg flex-shrink-0">
                  {CATEGORY_ICONS[item.task_category] || '📋'}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-gray-900 font-medium text-sm truncate">
                      {item.task_title}
                    </h4>
                    <StatusBadge status={item.status} />
                  </div>

                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-gray-500 text-xs">
                      {formatRelativeDate(item.submitted_at)}
                    </span>

                    {/* Payment amount for approved */}
                    {item.status === 'approved' && (
                      <span className="text-green-600 text-xs font-semibold">
                        +{formatCurrency(item.payment_amount || item.bounty_usd)}
                      </span>
                    )}

                    {/* Bounty for pending/rejected */}
                    {item.status !== 'approved' && (
                      <span className="text-gray-400 text-xs">
                        {formatCurrency(item.bounty_usd)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Load more button */}
      {hasMore && filteredHistory.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-100">
          <button
            onClick={onLoadMore}
            disabled={loading}
            className="w-full py-2.5 text-blue-600 text-sm font-medium hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {t('common.loading', 'Cargando...')}
              </span>
            ) : (
              t('common.loadMore', 'Cargar mas')
            )}
          </button>
        </div>
      )}
    </section>
  )
}

// --------------------------------------------------------------------------
// Settings Section
// --------------------------------------------------------------------------

function SettingsSection({
  displayName,
  preferredToken,
  notifications,
  selectedSkills,
  isSaving,
  saveSuccess,
  onDisplayNameChange,
  onPreferredTokenChange,
  onNotificationsChange,
  onSkillsChange,
  onSave,
}: {
  displayName: string
  preferredToken: string
  notifications: NotificationPreferences
  selectedSkills: string[]
  isSaving: boolean
  saveSuccess: boolean
  onDisplayNameChange: (name: string) => void
  onPreferredTokenChange: (token: string) => void
  onNotificationsChange: (prefs: NotificationPreferences) => void
  onSkillsChange: (skills: string[]) => void
  onSave: () => void
}) {
  const { t } = useTranslation()
  const [showSkillSelector, setShowSkillSelector] = useState(false)

  const toggleNotification = (key: keyof NotificationPreferences) => {
    onNotificationsChange({ ...notifications, [key]: !notifications[key] })
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">
          {t('profile.settings', 'Configuracion')}
        </h2>
      </div>

      <div className="p-6 space-y-6">
        {/* Display Name */}
        <div>
          <label htmlFor="displayName" className="block text-sm font-medium text-gray-700 mb-2">
            {t('profile.displayName', 'Nombre Visible')}
          </label>
          <input
            id="displayName"
            type="text"
            value={displayName}
            onChange={(e) => onDisplayNameChange(e.target.value)}
            placeholder={t('profile.displayNamePlaceholder', 'Tu nombre o apodo')}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>

        {/* Preferred Payment Token */}
        <div>
          <label htmlFor="paymentToken" className="block text-sm font-medium text-gray-700 mb-2">
            {t('profile.preferredToken', 'Token de Pago Preferido')}
          </label>
          <select
            id="paymentToken"
            value={preferredToken}
            onChange={(e) => onPreferredTokenChange(e.target.value)}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white transition-all"
          >
            {PAYMENT_TOKENS.map((token) => (
              <option key={token.value} value={token.value}>
                {token.label}
              </option>
            ))}
          </select>
        </div>

        {/* Skills/Categories */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              {t('profile.skills', 'Habilidades')}
            </label>
            <button
              onClick={() => setShowSkillSelector(!showSkillSelector)}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {showSkillSelector
                ? t('common.hide', 'Ocultar')
                : t('common.edit', 'Editar')
              }
            </button>
          </div>

          {/* Selected skills preview */}
          {selectedSkills.length > 0 && !showSkillSelector && (
            <div className="flex flex-wrap gap-2">
              {selectedSkills.slice(0, 6).map(skillId => (
                <span
                  key={skillId}
                  className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                >
                  {skillId.replace(/_/g, ' ')}
                </span>
              ))}
              {selectedSkills.length > 6 && (
                <span className="px-3 py-1 bg-gray-100 text-gray-600 text-sm rounded-full">
                  +{selectedSkills.length - 6} {t('common.more', 'mas')}
                </span>
              )}
            </div>
          )}

          {/* Skills selector */}
          {showSkillSelector && (
            <div className="mt-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <SkillSelector
                selectedSkills={selectedSkills}
                onSkillsChange={onSkillsChange}
                maxSkills={15}
                showCategories={true}
              />
            </div>
          )}

          {selectedSkills.length === 0 && !showSkillSelector && (
            <p className="text-sm text-gray-500">
              {t('profile.noSkills', 'No has seleccionado habilidades. Agregalas para recibir tareas relevantes.')}
            </p>
          )}
        </div>

        {/* Notification Preferences */}
        <div>
          <span className="block text-sm font-medium text-gray-700 mb-3">
            {t('profile.notifications', 'Notificaciones')}
          </span>
          <div className="space-y-3">
            {/* New Tasks */}
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-600">
                {t('profile.notifyNewTasks', 'Nuevas tareas disponibles')}
              </span>
              <button
                role="switch"
                aria-checked={notifications.newTasks}
                onClick={() => toggleNotification('newTasks')}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  notifications.newTasks ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    notifications.newTasks ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </label>

            {/* Task Updates */}
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-600">
                {t('profile.notifyTaskUpdates', 'Actualizaciones de tareas')}
              </span>
              <button
                role="switch"
                aria-checked={notifications.taskUpdates}
                onClick={() => toggleNotification('taskUpdates')}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  notifications.taskUpdates ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    notifications.taskUpdates ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </label>

            {/* Payments */}
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-600">
                {t('profile.notifyPayments', 'Pagos recibidos')}
              </span>
              <button
                role="switch"
                aria-checked={notifications.payments}
                onClick={() => toggleNotification('payments')}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  notifications.payments ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    notifications.payments ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </label>

            {/* Disputes */}
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-600">
                {t('profile.notifyDisputes', 'Actualizaciones de disputas')}
              </span>
              <button
                role="switch"
                aria-checked={notifications.disputes}
                onClick={() => toggleNotification('disputes')}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  notifications.disputes ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    notifications.disputes ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </label>
          </div>
        </div>

        {/* Save Button */}
        <button
          onClick={onSave}
          disabled={isSaving}
          className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {isSaving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              {t('common.saving', 'Guardando...')}
            </>
          ) : saveSuccess ? (
            <>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              {t('common.saved', 'Guardado')}
            </>
          ) : (
            t('common.saveChanges', 'Guardar Cambios')
          )}
        </button>
      </div>
    </section>
  )
}

// --------------------------------------------------------------------------
// Withdrawal Modal
// --------------------------------------------------------------------------

function WithdrawalModal({
  isOpen,
  onClose,
  availableBalance,
  executorId,
  walletAddress,
}: {
  isOpen: boolean
  onClose: () => void
  availableBalance: number
  executorId: string
  walletAddress: string
}) {
  const { t } = useTranslation()
  const [amount, setAmount] = useState('')
  const [destination, setDestination] = useState(walletAddress)
  const { withdraw, loading, error, success, reset } = useWithdrawal(executorId)

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => {
        onClose()
        reset()
        setAmount('')
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [success, onClose, reset])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const amountNum = parseFloat(amount)
    if (amountNum > 0 && amountNum <= availableBalance) {
      await withdraw(amountNum, destination)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {t('profile.withdrawFunds', 'Retirar Fondos')}
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {success ? (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">
              {t('profile.withdrawalSuccess', 'Retiro Exitoso')}
            </h4>
            <p className="text-gray-500 text-sm">
              {t('profile.withdrawalProcessing', 'Tu retiro esta siendo procesado')}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Available balance */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-sm text-gray-600">
                {t('profile.availableForWithdrawal', 'Disponible para retiro')}
              </div>
              <div className="text-xl font-bold text-gray-900">
                {formatCurrency(availableBalance)}
              </div>
            </div>

            {/* Amount input */}
            <div>
              <label htmlFor="withdrawAmount" className="block text-sm font-medium text-gray-700 mb-2">
                {t('profile.withdrawAmount', 'Cantidad a retirar (USDC)')}
              </label>
              <input
                id="withdrawAmount"
                type="number"
                step="0.01"
                min="0.01"
                max={availableBalance}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <button
                type="button"
                onClick={() => setAmount(availableBalance.toString())}
                className="mt-1 text-sm text-blue-600 hover:text-blue-700"
              >
                {t('profile.withdrawMax', 'Retirar todo')}
              </button>
            </div>

            {/* Destination address */}
            <div>
              <label htmlFor="withdrawDestination" className="block text-sm font-medium text-gray-700 mb-2">
                {t('profile.destinationAddress', 'Direccion de destino')}
              </label>
              <input
                id="withdrawDestination"
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="0x..."
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                required
              />
            </div>

            {/* Error message */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error.message}
              </div>
            )}

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading || !amount || parseFloat(amount) <= 0 || parseFloat(amount) > availableBalance}
              className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {t('common.processing', 'Procesando...')}
                </>
              ) : (
                t('profile.confirmWithdrawal', 'Confirmar Retiro')
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------
// Identity Badge Section (ERC-8004)
// --------------------------------------------------------------------------

function IdentitySection({ executorId }: { executorId: string }) {
  const { t } = useTranslation()
  const { identity, loading, isRegistered, agentId, error } = useIdentity(executorId)

  if (loading) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center gap-3 animate-pulse">
          <div className="w-10 h-10 bg-gray-200 rounded-full" />
          <div className="flex-1">
            <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
          </div>
        </div>
      </section>
    )
  }

  // Service unavailable or unloaded -- hide section silently
  if (!identity && !error) {
    return null
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div
          className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
            isRegistered
              ? 'bg-green-100 text-green-600'
              : 'bg-gray-100 text-gray-400'
          }`}
        >
          {isRegistered ? (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900">
              {t('profile.identity', 'Identidad On-Chain')}
            </h3>
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                isRegistered
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              {isRegistered
                ? t('profile.identityRegistered', 'Verificado')
                : t('profile.identityNotRegistered', 'No registrado')}
            </span>
          </div>
          {isRegistered && agentId ? (
            <p className="text-xs text-gray-500 mt-0.5">
              ERC-8004 Agent #{agentId} &middot; {identity?.network || 'Base'}
            </p>
          ) : (
            <p className="text-xs text-gray-500 mt-0.5">
              {t(
                'profile.identityHint',
                'Registra tu identidad en Base para mayor confianza',
              )}
            </p>
          )}
        </div>

        {/* Network badge */}
        {isRegistered && (
          <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded-full">
            <div className="w-2 h-2 bg-blue-500 rounded-full" />
            <span className="text-xs font-medium text-blue-700">Base</span>
          </div>
        )}
      </div>

      {/* Error display */}
      {error && (
        <p className="mt-2 text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">
          {error}
        </p>
      )}
    </section>
  )
}

// --------------------------------------------------------------------------
// Main Profile Page Component
// --------------------------------------------------------------------------

export function Profile({ executor, onBack, onLogout }: ProfilePageProps) {
  const { t } = useTranslation()

  // Data hooks
  const { earnings, loading: earningsLoading, refetch: refetchEarnings } = useEarnings(executor.id)
  const { reputation, loading: reputationLoading } = useReputation(executor.id)
  const { history, loading: historyLoading, hasMore, loadMore } = useTaskHistory(executor.id, 10)

  // Local state for settings
  const [displayName, setDisplayName] = useState(executor.display_name || '')
  const [preferredToken, setPreferredToken] = useState('USDC')
  const [notifications, setNotifications] = useState<NotificationPreferences>({
    newTasks: true,
    taskUpdates: true,
    payments: true,
    disputes: true,
  })
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Task history filter state
  const [historyFilter, setHistoryFilter] = useState<TaskHistoryFilter>({
    status: 'all',
    category: 'all',
    dateRange: 'all',
  })

  // Withdrawal modal state
  const [showWithdrawalModal, setShowWithdrawalModal] = useState(false)

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('em_preferred_token')
    if (savedToken) setPreferredToken(savedToken)

    const savedNotifications = localStorage.getItem('em_notifications')
    if (savedNotifications) {
      try {
        setNotifications(JSON.parse(savedNotifications))
      } catch (e) {
        console.error('Failed to parse notifications:', e)
      }
    }

    const savedSkills = localStorage.getItem('em_skills')
    if (savedSkills) {
      try {
        setSelectedSkills(JSON.parse(savedSkills))
      } catch (e) {
        console.error('Failed to parse skills:', e)
      }
    }
  }, [])

  // Save settings handler
  const handleSaveSettings = useCallback(async () => {
    setIsSaving(true)
    setSaveSuccess(false)

    try {
      // Save to localStorage
      localStorage.setItem('em_preferred_token', preferredToken)
      localStorage.setItem('em_notifications', JSON.stringify(notifications))
      localStorage.setItem('em_skills', JSON.stringify(selectedSkills))

      // In production, also save to API
      // await updateExecutorSettings(executor.id, { displayName, preferredToken, notifications, skills: selectedSkills })

      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500))

      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2000)
    } catch (err) {
      console.error('Error saving settings:', err)
    } finally {
      setIsSaving(false)
    }
  }, [preferredToken, notifications, selectedSkills])

  // Copy wallet address
  const copyWalletAddress = useCallback(() => {
    navigator.clipboard.writeText(executor.wallet_address)
  }, [executor.wallet_address])

  // Handle withdrawal modal
  const handleWithdrawalClose = useCallback(() => {
    setShowWithdrawalModal(false)
    refetchEarnings()
  }, [refetchEarnings])

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-8">
      {/* Navigation */}
      <div className="flex items-center justify-between">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="text-sm font-medium">{t('common.back', 'Volver')}</span>
          </button>
        )}
        {onLogout && (
          <button
            onClick={onLogout}
            className="text-sm text-red-600 hover:text-red-700 font-medium"
          >
            {t('common.logout', 'Cerrar Sesion')}
          </button>
        )}
      </div>

      {/* Profile Header */}
      <section className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-4">
          {/* Avatar */}
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white text-2xl font-bold shadow-lg flex-shrink-0">
            {executor.avatar_url ? (
              <img
                src={executor.avatar_url}
                alt={executor.display_name || 'Usuario'}
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              (executor.display_name || 'U')[0].toUpperCase()
            )}
          </div>

          {/* User info */}
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-gray-900 truncate">
              {executor.display_name || t('profile.anonymous', 'Usuario Anonimo')}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <code className="text-sm font-mono text-gray-500 bg-gray-50 px-2 py-0.5 rounded">
                {shortenAddress(executor.wallet_address)}
              </code>
              <button
                onClick={copyWalletAddress}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title={t('common.copyAddress', 'Copiar direccion')}
              >
                <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            {executor.location_city && (
              <div className="flex items-center gap-1 mt-2 text-sm text-gray-500">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                </svg>
                <span>{executor.location_city}{executor.location_country ? `, ${executor.location_country}` : ''}</span>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* On-Chain Identity Section */}
      <IdentitySection executorId={executor.id} />

      {/* Reputation Section */}
      <ReputationSection
        reputation={reputation}
        loading={reputationLoading}
        memberSince={executor.created_at}
      />

      {/* Earnings Section */}
      <EarningsSection
        earnings={earnings}
        loading={earningsLoading}
        onWithdraw={() => setShowWithdrawalModal(true)}
      />

      {/* Task History Section */}
      <TaskHistorySection
        history={history}
        loading={historyLoading}
        hasMore={hasMore}
        onLoadMore={loadMore}
        filter={historyFilter}
        onFilterChange={setHistoryFilter}
      />

      {/* Settings Section */}
      <SettingsSection
        displayName={displayName}
        preferredToken={preferredToken}
        notifications={notifications}
        selectedSkills={selectedSkills}
        isSaving={isSaving}
        saveSuccess={saveSuccess}
        onDisplayNameChange={setDisplayName}
        onPreferredTokenChange={setPreferredToken}
        onNotificationsChange={setNotifications}
        onSkillsChange={setSelectedSkills}
        onSave={handleSaveSettings}
      />

      {/* Withdrawal Modal */}
      <WithdrawalModal
        isOpen={showWithdrawalModal}
        onClose={handleWithdrawalClose}
        availableBalance={earnings?.balance_usdc || 0}
        executorId={executor.id}
        walletAddress={executor.wallet_address}
      />
    </div>
  )
}

export default Profile
