/**
 * Markdown negotiation — production smoke test.
 *
 * Validates that the CloudFront viewer-request function rewrites requests
 * carrying `Accept: text/markdown` to the canonical skill.md, while plain
 * browser requests keep receiving HTML. Runs against the deployed CDN by
 * default — override with PLAYWRIGHT_BASE_URL for a different environment.
 *
 * Run post-deploy:
 *   npx playwright test e2e/markdown-negotiation.spec.ts
 *
 * Or against a custom origin:
 *   PLAYWRIGHT_BASE_URL=https://staging.execution.market npx playwright test \
 *     e2e/markdown-negotiation.spec.ts
 */

import { test, expect } from '@playwright/test'

const BASE = process.env.PLAYWRIGHT_BASE_URL || 'https://execution.market'

test.describe('markdown negotiation (RFC 8288 / Cloudflare Markdown for Agents)', () => {
  test('root returns skill.md when Accept: text/markdown', async ({ request }) => {
    const res = await request.get(BASE + '/', {
      headers: { accept: 'text/markdown' },
    })
    expect(res.status()).toBe(200)
    const contentType = res.headers()['content-type'] || ''
    expect(contentType).toContain('text/markdown')

    const body = await res.text()
    expect(body).toContain('name: execution-market')
    expect(body).toContain('version:')
  })

  test('root returns HTML for a normal browser request', async ({ request }) => {
    const res = await request.get(BASE + '/', {
      headers: {
        accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      },
    })
    expect(res.status()).toBe(200)
    const contentType = res.headers()['content-type'] || ''
    expect(contentType).toContain('text/html')
  })

  test('unknown SPA route falls back to skill.md when Accept: text/markdown', async ({
    request,
  }) => {
    const res = await request.get(BASE + '/some/deep/agent-route', {
      headers: { accept: 'text/markdown' },
    })
    expect(res.status()).toBe(200)
    expect(res.headers()['content-type'] || '').toContain('text/markdown')
    const body = await res.text()
    expect(body).toContain('name: execution-market')
  })

  test('.well-known files are not rewritten even with Accept: text/markdown', async ({
    request,
  }) => {
    const res = await request.get(BASE + '/.well-known/mcp/server-card.json', {
      headers: { accept: 'text/markdown' },
    })
    expect(res.status()).toBe(200)
    const contentType = res.headers()['content-type'] || ''
    expect(contentType).toContain('application/json')
  })

  test('wildcard */* alone does NOT trigger markdown', async ({ request }) => {
    const res = await request.get(BASE + '/', {
      headers: { accept: '*/*' },
    })
    expect(res.status()).toBe(200)
    // Should still be HTML — wildcard is not an explicit markdown preference.
    expect(res.headers()['content-type'] || '').toContain('text/html')
  })

  test('Link header advertises discovery endpoints', async ({ request }) => {
    const res = await request.get(BASE + '/', {
      headers: { accept: 'text/html' },
    })
    const link = res.headers()['link'] || ''
    expect(link).toContain('api-catalog')
    expect(link).toContain('mcp-server-card')
    expect(link).toContain('agent-skills')
    expect(link).toContain('oauth-protected-resource')
  })
})
