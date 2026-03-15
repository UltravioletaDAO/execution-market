import { View, Text, Pressable, ScrollView, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useAuth } from "../../providers/AuthProvider";
import { ConnectWalletButton } from "../../components/ConnectWalletButton";
import { useTranslation } from "react-i18next";

export default function ProfileScreen() {
  const { t } = useTranslation();
  const { isAuthenticated, wallet, executor, logout } = useAuth();

  if (!isAuthenticated) {
    return (
      <SafeAreaView className="flex-1 bg-black">
        <View className="px-4 pt-4">
          <Text className="text-white text-2xl font-bold">{t("profile.title")}</Text>
        </View>
        <View className="flex-1 items-center justify-center px-6">
          <View className="w-24 h-24 rounded-full bg-surface items-center justify-center mb-6">
            <Text style={{ fontSize: 40 }}>👤</Text>
          </View>
          <Text className="text-gray-400 text-center text-lg mb-8">
            {t("profile.connectWallet")}
          </Text>
          <View className="w-full">
            <ConnectWalletButton />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-row items-center justify-between px-4 pt-4">
        <Text className="text-white text-2xl font-bold">{t("profile.title")}</Text>
        <Pressable onPress={() => router.push("/settings")}>
          <Text className="text-gray-400 text-2xl">&#x2699;&#xFE0F;</Text>
        </Pressable>
      </View>
      <ScrollView className="flex-1 px-4 mt-4">
        {/* Avatar + Name + Bio + Skills */}
        <View className="items-center mb-6">
          {executor?.avatar_url ? (
            <Image
              source={{ uri: executor.avatar_url }}
              className="w-24 h-24 rounded-full mb-3"
            />
          ) : (
            <View className="w-24 h-24 rounded-full bg-surface items-center justify-center mb-3">
              <Text style={{ fontSize: 40 }}>{"\uD83D\uDC64"}</Text>
            </View>
          )}
          <Text className="text-white text-xl font-bold">
            {executor?.display_name || "Worker"}
          </Text>
          <Text className="text-gray-500 text-sm font-mono mt-1">
            {wallet?.slice(0, 6)}...{wallet?.slice(-4)}
          </Text>
          {executor?.bio ? (
            <Text className="text-gray-400 text-sm text-center mt-2 px-4">
              {executor.bio}
            </Text>
          ) : null}
          {executor?.skills && executor.skills.length > 0 ? (
            <View className="flex-row flex-wrap justify-center gap-1.5 mt-3 px-2">
              {executor.skills.map((skill) => (
                <View key={skill} className="bg-surface rounded-full px-3 py-1">
                  <Text className="text-gray-400 text-xs">
                    {skill.replace("_", " ")}
                  </Text>
                </View>
              ))}
            </View>
          ) : null}
        </View>

        {/* Stats Cards */}
        <View className="flex-row gap-3 mb-6">
          <View className="flex-1 bg-surface rounded-2xl p-4 items-center">
            <Text className="text-white text-2xl font-bold">
              {executor?.reputation_score || 0}
            </Text>
            <Text className="text-gray-400 text-xs mt-1">
              {t("profile.reputation")}
            </Text>
          </View>
          <View className="flex-1 bg-surface rounded-2xl p-4 items-center">
            <Text className="text-white text-2xl font-bold">
              {executor?.tasks_completed || 0}
            </Text>
            <Text className="text-gray-400 text-xs mt-1">
              {t("profile.tasksCompleted")}
            </Text>
          </View>
        </View>

        {/* Actions */}
        <Pressable
          className="bg-surface rounded-2xl px-4 py-4 mb-3 flex-row items-center justify-between"
          onPress={() => router.push("/edit-profile")}
        >
          <Text className="text-white font-medium">{t("profile.editProfile")}</Text>
          <Text className="text-gray-500">{"\u2192"}</Text>
        </Pressable>

        <Pressable
          className="bg-surface rounded-2xl px-4 py-4 mb-3 flex-row items-center justify-between"
          onPress={() => router.push("/leaderboard")}
        >
          <Text className="text-white font-medium">{t("leaderboard.title")}</Text>
          <Text className="text-gray-500">{"\u2192"}</Text>
        </Pressable>

        <Pressable
          className="bg-surface rounded-2xl px-4 py-4 mb-3 flex-row items-center justify-between"
          onPress={() => router.push("/settings")}
        >
          <Text className="text-white font-medium">{t("profile.settings")}</Text>
          <Text className="text-gray-500">{"\u2192"}</Text>
        </Pressable>

        {/* Wallet Info */}
        <View className="mt-4 mb-4">
          <ConnectWalletButton />
        </View>

        {/* Logout */}
        <Pressable
          className="bg-red-900/30 rounded-2xl px-4 py-4 mb-8 items-center"
          onPress={logout}
        >
          <Text className="text-red-500 font-bold">{t("profile.logout")}</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}
