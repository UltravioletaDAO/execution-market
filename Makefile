# =============================================================================
# Execution Market Makefile
# =============================================================================
# Common commands for local development
#
# Usage:
#   make help       - Show available commands
#   make up         - Start all services
#   make dev        - Start with development overrides
#   make down       - Stop all services
#   make logs       - View all logs
#   make reset      - Reset and restart
# =============================================================================

.PHONY: help up down dev prod logs logs-f status ps reset clean \
        build rebuild shell db-shell redis-cli anvil-console \
        test test-mcp test-dashboard lint format \
        migrate seed db-reset contracts-deploy \
        setup check-env

# Default target
.DEFAULT_GOAL := help

# Docker Compose files
COMPOSE_BASE := docker-compose.yml
COMPOSE_DEV := docker-compose.dev.yml
COMPOSE_PROD := docker-compose.prod.yml

# Docker Compose commands
DC := docker compose
DC_DEV := $(DC) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV)
DC_PROD := $(DC) -f $(COMPOSE_BASE) -f $(COMPOSE_PROD)

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# =============================================================================
# HELP
# =============================================================================

help: ## Show this help message
	@echo ""
	@echo "$(CYAN)Execution Market Development Commands$(RESET)"
	@echo "============================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Quick Start:$(RESET)"
	@echo "  1. cp .env.docker.example .env"
	@echo "  2. make up"
	@echo "  3. Open http://localhost:5173 (Dashboard)"
	@echo "  4. Open http://localhost:54322 (Supabase Studio)"
	@echo ""

# =============================================================================
# DOCKER COMPOSE COMMANDS
# =============================================================================

up: check-env ## Start all services in background
	@echo "$(CYAN)Starting Execution Market services...$(RESET)"
	$(DC) up -d
	@echo "$(GREEN)Services started!$(RESET)"
	@make urls

dev: check-env ## Start with development overrides (hot reload)
	@echo "$(CYAN)Starting Execution Market in development mode...$(RESET)"
	$(DC_DEV) up -d
	@echo "$(GREEN)Development services started!$(RESET)"
	@make urls

prod: check-env ## Start with production configuration
	@echo "$(CYAN)Starting Execution Market in production mode...$(RESET)"
	$(DC_PROD) up -d
	@echo "$(GREEN)Production services started!$(RESET)"

down: ## Stop all services
	@echo "$(CYAN)Stopping Execution Market services...$(RESET)"
	$(DC) down
	@echo "$(GREEN)Services stopped.$(RESET)"

stop: down ## Alias for down

restart: ## Restart all services
	@echo "$(CYAN)Restarting Execution Market services...$(RESET)"
	$(DC) restart
	@echo "$(GREEN)Services restarted.$(RESET)"

# =============================================================================
# LOGGING & STATUS
# =============================================================================

logs: ## View logs for all services
	$(DC) logs

logs-f: ## Follow logs for all services
	$(DC) logs -f

logs-mcp: ## Follow MCP server logs
	$(DC) logs -f mcp-server

logs-dashboard: ## Follow Dashboard logs
	$(DC) logs -f dashboard

logs-db: ## Follow database logs
	$(DC) logs -f supabase-db

logs-anvil: ## Follow Anvil logs
	$(DC) logs -f anvil

status: ## Show service status
	@echo "$(CYAN)Service Status:$(RESET)"
	$(DC) ps

ps: status ## Alias for status

urls: ## Show service URLs
	@echo ""
	@echo "$(CYAN)Execution Market Services:$(RESET)"
	@echo "  Dashboard:        $(GREEN)http://localhost:5173$(RESET)"
	@echo "  MCP Server:       $(GREEN)http://localhost:8000$(RESET)"
	@echo "  MCP Health:       $(GREEN)http://localhost:8000/health$(RESET)"
	@echo ""
	@echo "$(CYAN)Supabase:$(RESET)"
	@echo "  API Gateway:      $(GREEN)http://localhost:54321$(RESET)"
	@echo "  Studio (Admin):   $(GREEN)http://localhost:54322$(RESET)"
	@echo "  Email Testing:    $(GREEN)http://localhost:54323$(RESET)"
	@echo "  PostgreSQL:       $(GREEN)localhost:54320$(RESET)"
	@echo ""
	@echo "$(CYAN)Blockchain:$(RESET)"
	@echo "  Anvil RPC:        $(GREEN)http://localhost:8545$(RESET)"
	@echo ""
	@echo "$(CYAN)Cache:$(RESET)"
	@echo "  Redis:            $(GREEN)localhost:6379$(RESET)"
	@echo ""

# =============================================================================
# BUILD & REBUILD
# =============================================================================

build: ## Build all Docker images
	@echo "$(CYAN)Building Docker images...$(RESET)"
	$(DC) build
	@echo "$(GREEN)Build complete.$(RESET)"

rebuild: ## Rebuild all Docker images (no cache)
	@echo "$(CYAN)Rebuilding Docker images (no cache)...$(RESET)"
	$(DC) build --no-cache
	@echo "$(GREEN)Rebuild complete.$(RESET)"

rebuild-mcp: ## Rebuild MCP server image
	$(DC) build --no-cache mcp-server

rebuild-dashboard: ## Rebuild Dashboard image
	$(DC) build --no-cache dashboard

pull: ## Pull latest images
	$(DC) pull

# =============================================================================
# SHELL ACCESS
# =============================================================================

shell: ## Open shell in MCP server container
	$(DC) exec mcp-server /bin/bash

