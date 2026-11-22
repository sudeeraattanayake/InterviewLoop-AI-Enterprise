# InterviewLoop AI — Enterprise Vision Edition

**A real, source-code-first recruitment workspace for recruiters and candidates** with premium dark glassmorphism UI, FastAPI, React, OpenAI, persistent LangGraph subgraphs and human approval interrupts. **NO Docker anywhere.**

> **Status / honest scope:** Complete local-first **reference application** with functioning application workflows, database models, API, React screens, protected file endpoints, multi-company tenant access and downloadable reports. It is **not** certified for regulated recruitment or ready to host applicants on the public internet without additional security/compliance hardening. External OpenAI, Judge0, SMTP and Jitsi features depend on third-party credentials, accounts, costs, limits and availability. All code is provided; generated vendor binaries are downloaded during setup.

## 1. What's included

| Area | Delivered behavior | Dependencies / limitations |
| --- | --- | --- |
| Glassmorphism UI | Animated dark glass recruiting dashboard, charts, cards, workflows, mobile layout | React, Framer Motion, Recharts, custom CSS |
| Recruiter & candidate portal | Sign-up/login, job publishing, candidate tracking and file upload | Argon2 + JWT; production auth hardening required |
| Organizations | Separate workspaces, owner invitation codes, company switching, team comments, tenant-scoped queries | Organizations and membership stored in SQLAlchemy DB |
| ATS Kanban | Draggable applicant cards across stage buckets; drag opens protected human review page | **No direct stage writes**; all transitions use authorized endpoints |
| AI CV evidence | PDF/DOCX text extraction, job requirement evidence with source excerpts and clarification questions | OpenAI only with opt-in; conservative local mode otherwise |
| AI interview questions | LangGraph question-generation subgraph, 4 questions derived from requirements | OpenAI when configured/consented, templates otherwise |
| Webcam video interview | Actual browser MediaRecorder per question, upload, protected playback, manual or optional Whisper transcription | localhost/HTTPS camera; media stored on local disk |
| Realtime AI voice | Browser WebRTC speech-to-speech interviewer with optional follow-ups, live text, mic mute and disconnect | Requires `OPENAI_API_KEY`, candidate opt-in, Realtime model access, fees and browser microphone permission |
| Optional vision monitor | MediaPipe face outline, iris landmarks, camera-facing calibration, face missing, multi-face, sustained eye/head look-away reminder | ON-DEVICE ONLY; approximate heuristic, **not** cheating/hiring detection |
| Candidate camera reminder | After ~3 seconds away: friendly overlay and optional spoken reminder; clears when camera direction returns; dismissible | Never uploaded to backend or visible to recruiter |
| Live coding assessment | Recruiter challenge builder, public/hidden test cases, Monaco editor (plain editor fallback), source submission | Judge0 remote execution optional; with no Judge0, human code review still works |
| Human interview room | Individual interview scheduling, automatic private Jitsi room link if absent, iframe or external-tab fallback, private notes | Third-party video provider. InterviewLoop does not host a video conferencing server |
| Calendar + reminders | Downloadable `.ics`, in-app invites, 24h reminders checked every 5 minutes, opt-in SMTP email | Automatic email requires SMTP; scheduler is single-process only |
| Structured PDF reports | Resume evidence, video transcripts, graph-generated outline, human feedback only in recruiter reports | ReportLab, no fake hiring score |
| Human-in-the-loop | Real LangGraph `interrupt()` + `Command(resume=...)` for CV, video and code; verified owner/tenant actions | SQLite checkpoints persistent across restarts |
| Offers | Human reviewer makes offer/decline with reasoning; candidate can accept/decline; recruiter documents offer terms | No e-signature or payroll integration |
| Analytics & audit | Funnel, by-role counts, average time to offer, review queue, actor/time/notes audit | Workspace-scoped reporting |
| Data rights | Candidate data export, per-application deletion of DB rows, files and workflow checkpoints, consent controls | Third-party retention/backups require independent procedures |

**Five compiled LangGraph subgraphs:** CV analysis, interview question generation, video evidence, coding evidence, factual report assembly. CV, video and coding each run inside checkpointed parent graphs with human approval gates. **No AI auto-hiring, no AI auto-rejection, no ranking applicants, no emotion/personality/cheating inference.**

## 2. Prerequisites (Mac)

- Python **3.11+** (`python3 --version`)
- Node.js **20+** (`node --version`), npm (`npm --version`)
- Internet for first-time `pip`, `npm` and optional MediaPipe model download
- Chrome or Edge recommended for webcam and voice (camera/mic require localhost or HTTPS)
- Optional OpenAI API key for actual LLM + realtime voice; **don't put it in the React environment**

