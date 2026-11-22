# Implemented features and provider requirements

**Locally functional without API keys:** recruiter and candidate sign-up, company workspace, membership invitation, job posting, PDF/DOCX CV upload/extraction, local rule-based evidence, LangGraph checkpoints, human CV/video/code approvals, webcam recording, manual transcripts, human scheduling, generated Jitsi meeting links, note-taking, ATS Kanban, coding challenge editor + source persistence, PDF/ICS download, offers, in-app notifications/reminders, analytics, audits and personal data export/delete.

**Opt-in OpenAI functionality:** CV evidence, interview question generation, transcript evidence, optional Whisper, realtime voice conversation with ephemeral tokens. These require network, a billed OpenAI account, model permissions and appropriate consent. Offline behavior intentionally says *local rules*, not synthetic AI.

**MediaPipe:** initial download of Google's Face Landmarker float16 model and matching WebAssembly runtime. After setup the detection operates on candidate's browser frames locally. Alerts use calibrated geometry and **do not enter any recruitment report or score**. The face monitor is NOT a proctor, integrity service, biometric identity matcher or emotion detector.

**Judge0:** remote isolated test execution only when trusted HTTPS API is configured and supports synchronous `wait=true` requests. Without it, code is submitted for recruiter inspection without fabricated pass/fail status.

**Live individual interview:** launch external Jitsi Meet room (embedded for compatible `meet.jit.si` links, new tab fallback) or a custom HTTPS URL. InterviewLoop does not implement an independent encrypted conferencing backend.

**Scheduling:** manual recruiter scheduling, `.ics`, in-app notification and local single-process 24-hour reminder scheduler. SMTP email only if configured **and** candidate opted in. Google Calendar/O365 OAuth sync is not implemented (ICS export works instead).

**Advanced app UX:** React 19 + Vite, dark translucent glass panels, status chips, Framer Motion transitions, Recharts dashboards, Kanban, responsive layouts and accessible labels for key form inputs. Full WCAG testing not completed.

**Enterprise maturity:** reference implementation, local running, no Docker, not yet production-certified. No payments/billing, organizational SSO, e-signature, automated data residency, cloud object store, multi-region redundancy or legally verified retention.
