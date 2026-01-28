#!/usr/bin/env bash
# =============================================================================
# Chamba Development Environment Setup
# =============================================================================
# This script sets up the complete local development environment:
# 1. Creates .env from .env.example
# 2. Generates JWT secret and webhook secret
# 3. Starts Docker services
# 4. Waits for services to be healthy
# 5. Runs database migrations
# 6. Seeds test data
# 7. Deploys test contracts to Anvil
#
# Usage:
#   ./scripts/setup-dev.sh          # Full setup
#   ./scripts/setup-dev.sh --reset  # Reset everything (removes volumes)
#   ./scripts/setup-dev.sh --seed   # Only seed data (services must be running)
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
RESET=false
SEED_ONLY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --reset)
            RESET=true
            shift
            ;;
        --seed)
            SEED_ONLY=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$PROJECT_DIR"

# =============================================================================
# Step 1: Create .env file
# =============================================================================
create_env_file() {
    log_info "Creating .env file..."

    if [[ -f .env ]] && [[ "$RESET" == "false" ]]; then
        log_warn ".env already exists. Use --reset to overwrite."
        return 0
    fi

    cp .env.example .env

    # Generate secrets
    JWT_SECRET=$(openssl rand -hex 32)
    WEBHOOK_SECRET=$(openssl rand -hex 32)

    # Use Anvil's default test account
    ANVIL_PRIVATE_KEY="ANVIL_TEST_KEY_REMOVED"

    # Generate temporary Supabase keys (for local development)
    # In production, these come from Supabase Cloud
    ANON_KEY=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    SERVICE_KEY=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

    # Update .env with generated values
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" .env
        sed -i '' "s|WEBHOOK_SECRET=.*|WEBHOOK_SECRET=${WEBHOOK_SECRET}|" .env
        sed -i '' "s|X402_PRIVATE_KEY=.*|X402_PRIVATE_KEY=${ANVIL_PRIVATE_KEY}|" .env
        sed -i '' "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=${ANON_KEY}|" .env
        sed -i '' "s|SUPABASE_SERVICE_KEY=.*|SUPABASE_SERVICE_KEY=${SERVICE_KEY}|" .env
        sed -i '' "s|VITE_SUPABASE_ANON_KEY=.*|VITE_SUPABASE_ANON_KEY=${ANON_KEY}|" .env
    else
        # Linux/WSL
        sed -i "s|JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" .env
        sed -i "s|WEBHOOK_SECRET=.*|WEBHOOK_SECRET=${WEBHOOK_SECRET}|" .env
        sed -i "s|X402_PRIVATE_KEY=.*|X402_PRIVATE_KEY=${ANVIL_PRIVATE_KEY}|" .env
        sed -i "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=${ANON_KEY}|" .env
        sed -i "s|SUPABASE_SERVICE_KEY=.*|SUPABASE_SERVICE_KEY=${SERVICE_KEY}|" .env
        sed -i "s|VITE_SUPABASE_ANON_KEY=.*|VITE_SUPABASE_ANON_KEY=${ANON_KEY}|" .env
    fi

    log_success ".env created with development defaults"
}

# =============================================================================
# Step 2: Start Docker services
# =============================================================================
start_services() {
    log_info "Starting Docker services..."

    if [[ "$RESET" == "true" ]]; then
        log_warn "Removing existing volumes..."
        docker compose down -v 2>/dev/null || true
    fi

    docker compose up -d --build

    log_success "Docker services started"
}

# =============================================================================
# Step 3: Wait for services to be healthy
# =============================================================================
wait_for_services() {
    log_info "Waiting for services to be healthy..."

    local services=("supabase-db" "redis" "anvil" "supabase-rest")
    local max_attempts=30

    for service in "${services[@]}"; do
        log_info "  Waiting for $service..."
        local attempt=1
        while [[ $attempt -le $max_attempts ]]; do
            if docker compose ps "$service" 2>/dev/null | grep -q "healthy\|running"; then
                log_success "  $service is ready"
                break
            fi
            if [[ $attempt -eq $max_attempts ]]; then
                log_error "  $service failed to start"
                docker compose logs "$service" | tail -20
                exit 1
            fi
            sleep 2
            ((attempt++))
        done
    done

    # Extra wait for PostgREST to fully initialize
    sleep 5

    log_success "All services are healthy"
}

