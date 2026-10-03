"""
Health check and system diagnostics endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.db.session import get_db
from backend.app.core.secrets import SecretManager
from backend.app.rag.engine import rag_engine
from backend.app.llm.model_registry import model_registry

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def get_health_status(db: Session = Depends(get_db)):
    """
    Returns live health diagnostics for the application backend,
    database connection, RAG vector collection, and LLM configuration.
    """
    # 1. Database check
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # 2. Key configuration
    masked_key = SecretManager.get_masked_openrouter_key()
    has_key = masked_key is not None

    # 3. Free models count
    free_models_count = len(model_registry.get_enabled_free_models())

    # 4. RAG engine status
    rag_chunks_count = rag_engine.count()

    return {
        "status": "healthy" if db_ok else "degraded",
        "database_connected": db_ok,
        "llm_key_configured": has_key,
        "masked_key": masked_key,
        "available_free_models": free_models_count,
        "rag_indexed_chunks": rag_chunks_count,
        "version": "1.0.0",
    }
