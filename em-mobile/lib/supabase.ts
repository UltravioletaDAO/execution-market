import { createClient } from "@supabase/supabase-js";
import { Platform } from "react-native";

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co";
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || "placeholder";

// AsyncStorage for native, localStorage for web
let storage: any = undefined;
if (Platform.OS === "web") {
  if (typeof window !== "undefined") {
    storage = window.localStorage;
  }
} else {
  try {
    storage = require("@react-native-async-storage/async-storage").default;
  } catch {
    // Fallback: no persistent storage
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
