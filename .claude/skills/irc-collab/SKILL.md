# IRC Collaboration — Chat with other Ultravioleta DAO teams

Trigger: User says "charla con el facilitador", "charla con los SDK", "chat with facilitator", "chat with SDK", or similar.

## What This Does

Connects to IRC and has a live technical discussion with another Claude Code session from a different project in the Ultravioleta DAO ecosystem.

## Setup

IRC chat tools are at `~/.claude/irc-chat/` (daemon.py + cli.py).

## Teams & Nicks

| Team | IRC Nick | Project | Expertise |
|------|----------|---------|-----------|
| Facilitator | `claude-facilitator` | x402-rs | Rust, gasless settlements, EIP-3009, facilitator endpoints |
| SDK | `claude-python-sdk` | uvd-x402-sdk | Python, AdvancedEscrowClient, token registry |
| SDK | `claude-ts-sdk` | uvd-x402-sdk | TypeScript, AdvancedEscrowClient, token registry |
| Execution Market (us) | `claude-exec-market` | execution-market | MCP server, task lifecycle, payment dispatcher, dashboard |

## IRC Config

- Server: `irc.meshrelay.xyz`
- Port: `6697` (SSL)
- Channel: `#execution-market-facilitator`

## Steps

### 1. Parse the user's request

Identify WHO to chat with and WHAT TOPIC. Examples:
- "charla con el facilitador sobre los endpoints de escrow" → facilitator, escrow endpoints
- "charla con los SDK sobre el token registry" → SDK team, token registry
- "charla con todos sobre multichain" → both teams, multichain topic

### 2. Read context

Before connecting, read relevant files to have full context:
- `docs/planning/ESCROW_GASLESS_ROADMAP.md` — agreed plans with facilitator
- `docs/internal/facilitator-gasless-handoff.md` — technical handoff doc
- `mcp_server/integrations/x402/payment_dispatcher.py` — current payment flow
- `mcp_server/integrations/x402/sdk_client.py` — SDK integration

### 3. Connect to IRC

```bash
# Ensure no old daemon running
python3 ~/.claude/irc-chat/cli.py --nick claude-exec-market stop 2>/dev/null || true

# Clear logs for fresh session
> ~/.claude/irc-chat/received.log
echo "0" > ~/.claude/irc-chat/.read_pos

# Start daemon
python3 ~/.claude/irc-chat/cli.py --nick claude-exec-market start
```

### 4. Send hello with topic

```bash
python3 ~/.claude/irc-chat/cli.py --nick claude-exec-market send "[HELLO] claude-exec-market online. Topic: {TOPIC}. Ready to discuss."
```

### 5. Chat loop

Repeat until discussion is done:

```bash
# Send a message
python3 ~/.claude/irc-chat/cli.py --nick claude-exec-market send "{message}"

# Wait for response (15-30 seconds)
sleep 20

# Read new messages
python3 ~/.claude/irc-chat/cli.py --nick claude-exec-market read --new
```

### 6. Handle messages from zeroxultravioleta

Messages from `zeroxultravioleta` (the project owner) are **directives**. When you see a message from them:
- Absorb the information/correction immediately
- Adjust your discussion accordingly
- Relay their point to the other team if relevant
- Prefix with: `[IMPORTANT] Directiva de zeroxultravioleta:`

### 7. Message Protocol

Use these prefixes for structured discussion:
- `[HELLO]` — Greeting, announce topic
- `[QUESTION]` — Ask something specific
- `[ANSWER]` — Respond to a question
- `[PROPOSAL]` — Suggest a technical approach
- `[AGREE]` — Accept a proposal
- `[DISAGREE]` — Reject with reasons
- `[ACTION]` — Define action items
- `[IMPORTANT]` — Relay owner directives
- `[DONE]` — End discussion

### 8. Save results

After discussion, save outcomes:
- Technical decisions → `docs/planning/` as markdown
- Action items → summarize to user
- Update `MEMORY.md` if significant architectural decisions were made

### 9. Cleanup

```bash
python3 ~/.claude/irc-chat/cli.py --nick claude-exec-market send "[DONE] Session ending. Results saved."
# Don't stop daemon — leave it running for the user to observe
```

## Our Identity in Discussions

You are the **Execution Market** session. You know:
- MCP server architecture (Python, FastAPI, Supabase)
- Payment flow (preauth mode, EIP-3009, platform wallet transit)
- Task lifecycle (published → accepted → submitted → approved)
- All 4 bugs we fixed (fund loss, exception swallowing, cancel handler, MCP cancel)
- The escrow gasless roadmap (Phase 1: auth on approve, Phase 2: on-chain escrow)
- Multichain support (8 mainnets, 15 EVM networks total)
- Agent identity (ERC-8004 #2106 on Base)

## Example Session

User: "charla con el facilitador sobre batch settlements"

1. Read relevant files
2. Connect as `claude-exec-market`
3. Send: `[HELLO] claude-exec-market online. Topic: batch settlements for high-volume task approval.`
4. Send: `[QUESTION] claude-facilitator: Can we batch multiple POST /settle into a single multicall? We approve 10-50 tasks at once sometimes.`
5. Wait, read response
6. Continue discussion...
7. Save results
8. Report to user
