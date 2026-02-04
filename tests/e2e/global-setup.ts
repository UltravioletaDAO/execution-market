/**
 * Execution Market E2E Tests - Global Setup
 *
 * Runs once before all tests to:
 * 1. Verify test environment is ready
 * 2. Set up test database state (if needed)
 * 3. Create test users and seed data
 */
import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('\n=== Execution Market E2E Test Suite - Global Setup ===\n');

  const baseURL = config.projects[0].use.baseURL || 'http://localhost:3000';

  // 1. Verify the app is running
  console.log(`Checking if app is running at ${baseURL}...`);

  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // Try to access the app
    const response = await page.goto(baseURL, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    if (!response || !response.ok()) {
      throw new Error(`App not accessible. Status: ${response?.status()}`);
    }

    console.log('App is running and accessible.');

    // 2. Check for essential elements
    const emLogo = page.getByText('Execution Market');
    const isReady = await emLogo.isVisible({ timeout: 10000 }).catch(() => false);

    if (isReady) {
      console.log('App loaded successfully with Execution Market branding.');
    } else {
      console.warn('Warning: Could not verify Execution Market branding. Tests may still work.');
    }

    // 3. Set up test data via API (if available)
    const apiHealthCheck = await page.request.get(`${baseURL}/api/health`).catch(() => null);
    if (apiHealthCheck?.ok()) {
      console.log('API is available. Seeding test data...');

      // Seed test tasks
      await seedTestData(page, baseURL);

      console.log('Test data seeded successfully.');
    } else {
      console.log('API health check not available. Skipping data seeding.');
    }

    // 4. Store global state for tests
    await page.context().storageState({
      path: './test-results/storage-state.json',
    });

  } catch (error) {
    console.error('\nGlobal Setup Failed:');
    console.error(error);
    console.error('\nMake sure the Execution Market dashboard is running:');
    console.error('  cd dashboard && npm run dev\n');
    throw error;
  } finally {
    await browser.close();
  }

  console.log('\n=== Global Setup Complete ===\n');
}

/**
 * Seed test data via API
 */
async function seedTestData(page: any, baseURL: string) {
  const testApiKey = process.env.TEST_AGENT_API_KEY || 'test_agent_api_key_12345';

  // Create test tasks
  const testTasks = [
    {
      title: 'E2E Test Task - Photo Verification',
      instructions: 'Take a photo of the specified product.',
      category: 'simple_action',
      bounty_usd: 5.0,
      deadline: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      evidence_schema: { required: ['photo'] },
      min_reputation: 30,
    },
    {
      title: 'E2E Test Task - Location Check',
      instructions: 'Visit the address and verify the business exists.',
      category: 'physical_presence',
      bounty_usd: 15.0,
      deadline: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
      evidence_schema: { required: ['photo_geo'] },
      location: { lat: 19.4326, lng: -99.1332 },
      location_hint: 'CDMX',
      min_reputation: 50,
    },
  ];

  for (const task of testTasks) {
    try {
      await page.request.post(`${baseURL}/api/tasks`, {
        headers: {
          'Authorization': `Bearer ${testApiKey}`,
          'Content-Type': 'application/json',
        },
        data: task,
      });
    } catch (e) {
      // Ignore errors - API might not be implemented yet
    }
  }
}

export default globalSetup;
