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
  danger: "#EF4444",
  text: "#FFFFFF",
  textMuted: "#A1A1AA",
};

// ============ ESCENA 1: HOOK - Notificacion ============
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
          maxWidth: 900,
          boxShadow: `0 0 60px ${colors.primary}40`,
          border: `2px solid ${colors.primary}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 20 }}>
          <div style={{ width: 50, height: 50, borderRadius: "50%", backgroundColor: colors.primary, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>
            📍
          </div>
          <span style={{ color: colors.textMuted, fontSize: 24 }}>Execution Market</span>
        </div>
        <p style={{ color: colors.text, fontSize: 30, lineHeight: 1.5, margin: 0 }}>
          "Verificar cartel de <span style={{ color: colors.accent }}>'Se Renta'</span> - 200 metros"
        </p>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 30 }}>
          <span style={{ color: colors.success, fontSize: 56, fontWeight: "bold" }}>$3</span>
          <span style={{ color: colors.textMuted, fontSize: 24, alignSelf: "center" }}>Pago instantaneo</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 2: TITULO PRINCIPAL ============
const Scene2Title: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 10 } });
  const line2 = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center", transform: `scale(${scale})` }}>
        <h1 style={{ color: colors.text, fontSize: 72, fontWeight: "bold", marginBottom: 30, lineHeight: 1.2 }}>
          La IA no te va a <span style={{ color: colors.danger }}>reemplazar</span>.
        </h1>
        <h1 style={{ color: colors.text, fontSize: 72, fontWeight: "bold", opacity: line2 }}>
          Te va a <span style={{ color: colors.success }}>necesitar</span>.
        </h1>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 3: DAVOS / AMODEI ============
const Scene3Davos: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 15 } });
  const line2 = interpolate(frame, [90, 120], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ transform: `scale(${scale})`, maxWidth: 1500, textAlign: "center" }}>
        <p style={{ color: colors.textMuted, fontSize: 24, marginBottom: 30 }}>
          DAVOS 2026 - Dario Amodei, CEO de Anthropic
        </p>
        <blockquote style={{ color: colors.text, fontSize: 38, fontStyle: "italic", lineHeight: 1.5, borderLeft: `4px solid ${colors.primary}`, paddingLeft: 40, margin: 0, textAlign: "left" }}>
          "El creador de Claude Code dijo que el <span style={{ color: colors.accent }}>100% de sus contribuciones</span> en diciembre fueron escritas por Claude Code."
        </blockquote>
        <p style={{ color: colors.secondary, fontSize: 36, marginTop: 50, opacity: line2 }}>
          "6 a 12 meses para que la IA haga <span style={{ color: colors.accent }}>todo</span> lo que hacen los ingenieros."
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 4: SILICON VS CARBON ============
const Scene4SiliconCarbon: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12 } });
  const fadeIn = interpolate(frame, [60, 90], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center", maxWidth: 1400 }}>
        <div style={{ display: "flex", justifyContent: "center", gap: 60, marginBottom: 50, transform: `scale(${scale})` }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 80 }}>🔲</div>
            <p style={{ color: colors.secondary, fontSize: 36, fontWeight: "bold" }}>SILICON</p>
            <p style={{ color: colors.textMuted, fontSize: 24 }}>Procesa. Analiza. Decide.</p>
          </div>
          <div style={{ fontSize: 60, color: colors.textMuted, alignSelf: "center" }}>+</div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 80 }}>🧬</div>
            <p style={{ color: colors.success, fontSize: 36, fontWeight: "bold" }}>CARBON</p>
            <p style={{ color: colors.textMuted, fontSize: 24 }}>Ejecuta. Verifica. Existe.</p>
          </div>
        </div>
        <p style={{ color: colors.text, fontSize: 32, fontStyle: "italic", opacity: fadeIn, lineHeight: 1.5 }}>
          "La elegancia del futuro no esta en hombre vs maquina,<br/>
          sino en su <span style={{ color: colors.accent }}>division del trabajo</span>."
        </p>
        <p style={{ color: colors.textMuted, fontSize: 20, marginTop: 20, opacity: fadeIn }}>- Chris Paik</p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 5: EL PROBLEMA ============
const Scene5Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const line2 = interpolate(frame, [40, 60], [0, 1], { extrapolateRight: "clamp" });
  const line3 = interpolate(frame, [80, 100], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 100 }}>
      <div style={{ textAlign: "center" }}>
        <h2 style={{ color: colors.text, fontSize: 48, marginBottom: 50, opacity: fadeIn }}>
          Los agentes pueden <span style={{ color: colors.primary }}>pensar</span>.
        </h2>
        <h2 style={{ color: colors.text, fontSize: 48, marginBottom: 50, opacity: line2 }}>
          Pero no pueden <span style={{ color: colors.accent }}>estar ahi</span>.
        </h2>
        <p style={{ color: colors.textMuted, fontSize: 32, opacity: line3 }}>
          No pueden cruzar la calle. No pueden firmar. No pueden ser testigos.
        </p>
        <p style={{ color: colors.success, fontSize: 48, fontWeight: "bold", marginTop: 50, opacity: line3 }}>
          Tu si.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 6: EXECUTION MARKET - SOLUCION ============
const Scene6Solution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const logoScale = spring({ frame, fps, config: { damping: 10 } });
  const textFade = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });
  const subtitle = interpolate(frame, [60, 80], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ color: colors.primary, fontSize: 160, fontWeight: "bold", transform: `scale(${logoScale})`, textShadow: `0 0 100px ${colors.primary}`, marginBottom: 20 }}>
          EXECUTION MARKET
        </h1>
        <p style={{ color: colors.accent, fontSize: 36, opacity: textFade, fontWeight: "bold", letterSpacing: 4 }}>
          UNIVERSAL EXECUTION LAYER
        </p>
        <p style={{ color: colors.text, fontSize: 32, opacity: subtitle, marginTop: 40, maxWidth: 900 }}>
          Infraestructura para que <span style={{ color: colors.secondary }}>agentes contraten ejecutores</span><br/>
          humanos hoy, robots manana.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 7: MTURK VS EXECUTION MARKET ============
const Scene7Comparison: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const rows = [
    { label: "Cliente", mturk: "Humanos", em: "Agentes IA", color: colors.secondary },
    { label: "Velocidad", mturk: "Horas/dias", em: "Segundos", color: colors.success },
    { label: "Pagos", mturk: "Retrasados", em: "Instantaneos", color: colors.accent },
    { label: "Minimo", mturk: "$5+", em: "$0.50", color: colors.primary },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <h2 style={{ color: colors.text, fontSize: 48, marginBottom: 50 }}>
        "¿No es esto como <span style={{ color: colors.danger }}>MTurk</span>?" No.
      </h2>
      <div style={{ display: "flex", gap: 60 }}>
        <div style={{ textAlign: "center" }}>
          <h3 style={{ color: colors.danger, fontSize: 32, marginBottom: 20 }}>MTurk</h3>
          {rows.map((row, i) => {
            const delay = i * 12;
            const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
            return (
              <p key={i} style={{ color: colors.textMuted, fontSize: 28, opacity, margin: "15px 0" }}>{row.mturk}</p>
            );
          })}
        </div>
        <div style={{ width: 2, backgroundColor: colors.textMuted, opacity: 0.3 }} />
        <div style={{ textAlign: "center" }}>
          <h3 style={{ color: colors.success, fontSize: 32, marginBottom: 20 }}>Execution Market</h3>
          {rows.map((row, i) => {
            const delay = i * 12;
            const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
            return (
              <p key={i} style={{ color: row.color, fontSize: 28, fontWeight: "bold", opacity, margin: "15px 0" }}>{row.em}</p>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 8: ARBITRAJE GEOGRAFICO ============
const Scene8Arbitrage: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const title = spring({ frame, fps, config: { damping: 12 } });
  const sf = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });
  const col = interpolate(frame, [60, 80], [0, 1], { extrapolateRight: "clamp" });
  const conclusion = interpolate(frame, [110, 130], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center" }}>
        <h2 style={{ color: colors.text, fontSize: 56, marginBottom: 60, transform: `scale(${title})` }}>
          <span style={{ color: colors.accent }}>$0.50</span> USD
        </h2>

        <div style={{ display: "flex", gap: 100, justifyContent: "center", marginBottom: 60 }}>
          <div style={{ opacity: sf, transform: `translateY(${interpolate(sf, [0, 1], [30, 0])}px)` }}>
            <p style={{ color: colors.textMuted, fontSize: 28 }}>San Francisco</p>
            <p style={{ color: colors.danger, fontSize: 48 }}>Ni un cafe</p>
          </div>

          <div style={{ opacity: col, transform: `translateY(${interpolate(col, [0, 1], [30, 0])}px)` }}>
            <p style={{ color: colors.textMuted, fontSize: 28 }}>Colombia</p>
            <p style={{ color: colors.success, fontSize: 48, fontWeight: "bold" }}>$2,000 COP</p>
          </div>
        </div>

        <p style={{ color: colors.text, fontSize: 32, opacity: conclusion, maxWidth: 1100 }}>
          Los agentes no distinguen entre <span style={{ color: colors.secondary }}>Manhattan</span> y <span style={{ color: colors.accent }}>Medellin</span>.
        </p>
        <p style={{ color: colors.primary, fontSize: 36, marginTop: 20, opacity: conclusion, fontWeight: "bold" }}>
          Arbitraje geografico democratizado.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 9: STACK TECNOLOGICO ============
const Scene9Stack: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const items = [
    { icon: "⚡", name: "x402", desc: "Pagos HTTP" },
    { icon: "🔄", name: "x402r", desc: "Refunds auto" },
    { icon: "🌊", name: "Superfluid", desc: "Streaming" },
    { icon: "🆔", name: "ERC-8004", desc: "Reputacion" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <h2 style={{ color: colors.text, fontSize: 48, marginBottom: 20 }}>Los rieles ya existen</h2>
      <p style={{ color: colors.success, fontSize: 28, marginBottom: 50 }}>
        17 redes mainnet • Live en produccion
      </p>
      <div style={{ display: "flex", gap: 30 }}>
        {items.map((item, i) => {
          const delay = i * 12;
          const scale = spring({ frame: frame - delay, fps, config: { damping: 12 } });
          return (
            <div key={i} style={{ backgroundColor: "#1F1F23", padding: "30px 40px", borderRadius: 16, textAlign: "center", transform: `scale(${Math.max(0, scale)})`, border: `2px solid ${colors.primary}40` }}>
              <span style={{ fontSize: 48 }}>{item.icon}</span>
              <h3 style={{ color: colors.primary, fontSize: 28, marginTop: 15, marginBottom: 8 }}>{item.name}</h3>
              <p style={{ color: colors.textMuted, fontSize: 18, margin: 0 }}>{item.desc}</p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 10: ROBOTS ============
const Scene10Robots: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12 } });
  const fadeIn = interpolate(frame, [40, 60], [0, 1], { extrapolateRight: "clamp" });
  const mining = interpolate(frame, [80, 100], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center" }}>
        <h2 style={{ color: colors.text, fontSize: 48, marginBottom: 30, transform: `scale(${scale})` }}>
          Por que <span style={{ color: colors.accent }}>"Universal"</span>
        </h2>
        <p style={{ color: colors.textMuted, fontSize: 32, opacity: fadeIn, marginBottom: 40 }}>
          Humanos hoy. <span style={{ color: colors.secondary }}>Robots manana.</span>
        </p>
        <div style={{ display: "flex", gap: 60, justifyContent: "center", marginBottom: 40, opacity: fadeIn }}>
          <div style={{ textAlign: "center" }}>
            <span style={{ fontSize: 64 }}>🤖</span>
            <p style={{ color: colors.text, fontSize: 24 }}>Hardware: $20-30K</p>
          </div>
          <div style={{ textAlign: "center" }}>
            <span style={{ fontSize: 64 }}>💰</span>
            <p style={{ color: colors.success, fontSize: 24 }}>$60-200/dia</p>
          </div>
          <div style={{ textAlign: "center" }}>
            <span style={{ fontSize: 64 }}>📈</span>
            <p style={{ color: colors.accent, fontSize: 24 }}>ROI: 3-10 meses</p>
          </div>
        </div>
        <p style={{ color: colors.primary, fontSize: 36, fontWeight: "bold", opacity: mining }}>
          Es como mining, pero de trabajo fisico.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ ESCENA 11: CTA ============
const Scene11CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = Math.sin(frame * 0.12) * 0.03 + 1;
  const fadeIn = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const line2 = interpolate(frame, [40, 60], [0, 1], { extrapolateRight: "clamp" });
  const handle = interpolate(frame, [80, 100], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, justifyContent: "center", alignItems: "center", background: `radial-gradient(circle at center, ${colors.primary}20, ${colors.bg})` }}>
      <div style={{ textAlign: "center", transform: `scale(${pulse})` }}>
        <h1 style={{ color: colors.text, fontSize: 48, marginBottom: 30, opacity: fadeIn }}>
          Si llegaste hasta aqui,
        </h1>
        <h1 style={{ color: colors.accent, fontSize: 52, marginBottom: 30, opacity: line2 }}>
          ya ves lo que nosotros vemos.
        </h1>
        <p style={{ color: colors.text, fontSize: 36, marginBottom: 50, opacity: line2 }}>
          Los rieles existen. Ahora construimos el puente.
        </p>
        <p style={{ color: colors.primary, fontSize: 64, fontWeight: "bold", opacity: handle }}>@UltravioletaDAO</p>
      </div>
    </AbsoluteFill>
  );
};

// ============ VIDEO PRINCIPAL V34 ============
export const EMV34: React.FC = () => {
  const { fps } = useVideoConfig();

  const scenes = [
    { component: Scene1Hook, duration: 6 },
    { component: Scene2Title, duration: 7 },
    { component: Scene3Davos, duration: 14 },
    { component: Scene4SiliconCarbon, duration: 12 },
    { component: Scene5Problem, duration: 10 },
    { component: Scene6Solution, duration: 10 },
    { component: Scene7Comparison, duration: 10 },
    { component: Scene8Arbitrage, duration: 12 },
    { component: Scene9Stack, duration: 8 },
    { component: Scene10Robots, duration: 8 },
    { component: Scene11CTA, duration: 10 },
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
