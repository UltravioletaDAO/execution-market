import { Pressable, Text } from "react-native";
import { useTranslation } from "react-i18next";
import * as ImagePicker from "expo-image-picker";
import type { ExifData } from "./CameraCapture";

interface ImagePickerButtonProps {
  onPick: (uri: string, exif?: ExifData) => void;
}

export function ImagePickerButton({ onPick }: ImagePickerButtonProps) {
  const { t } = useTranslation();

  async function pickImage() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: true,
      quality: 0.8,
      exif: true,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      const exif = asset.exif as ExifData | undefined;
      if (exif) {
        console.log("[ImagePicker] EXIF found:", Object.keys(exif).join(", "));
      } else {
        console.log("[ImagePicker] No EXIF data in selected image");
      }
      onPick(asset.uri, exif);
    }
  }

  return (
    <Pressable
      className="flex-1 bg-surface rounded-2xl py-6 items-center"
      onPress={pickImage}
    >
      <Text style={{ fontSize: 32 }}>{"\uD83D\uDDBC\uFE0F"}</Text>
      <Text className="text-white font-medium mt-2">{t("submit.gallery")}</Text>
    </Pressable>
  );
}
