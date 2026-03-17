import { View, Text, FlatList, TouchableOpacity, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import * as Linking from "expo-linking";
import { useXMTP } from "../../providers/XMTPProvider";
import { useConversations, type ConversationPreview } from "../../hooks/useConversations";
import { ConversationRow } from "../../components/messaging/ConversationRow";

const WEB_APP_MESSAGES_URL = "https://execution.market/messages";

export default function MessagesScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  const { isConnected, isConnecting, connect, nativeAvailable } = useXMTP();
  const { previews, isLoading } = useConversations();

  // Native XMTP SDK requires EAS Build — show web redirect instead
  if (!nativeAvailable) {
    return (
      <View className="flex-1 bg-black items-center justify-center px-6">
        <Text className="text-white text-3xl mb-4">💬</Text>
        <Text className="text-white text-xl font-bold mb-3 text-center">
          {t("messages.webOnlyTitle")}
        </Text>
        <Text className="text-white/60 text-center mb-8 leading-6">
          {t("messages.webOnlySubtitle")}
        </Text>
        <TouchableOpacity
          onPress={() => Linking.openURL(WEB_APP_MESSAGES_URL)}
          className="bg-white px-8 py-3 rounded-xl mb-4"
          activeOpacity={0.8}
        >
          <Text className="text-black font-semibold text-base">
            {t("messages.openWebApp")}
          </Text>
        </TouchableOpacity>
        <Text className="text-white/30 text-xs text-center mt-2">
          {t("messages.webOnlyNote")}
        </Text>
      </View>
    );
  }

  if (!isConnected) {
    return (
      <View className="flex-1 bg-black items-center justify-center px-6">
        <Text className="text-white text-xl font-bold mb-2">{t("messages.title")}</Text>
        <Text className="text-white/60 text-center mb-6">
          {t("messages.subtitle")}
        </Text>
        <TouchableOpacity
          onPress={connect}
          disabled={isConnecting}
          className="bg-white px-6 py-3 rounded-xl"
          activeOpacity={0.8}
        >
          <Text className="text-black font-semibold">
            {isConnecting ? t("messages.connecting") : t("messages.connect")}
          </Text>
        </TouchableOpacity>
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
