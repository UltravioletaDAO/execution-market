import {
  View,
  Text,
  ScrollView,
  Pressable,
  Linking,
  Alert,
  Image,
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { useState } from "react";

const CHAINS = [
  { name: "Base", icon: require("../assets/images/chains/base.png") },
  { name: "Ethereum", icon: require("../assets/images/chains/ethereum.png") },
  { name: "Polygon", icon: require("../assets/images/chains/polygon.png") },
  { name: "Arbitrum", icon: require("../assets/images/chains/arbitrum.png") },
  { name: "Avalanche", icon: require("../assets/images/chains/avalanche.png") },
  { name: "Optimism", icon: require("../assets/images/chains/optimism.png") },
  { name: "Celo", icon: require("../assets/images/chains/celo.png") },
  { name: "Monad", icon: require("../assets/images/chains/monad.png") },
];

const COINS = [
  { name: "USDC", icon: require("../assets/images/coins/usdc.png") },
  { name: "EURC", icon: require("../assets/images/coins/eurc.png") },
  { name: "USDT", icon: require("../assets/images/coins/usdt.png") },
  { name: "PYUSD", icon: require("../assets/images/coins/pyusd.png") },
  { name: "AUSD", icon: require("../assets/images/coins/ausd.png") },
];

const LINKS = [
  {
    labelKey: "about.dashboard",
    url: "https://execution.market",
    icon: "🌐",
  },
  {
    labelKey: "about.apiDocs",
    url: "https://api.execution.market/docs",
    icon: "📄",
  },
  {
    labelKey: "about.mcpEndpoint",
    url: "https://mcp.execution.market/mcp/",
    icon: "🤖",
  },
  {
    labelKey: "about.agentCard",
    url: "https://mcp.execution.market/.well-known/agent.json",
    icon: "🪪",
  },
  {
    labelKey: "about.twitter",
    url: "https://x.com/ExecutionMarket",
    icon: "𝕏",
  },
  {
    labelKey: "about.github",
    url: "https://github.com/UltravioletaDAO/execution-market",
    icon: "📦",
  },
  {
    labelKey: "legal.privacyPolicy",
    url: "__internal__:/legal/privacy",
    icon: "🔒",
  },
  {
    labelKey: "legal.termsOfService",
    url: "__internal__:/legal/terms",
    icon: "📋",
  },
];

function SectionTitle({ children }: { children: string }) {
  return (
    <Text className="text-gray-500 text-xs font-bold uppercase tracking-wider mb-2 mt-5">
      {children}
    </Text>
  );
}

function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <Pressable
      className="border-b border-gray-800/50"
      onPress={() => setExpanded(!expanded)}
    >
      <View className="flex-row items-center justify-between px-4 py-3">
        <Text className="text-white text-sm font-medium flex-1 mr-3">
          {question}
        </Text>
        <Text className="text-gray-500 text-sm">
          {expanded ? "\u2212" : "+"}
        </Text>
      </View>
      {expanded && (
        <View className="px-4 pb-3">
          <Text className="text-gray-400 text-sm leading-5">{answer}</Text>
        </View>
      )}
    </Pressable>
  );
}

