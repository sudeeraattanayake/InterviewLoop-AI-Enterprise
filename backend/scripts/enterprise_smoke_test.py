"""Run synthetic full-stack enterprise API smoke test after installing requirements."""
import sys,os,tempfile,io
from pathlib import Path
from datetime import datetime,timezone,timedelta
os.environ.update({'DATABASE_URL':'sqlite:///'+tempfile.mkdtemp(prefix='il-runtime-')+'/db.sqlite','DATA_DIR':tempfile.mkdtemp(prefix='il-data-'),'ENABLE_REMINDERS':'false','SECRET_KEY':'debug-only-not-production-secret-00000000000','OPENAI_API_KEY':''})
root=str(Path(__file__).resolve().parents[1])
sys.path.insert(0,root)
# Requires real installed LangGraph, checkpoint and Argon2 dependencies.
from app.main import app
from fastapi.testclient import TestClient
from docx import Document
client=TestClient(app)
def ok(r,status=200):
 if r.status_code!=status:raise AssertionError(f'{r.request.method} {r.url}: {r.status_code} {r.text[:1300]}')
 return r.json() if 'application/json' in r.headers.get('content-type','') else r.content
def reg(name,role):
 x=ok(client.post('/api/auth/register',json={'name':name,'role':role,'email':name.lower().replace(' ','')+'@test.example','password':'Password2026!','company_name':name+' Team'}),201)
 return {'Authorization':'Bearer '+x['token']}
r1=reg('Recruiter Alpha','recruiter')
r2=reg('Recruiter Beta','recruiter')
c=reg('Candidate One','candidate')
org1=ok(client.get('/api/organizations/current',headers=r1))
assert org1['members'][0]['role']=='owner'
assert org1['invite_code']
other=ok(client.get('/api/organizations/current',headers=r2))
assert org1['id']!=other['id']
job=ok(client.post('/api/jobs',headers=r1,json={'title':'AI Engineer','description':'Build LangGraph AI systems for an engineering company using robust APIs and teamwork.', 'requirements':['Python','LangGraph']}),201)
jid=job['id']
assert client.post(f'/api/jobs/{jid}/challenge',headers=r2,json={'title':'Task 1','prompt':'write code'*6,'cases':[]}).status_code==403
challenge=ok(client.post(f'/api/jobs/{jid}/challenge',headers=r1,json={'title':'Sum values','prompt':'Given standard input of integers, output their sum using Python.','language':'python','starter_code':'print(0)','cases':[{'input':'1 2','expected':'3\n','public':True},{'input':'3 4','expected':'7\n','public':False}]}))
assert len(challenge['cases'])==2
ok(client.post(f'/api/jobs/{jid}/publish',headers=r1))
# Candidate sees public test only
assert len(ok(client.get(f'/api/jobs/{jid}/challenge',headers=c))['cases'])==1
from docx import Document
doc=Document();doc.add_paragraph('Python and LangGraph: Built an AI workflow, tested it, deployed it and iterated with a team.')
f=io.BytesIO();doc.save(f)
a=ok(client.post(f'/api/jobs/{jid}/apply',headers=c,files={'cv':('cv.docx',f.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')},data={'ai_consent':'false'}),201)
aid=a['id'];assert a['stage']=='awaiting_cv_review'
assert client.get(f'/api/applications/{aid}',headers=r2).status_code==403
assert client.get('/api/applications',headers=r2).json()==[]
# Beta recruiter may join Alpha after invitation
joined=ok(client.post('/api/organizations/join',headers=r2,json={'invite_code':org1['invite_code']}))
assert joined['id']==org1['id']
assert ok(client.get(f'/api/applications/{aid}',headers=r2))['id']==aid
app_review=ok(client.post(f'/api/applications/{aid}/review-cv',headers=r2,json={'decision':'advance','notes':'Reviewed the submitted role requirements and cited evidence.'}))
assert app_review['stage']=='video_invited'
assert client.post(f'/api/applications/{aid}/voice/token',headers=c).status_code==403
ok(client.post(f'/api/applications/{aid}/video-consent',headers=c,json={'video_consent':True}))
for q in app_review['questions']:
 ok(client.post(f'/api/applications/{aid}/answers/{q["id"]}',headers=c,files={'recording':('x.webm',bytes.fromhex('1a45dfa3')+b'0'*80,'video/webm')},data={'transcript_text':'I wrote Python code for production, tested it and improved it.'}))
ok(client.post(f'/api/applications/{aid}/video-complete',headers=c))
x=ok(client.post(f'/api/applications/{aid}/review-video',headers=r1,json={'decision':'advance','notes':'Interview answers reviewed and technical exercise warranted.'}))
assert x['stage']=='coding_invited'
assert client.get(f'/api/applications/{aid}/coding',headers=c).json()['challenge']['cases']==challenge['cases'][:1]
assert client.post(f'/api/applications/{aid}/coding/review',headers=c,json={'decision':'advance','notes':'I say yes yes yes.'}).status_code==403
sub=ok(client.post(f'/api/applications/{aid}/coding/submit',headers=c,json={'source_code':'print(sum(map(int,input().split())))'}))
assert sub['execution']['status']=='manual_review'
ok(client.post(f'/api/applications/{aid}/coding/review',headers=r2,json={'decision':'advance','notes':'Manually inspected the code solution for correctness.'}))
now=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
ok(client.post(f'/api/applications/{aid}/schedule',headers=r1,json={'starts_at':now,'meeting_link':'https://meet.jit.si/test-ai-123'}))
pdf=ok(client.get(f'/api/applications/{aid}/report',headers=c));assert pdf[:4]==b'%PDF'
ics=ok(client.get(f'/api/applications/{aid}/calendar.ics',headers=c));assert b'BEGIN:VCALENDAR' in ics
notify=ok(client.post(f'/api/applications/{aid}/notify',headers=r1));assert notify['delivered']=='in_app'
ok(client.post(f'/api/applications/{aid}/comments',headers=r2,json={'body':'Discuss evaluation rubric and project ownership.'}))
assert len(ok(client.get(f'/api/applications/{aid}/comments',headers=r1)))==1
assert client.get(f'/api/applications/{aid}/comments',headers=c).status_code==403
assert len(ok(client.get('/api/notifications',headers=c)))>=1
ok(client.post(f'/api/applications/{aid}/final-decision',headers=r2,json={'outcome':'offer','notes':'Human evaluation found job-related project evidence sufficient.','rubric':{'technical':'demonstrated coding'}}))
ok(client.post(f'/api/applications/{aid}/offer-terms',headers=r1,json={'terms':'Salary details to follow in a signed contract.'}))
assert len(ok(client.get('/api/privacy/export',headers=c))['applications'])==1
accepted=ok(client.post(f'/api/applications/{aid}/offer-response',headers=c,json={'response':'accept'}))
assert accepted['stage']=='hired'
assert client.get(f'/api/applications/{aid}',headers=c).json().get('individual_feedback') is None
assert ok(client.get('/api/analytics',headers=r1))['pipeline']['offers']==1
# Prevent cross-tenant access after switching back to Beta
ok(client.post(f'/api/organizations/{other["id"]}/switch',headers=r2))
assert client.get(f'/api/applications/{aid}',headers=r2).status_code==403
print('OK — full synthetic enterprise HTTP flow, tenant isolation, challenge/code, reviews, PDF/ICS, collaboration, notifications and offer response')
