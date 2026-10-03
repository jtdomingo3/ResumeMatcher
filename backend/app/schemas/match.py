"""
Schemas for Resume-to-Job Matching, Scoring Breakdown, ATS Report, and Gap Analysis.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MatchBreakdown(BaseModel):
    skills_score: float = Field(..., ge=0.0, le=100.0, description="Score based on required and preferred skills coverage")
    semantic_score: float = Field(..., ge=0.0, le=100.0, description="Embedding cosine similarity between experience and job description")
    experience_score: float = Field(..., ge=0.0, le=100.0, description="Seniority and years of experience alignment")
    education_score: float = Field(..., ge=0.0, le=100.0, description="Degree and educational requirement fit")
    llm_rubric_score: float = Field(..., ge=0.0, le=100.0, description="Holistic assessment from AI reasoning")
    overall_score: int = Field(..., ge=0, le=100, description="Weighted composite match score (0-100)")


class SkillMatchDetails(BaseModel):
    matched_required: List[str] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    matched_preferred: List[str] = Field(default_factory=list)
    missing_preferred: List[str] = Field(default_factory=list)
    evidence_by_skill: Dict[str, str] = Field(default_factory=dict, description="Contextual snippet from resume for each matched skill")


class AtsReport(BaseModel):
    score: int = Field(..., ge=0, le=100)
    format_issues: List[str] = Field(default_factory=list)
    found_headings: List[str] = Field(default_factory=list)
    missing_headings: List[str] = Field(default_factory=list)
    has_contact_info: bool = True
    word_count: int = 0
    verdict: str = "PASS"  # PASS, CAUTION, REVISE


class GapAnalysis(BaseModel):
    critical_skill_gaps: List[str] = Field(default_factory=list)
    bonus_skill_gaps: List[str] = Field(default_factory=list)
    experience_gap_notes: Optional[str] = None
    priority_fixes: List[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    id: str
    resume_name: str = "Candidate Resume"
    job_title: str = "Job Opening"
    overall_score: int = Field(..., ge=0, le=100)
    match_tier: str = Field(..., description="High Match, Strong Match, Moderate Match, or Low Match")
    summary: str = ""
    breakdown: MatchBreakdown
    skills_analysis: SkillMatchDetails
    ats_report: AtsReport
    gap_analysis: GapAnalysis
    llm_eval_notes: Optional[str] = None
    evaluated_with_model: Optional[str] = None
