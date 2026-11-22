"""Durable-ish single-process reminder tick. Database deduplication persists across restarts.

For multi-worker deployments replace this with a single externally scheduled worker.
"""
from datetime import datetime, timezone, timedelta
import smtplib
from email.message import EmailMessage
from sqlalchemy import select
from ..config import get_settings
from ..db import SessionLocal
from ..models import Application, AuditEvent, Notification, User


def send_due_reminders():
    settings=get_settings()
    now=datetime.now(timezone.utc)
    horizon=now+timedelta(hours=24)
    count=0
    with SessionLocal() as db:
        items=db.scalars(select(Application).where(Application.stage=='individual_scheduled')).all()
        for a in items:
            try:
                start=datetime.fromisoformat(a.interview_datetime.replace('Z','+00:00'))
                if start.tzinfo is None: continue
                start=start.astimezone(timezone.utc)
            except (ValueError,AttributeError):continue
            if not now<start<=horizon:continue
            sent=db.scalar(select(AuditEvent.id).where(AuditEvent.application_id==a.id,AuditEvent.event=='interview_reminder_24h'))
            if sent:continue
            text=(f'Your upcoming interview for {a.job.title} is at {a.interview_datetime}. '
                  f'Meeting: {a.interview_link or "See the InterviewLoop portal"}')
            db.add(Notification(user_id=a.candidate_id,subject='Upcoming individual interview',body=text,application_id=a.id))
            db.add(AuditEvent(actor_id=None,job_id=a.job_id,application_id=a.id,
                              event='interview_reminder_24h',details={'channel':'in_app'}))
            # Save first; provider errors cannot cause repeat/infinite email retries.
            db.commit()
            if settings.enable_email and a.candidate.email_opt_in and settings.smtp_host and settings.smtp_from:
                try:
                    msg=EmailMessage();msg['Subject']='InterviewLoop: interview reminder';msg['From']=settings.smtp_from
                    msg['To']=a.candidate.email;msg.set_content(text)
                    with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=8) as smtp:
                        smtp.starttls();smtp.login(settings.smtp_user,settings.smtp_password);smtp.send_message(msg)
                except (OSError,smtplib.SMTPException):
                    pass  # In-app reminder remains delivered and logged.
            count+=1
    return count
