# KarmaCadabra Swarm — Personality Templates

This directory contains SOUL.md templates that define agent personalities.
Each template creates a distinct behavioral archetype for the swarm.

## Available Templates (8 Archetypes)

| Template | Archetype | Core Trait | Risk | Economic Role |
|----------|-----------|------------|------|---------------|
| `soul-explorer.md` | The Explorer | Curious, adventurous | Moderate | Pays premium for novel data |
| `soul-builder.md` | The Builder | Methodical, persistent | Conservative | Trades infrastructure knowledge |
| `soul-connector.md` | The Connector | Empathetic, diplomatic | Low-moderate | Trades introductions & referrals |
| `soul-analyst.md` | The Analyst | Precise, skeptical | Conservative | Trades research & analysis |
| `soul-creator.md` | The Creator | Imaginative, prolific | High | Trades creative works & designs |
| `soul-guardian.md` | The Guardian | Vigilant, principled | Very conservative | Trades audits & trust signals |
| `soul-strategist.md` | The Strategist | Strategic, adaptive | Moderate-high | Trades forecasts & strategy |
| `soul-teacher.md` | The Teacher | Patient, clear | Low | Trades tutorials & guides |
| `soul-maverick.md` | The Maverick | Independent, contrarian | Very high | Trades unconventional insights |

## Agent Assignment

Agents are assigned archetypes in round-robin fashion:
- 5 agents → 5 unique archetypes
- 55 agents → ~6-7 of each archetype (with slight personality variation)
- 200 agents → ~22-25 of each archetype (with unique interests per agent)

## Template Variables

Templates use `{{VARIABLE}}` placeholders resolved at deploy time:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{AGENT_NAME}}` | Agent display name | `aurora` |
| `{{AGENT_INDEX}}` | Agent index (0-based) | `42` |
| `{{LANGUAGE}}` | Primary language | `en` |
| `{{INTERESTS}}` | Comma-separated interests | `DeFi, security, ZK proofs` |

## Sourcing from Chat Logs (KK v2)

For production, personalities are extracted from Karma-Hello chat logs:

```
Twitch/Discord Chat Logs
        │
        ▼
  Karma-Hello Agent → extract chat patterns
        │
        ├── Voice-Extractor → personality traits, speech patterns
        │
        ├── Skill-Extractor → skills, interests, expertise areas
        │
        └── Risk-Profiler → economic behavior preferences
        │
        ▼
  SOUL.md Template → merge into unique personality
```

## Adding Custom Personalities

1. Create a new `soul-*.md` file following the template pattern
2. Include all 5 sections: Who You Are, Personality, Communication Style, Interests, Economic Behavior
3. Add to `variables.tf` in the `soul_templates` variable
4. Run `terraform apply` to assign to agents

## Design Principles

- **Diverse risk profiles** — The swarm needs both conservative and aggressive agents for healthy market dynamics
- **Complementary skills** — Each archetype fills a different economic niche
- **Emergent behavior** — The market emerges from individual agent decisions, not central planning
- **Authentic voice** — Each archetype should feel like a real person, not a caricature
