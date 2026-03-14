import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  ActivityIndicator,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import { useAuth } from "../providers/AuthProvider";
import { supabase } from "../lib/supabase";

const AVAILABLE_SKILLS = [
  "photography",
  "delivery",
  "translation",
  "verification",
  "data_entry",
  "research",
  "transcription",
  "design",
  "testing",
  "surveys",
] as const;

export default function EditProfileScreen() {
  const { t } = useTranslation();
  const { executor, refreshExecutor } = useAuth();

  const [name, setName] = useState(executor?.display_name || "");
  const [bio, setBio] = useState(executor?.bio || "");
  const [email, setEmail] = useState(executor?.email || "");
  const [city, setCity] = useState(executor?.location_city || "");
  const [country, setCountry] = useState(executor?.location_country || "");
  const [selectedSkills, setSelectedSkills] = useState<string[]>(
    executor?.skills || []
  );
  const [saving, setSaving] = useState(false);

  function toggleSkill(skill: string) {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    );
  }

  async function handleSave() {
    if (!executor?.id) return;

    setSaving(true);
    try {
      const { error } = await supabase
        .from("executors")
        .update({
          display_name: name.trim() || null,
          bio: bio.trim() || null,
          email: email.trim() || null,
          skills: selectedSkills,
          location_city: city.trim() || null,
          location_country: country.trim() || null,
        })
        .eq("id", executor.id);

      if (error) {
        Alert.alert(t("common.error"), error.message);
        return;
      }

      await refreshExecutor();
      router.back();
    } catch (err) {
      Alert.alert(t("common.error"), t("profile.saveError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center justify-between px-4 pt-4 pb-4">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"}</Text>
        </Pressable>
        <Text className="text-white text-xl font-bold">{t("profile.editProfile")}</Text>
        <Pressable
          onPress={handleSave}
          disabled={saving}
          className="py-2 pl-4"
        >
          {saving ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text className="text-white text-lg font-bold">{t("common.save")}</Text>
          )}
        </Pressable>
      </View>

      <ScrollView
        className="flex-1 px-4"
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {/* Avatar */}
        <View className="items-center mb-8 mt-4">
          <Pressable className="w-24 h-24 rounded-full bg-surface items-center justify-center">
            <Text style={{ fontSize: 40 }}>
              {executor?.avatar_url ? "" : "\uD83D\uDC64"}
            </Text>
          </Pressable>
          <Text className="text-gray-500 text-xs mt-2">
            {t("profile.tapToChangePhoto")}
          </Text>
        </View>

        {/* Display Name */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("common.name")}</Text>
        <TextInput
          className="bg-surface text-white rounded-xl px-4 py-3.5 text-base mb-5"
          value={name}
          onChangeText={setName}
          placeholder={t("profile.yourName")}
          placeholderTextColor="#666"
          autoCapitalize="words"
        />

        {/* Bio */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("common.bio")}</Text>
        <TextInput
          className="bg-surface text-white rounded-xl px-4 py-3.5 text-base mb-5"
          value={bio}
          onChangeText={setBio}
          placeholder={t("profile.tellAboutYourself")}
          placeholderTextColor="#666"
          multiline
          numberOfLines={3}
          style={{ minHeight: 80, textAlignVertical: "top" }}
        />

        {/* Email */}
        <Text className="text-gray-400 text-xs font-bold mb-2">{t("common.email")}</Text>
        <TextInput
          className="bg-surface text-white rounded-xl px-4 py-3.5 text-base mb-5"
          value={email}
          onChangeText={setEmail}
          placeholder="tu@email.com"
          placeholderTextColor="#666"
          keyboardType="email-address"
          autoCapitalize="none"
        />

        {/* Skills */}
        <Text className="text-gray-400 text-xs font-bold mb-2">
          {t("common.skills")}
        </Text>
        <View className="flex-row flex-wrap gap-2 mb-5">
          {AVAILABLE_SKILLS.map((skill) => {
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
                  {skill.replace("_", " ")}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {/* Location */}
        <Text className="text-gray-400 text-xs font-bold mb-2">
          {t("common.location")}
        </Text>
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

        <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}
