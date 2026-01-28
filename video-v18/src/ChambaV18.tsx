import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

const colors = {
  bg: "#0a0a0a",
  primary: "#8B5CF6",
  secondary: "#06B6D4",
  accent: "#F59E0B",
  success: "#10B981",
  text: "#FFFFFF",
  textMuted: "#A1A1AA",
};

// ============ ESCENA 1: HOOK - Notificación ============
const Scene1Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const slideIn = spring({ frame, fps, config: { damping: 12 } });
  const pulse = Math.sin(frame * 0.1) * 0.05 + 1;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center" }}>
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
          <div style={{ width: 50, height: 50, borderRadius: "50%", backgroundColor: colors.primary, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>
            📍
          </div>
          <span style={{ color: colors.textMuted, fontSize: 24 }}>Chamba</span>
        </div>
        <p style={{ color: colors.text, fontSize: 32, lineHeight: 1.5, margin: 0 }}>
          "Verificar cartel de <span style={{ color: colors.accent }}>'Se Renta'</span>"
        </p>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 30 }}>
          <span style={{ color: colors.success, fontSize: 48, fontWeight: "bold" }}>$3</span>
          <span style={{ color: colors.secondary, fontSize: 28 }}>200 metros</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 2: PROBLEMA ============
const Scene2Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const line2Delay = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 100 }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ color: colors.text, fontSize: 72, fontWeight: "bold", opacity: fadeIn, marginBottom: 40 }}>
          Los agentes pueden <span style={{ color: colors.primary }}>pensar</span>.
        </h1>
        <h1 style={{ color: colors.text, fontSize: 72, fontWeight: "bold", opacity: line2Delay }}>
          Pero no pueden <span style={{ color: colors.accent }}>estar ahí</span>.
        </h1>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 3: QUOTE DAVOS (V18 - más fuerte) ============
const Scene3Davos: React.FC = () => {
  const frame = useCurrentFrame();
  const scale = spring({ frame, fps: 30, config: { damping: 15 } });
  const line2 = interpolate(frame, [60, 80], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ transform: `scale(${scale})`, maxWidth: 1400, textAlign: "center" }}>
        <p style={{ color: colors.textMuted, fontSize: 24, marginBottom: 30 }}>
          DAVOS 2026 - Dario Amodei, CEO de Anthropic
        </p>
        <blockquote style={{ color: colors.text, fontSize: 42, fontStyle: "italic", lineHeight: 1.4, borderLeft: `4px solid ${colors.primary}`, paddingLeft: 40, margin: 0, textAlign: "left" }}>
          "El creador de Claude Code dijo que el <span style={{ color: colors.accent }}>100% de sus contribuciones</span> en diciembre fueron escritas por Claude Code."
        </blockquote>
        <p style={{ color: colors.secondary, fontSize: 36, marginTop: 40, opacity: line2 }}>
          "6 a 12 meses para que la IA haga <span style={{ color: colors.accent }}>todo</span> lo que hacen los ingenieros."
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 4: LATAM IMPACT (NUEVA!) ============
const Scene4Latam: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const title = spring({ frame, fps, config: { damping: 12 } });
  const sf = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });
  const col = interpolate(frame, [60, 80], [0, 1], { extrapolateRight: "clamp" });
  const conclusion = interpolate(frame, [100, 120], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center" }}>
        <h2 style={{ color: colors.text, fontSize: 56, marginBottom: 60, transform: `scale(${title})` }}>
          <span style={{ color: colors.accent }}>$0.50</span> USD
        </h2>

        <div style={{ display: "flex", gap: 80, justifyContent: "center", marginBottom: 60 }}>
          <div style={{ opacity: sf, transform: `translateY(${interpolate(sf, [0, 1], [30, 0])}px)` }}>
            <p style={{ color: colors.textMuted, fontSize: 28 }}>San Francisco</p>
            <p style={{ color: colors.text, fontSize: 48 }}>🚫 Ni un café</p>
          </div>

          <div style={{ opacity: col, transform: `translateY(${interpolate(col, [0, 1], [30, 0])}px)` }}>
            <p style={{ color: colors.textMuted, fontSize: 28 }}>Colombia</p>
            <p style={{ color: colors.success, fontSize: 48, fontWeight: "bold" }}>$2,000 COP</p>
          </div>
        </div>

        <p style={{ color: colors.secondary, fontSize: 36, opacity: conclusion, maxWidth: 1000 }}>
          20 tareas/día = <span style={{ color: colors.success }}>$5-10 USD</span> = Almuerzo de la semana
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 5: ARBITRAJE GEOGRÁFICO ============
const Scene5Arbitrage: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 100 }}>
      <div style={{ textAlign: "center", opacity: fadeIn }}>
        <h1 style={{ color: colors.text, fontSize: 56, marginBottom: 40, lineHeight: 1.3 }}>
          Los agentes <span style={{ color: colors.primary }}>no distinguen</span> entre
        </h1>
        <div style={{ display: "flex", gap: 40, justifyContent: "center", marginBottom: 50 }}>
          <span style={{ color: colors.secondary, fontSize: 64 }}>Manhattan</span>
          <span style={{ color: colors.textMuted, fontSize: 64 }}>y</span>
          <span style={{ color: colors.accent, fontSize: 64 }}>Medellín</span>
        </div>
        <p style={{ color: colors.textMuted, fontSize: 36 }}>
          Solo importa que el trabajo <span style={{ color: colors.success }}>se haga</span>.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 6: SOLUCIÓN - CHAMBA ============