## 3. Run on macOS — NO Docker

Unzip `InterviewLoop-AI-Enterprise-Full-Source.zip` into `~/Downloads` (if you choose a different location, use that folder in commands).

### Terminal 1: backend

```bash
cd ~/Downloads/InterviewLoop-AI-Enterprise
./scripts/start-backend.sh
```

First run creates `backend/.venv`, installs Python packages, copies `.env.example` to `backend/.env` and starts FastAPI at **http://127.0.0.1:8000**. Swagger: **http://127.0.0.1:8000/docs**.

### Terminal 2: frontend

```bash
cd ~/Downloads/InterviewLoop-AI-Enterprise
./scripts/start-frontend.sh
```

First run installs npm dependencies, copies `frontend/.env.example` to `frontend/.env`, downloads the official MediaPipe model and matching WASM runtime, and starts Vite at **http://127.0.0.1:5173**.

**Keep both terminals open.** Press Ctrl+C in each to stop. Launch again using the same commands. These are **development** scripts intended for localhost, not internet-facing deployment.

### Optional shortcut: both dev servers together

```bash
cd ~/Downloads/InterviewLoop-AI-Enterprise
./scripts/dev.sh
```

### Windows PowerShell

```powershell
.\scripts\start-backend.ps1
# In a second PowerShell window:
.\scripts\start-frontend.ps1
```

## 4. Configure real OpenAI AI and voice

Edit `backend/.env`, restart the backend:

```dotenv
SECRET_KEY=GENERATE_A_48_PLUS_CHARACTER_RANDOM_KEY
OPENAI_API_KEY=sk-your-own-secret
OPENAI_MODEL=gpt-4.1-mini
REALTIME_MODEL=gpt-realtime-2.1
```

Generate a secret on your Mac:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

- The API key is **server-only**; never publish `backend/.env` or paste the key into React.
- Candidate external AI processing consent at job application is required for CV/voice/transcription.
- Voice also requires explicit interview video consent and a supported browser. Click **Start live AI interviewer** in the candidate studio; the backend generates a short-lived OpenAI client secret; the browser connects over WebRTC.
- AI voice event text is shown to the candidate; only content they explicitly copy to the per-question transcript and submit is retained for transcript-based evidence.
- Without `OPENAI_API_KEY`, the normal applicant pipeline, webcam recording, **local rules** and manual coding review still run. The system identifies rule-based fallback accurately.
- OpenAI Realtime integration follows the current GA `POST /v1/realtime/client_secrets` and browser `POST /v1/realtime/calls` flow.

## 5. Configure isolated code execution (optional)

Candidate code is **NEVER executed in your FastAPI server process**. To execute the Python/JS test cases, use an isolated, trusted Judge0-compatible managed environment:

```dotenv
JUDGE0_URL=https://your-trusted-judge0.example/api
JUDGE0_API_KEY=
JUDGE0_API_HOST=
```

The service sends each source/test input to the configured HTTPS provider with tight CPU/wall/memory limits; `wait=true` is required. Confirm that your provider supports language IDs **71 (Python)** and **63 (JavaScript)**, synchronous wait responses and the chosen API path. Providers may differ. When absent/unavailable, the submission is persisted with **manual_review** or **partial_or_unavailable**, not falsely marked failed. Hidden test inputs are not returned to candidates. Technical outcomes **never** auto-reject an applicant.

## 6. Email, interview reminders and optional PostgreSQL

In-app notifications work with no configuration. Each backend process checks for interviews occurring within 24 hours every five minutes and saves one reminder to the candidate inbox. For opt-in SMTP emails, set:

```dotenv
ENABLE_EMAIL=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-secret
SMTP_FROM=interviews@example.com
ENABLE_REMINDERS=true
```

Only candidates who check the email opt-in can receive email. In production, use a durable single-worker scheduler, not independent per-process background reminder loops. Calendar downloads are `.ics` files with UTC event times, and interview times are stored as offset-aware ISO 8601 values.

SQLite is the default. To use PostgreSQL **without Docker**, install the optional driver from `backend/requirements-postgres.txt`, then configure `DATABASE_URL=postgresql+psycopg://user:password@host:5432/database`. Persistent LangGraph checkpoints remain SQLite in this reference; before scaling workers move checkpoints to a shared durable storage solution.

## 7. Full demo walkthrough

