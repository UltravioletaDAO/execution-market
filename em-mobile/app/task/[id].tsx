import {
  View,
  Text,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Linking,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useTask, useMyApplication } from "../../hooks/api/useTasks";
import { useTaskPaymentEvents } from "../../hooks/api/useEarnings";
import { useAuth } from "../../providers/AuthProvider";
import { TASK_CATEGORIES } from "../../constants/categories";
import { NETWORKS, getExplorerTxUrl } from "../../constants/networks";
import { ApplyModal } from "../../components/ApplyModal";

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTimeRemaining(deadline: string, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const now = new Date();
  const dl = new Date(deadline);
  const diffMs = dl.getTime() - now.getTime();
  if (diffMs < 0) return t("task.expired");
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  if (hours > 24) return t("task.daysRemaining", { days: Math.floor(hours / 24), hours: hours % 24 });
  if (hours > 0) return t("task.hoursRemaining", { hours, minutes });
  return t("task.minutesRemaining", { minutes });
}

// Timeline step component
function TimelineStep({
  icon,
  label,
  sublabel,
  txHash,
  network,
  isCompleted,
  isLast,
  t,
}: {
  icon: string;
  label: string;
  sublabel?: string;
  txHash?: string | null;
  network?: string;
  isCompleted: boolean;
  isLast: boolean;
  t: (key: string) => string;
}) {
  return (
    <View className="flex-row">
      {/* Vertical line + dot */}
      <View className="items-center mr-3" style={{ width: 24 }}>
        <View
          className={`w-6 h-6 rounded-full items-center justify-center ${
            isCompleted ? "bg-green-900/40" : "bg-gray-800"
          }`}
        >
          <Text style={{ fontSize: 12 }}>{isCompleted ? icon : "○"}</Text>
        </View>
        {!isLast && (
          <View
            className={`w-0.5 flex-1 min-h-[20px] ${
              isCompleted ? "bg-green-800/40" : "bg-gray-800"
            }`}
          />
        )}
      </View>

      {/* Content */}
      <View className="flex-1 pb-3">
        <Text className={`text-sm font-medium ${isCompleted ? "text-white" : "text-gray-600"}`}>
          {label}
        </Text>
        {sublabel && (
          <Text className="text-gray-500 text-xs mt-0.5">{sublabel}</Text>
        )}
        {txHash && network && (
          <Pressable
            className="flex-row items-center mt-1"
            onPress={() => Linking.openURL(getExplorerTxUrl(network, txHash))}
          >
            <Text className="text-blue-400 text-xs">
              {t("task.viewTx")} · {txHash.slice(0, 10)}... ↗
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

export default function TaskDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useTranslation();
  const { isAuthenticated, executor } = useAuth();
  const { data: task, isLoading, isError, refetch } = useTask(id);
  const { data: myApplication } = useMyApplication(id, executor?.id ?? null);
  const { data: paymentEvents } = useTaskPaymentEvents(id);
  const [showApplyModal, setShowApplyModal] = useState(false);

  const hasApplied = myApplication?.applied === true;
  const isMyTask = !!(executor && task && task.executor_id === executor.id);

  // Auto-refresh task status every 10s when waiting for review/assignment
  // MUST be before any early returns (Rules of Hooks)
  useEffect(() => {
    if (!task) return;
    const shouldPoll = ["submitted", "accepted", "in_progress", "verifying"].includes(task.status) && isMyTask;
    const waitingAssignment = hasApplied && !isMyTask && task.status === "published";
    if (!shouldPoll && !waitingAssignment) return;

    const interval = setInterval(() => {
      refetch();
    }, 10000);
    return () => clearInterval(interval);
  }, [task?.status, isMyTask, hasApplied]);

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-black items-center justify-center">
        <ActivityIndicator color="#ffffff" size="large" />
      </SafeAreaView>
    );
  }

  if (isError || !task) {
    return (
      <SafeAreaView className="flex-1 bg-black items-center justify-center px-4">
        <Text className="text-red-500 text-xl mb-4">{t("common.error")}</Text>
        <Pressable onPress={() => router.back()}>
          <Text className="text-white">{t("common.back")}</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  const category = TASK_CATEGORIES.find((c) => c.key === task.category) ?? null;
  const network = NETWORKS.find((n) => n.key === task.payment_network) ?? null;

  const canApply =
    task.status === "published" &&
    !task.executor_id &&
    !hasApplied &&
    isAuthenticated &&
    (task.min_reputation === 0 ||
      (executor?.reputation_score || 0) >= task.min_reputation);

  // Determine bottom action bar content
  let bottomAction: "apply" | "applied" | "submitted" | "completed" | "submit" | "login" | "none" = "none";
  if (!isAuthenticated) {
    bottomAction = "login";
  } else if (isMyTask && ["accepted", "in_progress"].includes(task.status)) {
    bottomAction = "submit";
  } else if (isMyTask && task.status === "submitted") {
    bottomAction = "submitted";
  } else if (isMyTask && task.status === "completed") {
    bottomAction = "completed";
  } else if (hasApplied && !isMyTask) {
    bottomAction = "applied";
  } else if (canApply) {
    bottomAction = "apply";
  }

  // Build timeline steps from task state + payment events
  // Event types vary by payment mode: Fase 1 (settle_worker_direct), Fase 2 (escrow_authorize/release), H2A, legacy
  const escrowEvent = paymentEvents?.find((e) =>
    ["escrow_authorize", "verify", "balance_check"].includes(e.event_type)
  );
  const workerPaymentEvent = paymentEvents?.find((e) =>
    ["settle_worker_direct", "escrow_release", "h2a_settle_worker", "disburse_worker"].includes(e.event_type)
  );
  const paymentTx = workerPaymentEvent?.tx_hash ?? null;

  const statusOrder = ["published", "accepted", "in_progress", "submitted", "verifying", "completed"];
  const currentIdx = statusOrder.indexOf(task.status);

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center justify-between px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">← {t("common.back")}</Text>
        </Pressable>
        <View
          className={`rounded-full px-3 py-1 ${
            task.status === "published"
              ? "bg-green-900/30"
              : task.status === "completed"
                ? "bg-blue-900/30"
                : "bg-yellow-900/30"
          }`}
        >
          <Text
            className={`text-xs font-medium ${
              task.status === "published"
                ? "text-green-400"
                : task.status === "completed"
                  ? "text-blue-400"
                  : "text-yellow-400"
            }`}
          >
            {task.status.toUpperCase()}
          </Text>
        </View>
      </View>

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        {/* Category */}
        <View className="flex-row items-center mb-3">
          <View
            className="rounded-full px-3 py-1 flex-row items-center"
            style={{ backgroundColor: `${category?.color || "#333"}30` }}
          >
            <Text style={{ fontSize: 14 }}>{category?.icon || "📌"}</Text>
            <Text
              style={{
                color: category?.color || "#999",
                fontSize: 12,
                marginLeft: 4,
                fontWeight: "600",
              }}
            >
              {t(`categories.${task.category}`, task.category)}
            </Text>
          </View>
        </View>

        {/* Title */}
        <Text className="text-white text-2xl font-bold mb-2">
          {task.title}
        </Text>

        {/* Agent info */}
        {task.agent_name && (
          <Text className="text-gray-500 text-sm mb-4">
            {t("task.postedBy", { name: task.agent_name })}
            {task.erc8004_agent_id && ` (Agent #${task.erc8004_agent_id})`}
          </Text>
        )}

        {/* Bounty + Network Card */}
        <View className="bg-surface rounded-2xl p-4 mb-4">
          <View className="flex-row items-center justify-between">
            <View>
              <Text className="text-gray-400 text-xs">
                {t("task.bounty")}
              </Text>
              <Text className="text-white text-3xl font-bold">
                ${task.bounty_usd.toFixed(2)}
              </Text>
              <Text className="text-gray-500 text-xs">
                {task.payment_token || "USDC"}
              </Text>
            </View>
            <View className="items-end">
              <Text className="text-gray-400 text-xs">
                {t("task.deadline")}
              </Text>
              <Text className="text-yellow-400 font-bold">
                {formatTimeRemaining(task.deadline, t)}
              </Text>
              <Text className="text-gray-500 text-xs">
                {formatDate(task.deadline)}
              </Text>
            </View>
          </View>
          {network && (
            <View className="flex-row items-center mt-3 pt-3 border-t border-gray-800">
              <View
                className="w-3 h-3 rounded-full mr-2"
                style={{ backgroundColor: network.color }}
              />
              <Text className="text-gray-400 text-sm">
                {t("task.paymentOn", { network: network.name })}
              </Text>
            </View>
          )}
        </View>

        {/* Status Timeline — visible when executor has interacted with this task */}
        {isMyTask && currentIdx >= 1 && (
          <View className="mb-4">
            <Text className="text-gray-400 text-sm font-bold mb-3">
              {t("task.timeline")}
            </Text>
            <View className="bg-surface rounded-2xl p-4">
              {/* Step 1: Assigned / Escrow locked */}
              <TimelineStep
                icon="✓"
                label={t("task.timelineAssigned")}
                sublabel={task.escrow_tx ? t("task.timelineEscrowLocked") : undefined}
                txHash={task.escrow_tx}
                network={task.payment_network}
                isCompleted={currentIdx >= 1}
                isLast={false}
                t={t}
              />

              {/* Step 2: Evidence submitted */}
              <TimelineStep
                icon="✓"
                label={t("task.timelineEvidenceSubmitted")}
                sublabel={
                  currentIdx >= 5
                    ? t("task.timelineReviewComplete")
                    : currentIdx >= 3
                      ? t("task.timelineUnderReview")
                      : undefined
                }
                isCompleted={currentIdx >= 3}
                isLast={currentIdx < 5}
                t={t}
              />

              {/* Step 3: Approved + Paid (only if completed) */}
              {currentIdx >= 5 && (
                <TimelineStep
                  icon="✓"
                  label={t("task.timelineApproved")}
                  sublabel={t("task.timelinePaymentSent", {
                    amount: (task.bounty_usd * 0.87).toFixed(2),
                  })}
                  txHash={paymentTx}
                  network={task.payment_network}
                  isCompleted={true}
                  isLast={true}
                  t={t}
                />
              )}
            </View>
          </View>
        )}

        {/* Status Banners — show exactly one based on current state */}
        {isMyTask && task.status === "completed" && (
          <View className="bg-green-900/20 rounded-2xl p-4 mb-4 flex-row items-center">
            <Text style={{ fontSize: 20, marginRight: 8 }}>{"\u2705"}</Text>
            <View className="flex-1">
              <Text className="text-green-400 font-bold">
                {t("task.completed")}
              </Text>
              <Text className="text-gray-400 text-sm mt-0.5">
                {t("task.paymentReleased")}
              </Text>
            </View>
          </View>
        )}

        {isMyTask && task.status === "submitted" && (
          <View className="bg-yellow-900/20 rounded-2xl p-4 mb-4 flex-row items-center">
            <Text style={{ fontSize: 20, marginRight: 8 }}>{"\uD83D\uDCE4"}</Text>
            <View className="flex-1">
              <Text className="text-yellow-400 font-bold">
                {t("task.evidenceSubmitted")}
              </Text>
              <Text className="text-gray-400 text-sm mt-0.5">
                {t("task.awaitingAgentReview")}
              </Text>
            </View>
          </View>
        )}

        {isMyTask && ["accepted", "in_progress"].includes(task.status) && (
          <View className="bg-green-900/20 rounded-2xl p-4 mb-4 flex-row items-center">
            <Text style={{ fontSize: 20, marginRight: 8 }}>{"\uD83C\uDFAF"}</Text>
            <View className="flex-1">
              <Text className="text-green-400 font-bold">
                {t("task.taskAssigned")}
              </Text>
              <Text className="text-gray-400 text-sm mt-0.5">
                {t("task.completeAndUpload")}
              </Text>
            </View>
          </View>
        )}

        {hasApplied && !isMyTask && task.status === "published" && (
          <View className="bg-blue-900/20 rounded-2xl p-4 mb-4 flex-row items-center">
            <Text style={{ fontSize: 20, marginRight: 8 }}>{"\uD83D\uDCE8"}</Text>
            <View className="flex-1">
              <Text className="text-blue-400 font-bold">
                {t("task.applicationSent")}
              </Text>
              <Text className="text-gray-400 text-sm mt-0.5">
                {t("task.waitingAssignment")}
              </Text>
            </View>
          </View>
        )}

        {/* Instructions */}
        <View className="mb-4">
          <Text className="text-gray-400 text-sm font-bold mb-2">
            {t("task.instructions")}
          </Text>
          <View className="bg-surface rounded-2xl p-4">
            <Text className="text-white text-sm leading-6">
              {task.instructions}
            </Text>
          </View>
        </View>

        {/* Location */}
        {task.location_hint && (
          <View className="mb-4">
            <Text className="text-gray-400 text-sm font-bold mb-2">
              {t("task.location")}
            </Text>
            <View className="bg-surface rounded-2xl p-4 flex-row items-center">
              <Text style={{ fontSize: 20 }}>📍</Text>
              <Text className="text-white text-sm ml-3">
                {task.location_hint}
              </Text>
            </View>
          </View>
        )}

        {/* Evidence Required */}
        {task.evidence_schema?.required?.length > 0 && (
          <View className="mb-4">
            <Text className="text-gray-400 text-sm font-bold mb-2">
              {t("task.evidenceRequired")}
            </Text>
            <View className="bg-surface rounded-2xl p-4">
              {task.evidence_schema?.required?.map((ev: string, i: number) => (
                <View
                  key={ev}
                  className={`flex-row items-center ${i > 0 ? "mt-2" : ""}`}
                >
                  <Text className="text-green-400 mr-2">●</Text>
                  <Text className="text-white text-sm">
                    {ev.replace(/_/g, " ")}
                  </Text>
                </View>
              ))}
              {task.evidence_schema?.optional?.map((ev: string) => (
                <View key={ev} className="flex-row items-center mt-2">
                  <Text className="text-gray-500 mr-2">○</Text>
                  <Text className="text-gray-400 text-sm">
                    {ev.replace(/_/g, " ")} ({t("task.optional")})
                  </Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Skills */}
        {task.skills_required?.length > 0 && (
          <View className="mb-4">
            <Text className="text-gray-400 text-sm font-bold mb-2">
              {t("task.skills")}
            </Text>
            <View className="flex-row flex-wrap gap-2">
              {task.skills_required?.map((skill: string) => (
                <View
                  key={skill}
                  className="bg-surface rounded-full px-3 py-1"
                >
                  <Text className="text-gray-300 text-sm">{skill}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Min Reputation */}
        {task.min_reputation > 0 && (
          <View className="bg-yellow-900/20 rounded-2xl p-4 mb-4">
            <Text className="text-yellow-400 font-bold">
              &#x2B50; {t("task.minReputation")}: {task.min_reputation}
            </Text>
            {executor && executor.reputation_score < task.min_reputation && (
              <Text className="text-red-400 text-sm mt-1">
                {t("task.yourReputation", { score: executor.reputation_score })}
              </Text>
            )}
          </View>
        )}

        {/* Bottom padding */}
        <View className="h-24" />
      </ScrollView>

      {/* Bottom Action Bar */}
      <View className="absolute bottom-0 left-0 right-0 bg-black border-t border-gray-800 px-4 py-4 pb-8">
        {bottomAction === "apply" && (
          <Pressable
            className="bg-white rounded-2xl py-4 items-center active:opacity-80"
            onPress={() => setShowApplyModal(true)}
          >
            <Text className="text-black font-bold text-lg">
              {t("task.apply")} · ${task.bounty_usd.toFixed(2)}
            </Text>
          </Pressable>
        )}

        {bottomAction === "applied" && (
          <View className="bg-blue-900/30 rounded-2xl py-4 items-center">
            <Text className="text-blue-400 font-bold text-lg">
              &#x1F4E8; {t("task.applicationSent")}
            </Text>
            <Text className="text-gray-500 text-xs mt-1">
              {t("task.agentWillReview")}
            </Text>
          </View>
        )}

        {bottomAction === "submit" && (
          <Pressable
            className="bg-white rounded-2xl py-4 items-center active:opacity-80"
            onPress={() => router.push(`/submit/${task.id}`)}
          >
            <Text className="text-black font-bold text-lg">
              {t("task.submit")}
            </Text>
          </Pressable>
        )}

        {bottomAction === "submitted" && (
          <View className="bg-yellow-900/30 rounded-2xl py-4 items-center">
            <Text className="text-yellow-400 font-bold text-lg">
              {"\uD83D\uDCE4"} {t("task.evidenceSubmitted")}
            </Text>
            <Text className="text-gray-500 text-xs mt-1">
              {t("task.awaitingAgentReview")}
            </Text>
          </View>
        )}

        {bottomAction === "completed" && (
          <View className="bg-green-900/30 rounded-2xl py-4 items-center">
            <Text className="text-green-400 font-bold text-lg">
              {"\u2705"} {t("task.completed")}
            </Text>
            <Text className="text-gray-500 text-xs mt-1">
              +${(task.bounty_usd * 0.87).toFixed(2)} USDC
            </Text>
            {paymentTx && (
              <Pressable
                className="mt-2"
                onPress={() => Linking.openURL(getExplorerTxUrl(task.payment_network, paymentTx))}
              >
                <Text className="text-blue-400 text-xs">
                  {t("task.viewPayment")} ↗
                </Text>
              </Pressable>
            )}
          </View>
        )}

        {bottomAction === "login" && (
          <Pressable
            className="bg-white rounded-2xl py-4 items-center active:opacity-80"
            onPress={() => router.push("/(tabs)/profile")}
          >
            <Text className="text-black font-bold text-lg">
              {t("auth.connectWallet")}
            </Text>
          </Pressable>
        )}
      </View>

      {task && (
        <ApplyModal
          visible={showApplyModal}
          onClose={() => setShowApplyModal(false)}
          onSuccess={() => refetch()}
          taskId={task.id}
          taskTitle={task.title}
          bounty={task.bounty_usd}
        />
      )}
    </SafeAreaView>
  );
}
