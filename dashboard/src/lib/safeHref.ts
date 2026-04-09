/**
 * Sanitize user-supplied URLs before rendering as href or src.
 *
 * Blocks javascript:, data:, vbscript:, file:, blob: and any scheme other
 * than http/https/mailto. Returns '#' for blocked URLs so the element
 * still renders but doesn't execute.
 *
 * Phase 0 GR-0.4. See
 *   docs/reports/security-audit-2026-04-07/specialists/SC_07_FRONTEND.md
 *   [FE-005]
 */

const ALLOWED_HREF_SCHEMES = new Set(['http:', 'https:', 'mailto:'])
const ALLOWED_SRC_SCHEMES = new Set(['http:', 'https:'])

// Schemes we explicitly refuse before parsing, because some of them
// (javascript:, data:) are interpreted by the browser in surprising
// contexts even if new URL() accepts them.
const BLOCKED_SCHEME_PREFIXES = [
  'javascript:',
  'data:',
  'vbscript:',
  'file:',
  'blob:',
  'about:',
  'chrome:',
  'chrome-extension:',
]

function isBlockedPrefix(lower: string): boolean {
  for (const prefix of BLOCKED_SCHEME_PREFIXES) {
    if (lower.startsWith(prefix)) return true
  }
  return false
}

function isRelative(url: string): boolean {
  return url.startsWith('/') || url.startsWith('./') || url.startsWith('../')
}

/**
 * Sanitize a URL for use as an <a href={...}>.
 *
 * Rules:
 *   - null/undefined/empty -> '#'
 *   - javascript:/data:/vbscript:/file:/blob: -> '#'
 *   - relative URLs (/foo, ./foo, ../foo) -> returned as-is
 *   - http/https/mailto -> returned normalized
 *   - anything else -> '#'
 */
export function safeHref(url: string | undefined | null): string {
  if (url == null) return '#'
  if (typeof url !== 'string') return '#'

  const trimmed = url.trim()
  if (trimmed === '') return '#'

  // Strip control characters that browsers might ignore when parsing the
  // scheme (CVE-style bypasses like "java\tscript:alert(1)").
  // eslint-disable-next-line no-control-regex
  const cleaned = trimmed.replace(/[\x00-\x1f\x7f]/g, '')
  const lower = cleaned.toLowerCase()

  if (isBlockedPrefix(lower)) return '#'

  if (isRelative(cleaned)) return cleaned

  // Absolute URL: parse and validate scheme.
  try {
    const parsed = new URL(cleaned)
    if (!ALLOWED_HREF_SCHEMES.has(parsed.protocol)) {
      return '#'
    }
    return parsed.toString()
  } catch {
    // Not a valid URL and not relative — refuse.
    return '#'
  }
}

/**
 * Sanitize a URL for use as <img src={...}> or <video src={...}>.
 *
 * Stricter than safeHref: mailto: is not allowed for src.
 * Returns '' for blocked URLs so the <img> renders empty instead of
 * loading an unintended document.
 */
export function safeSrc(url: string | undefined | null): string {
  if (url == null) return ''
  if (typeof url !== 'string') return ''

  const trimmed = url.trim()
  if (trimmed === '') return ''

  // eslint-disable-next-line no-control-regex
  const cleaned = trimmed.replace(/[\x00-\x1f\x7f]/g, '')
  const lower = cleaned.toLowerCase()

  if (isBlockedPrefix(lower)) return ''

  if (isRelative(cleaned)) return cleaned

  try {
    const parsed = new URL(cleaned)
    if (!ALLOWED_SRC_SCHEMES.has(parsed.protocol)) {
      return ''
    }
    return parsed.toString()
  } catch {
    return ''
  }
}
