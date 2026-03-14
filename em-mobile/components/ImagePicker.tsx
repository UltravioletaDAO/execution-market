import { Pressable, Text } from "react-native";
import { useTranslation } from "react-i18next";
import * as ImagePicker from "expo-image-picker";

interface ImagePickerButtonProps {
  onPick: (uri: string) => void;
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
      onPick(result.assets[0].uri);
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
