import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

// ============ PALETTE ============
const c = {
  bg: "#09090B",
  card: "#18181B",
  primary: "#8B5CF6",    // violet
  cyan: "#06B6D4",
  green: "#10B981",
  red: "#EF4444",
  amber: "#F59E0B",
  white: "#FAFAFA",
  muted: "#71717A",
  border: "#27272A",
};

// ============ HELPERS ============
const fade = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, end], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const slideUp = (frame: number, fps: number, delay = 0) =>
  spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 12, mass: 0.8 } });

// ============ SCENE 1: TELEGRAM PROMPT ============
const SceneTelegramPrompt: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = slideUp(frame, fps);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `translateY(${interpolate(s, [0, 1], [80, 0])}px)`, opacity: s }}>
        {/* Telegram-style chat */}
        <div style={{ backgroundColor: c.card, borderRadius: 24, padding: 50, maxWidth: 1000, border: `1px solid ${c.border}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 30 }}>
            <div style={{ width: 48, height: 48, borderRadius: "50%", background: `linear-gradient(135deg, ${c.primary}, ${c.cyan})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, color: c.white, fontWeight: "bold" }}>U</div>
            <span style={{ color: c.muted, fontSize: 20 }}>0x Ultravioleta</span>
            <span style={{ color: c.muted, fontSize: 16, marginLeft: "auto" }}>11:05 PM</span>
          </div>
          <p style={{ color: c.white, fontSize: 32, lineHeight: 1.6, margin: 0 }}>
            hey i want you to hire a human to take a picture of the current sky in miami, <span style={{ color: c.green, fontWeight: "bold" }}>0.05 usdc</span> on <span style={{ color: c.cyan }}>base</span>
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ SCENE 2: CLAWD RESPONDS ============
const SceneClawdPublish: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = slideUp(frame, fps);
  const check = fade(frame, 30, 45);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ maxWidth: 1000, width: "100%" }}>
        {/* User message */}
        <div style={{ backgroundColor: c.card, borderRadius: 20, padding: 30, marginBottom: 30, border: `1px solid ${c.border}`, opacity: 0.6 }}>
          <p style={{ color: c.muted, fontSize: 22, margin: 0 }}>hire a human to take a picture of the current sky in miami...</p>
        </div>
        {/* Bot response */}
        <div style={{ transform: `translateY(${interpolate(s, [0, 1], [60, 0])}px)`, opacity: s }}>
          <div style={{ backgroundColor: c.card, borderRadius: 20, padding: 40, border: `1px solid ${c.primary}40` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: c.primary, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, color: c.white }}>C</div>
              <span style={{ color: c.primary, fontSize: 20, fontWeight: "bold" }}>ultraclawd</span>
            </div>
            <p style={{ color: c.white, fontSize: 28, margin: 0 }}>
              <span style={{ color: c.green, opacity: check }}>Task published.</span>{" "}
              <span style={{ color: c.muted }}>$0.05 on Base. Waiting for a worker to apply.</span>
            </p>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ SCENE 3: OWS VERIFICATION CHECKLIST ============
const checklistRows = [
  { num: 1, step: "Create task", endpoint: "POST /tasks", method: "ERC-8128 header", evidence: "Task 42dbf95f created" },
  { num: 2, step: "Check applications", endpoint: "GET /tasks/{id}/applications", method: "ERC-8128 header", evidence: "Worker detected via OWS-signed GET" },
  { num: 3, step: "Lock escrow on-chain", endpoint: "USDC ReceiveWithAuthorization", method: "EIP-712 typed data", evidence: "TX 0xf3ec...493d on Base", highlight: true },
  { num: 4, step: "Assign worker", endpoint: "POST /tasks/{id}/assign", method: "ERC-8128 header", evidence: "Worker assigned with escrow proof" },
  { num: 5, step: "Check submissions", endpoint: "GET /tasks/{id}/submissions", method: "ERC-8128 header", evidence: "Evidence detected via OWS-signed GET" },
  { num: 6, step: "Approve submission", endpoint: "POST /submissions/{id}/approve", method: "ERC-8128 header", evidence: "Payment released on-chain" },
  { num: 7, step: "Pay worker", endpoint: "escrow release", method: "Server-side (triggered by approve)", evidence: "TX 0x1934...eeca — worker paid" },
  { num: 8, step: "Rate worker", endpoint: "POST /reputation/workers/rate", method: "ERC-8128 header", evidence: "Rating submitted" },
];

