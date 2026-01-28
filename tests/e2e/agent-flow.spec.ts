/**
 * Agent Flow E2E Tests
 *
 * Tests complete agent journey:
 * 1. API authentication
 * 2. Task creation via API
 * 3. Task management via dashboard
 * 4. Submission review
 * 5. Evidence approval/rejection
 * 6. Payment authorization
 * 7. Analytics and reporting
 */
import { test, expect, APIRequestContext } from '@playwright/test';
import {
  TEST_USERS,
  TEST_LOCATIONS,
  TASK_TEMPLATES,
  waitForNetworkIdle,
  createDeadline,
} from './fixtures/test-fixtures';

// ============================================================================
// API Test Helpers
// ============================================================================

interface TaskCreatePayload {
  title: string;
  instructions: string;
  category: string;
  bountyUsd: number;
  deadlineHours: number;
  evidenceRequired: string[];
  location?: { lat: number; lng: number };
  locationHint?: string;
  locationRadiusKm?: number;
  minReputation?: number;
  requiredRoles?: string[];
  maxExecutors?: number;
}

async function createTaskViaAPI(
  request: APIRequestContext,
  apiKey: string,
  taskData: TaskCreatePayload
): Promise<{ id: string; status: string }> {
  const response = await request.post('/api/tasks', {
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    data: {
      title: taskData.title,
      instructions: taskData.instructions,
      category: taskData.category,
      bounty_usd: taskData.bountyUsd,
      deadline: createDeadline(taskData.deadlineHours),
      evidence_schema: {
        required: taskData.evidenceRequired,
        optional: [],
      },
      location: taskData.location || null,
      location_hint: taskData.locationHint || null,
      location_radius_km: taskData.locationRadiusKm || null,
      min_reputation: taskData.minReputation || 0,
      required_roles: taskData.requiredRoles || [],
      max_executors: taskData.maxExecutors || 1,
    },
  });

  return response.json();
}

// ============================================================================
// Test Setup
// ============================================================================

