import { View, Text } from "react-native";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import type { XMTPMessage } from "../../hooks/useMessages";

interface Props {
  message: XMTPMessage;
  isMine: boolean;
}

export function MessageBubbleNative({ message, isMine }: Props) {
  if (!message.content || !message.content.trim()) return null;

  return (
    <View className={`flex-row ${isMine ? "justify-end" : "justify-start"} mb-2`}>
      <View className={`max-w-[75%] rounded-2xl px-4 py-2 ${
        isMine
          ? "bg-white rounded-br-sm"
          : "bg-white/10 rounded-bl-sm"
      }`}>
        <Text className={`text-sm ${isMine ? "text-black" : "text-white"}`}>
          {message.content}
        </Text>
        <Text className={`text-[10px] mt-1 ${isMine ? "text-black/40" : "text-white/40"}`}>
          {formatDistanceToNow(message.sentAt, { addSuffix: true, locale: es })}
        </Text>
      </View>
    </View>
  );
}
