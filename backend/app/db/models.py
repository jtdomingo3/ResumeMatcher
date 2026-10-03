"""
SQLAlchemy ORM models for resumes, job descriptions, match results, career reports, and chat.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from backend.app.db.session import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class ResumeModel(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    total_experience_years = Column(Float, default=0.0)
    skills_count = Column(Integer, default=0)
    raw_text = Column(Text, nullable=False)
    parsed_profile_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    matches = relationship("MatchModel", back_populates="resume", cascade="all, delete-orphan")
    career_reports = relationship("CareerReportModel", back_populates="resume", cascade="all, delete-orphan")


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    company = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    min_experience_years = Column(Float, default=0.0)
    required_skills_count = Column(Integer, default=0)
    raw_text = Column(Text, nullable=False)
    parsed_profile_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    matches = relationship("MatchModel", back_populates="job", cascade="all, delete-orphan")


class MatchModel(Base):
    __tablename__ = "matches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, nullable=False)
    match_tier = Column(String, nullable=False)
    match_breakdown_json = Column(Text, nullable=False)
    skills_analysis_json = Column(Text, nullable=False)
    ats_report_json = Column(Text, nullable=False)
    gap_analysis_json = Column(Text, nullable=False)
    llm_review_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    resume = relationship("ResumeModel", back_populates="matches")
    job = relationship("JobModel", back_populates="matches")


class CareerReportModel(Base):
    __tablename__ = "career_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    target_career = Column(String, nullable=True)
    current_level = Column(String, nullable=False)
    report_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    resume = relationship("ResumeModel", back_populates="career_reports")


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, default="Career Advisory Session")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    messages = relationship("ChatMessageModel", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessageModel.created_at")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=True)
    model_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    session = relationship("ChatSessionModel", back_populates="messages")


class AppSettingModel(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
