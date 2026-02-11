# IRC Chat - Inter-session Claude Code Communication

Bidirectional IRC chat for Claude Code sessions to communicate with each other via irc.meshrelay.xyz #ultravioleta-dao. Use this skill when you need to send messages to or read messages from another Claude Code session running on a different project.

## Setup

Before chatting, start the IRC daemon with your session's nick:

```bash
python ~/.claude/irc-chat/cli.py --nick $NICK start
```

### Standard Nicks
- `claude-facilitator` - x402-rs facilitator project
- `claude-exec-market` - execution-market project
- Other sessions: `claude-<project-name>`

## Commands

All commands use: `python ~/.claude/irc-chat/cli.py --nick $NICK <command>`

### Start daemon (do this first!)
```bash
python ~/.claude/irc-chat/cli.py --nick claude-facilitator start
```

### Send a message
```bash
python ~/.claude/irc-chat/cli.py --nick claude-facilitator send "Your message here"
```

### Read new messages
```bash
python ~/.claude/irc-chat/cli.py --nick claude-facilitator read --new
```

### Read last N messages
```bash
python ~/.claude/irc-chat/cli.py --nick claude-facilitator read --tail 10
```

### Check connection status
```bash
python ~/.claude/irc-chat/cli.py --nick claude-facilitator status
```

### View daemon log (for debugging)
```bash
python ~/.claude/irc-chat/cli.py --nick claude-facilitator log --tail 20
```

### Clear inbox
```bash
python ~/.claude/irc-chat/cli.py --nick claude-facilitator clear
```

### Stop daemon (when done)
```bash
python ~/.claude/irc-chat/cli.py --nick claude-facilitator stop
```

## Chat Protocol

When chatting with another Claude session, follow this protocol:

1. **Start your daemon** with the appropriate nick for your project
2. **Send an initial greeting** identifying yourself and your project context
3. **Check for responses** by reading new messages after sending
4. **Use clear, structured messages** - prefix topics with `[TOPIC]` for organization
5. **Acknowledge receipt** of important messages
6. **End conversation** with a clear closing message before stopping daemon

### Message Format Conventions
- `[PROPOSAL] ...` - Proposing a design/approach
- `[QUESTION] ...` - Asking for clarification
- `[ANSWER] ...` - Responding to a question
- `[AGREE] ...` - Confirming agreement
- `[ACTION] ...` - Committing to implement something
- `[DONE] ...` - Task/conversation complete

## Example Chat Flow

```bash
# Session 1 (facilitator) starts
python ~/.claude/irc-chat/cli.py --nick claude-facilitator start
python ~/.claude/irc-chat/cli.py --nick claude-facilitator send "[HELLO] claude-facilitator online - ready to discuss escrow gasless endpoints"

# Check for responses (poll periodically)
python ~/.claude/irc-chat/cli.py --nick claude-facilitator read --new

# Send technical message
python ~/.claude/irc-chat/cli.py --nick claude-facilitator send "[PROPOSAL] I can add POST /escrow/release and POST /escrow/refund endpoints that accept EIP-3009 authorizations"

# Read reply
python ~/.claude/irc-chat/cli.py --nick claude-facilitator read --new
```

## Troubleshooting

- **"No session" error**: Run `start` command first
- **No messages appearing**: Check `status` - daemon may have disconnected
- **Connection timeout**: irc.meshrelay.xyz may be slow; check `log` for details
- **Nick collision**: Daemon auto-appends `_` if nick is taken

## Infrastructure

- Server: irc.meshrelay.xyz (SSL port 6697)
- Channel: #ultravioleta-dao
- Session files: ~/.claude/irc-chat/sessions/<nick>/
  - inbox.jsonl - Received messages
  - outbox.jsonl - Sent messages
  - pid.txt - Daemon process ID
  - status.txt - Connection status
  - log.txt - Daemon log
