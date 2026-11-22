#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
printf 'Launching InterviewLoop AI without Docker.\n'
"$ROOT/scripts/start-backend.sh" &
BACKEND_PID=$!
"$ROOT/scripts/start-frontend.sh" &
FRONTEND_PID=$!
cleanup(){ kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
wait "$BACKEND_PID" "$FRONTEND_PID"
