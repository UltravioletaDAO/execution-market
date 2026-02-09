import { defineConfig, devices } from '@playwright/test'

/**
 * Execution Market E2E Test Configuration
 *
 * Uses VITE_E2E_MODE=true to enable the auth escape hatch in the dashboard,
 * bypassing Dynamic.xyz wallet auth (iframe/shadow DOM) entirely.
 *
 * Run tests with:
 *   npm test              - Run all tests headless
 *   npm run test:headed   - Run with browser visible
 *   npm run test:ui       - Run with Playwright UI
 *   npm run test:debug    - Run in debug mode
 */
export default defineConfig({
  testDir: './tests',

  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    navigationTimeout: 30000,
    actionTimeout: 15000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  outputDir: 'test-results/',

  webServer: {
    command: 'npx vite --port 3000',
    cwd: '../dashboard',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    env: {
      VITE_E2E_MODE: 'true',
    },
  },

  timeout: 60000,

  expect: {
    timeout: 10000,
  },
})
