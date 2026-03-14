import { View, Text } from "react-native";
import { NETWORKS } from "../constants/networks";

interface NetworkBadgeProps {
  network: string;
  size?: "sm" | "md";
}

export function NetworkBadge({ network, size = "md" }: NetworkBadgeProps) {
  const net = NETWORKS.find((n) => n.key === network);
  if (!net) return null;

  return (
    <View
      className={`rounded-full flex-row items-center ${size === "sm" ? "px-2 py-0.5" : "px-3 py-1"}`}
      style={{ backgroundColor: `${net.color}20` }}
    >
      <View
        className={`rounded-full ${size === "sm" ? "w-2 h-2" : "w-3 h-3"} mr-1.5`}
        style={{ backgroundColor: net.color }}
      />
      <Text style={{ color: net.color, fontSize: size === "sm" ? 10 : 12, fontWeight: "600" }}>
        {net.name}
      </Text>
    </View>
  );
}
