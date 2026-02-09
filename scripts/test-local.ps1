# =============================================================================
# Local Test Runner - Execution Market (PowerShell)
# =============================================================================
# Corre todos los tests localmente antes de push
#
# Usage:
#   .\scripts\test-local.ps1 [-KeepRunning] [-SkipUnit] [-SkipE2E]
#
# Flags:
#   -KeepRunning    Deja el stack corriendo después de los tests
#   -SkipUnit       Salta tests unitarios (solo E2E)
#   -SkipE2E        Salta tests E2E (solo unit)
# =============================================================================

param(
    [switch]$KeepRunning,
    [switch]$SkipUnit,
    [switch]$SkipE2E
)

$ErrorActionPreference = "Stop"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Cyan "================================"
Write-ColorOutput Cyan "Execution Market - Local Tests"
Write-ColorOutput Cyan "================================"
Write-Output ""

# Track test results
$BackendPassed = $false
$FrontendPassed = $false
$E2EPassed = $false

# =============================================================================
# Step 1: Stop any running Docker services
# =============================================================================
Write-ColorOutput Yellow "[1/5] Parando servicios Docker..."
docker compose -f docker-compose.dev.yml down 2>&1 | Out-Null
Write-ColorOutput Green "✓ Servicios parados"
Write-Output ""

# =============================================================================
# Step 2: Backend Tests (Python + Pytest)
# =============================================================================
if (-not $SkipUnit) {
    Write-ColorOutput Yellow "[2/5] Corriendo tests de backend (pytest)..."
    Push-Location mcp_server

    # Check if pytest is installed
    if (-not (Get-Command pytest -ErrorAction SilentlyContinue)) {
        Write-ColorOutput Red "✗ pytest no encontrado. Instalando dependencias..."
        pip install -e ".[dev]" | Out-Null
    }

    # Run tests
    pytest -v --tb=short 2>&1 | Tee-Object -FilePath ..\test-backend.log
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "✓ Tests de backend pasaron"
        $BackendPassed = $true
    } else {
        Write-ColorOutput Red "✗ Tests de backend fallaron"
        Write-ColorOutput Yellow "Ver detalles en: test-backend.log"
    }

    Pop-Location
    Write-Output ""
} else {
    Write-ColorOutput Yellow "[2/5] Saltando tests de backend (--skip-unit)"
    Write-Output ""
    $BackendPassed = $true
}

# =============================================================================
# Step 3: Frontend Tests (Vitest)
# =============================================================================
if (-not $SkipUnit) {
    Write-ColorOutput Yellow "[3/5] Corriendo tests de frontend (vitest)..."
    Push-Location dashboard

    # Check if node_modules exists
    if (-not (Test-Path "node_modules")) {
        Write-ColorOutput Yellow "→ Instalando dependencias..."
        npm install --legacy-peer-deps | Out-Null
    }

    # Run tests
    npm run test:run 2>&1 | Tee-Object -FilePath ..\test-frontend.log
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "✓ Tests de frontend pasaron"
        $FrontendPassed = $true
    } else {
        Write-ColorOutput Red "✗ Tests de frontend fallaron"
        Write-ColorOutput Yellow "Ver detalles en: test-frontend.log"
    }

    Pop-Location
    Write-Output ""
} else {
    Write-ColorOutput Yellow "[3/5] Saltando tests de frontend (--skip-unit)"
    Write-Output ""
    $FrontendPassed = $true
}

