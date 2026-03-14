import { View, Text, Pressable } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";

export default function NotFoundScreen() {
  const { t } = useTranslation();

  return (
    <SafeAreaView className="flex-1 bg-black items-center justify-center px-8">
      <Text style={{ fontSize: 64 }}>{"\uD83D\uDD0D"}</Text>
      <Text className="text-white text-2xl font-bold mt-4">
        {t("notFound.title")}
      </Text>
      <Text className="text-gray-400 text-center mt-2 mb-8">
        {t("notFound.description")}
      </Text>
      <Pressable
        className="bg-white rounded-2xl px-8 py-4"
        onPress={() => router.replace("/(tabs)")}
      >
        <Text className="text-black font-bold text-lg">{t("notFound.goHome")}</Text>
      </Pressable>
    </SafeAreaView>
  );
}
