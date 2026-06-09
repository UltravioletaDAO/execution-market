/**
 * Pure chunk/reassemble logic for the encrypted Supabase token store (L-71).
 *
 * This file has NO native imports so it is unit-testable in plain Node. The
 * platform binding (expo-secure-store) lives in `secureStorage.ts`, which wires
 * `createSecureStorageAdapter` to the real OS keystore.
 *
 * SecureStore caps a single value at ~2 KB; a full Supabase session blob (access
 * + refresh JWT + user metadata) routinely exceeds that, so the adapter splits
 * large values across multiple keystore entries and reassembles them on read.
 */

// SecureStore value-size ceiling is ~2048 bytes. Stay comfortably under it so a
// multibyte-UTF-8 tail can never tip a chunk over the limit.
export const CHUNK_SIZE = 1800;
// Metadata key suffix recording how many chunks a value was split into.
const CHUNK_COUNT_SUFFIX = "__chunks";

/**
 * Minimal async key/value surface backing the adapter. `expo-secure-store`
 * satisfies it; tests inject an in-memory implementation.
 */
export interface SecureKVBackend {
  getItemAsync(key: string): Promise<string | null>;
  setItemAsync(key: string, value: string): Promise<void>;
  deleteItemAsync(key: string): Promise<void>;
}

export interface StorageAdapter {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

/**
 * SecureStore keys must match [A-Za-z0-9._-]. Supabase uses keys like
 * `sb-<ref>-auth-token` which already satisfy this, but encode defensively so an
 * unexpected key can never throw at the keystore boundary.
 */
export function safeKey(key: string): string {
  return key.replace(/[^A-Za-z0-9._-]/g, "_");
}

function chunkKey(baseKey: string, index: number): string {
  return `${baseKey}.${index}`;
}

/** Split a string into <= size-byte pieces without splitting a UTF-8 char. */
export function splitIntoChunks(value: string, size: number = CHUNK_SIZE): string[] {
  const chunks: string[] = [];
  for (let i = 0; i < value.length; i += size) {
    chunks.push(value.slice(i, i + size));
  }
  return chunks;
}

/**
 * Build a chunk-aware storage adapter over any {@link SecureKVBackend}.
 * Production calls this with `expo-secure-store`; tests pass a fake backend.
 */
export function createSecureStorageAdapter(backend: SecureKVBackend): StorageAdapter {
  async function readChunkCount(baseKey: string): Promise<number> {
    const raw = await backend.getItemAsync(`${baseKey}${CHUNK_COUNT_SUFFIX}`);
    if (!raw) return 0;
    const n = Number.parseInt(raw, 10);
    return Number.isFinite(n) && n > 0 ? n : 0;
  }

  async function clearChunks(baseKey: string): Promise<void> {
    const count = await readChunkCount(baseKey);
    const deletions: Promise<void>[] = [];
    for (let i = 0; i < count; i += 1) {
      deletions.push(backend.deleteItemAsync(chunkKey(baseKey, i)));
    }
    deletions.push(backend.deleteItemAsync(`${baseKey}${CHUNK_COUNT_SUFFIX}`));
    // Also clear any legacy single-value entry written before chunking existed.
    deletions.push(backend.deleteItemAsync(baseKey));
    await Promise.all(deletions);
  }

  return {
    async getItem(key: string): Promise<string | null> {
      const baseKey = safeKey(key);
      const count = await readChunkCount(baseKey);

      // No chunk marker — fall back to a plain single-value read (covers values
      // small enough they were never chunked, and is also the legacy path).
      if (count === 0) {
        return backend.getItemAsync(baseKey);
      }

      const parts: string[] = [];
      for (let i = 0; i < count; i += 1) {
        const part = await backend.getItemAsync(chunkKey(baseKey, i));
        if (part == null) {
          // A chunk is missing — the stored value is corrupt/partial. Treat as
          // absent (Supabase will re-auth) rather than returning a truncated token.
          return null;
        }
        parts.push(part);
      }
      return parts.join("");
    },

    async setItem(key: string, value: string): Promise<void> {
      const baseKey = safeKey(key);
      // Replace any previous representation first to avoid orphaned chunks.
      await clearChunks(baseKey);

      if (value.length <= CHUNK_SIZE) {
        await backend.setItemAsync(baseKey, value);
        return;
      }

      const chunks = splitIntoChunks(value);
      await Promise.all(
        chunks.map((chunk, i) => backend.setItemAsync(chunkKey(baseKey, i), chunk)),
      );
      await backend.setItemAsync(`${baseKey}${CHUNK_COUNT_SUFFIX}`, String(chunks.length));
    },

    async removeItem(key: string): Promise<void> {
      await clearChunks(safeKey(key));
    },
  };
}
