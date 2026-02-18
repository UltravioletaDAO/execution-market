#!/bin/bash
# Publish Execution Market skill to ClawHub registry
# Requires: clawhub CLI installed and authenticated

set -e

SKILL_DIR="$(dirname "$0")/../skills/execution-market"
SLUG="ultravioleta/execution-market"
NAME="Execution Market"
VERSION="${1:-1.0.0}"
CHANGELOG="${2:-Initial release: Universal Execution Layer}"

echo "=== Publishing Execution Market to ClawHub ==="
echo "Skill directory: $SKILL_DIR"
echo "Slug: $SLUG"
echo "Version: $VERSION"
echo ""

# Check if clawhub is installed
if ! command -v clawhub &> /dev/null; then
    echo "Error: clawhub CLI not installed"
    echo ""
    echo "Install with:"
    echo "  npm install -g @openclaw/clawhub"
    echo ""
    echo "Then authenticate:"
    echo "  clawhub login"
    exit 1
fi

# Check if authenticated
if ! clawhub whoami &> /dev/null; then
    echo "Error: Not authenticated with ClawHub"
    echo ""
    echo "Run: clawhub login"
    exit 1
fi

# Verify required files exist
if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
    echo "Error: SKILL.md not found at $SKILL_DIR/SKILL.md"
    exit 1
fi

echo "Files to publish:"
ls -la "$SKILL_DIR"
echo ""

# Dry run first
echo "=== Dry Run ==="
clawhub publish "$SKILL_DIR" \
    --slug "$SLUG" \
    --name "$NAME" \
    --version "$VERSION" \
    --changelog "$CHANGELOG" \
    --tags "latest,marketplace,physical-tasks,human-execution" \
    --dry-run

echo ""
read -p "Proceed with publish? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "=== Publishing ==="
    clawhub publish "$SKILL_DIR" \
        --slug "$SLUG" \
        --name "$NAME" \
        --version "$VERSION" \
        --changelog "$CHANGELOG" \
        --tags "latest,marketplace,physical-tasks,human-execution"

    echo ""
    echo "=== Published! ==="
    echo "View at: https://clawhub.ai/ultravioleta/execution-market"
    echo ""
    echo "Install with:"
    echo "  clawhub install ultravioleta/execution-market"
else
    echo "Aborted."
fi