const Scene6Solution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const logoScale = spring({ frame, fps, config: { damping: 10 } });
  const textFade = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ color: colors.primary, fontSize: 180, fontWeight: "bold", transform: `scale(${logoScale})`, textShadow: `0 0 100px ${colors.primary}`, marginBottom: 40 }}>
          CHAMBA
        </h1>
        <p style={{ color: colors.text, fontSize: 42, opacity: textFade, maxWidth: 900 }}>
          Infraestructura para que <span style={{ color: colors.secondary }}>agentes contraten humanos</span>
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 7: STACK (V18 - 17 redes) ============
const Scene7Stack: React.FC = () => {
  const frame = useCurrentFrame();

  const items = [
    { icon: "⚡", name: "x402", desc: "Pagos HTTP" },
    { icon: "🔄", name: "x402r", desc: "Refunds auto" },
    { icon: "🆔", name: "ERC-8004", desc: "Identidad 0-100" },
    { icon: "🌊", name: "Superfluid", desc: "Streaming" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <h2 style={{ color: colors.text, fontSize: 48, marginBottom: 20 }}>Los rieles ya existen</h2>
      <p style={{ color: colors.success, fontSize: 32, marginBottom: 50 }}>
        17 redes mainnet • Live en producción
      </p>
      <div style={{ display: "flex", gap: 30 }}>
        {items.map((item, i) => {
          const delay = i * 10;
          const scale = spring({ frame: frame - delay, fps: 30, config: { damping: 12 } });
          return (
            <div key={i} style={{ backgroundColor: "#1F1F23", padding: "30px 40px", borderRadius: 16, textAlign: "center", transform: `scale(${Math.max(0, scale)})`, border: `2px solid ${colors.primary}40` }}>
              <span style={{ fontSize: 40 }}>{item.icon}</span>
              <h3 style={{ color: colors.primary, fontSize: 28, marginTop: 10, marginBottom: 5 }}>{item.name}</h3>
              <p style={{ color: colors.textMuted, fontSize: 18, margin: 0 }}>{item.desc}</p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 8: CTA (V18 - más fuerte) ============
const Scene8CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = Math.sin(frame * 0.15) * 0.03 + 1;
  const line2 = interpolate(frame, [40, 60], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", background: `radial-gradient(circle at center, ${colors.primary}20, ${colors.bg})` }}>
      <div style={{ textAlign: "center", transform: `scale(${pulse})` }}>
        <h1 style={{ color: colors.text, fontSize: 52, marginBottom: 30, lineHeight: 1.3 }}>
          ¿Vas a ser de los que <span style={{ color: colors.success }}>lo vieron venir</span>?
        </h1>
        <h2 style={{ color: colors.accent, fontSize: 44, marginBottom: 50, opacity: line2 }}>
          ¿O de los que se enteraron cuando ya era tarde?
        </h2>
        <p style={{ color: colors.primary, fontSize: 56, fontWeight: "bold" }}>@ultravioletadao</p>
      </div>
    </AbsoluteFill>
  );
};

// ============ VIDEO PRINCIPAL V18 ============
export const ChambaV18: React.FC = () => {
  const { fps } = useVideoConfig();

  const scenes = [
    { component: Scene1Hook, duration: 5 },
    { component: Scene2Problem, duration: 7 },
    { component: Scene3Davos, duration: 12 },
    { component: Scene4Latam, duration: 15 },      // NUEVA!
    { component: Scene5Arbitrage, duration: 10 },  // NUEVA!
    { component: Scene6Solution, duration: 12 },
    { component: Scene7Stack, duration: 15 },
    { component: Scene8CTA, duration: 14 },
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
