/**
 * Phase 0 GR-0.4 — tests for safeHref / safeSrc URL sanitizers.
 *
 * Covers every branch of the FE-005 audit finding.
 */

import { describe, it, expect } from 'vitest'
import { safeHref, safeSrc } from './safeHref'

describe('safeHref', () => {
  describe('blocked schemes', () => {
    it('blocks javascript:', () => {
      expect(safeHref('javascript:alert(1)')).toBe('#')
      expect(safeHref('JAVASCRIPT:alert(1)')).toBe('#')
      expect(safeHref('  javascript:alert(1)  ')).toBe('#')
    })

    it('blocks data:', () => {
      expect(safeHref('data:text/html,<script>alert(1)</script>')).toBe('#')
      expect(safeHref('DATA:image/png;base64,iVBOR')).toBe('#')
    })

    it('blocks vbscript:', () => {
      expect(safeHref('vbscript:msgbox(1)')).toBe('#')
    })

    it('blocks file:', () => {
      expect(safeHref('file:///etc/passwd')).toBe('#')
      expect(safeHref('file://C:/Windows/System32')).toBe('#')
    })

    it('blocks blob:', () => {
      expect(safeHref('blob:https://evil.example.com/abc')).toBe('#')
    })

    it('blocks about:', () => {
      expect(safeHref('about:blank')).toBe('#')
    })

    it('blocks control-character bypass (java\\tscript:)', () => {
      // Tab character between "java" and "script" is sometimes stripped
      // by the browser when resolving the scheme.
      expect(safeHref('java\tscript:alert(1)')).toBe('#')
      expect(safeHref('java\nscript:alert(1)')).toBe('#')
    })
  })

  describe('allowed schemes', () => {
    it('allows https', () => {
      expect(safeHref('https://execution.market/foo')).toBe(
        'https://execution.market/foo'
      )
    })

    it('allows http', () => {
      expect(safeHref('http://example.com/path')).toBe('http://example.com/path')
    })

    it('allows mailto', () => {
      // URL parser normalizes mailto: so we just check the prefix survived.
      const out = safeHref('mailto:hello@execution.market')
      expect(out).toMatch(/^mailto:/)
      expect(out).toContain('hello@execution.market')
    })
  })

  describe('relative URLs', () => {
    it('allows absolute-path relative', () => {
      expect(safeHref('/tasks/abc')).toBe('/tasks/abc')
    })

    it('allows ./relative', () => {
      expect(safeHref('./foo')).toBe('./foo')
    })

    it('allows ../relative', () => {
      expect(safeHref('../foo')).toBe('../foo')
    })
  })

  describe('empty / invalid', () => {
    it('returns # for undefined', () => {
      expect(safeHref(undefined)).toBe('#')
    })

    it('returns # for null', () => {
      expect(safeHref(null)).toBe('#')
    })

    it('returns # for empty string', () => {
      expect(safeHref('')).toBe('#')
    })

    it('returns # for whitespace-only string', () => {
      expect(safeHref('   ')).toBe('#')
    })

    it('returns # for non-string', () => {
      // @ts-expect-error - deliberately testing invalid input
      expect(safeHref(42)).toBe('#')
      // @ts-expect-error - deliberately testing invalid input
      expect(safeHref({})).toBe('#')
    })

    it('returns # for unparseable garbage', () => {
      expect(safeHref('ht!tps://%%%%')).toBe('#')
    })

    it('returns # for unknown scheme', () => {
      expect(safeHref('gopher://example.com/')).toBe('#')
      expect(safeHref('ftp://example.com/')).toBe('#')
      expect(safeHref('ssh://example.com/')).toBe('#')
    })
  })
})

describe('safeSrc', () => {
  it('allows https image URLs', () => {
    expect(safeSrc('https://cdn.execution.market/evidence/x.jpg')).toBe(
      'https://cdn.execution.market/evidence/x.jpg'
    )
  })

  it('allows http image URLs', () => {
    expect(safeSrc('http://example.com/a.png')).toBe('http://example.com/a.png')
  })

  it('blocks mailto: (not valid for src)', () => {
    expect(safeSrc('mailto:hello@x.com')).toBe('')
  })

  it('blocks javascript:', () => {
    expect(safeSrc('javascript:alert(1)')).toBe('')
  })

  it('blocks data: URIs', () => {
    expect(safeSrc('data:image/svg+xml;base64,PHN2Zw==')).toBe('')
  })

  it('blocks blob:', () => {
    // Note: blob: URLs are legitimate for client-side previews, but
    // safeSrc is for USER-SUPPLIED URLs. Local preview code that uses
    // URL.createObjectURL() must NOT pass the URL through safeSrc.
    expect(safeSrc('blob:https://example.com/abc')).toBe('')
  })

  it('returns empty string for null/undefined', () => {
    expect(safeSrc(null)).toBe('')
    expect(safeSrc(undefined)).toBe('')
    expect(safeSrc('')).toBe('')
  })

  it('allows relative URLs', () => {
    expect(safeSrc('/logo.png')).toBe('/logo.png')
    expect(safeSrc('./avatar.jpg')).toBe('./avatar.jpg')
  })

  it('returns empty string for unknown scheme', () => {
    expect(safeSrc('gopher://x/y')).toBe('')
  })

  it('returns empty string for garbage', () => {
    expect(safeSrc('not a url at all %%%')).toBe('')
  })
})
