import {
  View,
  Text,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Linking,
  Alert,
  Image,
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import { useLocalSearchParams, router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useTask, useMyApplication, useMySubmission } from "../../hooks/api/useTasks";
import { useTaskPaymentEvents } from "../../hooks/api/useEarnings";
import { useAuth } from "../../providers/AuthProvider";
import { TASK_CATEGORIES } from "../../constants/categories";
import { NETWORKS, getExplorerTxUrl } from "../../constants/networks";
import { ApplyModal } from "../../components/ApplyModal";
import { RateAgentModal } from "../../components/RateAgentModal";
import { ReputationBadge } from "../../components/ReputationBadge";
import { useAgentReputation } from "../../hooks/api/useReputation";
import { useTaskRatings } from "../../hooks/api/useRatings";
import AsyncStorage from "@react-native-async-storage/async-storage";

/** Open URL safely — tries in-app browser first, falls back to Linking */
async function openUrl(url: string) {
  try {
    await WebBrowser.openBrowserAsync(url);
  } catch {
    try {
      await Linking.openURL(url);
    } catch {
      Alert.alert("Error", `Could not open: ${url}`);
    }
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTimeRemaining(deadline: string, t: (key: string, opts?: Record<string, unknown>) => string): string {
  if (!deadline) return "—";
  const now = new Date();
  const dl = new Date(deadline);
  if (isNaN(dl.getTime())) return "—";
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
            onPress={() => openUrl(getExplorerTxUrl(network, txHash))}
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
  const { data: mySubmission } = useMySubmission(id, executor?.id ?? undefined);
  const { data: agentRep } = useAgentReputation(task?.erc8004_agent_id ?? null);
  const { data: taskRatings } = useTaskRatings(task?.status === "completed" ? id : null);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showRateModal, setShowRateModal] = useState(false);
  const [hasRated, setHasRated] = useState(false);

  const hasApplied = myApplication?.applied === true;
  const isMyTask = !!(executor && task && task.executor_id === executor.id);

  // Sync hasRated with DB data (workerRating exists = already rated)
  useEffect(() => {
    if (taskRatings?.workerRating) {
      setHasRated(true);
    }
  }, [taskRatings?.workerRating]);

  // Auto-show rating modal when task is completed (one-time)
  useEffect(() => {
    if (!task || !isMyTask || task.status !== "completed") return;
    // If DB already has a worker rating, don't show modal
    if (taskRatings?.workerRating) return;
    const key = `rated_agent_${task.id}`;
    AsyncStorage.getItem(key).then((val) => {
      if (!val) {
        // Small delay so user sees the completion state first
        setTimeout(() => setShowRateModal(true), 1500);
      } else {
        setHasRated(true);
      }
    });
  }, [task?.status, isMyTask, task?.id, taskRatings?.workerRating]);

  const handleRateComplete = () => {
    setShowRateModal(false);
    setHasRated(true);
    if (task) {
      AsyncStorage.setItem(`rated_agent_${task.id}`, "true");
    }
  };

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
        <Text className="text-gray-500 text-sm mb-4 text-center px-8">
          {isError ? "Could not load task details. The task may have been removed or the server returned an error." : "No task data received."}
        </Text>
        <Pressable
          className="bg-surface rounded-xl px-6 py-3 mb-3"
          onPress={() => refetch()}
        >
          <Text className="text-white font-medium">{t("common.retry") || "Retry"}</Text>
        </Pressable>
        <Pressable onPress={() => router.back()}>
          <Text className="text-white">{t("common.back")}</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  // Safely coerce fields that might arrive as null/undefined from API despite TS types
  const safeBounty = typeof task.bounty_usd === "number" ? task.bounty_usd : parseFloat(String(task.bounty_usd)) || 0;
  const safeDeadline = task.deadline || new Date(Date.now() + 86400000).toISOString(); // fallback: 24h from now
  const safeStatus = task.status || "published";
  const safeMinReputation = typeof task.min_reputation === "number" ? task.min_reputation : 0;

  const category = TASK_CATEGORIES.find((c) => c.key === task.category) ?? null;
  const network = NETWORKS.find((n) => n.key === task.payment_network) ?? null;

  const canApply =
    safeStatus === "published" &&
    !task.executor_id &&
    !hasApplied &&
    isAuthenticated &&
    (safeMinReputation === 0 ||
      (executor?.reputation_score || 0) >= safeMinReputation);

  // Determine bottom action bar content
  let bottomAction: "apply" | "applied" | "submitted" | "submit" | "login" | "none" = "none";
  if (!isAuthenticated) {
    bottomAction = "login";
  } else if (isMyTask && ["accepted", "in_progress"].includes(safeStatus)) {
    bottomAction = "submit";
  } else if (isMyTask && safeStatus === "submitted") {
    bottomAction = "submitted";
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
  // Fallback chain: payment_events (RLS-gated) → task.payment_tx (from API)
  const paymentTx = workerPaymentEvent?.tx_hash ?? task?.payment_tx ?? null;

  const statusOrder = ["published", "accepted", "in_progress", "submitted", "verifying", "completed"];
  const currentIdx = statusOrder.indexOf(safeStatus);

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center justify-between px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">← {t("common.back")}</Text>
        </Pressable>
        <View
          className={`rounded-full px-3 py-1 ${
            safeStatus === "published"
              ? "bg-green-900/30"
              : safeStatus === "completed"
                ? "bg-blue-900/30"
                : "bg-yellow-900/30"
          }`}
        >
          <Text
            className={`text-xs font-medium ${
              safeStatus === "published"
                ? "text-green-400"
                : safeStatus === "completed"
                  ? "text-blue-400"
                  : "text-yellow-400"
            }`}
          >
            {safeStatus.toUpperCase()}
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

        {/* Agent info with reputation */}
        {task.agent_name && (
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-gray-500 text-sm flex-1">
              {t("task.postedBy", { name: task.agent_name })}
              {task.erc8004_agent_id && ` (Agent #${task.erc8004_agent_id})`}
            </Text>
            {agentRep && agentRep.score > 0 && (
              <ReputationBadge score={agentRep.score} size="md" />
            )}
          </View>
        )}

        {/* Bounty + Network Card */}
        <View className="bg-surface rounded-2xl p-4 mb-4">
          <View className="flex-row items-center justify-between">
            <View>
              <Text className="text-gray-400 text-xs">
                {t("task.bounty")}
              </Text>
              <Text className="text-white text-3xl font-bold">
                ${safeBounty.toFixed(2)}
              </Text>
              <Text className="text-gray-500 text-xs">
                {task.payment_token || "USDC"}
              </Text>
            </View>
            <View className="items-end">
              {["completed", "cancelled", "expired", "disputed"].includes(safeStatus) ? (
                <>
                  <Text className="text-gray-400 text-xs">
                    {t("task.deadline")}
                  </Text>
                  <Text className="text-gray-500 text-sm">
                    {formatDate(safeDeadline)}
                  </Text>
                </>
              ) : (
                <>
                  <Text className="text-gray-400 text-xs">
                    {t("task.deadline")}
                  </Text>
                  <Text className="text-yellow-400 font-bold">
                    {formatTimeRemaining(safeDeadline, t)}
                  </Text>
                  <Text className="text-gray-500 text-xs">
                    {formatDate(safeDeadline)}
                  </Text>
                </>
              )}
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
                    amount: (safeBounty * 0.87).toFixed(2),
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

        {/* My Evidence — only visible to the executor who submitted */}
        {isMyTask && mySubmission && currentIdx >= 3 && (() => {
          const evidence = mySubmission.evidence || {};
          const photoEntry = evidence.photo_geo || evidence.photo || evidence.screenshot || evidence.receipt;
          const photoUrl = photoEntry?.url || photoEntry?.fileUrl;
          const gps = photoEntry?.gps;
          const textEntries = Object.entries(evidence).filter(
            ([k]) => !["photo", "photo_geo", "screenshot", "receipt"].includes(k)
          );
          if (!photoUrl && textEntries.length === 0) return null;
          return (
            <View className="mb-4">
              <Text className="text-gray-400 text-sm font-bold mb-3">
                {t("task.myEvidence")}
              </Text>
              <View className="bg-surface rounded-2xl overflow-hidden">
                {photoUrl && (
                  <Pressable onPress={() => openUrl(photoUrl)}>
                    <Image
                      source={{ uri: photoUrl }}
                      style={{ width: "100%", height: 200 }}
                      resizeMode="cover"
                    />
                    <View className="absolute bottom-2 right-2 bg-black/60 rounded-full px-2 py-1">
                      <Text className="text-white text-xs">Tap to view full</Text>
                    </View>
                  </Pressable>
                )}
                {gps && (
                  <View className="px-4 py-2 border-t border-gray-800 flex-row items-center">
                    <Text className="text-gray-500 text-xs">
                      GPS: {gps.lat?.toFixed(5)}, {gps.lng?.toFixed(5)}
                      {gps.accuracy ? ` (\u00B1${gps.accuracy.toFixed(0)}m)` : ""}
                    </Text>
                  </View>
                )}
                {textEntries.length > 0 && (
                  <View className="px-4 py-3">
                    {textEntries.map(([key, value]) => (
                      <View key={key} className="mb-2">
                        <Text className="text-gray-400 text-xs uppercase">
                          {key.replace(/_/g, " ")}
                        </Text>
                        <Text className="text-white text-sm mt-0.5" numberOfLines={4}>
                          {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            </View>
          );
        })()}

        {/* Status Banners — show exactly one based on current state */}
        {/* Completed banner removed — timeline already shows "Approved & Paid" */}

        {isMyTask && safeStatus === "submitted" && (
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

        {isMyTask && ["accepted", "in_progress"].includes(safeStatus) && (
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

        {hasApplied && !isMyTask && safeStatus === "published" && (
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

            {/* Location + Evidence Required — compact inline */}
            {(task.location_hint || (Array.isArray(task.evidence_schema?.required) && task.evidence_schema.required.length > 0)) && (
              <View className="mt-3 pt-3 border-t border-gray-800">
                {task.location_hint && (
                  <View className="flex-row items-center mb-1">
                    <Text style={{ fontSize: 14 }}>📍</Text>
                    <Text className="text-gray-400 text-xs ml-1.5 flex-1" numberOfLines={1}>
                      {task.location_hint}
                    </Text>
                  </View>
                )}
                {Array.isArray(task.evidence_schema?.required) && task.evidence_schema.required.length > 0 && (
                  <View className="flex-row items-center flex-wrap">
                    <Text style={{ fontSize: 14 }}>📎</Text>
                    <Text className="text-gray-400 text-xs ml-1.5">
                      {task.evidence_schema.required.map((ev: string) => ev.replace(/_/g, " ")).join(", ")}
                      {Array.isArray(task.evidence_schema?.optional) && task.evidence_schema.optional.length > 0
                        ? ` + ${task.evidence_schema.optional.length} ${t("task.optional")}`
                        : ""}
                    </Text>
                  </View>
                )}
              </View>
            )}
          </View>
        </View>

        {/* Skills */}
        {Array.isArray(task.skills_required) && task.skills_required.length > 0 && (
          <View className="mb-4">
            <Text className="text-gray-400 text-sm font-bold mb-2">
              {t("task.skills")}
            </Text>
            <View className="flex-row flex-wrap gap-2">
              {task.skills_required.map((skill: string) => (
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
        {safeMinReputation > 0 && (
          <View className="bg-yellow-900/20 rounded-2xl p-4 mb-4">
            <Text className="text-yellow-400 font-bold">
              &#x2B50; {t("task.minReputation")}: {safeMinReputation}
            </Text>
            {executor && (executor.reputation_score || 0) < safeMinReputation && (
              <Text className="text-red-400 text-sm mt-1">
                {t("task.yourReputation", { score: executor.reputation_score || 0 })}
              </Text>
            )}
          </View>
        )}

        {/* Ratings & Feedback — visible for completed tasks */}
        {isMyTask && safeStatus === "completed" && (
          <View className="mb-4">
            <Text className="text-gray-400 text-sm font-bold mb-3">
              {t("task.ratingsTitle")}
            </Text>
            <View className="bg-surface rounded-2xl p-4">
              {/* Agent's rating of worker */}
              {taskRatings?.agentRating ? (
                <View className="mb-4">
                  <Text className="text-gray-500 text-xs uppercase mb-1">
                    {t("task.agentRatedYou")}
                  </Text>
                  <View className="flex-row items-center mb-1">
                    <Text className="text-white text-2xl font-bold">
                      {taskRatings.agentRating.rating}
                    </Text>
                    <Text className="text-gray-500 text-sm ml-1">/100</Text>
                  </View>
                  {taskRatings.agentRating.comment && (
                    <Text className="text-gray-300 text-sm italic">
                      "{taskRatings.agentRating.comment}"
                    </Text>
                  )}
                </View>
              ) : (
                <View className="mb-4">
                  <Text className="text-gray-500 text-xs uppercase mb-1">
                    {t("task.agentRatedYou")}
                  </Text>
                  <Text className="text-gray-600 text-sm">
                    {t("task.noRatingYet")}
                  </Text>
                </View>
              )}

              {/* Payment TX link */}
              {paymentTx && task.payment_network && (
                <Pressable
                  className="mb-3"
                  onPress={() => openUrl(getExplorerTxUrl(task.payment_network!, paymentTx))}
                >
                  <Text className="text-blue-400 text-xs">
                    {t("task.viewTx")} · {paymentTx.slice(0, 12)}... ↗
                  </Text>
                </Pressable>
              )}

              {/* Divider */}
              <View className="border-t border-gray-800 mb-4" />

              {/* Worker's rating of agent */}
              {taskRatings?.workerRating ? (
                <View>
                  <Text className="text-gray-500 text-xs uppercase mb-1">
                    {t("task.yourRatingOfAgent")}
                  </Text>
                  <View className="flex-row items-center mb-1">
                    <Text className="text-white text-2xl font-bold">
                      {taskRatings.workerRating.rating}
                    </Text>
                    <Text className="text-gray-500 text-sm ml-1">/100</Text>
                  </View>
                  {taskRatings.workerRating.comment && (
                    <Text className="text-gray-300 text-sm italic">
                      "{taskRatings.workerRating.comment}"
                    </Text>
                  )}
                </View>
              ) : (
                <View>
                  <Text className="text-gray-500 text-xs uppercase mb-1">
                    {t("task.yourRatingOfAgent")}
                  </Text>
                  {!hasRated ? (
                    <Pressable
                      className="bg-white/10 rounded-xl py-3 items-center mt-1 active:opacity-80"
                      onPress={() => setShowRateModal(true)}
                    >
                      <Text className="text-white font-medium">
                        {t("task.rateThisAgent")}
                      </Text>
                    </Pressable>
                  ) : (
                    <Text className="text-gray-600 text-sm">
                      {t("task.ratingSubmitted")}
                    </Text>
                  )}
                </View>
              )}
            </View>
          </View>
        )}

        {/* Bottom padding — extra when action bar is visible */}
        <View className={bottomAction !== "none" ? "h-24" : "h-8"} />
      </ScrollView>

      {/* Bottom Action Bar — hidden when no action needed (e.g. completed tasks) */}
      {bottomAction !== "none" && (
      <View className="absolute bottom-0 left-0 right-0 bg-black border-t border-gray-800 px-4 py-4 pb-8">
        {bottomAction === "apply" && (
          <Pressable
            className="bg-white rounded-2xl py-4 items-center active:opacity-80"
            onPress={() => setShowApplyModal(true)}
          >
            <Text className="text-black font-bold text-lg">
              {t("task.apply")} · ${safeBounty.toFixed(2)}
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
      )}

      {task && (
        <ApplyModal
          visible={showApplyModal}
          onClose={() => setShowApplyModal(false)}
          onSuccess={() => refetch()}
          taskId={task.id}
          taskTitle={task.title}
          bounty={safeBounty}
        />
      )}

      {task && task.erc8004_agent_id && (
        <RateAgentModal
          visible={showRateModal}
          onClose={handleRateComplete}
          taskId={task.id}
          agentId={task.erc8004_agent_id}
          agentName={task.agent_name || undefined}
        />
      )}
    </SafeAreaView>
  );
}
