import { View, Text, FlatList, TouchableOpacity, ActivityIndicator, Modal, TextInput, Alert, KeyboardAvoidingView, Platform } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { useXMTP } from "../../providers/XMTPProvider";
import { useConversations, type ConversationPreview } from "../../hooks/useConversations";
import { ConversationRow } from "../../components/messaging/ConversationRow";

export default function MessagesScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  const insets = useSafeAreaInsets();
  const { isConnected, isConnecting, connect, error, walletAddress, client } = useXMTP();
  const { previews, isLoading, refresh } = useConversations();
  const [showNewChat, setShowNewChat] = useState(false);
  const [peerInput, setPeerInput] = useState("");
  const [isStarting, setIsStarting] = useState(false);

  const handleStartConversation = async () => {
    const address = peerInput.trim();
    if (!address) return;
    if (!client) return;

    setIsStarting(true);
    try {
      const { PublicIdentity } = await import("@xmtp/react-native-sdk");
      const identity = new PublicIdentity(address, "ETHEREUM");

      // Check if the address has an XMTP v5 inbox before trying to create a DM
      const inboxId = await client.findInboxIdFromIdentity(identity);
      if (!inboxId) {
        Alert.alert(
          t("messages.noXmtpV5Title"),
          t("messages.noXmtpV5Body")
        );
        return;
      }

      await client.conversations.findOrCreateDmWithIdentity(identity);
      await refresh();
      setShowNewChat(false);
      setPeerInput("");
      router.push(`/messages/${encodeURIComponent(address)}`);
    } catch (err) {
      Alert.alert(
        t("common.error"),
        err instanceof Error ? err.message : t("messages.createDmError")
      );
    } finally {
      setIsStarting(false);
    }
  };

  if (!isConnected) {
    return (
      <View className="flex-1 bg-black items-center justify-center px-6">
        <Text className="text-white text-xl font-bold mb-2">{t("messages.title")}</Text>
        <Text className="text-white/60 text-center mb-6">
          {t("messages.subtitle")}
        </Text>
        {error && (
          <Text className="text-red-400 text-sm text-center mb-4">{error}</Text>
        )}
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
      {/* Header */}
      <View className="flex-row items-center justify-between px-4 pt-4 pb-2">
        <View className="flex-row items-center">
          <Text className="text-white text-2xl font-bold">{t("messages.header")}</Text>
          <View className="ml-2 border border-white/10 rounded px-1.5 py-0.5">
            <Text className="text-white/40 text-[10px] font-mono">{t("messages.xmtpBadge")}</Text>
          </View>
        </View>
        <TouchableOpacity
          onPress={() => setShowNewChat(true)}
          className="w-9 h-9 bg-white rounded-full items-center justify-center"
          activeOpacity={0.8}
        >
          <Text className="text-black text-xl font-bold leading-none">+</Text>
        </TouchableOpacity>
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
              onPress={() => router.push(`/messages/${encodeURIComponent(item.convoId)}`)}
            />
          )}
          ListEmptyComponent={
            <View className="items-center mt-16 px-6">
              <Text className="text-white/40 text-center mb-4">{t("messages.empty")}</Text>
              <TouchableOpacity
                onPress={() => setShowNewChat(true)}
                className="border border-white/20 px-5 py-2.5 rounded-xl"
                activeOpacity={0.8}
              >
                <Text className="text-white/60 text-sm">{t("messages.startConversation")}</Text>
              </TouchableOpacity>
              <View className="flex-row items-center mt-6">
                <Ionicons name="lock-closed" size={10} color="rgba(255,255,255,0.3)" />
                <Text className="text-white/30 text-[10px] ml-1">{t("messages.e2eEncrypted")} · XMTP</Text>
              </View>
              {(client?.accountIdentifier?.identifier ?? client?.address ?? walletAddress) && (
                <View className="mt-3 items-center">
                  <Text className="text-white/30 text-[10px]">{t("messages.yourXmtpAddress")}</Text>
                  <Text className="text-white/40 text-[10px] font-mono mt-0.5">
                    {client?.accountIdentifier?.identifier ?? client?.address ?? walletAddress}
                  </Text>
                </View>
              )}
            </View>
          }
        />
      )}

      {/* New conversation modal */}
      <Modal
        visible={showNewChat}
        transparent
        animationType="slide"
        onRequestClose={() => setShowNewChat(false)}
      >
        {/* Overlay oscuro — tap para cerrar */}
        <TouchableOpacity
          style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.7)" }}
          activeOpacity={1}
          onPress={() => { setShowNewChat(false); setPeerInput(""); }}
        />
        {/* Sheet — KAV envuelve SOLO el contenido, no la pantalla entera */}
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "padding"}
          keyboardVerticalOffset={0}
        >
          <View
            style={{
              backgroundColor: "#18181b",
              borderTopLeftRadius: 16,
              borderTopRightRadius: 16,
              paddingHorizontal: 20,
              paddingTop: 20,
              paddingBottom: Math.max(insets.bottom + 12, 24),
            }}
          >
            <View className="flex-row items-center justify-between mb-4">
              <Text className="text-white text-lg font-semibold">{t("messages.newConversation")}</Text>
              <TouchableOpacity onPress={() => { setShowNewChat(false); setPeerInput(""); }}>
                <Text className="text-white/50 text-2xl leading-none">×</Text>
              </TouchableOpacity>
            </View>
            <Text className="text-white/50 text-xs mb-2">{t("messages.addressLabel")}</Text>
            <TextInput
              value={peerInput}
              onChangeText={setPeerInput}
              placeholder={t("messages.addressPlaceholder")}
              placeholderTextColor="rgba(255,255,255,0.2)"
              autoCapitalize="none"
              autoCorrect={false}
              style={{
                backgroundColor: "rgba(255,255,255,0.08)",
                color: "white",
                borderRadius: 12,
                paddingHorizontal: 16,
                paddingVertical: 12,
                marginBottom: 16,
                fontFamily: "RobotoMono-Regular",
                fontSize: 13,
              }}
            />
            <TouchableOpacity
              onPress={handleStartConversation}
              disabled={isStarting || !peerInput.trim()}
              style={{
                backgroundColor: "white",
                borderRadius: 12,
                paddingVertical: 12,
                alignItems: "center",
                opacity: !peerInput.trim() ? 0.4 : 1,
              }}
              activeOpacity={0.8}
            >
              {isStarting ? (
                <ActivityIndicator color="black" />
              ) : (
                <Text style={{ color: "black", fontWeight: "600" }}>{t("messages.openChat")}</Text>
              )}
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}
