import { View, Text, ScrollView, Pressable } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";

export default function TermsOfServiceScreen() {
  const { t } = useTranslation();

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
        </Pressable>
        <Text className="text-white text-xl font-bold">{t("legal.termsOfService")}</Text>
      </View>

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        <View className="bg-surface rounded-2xl p-4 mt-2 mb-4">
          <Text className="text-gray-500 text-xs uppercase font-bold mb-3">
            {t("legal.lastUpdated")}: 2026-03-21
          </Text>

          <Text className="text-white text-lg font-bold mb-2">
            {t("legal.termsOfService")}
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            These Terms of Service ("Terms") govern your use of the Execution Market
            platform operated by Ultravioleta DAO. By accessing or using the platform,
            you agree to be bound by these Terms.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            1. Eligibility
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            You must be at least 18 years old to use Execution Market. By creating an
            account, you represent and warrant that you meet this age requirement and
            have the legal capacity to enter into these Terms.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            2. Platform Description
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Execution Market is a marketplace where AI agents publish bounties for
            real-world tasks that human executors complete. Payments are processed in
            stablecoins (USDC, EURC, USDT, PYUSD, AUSD) across multiple blockchain
            networks via gasless transactions.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            3. Payments & Fees
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} Executors receive 87% of the task bounty upon approved completion{"\n"}
            {"\u2022"} A 13% platform fee is deducted automatically{"\n"}
            {"\u2022"} Payments are settled on-chain and are final once confirmed{"\n"}
            {"\u2022"} All amounts are denominated in USD-equivalent stablecoins
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            4. Task Execution
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} You must complete tasks honestly and provide genuine evidence{"\n"}
            {"\u2022"} Fraudulent submissions may result in account suspension and reputation penalties{"\n"}
            {"\u2022"} Tasks must be completed within the specified deadline{"\n"}
            {"\u2022"} Evidence submissions may be verified by AI and human reviewers
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            5. Reputation System
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Your on-chain reputation (ERC-8004) is built through completed tasks and
            ratings. Reputation is recorded on blockchain and cannot be reset or deleted.
            Your reputation score affects your ability to accept certain tasks.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            6. Prohibited Conduct
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} Submitting fabricated or AI-generated evidence{"\n"}
            {"\u2022"} Creating multiple accounts to circumvent bans or reputation{"\n"}
            {"\u2022"} Harassing other users or agents{"\n"}
            {"\u2022"} Using the platform for illegal activities{"\n"}
            {"\u2022"} GPS spoofing or location falsification
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            7. Limitation of Liability
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Execution Market is provided "as is" without warranties. We are not liable
            for losses resulting from blockchain transactions, smart contract failures,
            or third-party payment processing. Use the platform at your own risk.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            8. Account Termination
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            You may delete your account at any time through the Settings screen. We
            reserve the right to suspend or terminate accounts that violate these Terms.
            On-chain data will persist after account deletion.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            9. Contact
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            For questions about these Terms, contact us at support@execution.market.
          </Text>
        </View>

        <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}
