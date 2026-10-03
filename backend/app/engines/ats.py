"""
Applicant Tracking System (ATS) Compliance Checker.
Audits document structure, keyword density, section headers, and formatting pitfalls.
"""

import re
from typing import Dict, List
from backend.app.schemas.match import AtsReport
from backend.app.schemas.profile import ResumeProfile

STANDARD_SECTIONS = [
    ("Work Experience", re.compile(r"(?i)\b(?:experience|employment|work\s+history)\b")),
    ("Education", re.compile(r"(?i)\b(?:education|academic|qualifications)\b")),
    ("Technical Skills", re.compile(r"(?i)\b(?:skills|competencies|technologies)\b")),
    ("Professional Summary", re.compile(r"(?i)\b(?:summary|profile|about)\b")),
]


def evaluate_ats_compliance(profile: ResumeProfile, raw_text: str) -> AtsReport:
    """
    Evaluates ATS readability and compliance.
    """
    issues: List[str] = []
    found_headings: List[str] = []
    missing_headings: List[str] = []
    score = 100

    words = raw_text.split()
    word_count = len(words)

    # 1. Word count checks (ideal resume is 400 - 1000 words)
    if word_count < 250:
        issues.append(f"Resume is very short ({word_count} words). ATS engines may flag insufficient detail.")
        score -= 15
    elif word_count > 1500:
        issues.append(f"Resume is very long ({word_count} words). Consider condensing to 1-2 pages.")
        score -= 10

    # 2. Section headings audit
    for sec_name, pattern in STANDARD_SECTIONS:
        if pattern.search(raw_text):
            found_headings.append(sec_name)
        else:
            missing_headings.append(sec_name)
            issues.append(f"Missing standard section heading: '{sec_name}'.")
            score -= 10

    # 3. Contact information presence
    has_contact = bool(profile.email or profile.phone)
    if not has_contact:
        issues.append("No direct email address or phone number detected in main body.")
        score -= 20

    # 4. Check for unformatted dense text blocks
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    dense_paragraphs = [p for p in paragraphs if len(p.split()) > 120]
    if dense_paragraphs:
        issues.append("Found dense narrative paragraphs over 120 words. Use bullet points for ATS readability.")
        score -= 10

    # 5. Check bullet points usage
    bullet_count = raw_text.count("- ")
    if bullet_count < 4:
        issues.append("Very few bullet points detected. ATS scanners parse bulleted achievements more accurately.")
        score -= 10

    final_score = max(20, min(100, score))

    if final_score >= 80:
        verdict = "PASS"
    elif final_score >= 60:
        verdict = "CAUTION"
    else:
        verdict = "REVISE"

    return AtsReport(
        score=final_score,
        format_issues=issues,
        found_headings=found_headings,
        missing_headings=missing_headings,
        has_contact_info=has_contact,
        word_count=word_count,
        verdict=verdict,
    )
