"""InterviewLoop AI REST API. Start: uvicorn app.main:app --reload"""
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, HTTPException, File, Form, UploadFile, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import get_settings
from .db import Base, engine, get_db
from .models import User, Job, Application, InterviewQuestion, AuditEvent, Organization, Membership, CodingChallenge, CodeSubmission, TeamComment, Notification
from .schemas import RegisterIn, LoginIn, JobIn, DecisionIn, ScheduleIn, FinalDecisionIn, PreferencesIn, TranscriptIn
from .security import hash_password, verify_password, create_token, current_user, role_guard
from .services.files import receive_file, extract_resume
from .services.workflows import start_cv, resume_cv, questions_for, start_video, resume_video
from .services.ai import transcribe

settings = get_settings()
Base.metadata.create_all(bind=engine)
if settings.secret_key in ('dev-only-change-me-before-deployment', 'REPLACE_WITH_A_LONG_RANDOM_SECRET_AT_LEAST_32_CHARS'):
    print('WARNING: Set SECRET_KEY in backend/.env before using this with real candidate data.')
@asynccontextmanager
async def lifespan(application):
    task = None
    if settings.enable_reminders:
        async def reminder_loop():
            from .services.reminders import send_due_reminders
            while True:
                try:
                    await asyncio.to_thread(send_due_reminders)
                except Exception as exc:
                    print(f'Reminder scheduler: {type(exc).__name__}')
                await asyncio.sleep(300)
        task = asyncio.create_task(reminder_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(lifespan=lifespan, title='InterviewLoop AI API', version='1.0.0', description='Recruiter-led recruitment workflow with LangGraph HITL')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',')], allow_credentials=True, allow_methods=['GET','POST','PATCH','DELETE'], allow_headers=['Authorization','Content-Type'])

# Basic development login throttling; replace with a distributed store before production.
from collections import defaultdict
from time import monotonic
_auth_attempts = defaultdict(list)

@app.middleware('http')
async def auth_throttle(request: Request, call_next):
    if request.url.path in ('/api/auth/register', '/api/auth/login') and request.method == 'POST':
        key = (request.client.host if request.client else 'unknown', request.url.path)
        now_ts = monotonic()
        recent = [stamp for stamp in _auth_attempts[key] if now_ts - stamp < 60]
        if len(recent) >= 12:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={'detail': 'Too many authentication requests. Try again in a minute.'}, headers={'Retry-After': '60'})
        recent.append(now_ts)
        _auth_attempts[key] = recent
    return await call_next(request)



def utc_iso(value):
    return value.isoformat() if value else None


