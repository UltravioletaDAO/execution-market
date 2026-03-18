import { useLocalSearchParams, useRouter } from "expo-router";
import { View, Text, FlatList, KeyboardAvoidingView, Platform, TouchableOpacity } from "react-native";
import { useRef } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { useXMTP } from "../../providers/XMTPProvider";
import { useMessages, type XMTPMessage } from "../../hooks/useMessages";
import { MessageBubbleNative } from "../../components/messaging/MessageBubbleNative";
import { MessageInputNative } from "../../components/messaging/MessageInputNative";

export default function MessageThreadScreen() {
  const { threadId } = useLocalSearchParams<{ threadId: string }>();
  const router = useRouter();
  const { t } = useTranslation();
  const insets = useSafeAreaInsets();
  const { client } = useXMTP();
  const peerAddress = threadId ? decodeURIComponent(threadId) : null;
  const { messages, isLoading, isSending, sendMessage } = useMessages(peerAddress);
  const flatListRef = useRef<FlatList>(null);

  // If peerAddress is an ETH address show 0x1234...abcd, else abbreviate convo ID
  const isEthAddress = peerAddress ? /^0x[0-9a-fA-F]{40}$/.test(peerAddress) : false;
  const shortAddr = peerAddress
    ? isEthAddress
      ? `${peerAddress.slice(0, 6)}...${peerAddress.slice(-4)}`
      : `Conv ${peerAddress.slice(0, 4)}...${peerAddress.slice(-4)}`
    : "";

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: "#000", paddingTop: insets.top }}
      behavior={Platform.OS === "ios" ? "padding" : "padding"}
      keyboardVerticalOffset={0}
    >
      {/* Header */}
      <View className="flex-row items-center px-4 py-3 border-b border-white/10">
        <TouchableOpacity onPress={() => router.back()} className="mr-3">
          <Text className="text-white/60 text-2xl">{"<"}</Text>
        </TouchableOpacity>
        <View className="w-8 h-8 rounded-full bg-white/10 items-center justify-center mr-2">
          <Text className="text-white/60 text-xs font-mono">
            {peerAddress?.slice(2, 4).toUpperCase() ?? "??"}
          </Text>
        </View>
        <Text className="text-white font-medium">{shortAddr}</Text>
      </View>

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(msg: XMTPMessage) => msg.id}
        renderItem={({ item }: { item: XMTPMessage }) => (
          <MessageBubbleNative
            message={item}
            isMine={
              item.senderAddress ===
                (client?.accountIdentifier?.identifier ?? client?.address)
            }
          />
        )}
        contentContainerStyle={{ padding: 12, flexGrow: 1 }}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
        ListEmptyComponent={
          isLoading ? null : (
            <View className="flex-1 items-center justify-center">
              <Text className="text-white/30 text-sm">{t("messages.firstMessage")}</Text>
            </View>
          )
        }
      />

      {/* Input */}
      <MessageInputNative onSend={sendMessage} isSending={isSending} />
    </KeyboardAvoidingView>
  );
}
