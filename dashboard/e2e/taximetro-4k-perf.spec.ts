/**
 * Phase 5.9 prep — Taxímetro performance harness.
 *
 * Quantifies frame rate and long-task count on `/demo/nyc` so we have a
 * regression baseline *before* the physical 4K monitor test. The
 * on-monitor visual test itself remains HITL (eyes from 2m, "does it
 * feel smooth"), but the FPS/jank numbers this spec captures let us
 * answer "did the last code change regress the meter?" without booting
 * up the demo rig.
 *
 * Methodology:
 *   1. Open /demo/nyc at the production base URL (or local dev via BASE_URL)
 *   2. Inject a frame-timing observer into the page via page.evaluate
 *   3. Let the page run for SAMPLE_MS — the meter's rAF extrapolation
 *      loop will fire continuously even without real SSE input because
 *      `useTaximetroStream` keeps the rAF active while the component
 *      is mounted.
 *   4. Pull the frame deltas back out, compute median + p95 + long-task count
 *   5. Assert against soft budgets (warn on regression, fail on egregious jank)
 *
 * Budgets (tuned for a modern dev laptop running unthrottled):
 *   - Median frame delta ≤ 18ms (≥55 fps)
 *   - p95 frame delta ≤ 32ms (rare jank acceptable)
 *   - Long tasks (>50ms) ≤ 3 in a 10s window
 *
 * On the 4K stage laptop the budgets may differ; tune via env vars:
 *   PERF_MEDIAN_MS_MAX, PERF_P95_MS_MAX, PERF_LONG_TASKS_MAX
 *
 * Run:
 *   cd dashboard
 *   BASE_URL=https://execution.market npx playwright test taximetro-4k-perf
 */
import { test, expect } from '@playwright/test';

const SAMPLE_MS = 10_000;
const MEDIAN_MS_MAX = Number(process.env.PERF_MEDIAN_MS_MAX ?? 18);
const P95_MS_MAX = Number(process.env.PERF_P95_MS_MAX ?? 32);
const LONG_TASKS_MAX = Number(process.env.PERF_LONG_TASKS_MAX ?? 3);

interface FrameStats {
  frames: number;
  medianMs: number;
  p95Ms: number;
  longTasks: number;
  raw: number[];
}

test('taximetro live meter holds ≥55fps median over 10s window', async ({ page }) => {
  await page.goto('/demo/nyc');

  // Wait for the meter to be on screen. The taxímetro digits live inside
  // TaskExecutionScene which is the beat-5 surface; the demo page advances
  // through beats on a timer. We pick the meter directly by its tabular
  // numeric class to avoid coupling to brittle beat-state.
  await page
    .locator('.tabular-nums')
    .first()
    .waitFor({ state: 'visible', timeout: 30_000 });

  const stats = await page.evaluate<FrameStats, number>(async (sampleMs) => {
    const deltas: number[] = [];
    let longTasks = 0;
    let last = performance.now();
    let cancelled = false;

    // PerformanceObserver for long tasks (>50ms blocking work)
    let observer: PerformanceObserver | null = null;
    try {
      observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) longTasks += 1;
        }
      });
      observer.observe({ entryTypes: ['longtask'] });
    } catch {
      // longtask entry type not supported (Firefox/some Safari versions)
    }

    const tick = () => {
      if (cancelled) return;
      const now = performance.now();
      deltas.push(now - last);
      last = now;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);

    await new Promise((r) => setTimeout(r, sampleMs));
    cancelled = true;
    observer?.disconnect();

    const sorted = [...deltas].sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)] ?? 0;
    const p95 = sorted[Math.floor(sorted.length * 0.95)] ?? 0;
    return {
      frames: deltas.length,
      medianMs: median,
      p95Ms: p95,
      longTasks,
      raw: deltas,
    };
  }, SAMPLE_MS);

  // Surface the numbers in the test report regardless of pass/fail
  console.log(
    `[perf] frames=${stats.frames} median=${stats.medianMs.toFixed(2)}ms ` +
      `p95=${stats.p95Ms.toFixed(2)}ms longTasks=${stats.longTasks} ` +
      `budget(median<=${MEDIAN_MS_MAX} p95<=${P95_MS_MAX} long<=${LONG_TASKS_MAX})`,
  );

  expect(stats.frames, 'rAF must produce frames').toBeGreaterThan(200);
  expect(
    stats.medianMs,
    `median frame delta must be <=${MEDIAN_MS_MAX}ms (≥55fps)`,
  ).toBeLessThanOrEqual(MEDIAN_MS_MAX);
  expect(
    stats.p95Ms,
    `p95 frame delta must be <=${P95_MS_MAX}ms (occasional jank ok)`,
  ).toBeLessThanOrEqual(P95_MS_MAX);
  expect(
    stats.longTasks,
    `long tasks (>50ms) must be <=${LONG_TASKS_MAX} in a 10s window`,
  ).toBeLessThanOrEqual(LONG_TASKS_MAX);
});
