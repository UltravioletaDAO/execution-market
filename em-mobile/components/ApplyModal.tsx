import { View, Text, Pressable, TextInput, Modal, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView } from "react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useApplyToTask } from "../hooks/api/useTasks";
import { useAuth } from "../providers/AuthProvider";

interface ApplyModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  taskId: string;
  taskTitle: string;
  bounty: number;
}

export function ApplyModal({ visible, onClose, onSuccess, taskId, taskTitle, bounty }: ApplyModalProps) {
  const { t } = useTranslation();
  const { executor } = useAuth();
  const [message, setMessage] = useState("");
  const [applied, setApplied] = useState(false);
  const applyMutation = useApplyToTask();

  async function handleApply() {
    if (!executor?.id) return;
    try {
      await applyMutation.mutateAsync({
        taskId,
        executorId: executor.id,
        message: message.trim() || undefined,
      });
      setApplied(true);
      onSuccess?.();
    } catch {
      // Error handled by mutation state
    }
  }

  function handleClose() {
    setApplied(false);
    setMessage("");
    applyMutation.reset();
    onClose();
  }

  // Success state
  if (applied) {
    return (
      <Modal visible={visible} transparent animationType="slide">
        <View className="flex-1 justify-end">
          <Pressable className="flex-1" onPress={handleClose} />
          <View className="bg-surface-light rounded-t-3xl px-6 pt-6 pb-10">
            <View className="w-12 h-1 bg-gray-600 rounded-full self-center mb-6" />

            <View className="items-center py-6">
              <View className="w-16 h-16 rounded-full bg-green-900/30 items-center justify-center mb-4">
                <Text style={{ fontSize: 32 }}>&#x2705;</Text>
              </View>
              <Text className="text-white text-xl font-bold mb-2">
                {t("apply.successTitle")}
              </Text>
              <Text className="text-gray-400 text-sm text-center px-4">
                {t("apply.successMessage")}
              </Text>
              <View className="bg-green-900/30 rounded-xl px-4 py-2 mt-4">
                <Text className="text-green-400 font-bold">
                  ${bounty.toFixed(2)} USDC
                </Text>
              </View>
            </View>

            <Pressable
              className="bg-white rounded-2xl py-4 items-center mt-2"
              onPress={handleClose}
            >
              <Text className="text-black font-bold text-lg">{t("common.understood")}</Text>
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

              <Text className="text-white text-xl font-bold mb-2">
                {t("apply.title")}
              </Text>
              <Text className="text-gray-400 text-sm mb-4" numberOfLines={2}>
                {taskTitle}
              </Text>

              <View className="bg-green-900/30 rounded-2xl p-4 mb-4 items-center">
                <Text className="text-green-400 text-2xl font-bold">
                  ${bounty.toFixed(2)} USDC
                </Text>
                <Text className="text-gray-400 text-xs mt-1">{t("apply.reward")}</Text>
              </View>

              <Text className="text-gray-400 text-sm mb-2">
                {t("apply.messageLabel")}
              </Text>
              <TextInput
                className="bg-surface rounded-xl px-4 py-3 text-white mb-4"
                placeholder={t("apply.messagePlaceholder")}
                placeholderTextColor="#666"
                value={message}
                onChangeText={setMessage}
                multiline
                numberOfLines={3}
                style={{ minHeight: 80, textAlignVertical: "top" }}
              />

              {applyMutation.isError && (
                <View className="bg-red-900/30 rounded-xl p-3 mb-4">
                  <Text className="text-red-400 text-sm">
                    {(applyMutation.error as Error)?.message || t("apply.applyError")}
                  </Text>
                </View>
              )}

              <Pressable
                className={`rounded-2xl py-4 items-center ${
                  applyMutation.isPending ? "bg-gray-700" : "bg-white"
                }`}
                onPress={handleApply}
                disabled={applyMutation.isPending}
              >
                {applyMutation.isPending ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text className="text-black font-bold text-lg">
                    {t("apply.applyButton")}
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
