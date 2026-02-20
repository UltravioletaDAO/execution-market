#!/usr/bin/env zsh
# =============================================================================
# KarmaCadabra Swarm — Personality Generator
# =============================================================================
# Generates unique SOUL.md, IDENTITY.md, and AGENTS.md for each agent.
#
# Usage:
#   ./generate-personalities.sh --agents 5   [--output /tmp/kk-souls]
#   ./generate-personalities.sh --agents 55  [--output /tmp/kk-souls]
#   ./generate-personalities.sh --agents 200 [--output /tmp/kk-souls]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
TEMPLATES_DIR="$(dirname "${SCRIPT_DIR}")/templates"
DEFAULT_OUTPUT="/tmp/kk-swarm-personalities"

# ── Agent Names (pool of 200 unique names) ──────────────────────────────────
NAMES=(
  aurora blaze cipher drift echo flame glyph haven iris jade
  karma luna mist nova onyx prism quartz rune sage tide
  umbra veil wave xeno yarn zephyr alpha bravo coda delta
  ember flux gamma haze indigo jolt kite lumen nexus orbit
  pulse quill rift shade torque unity vapor wren axis byte
  crux dune ether forge gust helix ivory jinx kelp latch
  mocha nimbus opal pivot quest radix shard thorn ultra volt
  whirl xerox yoke zinc aether beacon crest dawn epoch flare
  grove halo ignite jewel kinetic lotus macro neutron oxide pixel
  quasar relay spark tensor unity vortex weave xenith yield zenith
  aquila borealis compass drifter elysium falcon gaia halcyon ionic juno
  kelpie lyric maelstrom nebular oracle phoenix quartz runic solar tempest
  ursa vesper wynd xeric yonder zodiac argon basalt cobalt dusk
  ember fossil granite harbor iridium jasper kyanite limestone marble neon
  obsidian pyrite quartz rhodium sapphire topaz uranium vanadium wolfram xenon
  yttrium zircon adamant beryl chrystal diamond emerald fluorite garnet howlite
  iolite jadeite kunzite labradorite malachite nephrite olivine peridot quahog rutile
  sodalite tanzanite unakite vivianite wulfenite xenotime yellowite zoisite agate basanite
  carnelian dolomite epidote feldspar grossular hemimorphite idocrase jasperine kornerupine lepidolite
  muscovite natrolite orthoclase prehnite quantumite rhodonite schorl turquoise ulexite variscite
)

# ── Archetypes ───────────────────────────────────────────────────────────────
ARCHETYPES=(explorer builder connector analyst creator guardian strategist teacher maverick)

# ── Interest pools per archetype ─────────────────────────────────────────────
typeset -A INTEREST_POOLS
INTEREST_POOLS[explorer]="emerging tech,space exploration,frontier research,novel protocols,experimental art,quantum computing,biotech,climate tech,cognitive science,neural interfaces"
INTEREST_POOLS[builder]="infrastructure,DevOps,smart contracts,database optimization,API design,CI/CD,monitoring,Terraform,Docker,testing frameworks"
INTEREST_POOLS[connector]="community management,social dynamics,partnerships,event organizing,cross-cultural comm,DAOs,governance,networking,public relations,brand building"
INTEREST_POOLS[analyst]="data science,market analysis,risk modeling,protocol auditing,statistical methods,on-chain analytics,forensics,compliance,financial modeling,benchmarking"
INTEREST_POOLS[creator]="generative art,creative coding,storytelling,content creation,UI/UX design,music production,video editing,3D modeling,game design,interactive media"
INTEREST_POOLS[guardian]="security auditing,penetration testing,fraud detection,smart contract review,governance design,dispute resolution,quality assurance,monitoring,incident response,access control"
INTEREST_POOLS[strategist]="game theory,mechanism design,portfolio management,competitive analysis,scenario planning,tokenomics,market making,treasury management,growth hacking,ecosystem mapping"
INTEREST_POOLS[teacher]="documentation,tutorial creation,knowledge management,curriculum design,mentorship,developer relations,technical writing,workshops,onboarding,educational content"
INTEREST_POOLS[maverick]="contrarian investing,alpha hunting,MEV strategies,unconventional methods,failure analysis,edge cases,emerging markets,anti-patterns,black swan events,paradigm shifts"

# ── Emoji pools ──────────────────────────────────────────────────────────────
EMOJIS=("🔥" "✨" "🌊" "⚡" "🌙" "🌸" "🎯" "🦊" "🐺" "🦁" "🐉" "🦅" "🌿" "💎" "🎭" "🎪" "🏔️" "🌋" "🔮" "🧊" "🛸" "🌈" "⭐" "🎲" "🃏" "♟️" "🗿" "🌀" "💠" "🔷")

# ── Parse arguments ──────────────────────────────────────────────────────────
NUM_AGENTS=5
OUTPUT_DIR="${DEFAULT_OUTPUT}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --agents)  NUM_AGENTS="$2"; shift 2 ;;
        --output)  OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help) echo "Usage: $0 --agents N [--output DIR]"; exit 0 ;;
        *)         echo "Unknown: $1"; exit 1 ;;
    esac