def user_json(u: User):
    return {'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role, 'active_organization_id': u.active_organization_id, 'email_opt_in': bool(u.email_opt_in)}


def job_json(j: Job):
    return {'id': j.id, 'recruiter_id': j.recruiter_id, 'organization_id': j.organization_id, 'company_name': (j.organization.name if j.organization else 'Independent recruiter'), 'title': j.title, 'department': j.department, 'location': j.location, 'employment_type': j.employment_type, 'description': j.description, 'requirements': j.requirements, 'status': j.status, 'created_at': utc_iso(j.created_at)}


def app_json(a: Application, details=False):
    payload = {'id': a.id, 'job_id': a.job_id, 'candidate_id': a.candidate_id, 'candidate_name': a.candidate.name, 'candidate_email': a.candidate.email, 'job_title': a.job.title, 'department': a.job.department,
               'stage': a.stage, 'created_at': utc_iso(a.created_at), 'updated_at': utc_iso(a.updated_at),
               'cv_review': a.cv_review, 'video_review': a.video_review, 'ai_consent': a.ai_consent,
               'video_consent': a.video_consent, 'resume_filename': a.resume_filename,
               'interview_datetime': a.interview_datetime, 'interview_link': a.interview_link, 'offer_response': a.offer_response, 'offer_terms': a.offer_terms}
    if details:
        payload['questions'] = [{'id': q.id, 'order': q.order, 'skill': q.skill, 'prompt': q.prompt, 'duration_sec': q.duration_sec, 'submitted': bool(q.submitted_at), 'transcript': q.transcript, 'has_recording': bool(q.video_path)} for q in questions_for_app(a)]
    return payload


def questions_for_app(a: Application):
    return sorted(a._sa_instance_state.session.scalars(select(InterviewQuestion).where(InterviewQuestion.application_id == a.id)).all(), key=lambda q: q.order)


def log(db, actor: int, event: str, app_id=None, job_id=None, **kwargs):
    if app_id is not None and job_id is None:
        related = db.get(Application, app_id)
        if related:
            job_id = related.job_id
    db.add(AuditEvent(actor_id=actor, application_id=app_id, job_id=job_id, event=event, details=kwargs))


def org_access(db: Session, u: User, organization_id: int | None) -> bool:
    return bool(u.role == 'recruiter' and organization_id and organization_id == u.active_organization_id and
                db.scalar(select(Membership).where(Membership.user_id == u.id, Membership.organization_id == organization_id)))


def recruiter_jobs(db: Session, u: User):
    if u.role != 'recruiter' or not u.active_organization_id:
        raise HTTPException(403, 'Select an organization first')
    return select(Job).where(Job.organization_id == u.active_organization_id)


def notify(db: Session, u_id: int, subject: str, body: str, app_id: int | None = None):
    db.add(Notification(user_id=u_id, subject=subject[:200], body=body[:3000], application_id=app_id))


def job_for_recruiter(db: Session, job_id: int, u: User) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, 'Job not found')
    if not org_access(db, u, job.organization_id):
        raise HTTPException(403, 'Job belongs to another organization')
    return job


def application_access(db: Session, aid: int, u: User) -> Application:
    a = db.get(Application, aid)
    if not a:
        raise HTTPException(404, 'Application not found')
    if u.role == 'candidate' and a.candidate_id != u.id:
        raise HTTPException(403, 'Not your application')
    if u.role == 'recruiter' and not org_access(db, u, a.job.organization_id):
        raise HTTPException(403, 'Not your applicant')
    return a


def recruiter_application(db, aid, u):
    a = application_access(db, aid, u)
    if u.role != 'recruiter':
        raise HTTPException(403, 'Recruiter action only')
    return a


def as_workflow_job(j: Job):
    return {'title': j.title, 'description': j.description, 'requirements': j.requirements}


@app.get('/api/health')
def health():
    return {'status': 'ok', 'name': 'InterviewLoop AI', 'ai_configured': bool(settings.openai_api_key), 'storage': 'local'}


@app.post('/api/auth/register', status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.casefold().strip()
    if '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(422, 'Invalid email')
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'Email already registered')
    user = User(name=data.name.strip(), email=email, password_hash=hash_password(data.password), role=data.role, email_opt_in=data.email_opt_in)
    db.add(user)
    db.flush()
    if data.role == 'recruiter':
        import secrets
        org = Organization(name=data.company_name.strip() or f'{data.name.strip()} Workspace', invite_code=secrets.token_urlsafe(24))
        db.add(org); db.flush()
        db.add(Membership(user_id=user.id, organization_id=org.id, role='owner'))
        user.active_organization_id = org.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Email already registered')
    db.refresh(user)
    return {'token': create_token(user), 'user': user_json(user)}


@app.post('/api/auth/login')
def login(data: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == data.email.casefold().strip()))
    if not u or not verify_password(data.password, u.password_hash):
        raise HTTPException(401, 'Invalid email or password')
    return {'token': create_token(u), 'user': user_json(u)}


@app.get('/api/auth/me')
def me(u: User = Depends(current_user)):
    return user_json(u)


@app.get('/api/jobs')
def jobs(db: Session = Depends(get_db), u: User = Depends(current_user)):
    query = select(Job)
    query = recruiter_jobs(db, u) if u.role == 'recruiter' else query.where(Job.status == 'published')
    return [job_json(j) for j in db.scalars(query.order_by(Job.id.desc())).all()]


