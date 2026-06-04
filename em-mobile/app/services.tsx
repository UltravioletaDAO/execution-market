import { View, Text, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, type Href } from "expo-router";
import { useTranslation } from "react-i18next";
import { SERVICES } from "../constants/services";

/**
 * Services catalog (mobile) — the Rappi-style "¿qué necesitas hoy?" grid.
 * Tiles route to the publish wizard with the category preset + H2H target.
 * Mirror of the web ServicesHome. B&W canonical (black bg, white accents).
 */
export default function ServicesScreen() {
  const router = useRouter();
  const { t } = useTranslation();

  return (
    <SafeAreaView className="flex-1 bg-black">
      <ScrollView contentContainerStyle={{ padding: 16 }}>
        <Pressable onPress={() => router.back()} className="mb-3">
          <Text className="text-gray-400">← {t("common.back", "Atrás")}</Text>
        </Pressable>

        <Text className="text-white text-2xl font-bold">
          {t("services.title", "¿Qué necesitas hoy?")}
        </Text>
        <Text className="text-gray-400 text-sm mt-1 mb-5">
          {t("services.subtitle", "Publica una tarea y un humano cercano la ejecuta. Pago seguro en USDC.")}
        </Text>

        <View className="flex-row flex-wrap justify-between">
          {SERVICES.map((s) => (
            <Pressable
              key={s.key}
              onPress={() =>
                router.push({
                  pathname: "/(tabs)/publish",
                  params: { presetCategory: s.category, presetTarget: "human" },
                })
              }
              className="bg-surface border border-gray-800 rounded-2xl p-4 items-center mb-3"
              style={{ width: "47%" }}
            >
              <Text style={{ fontSize: 32 }}>{s.icon}</Text>
              <Text className="text-white font-medium mt-2">{s.label}</Text>
              <Text className="text-gray-500 text-xs text-center mt-1">{s.desc}</Text>
            </Pressable>
          ))}
        </View>

        <Pressable
          onPress={() => router.push("/deposit" as Href)}
          className="bg-white rounded-2xl py-4 items-center mt-4"
        >
          <Text className="text-black font-bold">💳 {t("services.deposit", "Depositar USDC")}</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}
