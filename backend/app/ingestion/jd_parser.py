"""
Job Description Parser and Secure URL Extractor.
Features:
- SSRF-protected web fetcher for direct job link imports (blocking private IP ranges)
- HTML cleaning via trafilatura
- Heuristic parsing of required vs preferred qualifications and years of experience
"""

import ipaddress
import logging
import re
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx
import trafilatura

from backend.app.ingestion.normalizer import normalize_text
from backend.app.ingestion.skills_taxonomy import extract_skills_from_text
from backend.app.schemas.profile import JobProfile, SkillItem

logger = logging.getLogger(__name__)

SENIORITY_PATTERNS = {
    "Lead": re.compile(r"\b(lead|principal|staff|architect)\b", re.IGNORECASE),
    "Senior": re.compile(r"\b(senior|sr\.?)\b", re.IGNORECASE),
    "Junior": re.compile(r"\b(junior|jr\.?|entry[- ]level|associate|intern)\b", re.IGNORECASE),
    "Mid": re.compile(r"\b(mid[- ]level|intermediate)\b", re.IGNORECASE),
}

YEARS_EXP_REGEX = re.compile(r"\b(\d{1,2})\+?\s*(?:to\s*\d{1,2}\s*)?years?(?:\s+of)?(?:\s+experience)?\b", re.IGNORECASE)


def validate_safe_url(url: str) -> str:
    """
    Guards against Server-Side Request Forgery (SSRF).
    Blocks private IP addresses, loopback, link-local, and AWS metadata endpoints.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname.")

    # Block localhost by name
    if hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Access to localhost is forbidden (SSRF protection).")

    try:
        # Resolve hostname to IP addresses
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)

            if (
                ip_obj.is_loopback
                or ip_obj.is_private
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                raise ValueError(f"Destination IP '{ip_str}' is within a private/restricted network range.")
    except socket.gaierror as ge:
        raise ValueError(f"Could not resolve hostname '{hostname}': {ge}")

    return url


async def fetch_job_from_url(url: str, timeout_seconds: float = 12.0) -> str:
    """
    Safely fetches job posting HTML and extracts clean text using trafilatura.
    """
    safe_url = validate_safe_url(url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        resp = await client.get(safe_url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch job URL (HTTP {resp.status_code})")

        # Extract main text body, discarding navigation, sidebars, and footers
        extracted = trafilatura.extract(resp.text, include_tables=True, include_links=False)
        if not extracted or len(extracted.strip()) < 100:
            # Fallback to basic html-to-text if trafilatura extracted too little
            return normalize_text(resp.text[:8000])

        return normalize_text(extracted)


fetch_page_safely = fetch_job_from_url



def parse_job_description(raw_text: str, default_title: str = "Job Opening") -> JobProfile:
    """
    Parses job description into structured JobProfile with required and preferred skills.
    """
    clean_text = normalize_text(raw_text)

    # 1. Detect title from first lines
    lines = [l.strip() for l in clean_text.split("\n") if l.strip()]
    title = default_title
    if lines:
        first_line = lines[0]
        if len(first_line) < 80 and not any(kw in first_line.lower() for kw in ["about", "overview", "description"]):
            title = first_line

    # 2. Detect seniority level (prioritize title, then body)
    seniority = "Mid"
    for level, pattern in SENIORITY_PATTERNS.items():
        if pattern.search(title):
            seniority = level
            break
    else:
        # Search body only if title did not specify
        for level, pattern in SENIORITY_PATTERNS.items():
            if level == "Lead":
                # Stricter pattern in body to avoid matching verb 'to lead'
                lead_strict = re.compile(r"\b(tech\s+lead|team\s+lead|lead\s+developer|lead\s+engineer|principal|staff)\b", re.IGNORECASE)
                if lead_strict.search(clean_text):
                    seniority = "Lead"
                    break
            elif pattern.search(clean_text):
                seniority = level
                break

    # 3. Detect minimum years of experience
    min_years = 0.0
    year_matches = YEARS_EXP_REGEX.findall(clean_text)
    if year_matches:
        try:
            min_years = float(year_matches[0])
        except ValueError:
            pass

    # 4. Partition required vs preferred skills
    required_text = clean_text
    preferred_text = ""

    # Look for "Preferred" / "Nice to have" markers
    preferred_split = re.split(r"(?i)\b(?:preferred\s+qualifications|nice\s+to\s+have|bonus\s+points|preferred)\b", clean_text)
    if len(preferred_split) > 1:
        required_text = preferred_split[0]
        preferred_text = "\n".join(preferred_split[1:])

    req_skills = extract_skills_from_text(required_text)
    pref_skills = extract_skills_from_text(preferred_text)

    # De-duplicate: if a skill is in both, keep in required
    req_names = {s.name for s in req_skills}
    pref_skills = [s for s in pref_skills if s.name not in req_names]

    # Extract bullet points as responsibilities
    responsibilities = [l for l in lines if l.startswith("- ") and len(l) > 25][:8]

    return JobProfile(
        title=title,
        seniority_level=seniority,
        min_experience_years=min_years,
        required_skills=req_skills,
        preferred_skills=pref_skills,
        responsibilities=responsibilities,
        raw_text=clean_text,
    )


class JobParser:
    """Convenience class wrapper for parsing job descriptions."""

    @staticmethod
    def parse(raw_text: str, title: Optional[str] = None) -> JobProfile:
        return parse_job_description(raw_text, default_title=title or "Job Opening")

