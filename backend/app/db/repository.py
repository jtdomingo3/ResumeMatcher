"""
Database repository helpers for CRUD operations on resumes, jobs, matches, and chat.
"""

import json
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.models import (
    ResumeModel,
    JobModel,
    MatchModel,
    CareerReportModel,
    ChatSessionModel,
    ChatMessageModel,
    AppSettingModel,
)
from backend.app.schemas.profile import ResumeProfile, JobProfile
from backend.app.schemas.match import MatchResult
from backend.app.schemas.career import CareerReport


class DBRepository:
    """
    Data access layer for application persistence.
    """

    # --- Resumes ---
    @staticmethod
    def save_resume(db: Session, filename: str, profile: ResumeProfile, raw_text: str) -> ResumeModel:
        record = ResumeModel(
            filename=filename,
            full_name=profile.full_name,
            email=profile.email,
            phone=profile.phone,
            total_experience_years=profile.total_experience_years,
            skills_count=len(profile.skills),
            raw_text=raw_text,
            parsed_profile_json=profile.model_dump_json(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_resume(db: Session, resume_id: str) -> Optional[ResumeModel]:
        return db.query(ResumeModel).filter(ResumeModel.id == resume_id).first()

    @staticmethod
    def list_resumes(db: Session, limit: int = 50) -> List[ResumeModel]:
        return db.query(ResumeModel).order_by(desc(ResumeModel.created_at)).limit(limit).all()

    @staticmethod
    def delete_resume(db: Session, resume_id: str) -> bool:
        rec = db.query(ResumeModel).filter(ResumeModel.id == resume_id).first()
        if rec:
            db.delete(rec)
            db.commit()
            return True
        return False

    # --- Jobs ---
    @staticmethod
    def save_job(db: Session, profile: JobProfile, raw_text: str, source_url: Optional[str] = None) -> JobModel:
        record = JobModel(
            title=profile.title,
            company=profile.company,
            source_url=source_url,
            min_experience_years=profile.min_experience_years,
            required_skills_count=len(profile.required_skills),
            raw_text=raw_text,
            parsed_profile_json=profile.model_dump_json(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[JobModel]:
        return db.query(JobModel).filter(JobModel.id == job_id).first()

    @staticmethod
    def list_jobs(db: Session, limit: int = 50) -> List[JobModel]:
        return db.query(JobModel).order_by(desc(JobModel.created_at)).limit(limit).all()

    @staticmethod
    def delete_job(db: Session, job_id: str) -> bool:
        rec = db.query(JobModel).filter(JobModel.id == job_id).first()
        if rec:
            db.delete(rec)
            db.commit()
            return True
        return False

    # --- Matches ---
    @staticmethod
    def save_match(db: Session, resume_id: str, job_id: str, result: MatchResult) -> MatchModel:
        record = MatchModel(
            id=result.id,
            resume_id=resume_id,
            job_id=job_id,
            overall_score=result.overall_score,
            match_tier=result.match_tier,
            match_breakdown_json=result.breakdown.model_dump_json(),
            skills_analysis_json=result.skills_analysis.model_dump_json(),
            ats_report_json=result.ats_report.model_dump_json(),
            gap_analysis_json=result.gap_analysis.model_dump_json(),
            llm_review_json=json.dumps(result.llm_eval_notes) if result.llm_eval_notes else None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_match(db: Session, match_id: str) -> Optional[MatchModel]:
        return db.query(MatchModel).filter(MatchModel.id == match_id).first()

    @staticmethod
    def list_matches(db: Session, limit: int = 50) -> List[MatchModel]:
        return db.query(MatchModel).order_by(desc(MatchModel.created_at)).limit(limit).all()

    # --- Career Reports ---
    @staticmethod
    def save_career_report(db: Session, resume_id: str, report: CareerReport, target_career: Optional[str] = None) -> CareerReportModel:
        record = CareerReportModel(
            id=report.id,
            resume_id=resume_id,
            target_career=target_career,
            current_level=report.current_level,
            report_json=report.model_dump_json(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_career_report(db: Session, report_id: str) -> Optional[CareerReportModel]:
        return db.query(CareerReportModel).filter(CareerReportModel.id == report_id).first()

    @staticmethod
    def get_career_reports_for_resume(db: Session, resume_id: str) -> List[CareerReportModel]:
        return db.query(CareerReportModel).filter(CareerReportModel.resume_id == resume_id).order_by(desc(CareerReportModel.created_at)).all()

    # --- Chat ---
    @staticmethod
    def create_chat_session(db: Session, title: str = "Career Advisory Session") -> ChatSessionModel:
        session = ChatSessionModel(title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def list_chat_sessions(db: Session, limit: int = 20) -> List[ChatSessionModel]:
        return db.query(ChatSessionModel).order_by(desc(ChatSessionModel.updated_at)).limit(limit).all()

    @staticmethod
    def get_chat_session(db: Session, session_id: str) -> Optional[ChatSessionModel]:
        return db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()

    @staticmethod
    def add_chat_message(
        db: Session,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[List[dict]] = None,
        model_used: Optional[str] = None,
    ) -> ChatMessageModel:
        msg = ChatMessageModel(
            session_id=session_id,
            role=role,
            content=content,
            citations_json=json.dumps(citations) if citations else None,
            model_used=model_used,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg
