#!/bin/bash
# =============================================================================
# lint-all.sh - Run linters for all project components
# =============================================================================
# Usage: ./lint-all.sh [--fix] [--dashboard] [--mcp] [--scripts] [--contracts]
#        --fix: Auto-fix issues where possible
#        Without component flags, runs all linters
# =============================================================================

set -e  # Exit on first error

# Project root (relative to this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
PASSED=()
FAILED=()
SKIPPED=()

# Options
FIX_MODE=false

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Parse arguments
RUN_ALL=true
RUN_DASHBOARD=false
RUN_MCP=false
RUN_SCRIPTS=false
RUN_CONTRACTS=false

for arg in "$@"; do
    case $arg in
        --fix)        FIX_MODE=true ;;
        --dashboard)  RUN_DASHBOARD=true; RUN_ALL=false ;;
        --mcp)        RUN_MCP=true; RUN_ALL=false ;;
        --scripts)    RUN_SCRIPTS=true; RUN_ALL=false ;;
        --contracts)  RUN_CONTRACTS=true; RUN_ALL=false ;;
        --help|-h)
            echo "Usage: $0 [--fix] [--dashboard] [--mcp] [--scripts] [--contracts]"
            echo "  --fix: Auto-fix issues where possible"
            echo "Without component flags, runs all linters"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}Execution Market - Lint Suite${NC}"
echo "Project root: $PROJECT_ROOT"
if [ "$FIX_MODE" = true ]; then
    echo -e "${YELLOW}Fix mode enabled - will auto-fix issues${NC}"
fi

# =============================================================================
# Dashboard (ESLint + TypeScript)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_DASHBOARD" = true ]; then
    if [ -d "$PROJECT_ROOT/dashboard" ]; then
        print_header "Linting: Dashboard (ESLint + TypeScript)"
        cd "$PROJECT_ROOT/dashboard"

        # ESLint
        if [ "$FIX_MODE" = true ]; then
            if npm run lint -- --fix 2>/dev/null || npx eslint src --ext .ts,.tsx --fix; then
                echo -e "${GREEN}[PASS]${NC} Dashboard ESLint (with fixes)"
                PASSED+=("Dashboard ESLint")
            else
                echo -e "${RED}[FAIL]${NC} Dashboard ESLint"
                FAILED+=("Dashboard ESLint")
            fi
        else
            if npm run lint 2>/dev/null || npx eslint src --ext .ts,.tsx; then
                echo -e "${GREEN}[PASS]${NC} Dashboard ESLint"
                PASSED+=("Dashboard ESLint")
            else
                echo -e "${RED}[FAIL]${NC} Dashboard ESLint"
                FAILED+=("Dashboard ESLint")
            fi
        fi

        # TypeScript type checking
        if npx tsc --noEmit; then
            echo -e "${GREEN}[PASS]${NC} Dashboard TypeScript"
            PASSED+=("Dashboard TypeScript")
        else
            echo -e "${RED}[FAIL]${NC} Dashboard TypeScript"
            FAILED+=("Dashboard TypeScript")
        fi

        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# MCP Server (Python - black, mypy, ruff)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_MCP" = true ]; then
    if [ -d "$PROJECT_ROOT/mcp_server" ]; then
        print_header "Linting: MCP Server (Python)"
        cd "$PROJECT_ROOT/mcp_server"

        # Black (formatter)
        if command -v black &> /dev/null; then
            if [ "$FIX_MODE" = true ]; then
                if black . --quiet; then
                    echo -e "${GREEN}[PASS]${NC} MCP Server Black (formatted)"
                    PASSED+=("MCP Black")
                else
                    echo -e "${RED}[FAIL]${NC} MCP Server Black"
                    FAILED+=("MCP Black")
                fi
            else
                if black . --check --quiet; then
                    echo -e "${GREEN}[PASS]${NC} MCP Server Black"
                    PASSED+=("MCP Black")
                else
                    echo -e "${YELLOW}[WARN]${NC} MCP Server Black - needs formatting (run with --fix)"
                    SKIPPED+=("MCP Black")
                fi
            fi
        else
            echo -e "${YELLOW}[SKIP]${NC} MCP Server Black - not installed"
            SKIPPED+=("MCP Black")
        fi

        # Ruff (fast linter, replaces flake8/isort)
        if command -v ruff &> /dev/null; then
            if [ "$FIX_MODE" = true ]; then
                if ruff check . --fix; then
                    echo -e "${GREEN}[PASS]${NC} MCP Server Ruff (with fixes)"
                    PASSED+=("MCP Ruff")
                else
                    echo -e "${RED}[FAIL]${NC} MCP Server Ruff"
                    FAILED+=("MCP Ruff")
                fi
            else
                if ruff check .; then
                    echo -e "${GREEN}[PASS]${NC} MCP Server Ruff"
                    PASSED+=("MCP Ruff")
                else
                    echo -e "${RED}[FAIL]${NC} MCP Server Ruff"
                    FAILED+=("MCP Ruff")
                fi
            fi
        else
            echo -e "${YELLOW}[SKIP]${NC} MCP Server Ruff - not installed"
            SKIPPED+=("MCP Ruff")
        fi

        # MyPy (type checking)
        if command -v mypy &> /dev/null; then
            if mypy . --ignore-missing-imports 2>/dev/null; then
                echo -e "${GREEN}[PASS]${NC} MCP Server MyPy"
                PASSED+=("MCP MyPy")
            else
                echo -e "${RED}[FAIL]${NC} MCP Server MyPy"
                FAILED+=("MCP MyPy")
            fi
        else
            echo -e "${YELLOW}[SKIP]${NC} MCP Server MyPy - not installed"
            SKIPPED+=("MCP MyPy")
        fi

        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# Blockchain Scripts (TypeScript/ESLint)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_SCRIPTS" = true ]; then
    if [ -d "$PROJECT_ROOT/scripts" ]; then
        print_header "Linting: Scripts (TypeScript)"
        cd "$PROJECT_ROOT/scripts"

        # TypeScript type checking
        if [ -f "tsconfig.json" ]; then
            if npx tsc --noEmit; then
                echo -e "${GREEN}[PASS]${NC} Scripts TypeScript"
                PASSED+=("Scripts TypeScript")
            else
                echo -e "${RED}[FAIL]${NC} Scripts TypeScript"
                FAILED+=("Scripts TypeScript")
            fi
        else
            echo -e "${YELLOW}[SKIP]${NC} Scripts - no tsconfig.json"
            SKIPPED+=("Scripts TypeScript")
        fi

        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# Smart Contracts (Solhint/Foundry fmt)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_CONTRACTS" = true ]; then
    if [ -d "$PROJECT_ROOT/contracts" ]; then
        print_header "Linting: Smart Contracts"
        cd "$PROJECT_ROOT/contracts"

        # Foundry fmt
        if command -v forge &> /dev/null && [ -f "foundry.toml" ]; then
            if [ "$FIX_MODE" = true ]; then
                if forge fmt; then
                    echo -e "${GREEN}[PASS]${NC} Contracts Forge fmt (formatted)"
                    PASSED+=("Contracts fmt")
                else
                    echo -e "${RED}[FAIL]${NC} Contracts Forge fmt"
                    FAILED+=("Contracts fmt")
                fi
            else
                if forge fmt --check; then
                    echo -e "${GREEN}[PASS]${NC} Contracts Forge fmt"
                    PASSED+=("Contracts fmt")
                else
                    echo -e "${YELLOW}[WARN]${NC} Contracts Forge fmt - needs formatting"
                    SKIPPED+=("Contracts fmt")
                fi
            fi
        fi

        # Solhint
        if command -v solhint &> /dev/null || [ -f "node_modules/.bin/solhint" ]; then
            SOLHINT_CMD="solhint"
            [ -f "node_modules/.bin/solhint" ] && SOLHINT_CMD="npx solhint"

            if $SOLHINT_CMD 'src/**/*.sol' 2>/dev/null; then
                echo -e "${GREEN}[PASS]${NC} Contracts Solhint"
                PASSED+=("Contracts Solhint")
            else
                echo -e "${RED}[FAIL]${NC} Contracts Solhint"
                FAILED+=("Contracts Solhint")
            fi
        else
            echo -e "${YELLOW}[SKIP]${NC} Contracts Solhint - not installed"
            SKIPPED+=("Contracts Solhint")
        fi

        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# Rust (if present)
