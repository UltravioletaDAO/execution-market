#!/bin/bash
# Quick command: /dev-stop
# Stop local development stack
docker compose -f docker-compose.dev.yml down
echo "✅ Stack stopped"
