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
      className="py-1"
      contentContainerStyle={{ paddingHorizontal: 16, gap: 6 }}
    >
      {/* All button */}
      <Pressable
        className={`rounded-full px-3 py-1 ${
          selected === null ? "bg-white" : "bg-surface"
        }`}
        onPress={() => onSelect(null)}
      >
        <Text
          className={`text-xs font-medium ${
            selected === null ? "text-black" : "text-gray-400"
          }`}
        >
          {t("browse.allCategories")}
        </Text>
      </Pressable>

      {TASK_CATEGORIES.map((cat) => (
        <Pressable
          key={cat.key}
          className={`rounded-full px-3 py-1 flex-row items-center ${
            selected === cat.key ? "bg-white" : "bg-surface"
          }`}
          onPress={() => onSelect(selected === cat.key ? null : cat.key)}
        >
          <Text style={{ fontSize: 12 }}>{cat.icon}</Text>
          <Text
            className={`text-xs font-medium ml-1 ${
              selected === cat.key ? "text-black" : "text-gray-400"
            }`}
          >
            {t(`categories.${cat.key}`, cat.key)}
          </Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}