# =============================================================================
if [ "$RUN_ALL" = true ]; then
    if [ -f "$PROJECT_ROOT/Cargo.toml" ]; then
        print_header "Linting: Rust (rustfmt + clippy)"
        cd "$PROJECT_ROOT"

        # Rustfmt
        if command -v rustfmt &> /dev/null; then
            if [ "$FIX_MODE" = true ]; then
                if cargo fmt; then
                    echo -e "${GREEN}[PASS]${NC} Rust rustfmt (formatted)"
                    PASSED+=("Rust fmt")
                else
                    echo -e "${RED}[FAIL]${NC} Rust rustfmt"
                    FAILED+=("Rust fmt")
                fi
            else
                if cargo fmt -- --check; then
                    echo -e "${GREEN}[PASS]${NC} Rust rustfmt"
                    PASSED+=("Rust fmt")
                else
                    echo -e "${YELLOW}[WARN]${NC} Rust rustfmt - needs formatting"
                    SKIPPED+=("Rust fmt")
                fi
            fi
        fi

        # Clippy
        if command -v cargo-clippy &> /dev/null || cargo clippy --version &> /dev/null; then
            if [ "$FIX_MODE" = true ]; then
                if cargo clippy --fix --allow-dirty --allow-staged -- -D warnings; then
                    echo -e "${GREEN}[PASS]${NC} Rust clippy (with fixes)"
                    PASSED+=("Rust clippy")
                else
                    echo -e "${RED}[FAIL]${NC} Rust clippy"
                    FAILED+=("Rust clippy")
                fi
            else
                if cargo clippy -- -D warnings; then
                    echo -e "${GREEN}[PASS]${NC} Rust clippy"
                    PASSED+=("Rust clippy")
                else
                    echo -e "${RED}[FAIL]${NC} Rust clippy"
                    FAILED+=("Rust clippy")
                fi
            fi
        fi
    fi
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Lint Summary"

if [ ${#PASSED[@]} -gt 0 ]; then
    echo -e "${GREEN}Passed (${#PASSED[@]}):${NC}"
    for item in "${PASSED[@]}"; do
        echo -e "  ${GREEN}✓${NC} $item"
    done
fi

if [ ${#SKIPPED[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}Skipped/Warnings (${#SKIPPED[@]}):${NC}"
    for item in "${SKIPPED[@]}"; do
        echo -e "  ${YELLOW}○${NC} $item"
    done
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    echo -e "\n${RED}Failed (${#FAILED[@]}):${NC}"
    for item in "${FAILED[@]}"; do
        echo -e "  ${RED}✗${NC} $item"
    done
    exit 1
fi

echo -e "\n${GREEN}All linters passed!${NC}"
