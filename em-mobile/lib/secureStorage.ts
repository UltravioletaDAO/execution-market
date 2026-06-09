/**
 * Encrypted storage adapter for the Supabase auth client (em-mobile).
 *
 * Security-audit-2026-06-09, finding L-71: Supabase session tokens (the access
 * and refresh JWTs) were persisted in *unencrypted* AsyncStorage on native, so
 * any process or backup that can read app storage could lift a live bearer token.
 *
 * Fix: persist them in the OS-backed encrypted keystore via `expo-secure-store`
 * (iOS Keychain / Android Keystore). The chunk/reassemble logic that works around
 * SecureStore's ~2 KB per-value cap lives in `secureStorageCore.ts` (native-free,
 * unit-tested); this module only binds it to the real keystore.
 *
 * On web there is no SecureStore; the Supabase client uses `window.localStorage`
 * directly (see lib/supabase.ts), so this module is only wired in on native.
 */
import * as SecureStore from "expo-secure-store";
import {
  createSecureStorageAdapter,
  type StorageAdapter,
} from "./secureStorageCore";

export type { StorageAdapter, SecureKVBackend } from "./secureStorageCore";
export {
  createSecureStorageAdapter,
  splitIntoChunks,
  safeKey,
  CHUNK_SIZE,
} from "./secureStorageCore";

/** Production adapter, backed by the OS encrypted keystore. */
export const SecureStorageAdapter: StorageAdapter = createSecureStorageAdapter(SecureStore);

export default SecureStorageAdapter;