@app.get('/api/jobs/{jid}')
def job_detail(jid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    j = db.get(Job, jid)
    if not j or (j.status != 'published' and not org_access(db, u, j.organization_id)):
        raise HTTPException(404, 'Job not found')
    return job_json(j)


@app.post('/api/jobs', status_code=201)
def create_job(data: JobIn, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    recruiter_jobs(db, u)
    j = Job(recruiter_id=u.id, organization_id=u.active_organization_id, **data.model_dump())
    db.add(j)
    db.flush()
    log(db, u.id, 'job_created', job_id=j.id)
    db.commit()
    db.refresh(j)
    return job_json(j)


@app.patch('/api/jobs/{jid}')
def update_job(jid: int, data: JobIn, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    j = job_for_recruiter(db, jid, u)
    if j.status != 'draft':
        raise HTTPException(409, 'Published jobs cannot be changed. Create a new version to preserve application integrity.')
    for key, value in data.model_dump().items():
        setattr(j, key, value)
    log(db, u.id, 'job_edited', job_id=j.id)
    db.commit()
    return job_json(j)


@app.post('/api/jobs/{jid}/publish')
def publish_job(jid: int, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    j = job_for_recruiter(db, jid, u)
    j.status = 'published'
    log(db, u.id, 'job_published', job_id=j.id, human_approved=True)
    db.commit()
    return job_json(j)


@app.post('/api/jobs/{jid}/close')
def close_job(jid: int, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    j = job_for_recruiter(db, jid, u)
    j.status = 'closed'
    log(db, u.id, 'job_closed', job_id=j.id)
    db.commit()
    return job_json(j)


@app.post('/api/jobs/{jid}/apply', status_code=201)
async def apply(jid: int, cv: UploadFile = File(...), ai_consent: bool = Form(False), db: Session = Depends(get_db), u: User = Depends(role_guard('candidate'))):
    j = db.get(Job, jid)
    if not j or j.status != 'published':
        raise HTTPException(404, 'Open job not found')
    if db.scalar(select(Application).where(Application.job_id == jid, Application.candidate_id == u.id)):
        raise HTTPException(409, 'You have already applied for this job')
    path, data = await receive_file(cv, 'resumes', settings.max_cv_mb)
    try:
        resume_text = extract_resume(cv.filename or '', data)
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
    a = Application(job_id=jid, candidate_id=u.id, resume_filename=Path(cv.filename or 'resume').name[:255], resume_path=path, resume_text=resume_text, ai_consent=ai_consent, stage='processing_cv')
    db.add(a)
    db.flush()
    log(db, u.id, 'application_submitted', app_id=a.id, job_id=jid, ai_consent=ai_consent)
    db.commit()
    db.refresh(a)
    # Analysis is deterministic locally without an API key; with a key it may take seconds.
    try:
        review = await run_in_threadpool(start_cv, a.id, as_workflow_job(j), resume_text, ai_consent)
        a.cv_review = review
        a.stage = 'awaiting_cv_review'
        log(db, u.id, 'cv_evidence_ready', app_id=a.id, job_id=jid, mode=review.get('mode'))
        db.commit()
    except Exception:
        a.stage = 'cv_processing_error'
        db.commit()
    return app_json(a)


@app.get('/api/applications')
def applications(job_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(current_user)):
    query = select(Application)
    if u.role == 'candidate':
        query = query.where(Application.candidate_id == u.id)
    else:
        recruiter_jobs(db, u)
        query = query.join(Job, Application.job_id == Job.id).where(Job.organization_id == u.active_organization_id)
    if job_id is not None:
        query = query.where(Application.job_id == job_id)
    return [app_json(a) for a in db.scalars(query.order_by(Application.id.desc())).all()]


@app.get('/api/applications/{aid}')
def application_detail(aid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = application_access(db, aid, u)
    item = app_json(a, details=True)
    if u.role == 'recruiter':
        item['recruiter_notes'] = a.recruiter_notes
        item['individual_feedback'] = a.individual_feedback
    return item


@app.post('/api/applications/{aid}/retry-cv')
async def retry_cv(aid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = application_access(db, aid, u)
    if a.stage != 'cv_processing_error':
        raise HTTPException(409, 'CV analysis does not need to be retried')
    review = await run_in_threadpool(start_cv, a.id, as_workflow_job(a.job), a.resume_text, a.ai_consent)
    a.cv_review = review
    a.stage = 'awaiting_cv_review'
    log(db, u.id, 'cv_analysis_retried', app_id=aid, mode=review.get('mode'))
    db.commit()
    return app_json(a, details=True)


@app.get('/api/applications/{aid}/resume')
def download_cv(aid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = application_access(db, aid, u)
    if not Path(a.resume_path).is_file():
        raise HTTPException(404, 'File unavailable')
    return FileResponse(a.resume_path, filename=a.resume_filename, media_type='application/octet-stream', headers={'Cache-Control': 'no-store'})


@app.post('/api/applications/{aid}/review-cv')
def review_cv(aid: int, payload: DecisionIn, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    a = recruiter_application(db, aid, u)
    if a.stage != 'awaiting_cv_review':
        raise HTTPException(409, f'Application must be awaiting CV review, not {a.stage}')
    if payload.decision not in ('advance', 'decline'):
        raise HTTPException(422, 'Decision must be advance or decline')
    if len(payload.notes.strip()) < 10:
        raise HTTPException(422, 'Record at least 10 characters of job-related rationale')
    result = resume_cv(a.id, payload.decision, payload.notes)
    if result.get('decision') != payload.decision:
        raise HTTPException(500, 'Approval checkpoint did not confirm decision')
    a.recruiter_notes = (a.recruiter_notes + '\nCV review: ' + payload.notes).strip()
    if payload.decision == 'advance':
        notify(db, a.candidate_id, 'Video interview invitation', f'Your application for {a.job.title} has progressed to a video interview.', a.id)
        qdata = questions_for(as_workflow_job(a.job), a.ai_consent)
        for index, q in enumerate(qdata['questions'][:4]):
            db.add(InterviewQuestion(application_id=a.id, order=index+1, skill=q['skill'][:160], prompt=q['question'], duration_sec=180))
        a.stage = 'video_invited'
    else:
        a.stage = 'declined_cv'
        notify(db, a.candidate_id, 'Application update', f'Your application for {a.job.title} will not progress to the next stage.', a.id)
    log(db, u.id, 'human_cv_decision', app_id=a.id, job_id=a.job_id, decision=payload.decision, notes=payload.notes)
    db.commit()
    return app_json(a, details=True)


@app.post('/api/applications/{aid}/video-consent')
def consent_video(aid: int, payload: PreferencesIn, db: Session = Depends(get_db), u: User = Depends(role_guard('candidate'))):
    a = application_access(db, aid, u)
    if a.stage != 'video_invited':
        raise HTTPException(409, 'Video interview is not available at this stage')
    a.video_consent = payload.video_consent
    log(db, u.id, 'video_consent_changed', app_id=aid, consent=payload.video_consent)
    db.commit()
    return {'video_consent': a.video_consent}


@app.post('/api/applications/{aid}/answers/{qid}')
async def submit_answer(aid: int, qid: int, recording: UploadFile = File(...), transcript_text: str = Form(''), auto_transcribe: bool = Form(False), db: Session = Depends(get_db), u: User = Depends(role_guard('candidate'))):
    a = application_access(db, aid, u)
    if a.stage != 'video_invited':
        raise HTTPException(409, 'You cannot answer at this stage')
    if not a.video_consent:
        raise HTTPException(403, 'Explicit recording consent is required')
    q = db.get(InterviewQuestion, qid)
    if not q or q.application_id != a.id:
        raise HTTPException(404, 'Question not found')
    if q.submitted_at:
        raise HTTPException(409, 'Answer already submitted')
    if len(transcript_text) > 12000:
        raise HTTPException(422, 'Transcript too long')
    path, data = await receive_file(recording, 'recordings', settings.max_video_mb)
    q.video_path = path
    q.transcript = transcript_text.strip() or (await run_in_threadpool(transcribe, data, recording.filename or 'recording.webm', a.ai_consent and auto_transcribe))
    q.submitted_at = datetime.now(timezone.utc)
    log(db, u.id, 'video_answer_recorded', app_id=aid, question_id=qid, external_transcription=bool(auto_transcribe and a.ai_consent))
    db.commit()
    return {'id': q.id, 'submitted': True, 'transcript': q.transcript, 'transcript_available': bool(q.transcript)}


@app.patch('/api/applications/{aid}/answers/{qid}/transcript')
def correct_transcript(aid: int, qid: int, payload: TranscriptIn, db: Session = Depends(get_db), u: User = Depends(role_guard('candidate'))):
    a = application_access(db, aid, u)
    if a.stage != 'video_invited':
        raise HTTPException(409, 'Transcript editing is closed')
    q = db.get(InterviewQuestion, qid)
    if not q or q.application_id != aid or not q.submitted_at:
        raise HTTPException(404, 'Recorded answer not found')
    q.transcript = payload.transcript.strip()
    log(db, u.id, 'candidate_corrected_transcript', app_id=aid, question_id=qid)
    db.commit()
    return {'id': q.id, 'transcript': q.transcript}


@app.post('/api/applications/{aid}/video-complete')
def complete_video(aid: int, db: Session = Depends(get_db), u: User = Depends(role_guard('candidate'))):
    a = application_access(db, aid, u)
    if a.stage != 'video_invited':
        raise HTTPException(409, 'Not in video stage')
    answers = questions_for_app(a)
    if not answers or any(not q.submitted_at for q in answers):
        raise HTTPException(409, 'All video questions must be recorded first')
    if any(not q.transcript.strip() for q in answers):
        raise HTTPException(409, 'All questions need transcripts. Type them manually if automatic transcription is unavailable.')
    payload = [{'skill': q.skill, 'prompt': q.prompt, 'transcript': q.transcript} for q in answers]
    try:
        a.video_review = start_video(a.id, payload, a.ai_consent)
        a.stage = 'awaiting_video_review'
    except Exception:
        a.stage = 'video_processing_error'
    log(db, u.id, 'video_completed', app_id=aid, result=a.stage)
    db.commit()
    return app_json(a, details=True)


@app.post('/api/applications/{aid}/retry-video')
async def retry_video(aid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = application_access(db, aid, u)
    if a.stage != 'video_processing_error':
        raise HTTPException(409, 'Video analysis does not need to be retried')
    questions = questions_for_app(a)
    if not questions or any(not q.transcript.strip() for q in questions):
        raise HTTPException(409, 'Missing transcripts')
    payload = [{'skill': q.skill, 'prompt': q.prompt, 'transcript': q.transcript} for q in questions]
    a.video_review = await run_in_threadpool(start_video, a.id, payload, a.ai_consent)
    a.stage = 'awaiting_video_review'
    log(db, u.id, 'video_analysis_retried', app_id=aid)
    db.commit()
    return app_json(a, details=True)


@app.get('/api/applications/{aid}/answers/{qid}/recording')
def get_recording(aid: int, qid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = application_access(db, aid, u)
    q = db.get(InterviewQuestion, qid)
    if not q or q.application_id != a.id or not q.video_path or not Path(q.video_path).is_file():
        raise HTTPException(404, 'Recording unavailable')
    media = 'video/mp4' if q.video_path.endswith('.mp4') else 'video/webm'
    # Authenticated response; not a publicly accessible media URL.
    return FileResponse(q.video_path, media_type=media, headers={'Cache-Control': 'private, no-store'})


@app.post('/api/applications/{aid}/review-video')
def review_video(aid: int, payload: DecisionIn, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    a = recruiter_application(db, aid, u)
    if a.stage != 'awaiting_video_review':
        raise HTTPException(409, 'Not awaiting video review')
    if payload.decision not in ('advance', 'decline'):
        raise HTTPException(422, 'Decision must be advance or decline')
    if len(payload.notes.strip()) < 10:
        raise HTTPException(422, 'Record at least 10 characters of job-related rationale')
    result = resume_video(a.id, payload.decision, payload.notes)
    if result.get('decision') != payload.decision:
        raise HTTPException(500, 'Approval checkpoint did not confirm decision')
    challenge = db.scalar(select(CodingChallenge).where(CodingChallenge.job_id == a.job_id))
    a.stage = ('coding_invited' if challenge else 'individual_pending') if payload.decision == 'advance' else 'declined_video'
    notify(db, a.candidate_id, 'Application stage update', f'Your application for {a.job.title} is now at: {a.stage.replace("_", " ")}.', a.id)
    a.recruiter_notes = (a.recruiter_notes + '\nVideo review: ' + payload.notes).strip()
    log(db, u.id, 'human_video_decision', app_id=aid, decision=payload.decision, notes=payload.notes)
    db.commit()
    return app_json(a, details=True)


@app.post('/api/applications/{aid}/schedule')
def schedule(aid: int, payload: ScheduleIn, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    a = recruiter_application(db, aid, u)
    if a.stage not in ('individual_pending', 'individual_scheduled'):
        raise HTTPException(409, 'Individual interview cannot be scheduled at this stage')
    try:
        when = datetime.fromisoformat(payload.starts_at.replace('Z','+00:00'))
        if when.tzinfo is None or when.astimezone(timezone.utc) < datetime.now(timezone.utc):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, 'Provide a future date with timezone')
    if payload.meeting_link:
        url = urlsplit(payload.meeting_link)
        if url.scheme != 'https' or not url.netloc:
            raise HTTPException(422, 'Meeting link must be a valid HTTPS URL')
    a.stage = 'individual_scheduled'
    notify(db, a.candidate_id, 'Individual interview scheduled', f'Your interview for {a.job.title} is scheduled for {when.isoformat()}.', a.id)
    a.interview_datetime = when.isoformat()
    if payload.meeting_link:
        a.interview_link = payload.meeting_link
    elif not a.interview_link:
        import secrets
        a.interview_link = 'https://meet.jit.si/InterviewLoop-' + secrets.token_urlsafe(18)
    a.recruiter_notes = (a.recruiter_notes + '\nScheduling: ' + payload.notes).strip()
    log(db, u.id, 'individual_scheduled', app_id=aid, starts_at=a.interview_datetime)
    db.commit()
    return app_json(a, details=True)


@app.post('/api/applications/{aid}/final-decision')
def final_decision(aid: int, payload: FinalDecisionIn, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    a = recruiter_application(db, aid, u)
    if a.stage != 'individual_scheduled':
        raise HTTPException(409, 'An individual interview must be scheduled before final decision')
    if payload.outcome not in ('offer', 'reject'):
        raise HTTPException(422, 'Outcome must be offer or reject')
    a.stage = 'offer_extended' if payload.outcome == 'offer' else 'declined_final'
    a.individual_feedback = {'notes': payload.notes, 'rubric': payload.rubric, 'human_decision': True, 'reviewed_by': u.id, 'decided_at': datetime.now(timezone.utc).isoformat()}
    notify(db, a.candidate_id, 'Final application update', f'Your application for {a.job.title} has been updated. Sign in to view the outcome.', a.id)
    log(db, u.id, 'human_final_decision', app_id=aid, outcome=payload.outcome, notes=payload.notes)
    db.commit()
    return app_json(a, details=True)


@app.get('/api/audit')
def audit(application_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(role_guard('recruiter'))):
    recruiter_jobs(db, u)
    q = select(AuditEvent).outerjoin(Job, AuditEvent.job_id == Job.id).where(Job.organization_id == u.active_organization_id)
    if application_id is not None:
        recruiter_application(db, application_id, u)
        q = q.where(AuditEvent.application_id == application_id)
    events = db.scalars(q.order_by(AuditEvent.id.desc()).limit(150)).all()
    return [{'id': e.id, 'event': e.event, 'actor_id': e.actor_id, 'application_id': e.application_id, 'job_id': e.job_id, 'details': e.details, 'created_at': utc_iso(e.created_at)} for e in events]


@app.get('/api/stats')
def stats(db: Session = Depends(get_db), u: User = Depends(current_user)):
    if u.role == 'candidate':
        applications = db.scalars(select(Application).where(Application.candidate_id == u.id)).all()
        return {'applications': len(applications), 'interviews': sum(a.stage in ('video_invited', 'awaiting_video_review', 'individual_pending', 'individual_scheduled') for a in applications), 'offers': sum(a.stage in ('offer_extended','hired','offer_declined') for a in applications)}
    jobs = db.scalars(recruiter_jobs(db, u)).all()
    apps = db.scalars(select(Application).join(Job).where(Job.organization_id == u.active_organization_id)).all()
    stage_counts = {}
    for a in apps:
        stage_counts[a.stage] = stage_counts.get(a.stage, 0) + 1
    today = datetime.now(timezone.utc)
    week_start = today - timedelta(days=today.weekday(), hours=today.hour, minutes=today.minute, seconds=today.second, microseconds=today.microsecond)
    weekly = []
    for offset in (3, 2, 1, 0):
        start = week_start - timedelta(weeks=offset)
        end = start + timedelta(weeks=1)
        n = sum(1 for item in apps if start <= (item.created_at.replace(tzinfo=timezone.utc) if item.created_at.tzinfo is None else item.created_at) < end)
        weekly.append({'week': start.strftime('%b %d'), 'applications': n})
    return {'jobs': len(jobs), 'active_jobs': sum(j.status == 'published' for j in jobs), 'applications': len(apps),
            'review_queue': sum(a.stage.startswith('awaiting_') or a.stage=='coding_submitted' for a in apps), 'interviews': sum(a.stage in ('video_invited','awaiting_video_review','individual_pending','individual_scheduled') for a in apps),
            'offers': sum(a.stage in ('offer_extended','hired','offer_declined') for a in apps), 'stages': stage_counts,
            'weekly': weekly}


@app.delete('/api/applications/{aid}')
def delete_application(aid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = application_access(db, aid, u)
    if u.role != 'candidate':
        raise HTTPException(403, 'Only the data subject may request deletion')
    paths = [a.resume_path] + [q.video_path for q in questions_for_app(a) if q.video_path]
    for q in questions_for_app(a):
        db.delete(q)
    db.query(CodeSubmission).filter(CodeSubmission.application_id == aid).delete(synchronize_session=False)
    db.query(TeamComment).filter(TeamComment.application_id == aid).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.application_id == aid).delete(synchronize_session=False)
    db.query(AuditEvent).filter(AuditEvent.application_id == aid).delete(synchronize_session=False)
    db.delete(a)
    db.commit()
    from .services.workflows import checkpointer, workflow_lock
    checkpoint_errors = []
    with workflow_lock:
        for thread in (f'cv-{aid}', f'video-{aid}', f'code-{aid}'):
            try:
                checkpointer.delete_thread(thread)
            except Exception as exc:
                checkpoint_errors.append(type(exc).__name__)
    for path in paths:
        if path:
            Path(path).unlink(missing_ok=True)
    if checkpoint_errors:
        raise HTTPException(500, 'Application rows and media deleted, but checkpoint cleanup needs administrator attention')
    return {'deleted': True, 'note': 'Live application records, local media, checkpoint rows and associated audit records deleted; SQLite free-space bytes/backups and external AI provider processing require separate retention controls.'}

# Enterprise modules are attached after the base hiring workflow is declared.
from .enterprise import router as enterprise_router
app.include_router(enterprise_router)
