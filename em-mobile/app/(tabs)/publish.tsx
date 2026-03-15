import { View, Text, ScrollView, Pressable, TextInput, ActivityIndicator, Alert, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../providers/AuthProvider";
import { ConnectWalletButton } from "../../components/ConnectWalletButton";
import { useCreateH2ATask } from "../../hooks/api/useH2A";
import { TASK_CATEGORIES } from "../../constants/categories";
import { NETWORKS } from "../../constants/networks";

const CHAIN_IMAGES: Record<string, number> = {
  base: require("../../assets/images/chains/base.png"),
  ethereum: require("../../assets/images/chains/ethereum.png"),
  polygon: require("../../assets/images/chains/polygon.png"),
  arbitrum: require("../../assets/images/chains/arbitrum.png"),
  avalanche: require("../../assets/images/chains/avalanche.png"),
  optimism: require("../../assets/images/chains/optimism.png"),
  celo: require("../../assets/images/chains/celo.png"),
  monad: require("../../assets/images/chains/monad.png"),
};

type Step = 1 | 2 | 3 | 4;
type ExecutorTarget = "any" | "human" | "agent" | "robot";

const EVIDENCE_TYPES = [
  { key: "json_response", labelKey: "publish.evidenceTypes.json_response", icon: "\uD83D\uDCCB" },
  { key: "code_output", labelKey: "publish.evidenceTypes.code_output", icon: "\uD83D\uDCBB" },
  { key: "text_report", labelKey: "publish.evidenceTypes.text_report", icon: "\uD83D\uDCDD" },
  { key: "api_response", labelKey: "publish.evidenceTypes.api_response", icon: "\uD83D\uDD0C" },
  { key: "structured_data", labelKey: "publish.evidenceTypes.structured_data", icon: "\uD83D\uDCCA" },
  { key: "text_response", labelKey: "publish.evidenceTypes.text_response", icon: "\u270D\uFE0F" },
  { key: "photo", labelKey: "publish.evidenceTypes.photo", icon: "\uD83D\uDCF7" },
  { key: "photo_geo", labelKey: "publish.evidenceTypes.photo_geo", icon: "\uD83D\uDCCD" },
  { key: "screenshot", labelKey: "publish.evidenceTypes.screenshot", icon: "\uD83D\uDDA5\uFE0F" },
  { key: "document", labelKey: "publish.evidenceTypes.document", icon: "\uD83D\uDCC4" },
  { key: "video", labelKey: "publish.evidenceTypes.video", icon: "\uD83C\uDFA5" },
  { key: "receipt", labelKey: "publish.evidenceTypes.receipt", icon: "\uD83E\uDDFE" },
];

const DEADLINES = [
  { hours: 1, labelKey: "publish.deadlines.1h" },
  { hours: 4, labelKey: "publish.deadlines.4h" },
  { hours: 12, labelKey: "publish.deadlines.12h" },
  { hours: 24, labelKey: "publish.deadlines.1d" },
  { hours: 72, labelKey: "publish.deadlines.3d" },
  { hours: 168, labelKey: "publish.deadlines.1w" },
];

const EXECUTOR_TARGETS: Array<{ key: ExecutorTarget; labelKey: string; icon: string; descKey: string }> = [
  { key: "any", labelKey: "publish.executorTargets.any", icon: "\uD83C\uDF10", descKey: "publish.executorTargets.anyDesc" },
  { key: "human", labelKey: "publish.executorTargets.human", icon: "\uD83E\uDDD1", descKey: "publish.executorTargets.humanDesc" },
  { key: "agent", labelKey: "publish.executorTargets.agent", icon: "\uD83E\uDD16", descKey: "publish.executorTargets.agentDesc" },
  { key: "robot", labelKey: "publish.executorTargets.robot", icon: "\uD83E\uDDBE", descKey: "publish.executorTargets.robotDesc" },
];

export default function PublishTaskScreen() {
  const { t } = useTranslation();
  const { isAuthenticated, executor } = useAuth();
  const createTask = useCreateH2ATask();

  const [step, setStep] = useState<Step>(1);
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [targetType, setTargetType] = useState<ExecutorTarget>("any");
  const [bounty, setBounty] = useState("0.10");
  const [deadlineHours, setDeadlineHours] = useState(24);
  const [selectedEvidence, setSelectedEvidence] = useState<string[]>(["text_response"]);
  const [network, setNetwork] = useState("base");
  const [published, setPublished] = useState(false);
  const [publishedTaskId, setPublishedTaskId] = useState<string | null>(null);

  const fee = parseFloat(bounty || "0") * 0.13;
  const total = parseFloat(bounty || "0") + fee;

  if (!isAuthenticated) {
    return (
      <SafeAreaView className="flex-1 bg-black">
        <View className="px-4 pt-4">
          <Text className="text-white text-2xl font-bold">{t("publish.title")}</Text>
          <Text className="text-gray-400 text-sm mt-1">{t("publish.subtitle")}</Text>
        </View>
        <View className="flex-1 items-center justify-center px-6">
          <Text style={{ fontSize: 48 }}>{"\uD83D\uDCCB"}</Text>
          <Text className="text-gray-400 text-lg text-center mt-4 mb-8">
            {t("publish.connectToPublish")}
          </Text>
          <View className="w-full">
            <ConnectWalletButton />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  if (published) {
    return (
      <SafeAreaView className="flex-1 bg-black items-center justify-center px-6">
        <Text style={{ fontSize: 64 }}>{"\uD83C\uDF89"}</Text>
        <Text className="text-white text-2xl font-bold mt-4 text-center">
          {t("publish.success")}
        </Text>
        <View className="bg-surface rounded-2xl p-4 mt-6 w-full">
          <View className="flex-row justify-between mb-2">
            <Text className="text-gray-400">{t("publish.reward")}</Text>
            <Text className="text-white font-bold">${parseFloat(bounty).toFixed(2)}</Text>
          </View>
          <View className="flex-row justify-between mb-2">
            <Text className="text-gray-400">{t("publish.platformFee")}</Text>
            <Text className="text-white">${fee.toFixed(2)}</Text>
          </View>
          <View className="flex-row justify-between pt-2 border-t border-gray-800">
            <Text className="text-white font-bold">{t("publish.total")}</Text>
            <Text className="text-white font-bold">${total.toFixed(2)} USDC</Text>
          </View>
        </View>
        <Pressable
          className="bg-white rounded-2xl py-4 items-center mt-6 w-full"
          onPress={() => {
            setPublished(false);
            setStep(1);
            setTitle("");
            setInstructions("");
            setCategory(null);
          }}
        >
          <Text className="text-black font-bold text-lg">{t("publish.createAnother")}</Text>
        </Pressable>
        <Pressable
          className="py-4 items-center mt-2"
          onPress={() => {
            setPublished(false);
            setStep(1);
          }}
        >
          <Text className="text-gray-400">{t("publish.backToHome")}</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  async function handlePublish() {
    if (!category) return;
    const bountyNum = parseFloat(bounty);
    if (isNaN(bountyNum) || bountyNum <= 0) {
      Alert.alert(t("common.error"), t("publish.invalidAmount"));
      return;
    }
    try {
      const result = await createTask.mutateAsync({
        title: title.trim(),
        instructions: instructions.trim(),
        category,
        bounty_usd: bountyNum,
        deadline_hours: deadlineHours,
        evidence_required: selectedEvidence,
        target_executor_type: targetType,
      });
      setPublishedTaskId((result as any)?.id || null);
      setPublished(true);
    } catch (e) {
      Alert.alert(t("common.error"), (e as Error).message || t("publish.publishError"));
    }
  }

  const StepIndicator = () => (
    <View className="flex-row items-center justify-center gap-2 py-4">
      {[1, 2, 3, 4].map((s) => (
        <View
          key={s}
          className={`h-2 rounded-full ${
            s === step ? "w-8 bg-white" : s < step ? "w-8 bg-gray-600" : "w-2 bg-gray-700"
          }`}
        />
      ))}
    </View>
  );

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="px-4 pt-4">
        <Text className="text-white text-2xl font-bold">{t("publish.title")}</Text>
        <Text className="text-gray-400 text-sm mt-0.5">
          {t(`publish.step${step}`)} ({step}/4)
        </Text>
      </View>

      <StepIndicator />

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        {step === 1 && (
          <View>
            <Text className="text-gray-400 text-sm mb-2">{t("publish.taskTitle")} *</Text>
            <TextInput
              className="bg-surface rounded-xl px-4 py-3 text-white mb-4"
              placeholder={t("publish.titlePlaceholder")}
              placeholderTextColor="#666"
              value={title}
              onChangeText={setTitle}
              maxLength={255}
            />

            <Text className="text-gray-400 text-sm mb-2">{t("publish.instructions")} *</Text>
            <TextInput
              className="bg-surface rounded-xl px-4 py-3 text-white mb-4"
              placeholder={t("publish.instructionsPlaceholder")}
              placeholderTextColor="#666"
              value={instructions}
              onChangeText={setInstructions}
              multiline
              numberOfLines={5}
              style={{ minHeight: 120, textAlignVertical: "top" }}
              maxLength={10000}
            />

            <Text className="text-gray-400 text-sm mb-2">{t("publish.category")} *</Text>
            <View className="flex-row flex-wrap gap-2 mb-4">
              {TASK_CATEGORIES.map((cat) => (
                <Pressable
                  key={cat.key}
                  className={`rounded-full px-3 py-2 flex-row items-center ${
                    category === cat.key ? "bg-white" : "bg-surface"
                  }`}
                  onPress={() => setCategory(cat.key)}
                >
                  <Text style={{ fontSize: 14 }}>{cat.icon}</Text>
                  <Text
                    className={`text-xs ml-1 font-medium ${
                      category === cat.key ? "text-black" : "text-gray-400"
                    }`}
                  >
                    {t(`categories.${cat.key}`, cat.key)}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        )}

        {step === 2 && (
          <View>
            <Text className="text-white text-lg font-bold mb-4">
              {t("publish.targetType")}
            </Text>
            {EXECUTOR_TARGETS.map((target) => (
              <Pressable
                key={target.key}
                className={`rounded-2xl p-4 mb-3 flex-row items-center ${
                  targetType === target.key ? "bg-white" : "bg-surface"
                }`}
                onPress={() => setTargetType(target.key)}
              >
                <Text style={{ fontSize: 32 }}>{target.icon}</Text>
                <View className="ml-4 flex-1">
                  <Text
                    className={`font-bold ${
                      targetType === target.key ? "text-black" : "text-white"
                    }`}
                  >
                    {t(target.labelKey)}
                  </Text>
                  <Text
                    className={`text-sm mt-0.5 ${
                      targetType === target.key ? "text-gray-600" : "text-gray-400"
                    }`}
                  >
                    {t(target.descKey)}
                  </Text>
                </View>
                {targetType === target.key && (
                  <Text className="text-black text-xl">{"\u2713"}</Text>
                )}
              </Pressable>
            ))}
          </View>
        )}

        {step === 3 && (
          <View>
            <Text className="text-gray-400 text-sm mb-2">{t("publish.bounty")} *</Text>
            <View className="bg-surface rounded-xl px-4 py-3 flex-row items-center mb-4">
              <Text className="text-white text-2xl font-bold mr-1">$</Text>
              <TextInput
                className="text-white text-2xl font-bold flex-1"
                value={bounty}
                onChangeText={setBounty}
                keyboardType="decimal-pad"
                placeholder="0.10"
                placeholderTextColor="#666"
              />
              <Text className="text-gray-400">USDC</Text>
            </View>

            <Text className="text-gray-400 text-sm mb-2">{t("publish.deadline")}</Text>
            <View className="flex-row flex-wrap gap-2 mb-4">
              {DEADLINES.map((dl) => (
                <Pressable
                  key={dl.hours}
                  className={`rounded-full px-4 py-2 ${
                    deadlineHours === dl.hours ? "bg-white" : "bg-surface"
                  }`}
                  onPress={() => setDeadlineHours(dl.hours)}
                >
                  <Text
                    className={`text-sm font-medium ${
                      deadlineHours === dl.hours ? "text-black" : "text-gray-400"
                    }`}
                  >
                    {t(dl.labelKey)}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text className="text-gray-400 text-sm mb-2">{t("publish.evidenceRequired")}</Text>
            <View className="flex-row flex-wrap gap-2 mb-4">
              {EVIDENCE_TYPES.map((ev) => (
                <Pressable
                  key={ev.key}
                  className={`rounded-full px-3 py-2 flex-row items-center ${
                    selectedEvidence.includes(ev.key) ? "bg-white" : "bg-surface"
                  }`}
                  onPress={() => {
                    setSelectedEvidence((prev) =>
                      prev.includes(ev.key)
                        ? prev.filter((e) => e !== ev.key)
                        : [...prev, ev.key]
                    );
                  }}
                >
                  <Text style={{ fontSize: 12 }}>{ev.icon}</Text>
                  <Text
                    className={`text-xs ml-1 ${
                      selectedEvidence.includes(ev.key) ? "text-black font-bold" : "text-gray-400"
                    }`}
                  >
                    {t(ev.labelKey)}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text className="text-gray-400 text-sm mb-2">{t("publish.paymentNetwork")}</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              <View className="flex-row gap-2 mb-4">
                {NETWORKS.map((net) => (
                  <Pressable
                    key={net.key}
                    className={`rounded-full px-4 py-2 flex-row items-center ${
                      network === net.key ? "bg-white" : "bg-surface"
                    }`}
                    onPress={() => setNetwork(net.key)}
                  >
                    {CHAIN_IMAGES[net.key] && (
                      <Image
                        source={CHAIN_IMAGES[net.key]}
                        style={{ width: 18, height: 18, borderRadius: 9, marginRight: 6 }}
                      />
                    )}
                    <Text
                      className={`text-sm font-medium ${
                        network === net.key ? "text-black" : "text-gray-400"
                      }`}
                    >
                      {net.name}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </ScrollView>
          </View>
        )}

        {step === 4 && (
          <View>
            <View className="bg-surface rounded-2xl p-4 mb-4">
              <Text className="text-white text-lg font-bold mb-1">{title}</Text>
              <Text className="text-gray-400 text-sm mb-3" numberOfLines={4}>
                {instructions}
              </Text>
              <View className="flex-row flex-wrap gap-2">
                {category && (
                  <View className="bg-surface-light rounded-full px-3 py-1">
                    <Text className="text-gray-300 text-xs">
                      {TASK_CATEGORIES.find((c) => c.key === category)?.icon}{" "}
                      {t(`categories.${category}`, category)}
                    </Text>
                  </View>
                )}
                <View className="bg-surface-light rounded-full px-3 py-1">
                  <Text className="text-gray-300 text-xs">
                    {EXECUTOR_TARGETS.find((e) => e.key === targetType)?.icon}{" "}
                    {t(EXECUTOR_TARGETS.find((e) => e.key === targetType)?.labelKey || "")}
                  </Text>
                </View>
              </View>
            </View>

            <View className="bg-surface rounded-2xl p-4 mb-4">
              <Text className="text-white font-bold mb-3">{t("publish.costSummary")}</Text>
              <View className="flex-row justify-between mb-2">
                <Text className="text-gray-400">{t("publish.reward")}</Text>
                <Text className="text-white font-bold">${parseFloat(bounty).toFixed(2)} USDC</Text>
              </View>
              <View className="flex-row justify-between mb-2">
                <Text className="text-gray-400">{t("publish.platformFee")}</Text>
                <Text className="text-white">${fee.toFixed(4)} USDC</Text>
              </View>
              <View className="flex-row justify-between mb-2">
                <Text className="text-gray-400">{t("publish.deadline")}</Text>
                <Text className="text-white">
                  {t(DEADLINES.find((d) => d.hours === deadlineHours)?.labelKey || "")}
                </Text>
              </View>
              <View className="flex-row justify-between mb-2">
                <Text className="text-gray-400">{t("publish.paymentNetwork")}</Text>
                <Text className="text-white">
                  {NETWORKS.find((n) => n.key === network)?.name}
                </Text>
              </View>
              <View className="flex-row justify-between pt-2 mt-2 border-t border-gray-800">
                <Text className="text-white font-bold text-lg">{t("publish.total")}</Text>
                <Text className="text-white font-bold text-lg">${total.toFixed(4)} USDC</Text>
              </View>
            </View>

            <View className="bg-yellow-900/20 rounded-2xl p-4 mb-4">
              <Text className="text-yellow-400 text-sm">
                {t("publish.balanceWarning", { network: NETWORKS.find((n) => n.key === network)?.name })}
              </Text>
            </View>
          </View>
        )}

        <View className="h-8" />
      </ScrollView>

      <View className="px-4 py-4 pb-8 border-t border-gray-800">
        <View className="flex-row gap-3">
          {step > 1 && (
            <Pressable
              className="flex-1 bg-surface rounded-2xl py-4 items-center"
              onPress={() => setStep((step - 1) as Step)}
            >
              <Text className="text-white font-bold">{t("common.back")}</Text>
            </Pressable>
          )}

          {step < 4 ? (
            <Pressable
              className={`flex-1 rounded-2xl py-4 items-center ${
                (step === 1 && (!title.trim() || !instructions.trim() || !category))
                  ? "bg-gray-700"
                  : "bg-white"
              }`}
              onPress={() => setStep((step + 1) as Step)}
              disabled={step === 1 && (!title.trim() || !instructions.trim() || !category)}
            >
              <Text className={`font-bold ${
                (step === 1 && (!title.trim() || !instructions.trim() || !category))
                  ? "text-gray-500"
                  : "text-black"
              }`}>
                {t("common.next")}
              </Text>
            </Pressable>
          ) : (
            <Pressable
              className={`flex-1 rounded-2xl py-4 items-center ${
                createTask.isPending ? "bg-gray-700" : "bg-white"
              }`}
              onPress={handlePublish}
              disabled={createTask.isPending}
            >
              {createTask.isPending ? (
                <ActivityIndicator color="#000" />
              ) : (
                <Text className="text-black font-bold text-lg">
                  {t("publish.submit")}
                </Text>
              )}
            </Pressable>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}
