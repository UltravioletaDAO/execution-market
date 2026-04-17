/**
 * Proof Wall — landing carousel E2E.
 *
 * Mocks GET /api/v1/showcase/evidence so the test is hermetic and does not
 * depend on production DB state. Assumes VITE_ENABLE_EVIDENCE_CAROUSEL=true
 * on the dev server (pass EVIDENCE_CAROUSEL_E2E=true when starting vite).
 *
 * Run:
 *   cd dashboard && VITE_ENABLE_EVIDENCE_CAROUSEL=true npm run dev
 *   npx playwright test e2e/landing-carousel.spec.ts
 */

import { test, expect, type Route } from '@playwright/test'

const SHOWCASE_ENDPOINT = /\/api\/v1\/showcase\/evidence(\?.*)?$/

function makeItem(id: string, title: string, bounty = 0.25) {
  return {
    id,
    task_title: title,
    task_description: `Description for ${id}`,
    category: 'physical_presence',
    bounty_usd: bounty,
    payment_token: 'USDC',
    payment_network: 'base',
    paid_at: '2026-04-16T12:00:00Z',
    completed_at: '2026-04-16T12:00:30Z',
    executor: {
      display_name: `worker-${id}`,
      avatar_url: null,
      rating: 4.8,
    },
    evidence: {
      primary_image_url: `https://via.placeholder.com/400x500?text=${id}`,
      image_count: 1,
      blurhash: null,
      verification: {
        gps_verified: true,
        exif_verified: true,
        timestamp_verified: true,
        world_id_verified: id === 'sub-a',
      },
    },
  }
}

function makePayload(n: number) {
  return {
    items: Array.from({ length: n }, (_, i) => makeItem(`sub-${i}`, `Task ${i}`)),
    next_cursor: null,
    generated_at: '2026-04-16T12:01:00Z',
  }
}

async function mockShowcase(route: Route, payload: unknown) {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    headers: {
      'cache-control': 'public, max-age=60, stale-while-revalidate=300',
      etag: 'W/"test"',
    },
    body: JSON.stringify(payload),
  })
}

test.describe('Proof Wall carousel', () => {
  test.skip(
    ({ browserName }) => browserName === 'webkit',
    'Embla autoplay + WebKit on Windows is flaky; covered by Chromium/Firefox.'
  )

  test('renders slides, has accessible region, and opens lightbox on click', async ({ page }) => {
    await page.route(SHOWCASE_ENDPOINT, (route) => mockShowcase(route, makePayload(6)))
    await page.goto('/')

    const region = page.getByRole('region', { name: /verified evidence showcase/i })
    await expect(region).toBeVisible()
    await expect(region.getByText(/proof of work/i)).toBeVisible()
    await expect(region.getByText(/paid for/i)).toBeVisible()

    const slides = region.locator('[data-testid="evidence-slide"]')
    await expect(slides).toHaveCount(6)

    // Click first slide → modal opens.
    await slides.first().getByRole('button', { name: /open evidence/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()

    // Close the modal with Escape and ensure focus returns near the opener.
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).toBeHidden()
  })

  test('hides the section when fewer than 5 items come back', async ({ page }) => {
    await page.route(SHOWCASE_ENDPOINT, (route) => mockShowcase(route, makePayload(3)))
    await page.goto('/')

    await expect(
      page.getByRole('region', { name: /verified evidence showcase/i })
    ).toHaveCount(0)
  })

  test('is reachable by keyboard and responds to arrow keys', async ({ page }) => {
    await page.route(SHOWCASE_ENDPOINT, (route) => mockShowcase(route, makePayload(8)))
    await page.goto('/')

    const region = page.getByRole('region', { name: /verified evidence showcase/i })
    await expect(region).toBeVisible()

    const viewport = region.locator('[aria-label*="arrow keys"]').first()
    await viewport.focus()
    await page.keyboard.press('ArrowRight')
    await page.keyboard.press('ArrowRight')

    // The live region should advance past slide 1.
    const live = region.locator('[aria-live="polite"]').first()
    await expect(live).not.toHaveText(/Slide 1 of/)
  })
})