export default function AboutScreen() {
  const { t } = useTranslation();

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
        </Pressable>
      </View>

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        {/* Hero */}
        <View className="items-center mt-2 mb-4">
          <View className="bg-white rounded-2xl p-1 mb-3" style={{ elevation: 6 }}>
            <Image
              source={require("../assets/images/logo.png")}
              style={{ width: 80, height: 80, borderRadius: 14 }}
              resizeMode="contain"
            />
          </View>
          <Text className="text-white text-2xl font-bold">Execution Market</Text>
          <View className="mt-1.5 px-3 py-1 rounded-full border border-gray-700">
            <Text className="text-gray-400 text-xs font-medium">
              Universal Execution Layer
            </Text>
          </View>
          <Text className="text-gray-500 text-xs mt-2">
            Agent #2106 · Base ERC-8004
          </Text>
        </View>

        {/* Description */}
        <View className="bg-surface rounded-2xl p-4 mb-1">
          <Text className="text-gray-300 text-sm leading-5">
            {t("about.description")}
          </Text>
        </View>

        {/* Stats row */}
        <View className="flex-row mt-3 gap-2">
          <View className="flex-1 bg-surface rounded-xl p-3 items-center">
            <Text className="text-white text-xl font-bold">8</Text>
            <Text className="text-gray-500 text-xs">{t("about.chains")}</Text>
          </View>
          <View className="flex-1 bg-surface rounded-xl p-3 items-center">
            <Text className="text-white text-xl font-bold">5</Text>
            <Text className="text-gray-500 text-xs">{t("about.stablecoins")}</Text>
          </View>
          <View className="flex-1 bg-surface rounded-xl p-3 items-center">
            <Text className="text-white text-xl font-bold">21</Text>
            <Text className="text-gray-500 text-xs">{t("about.categories")}</Text>
          </View>
          <View className="flex-1 bg-surface rounded-xl p-3 items-center">
            <Text className="text-white text-xl font-bold">87%</Text>
            <Text className="text-gray-500 text-xs">{t("about.toExecutor")}</Text>
          </View>
        </View>

        {/* Supported Chains */}
        <SectionTitle>{t("about.supportedChains")}</SectionTitle>
        <View className="flex-row flex-wrap gap-2">
          {CHAINS.map((chain) => (
            <View
              key={chain.name}
              className="flex-row items-center bg-surface rounded-full px-3 py-1.5"
            >
              <Image
                source={chain.icon}
                style={{ width: 16, height: 16, borderRadius: 8, marginRight: 6 }}
                resizeMode="contain"
              />
              <Text className="text-gray-300 text-xs font-medium">{chain.name}</Text>
            </View>
          ))}
        </View>

        {/* Stablecoins */}
        <SectionTitle>{t("about.acceptedCoins")}</SectionTitle>
        <View className="flex-row flex-wrap gap-2">
          {COINS.map((coin) => (
            <View
              key={coin.name}
              className="flex-row items-center bg-surface rounded-full px-3 py-1.5"
            >
              <Image
                source={coin.icon}
                style={{ width: 16, height: 16, borderRadius: 8, marginRight: 6 }}
                resizeMode="contain"
              />
              <Text className="text-gray-300 text-xs font-medium">{coin.name}</Text>
            </View>
          ))}
        </View>

        {/* How it works */}
        <SectionTitle>{t("about.howItWorks")}</SectionTitle>
        <View className="bg-surface rounded-2xl p-4">
          {[
            { step: "1", labelKey: "about.step1" },
            { step: "2", labelKey: "about.step2" },
            { step: "3", labelKey: "about.step3" },
          ].map((s, i) => (
            <View key={i} className={`flex-row items-center ${i > 0 ? "mt-3" : ""}`}>
              <View className="w-7 h-7 rounded-full bg-white items-center justify-center mr-3">
                <Text className="text-black text-xs font-bold">{s.step}</Text>
              </View>
              <Text className="text-gray-300 text-sm flex-1">{t(s.labelKey)}</Text>
            </View>
          ))}
        </View>

        {/* Key features */}
        <SectionTitle>{t("about.features")}</SectionTitle>
        <View className="flex-row flex-wrap gap-2">
          {[
            "about.featureGasless",
            "about.featureEscrow",
            "about.featureReputation",
            "about.featureIdentity",
            "about.featureMCP",
            "about.featureA2A",
          ].map((key) => (
            <View
              key={key}
              className="bg-surface rounded-full px-3 py-1.5"
              style={{ borderWidth: 1, borderColor: "#222" }}
            >
              <Text className="text-gray-300 text-xs">{t(key)}</Text>
            </View>
          ))}
        </View>

        {/* Links */}
        <SectionTitle>{t("about.links")}</SectionTitle>
        <View className="bg-surface rounded-2xl overflow-hidden mb-2">
          {LINKS.map((link, i) => (
            <Pressable
              key={link.url}
              className={`flex-row items-center px-4 py-3 active:bg-gray-800 ${
                i > 0 ? "border-t border-gray-800/50" : ""
              }`}
              onPress={() => {
                if (link.url.startsWith("__internal__:")) {
                  router.push(link.url.replace("__internal__:", "") as any);
                } else {
                  WebBrowser.openBrowserAsync(link.url).catch(() => Linking.openURL(link.url).catch(() => Alert.alert("Error", `Could not open: ${link.url}`)));
                }
              }}
            >
              <Text style={{ fontSize: 16, marginRight: 10 }}>{link.icon}</Text>
              <View className="flex-1">
                <Text className="text-white text-sm font-medium">{t(link.labelKey)}</Text>
                <Text className="text-gray-600 text-xs" numberOfLines={1}>
                  {link.url}
                </Text>
              </View>
              <Text className="text-gray-600 text-sm">{"\u2197"}</Text>
            </Pressable>
          ))}
        </View>

        {/* FAQ */}
        <SectionTitle>{t("about.faqTitle")}</SectionTitle>
        <View className="bg-surface rounded-2xl overflow-hidden mb-2">
          <FAQItem
            question={t("about.faq1Q")}
            answer={t("about.faq1A")}
          />
          <FAQItem
            question={t("about.faq2Q")}
            answer={t("about.faq2A")}
          />
          <FAQItem
            question={t("about.faq3Q")}
            answer={t("about.faq3A")}
          />
          <FAQItem
            question={t("about.faq4Q")}
            answer={t("about.faq4A")}
          />
          <FAQItem
            question={t("about.faq5Q")}
            answer={t("about.faq5A")}
          />
          <FAQItem
            question={t("about.faq6Q")}
            answer={t("about.faq6A")}
          />
        </View>

        {/* Support */}
        <SectionTitle>{t("settings.support")}</SectionTitle>
        <Pressable
          className="bg-surface rounded-2xl px-4 py-4 mb-2"
          onPress={() => Linking.openURL("mailto:support@execution.market")}
        >
          <Text className="text-white font-medium">{t("settings.contactSupport")}</Text>
          <Text className="text-gray-500 text-xs mt-0.5">support@execution.market</Text>
        </Pressable>

        {/* Crypto Disclaimer */}
        <View className="bg-surface rounded-2xl px-4 py-3 mt-2 mb-2">
          <Text className="text-gray-500 text-xs leading-4">
            {t("about.cryptoDisclaimer")}
          </Text>
        </View>

        {/* Built by */}
        <View className="items-center py-6 mb-4">
          <Text className="text-gray-600 text-xs">
            {t("about.builtBy")}
          </Text>
          <Text className="text-gray-500 text-xs mt-1">
            Ultravioleta DAO
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
