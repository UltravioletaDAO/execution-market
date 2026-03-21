import {
  View,
  Text,
  Pressable,
  Dimensions,
  FlatList,
  Image,
} from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState, useRef, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useTranslation } from "react-i18next";

const LANGUAGE_KEY = "em_language";

function LanguageToggle() {
  const { i18n } = useTranslation();
  const isEn = i18n.language === "en";

  const toggle = useCallback(async () => {
    const next = isEn ? "es" : "en";
    await i18n.changeLanguage(next);
    await AsyncStorage.setItem(LANGUAGE_KEY, next);
  }, [isEn, i18n]);

  return (
    <Pressable
      onPress={toggle}
      className="flex-row items-center rounded-full bg-gray-900"
      style={{ borderWidth: 1, borderColor: "#333", paddingHorizontal: 2, paddingVertical: 2 }}
    >
      <View
        className={`rounded-full px-2.5 py-1 ${isEn ? "bg-white" : ""}`}
      >
        <Text
          className={`text-xs font-bold ${isEn ? "text-black" : "text-gray-500"}`}
        >
          EN
        </Text>
      </View>
      <View
        className={`rounded-full px-2.5 py-1 ${!isEn ? "bg-white" : ""}`}
      >
        <Text
          className={`text-xs font-bold ${!isEn ? "text-black" : "text-gray-500"}`}
        >
          ES
        </Text>
      </View>
    </Pressable>
  );
}

const { width } = Dimensions.get("window");

// ---------------------------------------------------------------------------
// Chain & coin assets
// ---------------------------------------------------------------------------
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

const STEP_KEYS = [
  { emoji: "1", labelKey: "onboarding.step1Label", descKey: "onboarding.step1Desc" },
  { emoji: "2", labelKey: "onboarding.step2Label", descKey: "onboarding.step2Desc" },
  { emoji: "3", labelKey: "onboarding.step3Label", descKey: "onboarding.step3Desc" },
];

const CATEGORY_KEYS = [
  { emoji: "\uD83D\uDCCD", labelKey: "onboarding.catPhysical" },
  { emoji: "\uD83D\uDCF7", labelKey: "onboarding.catPhotos" },
  { emoji: "\uD83D\uDCDA", labelKey: "onboarding.catKnowledge" },
  { emoji: "\uD83D\uDCE6", labelKey: "onboarding.catDelivery" },
  { emoji: "\uD83D\uDD0D", labelKey: "onboarding.catVerification" },
  { emoji: "\uD83D\uDCDD", labelKey: "onboarding.catDocuments" },
];

// ---------------------------------------------------------------------------
// Slide components
// ---------------------------------------------------------------------------

function HeroSlide() {
  const { t } = useTranslation();
  return (
    <View style={{ width }} className="flex-1 items-center justify-center px-8">
      {/* Logo */}
      <View className="bg-white rounded-3xl p-1 mb-6" style={{ elevation: 10 }}>
        <Image
          source={require("../assets/images/logo.png")}
          style={{ width: 140, height: 140, borderRadius: 20 }}
          resizeMode="contain"
        />
      </View>

      {/* Title */}
      <Text className="text-white text-4xl font-bold text-center tracking-tight">
        Execution Market
      </Text>

      {/* Tagline */}
      <View className="mt-3 px-4 py-1.5 rounded-full border border-gray-700">
        <Text className="text-gray-300 text-sm font-medium tracking-wide text-center">
          Universal Execution Layer
        </Text>
      </View>

      {/* Description */}
      <Text className="text-gray-400 text-base text-center mt-6 leading-6 px-4">
        {t("onboarding.description")}
      </Text>

      {/* Subtle stat row */}
      <View className="flex-row items-center mt-8 gap-6">
        <View className="items-center">
          <Text className="text-white text-2xl font-bold">8</Text>
          <Text className="text-gray-500 text-xs mt-1">{t("onboarding.blockchains")}</Text>
        </View>
        <View className="w-px h-8 bg-gray-700" />
        <View className="items-center">
          <Text className="text-white text-2xl font-bold">5</Text>
          <Text className="text-gray-500 text-xs mt-1">{t("onboarding.stablecoins")}</Text>
        </View>
        <View className="w-px h-8 bg-gray-700" />
        <View className="items-center">
          <Text className="text-white text-2xl font-bold">21</Text>
          <Text className="text-gray-500 text-xs mt-1">{t("onboarding.categoriesLabel")}</Text>
        </View>
      </View>
    </View>
  );
}

