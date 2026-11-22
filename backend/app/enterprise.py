"""Enterprise modules: tenant isolation, coding, voice, collaboration, reports, calendar and notifications.

Add via app.include_router at end of main.py. All workflows remain recruiter controlled.
"""
import io
import secrets
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
import smtplib
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import get_settings
from .db import get_db
from .models import (User, Job, Application, Membership, Organization, CodingChallenge,
                     CodeSubmission, TeamComment, Notification, InterviewQuestion, AuditEvent)
from .schemas import (OrganizationIn, JoinOrganizationIn, ChallengeIn, CodeIn, CommentIn,
                      CodeReviewIn, OfferReplyIn, OfferTermsIn, PreferenceIn)
from .security import current_user, role_guard
from .main import (org_access, recruiter_jobs, job_for_recruiter, application_access,
                   recruiter_application, log, notify, utc_iso, app_json, questions_for_app)
from .services.enterprise_ai import voice_session_secret, run_remote_tests
from .services.reporting import create_report
from .services.workflows import start_code, resume_code, report_sections

router = APIRouter(prefix='/api', tags=['Enterprise'])
settings = get_settings()


def org_item(db, org, user):
    membership = db.scalar(select(Membership).where(Membership.user_id==user.id, Membership.organization_id==org.id))
    return {'id':org.id,'name':org.name,'retention_days':org.retention_days,
            'role': membership.role if membership else None,'active':user.active_organization_id==org.id}


def ensure_org_owner(db, user):
    if user.role!='recruiter' or not user.active_organization_id:
        raise HTTPException(403, 'Select an organization')
    membership = db.scalar(select(Membership).where(Membership.user_id==user.id, Membership.organization_id==user.active_organization_id, Membership.role=='owner'))
    if not membership:
        raise HTTPException(403, 'Workspace owner permission required')
    return db.get(Organization, user.active_organization_id)


@router.get('/organizations')
def list_organizations(db:Session=Depends(get_db), u:User=Depends(role_guard('recruiter'))):
    query=select(Organization).join(Membership, Membership.organization_id==Organization.id).where(Membership.user_id==u.id)
    return [org_item(db, x, u) for x in db.scalars(query).all()]


@router.post('/organizations',status_code=201)
def create_organization(body: OrganizationIn, db:Session=Depends(get_db), u:User=Depends(role_guard('recruiter'))):
    org=Organization(name=body.name.strip(), invite_code=secrets.token_urlsafe(24))
    db.add(org); db.flush()
    db.add(Membership(user_id=u.id, organization_id=org.id, role='owner'))
    u.active_organization_id=org.id
    log(db,u.id,'organization_created',name=org.name)
    db.commit()
    return org_item(db,org,u)


@router.post('/organizations/join')
def join_organization(body:JoinOrganizationIn, db:Session=Depends(get_db), u:User=Depends(role_guard('recruiter'))):
    org=db.scalar(select(Organization).where(Organization.invite_code==body.invite_code.strip()))
    if not org:
        raise HTTPException(404,'Invalid organization invitation')
    existing=db.scalar(select(Membership).where(Membership.organization_id==org.id,Membership.user_id==u.id))
    if not existing:
        db.add(Membership(user_id=u.id,organization_id=org.id,role='recruiter'))
    u.active_organization_id=org.id
    log(db,u.id,'organization_joined',organization_id=org.id)
    db.commit()
    return org_item(db,org,u)


