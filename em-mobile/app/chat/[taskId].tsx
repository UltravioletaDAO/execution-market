import {
  View,
  Text,
  FlatList,
  TextInput,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Ionicons } from "@expo/vector-icons";
import { useChatWebSocket, type ChatMessage } from "../../hooks/useChatWebSocket";

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({ message, isOwn }: { message: ChatMessage; isOwn: boolean }) {
  const { t } = useTranslation();

  // System messages — centered, gray
  if (message.type === "system" || message.source === "system") {
    return (
      <View className="items-center my-2 px-8">
        <Text className="text-gray-500 text-xs text-center italic">
          {message.text}
        </Text>
      </View>
    );
  }

  // Error messages — centered, red
  if (message.type === "error") {
    return (
      <View className="items-center my-2 px-8">
        <Text className="text-red-400 text-xs text-center">
          {message.text}
        </Text>
      </View>
    );
  }

  const time = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "";

  // Source badge for non-mobile messages
  const sourceBadge =
    message.source && message.source !== "mobile" ? `[${message.source.toUpperCase()}]` : null;

  return (
    <View className={`flex-row ${isOwn ? "justify-end" : "justify-start"} mb-2 px-3`}>
      <View
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
          isOwn ? "bg-white" : "bg-gray-800"
        }`}
      >
        {/* Nick + source badge */}
        {!isOwn && (
          <View className="flex-row items-center mb-0.5">
            <Text className="text-blue-400 text-xs font-bold">{message.nick}</Text>
            {sourceBadge && (
              <Text className="text-gray-600 text-[10px] ml-1">{sourceBadge}</Text>
            )}
          </View>
        )}

        <Text className={isOwn ? "text-black text-sm" : "text-white text-sm"}>
          {message.text}
        </Text>

        <Text
          className={`text-[10px] mt-1 ${isOwn ? "text-gray-400 text-right" : "text-gray-500"}`}
        >
          {time}
        </Text>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export default function TaskChatScreen() {
  const { taskId } = useLocalSearchParams<{ taskId: string }>();
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const flatListRef = useRef<FlatList>(null);

  const { messages, sendMessage, isConnected, isConnecting, error, reconnect } =
    useChatWebSocket(taskId || "");

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages.length]);

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    sendMessage(text);
    setInput("");
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <SafeAreaView className="flex-1 bg-black" edges={["top"]}>
      {/* Header */}
      <View className="flex-row items-center px-4 py-3 border-b border-gray-800">
        <Pressable onPress={() => router.back()} className="mr-3 active:opacity-60">
          <Ionicons name="arrow-back" size={24} color="white" />
        </Pressable>
        <View className="flex-1">
          <Text className="text-white font-bold text-base" numberOfLines={1}>
            {t("chat.title")}
          </Text>
          <Text className="text-gray-500 text-xs" numberOfLines={1}>
            #{taskId?.slice(0, 8)}
          </Text>
        </View>
        {/* Connection indicator */}
        <View className="flex-row items-center">
          <View
            className={`w-2 h-2 rounded-full mr-1.5 ${
              isConnected ? "bg-green-500" : isConnecting ? "bg-yellow-500" : "bg-red-500"
            }`}
          />
          <Text className="text-gray-500 text-xs">
            {isConnected ? "Live" : isConnecting ? "..." : "Off"}
          </Text>
        </View>
      </View>

      {/* Connection banner */}
      {error && (
        <Pressable
          className="bg-red-900/30 px-4 py-2 flex-row items-center justify-between"
          onPress={reconnect}
        >
          <Text className="text-red-400 text-xs flex-1">{error}</Text>
          <Text className="text-red-300 text-xs font-bold ml-2">{t("common.retry")}</Text>
        </Pressable>
      )}

      {!isConnected && isConnecting && (
        <View className="bg-yellow-900/20 px-4 py-2 flex-row items-center">
          <ActivityIndicator size="small" color="#EAB308" />
          <Text className="text-yellow-400 text-xs ml-2">{t("chat.connecting")}</Text>
        </View>
      )}

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={0}
      >
        {/* Messages */}
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(_, i) => String(i)}
          renderItem={({ item }) => (
            <MessageBubble
              message={item}
              isOwn={item.source === "mobile"}
            />
          )}
          contentContainerStyle={{
            flexGrow: 1,
            justifyContent: messages.length === 0 ? "center" : "flex-end",
            paddingVertical: 12,
          }}
          ListEmptyComponent={
            <View className="items-center px-8">
              <Text className="text-gray-600 text-sm text-center">
                {t("chat.noMessages")}
              </Text>
            </View>
          }
          onContentSizeChange={() =>
            flatListRef.current?.scrollToEnd({ animated: false })
          }
        />

        {/* Input bar */}
        <View className="flex-row items-end px-3 py-2 border-t border-gray-800 bg-black">
          <TextInput
            className="flex-1 bg-gray-900 text-white rounded-2xl px-4 py-2.5 mr-2 text-sm max-h-24"
            placeholder={t("chat.placeholder")}
            placeholderTextColor="#6B7280"
            value={input}
            onChangeText={setInput}
            multiline
            maxLength={2000}
            onSubmitEditing={handleSend}
            blurOnSubmit={false}
            returnKeyType="send"
            editable={isConnected}
          />
          <Pressable
            className={`w-10 h-10 rounded-full items-center justify-center ${
              input.trim() && isConnected ? "bg-white" : "bg-gray-800"
            }`}
            onPress={handleSend}
            disabled={!input.trim() || !isConnected}
          >
            <Ionicons
              name="send"
              size={18}
              color={input.trim() && isConnected ? "#000" : "#6B7280"}
            />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
