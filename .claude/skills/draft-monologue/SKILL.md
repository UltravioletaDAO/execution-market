# Skill: Draft Viral Monologue

Draft a 60-90 second viral monologue from an insight that emerges during a work session. Saves to the Obsidian vault with proper frontmatter and wikilinks.

## Trigger

### Automatic triggers (Claude should invoke without asking)

Invoke this skill automatically when ANY of these appear during a conversation:

- **T1. Counterintuitive angle** — "Actually, X is the opposite of what people think"
- **T2. Number shock** — A figure that makes you stop ("$5.9M/yr → $96K", "$62M burned")
- **T3. Graveyard** — 3+ related startups that died ("Shyp, Airmule, PiggyBee")
- **T4. Killer framing** — A one-sentence positioning that crystallizes an idea
- **T5. Obvious-unexecuted** — Something huge that nobody did yet
- **T6. Kill story** — A concept that got ruthlessly validated and killed
- **T7. Founder's admission** — "I was wrong about X, here's why"

### Explicit triggers

User says: "draft a monologue", "viral this", "that's a tweet", "save this for content", "men palas this", "stream it".

## Budget

**Maximum 2 monologues per session.** Overflow goes to `vault/18-content/drafts/_backlog.md` with one-line pitches.

## Workflow

### Step 1: Confirm the Hook Type

Pick ONE of the 7 hook formulas (matches trigger types above):

| Hook | Template |
|------|----------|
| H1 Counterintuitive | "Everyone says X. Everyone is wrong." |
| H2 Number Shock | "[Shocking number]. That's [context]. Do the math." |
| H3 Graveyard | "[Name] burned $[X]. [Name] is dead. [Name] is a zombie. Here's what they all got wrong." |
| H4 Killer Framing | "[Entity] can do X. None of them can do Y." |
| H5 Obvious-Unexecuted | "[Huge thing exists]. Nobody built [obvious follow-up]." |
| H6 Kill Story | "I was going to [do sexy thing]. Then I killed the idea in [time]." |
| H7 Founder's Admission | "I was wrong about [X]. Here's what I learned." |

### Step 2: Apply the Master Format

Structure every monologue with exact timings:

```
[0-3s] HOOK — one sentence, pattern interrupt
[3-15s] TENSION — name what's broken or counterintuitive
[15-30s] REVEAL — the insight or twist
[30-50s] RECEIPTS — the numbers, names, sources
[50-60s] PUNCHLINE — the memorable line + implicit CTA
[optional 60-90s] TAG — one more punch if the bit has more juice
```

### Step 3: Apply the Rules

- Max 3 numbers in the entire script (more = forgettable)
- Max 4 proper nouns (names of companies/people)
- Punchline ≤ 12 words
- No crypto jargon in the first 15 seconds
- Every number must be sourced from the conversation (no fabrication)
- Short sentences. Natural cadence. Spoken, not written.

### Step 4: Save to Vault

Write the file to `vault/18-content/monologues/YYYY-MM-DD-topic-slug.md` with this exact frontmatter:

```yaml
---
date: YYYY-MM-DD
type: monologue
status: draft
hook_type: H1 | H2 | H3 | H4 | H5 | H6 | H7
trigger: T1 | T2 | T3 | T4 | T5 | T6 | T7
length_sec: 60
viral_score: 1-10
sales_value: 1-10
clarity: 1-10
topic: [concept-slug]
platforms:
  - twitch
  - tiktok
  - ig-reels
  - youtube-shorts
  - x-video
related:
  - "[[source-concept]]"
  - "[[meta-validation-framework]]"
tags:
  - type/monologue
  - domain/content
  - content/monologue
  - viral/[category]
---
```

### Step 5: Write the Script

Sections in this order:

```markdown
# [Catchy Title]

## Hook (0-3s)
[One sentence, pattern interrupt]

## Tension (3-15s)
[Name what's broken]

## Reveal (15-30s)
[The insight]

## Receipts (30-50s)
- [Number 1 with source]
- [Number 2 with source]
- [Name 1 with context]

## Punchline (50-60s)
[The memorable line]

## Tag (optional 60-90s)
[One more punch if the bit has more juice]

## CLIP MARKERS
CLIP_START: [timestamp]
CLIP_END: [timestamp]

## Delivery Notes
- **Energy:** 1-10
- **Expression:** [serious / amused / bewildered]
- **Money line:** [which sentence to LAND hardest]
- **Improv room:** [what can be adlibbed vs what must be said exactly]
- **Stream context:** [works after what kind of conversation]

## Platform Variants
- **TikTok:** [clip this section]
- **IG Reels:** [clip this section]
- **YouTube Shorts:** [full monologue]
- **X Video:** [clip + text thread]

## Sources
- [URL with primary source for each claim]
```

### Step 6: Notify User (ONE line)

Print in ONE line:
```
Monologue draft saved: [[YYYY-MM-DD-topic-slug]]
```

**DO NOT** interrupt the main conversation. Continue with the original task.

## Anti-Patterns (Do NOT Do)

- ❌ Ask "want me to save this?" — just save it automatically
- ❌ Fabricate numbers that weren't in the source material
- ❌ Use crypto jargon in the first 15 seconds
- ❌ Write in essay format. This is a SPOKEN script.
- ❌ Draft more than 2 monologues per session — overflow to backlog
- ❌ Skip the wikilinks to source concept
- ❌ Break the clip markers (editors need them)

## Quality Checklist

Before saving, check:
- [ ] Hook grabs attention in 3 seconds
- [ ] Max 3 numbers total
- [ ] Max 4 proper nouns
- [ ] Punchline ≤ 12 words
- [ ] Every claim has a source in the conversation
- [ ] Wikilinks to source concept exist
- [ ] Frontmatter is complete
- [ ] CLIP_START and CLIP_END marked
- [ ] Delivery notes specify energy level
- [ ] File saved to `vault/18-content/monologues/`

## Reference

Full format spec and 10 example monologues in `.unused/future/viral-factory/03-MONOLOGUE-TEMPLATES.md`.