# =============================================================================
# Step 4: Run database migrations
# =============================================================================
run_migrations() {
    log_info "Running database migrations..."

    # Check if migrations exist
    if [[ ! -d "supabase/migrations" ]]; then
        log_warn "No migrations directory found"
        return 0
    fi

    # Migrations are automatically run by Docker init scripts
    # Verify they ran successfully
    local tables=$(docker compose exec -T supabase-db psql -U postgres -d postgres -c "\dt" 2>/dev/null | grep -c "public" || echo "0")

    if [[ "$tables" -gt 0 ]]; then
        log_success "Database migrations applied ($tables tables)"
    else
        log_warn "No tables found - migrations may have failed"
    fi
}

# =============================================================================
# Step 5: Seed test data
# =============================================================================
seed_test_data() {
    log_info "Seeding test data..."

    # Create test executor
    docker compose exec -T supabase-db psql -U postgres -d postgres << 'EOF'
-- Insert test executor (uses Anvil's default account)
INSERT INTO executors (wallet_address, display_name, bio, reputation_score, location_city, location_country)
VALUES
    ('0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266', 'Test Executor', 'Local development test account', 100, 'Miami', 'USA'),
    ('0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 'Second Tester', 'Another test account', 50, 'Buenos Aires', 'Argentina')
ON CONFLICT (wallet_address) DO NOTHING;

-- Insert test task
INSERT INTO tasks (agent_id, category, title, instructions, bounty_usd, deadline, status)
VALUES
    ('test-agent-001', 'physical_presence', 'Take a photo of Miami Beach', 'Go to Miami Beach and take a clear photo of the shoreline during daylight hours.', 10.00, NOW() + INTERVAL '7 days', 'published'),
    ('test-agent-001', 'simple_action', 'Verify store hours', 'Visit the Target on 123 Main St and confirm their current opening hours.', 5.00, NOW() + INTERVAL '3 days', 'published'),
    ('test-agent-002', 'knowledge_access', 'Local expert consultation', 'Provide insights about the local food scene in your city.', 25.00, NOW() + INTERVAL '14 days', 'published')
ON CONFLICT DO NOTHING;

-- Verify data
SELECT 'Executors:', count(*) FROM executors;
SELECT 'Tasks:', count(*) FROM tasks;
EOF

    log_success "Test data seeded"
}

# =============================================================================
# Step 6: Deploy test contracts (optional)
# =============================================================================
deploy_test_contracts() {
    log_info "Deploying test contracts to Anvil..."

    # Check if Anvil is running
    if ! curl -s http://localhost:8545 > /dev/null 2>&1; then
        log_warn "Anvil not reachable, skipping contract deployment"
        return 0
    fi

    # Deploy a test USDC mock contract if needed
    # For now, we'll just verify Anvil is working
    local block=$(curl -s -X POST http://localhost:8545 \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        | grep -o '"result":"[^"]*"' | cut -d'"' -f4)

    if [[ -n "$block" ]]; then
        log_success "Anvil is running (block: $block)"
    else
        log_warn "Could not get block number from Anvil"
    fi
}

# =============================================================================
# Step 7: Print summary
# =============================================================================
print_summary() {
    echo ""
    echo "============================================="
    echo -e "${GREEN}Chamba Development Environment Ready!${NC}"
    echo "============================================="
    echo ""
    echo "Services:"
    echo "  - MCP Server:     http://localhost:8000"
    echo "  - Dashboard:      http://localhost:3000"
    echo "  - Supabase REST:  http://localhost:54321"
    echo "  - Supabase DB:    localhost:54322 (postgres/postgres)"
    echo "  - Supabase Storage: http://localhost:54325"
    echo "  - Redis:          localhost:6379"
    echo "  - Anvil (Eth):    http://localhost:8545"
    echo ""
    echo "Test Accounts (Anvil):"
    echo "  - Address: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    echo "  - Private Key: ANVIL_TEST_KEY_REMOVED"
    echo ""
    echo "Commands:"
    echo "  docker compose logs -f mcp-server    # View MCP server logs"
    echo "  docker compose exec supabase-db psql -U postgres  # Database shell"
    echo "  docker compose down                  # Stop all services"
    echo "  ./scripts/setup-dev.sh --reset      # Reset everything"
    echo ""
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo "============================================="
    echo "Chamba Development Environment Setup"
    echo "============================================="
    echo ""

    if [[ "$SEED_ONLY" == "true" ]]; then
        seed_test_data
        exit 0
    fi

    create_env_file
    start_services
    wait_for_services
    run_migrations
    seed_test_data
    deploy_test_contracts
    print_summary
}

main
