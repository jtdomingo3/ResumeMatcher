"""
Unit Tests for Career Analyzer and AI Writer Engines.
Tests both deterministic fallbacks and mocked LLM generation pathways.
"""

from unittest.mock import patch, AsyncMock
import pytest
from backend.app.schemas.profile import ResumeProfile, JobProfile, SkillItem
from backend.app.schemas.career import BulletRewriteRequest
from backend.app.engines.career import CareerAnalyzerEngine, generate_fallback_career_report
from backend.app.engines.writer import WriterEngine
from backend.app.core.secrets import SecretManager


@pytest.fixture
def sample_resume():
    return ResumeProfile(
        full_name="Alex Rivera",
        total_experience_years=4.5,
        skills=[
            SkillItem(name="Python"),
            SkillItem(name="FastAPI"),
            SkillItem(name="Docker"),
            SkillItem(name="PostgreSQL"),
            SkillItem(name="Kubernetes"),
            SkillItem(name="Git"),
        ],
        raw_text="Alex Rivera, Backend Engineer with 4.5 years experience in Python, FastAPI, Docker.",
    )


@pytest.fixture
def sample_job():
    return JobProfile(
        title="Senior Python Platform Engineer",
        min_experience_years=5.0,
        required_skills=[
            SkillItem(name="Python"),
            SkillItem(name="FastAPI"),
            SkillItem(name="Docker"),
            SkillItem(name="Kubernetes"),
        ],
        preferred_skills=[SkillItem(name="Terraform")],
        raw_text="Senior Python Platform Engineer needed to build cloud microservices.",
    )


def test_fallback_career_report(sample_resume):
    report = generate_fallback_career_report(sample_resume)
    assert report.candidate_name == "Alex Rivera"
    assert len(report.career_paths) == 3
    path_types = {p.path_type for p in report.career_paths}
    assert {"Vertical", "Lateral", "Pivot"}.issubset(path_types)

    assert len(report.roadmap_90_days) == 3
    phases = [m.phase for m in report.roadmap_90_days]
    assert phases == ["Day 1-30", "Day 31-60", "Day 61-90"]

    assert report.market_insights is not None
    assert "Software Engineering" in report.market_insights.role_title
    assert len(report.market_insights.in_demand_skills) > 0


@pytest.mark.asyncio
async def test_career_analyzer_engine_analyze_fallback(sample_resume):
    with patch.object(SecretManager, "get_openrouter_key", return_value=None):
        report = await CareerAnalyzerEngine.analyze(sample_resume, target_career="Senior Cloud Engineer")
        assert report is not None
        assert len(report.career_paths) >= 3
        assert len(report.roadmap_90_days) >= 3
        assert report.market_insights is not None


@pytest.mark.asyncio
async def test_career_analyzer_engine_analyze_llm(sample_resume):
    mock_llm_json = """
    {
      "current_level": "Senior Backend Engineer",
      "career_paths": [
        {
          "title": "Principal Architect",
          "path_type": "Vertical",
          "fit_score": 92,
          "rationale": "High depth in distributed systems.",
          "required_skills": ["Distributed Systems", "Go"],
          "transferable_skills": ["Python", "FastAPI"],
          "timeline_months": "12-18 months"
        },
        {
          "title": "MLOps Engineer",
          "path_type": "Lateral",
          "fit_score": 85,
          "rationale": "Strong Docker and backend foundation.",
          "required_skills": ["Kubeflow", "MLflow"],
          "transferable_skills": ["Docker", "Kubernetes"],
          "timeline_months": "6-9 months"
        },
        {
          "title": "Engineering Manager",
          "path_type": "Pivot",
          "fit_score": 78,
          "rationale": "Leadership and product alignment.",
          "required_skills": ["People Management", "Agile"],
          "transferable_skills": ["Communication"],
          "timeline_months": "12 months"
        }
      ],
      "roadmap_90_days": [
        {"phase": "Day 1-30", "focus_area": "Foundations", "goals": ["Audit codebases"], "recommended_resources": ["Book A"]},
        {"phase": "Day 31-60", "focus_area": "Scaling", "goals": ["Build prototype"], "recommended_resources": ["Course B"]},
        {"phase": "Day 61-90", "focus_area": "Capstone", "goals": ["Deploy live"], "recommended_resources": ["Doc C"]}
      ],
      "market_insights": {
        "role_title": "Cloud Architect",
        "demand_trend": "Exponential",
        "estimated_salary_range": "$150k - $200k",
        "in_demand_skills": ["Kubernetes", "FastAPI"],
        "market_summary": "Extremely high demand in enterprise clouds.",
        "citations": ["Tech Trends 2026"]
      }
    }
    """
    with patch("backend.app.engines.career.openrouter_client.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = {"content": mock_llm_json, "model": "meta-llama/llama-3.3-70b-instruct:free"}
        with patch.object(SecretManager, "get_openrouter_key", return_value="mock-key"):
            report = await CareerAnalyzerEngine.analyze(sample_resume, target_career="Cloud Architect")
            assert report.current_level == "Senior Backend Engineer"
            assert report.career_paths[0].title == "Principal Architect"
            assert report.market_insights.demand_trend == "Exponential"


@pytest.mark.asyncio
async def test_writer_engine_bullet_rewrite():
    req = BulletRewriteRequest(
        bullet_text="worked on backend apis and fixed database queries",
        target_role="Senior Backend Engineer",
        target_skill="Python / PostgreSQL",
    )
    with patch.object(SecretManager, "get_openrouter_key", return_value=None):
        result = await WriterEngine.rewrite_bullet(req)
        assert result.original == req.bullet_text
        assert result.rewritten_star != ""
        assert result.action_verb_used != ""
        assert result.metrics_quantified != ""
        assert len(result.rewritten_star) > len(result.original)


@pytest.mark.asyncio
async def test_writer_engine_cover_letter(sample_resume):
    jd_text = "Looking for a Senior Python Engineer to architect high-throughput FastAPI services."
    with patch.object(SecretManager, "get_openrouter_key", return_value=None):
        result = await WriterEngine.generate_cover_letter(
            resume=sample_resume,
            job_description=jd_text,
            company_name="TechCorp Labs",
        )
        assert result.cover_letter_markdown != ""
        assert "TechCorp Labs" in result.cover_letter_markdown
        assert "Alex Rivera" in result.cover_letter_markdown


@pytest.mark.asyncio
async def test_writer_engine_interview_prep(sample_resume, sample_job):
    with patch.object(SecretManager, "get_openrouter_key", return_value=None):
        questions = await WriterEngine.generate_interview_prep(resume=sample_resume, job=sample_job)
        assert len(questions) >= 1
        q = questions[0]
        assert q.question != ""
        assert q.what_interviewer_looks_for != ""
        assert q.star_answer_outline != ""
