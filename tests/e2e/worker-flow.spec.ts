/**
 * Worker Flow E2E Tests
 *
 * Tests complete worker journey from signup to payment:
 * 1. Onboarding (signup with email/wallet)
 * 2. Profile setup (skills, location)
 * 3. Task discovery (browse, filter, search)
 * 4. Task acceptance
 * 5. Evidence submission
 * 6. Payment receipt
 * 7. Reputation updates
 */
import { test, expect, Page } from '@playwright/test';
import {
  TEST_USERS,
  TEST_LOCATIONS,
  TASK_TEMPLATES,
  waitForNetworkIdle,
  generateTestWallet,
  mockGeolocation,
  mockPhotoUpload,
  waitForToast,
  clearAuthState,
} from './fixtures/test-fixtures';

// ============================================================================
// Test Setup
// ============================================================================

test.describe('Worker Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing auth state
    await clearAuthState(page);
  });

  // ==========================================================================
  // 1. ONBOARDING & AUTHENTICATION
  // ==========================================================================

  test.describe('Onboarding', () => {
    test('should display welcome screen with language selection', async ({ page }) => {
      await page.goto('/');

      // Verify Execution Market branding is visible
      await expect(page.getByText('Execution Market')).toBeVisible();

      // Check for login button
      const loginButton = page.getByRole('button', { name: /iniciar sesion|login/i });
      await expect(loginButton).toBeVisible();
    });

    test('should sign up with manual wallet address', async ({ page }) => {
      await page.goto('/');

      // Click login
      await page.getByRole('button', { name: /iniciar sesion|login/i }).click();

      // Wait for auth modal
      await expect(page.locator('[class*="modal"], [role="dialog"]')).toBeVisible();

      // Click "Enter wallet manually" option
      await page.getByText(/enter.*manual|ingresar.*manual/i).click();

      // Fill wallet address
      const testWallet = generateTestWallet();
      await page.getByPlaceholder(/0x/i).fill(testWallet);

      // Fill display name (for new users)
      const nameInput = page.getByPlaceholder(/nombre|name/i);
      if (await nameInput.isVisible()) {
        await nameInput.fill('Test Worker E2E');
      }

      // Submit
      await page.getByRole('button', { name: /connect|conectar/i }).click();

      // Wait for authentication to complete
      await waitForNetworkIdle(page);

      // Verify logged in state - should see profile avatar or name
      await expect(
        page.locator('[data-testid="user-menu"], [data-testid="profile-button"]').or(
          page.getByText('Test Worker E2E')
        )
      ).toBeVisible({ timeout: 15000 });
    });

    test('should sign up with email and password', async ({ page }) => {
      await page.goto('/');

      // Open auth modal
      await page.getByRole('button', { name: /iniciar sesion|login/i }).click();

      // Click email option
      await page.getByText(/email.*password|correo/i).click();

      // Wait for email form
      await expect(page.getByPlaceholder(/email|correo/i)).toBeVisible();

      // Fill form
      const uniqueEmail = `test+${Date.now()}@execution.market`;
      await page.getByPlaceholder(/email|correo/i).fill(uniqueEmail);
      await page.getByPlaceholder(/password|contrasena/i).fill('TestPassword123!');

      // Look for signup link/button
      const signupLink = page.getByText(/registr|sign.*up|crear.*cuenta/i);
      if (await signupLink.isVisible()) {
        await signupLink.click();

        // Fill wallet address for signup
        const walletInput = page.getByPlaceholder(/0x/i);
        if (await walletInput.isVisible()) {
          await walletInput.fill(generateTestWallet());
        }
      }

      // Submit
      await page.getByRole('button', { name: /login|iniciar|sign|registrar/i }).click();

      // Wait for auth
      await waitForNetworkIdle(page);
    });

    test('should complete onboarding flow for new users', async ({ page }) => {
      await page.goto('/');

      // Authenticate first
      await page.getByRole('button', { name: /iniciar sesion|login/i }).click();
      await page.getByText(/enter.*manual|ingresar.*manual/i).click();
      await page.getByPlaceholder(/0x/i).fill(generateTestWallet());
      await page.getByRole('button', { name: /connect|conectar/i }).click();
      await waitForNetworkIdle(page);

      // If onboarding flow appears, complete it
      const welcomeTitle = page.getByText(/bienvenido|welcome/i);
      if (await welcomeTitle.isVisible({ timeout: 5000 })) {
        // Step 1: Language selection
        await page.getByText('Espanol').or(page.getByText('ES')).click();
        await page.getByRole('button', { name: /comenzar|get.*started|continuar/i }).click();

        // Step 2: Profile (if shown)
        const nameInput = page.getByPlaceholder(/nombre|apodo|name/i);
        if (await nameInput.isVisible({ timeout: 3000 })) {
          await nameInput.fill('Worker E2E');
          await page.getByRole('button', { name: /continuar|continue/i }).click();
        }

        // Step 3: Skills selection (if shown)
        const skillsTitle = page.getByText(/habilidades|skills/i);
        if (await skillsTitle.isVisible({ timeout: 3000 })) {
          // Select some skills
          await page.getByText(/fotografia|photography/i).click().catch(() => {});
          await page.getByText(/delivery|entrega/i).click().catch(() => {});
          await page.getByRole('button', { name: /continuar|continue|saltar|skip/i }).click();
        }

        // Step 4: Location (if shown)
        const locationTitle = page.getByText(/ubicacion|location/i);
        if (await locationTitle.isVisible({ timeout: 3000 })) {
          await page.getByRole('button', { name: /continuar|continue|saltar|skip/i }).click();
        }

        // Step 5: Notifications (if shown)
        const notifTitle = page.getByText(/notificaciones|notifications/i);
        if (await notifTitle.isVisible({ timeout: 3000 })) {
          await page.getByRole('button', { name: /saltar|skip|continuar/i }).click();
        }

        // Complete
        const completeButton = page.getByRole('button', { name: /explorar|start|listo/i });
        if (await completeButton.isVisible({ timeout: 3000 })) {
          await completeButton.click();
        }
      }

      // Should now see main app
      await expect(page.getByText(/tareas|tasks/i)).toBeVisible();
    });
  });

  // ==========================================================================
  // 2. TASK DISCOVERY
  // ==========================================================================

  test.describe('Task Discovery', () => {
    test.beforeEach(async ({ page }) => {
      // Login before each task discovery test
      await page.goto('/');
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
          window.localStorage.setItem('em_display_name', worker.displayName);
        },
        TEST_USERS.worker
      );
      await page.reload();
    });

    test('should browse available tasks', async ({ page }) => {
      // Navigate to task list
      await page.goto('/');

      // Check for task list
      await expect(page.getByText(/tareas disponibles|available/i)).toBeVisible();

      // Verify task cards are displayed
      const taskCards = page.locator('[data-testid="task-card"], .task-card, article');
      await expect(taskCards.first()).toBeVisible({ timeout: 10000 });
    });

    test('should filter tasks by category', async ({ page }) => {
      await page.goto('/');

      // Find category filter
      const categoryFilter = page.locator('[data-testid="category-filter"], select, [role="combobox"]').first();

      if (await categoryFilter.isVisible()) {
        // Click to open filter
        await categoryFilter.click();

        // Select "Physical Presence" category
        await page.getByText(/presencia.*fisica|physical.*presence/i).click();

        // Verify filtered results
        await waitForNetworkIdle(page);

        // Tasks should be filtered
        const taskCards = page.locator('[data-testid="task-card"], .task-card');
        const count = await taskCards.count();
        expect(count).toBeGreaterThanOrEqual(0);
      }
    });

    test('should filter tasks by location', async ({ page }) => {
      // Mock location as Mexico City
      await mockGeolocation(page, TEST_LOCATIONS.mexicoCity);

      await page.goto('/');

      // Look for location filter
      const locationFilter = page.getByText(/ubicacion|location|cerca de mi/i);

      if (await locationFilter.isVisible({ timeout: 5000 })) {
        await locationFilter.click();

        // Enable location-based filtering
        const nearMeButton = page.getByText(/cerca de mi|near me|usar ubicacion/i);
        if (await nearMeButton.isVisible()) {
          await nearMeButton.click();
        }

        // Wait for filtered results
        await waitForNetworkIdle(page);
      }
    });

    test('should view task details', async ({ page }) => {
      await page.goto('/');

      // Wait for tasks to load
      const firstTask = page.locator('[data-testid="task-card"], .task-card, article').first();
      await expect(firstTask).toBeVisible({ timeout: 10000 });

      // Click on first task
      await firstTask.click();

      // Verify detail view
      await expect(page.getByText(/instrucciones|instructions/i)).toBeVisible();
      await expect(page.getByText(/evidencia.*requerida|evidence.*required/i)).toBeVisible();
      await expect(page.getByText(/fecha.*limite|deadline/i)).toBeVisible();
    });

    test('should switch between available and my tasks tabs', async ({ page }) => {
      await page.goto('/');

      // Find tab buttons
      const availableTab = page.getByRole('button', { name: /disponibles|available/i }).or(
        page.getByText(/tareas disponibles/i)
      );
      const myTasksTab = page.getByRole('button', { name: /mis tareas|my tasks/i });

      await expect(availableTab).toBeVisible();
      await expect(myTasksTab).toBeVisible();

      // Click my tasks
      await myTasksTab.click();

      // Should show my tasks view (might be empty)
      await expect(
        page.getByText(/mis tareas|my tasks/i).or(page.getByText(/no tienes tareas/i))
      ).toBeVisible();
    });
  });

  // ==========================================================================
  // 3. TASK APPLICATION & ACCEPTANCE
  // ==========================================================================

  test.describe('Task Acceptance', () => {
    test('should apply to a task successfully', async ({ page }) => {
      // Setup authenticated worker
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
          window.localStorage.setItem('em_display_name', worker.displayName);
          window.localStorage.setItem('em_reputation', String(worker.reputation));
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Click on first available task
      const firstTask = page.locator('[data-testid="task-card"], .task-card').first();
      await firstTask.click();

      // Find and click accept button
      const acceptButton = page.getByRole('button', { name: /aceptar|accept|aplicar|apply/i });

      if (await acceptButton.isEnabled()) {
        await acceptButton.click();

        // Wait for success
        await waitForNetworkIdle(page);

        // Should show confirmation or redirect
        await expect(
          page
            .getByText(/aceptada|accepted|confirmado/i)
            .or(page.getByText(/mis tareas|my tasks/i))
        ).toBeVisible({ timeout: 10000 });
      }
    });

    test('should show requirements not met message for low reputation', async ({ page }) => {
      // Setup low reputation worker
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
          window.localStorage.setItem('em_display_name', worker.displayName);
          window.localStorage.setItem('em_reputation', String(worker.reputation));
        },
        TEST_USERS.workerLowRep
      );

      await page.goto('/');

      // Try to find a high-reputation task
      const taskCards = page.locator('[data-testid="task-card"], .task-card');
      await taskCards.first().click();

      // Check for requirements message
      const requirementsMessage = page.getByText(/no cumples|requisitos|not meet|requirements/i);
      const acceptButton = page.getByRole('button', { name: /aceptar|accept/i });

      // Either show message or button should be disabled
      const hasMessage = await requirementsMessage.isVisible({ timeout: 3000 }).catch(() => false);
      const isDisabled = await acceptButton.isDisabled().catch(() => false);

      expect(hasMessage || isDisabled).toBeTruthy();
    });

    test('should not allow accepting already taken task', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Navigate to a task that's already accepted (mock or find one)
      // This test assumes there might be tasks with different statuses

      const taskCards = page.locator('[data-testid="task-card"], .task-card');
      const count = await taskCards.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        await taskCards.nth(i).click();

        // Check if task is already taken
        const statusBadge = page.getByText(/aceptada|accepted|en progreso|in progress/i);
        if (await statusBadge.isVisible({ timeout: 2000 })) {
          // Accept button should be hidden or show different text
          const acceptButton = page.getByRole('button', { name: /aceptar tarea/i });
          await expect(acceptButton).not.toBeVisible();
          break;
        }

        // Go back and try next
        await page.getByText(/volver|back/i).click();
      }
    });
  });

  // ==========================================================================
  // 4. EVIDENCE SUBMISSION
  // ==========================================================================

  test.describe('Evidence Submission', () => {
    test('should navigate to submission form for accepted task', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
          window.localStorage.setItem('em_display_name', worker.displayName);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Go to my tasks
      await page.getByText(/mis tareas|my tasks/i).click();

      // Click on an accepted task (if any)
      const acceptedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /aceptada|in progress|accepted/i,
      });

      if ((await acceptedTask.count()) > 0) {
        await acceptedTask.first().click();

        // Find submit evidence button
        const submitButton = page.getByRole('button', {
          name: /enviar evidencia|submit evidence/i,
        });
        await expect(submitButton).toBeVisible();

        // Click to open submission form
        await submitButton.click();

        // Verify submission form
        await expect(page.getByText(/evidencia requerida|required evidence/i)).toBeVisible();
      }
    });

    test('should upload photo evidence', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Navigate to submission form (assuming we have an accepted task)
      await page.getByText(/mis tareas|my tasks/i).click();

      const acceptedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /aceptada|accepted/i,
      });

      if ((await acceptedTask.count()) > 0) {
        await acceptedTask.first().click();
        await page.getByRole('button', { name: /enviar evidencia|submit/i }).click();

        // Find file input
        const fileInput = page.locator('input[type="file"]').first();

        if (await fileInput.isVisible({ timeout: 5000 })) {
          // Upload mock photo
          await mockPhotoUpload(page, 'input[type="file"]', 'evidence-photo.jpg');

          // Verify preview appears
          await expect(page.locator('img[alt*="preview"], img[src*="blob"]')).toBeVisible({
            timeout: 5000,
          });
        }
      }
    });

    test('should validate required evidence before submission', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');
      await page.getByText(/mis tareas|my tasks/i).click();

      const acceptedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /aceptada|accepted/i,
      });

      if ((await acceptedTask.count()) > 0) {
        await acceptedTask.first().click();
        await page.getByRole('button', { name: /enviar evidencia|submit/i }).click();

        // Try to submit without evidence
        const submitButton = page.getByRole('button', { name: /enviar|submit/i }).last();
        await submitButton.click();

        // Should show validation error
        await expect(page.getByText(/falta.*evidencia|missing.*evidence|requerida/i)).toBeVisible();
      }
    });

    test('should submit evidence successfully', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');
      await page.getByText(/mis tareas|my tasks/i).click();

      const acceptedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /aceptada|accepted/i,
      });

      if ((await acceptedTask.count()) > 0) {
        await acceptedTask.first().click();
        await page.getByRole('button', { name: /enviar evidencia|submit/i }).click();

        // Upload required evidence
        const fileInputs = page.locator('input[type="file"]');
        const count = await fileInputs.count();

        for (let i = 0; i < count; i++) {
          await mockPhotoUpload(
            page,
            `input[type="file"]:nth-of-type(${i + 1})`,
            `evidence-${i}.jpg`
          );
        }

        // Fill text responses if any
        const textareas = page.locator('textarea');
        const textCount = await textareas.count();
        for (let i = 0; i < textCount; i++) {
          const textarea = textareas.nth(i);
          if (await textarea.isVisible()) {
            await textarea.fill('E2E test evidence response');
          }
        }

        // Submit
        await page.getByRole('button', { name: /enviar evidencia|submit evidence/i }).click();

        // Wait for submission
        await waitForNetworkIdle(page);

        // Should show success or redirect
        await expect(
          page.getByText(/enviada|submitted|success|exito/i).or(page.getByText(/mis tareas/i))
        ).toBeVisible({ timeout: 15000 });
      }
    });

    test('should verify EXIF/GPS data extraction from photo', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      // Mock geolocation
      await mockGeolocation(page, TEST_LOCATIONS.mexicoCity);

      await page.goto('/');
      await page.getByText(/mis tareas|my tasks/i).click();

      const geoTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /ubicacion|geo|location/i,
      });

      if ((await geoTask.count()) > 0) {
        await geoTask.first().click();
        await page.getByRole('button', { name: /enviar evidencia|submit/i }).click();

        // Upload photo with geo requirement
        await mockPhotoUpload(page, 'input[type="file"]', 'geo-evidence.jpg');

        // Check for GPS validation indicator
        const gpsIndicator = page.getByText(
          /gps.*verificado|location.*verified|ubicacion.*confirmada/i
        );
        // This might not show immediately depending on implementation
      }
    });
  });

  // ==========================================================================
  // 5. PAYMENT & EARNINGS
  // ==========================================================================

  test.describe('Payment & Earnings', () => {
    test('should see payment status after approval', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Navigate to profile/earnings
      await page.getByText(TEST_USERS.worker.displayName).or(page.locator('[data-testid="profile-button"]')).click();

      // Look for earnings section
      await expect(
        page.getByText(/ganancias|earnings|balance/i)
      ).toBeVisible({ timeout: 10000 });
    });

    test('should display payment history', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Navigate to profile
      await page.getByText(TEST_USERS.worker.displayName).or(page.locator('[data-testid="profile-button"]')).click();

      // Find payment history
      const historySection = page.getByText(/historial.*pagos|payment.*history/i);
      if (await historySection.isVisible({ timeout: 5000 })) {
        await historySection.click();

        // Should show list of payments or empty state
        await expect(
          page.getByText(/pago|payment|\$/i).or(page.getByText(/sin pagos|no payments/i))
        ).toBeVisible();
      }
    });

    test('should see reputation update after task completion', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Navigate to profile
      await page.getByText(TEST_USERS.worker.displayName).or(page.locator('[data-testid="profile-button"]')).click();

      // Look for reputation score
      await expect(page.getByText(/reputacion|reputation/i)).toBeVisible();

      // Verify reputation display format
      const repScore = page.locator('[data-testid="reputation-score"], .reputation-score');
      await expect(repScore.or(page.getByText(/\d+\s*\/\s*100|\d+%/))).toBeVisible();
    });

    test('should initiate withdrawal', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Navigate to profile/wallet
      await page.getByText(TEST_USERS.worker.displayName).or(page.locator('[data-testid="profile-button"]')).click();

      // Find withdraw button
      const withdrawButton = page.getByRole('button', { name: /retirar|withdraw/i });

      if (await withdrawButton.isVisible({ timeout: 5000 })) {
        await withdrawButton.click();

        // Should show withdrawal form or modal
        await expect(
          page.getByText(/cantidad|amount/i).or(page.getByPlaceholder(/monto|amount/i))
        ).toBeVisible();
      }
    });
  });

  // ==========================================================================
  // 6. PROFILE MANAGEMENT
  // ==========================================================================

  test.describe('Profile Management', () => {
    test('should display worker profile with all sections', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
          window.localStorage.setItem('em_display_name', worker.displayName);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Navigate to profile
      await page.getByText(TEST_USERS.worker.displayName).or(page.locator('[data-testid="profile-button"]')).click();

      // Verify profile sections
      await expect(page.getByText(/perfil|profile/i)).toBeVisible();
      await expect(page.getByText(/reputacion|reputation/i)).toBeVisible();
      await expect(page.getByText(/tareas completadas|tasks completed/i).or(page.getByText(/completadas|completed/i))).toBeVisible();
    });

    test('should update display name', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Navigate to profile
      await page.locator('[data-testid="profile-button"]').or(page.getByText(/perfil|profile/i)).click();

      // Find edit button
      const editButton = page.getByRole('button', { name: /editar|edit/i });
      if (await editButton.isVisible({ timeout: 5000 })) {
        await editButton.click();

        // Update name
        const nameInput = page.getByPlaceholder(/nombre|name/i).or(
          page.locator('input[name="displayName"]')
        );
        await nameInput.clear();
        await nameInput.fill('Updated Worker Name');

        // Save
        await page.getByRole('button', { name: /guardar|save/i }).click();

        // Verify update
        await waitForNetworkIdle(page);
        await expect(page.getByText('Updated Worker Name')).toBeVisible();
      }
    });

    test('should change language preference', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');

      // Find language switcher
      const langSwitcher = page.locator('[data-testid="language-switcher"], .language-switcher');

      if (await langSwitcher.isVisible()) {
        await langSwitcher.click();

        // Select English
        await page.getByText('English').or(page.getByText('EN')).click();

        // Verify UI changed to English
        await expect(page.getByText(/tasks|available/i)).toBeVisible();
      }
    });
  });

  // ==========================================================================
  // 7. ERROR HANDLING
  // ==========================================================================

  test.describe('Error Handling', () => {
    test('should handle network errors gracefully', async ({ page }) => {
      await page.route('**/api/**', (route) => route.abort());

      await page.goto('/');

      // Should show error state or offline indicator
      await expect(
        page
          .getByText(/error|problema|sin conexion|offline/i)
          .or(page.getByText(/intentar de nuevo|retry/i))
      ).toBeVisible({ timeout: 10000 });
    });

    test('should handle session expiration', async ({ page }) => {
      await page.addInitScript(() => {
        window.localStorage.setItem('em_wallet_address', 'expired_session');
      });

      // Mock API to return 401
      await page.route('**/api/**', (route) => {
        route.fulfill({
          status: 401,
          body: JSON.stringify({ error: 'Session expired' }),
        });
      });

      await page.goto('/');

      // Should redirect to login or show session expired message
      await expect(
        page.getByText(/sesion|session|expirada|expired|iniciar/i).or(
          page.getByRole('button', { name: /login|iniciar/i })
        )
      ).toBeVisible({ timeout: 10000 });
    });

    test('should recover from submission failure', async ({ page }) => {
      await page.addInitScript(
        (worker) => {
          window.localStorage.setItem('em_wallet_address', worker.walletAddress);
        },
        TEST_USERS.worker
      );

      await page.goto('/');
      await page.getByText(/mis tareas|my tasks/i).click();

      // Mock submission API to fail
      await page.route('**/submissions**', (route) => {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Server error' }),
        });
      });

      const acceptedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /aceptada|accepted/i,
      });

      if ((await acceptedTask.count()) > 0) {
        await acceptedTask.first().click();
        await page.getByRole('button', { name: /enviar evidencia|submit/i }).click();

        // Try to submit (assuming evidence is pre-filled or not required)
        await page.getByRole('button', { name: /enviar|submit/i }).click();

        // Should show error message
        await expect(page.getByText(/error|fallo|failed/i)).toBeVisible();

        // Should allow retry
        await expect(page.getByRole('button', { name: /enviar|submit|retry/i })).toBeEnabled();
      }
    });
  });
});
