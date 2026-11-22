"""Optional LOCAL demo users, 2 jobs, sample applications (synthetic data only)."""
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import User, Job, Application, AuditEvent, Organization, Membership, CodingChallenge
from app.security import hash_password
from app.services.workflows import start_cv
from pathlib import Path
from docx import Document

if not get_settings().demo_mode:
    raise SystemExit('Set DEMO_MODE=true in backend/.env to seed demo accounts')
Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    if db.query(User).filter(User.email == 'recruiter@demo.test').first():
        print('Demo already seeded')
        raise SystemExit(0)
    recruiter = User(name='Alex Morgan', email='recruiter@demo.test', password_hash=hash_password('DemoRecruiter2026!'), role='recruiter')
    candidate = User(name='Taylor Rivera', email='candidate@demo.test', password_hash=hash_password('DemoCandidate2026!'), role='candidate')
    db.add_all([recruiter, candidate]); db.flush()
    org=Organization(name='Nebula Talent Lab', invite_code='synthetic-local-invite-code-not-production')
    db.add(org);db.flush()
    db.add(Membership(user_id=recruiter.id,organization_id=org.id,role='owner'))
    recruiter.active_organization_id=org.id
    jobs = [Job(organization_id=org.id,recruiter_id=recruiter.id, title='Senior AI Engineer', department='AI Research', location='Remote • Europe', employment_type='Full-time', status='published', description='Build reliable production LLM agents and retrieval systems. Collaborate with engineers and product teams to evaluate model quality, deploy APIs and monitor performance.', requirements=['Python and FastAPI','LangGraph or agent orchestration','Retrieval augmented generation (RAG)','LLM evaluation and observability','PostgreSQL and SQL']),
            Job(organization_id=org.id,recruiter_id=recruiter.id, title='ML Platform Engineer', department='Infrastructure', location='Milan • Hybrid', employment_type='Full-time', status='published', description='Deliver ML services and performant data tooling with reproducible pipelines, CI and scalable deployment practices.', requirements=['Python and machine learning','CI/CD pipelines','SQL databases','Model serving APIs'])]
    db.add_all(jobs); db.flush()
    example_text = 'Synthetic resume: Built Python FastAPI ML prediction APIs and used PostgreSQL for data storage. Implemented ML experiments and tested pipelines. No other skills are asserted.'
    local_resume = get_settings().root / 'resumes' / 'synthetic-demo.docx'
    local_resume.parent.mkdir(parents=True, exist_ok=True)
    doc = Document(); doc.add_heading('Synthetic Demo Resume',0); doc.add_paragraph(example_text); doc.save(local_resume)
    app = Application(job_id=jobs[0].id, candidate_id=candidate.id, resume_filename='synthetic-demo.docx', resume_path=str(local_resume), resume_text=example_text, ai_consent=False, stage='processing_cv', cv_review={}, video_review={})
    db.add(app); db.flush()
    app.cv_review = start_cv(app.id, {'title':jobs[0].title, 'description':jobs[0].description, 'requirements':jobs[0].requirements}, example_text, False)
    app.stage='awaiting_cv_review'
    db.commit()
    print('Demo seeded. Recruiter: recruiter@demo.test / DemoRecruiter2026!')
    print('Candidate: candidate@demo.test / DemoCandidate2026!')
    print('Synthetic demo application is fully reviewable with a real LangGraph approval checkpoint.')
except Exception:
    db.rollback(); raise
finally:
    db.close()