1. Register as a **recruiter**, choose a company name; a tenant-isolated workspace is created.
2. Create a draft job, add detailed requirements and optionally configure a **coding challenge while still in draft**.
3. Publish the job. Register another user as a **candidate**.
4. Apply with a real text-based PDF/DOCX CV; choose whether to allow external AI processing.
5. Recruiter opens the candidate, reviews CV evidence and **explicitly approves/declines** with rationale. LangGraph resumes the saved checkpoint.
6. If advanced, the candidate opens the interview studio and consents to recording, optionally enables the **private face/iris monitor** and calibrates while looking at the camera. Face-away reminders appear only after a sustained approximate deviation. The candidate may dismiss/disable them or opt into a local voice reminder.
7. Candidate optionally starts the **AI Realtime voice** interview, submits the required webcam recordings and correct transcripts, and finishes. Recruiter views text evidence and protected recordings before making another explicit approval decision.
8. If the job has a coding task, candidate opens **Coding Studio**, types source in Monaco and submits. Optional Judge0 execution returns factual technical test data. Recruiter then approves or declines the coding step through another LangGraph human gate.
9. Recruiter schedules an individual live interview (generate a private Jitsi room automatically if no meeting link entered). Both users open **Individual interview room**; recruiter can save team notes and complete a manual structured rubric.
10. Recruiter documents a final manual offer/decline. If offered, terms may be entered and candidate may accept/decline. Download PDF evidence packet and calendar invite.
11. Visit **ATS board, Analytics, Reports, Workspace, Notifications and Audit Trail**. A workspace owner may share an invitation code with another recruiter, who can join and collaborate; switching workspaces scopes jobs and data to that company.
12. Candidate uses **Privacy center** to export application data or deletes each application. Document any retention obligations separately.

### Optional demo accounts

After launching backend, set `DEMO_MODE=true` in `backend/.env`, restart, then:

```bash
cd ~/Downloads/InterviewLoop-AI-Enterprise/backend
source .venv/bin/activate
python -m scripts.seed_demo
```

Recruiter: `recruiter@demo.test` / `DemoRecruiter2026!`  
Candidate: `candidate@demo.test` / `DemoCandidate2026!`

**Only local synthetic demonstrations!** Never enable demo users in a public deployment.

## 8. Verify locally

```bash
cd ~/Downloads/InterviewLoop-AI-Enterprise/backend
source .venv/bin/activate
pytest -q
python -m scripts.smoke_test
python -m scripts.enterprise_smoke_test
```

Frontend:

```bash
cd ~/Downloads/InterviewLoop-AI-Enterprise/frontend
npm run test:vision
npm run build
```

These require installing declared dependencies first. In the authoring environment, All **9 Python unit tests** and **4 browser-side gaze math tests** passed and a synthetic end-to-end API check using **temporary substitutes for unavailable LangGraph/password library dependencies** passed. The actual dependency installation, real LangGraph graph runtime and browser/Vite build **could not be exercised there** because PyPI and npm were unreachable. **Run the supplied smoke tests on your Mac** before trusting the workflows.

## 9. Critical security and compliance limitations

- **Do not expose the dev build to the internet.** JWT localStorage and a single FastAPI process are convenient for development; production should use hardened session management, secure HTTP-only cookies/CSRF strategy, account recovery, optional MFA/SSO, verified domains, audit integrity, security headers, HTTPS and robust distributed rate limits.
- Add tested database migrations (Alembic), backups, secrets rotation, managed encrypted object storage and proper retention policies. Run uploaded file malware scanning; scanned-image PDFs currently need external OCR.
- Realtime voice, hosted video conferences and Judge0 have external privacy/cost requirements. Confirm contracts, DPA, accessibility, consent and cross-border transfer legality. **Do not transmit CVs or recordings without authorization.**
- InterviewLoop does not perform facial recognition, identity authentication, emotion detection, lie detection, cheating determination or automated hiring decisions. Gaze proxies are approximate and unreliable for assessing attention: camera geometry, glasses, disability, neurodivergence, screen-reading and normal conversational behavior can cause false alerts. Tracking can always be disabled and must not affect progression.
- The product is an **advanced implementation / reference SaaS architecture**, not a production-certified ATS nor an EU AI Act compliance certificate. Qualified privacy/security and employment counsel review is needed before actual candidate onboarding.

See `docs/ARCHITECTURE.md`, `docs/FEATURE-MATRIX.md`, and `docs/SECURITY.md` for module boundaries and operational gaps. **No Dockerfile / docker-compose / container runtime required.**
