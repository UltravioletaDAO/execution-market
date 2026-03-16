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
  GestureResponderEvent,
} from "react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { apiClient } from "../lib/api";

interface RateAgentModalProps {
  visible: boolean;
  onClose: () => void;
  taskId: string;
  agentId: number;
  agentName?: string;
  suggestedScore?: number;
}

export function RateAgentModal({ visible, onClose, taskId, agentId, agentName, suggestedScore }: RateAgentModalProps) {
  const { t } = useTranslation();
  const [score, setScore] = useState(suggestedScore ?? 80);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleRate() {
    setSubmitting(true);
    try {
      await apiClient("/api/v1/reputation/agents/rate", {
        method: "POST",
        body: {
          agent_id: agentId,
          task_id: taskId,
          score,
          comment: comment.trim() || undefined,
        },
      });
      onClose();
    } catch (e) {
      // Silent fail -- rating is optional
      onClose();
    } finally {
      setSubmitting(false);
    }
  }

  const scoreColor = score >= 80 ? "#4ade80" : score >= 50 ? "#facc15" : "#f87171";

  return (
    <Modal visible={visible} transparent animationType="slide">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <View className="flex-1 justify-end">
          <Pressable className="flex-1" onPress={onClose} />
          <ScrollView
            bounces={false}
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{ flexGrow: 0 }}
          >
            <View className="bg-surface-light rounded-t-3xl px-6 pt-6 pb-10">
              <View className="w-12 h-1 bg-gray-600 rounded-full self-center mb-4" />

              <Text className="text-white text-xl font-bold mb-1">
                {t("rate.title")}
              </Text>
              {agentName && (
                <Text className="text-gray-400 text-sm mb-3">{agentName}</Text>
              )}

              {/* Score display */}
              <View className="items-center mb-2">
                <Text style={{ fontSize: 56, fontWeight: "800", color: scoreColor }}>
                  {score}
                </Text>
                <Text className="text-gray-500 text-sm">/100</Text>
              </View>

              {/* Slider track */}
              <View className="mb-2 px-2">
                <Pressable
                  onPress={(e: GestureResponderEvent) => {
                    const { locationX } = e.nativeEvent;
                    const trackWidth = 300; // approximate
                    const pct = Math.max(0, Math.min(100, Math.round((locationX / trackWidth) * 100)));
                    setScore(pct);
                  }}
                  style={{ height: 40, justifyContent: "center" }}
                >
                  <View style={{ height: 6, borderRadius: 3, backgroundColor: "#374151", overflow: "hidden" }}>
                    <View style={{ width: `${score}%`, height: "100%", backgroundColor: scoreColor, borderRadius: 3 }} />
                  </View>
                </Pressable>
                <View className="flex-row justify-between px-1">
                  <Text className="text-gray-600 text-xs">0</Text>
                  <Text className="text-gray-600 text-xs">50</Text>
                  <Text className="text-gray-600 text-xs">100</Text>
                </View>
              </View>

              {/* Quick presets */}
              <View className="flex-row justify-center gap-2 mb-4">
                {[20, 40, 60, 80, 100].map((preset) => (
                  <Pressable
                    key={preset}
                    onPress={() => setScore(preset)}
                    className={`px-3 py-1.5 rounded-lg ${score === preset ? "bg-white" : "bg-surface"}`}
                  >
                    <Text className={`text-sm font-semibold ${score === preset ? "text-black" : "text-gray-500"}`}>
                      {preset}
                    </Text>
                  </Pressable>
                ))}
              </View>

              <TextInput
                className="bg-surface rounded-xl px-4 py-3 text-white mb-4"
                placeholder={t("rate.commentPlaceholder")}
                placeholderTextColor="#666"
                value={comment}
                onChangeText={setComment}
                multiline
                numberOfLines={2}
                style={{ minHeight: 60, textAlignVertical: "top" }}
              />

              <Pressable
                className={`rounded-2xl py-4 items-center ${submitting ? "bg-gray-700" : "bg-white"}`}
                onPress={handleRate}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text className="text-black font-bold text-lg">{t("rate.submitRating")}</Text>
                )}
              </Pressable>

              <Pressable className="py-3 items-center mt-1" onPress={onClose}>
                <Text className="text-gray-400">{t("rate.skip")}</Text>
              </Pressable>
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
