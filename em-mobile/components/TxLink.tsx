import { Pressable, Text, Linking } from "react-native";
import { getExplorerTxUrl } from "../constants/networks";

interface TxLinkProps {
  txHash: string;
  network: string;
}

export function TxLink({ txHash, network }: TxLinkProps) {
  return (
    <Pressable
      onPress={() => Linking.openURL(getExplorerTxUrl(network, txHash))}
    >
      <Text className="text-blue-400 text-xs font-mono">
        {txHash.slice(0, 8)}...{txHash.slice(-6)} ↗
      </Text>
    </Pressable>
  );
}
