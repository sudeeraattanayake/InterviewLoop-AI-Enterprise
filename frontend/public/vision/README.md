The MediaPipe binary model and WASM are intentionally downloaded/copied during initial setup:
  cd frontend
  npm install
  npm run setup:vision
The model is fetched from the official Google MediaPipe storage bucket.
The WASM runtime is copied from the matching installed @mediapipe/tasks-vision package.
After setup, camera frame processing happens entirely in the candidate's browser.
Do not add model binaries from untrusted mirrors without verifying integrity and license.
