#!/bin/bash
# =============================================================================
# Local Test Runner - Execution Market
# =============================================================================
# Corre todos los tests localmente antes de push
#
# Usage:
#   bash scripts/test-local.sh [--keep-running]
#
# Flags:
#   --keep-running    Deja el stack corriendo después de los tests
#   --skip-unit       Salta tests unitarios (solo E2E)
#   --skip-e2e        Salta tests E2E (solo unit)
# =============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
KEEP_RUNNING=false
SKIP_UNIT=false
SKIP_E2E=false

# Parse arguments
for arg in "$@"; do
  case $arg in
    --keep-running)
      KEEP_RUNNING=true
      shift
      ;;
    --skip-unit)
      SKIP_UNIT=true
      shift
      ;;
    --skip-e2e)
      SKIP_E2E=true
      shift
      ;;
  esac
done

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Execution Market - Local Tests${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Track test results
BACKEND_PASSED=false
FRONTEND_PASSED=false
E2E_PASSED=false

# =============================================================================
# Step 1: Stop any running Docker services
# =============================================================================
echo -e "${YELLOW}[1/5] Parando servicios Docker...${NC}"
docker compose -f docker-compose.dev.yml down > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Servicios parados${NC}"
echo ""

# =============================================================================
# Step 2: Backend Tests (Python + Pytest)
# =============================================================================
if [ "$SKIP_UNIT" = false ]; then
  echo -e "${YELLOW}[2/5] Corriendo tests de backend (pytest)...${NC}"
  cd mcp_server

  # Check if pytest is installed
  if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest no encontrado. Instalando dependencias...${NC}"
    pip install -e ".[dev]" > /dev/null 2>&1
  fi

  # Run tests
  if pytest -v --tb=short 2>&1 | tee ../test-backend.log; then
    echo -e "${GREEN}✓ Tests de backend pasaron${NC}"
    BACKEND_PASSED=true
  else
    echo -e "${RED}✗ Tests de backend fallaron${NC}"
    echo -e "${YELLOW}Ver detalles en: test-backend.log${NC}"
  fi

  cd ..
  echo ""
else
  echo -e "${YELLOW}[2/5] Saltando tests de backend (--skip-unit)${NC}"
  echo ""
  BACKEND_PASSED=true
fi

# =============================================================================
# Step 3: Frontend Tests (Vitest)
# =============================================================================
if [ "$SKIP_UNIT" = false ]; then
  echo -e "${YELLOW}[3/5] Corriendo tests de frontend (vitest)...${NC}"
  cd dashboard

  # Check if node_modules exists
  if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}→ Instalando dependencias...${NC}"
    npm install --legacy-peer-deps > /dev/null 2>&1
  fi

  # Run tests
  if npm run test:run 2>&1 | tee ../test-frontend.log; then
    echo -e "${GREEN}✓ Tests de frontend pasaron${NC}"
    FRONTEND_PASSED=true
  else
    echo -e "${RED}✗ Tests de frontend fallaron${NC}"
    echo -e "${YELLOW}Ver detalles en: test-frontend.log${NC}"
  fi

  cd ..
  echo ""
else
  echo -e "${YELLOW}[3/5] Saltando tests de frontend (--skip-unit)${NC}"
  echo ""
  FRONTEND_PASSED=true
fi

