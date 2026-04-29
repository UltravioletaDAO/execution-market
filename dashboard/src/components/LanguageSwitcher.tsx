/**
 * Language Switcher Components
 *
 * Provides two variants:
 * 1. LanguageSwitcher - Inline button group with flags
 * 2. LanguageSwitcherDropdown - Compact dropdown for mobile/headers
 */

import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  changeLanguage,
  getCurrentLanguage,
  LANGUAGE_CONFIG,
  SUPPORTED_LANGUAGES,
  type SupportedLanguage,
} from '../i18n'
import { Pill } from './ui/Pill'

interface LanguageSwitcherProps {
  className?: string
  showFlags?: boolean
  showLabels?: boolean
  compact?: boolean
}

/**
 * Inline language switcher with flag icons
 * Best for: Headers, settings pages, landing pages
 */
export function LanguageSwitcher({
  className = '',
  showFlags = false,
  showLabels = true,
  compact = false,
}: LanguageSwitcherProps) {
  useTranslation() // Hook needed for re-render on language change
  const currentLang = getCurrentLanguage()

  const languages = SUPPORTED_LANGUAGES.map((code) => LANGUAGE_CONFIG[code])

  return (
    <div className={`flex items-center gap-0.5 ${className}`} role="group" aria-label="Language selection">
      {languages.map((lang, idx) => (
        <span key={lang.code} className="flex items-center">
          <Pill
            variant={currentLang === lang.code ? 'selected' : 'default'}
            size="sm"
            onClick={() => changeLanguage(lang.code)}
            title={lang.nativeName}
            aria-label={`Switch to ${lang.fullName}`}
            aria-pressed={currentLang === lang.code}
            leftIcon={showFlags ? <span aria-hidden="true">{lang.flag}</span> : undefined}
          >
            {showLabels ? lang.label : null}
          </Pill>
          {idx < languages.length - 1 && (
            <span className="text-zinc-400 dark:text-zinc-600 mx-0.5" aria-hidden="true">|</span>
          )}
        </span>
      ))}
    </div>
  )
}

/**
 * Dropdown version for mobile/compact spaces
 * Best for: Mobile nav, compact headers
 */
export function LanguageSwitcherDropdown({ className = '' }: LanguageSwitcherProps) {
  useTranslation() // Hook needed for re-render on language change
  const currentLang = getCurrentLanguage()

  return (
    <select
      value={currentLang}
      onChange={(e) => changeLanguage(e.target.value as SupportedLanguage)}
      className={`px-2 py-1 text-sm border border-zinc-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 focus:ring-2 focus:ring-zinc-500 focus:border-zinc-500 outline-none cursor-pointer ${className}`}
      aria-label="Select language"
    >
      {SUPPORTED_LANGUAGES.map((code) => {
        const config = LANGUAGE_CONFIG[code]
        return (
          <option key={code} value={code}>
            {config.flag} {config.nativeName}
          </option>
        )
      })}
    </select>
  )
}

/**
 * Full-featured dropdown with preview and better UX
 * Best for: Settings pages, onboarding
 */
export function LanguageSwitcherMenu({ className = '' }: LanguageSwitcherProps) {
  useTranslation()
  const currentLang = getCurrentLanguage()
  const currentConfig = LANGUAGE_CONFIG[currentLang]
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Close on escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  const handleSelectLanguage = (lang: SupportedLanguage) => {
    changeLanguage(lang)
    setIsOpen(false)
  }

  return (
    <div ref={menuRef} className={`relative ${className}`}>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-zinc-900 dark:text-zinc-100 bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="text-lg" aria-hidden="true">{currentConfig.flag}</span>
        <span>{currentConfig.nativeName}</span>
        <svg
          className={`w-4 h-4 text-zinc-500 dark:text-zinc-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div
          className="absolute z-50 mt-2 w-48 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg shadow-lg py-1"
          role="listbox"
          aria-label="Available languages"
        >
          {SUPPORTED_LANGUAGES.map((code) => {
            const config = LANGUAGE_CONFIG[code]
            const isSelected = code === currentLang

            return (
              <button
                key={code}
                onClick={() => handleSelectLanguage(code)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  isSelected
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
                    : 'text-zinc-900 dark:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-800'
                }`}
                role="option"
                aria-selected={isSelected}
              >
                <span className="text-xl" aria-hidden="true">{config.flag}</span>
                <div className="flex-1 text-left">
                  <div className="font-medium">{config.nativeName}</div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-400">{config.fullName}</div>
                </div>
                {isSelected && (
                  <svg className="w-4 h-4 text-zinc-900 dark:text-zinc-100" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default LanguageSwitcher
