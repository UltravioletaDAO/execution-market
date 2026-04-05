/**
 * Dynamic.xyz SDK Configuration
 *
 * Dynamic provides wallet authentication with built-in UI and multi-wallet support.
 * https://docs.dynamic.xyz/
 */

// Environment ID from Dynamic dashboard
export const DYNAMIC_ENVIRONMENT_ID = import.meta.env.VITE_DYNAMIC_ENVIRONMENT_ID || ''

// Known Live (production) environment ID
export const DYNAMIC_LIVE_ENVIRONMENT_ID = '11e08592-9807-4079-be4f-3152c3e52d12'

// Check if Dynamic is properly configured
export const isDynamicConfigured = (): boolean => {
  return Boolean(DYNAMIC_ENVIRONMENT_ID)
}

// Check if the current environment is the Live (production) environment
export const isDynamicLive = (): boolean => {
  return DYNAMIC_ENVIRONMENT_ID === DYNAMIC_LIVE_ENVIRONMENT_ID
}

// CSS overrides for Dynamic widget (optional)
export const dynamicCssOverrides = `
  .dynamic-widget-inline-controls {
    background: transparent;
  }
  .dynamic-widget-card {
    border-radius: 1rem;
  }
`
