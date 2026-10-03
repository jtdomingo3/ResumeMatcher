"""
Cryptographic Protection Module: AES-256-GCM symmetric encryption.
Used to encrypt sensitive secrets (e.g. per-user API keys or tokens) at rest.
SECURITY NOTICE:
Unlike legacy prototypes, NO master key or fallback secret is hardcoded in the codebase.
The master key is either derived from the OS Keyring (Windows Credential Manager / DPAPI)
or an environment-injected secret.
"""

import base64
import json
import os
import secrets
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEYRING_SERVICE_NAME = "ResumeMatcher"
KEYRING_MASTER_KEY_USER = "system_master_key"


def _get_or_create_master_secret() -> bytes:
    """
    Retrieves or initializes a 32-byte master key securely without any hardcoded constants.
    Order of preference:
    1. System environment: RESUME_MATCHER_MASTER_KEY
    2. OS Keyring: Windows Credential Manager
    3. Secure local keyfile with 0600 permissions as headless fallback
    """
    # 1. Environment override
    env_secret = os.environ.get("RESUME_MATCHER_MASTER_KEY")
    if env_secret and len(env_secret.strip()) >= 32:
        return env_secret.strip().encode("utf-8")[:32]

    # 2. OS Keyring
    try:
        import keyring
        stored = keyring.get_password(KEYRING_SERVICE_NAME, KEYRING_MASTER_KEY_USER)
        if stored and len(stored) == 64:  # 32 bytes hex encoded
            return bytes.fromhex(stored)

        # Generate new random 32-byte master key
        new_key = secrets.token_bytes(32)
        keyring.set_password(KEYRING_SERVICE_NAME, KEYRING_MASTER_KEY_USER, new_key.hex())
        return new_key
    except Exception:
        # Fallback to local protected keyfile in data directory (no hardcoded strings!)
        pass

    data_dir = Path(os.environ.get("RAG_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    keyfile = data_dir / ".master_secret.key"

    if keyfile.exists():
        content = keyfile.read_text(encoding="utf-8").strip()
        if len(content) == 64:
            return bytes.fromhex(content)

    new_key = secrets.token_bytes(32)
    keyfile.write_text(new_key.hex(), encoding="utf-8")
    try:
        # On POSIX systems restrict permissions
        os.chmod(keyfile, 0o600)
    except Exception:
        pass
    return new_key


def derive_encryption_key(salt: bytes, master_secret: Optional[bytes] = None) -> bytes:
    """
    Derives a 256-bit encryption key using HKDF-SHA256 from the master secret.
    """
    secret = master_secret or _get_or_create_master_secret()
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"resume-matcher-aes-gcm-key",
    )
    return hkdf.derive(secret)


def encrypt_secret(plaintext: str) -> str:
    """
    Encrypts a plaintext secret using AES-256-GCM.
    Returns a URL-safe base64 string encoding:
    { "v": 1, "s": salt_b64, "n": nonce_b64, "ct": ciphertext_and_tag_b64 }
    """
    if not plaintext:
        return ""

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)  # 96-bit nonce recommended for AES-GCM
    key = derive_encryption_key(salt)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    payload = {
        "v": 1,
        "s": base64.b64encode(salt).decode("ascii"),
        "n": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ciphertext).decode("ascii"),
    }
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("ascii")


def decrypt_secret(cipher_payload: str) -> Optional[str]:
    """
    Decrypts an AES-256-GCM encrypted payload.
    Returns None if verification or decryption fails.
    """
    if not cipher_payload:
        return None

    try:
        raw_json = base64.urlsafe_b64decode(cipher_payload.encode("ascii")).decode("utf-8")
        parsed = json.loads(raw_json)

        if not isinstance(parsed, dict) or "ct" not in parsed or "n" not in parsed or "s" not in parsed:
            return None

        salt = base64.b64decode(parsed["s"])
        nonce = base64.b64decode(parsed["n"])
        ciphertext = base64.b64decode(parsed["ct"])

        key = derive_encryption_key(salt)
        aesgcm = AESGCM(key)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return None