# =============================================================================
# Step 4: Start Docker Stack for E2E Tests
# =============================================================================
if (-not $SkipE2E) {
    Write-ColorOutput Yellow "[4/5] Levantando stack para tests E2E..."
    docker compose -f docker-compose.dev.yml up -d

    # Wait for services to be healthy
    Write-ColorOutput Yellow "→ Esperando a que los servicios estén listos..."
    Start-Sleep -Seconds 10

    # Check MCP health
    $MaxRetries = 30
    $RetryCount = 0
    while ($RetryCount -lt $MaxRetries) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 503) {
                Write-ColorOutput Green "✓ MCP Server listo"
                break
            }
        } catch {
            # Continue
        }
        $RetryCount++
        Write-ColorOutput Yellow "→ Retry $RetryCount/$MaxRetries..."
        Start-Sleep -Seconds 2
    }

    if ($RetryCount -eq $MaxRetries) {
        Write-ColorOutput Red "✗ MCP Server no respondió a tiempo"
        Write-ColorOutput Yellow "Ver logs: docker compose -f docker-compose.dev.yml logs mcp-server"
        exit 1
    }

    # Check Dashboard
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -ErrorAction SilentlyContinue
        Write-ColorOutput Green "✓ Dashboard listo"
    } catch {
        Write-ColorOutput Yellow "⚠ Dashboard no responde, pero continuando..."
    }

    Write-Output ""

    # =============================================================================
    # Step 5: E2E Tests (Playwright)
    # =============================================================================
    Write-ColorOutput Yellow "[5/5] Corriendo tests E2E (playwright)..."
    Push-Location e2e

    # Check if node_modules exists
    if (-not (Test-Path "node_modules")) {
        Write-ColorOutput Yellow "→ Instalando dependencias..."
        npm install | Out-Null
    }

    # Install browsers if needed
    try {
        npx playwright --version | Out-Null
    } catch {
        Write-ColorOutput Yellow "→ Instalando navegadores de Playwright..."
        npx playwright install | Out-Null
    }

    # Run E2E tests
    npm run test 2>&1 | Tee-Object -FilePath ..\test-e2e.log
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "✓ Tests E2E pasaron"
        $E2EPassed = $true
    } else {
        Write-ColorOutput Red "✗ Tests E2E fallaron"
        Write-ColorOutput Yellow "Ver detalles en: test-e2e.log"
        Write-ColorOutput Yellow "Ver reporte: cd e2e; npm run report"
    }

    Pop-Location
    Write-Output ""
} else {
    Write-ColorOutput Yellow "[4/5] Saltando tests E2E (--skip-e2e)"
    Write-ColorOutput Yellow "[5/5] Saltando tests E2E (--skip-e2e)"
    Write-Output ""
    $E2EPassed = $true
}

# =============================================================================
# Step 6: Cleanup (unless -KeepRunning)
# =============================================================================
if (-not $KeepRunning -and -not $SkipE2E) {
    Write-ColorOutput Yellow "Parando stack Docker..."
    docker compose -f docker-compose.dev.yml down | Out-Null
    Write-ColorOutput Green "✓ Stack parado"
    Write-Output ""
} elseif ($KeepRunning) {
    Write-ColorOutput Cyan "ℹ Stack sigue corriendo (-KeepRunning)"
    Write-ColorOutput Cyan "  Dashboard: http://localhost:5173"
    Write-ColorOutput Cyan "  MCP: http://localhost:8000"
    Write-Output ""
}

# =============================================================================
# Final Report
# =============================================================================
Write-ColorOutput Cyan "================================"
Write-ColorOutput Cyan "Resumen de Tests"
Write-ColorOutput Cyan "================================"

if (-not $SkipUnit) {
    if ($BackendPassed) {
        Write-ColorOutput Green "✓ Backend Tests (pytest)"
    } else {
        Write-ColorOutput Red "✗ Backend Tests (pytest)"
    }

    if ($FrontendPassed) {
        Write-ColorOutput Green "✓ Frontend Tests (vitest)"
    } else {
        Write-ColorOutput Red "✗ Frontend Tests (vitest)"
    }
}

if (-not $SkipE2E) {
    if ($E2EPassed) {
        Write-ColorOutput Green "✓ E2E Tests (playwright)"
    } else {
        Write-ColorOutput Red "✗ E2E Tests (playwright)"
    }
}

Write-Output ""

# Exit with error if any test failed
if ($BackendPassed -and $FrontendPassed -and $E2EPassed) {
    Write-ColorOutput Green "✓ TODOS LOS TESTS PASARON"
    Write-ColorOutput Green "Listo para hacer push!"
    exit 0
} else {
    Write-ColorOutput Red "✗ ALGUNOS TESTS FALLARON"
    Write-ColorOutput Yellow "Revisa los logs antes de hacer push"
    exit 1
}
