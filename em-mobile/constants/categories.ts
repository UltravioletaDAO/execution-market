export const TASK_CATEGORIES = [
  // Physical
  { key: "physical_presence", icon: "📍", color: "#FF6B6B" },
  { key: "knowledge_access", icon: "📚", color: "#4ECDC4" },
  { key: "human_authority", icon: "⚖️", color: "#FFE66D" },
  { key: "simple_action", icon: "🎯", color: "#95E1D3" },
  { key: "digital_physical", icon: "🔗", color: "#F38181" },
  // Digital
  { key: "data_processing", icon: "📊", color: "#AA96DA" },
  { key: "research", icon: "🔬", color: "#A8E6CF" },
  { key: "content_generation", icon: "✍️", color: "#DCD6F7" },
  { key: "code_execution", icon: "💻", color: "#FCBAD3" },
  { key: "api_integration", icon: "🔌", color: "#B5EAD7" },
  { key: "multi_step_workflow", icon: "🔄", color: "#E2F0CB" },
  // Extended
  { key: "delivery", icon: "📦", color: "#FFB7B2" },
  { key: "verification", icon: "✅", color: "#B5E2FA" },
  { key: "survey", icon: "📝", color: "#F9F871" },
  { key: "translation", icon: "🌐", color: "#CAB8FF" },
  { key: "transcription", icon: "🎙️", color: "#FFD6A5" },
  { key: "data_collection", icon: "📋", color: "#CAFFBF" },
  { key: "quality_check", icon: "🔍", color: "#BDB2FF" },
  { key: "testing", icon: "🧪", color: "#FFC6FF" },
  { key: "design", icon: "🎨", color: "#A0C4FF" },
  { key: "other", icon: "📌", color: "#FFFFFC" },
] as const;

export type TaskCategory = (typeof TASK_CATEGORIES)[number]["key"];
