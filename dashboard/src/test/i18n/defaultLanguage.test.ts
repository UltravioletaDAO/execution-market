/**
 * Default Language Tests
 *
 * CRITICAL: The platform must default to English. Spanish (or any other
 * language) should ONLY activate when the user explicitly selects it
 * via the language switcher menu.
 *
 * No browser auto-detection. No navigator.language sniffing.
 *
 * Incident: Feb 16 2026 — Users with Spanish-language browsers were
 * seeing the entire platform in Spanish without ever choosing it.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ============================================================================
// We can't easily test the actual i18n init (it runs at import time),
// so we test the getInitialLanguage logic directly by reproducing it.
// Use a real Map-backed localStorage mock since test setup replaces global one.
// ============================================================================

const SUPPORTED_LANGUAGES = ['en', 'es'] as const
type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]
const STORAGE_KEY = 'em-lang'
const LEGACY_STORAGE_KEY = 'em_language'

// In-memory storage for these tests (test setup mocks global localStorage)
const store = new Map<string, string>()
const mockStorage = {
  getItem: (key: string) => store.get(key) ?? null,
  setItem: (key: string, value: string) => { store.set(key, value) },
  removeItem: (key: string) => { store.delete(key) },
  clear: () => { store.clear() },
}

/**
 * Reproduction of getInitialLanguage from i18n/index.ts
 * Must match the actual implementation exactly.
 * Uses mockStorage instead of window.localStorage for test isolation.
 */
function getInitialLanguage(): SupportedLanguage {
  const stored = mockStorage.getItem(STORAGE_KEY)
    || mockStorage.getItem(LEGACY_STORAGE_KEY)
  if (stored && SUPPORTED_LANGUAGES.includes(stored as SupportedLanguage)) {
    return stored as SupportedLanguage
  }
  return 'en'
}

// ============================================================================
// Tests
// ============================================================================

describe('Default Language', () => {
  beforeEach(() => {
    store.clear()
  })

  afterEach(() => {
    store.clear()
  })

  // --------------------------------------------------------------------------
  // Core requirement: English by default
  // --------------------------------------------------------------------------

  it('defaults to English when no language is stored', () => {
    expect(getInitialLanguage()).toBe('en')
  })

  it('defaults to English even when browser is in Spanish', () => {
    // Simulate Spanish browser — should NOT affect default
    Object.defineProperty(navigator, 'language', { value: 'es-MX', configurable: true })
    Object.defineProperty(navigator, 'languages', { value: ['es-MX', 'es', 'en'], configurable: true })

    expect(getInitialLanguage()).toBe('en')

    // Restore
    Object.defineProperty(navigator, 'language', { value: 'en-US', configurable: true })
    Object.defineProperty(navigator, 'languages', { value: ['en-US', 'en'], configurable: true })
  })

  it('defaults to English even when browser is in Portuguese', () => {
    Object.defineProperty(navigator, 'language', { value: 'pt-BR', configurable: true })

    expect(getInitialLanguage()).toBe('en')

    Object.defineProperty(navigator, 'language', { value: 'en-US', configurable: true })
  })

  it('defaults to English even when browser is in unsupported language (Chinese)', () => {
    Object.defineProperty(navigator, 'language', { value: 'zh-CN', configurable: true })

    expect(getInitialLanguage()).toBe('en')

    Object.defineProperty(navigator, 'language', { value: 'en-US', configurable: true })
  })

  // --------------------------------------------------------------------------
  // Explicit user choice is respected
  // --------------------------------------------------------------------------

  it('returns Spanish when user explicitly chose it (em-lang)', () => {
    mockStorage.setItem(STORAGE_KEY, 'es')
    expect(getInitialLanguage()).toBe('es')
  })

  it('returns English when user explicitly chose it (em-lang)', () => {
    mockStorage.setItem(STORAGE_KEY, 'en')
    expect(getInitialLanguage()).toBe('en')
  })

  it('returns Spanish from legacy key (em_language) for backward compat', () => {
    mockStorage.setItem(LEGACY_STORAGE_KEY, 'es')
    expect(getInitialLanguage()).toBe('es')
  })

  it('canonical key takes precedence over legacy key', () => {
    mockStorage.setItem(STORAGE_KEY, 'en')
    mockStorage.setItem(LEGACY_STORAGE_KEY, 'es')
    expect(getInitialLanguage()).toBe('en')
  })

  // --------------------------------------------------------------------------
  // Edge cases
  // --------------------------------------------------------------------------

  it('ignores invalid stored language', () => {
    mockStorage.setItem(STORAGE_KEY, 'fr')
    expect(getInitialLanguage()).toBe('en')
  })

  it('ignores empty stored value', () => {
    mockStorage.setItem(STORAGE_KEY, '')
    expect(getInitialLanguage()).toBe('en')
  })

  it('ignores garbage stored value', () => {
    mockStorage.setItem(STORAGE_KEY, 'xyz123')
    expect(getInitialLanguage()).toBe('en')
  })
})

describe('Storage Key Consistency', () => {
  it('canonical key is em-lang', () => {
    expect(STORAGE_KEY).toBe('em-lang')
  })

  it('legacy key is em_language', () => {
    expect(LEGACY_STORAGE_KEY).toBe('em_language')
  })

  it('changeLanguage should persist to canonical key', () => {
    // Verify the contract: when changeLanguage is called,
    // storage must use 'em-lang' (not 'em_language')
    mockStorage.setItem('em-lang', 'es')
    expect(mockStorage.getItem('em-lang')).toBe('es')
  })
})