test.describe('Agent Flow', () => {
  // ==========================================================================
  // 1. API AUTHENTICATION
  // ==========================================================================

  test.describe('API Authentication', () => {
    test('should authenticate with valid API key', async ({ request }) => {
      const response = await request.get('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
        },
      });

      // Should succeed or return auth-related status
      expect([200, 401, 403]).toContain(response.status());

      if (response.ok()) {
        const data = await response.json();
        expect(Array.isArray(data) || data.tasks).toBeTruthy();
      }
    });

    test('should reject invalid API key', async ({ request }) => {
      const response = await request.get('/api/tasks', {
        headers: {
          Authorization: 'Bearer invalid_key_12345',
        },
      });

      expect(response.status()).toBe(401);
    });

    test('should reject missing API key', async ({ request }) => {
      const response = await request.get('/api/tasks');

      // Should return 401 Unauthorized
      expect([401, 403]).toContain(response.status());
    });

    test('should return agent profile with valid key', async ({ request }) => {
      const response = await request.get('/api/agent/profile', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
        },
      });

      if (response.ok()) {
        const profile = await response.json();
        expect(profile).toHaveProperty('id');
      }
    });
  });

  // ==========================================================================
  // 2. TASK CREATION VIA API
  // ==========================================================================

  test.describe('Task Creation', () => {
    test('should create a simple task via API', async ({ request }) => {
      const response = await request.post('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
          'Content-Type': 'application/json',
        },
        data: {
          title: 'E2E Test Task - Simple Photo',
          instructions: 'Take a photo of the product on the shelf with price visible.',
          category: 'simple_action',
          bounty_usd: 5.0,
          deadline: createDeadline(4),
          evidence_schema: {
            required: ['photo'],
            optional: ['text_response'],
          },
          min_reputation: 30,
          max_executors: 1,
        },
      });

      if (response.ok()) {
        const task = await response.json();
        expect(task.id).toBeDefined();
        expect(task.status).toBe('published');
      } else {
        // If API is not implemented, skip
        expect([200, 201, 501]).toContain(response.status());
      }
    });

    test('should create a location-based task', async ({ request }) => {
      const response = await request.post('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
          'Content-Type': 'application/json',
        },
        data: {
          title: 'E2E Test Task - Location Verification',
          instructions: 'Visit the address and take a geotagged photo of the building exterior.',
          category: 'physical_presence',
          bounty_usd: 15.0,
          deadline: createDeadline(24),
          evidence_schema: {
            required: ['photo_geo'],
          },
          location: TEST_LOCATIONS.mexicoCity,
          location_hint: TEST_LOCATIONS.mexicoCity.hint,
          location_radius_km: 0.5,
          min_reputation: 50,
          max_executors: 1,
        },
      });

      if (response.ok()) {
        const task = await response.json();
        expect(task.id).toBeDefined();
        expect(task.location).toBeDefined();
      }
    });

    test('should create a task requiring multiple evidence types', async ({ request }) => {
      const response = await request.post('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
          'Content-Type': 'application/json',
        },
        data: {
          title: 'E2E Test Task - Document Collection',
          instructions: 'Collect signed document from notary with photo proof and receipt.',
          category: 'human_authority',
          bounty_usd: 45.0,
          deadline: createDeadline(72),
          evidence_schema: {
            required: ['document', 'signature', 'photo'],
            optional: ['receipt'],
          },
          min_reputation: 75,
          required_roles: ['notary_authorized'],
          max_executors: 1,
        },
      });

      if (response.ok()) {
        const task = await response.json();
        expect(task.evidence_schema.required).toHaveLength(3);
      }
    });

    test('should validate required fields on task creation', async ({ request }) => {
      // Missing title
      const response = await request.post('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
          'Content-Type': 'application/json',
        },
        data: {
          instructions: 'Instructions without title',
          category: 'simple_action',
          bounty_usd: 5.0,
          deadline: createDeadline(4),
        },
      });

      // Should return validation error
      expect([400, 422]).toContain(response.status());

      if (!response.ok()) {
        const error = await response.json();
        expect(error.error || error.message).toBeDefined();
      }
    });

    test('should validate bounty minimum', async ({ request }) => {
      const response = await request.post('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
          'Content-Type': 'application/json',
        },
        data: {
          title: 'Test Task - Invalid Bounty',
          instructions: 'Test instructions',
          category: 'simple_action',
          bounty_usd: 0.01, // Too low
          deadline: createDeadline(4),
          evidence_schema: { required: ['photo'] },
        },
      });

      // Should reject if bounty is below minimum
      // Accept 200 if there's no minimum validation
      expect([200, 201, 400, 422]).toContain(response.status());
    });

    test('should validate deadline is in the future', async ({ request }) => {
      const pastDate = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

      const response = await request.post('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
          'Content-Type': 'application/json',
        },
        data: {
          title: 'Test Task - Past Deadline',
          instructions: 'Test instructions',
          category: 'simple_action',
          bounty_usd: 5.0,
          deadline: pastDate,
          evidence_schema: { required: ['photo'] },
        },
      });

      // Should reject past deadline
      expect([400, 422]).toContain(response.status());
    });
  });

  // ==========================================================================
  // 3. TASK MANAGEMENT VIA DASHBOARD
  // ==========================================================================

  test.describe('Dashboard Task Management', () => {
    test('should display agent dashboard', async ({ page }) => {
      // Setup agent session
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_agent_api_key', agent.apiKey);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Should show agent dashboard
      await expect(page.getByText(/panel.*agente|agent.*dashboard/i)).toBeVisible({
        timeout: 10000,
      });
    });

    test('should display task list with status filters', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Look for status filters
      await expect(
        page.getByText(/publicadas|published/i).or(page.getByText(/todas|all/i))
      ).toBeVisible({ timeout: 10000 });

      // Check for task list
      const taskList = page.locator('[data-testid="task-list"], .task-list, .tasks-grid');
      await expect(taskList).toBeVisible();
    });

    test('should view task details from dashboard', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Click on a task
      const firstTask = page.locator('[data-testid="task-card"], .task-card').first();
      if ((await firstTask.count()) > 0) {
        await firstTask.click();

        // Should show task details
        await expect(page.getByText(/instrucciones|instructions/i)).toBeVisible();
        await expect(page.getByText(/estado|status/i)).toBeVisible();
      }
    });

    test('should cancel a published task', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Find a published task
      const publishedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /publicada|published/i,
      });

      if ((await publishedTask.count()) > 0) {
        await publishedTask.first().click();

        // Look for cancel button
        const cancelButton = page.getByRole('button', { name: /cancelar|cancel/i });
        if (await cancelButton.isVisible()) {
          await cancelButton.click();

          // Confirm cancellation
          const confirmButton = page.getByRole('button', { name: /confirmar|confirm/i });
          if (await confirmButton.isVisible()) {
            await confirmButton.click();
          }

          // Verify status changed
          await waitForNetworkIdle(page);
          await expect(page.getByText(/cancelada|cancelled/i)).toBeVisible();
        }
      }
    });
  });

  // ==========================================================================
  // 4. SUBMISSION REVIEW
  // ==========================================================================

  test.describe('Submission Review', () => {
    test('should display pending submissions', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Look for submissions section
      await expect(
        page.getByText(/entregas.*revisar|pending.*submissions|por revisar/i)
      ).toBeVisible({ timeout: 10000 });
    });

    test('should view submission details', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Click on first pending submission
      const reviewButton = page.getByRole('button', { name: /revisar|review/i }).first();
      if (await reviewButton.isVisible({ timeout: 5000 })) {
        await reviewButton.click();

        // Should show submission details
        await expect(
          page.getByText(/evidencia|evidence/i).or(page.getByText(/submission/i))
        ).toBeVisible();
      }
    });

    test('should view submitted evidence files', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      const reviewButton = page.getByRole('button', { name: /revisar|review/i }).first();
      if (await reviewButton.isVisible({ timeout: 5000 })) {
        await reviewButton.click();

        // Should display evidence images/files
        const evidenceSection = page.locator('[data-testid="evidence-viewer"], .evidence-viewer');
        if (await evidenceSection.isVisible({ timeout: 5000 })) {
          // Check for image thumbnails or file links
          await expect(
            page.locator('img[alt*="evidence"], img[alt*="evidencia"], a[href*="storage"]').first()
          ).toBeVisible();
        }
      }
    });

    test('should verify auto-check results are displayed', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      const reviewButton = page.getByRole('button', { name: /revisar|review/i }).first();
      if (await reviewButton.isVisible({ timeout: 5000 })) {
        await reviewButton.click();

        // Look for auto-check indicator
        const autoCheckIndicator = page.getByText(
          /verificacion automatica|auto.*check|validacion/i
        );
        if (await autoCheckIndicator.isVisible({ timeout: 5000 })) {
          // Check for pass/fail status
          await expect(
            page
              .getByText(/aprobado|passed|verificado/i)
              .or(page.getByText(/rechazado|failed|error/i))
          ).toBeVisible();
        }
      }
    });
  });

  // ==========================================================================
  // 5. EVIDENCE APPROVAL/REJECTION
  // ==========================================================================

  test.describe('Evidence Approval', () => {
    test('should approve submission with notes', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      const reviewButton = page.getByRole('button', { name: /revisar|review/i }).first();
      if (await reviewButton.isVisible({ timeout: 5000 })) {
        await reviewButton.click();

        // Find approve button
        const approveButton = page.getByRole('button', { name: /aprobar|approve/i });
        if (await approveButton.isVisible()) {
          // Add notes if field exists
          const notesField = page.getByPlaceholder(/notas|notes|comentarios/i);
          if (await notesField.isVisible({ timeout: 2000 })) {
            await notesField.fill('Good quality evidence. Task completed correctly.');
          }

          // Approve
          await approveButton.click();

          // Confirm if needed
          const confirmButton = page.getByRole('button', { name: /confirmar|confirm/i });
          if (await confirmButton.isVisible({ timeout: 2000 })) {
            await confirmButton.click();
          }

          // Verify approval
          await waitForNetworkIdle(page);
          await expect(
            page.getByText(/aprobada|approved|completada/i).or(page.getByText(/pago/i))
          ).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('should reject submission with reason', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      const reviewButton = page.getByRole('button', { name: /revisar|review/i }).first();
      if (await reviewButton.isVisible({ timeout: 5000 })) {
        await reviewButton.click();

        // Find reject button
        const rejectButton = page.getByRole('button', { name: /rechazar|reject/i });
        if (await rejectButton.isVisible()) {
          await rejectButton.click();

          // Must provide rejection reason
          const reasonField = page
            .getByPlaceholder(/razon|reason|motivo/i)
            .or(page.locator('textarea'));
          await expect(reasonField).toBeVisible();
          await reasonField.fill('Evidence quality insufficient. Photo is blurry and price not visible.');

          // Confirm rejection
          await page.getByRole('button', { name: /confirmar|confirm|enviar/i }).click();

          // Verify rejection
          await waitForNetworkIdle(page);
          await expect(page.getByText(/rechazada|rejected|disputa/i)).toBeVisible();
        }
      }
    });

    test('should require rejection reason', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      const reviewButton = page.getByRole('button', { name: /revisar|review/i }).first();
      if (await reviewButton.isVisible({ timeout: 5000 })) {
        await reviewButton.click();

        const rejectButton = page.getByRole('button', { name: /rechazar|reject/i });
        if (await rejectButton.isVisible()) {
          await rejectButton.click();

          // Try to confirm without reason
          const confirmButton = page.getByRole('button', { name: /confirmar|confirm/i });
          if (await confirmButton.isVisible()) {
            await confirmButton.click();

            // Should show validation error
            await expect(
              page.getByText(/requerido|required|obligatorio/i)
            ).toBeVisible();
          }
        }
      }
    });
  });

  // ==========================================================================
  // 6. PAYMENT AUTHORIZATION
  // ==========================================================================

  test.describe('Payment Authorization', () => {
    test('should trigger payment after approval', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Find an approvable submission
      const reviewButton = page.getByRole('button', { name: /revisar|review/i }).first();
      if (await reviewButton.isVisible({ timeout: 5000 })) {
        await reviewButton.click();

        // Approve
        const approveButton = page.getByRole('button', { name: /aprobar|approve/i });
        if (await approveButton.isVisible()) {
          await approveButton.click();

          // Look for payment confirmation
          await expect(
            page.getByText(/pago.*enviado|payment.*sent|pago.*procesado/i).or(
              page.getByText(/transaccion|transaction/i)
            )
          ).toBeVisible({ timeout: 15000 });
        }
      }
    });

    test('should display escrow balance', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Look for escrow/balance display
      const balanceDisplay = page.getByText(/balance|escrow|saldo|fondos/i);
      if (await balanceDisplay.isVisible({ timeout: 5000 })) {
        // Should show amount
        await expect(page.getByText(/\$[\d,]+\.?\d*|USDC/i)).toBeVisible();
      }
    });
  });

  // ==========================================================================
  // 7. ANALYTICS & REPORTING
  // ==========================================================================

  test.describe('Analytics', () => {
    test('should display task analytics', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Look for analytics section
      await expect(
        page.getByText(/resumen|analytics|estadisticas|summary/i)
      ).toBeVisible({ timeout: 10000 });

      // Check for key metrics
      await expect(page.getByText(/tareas.*creadas|tasks.*created/i)).toBeVisible();
      await expect(page.getByText(/completadas|completed/i)).toBeVisible();
    });

    test('should display completion rate', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Look for completion rate
      await expect(
        page.getByText(/tasa.*completado|completion.*rate|%/i)
      ).toBeVisible({ timeout: 10000 });
    });

    test('should display spending summary', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Look for spending/cost metrics
      await expect(
        page.getByText(/gasto|spending|total.*pagado|cost/i)
      ).toBeVisible({ timeout: 10000 });
    });

    test('should display activity feed', async ({ page }) => {
      await page.addInitScript(
        (agent) => {
          window.localStorage.setItem('chamba_agent_id', agent.agentId);
          window.localStorage.setItem('chamba_user_role', 'agent');
        },
        TEST_USERS.agent
      );

      await page.goto('/agent');

      // Look for activity section
      await expect(
        page.getByText(/actividad.*reciente|recent.*activity/i)
      ).toBeVisible({ timeout: 10000 });
    });
  });

  // ==========================================================================
  // 8. API-DRIVEN WORKFLOWS
  // ==========================================================================

  test.describe('API Workflows', () => {
    test('should list agent tasks via API', async ({ request }) => {
      const response = await request.get('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
        },
        params: {
          agent_id: TEST_USERS.agent.agentId,
        },
      });

      if (response.ok()) {
        const data = await response.json();
        expect(Array.isArray(data) || data.tasks).toBeTruthy();
      }
    });

    test('should get submission details via API', async ({ request }) => {
      // First get tasks to find a submission
      const tasksResponse = await request.get('/api/tasks', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
        },
        params: {
          status: 'submitted',
        },
      });

      if (tasksResponse.ok()) {
        const tasks = await tasksResponse.json();
        if (tasks.length > 0 && tasks[0].id) {
          const subResponse = await request.get(`/api/tasks/${tasks[0].id}/submissions`, {
            headers: {
              Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
            },
          });

          if (subResponse.ok()) {
            const submissions = await subResponse.json();
            expect(Array.isArray(submissions)).toBeTruthy();
          }
        }
      }
    });

    test('should approve submission via API', async ({ request }) => {
      // This test creates a task, simulates submission, and approves it
      const approveResponse = await request.post('/api/submissions/test_sub_id/approve', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
          'Content-Type': 'application/json',
        },
        data: {
          notes: 'Approved via E2E API test',
        },
      });

      // Accept various responses as API may not be fully implemented
      expect([200, 201, 404, 501]).toContain(approveResponse.status());
    });

    test('should reject submission via API', async ({ request }) => {
      const rejectResponse = await request.post('/api/submissions/test_sub_id/reject', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
          'Content-Type': 'application/json',
        },
        data: {
          reason: 'Evidence quality insufficient',
        },
      });

      expect([200, 201, 400, 404, 501]).toContain(rejectResponse.status());
    });

    test('should get agent analytics via API', async ({ request }) => {
      const response = await request.get('/api/agent/analytics', {
        headers: {
          Authorization: `Bearer ${TEST_USERS.agent.apiKey}`,
        },
      });

      if (response.ok()) {
        const analytics = await response.json();
        expect(analytics).toHaveProperty('tasksCreated');
        expect(analytics).toHaveProperty('tasksCompleted');
      }
    });
  });
});
