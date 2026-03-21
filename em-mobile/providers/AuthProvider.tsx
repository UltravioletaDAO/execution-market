import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useReactiveClient } from "@dynamic-labs/react-hooks";
import { dynamicClient } from "../lib/dynamic";
import { supabase } from "../lib/supabase";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useSettingsStore } from "../stores/settings";
import { i18n } from "./I18nProvider";

export interface Executor {
  id: string;
  wallet_address: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  email: string | null;
  skills: string[];
  languages: string[];
  reputation_score: number;
  tasks_completed: number;
  tasks_disputed: number;
  location_city: string | null;
  location_country: string | null;
  agent_type: string;
  preferred_language?: string | null;
  created_at: string;
}

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  isProfileComplete: boolean;
  wallet: string | null;
  executor: Executor | null;
  userType: "worker" | "publisher" | null;
  login: (walletAddress: string) => Promise<void>;
  logout: () => Promise<void>;
  setUserType: (type: "worker" | "publisher") => void;
  openAuth: () => void;
  refreshExecutor: () => Promise<void>;
}

// Auto-generated name pattern from get_or_create_executor (Worker_XXXXXXXX)
const AUTO_GENERATED_NAME = /^Worker_[0-9a-f]{8}$/i;

function checkProfileComplete(exec: Executor | null): boolean {
  if (!exec) return false;
  if (!exec.display_name) return false;
  if (AUTO_GENERATED_NAME.test(exec.display_name)) return false;
  return true;
}

