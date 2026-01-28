/**
 * TaxReports Page (NOW-037)
 *
 * Export earnings by period for tax purposes.
 * Supports multiple date ranges, jurisdictions, and export formats.
 */

import { useState, useCallback, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { Executor } from '../types/database'

// ============================================================================
// TYPES
// ============================================================================

export interface TaxReportsProps {
  executor: Executor
  onBack?: () => void
}

type DateRangePreset = 'this_month' | 'last_month' | 'this_quarter' | 'last_quarter' | 'this_year' | 'last_year' | 'custom'
type ExportFormat = 'csv' | 'pdf' | 'json'
type TaxJurisdiction = 'mx' | 'us' | 'generic'

interface DateRange {
  start: string
  end: string
}

interface EarningsSummary {
  total_earned: number
  total_tasks: number
  total_fees: number
  net_earnings: number
  by_category: CategoryEarnings[]
  by_month: MonthlyEarnings[]
}

interface CategoryEarnings {
  category: string
  category_label: string
  task_count: number
  total_earned: number
  percentage: number
}

interface MonthlyEarnings {
  month: string
  month_label: string
  task_count: number
  total_earned: number
  fees: number
  net: number
}

interface Transaction {
  id: string
  date: string
  task_id: string
  task_title: string
  category: string
  gross_amount: number
  fee_amount: number
  net_amount: number
  tx_hash: string | null
  payment_token: string
}

interface TaxReportData {
  period: DateRange
  summary: EarningsSummary
  transactions: Transaction[]
  generated_at: string
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DATE_RANGE_PRESETS: Record<DateRangePreset, { labelKey: string; labelDefault: string }> = {
  this_month: { labelKey: 'tax.thisMonth', labelDefault: 'This Month' },
  last_month: { labelKey: 'tax.lastMonth', labelDefault: 'Last Month' },
  this_quarter: { labelKey: 'tax.thisQuarter', labelDefault: 'This Quarter' },
  last_quarter: { labelKey: 'tax.lastQuarter', labelDefault: 'Last Quarter' },
  this_year: { labelKey: 'tax.thisYear', labelDefault: 'This Year' },
  last_year: { labelKey: 'tax.lastYear', labelDefault: 'Last Year' },
  custom: { labelKey: 'tax.customRange', labelDefault: 'Custom Range' },
}

const JURISDICTIONS: Record<TaxJurisdiction, { labelKey: string; labelDefault: string; flag: string }> = {
  mx: { labelKey: 'tax.jurisdiction.mx', labelDefault: 'Mexico (SAT)', flag: 'MX' },
  us: { labelKey: 'tax.jurisdiction.us', labelDefault: 'United States (IRS)', flag: 'US' },
  generic: { labelKey: 'tax.jurisdiction.generic', labelDefault: 'Generic Report', flag: 'INT' },
}

const EXPORT_FORMATS: Record<ExportFormat, { label: string; icon: string; description: string }> = {
  csv: { label: 'CSV', icon: 'csv', description: 'Spreadsheet compatible' },
  pdf: { label: 'PDF', icon: 'pdf', description: 'Print-ready document' },
  json: { label: 'JSON', icon: 'json', description: 'Machine readable' },
}

const CATEGORY_LABELS: Record<string, string> = {
  physical_presence: 'Presencia Fisica',
  knowledge_access: 'Acceso a Conocimiento',
  human_authority: 'Autoridad Humana',
  simple_action: 'Accion Simple',
  digital_physical: 'Digital-Fisico',
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('es-MX', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatDateISO(date: Date): string {
  return date.toISOString().split('T')[0]
}

function getDateRange(preset: DateRangePreset): DateRange {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const quarter = Math.floor(month / 3)

  switch (preset) {
    case 'this_month':
      return {
        start: formatDateISO(new Date(year, month, 1)),
        end: formatDateISO(new Date(year, month + 1, 0)),
      }
    case 'last_month':
      return {
        start: formatDateISO(new Date(year, month - 1, 1)),
        end: formatDateISO(new Date(year, month, 0)),
      }
    case 'this_quarter':
      return {
        start: formatDateISO(new Date(year, quarter * 3, 1)),
        end: formatDateISO(new Date(year, (quarter + 1) * 3, 0)),
      }
    case 'last_quarter':
      return {
        start: formatDateISO(new Date(year, (quarter - 1) * 3, 1)),
        end: formatDateISO(new Date(year, quarter * 3, 0)),
      }
    case 'this_year':
      return {
        start: formatDateISO(new Date(year, 0, 1)),
        end: formatDateISO(new Date(year, 11, 31)),
      }
    case 'last_year':
      return {
        start: formatDateISO(new Date(year - 1, 0, 1)),
        end: formatDateISO(new Date(year - 1, 11, 31)),
      }
    default:
      return {
        start: formatDateISO(new Date(year, month, 1)),
        end: formatDateISO(now),
      }
  }
}

function shortenTxHash(hash: string | null): string {
  if (!hash) return '-'
  return `${hash.slice(0, 6)}...${hash.slice(-4)}`
}

// ============================================================================
// MOCK DATA HOOK (Replace with real API)
// ============================================================================

function useTaxReportData(executorId: string, dateRange: DateRange) {
  const [data, setData] = useState<TaxReportData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // Mock data - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 800))

      const mockTransactions: Transaction[] = [
        {
          id: 'tx_1',
          date: '2026-01-24',
          task_id: 'task_abc123',
          task_title: 'Verify store opening hours in CDMX',
          category: 'physical_presence',
          gross_amount: 15.00,
          fee_amount: 1.50,
          net_amount: 13.50,
          tx_hash: '0xaaaa...1111',
          payment_token: 'USDC',
        },
        {
          id: 'tx_2',
          date: '2026-01-23',
          task_id: 'task_def456',
          task_title: 'Translate medical document',
          category: 'knowledge_access',
          gross_amount: 25.00,
          fee_amount: 2.50,
          net_amount: 22.50,
          tx_hash: '0xbbbb...2222',
          payment_token: 'USDC',
        },
        {
          id: 'tx_3',
          date: '2026-01-22',
          task_id: 'task_ghi789',
          task_title: 'Sign rental agreement',
          category: 'human_authority',
          gross_amount: 50.00,
          fee_amount: 5.00,
          net_amount: 45.00,
          tx_hash: '0xcccc...3333',
          payment_token: 'USDC',
        },
        {
          id: 'tx_4',
          date: '2026-01-20',
          task_id: 'task_jkl012',
          task_title: 'Photo verification at restaurant',
          category: 'physical_presence',
          gross_amount: 12.00,
          fee_amount: 1.20,
          net_amount: 10.80,
          tx_hash: '0xdddd...4444',
          payment_token: 'USDC',
        },
        {
          id: 'tx_5',
          date: '2026-01-18',
          task_id: 'task_mno345',
          task_title: 'Confirm package delivery',
          category: 'simple_action',
          gross_amount: 8.00,
          fee_amount: 0.80,
          net_amount: 7.20,
          tx_hash: '0xeeee...5555',
          payment_token: 'USDC',
        },
      ]

      // Calculate summary
      const totalEarned = mockTransactions.reduce((sum, t) => sum + t.gross_amount, 0)
      const totalFees = mockTransactions.reduce((sum, t) => sum + t.fee_amount, 0)

      // Group by category
      const categoryMap = new Map<string, { count: number; total: number }>()
      mockTransactions.forEach(t => {
        const existing = categoryMap.get(t.category) || { count: 0, total: 0 }
        categoryMap.set(t.category, {
          count: existing.count + 1,
          total: existing.total + t.gross_amount,
        })
      })

      const byCategory: CategoryEarnings[] = Array.from(categoryMap.entries()).map(([category, data]) => ({
        category,
        category_label: CATEGORY_LABELS[category] || category,
        task_count: data.count,
        total_earned: data.total,
        percentage: (data.total / totalEarned) * 100,
      })).sort((a, b) => b.total_earned - a.total_earned)

      // Group by month (mock)
      const byMonth: MonthlyEarnings[] = [
        {
          month: '2026-01',
          month_label: 'January 2026',
          task_count: 5,
          total_earned: totalEarned,
          fees: totalFees,
          net: totalEarned - totalFees,
        },
      ]

      setData({
        period: dateRange,
        summary: {
          total_earned: totalEarned,
          total_tasks: mockTransactions.length,
          total_fees: totalFees,
          net_earnings: totalEarned - totalFees,
          by_category: byCategory,
          by_month: byMonth,
        },
        transactions: mockTransactions,
        generated_at: new Date().toISOString(),
      })
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch report data'))
    } finally {
      setLoading(false)
    }
  }, [executorId, dateRange])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function DateRangePicker({
  preset,
  customRange,
  onPresetChange,
  onCustomRangeChange,
}: {
  preset: DateRangePreset
  customRange: DateRange
  onPresetChange: (preset: DateRangePreset) => void
  onCustomRangeChange: (range: DateRange) => void
}) {
  const { t } = useTranslation()

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">
        {t('tax.selectPeriod', 'Select Period')}
      </h3>

      {/* Preset Buttons */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {(Object.entries(DATE_RANGE_PRESETS) as [DateRangePreset, typeof DATE_RANGE_PRESETS[DateRangePreset]][])
          .filter(([key]) => key !== 'custom')
          .map(([key, config]) => (
            <button
              key={key}
              onClick={() => onPresetChange(key)}
              className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                preset === key
                  ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                  : 'bg-gray-50 text-gray-700 border border-gray-200 hover:bg-gray-100'
              }`}
            >
              {t(config.labelKey, config.labelDefault)}
            </button>
          ))}
      </div>

      {/* Custom Range Toggle */}
      <button
        onClick={() => onPresetChange('custom')}
        className={`w-full px-3 py-2 text-sm font-medium rounded-lg transition-colors mb-3 ${
          preset === 'custom'
            ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
            : 'bg-gray-50 text-gray-700 border border-gray-200 hover:bg-gray-100'
        }`}
      >
        {t('tax.customRange', 'Custom Range')}
      </button>

      {/* Custom Date Inputs */}
      {preset === 'custom' && (
        <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-100">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              {t('tax.startDate', 'Start Date')}
            </label>
            <input
              type="date"
              value={customRange.start}
              onChange={(e) => onCustomRangeChange({ ...customRange, start: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              {t('tax.endDate', 'End Date')}
            </label>
            <input
              type="date"
              value={customRange.end}
              onChange={(e) => onCustomRangeChange({ ...customRange, end: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      )}
    </div>
  )
}

function JurisdictionSelector({
  selected,
  onChange,
}: {
  selected: TaxJurisdiction
  onChange: (jurisdiction: TaxJurisdiction) => void
}) {
  const { t } = useTranslation()

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">
        {t('tax.jurisdiction', 'Tax Jurisdiction')}
      </h3>
      <div className="space-y-2">
        {(Object.entries(JURISDICTIONS) as [TaxJurisdiction, typeof JURISDICTIONS[TaxJurisdiction]][]).map(([key, config]) => (
          <button
            key={key}
            onClick={() => onChange(key)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              selected === key
                ? 'bg-indigo-50 border border-indigo-200'
                : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
            }`}
          >
            <span className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center text-xs font-bold text-gray-600">
              {config.flag}
            </span>
            <span className={`text-sm font-medium ${selected === key ? 'text-indigo-700' : 'text-gray-700'}`}>
              {t(config.labelKey, config.labelDefault)}
            </span>
            {selected === key && (
              <svg className="w-5 h-5 text-indigo-600 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

function EarningsSummaryCard({
  summary,
  loading,
  dateRange,
}: {
  summary: EarningsSummary | null
  loading: boolean
  dateRange: DateRange
}) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl p-6 text-white">
        <div className="animate-pulse">
          <div className="h-4 bg-green-400/50 rounded w-1/3 mb-4"></div>
          <div className="h-10 bg-green-400/50 rounded w-1/2 mb-6"></div>
          <div className="grid grid-cols-3 gap-4">
            <div className="h-16 bg-green-400/50 rounded"></div>
            <div className="h-16 bg-green-400/50 rounded"></div>
            <div className="h-16 bg-green-400/50 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!summary) return null

  return (
    <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl shadow-lg p-6 text-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-green-100 text-sm font-medium">
          {t('tax.periodSummary', 'Period Summary')}
        </h2>
        <span className="text-green-200 text-xs">
          {formatDate(dateRange.start)} - {formatDate(dateRange.end)}
        </span>
      </div>

      {/* Net Earnings (Main) */}
      <div className="mb-4">
        <div className="text-green-200 text-xs mb-1">{t('tax.netEarnings', 'Net Earnings')}</div>
        <span className="text-4xl font-bold">{formatCurrency(summary.net_earnings)}</span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-green-200 text-xs mb-1">
            {t('tax.grossEarnings', 'Gross')}
          </div>
          <div className="text-lg font-semibold">{formatCurrency(summary.total_earned)}</div>
        </div>
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-green-200 text-xs mb-1">
            {t('tax.platformFees', 'Fees')}
          </div>
          <div className="text-lg font-semibold">-{formatCurrency(summary.total_fees)}</div>
        </div>
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-green-200 text-xs mb-1">
            {t('tax.tasksCompleted', 'Tasks')}
          </div>
          <div className="text-lg font-semibold">{summary.total_tasks}</div>
        </div>
      </div>
    </div>
  )
}

function CategoryBreakdown({ categories, loading }: { categories: CategoryEarnings[]; loading: boolean }) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="h-5 bg-gray-200 rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="space-y-3">
          <div className="h-12 bg-gray-100 rounded animate-pulse"></div>
          <div className="h-12 bg-gray-100 rounded animate-pulse"></div>
        </div>
      </div>
    )
  }

  if (categories.length === 0) return null

  const CATEGORY_COLORS: Record<string, string> = {
    physical_presence: 'bg-blue-500',
    knowledge_access: 'bg-purple-500',
    human_authority: 'bg-amber-500',
    simple_action: 'bg-green-500',
    digital_physical: 'bg-indigo-500',
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">
        {t('tax.earningsByCategory', 'Earnings by Category')}
      </h3>
      <div className="space-y-3">
        {categories.map(cat => (
          <div key={cat.category}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-700">{cat.category_label}</span>
              <span className="font-medium text-gray-900">{formatCurrency(cat.total_earned)}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${CATEGORY_COLORS[cat.category] || 'bg-gray-400'}`}
                  style={{ width: `${cat.percentage}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 w-12 text-right">
                {cat.percentage.toFixed(0)}%
              </span>
            </div>
            <div className="text-xs text-gray-400 mt-0.5">
              {cat.task_count} {t('tax.tasks', 'tasks')}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function TransactionHistory({
  transactions,
  loading,
  hasMore,
  onLoadMore,
}: {
  transactions: Transaction[]
  loading: boolean
  hasMore: boolean
  onLoadMore: () => void
}) {
  const { t } = useTranslation()
  const [showAll, setShowAll] = useState(false)

  if (loading && transactions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="h-5 bg-gray-200 rounded w-1/3 animate-pulse"></div>
        </div>
        <div className="p-4 space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-gray-100 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    )
  }

  const displayedTransactions = showAll ? transactions : transactions.slice(0, 5)

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          {t('tax.transactionHistory', 'Transaction History')}
        </h3>
        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">
          {transactions.length} {t('tax.transactions', 'transactions')}
        </span>
      </div>

      {transactions.length === 0 ? (
        <div className="p-8 text-center">
          <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <p className="text-gray-600 font-medium">
            {t('tax.noTransactions', 'No transactions in this period')}
          </p>
        </div>
      ) : (
        <>
          {/* Table Header */}
          <div className="hidden sm:grid grid-cols-12 gap-4 px-6 py-2 bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide">
            <div className="col-span-2">{t('tax.date', 'Date')}</div>
            <div className="col-span-4">{t('tax.task', 'Task')}</div>
            <div className="col-span-2 text-right">{t('tax.gross', 'Gross')}</div>
            <div className="col-span-2 text-right">{t('tax.fees', 'Fees')}</div>
            <div className="col-span-2 text-right">{t('tax.net', 'Net')}</div>
          </div>

          {/* Transaction Rows */}
          <div className="divide-y divide-gray-50">
            {displayedTransactions.map(tx => (
              <div key={tx.id} className="px-6 py-3 hover:bg-gray-50 transition-colors">
                {/* Mobile Layout */}
                <div className="sm:hidden">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 line-clamp-1">
                        {tx.task_title}
                      </h4>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {formatDate(tx.date)} | {CATEGORY_LABELS[tx.category] || tx.category}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold text-green-600">
                        +{formatCurrency(tx.net_amount)}
                      </div>
                      <div className="text-xs text-gray-400">
                        {formatCurrency(tx.gross_amount)} - {formatCurrency(tx.fee_amount)}
                      </div>
                    </div>
                  </div>
                  {tx.tx_hash && (
                    <a
                      href={`https://basescan.org/tx/${tx.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-indigo-600 hover:text-indigo-700"
                    >
                      {shortenTxHash(tx.tx_hash)}
                    </a>
                  )}
                </div>

                {/* Desktop Layout */}
                <div className="hidden sm:grid grid-cols-12 gap-4 items-center">
                  <div className="col-span-2 text-sm text-gray-600">
                    {formatDate(tx.date)}
                  </div>
                  <div className="col-span-4">
                    <div className="text-sm font-medium text-gray-900 line-clamp-1">
                      {tx.task_title}
                    </div>
                    <div className="text-xs text-gray-500">
                      {CATEGORY_LABELS[tx.category] || tx.category}
                      {tx.tx_hash && (
                        <>
                          {' | '}
                          <a
                            href={`https://basescan.org/tx/${tx.tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-600 hover:text-indigo-700"
                          >
                            {shortenTxHash(tx.tx_hash)}
                          </a>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="col-span-2 text-sm text-gray-900 text-right">
                    {formatCurrency(tx.gross_amount)}
                  </div>
                  <div className="col-span-2 text-sm text-gray-500 text-right">
                    -{formatCurrency(tx.fee_amount)}
                  </div>
                  <div className="col-span-2 text-sm font-semibold text-green-600 text-right">
                    {formatCurrency(tx.net_amount)}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Show More / Load More */}
          {(transactions.length > 5 || hasMore) && (
            <div className="px-6 py-3 border-t border-gray-100">
              {!showAll && transactions.length > 5 ? (
                <button
                  onClick={() => setShowAll(true)}
                  className="w-full py-2 text-indigo-600 hover:text-indigo-700 text-sm font-medium transition-colors"
                >
                  {t('common.showAll', 'Show all ({count})', { count: transactions.length })}
                </button>
              ) : hasMore ? (
                <button
                  onClick={onLoadMore}
                  disabled={loading}
                  className="w-full py-2 text-indigo-600 hover:text-indigo-700 text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {loading ? t('common.loading', 'Loading...') : t('common.loadMore', 'Load more')}
                </button>
              ) : null}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function ExportSection({
  onExport,
  loading,
  hasData,
}: {
  onExport: (format: ExportFormat) => void
  loading: boolean
  hasData: boolean
}) {
  const { t } = useTranslation()

  const formatIcons: Record<ExportFormat, React.ReactNode> = {
    csv: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    pdf: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
    json: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">
        {t('tax.exportReport', 'Export Report')}
      </h3>
      <div className="grid grid-cols-3 gap-2">
        {(Object.entries(EXPORT_FORMATS) as [ExportFormat, typeof EXPORT_FORMATS[ExportFormat]][]).map(([format, config]) => (
          <button
            key={format}
            onClick={() => onExport(format)}
            disabled={loading || !hasData}
            className={`flex flex-col items-center gap-2 p-4 rounded-lg transition-colors ${
              hasData
                ? 'bg-gray-50 hover:bg-indigo-50 hover:border-indigo-200 border border-gray-200'
                : 'bg-gray-50 border border-gray-200 opacity-50 cursor-not-allowed'
            }`}
          >
            <span className="text-gray-600">{formatIcons[format]}</span>
            <span className="text-sm font-medium text-gray-900">{config.label}</span>
            <span className="text-xs text-gray-500">{config.description}</span>
          </button>
        ))}
      </div>
      {!hasData && (
        <p className="text-xs text-gray-500 text-center mt-3">
          {t('tax.noDataToExport', 'No data to export for the selected period')}
        </p>
      )}
    </div>
  )
}

// ============================================================================
// EXPORT UTILITIES
// ============================================================================

function generateCSV(data: TaxReportData): string {
  const headers = ['Date', 'Task ID', 'Task Title', 'Category', 'Gross Amount', 'Fee', 'Net Amount', 'Payment Token', 'TX Hash']
  const rows = data.transactions.map(tx => [
    tx.date,
    tx.task_id,
    `"${tx.task_title.replace(/"/g, '""')}"`,
    tx.category,
    tx.gross_amount.toFixed(2),
    tx.fee_amount.toFixed(2),
    tx.net_amount.toFixed(2),
    tx.payment_token,
    tx.tx_hash || '',
  ])

  // Add summary rows
  rows.push([])
  rows.push(['Summary'])
  rows.push(['Total Gross', '', '', '', data.summary.total_earned.toFixed(2)])
  rows.push(['Total Fees', '', '', '', data.summary.total_fees.toFixed(2)])
  rows.push(['Net Earnings', '', '', '', data.summary.net_earnings.toFixed(2)])
  rows.push(['Total Tasks', '', '', '', data.summary.total_tasks.toString()])

  return [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
}

function generateJSON(data: TaxReportData): string {
  return JSON.stringify({
    period: data.period,
    summary: data.summary,
    transactions: data.transactions,
    generated_at: data.generated_at,
  }, null, 2)
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function TaxReports({ executor, onBack }: TaxReportsProps) {
  const { t } = useTranslation()

  // State
  const [preset, setPreset] = useState<DateRangePreset>('this_month')
  const [customRange, setCustomRange] = useState<DateRange>(() => getDateRange('this_month'))
  const [jurisdiction, setJurisdiction] = useState<TaxJurisdiction>('mx')
  const [exporting, setExporting] = useState(false)

  // Calculate effective date range
  const effectiveDateRange = useMemo(() => {
    if (preset === 'custom') {
      return customRange
    }
    return getDateRange(preset)
  }, [preset, customRange])

  // Update custom range when preset changes
  useEffect(() => {
    if (preset !== 'custom') {
      setCustomRange(getDateRange(preset))
    }
  }, [preset])

  // Fetch data
  const { data, loading, error } = useTaxReportData(executor.id, effectiveDateRange)

  // Export handlers
  const handleExport = useCallback(async (format: ExportFormat) => {
    if (!data) return

    setExporting(true)

    try {
      const timestamp = new Date().toISOString().split('T')[0]
      const filename = `chamba-tax-report-${timestamp}`

      switch (format) {
        case 'csv': {
          const csvContent = generateCSV(data)
          downloadFile(csvContent, `${filename}.csv`, 'text/csv')
          break
        }
        case 'json': {
          const jsonContent = generateJSON(data)
          downloadFile(jsonContent, `${filename}.json`, 'application/json')
          break
        }
        case 'pdf': {
          // PDF generation would require a library like jsPDF
          // For now, show alert
          alert(t('tax.pdfNotImplemented', 'PDF export coming soon! Use CSV for now.'))
          break
        }
      }
    } catch (err) {
      console.error('Export failed:', err)
      alert(t('tax.exportError', 'Export failed. Please try again.'))
    } finally {
      setExporting(false)
    }
  }, [data, t])

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
            <span className="text-sm font-medium">{t('common.back', 'Back')}</span>
          </button>
        )}
        <h1 className="text-xl font-bold text-gray-900">
          {t('tax.title', 'Tax Reports')}
        </h1>
        <div className="w-16" /> {/* Spacer for centering */}
      </div>

      {/* Info Banner */}
      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-amber-900 mb-1">
              {t('tax.disclaimer', 'Tax Disclaimer')}
            </h3>
            <p className="text-sm text-amber-700">
              {t('tax.disclaimerText', 'This report is for informational purposes only. Please consult a tax professional for advice specific to your situation. Chamba does not provide tax advice.')}
            </p>
          </div>
        </div>
      </div>

      {/* Date Range Picker */}
      <DateRangePicker
        preset={preset}
        customRange={customRange}
        onPresetChange={setPreset}
        onCustomRangeChange={setCustomRange}
      />

      {/* Jurisdiction Selector */}
      <JurisdictionSelector
        selected={jurisdiction}
        onChange={setJurisdiction}
      />

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-center gap-2 text-red-700">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="font-medium">{t('tax.loadError', 'Failed to load report data')}</span>
          </div>
          <p className="text-sm text-red-600 mt-1">{error.message}</p>
        </div>
      )}

      {/* Earnings Summary */}
      <EarningsSummaryCard
        summary={data?.summary || null}
        loading={loading}
        dateRange={effectiveDateRange}
      />

      {/* Category Breakdown */}
      <CategoryBreakdown
        categories={data?.summary.by_category || []}
        loading={loading}
      />

      {/* Export Section */}
      <ExportSection
        onExport={handleExport}
        loading={exporting}
        hasData={!!data && data.transactions.length > 0}
      />

      {/* Transaction History */}
      <TransactionHistory
        transactions={data?.transactions || []}
        loading={loading}
        hasMore={false}
        onLoadMore={() => {}}
      />

      {/* Generated Timestamp */}
      {data && (
        <p className="text-xs text-gray-400 text-center">
          {t('tax.generatedAt', 'Report generated')}: {new Date(data.generated_at).toLocaleString('es-MX')}
        </p>
      )}
    </div>
  )
}

export default TaxReports
