import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";

// Colores del tema
const colors = {
  bg: "#0a0a0a",
  primary: "#8B5CF6", // Violeta
  secondary: "#06B6D4", // Cyan
  accent: "#F59E0B", // Amber
  text: "#FFFFFF",
  textMuted: "#A1A1AA",
  success: "#10B981",
};

// ============ ESCENA 1: HOOK - Notificación ============
const Scene1Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const slideIn = spring({ frame, fps, config: { damping: 12 } });
  const pulse = Math.sin(frame * 0.1) * 0.05 + 1;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* Notificación estilo móvil */}
      <div
        style={{
          transform: `translateY(${interpolate(slideIn, [0, 1], [100, 0])}px) scale(${pulse})`,
          backgroundColor: "#1F1F23",
          borderRadius: 20,
          padding: "30px 50px",
          maxWidth: 800,
          boxShadow: `0 0 60px ${colors.primary}40`,
          border: `2px solid ${colors.primary}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 20 }}>
          <div
            style={{
              width: 50,
              height: 50,
              borderRadius: "50%",
              backgroundColor: colors.primary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 24,
            }}
          >
            📍
          </div>
          <span style={{ color: colors.textMuted, fontSize: 24 }}>Execution Market</span>
        </div>
        <p style={{ color: colors.text, fontSize: 32, lineHeight: 1.5, margin: 0 }}>
          "Un agente necesita verificar que el cartel de{" "}
          <span style={{ color: colors.accent }}>'Se Renta'</span> sigue visible."
        </p>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 30 }}>
          <span style={{ color: colors.success, fontSize: 48, fontWeight: "bold" }}>$3</span>
          <span style={{ color: colors.secondary, fontSize: 28 }}>Estás a 200 metros</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 2: PROBLEMA ============
const Scene2Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const line2Delay = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 100,
      }}
    >
      <div style={{ textAlign: "center" }}>
        <h1
          style={{
            color: colors.text,
            fontSize: 72,
            fontWeight: "bold",
            opacity: fadeIn,
            marginBottom: 40,
          }}
        >
          Los agentes pueden <span style={{ color: colors.primary }}>pensar</span>.
        </h1>
        <h1
          style={{
            color: colors.text,
            fontSize: 72,
            fontWeight: "bold",
            opacity: line2Delay,
          }}
        >
          Pero no pueden <span style={{ color: colors.accent }}>caminar</span>.
        </h1>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 3: QUOTE DAVOS ============
const Scene3Davos: React.FC = () => {
  const frame = useCurrentFrame();
  const scale = spring({ frame, fps: 30, config: { damping: 15 } });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 100,
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          maxWidth: 1200,
          textAlign: "center",
        }}
      >
        <p
          style={{
            color: colors.textMuted,
            fontSize: 28,
            marginBottom: 30,
          }}
        >
          DAVOS 2026 - Dario Amodei, CEO de Anthropic
        </p>
        <blockquote
          style={{
            color: colors.text,
            fontSize: 48,
            fontStyle: "italic",
            lineHeight: 1.4,
            borderLeft: `4px solid ${colors.primary}`,
            paddingLeft: 40,
            margin: 0,
          }}
        >
          "En 3 a 6 meses, la IA estará escribiendo el{" "}
          <span style={{ color: colors.accent }}>90% del código</span>."
        </blockquote>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 4: EJEMPLOS / TABLA ============
const Scene4Examples: React.FC = () => {
  const frame = useCurrentFrame();

  const tasks = [
    { task: "Verificar si tienda está abierta", price: "$0.50", time: "5 min" },
    { task: "Completar un CAPTCHA", price: "$0.25", time: "30 seg" },
    { task: "Tomar foto de cartel", price: "$3.00", time: "10 min" },
    { task: "Hacer llamada telefónica", price: "$0.50", time: "5 min" },
    { task: "Entregar documento urgente", price: "$25.00", time: "1 hora" },
    { task: "Notarizar documento legal", price: "$150.00", time: "1 día" },
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 80,
      }}
    >
      <h2 style={{ color: colors.text, fontSize: 56, marginBottom: 50 }}>
        Tareas que los agentes <span style={{ color: colors.primary }}>no pueden hacer</span>
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 15, width: "100%", maxWidth: 1000 }}>
        {tasks.map((item, i) => {
          const delay = i * 8;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], {
            extrapolateRight: "clamp",
            extrapolateLeft: "clamp",
          });
          const slideX = interpolate(frame, [delay, delay + 15], [-50, 0], {
            extrapolateRight: "clamp",
            extrapolateLeft: "clamp",
          });

          return (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                backgroundColor: "#1F1F23",
                padding: "20px 30px",
                borderRadius: 12,
                opacity,
                transform: `translateX(${slideX}px)`,
              }}
            >
              <span style={{ color: colors.text, fontSize: 28 }}>{item.task}</span>
              <div style={{ display: "flex", gap: 30 }}>
                <span style={{ color: colors.textMuted, fontSize: 24 }}>{item.time}</span>
                <span style={{ color: colors.success, fontSize: 28, fontWeight: "bold" }}>
                  {item.price}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 5: SOLUCIÓN - EXECUTION MARKET ============
const Scene5Solution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 10 } });
  const textFade = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <h1
          style={{
            color: colors.primary,
            fontSize: 180,
            fontWeight: "bold",
            transform: `scale(${logoScale})`,
            textShadow: `0 0 100px ${colors.primary}`,
            marginBottom: 40,
          }}
        >
          EXECUTION MARKET
        </h1>
        <p
          style={{
            color: colors.text,
            fontSize: 42,
            opacity: textFade,
            maxWidth: 900,
          }}
        >
          Infraestructura para que{" "}
          <span style={{ color: colors.secondary }}>agentes contraten humanos</span>
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 6: STACK TECNOLÓGICO ============
const Scene6Stack: React.FC = () => {
  const frame = useCurrentFrame();

  const stack = [
    { name: "x402", desc: "Pagos HTTP nativos" },
    { name: "ERC-8004", desc: "Identidad + reputación 0-100" },
    { name: "Superfluid", desc: "Streaming de pagos" },
    { name: "Safe", desc: "Verificación por consenso" },
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 100,
      }}
    >
      <h2 style={{ color: colors.text, fontSize: 48, marginBottom: 60 }}>
        Los rieles ya existen
      </h2>
      <div style={{ display: "flex", gap: 40 }}>
        {stack.map((item, i) => {
          const delay = i * 12;
          const scale = spring({ frame: frame - delay, fps: 30, config: { damping: 12 } });

          return (
            <div
              key={i}
              style={{
                backgroundColor: "#1F1F23",
                padding: "40px 50px",
                borderRadius: 20,
                textAlign: "center",
                transform: `scale(${Math.max(0, scale)})`,
                border: `2px solid ${colors.primary}40`,
              }}
            >
              <h3 style={{ color: colors.primary, fontSize: 36, marginBottom: 15 }}>
                {item.name}
              </h3>
              <p style={{ color: colors.textMuted, fontSize: 22, margin: 0 }}>{item.desc}</p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 7: CTA ============
const Scene7CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = Math.sin(frame * 0.15) * 0.03 + 1;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        justifyContent: "center",
        alignItems: "center",
        background: `radial-gradient(circle at center, ${colors.primary}20, ${colors.bg})`,
      }}
    >
      <div style={{ textAlign: "center", transform: `scale(${pulse})` }}>
        <h1 style={{ color: colors.text, fontSize: 64, marginBottom: 30 }}>
          El primer empleador que nunca nació
        </h1>
        <h2 style={{ color: colors.primary, fontSize: 56, marginBottom: 50 }}>
          ya está escribiendo ofertas de trabajo.
        </h2>
        <p style={{ color: colors.secondary, fontSize: 48, fontWeight: "bold" }}>
          @ultravioletadao
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ VIDEO PRINCIPAL ============
export const EMVideo: React.FC = () => {
  const { fps } = useVideoConfig();

  // Duración de cada escena en segundos
  const scenes = [
    { component: Scene1Hook, duration: 5 },
    { component: Scene2Problem, duration: 8 },
    { component: Scene3Davos, duration: 10 },
    { component: Scene4Examples, duration: 20 },
    { component: Scene5Solution, duration: 12 },
    { component: Scene6Stack, duration: 15 },
    { component: Scene7CTA, duration: 10 },
  ];

  let currentFrame = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {scenes.map((scene, i) => {
        const Scene = scene.component;
        const durationInFrames = scene.duration * fps;
        const startFrame = currentFrame;
        currentFrame += durationInFrames;

        return (
          <Sequence key={i} from={startFrame} durationInFrames={durationInFrames}>
            <Scene />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
