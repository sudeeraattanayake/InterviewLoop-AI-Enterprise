#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"
if [[ ! -d node_modules ]]; then npm install; fi
if [[ ! -f .env ]]; then cp .env.example .env; fi
if [[ ! -f public/vision/face_landmarker.task || ! -f public/vision/wasm/vision_wasm_internal.wasm ]]; then
  npm run setup:vision
fi
exec npm run dev
