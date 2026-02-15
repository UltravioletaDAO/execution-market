# KarmaCadabra Swarm — Personality Templates

This directory contains SOUL.md templates that define agent personalities.

## Available Templates

| Template | Archetype | Traits | Risk |
|----------|-----------|--------|------|
| `soul-explorer.md` | The Explorer | curious, adventurous, open-minded | moderate |
| `soul-builder.md` | The Builder | methodical, persistent, detail-oriented | conservative |

## Adding Custom Personalities

1. Create a new `soul-*.md` file following the template pattern
2. Add the personality to `variables.tf` in the `soul_templates` variable
3. Run `terraform apply` to assign the new personality to agents

## Sourcing from Chat Logs

For KK v2, personalities should be extracted from Karma-Hello chat logs.
Use the Skill-Extractor and Voice-Extractor agents to generate SOUL.md
files from real community member data.

### Extraction Pipeline

```
Twitch/Discord Chat Logs
        │
        ▼
  Karma-Hello Agent → extract chat patterns
        │
        ▼
  Voice-Extractor → personality profile
        │
        ▼
  Skill-Extractor → skills & interests
        │
        ▼
  SOUL.md Template → merge into personality
```

## Template Variables

Templates can use the following `{{VARIABLE}}` placeholders:

| Variable | Description |
|----------|-------------|
| `{{AGENT_NAME}}` | Agent display name |
| `{{AGENT_INDEX}}` | Agent index number |
| `{{LANGUAGE}}` | Primary language |
| `{{INTERESTS}}` | Comma-separated interests |
