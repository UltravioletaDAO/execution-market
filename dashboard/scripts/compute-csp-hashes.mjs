#!/usr/bin/env node
// Compute the SHA-256 CSP source hashes for the executable inline <script>
// blocks in index.html. Run after editing any inline script:
//
//   node scripts/compute-csp-hashes.mjs
//
// Paste the printed `'sha256-...'` values into the script-src directive of BOTH:
//   - index.html  (<meta http-equiv="Content-Security-Policy">)
//   - public/_headers  (Content-Security-Policy header)
//   - infrastructure/terraform/dashboard-cdn.tf  (CloudFront policy, owned by infra)
//
// CSP rule: <script type="application/ld+json"> is data, not script, and is NOT
// governed by script-src — it is intentionally excluded here. Only inline scripts
// that the browser executes need a hash.
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const indexHtmlPath = resolve(__dirname, '..', 'index.html')

/**
 * Extract the bodies of executable inline <script> blocks from an HTML string.
 * Skips scripts with a `src=` attribute (external) and `application/ld+json`
 * (data, exempt from script-src).
 * @param {string} html
 * @returns {string[]} inline script bodies in document order
 */
export function extractExecutableInlineScripts(html) {
  const re = /<script([^>]*)>([\s\S]*?)<\/script>/g
  const bodies = []
  let m
  while ((m = re.exec(html)) !== null) {
    const attrs = m[1]
    const body = m[2]
    if (/\ssrc\s*=/.test(attrs)) continue
    if (/application\/ld\+json/.test(attrs)) continue
    // CSP hashes the script's PARSED text content, and the HTML parser
    // normalizes CRLF/CR to LF before the text reaches the DOM — so a CRLF
    // file on disk must be hashed as LF or browsers reject the script
    // (found in production 2026-06-09: theme + SW scripts blocked).
    bodies.push(body.replace(/\r\n?/g, '\n'))
  }
  return bodies
}

/** @param {string} body */
export function cspHashFor(body) {
  return `sha256-${createHash('sha256').update(body, 'utf8').digest('base64')}`
}

export function computeInlineScriptHashes(html) {
  return extractExecutableInlineScripts(html).map(cspHashFor)
}

// CLI entrypoint
if (import.meta.url === `file://${process.argv[1]}`) {
  const html = readFileSync(indexHtmlPath, 'utf8')
  const hashes = computeInlineScriptHashes(html)
  if (hashes.length === 0) {
    console.error('No executable inline scripts found in index.html.')
    process.exit(1)
  }
  console.log('Inline-script CSP sources (paste into script-src):')
  for (const h of hashes) console.log(`  '${h}'`)
}
