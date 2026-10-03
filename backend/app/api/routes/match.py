"""
Resume-to-Job matching and batch ranking endpoints with explainable scoring.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json

from backend.app.db.session import get_db
from backend.app.db.repository import DBRepository
from backend.app.schemas.profile import ResumeProfile, JobProfile
from backend.app.schemas.match import MatchResult
from backend.app.engines.matcher import MatcherEngine

router = APIRouter(prefix="/match", tags=["Match"])


class SingleMatchRequest(BaseModel):
    resume_id: str = Field(..., description="ID of the uploaded resume")
    job_id: str = Field(..., description="ID of the target job posting")
    use_llm: bool = Field(True, description="Whether to include LLM holistic review or pure deterministic scoring")


class BatchMatchRequest(BaseModel):
    resume_id: Optional[str] = Field(None, description="Resume ID for 1-to-N matching")
    job_ids: Optional[List[str]] = Field(None, description="List of Job IDs to match against")
    job_id: Optional[str] = Field(None, description="Job ID for N-to-1 candidate ranking")
    resume_ids: Optional[List[str]] = Field(None, description="List of Resume IDs to rank")
    use_llm: bool = Field(False, description="Default False for high-throughput batch evaluations")


@router.post("", response_model=MatchResult)
async def match_resume_to_job(req: SingleMatchRequest, db: Session = Depends(get_db)):
    """
    Execute explainable hybrid match between a resume and job description.
    Returns 0-100 overall score, 5-dimensional breakdown, ATS compliance, and gap analysis.
    """
    resume_rec = DBRepository.get_resume(db=db, resume_id=req.resume_id)
    if not resume_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Resume '{req.resume_id}' not found.")

    job_rec = DBRepository.get_job(db=db, job_id=req.job_id)
    if not job_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{req.job_id}' not found.")

    resume_profile = ResumeProfile.model_validate_json(resume_rec.parsed_profile_json)
    job_profile = JobProfile.model_validate_json(job_rec.parsed_profile_json)

    # Execute matching
    result = await MatcherEngine.match(resume_profile, job_profile, use_llm=req.use_llm)

    # Persist match result
    DBRepository.save_match(db=db, resume_id=req.resume_id, job_id=req.job_id, result=result)

    return result


@router.post("/batch")
async def batch_match(req: BatchMatchRequest, db: Session = Depends(get_db)):
    """
    Run 1-to-N or N-to-1 batch ranking across multiple resumes and jobs.
    Returns ranked pairs ordered by overall match score.
    """
    ranked_results = []

    # Case 1: 1 Resume vs N Jobs
    if req.resume_id and req.job_ids:
        resume_rec = DBRepository.get_resume(db=db, resume_id=req.resume_id)
        if not resume_rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
        resume_profile = ResumeProfile.model_validate_json(resume_rec.parsed_profile_json)

        for jid in req.job_ids:
            job_rec = DBRepository.get_job(db=db, job_id=jid)
            if not job_rec:
                continue
            job_profile = JobProfile.model_validate_json(job_rec.parsed_profile_json)
            result = await MatcherEngine.match(resume_profile, job_profile, use_llm=req.use_llm)
            ranked_results.append({
                "job_id": jid,
                "job_title": job_rec.title,
                "company": job_rec.company,
                "overall_score": result.overall_score,
                "match_tier": result.match_tier,
                "matched_skills_count": len(result.skills_analysis.matched_required) + len(result.skills_analysis.matched_preferred),
                "critical_gaps_count": len(result.gap_analysis.critical_skill_gaps),
            })

    # Case 2: N Resumes vs 1 Job
    elif req.job_id and req.resume_ids:
        job_rec = DBRepository.get_job(db=db, job_id=req.job_id)
        if not job_rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        job_profile = JobProfile.model_validate_json(job_rec.parsed_profile_json)

        for rid in req.resume_ids:
            resume_rec = DBRepository.get_resume(db=db, resume_id=rid)
            if not resume_rec:
                continue
            resume_profile = ResumeProfile.model_validate_json(resume_rec.parsed_profile_json)
            result = await MatcherEngine.match(resume_profile, job_profile, use_llm=req.use_llm)
            ranked_results.append({
                "resume_id": rid,
                "candidate_name": resume_rec.full_name or resume_rec.filename,
                "experience_years": resume_rec.total_experience_years,
                "overall_score": result.overall_score,
                "match_tier": result.match_tier,
                "critical_gaps_count": len(result.gap_analysis.critical_skill_gaps),
            })
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specify either ('resume_id' and 'job_ids') or ('job_id' and 'resume_ids').",
        )

    # Sort descending by overall score
    ranked_results.sort(key=lambda x: x["overall_score"], reverse=True)
    return {"total": len(ranked_results), "rankings": ranked_results}


@router.get("", response_model=List[dict])
async def list_matches(db: Session = Depends(get_db)):
    """
    List all recent match analyses.
    """
    matches = DBRepository.list_matches(db=db)
    return [
        {
            "id": m.id,
            "resume_id": m.resume_id,
            "job_id": m.job_id,
            "overall_score": m.overall_score,
            "match_tier": m.match_tier,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in matches
    ]


@router.get("/{match_id}")
async def get_match_by_id(match_id: str, db: Session = Depends(get_db)):
    """
    Retrieve full saved match result by ID.
    """
    match_rec = DBRepository.get_match(db=db, match_id=match_id)
    if not match_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match record not found.")

    return {
        "id": match_rec.id,
        "resume_id": match_rec.resume_id,
        "job_id": match_rec.job_id,
        "overall_score": match_rec.overall_score,
        "match_tier": match_rec.match_tier,
        "breakdown": json.loads(match_rec.match_breakdown_json),
        "skills_analysis": json.loads(match_rec.skills_analysis_json),
        "ats_report": json.loads(match_rec.ats_report_json),
        "gap_analysis": json.loads(match_rec.gap_analysis_json),
        "llm_review": json.loads(match_rec.llm_review_json) if match_rec.llm_review_json else None,
        "created_at": match_rec.created_at.isoformat() if match_rec.created_at else None,
    }
