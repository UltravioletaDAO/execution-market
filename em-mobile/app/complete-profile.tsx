import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import { useAuth } from "../providers/AuthProvider";
import { supabase } from "../lib/supabase";
import { dynamicClient } from "../lib/dynamic";
import { useReactiveClient } from "@dynamic-labs/react-hooks";

const PREDEFINED_SKILLS = [
  "photography",
  "delivery",
  "verification",
  "data_collection",
  "translation",
  "notarization",
  "physical_inspection",
  "document_handling",
  "research",
  "transcription",
] as const;

const LANGUAGE_OPTIONS = [
  "Spanish",
  "English",
  "Portuguese",
  "French",
  "German",
  "Italian",
  "Chinese",
  "Japanese",
] as const;

export default function CompleteProfileScreen() {
  const { t } = useTranslation();
  const { executor, refreshExecutor, wallet } = useAuth();
  const { auth, wallets } = useReactiveClient(dynamicClient);

  // Don't pre-fill auto-generated names (Worker_XXXX)
  const isAutoName =
    executor?.display_name && /^Worker_[0-9a-f]{8}$/i.test(executor.display_name);

  const [name, setName] = useState(isAutoName ? "" : executor?.display_name || "");
  const [bio, setBio] = useState(executor?.bio || "");
  const [email, setEmail] = useState(executor?.email || "");
  const [city, setCity] = useState(executor?.location_city || "");
  const [country, setCountry] = useState(executor?.location_country || "");
  const [selectedSkills, setSelectedSkills] = useState<string[]>(
    executor?.skills || []
  );
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(
    executor?.languages?.length ? executor.languages : ["English"]
  );
  const [saving, setSaving] = useState(false);

  const isValid = name.trim().length > 0 && bio.trim().length > 0;

  function toggleSkill(skill: string) {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    );
  }

  function toggleLanguage(lang: string) {
    setSelectedLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  }

  async function handleSave() {
    console.log("[CompleteProfile] handleSave — executor?.id:", executor?.id, "wallet:", wallet, "isValid:", isValid);
    if (!isValid) {
      Alert.alert(t("common.error"), "Name and bio are required.");
      return;
    }

    setSaving(true);
    try {
      let executorId = executor?.id;

      // If no executor exists yet, create one via RPC
      if (!executorId) {
        // Try multiple sources for wallet address
        let resolvedWallet = wallet;
        if (!resolvedWallet) {
          // Try Dynamic userWallets
          resolvedWallet = wallets?.userWallets?.[0]?.address?.toLowerCase() ?? null;
        }
        if (!resolvedWallet) {
          // Try Dynamic embedded wallet
          try {
            const embedded = wallets?.embedded?.hasWallet
              ? wallets.embedded.getWallet()
              : null;
            resolvedWallet = embedded?.address?.toLowerCase() ?? null;
          } catch { /* ignore */ }
        }
        if (!resolvedWallet) {
          // Try verifiedCredentials
          const creds = auth?.authenticatedUser?.verifiedCredentials;
          if (Array.isArray(creds)) {
            const bc = creds.find((c: any) => c.format === "blockchain" && c.address);
            resolvedWallet = bc?.address?.toLowerCase() ?? null;
          }
        }
        if (!resolvedWallet) {
          // Last resort: generate a placeholder wallet from the Dynamic user ID
          const userId = auth?.authenticatedUser?.userId;
          if (userId) {
            // Create a deterministic pseudo-address from the user ID
            const hash = userId.replace(/-/g, "").slice(0, 40);
            resolvedWallet = `0x${hash}`;
            console.log("[CompleteProfile] Using pseudo-address from Dynamic userId:", resolvedWallet);
          }
        }
        if (!resolvedWallet) {
          Alert.alert(t("common.error"), "No wallet connected. Try logging out and back in.");
          setSaving(false);
          return;
        }
        console.log("[CompleteProfile] No executor — creating directly for wallet:", resolvedWallet);

        // Ensure Supabase anonymous session exists
        await supabase.auth.signInAnonymously();

        // First check if executor already exists by wallet
        const { data: existing } = await supabase
          .from("executors")
          .select("id")
          .eq("wallet_address", resolvedWallet)
          .maybeSingle();

        if (existing?.id) {
          executorId = existing.id;
          console.log("[CompleteProfile] Found existing executor:", executorId);
        } else {
          // Create new executor directly
          const { data: newExec, error: insertError } = await supabase
            .from("executors")
            .insert({
              wallet_address: resolvedWallet,
              display_name: name.trim(),
              email: email.trim() || null,
              bio: bio.trim(),
              skills: selectedSkills,
              languages: selectedLanguages,
              location_city: city.trim() || null,
              location_country: country.trim() || null,
              reputation_score: 50,
              status: "active",
            })
            .select("id")
            .single();

          if (insertError) {
            console.error("[CompleteProfile] Insert error:", insertError);
            Alert.alert(t("common.error"), insertError.message);
            setSaving(false);
            return;
          }

          executorId = newExec?.id;
          console.log("[CompleteProfile] Created executor:", executorId);
        }
      }

      if (!executorId) {
        Alert.alert(t("common.error"), "Could not create profile. Try logging out and back in.");
        setSaving(false);
        return;
      }

      // Update with full profile data
      const { error } = await supabase
        .from("executors")
        .update({
          display_name: name.trim(),
          bio: bio.trim(),
          email: email.trim() || null,
          skills: selectedSkills,
          languages: selectedLanguages,
          location_city: city.trim() || null,
          location_country: country.trim() || null,
        })
        .eq("id", executorId);

      if (error) {
        Alert.alert(t("common.error"), error.message);
        return;
      }

      await refreshExecutor();
      router.replace("/(tabs)");
    } catch {
      Alert.alert(t("common.error"), t("profile.saveError"));
    } finally {
      setSaving(false);
    }
  }

  function handleSkip() {
    router.replace("/(tabs)");
  }

  return (
    <SafeAreaView className="flex-1 bg-black">
      <KeyboardAvoidingView
        className="flex-1"
        behavior="padding"
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 24}
      >
      {/* Header */}
      <View className="px-4 pt-4 pb-2">
        <Text className="text-white text-2xl font-bold">{t("profile.completeProfile")}</Text>
        <Text className="text-gray-500 text-sm mt-1">
          {t("profile.completeProfileSubtitle")}
        </Text>
      </View>

      <ScrollView
        className="flex-1 px-4"
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="interactive"
      >
        {/* Display Name */}
        <Text className="text-gray-400 text-xs font-bold mb-2 mt-4">
          {t("common.name")} *
        </Text>
        <TextInput
          className="bg-surface text-white rounded-xl px-4 py-3.5 text-base mb-5"
          value={name}
          onChangeText={setName}
          placeholder={t("profile.namePlaceholder")}
          placeholderTextColor="#666"
          autoCapitalize="words"
          maxLength={50}
        />

        {/* Bio */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("common.bio")} *</Text>
        <TextInput
          className="bg-surface text-white rounded-xl px-4 py-3.5 text-base mb-1"
          value={bio}
          onChangeText={setBio}
          placeholder={t("profile.describeSkills")}
          placeholderTextColor="#666"
          multiline
          numberOfLines={3}
          style={{ minHeight: 80, textAlignVertical: "top" }}
          maxLength={500}

        />
        <Text className="text-gray-600 text-xs text-right mb-5">
          {bio.length}/500
        </Text>

        {/* Skills */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("common.skills")}</Text>
        <View className="flex-row flex-wrap gap-2 mb-5">
          {PREDEFINED_SKILLS.map((skill) => {
            const isSelected = selectedSkills.includes(skill);
            return (
              <Pressable
                key={skill}
                onPress={() => toggleSkill(skill)}
                className={`rounded-full px-4 py-2 ${
                  isSelected ? "bg-white" : "bg-surface"
                }`}
              >
                <Text
                  className={`text-sm font-medium ${
                    isSelected ? "text-black" : "text-gray-400"
                  }`}
                >
                  {skill.replace(/_/g, " ")}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {/* Languages */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("common.languages")}</Text>
        <View className="flex-row flex-wrap gap-2 mb-5">
          {LANGUAGE_OPTIONS.map((lang) => {
            const isSelected = selectedLanguages.includes(lang);
            return (
              <Pressable
                key={lang}
                onPress={() => toggleLanguage(lang)}
                className={`rounded-full px-4 py-2 ${
                  isSelected ? "bg-white" : "bg-surface"
                }`}
              >
                <Text
                  className={`text-sm font-medium ${
                    isSelected ? "text-black" : "text-gray-400"
                  }`}
                >
                  {lang}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {/* Email */}
        <Text className="text-gray-400 text-xs font-bold mb-2">
          {t("common.emailOptional")}
        </Text>
        <TextInput
          className="bg-surface text-white rounded-xl px-4 py-3.5 text-base mb-5"
          value={email}
          onChangeText={setEmail}
          placeholder={t("profile.forTaskNotifications")}
          placeholderTextColor="#666"
          keyboardType="email-address"
          autoCapitalize="none"

        />

        {/* Location */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("common.location")}</Text>
        <View className="flex-row gap-3 mb-8">
          <TextInput
            className="flex-1 bg-surface text-white rounded-xl px-4 py-3.5 text-base"
            value={city}
            onChangeText={setCity}
            placeholder={t("profile.city")}
            placeholderTextColor="#666"
  
          />
          <TextInput
            className="flex-1 bg-surface text-white rounded-xl px-4 py-3.5 text-base"
            value={country}
            onChangeText={setCountry}
            placeholder={t("profile.country")}
            placeholderTextColor="#666"
  
          />
        </View>

        {/* Extra padding so bottom fields scroll above keyboard */}
        <View className="h-40" />
      </ScrollView>

      {/* Footer */}
      <View className="px-4 pb-8 pt-3 border-t border-white/5">
        <Pressable
          className={`rounded-2xl py-4 items-center mb-3 ${
            isValid ? "bg-white" : "bg-gray-800"
          }`}
          onPress={handleSave}
          disabled={!isValid || saving}
          style={({ pressed }) => ({ opacity: pressed && isValid ? 0.85 : 1 })}
        >
          {saving ? (
            <ActivityIndicator size="small" color="#000" />
          ) : (
            <Text
              className={`font-bold text-lg ${
                isValid ? "text-black" : "text-gray-600"
              }`}
            >
              {t("profile.completeProfile")}
            </Text>
          )}
        </Pressable>

        <Pressable className="py-3 items-center" onPress={handleSkip}>
          <Text className="text-gray-500">{t("profile.skipForNow")}</Text>
        </Pressable>
      </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
