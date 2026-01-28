/**
 * Chamba E2E Test Fixtures
 *
 * Shared test data and utilities for all E2E tests.
 */
import { test as base, expect, Page } from '@playwright/test';

// ============================================================================
// Test Data Constants
// ============================================================================

export const TEST_USERS = {
  worker: {
    email: 'worker.test@chamba.lat',
    walletAddress: '0x1234567890123456789012345678901234567890',
    displayName: 'Test Worker',
    reputation: 75,
  },
  workerLowRep: {
    email: 'worker.lowrep@chamba.lat',
    walletAddress: '0x2234567890123456789012345678901234567890',
    displayName: 'Low Rep Worker',
    reputation: 25,
  },
  agent: {
    apiKey: 'test_agent_api_key_12345',
    agentId: 'agent_test_001',
    displayName: 'Test Agent Bot',
  },
  validator: {
    email: 'validator@chamba.lat',
    walletAddress: '0x3234567890123456789012345678901234567890',
    displayName: 'Test Validator',
    stake: 100,
  },
};

export const TEST_LOCATIONS = {
  mexicoCity: {
    lat: 19.4326,
    lng: -99.1332,
    city: 'CDMX',
    hint: 'Reforma, CDMX',
  },
  bogota: {
    lat: 4.6097,
    lng: -74.0817,
    city: 'Bogota',
    hint: 'Chapinero, Bogota',
  },
  lima: {
    lat: -12.0464,
    lng: -77.0428,
    city: 'Lima',
    hint: 'Miraflores, Lima',
  },
};

export const TASK_TEMPLATES = {
  simplePhoto: {
    title: 'Tomar foto de producto en tienda',
    category: 'simple_action' as const,
    instructions:
      'Ir a la tienda indicada y tomar una foto clara del producto X con el precio visible.',
    bountyUsd: 5.0,
    deadlineHours: 4,
    evidenceRequired: ['photo'] as const,
    minReputation: 30,
  },
  locationVerification: {
    title: 'Verificar direccion de entrega',
    category: 'physical_presence' as const,
    instructions:
      'Visitar la direccion y confirmar que existe el edificio/casa. Tomar foto del exterior con geolocalizacion.',
    bountyUsd: 15.0,
    deadlineHours: 24,
    evidenceRequired: ['photo_geo'] as const,
    minReputation: 50,
  },
  documentSigning: {
    title: 'Firmar documento en notaria',
    category: 'human_authority' as const,
    instructions:
      'Presentarse en la notaria con identificacion oficial y firmar el documento preparado.',
    bountyUsd: 45.0,
    deadlineHours: 72,
    evidenceRequired: ['document', 'signature'] as const,
    minReputation: 75,
  },
  survey: {
    title: 'Encuesta de satisfaccion en restaurante',
    category: 'knowledge_access' as const,
    instructions:
      'Realizar encuesta de 5 preguntas a cliente del restaurante y registrar respuestas.',
    bountyUsd: 8.0,
    deadlineHours: 2,
    evidenceRequired: ['text_response'] as const,
    minReputation: 20,
  },
};

// ============================================================================
// Custom Fixtures
// ============================================================================

type ChambaFixtures = {
  workerPage: Page;
  agentPage: Page;
  validatorPage: Page;
  authenticatedWorker: Page;
};

export const test = base.extend<ChambaFixtures>({
  // Worker page with basic setup
  workerPage: async ({ page }, use) => {
    // Set worker-specific settings
    await page.addInitScript(() => {
      window.localStorage.setItem('chamba_language', 'es');
    });
    await use(page);
  },

  // Agent page with API key authentication
  agentPage: async ({ page }, use) => {
    await page.addInitScript(
      (apiKey) => {
        window.localStorage.setItem('chamba_agent_api_key', apiKey);
      },
      TEST_USERS.agent.apiKey
    );
    await use(page);
  },

  // Validator page with stake info
  validatorPage: async ({ page }, use) => {
    await page.addInitScript(
      (validator) => {
        window.localStorage.setItem('chamba_is_validator', 'true');
        window.localStorage.setItem('chamba_validator_stake', String(validator.stake));
      },
      TEST_USERS.validator
    );
    await use(page);
  },

  // Pre-authenticated worker
  authenticatedWorker: async ({ page }, use) => {
    // Mock authentication state
    await page.addInitScript(
      (worker) => {
        window.localStorage.setItem('chamba_language', 'es');
        window.localStorage.setItem('chamba_wallet_address', worker.walletAddress);
        window.localStorage.setItem('chamba_display_name', worker.displayName);
        // Mock session token
        window.localStorage.setItem('supabase.auth.token', JSON.stringify({
          access_token: 'mock_access_token',
          user: {
            id: 'mock_user_id',
            email: worker.email,
          },
        }));
      },
      TEST_USERS.worker
    );
    await use(page);
  },
});

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Wait for network to be idle (useful after auth operations)
 */
export async function waitForNetworkIdle(page: Page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Generate a random wallet address for testing
 */
export function generateTestWallet(): string {
  const chars = '0123456789abcdef';
  let address = '0x';
  for (let i = 0; i < 40; i++) {
    address += chars[Math.floor(Math.random() * chars.length)];
  }
  return address;
}

/**
 * Create a future deadline from now
 */
export function createDeadline(hoursFromNow: number): string {
  const date = new Date();
  date.setHours(date.getHours() + hoursFromNow);
  return date.toISOString();
}

/**
 * Mock geolocation for location-based tests
 */
export async function mockGeolocation(
  page: Page,
  coords: { lat: number; lng: number }
) {
  await page.context().setGeolocation({
    latitude: coords.lat,
    longitude: coords.lng,
  });
}

/**
 * Mock file upload (photo evidence)
 */
export async function mockPhotoUpload(
  page: Page,
  inputSelector: string,
  filename = 'test-photo.jpg'
) {
  // Create a test image buffer
  const buffer = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'base64'
  );

  await page.setInputFiles(inputSelector, {
    name: filename,
    mimeType: 'image/jpeg',
    buffer,
  });
}

/**
 * Wait for toast notification
 */
export async function waitForToast(page: Page, text: string) {
  await expect(
    page.locator('[role="alert"], .toast, [data-testid="toast"]').filter({ hasText: text })
  ).toBeVisible({ timeout: 10000 });
}

/**
 * Clear local storage and cookies
 */
export async function clearAuthState(page: Page) {
  await page.evaluate(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
  await page.context().clearCookies();
}

// Re-export expect for convenience
export { expect };
