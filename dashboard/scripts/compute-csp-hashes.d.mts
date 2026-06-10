// Type declarations for compute-csp-hashes.mjs (imported by src/security/csp.test.ts).
// Keep in sync with the runtime exports in compute-csp-hashes.mjs.

/** Bodies of executable inline <script> blocks in the given HTML (JSON-LD excluded). */
export function extractExecutableInlineScripts(html: string): string[]

/** CSP source token (`sha256-...`) for one inline script body. */
export function cspHashFor(body: string): string

/** CSP hash source tokens for every executable inline script in the given HTML. */
export function computeInlineScriptHashes(html: string): string[]
