import { useState, useRef } from "react";
import { View, TextInput, TouchableOpacity } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";

interface Props {
  onSend: (text: string) => Promise<void>;
  isSending: boolean;
  placeholder?: string;
}

export function MessageInputNative({ onSend, isSending, placeholder = "Escribe un mensaje..." }: Props) {
  const [text, setText] = useState("");
  const inputRef = useRef<TextInput>(null);
  const insets = useSafeAreaInsets();

  const handleSend = async () => {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;
    setText("");
    await onSend(trimmed);
  };

  return (
    <View
      className="flex-row items-end px-3 pt-2 border-t border-white/10 bg-black"
      style={{ paddingBottom: Math.max(insets.bottom, 8) }}
    >
      <TextInput
        ref={inputRef}
        value={text}
        onChangeText={setText}
        placeholder={placeholder}
        placeholderTextColor="rgba(255,255,255,0.3)"
        multiline
        maxLength={4096}
        className="flex-1 bg-white/5 rounded-2xl px-4 py-2.5 text-white text-sm border border-white/10"
        style={{ minHeight: 40, maxHeight: 120 }}
      />
      <TouchableOpacity
        onPress={handleSend}
        disabled={!text.trim() || isSending}
        className="ml-2 p-2.5 bg-white rounded-full"
        style={{ opacity: !text.trim() || isSending ? 0.3 : 1 }}
        activeOpacity={0.7}
      >
        <Ionicons name="send" size={18} color="black" />
      </TouchableOpacity>
    </View>
  );
}