function HowItWorksSlide() {
  const { t } = useTranslation();
  return (
    <View style={{ width }} className="flex-1 justify-center px-6">
      <Text className="text-white text-3xl font-bold text-center mb-2">
        {t("onboarding.howItWorks")}
      </Text>
      <Text className="text-gray-500 text-sm text-center mb-8">
        {t("onboarding.howItWorksSubtitle")}
      </Text>

      {/* Steps */}
      {STEP_KEYS.map((step, i) => (
        <View
          key={i}
          className="flex-row items-center bg-gray-900 rounded-2xl p-4 mb-3"
          style={{ borderWidth: 1, borderColor: "#1a1a1a" }}
        >
          <View className="w-12 h-12 rounded-full bg-white items-center justify-center mr-4">
            <Text className="text-black text-lg font-bold">{step.emoji}</Text>
          </View>
          <View className="flex-1">
            <Text className="text-white text-lg font-bold">{t(step.labelKey)}</Text>
            <Text className="text-gray-400 text-sm mt-0.5">{t(step.descKey)}</Text>
          </View>
        </View>
      ))}

      {/* Category pills */}
      <Text className="text-gray-500 text-xs text-center mt-6 mb-3">
        {t("onboarding.taskCategories")}
      </Text>
      <View className="flex-row flex-wrap justify-center gap-2">
        {CATEGORY_KEYS.map((cat, i) => (
          <View
            key={i}
            className="flex-row items-center bg-gray-900 rounded-full px-3 py-1.5"
            style={{ borderWidth: 1, borderColor: "#222" }}
          >
            <Text style={{ fontSize: 14 }}>{cat.emoji}</Text>
            <Text className="text-gray-300 text-xs ml-1.5">{t(cat.labelKey)}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function ChainsSlide() {
  const { t } = useTranslation();
  return (
    <View style={{ width }} className="flex-1 justify-center px-6">
      <Text className="text-white text-3xl font-bold text-center mb-2">
        {t("onboarding.chainsTitle")}
      </Text>
      <Text className="text-gray-500 text-sm text-center mb-8">
        {t("onboarding.chainsSubtitle")}
      </Text>

      {/* Chain grid — 2 columns, 4 rows */}
      <View className="flex-row flex-wrap justify-center" style={{ gap: 12 }}>
        {CHAINS.map((chain, i) => (
          <View
            key={i}
            className="items-center bg-gray-900 rounded-2xl p-4"
            style={{
              width: (width - 60) / 2 - 6,
              borderWidth: 1,
              borderColor: "#1a1a1a",
            }}
          >
            <View className="bg-gray-800 rounded-xl p-2">
              <Image
                source={chain.icon}
                style={{ width: 40, height: 40 }}
                resizeMode="contain"
              />
            </View>
            <Text className="text-white text-sm font-semibold mt-2">
              {chain.name}
            </Text>
          </View>
        ))}
      </View>

      <Text className="text-gray-600 text-xs text-center mt-6">
        {t("onboarding.chainsGasless")}
      </Text>
    </View>
  );
}

function CoinsSlide() {
  const { t } = useTranslation();
  return (
    <View style={{ width }} className="flex-1 justify-center px-6">
      <Text className="text-white text-3xl font-bold text-center mb-2">
        {t("onboarding.coinsTitle")}
      </Text>
      <Text className="text-gray-500 text-sm text-center mb-8">
        {t("onboarding.coinsSubtitle")}
      </Text>

      {/* Coin row */}
      <View className="flex-row justify-center" style={{ gap: 16 }}>
        {COINS.map((coin, i) => (
          <View key={i} className="items-center">
            <View
              className="bg-gray-900 rounded-2xl p-3"
              style={{ borderWidth: 1, borderColor: "#1a1a1a" }}
            >
              <Image
                source={coin.icon}
                style={{ width: 48, height: 48 }}
                resizeMode="contain"
              />
            </View>
            <Text className="text-white text-xs font-semibold mt-2">
              {coin.name}
            </Text>
          </View>
        ))}
      </View>

      {/* Gasless callout */}
      <View
        className="bg-gray-900 rounded-2xl p-5 mt-8 mx-2"
        style={{ borderWidth: 1, borderColor: "#1a1a1a" }}
      >
        <Text className="text-white text-lg font-bold text-center mb-1">
          {t("onboarding.gaslessTitle")}
        </Text>
        <Text className="text-gray-400 text-sm text-center leading-5">
          {t("onboarding.gaslessDesc")}
        </Text>
      </View>

      {/* Features row */}
      <View className="flex-row justify-center mt-6 gap-6">
        <View className="items-center">
          <Text className="text-gray-300 text-xs">EIP-3009</Text>
          <Text className="text-gray-600 text-xs">{t("onboarding.gaslessSigs")}</Text>
        </View>
        <View className="w-px h-8 bg-gray-800" />
        <View className="items-center">
          <Text className="text-gray-300 text-xs">x402</Text>
          <Text className="text-gray-600 text-xs">{t("onboarding.paymentProtocol")}</Text>
        </View>
        <View className="w-px h-8 bg-gray-800" />
        <View className="items-center">
          <Text className="text-gray-300 text-xs">Escrow</Text>
          <Text className="text-gray-600 text-xs">{t("onboarding.protectedFunds")}</Text>
        </View>
      </View>
    </View>
  );
}

function GetStartedSlide() {
  const { t } = useTranslation();
  return (
    <View style={{ width }} className="flex-1 items-center justify-center px-8">
      {/* Logo */}
      <View className="bg-white rounded-3xl p-1 mb-6" style={{ elevation: 10 }}>
        <Image
          source={require("../assets/images/logo.png")}
          style={{ width: 100, height: 100, borderRadius: 16 }}
          resizeMode="contain"
        />
      </View>

      <Text className="text-white text-3xl font-bold text-center">
        {t("onboarding.getStarted")}
      </Text>

      <Text className="text-gray-400 text-base text-center mt-3 leading-6">
        {t("onboarding.getStartedDesc")}
      </Text>

      {/* Stats */}
      <View
        className="bg-gray-900 rounded-2xl p-5 mt-8 w-full"
        style={{ borderWidth: 1, borderColor: "#1a1a1a" }}
      >
        <View className="flex-row justify-between">
          <View className="items-center flex-1">
            <Text className="text-white text-xl font-bold">87%</Text>
            <Text className="text-gray-500 text-xs mt-1 text-center">
              {t("onboarding.forExecutor")}
            </Text>
          </View>
          <View className="w-px bg-gray-800" />
          <View className="items-center flex-1">
            <Text className="text-white text-xl font-bold">13%</Text>
            <Text className="text-gray-500 text-xs mt-1 text-center">
              {t("onboarding.platformFee")}
            </Text>
          </View>
          <View className="w-px bg-gray-800" />
          <View className="items-center flex-1">
            <Text className="text-white text-xl font-bold">$0.01</Text>
            <Text className="text-gray-500 text-xs mt-1 text-center">
              {t("onboarding.minTask")}
            </Text>
          </View>
        </View>
      </View>

      {/* Trust signals */}
      <View className="flex-row flex-wrap justify-center mt-6 gap-2">
        {[
          "ERC-8004 Identity",
          t("onboarding.onchainReputation"),
          t("onboarding.trustlessEscrow"),
          t("onboarding.gaslessPayments"),
        ].map((tag, i) => (
          <View
            key={i}
            className="bg-gray-900 rounded-full px-3 py-1.5"
            style={{ borderWidth: 1, borderColor: "#222" }}
          >
            <Text className="text-gray-300 text-xs">{tag}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Slide definitions
// ---------------------------------------------------------------------------
const SLIDE_COUNT = 5;

const SLIDE_COMPONENTS = [
  HeroSlide,
  HowItWorksSlide,
  ChainsSlide,
  CoinsSlide,
  GetStartedSlide,
];

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------
export default function OnboardingScreen() {
  const { t } = useTranslation();
  const [currentIndex, setCurrentIndex] = useState(0);
  const flatListRef = useRef<FlatList>(null);

  const handleComplete = useCallback(async () => {
    await AsyncStorage.setItem("em_onboarding_complete", "true");
    router.replace("/(tabs)");
  }, []);

  const handleNext = useCallback(() => {
    if (currentIndex < SLIDE_COUNT - 1) {
      flatListRef.current?.scrollToIndex({ index: currentIndex + 1 });
    } else {
      handleComplete();
    }
  }, [currentIndex, handleComplete]);

  const isLastSlide = currentIndex === SLIDE_COUNT - 1;

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Language selector */}
      <View className="flex-row justify-end px-4 pt-2">
        <LanguageToggle />
      </View>

      <FlatList
        ref={flatListRef}
        data={SLIDE_COMPONENTS}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={(e) => {
          const index = Math.round(e.nativeEvent.contentOffset.x / width);
          setCurrentIndex(index);
        }}
        renderItem={({ item: SlideComponent }) => <SlideComponent />}
        keyExtractor={(_, i) => String(i)}
        getItemLayout={(_, index) => ({
          length: width,
          offset: width * index,
          index,
        })}
      />

      {/* Navigation controls */}
      <View className="px-8 pb-8">
        {/* Dots */}
        <View className="flex-row justify-center gap-2 mb-6">
          {Array.from({ length: SLIDE_COUNT }).map((_, i) => (
            <View
              key={i}
              className={`h-2 rounded-full ${
                i === currentIndex ? "w-8 bg-white" : "w-2 bg-gray-700"
              }`}
            />
          ))}
        </View>

        {/* Next / Get Started button */}
        <Pressable
          className="bg-white rounded-2xl py-4 items-center mb-3"
          onPress={handleNext}
          style={({ pressed }) => ({ opacity: pressed ? 0.85 : 1 })}
        >
          <Text className="text-black font-bold text-lg">
            {isLastSlide ? t("onboarding.startButton") : t("onboarding.nextButton")}
          </Text>
        </Pressable>

        {/* Skip button */}
        {!isLastSlide && (
          <Pressable className="py-3 items-center" onPress={handleComplete}>
            <Text className="text-gray-500">{t("onboarding.skip")}</Text>
          </Pressable>
        )}
      </View>
    </SafeAreaView>
  );
}
