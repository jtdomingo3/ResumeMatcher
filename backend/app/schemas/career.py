"""
Schemas for Career Analysis, Path Exploration, Bullet Rewriting, and Interview Prep.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CareerPathOption(BaseModel):
    title: str = Field(..., description="Target role title")
    path_type: str = Field(..., description="Vertical, Lateral, or Pivot")
    fit_score: int = Field(..., ge=0, le=100)
    rationale: str
    required_skills: List[str]
    transferable_skills: List[str]
    timeline_months: str = "6-12 months"


class RoadmapMilestone(BaseModel):
    phase: str = Field(..., description="Day 1-30, Day 31-60, or Day 61-90")
    focus_area: str
    goals: List[str]
    recommended_resources: List[str] = Field(default_factory=list, description="Courses, documentation, projects")


class MarketInsight(BaseModel):
    role_title: str
    demand_trend: str = "High Demand"  # High, Growing, Stable, Declining
    estimated_salary_range: str = "$110k - $160k"
    in_demand_skills: List[str]
    market_summary: str
    citations: List[str] = Field(default_factory=list)


class CareerReport(BaseModel):
    id: str
    candidate_name: str
    current_level: str
    career_paths: List[CareerPathOption]
    roadmap_90_days: List[RoadmapMilestone]
    market_insights: MarketInsight
    generated_with_model: Optional[str] = None


class BulletRewriteRequest(BaseModel):
    bullet_text: str
    target_role: Optional[str] = None
    target_skill: Optional[str] = None


class BulletRewriteResult(BaseModel):
    original: str
    rewritten_star: str
    metrics_quantified: str
    action_verb_used: str
    improvement_rationale: str


class CoverLetterRequest(BaseModel):
    resume_id: Optional[str] = None
    job_description: str
    company_name: Optional[str] = None
    tone: str = "Professional & Engaging"


class CoverLetterResult(BaseModel):
    cover_letter_markdown: str
    key_highlights_included: List[str]


class InterviewPrepQuestion(BaseModel):
    category: str = "Technical"  # Technical, Behavioral, System Design
    question: str
    what_interviewer_looks_for: str
    star_answer_outline: str
