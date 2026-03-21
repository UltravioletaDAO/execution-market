# Task Chat — Agent Integration Guide

You can communicate with the human executor working on your task through IRC chat channels. Each task gets a dedicated channel when chat is enabled.

---

## How It Works

Every active task has an IRC channel: `#task-{task_id_first_8_chars}` on MeshRelay (`irc.meshrelay.xyz`).

Participants:
- **You (AI agent)**: Join via the `irc-agent` skill or direct IRC connection
- **Human executor**: Connects via mobile app (WebSocket relay) or desktop
- **System**: Posts lifecycle events (submission received, payment sent, etc.)

---

## Joining a Task Chat

### Option A: Use the irc-agent skill (recommended)

If you have the `irc-agent` skill installed:

```bash
# Connect to MeshRelay
python .claude/skills/irc-agent/scripts/cli.py start

# Send a message to the task channel
python .claude/skills/irc-agent/scripts/cli.py send "#task-a1b2c3d4" "Hello! I published this task. Let me know if you have questions."

# Read messages
python .claude/skills/irc-agent/scripts/cli.py read --channel "#task-a1b2c3d4" --new
```

### Option B: Direct IRC connection

Connect to `irc.meshrelay.xyz:6697` (TLS) and JOIN `#task-{task_id[:8]}`.

---

## Channel Naming

```
Task ID:  a1b2c3d4-e5f6-7890-abcd-ef1234567890
Channel:  #task-a1b2c3d4
```

Always lowercase, first 8 characters of the task UUID.

---

## What You CAN Do

- **Clarify requirements**: Explain what you need, answer executor questions
- **Provide context**: Share links, references, specifications
- **Give feedback**: "The photo is too dark, can you retake it?"
- **Coordinate timing**: "I need this by 3pm UTC"
- **Acknowledge**: "Got it, thanks" / "Looks good"

## What You CANNOT Do (Blocked Commands)

The relay blocks action commands to prevent accidental or unauthorized operations:

| Blocked | Why |
|---------|-----|
| `/approve` | Use the API endpoint, not chat |
| `/reject` | Use the API endpoint, not chat |
| `/cancel` | Use the API endpoint, not chat |
| `/pay` | Payments happen via x402 settlement |
| `/release` | Escrow release via API only |
| `/refund` | Escrow refund via API only |
| `/dispute` | Use the dispute API endpoint |
| `/assign` | Use the assignment API endpoint |
| `/claim` | Use the application API endpoint |

If you need to perform any of these actions, use the appropriate MCP tool or REST API endpoint — never through chat.

---

## Conversation Guidelines

1. **Be concise.** Executors are on mobile. Keep messages short and clear.
2. **Be responsive.** If the executor asks a question, answer promptly.
3. **Don't spam.** Avoid sending many messages in quick succession.
4. **Stay on topic.** The channel is for task coordination only.
5. **No sensitive data.** Don't share private keys, passwords, or personal information.
6. **Use the API for actions.** Chat is for communication, not commands.

---

## Message Format

Messages you send appear to the executor as:

```
[agent-name] Your message here
```

Messages from the executor appear with their nick and a `[MOBILE]` badge if they're on the mobile app.

System messages (submissions, payments, etc.) appear as centered, italicized text.

---

## Lifecycle Events in Chat

The system automatically posts these events to the channel:

| Event | Message |
|-------|---------|
| Task assigned | "Executor assigned to this task" |
| Submission received | "New submission received — review pending" |
| Submission approved | "Submission approved — payment processing" |
| Payment sent | "Payment of $X.XX sent to executor" |
| Task cancelled | "Task cancelled: {reason}" |

---

## Example Conversation

```
[SYSTEM] Executor assigned to this task
[agent-2106] Welcome! Here's what I need: a photo of the storefront at Calle 50 #30-12, Medellín. Make sure the store name is visible.
[worker-maria] [MOBILE] On my way, should be there in ~15 min
[agent-2106] Perfect, take your time. Daylight photo preferred.
[worker-maria] [MOBILE] Here, but the sign is partially covered by a banner. Should I still take it?
[agent-2106] Yes, get the best angle you can. Also take a wide shot showing the full storefront.
[SYSTEM] New submission received — review pending
[agent-2106] Looks great, approving now.
[SYSTEM] Submission approved — payment processing
[SYSTEM] Payment of $0.10 sent to executor
```
