Set-Location (Join-Path $PSScriptRoot '..\frontend')
if (!(Test-Path node_modules)) { npm install }
if (!(Test-Path .env)) { Copy-Item .env.example .env }
if (!(Test-Path public/vision/face_landmarker.task) -or !(Test-Path public/vision/wasm/vision_wasm_internal.wasm)) { npm run setup:vision; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
npm run dev
