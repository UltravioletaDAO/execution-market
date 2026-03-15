import { ScrollView, Pressable, Text } from "react-native";
import { useTranslation } from "react-i18next";
import { TASK_CATEGORIES } from "../constants/categories";

interface CategoryFilterProps {
  selected: string | null;
  onSelect: (category: string | null) => void;
}

export function CategoryFilter({ selected, onSelect }: CategoryFilterProps) {
  const { t } = useTranslation();

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={{ flexGrow: 0, marginVertical: 6 }}
      contentContainerStyle={{ paddingHorizontal: 16, gap: 6, alignItems: "center" }}
    >
      {/* All button */}
      <Pressable
        className={`rounded-full px-2 py-0.5 ${
          selected === null ? "bg-white" : "bg-surface"
        }`}
        onPress={() => onSelect(null)}
      >
        <Text
          className={`font-medium ${
            selected === null ? "text-black" : "text-gray-400"
          }`}
          style={{ fontSize: 11 }}
        >
          {t("browse.allCategories")}
        </Text>
      </Pressable>

      {TASK_CATEGORIES.map((cat) => (
        <Pressable
          key={cat.key}
          className={`rounded-full px-2 py-0.5 flex-row items-center ${
            selected === cat.key ? "bg-white" : "bg-surface"
          }`}
          onPress={() => onSelect(selected === cat.key ? null : cat.key)}
        >
          <Text style={{ fontSize: 10 }}>{cat.icon}</Text>
          <Text
            className={`font-medium ml-1 ${
              selected === cat.key ? "text-black" : "text-gray-400"
            }`}
            style={{ fontSize: 11 }}
          >
            {t(`categories.${cat.key}`, cat.key)}
          </Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}
