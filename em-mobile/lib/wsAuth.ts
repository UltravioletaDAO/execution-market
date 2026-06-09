/**
 * WebSocket bearer-token transport for em-mobile.
 *
 * Security-audit-2026-06-09, finding L-72: the chat client appended the Supabase
 * access token to the WebSocket URL as `?token=<JWT>`. Query strings are written
 * verbatim to ALB access logs, reverse-proxy logs and crash/telemetry breadcrumbs,
 * so a live bearer token leaks into log storage on every connect.
 *
 * Fix: carry the token in the WebSocket handshake's `Sec-WebSocket-Protocol`
 * header instead of the URL. The React-Native / browser `WebSocket` constructor
 * exposes that header via its `protocols` argument, and ALBs do NOT log request
 * headers — only the request line / query — so the token no longer lands in logs.
 *
 * Wire format (server must mirror it): two subprotocol values are offered —
 *   1. the sentinel `WS_AUTH_SENTINEL` so the server can detect the scheme, and
 *   2. `${WS_BEARER_PREFIX}<token>` carrying the JWT.
 * A JWT's alphabet (A-Za-z0-9-_.) is already a valid RFC 6455 subprotocol token,
 * so no extra encoding is needed.
 */
export const WS_AUTH_SENTINEL = "em-bearer";
export const WS_BEARER_PREFIX = "bearer.";

/**
 * Build the `protocols` array to hand to `new WebSocket(url, protocols)`.
 * Returns an empty array when there is no token so callers never offer an empty
 * `bearer.` value.
 */
export function buildAuthProtocols(token: string): string[] {
  if (!token) return [];
  return [WS_AUTH_SENTINEL, `${WS_BEARER_PREFIX}${token}`];
}

/**
 * Open an authenticated WebSocket without placing the token in the URL.
 * The token travels in the subprotocol handshake header.
 */
export function openAuthenticatedWebSocket(url: string, token: string): WebSocket {
  const protocols = buildAuthProtocols(token);
  return protocols.length > 0 ? new WebSocket(url, protocols) : new WebSocket(url);
}
