// CSP hardening regression tests — security-audit-2026-06-09, finding L-53.
//
// Reproduces the vulnerability: before the fix, both the index.html <meta> CSP and
// public/_headers shipped `script-src 'self' 'unsafe-inline' 'unsafe-eval'`, which
// lets any injected inline <script> execute and permits eval()/new Function().
// These tests FAIL against that policy and PASS once script-src drops
// 'unsafe-inline'/'unsafe-eval' and allow-lists the legitimate inline scripts by
// their SHA-256 hashes.
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { describe, it, expect } from 'vitest'
import {
  computeInlineScriptHashes,
  extractExecutableInlineScripts,
} from '../../scripts/compute-csp-hashes.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const dashboardRoot = resolve(here, '..', '..')
const indexHtml = readFileSync(resolve(dashboardRoot, 'index.html'), 'utf8')
const headersFile = readFileSync(resolve(dashboardRoot, 'public', '_headers'), 'utf8')

/**
 * Pull the CSP value out of the index.html <meta http-equiv> tag.
 * The content attribute is double-quoted and the policy itself contains single
 * quotes (`'self'`, `'sha256-…'`), so match a double-quoted attribute value.
 */
function metaCsp(html: string): string {
  const m = html.match(
    /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i,
  )
  if (!m) throw new Error('No <meta> CSP found in index.html')
  return m[1]
}

/** Pull the CSP value out of the _headers file (the `Content-Security-Policy:` line). */
function headersCsp(headers: string): string {
  const line = headers
    .split('\n')
    .map((l) => l.trim())
    .find((l) => l.startsWith('Content-Security-Policy:'))
  if (!line) throw new Error('No Content-Security-Policy header in _headers')
  return line.replace(/^Content-Security-Policy:\s*/, '')
}

/** Extract a single directive's source list from a CSP string. */
function directive(csp: string, name: string): string {
  const parts = csp.split(';').map((p) => p.trim())
  const found = parts.find((p) => p === name || p.startsWith(name + ' '))
  if (!found) throw new Error(`Directive ${name} not found in CSP`)
  return found.slice(name.length).trim()
}

const sources = [
  { label: 'index.html meta CSP', csp: metaCsp(indexHtml) },
  { label: '_headers CSP', csp: headersCsp(headersFile) },
] as const

describe('CSP script-src hardening (L-53)', () => {
  for (const { label, csp } of sources) {
    describe(label, () => {
      it("does not allow 'unsafe-eval' in script-src", () => {
        expect(directive(csp, 'script-src')).not.toContain("'unsafe-eval'")
      })

      it("does not allow 'unsafe-inline' in script-src", () => {
        // A hash source makes the browser ignore 'unsafe-inline', but we assert
        // its absence so the intent is explicit and a future re-add is caught.
        expect(directive(csp, 'script-src')).not.toContain("'unsafe-inline'")
      })

      it("keeps a restrictive object-src 'none'", () => {
        expect(directive(csp, 'object-src')).toBe("'none'")
      })

      it("allows WebAssembly via 'wasm-unsafe-eval' (XMTP + World ID ship WASM)", () => {
        expect(directive(csp, 'script-src')).toContain("'wasm-unsafe-eval'")
      })

      it('allow-lists every executable inline script in index.html by hash', () => {
        const scriptSrc = directive(csp, 'script-src')
        const requiredHashes = computeInlineScriptHashes(indexHtml)
        // Sanity: index.html really does contain inline scripts to cover.
        expect(requiredHashes.length).toBeGreaterThan(0)
        for (const hash of requiredHashes) {
          expect(scriptSrc).toContain(`'${hash}'`)
        }
      })
    })
  }

  it('index.html and _headers ship the identical script-src source list', () => {
    const a = directive(metaCsp(indexHtml), 'script-src').split(/\s+/).sort()
    const b = directive(headersCsp(headersFile), 'script-src').split(/\s+/).sort()
    expect(a).toEqual(b)
  })

  it('only the two known inline scripts exist (any new one must be hashed)', () => {
    // Guards against an unhashed inline script being added without updating CSP.
    const bodies = extractExecutableInlineScripts(indexHtml)
    expect(bodies.length).toBe(2)
  })
})
