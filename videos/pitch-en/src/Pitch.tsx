import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";

// ─── Design System — Matches execution.market web aesthetic ─────────────────
//     Monochromatic. Roboto Mono. Square corners. Terminal feel.

const c = {
  bg: "#000000",
  surface: "#18181b",
  surfaceLight: "#27272a",
  border: "#3f3f46",
  accent: "#52525b",
  white: "#fafafa",
  muted: "#a1a1aa",
  dim: "#71717a",
  dark: "#09090b",
  // Functional colors — used sparingly for data only (same as dashboard status colors)
  green: "#10b981",
  greenDim: "#065f46",
};

const mono = "'Roboto Mono', 'JetBrains Mono', 'SF Mono', 'Menlo', monospace";

// ─── Animation Helpers ───────────────────────────────────────────────────────

const fadeUp = (frame: number, fps: number, delay = 0) => {
  const p = spring({ frame: frame - delay, fps, config: { damping: 100, stiffness: 200 } });
  return {
    opacity: p,
    transform: `translateY(${interpolate(p, [0, 1], [40, 0])}px)`,
  };
};

const scaleIn = (frame: number, fps: number, delay = 0) => {
  const p = spring({ frame: frame - delay, fps, config: { damping: 14, stiffness: 120 } });
  return {
    opacity: Math.min(p * 2, 1),
    transform: `scale(${interpolate(p, [0, 1], [0.85, 1])})`,
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

/** Scanline overlay — matches the landing page effect */
const Scanlines: React.FC = () => (
  <div style={{
    position: "absolute", top: 0, left: 0, width: "100%", height: "100%",
    pointerEvents: "none", zIndex: 100,
    background: "repeating-linear-gradient(0deg, rgba(255,255,255,0.02), rgba(255,255,255,0.02) 1px, transparent 1px, transparent 3px)",
  }} />
);

/** Grid background — subtle 24px pattern */
const GridBg: React.FC = () => (
  <div style={{
    position: "absolute", top: 0, left: 0, width: "100%", height: "100%",
    pointerEvents: "none", opacity: 0.03,
    backgroundImage: `linear-gradient(${c.muted} 1px, transparent 1px), linear-gradient(90deg, ${c.muted} 1px, transparent 1px)`,
    backgroundSize: "48px 48px",
  }} />
);

/** EM Logo — real geometric E+M interlock logo from logo.png */
const EMLogo: React.FC<{ size?: number }> = ({ size = 80 }) => (
  <Img src={staticFile("logo.png")} width={size} height={size}
    style={{ objectFit: "contain", filter: "invert(1)" }} />
);

/** Monochrome badge — square corners, subtle border */
const Tag: React.FC<{ children: React.ReactNode; highlight?: boolean }> = ({
  children, highlight = false,
}) => (
  <span style={{
    display: "inline-block", padding: "6px 16px",
    border: `1px solid ${highlight ? c.muted : c.border}`,
    color: highlight ? c.white : c.muted,
    fontSize: 14, fontFamily: mono, fontWeight: 500,
    letterSpacing: 2, textTransform: "uppercase",
  }}>
    {children}
  </span>
);

/** Terminal prompt character */
const Prompt: React.FC = () => (
  <span style={{ color: c.dim, fontFamily: mono }}>&gt; </span>
);

/** Blinking cursor */
const Cursor: React.FC = () => {
  const frame = useCurrentFrame();
  const visible = frame % 21 > 10;
  return (
    <span style={{
      display: "inline-block", width: 12, height: 24,
      backgroundColor: c.white, verticalAlign: "middle",
      marginLeft: 4, opacity: visible ? 1 : 0,
    }} />
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 1 — Hook: Task Notification (5s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene1Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const slideIn = spring({ frame, fps, config: { damping: 14, stiffness: 100 } });
  const badgeFade = interpolate(frame, [80, 100], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center" }}>
      <GridBg />
      <Scanlines />

      <div style={{
        transform: `translateY(${interpolate(slideIn, [0, 1], [60, 0])}px)`,
        backgroundColor: c.dark, padding: "40px 56px",
        maxWidth: 780, width: "100%",
        border: `1px solid ${c.border}`,
        boxShadow: `0 0 40px rgba(0,0,0,0.4)`,
        position: "relative", overflow: "hidden",
      }}>
        {/* Top accent line */}
        <div style={{
          position: "absolute", top: 0, left: 0, width: "100%", height: 2,
          background: `linear-gradient(90deg, ${c.border}, ${c.muted}, ${c.border})`,
        }} />

        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 28 }}>
          <EMLogo size={44} />
          <span style={{ color: c.muted, fontSize: 18, fontFamily: mono, fontWeight: 500 }}>
            Execution Market
          </span>
          <span style={{ color: c.dim, fontSize: 14, fontFamily: mono, marginLeft: "auto" }}>
            now
          </span>
        </div>

        <p style={{
          color: c.white, fontSize: 24, lineHeight: 1.7, margin: 0,
          fontFamily: mono, fontWeight: 500,
        }}>
          New task near you:{" "}
          <span style={{ color: c.white, fontWeight: 700 }}>
            "Verify 'For Rent' sign at 200m"
          </span>
        </p>

        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          marginTop: 28, paddingTop: 24, borderTop: `1px solid ${c.border}`,
        }}>
          <span style={{ color: c.white, fontSize: 42, fontWeight: 700, fontFamily: mono }}>
            $3 USDC
          </span>
          <span style={{ color: c.dim, fontSize: 16, fontFamily: mono }}>
            Instant on-chain payment
          </span>
        </div>
      </div>

      <div style={{
        position: "absolute", bottom: 60,
        opacity: badgeFade, transform: `translateY(${interpolate(badgeFade, [0, 1], [15, 0])}px)`,
      }}>
        <Tag highlight>LIVE ON MAINNET</Tag>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 2 — The Problem (7s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene2Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const l1 = fadeUp(frame, fps, 0);
  const l2 = fadeUp(frame, fps, 40);
  const l3 = fadeUp(frame, fps, 90);
  const l4 = fadeUp(frame, fps, 130);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 100 }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", maxWidth: 1100, zIndex: 1 }}>
        <h2 style={{
          color: c.white, fontSize: 52, fontWeight: 700, marginBottom: 40,
          fontFamily: mono, ...l1,
        }}>
          AI agents can <span style={{ fontWeight: 700 }}>think</span>.
        </h2>
        <h2 style={{
          color: c.white, fontSize: 52, fontWeight: 700, marginBottom: 48,
          fontFamily: mono, ...l2,
        }}>
          But they can't <span style={{ fontWeight: 700 }}>be there</span>.
        </h2>
        <p style={{
          color: c.dim, fontSize: 24, fontFamily: mono, lineHeight: 1.7,
          ...l3,
        }}>
          They can't cross the street. They can't sign a document.
          <br />They can't take a photo. They can't be a witness.
        </p>
        <p style={{
          color: c.white, fontSize: 48, fontWeight: 700, marginTop: 50,
          fontFamily: mono, ...l4,
        }}>
          You can.
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 3 — The Market Gap (6s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene3Gap: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const num = countUp(frame, fps, 44, 50, 20);
  const line2 = fadeUp(frame, fps, 70);
  const line3 = fadeUp(frame, fps, 120);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <p style={{
          color: c.dim, fontSize: 16, fontFamily: mono, letterSpacing: 4,
          marginBottom: 24, ...fadeUp(frame, fps, 0),
        }}>
          GARTNER 2026
        </p>
        <div style={{ ...scaleIn(frame, fps, 10) }}>
          <span style={{
            color: c.white, fontSize: 140, fontWeight: 700, fontFamily: mono,
            textShadow: `0 0 60px rgba(255,255,255,0.1)`,
          }}>
            ${num}T
          </span>
        </div>
        <p style={{
          color: c.muted, fontSize: 30, fontFamily: mono, fontWeight: 500,
          marginTop: 12, ...line2,
        }}>
          AI agent economy by 2028
        </p>
        <p style={{
          color: c.white, fontSize: 28, fontFamily: mono, fontWeight: 700,
          marginTop: 40, ...line3,
        }}>
          No physical execution layer.
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

  const logoScale = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  const tagline = fadeUp(frame, fps, 50);
  const sub = fadeUp(frame, fps, 90);

  const glowPulse = Math.sin(frame * 0.04) * 0.15 + 0.85;

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center" }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <div style={{
          transform: `scale(${logoScale})`, marginBottom: 32,
          display: "flex", justifyContent: "center",
        }}>
          <EMLogo size={100} />
        </div>
        <h1 style={{
          color: c.white, fontSize: 80, fontWeight: 700,
          fontFamily: mono, letterSpacing: -1,
          transform: `scale(${logoScale})`,
          textShadow: `0 0 ${40 * glowPulse}px rgba(255,255,255,0.08)`,
          marginBottom: 16, lineHeight: 1.1,
        }}>
          EXECUTION
          <br />MARKET
        </h1>
        <div style={tagline}>
          <p style={{
            color: c.muted, fontSize: 18, fontWeight: 500,
            fontFamily: mono, letterSpacing: 8,
          }}>
            UNIVERSAL EXECUTION LAYER
          </p>
        </div>
        <div style={sub}>
          <p style={{
            color: c.dim, fontSize: 22, fontFamily: mono,
            marginTop: 36, maxWidth: 800, lineHeight: 1.6,
          }}>
            Infrastructure for AI agents to hire
            <br />
            <span style={{ color: c.white, fontWeight: 700 }}>executors</span> — humans today, robots tomorrow.
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 5 — How It Works (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene5Flow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const steps = [
    { num: "01", label: "Agent publishes task", sub: "via MCP / A2A / REST" },
    { num: "02", label: "Escrow locks on-chain", sub: "Gasless via Facilitator" },
    { num: "03", label: "Executor completes", sub: "Verifiable evidence" },
    { num: "04", label: "Instant payment", sub: "Trustless release" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <h2 style={{
        color: c.white, fontSize: 36, fontWeight: 700, fontFamily: mono,
        marginBottom: 60, textAlign: "center", letterSpacing: 2, ...fadeUp(frame, fps, 0),
      }}>
        <Prompt />HOW IT WORKS
      </h2>
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        {steps.map((step, i) => {
          const delay = 20 + i * 25;
          const anim = fadeUp(frame, fps, delay);
          const lineFade = interpolate(frame, [delay + 15, delay + 30], [0, 1], { extrapolateRight: "clamp" });

          return (
            <React.Fragment key={i}>
              <div style={{
                textAlign: "center", width: 280,
                backgroundColor: c.dark, border: `1px solid ${c.border}`,
                padding: "32px 24px", position: "relative", ...anim,
              }}>
                {/* Top accent line */}
                <div style={{
                  position: "absolute", top: 0, left: 0, width: "100%", height: 2,
                  backgroundColor: c.muted,
                }} />
                <p style={{
                  color: c.dim, fontSize: 40, fontWeight: 700,
                  fontFamily: mono, marginBottom: 16,
                }}>
                  {step.num}
                </p>
                <p style={{
                  color: c.white, fontSize: 18, fontWeight: 600,
                  fontFamily: mono, marginBottom: 10,
                }}>
                  {step.label}
                </p>
                <p style={{ color: c.dim, fontSize: 14, fontFamily: mono }}>
                  {step.sub}
                </p>
              </div>
              {i < steps.length - 1 && (
                <div style={{
                  color: c.dim, fontSize: 28, alignSelf: "center",
                  marginTop: -10, opacity: lineFade, fontFamily: mono,
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
//  SCENE 6 — Live on 8 Chains (7s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene6Chains: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const chains = [
    "Base", "Ethereum", "Polygon", "Arbitrum",
    "Avalanche", "Optimism", "Celo", "Monad",
  ];

  const counter = countUp(frame, fps, 8, 40, 30);
  const avaxLogoFade = interpolate(frame, [10, 30], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <div style={fadeUp(frame, fps, 0)}>
          <p style={{
            color: c.dim, fontSize: 14, fontFamily: mono, letterSpacing: 4, marginBottom: 12,
          }}>
            PRODUCTION — MAINNET
          </p>
          <h2 style={{
            color: c.white, fontSize: 80, fontWeight: 700, fontFamily: mono, margin: 0,
          }}>
            {counter} Chains
          </h2>
          <p style={{ color: c.dim, fontSize: 18, fontFamily: mono, marginTop: 10 }}>
            Trustless escrow + gasless payments on each
          </p>
        </div>

        <div style={{
          display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center",
          marginTop: 50, maxWidth: 800,
        }}>
          {chains.map((chain, i) => {
            const delay = 50 + i * 10;
            const anim = scaleIn(frame, fps, delay);
            const isAvalanche = chain === "Avalanche";
            return (
              <div key={i} style={{
                padding: "12px 24px",
                border: `1px solid ${isAvalanche ? c.muted : c.border}`,
                backgroundColor: c.dark,
                display: "flex", alignItems: "center", gap: 10,
                ...anim,
              }}>
                {isAvalanche && (
                  <Img src={staticFile("avalanche.png")} width={22} height={22}
                    style={{ objectFit: "contain" }} />
                )}
                <span style={{
                  color: c.white, fontSize: 16, fontWeight: isAvalanche ? 700 : 500,
                  fontFamily: mono,
                }}>
                  {chain}
                </span>
              </div>
            );
          })}
        </div>

        {/* Avalanche callout */}
        <div style={{
          marginTop: 36, display: "flex", alignItems: "center",
          justifyContent: "center", gap: 14,
          opacity: avaxLogoFade,
          transform: `translateY(${interpolate(avaxLogoFade, [0, 1], [12, 0])}px)`,
        }}>
          <Img src={staticFile("avalanche.png")} width={32} height={32}
            style={{ objectFit: "contain" }} />
          <span style={{
            color: c.muted, fontSize: 15, fontFamily: mono, fontWeight: 500,
          }}>
            First deployed on Avalanche C-Chain
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 7 — The Protocol Stack (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene7Stack: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const items = [
    { name: "x402r Escrow", desc: "On-chain lock + release", sub: "Gasless via Facilitator" },
    { name: "ERC-8004", desc: "On-chain identity", sub: "Verifiable reputation" },
    { name: "MCP + A2A", desc: "Agent protocols", sub: "Anthropic + Google" },
    { name: "EIP-8128", desc: "Crypto auth", sub: "Agent signs, chain verifies" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <h2 style={{
        color: c.white, fontSize: 32, fontWeight: 700, fontFamily: mono,
        marginBottom: 12, letterSpacing: 2, ...fadeUp(frame, fps, 0),
      }}>
        <Prompt />BUILT ON OPEN STANDARDS
      </h2>
      <p style={{
        color: c.dim, fontSize: 18, fontFamily: mono, marginBottom: 50,
        ...fadeUp(frame, fps, 10),
      }}>
        We didn't reinvent the wheel — we connected them
      </p>

      <div style={{ display: "flex", gap: 20 }}>
        {items.map((item, i) => {
          const delay = 20 + i * 18;
          return (
            <div key={i} style={{
              width: 270, padding: "28px 24px",
              backgroundColor: c.dark, border: `1px solid ${c.border}`,
              textAlign: "left", position: "relative",
              ...fadeUp(frame, fps, delay),
            }}>
              {/* Top accent */}
              <div style={{
                position: "absolute", top: 0, left: 0, width: "100%", height: 2,
                backgroundColor: c.muted,
              }} />
              <h3 style={{
                color: c.white, fontSize: 18, fontWeight: 700,
                fontFamily: mono, marginBottom: 12,
              }}>
                <Prompt />{item.name}
              </h3>
              <p style={{
                color: c.muted, fontSize: 15, fontFamily: mono,
                marginBottom: 6, lineHeight: 1.5,
              }}>
                {item.desc}
              </p>
              <p style={{ color: c.dim, fontSize: 13, fontFamily: mono }}>
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
//  SCENE 8 — Trustless by Design (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene8Trustless: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const steps = [
    { num: "01", label: "Task published", detail: "Advisory balance check only" },
    { num: "02", label: "Worker assigned", detail: "Escrow locks bounty on-chain" },
    { num: "03", label: "Task approved", detail: "1 TX: atomic split worker + fee" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", zIndex: 1, maxWidth: 1100 }}>
        <div style={fadeUp(frame, fps, 0)}>
          <Tag>FASE 5 — CREDIT CARD MODEL</Tag>
        </div>
        <h2 style={{
          color: c.white, fontSize: 44, fontWeight: 700, fontFamily: mono,
          marginTop: 24, marginBottom: 12, ...fadeUp(frame, fps, 8),
        }}>
          Trustless by design
        </h2>
        <p style={{
          color: c.dim, fontSize: 18, fontFamily: mono, lineHeight: 1.6,
          marginBottom: 50, ...fadeUp(frame, fps, 16),
        }}>
          Platform never touches funds. Escrow pays worker directly.
          <br />Fee split is atomic on-chain.
        </p>

        <div style={{ display: "flex", gap: 32, justifyContent: "center" }}>
          {steps.map((step, i) => {
            const delay = 35 + i * 25;
            const arrowFade = interpolate(frame, [delay + 15, delay + 28], [0, 1], { extrapolateRight: "clamp" });
            return (
              <React.Fragment key={i}>
                <div style={{
                  textAlign: "center", width: 280,
                  backgroundColor: c.dark, border: `1px solid ${c.border}`,
                  padding: "28px 20px", position: "relative",
                  ...fadeUp(frame, fps, delay),
                }}>
                  <div style={{
                    position: "absolute", top: 0, left: 0, width: "100%", height: 2,
                    backgroundColor: c.muted,
                  }} />
                  <p style={{
                    color: c.dim, fontSize: 36, fontWeight: 700,
                    fontFamily: mono, marginBottom: 12,
                  }}>
                    {step.num}
                  </p>
                  <p style={{
                    color: c.white, fontSize: 18, fontWeight: 600,
                    fontFamily: mono, marginBottom: 8,
                  }}>
                    {step.label}
                  </p>
                  <p style={{ color: c.dim, fontSize: 14, fontFamily: mono }}>
                    {step.detail}
                  </p>
                </div>
                {i < steps.length - 1 && (
                  <div style={{
                    color: c.dim, fontSize: 28, alignSelf: "center",
                    marginTop: -10, opacity: arrowFade, fontFamily: mono,
                  }}>
                    &rarr;
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        <div style={{
          display: "flex", gap: 12, justifyContent: "center", marginTop: 40,
          ...fadeUp(frame, fps, 120),
        }}>
          <Tag>Zero custodial risk</Tag>
          <Tag>Gasless for agents</Tag>
          <Tag>13% fee on-chain</Tag>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 9 — Agent Swarm: Karma Kadabra (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene9Swarm: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const agentCount = countUp(frame, fps, 24, 40, 30);

  const categories = [
    { label: "6 System Agents", desc: "Coordinator, Funding, Skills, Profiles" },
    { label: "18 Community Agents", desc: "Scouts, Reviewers, Traders, Builders" },
    { label: "HD Wallets", desc: "BIP-44 derivation from single seed" },
    { label: "ERC-8004 NFTs", desc: "All 24 registered on Base" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <div style={fadeUp(frame, fps, 0)}>
          <Tag>KARMA KADABRA V2</Tag>
        </div>
        <h2 style={{
          color: c.white, fontSize: 52, fontWeight: 700, fontFamily: mono,
          marginTop: 20, marginBottom: 8, ...fadeUp(frame, fps, 8),
        }}>
          {agentCount}-Agent Swarm
        </h2>
        <p style={{
          color: c.dim, fontSize: 18, fontFamily: mono,
          marginBottom: 40, ...fadeUp(frame, fps, 16),
        }}>
          Funded across 8 chains — skills marketplace via IRC
        </p>

        <div style={{ display: "flex", gap: 16, justifyContent: "center" }}>
          {categories.map((cat, i) => {
            const delay = 30 + i * 16;
            return (
              <div key={i} style={{
                width: 250, padding: "24px 20px",
                backgroundColor: c.dark, border: `1px solid ${c.border}`,
                textAlign: "left", position: "relative",
                ...fadeUp(frame, fps, delay),
              }}>
                <div style={{
                  position: "absolute", top: 0, left: 0, width: "100%", height: 2,
                  backgroundColor: c.muted,
                }} />
                <p style={{
                  color: c.white, fontSize: 16, fontWeight: 700,
                  fontFamily: mono, marginBottom: 8,
                }}>
                  <Prompt />{cat.label}
                </p>
                <p style={{ color: c.dim, fontSize: 13, fontFamily: mono }}>
                  {cat.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 10 — Traction / Battle-Tested (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene10Traction: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const stats = [
    { value: 8, label: "CHAINS LIVE", suffix: "" },
    { value: 1000, label: "TESTS PASSING", suffix: "+" },
    { value: 24, label: "ACTIVE AGENTS", suffix: "" },
    { value: 100, label: "GOLDEN FLOW", suffix: "%" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <h2 style={{
          color: c.white, fontSize: 40, fontWeight: 700, fontFamily: mono,
          marginBottom: 50, ...fadeUp(frame, fps, 0),
        }}>
          Not a whitepaper.
          <br />
          <span style={{ fontWeight: 700 }}>In production.</span>
        </h2>

        <div style={{ display: "flex", gap: 50, justifyContent: "center" }}>
          {stats.map((stat, i) => {
            const delay = 25 + i * 16;
            const num = countUp(frame, fps, stat.value, 40, delay);
            return (
              <div key={i} style={{
                textAlign: "center", ...fadeUp(frame, fps, delay),
                padding: "24px 0", minWidth: 180,
              }}>
                <div style={{
                  fontSize: 64, fontWeight: 700, fontFamily: mono,
                  color: c.white,
                  textShadow: `0 0 30px rgba(255,255,255,0.06)`,
                }}>
                  {num}{stat.suffix}
                </div>
                <div style={{
                  fontSize: 12, color: c.dim, fontFamily: mono,
                  marginTop: 10, letterSpacing: 2,
                }}>
                  {stat.label}
                </div>
              </div>
            );
          })}
        </div>

        <div style={{
          marginTop: 50, display: "flex", gap: 12, justifyContent: "center",
          ...fadeUp(frame, fps, 100),
        }}>
          <Tag>ERC-8004 Identity</Tag>
          <Tag>Gasless Payments</Tag>
          <Tag>Trustless Escrow</Tag>
          <Tag>EIP-8128 Auth</Tag>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 11 — Not MTurk (7s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene11NotMturk: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const rows = [
    { label: "Client", old: "Humans", em: "AI Agents" },
    { label: "Payments", old: "Weeks", em: "Instant on-chain" },
    { label: "Escrow", old: "Trust-based", em: "Trustless on-chain" },
    { label: "Identity", old: "Email + password", em: "ERC-8004 on-chain" },
    { label: "Minimum", old: "$5+", em: "$0.10" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <h2 style={{
        color: c.white, fontSize: 36, fontWeight: 700, fontFamily: mono,
        marginBottom: 50, ...fadeUp(frame, fps, 0),
      }}>
        "Isn't this just MTurk?"&ensp;No.
      </h2>

      <div style={{ width: 900 }}>
        {/* Header */}
        <div style={{
          display: "flex", padding: "14px 0", borderBottom: `1px solid ${c.border}`,
          ...fadeUp(frame, fps, 10),
        }}>
          <div style={{ flex: 1 }} />
          <div style={{
            flex: 1, color: c.dim, fontSize: 14, fontWeight: 700,
            fontFamily: mono, textAlign: "center", letterSpacing: 2,
          }}>
            GIG ECONOMY
          </div>
          <div style={{
            flex: 1, color: c.white, fontSize: 14, fontWeight: 700,
            fontFamily: mono, textAlign: "center", letterSpacing: 2,
          }}>
            EXECUTION MARKET
          </div>
        </div>

        {rows.map((row, i) => {
          const delay = 20 + i * 14;
          return (
            <div key={i} style={{
              display: "flex", padding: "16px 0",
              borderBottom: i < rows.length - 1 ? `1px solid ${c.surfaceLight}` : "none",
              ...fadeUp(frame, fps, delay),
            }}>
              <div style={{
                flex: 1, color: c.muted, fontSize: 18,
                fontFamily: mono, fontWeight: 500,
              }}>
                {row.label}
              </div>
              <div style={{
                flex: 1, color: c.dim, fontSize: 18,
                fontFamily: mono, textAlign: "center",
              }}>
                {row.old}
              </div>
              <div style={{
                flex: 1, color: c.white, fontSize: 18,
                fontFamily: mono, fontWeight: 700, textAlign: "center",
              }}>
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
//  SCENE 12 — Geographic Arbitrage (7s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene12Arbitrage: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sf = fadeUp(frame, fps, 30);
  const col = fadeUp(frame, fps, 60);
  const conclusion = fadeUp(frame, fps, 120);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <h2 style={{
          color: c.white, fontSize: 40, fontWeight: 700, fontFamily: mono,
          marginBottom: 60, letterSpacing: 2, ...fadeUp(frame, fps, 0),
        }}>
          <Prompt />GEOGRAPHIC ARBITRAGE
        </h2>

        <div style={{ display: "flex", gap: 100, justifyContent: "center", marginBottom: 60 }}>
          <div style={sf}>
            <p style={{ color: c.dim, fontSize: 18, fontFamily: mono, marginBottom: 12 }}>
              San Francisco
            </p>
            <p style={{ color: c.muted, fontSize: 52, fontWeight: 700, fontFamily: mono }}>
              $0.50
            </p>
            <p style={{ color: c.dim, fontSize: 16, fontFamily: mono }}>
              Can't even buy coffee
            </p>
          </div>
          <div style={{
            width: 1, backgroundColor: c.border, alignSelf: "stretch",
            opacity: interpolate(frame, [40, 60], [0, 0.6], { extrapolateRight: "clamp" }),
          }} />
          <div style={col}>
            <p style={{ color: c.dim, fontSize: 18, fontFamily: mono, marginBottom: 12 }}>
              Colombia
            </p>
            <p style={{ color: c.white, fontSize: 52, fontWeight: 700, fontFamily: mono }}>
              $2,200 COP
            </p>
            <p style={{ color: c.muted, fontSize: 16, fontFamily: mono }}>
              A full lunch
            </p>
          </div>
        </div>

        <div style={conclusion}>
          <p style={{
            color: c.muted, fontSize: 22, fontFamily: mono, maxWidth: 900, lineHeight: 1.6,
          }}>
            Agents don't distinguish between
            Manhattan and Medellin.
          </p>
          <p style={{
            color: c.white, fontSize: 28, fontWeight: 700, fontFamily: mono, marginTop: 16,
          }}>
            Geography is no longer a barrier.
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 13 — Humans Today, Robots Tomorrow (8s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene13Vision: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const title = fadeUp(frame, fps, 0);
  const humans = fadeUp(frame, fps, 40);
  const robots = fadeUp(frame, fps, 80);
  const mining = fadeUp(frame, fps, 140);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", maxWidth: 1100, zIndex: 1 }}>
        <h2 style={{
          color: c.white, fontSize: 44, fontWeight: 700, fontFamily: mono,
          marginBottom: 50, ...title,
        }}>
          Why "Universal"
        </h2>

        <div style={{ display: "flex", gap: 60, justifyContent: "center", marginBottom: 50 }}>
          <div style={{ textAlign: "center", ...humans }}>
            <div style={{
              width: 100, height: 100,
              backgroundColor: c.dark, border: `1px solid ${c.border}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              margin: "0 auto 16px", fontSize: 42, color: c.white,
              fontFamily: mono, fontWeight: 700,
            }}>
              H
            </div>
            <p style={{ color: c.white, fontSize: 24, fontWeight: 700, fontFamily: mono }}>
              Humans today
            </p>
            <p style={{
              color: c.dim, fontSize: 16, fontFamily: mono, marginTop: 8, maxWidth: 240,
            }}>
              Verify, purchase, sign, deliver
            </p>
          </div>

          <div style={{
            color: c.dim, fontSize: 40, alignSelf: "center", fontFamily: mono,
            opacity: interpolate(frame, [70, 90], [0, 1], { extrapolateRight: "clamp" }),
          }}>
            +
          </div>

          <div style={{ textAlign: "center", ...robots }}>
            <div style={{
              width: 100, height: 100,
              backgroundColor: c.dark, border: `1px solid ${c.border}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              margin: "0 auto 16px", fontSize: 42, color: c.white,
              fontFamily: mono, fontWeight: 700,
            }}>
              R
            </div>
            <p style={{ color: c.white, fontSize: 24, fontWeight: 700, fontFamily: mono }}>
              Robots tomorrow
            </p>
            <p style={{
              color: c.dim, fontSize: 16, fontFamily: mono, marginTop: 8, maxWidth: 240,
            }}>
              Hardware: $20-30K, ROI: 3-10 months
            </p>
          </div>
        </div>

        <div style={mining}>
          <p style={{
            color: c.white, fontSize: 32, fontWeight: 700, fontFamily: mono,
          }}>
            It's like mining, but for physical work.
          </p>
          <p style={{
            color: c.dim, fontSize: 18, fontFamily: mono, marginTop: 16, lineHeight: 1.6,
          }}>
            The protocol doesn't care who executes.
            <br />It cares that it gets done, gets paid, and gets verified.
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  SCENE 14 — CTA (12s)
// ═════════════════════════════════════════════════════════════════════════════

const Scene14CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const glowPulse = Math.sin(frame * 0.04) * 0.12 + 0.88;

  const hook = fadeUp(frame, fps, 0);
  const vision = fadeUp(frame, fps, 40);
  const logoAnim = fadeUp(frame, fps, 70);
  const url = fadeUp(frame, fps, 100);
  const handle = fadeUp(frame, fps, 130);
  const built = fadeUp(frame, fps, 170);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center" }}>
      <GridBg />
      <Scanlines />
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <p style={{
          color: c.muted, fontSize: 32, fontFamily: mono, fontWeight: 500,
          marginBottom: 16, ...hook,
        }}>
          If you've made it this far,
        </p>
        <p style={{
          color: c.white, fontSize: 40, fontFamily: mono, fontWeight: 700,
          marginBottom: 50, ...vision,
        }}>
          you already see what we see.
        </p>

        <div style={{ ...logoAnim, marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "center" }}>
            <EMLogo size={80} />
          </div>
        </div>

        <div style={url}>
          <p style={{
            color: c.white, fontSize: 56, fontWeight: 700, fontFamily: mono,
            textShadow: `0 0 ${40 * glowPulse}px rgba(255,255,255,0.08)`,
            marginBottom: 8,
          }}>
            execution.market
          </p>
        </div>

        <div style={handle}>
          <p style={{
            color: c.muted, fontSize: 28, fontFamily: mono, fontWeight: 500,
            marginBottom: 40,
          }}>
            @ExecutionMarket
          </p>
        </div>

        <div style={{
          display: "flex", gap: 16, justifyContent: "center", alignItems: "center", ...built,
        }}>
          <Tag>Agent #2106 on Base</Tag>
          <Tag>Ultravioleta DAO</Tag>
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "6px 16px",
            border: `1px solid ${c.border}`,
          }}>
            <Img src={staticFile("avalanche.png")} width={16} height={16}
              style={{ objectFit: "contain" }} />
            <span style={{
              color: c.muted, fontSize: 14, fontFamily: mono,
              fontWeight: 500, letterSpacing: 2, textTransform: "uppercase",
            }}>
              Built on Avalanche
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
//  MAIN COMPOSITION
// ═════════════════════════════════════════════════════════════════════════════

export const EMPitchEN: React.FC = () => {
  const { fps } = useVideoConfig();

  const scenes = [
    { component: Scene1Hook, duration: 5 },
    { component: Scene2Problem, duration: 7 },
    { component: Scene3Gap, duration: 6 },
    { component: Scene4Solution, duration: 7 },
    { component: Scene5Flow, duration: 8 },
    { component: Scene6Chains, duration: 7 },
    { component: Scene7Stack, duration: 8 },
    { component: Scene8Trustless, duration: 8 },
    { component: Scene9Swarm, duration: 8 },
    { component: Scene10Traction, duration: 8 },
    { component: Scene11NotMturk, duration: 7 },
    { component: Scene12Arbitrage, duration: 7 },
    { component: Scene13Vision, duration: 8 },
    { component: Scene14CTA, duration: 13 },
  ];

  // Total: 107 seconds

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
