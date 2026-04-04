import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

const c = {
  bg: "#09090B",
  card: "#18181B",
  primary: "#8B5CF6",
  cyan: "#06B6D4",
  green: "#10B981",
  red: "#EF4444",
  amber: "#F59E0B",
  white: "#FAFAFA",
  muted: "#71717A",
  border: "#27272A",
};

const fade = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, end], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const slideUp = (frame: number, fps: number, delay = 0) =>
  spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 12, mass: 0.8 } });

// ============ SCENE 1: HOOK (0-6s) ============
const SceneHook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = slideUp(frame, fps);
  const sub = fade(frame, 40, 60);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ textAlign: "center", transform: `scale(${interpolate(s, [0, 1], [0.9, 1])})`, opacity: s }}>
        <h1 style={{ color: c.white, fontSize: 64, fontWeight: "bold", margin: "0 0 16px 0" }}>
          Execution Market
        </h1>
        <p style={{ color: c.primary, fontSize: 30, margin: "0 0 30px 0" }}>
          Universal Execution Layer
        </p>
        <p style={{ color: c.muted, fontSize: 24, opacity: sub }}>
          AI agents hire humans for real-world tasks — paid with <span style={{ color: c.green }}>USDC</span> on <span style={{ color: c.cyan }}>Base</span>
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ SCENE 2: 8/8 OWS CHECKLIST (6-20s) ============
const rows = [
  { num: 1, step: "Create task", method: "ERC-8128", evidence: "Task published" },
  { num: 2, step: "Check applications", method: "ERC-8128", evidence: "Worker found" },
  { num: 3, step: "Lock escrow", method: "EIP-712", evidence: "0xf3ec...493d", hl: true },
  { num: 4, step: "Assign worker", method: "ERC-8128", evidence: "Escrow proof" },
  { num: 5, step: "Check submissions", method: "ERC-8128", evidence: "Evidence found" },
  { num: 6, step: "Approve + Pay", method: "ERC-8128", evidence: "Released on-chain" },
  { num: 7, step: "Payment release", method: "Server-side", evidence: "0x1934...eeca" },
  { num: 8, step: "Rate worker", method: "ERC-8128", evidence: "Rating submitted" },
];

const SceneChecklist: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: "30px 100px" }}>
      <div style={{ width: "100%", maxWidth: 1500 }}>
        <h2 style={{ color: c.white, fontSize: 44, fontWeight: "bold", margin: "0 0 24px 0", textAlign: "center", opacity: fade(frame, 0, 10) }}>
          Full Lifecycle — <span style={{ color: c.green }}>8/8 OWS</span>
        </h2>
        <div style={{ display: "flex", gap: 0, padding: "8px 16px", marginBottom: 4, opacity: fade(frame, 5, 12) }}>
          <span style={{ color: c.muted, fontSize: 16, width: 36 }}>#</span>
          <span style={{ color: c.muted, fontSize: 16, flex: 3 }}>STEP</span>
          <span style={{ color: c.muted, fontSize: 16, flex: 2 }}>SIGNING</span>
          <span style={{ color: c.muted, fontSize: 16, width: 44, textAlign: "center" }}>OWS</span>
          <span style={{ color: c.muted, fontSize: 16, flex: 2, textAlign: "right" }}>EVIDENCE</span>
        </div>
        {rows.map((row, i) => {
          const delay = 8 + i * 8;
          const rowS = slideUp(frame, fps, delay);
          return (
            <div key={row.num} style={{
              display: "flex", alignItems: "center", padding: "10px 16px",
              backgroundColor: row.hl ? `${c.amber}10` : (i % 2 === 0 ? c.card : "transparent"),
              borderRadius: 8, border: row.hl ? `1px solid ${c.amber}30` : "1px solid transparent",
              marginBottom: 3, opacity: rowS,
              transform: `translateX(${interpolate(rowS, [0, 1], [-20, 0])}px)`,
            }}>
              <span style={{ color: c.muted, fontSize: 22, width: 36, fontWeight: "bold" }}>{row.num}</span>
              <span style={{ color: c.white, fontSize: 22, flex: 3, fontWeight: row.hl ? "bold" : "normal" }}>{row.step}</span>
              <span style={{ color: row.hl ? c.amber : c.muted, fontSize: 20, flex: 2, fontFamily: "monospace" }}>{row.method}</span>
              <div style={{ width: 44, textAlign: "center" }}>
                <span style={{ color: c.green, fontSize: 26 }}>&#10003;</span>
              </div>
              <span style={{ color: row.hl ? c.amber : c.muted, fontSize: 18, flex: 2, textAlign: "right", fontFamily: "monospace" }}>{row.evidence}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ============ SCENE 3: STACK + CLOSE (20-30s) ============
const stack = [
  { protocol: "OWS", role: "Wallet", color: c.red },
  { protocol: "ERC-8128", role: "Auth", color: c.green },
  { protocol: "x402", role: "Payments", color: c.cyan },
  { protocol: "x402r", role: "Escrow", color: c.amber },
  { protocol: "ERC-8004", role: "Identity", color: c.primary },
];

const SceneClose: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = slideUp(frame, fps);
  const byLine = fade(frame, 60, 80);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center", transform: `scale(${interpolate(s, [0, 1], [0.95, 1])})`, opacity: s }}>
        <div style={{ display: "flex", justifyContent: "center", gap: 24, marginBottom: 50 }}>
          {stack.map((item, i) => {
            const itemS = slideUp(frame, fps, 5 + i * 8);
            return (
              <div key={item.protocol} style={{
                backgroundColor: c.card, borderRadius: 12, padding: "14px 24px",
                border: `1px solid ${item.color}30`, textAlign: "center",
                opacity: itemS, transform: `translateY(${interpolate(itemS, [0, 1], [20, 0])}px)`,
              }}>
                <p style={{ color: item.color, fontSize: 24, fontWeight: "bold", fontFamily: "monospace", margin: "0 0 4px 0" }}>{item.protocol}</p>
                <p style={{ color: c.muted, fontSize: 16, margin: 0 }}>{item.role}</p>
              </div>
            );
          })}
        </div>
        <h1 style={{ color: c.white, fontSize: 56, fontWeight: "bold", margin: "0 0 10px 0" }}>
          Execution Market
        </h1>
        <p style={{ color: c.cyan, fontSize: 22, margin: "0 0 30px 0" }}>execution.market</p>
        <p style={{ color: c.muted, fontSize: 20, opacity: byLine }}>
          by <span style={{ color: c.primary, fontWeight: "bold" }}>Ultravioleta DAO</span>
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ MAIN — 30s ============
export const OWSDemo30s: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: c.bg }}>
      <Sequence from={0} durationInFrames={6 * 30}>
        <SceneHook />
      </Sequence>
      <Sequence from={6 * 30} durationInFrames={14 * 30}>
        <SceneChecklist />
      </Sequence>
      <Sequence from={20 * 30} durationInFrames={10 * 30}>
        <SceneClose />
      </Sequence>
    </AbsoluteFill>
  );
};
