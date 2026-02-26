import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";

// ─── Design System ───────────────────────────────────────────────────────────

const c = {
  bg: "#09090B",
  surface: "#18181B",
  surfaceLight: "#27272A",
  violet: "#8B5CF6",
  violetGlow: "#7C3AED",
  cyan: "#06B6D4",
  amber: "#F59E0B",
  green: "#10B981",
  red: "#EF4444",
  white: "#FAFAFA",
  muted: "#A1A1AA",
  dim: "#71717A",
};

const font = {
  display: "'Inter', 'SF Pro Display', system-ui, sans-serif",
  mono: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
};

// ─── Animation Helpers ───────────────────────────────────────────────────────

const fadeUp = (frame: number, fps: number, delay = 0) => {
  const p = spring({ frame: frame - delay, fps, config: { damping: 100, stiffness: 200 } });
  return {
    opacity: p,
    transform: `translateY(${interpolate(p, [0, 1], [50, 0])}px)`,
  };
};

const scaleIn = (frame: number, fps: number, delay = 0) => {
  const p = spring({ frame: frame - delay, fps, config: { damping: 12, stiffness: 120 } });
  return {
    opacity: Math.min(p * 2, 1),
    transform: `scale(${interpolate(p, [0, 1], [0.8, 1])})`,
  };
};

