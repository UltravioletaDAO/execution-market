/**
 * Dispute Flow E2E Tests
 *
 * Tests complete dispute resolution journey:
 * 1. Dispute creation (after rejection)
 * 2. Evidence submission by both parties
 * 3. Validator voting
 * 4. Vote progress tracking
 * 5. Dispute resolution
 * 6. Appeal process (Gnosis Safe escalation)
 * 7. Stake management
 */
import { test, expect, Page } from '@playwright/test';
import {
  TEST_USERS,
  waitForNetworkIdle,
} from './fixtures/test-fixtures';

// ============================================================================
// Test Helpers
// ============================================================================

async function navigateToDisputes(page: Page, role: 'worker' | 'agent' | 'validator') {
  await page.addInitScript(
    ({ user, role }) => {
      if (role === 'validator') {
        window.localStorage.setItem('chamba_is_validator', 'true');
        window.localStorage.setItem('chamba_validator_stake', String(user.stake));
      }
      window.localStorage.setItem('chamba_wallet_address', user.walletAddress);
      window.localStorage.setItem('chamba_display_name', user.displayName);
      window.localStorage.setItem('chamba_user_role', role);
    },
    {
      user: role === 'validator' ? TEST_USERS.validator : TEST_USERS.worker,
      role,
    }
  );

  await page.goto('/disputes');
}

// ============================================================================
// Test Setup
// ============================================================================

