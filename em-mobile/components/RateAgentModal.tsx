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
  const [score, setScore] = useState(4);
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
          score: score * 20, // Convert 1-5 to 0-100
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

          {/* Star rating */}
          <View className="flex-row justify-center gap-4 mb-6">
            {[1, 2, 3, 4, 5].map((star) => (
              <Pressable key={star} onPress={() => setScore(star)}>
                <Text style={{ fontSize: 36 }}>
                  {star <= score ? "★" : "☆"}
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
