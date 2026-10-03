"""
Candidate Resume Parser.
Combines deterministic section parsing, contact extraction, and skill extraction
with optional LLM refinement.
"""

import re
from typing import Dict, List, Optional, Tuple
from backend.app.core.redaction import mask_candidate_pii
from backend.app.ingestion.normalizer import normalize_text
from backend.app.ingestion.skills_taxonomy import extract_skills_from_text
from backend.app.schemas.profile import (
    CertificationItem,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeProfile,
    SkillItem,
)

# Common section headers in resumes
SECTION_PATTERNS = {
    "summary": re.compile(r"(?i)^(?:professional\s+summary|summary|profile|about\s+me)\b", re.MULTILINE),
    "experience": re.compile(r"(?i)^(?:work\s+experience|professional\s+experience|experience|employment\s+history)\b", re.MULTILINE),
    "education": re.compile(r"(?i)^(?:education|academic\s+background|qualifications)\b", re.MULTILINE),
    "skills": re.compile(r"(?i)^(?:skills|technical\s+skills|core\s+competencies|technologies)\b", re.MULTILINE),
    "projects": re.compile(r"(?i)^(?:projects|key\s+projects|personal\s+projects)\b", re.MULTILINE),
    "certifications": re.compile(r"(?i)^(?:certifications|certificates|licenses)\b", re.MULTILINE),
}

LINKEDIN_REGEX = re.compile(r"(?i)linkedin\.com/in/([a-zA-Z0-9_\-]+)")
GITHUB_REGEX = re.compile(r"(?i)github\.com/([a-zA-Z0-9_\-]+)")
YEAR_RANGE_REGEX = re.compile(r"\b(19\d{2}|20\d{2})\s*[-–—to]+\s*(19\d{2}|20\d{2}|present|current)\b", re.IGNORECASE)


def extract_contact_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extracts name, email, phone, and links from header text.
    """
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", text)
    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", text)
    linkedin_match = LINKEDIN_REGEX.search(text)
    github_match = GITHUB_REGEX.search(text)

    # First non-empty line is usually the candidate's name
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    candidate_name = lines[0] if lines and len(lines[0]) < 50 else None

    return {
        "full_name": candidate_name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "linkedin_url": f"https://linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else None,
        "github_url": f"https://github.com/{github_match.group(1)}" if github_match else None,
    }


def estimate_experience_years(text: str) -> float:
    """
    Scans for employment year ranges (e.g. 2018 - 2023) and computes total years.
    """
    current_year = 2026
    ranges = []

    for match in YEAR_RANGE_REGEX.finditer(text):
        start = int(match.group(1))
        end_str = match.group(2).lower()
        end = current_year if ("present" in end_str or "current" in end_str) else int(end_str)
        if 1980 <= start <= current_year and start <= end <= current_year:
            ranges.append((start, end))

    if not ranges:
        return 0.0

    # Merge overlapping year intervals
    ranges.sort(key=lambda x: x[0])
    merged = [ranges[0]]
    for current in ranges[1:]:
        prev_start, prev_end = merged[-1]
        if current[0] <= prev_end:
            merged[-1] = (prev_start, max(prev_end, current[1]))
        else:
            merged.append(current)

    total_years = sum(end - start for start, end in merged)
    return float(max(0.5, total_years))


def segment_sections(text: str) -> Dict[str, str]:
    """
    Splits resume text by common section headers.
    """
    matches = []
    for section_name, pattern in SECTION_PATTERNS.items():
        for m in pattern.finditer(text):
            matches.append((m.start(), section_name, m.group(0)))

    matches.sort(key=lambda x: x[0])
    sections: Dict[str, str] = {}

    if not matches:
        return {"content": text}

    for i in range(len(matches)):
        start_idx = matches[i][0]
        sec_name = matches[i][1]
        end_idx = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        chunk = text[start_idx:end_idx].strip()
        sections[sec_name] = chunk

    return sections


def parse_resume(raw_text: str, mask_pii: bool = True) -> ResumeProfile:
    """
    Deterministic extraction pipeline converting raw text into ResumeProfile.
    """
    clean_text = normalize_text(raw_text)

    # 1. Contact info extraction
    contacts = extract_contact_info(clean_text)

    # 2. PII masking if enabled
    masked_text = clean_text
    pii_map = {}
    if mask_pii:
        masked_text, pii_map = mask_candidate_pii(clean_text)
        if contacts["email"]:
            contacts["email"] = "[CANDIDATE_EMAIL]"
        if contacts["phone"]:
            contacts["phone"] = "[CANDIDATE_PHONE]"

    # 3. Extract skills from entire resume and skills section
    skills = extract_skills_from_text(clean_text)

    # 4. Estimate years of experience
    exp_years = estimate_experience_years(clean_text)

    # 5. Segment sections
    sections = segment_sections(clean_text)

    # 6. Basic experience and education extraction
    experience_list: List[ExperienceItem] = []
    if "experience" in sections:
        exp_text = sections["experience"]
        # Split into bullet blocks or company headings
        lines = [l.strip() for l in exp_text.split("\n") if l.strip()]
        if len(lines) > 1:
            experience_list.append(
                ExperienceItem(
                    title=lines[1] if len(lines) > 1 else "Experience History",
                    bullets=[l for l in lines[2:10] if l.startswith("- ") or len(l) > 20],
                )
            )

    education_list: List[EducationItem] = []
    if "education" in sections:
        edu_lines = [l.strip() for l in sections["education"].split("\n") if l.strip()]
        if len(edu_lines) > 1:
            education_list.append(EducationItem(degree=edu_lines[1]))

    return ResumeProfile(
        full_name=contacts["full_name"],
        email=contacts["email"],
        phone=contacts["phone"],
        linkedin_url=contacts["linkedin_url"],
        github_url=contacts["github_url"],
        total_experience_years=exp_years,
        skills=skills,
        experience=experience_list,
        education=education_list,
        raw_text=clean_text,
        pii_masked=mask_pii,
        pii_mapping=pii_map,
    )


class ResumeParser:
    """Convenience class wrapper for parsing resumes."""

    @staticmethod
    def parse(raw_text: str, mask_pii: bool = False) -> ResumeProfile:
        return parse_resume(raw_text, mask_pii=mask_pii)

