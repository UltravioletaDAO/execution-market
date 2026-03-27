import { View, Text, Image } from "react-native";
import { NETWORKS } from "../constants/networks";

const CHAIN_IMAGES: Record<string, number> = {
  base: require("../assets/images/chains/base.png"),
  ethereum: require("../assets/images/chains/ethereum.png"),
  polygon: require("../assets/images/chains/polygon.png"),
  arbitrum: require("../assets/images/chains/arbitrum.png"),
  avalanche: require("../assets/images/chains/avalanche.png"),
  optimism: require("../assets/images/chains/optimism.png"),
  celo: require("../assets/images/chains/celo.png"),
  monad: require("../assets/images/chains/monad.png"),
  skale: require("../assets/images/chains/skale.png"),
};

interface NetworkBadgeProps {
  network: string;
  size?: "sm" | "md";
}

export function NetworkBadge({ network, size = "md" }: NetworkBadgeProps) {
  const net = NETWORKS.find((n) => n.key === network);
  if (!net) return null;

  const iconSize = size === "sm" ? 14 : 18;
  const chainImage = CHAIN_IMAGES[network];

  return (
    <View
      className={`rounded-full flex-row items-center ${size === "sm" ? "px-2 py-0.5" : "px-3 py-1"}`}
      style={{ backgroundColor: `${net.color}20` }}
    >
      {chainImage ? (
        <Image
          source={chainImage}
          style={{ width: iconSize, height: iconSize, borderRadius: iconSize / 2, marginRight: 4 }}
        />
      ) : (
        <View
          className={`rounded-full ${size === "sm" ? "w-2 h-2" : "w-3 h-3"} mr-1.5`}
          style={{ backgroundColor: net.color }}
        />
      )}
      <Text style={{ color: net.color, fontSize: size === "sm" ? 10 : 12, fontWeight: "600" }}>
        {net.name}
      </Text>
    </View>
  );
}
