#!/usr/bin/env bash
# Realtime Voice Translate - Unified Launch Entrypoint
exec "$(dirname "$0")/docker/start.sh" "$@"
