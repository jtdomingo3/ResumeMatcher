"""
AI Resume Writer, Bullet Rewriter (STAR Framework), and Cover Letter Generator.
Uses RAG retrieval from STAR method guidelines and action verb taxonomy.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.app.core.secrets import SecretManager
from backend.app.llm.openrouter_client import openrouter_client
from backend.app.llm.structured import extract_json_object
from backend.app.rag.engine import rag_engine
from backend.app.rag.context import format_rag_context
from backend.app.schemas.career import (
    BulletRewriteRequest,
    BulletRewriteResult,
    CoverLetterRequest,
    CoverLetterResult,
    InterviewPrepQuestion,
)
from backend.app.schemas.profile import JobProfile, ResumeProfile

logger = logging.getLogger(__name__)


class WriterEngine:
    """
    Generates high-converting bullet rewrites and tailored application materials.
    """

    @classmethod
    async def rewrite_bullet(cls, req: BulletRewriteRequest) -> BulletRewriteResult:
        secret = SecretManager.get_openrouter_key()

        # Fallback if no LLM
        if not secret:
            action_verbs = ["Architected", "Engineered", "Optimized", "Spearheaded", "Automated"]
            original = req.bullet_text.strip()
            return BulletRewriteResult(
                original=original,
                rewritten_star=f"Engineered and deployed scalable solutions for {original.lower().lstrip('- ')}, improving system throughput by 35% and reducing processing turnaround.",
                metrics_quantified="35% throughput increase",
                action_verb_used="Engineered",
                improvement_rationale="Applied STAR-XYZ structure with concrete action verb and quantified performance outcome.",
            )

        # Retrieve STAR guidelines via RAG
        rag_chunks = rag_engine.query("STAR method bullet rewriting formula action verbs quantified impact", top_k=2)
        rag_context = format_rag_context(rag_chunks)

        prompt = f"""
You are an expert resume editor and executive career coach.
Rewrite the following resume bullet point using the Google STAR-XYZ framework:
[Strong Action Verb] + [Action & Technical Solution] + [Context/Problem] + [Quantified Result/Impact].

ORIGINAL BULLET:
"{req.bullet_text}"
TARGET ROLE: {req.target_role or 'Senior Software Engineer'}
TARGET SKILL/TECHNOLOGY: {req.target_skill or 'Python / Backend Architecture'}

{rag_context}

Return strictly a JSON object with these keys:
{{
  "rewritten_star": "...",
  "metrics_quantified": "...",
  "action_verb_used": "...",
  "improvement_rationale": "..."
}}
"""
        try:
            res = await openrouter_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task="chat",
                max_tokens=500,
                temperature=0.3,
            )
            parsed = extract_json_object(res.get("content", ""))
            if parsed and "rewritten_star" in parsed:
                return BulletRewriteResult(
                    original=req.bullet_text,
                    rewritten_star=parsed["rewritten_star"],
                    metrics_quantified=parsed.get("metrics_quantified", "Quantified metric added"),
                    action_verb_used=parsed.get("action_verb_used", "Engineered"),
                    improvement_rationale=parsed.get("improvement_rationale", "Restructured using STAR framework."),
                )
        except Exception as e:
            logger.warning(f"Bullet rewrite LLM call failed: {e}")

        return BulletRewriteResult(
            original=req.bullet_text,
            rewritten_star=f"Spearheaded optimization of {req.bullet_text.lower().lstrip('- ')}, resulting in a 40% reduction in processing latency.",
            metrics_quantified="40% latency reduction",
            action_verb_used="Spearheaded",
            improvement_rationale="Fallback STAR rewrite applied.",
        )

    @classmethod
    async def generate_cover_letter(
        cls,
        resume: ResumeProfile,
        job_description: str,
        company_name: Optional[str] = None,
    ) -> CoverLetterResult:
        secret = SecretManager.get_openrouter_key()
        cand_name = resume.full_name or "Applicant"
        company = company_name or "the Hiring Team"

        if not secret:
            sample_md = f"""# Application for Employment

**Dear Hiring Manager at {company},**

I am writing to express my enthusiastic interest in this opportunity. With over {resume.total_experience_years:.0f} years of engineering experience and a proven background in {', '.join(s.name for s in resume.skills[:4])}, I am confident in my ability to make an immediate, positive impact on your team.

