import { View, Text, ScrollView, Pressable, TextInput, ActivityIndicator, Alert, Platform, KeyboardAvoidingView } from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import * as Location from "expo-location";
import { useTask } from "../../hooks/api/useTasks";
import { useAuth } from "../../providers/AuthProvider";
import { CameraCapture, type ExifData } from "../../components/CameraCapture";
import { GPSCapture } from "../../components/GPSCapture";
import { ImagePickerButton } from "../../components/ImagePicker";
import { uploadEvidence } from "../../lib/upload";
import { apiClient } from "../../lib/api";
import { extractExifFromFile, buildExifPayload, isLikelyCameraPhoto } from "../../lib/exif";

interface EvidenceData {
  [key: string]: unknown;
}

interface GPSData {
  lat: number;
  lng: number;
  accuracy: number;
  timestamp: string;
}

export default function SubmitEvidenceScreen() {
  const { taskId } = useLocalSearchParams<{ taskId: string }>();
  const { t } = useTranslation();
  const { executor } = useAuth();
  const { data: task, refetch: refetchTask } = useTask(taskId);

  const [showCamera, setShowCamera] = useState(false);
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [photoExif, setPhotoExif] = useState<ExifData | null>(null);
  const [exifWarning, setExifWarning] = useState<string | null>(null);
  const [gpsData, setGpsData] = useState<GPSData | null>(null);
  const [autoGps, setAutoGps] = useState<GPSData | null>(null);
  const [textEvidence, setTextEvidence] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [verificationResult, setVerificationResult] = useState<Record<string, unknown> | null>(null);

  // Poll task status after submission (every 5s) until terminal state
  useEffect(() => {
    if (!submitted || !taskId) return;
    const terminalStatuses = ["completed", "disputed", "cancelled", "expired"];
    if (task?.status && terminalStatuses.includes(task.status)) return;
    const interval = setInterval(() => {
      refetchTask();
    }, 5000);
    return () => clearInterval(interval);
  }, [submitted, taskId, refetchTask, task?.status]);

  // Auto-capture GPS on screen mount (always, for metadata)
  useEffect(() => {
    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== "granted") return;
        const loc = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
        });
        const captured: GPSData = {
          lat: loc.coords.latitude,
          lng: loc.coords.longitude,
          accuracy: loc.coords.accuracy ?? 0,
          timestamp: new Date(loc.timestamp).toISOString(),
        };
        setAutoGps(captured);
        // Also set gpsData if user hasn't manually captured yet
        if (!gpsData) setGpsData(captured);
      } catch {
        // GPS not available — non-fatal
      }
    })();
  }, []);

  if (showCamera) {
    return (
      <CameraCapture
        onCapture={async (uri, exif) => {
          setPhotoUri(uri);
          setShowCamera(false);
          // Use EXIF from camera, or extract via exifr as fallback
          let finalExif = exif || null;
          if (!finalExif) {
            finalExif = await extractExifFromFile(uri);
          }
          setPhotoExif(finalExif);
          if (finalExif) {
            const check = isLikelyCameraPhoto(finalExif);
            if (!check.isCamera) {
              setExifWarning(check.reason);
            } else {
              setExifWarning(null);
            }
          } else {
            setExifWarning("No camera metadata detected. Fresh camera photos score higher.");
          }
        }}
        onCancel={() => setShowCamera(false)}
      />
    );
  }

  const requiredEvidence = task?.evidence_schema?.required || [];
  const optionalEvidence = task?.evidence_schema?.optional || [];
  const allEvidence = [...requiredEvidence, ...optionalEvidence];

  const needsPhoto = allEvidence.some((e) => ["photo", "photo_geo", "receipt", "screenshot"].includes(e));
  const needsGPS = allEvidence.some((e) => ["photo_geo"].includes(e));
  const needsText = allEvidence.some((e) =>
    ["text_response", "json_response", "measurement", "url_reference", "text_report"].includes(e)
  );

  async function handleSubmit() {
    if (!executor?.id || !taskId) {
      Alert.alert(t("common.error"), t("submit.authRequired"));
      return;
    }

    setSubmitting(true);
    try {
      const evidence: EvidenceData = {};

      // Upload photo if captured
      if (photoUri) {
        const evidenceType = requiredEvidence.includes("photo_geo") ? "photo_geo" : "photo";
        const uploaded = await uploadEvidence(photoUri, taskId, evidenceType, executor.id);
        const photoPayload: Record<string, unknown> = {
          url: uploaded.url,
          fileUrl: uploaded.url,
          ...(gpsData && {
            gps: {
              lat: gpsData.lat,
              lng: gpsData.lng,
              accuracy: gpsData.accuracy,
            },
          }),
          timestamp: new Date().toISOString(),
        };
        // Include EXIF metadata for backend verification
        if (photoExif) {
          photoPayload.exif = buildExifPayload(photoExif);
        }
        evidence[evidenceType] = photoPayload;
        // If uploaded as photo_geo, also satisfy "photo" requirement with same data
        if (evidenceType === "photo_geo" && requiredEvidence.includes("photo")) {
          evidence.photo = photoPayload;
        }
      }

      // Add GPS data if captured separately
      if (gpsData && !photoUri) {
        evidence.photo_geo = {
          lat: gpsData.lat,
          lng: gpsData.lng,
          accuracy: gpsData.accuracy,
          timestamp: gpsData.timestamp,
        };
      }

      // Add text evidence
      for (const [key, value] of Object.entries(textEvidence)) {
        if (value.trim()) {
          evidence[key] = key === "json_response" ? tryParseJSON(value) : value;
        }
      }

      console.log("[Submit] Evidence keys:", Object.keys(evidence));
      console.log("[Submit] Required evidence:", requiredEvidence);
      console.log("[Submit] Evidence URLs:", Object.entries(evidence).map(([k, v]) => [k, (v as any)?.url || (v as any)?.fileUrl || "no-url"]));

      // Warn if required evidence is missing
      const missingRequired = requiredEvidence.filter((r: string) => !(r in evidence));
      if (missingRequired.length > 0) {
        console.warn("[Submit] MISSING required evidence:", missingRequired);
      }

      // Always include submission GPS + device metadata for verification
      const submissionGps = gpsData || autoGps;
      const deviceMetadata: Record<string, unknown> = {
        platform: Platform.OS,
        os_version: Platform.Version,
        submitted_at: new Date().toISOString(),
        has_exif: !!photoExif,
      };
      if (submissionGps) {
        deviceMetadata.gps = {
          lat: submissionGps.lat,
          lng: submissionGps.lng,
          accuracy: submissionGps.accuracy,
          timestamp: submissionGps.timestamp,
        };
      }

      // Submit to API
      const result = await apiClient(`/api/v1/tasks/${taskId}/submit`, {
        method: "POST",
        body: {
          executor_id: executor.id,
          evidence,
          notes: notes.trim() || undefined,
          device_metadata: deviceMetadata,
        },
      });

      setVerificationResult(result as Record<string, unknown>);
      setSubmitted(true);
    } catch (e) {
      Alert.alert(t("common.error"), (e as Error).message || t("submit.submitError"));
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    const vData = verificationResult?.data as Record<string, unknown> | undefined;
    const verification = (vData?.verification ?? verificationResult?.verification) as Record<string, unknown> | undefined;
    const score = typeof verification?.score === "number" ? verification.score : null;
    const passed = verification?.passed as boolean | undefined;
    const checks = (verification?.checks ?? []) as Array<{
      name: string;
      passed: boolean;
      score: number;
      reason: string;
    }>;
    const warnings = (verification?.warnings ?? []) as string[];
    const summary = verification?.summary as string | undefined;
    const phaseBStatus = verification?.phase_b_status as string | undefined;
    const submissionStatus = (vData?.status ?? verificationResult?.status ?? "submitted") as string;

    const scorePercent = score !== null ? Math.round(score * 100) : null;
    const scoreColor = scorePercent !== null
      ? scorePercent >= 80 ? "text-green-400"
        : scorePercent >= 50 ? "text-yellow-400"
        : "text-red-400"
      : "text-gray-400";
    const scoreBgColor = scorePercent !== null
      ? scorePercent >= 80 ? "bg-green-900/20"
        : scorePercent >= 50 ? "bg-yellow-900/20"
        : "bg-red-900/20"
      : "bg-surface";

    const CHECK_ICONS: Record<string, string> = {
      schema: "\uD83D\uDCCB",
      gps: "\uD83D\uDCCD",
      timestamp: "\u23F0",
      evidence_hash: "\uD83D\uDD12",
      metadata: "\uD83D\uDCF1",
    };

    const CHECK_LABELS: Record<string, string> = {
      schema: t("submit.checkSchema"),
      gps: t("submit.checkGps"),
      timestamp: t("submit.checkTimestamp"),
      evidence_hash: t("submit.checkHash"),
      metadata: t("submit.checkMetadata"),
    };

    return (
      <SafeAreaView className="flex-1 bg-black">
        <ScrollView className="flex-1 px-4 pt-6" showsVerticalScrollIndicator={false}>
          {/* Hero */}
          <View className="items-center mb-6">
            <Text style={{ fontSize: 56 }}>{passed ? "\u2705" : "\u26A0\uFE0F"}</Text>
            <Text className="text-white text-2xl font-bold mt-3">
              {t("submit.successTitle")}
            </Text>
            <Text className="text-gray-400 text-center mt-1.5 px-4">
              {summary || t("submit.successSubtitle")}
            </Text>
          </View>

          {/* Score Card */}
          {scorePercent !== null && (
            <View className={`${scoreBgColor} rounded-2xl p-5 mb-4 items-center`}>
              <Text className="text-gray-400 text-xs font-bold uppercase mb-1">
                {t("submit.verificationScore")}
              </Text>
              <Text className={`${scoreColor} text-5xl font-bold`}>
                {scorePercent}%
              </Text>
              <Text className="text-gray-500 text-xs mt-1">
                {t("submit.phaseAAutomatic")}
              </Text>
            </View>
          )}

          {/* Checks */}
          {checks.length > 0 && (
            <View className="bg-surface rounded-2xl p-4 mb-4">
              <Text className="text-white font-bold mb-3">
                {t("submit.verificationChecks")}
              </Text>
              {checks.map((check, i) => {
                const checkScore = Math.round(check.score * 100);
                return (
                  <View
                    key={check.name}
                    className={`flex-row items-center py-3 ${i < checks.length - 1 ? "border-b border-gray-800" : ""}`}
                  >
                    <Text style={{ fontSize: 20, width: 32 }}>
                      {CHECK_ICONS[check.name] || "\u2713"}
                    </Text>
                    <View className="flex-1 ml-2">
                      <Text className="text-white font-medium">
                        {CHECK_LABELS[check.name] || check.name}
                      </Text>
                      {check.reason ? (
                        <Text className="text-gray-500 text-xs mt-0.5" numberOfLines={2}>
                          {check.reason}
                        </Text>
                      ) : null}
                    </View>
                    <View className="items-end ml-3">
                      <Text className={`font-bold ${check.passed ? "text-green-400" : "text-red-400"}`}>
                        {check.passed ? "\u2713" : "\u2717"}
                      </Text>
                      <Text className="text-gray-500 text-xs">
                        {checkScore}%
                      </Text>
                    </View>
                  </View>
                );
              })}
            </View>
          )}

          {/* Warnings */}
          {warnings.length > 0 && (
            <View className="bg-yellow-900/20 rounded-2xl p-4 mb-4">
              <Text className="text-yellow-400 font-bold mb-2">
                {t("submit.warnings")}
              </Text>
              {warnings.map((w, i) => (
                <Text key={i} className="text-yellow-400/80 text-sm mb-1">
                  {"\u26A0"} {w}
                </Text>
              ))}
            </View>
          )}

          {/* Task Status — dynamic based on polling */}
          {task?.status === "completed" ? (
            <View className="bg-green-900/20 rounded-2xl p-5 mb-4 items-center">
              <Text style={{ fontSize: 48 }}>{"\u2705"}</Text>
              <Text className="text-green-400 text-xl font-bold mt-2">
                {t("submit.approvedPaid")}
              </Text>
              <Text className="text-green-400/80 text-sm mt-1">
                +${task.bounty_usd.toFixed(2)} USDC
              </Text>
              <Text className="text-gray-500 text-xs mt-2">
                {t("submit.paymentSent")}
              </Text>
            </View>
          ) : task?.status === "disputed" ? (
            <View className="bg-red-900/20 rounded-2xl p-5 mb-4 items-center">
              <Text style={{ fontSize: 48 }}>{"\u26A0\uFE0F"}</Text>
              <Text className="text-red-400 text-xl font-bold mt-2">
                {t("submit.disputed")}
              </Text>
              <Text className="text-gray-400 text-sm mt-1 text-center px-4">
                {t("submit.disputedSubtitle")}
              </Text>
            </View>
          ) : task?.status === "cancelled" ? (
            <View className="bg-red-900/20 rounded-2xl p-5 mb-4 items-center">
              <Text style={{ fontSize: 48 }}>{"\u274C"}</Text>
              <Text className="text-red-400 text-xl font-bold mt-2">
                {t("submit.cancelled")}
              </Text>
              <Text className="text-gray-400 text-sm mt-1 text-center px-4">
                {t("submit.cancelledSubtitle")}
              </Text>
            </View>
          ) : (
            <>
              {/* Phase B Status — only while still pending */}
              {phaseBStatus && (
                <View className="bg-surface rounded-2xl p-4 mb-4 flex-row items-center">
                  <Text style={{ fontSize: 20, marginRight: 10 }}>{"\uD83E\uDD16"}</Text>
                  <View className="flex-1">
                    <Text className="text-white font-medium">
                      {t("submit.aiVerification")}
                    </Text>
                    <Text className="text-gray-500 text-xs mt-0.5">
                      {phaseBStatus === "pending" ? t("submit.aiPending") : phaseBStatus}
                    </Text>
                  </View>
                  {phaseBStatus === "pending" && (
                    <ActivityIndicator size="small" color="#666" />
                  )}
                </View>
              )}

              {/* Awaiting review status */}
              <View className="bg-surface rounded-2xl p-4 mb-6 flex-row items-center">
                <Text style={{ fontSize: 20, marginRight: 10 }}>{"\uD83D\uDCE8"}</Text>
                <View className="flex-1">
                  <Text className="text-white font-medium">
                    {t("submit.statusLabel")}
                  </Text>
                  <Text className="text-gray-400 text-sm mt-0.5">
                    {t("submit.awaitingReview")}
                  </Text>
                </View>
                <ActivityIndicator size="small" color="#666" />
              </View>
            </>
          )}

          <View className="h-4" />
        </ScrollView>

        {/* Fixed bottom button */}
        <View className="px-4 pt-3 pb-8 border-t border-gray-800 bg-black">
          <Pressable
            className="bg-white rounded-2xl py-4 items-center"
            onPress={() => router.replace("/(tabs)/my-tasks")}
          >
            <Text className="text-black font-bold text-lg">
              {t("common.viewMyTasks")}
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
        </Pressable>
        <Text className="text-white text-xl font-bold flex-1" numberOfLines={1}>
          {t("submit.title")}
        </Text>
      </View>

      <KeyboardAvoidingView
        className="flex-1"
        behavior="padding"
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 24}
      >
      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
        {/* Task info */}
        {task && (
          <View className="bg-surface rounded-2xl p-4 mb-4">
            <Text className="text-white font-bold" numberOfLines={2}>
              {task.title}
            </Text>
            <Text className="text-green-400 font-bold mt-1">
              ${task.bounty_usd.toFixed(2)} USDC
            </Text>
          </View>
        )}

        {/* Evidence checklist */}
        <Text className="text-gray-400 text-sm font-bold mb-3">
          {t("submit.required")}
        </Text>

        {/* Photo capture */}
        {needsPhoto && (
          <View className="mb-4">
            {photoUri ? (
              <View className="bg-surface rounded-2xl overflow-hidden">
                <Pressable onPress={() => setShowCamera(true)}>
                  <View className="h-48 bg-gray-800 items-center justify-center">
                    <Text className="text-green-400 text-lg">{"\uD83D\uDCF7"} {t("submit.photoCaptured")}</Text>
                    <Text className="text-gray-500 text-xs mt-1">{t("submit.tapToRetake")}</Text>
                    {photoExif?.Make && (
                      <Text className="text-gray-500 text-xs mt-1">
                        {"\uD83D\uDCF1"} {photoExif.Make} {photoExif.Model || ""}
                      </Text>
                    )}
                    {gpsData && (
                      <Text className="text-gray-600 text-xs mt-1">
                        {"\uD83D\uDCCD"} {t("submit.gpsCaptured")}
                      </Text>
                    )}
                  </View>
                </Pressable>
                {exifWarning && (
                  <View className="bg-yellow-900/30 px-4 py-2">
                    <Text className="text-yellow-400 text-xs">
                      {"\u26A0"} {exifWarning}
                    </Text>
                  </View>
                )}
              </View>
            ) : (
              <View className="flex-row gap-3">
                <Pressable
                  className="flex-1 bg-surface rounded-2xl py-6 items-center"
                  onPress={() => setShowCamera(true)}
                >
                  <Text style={{ fontSize: 32 }}>{"\uD83D\uDCF7"}</Text>
                  <Text className="text-white font-medium mt-2">{t("submit.camera")}</Text>
                </Pressable>
                <ImagePickerButton
                  onPick={async (uri, exif) => {
                    setPhotoUri(uri);
                    let finalExif = exif || null;
                    if (!finalExif) {
                      finalExif = await extractExifFromFile(uri);
                    }
                    setPhotoExif(finalExif);
                    if (finalExif) {
                      const check = isLikelyCameraPhoto(finalExif);
                      if (!check.isCamera) {
                        setExifWarning(check.reason);
                      } else {
                        setExifWarning(null);
                      }
                    } else {
                      setExifWarning("No camera metadata. Gallery photos may score lower.");
                    }
                  }}
                />
              </View>
            )}
          </View>
        )}

        {/* GPS capture — manual if required, auto indicator always */}
        {needsGPS && (
          <View className="mb-4">
            <GPSCapture onCapture={setGpsData} />
            {gpsData && (
              <View className="mt-2 flex-row items-center bg-surface rounded-xl px-4 py-3">
                <Text style={{ fontSize: 16, marginRight: 8 }}>{"\uD83D\uDCCD"}</Text>
                <View className="flex-1">
                  <Text className="text-green-400 text-sm">{"\u2713"} {t("submit.gpsCaptured")} ({"\u00B1"}{gpsData.accuracy.toFixed(0)}m)</Text>
                </View>
              </View>
            )}
          </View>
        )}
        {!needsGPS && autoGps && (
          <View className="mb-4 flex-row items-center bg-surface rounded-xl px-4 py-3">
            <Text style={{ fontSize: 16, marginRight: 8 }}>{"\uD83D\uDCCD"}</Text>
            <View className="flex-1">
              <Text className="text-gray-400 text-sm">{t("submit.gpsAutoCapture")} ({"\u00B1"}{autoGps.accuracy.toFixed(0)}m)</Text>
            </View>
            <Text className="text-green-400">{"\u2713"}</Text>
          </View>
        )}

        {/* Text evidence inputs */}
        {needsText && (
          <View className="mb-4">
            {allEvidence
              .filter((e) =>
                ["text_response", "json_response", "measurement", "url_reference", "text_report"].includes(e)
              )
              .map((evidenceType) => (
                <View key={evidenceType} className="mb-3">
                  <Text className="text-gray-400 text-sm mb-1">
                    {evidenceType.replace(/_/g, " ")}
                    {requiredEvidence.includes(evidenceType) ? ` ${t("submit.required_suffix")}` : ` ${t("submit.optional_suffix")}`}
                  </Text>
                  <TextInput
                    className="bg-surface rounded-xl px-4 py-3 text-white"
                    placeholder={t("submit.enterEvidence", { type: evidenceType.replace(/_/g, " ") })}
                    placeholderTextColor="#666"
                    value={textEvidence[evidenceType] || ""}
                    onChangeText={(text) =>
                      setTextEvidence((prev) => ({ ...prev, [evidenceType]: text }))
                    }
                    multiline={evidenceType !== "url_reference"}
                    numberOfLines={evidenceType === "text_report" ? 6 : 3}
                    style={{ minHeight: evidenceType === "text_report" ? 120 : 60, textAlignVertical: "top" }}

                  />
                </View>
              ))}
          </View>
        )}

        {/* Notes */}
        <View className="mb-4">
          <Text className="text-gray-400 text-sm mb-1">{t("submit.additionalNotes")}</Text>
          <TextInput
            className="bg-surface rounded-xl px-4 py-3 text-white"
            placeholder={t("submit.notesPlaceholder")}
            placeholderTextColor="#666"
            value={notes}
            onChangeText={setNotes}
            multiline
            numberOfLines={2}
            style={{ minHeight: 60, textAlignVertical: "top" }}

          />
        </View>

        {/* Extra padding so bottom fields scroll above keyboard */}
        <View className="h-40" />
      </ScrollView>
      </KeyboardAvoidingView>

      {/* Fixed bottom button — above Android nav bar */}
      <View className="px-4 pt-3 pb-8 border-t border-gray-800 bg-black">
        <Pressable
          className={`rounded-2xl py-4 items-center ${
            submitting ? "bg-gray-700" : "bg-white"
          }`}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <View className="flex-row items-center">
              <ActivityIndicator color="#000" />
              <Text className="text-black font-bold text-lg ml-3">
                {t("submit.submitting")}
              </Text>
            </View>
          ) : (
            <Text className="text-black font-bold text-lg">
              {t("submit.submitButton")}
            </Text>
          )}
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

function tryParseJSON(str: string): unknown {
  try {
    return JSON.parse(str);
  } catch {
    return str;
  }
}
