import { View, Text, Pressable, ActivityIndicator } from "react-native";
import { useAuth } from "../providers/AuthProvider";
import { useTranslation } from "react-i18next";

export function ConnectWalletButton() {
  const { t } = useTranslation();
  const { wallet, isAuthenticated, isLoading, logout, openAuth } = useAuth();

  if (isLoading) {
    return (
      <View className="bg-surface rounded-2xl px-6 py-4 flex-row items-center justify-center">
        <ActivityIndicator color="#ffffff" size="small" />
        <Text className="text-gray-400 ml-3 font-medium">
          {t("auth.connecting")}
        </Text>
      </View>
    );
  }

  if (isAuthenticated && wallet) {
    return (
      <Pressable
        className="bg-surface rounded-2xl px-6 py-4 flex-row items-center justify-between"
        onPress={logout}
      >
        <View>
          <Text className="text-gray-400 text-xs">{t("common.wallet")}</Text>
          <Text
            className="text-white text-sm"
            style={{ fontFamily: "monospace" }}
          >
            {wallet.slice(0, 6)}...{wallet.slice(-4)}
          </Text>
        </View>
        <Text className="text-red-500 text-sm font-medium">
          {t("auth.disconnect")}
        </Text>
      </Pressable>
    );
  }

  return (
    <View>
      <Pressable
        className="bg-white rounded-2xl px-6 py-4 items-center"
        onPress={openAuth}
      >
        <Text className="text-black font-bold text-lg">
          {t("auth.connectWallet")}
        </Text>
      </Pressable>
      <Text className="text-gray-600 text-xs text-center mt-2">
        Email, MetaMask, Coinbase, Rainbow
      </Text>
    </View>
  );
}
