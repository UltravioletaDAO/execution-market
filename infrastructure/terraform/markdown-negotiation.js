// CloudFront Function — Markdown negotiation for AI agents.
// Runtime: cloudfront-js-2.0 (ECMAScript 5.1-ish, no fetch, 1ms budget).
//
// Contract: when a client sends `Accept: text/markdown` *explicitly* (not via
// the `*/*` wildcard that every browser includes), rewrite the request URI to
// the canonical markdown representation of the requested page.
//
// Why: Cloudflare's Markdown for Agents convention + agent-readiness scanners
// probe `/` with `Accept: text/markdown` and expect `Content-Type: text/markdown`
// back. The dashboard is a static SPA — we don't render HTML server-side — so
// we redirect agents to skill.md (the canonical machine-readable description
// of the platform). Browsers keep receiving index.html because they don't
// list text/markdown explicitly.
//
// Route map: explicit SPA paths get their topical skill document; every other
// path falls through to the full skill.md. skill.md is pre-uploaded to S3 with
// Content-Type: text/markdown by .github/workflows/deploy.yml — no response
// transformation needed here.

function handler(event) {
    var request = event.request;
    var acceptHeader = request.headers.accept;
    if (!acceptHeader || !acceptHeader.value) {
        return request;
    }

    // Detect explicit text/markdown (case-insensitive). We intentionally ignore
    // the */* wildcard — every browser sends it, and rewriting every browser
    // request to .md would break the site.
    var accept = acceptHeader.value.toLowerCase();
    var wantsMarkdown = false;
    var parts = accept.split(',');
    for (var i = 0; i < parts.length; i++) {
        var mediaType = parts[i].split(';')[0].trim();
        if (mediaType === 'text/markdown') {
            wantsMarkdown = true;
            break;
        }
    }
    if (!wantsMarkdown) {
        return request;
    }

    // Explicit SPA route -> markdown mapping. Extend this when we publish
    // per-page markdown snapshots.
    var routeMap = {
        '/': '/skill.md',
        '/developers': '/workflows.md',
        '/workflows': '/workflows.md',
        '/about': '/skill-lite.md',
        '/skill': '/skill.md'
    };

    var uri = request.uri;
    // Strip trailing slash for lookup (except root).
    var lookupKey = uri;
    if (lookupKey.length > 1 && lookupKey.charAt(lookupKey.length - 1) === '/') {
        lookupKey = lookupKey.substring(0, lookupKey.length - 1);
    }

    if (routeMap[lookupKey]) {
        request.uri = routeMap[lookupKey];
    } else if (uri.indexOf('/.well-known/') === 0 || uri.indexOf('/assets/') === 0) {
        // Don't rewrite discovery/asset paths — they have their own MIME types.
        return request;
    } else {
        // Unknown SPA route + Accept: text/markdown -> serve the canonical skill.
        // This keeps agents productive for any URL they probe. Per-page
        // markdown snapshots can replace this fallback later.
        request.uri = '/skill.md';
    }

    return request;
}
