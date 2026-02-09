/**
 * Custom useTranslation hook with type-safe keys and locale-aware formatting
 *
 * Features:
 * - Wraps react-i18next useTranslation
 * - Type-safe translation keys (autocomplete support)
 * - Locale-aware number formatting
 * - Locale-aware date formatting
 * - Currency formatting
 * - Relative time formatting
 */

import { useTranslation as useI18nextTranslation } from 'react-i18next'
import { useCallback, useMemo } from 'react'
import { getCurrentLanguage, type SupportedLanguage } from '../index'

// Import the translation type from English locale for type inference
import type en from '../locales/en.json'

// Type for nested keys (e.g., "common.loading", "auth.errors.invalidWallet")
type NestedKeyOf<T, K extends string = ''> = T extends object
  ? {
      [P in keyof T & string]: T[P] extends object
        ? NestedKeyOf<T[P], K extends '' ? P : `${K}.${P}`>
        : K extends ''
          ? P
          : `${K}.${P}`
    }[keyof T & string]
  : never

// Translation key type derived from the English locale structure
export type TranslationKey = NestedKeyOf<typeof en>

// Locale mapping for Intl APIs
const LOCALE_MAP: Record<SupportedLanguage, string> = {
  en: 'en-US',
  es: 'es-MX', // Latin American Spanish
}

// Currency options by region
const CURRENCY_BY_LOCALE: Record<SupportedLanguage, string> = {
  en: 'USD',
  es: 'USD', // Most LATAM uses USD for crypto
}

/**
 * Custom translation hook with locale-aware formatting utilities
 */
