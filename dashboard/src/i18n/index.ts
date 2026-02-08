/**
 * i18n Configuration for Execution Market Dashboard
 *
 * Supports:
 * - English (en)
 * - Spanish (es) - Latin American
 *
 * Features:
 * - Browser language detection
 * - Persisted language preference
 * - Dynamic resource loading
 * - Fallback to English
 */

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Import translations statically for initial bundle
// These are relatively small JSON files, so static import is acceptable
import en from './locales/en.json'
import es from './locales/es.json'

// Supported languages (Portuguese removed - incomplete translations)
export const SUPPORTED_LANGUAGES = ['en', 'es'] as const
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

// Language metadata for UI
export const LANGUAGE_CONFIG: Record<
  SupportedLanguage,
  {
    code: SupportedLanguage
    label: string
    fullName: string
    flag: string
    nativeName: string
  }
> = {
  en: {
    code: 'en',
    label: 'EN',
    fullName: 'English',
    flag: '🇺🇸',
    nativeName: 'English',
  },
  es: {
    code: 'es',
    label: 'ES',
    fullName: 'Spanish',
    flag: '🇲🇽',
    nativeName: 'Espanol',
  },
}

// Storage key for persisted language
const STORAGE_KEY = 'em-lang'

/**
 * Detect browser language and return a supported language code
 */
function getBrowserLanguage(): SupportedLanguage {
  // Try navigator.language first (e.g., "en-US", "es-MX", "pt-BR")
  const browserLang = navigator.language?.split('-')[0]?.toLowerCase()

  if (browserLang && SUPPORTED_LANGUAGES.includes(browserLang as SupportedLanguage)) {
    return browserLang as SupportedLanguage
  }

  // Try navigator.languages array
  for (const lang of navigator.languages || []) {
    const code = lang.split('-')[0].toLowerCase()
    if (SUPPORTED_LANGUAGES.includes(code as SupportedLanguage)) {
      return code as SupportedLanguage
    }
  }

  // Default to English as the fallback
  return 'en'
}

/**
 * Get the initial language to use
 * Priority: localStorage > browser detection > English
 */
function getInitialLanguage(): SupportedLanguage {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && SUPPORTED_LANGUAGES.includes(stored as SupportedLanguage)) {
    return stored as SupportedLanguage
  }
  return getBrowserLanguage()
}

// Initialize i18next
i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    es: { translation: es },
  },
  lng: getInitialLanguage(),
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false, // React already escapes values
  },
  // Enable debug in development
  debug: import.meta.env.DEV && false, // Set to true for debugging
})

export default i18n

/**
 * Change language and persist preference
 */
export function changeLanguage(lang: SupportedLanguage): void {
  if (!SUPPORTED_LANGUAGES.includes(lang)) {
    console.warn(`Unsupported language: ${lang}`)
    return
  }
  localStorage.setItem(STORAGE_KEY, lang)
  i18n.changeLanguage(lang)
}

/**
 * Get current language code
 */
export function getCurrentLanguage(): SupportedLanguage {
  const current = i18n.language?.split('-')[0]
  if (SUPPORTED_LANGUAGES.includes(current as SupportedLanguage)) {
    return current as SupportedLanguage
  }
  return 'en'
}

/**
 * Get language configuration for the current language
 */
export function getCurrentLanguageConfig() {
  return LANGUAGE_CONFIG[getCurrentLanguage()]
}

/**
 * Check if a language is supported
 */
export function isLanguageSupported(lang: string): lang is SupportedLanguage {
  return SUPPORTED_LANGUAGES.includes(lang as SupportedLanguage)
}
