# Vision Advanced: Face and approximate gaze tracking

## Quick start without Docker

```bash
./scripts/start-backend.sh
# second terminal
./scripts/start-frontend.sh
```

The frontend start script installs npm dependencies (if missing), then `npm run setup:vision` if the official model or WASM assets are missing. Initial internet access is required. Visit `http://127.0.0.1:5173` after startup.

## Where the new code lives

- `frontend/src/vision/gazeMath.js`: facial landmark geometry, calibration, approximate deviation and canvas drawing.
- `frontend/src/vision/useFaceMonitor.js`: browser-only vision runtime, face count/iris detection, sustained-event state, CPU fallback and lifecycle cleanup.
- `frontend/src/vision/gazeMath.test.js`: zero-dependency Node unit tests.
- `frontend/src/pages/Interview.jsx`: live glassmorphism vision UI, calibration and optional controls.
- `frontend/src/styles.css`: additional vision-command and scanner effects.
- `frontend/scripts/setup-vision.mjs`: downloads official model once and copies WASM files from installed dependency.

## Monitoring privacy and limitations

Eye direction cannot be determined accurately from webcam landmarks alone. Looking at a screen to think or read is not misconduct. This application **does not** identify people, infer emotion, predict honesty, compute attention percentages, send vision measurements to the backend, or make any automated personnel decision. Monitoring is off by default and purely informational to the candidate. Recruiters see recorded answers and verified transcript evidence only. Real-world deployment still needs appropriate consent, accessibility alternatives and independent security review.
