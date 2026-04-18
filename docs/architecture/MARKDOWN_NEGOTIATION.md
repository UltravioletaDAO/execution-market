---
date: 2026-04-17
tags:
  - type/adr
  - domain/infrastructure
  - domain/agents
status: active
related-files:
  - infrastructure/terraform/markdown-negotiation.js
  - infrastructure/terraform/dashboard-cdn.tf
  - dashboard/e2e/markdown-negotiation.spec.ts
  - dashboard/public/skill.md
---

# Markdown Negotiation for AI Agents

## Summary

`execution.market` serves HTML to browsers and Markdown to agents. The
decision point is the HTTP `Accept` header. A CloudFront viewer-request
function rewrites the request URI to a canonical Markdown document when
the client asks for `text/markdown` explicitly.

## Why

- **Agent readiness scanners** (e.g. `isitagentready.com`) probe `/` with
  `Accept: text/markdown` and mark the site red if the response is HTML.
- **Cloudflare's Markdown for Agents convention** and the emerging
  Content-Type negotiation pattern expect the same behavior.
- The dashboard is a static SPA — we do not render per-page HTML server-side,
  so we cannot generate per-page Markdown server-side. The best
  machine-readable description of the platform we already have is `skill.md`
  (the canonical skill file consumed by all MCP clients).

## Decision

Route map, implemented in `infrastructure/terraform/markdown-negotiation.js`:

| Request URI | Rewrite (if `Accept: text/markdown`) |
|---|---|
| `/` | `/skill.md` |
| `/skill` | `/skill.md` |
| `/about` | `/skill-lite.md` |
| `/developers` | `/workflows.md` |
| `/workflows` | `/workflows.md` |
| `/.well-known/*`, `/assets/*` | *(no rewrite — keep their own MIME types)* |
| Anything else | `/skill.md` (fallback) |

### Detection rule

The function looks for `text/markdown` as an **explicit** media type in the
`Accept` header. It does **not** treat `*/*` as a markdown preference — every
browser includes the wildcard, and rewriting every browser request would
break the site.

```
Accept: text/markdown                              -> rewrite to .md
Accept: text/markdown, text/html;q=0.9             -> rewrite to .md
Accept: text/html,*/*;q=0.8                        -> leave alone (HTML)
Accept: */*                                         -> leave alone (HTML)
```

### Why fallback to `skill.md` for unknown routes

An agent probing an arbitrary SPA URL with `Accept: text/markdown` is almost
certainly trying to understand the platform. Returning `406 Not Acceptable`
would be technically correct but unhelpful — the agent would likely retry
against `/` anyway. Serving `skill.md` keeps the agent productive while we
incrementally add per-page markdown snapshots.

## Alternatives considered

1. **Lambda@Edge with origin-response rewriting** — generate Markdown from
   the React app's HTML on demand. Rejected: React Router routes are
   client-rendered; origin HTML is the same `index.html` for every path,
   so there's nothing to transform.
2. **Static `.md` per route, prerendered at build time** — write a Vite
   plugin that renders each SPA page as markdown during `npm run build`.
   Deferred: worth doing for high-traffic pages (landing, developers,
   about) but the current SPA is small enough that `skill.md` covers the
   agent-relevant surface. Revisit in Phase 3 if scanners start checking
   per-page markdown.
3. **406 Not Acceptable on unknown routes** — strictly correct per RFC 7231,
   but scanners treat 406 as failure and most agents won't handle it well.

## Validation

End-to-end tests in `dashboard/e2e/markdown-negotiation.spec.ts` cover:

- Root rewrites to `skill.md` under `Accept: text/markdown`.
- Browser requests continue returning HTML.
- Unknown SPA routes fall back to `skill.md`.
- `/.well-known/*` keeps its own content type (not rewritten).
- `Accept: */*` alone is **not** treated as a markdown preference.
- `Link` headers (RFC 8288) from Phase 1 still appear on the root response.

Run post-deploy:

```bash
cd dashboard
npx playwright test e2e/markdown-negotiation.spec.ts
```

## Rollback

The function can be detached from the viewer-request event in
`dashboard-cdn.tf` without deleting the resource — remove the
`function_association` block and `terraform apply`. Rollback propagates in
~2 minutes.

## References

- RFC 7231 §5.3 — Accept header
- RFC 8288 — Web Linking (the Link header complements this negotiation)
- Cloudflare Markdown for Agents —
  `https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/`
- `isitagentready.com` scanner — probes `Accept: text/markdown` on `/`
