#!/bin/bash
# Quick command: /dev-start
# Start local development stack
docker compose -f docker-compose.dev.yml up -d
echo ""
echo "✅ Stack started!"
echo "📍 Dashboard: http://localhost:5173"
echo "📍 MCP Server: http://localhost:8000"
echo "📍 Health: http://localhost:8000/health"
