import { TouchableOpacity, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { useXMTP } from "../../providers/XMTPProvider";

interface Props {
  walletAddress: string;
  label?: string;
}

export function MessageAgentButton({ walletAddress, label }: Props) {
  const { t } = useTranslation();
  const { isConnected } = useXMTP();
  const router = useRouter();
  const resolvedLabel = label ?? t("messages.messageAgent");

  if (!isConnected || !walletAddress) return null;

  return (
    <TouchableOpacity
      onPress={() => router.push(`/messages/${encodeURIComponent(walletAddress)}`)}
      className="flex-row items-center justify-center gap-2 bg-white/5 border border-white/10 rounded-xl py-3 px-4"
      activeOpacity={0.7}
    >
      <Ionicons name="chatbubble-outline" size={18} color="white" />
      <Text className="text-white font-medium">{resolvedLabel}</Text>
    </TouchableOpacity>
  );
}
