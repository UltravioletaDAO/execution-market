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
 * Get the initial language to use.
 *
 * ENGLISH BY DEFAULT. Only switches to another language when the user
 * explicitly selects it via the language switcher menu. No browser
 * auto-detection — we don't want Spanish-browser users seeing the site
 * in Spanish without opting in.
 *
 * Priority: localStorage (explicit user choice) > English
 */
function getInitialLanguage(): SupportedLanguage {
  // Check both storage keys for backward compatibility
  // (SettingsPage previously used 'em_language', canonical key is 'em-lang')
  const stored = localStorage.getItem(STORAGE_KEY)
    || localStorage.getItem('em_language')
  if (stored && SUPPORTED_LANGUAGES.includes(stored as SupportedLanguage)) {
    return stored as SupportedLanguage
  }
  return 'en'
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

  // Best-effort DB sync for cross-device persistence
  try {
    const walletAddress = localStorage.getItem('em_last_wallet_address')
    if (walletAddress) {
      import('../lib/supabase').then(({ supabase }) => {
        supabase
          .from('executors')
          .update({ preferred_language: lang })
          .eq('wallet_address', walletAddress.toLowerCase())
          .then(() => {})  // fire and forget
      }).catch(() => {})
    }
  } catch {
    // Non-fatal — localStorage is primary
  }
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
