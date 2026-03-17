import { View, Text, FlatList, TouchableOpacity, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { useXMTP } from "../../providers/XMTPProvider";
import { useConversations, type ConversationPreview } from "../../hooks/useConversations";
import { ConversationRow } from "../../components/messaging/ConversationRow";

export default function MessagesScreen() {
  const router = useRouter();
  const { isConnected, isConnecting, connect } = useXMTP();
  const { previews, isLoading } = useConversations();

  if (!isConnected) {
    return (
      <View className="flex-1 bg-black items-center justify-center px-6">
        <Text className="text-white text-xl font-bold mb-2">Mensajes XMTP</Text>
        <Text className="text-white/60 text-center mb-6">
          Activa mensajeria encriptada para comunicarte directamente con agentes AI
        </Text>
        <TouchableOpacity
          onPress={connect}
          disabled={isConnecting}
          className="bg-white px-6 py-3 rounded-xl"
          activeOpacity={0.8}
        >
          <Text className="text-black font-semibold">
            {isConnecting ? "Conectando..." : "Activar Mensajes"}
          </Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-black">
      <View className="px-4 pt-4 pb-2">
        <Text className="text-white text-2xl font-bold">Mensajes</Text>
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
            <Text className="text-white/40 text-center mt-8">No hay conversaciones aun</Text>
          }
        />
      )}
    </View>
  );
}
