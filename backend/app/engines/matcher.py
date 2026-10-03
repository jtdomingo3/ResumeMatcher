"""
Hybrid Explainable Resume-to-Job Matching Engine.
Calculates a 0-100 composite match score decomposed into:
- 40% Skills Coverage (Required skills 2x weighted + Preferred skills 1x)
- 20% Semantic Vector Proximity (Embedding Cosine Similarity)
- 15% Experience & Seniority Alignment
- 10% Education & Degree Fit
- 15% LLM Holistic Qualitative Evaluation (with deterministic heuristic fallback)
"""

import math
import uuid
import logging
from typing import Any, Dict, List, Optional
import numpy as np

from backend.app.core.config import settings
from backend.app.engines.ats import evaluate_ats_compliance
from backend.app.llm.openrouter_client import openrouter_client
from backend.app.llm.structured import extract_json_object
from backend.app.rag.engine import rag_engine
from backend.app.schemas.match import (
    GapAnalysis,
    MatchBreakdown,
    MatchResult,
    SkillMatchDetails,
)
from backend.app.schemas.profile import JobProfile, ResumeProfile

logger = logging.getLogger(__name__)


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class MatcherEngine:
    """
    Evaluates resume fit against target job description.
    """

    @classmethod
    async def match(
        cls,
        resume: ResumeProfile,
        job: JobProfile,
        use_llm: bool = True,
    ) -> MatchResult:
        result_id = str(uuid.uuid4())[:8]

        # 1. Skills Breakdown Analysis
        resume_skill_map = {s.name.lower(): s for s in resume.skills}
        matched_req: List[str] = []
        missing_req: List[str] = []
        matched_pref: List[str] = []
        missing_pref: List[str] = []
        evidence_map: Dict[str, str] = {}

        # Evaluate required skills
        for req in job.required_skills:
            req_key = req.name.lower()
            if req_key in resume_skill_map:
                matched_req.append(req.name)
                ev = resume_skill_map[req_key].evidence or f"Mentioned in resume profile: {req.name}"
                evidence_map[req.name] = ev
            else:
                missing_req.append(req.name)

        # Evaluate preferred skills
        for pref in job.preferred_skills:
            pref_key = pref.name.lower()
            if pref_key in resume_skill_map:
                matched_pref.append(pref.name)
                ev = resume_skill_map[pref_key].evidence or f"Mentioned in resume profile: {pref.name}"
                evidence_map[pref.name] = ev
            else:
                missing_pref.append(pref.name)

        # Calculate skills coverage score (Required 2x weight, Preferred 1x)
        total_possible = (len(job.required_skills) * 2) + len(job.preferred_skills)
        if total_possible > 0:
            earned = (len(matched_req) * 2) + len(matched_pref)
            skills_score = round((earned / total_possible) * 100.0, 1)
        else:
            # If JD specified no specific skills, base on general resume richness
            skills_score = 75.0 if resume.skills else 40.0

        # 2. Semantic Embedding Similarity
        resume_content = resume.raw_text or "Candidate profile with general technical experience."
        job_content = job.raw_text or "Job description with general technical requirements."

        try:
            embeddings = rag_engine.embedding_fn([resume_content[:2000], job_content[:2000]])
            sim = _cosine_similarity(embeddings[0], embeddings[1])
            semantic_score = round(sim * 100.0, 1)
        except Exception as e:
            logger.warning(f"Error computing embedding similarity: {e}. Using baseline.")
            semantic_score = 70.0

        # 3. Experience & Seniority Score
        cand_years = resume.total_experience_years
        req_years = job.min_experience_years

        if req_years <= 0:
            exp_score = 90.0 if cand_years >= 2.0 else 75.0
        elif cand_years >= req_years:
            # Full points + bonus for strong alignment
            exp_score = min(100.0, 85.0 + (cand_years - req_years) * 3.0)
        else:
            # Proportionate score if below minimum
            exp_score = round((cand_years / max(1.0, req_years)) * 80.0, 1)

        # 4. Education Fit
        edu_score = 80.0
        if resume.education:
            has_stem = any(
                any(stem_kw in (edu.degree or "").lower() for stem_kw in ["computer", "science", "engineering", "math", "information", "technology", "physics"])
                for edu in resume.education
            )
            edu_score = 95.0 if has_stem else 85.0
        else:
            edu_score = 65.0

        # 5. LLM Qualitative Evaluation or Deterministic Fallback
        llm_score = round((skills_score * 0.5) + (semantic_score * 0.3) + (exp_score * 0.2), 1)
        llm_notes = None
        model_used = None

        if use_llm:
            try:
                prompt = (
                    "You are an expert technical hiring manager. Evaluate this candidate for the target job.\n"
                    f"Candidate Experience: {cand_years} years. Skills: {', '.join(s.name for s in resume.skills[:15])}\n"
                    f"Job Title: {job.title}. Required Skills: {', '.join(s.name for s in job.required_skills[:10])}\n"
                    "Provide a holistic score from 0-100 based on role fit, and a brief 2-sentence feedback.\n"
                    "Return strictly JSON: {\"score\": 85, \"feedback\": \"...\"}"
                )
                res = await openrouter_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    task="scoring",
                    max_tokens=300,
                    temperature=0.2,
                )
                parsed = extract_json_object(res.get("content", ""))
                if parsed and "score" in parsed:
                    llm_score = float(parsed["score"])
                    llm_notes = parsed.get("feedback")
                    model_used = res.get("model")
            except Exception as le:
                logger.warning(f"LLM qualitative match evaluation skipped: {le}")

        # 6. Composite Weighted Overall Score
        overall = (
            (skills_score * settings.WEIGHT_SKILLS)
            + (semantic_score * settings.WEIGHT_SEMANTIC)
            + (exp_score * settings.WEIGHT_EXPERIENCE)
            + (edu_score * settings.WEIGHT_EDUCATION)
            + (llm_score * settings.WEIGHT_LLM)
        )
        final_overall = max(0, min(100, int(round(overall))))

        # Determine Match Tier
        if final_overall >= 80:
            tier = "High Match (80-100%)"
        elif final_overall >= 65:
            tier = "Strong Match (65-79%)"
        elif final_overall >= 50:
            tier = "Moderate Match (50-64%)"
        else:
            tier = "Low Match (<50%)"

        # 7. ATS Audit
        ats_rep = evaluate_ats_compliance(resume, resume_content)

        # 8. Gap Analysis & Actionable Fixes
        priority_fixes = []
        if missing_req:
            priority_fixes.append(f"Add evidence or projects for required competencies: {', '.join(missing_req[:3])}.")
        if cand_years < req_years:
            priority_fixes.append(f"Highlight freelance or open-source projects to bridge the {req_years - cand_years:.1f} year experience gap.")
        if ats_rep.format_issues:
            priority_fixes.append(ats_rep.format_issues[0])

        gap_analysis = GapAnalysis(
            critical_skill_gaps=missing_req,
            bonus_skill_gaps=missing_pref,
            experience_gap_notes=f"Candidate has ~{cand_years} years vs required ~{req_years} years." if req_years > 0 else None,
            priority_fixes=priority_fixes,
        )

        breakdown = MatchBreakdown(
            skills_score=skills_score,
            semantic_score=semantic_score,
            experience_score=exp_score,
            education_score=edu_score,
            llm_rubric_score=llm_score,
            overall_score=final_overall,
        )

        return MatchResult(
            id=result_id,
            resume_name=resume.full_name or "Candidate",
            job_title=job.title,
            overall_score=final_overall,
            match_tier=tier,
            summary=f"Candidate exhibits a {tier.lower()} for {job.title} with {len(matched_req)}/{len(job.required_skills)} required skills matched.",
            breakdown=breakdown,
            skills_analysis=SkillMatchDetails(
                matched_required=matched_req,
                missing_required=missing_req,
                matched_preferred=matched_pref,
                missing_preferred=missing_pref,
                evidence_by_skill=evidence_map,
            ),
            ats_report=ats_rep,
            gap_analysis=gap_analysis,
            llm_eval_notes=llm_notes,
            evaluated_with_model=model_used,
        )
