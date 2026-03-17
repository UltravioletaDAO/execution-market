import { View, Text, FlatList, TouchableOpacity, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { useXMTP } from "../../providers/XMTPProvider";
import { useConversations, type ConversationPreview } from "../../hooks/useConversations";
import { ConversationRow } from "../../components/messaging/ConversationRow";

export default function MessagesScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  const { isConnected, isConnecting, connect, error } = useXMTP();
  const { previews, isLoading } = useConversations();

  if (!isConnected) {
    return (
      <View className="flex-1 bg-black items-center justify-center px-6">
        <Text className="text-white text-xl font-bold mb-2">{t("messages.title")}</Text>
        <Text className="text-white/60 text-center mb-6">
          {t("messages.subtitle")}
        </Text>
        {error ? (
          <Text className="text-red-400 text-sm text-center mb-4">{error}</Text>
        ) : null}
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
