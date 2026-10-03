"""
Resume ingestion, profile management, and retrieval endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import json

from backend.app.db.session import get_db
from backend.app.db.repository import DBRepository
from backend.app.ingestion.parsers import DocumentParser
from backend.app.ingestion.normalizer import clean_and_normalize_text
from backend.app.ingestion.resume_parser import ResumeParser
from backend.app.core.redaction import mask_pii
from backend.app.schemas.profile import ResumeProfile

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    mask_pii_enabled: bool = Form(default=False),
    db: Session = Depends(get_db),
):
    """
    Upload and parse a resume document (PDF, DOCX, TXT).
    Extracts candidate profile, skills, experience, and education.
    """
    filename = file.filename or "resume.txt"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    allowed_exts = {".pdf", ".docx", ".txt", ".md"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(allowed_exts)}",
        )

    # Read bytes (capped at 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5MB upload limit.",
        )

    # 1. Parse document bytes to raw text
    try:
        raw_text = DocumentParser.parse_bytes(content, filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse document: {str(e)}",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded document contains no readable text. If this is a scanned PDF, please provide an OCR-processed or text-based document.",
        )

    # 2. Normalize text
    normalized_text = clean_and_normalize_text(raw_text)

    # 3. Optional PII masking
    processed_text = normalized_text
    pii_map = {}
    if mask_pii_enabled:
        processed_text, pii_map = mask_pii(normalized_text)

    # 4. Extract structured ResumeProfile
    profile = ResumeParser.parse(processed_text)
    if mask_pii_enabled:
        profile.pii_masked = True
        profile.pii_mapping = pii_map

    # 5. Persist to database
    record = DBRepository.save_resume(db=db, filename=filename, profile=profile, raw_text=normalized_text)

    return {
        "id": record.id,
        "filename": record.filename,
        "created_at": record.created_at.isoformat(),
        "profile": profile.model_dump(),
    }


@router.get("", response_model=List[dict])
async def list_resumes(db: Session = Depends(get_db)):
    """
    List all uploaded resumes with summary metadata.
    """
    records = DBRepository.list_resumes(db=db)
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "full_name": r.full_name,
            "total_experience_years": r.total_experience_years,
            "skills_count": r.skills_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/{resume_id}")
async def get_resume_by_id(resume_id: str, db: Session = Depends(get_db)):
    """
    Retrieve full parsed resume profile and raw text.
    """
    record = DBRepository.get_resume(db=db, resume_id=resume_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    profile_dict = json.loads(record.parsed_profile_json)
    return {
        "id": record.id,
        "filename": record.filename,
        "profile": profile_dict,
        "raw_text": record.raw_text,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.delete("/{resume_id}")
async def delete_resume_by_id(resume_id: str, db: Session = Depends(get_db)):
    """
    Delete a resume and its associated match history.
    """
    deleted = DBRepository.delete_resume(db=db, resume_id=resume_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return {"message": "Resume successfully deleted", "id": resume_id}
