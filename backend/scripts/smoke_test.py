"""Full recruiter/candidate API smoke test (synthetic data, isolated temp database)."""
import io
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

root = tempfile.mkdtemp(prefix='interviewloop-smoke-')
os.environ['DATABASE_URL'] = f'sqlite:///{root}/smoke.db'
os.environ['DATA_DIR'] = root
os.environ['OPENAI_API_KEY'] = ''
os.environ['SECRET_KEY'] = 'smoke-test-secret-only-never-deploy-123456'

from fastapi.testclient import TestClient
from docx import Document
from app.main import app

client = TestClient(app)
suffix = uuid4().hex[:8]


def ok(res, status=200):
    assert res.status_code == status, f'{res.request.method} {res.request.url}: {res.status_code} {res.text}'
    return res.json()


def register(role):
    response = ok(client.post('/api/auth/register', json={
        'name': f'Synthetic {role.capitalize()}',
        'email': f'{role}-{suffix}@example.test',
        'password': 'TestPassword123!',
        'role': role
    }), 201)
    return {'Authorization': f"Bearer {response['token']}"}


recruiter = register('recruiter')
candidate = register('candidate')
job = ok(client.post('/api/jobs', headers=recruiter, json={
    'title': 'Test AI Engineer', 'department': 'AI', 'location': 'Remote', 'employment_type': 'Full-time',
    'description': 'Build agent-based enterprise AI applications, APIs, ML systems and test code with teams.',
    'requirements': ['Python', 'FastAPI', 'LangGraph', 'PostgreSQL']
}), 201)
job_id = job['id']
ok(client.post(f'/api/jobs/{job_id}/publish', headers=recruiter))

doc = Document()
doc.add_heading('Synthetic CV', 0)
doc.add_paragraph('Built Python FastAPI REST APIs and tested applied machine learning models. Used PostgreSQL. This is synthetic demo data and contains no real applicant information.')
buf = io.BytesIO()
doc.save(buf)
cv_data = buf.getvalue()
app_data = ok(client.post(f'/api/jobs/{job_id}/apply', headers=candidate, files={'cv': ('synthetic.docx', cv_data, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}, data={'ai_consent': 'false'}), 201)
aid = app_data['id']
assert app_data['stage'] == 'awaiting_cv_review', app_data
assert app_data['cv_review']['mode'] == 'local_rules'

# Candidate must not be able to authorize a recruiting transition.
blocked = client.post(f'/api/applications/{aid}/review-cv', headers=candidate, json={'decision': 'advance', 'notes': 'Human review rationale'})
assert blocked.status_code == 403

review = ok(client.post(f'/api/applications/{aid}/review-cv', headers=recruiter, json={'decision': 'advance', 'notes': 'Human reviewer checked job-related example evidence.'}))
assert review['stage'] == 'video_invited'
assert len(review['questions']) == 4
ok(client.post(f'/api/applications/{aid}/video-consent', headers=candidate, json={'video_consent': True}))

# Synthetic test bytes validate the upload and persistence path, not actual playable media.
for q in review['questions']:
    ok(client.post(f"/api/applications/{aid}/answers/{q['id']}", headers=candidate,
                   files={'recording': ('test.webm', bytes.fromhex('1a45dfa3')+b'\x00'*64, 'video/webm')},
                   data={'transcript_text': f'I worked on {q["skill"]} in a sample project and validated the API with tests.', 'auto_transcribe': 'false'}))

completed = ok(client.post(f'/api/applications/{aid}/video-complete', headers=candidate))
assert completed['stage'] == 'awaiting_video_review'
assert completed['video_review']['mode'] == 'local_rules'

approved = ok(client.post(f'/api/applications/{aid}/review-video', headers=recruiter,
                          json={'decision': 'advance', 'notes': 'Verified response transcripts; follow-up interview required.'}))
assert approved['stage'] == 'individual_pending'
when = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
scheduled = ok(client.post(f'/api/applications/{aid}/schedule', headers=recruiter, json={'starts_at': when, 'meeting_link': 'https://meet.example.com/test', 'notes': 'Technical deep dive'}))
assert scheduled['stage'] == 'individual_scheduled'
final = ok(client.post(f'/api/applications/{aid}/final-decision', headers=recruiter, json={
    'outcome': 'offer', 'notes': 'Human reviewer decided to extend an offer after structured live interview.',
    'rubric': {'technical':'Discussed technical implementation', 'collaboration':'Shared concrete example'}
}))
assert final['stage'] == 'offer_extended'
assert len(ok(client.get('/api/audit', headers=recruiter))) > 5
assert ok(client.delete(f'/api/applications/{aid}', headers=candidate))['deleted']
print('PASS: auth, job publish, CV, real LangGraph HITL checkpoints, media submission, video evidence, individual schedule, human offer, audit and erasure')
print(f'Isolated test database: {root} (safe to delete)')
