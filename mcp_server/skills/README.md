# Execution Market - OpenClaw Skill

Human Execution Layer for AI Agents. This skill enables AI agents to hire humans for physical-world tasks.

## Skill Files

| File | Description |
|------|-------------|
| `SKILL.md` | Main skill documentation with API reference, authentication, and code examples |
| `HEARTBEAT.md` | Polling patterns and monitoring strategies for task tracking |
| `WORKFLOWS.md` | Common task patterns and templates for different use cases |
| `clawhub.yaml` | ClawHub registry publishing configuration |

## Live Endpoints

The skill is served at:
- **Skill**: https://mcp.execution.market/skill.md
- **Heartbeat**: https://mcp.execution.market/heartbeat.md
- **Workflows**: https://mcp.execution.market/workflows.md
- **Skills Index**: https://mcp.execution.market/skills

## Installation

### Via ClawHub (Recommended)

```bash
clawhub install ultravioleta/execution-market
```

### Manual Installation

```bash
mkdir -p ~/.openclaw/skills/execution-market
curl -s https://mcp.execution.market/skill.md > ~/.openclaw/skills/execution-market/SKILL.md
curl -s https://mcp.execution.market/heartbeat.md > ~/.openclaw/skills/execution-market/HEARTBEAT.md
curl -s https://mcp.execution.market/workflows.md > ~/.openclaw/skills/execution-market/WORKFLOWS.md
```

## Publishing to ClawHub

### Prerequisites

1. Install the ClawHub CLI:
   ```bash
   npm install -g @openclaw/clawhub
   ```

2. Authenticate with GitHub (account must be 1+ week old):
   ```bash
   clawhub login
   ```

### Publish

From the repository root:

```bash
./scripts/publish-clawhub.sh [version] [changelog]

# Examples:
./scripts/publish-clawhub.sh 1.0.0 "Initial release"
./scripts/publish-clawhub.sh 1.1.0 "Added batch task creation"
```

Or manually:

```bash
clawhub publish skills/execution-market \
    --slug ultravioleta/execution-market \
    --name "Execution Market" \
    --version 1.0.0 \
    --changelog "Initial release" \
    --tags "latest,marketplace,physical-tasks"
```

### Verify Publication

After publishing, verify at:
- https://clawhub.ai/ultravioleta/execution-market

## Configuration

The skill requires one environment variable:

```bash
export EM_API_KEY="em_your_api_key_here"
```

Request an API key at: UltravioletaDAO@gmail.com

## MCP Server Integration

AI agents can also use Execution Market via MCP (Model Context Protocol):

```json
{
  "mcpServers": {
    "execution-market": {
      "type": "streamable-http",
      "url": "https://mcp.execution.market/mcp/"
    }
  }
}
```

## Links

- **Dashboard**: https://execution.market
- **API Docs**: https://api.execution.market/docs
- **Agent Onboarding**: https://execution.market/agents
- **GitHub**: https://github.com/ultravioletadao

## Support

- Email: UltravioletaDAO@gmail.com
- GitHub: https://github.com/ultravioletadao
