#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "Stopping Realtime Voice Translate containers..."
docker compose -f docker/docker-compose.yml down --remove-orphans 2>/dev/null || true
docker compose -f docker/docker-compose.cpu.yml down --remove-orphans 2>/dev/null || true
echo "✓ All services stopped."
