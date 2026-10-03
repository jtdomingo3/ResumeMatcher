"""
Unit Tests for Ingestion Pipeline: Parsers, Normalizer, Skills Taxonomy, and SSRF Guard.
"""

import pytest
from backend.app.ingestion.normalizer import normalize_text
from backend.app.ingestion.skills_taxonomy import extract_skills_from_text, get_canonical_skill
from backend.app.ingestion.resume_parser import parse_resume, estimate_experience_years
from backend.app.ingestion.jd_parser import parse_job_description, validate_safe_url


def test_normalize_text_bullets_and_hyphens():
    raw = "• Strong back-\nend developer with C++\n\n\n\n► Python specialist"
    cleaned = normalize_text(raw)

    assert "- Strong backend developer" in cleaned
    assert "- Python specialist" in cleaned
    assert "\n\n\n" not in cleaned


def test_skills_taxonomy_alias_resolution():
    assert get_canonical_skill("py")[0] == "Python"
    assert get_canonical_skill("k8s")[0] == "Kubernetes"
    assert get_canonical_skill("aws")[0] == "Amazon Web Services (AWS)"
    assert get_canonical_skill("postgres")[0] == "PostgreSQL"
    assert get_canonical_skill("c++")[0] == "C++"

    sample = "Proficient in Python, TS, Docker, K8s, and PostgreSQL database optimization."
    extracted = extract_skills_from_text(sample)
    extracted_names = {s.name for s in extracted}

    assert "Python" in extracted_names
    assert "TypeScript" in extracted_names
    assert "Docker" in extracted_names
    assert "Kubernetes" in extracted_names
    assert "PostgreSQL" in extracted_names


def test_resume_parser_contacts_and_experience():
    resume_doc = """
    Jane Smith
    jane.smith@example.org | (555) 123-4567 | San Francisco, CA
    linkedin.com/in/janesmith-dev | github.com/janesmith

    PROFESSIONAL SUMMARY
    Senior Software Engineer with 6 years experience in Python, FastAPI, and Cloud Architecture.

    WORK EXPERIENCE
    Senior Backend Engineer - Acme Corp
    2020 - Present
    - Designed scalable microservices using FastAPI and Docker.
    - Mentored 4 junior engineers on clean code practices.

    Software Engineer - Beta Systems
    2018 - 2020
    - Built REST APIs and optimized PostgreSQL database queries.

    EDUCATION
    BS Computer Science - State University (2018)

    SKILLS
    Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL, Git
    """

    profile = parse_resume(resume_doc, mask_pii=False)

    assert profile.full_name == "Jane Smith"
    assert profile.email == "jane.smith@example.org"
    assert profile.total_experience_years >= 6.0
    assert "https://linkedin.com/in/janesmith-dev" in profile.linkedin_url

    skill_names = {s.name for s in profile.skills}
    assert "Python" in skill_names
    assert "FastAPI" in skill_names
    assert "Docker" in skill_names
    assert "Kubernetes" in skill_names


def test_jd_parser_requirements_and_seniority():
    jd_text = """
    Senior Python Backend Engineer
    Acme Analytics - San Francisco, CA

    About the Role:
    We are seeking a Senior Python Engineer with 5+ years of experience to lead our data infrastructure.

    Requirements:
    - 5+ years building production backend systems with Python and FastAPI
    - Strong expertise in Docker, PostgreSQL, and AWS
    - Experience designing high-throughput REST APIs

    Preferred Qualifications / Nice to have:
    - Experience with Kubernetes and RAG vector databases like ChromaDB
    - Knowledge of Machine Learning pipelines
    """

    job = parse_job_description(jd_text)

    assert "Senior" in job.title or "Python" in job.title
    assert job.seniority_level == "Senior"
    assert job.min_experience_years == 5.0

    req_names = {s.name for s in job.required_skills}
    pref_names = {s.name for s in job.preferred_skills}

    assert "Python" in req_names
    assert "FastAPI" in req_names
    assert "PostgreSQL" in req_names

    assert "Kubernetes" in pref_names or "ChromaDB" in pref_names or "Machine Learning" in pref_names


def test_ssrf_validator_blocks_internal_ips():
    # Loopback & local
    with pytest.raises(ValueError, match="forbidden|restricted|private"):
        validate_safe_url("http://127.0.0.1:8000/internal-admin")

    with pytest.raises(ValueError, match="forbidden|restricted|private"):
        validate_safe_url("http://localhost:3000/keys")

    # AWS metadata IP
    with pytest.raises(ValueError, match="forbidden|restricted|private"):
        validate_safe_url("http://169.254.169.254/latest/meta-data/")

    # Invalid scheme
    with pytest.raises(ValueError, match="scheme"):
        validate_safe_url("file:///etc/passwd")
