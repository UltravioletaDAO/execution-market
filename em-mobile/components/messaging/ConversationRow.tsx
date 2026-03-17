import { View, Text, TouchableOpacity } from "react-native";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import type { ConversationPreview } from "../../hooks/useConversations";

interface Props {
  preview: ConversationPreview;
  onPress: () => void;
}

export function ConversationRow({ preview, onPress }: Props) {
  const shortAddress = `${preview.peerAddress.slice(0, 6)}...${preview.peerAddress.slice(-4)}`;
  const content = preview.lastMessage ?? "Sin mensajes";
  const avatarLetters = preview.peerAddress.slice(2, 4).toUpperCase();

  return (
    <TouchableOpacity
      onPress={onPress}
      className="flex-row items-center px-4 py-3 border-b border-white/5"
      activeOpacity={0.7}
    >
      <View className="w-12 h-12 rounded-full bg-white/10 items-center justify-center mr-3">
        <Text className="text-white/60 text-lg font-mono">{avatarLetters}</Text>
      </View>

      <View className="flex-1 mr-2">
        <Text className="text-white font-semibold text-base" numberOfLines={1}>
          {preview.resolvedName || shortAddress}
        </Text>
        <Text className="text-white/50 text-sm mt-0.5" numberOfLines={1}>
          {content}
        </Text>
      </View>

      <View className="items-end">
        {preview.lastMessageAt && (
          <Text className="text-white/30 text-xs">
            {formatDistanceToNow(preview.lastMessageAt, { locale: es, addSuffix: false })}
          </Text>
        )}
        {preview.unreadCount > 0 && (
          <View className="bg-red-600 rounded-full h-5 min-w-[20px] items-center justify-center mt-1 px-1">
            <Text className="text-white text-xs font-bold">{preview.unreadCount}</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
}
