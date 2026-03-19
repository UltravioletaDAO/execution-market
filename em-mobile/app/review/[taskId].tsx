/**
 * Review Submission Screen
 *
 * For publishers to review submitted evidence: images, text, GPS data.
 * Approve or reject with optional reason.
 * Navigated to from task detail when status is "submitted" or "verifying".
 */

import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  Image,
  ActivityIndicator,
  TextInput,
  Alert,
  Dimensions,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { supabase } from "../../lib/supabase";
import { apiClient } from "../../lib/api";

const SCREEN_WIDTH = Dimensions.get("window").width;

interface Submission {
  id: string;
  task_id: string;
  executor_id: string;
  evidence: Record<string, unknown> | null;
  evidence_urls: string[] | null;
  notes: string | null;
  gps_lat: number | null;
  gps_lng: number | null;
  agent_verdict: string | null;
  created_at: string;
  status: string;
}

interface TaskInfo {
  id: string;
  title: string;
  instructions: string;
  bounty_usd: number;
  status: string;
}

export default function ReviewSubmissionScreen() {
  const { taskId } = useLocalSearchParams<{ taskId: string }>();
  const { t } = useTranslation();
  const [task, setTask] = useState<TaskInfo | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!taskId) return;
    setLoading(true);
    setError(null);

    try {
      // Fetch task
      const { data: taskData, error: taskError } = await supabase
        .from("tasks")
        .select("id, title, instructions, bounty_usd, status")
        .eq("id", taskId)
        .single();

      if (taskError) throw taskError;
      setTask(taskData);

      // Fetch latest submission for this task
      const { data: subData, error: subError } = await supabase
        .from("submissions")
        .select("*")
        .eq("task_id", taskId)
        .order("created_at", { ascending: false })
        .limit(1)
        .single();

      if (subError && subError.code !== "PGRST116") throw subError;
      setSubmission(subData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleApprove = async () => {
    if (!submission) return;
    setActionLoading(true);
    try {
      await apiClient(`/api/v1/submissions/${submission.id}/approve`, {
        method: "POST",
        body: { score: 80 },
      });
      Alert.alert(
        t("review.approvedTitle", "Approved"),
        t("review.approvedMessage", "Submission approved and payment initiated."),
        [{ text: "OK", onPress: () => router.back() }]
      );
    } catch (err) {
      Alert.alert(
        t("common.error", "Error"),
        err instanceof Error ? err.message : "Failed to approve"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!submission) return;
    setActionLoading(true);
    try {
      await apiClient(`/api/v1/submissions/${submission.id}/reject`, {
        method: "POST",
        body: { reason: rejectReason || "Does not meet requirements" },
      });
      Alert.alert(
        t("review.rejectedTitle", "Rejected"),
        t("review.rejectedMessage", "Submission has been rejected."),
        [{ text: "OK", onPress: () => router.back() }]
      );
    } catch (err) {
      Alert.alert(
        t("common.error", "Error"),
        err instanceof Error ? err.message : "Failed to reject"
      );
    } finally {
      setActionLoading(false);
    }
  };

  // Extract image URLs from evidence
  const getImageUrls = (): string[] => {
    if (!submission) return [];
    const urls: string[] = [];

    // From evidence_urls array
    if (submission.evidence_urls && Array.isArray(submission.evidence_urls)) {
      urls.push(...submission.evidence_urls);
    }

    // From evidence object (look for URL values)
    if (submission.evidence && typeof submission.evidence === "object") {
      for (const value of Object.values(submission.evidence)) {
        if (typeof value === "string" && (value.startsWith("http") || value.startsWith("/"))) {
          urls.push(value);
        }
        if (typeof value === "object" && value !== null && "url" in (value as Record<string, unknown>)) {
          const url = (value as Record<string, unknown>).url;
          if (typeof url === "string") urls.push(url);
        }
      }
    }

    return urls;
  };

  // Extract text evidence
  const getTextEvidence = (): Record<string, string> => {
    if (!submission?.evidence || typeof submission.evidence !== "object") return {};
    const text: Record<string, string> = {};
    for (const [key, value] of Object.entries(submission.evidence)) {
      if (typeof value === "string" && !value.startsWith("http")) {
        text[key] = value;
      } else if (typeof value === "object" && value !== null) {
        text[key] = JSON.stringify(value, null, 2);
      }
    }
    return text;
  };

  if (loading) {
    return (
      <SafeAreaView className="flex-1 bg-black items-center justify-center">
        <ActivityIndicator color="#ffffff" size="large" />
      </SafeAreaView>
    );
  }

  if (error || !task) {
    return (
      <SafeAreaView className="flex-1 bg-black">
        <View className="px-4 pt-4">
          <Pressable onPress={() => router.back()} className="py-2">
            <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
          </Pressable>
          <View className="items-center justify-center py-20">
            <Text className="text-red-400 text-base">{error || "Task not found"}</Text>
            <Pressable onPress={fetchData} className="mt-4 bg-white/10 px-4 py-2 rounded-lg">
              <Text className="text-white">{t("common.retry")}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  const imageUrls = getImageUrls();
  const textEvidence = getTextEvidence();

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
        </Pressable>
      </View>

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 20}
      >
      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        {/* Title */}
        <View className="mt-2 mb-4">
          <Text className="text-white text-2xl font-bold">{t("review.title")}</Text>
          <Text className="text-gray-400 text-sm mt-1">{task.title}</Text>
          <Text className="text-green-400 text-sm font-semibold mt-1">
            ${task.bounty_usd.toFixed(2)} USDC
          </Text>
        </View>

        {!submission ? (
          <View className="items-center justify-center py-20">
            <Text className="text-gray-500 text-base">
              {t("review.noSubmission", "No submission found for this task.")}
            </Text>
          </View>
        ) : (
          <>
            {/* Evidence Images */}
            {imageUrls.length > 0 && (
              <View className="mb-4">
                <Text className="text-white text-sm font-semibold mb-2">
                  {t("review.evidenceImages", "Evidence Images")}
                </Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  {imageUrls.map((url, idx) => (
                    <View key={idx} className="mr-3">
                      <Image
                        source={{ uri: url }}
                        style={{
                          width: SCREEN_WIDTH * 0.7,
                          height: SCREEN_WIDTH * 0.7,
                          borderRadius: 12,
                        }}
                        resizeMode="cover"
                      />
                    </View>
                  ))}
                </ScrollView>
              </View>
            )}

            {/* Text Evidence */}
            {Object.keys(textEvidence).length > 0 && (
              <View className="mb-4">
                <Text className="text-white text-sm font-semibold mb-2">
                  {t("review.evidenceText", "Evidence Details")}
                </Text>
                {Object.entries(textEvidence).map(([key, value]) => (
                  <View key={key} className="bg-surface rounded-xl p-3 mb-2">
                    <Text className="text-gray-400 text-xs uppercase mb-1">
                      {key.replace(/_/g, " ")}
                    </Text>
                    <Text className="text-white text-sm">{value}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Notes */}
            {submission.notes && (
              <View className="mb-4">
                <Text className="text-white text-sm font-semibold mb-2">
                  {t("review.workerNotes", "Worker Notes")}
                </Text>
                <View className="bg-surface rounded-xl p-3">
                  <Text className="text-gray-300 text-sm">{submission.notes}</Text>
                </View>
              </View>
            )}

            {/* GPS Data */}
            {(submission.gps_lat != null && submission.gps_lng != null) && (
              <View className="mb-4">
                <Text className="text-white text-sm font-semibold mb-2">
                  {t("review.gpsData", "GPS Location")}
                </Text>
                <View className="bg-surface rounded-xl p-3">
                  <Text className="text-gray-300 text-sm font-mono">
                    {submission.gps_lat.toFixed(6)}, {submission.gps_lng.toFixed(6)}
                  </Text>
                </View>
              </View>
            )}

            {/* Submission metadata */}
            <View className="mb-6">
              <Text className="text-gray-500 text-xs">
                {t("review.submittedAt", "Submitted")}: {new Date(submission.created_at).toLocaleString()}
              </Text>
            </View>

            {/* Action buttons */}
            {(submission.agent_verdict === null || submission.agent_verdict === "pending") && (
              <View className="mb-8">
                {showRejectForm ? (
                  <View className="mb-4">
                    <Text className="text-white text-sm font-semibold mb-2">
                      {t("review.rejectReason", "Reason for rejection (optional)")}
                    </Text>
                    <TextInput
                      className="bg-surface text-white rounded-xl p-3 text-sm min-h-[80px]"
                      placeholder={t("review.rejectPlaceholder", "Explain why this submission was rejected...")}
                      placeholderTextColor="#6B7280"
                      value={rejectReason}
                      onChangeText={setRejectReason}
                      multiline
                      textAlignVertical="top"
                    />
                    <View className="flex-row gap-3 mt-3">
                      <Pressable
                        onPress={handleReject}
                        disabled={actionLoading}
                        className="flex-1 bg-red-600 py-3 rounded-xl items-center"
                      >
                        {actionLoading ? (
                          <ActivityIndicator color="#ffffff" size="small" />
                        ) : (
                          <Text className="text-white font-semibold">
                            {t("review.confirmReject", "Confirm Reject")}
                          </Text>
                        )}
                      </Pressable>
                      <Pressable
                        onPress={() => setShowRejectForm(false)}
                        className="flex-1 bg-surface py-3 rounded-xl items-center"
                      >
                        <Text className="text-gray-400 font-semibold">{t("common.cancel")}</Text>
                      </Pressable>
                    </View>
                  </View>
                ) : (
                  <View className="flex-row gap-3">
                    <Pressable
                      onPress={handleApprove}
                      disabled={actionLoading}
                      className="flex-1 bg-green-600 py-3.5 rounded-xl items-center"
                    >
                      {actionLoading ? (
                        <ActivityIndicator color="#ffffff" size="small" />
                      ) : (
                        <Text className="text-white font-bold text-base">
                          {t("review.approve", "Approve")}
                        </Text>
                      )}
                    </Pressable>
                    <Pressable
                      onPress={() => setShowRejectForm(true)}
                      disabled={actionLoading}
                      className="flex-1 bg-red-600/80 py-3.5 rounded-xl items-center"
                    >
                      <Text className="text-white font-bold text-base">
                        {t("review.reject", "Reject")}
                      </Text>
                    </Pressable>
                  </View>
                )}
              </View>
            )}

            {/* Already reviewed notice */}
            {submission.agent_verdict && submission.agent_verdict !== "pending" && (
              <View className="mb-8 bg-surface rounded-xl p-4 items-center">
                <Text className="text-gray-400 text-sm">
                  {t("review.alreadyReviewed", "This submission has already been reviewed.")}
                </Text>
                <Text className="text-white font-semibold mt-1 capitalize">
                  {submission.agent_verdict}
                </Text>
              </View>
            )}
          </>
        )}
      </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
