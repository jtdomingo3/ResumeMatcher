"""
Secret Management Module.
Implements the multi-tiered secret resolution chain with OS Keyring priority,
ensuring raw API keys are never stored in source code, version control, or logs.
"""

import os
import secrets
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import SecretStr

from backend.app.core.redaction import mask_secret

KEYRING_SERVICE = "ResumeMatcher"
OPENROUTER_KEY_ACCOUNT = "openrouter_api_key"
SERVICE_TOKEN_ACCOUNT = "internal_service_token"


class SecretManager:
    """
    Centralized resolver and manager for sensitive credentials.
    Priority order:
    1. OS Keyring (Windows Credential Manager / DPAPI)
    2. Process Environment Variable (OPENROUTER_API_KEY)
    3. Local .env file (development only)
    """

    @classmethod
    def get_openrouter_key(cls) -> Optional[SecretStr]:
        """
        Resolves the OpenRouter API key from keyring or environment.
        Returns SecretStr to prevent accidental serialization/logging.
        """
        # 1. Check OS Keyring
        try:
            import keyring
            keyring_key = keyring.get_password(KEYRING_SERVICE, OPENROUTER_KEY_ACCOUNT)
            if keyring_key and keyring_key.strip().startswith("sk-or-"):
                return SecretStr(keyring_key.strip())
        except Exception:
            pass

        # 2. Check Environment Variable
        env_key = os.environ.get("OPENROUTER_API_KEY")
        if env_key and env_key.strip().startswith("sk-or-"):
            return SecretStr(env_key.strip())

        # 3. Check .env file directly if not loaded into env
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val.startswith("sk-or-"):
                        return SecretStr(val)

        return None

    @classmethod
    def get_masked_openrouter_key(cls) -> Optional[str]:
        """
        Returns masked representation of the active OpenRouter key or None.
        """
        status = cls.get_key_status()
        return status.get("masked") if status.get("has_key") else None

    @classmethod
    def get_key_source(cls) -> Optional[str]:
        """
        Returns the resolution source of the active key or None.
        """
        status = cls.get_key_status()
        return status.get("source") if status.get("has_key") else None


    @classmethod
    def set_openrouter_key(cls, key: str) -> bool:
        """
        Persists OpenRouter key into OS Keyring.
        Returns True on success.
        """
        clean_key = key.strip()
        if not clean_key.startswith("sk-or-"):
            raise ValueError("Invalid OpenRouter key format. Expected to begin with 'sk-or-'.")

        try:
            import keyring
            keyring.set_password(KEYRING_SERVICE, OPENROUTER_KEY_ACCOUNT, clean_key)
            return True
        except Exception as e:
            # Fallback: set in environment for current session
            os.environ["OPENROUTER_API_KEY"] = clean_key
            raise RuntimeError(f"Could not write to OS Keyring: {e}. Key set in current process only.")

    @classmethod
    def clear_openrouter_key(cls) -> bool:
        """
        Deletes the key from the OS Keyring.
        """
        try:
            import keyring
            keyring.delete_password(KEYRING_SERVICE, OPENROUTER_KEY_ACCOUNT)
        except Exception:
            pass
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]
        return True

    @classmethod
    def get_key_status(cls) -> Dict[str, Any]:
        """
        Safe inspectable metadata for UI and logs. Never exposes the plaintext key.
        """
        # Determine source
        try:
            import keyring
            if keyring.get_password(KEYRING_SERVICE, OPENROUTER_KEY_ACCOUNT):
                key = keyring.get_password(KEYRING_SERVICE, OPENROUTER_KEY_ACCOUNT)
                return {
                    "has_key": True,
                    "source": "os_keyring",
                    "masked": mask_secret(key, 12, 4) if key else "",
                    "prefix": "sk-or-v1" if (key and "v1" in key) else "sk-or",
                }
        except Exception:
            pass

        if os.environ.get("OPENROUTER_API_KEY"):
            key = os.environ["OPENROUTER_API_KEY"].strip()
            return {
                "has_key": True,
                "source": "environment_variable",
                "masked": mask_secret(key, 12, 4),
                "prefix": "sk-or-v1" if "v1" in key else "sk-or",
            }

        return {
            "has_key": False,
            "source": "none",
            "masked": "",
            "prefix": "",
        }

    @classmethod
    def get_internal_service_token(cls) -> str:
        """
        Returns or generates a random 32-byte internal token used to authenticate
        NiceGUI frontend requests to the FastAPI backend.
        """
        token = os.environ.get("INTERNAL_SERVICE_TOKEN")
        if token:
            return token

        try:
            import keyring
            stored = keyring.get_password(KEYRING_SERVICE, SERVICE_TOKEN_ACCOUNT)
            if stored and len(stored) >= 32:
                os.environ["INTERNAL_SERVICE_TOKEN"] = stored
                return stored
            new_token = secrets.token_hex(32)
            keyring.set_password(KEYRING_SERVICE, SERVICE_TOKEN_ACCOUNT, new_token)
            os.environ["INTERNAL_SERVICE_TOKEN"] = new_token
            return new_token
        except Exception:
            new_token = secrets.token_hex(32)
            os.environ["INTERNAL_SERVICE_TOKEN"] = new_token
            return new_token
