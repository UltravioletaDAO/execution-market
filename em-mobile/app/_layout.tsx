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
 */
function XMTPBridge({ children }: { children: ReactNode }) {
  const { wallet } = useAuth();
  const { wallets } = useReactiveClient(dynamicClient);

  const getSigner = useMemo(() => {
    const primaryWallet = wallets?.userWallets?.[0];
    if (!primaryWallet) return null;
    return async () => {
      const connector = primaryWallet.connector;
      if (connector && typeof connector.getSigner === "function") {
        return connector.getSigner();
      }
      return primaryWallet;
    };
  }, [wallets?.userWallets]);

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