const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  isLoading: true,
  isProfileComplete: false,
  wallet: null,
  executor: null,
  userType: null,
  login: async () => {},
  logout: async () => {},
  setUserType: () => {},
  openAuth: () => {},
  refreshExecutor: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const { auth, wallets } = useReactiveClient(dynamicClient);

  const [wallet, setWallet] = useState<string | null>(null);
  const [executor, setExecutor] = useState<Executor | null>(null);
  const [userType, setUserTypeState] = useState<"worker" | "publisher" | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);

  // Sync language preference from DB (cross-device persistence).
  // Updates local state + i18n only — does NOT write back to DB (avoids circular write).
  const syncLanguageFromExecutor = useCallback(async (exec: Executor | null) => {
    if (!exec?.preferred_language) return;
    const lang = exec.preferred_language;
    if (lang !== "es" && lang !== "en") return;
    try {
      const current = await AsyncStorage.getItem("em_language");
      if (current !== lang) {
        await AsyncStorage.setItem("em_language", lang);
        i18n.changeLanguage(lang);
        useSettingsStore.setState({ language: lang });
      }
    } catch {
      // Non-fatal
    }
  }, []);

  // Dynamic auth state
  const dynamicWallet = (() => {
    const allWallets = wallets?.userWallets;
    if (!allWallets || allWallets.length === 0) return null;
    // Prefer non-embedded wallet (matches web AuthContext behavior)
    const nonEmbedded = allWallets.find(
      (w: any) => w.address && !w.connector?.isEmbeddedWallet
    );
    if (nonEmbedded?.address) {
      console.log('[Auth] Preferring non-embedded wallet:', nonEmbedded.address);
      return nonEmbedded.address.toLowerCase();
    }
    return allWallets[0]?.address?.toLowerCase() ?? null;
  })();
  const isDynamicAuthenticated = auth?.authenticatedUser != null;

  // Extract wallet from verifiedCredentials (works even for email-only login
  // if the user previously linked a wallet on web)
  const credentialWallet = (() => {
    const creds = auth?.authenticatedUser?.verifiedCredentials;
    if (!creds || !Array.isArray(creds)) return null;
    const blockchainCred = creds.find(
      (c: { format?: string; address?: string }) =>
        c.format === "blockchain" && c.address
    );
    return blockchainCred?.address?.toLowerCase() ?? null;
  })();

  // Try embedded wallet (Dynamic creates one for email-only signups)
  const embeddedWallet = (() => {
    try {
      const w = wallets?.embedded?.getWallet?.();
      return w?.address?.toLowerCase() ?? null;
    } catch {
      return null;
    }
  })();

  // Best available wallet: direct > credential > embedded
  const resolvedWallet = dynamicWallet || credentialWallet || embeddedWallet;

  // Load saved preferences on mount
  useEffect(() => {
    loadSavedState();
  }, []);

  async function loadSavedState() {
    try {
      const [savedWallet, savedType] = await Promise.all([
        AsyncStorage.getItem("em_wallet"),
        AsyncStorage.getItem("em_user_type"),
      ]);
      if (savedType) setUserTypeState(savedType as "worker" | "publisher");

      if (savedWallet) {
        setWallet(savedWallet);
        // Fetch executor BEFORE marking loading as done
        // so isProfileComplete is accurate on first render
        try {
          await supabase.auth.signInAnonymously();
          const { data: savedExecutor } = await supabase
            .from("executors")
            .select("*")
            .eq("wallet_address", savedWallet.toLowerCase())
            .single();
          if (savedExecutor) {
            setExecutor(savedExecutor);
            syncLanguageFromExecutor(savedExecutor);
          }
        } catch {
          // Non-fatal — executor will be fetched later by Dynamic sync
        }
      }
    } finally {
      setIsLoading(false);
    }
  }

  // Sync Dynamic auth → local auth state
  useEffect(() => {
    if (isDynamicAuthenticated && resolvedWallet && resolvedWallet !== wallet) {
      // Wallet available (from userWallets, verifiedCredentials, or embedded)
      loginWithWallet(resolvedWallet);
    } else if (isDynamicAuthenticated && !resolvedWallet && !executor) {
      // Email-only auth with no linked wallet — look up by email as last resort
      const dynamicEmail = auth?.authenticatedUser?.email;
      if (dynamicEmail) {
        loginWithEmail(dynamicEmail);
      }
    } else if (!isDynamicAuthenticated && !resolvedWallet && wallet) {
      // Dynamic logged out but we still have local wallet — keep it
    }
  }, [isDynamicAuthenticated, resolvedWallet]);

  // Retry: if authenticated but no executor yet, poll for embedded wallet
  useEffect(() => {
    if (!isDynamicAuthenticated || executor) return;
    // Give Dynamic SDK time to initialize embedded wallet
    const timer = setTimeout(async () => {
      try {
        let w = wallets?.embedded?.hasWallet
          ? await wallets.embedded.getWallet()
          : null;
        if (w?.address && !executor) {
          console.log("[Auth] Late embedded wallet resolved:", w.address);
          await loginWithWallet(w.address);
        }
      } catch {
        // Non-fatal
      }
    }, 2000);
    return () => clearTimeout(timer);
  }, [isDynamicAuthenticated, executor]);

  async function loginWithEmail(email: string) {
    setIsLoading(true);
    try {
      // 1. Sign in anonymously to Supabase
      const { data: authData, error: authError } = await supabase.auth.signInAnonymously();
      if (authError) {
        console.warn("Supabase auth failed:", authError.message);
      }
      const userId = authData?.user?.id;

      // 2. Look up executor by email
      const { data: existingExecutor } = await supabase
        .from("executors")
        .select("*")
        .eq("email", email.toLowerCase())
        .single();

      if (existingExecutor) {
        setExecutor(existingExecutor);
        if (existingExecutor.wallet_address) {
          setWallet(existingExecutor.wallet_address);
          await AsyncStorage.setItem("em_wallet", existingExecutor.wallet_address);
        }
      } else {
        // No executor with this email — try to get/create embedded wallet from Dynamic
        console.log("[Auth] No executor found for email:", email, "— trying embedded wallet");
        let embeddedAddr: string | null = null;
        try {
          let w = wallets?.embedded?.hasWallet
            ? await wallets.embedded.getWallet()
            : null;
          if (!w) {
            console.log("[Auth] Creating embedded wallet for email user...");
            w = await wallets?.embedded?.createWallet?.({ chain: "Evm" });
          }
          embeddedAddr = w?.address?.toLowerCase() ?? null;
        } catch (err) {
          console.warn("[Auth] Failed to get/create embedded wallet:", err);
        }

        if (embeddedAddr && userId) {
          // Create executor with the embedded wallet
          await supabase.rpc("link_wallet_to_session", {
            p_user_id: userId,
            p_wallet_address: embeddedAddr,
            p_chain_id: 8453,
          });

          const { data: executorData } = await supabase.rpc(
            "get_or_create_executor",
            {
              p_wallet_address: embeddedAddr,
              p_display_name: `Worker_${embeddedAddr.slice(2, 10)}`,
              p_email: email.toLowerCase(),
            }
          );

          if (executorData) {
            const exec = Array.isArray(executorData) ? executorData[0] : executorData;
            if (exec?.id) {
              const { data: fullExecutor } = await supabase
                .from("executors")
                .select("*")
                .eq("id", exec.id)
                .single();
              setExecutor(fullExecutor || exec);
            }
          }
          setWallet(embeddedAddr);
          await AsyncStorage.setItem("em_wallet", embeddedAddr);
        } else {
          console.warn("[Auth] No embedded wallet available for email-only user");
        }
      }
    } catch (err) {
      console.error("[Auth] loginWithEmail error:", err);
    } finally {
      setIsLoading(false);
    }
  }

  async function loginWithWallet(walletAddress: string) {
    setIsLoading(true);
    try {
      const normalizedWallet = walletAddress.toLowerCase();

      // 1. Sign in anonymously to Supabase
      const { data: authData, error: authError } =
        await supabase.auth.signInAnonymously();
      if (authError) {
        console.warn("Supabase auth failed:", authError.message);
      }
      const userId = authData?.user?.id;

      if (userId) {
        // 2. Link wallet to session
        await supabase.rpc("link_wallet_to_session", {
          p_user_id: userId,
          p_wallet_address: normalizedWallet,
          p_chain_id: 8453,
        });

        // 3. Get or create executor
        const { data: executorData } = await supabase.rpc(
          "get_or_create_executor",
          {
            p_wallet_address: normalizedWallet,
            p_display_name: `Worker_${normalizedWallet.slice(2, 10)}`,
            p_email: null,
          }
        );

        if (executorData) {
          const exec = Array.isArray(executorData)
            ? executorData[0]
            : executorData;
          if (exec?.id) {
            // Fetch full executor profile from the executors table
            const { data: fullExecutor } = await supabase
              .from("executors")
              .select("*")
              .eq("id", exec.id)
              .single();
            if (fullExecutor) {
              setExecutor(fullExecutor);
              syncLanguageFromExecutor(fullExecutor);
            } else {
              setExecutor(exec);
              syncLanguageFromExecutor(exec);
            }
          }
        }
      }

      setWallet(normalizedWallet);
      await AsyncStorage.setItem("em_wallet", normalizedWallet);
    } catch (err) {
      console.error("[Auth] login error:", err);
    } finally {
      setIsLoading(false);
    }
  }

  const login = useCallback(async (walletAddress: string) => {
    await loginWithWallet(walletAddress);
  }, []);

  const logout = useCallback(async () => {
    try {
      await dynamicClient.auth.logout();
    } catch {
      // Dynamic might not have an active session
    }
    await supabase.auth.signOut();
    setWallet(null);
    setExecutor(null);
    setUserTypeState(null);
    await AsyncStorage.multiRemove([
      "em_wallet",
      "em_user_type",
      "em_onboarding_complete",
    ]);
  }, []);

  const setUserType = useCallback(
    (type: "worker" | "publisher") => {
      setUserTypeState(type);
      AsyncStorage.setItem("em_user_type", type);
    },
    []
  );

  const refreshExecutor = useCallback(async () => {
    const currentWallet = wallet || resolvedWallet;
    if (!currentWallet) return;
    try {
      const { data: freshExecutor } = await supabase
        .from("executors")
        .select("*")
        .eq("wallet_address", currentWallet.toLowerCase())
        .single();

      if (!freshExecutor) return;

      setExecutor(freshExecutor);
      // Sync wallet from executor if we didn't have one locally
      if (!wallet && freshExecutor.wallet_address) {
        setWallet(freshExecutor.wallet_address);
        await AsyncStorage.setItem("em_wallet", freshExecutor.wallet_address);
      }
    } catch (err) {
      console.error("[Auth] refreshExecutor error:", err);
    }
  }, [wallet, resolvedWallet]);

  const openAuth = useCallback(() => {
    dynamicClient.ui.auth.show();
  }, []);

  const isAuthenticated = !!wallet || isDynamicAuthenticated;
  const isProfileComplete = checkProfileComplete(executor);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        isProfileComplete,
        wallet: wallet || resolvedWallet,
        executor,
        userType,
        login,
        logout,
        setUserType,
        openAuth,
        refreshExecutor,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