Throughout my career, I have consistently focused on building scalable, reliable backend solutions and collaborating across teams to ship high-impact features. The requirements outlined in your job posting strongly align with my hands-on background and technical strengths.

Thank you for your time and consideration. I welcome the opportunity to discuss how my qualifications align with your goals.

Sincerely,  
**{cand_name}**
"""
            return CoverLetterResult(
                cover_letter_markdown=sample_md,
                key_highlights_included=[s.name for s in resume.skills[:4]],
            )

        prompt = f"""
You are an executive career advisor. Draft a compelling, personalized, publication-ready cover letter.
CANDIDATE:
Name: {cand_name}
Experience: {resume.total_experience_years} years
Skills: {', '.join(s.name for s in resume.skills[:10])}

TARGET COMPANY: {company}
JOB DESCRIPTION:
{job_description[:2000]}

Format the response in clean Markdown with professional tone.
Highlight 2-3 specific accomplishments that prove the candidate can solve the employer's needs.
"""
        try:
            res = await openrouter_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task="career_report",
                max_tokens=1200,
                temperature=0.4,
            )
            content = res.get("content", "").strip()
            return CoverLetterResult(
                cover_letter_markdown=content,
                key_highlights_included=[s.name for s in resume.skills[:3]],
            )
        except Exception as e:
            logger.warning(f"Cover letter generation failed: {e}")
            return CoverLetterResult(
                cover_letter_markdown=f"Dear {company},\n\nI am applying for this role based on my {resume.total_experience_years} years of software development experience.\n\nSincerely,\n{cand_name}",
                key_highlights_included=[],
            )

    @classmethod
    async def generate_interview_prep(
        cls,
        resume: ResumeProfile,
        job: JobProfile,
    ) -> List[InterviewPrepQuestion]:
        secret = SecretManager.get_openrouter_key()
        if not secret:
            return [
                InterviewPrepQuestion(
                    category="Technical Architecture",
                    question=f"How have you designed and scaled backend services using {job.required_skills[0].name if job.required_skills else 'Python'}?",
                    what_interviewer_looks_for="Understanding of latency, modular design, database indexing, and caching.",
                    star_answer_outline="S: High volume traffic on legacy endpoint. T: Refactor to asynchronous API. A: Used connection pooling and Redis caching. R: Scaled to 10k RPS with zero downtime.",
                ),
                InterviewPrepQuestion(
                    category="Behavioral Leadership",
                    question="Describe a situation where you had to bridge a technical gap on a tight project deadline.",
                    what_interviewer_looks_for="Ownership, fast learning ability, and pragmatic engineering trade-offs.",
                    star_answer_outline="S: Critical new technology requirement with 2-week deadline. T: Build production prototype. A: Created sandbox, ran spikes, wrote tests. R: Successfully delivered ahead of schedule.",
                ),
            ]

        # Use LLM for role-tailored interview prep
        req_skills_str = ", ".join(s.name for s in job.required_skills[:6])
        prompt = f"""
You are a senior technical interviewer. Generate 3 targeted interview questions for:
Candidate: {resume.total_experience_years} years exp, Skills: {', '.join(s.name for s in resume.skills[:8])}
Target Role: {job.title}
Key Required Skills: {req_skills_str}

Return strictly a JSON array with items containing:
- "category" (Technical / Behavioral / System Design)
- "question"
- "what_interviewer_looks_for"
- "star_answer_outline"
"""
        try:
            res = await openrouter_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task="scoring",
                max_tokens=1000,
                temperature=0.3,
            )
            raw = res.get("content", "")
            parsed = extract_json_object(raw)
            # If array returned directly or inside key
            items = parsed if isinstance(parsed, list) else (parsed.get("questions", []) if isinstance(parsed, dict) else [])
            if items:
                return [InterviewPrepQuestion(**item) for item in items[:4]]
        except Exception as e:
            logger.warning(f"Interview prep LLM generation failed: {e}")

        return [
            InterviewPrepQuestion(
                category="System Design",
                question=f"Walk me through how you would architect a production system using {req_skills_str}.",
                what_interviewer_looks_for="Scalability, fault tolerance, API contracts, and monitoring.",
                star_answer_outline="Outline components: API Gateway, Microservice instances, Database replication, and telemetry.",
            )
        ]
