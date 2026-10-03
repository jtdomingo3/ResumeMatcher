"""
Settings management endpoints: masked API key status, safe key rotation, and scoring preferences.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.secrets import SecretManager
from backend.app.llm.openrouter_client import openrouter_client

router = APIRouter(prefix="/settings", tags=["Settings"])


class ApiKeyUpdateRequest(BaseModel):
    api_key: str = Field(..., description="OpenRouter API Key (sk-or-...)")


@router.get("")
async def get_settings_status():
    """
    Returns non-sensitive configuration parameters and masked API key status.
    The raw API key is NEVER returned.
    """
    masked_key = SecretManager.get_masked_openrouter_key()
    source = SecretManager.get_key_source()

    return {
        "has_openrouter_key": masked_key is not None,
        "masked_key": masked_key,
        "key_source": source,
        "pii_masking_enabled": settings.MASK_PII_DEFAULT,
        "scoring_weights": {
            "skills": settings.WEIGHT_SKILLS,
            "semantic": settings.WEIGHT_SEMANTIC,
            "experience": settings.WEIGHT_EXPERIENCE,
            "education": settings.WEIGHT_EDUCATION,
            "llm_review": settings.WEIGHT_LLM,
        },
        "search_region": "Global (DuckDuckGo)",
    }


@router.post("/key")
async def update_api_key(req: ApiKeyUpdateRequest):
    """
    Safely store a new OpenRouter API key into the OS Keyring (Windows Credential Manager).
    Verifies key validity before persisting.
    """
    key_str = req.api_key.strip()
    if not key_str.startswith("sk-or-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key format. OpenRouter API keys must start with 'sk-or-'.",
        )

    # Validate against OpenRouter /key endpoint
    is_valid, err_msg = await openrouter_client.verify_key(key_str)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Key validation failed: {err_msg}",
        )

    # Store in OS Keyring
    success = SecretManager.set_openrouter_key(key_str)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist key to OS Keyring.",
        )

    masked = SecretManager.get_masked_openrouter_key()
    return {
        "status": "success",
        "message": "OpenRouter API key securely stored in OS Keyring.",
        "masked_key": masked,
    }


@router.delete("/key")
async def delete_api_key():
    """
    Delete the OpenRouter API key from the OS Keyring.
    """
    cleared = SecretManager.clear_openrouter_key()
    return {
        "status": "success",
        "message": "OpenRouter API key removed from OS Keyring.",
        "cleared": cleared,
    }
