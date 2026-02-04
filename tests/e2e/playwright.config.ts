/**
 * Execution Market E2E Tests - Playwright Configuration
 *
 * Comprehensive configuration for testing worker, agent, and dispute flows.
 * Supports both desktop and mobile viewports.
 */
import { defineConfig, devices } from '@playwright/test';

// Environment variables with defaults for local development
const baseURL = process.env.BASE_URL || 'http://localhost:3000';
const apiURL = process.env.API_URL || 'http://localhost:3000/api';

export default defineConfig({
  // Test directory
  testDir: './',
  testMatch: '**/*.spec.ts',

  // Parallel execution settings
  fullyParallel: true,
  workers: process.env.CI ? 1 : undefined,

  // Retry configuration
  retries: process.env.CI ? 2 : 0,

  // Timeout settings
  timeout: 30000,
  expect: {
    timeout: 10000,
  },

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: '../test-results/html-report' }],
    ['json', { outputFile: '../test-results/results.json' }],
    process.env.CI ? ['github'] : ['list'],
  ],

  // Output directories
  outputDir: '../test-results/artifacts',

  // Global test settings
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Browser settings
    headless: process.env.CI ? true : false,
    viewport: { width: 1280, height: 720 },

    // Network settings
    actionTimeout: 15000,
    navigationTimeout: 30000,

    // Locale for LATAM testing
    locale: 'es-MX',
    timezoneId: 'America/Mexico_City',

    // Geolocation for location-based tasks (Mexico City)
    geolocation: { latitude: 19.4326, longitude: -99.1332 },
    permissions: ['geolocation'],
  },

  // Browser projects
  projects: [
    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Mobile devices (critical for LATAM workers)
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 13'] },
    },

    // Low-end Android device (realistic LATAM scenario)
    {
      name: 'mobile-android-low',
      use: {
        ...devices['Pixel 5'],
        viewport: { width: 360, height: 640 },
        deviceScaleFactor: 2,
        isMobile: true,
        hasTouch: true,
      },
    },
  ],

  // Development server
  webServer: process.env.CI
    ? undefined
    : {
        command: 'cd ../dashboard && npm run dev',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
      },

  // Global setup/teardown
  globalSetup: process.env.CI ? undefined : './global-setup.ts',
  globalTeardown: process.env.CI ? undefined : './global-teardown.ts',
});

// Export for use in tests
export { baseURL, apiURL };
