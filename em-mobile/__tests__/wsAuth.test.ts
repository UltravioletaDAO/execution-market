/**
 * L-72 regression — the WebSocket bearer token must NOT appear in the connection
 * URL/query string (where it leaks into ALB / proxy access logs); it must travel
 * in the `Sec-WebSocket-Protocol` subprotocol handshake header instead.
 *
 * Run: npm test  (em-mobile)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildAuthProtocols,
  openAuthenticatedWebSocket,
  WS_AUTH_SENTINEL,
  WS_BEARER_PREFIX,
} from "../lib/wsAuth";

const FAKE_JWT =
  "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ3b3JrZXIifQ.s3cr3t-signature_value";

test("buildAuthProtocols carries the token in the subprotocol, not a URL", () => {
  const protocols = buildAuthProtocols(FAKE_JWT);
  assert.deepEqual(protocols, [WS_AUTH_SENTINEL, `${WS_BEARER_PREFIX}${FAKE_JWT}`]);
  // The token is present in the subprotocol payload...
  assert.ok(protocols.some((p) => p.includes(FAKE_JWT)));
});

test("buildAuthProtocols returns nothing when there is no token", () => {
  assert.deepEqual(buildAuthProtocols(""), []);
});

test("openAuthenticatedWebSocket passes the token via protocols, never the URL", () => {
  const calls: Array<{ url: string; protocols?: string | string[] }> = [];
  // Capture what the WebSocket constructor receives.
  const original = (globalThis as { WebSocket?: unknown }).WebSocket;
  class FakeWebSocket {
    constructor(url: string, protocols?: string | string[]) {
      calls.push({ url, protocols });
    }
  }
  (globalThis as { WebSocket?: unknown }).WebSocket = FakeWebSocket as unknown;

  try {
    const url = "wss://api.execution.market/ws/chat/task-123";
    openAuthenticatedWebSocket(url, FAKE_JWT);

    assert.equal(calls.length, 1);
    const call = calls[0];

    // The vulnerability: token must never be in the URL.
    assert.ok(!call.url.includes(FAKE_JWT), "token must not be in the WS URL");
    assert.ok(!call.url.includes("token="), "no token query param");
    assert.equal(call.url, url);

    // The fix: token rides in the subprotocol list.
    assert.ok(Array.isArray(call.protocols));
    assert.ok(
      (call.protocols as string[]).some((p) => p.includes(FAKE_JWT)),
      "token must travel in the subprotocol header",
    );
  } finally {
    (globalThis as { WebSocket?: unknown }).WebSocket = original;
  }
});

test("openAuthenticatedWebSocket omits protocols when unauthenticated", () => {
  const calls: Array<{ url: string; protocols?: string | string[] }> = [];
  const original = (globalThis as { WebSocket?: unknown }).WebSocket;
  class FakeWebSocket {
    constructor(url: string, protocols?: string | string[]) {
      calls.push({ url, protocols });
    }
  }
  (globalThis as { WebSocket?: unknown }).WebSocket = FakeWebSocket as unknown;

  try {
    openAuthenticatedWebSocket("wss://api.execution.market/ws/chat/task-1", "");
    assert.equal(calls.length, 1);
    assert.equal(calls[0].protocols, undefined);
  } finally {
    (globalThis as { WebSocket?: unknown }).WebSocket = original;
  }
});
