import {
  View,
  Text,
  Pressable,
  TextInput,
  Modal,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { useState } from "react";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";
import { apiClient } from "../lib/api";

const REPORT_REASONS = [
  "spam",
  "abuse",
  "fraud",
  "inappropriate",
  "harassment",
  "other",
] as const;

type ReportReason = (typeof REPORT_REASONS)[number];

interface ReportModalProps {
  visible: boolean;
  onClose: () => void;
  targetType: "task" | "submission" | "message" | "user";
  targetId: string;
}

export function ReportModal({ visible, onClose, targetType, targetId }: ReportModalProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState<ReportReason | null>(null);
  const [details, setDetails] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleClose() {
    setReason(null);
    setDetails("");
    setSubmitted(false);
    setError(null);
    onClose();
  }

  async function handleSubmit() {
    if (!reason) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiClient("/api/v1/reports", {
        method: "POST",
        body: {
          target_type: targetType,
          target_id: targetId,
          reason,
          details: details.trim() || undefined,
        },
      });
      setSubmitted(true);
    } catch (err) {
      setError((err as Error).message || t("report.error"));
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <Modal visible={visible} transparent animationType="slide">
        <View className="flex-1 justify-end">
          <Pressable className="flex-1" onPress={handleClose} />
          <View className="bg-surface-light rounded-t-3xl px-6 pt-6 pb-10">
            <View className="w-12 h-1 bg-gray-600 rounded-full self-center mb-6" />
            <View className="items-center py-6">
              <View className="w-16 h-16 rounded-full bg-green-900/30 items-center justify-center mb-4">
                <Ionicons name="checkmark-circle" size={40} color="#4ade80" />
              </View>
              <Text className="text-white text-xl font-bold mb-2">
                {t("report.thankYou")}
              </Text>
              <Text className="text-gray-400 text-sm text-center px-4">
                {t("report.submitted")}
              </Text>
            </View>
            <Pressable
              className="bg-white rounded-2xl py-4 items-center mt-2"
              onPress={handleClose}
            >
              <Text className="text-black font-bold text-lg">{t("common.close")}</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    );
  }

  return (
    <Modal visible={visible} transparent animationType="slide">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <View className="flex-1 justify-end">
          <Pressable className="flex-1" onPress={handleClose} />
          <ScrollView
            bounces={false}
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{ flexGrow: 0 }}
          >
            <View className="bg-surface-light rounded-t-3xl px-6 pt-6 pb-10">
              <View className="w-12 h-1 bg-gray-600 rounded-full self-center mb-6" />

              <View className="flex-row items-center mb-4">
                <Ionicons name="flag" size={20} color="#ef4444" />
                <Text className="text-white text-xl font-bold ml-2">
                  {t("report.title")}
                </Text>
              </View>

              <Text className="text-gray-400 text-sm mb-4">
                {t("report.selectReason")}
              </Text>

              {REPORT_REASONS.map((r) => (
                <Pressable
                  key={r}
                  className={`flex-row items-center rounded-xl px-4 py-3 mb-2 ${
                    reason === r ? "bg-white/10 border border-white/20" : "bg-surface"
                  }`}
                  onPress={() => setReason(r)}
                >
                  <View
                    className={`w-5 h-5 rounded-full border-2 items-center justify-center mr-3 ${
                      reason === r ? "border-white bg-white" : "border-gray-600"
                    }`}
                  >
                    {reason === r && (
                      <View className="w-2.5 h-2.5 rounded-full bg-black" />
                    )}
                  </View>
                  <Text className={`text-sm ${reason === r ? "text-white font-medium" : "text-gray-400"}`}>
                    {t(`report.reason_${r}`)}
                  </Text>
                </Pressable>
              ))}

              <Text className="text-gray-400 text-sm mt-4 mb-2">
                {t("report.detailsLabel")}
              </Text>
              <TextInput
                className="bg-surface rounded-xl px-4 py-3 text-white mb-4"
                placeholder={t("report.detailsPlaceholder")}
                placeholderTextColor="#666"
                value={details}
                onChangeText={setDetails}
                multiline
                numberOfLines={3}
                style={{ minHeight: 80, textAlignVertical: "top" }}
              />

              {error && (
                <View className="bg-red-900/30 rounded-xl p-3 mb-4">
                  <Text className="text-red-400 text-sm">{error}</Text>
                </View>
              )}

              <Pressable
                className={`rounded-2xl py-4 items-center ${
                  !reason || submitting ? "bg-gray-700" : "bg-red-600"
                }`}
                onPress={handleSubmit}
                disabled={!reason || submitting}
              >
                {submitting ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text className="text-white font-bold text-lg">
                    {t("report.submit")}
                  </Text>
                )}
              </Pressable>

              <Pressable className="py-3 items-center mt-2" onPress={handleClose}>
                <Text className="text-gray-400">{t("common.cancel")}</Text>
              </Pressable>
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
