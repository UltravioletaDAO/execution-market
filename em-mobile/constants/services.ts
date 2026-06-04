/**
 * Consumer service catalog (mobile) — mirror of the web dashboard's
 * constants/services.ts. Each entry maps an es-CO label/icon to a physical
 * TaskCategory; the services screen routes to the publish wizard with the
 * category preset and target_executor_type='human' (H2H).
 */
export interface ServiceDef {
  key: string;
  icon: string;
  label: string;
  desc: string;
  category: string;
}

export const SERVICES: ServiceDef[] = [
  { key: "domicilio", icon: "🛵", label: "Domicilio", desc: "Entrega o recogida", category: "physical_presence" },
  { key: "mandado", icon: "📦", label: "Mandado", desc: "Compra o diligencia", category: "simple_action" },
  { key: "tramite", icon: "🔑", label: "Trámite", desc: "Fila, firma o gestión", category: "human_authority" },
  { key: "foto", icon: "📸", label: "Foto / Evidencia", desc: "Captura en sitio", category: "digital_physical" },
  { key: "hogar", icon: "🏠", label: "Hogar", desc: "Arreglos o limpieza", category: "physical_presence" },
  { key: "info", icon: "🔍", label: "Info local", desc: "Verificar algo en sitio", category: "knowledge_access" },
];