@router.post('/organizations/{oid}/switch')
def switch_organization(oid:int,db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    org=db.get(Organization,oid)
    if not org or not db.scalar(select(Membership).where(Membership.user_id==u.id,Membership.organization_id==oid)):
        raise HTTPException(403,'Organization membership required')
    u.active_organization_id=oid
    db.commit()
    return org_item(db,org,u)


@router.get('/organizations/current')
def current_organization(db:Session=Depends(get_db), u:User=Depends(role_guard('recruiter'))):
    org=db.get(Organization,u.active_organization_id) if u.active_organization_id else None
    if not org or not org_access(db,u,org.id):
        raise HTTPException(404,'No active organization')
    memberrows=db.execute(select(Membership,User).join(User,User.id==Membership.user_id).where(Membership.organization_id==org.id)).all()
    owner=any(m.user_id==u.id and m.role=='owner' for m,_ in memberrows)
    return {**org_item(db,org,u), 'invite_code':org.invite_code if owner else None,
            'members':[{'id':member.id,'name':person.name,'email':person.email,'role':member.role} for member,person in memberrows]}


@router.post('/organizations/invite/rotate')
def rotate_org_invite(db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    org=ensure_org_owner(db,u)
    org.invite_code=secrets.token_urlsafe(24)
    log(db,u.id,'invite_rotated')
    db.commit()
    return {'invite_code':org.invite_code}


@router.get('/jobs/{jid}/challenge')
def challenge_view(jid:int,db:Session=Depends(get_db),u:User=Depends(current_user)):
    job=db.get(Job,jid)
    if not job or (u.role=='recruiter' and not org_access(db,u,job.organization_id)):
        raise HTTPException(404,'Job not available')
    if u.role=='candidate' and job.status!='published':
        raise HTTPException(404,'Job not available')
    challenge=db.scalar(select(CodingChallenge).where(CodingChallenge.job_id==jid))
    if not challenge:return None
    recruiter=u.role=='recruiter'
    return {'id':challenge.id,'job_id':jid,'title':challenge.title,'prompt':challenge.prompt,
            'language':challenge.language,'starter_code':challenge.starter_code,
            'cases':challenge.cases if recruiter else [x for x in challenge.cases if x.get('public',False)],
            'total_tests':len(challenge.cases)}


@router.post('/jobs/{jid}/challenge')
def upsert_challenge(jid:int,body:ChallengeIn,db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    job=job_for_recruiter(db,jid,u)
    if job.status!='draft':
        raise HTTPException(409,'Create or edit a coding challenge before publishing the job')
    ch=db.scalar(select(CodingChallenge).where(CodingChallenge.job_id==jid))
    if ch is None:
        ch=CodingChallenge(job_id=jid)
        db.add(ch)
    for k,v in body.model_dump().items():setattr(ch,k,v)
    log(db,u.id,'coding_challenge_saved',job_id=jid,language=ch.language)
    db.commit()
    return challenge_view(jid,db,u)


@router.get('/applications/{aid}/coding')
def application_coding(aid:int,db:Session=Depends(get_db),u:User=Depends(current_user)):
    a=application_access(db,aid,u)
    ch=db.scalar(select(CodingChallenge).where(CodingChallenge.job_id==a.job_id))
    if not ch:return {'challenge':None,'submission':None}
    if u.role=='candidate' and a.stage not in ('coding_invited','coding_submitted','individual_pending','individual_scheduled','offer_extended','declined_code','declined_final'):
        return {'challenge':None,'submission':None}
    chinfo={'id':ch.id,'title':ch.title,'prompt':ch.prompt,'language':ch.language,
            'starter_code':ch.starter_code,'cases':ch.cases if u.role=='recruiter' else [x for x in ch.cases if x.get('public')],
            'total_tests':len(ch.cases)}
    submission=db.scalar(select(CodeSubmission).where(CodeSubmission.application_id==aid,CodeSubmission.challenge_id==ch.id))
    result=None
    if submission:
        result={'id':submission.id,'source_code':submission.source_code,'language':submission.language,
                'execution':submission.execution,'created_at':utc_iso(submission.created_at),
                'reviewer_notes':submission.reviewer_notes if u.role=='recruiter' else ''}
    return {'challenge':chinfo,'submission':result}


@router.post('/applications/{aid}/coding/submit')
def submit_code(aid:int,body:CodeIn,db:Session=Depends(get_db),u:User=Depends(role_guard('candidate'))):
    a=application_access(db,aid,u)
    if a.stage!='coding_invited':
        raise HTTPException(409,'Coding assessment is not available at this stage')
    ch=db.scalar(select(CodingChallenge).where(CodingChallenge.job_id==a.job_id))
    if not ch:raise HTTPException(404,'Challenge not found')
    if db.scalar(select(CodeSubmission).where(CodeSubmission.application_id==aid)):
        raise HTTPException(409,'Coding assessment has already been submitted')
    execution=run_remote_tests(body.source_code,ch.language,ch.cases)
    execution['evidence']=start_code(aid,body.source_code,ch.language,execution)
    db.add(CodeSubmission(application_id=aid,challenge_id=ch.id,source_code=body.source_code,
                          language=ch.language,execution=execution))
    a.stage='coding_submitted'
    log(db,u.id,'coding_answer_submitted',app_id=aid,execution_status=execution.get('status'))
    db.commit()
    return {'submitted':True,'execution':execution}


@router.post('/applications/{aid}/coding/review')
def review_code(aid:int,body:CodeReviewIn,db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    a=recruiter_application(db,aid,u)
    if a.stage!='coding_submitted' or body.decision not in ('advance','decline'):
        raise HTTPException(409,'Application needs a submitted coding answer and human advance/decline')
    sub=db.scalar(select(CodeSubmission).where(CodeSubmission.application_id==aid))
    if not sub:raise HTTPException(404,'Coding submission not found')
    result=resume_code(aid,body.decision,body.notes)
    if result.get('decision')!=body.decision:
        raise HTTPException(500,'Technical assessment checkpoint did not confirm the human decision')
    sub.reviewer_notes=body.notes
    a.stage='individual_pending' if body.decision=='advance' else 'declined_code'
    notify(db,a.candidate_id,'Coding assessment reviewed',f'Your application for {a.job.title} has a new stage. Sign in for details.',aid)
    log(db,u.id,'human_coding_decision',app_id=aid,decision=body.decision,notes=body.notes)
    db.commit()
    return app_json(a,details=True)


@router.post('/applications/{aid}/voice/token')
def voice_token(aid:int,db:Session=Depends(get_db),u:User=Depends(role_guard('candidate'))):
    a=application_access(db,aid,u)
    if a.stage!='video_invited' or not a.ai_consent or not a.video_consent:
        raise HTTPException(403,'AI processing and interview recording consent are required; access only during your video stage')
    qs=questions_for_app(a)
    if not qs:raise HTTPException(409,'Interview questions not generated')
    return voice_session_secret(a.id,u.id,a.job.title,[q.prompt for q in qs])


@router.get('/applications/{aid}/report')
def report(aid:int,db:Session=Depends(get_db),u:User=Depends(current_user)):
    a=application_access(db,aid,u)
    # Candidate report deliberately excludes internal reviewer notes and private evaluative rubrics.
    qs=questions_for_app(a)
    code_submission=db.scalar(select(CodeSubmission).where(CodeSubmission.application_id==aid))
    outline=report_sections({'application_id':a.id,'stage':a.stage,
        'criteria_count':len(a.job.requirements),'video_answers':sum(bool(q.transcript) for q in qs),
        'coding_status':code_submission.execution.get('status','Not executed') if code_submission else 'Not assigned'})
    pdf=create_report(a,qs,candidate_view=(u.role=='candidate'),outline=outline)
    return StreamingResponse(io.BytesIO(pdf),media_type='application/pdf',
        headers={'Content-Disposition':f'attachment; filename="interviewloop-report-{aid}.pdf"',
                 'Cache-Control':'private, no-store'})


def ics_escape(value:str):
    return value.replace('\\','\\\\').replace('\n','\\n').replace(',','\\,').replace(';','\\;')


@router.get('/applications/{aid}/calendar.ics')
def calendar_ics(aid:int,db:Session=Depends(get_db),u:User=Depends(current_user)):
    a=application_access(db,aid,u)
    if not a.interview_datetime:raise HTTPException(404,'Interview not scheduled')
    when=datetime.fromisoformat(a.interview_datetime.replace('Z','+00:00')).astimezone(timezone.utc)
    end=when+timedelta(minutes=45)
    fmt=lambda d:d.strftime('%Y%m%dT%H%M%SZ')
    data='\r\n'.join(['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//InterviewLoop AI//EN','BEGIN:VEVENT',
        f'UID:interview-{a.id}@interviewloop.local',f'DTSTAMP:{fmt(datetime.now(timezone.utc))}',
        f'DTSTART:{fmt(when)}',f'DTEND:{fmt(end)}',
        f'SUMMARY:{ics_escape("Individual interview - "+a.job.title)}',
        f'DESCRIPTION:{ics_escape("Interview information: "+(a.interview_link or "Check your portal"))}',
        'END:VEVENT','END:VCALENDAR',''])
    return Response(data,media_type='text/calendar',headers={'Content-Disposition':f'attachment; filename="interview-{aid}.ics"'})


@router.get('/applications/{aid}/comments')
def comments(aid:int,db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    recruiter_application(db,aid,u)
    rows=db.execute(select(TeamComment,User).join(User,User.id==TeamComment.author_id).where(TeamComment.application_id==aid).order_by(TeamComment.id.desc())).all()
    return [{'id':c.id,'author':p.name,'body':c.body,'created_at':utc_iso(c.created_at)} for c,p in rows]


@router.post('/applications/{aid}/comments')
def add_comment(aid:int,body:CommentIn,db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    recruiter_application(db,aid,u)
    db.add(TeamComment(application_id=aid,author_id=u.id,body=body.body.strip()))
    log(db,u.id,'team_note_added',app_id=aid)
    db.commit()
    return comments(aid,db,u)


@router.get('/notifications')
def notifications(db:Session=Depends(get_db),u:User=Depends(current_user)):
    records=db.scalars(select(Notification).where(Notification.user_id==u.id).order_by(Notification.id.desc()).limit(70)).all()
    return [{'id':n.id,'subject':n.subject,'body':n.body,'application_id':n.application_id,
             'read':bool(n.read_at),'created_at':utc_iso(n.created_at)} for n in records]


@router.post('/notifications/{nid}/read')
def read_notification(nid:int,db:Session=Depends(get_db),u:User=Depends(current_user)):
    note=db.get(Notification,nid)
    if not note or note.user_id!=u.id:raise HTTPException(404,'Notification not found')
    note.read_at=datetime.now(timezone.utc)
    db.commit()
    return {'read':True}


@router.patch('/auth/preferences')
def update_preferences(body:PreferenceIn,db:Session=Depends(get_db),u:User=Depends(current_user)):
    u.email_opt_in=body.email_opt_in
    db.commit()
    return {'email_opt_in':u.email_opt_in}


@router.post('/applications/{aid}/notify')
def send_invite_notification(aid:int,db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    a=recruiter_application(db,aid,u)
    if a.stage!='individual_scheduled':raise HTTPException(409,'Schedule interview first')
    subject=f'InterviewLoop: interview invitation for {a.job.title}'
    text=f'Hello {a.candidate.name},\n\nYour individual interview is scheduled at {a.interview_datetime} (timezone included).\nMeeting: {a.interview_link or "See your interview portal"}\n\nPlease sign into the candidate portal for details.'
    notify(db,a.candidate_id,subject,text,aid)
    mode='in_app'
    if settings.enable_email and a.candidate.email_opt_in and settings.smtp_host and settings.smtp_from:
        try:
            msg=EmailMessage();msg['From']=settings.smtp_from;msg['To']=a.candidate.email;msg['Subject']=subject;msg.set_content(text)
            with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=8) as server:
                server.starttls();server.login(settings.smtp_user,settings.smtp_password);server.send_message(msg)
            mode='in_app_and_email'
        except (OSError,smtplib.SMTPException):
            mode='in_app_email_failed'
    log(db,u.id,'interview_invitation_sent',app_id=aid,channel=mode)
    db.commit()
    return {'delivered':mode,'message':'In-app notification saved; email requires SMTP and candidate opt-in.'}


@router.post('/applications/{aid}/offer-terms')
def set_offer_terms(aid:int,body:OfferTermsIn,db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    a=recruiter_application(db,aid,u)
    if a.stage!='offer_extended':raise HTTPException(409,'Only after a human-issued offer')
    a.offer_terms=body.terms.strip()
    log(db,u.id,'offer_terms_documented',app_id=aid)
    notify(db,a.candidate_id,'Offer terms available','Sign in to review the offered terms.',aid)
    db.commit()
    return {'offer_terms':a.offer_terms}


@router.post('/applications/{aid}/offer-response')
def offer_response(aid:int,body:OfferReplyIn,db:Session=Depends(get_db),u:User=Depends(role_guard('candidate'))):
    a=application_access(db,aid,u)
    if a.stage!='offer_extended' or body.response not in ('accept','decline'):
        raise HTTPException(409,'An active offer and accept/decline response are required')
    a.offer_response=body.response
    a.stage='hired' if body.response=='accept' else 'offer_declined'
    log(db,u.id,'candidate_offer_response',app_id=aid,response=body.response)
    # All active company members see the update in the pipeline; no AI selection.
    db.commit()
    return app_json(a,details=True)


@router.get('/analytics')
def analytics(db:Session=Depends(get_db),u:User=Depends(role_guard('recruiter'))):
    jobs=db.scalars(recruiter_jobs(db,u)).all()
    apps=db.scalars(select(Application).join(Job).where(Job.organization_id==u.active_organization_id)).all()
    times=[]
    by_job=[]
    for j in jobs:
        related=[a for a in apps if a.job_id==j.id]
        by_job.append({'title':j.title,'applications':len(related),
                       'reviewed':sum(a.stage not in ('processing_cv','awaiting_cv_review','cv_processing_error') for a in related),
                       'offers':sum(a.stage in ('offer_extended','hired','offer_declined') for a in related)})
    for a in apps:
        if a.stage in ('offer_extended','hired','offer_declined') and a.updated_at and a.created_at:
            times.append(max(0,(a.updated_at-a.created_at).total_seconds()/86400))
    pipeline={'applied':len(apps), 'cv_reviewed':sum(x['reviewed'] for x in by_job),
              'video_invited':sum(a.stage not in ('processing_cv','awaiting_cv_review','cv_processing_error','declined_cv') for a in apps),
              'interviewed':sum(a.stage in ('individual_scheduled','offer_extended','declined_final','hired','offer_declined') for a in apps),
              'offers':sum(a.stage in ('offer_extended','hired','offer_declined') for a in apps)}
    return {'pipeline':pipeline,'by_job':by_job[:30], 'average_days_to_offer':round(sum(times)/len(times),1) if times else None,
            'jobs_open':sum(j.status=='published' for j in jobs),'human_approval_queue':sum(a.stage.startswith('awaiting_') or a.stage=='coding_submitted' for a in apps)}


@router.get('/privacy/export')
def export_private_data(db:Session=Depends(get_db),u:User=Depends(role_guard('candidate'))):
    apps=db.scalars(select(Application).where(Application.candidate_id==u.id)).all()
    return {'user':{'name':u.name,'email':u.email}, 'applications':[
        {'id':a.id,'role':a.job.title,'stage':a.stage,'cv_text':a.resume_text,
         'questions':[{'prompt':q.prompt,'transcript':q.transcript} for q in questions_for_app(a)]}
         for a in apps], 'note':'Media recordings can be downloaded from the authenticated API before deletion.'}
