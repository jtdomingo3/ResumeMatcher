"""
Integration tests for FastAPI endpoints: Health, Resumes, Jobs, Matching, Models, and Settings.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.secrets import SecretManager

client = TestClient(app)


def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "AI-Powered Resume Matcher" in data["app"]
    assert data["version"] == "1.0.0"


def test_health_endpoint():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["database_connected"] is True
    assert "rag_indexed_chunks" in data


def test_settings_masked():
    res = client.get("/api/v1/settings")
    assert res.status_code == 200
    data = res.json()
    assert "has_openrouter_key" in data
    assert "scoring_weights" in data
    if data.get("has_openrouter_key"):
        masked = data.get("masked_key", "")
        assert "..." in masked or "****" in masked


def test_resume_upload_and_lifecycle():
    sample_text = """
    Alex Rivera
    alex.rivera@example.com | (555) 019-2834
    
    Summary:
    Senior Python engineer with 5 years experience building FastAPI and Docker microservices.
    
    Work Experience:
    Senior Backend Developer at CloudCorp
    2021 - Present
    - Engineered high-throughput FastAPI APIs serving 10,000 requests per second.
    - Automated CI/CD deployment pipelines using Docker and GitHub Actions.
    
    Technical Skills:
    Python, FastAPI, Docker, PostgreSQL, Redis, Kubernetes
    
    Education:
    BS in Computer Science, 2020
    """
    files = {"file": ("alex_resume.txt", sample_text.encode("utf-8"), "text/plain")}
    res = client.post("/api/v1/resumes/upload", files=files, data={"mask_pii_enabled": "true"})
    assert res.status_code == 201
    resume_data = res.json()
    resume_id = resume_data["id"]
    assert resume_id is not None
    assert resume_data["profile"]["pii_masked"] is True

    # 1. Fetch by id
    get_res = client.get(f"/api/v1/resumes/{resume_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == resume_id

    # 2. List
    list_res = client.get("/api/v1/resumes")
    assert list_res.status_code == 200
    assert any(r["id"] == resume_id for r in list_res.json())

    # 3. Create job
    jd_payload = {
        "title": "Senior Python Backend Engineer",
        "raw_text": "We need a Senior Python Engineer with 4+ years experience in FastAPI, Docker, and PostgreSQL.",
    }
    job_res = client.post("/api/v1/jobs", json=jd_payload)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 4. Match (deterministic without LLM)
    match_payload = {
        "resume_id": resume_id,
        "job_id": job_id,
        "use_llm": False,
    }
    match_res = client.post("/api/v1/match", json=match_payload)
    assert match_res.status_code == 200
    m_data = match_res.json()
    assert m_data["overall_score"] > 60
    assert any(t in m_data["match_tier"] for t in ["Strong Match", "High Match", "Moderate Match"])
    assert "breakdown" in m_data
    assert "ats_report" in m_data

    # 5. Career Fallback Analyze (mocking key so it uses deterministic fast path)
    with patch.object(SecretManager, "get_openrouter_key", return_value=None):
        career_res = client.post("/api/v1/career/analyze", json={"resume_id": resume_id})
        assert career_res.status_code == 200
        c_data = career_res.json()
        assert len(c_data["career_paths"]) >= 3
        assert len(c_data["roadmap_90_days"]) >= 3

    # 6. Cleanup
    del_res = client.delete(f"/api/v1/resumes/{resume_id}")
    assert del_res.status_code == 200
    del_job = client.delete(f"/api/v1/jobs/{job_id}")
    assert del_job.status_code == 200


def test_models_endpoint():
    res = client.get("/api/v1/models/free")
    assert res.status_code == 200
    data = res.json()
    assert "count" in data
    assert "models" in data