const countUp = (frame: number, fps: number, target: number, duration = 45, delay = 0) => {
  const p = interpolate(frame - delay, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return Math.round(p * target);
};

const typewriter = (frame: number, fps: number, text: string, delay = 0, speed = 20) => {
  const f = Math.max(0, frame - delay);
  return text.slice(0, Math.floor((f / fps) * speed));
};

// ─── Shared Components ───────────────────────────────────────────────────────

const GlowDot: React.FC<{ color: string; size?: number; x: string; y: string; delay?: number }> = ({
  color, size = 400, x, y, delay = 0,
}) => {
  const frame = useCurrentFrame();
  const pulse = Math.sin((frame + delay) * 0.03) * 0.15 + 0.85;
  return (
    <div style={{
      position: "absolute", left: x, top: y,
      width: size, height: size, borderRadius: "50%",
      background: `radial-gradient(circle, ${color}18 0%, transparent 70%)`,
      transform: `scale(${pulse})`, pointerEvents: "none",
    }} />
  );
};

const Badge: React.FC<{ children: React.ReactNode; color?: string }> = ({
  children, color = c.violet,
}) => (
  <span style={{
    display: "inline-block", padding: "8px 20px", borderRadius: 8,
    backgroundColor: `${color}20`, border: `1px solid ${color}40`,
    color, fontSize: 18, fontFamily: font.display, fontWeight: 600,
    letterSpacing: 1,
  }}>
    {children}
  </span>
);

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 1 — Hook: Mobile Notification (5s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene1Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const slideIn = spring({ frame, fps, config: { damping: 14, stiffness: 100 } });
  const pulse = Math.sin(frame * 0.08) * 0.02 + 1;
  const badgeFade = interpolate(frame, [60, 80], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center" }}>
      <GlowDot color={c.violet} x="15%" y="20%" />
      <GlowDot color={c.cyan} x="75%" y="60%" delay={40} />

      <div style={{
        transform: `translateY(${interpolate(slideIn, [0, 1], [80, 0])}px) scale(${pulse})`,
        backgroundColor: c.surface, borderRadius: 24, padding: "40px 56px",
        maxWidth: 800, border: `1px solid ${c.violet}30`,
        boxShadow: `0 0 80px ${c.violet}15, 0 20px 60px rgba(0,0,0,0.5)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: `linear-gradient(135deg, ${c.violet}, ${c.cyan})`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 20, color: c.white, fontWeight: 700, fontFamily: font.display,
          }}>EM</div>
          <span style={{ color: c.muted, fontSize: 20, fontFamily: font.display }}>
            Execution Market
          </span>
          <span style={{ color: c.dim, fontSize: 16, fontFamily: font.display, marginLeft: "auto" }}>
            ahora
          </span>
        </div>
        <p style={{
          color: c.white, fontSize: 28, lineHeight: 1.6, margin: 0,
          fontFamily: font.display, fontWeight: 500,
        }}>
          Nueva tarea cerca de ti:{" "}
          <span style={{ color: c.amber }}>Verificar cartel de 'Se Renta'</span>
        </p>
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          marginTop: 28, paddingTop: 24, borderTop: `1px solid ${c.surfaceLight}`,
        }}>
          <span style={{ color: c.green, fontSize: 48, fontWeight: 700, fontFamily: font.display }}>
            $3 USDC
          </span>
          <span style={{ color: c.muted, fontSize: 20, fontFamily: font.display }}>
            Pago instantaneo on-chain
          </span>
        </div>
      </div>

      <div style={{
        position: "absolute", bottom: 60,
        opacity: badgeFade, transform: `translateY(${interpolate(badgeFade, [0, 1], [20, 0])}px)`,
      }}>
        <Badge>LIVE ON MAINNET</Badge>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 2 — The Problem (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene2Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const l1 = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" });
  const l2 = interpolate(frame, [50, 75], [0, 1], { extrapolateRight: "clamp" });
  const l3 = interpolate(frame, [100, 125], [0, 1], { extrapolateRight: "clamp" });
  const l4 = interpolate(frame, [150, 175], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 100 }}>
      <GlowDot color={c.red} x="50%" y="30%" size={600} />
      <div style={{ textAlign: "center", maxWidth: 1200, zIndex: 1 }}>
        <h2 style={{
          color: c.white, fontSize: 56, fontWeight: 700, marginBottom: 48,
          fontFamily: font.display, opacity: l1,
          transform: `translateY(${interpolate(l1, [0, 1], [30, 0])}px)`,
        }}>
          Los agentes de IA pueden <span style={{ color: c.cyan }}>pensar</span>.
        </h2>
        <h2 style={{
          color: c.white, fontSize: 56, fontWeight: 700, marginBottom: 48,
          fontFamily: font.display, opacity: l2,
          transform: `translateY(${interpolate(l2, [0, 1], [30, 0])}px)`,
        }}>
          Pero no pueden <span style={{ color: c.amber }}>estar ahi</span>.
        </h2>
        <p style={{
          color: c.muted, fontSize: 30, fontFamily: font.display, lineHeight: 1.6,
          opacity: l3, transform: `translateY(${interpolate(l3, [0, 1], [20, 0])}px)`,
        }}>
          No pueden cruzar la calle. No pueden firmar un documento.
          <br />No pueden tomar una foto. No pueden ser testigos.
        </p>
        <p style={{
          color: c.green, fontSize: 52, fontWeight: 700, marginTop: 50,
          fontFamily: font.display, opacity: l4,
          transform: `scale(${interpolate(l4, [0, 1], [0.9, 1])})`,
        }}>
          Tu si.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 3 — The Gap (7s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene3Gap: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const num = countUp(frame, fps, 44, 60, 20);
  const line2 = interpolate(frame, [80, 110], [0, 1], { extrapolateRight: "clamp" });
  const line3 = interpolate(frame, [130, 160], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GlowDot color={c.amber} x="50%" y="40%" size={700} />
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <p style={{ color: c.muted, fontSize: 22, fontFamily: font.display, letterSpacing: 3, marginBottom: 20, ...fadeUp(frame, fps, 0) }}>
          GARTNER 2026
        </p>
        <div style={{ ...scaleIn(frame, fps, 10) }}>
          <span style={{
            color: c.white, fontSize: 140, fontWeight: 800, fontFamily: font.display,
            background: `linear-gradient(135deg, ${c.amber}, ${c.green})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            ${num}T
          </span>
        </div>
        <p style={{
          color: c.white, fontSize: 36, fontFamily: font.display, fontWeight: 500,
          marginTop: 10, opacity: line2,
          transform: `translateY(${interpolate(line2, [0, 1], [20, 0])}px)`,
        }}>
          en economia de agentes de IA para 2028
        </p>
        <p style={{
          color: c.red, fontSize: 32, fontFamily: font.display, fontWeight: 600,
          marginTop: 40, opacity: line3,
          transform: `translateY(${interpolate(line3, [0, 1], [20, 0])}px)`,
        }}>
          Sin capa de ejecucion fisica.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 4 — The Solution: EXECUTION MARKET (7s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene4Solution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 10, stiffness: 80 } });
  const tagline = interpolate(frame, [40, 65], [0, 1], { extrapolateRight: "clamp" });
  const sub = interpolate(frame, [80, 105], [0, 1], { extrapolateRight: "clamp" });

  const glowPulse = Math.sin(frame * 0.06) * 0.3 + 0.7;

  return (
    <AbsoluteFill style={{
      backgroundColor: c.bg, justifyContent: "center", alignItems: "center",
      background: `radial-gradient(ellipse at center, ${c.violetGlow}12 0%, ${c.bg} 70%)`,
    }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{
          color: c.white, fontSize: 100, fontWeight: 800,
          fontFamily: font.display, letterSpacing: -2,
          transform: `scale(${logoScale})`,
          textShadow: `0 0 ${80 * glowPulse}px ${c.violet}60`,
          marginBottom: 24,
        }}>
          EXECUTION<br />MARKET
        </h1>
        <p style={{
          color: c.amber, fontSize: 28, fontWeight: 600,
          fontFamily: font.display, letterSpacing: 6, opacity: tagline,
          transform: `translateY(${interpolate(tagline, [0, 1], [15, 0])}px)`,
        }}>
          UNIVERSAL EXECUTION LAYER
        </p>
        <p style={{
          color: c.muted, fontSize: 26, fontFamily: font.display,
          marginTop: 36, maxWidth: 800, lineHeight: 1.5, opacity: sub,
          transform: `translateY(${interpolate(sub, [0, 1], [15, 0])}px)`,
        }}>
          Infraestructura para que agentes de IA contraten
          <br />
          <span style={{ color: c.cyan }}>ejecutores</span> — humanos hoy, robots manana.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 5 — How It Works (9s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene5Flow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const steps = [
    { icon: "1", label: "Agente publica tarea", sub: "via MCP / A2A / REST", color: c.violet },
    { icon: "2", label: "Escrow on-chain", sub: "Fondos bloqueados (gasless)", color: c.cyan },
    { icon: "3", label: "Ejecutor completa", sub: "Evidencia verificable", color: c.amber },
    { icon: "4", label: "Pago instantaneo", sub: "Liberacion trustless", color: c.green },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <h2 style={{
        color: c.white, fontSize: 44, fontWeight: 700, fontFamily: font.display,
        marginBottom: 60, textAlign: "center", ...fadeUp(frame, fps, 0),
      }}>
        Como funciona
      </h2>
      <div style={{ display: "flex", gap: 32, alignItems: "flex-start" }}>
        {steps.map((step, i) => {
          const delay = 20 + i * 25;
          const anim = fadeUp(frame, fps, delay);
          const arrowFade = interpolate(frame, [delay + 15, delay + 30], [0, 1], { extrapolateRight: "clamp" });

          return (
            <React.Fragment key={i}>
              <div style={{
                textAlign: "center", width: 280, ...anim,
              }}>
                <div style={{
                  width: 72, height: 72, borderRadius: 20,
                  background: `linear-gradient(135deg, ${step.color}, ${step.color}90)`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  margin: "0 auto 20px", fontSize: 32, fontWeight: 800,
                  color: c.white, fontFamily: font.display,
                  boxShadow: `0 0 40px ${step.color}30`,
                }}>
                  {step.icon}
                </div>
                <p style={{
                  color: c.white, fontSize: 22, fontWeight: 600,
                  fontFamily: font.display, marginBottom: 8,
                }}>
                  {step.label}
                </p>
                <p style={{
                  color: c.muted, fontSize: 16, fontFamily: font.display,
                }}>
                  {step.sub}
                </p>
              </div>
              {i < steps.length - 1 && (
                <div style={{
                  color: c.dim, fontSize: 36, alignSelf: "center",
                  marginTop: -30, opacity: arrowFade,
                  fontFamily: font.display,
                }}>
                  &rarr;
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 6 — Live on 8 Chains (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene6Chains: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const chains = [
    { name: "Base", color: "#0052FF" },
    { name: "Ethereum", color: "#627EEA" },
    { name: "Polygon", color: "#8247E5" },
    { name: "Arbitrum", color: "#28A0F0" },
    { name: "Avalanche", color: "#E84142" },
    { name: "Optimism", color: "#FF0420" },
    { name: "Celo", color: "#35D07F" },
    { name: "Monad", color: "#836EF9" },
  ];

  const titleAnim = fadeUp(frame, fps, 0);
  const counter = countUp(frame, fps, 8, 40, 30);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GlowDot color={c.violet} x="50%" y="50%" size={800} />

      <div style={{ textAlign: "center", zIndex: 1 }}>
        <div style={titleAnim}>
          <p style={{ color: c.muted, fontSize: 20, fontFamily: font.display, letterSpacing: 3, marginBottom: 8 }}>
            PRODUCCION - MAINNET
          </p>
          <h2 style={{ color: c.white, fontSize: 80, fontWeight: 800, fontFamily: font.display, margin: 0 }}>
            <span style={{ color: c.green }}>{counter}</span> Chains
          </h2>
          <p style={{ color: c.muted, fontSize: 22, fontFamily: font.display, marginTop: 8 }}>
            Escrow trustless + pagos gasless en cada una
          </p>
        </div>

        <div style={{
          display: "flex", flexWrap: "wrap", gap: 16, justifyContent: "center",
          marginTop: 50, maxWidth: 900,
        }}>
          {chains.map((chain, i) => {
            const delay = 50 + i * 12;
            const anim = scaleIn(frame, fps, delay);
            return (
              <div key={i} style={{
                padding: "14px 28px", borderRadius: 14,
                backgroundColor: `${chain.color}15`,
                border: `1px solid ${chain.color}40`,
                ...anim,
              }}>
                <span style={{
                  color: chain.color, fontSize: 20, fontWeight: 600,
                  fontFamily: font.display,
                }}>
                  {chain.name}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 7 — The Stack (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene7Stack: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const items = [
    { name: "x402r Escrow", desc: "Bloqueo + liberacion on-chain", sub: "Gasless via Facilitador", color: c.violet },
    { name: "ERC-8004", desc: "Identidad on-chain", sub: "Reputacion verificable", color: c.cyan },
    { name: "MCP + A2A", desc: "Protocolos de agentes", sub: "Anthropic + Google", color: c.amber },
    { name: "EIP-8128", desc: "Auth criptografica", sub: "Agente firma, chain verifica", color: c.green },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <h2 style={{
        color: c.white, fontSize: 44, fontWeight: 700, fontFamily: font.display,
        marginBottom: 16, ...fadeUp(frame, fps, 0),
      }}>
        Construido sobre estandares abiertos
      </h2>
      <p style={{
        color: c.muted, fontSize: 22, fontFamily: font.display, marginBottom: 50,
        ...fadeUp(frame, fps, 10),
      }}>
        No reinventamos la rueda — la conectamos
      </p>

      <div style={{ display: "flex", gap: 24 }}>
        {items.map((item, i) => {
          const delay = 20 + i * 18;
          return (
            <div key={i} style={{
              width: 280, padding: "32px 28px", borderRadius: 20,
              backgroundColor: c.surface, border: `1px solid ${item.color}25`,
              textAlign: "center",
              boxShadow: `0 0 40px ${item.color}08`,
              ...fadeUp(frame, fps, delay),
            }}>
              <h3 style={{
                color: item.color, fontSize: 24, fontWeight: 700,
                fontFamily: font.display, marginBottom: 12,
              }}>
                {item.name}
              </h3>
              <p style={{
                color: c.white, fontSize: 18, fontFamily: font.display,
                marginBottom: 8, fontWeight: 500,
              }}>
                {item.desc}
              </p>
              <p style={{
                color: c.dim, fontSize: 15, fontFamily: font.display,
              }}>
                {item.sub}
              </p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 8 — Traction (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene8Traction: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const stats = [
    { value: 8, label: "chains live", suffix: "", color: c.green },
    { value: 24, label: "agentes activos", suffix: "", color: c.violet },
    { value: 950, label: "tests passing", suffix: "+", color: c.cyan },
    { value: 100, label: "Golden Flow", suffix: "%", color: c.amber },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GlowDot color={c.green} x="50%" y="40%" size={600} />

      <div style={{ textAlign: "center", zIndex: 1 }}>
        <p style={{
          color: c.muted, fontSize: 20, fontFamily: font.display, letterSpacing: 3,
          marginBottom: 10, ...fadeUp(frame, fps, 0),
        }}>
          TRACCION
        </p>
        <h2 style={{
          color: c.white, fontSize: 52, fontWeight: 700, fontFamily: font.display,
          marginBottom: 50, ...fadeUp(frame, fps, 5),
        }}>
          No es un whitepaper. <span style={{ color: c.green }}>Esta en produccion.</span>
        </h2>

        <div style={{ display: "flex", gap: 60, justifyContent: "center" }}>
          {stats.map((stat, i) => {
            const delay = 25 + i * 18;
            const num = countUp(frame, fps, stat.value, 40, delay);
            return (
              <div key={i} style={{ textAlign: "center", ...fadeUp(frame, fps, delay) }}>
                <div style={{
                  fontSize: 72, fontWeight: 800, fontFamily: font.display,
                  color: stat.color,
                }}>
                  {num}{stat.suffix}
                </div>
                <div style={{
                  fontSize: 18, color: c.muted, fontFamily: font.display,
                  marginTop: 8,
                }}>
                  {stat.label}
                </div>
              </div>
            );
          })}
        </div>

        <div style={{
          marginTop: 50, display: "flex", gap: 16, justifyContent: "center",
          ...fadeUp(frame, fps, 100),
        }}>
          <Badge color={c.green}>ERC-8004 Identity</Badge>
          <Badge color={c.cyan}>Gasless Payments</Badge>
          <Badge color={c.amber}>Trustless Escrow</Badge>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 9 — Not MTurk (7s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene9NotMturk: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const rows = [
    { label: "Cliente", old: "Humanos", em: "Agentes de IA" },
    { label: "Pagos", old: "Semanas", em: "Instantaneo on-chain" },
    { label: "Escrow", old: "Confianza", em: "Trustless on-chain" },
    { label: "Identidad", old: "Email + password", em: "ERC-8004 on-chain" },
    { label: "Minimo", old: "$5+", em: "$0.10" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <h2 style={{
        color: c.white, fontSize: 44, fontWeight: 700, fontFamily: font.display,
        marginBottom: 50, ...fadeUp(frame, fps, 0),
      }}>
        &ldquo;No es esto como <span style={{ color: c.red }}>MTurk</span>?&rdquo;&ensp;No.
      </h2>

      <div style={{ width: 900 }}>
        {/* Header */}
        <div style={{
          display: "flex", padding: "16px 0", borderBottom: `1px solid ${c.surfaceLight}`,
          ...fadeUp(frame, fps, 10),
        }}>
          <div style={{ flex: 1 }} />
          <div style={{ flex: 1, color: c.red, fontSize: 18, fontWeight: 600, fontFamily: font.display, textAlign: "center" }}>
            Gig Economy
          </div>
          <div style={{ flex: 1, color: c.green, fontSize: 18, fontWeight: 600, fontFamily: font.display, textAlign: "center" }}>
            Execution Market
          </div>
        </div>

        {rows.map((row, i) => {
          const delay = 20 + i * 16;
          return (
            <div key={i} style={{
              display: "flex", padding: "18px 0",
              borderBottom: i < rows.length - 1 ? `1px solid ${c.surfaceLight}40` : "none",
              ...fadeUp(frame, fps, delay),
            }}>
              <div style={{ flex: 1, color: c.muted, fontSize: 20, fontFamily: font.display, fontWeight: 500 }}>
                {row.label}
              </div>
              <div style={{ flex: 1, color: c.dim, fontSize: 20, fontFamily: font.display, textAlign: "center" }}>
                {row.old}
              </div>
              <div style={{ flex: 1, color: c.white, fontSize: 20, fontFamily: font.display, fontWeight: 600, textAlign: "center" }}>
                {row.em}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 10 — Geographic Arbitrage (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene10Arbitrage: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sf = fadeUp(frame, fps, 30);
  const col = fadeUp(frame, fps, 60);
  const conclusion = fadeUp(frame, fps, 120);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GlowDot color={c.amber} x="30%" y="40%" />
      <GlowDot color={c.green} x="70%" y="40%" delay={30} />

      <div style={{ textAlign: "center", zIndex: 1 }}>
        <h2 style={{
          color: c.white, fontSize: 48, fontWeight: 700, fontFamily: font.display,
          marginBottom: 60, ...fadeUp(frame, fps, 0),
        }}>
          Arbitraje geografico
        </h2>

        <div style={{ display: "flex", gap: 120, justifyContent: "center", marginBottom: 60 }}>
          <div style={sf}>
            <p style={{ color: c.dim, fontSize: 22, fontFamily: font.display, marginBottom: 12 }}>
              San Francisco
            </p>
            <p style={{ color: c.red, fontSize: 56, fontWeight: 700, fontFamily: font.display }}>
              $0.50
            </p>
            <p style={{ color: c.dim, fontSize: 20, fontFamily: font.display }}>
              Ni un cafe
            </p>
          </div>
          <div style={{
            width: 2, backgroundColor: c.surfaceLight, alignSelf: "stretch",
            opacity: interpolate(frame, [40, 60], [0, 0.5], { extrapolateRight: "clamp" }),
          }} />
          <div style={col}>
            <p style={{ color: c.dim, fontSize: 22, fontFamily: font.display, marginBottom: 12 }}>
              Colombia
            </p>
            <p style={{ color: c.green, fontSize: 56, fontWeight: 700, fontFamily: font.display }}>
              $2,200 COP
            </p>
            <p style={{ color: c.green, fontSize: 20, fontFamily: font.display }}>
              Un almuerzo completo
            </p>
          </div>
        </div>

        <div style={conclusion}>
          <p style={{ color: c.white, fontSize: 28, fontFamily: font.display, maxWidth: 900, lineHeight: 1.5 }}>
            Los agentes no distinguen entre{" "}
            <span style={{ color: c.cyan }}>Manhattan</span> y{" "}
            <span style={{ color: c.amber }}>Medellin</span>.
          </p>
          <p style={{
            color: c.violet, fontSize: 32, fontWeight: 600, fontFamily: font.display, marginTop: 16,
          }}>
            La geografia deja de ser barrera.
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 11 — Vision: Humans Today, Robots Tomorrow (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene11Vision: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const title = fadeUp(frame, fps, 0);
  const humans = fadeUp(frame, fps, 40);
  const robots = fadeUp(frame, fps, 80);
  const mining = fadeUp(frame, fps, 140);

  return (
    <AbsoluteFill style={{
      backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80,
      background: `radial-gradient(ellipse at center, ${c.violet}08 0%, ${c.bg} 60%)`,
    }}>
      <div style={{ textAlign: "center", maxWidth: 1100 }}>
        <h2 style={{
          color: c.white, fontSize: 52, fontWeight: 700, fontFamily: font.display,
          marginBottom: 50, ...title,
        }}>
          Por que <span style={{ color: c.amber }}>&ldquo;Universal&rdquo;</span>
        </h2>

        <div style={{ display: "flex", gap: 80, justifyContent: "center", marginBottom: 50 }}>
          <div style={{ textAlign: "center", ...humans }}>
            <div style={{
              width: 100, height: 100, borderRadius: 24,
              backgroundColor: `${c.cyan}15`, border: `1px solid ${c.cyan}30`,
              display: "flex", alignItems: "center", justifyContent: "center",
              margin: "0 auto 16px", fontSize: 48,
            }}>
              H
            </div>
            <p style={{ color: c.cyan, fontSize: 28, fontWeight: 600, fontFamily: font.display }}>
              Humanos hoy
            </p>
            <p style={{ color: c.muted, fontSize: 18, fontFamily: font.display, marginTop: 8, maxWidth: 240 }}>
              Verifican, compran, firman, entregan
            </p>
          </div>

          <div style={{
            color: c.dim, fontSize: 48, alignSelf: "center",
            opacity: interpolate(frame, [70, 90], [0, 1], { extrapolateRight: "clamp" }),
          }}>
            +
          </div>

          <div style={{ textAlign: "center", ...robots }}>
            <div style={{
              width: 100, height: 100, borderRadius: 24,
              backgroundColor: `${c.green}15`, border: `1px solid ${c.green}30`,
              display: "flex", alignItems: "center", justifyContent: "center",
              margin: "0 auto 16px", fontSize: 48,
            }}>
              R
            </div>
            <p style={{ color: c.green, fontSize: 28, fontWeight: 600, fontFamily: font.display }}>
              Robots manana
            </p>
            <p style={{ color: c.muted, fontSize: 18, fontFamily: font.display, marginTop: 8, maxWidth: 240 }}>
              Hardware: $20-30K, ROI: 3-10 meses
            </p>
          </div>
        </div>

        <div style={mining}>
          <p style={{
            color: c.violet, fontSize: 36, fontWeight: 700, fontFamily: font.display,
          }}>
            Es como mining, pero de trabajo fisico.
          </p>
          <p style={{
            color: c.muted, fontSize: 22, fontFamily: font.display, marginTop: 12,
          }}>
            El protocolo no le importa quien ejecuta. Le importa que se ejecute, se pague, y se verifique.
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 12 — CTA (13s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene12CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pulse = Math.sin(frame * 0.06) * 0.02 + 1;
  const glowPulse = Math.sin(frame * 0.04) * 0.4 + 0.6;

  const hook = fadeUp(frame, fps, 0);
  const vision = fadeUp(frame, fps, 40);
  const url = fadeUp(frame, fps, 80);
  const handle = fadeUp(frame, fps, 110);
  const built = fadeUp(frame, fps, 150);

  return (
    <AbsoluteFill style={{
      backgroundColor: c.bg, justifyContent: "center", alignItems: "center",
      background: `radial-gradient(ellipse at center, ${c.violetGlow}15 0%, ${c.bg} 65%)`,
    }}>
      <div style={{ textAlign: "center", transform: `scale(${pulse})` }}>
        <p style={{
          color: c.white, fontSize: 40, fontFamily: font.display, fontWeight: 500,
          marginBottom: 16, ...hook,
        }}>
          Si llegaste hasta aqui,
        </p>
        <p style={{
          color: c.amber, fontSize: 48, fontFamily: font.display, fontWeight: 700,
          marginBottom: 50, ...vision,
        }}>
          ya ves lo que nosotros vemos.
        </p>

        <div style={url}>
          <p style={{
            color: c.white, fontSize: 64, fontWeight: 800, fontFamily: font.display,
            textShadow: `0 0 ${60 * glowPulse}px ${c.violet}50`,
            marginBottom: 12,
          }}>
            execution.market
          </p>
        </div>

        <div style={handle}>
          <p style={{
            color: c.violet, fontSize: 36, fontFamily: font.display, fontWeight: 600,
            marginBottom: 40,
          }}>
            @ExecutionMarket
          </p>
        </div>

        <div style={{
          display: "flex", gap: 24, justifyContent: "center", ...built,
        }}>
          <Badge color={c.muted}>Agent #2106 on Base</Badge>
          <Badge color={c.muted}>Ultravioleta DAO</Badge>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  MAIN COMPOSITION
// ═════════════════════════════════════════════════════════════════════════════

export const EMPitch: React.FC = () => {
  const { fps } = useVideoConfig();

  const scenes = [
    { component: Scene1Hook, duration: 5 },
    { component: Scene2Problem, duration: 8 },
    { component: Scene3Gap, duration: 7 },
    { component: Scene4Solution, duration: 7 },
    { component: Scene5Flow, duration: 9 },
    { component: Scene6Chains, duration: 8 },
    { component: Scene7Stack, duration: 8 },
    { component: Scene8Traction, duration: 8 },
    { component: Scene9NotMturk, duration: 7 },
    { component: Scene10Arbitrage, duration: 8 },
    { component: Scene11Vision, duration: 8 },
    { component: Scene12CTA, duration: 13 },
  ];

  // Total: 96 seconds

  let currentFrame = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg }}>
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
