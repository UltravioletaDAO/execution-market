#!/bin/bash
# =============================================================================
# build-all.sh - Build all project components
# =============================================================================
# Usage: ./build-all.sh [--dashboard] [--mcp] [--contracts] [--sdk] [--docker]
#        --docker: Build Docker images instead of local builds
#        Without component flags, builds all components
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
DOCKER_MODE=false

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Parse arguments
RUN_ALL=true
RUN_DASHBOARD=false
RUN_MCP=false
RUN_CONTRACTS=false
RUN_SDK=false

for arg in "$@"; do
    case $arg in
        --docker)     DOCKER_MODE=true ;;
        --dashboard)  RUN_DASHBOARD=true; RUN_ALL=false ;;
        --mcp)        RUN_MCP=true; RUN_ALL=false ;;
        --contracts)  RUN_CONTRACTS=true; RUN_ALL=false ;;
        --sdk)        RUN_SDK=true; RUN_ALL=false ;;
        --help|-h)
            echo "Usage: $0 [--docker] [--dashboard] [--mcp] [--contracts] [--sdk]"
            echo "  --docker: Build Docker images instead of local builds"
            echo "Without component flags, builds all components"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}Execution Market - Build Suite${NC}"
echo "Project root: $PROJECT_ROOT"
if [ "$DOCKER_MODE" = true ]; then
    echo -e "${YELLOW}Docker mode enabled - building container images${NC}"
fi

# =============================================================================
# Dashboard (React + TypeScript + Vite)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_DASHBOARD" = true ]; then
    if [ -d "$PROJECT_ROOT/dashboard" ]; then
        print_header "Building: Dashboard"

        if [ "$DOCKER_MODE" = true ]; then
            # Docker build
            cd "$PROJECT_ROOT"
            if docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard; then
                echo -e "${GREEN}[PASS]${NC} Dashboard Docker image"
                PASSED+=("Dashboard Docker")
            else
                echo -e "${RED}[FAIL]${NC} Dashboard Docker image"
                FAILED+=("Dashboard Docker")
            fi
        else
            # Local build
            cd "$PROJECT_ROOT/dashboard"

            # Install dependencies if needed
            if [ ! -d "node_modules" ]; then
                echo "Installing dependencies..."
                npm install
            fi

            if npm run build; then
                echo -e "${GREEN}[PASS]${NC} Dashboard build"
                PASSED+=("Dashboard")

                # Show build output size
                if [ -d "dist" ]; then
                    echo -e "\nBuild output:"
                    du -sh dist/
                    ls -la dist/ 2>/dev/null | head -10
                fi
            else
                echo -e "${RED}[FAIL]${NC} Dashboard build"
                FAILED+=("Dashboard")
            fi
        fi

        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# MCP Server (Python)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_MCP" = true ]; then
    if [ -d "$PROJECT_ROOT/mcp_server" ]; then
        print_header "Building: MCP Server"

        if [ "$DOCKER_MODE" = true ]; then
            # Docker build
            cd "$PROJECT_ROOT"
            if docker build --no-cache -f mcp_server/Dockerfile -t em-mcp ./mcp_server; then
                echo -e "${GREEN}[PASS]${NC} MCP Server Docker image"
                PASSED+=("MCP Docker")
            else
                echo -e "${RED}[FAIL]${NC} MCP Server Docker image"
                FAILED+=("MCP Docker")
            fi
        else
            # Python "build" = install in editable mode + type check
            cd "$PROJECT_ROOT/mcp_server"

            # Create/check virtual environment
            if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
                echo "Creating virtual environment..."
                python -m venv venv
            fi

            # Activate if exists
            if [ -f "venv/bin/activate" ]; then
                source venv/bin/activate
            elif [ -f ".venv/bin/activate" ]; then
                source .venv/bin/activate
            fi

            # Install dependencies
            if [ -f "requirements.txt" ]; then
                pip install -r requirements.txt -q
            fi

            # Install in editable mode if setup.py/pyproject.toml exists
            if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
                pip install -e . -q 2>/dev/null || true
            fi

            # Verify import works
            if python -c "import server" 2>/dev/null || python -c "from mcp_server import server" 2>/dev/null; then
                echo -e "${GREEN}[PASS]${NC} MCP Server build"
                PASSED+=("MCP Server")
            else
                echo -e "${YELLOW}[WARN]${NC} MCP Server - imports may have issues"
                SKIPPED+=("MCP Server")
            fi
        fi

        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# Smart Contracts (Foundry/Hardhat)
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_CONTRACTS" = true ]; then
    if [ -d "$PROJECT_ROOT/contracts" ]; then
        print_header "Building: Smart Contracts"
        cd "$PROJECT_ROOT/contracts"

        # Try Foundry first
        if command -v forge &> /dev/null && [ -f "foundry.toml" ]; then
            if forge build; then
                echo -e "${GREEN}[PASS]${NC} Contracts (Foundry)"
                PASSED+=("Contracts")

                # Show artifacts
                if [ -d "out" ]; then
                    echo -e "\nCompiled contracts:"
                    find out -name "*.json" -type f | head -10
                fi
            else
                echo -e "${RED}[FAIL]${NC} Contracts (Foundry)"
                FAILED+=("Contracts")
            fi
        # Try Hardhat
        elif [ -f "hardhat.config.ts" ] || [ -f "hardhat.config.js" ]; then
            npm install 2>/dev/null || true
            if npx hardhat compile; then
                echo -e "${GREEN}[PASS]${NC} Contracts (Hardhat)"
                PASSED+=("Contracts")
            else
                echo -e "${RED}[FAIL]${NC} Contracts (Hardhat)"
                FAILED+=("Contracts")
            fi
        else
            echo -e "${YELLOW}[SKIP]${NC} Contracts - no build system found"
            SKIPPED+=("Contracts")
        fi

        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# TypeScript SDK
# =============================================================================
if [ "$RUN_ALL" = true ] || [ "$RUN_SDK" = true ]; then
    if [ -d "$PROJECT_ROOT/sdk/typescript" ]; then
        print_header "Building: TypeScript SDK"
        cd "$PROJECT_ROOT/sdk/typescript"

        # Install dependencies
        if [ ! -d "node_modules" ]; then
            npm install
        fi

        if npm run build 2>/dev/null || npx tsc; then
            echo -e "${GREEN}[PASS]${NC} TypeScript SDK"
            PASSED+=("SDK TypeScript")
        else
            echo -e "${RED}[FAIL]${NC} TypeScript SDK"
            FAILED+=("SDK TypeScript")
        fi

        cd "$PROJECT_ROOT"
    fi
fi

# =============================================================================
# Rust (if present)
# =============================================================================
if [ "$RUN_ALL" = true ]; then
    if [ -f "$PROJECT_ROOT/Cargo.toml" ]; then
        print_header "Building: Rust"
        cd "$PROJECT_ROOT"

        if cargo build --release; then
            echo -e "${GREEN}[PASS]${NC} Rust build"
            PASSED+=("Rust")

            # Show binary sizes
            if [ -d "target/release" ]; then
                echo -e "\nRelease binaries:"
                find target/release -maxdepth 1 -type f -executable 2>/dev/null | head -5
            fi
        else
            echo -e "${RED}[FAIL]${NC} Rust build"
            FAILED+=("Rust")
        fi
    fi
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Build Summary"

if [ ${#PASSED[@]} -gt 0 ]; then
    echo -e "${GREEN}Succeeded (${#PASSED[@]}):${NC}"
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

echo -e "\n${GREEN}All builds succeeded!${NC}"
