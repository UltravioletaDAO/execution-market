import { Platform } from "react-native";
if (Platform.OS !== "web") {
  try {
    require("react-native-url-polyfill/auto");
  } catch {
    // Optional polyfill
  }
}
import "../global.css";

import { useEffect, useState } from "react";
import { Stack, Redirect } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { dynamicClient } from "../lib/dynamic";
import { WalletProvider } from "../providers/WalletProvider";
import { AuthProvider, useAuth } from "../providers/AuthProvider";
import { I18nProvider } from "../providers/I18nProvider";

function RootNavigator() {
  const { isAuthenticated, isLoading, isProfileComplete } = useAuth();
  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null);

  // Re-check onboarding flag whenever auth state changes (e.g. after logout clears it)
  useEffect(() => {
    AsyncStorage.getItem("em_onboarding_complete").then((value) => {
      setOnboardingDone(value === "true");
    });
  }, [isAuthenticated, isLoading]);

  // Wait until we know onboarding state and auth state
  if (onboardingDone === null || isLoading) return null;

  // Determine redirect target:
  // 1. Not authenticated + onboarding not done → onboarding wizard
  // 2. Authenticated + profile incomplete → complete profile
  // 3. Otherwise → tabs (task list); unauthenticated users who finished
  //    onboarding land here and can connect wallet via Dynamic
  // Show onboarding wizard when user hasn't completed/skipped it
  // Flag is cleared on logout so returning users see it again
  const needsOnboarding = !onboardingDone;
  const needsProfile = isAuthenticated && !isProfileComplete;

  return (
    <>
      {/* Dynamic SDK WebView — renders in background for auth flows */}
      <dynamicClient.reactNative.WebView />

      {/* Redirect to onboarding if not completed AND not authenticated */}
      {needsOnboarding && <Redirect href="/onboarding" />}

      {/* Redirect to profile completion if authenticated but profile incomplete */}
      {!needsOnboarding && needsProfile && (
        <Redirect href="/complete-profile" />
      )}

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
  return (
    <SafeAreaProvider>
      <I18nProvider>
        <WalletProvider>
          <AuthProvider>
            <StatusBar style="light" />
            <RootNavigator />
          </AuthProvider>
        </WalletProvider>
      </I18nProvider>
    </SafeAreaProvider>
  );
}
