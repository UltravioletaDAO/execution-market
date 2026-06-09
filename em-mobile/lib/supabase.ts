import { createClient } from "@supabase/supabase-js";
import { Platform } from "react-native";

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co";
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || "placeholder";

// Session-token storage (L-71): on native we persist the access/refresh JWTs in
// the OS-backed encrypted keystore (expo-secure-store) instead of unencrypted
// AsyncStorage; on web the browser's localStorage is used.
let storage: any = undefined;
if (Platform.OS === "web") {
  if (typeof window !== "undefined") {
    storage = window.localStorage;
  }
} else {
  try {
    storage = require("./secureStorage").SecureStorageAdapter;
  } catch {
    // Fallback: no persistent storage (never silently downgrade to plaintext
    // AsyncStorage — a missing keystore means the session is kept in memory only).
  }
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage,
    autoRefreshToken: true,
    persistSession: Platform.OS !== "web" || typeof window !== "undefined",
    detectSessionInUrl: false,
  },
});
