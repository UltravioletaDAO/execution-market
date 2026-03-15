import { View, Text } from "react-native";
import { useTranslation } from "react-i18next";

interface ReputationBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

function getTier(score: number): { labelKey: string; color: string; bgColor: string } {
  if (score >= 76) return { labelKey: "reputation.legendary", color: "#FFD700", bgColor: "bg-yellow-900/30" };
  if (score >= 51) return { labelKey: "reputation.expert", color: "#C084FC", bgColor: "bg-purple-900/30" };
  if (score >= 26) return { labelKey: "reputation.intermediate", color: "#60A5FA", bgColor: "bg-blue-900/30" };
  return { labelKey: "reputation.novice", color: "#9CA3AF", bgColor: "bg-gray-800" };
}

export function ReputationBadge({ score, size = "md" }: ReputationBadgeProps) {
  const { t } = useTranslation();
  const tier = getTier(score);
  const fontSize = size === "lg" ? 20 : size === "sm" ? 11 : 14;
  const labelSize = size === "lg" ? 12 : size === "sm" ? 9 : 10;
  const px = size === "sm" ? "px-2" : "px-3";
  const py = size === "sm" ? "py-1" : "py-2";

  return (
    <View className={`${tier.bgColor} rounded-xl ${px} ${py} flex-row items-center`}>
      <Text style={{ color: tier.color, fontSize, fontWeight: "bold" }}>
        {Math.round(score)}
      </Text>
      <Text style={{ color: tier.color, fontSize: labelSize, marginLeft: 4 }}>
        {t(tier.labelKey)}
      </Text>
    </View>
  );
}
