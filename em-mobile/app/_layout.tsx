import { Platform } from "react-native";
if (Platform.OS !== "web") {
  try {
    require("react-native-url-polyfill/auto");
  } catch {
    // Optional polyfill
  }
}
import "../global.css";

import { useEffect, useState, useCallback, useMemo, type ReactNode } from "react";
import { Stack, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import * as SplashScreen from "expo-splash-screen";
import * as SystemUI from "expo-system-ui";
import { useFonts } from "expo-font";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useReactiveClient } from "@dynamic-labs/react-hooks";
import { dynamicClient } from "../lib/dynamic";
import { WalletProvider } from "../providers/WalletProvider";
import { AuthProvider, useAuth } from "../providers/AuthProvider";
import { XMTPProvider } from "../providers/XMTPProvider";
import { I18nProvider } from "../providers/I18nProvider";

// Force black background on the native root view IMMEDIATELY
// This prevents the white flash during bundle loading in Expo Go
SystemUI.setBackgroundColorAsync("#000000").catch(() => {});

// Keep splash visible until fonts + auth are ready
// Wrapped in try-catch: fails silently on web/Expo Go (IDBDatabase timing)
try {
  SplashScreen.preventAutoHideAsync();
} catch {
  // Ignore — splash screen API may not be available in all environments
}

/**
 * Bridge component that connects AuthProvider's wallet state to XMTPProvider.
 * Must be rendered inside AuthProvider so useAuth() is available.
 *
 * Dynamic React Native SDK: `wallets` from useReactiveClient is a wallet
 * manager object with methods (signMessage, embedded, connectWallet, etc.),
 * NOT a container with userWallets[]. We use wallets.embedded.getWallet().
 */
function XMTPBridge({ children }: { children: ReactNode }) {
  const { wallet } = useAuth();
  const { wallets } = useReactiveClient(dynamicClient);

  // Debug: understand Dynamic wallet manager state
  console.log("[XMTPBridge] wallet:", wallet);
  const embeddedResult = wallets?.embedded?.getWallet?.();
  console.log("[XMTPBridge] wallets?.embedded:", JSON.stringify({
    hasWallet: wallets?.embedded?.hasWallet,
    getWallet: typeof wallets?.embedded?.getWallet,
    getWalletResult: embeddedResult ? Object.keys(embeddedResult).slice(0, 15) : null,
    getWalletAddress: embeddedResult?.address ?? "none",
    keys: wallets?.embedded ? Object.keys(wallets.embedded) : "N/A",
  }));
  console.log("[XMTPBridge] wallets?.signMessage:", typeof wallets?.signMessage);
  console.log("[XMTPBridge] wallets keys:", wallets ? Object.keys(wallets).filter(k => !k.startsWith("_")).slice(0, 15) : "null");

  const getSigner = useMemo(() => {
    if (!wallet || !wallets?.signMessage || !wallets?.embedded) {
      console.log("[XMTPBridge] getSigner=null — wallet:", !!wallet);
      return null;
    }
    console.log("[XMTPBridge] getSigner ready — wallet:", wallet, "hasEmbedded:", wallets.embedded.hasWallet);
    return async () => {
      // Get or create embedded wallet — needed as first arg to wallets.signMessage(wallet, msg)
      let embeddedWallet: any = null;
      try {
        embeddedWallet = wallets.embedded.hasWallet
          ? await wallets.embedded.getWallet()
          : null;
        if (!embeddedWallet) {
          console.log("[XMTPBridge] creating embedded wallet for XMTP signing...");
          embeddedWallet = await wallets.embedded.createWallet({ chain: "Evm" });
        }
      } catch (err) {
        console.warn("[XMTPBridge] embedded wallet unavailable:", err);
        throw new Error("Embedded wallet not available. Use Dev Mode for messaging, or connect an external wallet.");
      }
      if (!embeddedWallet) {
        throw new Error("No embedded wallet found. Use Dev Mode for messaging.");
      }
      console.log("[XMTPBridge] embedded wallet ready:", embeddedWallet?.address,
        "keys:", embeddedWallet ? Object.keys(embeddedWallet).slice(0, 15) : "null");
      // Use BaseWallet.signMessage directly — buildNativeSigner Case 5 picks this up
      if (typeof embeddedWallet.signMessage === "function") {
        return embeddedWallet; // BaseWallet with signMessage(msg) → string
      }
      // Fallback: wrap wallets.signMessage with wallet ref
      return {
        signMessage: async (message: string) => {
          console.log("[XMTPBridge] signMessage via wallets.signMessage(wallet, msg)");
          const result = await wallets.signMessage(embeddedWallet, message);
          return typeof result === "string" ? result : result?.signature ?? result;
        },
      };
    };
  }, [wallet, wallets]);

  return (
    <XMTPProvider walletAddress={wallet ?? null} getSigner={getSigner}>
      {children}
    </XMTPProvider>
  );
}

