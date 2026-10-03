"""
OpenRouter Free Model Registry, dynamic health tracking, and configuration endpoints.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.llm.model_registry import model_registry
from backend.app.llm.openrouter_client import openrouter_client

router = APIRouter(prefix="/models", tags=["Models"])


class ModelSettingsUpdateRequest(BaseModel):
    enabled_models: Optional[List[str]] = Field(None, description="List of model IDs to enable")
    task_assignments: Optional[Dict[str, List[str]]] = Field(
        None, description="Mapping of task names to ordered lists of model IDs"
    )


@router.get("/free")
async def get_free_models():
    """
    List all dynamically detected OpenRouter free models with capability specs and health metrics.
    """
    models = model_registry.get_enabled_free_models()
    return {
        "count": len(models),
        "models": [m.model_dump() for m in models],
    }


@router.post("/refresh")
async def refresh_free_models():
    """
    Triggers a live query to OpenRouter's /models endpoint, filters for free tier models,
    and updates the local persistent cache.
    """
    try:
        models = await model_registry.refresh()
        return {
            "message": f"Successfully refreshed free models. Found {len(models)} free models.",
            "count": len(models),
            "models": [m.model_dump() for m in models],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to refresh models from OpenRouter: {str(e)}",
        )


@router.get("/settings")
async def get_model_settings():
    """
    Retrieve user configuration for enabled free models and per-task fallback chains.
    """
    return {
        "task_fallback_chains": {
            "extraction": model_registry.get_fallback_chain_for_task("extraction"),
            "scoring": model_registry.get_fallback_chain_for_task("scoring"),
            "career_report": model_registry.get_fallback_chain_for_task("career_report"),
            "chat": model_registry.get_fallback_chain_for_task("chat"),
        }
    }


@router.post("/{model_id:path}/test")
async def test_model_ping(model_id: str):
    """
    Sends a test ping message to the specified model and returns latency and response status.
    """
    import time
    start_time = time.time()
    try:
        res = await openrouter_client.chat(
            messages=[{"role": "user", "content": "Respond with single word: OK"}],
            model=model_id,
            max_tokens=10,
            temperature=0.0,
        )
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "online",
            "model": model_id,
            "latency_ms": latency_ms,
            "response": res.get("content", "").strip(),
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "status": "error",
                "model": model_id,
                "latency_ms": latency_ms,
                "error": str(e),
            },
        )


@router.get("/quota")
async def get_quota_info():
    """
    Queries OpenRouter's /key endpoint to inspect usage, limit, and credit rate status.
    """
    try:
        info = await openrouter_client.get_key_info()
        return info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch key quota from OpenRouter: {str(e)}",
        )
