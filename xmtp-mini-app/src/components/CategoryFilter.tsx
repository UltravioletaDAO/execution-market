const CATEGORIES = [
  { value: "", label: "Todas" },
  { value: "physical_presence", label: "Presencia Fisica" },
  { value: "knowledge_access", label: "Acceso a Info" },
  { value: "human_authority", label: "Autoridad Humana" },
  { value: "simple_action", label: "Accion Simple" },
  { value: "digital_physical", label: "Digital + Fisico" },
];

interface Props {
  selected: string;
  onChange: (category: string) => void;
}

export function CategoryFilter({ selected, onChange }: Props) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      {CATEGORIES.map((cat) => (
        <button
          key={cat.value}
          onClick={() => onChange(cat.value)}
          className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            selected === cat.value
              ? "bg-white text-black"
              : "bg-white/5 text-white/60 hover:bg-white/10"
          }`}
        >
          {cat.label}
        </button>
      ))}
    </div>
  );
}
