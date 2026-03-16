import { View, Text, Pressable, TextInput, Modal, ActivityIndicator } from "react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { apiClient } from "../lib/api";

interface RateAgentModalProps {
  visible: boolean;
  onClose: () => void;
  taskId: string;
  agentId: number;
  agentName?: string;
}

export function RateAgentModal({ visible, onClose, taskId, agentId, agentName }: RateAgentModalProps) {
  const { t } = useTranslation();
  const [score, setScore] = useState(80);
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

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View className="flex-1 justify-end">
        <Pressable className="flex-1" onPress={onClose} />
        <View className="bg-surface-light rounded-t-3xl px-6 pt-6 pb-10">
          <View className="w-12 h-1 bg-gray-600 rounded-full self-center mb-6" />

          <Text className="text-white text-xl font-bold mb-1">
            {t("rate.title")}
          </Text>
          {agentName && (
            <Text className="text-gray-400 text-sm mb-4">{agentName}</Text>
          )}

          {/* Score display */}
          <View className="items-center mb-4">
            <View className="flex-row items-baseline">
              <Text className="text-white font-bold" style={{ fontSize: 48 }}>
                {score}
              </Text>
              <Text className="text-gray-400 text-xl ml-1">/100</Text>
            </View>
          </View>

          {/* Preset buttons */}
          <View className="flex-row justify-center gap-3 mb-3">
            {[20, 40, 60, 80, 100].map((preset) => (
              <Pressable
                key={preset}
                onPress={() => setScore(preset)}
                className={`px-4 py-2 rounded-xl ${score === preset ? "bg-white" : "bg-surface"}`}
              >
                <Text className={`font-bold ${score === preset ? "text-black" : "text-gray-400"}`}>
                  {preset}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* Fine-tune +/- buttons */}
          <View className="flex-row justify-center gap-6 mb-6">
            <Pressable
              onPress={() => setScore((s) => Math.max(0, s - 5))}
              className="bg-surface px-5 py-2 rounded-xl"
            >
              <Text className="text-white font-bold text-lg">-5</Text>
            </Pressable>
            <Pressable
              onPress={() => setScore((s) => Math.max(0, s - 1))}
              className="bg-surface px-5 py-2 rounded-xl"
            >
              <Text className="text-white font-bold text-lg">-1</Text>
            </Pressable>
            <Pressable
              onPress={() => setScore((s) => Math.min(100, s + 1))}
              className="bg-surface px-5 py-2 rounded-xl"
            >
              <Text className="text-white font-bold text-lg">+1</Text>
            </Pressable>
            <Pressable
              onPress={() => setScore((s) => Math.min(100, s + 5))}
              className="bg-surface px-5 py-2 rounded-xl"
            >
              <Text className="text-white font-bold text-lg">+5</Text>
            </Pressable>
          </View>

          <TextInput
            className="bg-surface rounded-xl px-4 py-3 text-white mb-4"
            placeholder={t("rate.commentPlaceholder")}
            placeholderTextColor="#666"
            value={comment}
            onChangeText={setComment}
            multiline
            numberOfLines={3}
            style={{ minHeight: 80, textAlignVertical: "top" }}
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

          <Pressable className="py-3 items-center mt-2" onPress={onClose}>
            <Text className="text-gray-400">{t("rate.skip")}</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}