shell-dashboard: ## Open shell in Dashboard container
	$(DC) exec dashboard /bin/sh

db-shell: ## Open PostgreSQL shell
	$(DC) exec supabase-db psql -U postgres

redis-cli: ## Open Redis CLI
	$(DC) exec redis redis-cli

anvil-console: ## Open Anvil console (cast)
	$(DC) exec anvil cast --help

# =============================================================================
# DATABASE
# =============================================================================

migrate: ## Run database migrations
	@echo "$(CYAN)Running migrations...$(RESET)"
	$(DC) exec supabase-db psql -U postgres -d postgres -f /docker-entrypoint-initdb.d/001_initial_schema.sql
	@echo "$(GREEN)Migrations complete.$(RESET)"

seed: ## Seed database with test data
	@echo "$(CYAN)Seeding database...$(RESET)"
	$(DC) exec supabase-db psql -U postgres -d postgres -f /docker-entrypoint-initdb.d/99_seed.sql
	@echo "$(GREEN)Seed complete.$(RESET)"

db-reset: ## Reset database (drop all data)
	@echo "$(YELLOW)WARNING: This will delete all database data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	@echo "$(CYAN)Resetting database...$(RESET)"
	$(DC) down -v
	$(DC) up -d supabase-db
	@sleep 5
	@make migrate
	@make seed
	@$(DC) up -d
	@echo "$(GREEN)Database reset complete.$(RESET)"

# =============================================================================
# TESTING
# =============================================================================

test: ## Run all tests
	@echo "$(CYAN)Running all tests...$(RESET)"
	@make test-mcp
	@make test-dashboard
	@echo "$(GREEN)All tests passed.$(RESET)"

test-mcp: ## Run MCP server tests
	@echo "$(CYAN)Running MCP server tests...$(RESET)"
	$(DC) exec mcp-server pytest -v

test-dashboard: ## Run Dashboard tests
	@echo "$(CYAN)Running Dashboard tests...$(RESET)"
	$(DC) exec dashboard npm run test:run

lint: ## Run linters
	@echo "$(CYAN)Running linters...$(RESET)"
	$(DC) exec mcp-server python -m flake8 .
	$(DC) exec dashboard npm run lint

format: ## Format code
	@echo "$(CYAN)Formatting code...$(RESET)"
	$(DC) exec mcp-server python -m black .
	$(DC) exec dashboard npm run format

# =============================================================================
# CONTRACTS
# =============================================================================

contracts-deploy: ## Deploy contracts to Anvil
	@echo "$(CYAN)Deploying contracts to Anvil...$(RESET)"
	cd contracts && forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast
	@echo "$(GREEN)Contracts deployed.$(RESET)"

contracts-test: ## Run contract tests
	@echo "$(CYAN)Running contract tests...$(RESET)"
	cd contracts && forge test -vvv

# =============================================================================
# CLEANUP
# =============================================================================

reset: ## Reset everything and restart
	@echo "$(YELLOW)Resetting all services and data...$(RESET)"
	$(DC) down -v --remove-orphans
	$(DC) up -d
	@echo "$(GREEN)Reset complete.$(RESET)"
	@make urls

clean: ## Remove all containers, volumes, and images
	@echo "$(RED)WARNING: This will remove ALL Execution Market Docker resources!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	$(DC) down -v --rmi all --remove-orphans
	docker network rm em-network 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete.$(RESET)"

prune: ## Remove unused Docker resources
	@echo "$(CYAN)Pruning unused Docker resources...$(RESET)"
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)Prune complete.$(RESET)"

# =============================================================================
# SETUP
# =============================================================================

setup: ## Initial setup (create .env, pull images)
	@echo "$(CYAN)Setting up Execution Market development environment...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.docker.example .env; \
		echo "$(GREEN)Created .env from .env.docker.example$(RESET)"; \
	else \
		echo "$(YELLOW).env already exists, skipping$(RESET)"; \
	fi
	@echo "$(CYAN)Pulling Docker images...$(RESET)"
	$(DC) pull
	@echo "$(GREEN)Setup complete! Run 'make up' to start services.$(RESET)"

check-env: ## Check if .env exists
	@if [ ! -f .env ]; then \
		echo "$(RED)Error: .env file not found!$(RESET)"; \
		echo "Run: $(GREEN)make setup$(RESET) or $(GREEN)cp .env.docker.example .env$(RESET)"; \
		exit 1; \
	fi

# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================

watch: ## Start services and follow logs
	@make dev
	@make logs-f

health: ## Check health of all services
	@echo "$(CYAN)Checking service health...$(RESET)"
	@echo ""
	@echo "MCP Server:"
	@curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "  $(RED)Not responding$(RESET)"
	@echo ""
	@echo "Supabase API:"
	@curl -s http://localhost:54321/rest/v1/ -H "apikey: $$SUPABASE_ANON_KEY" | head -c 100 || echo "  $(RED)Not responding$(RESET)"
	@echo ""
	@echo "Anvil:"
	@curl -s -X POST http://localhost:8545 -H "Content-Type: application/json" \
		-d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | jq . 2>/dev/null || echo "  $(RED)Not responding$(RESET)"
	@echo ""
	@echo "Redis:"
	@docker compose exec -T redis redis-cli ping 2>/dev/null || echo "  $(RED)Not responding$(RESET)"
	@echo ""

# =============================================================================
# QUICK ALIASES
# =============================================================================

u: up
d: down
l: logs-f
s: status
r: restart
b: build
h: help
