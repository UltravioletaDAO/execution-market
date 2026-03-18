import { View, Text, FlatList, TouchableOpacity, ActivityIndicator, Modal, TextInput, Alert } from "react-native";
import { useState } from "react";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { useXMTP } from "../../providers/XMTPProvider";
import { useConversations, type ConversationPreview } from "../../hooks/useConversations";
import { ConversationRow } from "../../components/messaging/ConversationRow";
import { dynamicClient } from "../../lib/dynamic";

export default function MessagesScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  const { isConnected, isConnecting, connect, connectDev, error, walletAddress, signerAvailable, isDevMode, client } = useXMTP();
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
      // XMTP v5: newDm creates or opens existing DM conversation
      await client.conversations.newDm(address);
      await refresh();
      setShowNewChat(false);
      setPeerInput("");
      router.push(`/messages/${encodeURIComponent(address)}`);
    } catch (err) {
      Alert.alert(
        "Error",
        err instanceof Error ? err.message : "No se pudo iniciar la conversación"
      );
    } finally {
      setIsStarting(false);
    }
  };

  if (!isConnected) {
    const needsWalletConnector = !!walletAddress && !signerAvailable;

    return (
      <View className="flex-1 bg-black items-center justify-center px-6">
        <Text className="text-white text-xl font-bold mb-2">{t("messages.title")}</Text>
        <Text className="text-white/60 text-center mb-6">
          {t("messages.subtitle")}
        </Text>
        {error ? (
          <Text className="text-red-400 text-sm text-center mb-4">{error}</Text>
        ) : needsWalletConnector ? (
          <Text className="text-yellow-400 text-sm text-center mb-6">
            Entraste con email. XMTP necesita tu wallet connector activo.
          </Text>
        ) : null}
        {needsWalletConnector ? (
          <>
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
      {/* Header */}
      <View className="flex-row items-center justify-between px-4 pt-4 pb-2">
        <Text className="text-white text-2xl font-bold">{t("messages.header")}</Text>
        <TouchableOpacity
          onPress={() => setShowNewChat(true)}
          className="w-9 h-9 bg-white rounded-full items-center justify-center"
          activeOpacity={0.8}
        >
          <Text className="text-black text-xl font-bold leading-none">+</Text>
        </TouchableOpacity>
      </View>

      {isDevMode && (
        <Text className="text-yellow-400/50 text-xs text-center pb-1">
          Modo Dev — identidad temporal
        </Text>
      )}

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
            <View className="items-center mt-16 px-6">
              <Text className="text-white/40 text-center mb-4">{t("messages.empty")}</Text>
              <TouchableOpacity
                onPress={() => setShowNewChat(true)}
                className="border border-white/20 px-5 py-2.5 rounded-xl"
                activeOpacity={0.8}
              >
                <Text className="text-white/60 text-sm">Iniciar conversación</Text>
              </TouchableOpacity>
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
        <View className="flex-1 justify-end bg-black/70">
          <View className="bg-zinc-900 rounded-t-2xl px-5 pt-5 pb-8">
            <View className="flex-row items-center justify-between mb-4">
              <Text className="text-white text-lg font-semibold">Nueva conversación</Text>
              <TouchableOpacity onPress={() => { setShowNewChat(false); setPeerInput(""); }}>
                <Text className="text-white/50 text-2xl leading-none">×</Text>
              </TouchableOpacity>
            </View>
            <Text className="text-white/50 text-xs mb-2">Dirección XMTP (0x...)</Text>
            <TextInput
              value={peerInput}
              onChangeText={setPeerInput}
              placeholder="0x..."
              placeholderTextColor="rgba(255,255,255,0.2)"
              autoCapitalize="none"
              autoCorrect={false}
              className="bg-white/10 text-white rounded-xl px-4 py-3 mb-4 font-mono text-sm"
            />
            <TouchableOpacity
              onPress={handleStartConversation}
              disabled={isStarting || !peerInput.trim()}
              className="bg-white rounded-xl py-3 items-center"
              activeOpacity={0.8}
              style={{ opacity: !peerInput.trim() ? 0.4 : 1 }}
            >
              {isStarting ? (
                <ActivityIndicator color="black" />
              ) : (
                <Text className="text-black font-semibold">Abrir chat</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}