export function useTranslation() {
  const { t, i18n, ready } = useI18nextTranslation()
  const currentLang = getCurrentLanguage()
  const locale = LOCALE_MAP[currentLang]

  /**
   * Type-safe translation function
   * Usage: t('common.loading') or t('auth.errors.invalidWallet')
   */
  const translate = useCallback(
    (key: TranslationKey, options?: Record<string, unknown>): string => {
      return t(key, options as never) as unknown as string
    },
    [t]
  )

  /**
   * Format a number according to the current locale
   * @param value - The number to format
   * @param options - Intl.NumberFormatOptions
   */
  const formatNumber = useCallback(
    (value: number, options?: Intl.NumberFormatOptions): string => {
      return new Intl.NumberFormat(locale, options).format(value)
    },
    [locale]
  )

  /**
   * Format a number as currency (defaults to USD for crypto context)
   * @param value - The amount to format
   * @param currency - Currency code (defaults to locale-appropriate)
   */
  const formatCurrency = useCallback(
    (value: number, currency?: string): string => {
      const currencyCode = currency || CURRENCY_BY_LOCALE[currentLang]
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value)
    },
    [locale, currentLang]
  )

  /**
   * Format a number as compact currency (e.g., $1.2K, $3.5M)
   * @param value - The amount to format
   */
  const formatCompactCurrency = useCallback(
    (value: number, currency?: string): string => {
      const currencyCode = currency || CURRENCY_BY_LOCALE[currentLang]
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currencyCode,
        notation: 'compact',
        compactDisplay: 'short',
      }).format(value)
    },
    [locale, currentLang]
  )

  /**
   * Format a percentage value
   * @param value - The decimal value (0.15 = 15%)
   * @param decimals - Number of decimal places
   */
  const formatPercent = useCallback(
    (value: number, decimals: number = 0): string => {
      return new Intl.NumberFormat(locale, {
        style: 'percent',
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(value)
    },
    [locale]
  )

  /**
   * Format a date according to the current locale
   * @param date - Date object or ISO string
   * @param options - Intl.DateTimeFormatOptions or preset name
   */
  const formatDate = useCallback(
    (
      date: Date | string | number,
      options?: Intl.DateTimeFormatOptions | 'short' | 'medium' | 'long' | 'full'
    ): string => {
      const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date

      // Preset options
      const presets: Record<string, Intl.DateTimeFormatOptions> = {
        short: { month: 'numeric', day: 'numeric' },
        medium: { month: 'short', day: 'numeric', year: 'numeric' },
        long: { month: 'long', day: 'numeric', year: 'numeric' },
        full: { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' },
      }

      const formatOptions = typeof options === 'string' ? presets[options] : options

      return new Intl.DateTimeFormat(locale, formatOptions).format(dateObj)
    },
    [locale]
  )

  /**
   * Format a time according to the current locale
   * @param date - Date object or ISO string
   * @param includeSeconds - Whether to include seconds
   */
  const formatTime = useCallback(
    (date: Date | string | number, includeSeconds: boolean = false): string => {
      const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date

      return new Intl.DateTimeFormat(locale, {
        hour: 'numeric',
        minute: '2-digit',
        second: includeSeconds ? '2-digit' : undefined,
      }).format(dateObj)
    },
    [locale]
  )

  /**
   * Format a date and time together
   * @param date - Date object or ISO string
   */
  const formatDateTime = useCallback(
    (date: Date | string | number): string => {
      const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date

      return new Intl.DateTimeFormat(locale, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      }).format(dateObj)
    },
    [locale]
  )

  /**
   * Format a relative time (e.g., "2 hours ago", "in 3 days")
   * @param date - Date to compare against now
   * @param style - 'long' | 'short' | 'narrow'
   */
  const formatRelativeTime = useCallback(
    (date: Date | string | number, style: 'long' | 'short' | 'narrow' = 'long'): string => {
      const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date
      const now = new Date()
      const diffMs = dateObj.getTime() - now.getTime()
      const diffSeconds = Math.round(diffMs / 1000)
      const diffMinutes = Math.round(diffSeconds / 60)
      const diffHours = Math.round(diffMinutes / 60)
      const diffDays = Math.round(diffHours / 24)
      const diffWeeks = Math.round(diffDays / 7)
      const diffMonths = Math.round(diffDays / 30)
      const diffYears = Math.round(diffDays / 365)

      const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto', style })

      // Choose the most appropriate unit
      if (Math.abs(diffSeconds) < 60) {
        return rtf.format(diffSeconds, 'second')
      } else if (Math.abs(diffMinutes) < 60) {
        return rtf.format(diffMinutes, 'minute')
      } else if (Math.abs(diffHours) < 24) {
        return rtf.format(diffHours, 'hour')
      } else if (Math.abs(diffDays) < 7) {
        return rtf.format(diffDays, 'day')
      } else if (Math.abs(diffWeeks) < 4) {
        return rtf.format(diffWeeks, 'week')
      } else if (Math.abs(diffMonths) < 12) {
        return rtf.format(diffMonths, 'month')
      } else {
        return rtf.format(diffYears, 'year')
      }
    },
    [locale]
  )

  /**
   * Format time remaining until a deadline
   * Returns a human-readable string like "2 hours left" or "Expired"
   */
  const formatTimeRemaining = useCallback(
    (deadline: Date | string | number): string => {
      const deadlineDate =
        typeof deadline === 'string' || typeof deadline === 'number'
          ? new Date(deadline)
          : deadline
      const now = new Date()
      const diffMs = deadlineDate.getTime() - now.getTime()

      if (diffMs < 0) {
        return translate('time.expired')
      }

      const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
      const diffDays = Math.floor(diffHours / 24)

      if (diffHours < 1) {
        return translate('time.lessThanOneHour')
      } else if (diffHours < 24) {
        return diffHours === 1
          ? translate('time.hoursLeft', { count: 1 })
          : translate('time.hoursLeft_plural', { count: diffHours })
      } else {
        return diffDays === 1
          ? translate('time.daysLeft', { count: 1 })
          : translate('time.daysLeft_plural', { count: diffDays })
      }
    },
    [translate]
  )

  /**
   * Format a list of items according to locale (e.g., "A, B, and C")
   * @param items - Array of strings to format
   * @param type - 'conjunction' | 'disjunction' | 'unit'
   */
  const formatList = useCallback(
    (items: string[], type: 'conjunction' | 'disjunction' | 'unit' = 'conjunction'): string => {
      // @ts-expect-error ListFormat not in all TS lib versions
      return new Intl.ListFormat(locale, { style: 'long', type }).format(items)
    },
    [locale]
  )

  // Memoize the return object to prevent unnecessary re-renders
  return useMemo(
    () => ({
      // Original i18next exports
      t: translate,
      i18n,
      ready,

      // Current language info
      language: currentLang,
      locale,

      // Formatting utilities
      formatNumber,
      formatCurrency,
      formatCompactCurrency,
      formatPercent,
      formatDate,
      formatTime,
      formatDateTime,
      formatRelativeTime,
      formatTimeRemaining,
      formatList,
    }),
    [
      translate,
      i18n,
      ready,
      currentLang,
      locale,
      formatNumber,
      formatCurrency,
      formatCompactCurrency,
      formatPercent,
      formatDate,
      formatTime,
      formatDateTime,
      formatRelativeTime,
      formatTimeRemaining,
      formatList,
    ]
  )
}

export default useTranslation
