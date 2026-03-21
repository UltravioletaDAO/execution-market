---
name: tweet
description: Create X/Twitter threads with image prompts and optional AI image generation. Use when user says "tweet", "thread", "create a tweet", or wants to prepare social media content for @ExecutionMarket.
---

# Tweet Thread Creator

Create X/Twitter threads for @ExecutionMarket with text-to-image prompts and optional AI-generated images.

## Output Structure

Every thread lives under `docs/tweets/<thread-name>/`:

```
docs/tweets/<thread-name>/
├── thread.md          # Full thread text (copy-paste ready for X)
├── 1.txt              # Image prompt for post 1
├── 1.png              # Generated image for post 1 (if --generate-images)
├── 2.txt              # Image prompt for post 2
├── 2.png              # ...
├── ...
└── N.txt
```

**Naming rules:**
- `<thread-name>`: kebab-case, short, descriptive (e.g., `first-full-flow`, `openclaw-launch`, `escrow-deepdive`)
- Prompt files: `N.txt` where N matches the post number in thread.md
- Image files: `N.png` matching the prompt number
- Thread text: always `thread.md`

## Workflow

### Step 1: Understand the Topic

Ask the user (or infer from context):
- What is the thread about?
- What tone? (narrative story, technical breakdown, announcement, hype)
- Any specific transactions, links, or data to include?
- How many posts? (default: 8-12 for a full thread)

### Step 2: Write the Thread (`thread.md`)

Create `docs/tweets/<thread-name>/thread.md` with:

```markdown
# Thread Title (internal reference, not posted)

> Description of what this thread covers.

---

## Post 1 (Hook)

Tweet text here...

---

## Post 2 (Beat Name)

Tweet text here...

---
...
```

**Thread writing guidelines:**
- **Post 1** is always the hook — must grab attention in first line
- Each post should stand alone but advance the narrative
- Include BaseScan links, contract addresses, or data where relevant
- Keep posts under 280 characters when possible (X allows longer with Premium)
- Use line breaks for readability
- End with a closing post that includes `https://execution.market`
- Tag relevant accounts: `@base`, `@UltravioletaDAO`, `@ExecutionMarket`

**Tone for @ExecutionMarket:**
- Confident but not arrogant
- Technical but accessible — show, don't lecture
- Story-driven when possible — humans connect with narratives
- Always include verifiable proof (tx hashes, links, contract addresses)

### Step 3: Generate Image Prompts (`N.txt`)

For each post, create a `N.txt` file with a text-to-image prompt.

**Style guide for Execution Market visuals:**
- Color palette: deep ultraviolet purple (#7B2FBE), electric blue (#0052FF — Base chain), white, black
- Aesthetic: cinematic, photorealistic base with subtle digital/holographic overlays
- Aspect ratio: 16:9 (default for X timeline)
- No text baked into images (text goes in the tweet itself)
- Mix physical world + digital elements when the story involves both
- Consistent visual language across the entire thread

**Prompt structure:**
```
[Main subject]. [Scene/setting details]. [Lighting and atmosphere]. [Color palette notes]. [Style: photorealistic/cinematic/etc]. [Aspect ratio].
```

### Step 4 (Optional): Generate Images (`--generate-images`)

When the user provides an OpenAI API key and requests image generation:

```bash
# Environment variable
OPENAI_API_KEY=<key>

# Generate a single image
python .claude/skills/tweet/scripts/generate_image.py \
  --prompt-file docs/tweets/<thread-name>/N.txt \
  --output docs/tweets/<thread-name>/N.png \
  --size 1536x1024 \
  --model gpt-image-1

# Generate all images for a thread
python .claude/skills/tweet/scripts/generate_all.py \
  --thread-dir docs/tweets/<thread-name>/ \
  --model gpt-image-1 \
  --size 1536x1024
```

**Image generation notes:**
- Model: `gpt-image-1` (OpenAI's image generation model)
- Size: `1536x1024` for 16:9 aspect ratio
- Reads prompt from `N.txt`, saves to `N.png`
- Skips generation if `N.png` already exists (idempotent)
- Rate limit: ~5 requests/minute, script handles backoff

## Usage Examples

### Basic (text + prompts only)
```
User: /tweet
User: Create a thread about the new escrow feature
→ Creates docs/tweets/escrow-feature/thread.md + N.txt files
```

### With image generation
```
User: /tweet --generate-images
User: Thread about OpenClaw integration
→ Creates thread.md + N.txt + generates N.png via OpenAI API
```

### From existing content
```
User: /tweet
User: Turn docs/planning/SOME_DOC.md into a thread
→ Reads the doc, creates narrative thread + prompts
```

## Reference: Existing Threads

| Thread | Folder | Posts | Topic |
|--------|--------|-------|-------|
| First Full Flow | `docs/tweets/first-full-flow/` | 12 | E2E evidence: payments + escrow + identity + reputation |

## Important Rules

1. **Never auto-post** — Only create files. User posts manually.
2. **Always create thread.md first**, then prompts — thread text drives the visual narrative.
3. **One prompt per post** — Even if a post has no obvious visual, create a prompt anyway.
4. **Keep prompts visual, not textual** — No text/numbers baked into images. The tweet provides context.
5. **OpenClaw, not OpenCloud** — The AI agent platform is called OpenClaw.
6. **Ultravioleta branding** — Purple (#7B2FBE) is the primary accent. Blue (#0052FF) for Base chain references.
