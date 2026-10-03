"""
Security & Privacy Module: Secret Redaction and PII Masking.
Ensures API keys, tokens, and candidate PII never leak into logs or LLM prompts.
"""

import logging
import re
from typing import Dict, Tuple

# Patterns to match sensitive tokens
API_KEY_PATTERN = re.compile(r"(sk-or-v1-[A-Za-z0-9_-]{10,})", re.IGNORECASE)
BEARER_PATTERN = re.compile(r"(Bearer\s+)([A-Za-z0-9_\-\.]{15,})", re.IGNORECASE)
JWT_PATTERN = re.compile(r"\b(ey[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})\b")

# PII Patterns for candidate protection
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}")


def mask_secret(value: str | None, prefix_len: int = 4, suffix_len: int = 4) -> str:
    """
    Mask a sensitive token for display/logging.
    Example: sk-or-v1-508a...ce9c
    """
    if not value:
        return ""
    val_str = str(value).strip()
    if len(val_str) <= (prefix_len + suffix_len + 2):
        return "****"
    return f"{val_str[:prefix_len]}...{val_str[-suffix_len:]}"


def redact_text(text: str) -> str:
    """
    Replaces any matched API keys, Bearer tokens, or JWTs with masked equivalents.
    """
    if not text:
        return ""

    def replace_key(m):
        full = m.group(1)
        return mask_secret(full, 13, 4)

    def replace_bearer(m):
        prefix = m.group(1)
        token = m.group(2)
        return f"{prefix}{mask_secret(token, 4, 4)}"

    def replace_jwt(m):
        token = m.group(1)
        return mask_secret(token, 6, 6)

    sanitized = API_KEY_PATTERN.sub(replace_key, text)
    sanitized = BEARER_PATTERN.sub(replace_bearer, sanitized)
    sanitized = JWT_PATTERN.sub(replace_jwt, sanitized)
    return sanitized


class SecretRedactionFilter(logging.Filter):
    """
    Python logging filter that intercepts log records and redacts any API keys or tokens.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_text(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_text(str(v)) if isinstance(v, str) else v for v in record.args)
        return True


def mask_candidate_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Masks emails and phone numbers from resume text before transmitting to free LLM endpoints.
    Returns (masked_text, mapping_dict) so the UI or local storage can reconstruct if needed.
    """
    mapping: Dict[str, str] = {}
    masked_text = text

    # Mask emails
    email_idx = 1
    for match in EMAIL_PATTERN.finditer(text):
        email = match.group(0)
        placeholder = f"[CANDIDATE_EMAIL_{email_idx}]"
        mapping[placeholder] = email
        masked_text = masked_text.replace(email, placeholder)
        email_idx += 1

    # Mask phones
    phone_idx = 1
    for match in PHONE_PATTERN.finditer(masked_text):
        phone = match.group(0).strip()
        if len(re.sub(r"\D", "", phone)) >= 7:  # Avoid matching short numbers/dates
            placeholder = f"[CANDIDATE_PHONE_{phone_idx}]"
            mapping[placeholder] = phone
            masked_text = masked_text.replace(phone, placeholder)
            phone_idx += 1

    return masked_text, mapping


def unmask_candidate_pii(text: str, mapping: Dict[str, str]) -> str:
    """
    Restores original candidate contact information from placeholders.
    """
    restored = text
    for placeholder, original in mapping.items():
        restored = restored.replace(placeholder, original)
    return restored


mask_pii = mask_candidate_pii
unmask_pii = unmask_candidate_pii