function RootNavigator() {
  const { isAuthenticated, isLoading, isProfileComplete } = useAuth();
  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null);
  const router = useRouter();

  // Re-check onboarding flag whenever auth state changes (e.g. after logout clears it)
  useEffect(() => {
    AsyncStorage.getItem("em_onboarding_complete").then((value) => {
      setOnboardingDone(value === "true");
    });
  }, [isAuthenticated, isLoading]);

  // Navigate imperatively AFTER the Stack is mounted to avoid
  // "unhandled action REPLACE" warnings from premature <Redirect> renders.
  useEffect(() => {
    if (onboardingDone === null || isLoading) return;
    if (!onboardingDone) {
      router.replace("/onboarding");
    } else if (isAuthenticated && !isProfileComplete) {
      router.replace("/complete-profile");
    }
  }, [onboardingDone, isLoading, isAuthenticated, isProfileComplete]);

  // Wait until we know onboarding state and auth state before rendering Stack
  if (onboardingDone === null || isLoading) return null;

  return (
    <>
      {/* Dynamic SDK WebView — renders in background for auth flows */}
      <dynamicClient.reactNative.WebView />

      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: "#000000" },
        }}
      >
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="onboarding" />
        <Stack.Screen name="complete-profile" />
        <Stack.Screen
          name="task/[id]"
          options={{ presentation: "modal" }}
        />
        <Stack.Screen
          name="submit/[taskId]"
          options={{ presentation: "fullScreenModal" }}
        />
        <Stack.Screen
          name="review/[taskId]"
          options={{ presentation: "modal" }}
        />
        <Stack.Screen
          name="edit-profile"
          options={{ presentation: "modal" }}
        />
        <Stack.Screen
          name="agent/[id]"
          options={{ presentation: "modal" }}
        />
        <Stack.Screen
          name="messages/[threadId]"
          options={{ presentation: "modal" }}
        />
        <Stack.Screen name="ratings" />
        <Stack.Screen name="settings" />
        <Stack.Screen
          name="about"
          options={{ presentation: "modal" }}
        />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    "RobotoMono-Regular": require("../assets/fonts/RobotoMono-Regular.ttf"),
    "RobotoMono-Medium": require("../assets/fonts/RobotoMono-Medium.ttf"),
    "RobotoMono-SemiBold": require("../assets/fonts/RobotoMono-SemiBold.ttf"),
    "RobotoMono-Bold": require("../assets/fonts/RobotoMono-Bold.ttf"),
    "SpaceMono-Regular": require("../assets/fonts/SpaceMono-Regular.ttf"),
  });

  // Hide splash once fonts are loaded (auth state handled inside RootNavigator)
  useEffect(() => {
    if (fontsLoaded) {
      SplashScreen.hideAsync().catch(() => {});
    }
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <SafeAreaProvider>
      <I18nProvider>
        <WalletProvider>
          <AuthProvider>
            <XMTPBridge>
              <StatusBar style="light" />
              <RootNavigator />
            </XMTPBridge>
          </AuthProvider>
        </WalletProvider>
      </I18nProvider>
    </SafeAreaProvider>
  );
}
