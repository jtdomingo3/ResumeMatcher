"""
Unit Tests for Hybrid Matching Engine and ATS Compliance.
"""

import pytest
from backend.app.schemas.profile import ResumeProfile, JobProfile, SkillItem, EducationItem
from backend.app.engines.matcher import MatcherEngine
from backend.app.engines.ats import evaluate_ats_compliance


@pytest.mark.asyncio
async def test_high_match_candidate():
    resume = ResumeProfile(
        full_name="Alex Rivera",
        total_experience_years=6.0,
        skills=[
            SkillItem(name="Python"),
            SkillItem(name="FastAPI"),
            SkillItem(name="Docker"),
            SkillItem(name="PostgreSQL"),
            SkillItem(name="Kubernetes"),
        ],
        education=[EducationItem(degree="BS Computer Science")],
        raw_text="""
        Alex Rivera
        Professional Experience:
        - Built Python microservices with FastAPI and Docker.
        - Optimized PostgreSQL queries.
        Education:
        - BS Computer Science
        Technical Skills:
        - Python, FastAPI, Docker, PostgreSQL, Kubernetes
        """,
    )

    job = JobProfile(
        title="Senior Python Backend Engineer",
        min_experience_years=5.0,
        required_skills=[
            SkillItem(name="Python"),
            SkillItem(name="FastAPI"),
            SkillItem(name="Docker"),
        ],
        preferred_skills=[SkillItem(name="Kubernetes")],
        raw_text="Senior Python Backend Engineer needing 5+ years experience in Python, FastAPI, Docker, and Kubernetes.",
    )

    result = await MatcherEngine.match(resume, job, use_llm=False)

    assert result.overall_score >= 80
    assert "High Match" in result.match_tier or "Strong Match" in result.match_tier
    assert len(result.skills_analysis.missing_required) == 0
    assert "Python" in result.skills_analysis.matched_required
    assert "Kubernetes" in result.skills_analysis.matched_preferred


@pytest.mark.asyncio
async def test_low_match_candidate_gap_analysis():
    resume = ResumeProfile(
        full_name="Junior Front-End Dev",
        total_experience_years=1.0,
        skills=[SkillItem(name="HTML5"), SkillItem(name="CSS3"), SkillItem(name="JavaScript")],
        raw_text="Junior Front-End Dev with HTML5 and CSS3 skills.",
    )

    job = JobProfile(
        title="Senior Machine Learning & RAG Architect",
        min_experience_years=7.0,
        required_skills=[
            SkillItem(name="Python"),
            SkillItem(name="PyTorch"),
            SkillItem(name="Retrieval-Augmented Generation (RAG)"),
            SkillItem(name="Vector Databases"),
        ],
        raw_text="Architect to lead Deep Learning and RAG systems.",
    )

    result = await MatcherEngine.match(resume, job, use_llm=False)

    assert result.overall_score < 60
    assert len(result.gap_analysis.critical_skill_gaps) >= 3
    assert "Python" in result.gap_analysis.critical_skill_gaps
    assert result.gap_analysis.experience_gap_notes is not None


def test_ats_compliance_audit():
    # Good resume with standard headers
    good_text = """
    Jane Doe
    jane@example.com | 555-1234
    
    Professional Summary
    Experienced engineer with clean code practices.
    
    Work Experience
    - Engineered scalable microservices.
    - Automated testing pipelines.
    - Led architecture team.
    - Optimized system latency.
    
    Technical Skills
    - Python, Go, Docker, AWS
    
    Education
    - BS Software Engineering
    """
    profile = ResumeProfile(email="jane@example.com", phone="555-1234", raw_text=good_text)
    report = evaluate_ats_compliance(profile, good_text)

    assert report.verdict == "PASS"
    assert report.score >= 80
    assert report.has_contact_info is True
    assert len(report.missing_headings) == 0
