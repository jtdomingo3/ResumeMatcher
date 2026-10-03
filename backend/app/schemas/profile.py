"""
Domain Schemas for Candidate Resumes and Job Descriptions.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SkillItem(BaseModel):
    name: str = Field(..., description="Canonical or extracted skill name")
    category: str = Field("General", description="Skill category, e.g. Language, Framework, Cloud, Database, Soft Skill")
    years: Optional[float] = Field(None, description="Estimated years of experience if mentioned")
    level: Optional[str] = Field("Intermediate", description="Beginner, Intermediate, Advanced, Expert")
    evidence: Optional[str] = Field(None, description="Contextual snippet from the resume demonstrating this skill")


class ExperienceItem(BaseModel):
    title: str = Field(..., description="Job title / role")
    company: Optional[str] = Field(None, description="Company or organization name")
    location: Optional[str] = Field(None, description="Location (City, Country or Remote)")
    start_date: Optional[str] = Field(None, description="Start date (e.g. 2021-06)")
    end_date: Optional[str] = Field(None, description="End date or 'Present'")
    duration_months: Optional[int] = Field(None, description="Duration in months")
    bullets: List[str] = Field(default_factory=list, description="Key accomplishment and responsibility bullet points")
    technologies: List[str] = Field(default_factory=list, description="Tools and technologies mentioned in this role")


class EducationItem(BaseModel):
    degree: str = Field(..., description="Degree or program, e.g. BS Computer Science")
    institution: Optional[str] = Field(None, description="School, College, or University")
    graduation_year: Optional[int] = Field(None, description="Year of graduation")
    honors: Optional[str] = Field(None, description="GPA, honors, or thesis title")


class CertificationItem(BaseModel):
    name: str = Field(..., description="Certification name, e.g. AWS Certified Solutions Architect")
    issuer: Optional[str] = Field(None, description="Issuing organization")
    year: Optional[int] = Field(None, description="Year obtained")
    credential_id: Optional[str] = Field(None, description="Credential ID or URL if available")


class ProjectItem(BaseModel):
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Brief summary of project scope")
    bullets: List[str] = Field(default_factory=list, description="Key features, contributions, impact")
    technologies: List[str] = Field(default_factory=list, description="Technologies utilized")
    link: Optional[str] = Field(None, description="Repository or live URL")


class ResumeProfile(BaseModel):
    """
    Structured extraction of candidate qualifications.
    """
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    total_experience_years: float = 0.0
    skills: List[SkillItem] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[CertificationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = Field(None, description="Preserved clean text for RAG indexing")
    pii_masked: bool = False
    pii_mapping: Dict[str, str] = Field(default_factory=dict)


class JobProfile(BaseModel):
    """
    Structured representation of job description requirements.
    """
    title: str = Field(..., description="Target job title")
    company: Optional[str] = None
    location: Optional[str] = None
    is_remote: bool = False
    seniority_level: Optional[str] = Field("Mid", description="Entry, Junior, Mid, Senior, Lead, Director")
    min_experience_years: float = 0.0
    required_skills: List[SkillItem] = Field(default_factory=list)
    preferred_skills: List[SkillItem] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    education_requirements: List[str] = Field(default_factory=list)
    certifications_required: List[str] = Field(default_factory=list)
    salary_range: Optional[str] = None
    raw_text: Optional[str] = None
