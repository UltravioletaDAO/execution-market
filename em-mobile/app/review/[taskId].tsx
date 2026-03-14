import { View, Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";

export default function ReviewSubmissionScreen() {
  const { taskId } = useLocalSearchParams<{ taskId: string }>();
  const { t } = useTranslation();

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="px-4 pt-4">
        <Text className="text-white text-2xl font-bold">{t("review.title")}</Text>
        <Text className="text-gray-400 mt-1">{t("review.taskLabel", { taskId })}</Text>
      </View>
    </SafeAreaView>
  );
}
