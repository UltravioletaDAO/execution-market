import { View, Text, Pressable, Image, StyleSheet, Dimensions } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useState, useRef } from "react";
import { useTranslation } from "react-i18next";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");

interface CameraCaptureProps {
  onCapture: (uri: string) => void;
  onCancel: () => void;
}

export function CameraCapture({ onCapture, onCancel }: CameraCaptureProps) {
  const { t } = useTranslation();
  const [permission, requestPermission] = useCameraPermissions();
  const [facing, setFacing] = useState<"front" | "back">("back");
  const [flash, setFlash] = useState<"off" | "on">("off");
  const [preview, setPreview] = useState<string | null>(null);
  const cameraRef = useRef<CameraView>(null);

  if (!permission) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>{t("camera.loading")}</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <Text style={{ fontSize: 48 }}>{"\uD83D\uDCF7"}</Text>
        <Text style={styles.permissionText}>
          {t("camera.permissionText")}
        </Text>
        <Pressable style={styles.permissionButton} onPress={requestPermission}>
          <Text style={styles.permissionButtonText}>{t("camera.allowCamera")}</Text>
        </Pressable>
        <Pressable style={styles.cancelLink} onPress={onCancel}>
          <Text style={styles.cancelText}>{t("common.cancel")}</Text>
        </Pressable>
      </View>
    );
  }

  if (preview) {
    return (
      <View style={styles.container}>
        <Image
          source={{ uri: preview }}
          style={styles.previewImage}
          resizeMode="contain"
        />
        <View style={styles.previewControls}>
          <Pressable style={styles.retakeButton} onPress={() => setPreview(null)}>
            <Text style={styles.retakeText}>{t("camera.retake")}</Text>
          </Pressable>
          <Pressable style={styles.useButton} onPress={() => onCapture(preview)}>
            <Text style={styles.useText}>{t("camera.usePhoto")}</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing={facing}
        flash={flash}
      >
        {/* Top controls */}
        <View style={styles.topControls}>
          <Pressable style={styles.controlButton} onPress={onCancel}>
            <Text style={styles.controlIcon}>{"\u2715"}</Text>
          </Pressable>
          <Pressable
            style={styles.controlButton}
            onPress={() => setFlash(flash === "off" ? "on" : "off")}
          >
            <Text style={styles.controlIcon}>
              {flash === "on" ? "\u26A1" : "\u26A1\uFE0F"}
            </Text>
          </Pressable>
        </View>

        {/* Bottom controls */}
        <View style={styles.bottomControls}>
          <View style={styles.controlRow}>
            {/* Flip camera */}
            <Pressable
              style={styles.flipButton}
              onPress={() => setFacing(facing === "back" ? "front" : "back")}
            >
              <Text style={{ fontSize: 20 }}>{"\uD83D\uDD04"}</Text>
            </Pressable>

            {/* Capture button */}
            <Pressable
              style={styles.captureOuter}
              onPress={async () => {
                if (cameraRef.current) {
                  try {
                    const photo = await cameraRef.current.takePictureAsync({
                      quality: 0.8,
                      exif: true,
                    });
                    if (photo?.uri) {
                      setPreview(photo.uri);
                    }
                  } catch (err) {
                    console.error("[Camera] takePictureAsync error:", err);
                  }
                }
              }}
            >
              <View style={styles.captureInner} />
            </Pressable>

            {/* Spacer */}
            <View style={{ width: 56, height: 56 }} />
          </View>
        </View>
      </CameraView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
    alignItems: "center",
    justifyContent: "center",
  },
  camera: {
    flex: 1,
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
  },
  loadingText: {
    color: "#fff",
    fontSize: 16,
  },
  permissionText: {
    color: "#fff",
    fontSize: 18,
    textAlign: "center",
    marginTop: 16,
    marginBottom: 24,
    paddingHorizontal: 32,
  },
  permissionButton: {
    backgroundColor: "#fff",
    borderRadius: 16,
    paddingHorizontal: 32,
    paddingVertical: 16,
  },
  permissionButtonText: {
    color: "#000",
    fontWeight: "bold",
    fontSize: 16,
  },
  cancelLink: {
    marginTop: 16,
    paddingVertical: 8,
  },
  cancelText: {
    color: "#999",
    fontSize: 14,
  },
  previewImage: {
    flex: 1,
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
  },
  previewControls: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    justifyContent: "space-around",
    paddingVertical: 32,
    paddingHorizontal: 16,
    backgroundColor: "rgba(0,0,0,0.6)",
  },
  retakeButton: {
    backgroundColor: "rgba(127,29,29,0.8)",
    borderRadius: 16,
    paddingHorizontal: 32,
    paddingVertical: 16,
  },
  retakeText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 16,
  },
  useButton: {
    backgroundColor: "#fff",
    borderRadius: 16,
    paddingHorizontal: 32,
    paddingVertical: 16,
  },
  useText: {
    color: "#000",
    fontWeight: "bold",
    fontSize: 16,
  },
  topControls: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 24,
    paddingTop: 48,
  },
  controlButton: {
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 24,
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  controlIcon: {
    color: "#fff",
    fontSize: 18,
  },
  bottomControls: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: "center",
    paddingBottom: 48,
  },
  controlRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 32,
  },
  flipButton: {
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 28,
    width: 56,
    height: 56,
    alignItems: "center",
    justifyContent: "center",
  },
  captureOuter: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 4,
    borderColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  captureInner: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#fff",
  },
});
