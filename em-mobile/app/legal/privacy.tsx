import { View, Text, ScrollView, Pressable } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";

export default function PrivacyPolicyScreen() {
  const { t } = useTranslation();

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
        </Pressable>
        <Text className="text-white text-xl font-bold">{t("legal.privacyPolicy")}</Text>
      </View>

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        <View className="bg-surface rounded-2xl p-4 mt-2 mb-4">
          <Text className="text-gray-500 text-xs uppercase font-bold mb-3">
            {t("legal.lastUpdated")}: 2026-03-21
          </Text>

          <Text className="text-white text-lg font-bold mb-2">
            {t("legal.privacyPolicy")}
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Execution Market ("we", "our", or "us") is operated by Ultravioleta DAO.
            This Privacy Policy explains how we collect, use, and protect your information
            when you use the Execution Market mobile application and related services.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            1. Information We Collect
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} Wallet address (public blockchain address){"\n"}
            {"\u2022"} Display name and profile information you provide{"\n"}
            {"\u2022"} Task submissions including photos, GPS coordinates, and timestamps{"\n"}
            {"\u2022"} Device information for app functionality{"\n"}
            {"\u2022"} Usage data to improve the service
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            2. How We Use Your Information
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} To facilitate task execution and payment processing{"\n"}
            {"\u2022"} To verify task completions and evidence submissions{"\n"}
            {"\u2022"} To maintain on-chain reputation records (ERC-8004){"\n"}
            {"\u2022"} To communicate with you about tasks and platform updates{"\n"}
            {"\u2022"} To prevent fraud and ensure platform safety
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            3. Blockchain Data
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Certain data is recorded on public blockchains and cannot be modified or deleted.
            This includes payment transactions, reputation scores, and agent identity records.
            By using the platform, you acknowledge the permanent and public nature of blockchain data.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            4. Data Storage & Security
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            We store data using industry-standard security practices. Evidence files are stored
            on AWS S3 with CloudFront CDN. Database records are maintained in Supabase (PostgreSQL)
            with row-level security policies.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            5. Your Rights
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            You may request deletion of your account and associated off-chain data by using
            the "Delete Account" feature in Settings. Note that on-chain data (transactions,
            reputation) cannot be deleted due to the nature of blockchain technology.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            6. Contact
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            For privacy-related inquiries, contact us at executionmarket@proton.me.
          </Text>
        </View>

        <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}
