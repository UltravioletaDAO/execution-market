#!/bin/bash
# =============================================================================
# test-all.sh - Run tests for all project components
# =============================================================================
# Usage: ./test-all.sh [--dashboard] [--mcp] [--scripts] [--contracts] [--e2e]
#        Without flags, runs all tests
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

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

run_test() {
    local name="$1"
    local dir="$2"
    local cmd="$3"

    if [ ! -d "$dir" ]; then
        echo -e "${YELLOW}[SKIP]${NC} $name - directory not found: $dir"
        SKIPPED+=("$name")
        return
    fi

    print_header "Testing: $name"
    cd "$dir"

    if eval "$cmd"; then
        echo -e "\n${GREEN}[PASS]${NC} $name"
        PASSED+=("$name")
    else
        echo -e "\n${RED}[FAIL]${NC} $name"
        FAILED+=("$name")
    fi

    cd "$PROJECT_ROOT"
}

# Parse arguments
RUN_ALL=true
RUN_DASHBOARD=false
RUN_MCP=false
RUN_SCRIPTS=false
RUN_CONTRACTS=false
RUN_E2E=false

for arg in "$@"; do
    case $arg in
        --dashboard)  RUN_DASHBOARD=true; RUN_ALL=false ;;
        --mcp)        RUN_MCP=true; RUN_ALL=false ;;
        --scripts)    RUN_SCRIPTS=true; RUN_ALL=false ;;
        --contracts)  RUN_CONTRACTS=true; RUN_ALL=false ;;
        --e2e)        RUN_E2E=true; RUN_ALL=false ;;
        --help|-h)
            echo "Usage: $0 [--dashboard] [--mcp] [--scripts] [--contracts] [--e2e]"
            echo "Without flags, runs all tests"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}Execution Market - Test Suite${NC}"
echo "Project root: $PROJECT_ROOT"

# =============================================================================
# Dashboard (React + TypeScript + Vitest)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_DASHBOARD" = true ]; then
    run_test "Dashboard (Vitest)" \
        "$PROJECT_ROOT/dashboard" \
        "npm test -- --run"
fi

# =============================================================================
# MCP Server (Python + pytest)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_MCP" = true ]; then
    if [ -d "$PROJECT_ROOT/mcp_server" ]; then
        print_header "Testing: MCP Server (pytest)"
        cd "$PROJECT_ROOT/mcp_server"

        # Check for pytest
        if python -c "import pytest" 2>/dev/null; then
            if python -m pytest -v; then
                echo -e "\n${GREEN}[PASS]${NC} MCP Server"
                PASSED+=("MCP Server")
            else
                echo -e "\n${RED}[FAIL]${NC} MCP Server"
                FAILED+=("MCP Server")
            fi
        else
            echo -e "${YELLOW}[SKIP]${NC} MCP Server - pytest not installed"
            SKIPPED+=("MCP Server")
        fi
        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# Blockchain Scripts (TypeScript)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_SCRIPTS" = true ]; then
    if [ -d "$PROJECT_ROOT/scripts" ] && [ -f "$PROJECT_ROOT/scripts/package.json" ]; then
        # Check if test script exists
        if grep -q '"test"' "$PROJECT_ROOT/scripts/package.json"; then
            run_test "Scripts" "$PROJECT_ROOT/scripts" "npm test"
        else
            echo -e "${YELLOW}[SKIP]${NC} Scripts - no test script defined"
            SKIPPED+=("Scripts")
        fi
    fi
fi

# =============================================================================
# Smart Contracts (Foundry/Hardhat)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_CONTRACTS" = true ]; then
    if [ -d "$PROJECT_ROOT/contracts" ]; then
        print_header "Testing: Smart Contracts"
        cd "$PROJECT_ROOT/contracts"

        # Try Foundry first, then Hardhat
        if command -v forge &> /dev/null && [ -f "foundry.toml" ]; then
            if forge test; then
                echo -e "\n${GREEN}[PASS]${NC} Contracts (Foundry)"
                PASSED+=("Contracts")
            else
                echo -e "\n${RED}[FAIL]${NC} Contracts (Foundry)"
                FAILED+=("Contracts")
            fi
        elif [ -f "hardhat.config.ts" ] || [ -f "hardhat.config.js" ]; then
            if npx hardhat test; then
                echo -e "\n${GREEN}[PASS]${NC} Contracts (Hardhat)"
                PASSED+=("Contracts")
            else
                echo -e "\n${RED}[FAIL]${NC} Contracts (Hardhat)"
                FAILED+=("Contracts")
            fi
        else
            echo -e "${YELLOW}[SKIP]${NC} Contracts - no test framework found"
            SKIPPED+=("Contracts")
        fi
        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# E2E Tests (Playwright)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_E2E" = true ]; then
    if [ -d "$PROJECT_ROOT/dashboard" ] && [ -f "$PROJECT_ROOT/dashboard/playwright.config.ts" ]; then
        run_test "E2E (Playwright)" \
            "$PROJECT_ROOT/dashboard" \
            "npx playwright test"
    elif [ -d "$PROJECT_ROOT/e2e" ]; then
        run_test "E2E" "$PROJECT_ROOT/e2e" "npm test"
    fi
fi

# =============================================================================
# Rust (if present)
# =============================================================================
if [ "$RUN_ALL" = true ]; then
    if [ -f "$PROJECT_ROOT/Cargo.toml" ]; then
        print_header "Testing: Rust (cargo test)"
        cd "$PROJECT_ROOT"
        if cargo test; then
            echo -e "\n${GREEN}[PASS]${NC} Rust"
            PASSED+=("Rust")
        else
            echo -e "\n${RED}[FAIL]${NC} Rust"
            FAILED+=("Rust")
        fi
    fi
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Test Summary"

if [ ${#PASSED[@]} -gt 0 ]; then
    echo -e "${GREEN}Passed (${#PASSED[@]}):${NC}"
    for item in "${PASSED[@]}"; do
        echo -e "  ${GREEN}✓${NC} $item"
    done
fi

if [ ${#SKIPPED[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}Skipped (${#SKIPPED[@]}):${NC}"
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

echo -e "\n${GREEN}All tests passed!${NC}"