const SceneChecklist: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: "40px 80px" }}>
      <div style={{ width: "100%", maxWidth: 1700 }}>
        <h2 style={{ color: c.white, fontSize: 48, fontWeight: "bold", margin: "0 0 36px 0", textAlign: "center", opacity: fade(frame, 0, 15) }}>
          OWS Verification Checklist — <span style={{ color: c.green }}>8/8</span>
        </h2>
        {/* Header row */}
        <div style={{
          display: "flex", gap: 0, padding: "12px 20px", marginBottom: 6,
          opacity: fade(frame, 5, 15),
        }}>
          <span style={{ color: c.muted, fontSize: 18, width: 40, textTransform: "uppercase", letterSpacing: 1 }}>#</span>
          <span style={{ color: c.muted, fontSize: 18, flex: 2, textTransform: "uppercase", letterSpacing: 1 }}>Step</span>
          <span style={{ color: c.muted, fontSize: 18, flex: 2, textTransform: "uppercase", letterSpacing: 1 }}>Signing method</span>
          <span style={{ color: c.muted, fontSize: 18, width: 50, textAlign: "center", textTransform: "uppercase", letterSpacing: 1 }}>OWS</span>
          <span style={{ color: c.muted, fontSize: 18, flex: 2, textTransform: "uppercase", letterSpacing: 1, textAlign: "right" }}>Evidence</span>
        </div>
        {/* Rows */}
        {checklistRows.map((row, i) => {
          const delay = 10 + i * 10;
          const rowS = slideUp(frame, fps, delay);
          return (
            <div
              key={row.num}
              style={{
                display: "flex", gap: 0, alignItems: "center",
                padding: "14px 20px",
                backgroundColor: row.highlight ? `${c.amber}10` : (i % 2 === 0 ? c.card : "transparent"),
                borderRadius: 10,
                border: row.highlight ? `1px solid ${c.amber}30` : "1px solid transparent",
                marginBottom: 4,
                transform: `translateX(${interpolate(rowS, [0, 1], [-30, 0])}px)`,
                opacity: rowS,
              }}
            >
              <span style={{ color: c.muted, fontSize: 24, width: 40, fontWeight: "bold" }}>{row.num}</span>
              <span style={{ color: c.white, fontSize: 22, flex: 2, fontWeight: row.highlight ? "bold" : "normal" }}>{row.step}</span>
              <span style={{ color: row.highlight ? c.amber : c.muted, fontSize: 20, flex: 2, fontFamily: "monospace" }}>{row.method}</span>
              <div style={{ width: 50, textAlign: "center" }}>
                <span style={{ color: c.green, fontSize: 28 }}>&#10003;</span>
              </div>
              <span style={{ color: row.highlight ? c.amber : c.muted, fontSize: 19, flex: 2, textAlign: "right" }}>{row.evidence}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ============ SCENE 4: ESCROW TX HIGHLIGHT ============
const SceneEscrowTx: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = slideUp(frame, fps);
  const glow = Math.sin(frame * 0.08) * 0.3 + 0.7;

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center", transform: `scale(${interpolate(s, [0, 1], [0.9, 1])})`, opacity: s, maxWidth: 1400 }}>
        <div style={{ marginBottom: 40 }}>
          <span style={{ color: c.amber, fontSize: 20, textTransform: "uppercase", letterSpacing: 4, fontWeight: "bold" }}>Escrow Locked On-Chain</span>
        </div>
        <div style={{
          backgroundColor: c.card,
          borderRadius: 20,
          padding: "40px 50px",
          border: `2px solid ${c.amber}`,
          boxShadow: `0 0 ${60 * glow}px ${c.amber}40`,
        }}>
          <p style={{ color: c.muted, fontSize: 16, margin: "0 0 8px 0", textAlign: "left" }}>basescan.org/tx/</p>
          <p style={{ color: c.white, fontSize: 22, fontFamily: "monospace", margin: "0 0 28px 0", letterSpacing: 0.5, textAlign: "left", wordBreak: "break-all" }}>
            0xf3ecbf61917f8acfb3d1c4ccd0c4c56e704ae7d6291a56545aa59ac6d978493d
          </p>
          <div style={{ display: "flex", gap: 50, justifyContent: "center" }}>
            <div>
              <p style={{ color: c.muted, fontSize: 15, margin: 0 }}>Network</p>
              <p style={{ color: c.cyan, fontSize: 22, fontWeight: "bold", margin: 0 }}>Base</p>
            </div>
            <div>
              <p style={{ color: c.muted, fontSize: 15, margin: 0 }}>Amount</p>
              <p style={{ color: c.green, fontSize: 22, fontWeight: "bold", margin: 0 }}>$0.05 USDC</p>
            </div>
            <div>
              <p style={{ color: c.muted, fontSize: 15, margin: 0 }}>Signed By</p>
              <p style={{ color: c.primary, fontSize: 22, fontWeight: "bold", margin: 0 }}>OWS Vault</p>
            </div>
            <div>
              <p style={{ color: c.muted, fontSize: 15, margin: 0 }}>Method</p>
              <p style={{ color: c.amber, fontSize: 22, fontWeight: "bold", margin: 0 }}>EIP-712</p>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ SCENE 5: ON-CHAIN TRANSACTIONS ============
const SceneTransactions: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = slideUp(frame, fps);
  const tx2 = fade(frame, 50, 70);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center", maxWidth: 1200, transform: `scale(${interpolate(s, [0, 1], [0.9, 1])})`, opacity: s }}>
        <div style={{ fontSize: 80, marginBottom: 20 }}>
          <span style={{ color: c.green }}>8/8</span>
        </div>
        <h2 style={{ color: c.white, fontSize: 48, fontWeight: "bold", margin: "0 0 40px 0" }}>
          Full Lifecycle Complete
        </h2>

        {/* Escrow TX */}
        <div style={{ backgroundColor: c.card, borderRadius: 16, padding: "24px 40px", border: `1px solid ${c.amber}40`, marginBottom: 20, textAlign: "left" }}>
          <p style={{ color: c.amber, fontSize: 15, fontWeight: "bold", margin: "0 0 4px 0", textTransform: "uppercase", letterSpacing: 2 }}>Escrow Lock</p>
          <p style={{ color: c.muted, fontSize: 13, margin: "0 0 6px 0" }}>basescan.org/tx/</p>
          <p style={{ color: c.white, fontSize: 16, fontFamily: "monospace", margin: 0, letterSpacing: 0.3, wordBreak: "break-all" }}>
            0xf3ecbf61917f8acfb3d1c4ccd0c4c56e704ae7d6291a56545aa59ac6d978493d
          </p>
        </div>

        {/* Payment TX */}
        <div style={{ backgroundColor: c.card, borderRadius: 16, padding: "24px 40px", border: `1px solid ${c.green}40`, textAlign: "left", opacity: tx2 }}>
          <p style={{ color: c.green, fontSize: 15, fontWeight: "bold", margin: "0 0 4px 0", textTransform: "uppercase", letterSpacing: 2 }}>Payment Release</p>
          <p style={{ color: c.muted, fontSize: 13, margin: "0 0 6px 0" }}>basescan.org/tx/</p>
          <p style={{ color: c.white, fontSize: 16, fontFamily: "monospace", margin: 0, letterSpacing: 0.3, wordBreak: "break-all" }}>
            0x1934127aa0dd9d27a130f7ecb5c6ec0a27fd820307fed49c068b5b13d370eeca
          </p>
        </div>

        <p style={{ color: c.muted, fontSize: 16, fontFamily: "monospace", margin: "30px 0 0 0", opacity: tx2 }}>
          Create &rarr; Apply &rarr; Escrow &rarr; Assign &rarr; Submit &rarr; Approve &rarr; Pay &rarr; Rate
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============ SCENE 6: TECH STACK ============
const stackItems = [
  { protocol: "OWS", role: "Wallet", desc: "Keyless agent wallet management", color: c.red },
  { protocol: "ERC-8128", role: "Auth", desc: "Wallet-based agent signing", color: c.green },
  { protocol: "x402", role: "Payments", desc: "Gasless USDC settlements", color: c.cyan },
  { protocol: "x402r", role: "Escrow", desc: "On-chain lock/release/refund", color: c.amber },
  { protocol: "ERC-8004", role: "Identity", desc: "On-chain agent registry", color: c.primary },
];

const SceneTechStack: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = slideUp(frame, fps);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center", maxWidth: 1200, transform: `scale(${interpolate(s, [0, 1], [0.95, 1])})`, opacity: s }}>
        <h2 style={{ color: c.white, fontSize: 44, fontWeight: "bold", margin: "0 0 50px 0" }}>
          Execution Market Protocol Stack
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {stackItems.map((item, i) => {
            const delay = 10 + i * 15;
            const itemS = slideUp(frame, fps, delay);
            return (
              <div
                key={item.protocol}
                style={{
                  transform: `translateX(${interpolate(itemS, [0, 1], [-60, 0])}px)`,
                  opacity: itemS,
                  backgroundColor: c.card,
                  borderRadius: 14,
                  padding: "20px 40px",
                  border: `1px solid ${item.color}30`,
                  display: "flex",
                  alignItems: "center",
                  gap: 30,
                }}
              >
                <span style={{ color: item.color, fontSize: 28, fontWeight: "bold", fontFamily: "monospace", minWidth: 120, textAlign: "left" }}>
                  {item.protocol}
                </span>
                <span style={{ color: c.white, fontSize: 22, fontWeight: "bold", minWidth: 120, textAlign: "left" }}>
                  {item.role}
                </span>
                <span style={{ color: c.muted, fontSize: 20 }}>
                  {item.desc}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ SCENE 7: CLOSING / CTA ============
const SceneClosing: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = slideUp(frame, fps);
  const tagline = fade(frame, 30, 50);
  const byLine = fade(frame, 60, 80);

  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ textAlign: "center", transform: `scale(${interpolate(s, [0, 1], [0.9, 1])})`, opacity: s }}>
        <h1 style={{ color: c.white, fontSize: 72, fontWeight: "bold", margin: "0 0 16px 0" }}>
          Execution Market
        </h1>
        <p style={{ color: c.primary, fontSize: 28, margin: "0 0 20px 0", opacity: tagline }}>
          Universal Execution Layer
        </p>
        <p style={{ color: c.cyan, fontSize: 24, margin: "0 0 50px 0", opacity: tagline }}>
          execution.market
        </p>
        <div style={{ opacity: byLine }}>
          <p style={{ color: c.muted, fontSize: 20, margin: "0 0 30px 0" }}>
            by <span style={{ color: c.primary, fontWeight: "bold" }}>Ultravioleta DAO</span>
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ MAIN COMPOSITION ============
export const OWSDemo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: c.bg }}>
      {/* Scene 1: Telegram prompt (0-8s) */}
      <Sequence from={0} durationInFrames={8 * 30}>
        <SceneTelegramPrompt />
      </Sequence>

      {/* Scene 2: Clawd publishes (8-16s) */}
      <Sequence from={8 * 30} durationInFrames={8 * 30}>
        <SceneClawdPublish />
      </Sequence>

      {/* Scene 3: OWS verification checklist (16-30s) */}
      <Sequence from={16 * 30} durationInFrames={14 * 30}>
        <SceneChecklist />
      </Sequence>

      {/* Scene 4: Escrow TX highlight (30-42s) */}
      <Sequence from={30 * 30} durationInFrames={12 * 30}>
        <SceneEscrowTx />
      </Sequence>

      {/* Scene 5: On-chain transactions (42-54s) */}
      <Sequence from={42 * 30} durationInFrames={12 * 30}>
        <SceneTransactions />
      </Sequence>

      {/* Scene 6: Tech stack (54-66s) */}
      <Sequence from={54 * 30} durationInFrames={12 * 30}>
        <SceneTechStack />
      </Sequence>

      {/* Scene 7: Closing (66-75s) */}
      <Sequence from={66 * 30} durationInFrames={9 * 30}>
        <SceneClosing />
      </Sequence>
    </AbsoluteFill>
  );
};
