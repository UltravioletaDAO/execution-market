/**
 * L-71 regression — Supabase session tokens must live in the encrypted keystore,
 * not unencrypted AsyncStorage, and large session blobs must survive the
 * SecureStore ~2 KB per-value cap via chunking.
 *
 * Run: npm test  (em-mobile)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  createSecureStorageAdapter,
  splitIntoChunks,
  safeKey,
  CHUNK_SIZE,
  type SecureKVBackend,
} from "../lib/secureStorageCore";

/** In-memory stand-in for the OS keystore that also enforces the ~2 KB cap. */
function fakeKeystore(maxValueBytes = 2048) {
  const store = new Map<string, string>();
  const backend: SecureKVBackend = {
    async getItemAsync(key) {
      return store.has(key) ? store.get(key)! : null;
    },
    async setItemAsync(key, value) {
      if (Buffer.byteLength(value, "utf8") > maxValueBytes) {
        // Mirrors SecureStore rejecting oversized values.
        throw new Error(`value for ${key} exceeds keystore limit`);
      }
      store.set(key, value);
    },
    async deleteItemAsync(key) {
      store.delete(key);
    },
  };
  return { store, backend };
}

test("round-trips a small token through the keystore backend", async () => {
  const { store, backend } = fakeKeystore();
  const adapter = createSecureStorageAdapter(backend);
  const key = "sb-abcd-auth-token";
  const token = "header.payload.signature";

  await adapter.setItem(key, token);
  assert.equal(await adapter.getItem(key), token);
  // The value really landed in the (encrypted) keystore backend.
  assert.equal(store.get(safeKey(key)), token);
});

test("chunks a >2KB session blob that would otherwise be rejected", async () => {
  const { store, backend } = fakeKeystore(2048);
  const adapter = createSecureStorageAdapter(backend);
  const key = "sb-abcd-auth-token";
  // A realistic Supabase session JSON with two JWTs easily exceeds 2 KB.
  const bigBlob = "x".repeat(CHUNK_SIZE * 3 + 500);

  // Writing the blob as a single value would throw in the fake keystore; the
  // adapter must chunk it instead.
  await adapter.setItem(key, bigBlob);

  // Every persisted chunk is within the keystore limit.
  for (const value of store.values()) {
    assert.ok(Buffer.byteLength(value, "utf8") <= 2048, "chunk within keystore cap");
  }
  // And it reassembles byte-for-byte on read.
  assert.equal(await adapter.getItem(key), bigBlob);
});

test("overwriting a chunked value leaves no orphan chunks", async () => {
  const { store, backend } = fakeKeystore(2048);
  const adapter = createSecureStorageAdapter(backend);
  const key = "sb-abcd-auth-token";

  await adapter.setItem(key, "y".repeat(CHUNK_SIZE * 4));
  await adapter.setItem(key, "short");

  assert.equal(await adapter.getItem(key), "short");
  // No leftover `.0`, `.1`, ... chunk keys from the larger previous value.
  const leftoverChunks = [...store.keys()].filter((k) => /\.\d+$/.test(k));
  assert.deepEqual(leftoverChunks, []);
});

test("removeItem clears the value and its chunk metadata", async () => {
  const { store, backend } = fakeKeystore(2048);
  const adapter = createSecureStorageAdapter(backend);
  const key = "sb-abcd-auth-token";

  await adapter.setItem(key, "z".repeat(CHUNK_SIZE * 2));
  await adapter.removeItem(key);

  assert.equal(await adapter.getItem(key), null);
  assert.equal(store.size, 0);
});

test("a missing chunk yields null, never a truncated token", async () => {
  const { store, backend } = fakeKeystore(2048);
  const adapter = createSecureStorageAdapter(backend);
  const key = "sb-abcd-auth-token";

  await adapter.setItem(key, "w".repeat(CHUNK_SIZE * 3));
  // Corrupt storage: drop one chunk.
  store.delete(`${safeKey(key)}.1`);

  assert.equal(await adapter.getItem(key), null);
});

test("splitIntoChunks covers the input exactly", () => {
  const input = "a".repeat(CHUNK_SIZE * 2 + 7);
  const chunks = splitIntoChunks(input);
  assert.equal(chunks.length, 3);
  assert.equal(chunks.join(""), input);
  for (const c of chunks) assert.ok(c.length <= CHUNK_SIZE);
});
