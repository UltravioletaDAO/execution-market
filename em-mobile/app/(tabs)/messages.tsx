import { View, Text, FlatList, TouchableOpacity, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { useXMTP } from "../../providers/XMTPProvider";
import { useConversations, type ConversationPreview } from "../../hooks/useConversations";
import { ConversationRow } from "../../components/messaging/ConversationRow";
import { dynamicClient } from "../../lib/dynamic";

export default function MessagesScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  const { isConnected, isConnecting, connect, connectDev, error, walletAddress, signerAvailable, isDevMode } = useXMTP();
  const { previews, isLoading } = useConversations();

  if (!isConnected) {
    // Wallet address known but no active connector — user logged in with email only.
    // They need to connect their wallet via Dynamic to get a signer for XMTP.
    const needsWalletConnector = !!walletAddress && !signerAvailable;

    return (
      <View className="flex-1 bg-black items-center justify-center px-6">
        <Text className="text-white text-xl font-bold mb-2">{t("messages.title")}</Text>
        <Text className="text-white/60 text-center mb-6">
          {t("messages.subtitle")}
        </Text>
        {error && !needsWalletConnector ? (
          <Text className="text-red-400 text-sm text-center mb-4">{error}</Text>
        ) : null}
        {needsWalletConnector ? (
          <>
            <Text className="text-yellow-400 text-sm text-center mb-6">
              Entraste con email. XMTP necesita tu wallet connector activo.
            </Text>
            <TouchableOpacity
              onPress={() => dynamicClient.ui.userProfile.show()}
              className="bg-white px-6 py-3 rounded-xl mb-3"
              activeOpacity={0.8}
            >
              <Text className="text-black font-semibold">Conectar Wallet</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={connectDev}
              disabled={isConnecting}
              className="border border-white/30 px-6 py-3 rounded-xl"
              activeOpacity={0.8}
            >
              {isConnecting ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text className="text-white/50 text-sm font-medium">
                  🧪 Modo Dev (identidad temporal)
                </Text>
              )}
            </TouchableOpacity>
          </>
        ) : (
          <TouchableOpacity
            onPress={connect}
            disabled={isConnecting}
            className="bg-white px-6 py-3 rounded-xl"
            activeOpacity={0.8}
          >
            {isConnecting ? (
              <ActivityIndicator color="black" />
            ) : (
              <Text className="text-black font-semibold">
                {t("messages.connect")}
              </Text>
            )}
          </TouchableOpacity>
        )}
        {isDevMode && (
          <Text className="text-yellow-400/60 text-xs text-center mt-2">
            Modo Dev activo — identidad temporal, no vinculada a tu wallet
          </Text>
        )}
        <Text className="text-white/30 text-xs text-center mt-4">
          {t("messages.browserSdkNote")}
        </Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-black">
      <View className="px-4 pt-4 pb-2">
        <Text className="text-white text-2xl font-bold">{t("messages.header")}</Text>
      </View>
      {isLoading ? (
        <ActivityIndicator color="white" className="mt-8" />
      ) : (
        <FlatList
          data={previews}
          keyExtractor={(item: ConversationPreview) => item.peerAddress}
          renderItem={({ item }: { item: ConversationPreview }) => (
            <ConversationRow
              preview={item}
              onPress={() => router.push(`/messages/${encodeURIComponent(item.peerAddress)}`)}
            />
          )}
          ListEmptyComponent={
            <Text className="text-white/40 text-center mt-8">{t("messages.empty")}</Text>
          }
        />
      )}
    </View>
  );
}
