import { View, Text, Pressable, Switch, ScrollView, Alert, Linking } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useSettingsStore } from "../stores/settings";
import { NETWORKS } from "../constants/networks";
import { useAuth } from "../providers/AuthProvider";

export default function SettingsScreen() {
  const { t } = useTranslation();
  const { deleteAccount } = useAuth();
  const {
    language,
    notificationsEnabled,
    preferredNetwork,
    setLanguage,
    setNotificationsEnabled,
    setPreferredNetwork,
  } = useSettingsStore();

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-row items-center px-4 pt-4 pb-4">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
        </Pressable>
        <Text className="text-white text-xl font-bold">{t("profile.settings")}</Text>
      </View>

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        {/* Language */}
        <Text className="text-gray-400 text-xs font-bold mb-2 mt-4">{t("settings.language")}</Text>
        <View className="flex-row gap-3 mb-6">
          <Pressable
            className={`flex-1 rounded-2xl py-4 items-center ${
              language === "es" ? "bg-white" : "bg-surface"
            }`}
            onPress={() => setLanguage("es")}
          >
            <Text style={{ fontSize: 24 }}>{"\uD83C\uDDE8\uD83C\uDDF4"}</Text>
            <Text className={`font-bold mt-1 ${language === "es" ? "text-black" : "text-gray-400"}`}>
              {t("settings.spanish")}
            </Text>
          </Pressable>
          <Pressable
            className={`flex-1 rounded-2xl py-4 items-center ${
              language === "en" ? "bg-white" : "bg-surface"
            }`}
            onPress={() => setLanguage("en")}
          >
            <Text style={{ fontSize: 24 }}>{"\uD83C\uDDFA\uD83C\uDDF8"}</Text>
            <Text className={`font-bold mt-1 ${language === "en" ? "text-black" : "text-gray-400"}`}>
              {t("settings.english")}
            </Text>
          </Pressable>
        </View>

        {/* Notifications */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("settings.notifications")}</Text>
        <View className="bg-surface rounded-2xl px-4 py-4 mb-6 flex-row items-center justify-between">
          <View>
            <Text className="text-white font-medium">{t("settings.pushNotifications")}</Text>
            <Text className="text-gray-500 text-xs mt-0.5">
              {t("settings.pushDescription")}
            </Text>
          </View>
          <Switch
            value={notificationsEnabled}
            onValueChange={setNotificationsEnabled}
            trackColor={{ false: "#333", true: "#4ade80" }}
            thumbColor="#fff"
          />
        </View>

        {/* Preferred Network */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("settings.preferredNetwork")}</Text>
        <View className="flex-row flex-wrap gap-2 mb-6">
          {NETWORKS.map((net) => (
            <Pressable
              key={net.key}
              className={`rounded-full px-4 py-2 ${
                preferredNetwork === net.key ? "bg-white" : "bg-surface"
              }`}
              onPress={() => setPreferredNetwork(net.key)}
            >
              <Text
                className={`text-sm font-medium ${
                  preferredNetwork === net.key ? "text-black" : "text-gray-400"
                }`}
              >
                {net.name}
              </Text>
            </Pressable>
          ))}
        </View>

        {/* Legal */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("settings.legal")}</Text>
        <View className="bg-surface rounded-2xl overflow-hidden mb-6">
          <Pressable
            className="px-4 py-4 active:bg-gray-800"
            onPress={() => router.push("/legal/privacy")}
          >
            <Text className="text-white font-medium">{t("legal.privacyPolicy")}</Text>
          </Pressable>
          <View className="border-t border-gray-800/50" />
          <Pressable
            className="px-4 py-4 active:bg-gray-800"
            onPress={() => router.push("/legal/terms")}
          >
            <Text className="text-white font-medium">{t("legal.termsOfService")}</Text>
          </Pressable>
        </View>

        {/* Support */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("settings.support")}</Text>
        <Pressable
          className="bg-surface rounded-2xl px-4 py-4 mb-6"
          onPress={() => Linking.openURL("mailto:support@execution.market")}
        >
          <Text className="text-white font-medium">{t("settings.contactSupport")}</Text>
          <Text className="text-gray-500 text-xs mt-0.5">support@execution.market</Text>
        </Pressable>

        {/* Blocked Users */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("settings.blockedUsers")}</Text>
        <View className="bg-surface rounded-2xl px-4 py-4 mb-6">
          <Text className="text-white font-medium">{t("settings.manageBlocked")}</Text>
          <Text className="text-gray-500 text-xs mt-0.5">{t("settings.manageBlockedDesc")}</Text>
        </View>

        {/* About */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("settings.about")}</Text>
        <View className="bg-surface rounded-2xl px-4 py-4 mb-6">
          <Text className="text-white font-medium">Execution Market</Text>
          <Text className="text-gray-500 text-xs mt-0.5">
            Universal Execution Layer
          </Text>
          <Text className="text-gray-600 text-xs mt-2">
            Agent #2106 on Base {"\u00B7"} ERC-8004
          </Text>
        </View>

        {/* Dev Tools — only visible in development */}
        {__DEV__ && (
          <View>
            <Text className="text-gray-400 text-xs font-bold mb-2">{t("settings.dev")}</Text>
            <Pressable
              className="bg-surface rounded-2xl px-4 py-4 mb-2"
              onPress={async () => {
                await AsyncStorage.removeItem("em_onboarding_complete");
                Alert.alert(t("settings.onboardingResetTitle"), t("settings.onboardingResetMsg"));
              }}
            >
              <Text className="text-white font-medium">{t("settings.resetOnboarding")}</Text>
              <Text className="text-gray-500 text-xs mt-0.5">
                {t("settings.resetOnboardingDesc")}
              </Text>
            </Pressable>
          </View>
        )}

        {/* Delete Account */}
        <Text className="text-red-400 text-xs font-bold mb-2 mt-4">{t("settings.dangerZone")}</Text>
        <Pressable
          className="bg-red-900/20 rounded-2xl px-4 py-4 mb-2 border border-red-900/40"
          onPress={() => {
            Alert.alert(
              t("settings.deleteAccountTitle"),
              t("settings.deleteAccountMsg"),
              [
                { text: t("common.cancel"), style: "cancel" },
                {
                  text: t("settings.deleteAccountConfirm"),
                  style: "destructive",
                  onPress: () => deleteAccount(),
                },
              ]
            );
          }}
        >
          <Text className="text-red-400 font-medium">{t("settings.deleteAccount")}</Text>
          <Text className="text-red-400/60 text-xs mt-0.5">
            {t("settings.deleteAccountDesc")}
          </Text>
        </Pressable>

        <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}
