# Skill: Fact Check Claim

Verify any numerical or factual claim against primary sources. Prevents the Tesla Fleet failure mode: writing strategy based on fabricated or outdated numbers.

## Trigger

User says: "fact check this", "verify this", "is this true", "source this", "verifica esto con fuentes", or when preparing any public-facing content (tweets, pitches, LinkedIn posts, mayor outreach).

Also trigger automatically when:
- Drafting a tweet with numbers
- Preparing a pitch for a real person/company
- Writing a scorecard (all numbers need sources)
- About to post anything on social media

## Purpose

100% accuracy for anything going to real audiences. A wrong number kills credibility instantly. Tesla pitch almost got posted with "9 cameras accessible via Fleet API" — which is false. Option B tweet had "500M km" — actual is 730M.

## Workflow

### Step 1: Identify Every Claim

Parse the text and extract every:
- Numerical claim (figures, percentages, dollar amounts, counts)
- Date claim (when something happened)
- Name claim (who did what, company status)
- Technical claim (what an API exposes, what a product does)
- Legal claim (what a law requires, regulatory status)

### Step 2: Rank by Risk

High risk (MUST verify):
- Figures over $1M
- Claims about what companies do/don't offer
- Technical API capabilities
- Legal status in any jurisdiction
- Competitor product features
- Anything in a pitch to a real person

Medium risk (SHOULD verify):
- Historical numbers (10+ years old may be outdated)
- Market size estimates
- Trend claims ("X is growing at Y%")

Low risk (can flag as "needs verification" without blocking):
- General context or framing
- Well-known public facts
- Analogies or comparisons

### Step 3: Search for Primary Sources

For each high-risk claim, use WebSearch to find:
1. Official company page, SEC filing, or press release
2. Government data (FHWA, USDOT, NYC Comptroller, etc.)
3. Reputable business press with recent date
4. Academic or industry research with methodology

**Rules:**
- Date on source MUST be checked. 2023 data is stale for 2026 claims.
- Blog posts and Twitter threads are NOT primary sources
- Estimates from consultants are third-tier unless methodology is cited
- If no primary source found, mark as UNVERIFIABLE and flag

### Step 4: Return Verdict Per Claim

For each claim, return:

```markdown
### CLAIM X: "[verbatim claim]"
**Verdict:** VERIFIED / PARTIALLY TRUE / INCORRECT / UNVERIFIABLE
**Actual figure/fact:** [if different from claim]
**Primary source:** [URL]
**Source date:** [when the source is from]
**Supporting sources:** [other URLs]
**Recommended rewrite:** [exact text with corrected value]
```

### Step 5: Produce Rewrite

At the end, output the full rewritten text with all corrections applied. The user should be able to copy-paste without further editing.

### Step 6: Red Flag List

Highlight any claim that:
- Was off by >10% (conspicuous error)
- Referenced a company that has rebranded/shut down
- Used outdated technical specifications
- Confused USD with local currency
- Would be spotted by an insider in the target audience

## Known Fact-Check Patterns (From Past Sessions)

### Tesla Fleet API
- ❌ "Fleet API exposes camera frames" → Wrong, Fleet Telemetry is scalar-only per `vehicle_data.proto`
- ❌ "9 cameras" → Only on Model 3/Y HW4. Cybertruck has 7. Model S/X has 8 with no cabin cam.
- ❌ "Tesla pays owners for data" → $0 today, never has

### Option B Ecosystem Claims
- ❌ "Hivemapper 500M km" → Actually 730M per beemaps.com live stats
- ❌ "VW ADMT" → Rebranded to MOIA America in January 2026
- ❌ "NATIX $60/mo" → Ceiling not average, paid in NATIX tokens (down 95% from ATH)
- ❌ "USB dashcam" → USB dongle; VX360 doesn't record, monetizes built-in cameras

### CITYaaS Original Draft
- ❌ "43,000 hydrants" → 47,000 per Miami-Dade WASD Jan 2025
- ❌ "$140K/year signal inspection" → $1.2-3.7M per USDOT National Traffic Signal Report Card
- ❌ "$774K/year hydrant inspection" → $5.9-9.4M at real contract rates ($125-200/hydrant)
- ❌ "NYC $300M pothole claims over 5 years" → $138M over 6 years per NYC Comptroller ClaimStat 2015
- ❌ "46,154 structurally deficient bridges" → ~42,000 per ARTBA 2024
- ❌ "NYC ADA $1.2B settlement" → $1.55B over 10 years per Disability Rights Advocates 2019

### CARRIERaaS Draft
- ❌ "Servientrega Bogota-Medellin document $6" → Actually $1.25 USD per enviotodo.com.co (confused USD with COP)
- ❌ "PiggyBee/Airmule did trustless multi-hop" → They did single-hop and died
- ❌ "Amazon Flex allows third-party packages" → Explicitly forbidden in driver agreement

## Anti-Patterns (Do NOT Do)

- ❌ Accept a number because it "sounds right"
- ❌ Skip source verification for "well-known" facts
- ❌ Use a blog post as primary source
- ❌ Skip the date check on sources
- ❌ Assume old data is still current
- ❌ Let the user post something without fact-checking first

## Output Format

```markdown
# Fact-Check Report: [Topic]

## Summary
- Total claims: X
- Verified: X
- Partially true: X
- Incorrect: X
- Unverifiable: X

## Per-Claim Verdicts
[... per-claim breakdown ...]

## Red Flags
[Anything an insider would immediately spot]

## Rewritten Text
[Full text with corrections applied, ready to paste]
```
