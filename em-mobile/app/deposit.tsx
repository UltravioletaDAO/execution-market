import { View, Text, Pressable, TextInput, ActivityIndicator, Alert, Linking, ScrollView, AppState } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import { useSignMoonPayUrl, isMoonPayDisabledError } from "../hooks/api/useMoonPay";

/**
 * Deposit screen — fiat → USDC on Base via MoonPay (mobile onramp).
 *
 * Requests a signed Widget URL from the backend and opens it via Linking
 * (system browser handles KYC + payment; MoonPay delivers USDC to the user's
 * Base wallet). Balance refreshes when the user returns and pulls earnings.
 * In-app balance watch is a refinement (web uses Supabase Realtime). Mirrors
 * the web DepositModal. Requires device testing — Expo can't run headless here.
 */
const PRESETS = [10, 20, 50, 100];

export default function DepositScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  const { wallet, executor, isAuthenticated } = useAuth();
  const sign = useSignMoonPayUrl();
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState("20");
  // True once the user has been sent to MoonPay; drives the refresh-on-return UX.
  const [returnedFromMoonPay, setReturnedFromMoonPay] = useState(false);
  const launchedRef = useRef(false);

  // Pull fresh balances/earnings whenever the user comes back to the app after
  // completing (or abandoning) the MoonPay flow in the system browser.
  function refreshBalance() {
    queryClient.invalidateQueries({ queryKey: ["earnings"] });
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
  }

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active" && launchedRef.current) {
        setReturnedFromMoonPay(true);
        refreshBalance();
      }
    });
    return () => subscription.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleDeposit() {
    const amt = Math.max(5, parseFloat(amount) || 0);
    if (!isAuthenticated || !wallet) {
      Alert.alert(t("common.error", "Error"), t("deposit.connectFirst", "Conecta tu wallet primero."));
      return;
    }
    try {
      const res = await sign.mutateAsync({
        wallet_address: wallet,
        base_currency_amount: amt,
        currency_code: "usdc_base",
        external_customer_id: executor?.id,
      });
      const ok = await Linking.canOpenURL(res.url);
      if (ok) {
        launchedRef.current = true;
        await Linking.openURL(res.url);
      } else {
        Alert.alert(t("common.error", "Error"), t("deposit.cannotOpen", "No se pudo abrir MoonPay."));
      }
    } catch (e) {
      if (isMoonPayDisabledError(e)) {
        Alert.alert(
          t("common.error", "Error"),
          t("deposit.unavailable", "Los depósitos con tarjeta no están disponibles en este momento."),
        );
        return;
      }
      Alert.alert(
        t("common.error", "Error"),
        (e as Error).message || t("deposit.failed", "No se pudo iniciar el depósito."),
      );
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-black">
      <ScrollView contentContainerStyle={{ padding: 16 }}>
        <Pressable onPress={() => router.back()} className="mb-3">
          <Text className="text-gray-400">← {t("common.back", "Atrás")}</Text>
        </Pressable>

        <Text className="text-white text-2xl font-bold">
          {t("deposit.title", "Depositar USDC")}
        </Text>
        <Text className="text-gray-400 text-sm mt-1">
          {t("deposit.subtitle", "Compra USDC en Base con tarjeta vía MoonPay.")}
        </Text>

        <Text className="text-gray-400 text-xs mt-6 mb-2">{t("deposit.amount", "Monto (USD)")}</Text>
        <View className="flex-row gap-2 mb-3">
          {PRESETS.map((p) => (
            <Pressable
              key={p}
              onPress={() => setAmount(String(p))}
              className={`flex-1 rounded-xl py-3 items-center border ${
                amount === String(p) ? "bg-white border-white" : "bg-surface border-gray-800"
              }`}
            >
              <Text className={amount === String(p) ? "text-black font-bold" : "text-white"}>${p}</Text>
            </Pressable>
          ))}
        </View>

        <View className="flex-row items-center bg-surface rounded-xl px-4 border border-gray-800">
          <Text className="text-gray-400 text-lg">$</Text>
          <TextInput
            value={amount}
            onChangeText={setAmount}
            keyboardType="decimal-pad"
            className="flex-1 text-white text-lg py-4 px-2"
            placeholder="20"
            placeholderTextColor="#666"
          />
          <Text className="text-gray-400 text-sm">USDC · Base</Text>
        </View>
        <Text className="text-gray-500 text-xs mt-2">{t("deposit.min", "Mínimo $5.")}</Text>

        <Pressable
          onPress={handleDeposit}
          disabled={sign.isPending}
          className="bg-white rounded-2xl py-4 items-center mt-6"
        >
          {sign.isPending ? (
            <ActivityIndicator color="#000" />
          ) : (
            <Text className="text-black font-bold text-lg">
              {t("deposit.cta", "Depositar con MoonPay")}
            </Text>
          )}
        </Pressable>

        <Text className="text-gray-500 text-xs text-center mt-4">
          {t("deposit.note", "Se abrirá MoonPay para completar el pago. Tu USDC llegará a tu wallet en Base.")}
        </Text>

        {returnedFromMoonPay && (
          <View className="bg-surface border border-gray-800 rounded-2xl p-4 mt-6">
            <Text className="text-white text-sm font-medium text-center">
              {t("deposit.returned", "¿Completaste el pago? Tu USDC puede tardar unos minutos en llegar.")}
            </Text>
            <Pressable
              onPress={refreshBalance}
              className="bg-white rounded-xl py-3 items-center mt-3"
            >
              <Text className="text-black font-bold">{t("deposit.refresh", "Actualizar saldo")}</Text>
            </Pressable>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
