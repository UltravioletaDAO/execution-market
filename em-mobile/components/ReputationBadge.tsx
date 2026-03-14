import { View, Text } from "react-native";

interface ReputationBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

function getTier(score: number): { label: string; color: string; bgColor: string } {
  if (score >= 76) return { label: "Legendary", color: "#FFD700", bgColor: "bg-yellow-900/30" };
  if (score >= 51) return { label: "Expert", color: "#C084FC", bgColor: "bg-purple-900/30" };
  if (score >= 26) return { label: "Intermediate", color: "#60A5FA", bgColor: "bg-blue-900/30" };
  return { label: "Novice", color: "#9CA3AF", bgColor: "bg-gray-800" };
}

export function ReputationBadge({ score, size = "md" }: ReputationBadgeProps) {
  const tier = getTier(score);

  return (
    <View className={`${tier.bgColor} rounded-xl px-3 py-2 flex-row items-center`}>
      <Text style={{ color: tier.color, fontSize: size === "lg" ? 20 : 14, fontWeight: "bold" }}>
        {score}
      </Text>
      <Text style={{ color: tier.color, fontSize: size === "lg" ? 12 : 10, marginLeft: 4 }}>
        {tier.label}
      </Text>
    </View>
  );
}
