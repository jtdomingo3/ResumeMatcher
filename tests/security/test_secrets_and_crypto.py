"""
Security Verification Suite: Secrets, Redaction, AES-256-GCM, and PII Masking.
"""

import logging
import pytest
from backend.app.core.redaction import (
    mask_secret,
    redact_text,
    SecretRedactionFilter,
    mask_candidate_pii,
    unmask_candidate_pii,
)
from backend.app.core.crypto import encrypt_secret, decrypt_secret
from backend.app.core.secrets import SecretManager


def test_mask_secret():
    key = "sk-or-v1-" + "a" * 32 + "ce9c"
    masked = mask_secret(key, 13, 4)
    assert masked.startswith("sk-or-v1-aaaa")
    assert masked.endswith("ce9c")
    assert "..." in masked
    assert len(masked) < len(key)

    assert mask_secret("short") == "****"
    assert mask_secret("") == ""
    assert mask_secret(None) == ""


def test_redact_text_replaces_keys_and_tokens():
    raw_key = "sk-or-v1-" + "a" * 32
    bearer = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.do_not_leak"
    log_msg = f"Connecting to upstream using key {raw_key} with auth header {bearer}"

    redacted = redact_text(log_msg)

    # Ensure raw sensitive tokens are absent
    assert raw_key not in redacted
    assert "do_not_leak" not in redacted
    assert "sk-or-v1-aaaa..." in redacted
    assert "Bearer eyJh..." in redacted


def test_secret_redaction_logging_filter():
    logger = logging.getLogger("test_security_logger")
    logger.setLevel(logging.INFO)

    class CaptureHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def emit(self, record):
            self.records.append(record.getMessage())

    handler = CaptureHandler()
    handler.addFilter(SecretRedactionFilter())
    logger.addHandler(handler)

    test_key = "sk-or-v1-" + "9" * 32
    logger.info(f"Initialized client with key={test_key}")

    assert len(handler.records) == 1
    assert test_key not in handler.records[0]
    assert "sk-or-v1-9999..." in handler.records[0]


def test_crypto_aes_256_gcm_roundtrip():
    plaintext = "super-secret-user-api-key-sk-or-v1-12345"
    ciphertext_b64 = encrypt_secret(plaintext)

    assert ciphertext_b64 != plaintext
    assert len(ciphertext_b64) > 40

    decrypted = decrypt_secret(ciphertext_b64)
    assert decrypted == plaintext


def test_crypto_tamper_detection():
    plaintext = "vital-secret-payload"
    ciphertext_b64 = encrypt_secret(plaintext)

    # Tamper with the base64 string
    tampered = ciphertext_b64[:-4] + "AAAA"
    result = decrypt_secret(tampered)
    # AEAD tag mismatch must return None or fail safely, never return bad plaintext
    assert result is None


def test_pii_masking_and_unmasking():
    resume_text = (
        "John Doe\n"
        "Email: john.doe@university.edu\n"
        "Phone: +1 415-555-2671 or (555) 234-5678\n"
        "Experienced Python and Machine Learning Engineer with 6 years experience."
    )

    masked, mapping = mask_candidate_pii(resume_text)

    assert "john.doe@university.edu" not in masked
    assert "415-555-2671" not in masked
    assert "[CANDIDATE_EMAIL_1]" in masked
    assert "[CANDIDATE_PHONE_1]" in masked
    assert "Python and Machine Learning Engineer" in masked

    # Unmask
    restored = unmask_candidate_pii(masked, mapping)
    assert restored == resume_text