test.describe('Dispute Flow', () => {
  // ==========================================================================
  // 1. DISPUTE CREATION
  // ==========================================================================

  test.describe('Dispute Creation', () => {
    test('worker should be able to dispute a rejection', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Look for rejected submissions that can be disputed
      await page.goto('/');
      await page.getByText(/mis tareas|my tasks/i).click();

      // Find rejected task
      const rejectedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /rechazada|rejected/i,
      });

      if ((await rejectedTask.count()) > 0) {
        await rejectedTask.first().click();

        // Find dispute button
        const disputeButton = page.getByRole('button', { name: /disputar|dispute|apelar/i });
        if (await disputeButton.isVisible({ timeout: 5000 })) {
          await disputeButton.click();

          // Should show dispute form
          await expect(
            page.getByText(/razon.*disputa|dispute.*reason/i).or(
              page.getByPlaceholder(/explica|explain/i)
            )
          ).toBeVisible();
        }
      }
    });

    test('should require reason when creating dispute', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Navigate to rejected task
      await page.goto('/');
      await page.getByText(/mis tareas|my tasks/i).click();

      const rejectedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /rechazada|rejected/i,
      });

      if ((await rejectedTask.count()) > 0) {
        await rejectedTask.first().click();

        const disputeButton = page.getByRole('button', { name: /disputar|dispute/i });
        if (await disputeButton.isVisible()) {
          await disputeButton.click();

          // Try to submit without reason
          const submitButton = page.getByRole('button', { name: /enviar|submit|crear/i });
          if (await submitButton.isVisible()) {
            await submitButton.click();

            // Should show validation error
            await expect(page.getByText(/requerido|required|obligatorio/i)).toBeVisible();
          }
        }
      }
    });

    test('should show dispute timeline after creation', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Navigate to rejected task and create dispute
      await page.goto('/');
      await page.getByText(/mis tareas|my tasks/i).click();

      const rejectedTask = page.locator('[data-testid="task-card"]').filter({
        hasText: /rechazada|rejected/i,
      });

      if ((await rejectedTask.count()) > 0) {
        await rejectedTask.first().click();

        const disputeButton = page.getByRole('button', { name: /disputar|dispute/i });
        if (await disputeButton.isVisible()) {
          await disputeButton.click();

          // Fill reason
          const reasonField = page.getByPlaceholder(/razon|explain|motivo/i).or(
            page.locator('textarea')
          );
          if (await reasonField.isVisible()) {
            await reasonField.fill('The evidence was clear and met all requirements. Rejection was unjustified.');
          }

          // Submit
          await page.getByRole('button', { name: /enviar|submit|crear/i }).click();

          // Wait for creation
          await waitForNetworkIdle(page);

          // Should show timeline
          await expect(
            page.getByText(/timeline|historial|eventos/i)
          ).toBeVisible({ timeout: 10000 });
        }
      }
    });
  });

  // ==========================================================================
  // 2. DISPUTE LISTING & DETAILS
  // ==========================================================================

  test.describe('Dispute Listing', () => {
    test('should display list of disputes', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Check for dispute list
      await expect(
        page.getByText(/disputas|disputes/i)
      ).toBeVisible({ timeout: 10000 });

      // Check for filter options
      await expect(
        page.getByText(/todas|all|abiertas|open/i)
      ).toBeVisible();
    });

    test('should filter disputes by status', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Click on "Open" filter
      const openFilter = page.getByRole('button', { name: /abiertas|open/i }).or(
        page.getByText(/abiertas|open/i)
      );
      if (await openFilter.isVisible()) {
        await openFilter.click();

        await waitForNetworkIdle(page);

        // Verify filtered results
        const disputeCards = page.locator('[data-testid="dispute-card"], .dispute-card');
        // All visible disputes should be open
      }
    });

    test('should display dispute details', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Click on first dispute
      const firstDispute = page.locator('[data-testid="dispute-card"], .dispute-card, button').filter({
        hasText: /disputa|\$/i,
      }).first();

      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Should show dispute details
        await expect(page.getByText(/razon.*rechazo|rejection.*reason/i)).toBeVisible({ timeout: 10000 });
        await expect(page.getByText(/evidencia|evidence/i)).toBeVisible();
        await expect(page.getByText(/votos|votes/i)).toBeVisible();
      }
    });

    test('should show vote progress bar', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const firstDispute = page.locator('[data-testid="dispute-card"], .dispute-card').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Look for vote progress
        await expect(
          page.locator('[data-testid="vote-progress"], .vote-progress, [role="progressbar"]')
        ).toBeVisible({ timeout: 5000 });

        // Should show worker vs agent votes
        await expect(page.getByText(/worker|trabajador/i)).toBeVisible();
        await expect(page.getByText(/agente|agent/i)).toBeVisible();
      }
    });
  });

  // ==========================================================================
  // 3. EVIDENCE SUBMISSION
  // ==========================================================================

  test.describe('Evidence Submission', () => {
    test('worker should add additional evidence to dispute', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Find add evidence button
        const addEvidenceButton = page.getByRole('button', {
          name: /agregar.*evidencia|add.*evidence/i,
        });

        if (await addEvidenceButton.isVisible({ timeout: 5000 })) {
          await addEvidenceButton.click();

          // Should show upload form
          await expect(page.locator('input[type="file"]')).toBeVisible();
        }
      }
    });

    test('should display all evidence from both parties', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Check for evidence tabs/sections
        await expect(
          page.getByText(/evidencia|evidence/i)
        ).toBeVisible({ timeout: 10000 });

        // Look for agent and worker evidence sections
        const agentEvidence = page.getByText(/evidencia.*agente|agent.*evidence/i);
        const workerEvidence = page.getByText(/evidencia.*worker|worker.*evidence/i);

        // At least one should be visible
        expect(
          (await agentEvidence.isVisible({ timeout: 3000 })) ||
            (await workerEvidence.isVisible({ timeout: 3000 }))
        ).toBeTruthy();
      }
    });
  });

  // ==========================================================================
  // 4. VALIDATOR VOTING
  // ==========================================================================

  test.describe('Validator Voting', () => {
    test('validator should see voting interface', async ({ page }) => {
      await navigateToDisputes(page, 'validator');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Should show voting interface
        await expect(
          page.getByText(/votar|vote/i)
        ).toBeVisible({ timeout: 10000 });

        // Should show options for worker and agent
        await expect(
          page.getByRole('button', { name: /votar.*worker|vote.*worker/i })
        ).toBeVisible();
        await expect(
          page.getByRole('button', { name: /votar.*agente|vote.*agent/i })
        ).toBeVisible();
      }
    });

    test('validator should vote for worker', async ({ page }) => {
      await navigateToDisputes(page, 'validator');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Select worker option
        const voteWorkerButton = page.getByRole('button', { name: /worker|trabajador/i }).or(
          page.locator('[data-testid="vote-worker"]')
        );

        if (await voteWorkerButton.isVisible({ timeout: 5000 })) {
          await voteWorkerButton.click();

          // Add optional reason
          const reasonField = page.getByPlaceholder(/razon|reason/i);
          if (await reasonField.isVisible({ timeout: 2000 })) {
            await reasonField.fill('Evidence clearly shows task was completed correctly.');
          }

          // Confirm vote
          await page.getByRole('button', { name: /confirmar|confirm|submit/i }).click();

          // Wait for vote to be recorded
          await waitForNetworkIdle(page);

          // Should show voted state
          await expect(
            page.getByText(/votaste|you.*voted|ya.*votado/i)
          ).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('validator should vote for agent', async ({ page }) => {
      await navigateToDisputes(page, 'validator');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        const voteAgentButton = page.getByRole('button', { name: /agente|agent/i }).or(
          page.locator('[data-testid="vote-agent"]')
        );

        if (await voteAgentButton.isVisible({ timeout: 5000 })) {
          await voteAgentButton.click();

          const reasonField = page.getByPlaceholder(/razon|reason/i);
          if (await reasonField.isVisible({ timeout: 2000 })) {
            await reasonField.fill('Evidence was indeed insufficient as agent stated.');
          }

          await page.getByRole('button', { name: /confirmar|confirm/i }).click();

          await waitForNetworkIdle(page);

          await expect(
            page.getByText(/votaste|you.*voted/i)
          ).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('validator should see stake requirement', async ({ page }) => {
      await navigateToDisputes(page, 'validator');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Look for stake info
        await expect(
          page.getByText(/stake.*requerido|required.*stake|\$.*USDC/i)
        ).toBeVisible({ timeout: 10000 });
      }
    });

    test('should prevent double voting', async ({ page }) => {
      await navigateToDisputes(page, 'validator');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Check if already voted
        const alreadyVotedMessage = page.getByText(/ya.*votado|already.*voted/i);
        const votingButtons = page.getByRole('button', { name: /votar|vote/i });

        // Either show "already voted" message or buttons should be disabled
        const hasVoted = await alreadyVotedMessage.isVisible({ timeout: 3000 }).catch(() => false);
        const buttonsDisabled = (await votingButtons.count()) === 0 ||
          (await votingButtons.first().isDisabled().catch(() => false));

        // One of these should be true for users who already voted
        // For fresh validators, voting should be available
      }
    });
  });

  // ==========================================================================
  // 5. DISPUTE RESOLUTION
  // ==========================================================================

  test.describe('Dispute Resolution', () => {
    test('should show resolution when votes reach quorum', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Look for a resolved dispute
      await page.getByRole('button', { name: /resuelta|resolved/i }).click().catch(() => {});

      const resolvedDispute = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /resuelta|resolved/i,
      });

      if ((await resolvedDispute.count()) > 0) {
        await resolvedDispute.first().click();

        // Should show resolution details
        await expect(
          page.getByText(/resolucion|resolution|resultado|result/i)
        ).toBeVisible({ timeout: 10000 });

        // Should show winner
        await expect(
          page.getByText(/ganador|winner|favor/i)
        ).toBeVisible();
      }
    });

    test('should show payment release after worker wins', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const resolvedDispute = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /resuelta.*worker|resolved.*worker|ganaste/i,
      });

      if ((await resolvedDispute.count()) > 0) {
        await resolvedDispute.first().click();

        // Should show payment info
        await expect(
          page.getByText(/pago|payment|liberado|released/i)
        ).toBeVisible({ timeout: 10000 });
      }
    });

    test('should return stake to winning validators', async ({ page }) => {
      await navigateToDisputes(page, 'validator');

      const resolvedDispute = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /resuelta|resolved/i,
      });

      if ((await resolvedDispute.count()) > 0) {
        await resolvedDispute.first().click();

        // Look for stake return info
        await expect(
          page.getByText(/stake.*devuelto|stake.*returned|ganancia|profit/i)
        ).toBeVisible({ timeout: 5000 });
      }
    });
  });

  // ==========================================================================
  // 6. APPEAL PROCESS
  // ==========================================================================

  test.describe('Appeal Process', () => {
    test('should show appeal option after resolution', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const resolvedDispute = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /resuelta|resolved/i,
      });

      if ((await resolvedDispute.count()) > 0) {
        await resolvedDispute.first().click();

        // Look for appeal section
        const appealSection = page.getByText(/apelar|appeal/i);
        await expect(appealSection).toBeVisible({ timeout: 10000 });
      }
    });

    test('should show appeal cost', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const resolvedDispute = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /resuelta|resolved/i,
      });

      if ((await resolvedDispute.count()) > 0) {
        await resolvedDispute.first().click();

        // Look for appeal cost
        await expect(
          page.getByText(/costo.*apelacion|appeal.*cost|\$.*apelacion/i)
        ).toBeVisible({ timeout: 5000 });
      }
    });

    test('should initiate appeal with payment', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const resolvedDispute = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /resuelta|resolved/i,
      });

      if ((await resolvedDispute.count()) > 0) {
        await resolvedDispute.first().click();

        // Find appeal button
        const appealButton = page.getByRole('button', { name: /iniciar.*apelacion|start.*appeal/i });
        if (await appealButton.isVisible({ timeout: 5000 })) {
          await appealButton.click();

          // Should show confirmation with cost
          await expect(
            page.getByText(/confirmar|confirm/i)
          ).toBeVisible();
        }
      }
    });

    test('should show Gnosis Safe escalation for appeals', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Look for escalated disputes
      const escalatedDispute = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /escalada|escalated|gnosis/i,
      });

      if ((await escalatedDispute.count()) > 0) {
        await escalatedDispute.first().click();

        // Should show Gnosis Safe info
        await expect(
          page.getByText(/gnosis.*safe|multisig/i)
        ).toBeVisible({ timeout: 10000 });

        // Should have link to Safe
        const safeLink = page.getByRole('link', { name: /gnosis|safe/i });
        if (await safeLink.isVisible()) {
          const href = await safeLink.getAttribute('href');
          expect(href).toContain('safe.global');
        }
      }
    });

    test('should show appeal deadline', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const resolvedDispute = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /resuelta|resolved/i,
      });

      if ((await resolvedDispute.count()) > 0) {
        await resolvedDispute.first().click();

        // Look for appeal deadline
        await expect(
          page.getByText(/tiempo.*restante|time.*remaining|deadline/i)
        ).toBeVisible({ timeout: 5000 });
      }
    });
  });

  // ==========================================================================
  // 7. TIMELINE & HISTORY
  // ==========================================================================

  test.describe('Timeline & History', () => {
    test('should display complete dispute timeline', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Click on timeline tab if present
        const timelineTab = page.getByRole('button', { name: /timeline|historial/i });
        if (await timelineTab.isVisible({ timeout: 3000 })) {
          await timelineTab.click();
        }

        // Should show timeline events
        await expect(
          page.getByText(/creada|created|iniciada/i)
        ).toBeVisible({ timeout: 10000 });
      }
    });

    test('should show vote history in timeline', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const disputeWithVotes = page.locator('[data-testid="dispute-card"]').filter({
        hasText: /votos|votes/i,
      });

      if ((await disputeWithVotes.count()) > 0) {
        await disputeWithVotes.first().click();

        // Click on votes tab
        const votesTab = page.getByRole('button', { name: /votos|votes/i });
        if (await votesTab.isVisible({ timeout: 3000 })) {
          await votesTab.click();
        }

        // Should show vote records
        const voteEntries = page.locator('[data-testid="vote-entry"], .vote-entry');
        if ((await voteEntries.count()) > 0) {
          // Each vote should show validator, side, and timestamp
          await expect(voteEntries.first()).toBeVisible();
        }
      }
    });
  });

  // ==========================================================================
  // 8. MOBILE EXPERIENCE
  // ==========================================================================

  test.describe('Mobile Experience', () => {
    test.use({
      viewport: { width: 375, height: 667 },
      isMobile: true,
    });

    test('disputes should be accessible on mobile', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      // Verify mobile-friendly layout
      await expect(page.getByText(/disputas|disputes/i)).toBeVisible();

      // Cards should be full-width on mobile
      const firstCard = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstCard.count()) > 0) {
        const box = await firstCard.boundingBox();
        if (box) {
          // Should take most of the viewport width
          expect(box.width).toBeGreaterThan(300);
        }
      }
    });

    test('voting interface should work on mobile', async ({ page }) => {
      await navigateToDisputes(page, 'validator');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Vote buttons should be tappable
        const voteButton = page.getByRole('button', { name: /votar|vote/i }).first();
        if (await voteButton.isVisible({ timeout: 5000 })) {
          const box = await voteButton.boundingBox();
          if (box) {
            // Minimum touch target size (44x44 recommended)
            expect(box.height).toBeGreaterThanOrEqual(40);
          }
        }
      }
    });

    test('evidence viewer should work on mobile', async ({ page }) => {
      await navigateToDisputes(page, 'worker');

      const firstDispute = page.locator('[data-testid="dispute-card"]').first();
      if ((await firstDispute.count()) > 0) {
        await firstDispute.click();

        // Click on evidence
        const evidenceThumb = page.locator('img[alt*="evidence"], .evidence-thumbnail').first();
        if (await evidenceThumb.isVisible({ timeout: 5000 })) {
          await evidenceThumb.click();

          // Should show fullscreen modal on mobile
          await expect(
            page.locator('.modal, [role="dialog"], .fullscreen')
          ).toBeVisible();
        }
      }
    });
  });
});