# =============================================================================
# Step 4: Start Docker Stack for E2E Tests
# =============================================================================
if [ "$SKIP_E2E" = false ]; then
  echo -e "${YELLOW}[4/5] Levantando stack para tests E2E...${NC}"
  docker compose -f docker-compose.dev.yml up -d

  # Wait for services to be healthy
  echo -e "${YELLOW}→ Esperando a que los servicios estén listos...${NC}"
  sleep 10

  # Check MCP health
  MAX_RETRIES=30
  RETRY_COUNT=0
  while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
      echo -e "${GREEN}✓ MCP Server listo${NC}"
      break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}→ Retry $RETRY_COUNT/$MAX_RETRIES...${NC}"
    sleep 2
  done

  if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ MCP Server no respondió a tiempo${NC}"
    echo -e "${YELLOW}Ver logs: docker compose -f docker-compose.dev.yml logs mcp-server${NC}"
    exit 1
  fi

  # Check Dashboard
  if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Dashboard listo${NC}"
  else
    echo -e "${YELLOW}⚠ Dashboard no responde, pero continuando...${NC}"
  fi

  echo ""

  # =============================================================================
  # Step 5: E2E Tests (Playwright)
  # =============================================================================
  echo -e "${YELLOW}[5/5] Corriendo tests E2E (playwright)...${NC}"
  cd e2e

  # Check if node_modules exists
  if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}→ Instalando dependencias...${NC}"
    npm install > /dev/null 2>&1
  fi

  # Install browsers if needed
  if ! npx playwright --version > /dev/null 2>&1; then
    echo -e "${YELLOW}→ Instalando navegadores de Playwright...${NC}"
    npx playwright install > /dev/null 2>&1
  fi

  # Run E2E tests
  if npm run test 2>&1 | tee ../test-e2e.log; then
    echo -e "${GREEN}✓ Tests E2E pasaron${NC}"
    E2E_PASSED=true
  else
    echo -e "${RED}✗ Tests E2E fallaron${NC}"
    echo -e "${YELLOW}Ver detalles en: test-e2e.log${NC}"
    echo -e "${YELLOW}Ver reporte: cd e2e && npm run report${NC}"
  fi

  cd ..
  echo ""
else
  echo -e "${YELLOW}[4/5] Saltando tests E2E (--skip-e2e)${NC}"
  echo -e "${YELLOW}[5/5] Saltando tests E2E (--skip-e2e)${NC}"
  echo ""
  E2E_PASSED=true
fi

# =============================================================================
# Step 6: Cleanup (unless --keep-running)
# =============================================================================
if [ "$KEEP_RUNNING" = false ] && [ "$SKIP_E2E" = false ]; then
  echo -e "${YELLOW}Parando stack Docker...${NC}"
  docker compose -f docker-compose.dev.yml down > /dev/null 2>&1
  echo -e "${GREEN}✓ Stack parado${NC}"
  echo ""
elif [ "$KEEP_RUNNING" = true ]; then
  echo -e "${BLUE}ℹ Stack sigue corriendo (--keep-running)${NC}"
  echo -e "${BLUE}  Dashboard: http://localhost:5173${NC}"
  echo -e "${BLUE}  MCP: http://localhost:8000${NC}"
  echo ""
fi

# =============================================================================
# Final Report
# =============================================================================
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Resumen de Tests${NC}"
echo -e "${BLUE}================================${NC}"

if [ "$SKIP_UNIT" = false ]; then
  if [ "$BACKEND_PASSED" = true ]; then
    echo -e "${GREEN}✓ Backend Tests (pytest)${NC}"
  else
    echo -e "${RED}✗ Backend Tests (pytest)${NC}"
  fi

  if [ "$FRONTEND_PASSED" = true ]; then
    echo -e "${GREEN}✓ Frontend Tests (vitest)${NC}"
  else
    echo -e "${RED}✗ Frontend Tests (vitest)${NC}"
  fi
fi

if [ "$SKIP_E2E" = false ]; then
  if [ "$E2E_PASSED" = true ]; then
    echo -e "${GREEN}✓ E2E Tests (playwright)${NC}"
  else
    echo -e "${RED}✗ E2E Tests (playwright)${NC}"
  fi
fi

echo ""

# Exit with error if any test failed
if [ "$BACKEND_PASSED" = true ] && [ "$FRONTEND_PASSED" = true ] && [ "$E2E_PASSED" = true ]; then
  echo -e "${GREEN}✓ TODOS LOS TESTS PASARON${NC}"
  echo -e "${GREEN}Listo para hacer push!${NC}"
  exit 0
else
  echo -e "${RED}✗ ALGUNOS TESTS FALLARON${NC}"
  echo -e "${YELLOW}Revisa los logs antes de hacer push${NC}"
  exit 1
fi
