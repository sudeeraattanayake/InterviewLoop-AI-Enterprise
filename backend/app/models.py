from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # recruiter / candidate
    active_organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recruiter_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey('organizations.id'), index=True)
    title: Mapped[str] = mapped_column(String(160))
    department: Mapped[str] = mapped_column(String(100), default='Engineering')
    location: Mapped[str] = mapped_column(String(160), default='Remote')
    employment_type: Mapped[str] = mapped_column(String(50), default='Full-time')
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default='draft')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    recruiter = relationship('User')
    organization = relationship('Organization')


class Application(Base):
    __tablename__ = 'applications'
    __table_args__ = (UniqueConstraint('job_id', 'candidate_id', name='uq_application'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    resume_filename: Mapped[str] = mapped_column(String(255))
    resume_path: Mapped[str] = mapped_column(String(400))
    resume_text: Mapped[str] = mapped_column(Text)
    ai_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    video_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    stage: Mapped[str] = mapped_column(String(40), default='awaiting_cv_review')
    cv_review: Mapped[dict] = mapped_column(JSON, default=dict)
    video_review: Mapped[dict] = mapped_column(JSON, default=dict)
    recruiter_notes: Mapped[str] = mapped_column(Text, default='')
    interview_datetime: Mapped[str] = mapped_column(String(50), default='')
    interview_link: Mapped[str] = mapped_column(String(500), default='')
    individual_feedback: Mapped[dict] = mapped_column(JSON, default=dict)
    offer_response: Mapped[str] = mapped_column(String(30), default='')
    offer_terms: Mapped[str] = mapped_column(Text, default='')
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    job = relationship('Job')
    candidate = relationship('User')


class InterviewQuestion(Base):
    __tablename__ = 'interview_questions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey('applications.id'), index=True)
    order: Mapped[int] = mapped_column(Integer)
    skill: Mapped[str] = mapped_column(String(160), default='General')
    prompt: Mapped[str] = mapped_column(Text)
    duration_sec: Mapped[int] = mapped_column(Integer, default=180)
    transcript: Mapped[str] = mapped_column(Text, default='')
    video_path: Mapped[str] = mapped_column(String(400), default='')
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey('applications.id'), nullable=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey('jobs.id'), nullable=True)
    event: Mapped[str] = mapped_column(String(120))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Organization(Base):
    __tablename__ = 'organizations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    invite_code: Mapped[str] = mapped_column(String(80), unique=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=180)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Membership(Base):
    __tablename__ = 'memberships'
    __table_args__ = (UniqueConstraint('organization_id', 'user_id', name='uq_member_org'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    role: Mapped[str] = mapped_column(String(20), default='recruiter')


class CodingChallenge(Base):
    __tablename__ = 'coding_challenges'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(150))
    prompt: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), default='python')
    starter_code: Mapped[str] = mapped_column(Text, default='')
    cases: Mapped[list] = mapped_column(JSON, default=list)  # input / expected / public
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CodeSubmission(Base):
    __tablename__ = 'code_submissions'
    __table_args__ = (UniqueConstraint('application_id', 'challenge_id', name='uq_one_code_submission'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey('applications.id'), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey('coding_challenges.id'))
    source_code: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20))
    execution: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewer_notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TeamComment(Base):
    __tablename__ = 'team_comments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey('applications.id'), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    application_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