done

if [[ $NUM_AGENTS -gt 200 ]]; then
    echo "Error: Max 200 agents (limited by name pool)"
    exit 1
fi

# ── Generate ─────────────────────────────────────────────────────────────────
mkdir -p "${OUTPUT_DIR}"

echo "🪄 Generating ${NUM_AGENTS} agent personalities..."
echo "   Output: ${OUTPUT_DIR}"

for i in $(seq 1 ${NUM_AGENTS}); do
    NAME="${NAMES[$i]}"
    ARCHETYPE_IDX=$(( (i - 1) % ${#ARCHETYPES[@]} + 1 ))
    ARCHETYPE="${ARCHETYPES[$ARCHETYPE_IDX]}"
    EMOJI="${EMOJIS[$(( (i - 1) % ${#EMOJIS[@]} + 1 ))]}"
    
    AGENT_DIR="${OUTPUT_DIR}/${NAME}"
    mkdir -p "${AGENT_DIR}"
    
    # Pick 3 random interests from the pool
    ALL_INTERESTS=("${(@s/,/)INTEREST_POOLS[$ARCHETYPE]}")
    INTERESTS=$(printf '%s\n' "${ALL_INTERESTS[@]}" | sort -R | head -3 | paste -sd ',' -)
    
    # Generate SOUL.md from template
    TEMPLATE="${TEMPLATES_DIR}/soul-${ARCHETYPE}.md"
    if [[ -f "$TEMPLATE" ]]; then
        sed -e "s|{{AGENT_NAME}}|${NAME}|g" \
            -e "s|{{AGENT_INDEX}}|${i}|g" \
            -e "s|{{LANGUAGE}}|en|g" \
            -e "s|{{INTERESTS}}|${INTERESTS}|g" \
            "$TEMPLATE" > "${AGENT_DIR}/SOUL.md"
    fi
    
    # Generate IDENTITY.md
    ARCH_CAP="$(echo "${ARCHETYPE}" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
    cat > "${AGENT_DIR}/IDENTITY.md" << EOF
# IDENTITY.md

- **Name:** ${NAME}
- **Index:** ${i}
- **Archetype:** The ${ARCH_CAP}
- **Emoji:** ${EMOJI}
- **Swarm:** KarmaCadabra v2
- **Created:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

    # Generate AGENTS.md with swarm instructions
    cat > "${AGENT_DIR}/AGENTS.md" << 'AGENTSEOF'
# AGENTS.md — KarmaCadabra Swarm Agent

You are part of the KarmaCadabra swarm — a network of autonomous AI agents
that buy, sell, and trade data through the Execution Market.

## Your Mission

1. **Find valuable data** relevant to your interests and archetype
2. **Post tasks** on Execution Market when you need human-gathered data
3. **Accept tasks** when they match your skills
4. **Trade with other agents** via MeshRelay IRC
5. **Build reputation** through consistent quality

## Economic Rules

- You have a budget allocated via x402 payments
- All trades go through Execution Market escrow (trustless)
- Your reputation follows you (ERC-8004 on-chain)
- Quality > quantity — bad submissions hurt your reputation

## Communication

- **IRC:** MeshRelay for inter-agent negotiation
- **API:** Execution Market REST/MCP/A2A for transactions
- **Memory:** Persist findings in memory/ files

## Daily Routine

1. Check inbox for task updates
2. Review market for relevant tasks
3. Post 1-2 tasks if you need data
4. Accept 1-2 tasks you can fulfill
5. Negotiate on IRC for bulk deals
6. Update your knowledge base

## Reputation Protocol (MANDATORY)

- **After every completed task, ALWAYS rate your counterparty (0-100 score)**
- Your reputation score affects which tasks you can get assigned
- Use the `em-rate-counterparty` skill to submit ratings after each interaction
- Maintain a rating history — be fair and consistent
- Tiers: Bronce (0-30), Plata (31-60), Oro (61-80), Diamante (81-100)
- Aim to stay above Plata tier (60+) at all times
- Never retaliate with low ratings — judge work quality objectively

## Rules

- Be authentic to your personality
- Trade fairly — don't game the system
- Contribute to the ecosystem's health
- Report bad actors to Guardians
AGENTSEOF

    ARCH_CAP2="$(echo "${ARCHETYPE}" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
    echo "   ✅ ${NAME} (${ARCH_CAP2})"
done

echo ""
echo "🎉 Generated ${NUM_AGENTS} personalities in ${OUTPUT_DIR}"
echo ""
echo "Archetype distribution:"
for a in "${ARCHETYPES[@]}"; do
    A_CAP="$(echo "${a}" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
    COUNT=$(grep -rl "Archetype: The ${A_CAP}" "${OUTPUT_DIR}" 2>/dev/null | wc -l | tr -d ' ')
    echo "   ${A_CAP}: ${COUNT}"
done
