# InterviewLoop AI Enterprise — Vision Plus 3.1

Frontend-only upgrade for the original InterviewLoop AI Enterprise. No Docker. Existing backend, OpenAI key, user accounts and SQLite database can remain unchanged.

## Changed

1. **Auto-start after separate candidate choice**: A one-time, clearly worded optional consent is shown in the interview studio (also offered on the recording-consent screen). After a candidate chooses **Allow local guidance**, the on-device vision model starts automatically whenever that camera is enabled. There is no need to manually enable a vision-monitor switch each time. A candidate can decline, pause, resume or switch off their camera. **Do not quietly turn on facial analysis without disclosure/choice.**
2. **Automatic calibration**: On vision startup, look into the webcam lens for about 3 seconds so 24 consecutive usable frames establish a reference. The **Recalibrate** button is still available if camera position changes.
3. **Enhanced 3D head orientation**: The existing MediaPipe Face Landmarker now requests its optional facial transformation matrix. Relative yaw, pitch and roll changes join the iris-position proxy. The system falls back to prior 2D landmarks when a pose matrix is unavailable.
4. **Temporal filter**: A five-frame median of head/eye measurements reduces transient landmark noise. A look-away notice requires a sustained approximate deviation (3 seconds), not a single frame.
5. **Local-only and optional**: The detector runs in the candidate browser. No model landmark, head-pose, iris or gaze events are sent to the recruiter or backend. Alerts cannot approve, decline or rank an applicant. The recorded interview video is separate and remains governed by the original recording-consent and data retention setup.

## Important limitations

- MediaPipe Iris **does not measure the actual target a person is looking at**. The displayed direction is a rough calibrated proxy. A candidate reading questions on the monitor, wearing glasses, having eye differences, using an unusual camera angle or changing lighting can lead to false alerts.
- No lie detection, cheating detection, emotion recognition, attentiveness score or employment suitability assessment is provided or implied.
- This update improves *robustness*, not a clinically or experimentally validated accuracy rate. We have not run calibrated webcam/human ground-truth benchmarks.
- A true on-screen eye-gaze estimator could be trialled separately (e.g. opt-in multi-point calibrated WebGazer.js), but it needs a tested calibration UI and per-device accuracy measurements; it is not necessarily more accurate on moving heads.

## Apply patch to an existing Windows VS Code install

1. Stop the frontend terminal using `Ctrl+C`. Leave the backend/database untouched.
2. Back up `frontend/src/pages/Interview.jsx` and any other files you modified.
3. `cd` into the **project root** (`InterviewLoop-AI-Enterprise`, where `frontend`, `backend` and `scripts` folders exist).
4. From that folder, run:

```powershell
Expand-Archive -LiteralPath "$HOME\Downloads\InterviewLoop-Vision-Plus-Update.zip" -DestinationPath . -Force
cd frontend
npm run test:vision
cd ..
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\start-frontend.ps1
```

If ZIP was downloaded somewhere else, adjust its full path. The update ZIP has only frontend files and this guide. It does **not** replace `backend/.env` or SQLite `backend/data`.

## Updated-files tests

Run at project root (with Node.js available):

```powershell
cd frontend
npm run test:vision
npm run build
```

Vision unit tests cover calibration, synthetic face/iris geometry, simulated pose matrix angles and temporal median filtering. The unit tests do not replace real-device webcam tests. If a live page reports a missing local MediaPipe asset, follow `frontend/public/vision/README.md` and run `npm run setup:vision`.

## Verify in the browser

- Sign into candidate account and open the video interview.
- Choose **Allow local guidance** once (separate from recording consent). You can skip it and still complete your interview.
- Click **Enable camera + microphone**. The on-device vision model now loads automatically.
- Face the camera lens for about 3 seconds until you see the calibration status complete.
- Look away briefly: no warning should appear for a single frame. On sustained relative movement (~3 seconds), a gentle local reminder may appear; looking back clears it.
- Test **Pause guidance**, **Resume guidance** and **Turn off camera**.

This upgrade does not change recruitment decisions or create any server-side monitoring features.
