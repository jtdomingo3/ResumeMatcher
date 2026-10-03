"""
Career Path Analysis, 90-Day Roadmap, STAR Bullet Rewriting, and Cover Letter Endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.repository import DBRepository
from backend.app.schemas.profile import ResumeProfile, JobProfile
from backend.app.schemas.career import (
    CareerReport,
    BulletRewriteRequest,
    BulletRewriteResult,
    CoverLetterResult,
    InterviewPrepQuestion,
)
from backend.app.engines.career import CareerAnalyzerEngine
from backend.app.engines.writer import WriterEngine

router = APIRouter(prefix="/career", tags=["Career"])


class CareerAnalyzeRequest(BaseModel):
    resume_id: str = Field(..., description="ID of the uploaded resume")
    target_career: Optional[str] = Field(None, description="Optional target career or specialization")


class CoverLetterApiRequest(BaseModel):
    resume_id: str = Field(..., description="ID of the candidate resume")
    job_id: Optional[str] = Field(None, description="Optional target job ID from DB")
    job_description: Optional[str] = Field(None, description="Raw job description if job_id not provided")
    company_name: Optional[str] = Field(None, description="Target company name")


class InterviewPrepApiRequest(BaseModel):
    resume_id: str = Field(..., description="ID of the candidate resume")
    job_id: str = Field(..., description="ID of the target job posting")


@router.post("/analyze", response_model=CareerReport)
async def analyze_career(req: CareerAnalyzeRequest, db: Session = Depends(get_db)):
    """
    Generate 3 career paths (Vertical, Lateral, Pivot), 30/60/90-day roadmap,
    and market demand calibration for a candidate.
    """
    resume_rec = DBRepository.get_resume(db=db, resume_id=req.resume_id)
    if not resume_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    profile = ResumeProfile.model_validate_json(resume_rec.parsed_profile_json)
    report = await CareerAnalyzerEngine.analyze(profile, target_career=req.target_career)

    DBRepository.save_career_report(db=db, resume_id=req.resume_id, report=report, target_career=req.target_career)
    return report


@router.post("/rewrite-bullet", response_model=BulletRewriteResult)
async def rewrite_bullet(req: BulletRewriteRequest):
    """
    Transform a weak resume bullet into a high-impact Google STAR-XYZ bullet
    with strong action verbs and quantified metric outcomes.
    """
    return await WriterEngine.rewrite_bullet(req)


@router.post("/cover-letter", response_model=CoverLetterResult)
async def generate_cover_letter(req: CoverLetterApiRequest, db: Session = Depends(get_db)):
    """
    Generate a personalized, publication-ready cover letter tailored to a specific job description.
    """
    resume_rec = DBRepository.get_resume(db=db, resume_id=req.resume_id)
    if not resume_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    profile = ResumeProfile.model_validate_json(resume_rec.parsed_profile_json)

    jd_text = ""
    company = req.company_name
    if req.job_id:
        job_rec = DBRepository.get_job(db=db, job_id=req.job_id)
        if job_rec:
            jd_text = job_rec.raw_text
            if not company:
                company = job_rec.company
    elif req.job_description:
        jd_text = req.job_description

    if not jd_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'job_id' or 'job_description' must be provided.",
        )

    return await WriterEngine.generate_cover_letter(
        resume=profile,
        job_description=jd_text,
        company_name=company,
    )


@router.post("/interview-prep", response_model=List[InterviewPrepQuestion])
async def generate_interview_prep(req: InterviewPrepApiRequest, db: Session = Depends(get_db)):
    """
    Generate targeted technical and behavioral interview questions with STAR answer outlines.
    """
    resume_rec = DBRepository.get_resume(db=db, resume_id=req.resume_id)
    if not resume_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    job_rec = DBRepository.get_job(db=db, job_id=req.job_id)
    if not job_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    resume_profile = ResumeProfile.model_validate_json(resume_rec.parsed_profile_json)
    job_profile = JobProfile.model_validate_json(job_rec.parsed_profile_json)

    return await WriterEngine.generate_interview_prep(resume=resume_profile, job=job_profile)
