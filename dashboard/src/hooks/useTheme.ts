/**
 * useTheme Hook
 *
 * A React hook for managing dark mode and theme preferences.
 * Supports system preference detection, localStorage persistence,
 * and smooth transitions.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system';

export interface UseThemeOptions {
  /** Default theme mode */
  defaultTheme?: ThemeMode;
  /** localStorage key for persistence */
  storageKey?: string;
  /** Enable system preference detection */
  enableSystem?: boolean;
  /** Disable transition during theme change */
  disableTransitionOnChange?: boolean;
}

export interface UseThemeReturn {
  /** Current resolved theme ('light' or 'dark') */
  theme: 'light' | 'dark';
  /** Current theme mode setting */
  themeMode: ThemeMode;
  /** Whether dark mode is active */
  isDark: boolean;
  /** Whether light mode is active */
  isLight: boolean;
  /** Whether system preference is being used */
  isSystem: boolean;
  /** Set theme mode */
  setTheme: (mode: ThemeMode) => void;
  /** Toggle between light and dark */
  toggleTheme: () => void;
  /** Set to light mode */
  setLight: () => void;
  /** Set to dark mode */
  setDark: () => void;
  /** Set to system preference */
  setSystem: () => void;
}

const STORAGE_KEY = 'em-theme';
const THEME_ATTRIBUTE = 'class';
const DARK_CLASS = 'dark';

/**
 * Get system color scheme preference
 */
function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Get stored theme from localStorage
 */
function getStoredTheme(key: string): ThemeMode | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(key);
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
  } catch {
    // localStorage not available
  }
  return null;
}

/**
 * Store theme preference in localStorage
 */
function storeTheme(key: string, theme: ThemeMode): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(key, theme);
  } catch {
    // localStorage not available
  }
}

/**
 * Apply theme to document
 */
function applyTheme(theme: 'light' | 'dark', disableTransition: boolean): void {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;

  // Optionally disable transitions during theme change
  if (disableTransition) {
    const css = document.createElement('style');
    css.appendChild(
      document.createTextNode(
        `*,*::before,*::after{-webkit-transition:none!important;-moz-transition:none!important;-o-transition:none!important;-ms-transition:none!important;transition:none!important}`
      )
    );
    document.head.appendChild(css);

    // Force reflow
    (() => window.getComputedStyle(root).opacity)();

    // Remove the style after a short delay
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.head.removeChild(css);
      });
    });
  }

  // Apply or remove dark class
  if (theme === 'dark') {
    root.classList.add(DARK_CLASS);
  } else {
    root.classList.remove(DARK_CLASS);
  }

  // Update meta theme-color for mobile browsers
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute('content', theme === 'dark' ? '#0f172a' : '#ffffff');
  }

  // Update color-scheme property
  root.style.colorScheme = theme;
}

/**
 * Resolve theme mode to actual theme
 */
function resolveTheme(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'system') {
    return getSystemTheme();
  }
  return mode;
}

/**
 * useTheme hook
 */
export function useTheme(options: UseThemeOptions = {}): UseThemeReturn {
  const {
    defaultTheme = 'system',
    storageKey = STORAGE_KEY,
    enableSystem = true,
    disableTransitionOnChange = false,
  } = options;

  // Initialize theme mode from storage or default
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const stored = getStoredTheme(storageKey);
    return stored ?? defaultTheme;
  });

  // Track system preference
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() => getSystemTheme());

  // Resolved theme
  const theme = useMemo(() => {
    if (themeMode === 'system' && enableSystem) {
      return systemTheme;
    }
    return themeMode === 'dark' ? 'dark' : 'light';
  }, [themeMode, systemTheme, enableSystem]);

  // Derived states
  const isDark = theme === 'dark';
  const isLight = theme === 'light';
  const isSystem = themeMode === 'system';

  // Apply theme on mount and when it changes
  useEffect(() => {
    applyTheme(theme, disableTransitionOnChange);
  }, [theme, disableTransitionOnChange]);

  // Listen for system preference changes
  useEffect(() => {
    if (!enableSystem) return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? 'dark' : 'light');
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
    // Legacy browsers
    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, [enableSystem]);

  // Persist theme changes
  useEffect(() => {
    storeTheme(storageKey, themeMode);
  }, [themeMode, storageKey]);

  // Theme setters
  const setTheme = useCallback((mode: ThemeMode) => {
    setThemeMode(mode);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeMode((current) => {
      // If currently system, toggle based on resolved theme
      if (current === 'system') {
        return systemTheme === 'dark' ? 'light' : 'dark';
      }
      return current === 'dark' ? 'light' : 'dark';
    });
  }, [systemTheme]);

  const setLight = useCallback(() => setThemeMode('light'), []);
  const setDark = useCallback(() => setThemeMode('dark'), []);
  const setSystem = useCallback(() => setThemeMode('system'), []);

  return {
    theme,
    themeMode,
    isDark,
    isLight,
    isSystem,
    setTheme,
    toggleTheme,
    setLight,
    setDark,
    setSystem,
  };
}

/**
 * ThemeScript Component
 *
 * Inline script to prevent flash of incorrect theme.
 * Add this to your HTML head.
 */
export function getThemeScript(storageKey: string = STORAGE_KEY): string {
  return `
    (function() {
      try {
        var stored = localStorage.getItem('${storageKey}');
        var theme = stored;
        if (!theme || theme === 'system') {
          theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        }
        document.documentElement.style.colorScheme = theme;
      } catch (e) {}
    })();
  `.replace(/\s+/g, ' ').trim();
}

/**
 * usePrefersDarkMode hook
 *
 * Simple hook that only returns system preference.
 */
export function usePrefersDarkMode(): boolean {
  const [prefersDark, setPrefersDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersDark(e.matches);
    };

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  return prefersDark;
}

export default useTheme;
