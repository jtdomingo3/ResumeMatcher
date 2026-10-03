"""
Job description ingestion, parsing (text or SSRF-guarded URL), and retrieval endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json

from backend.app.db.session import get_db
from backend.app.db.repository import DBRepository
from backend.app.ingestion.normalizer import clean_and_normalize_text
from backend.app.ingestion.jd_parser import JobParser, fetch_page_safely

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobCreateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Optional explicit job title")
    raw_text: Optional[str] = Field(None, description="Pasted job description text")
    url: Optional[str] = Field(None, description="Job posting web URL to fetch and parse")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_job(req: JobCreateRequest, db: Session = Depends(get_db)):
    """
    Ingest a job description by pasting raw text or providing a URL.
    Extracts required skills, preferred skills, seniority, and responsibilities.
    """
    raw_content = ""
    source_url = None

    if req.url:
        source_url = req.url
        try:
            raw_content = await fetch_page_safely(req.url)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch job posting from URL: {str(e)}",
            )
    elif req.raw_text:
        raw_content = req.raw_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'raw_text' or 'url' must be provided.",
        )

    if not raw_content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job description text is empty or could not be extracted.",
        )

    normalized = clean_and_normalize_text(raw_content)
    profile = JobParser.parse(normalized, title=req.title)

    record = DBRepository.save_job(db=db, profile=profile, raw_text=normalized, source_url=source_url)

    return {
        "id": record.id,
        "title": record.title,
        "company": record.company,
        "source_url": record.source_url,
        "created_at": record.created_at.isoformat(),
        "profile": profile.model_dump(),
    }


@router.get("", response_model=List[dict])
async def list_jobs(db: Session = Depends(get_db)):
    """
    List all ingested job descriptions.
    """
    records = DBRepository.list_jobs(db=db)
    return [
        {
            "id": r.id,
            "title": r.title,
            "company": r.company,
            "min_experience_years": r.min_experience_years,
            "required_skills_count": r.required_skills_count,
            "source_url": r.source_url,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/{job_id}")
async def get_job_by_id(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieve full parsed job profile and raw posting content.
    """
    record = DBRepository.get_job(db=db, job_id=job_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    profile_dict = json.loads(record.parsed_profile_json)
    return {
        "id": record.id,
        "title": record.title,
        "company": record.company,
        "source_url": record.source_url,
        "profile": profile_dict,
        "raw_text": record.raw_text,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.delete("/{job_id}")
async def delete_job_by_id(job_id: str, db: Session = Depends(get_db)):
    """
    Delete a job posting and associated matches.
    """
    deleted = DBRepository.delete_job(db=db, job_id=job_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"message": "Job successfully deleted", "id": job_id}
