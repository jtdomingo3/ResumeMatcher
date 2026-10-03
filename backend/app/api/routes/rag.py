"""
RAG Engine endpoints: query vector database, check stats, and sync markdown KB.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.rag.engine import rag_engine
from backend.app.rag.sync import sync_knowledge_base

router = APIRouter(prefix="/rag", tags=["RAG"])


class RagQueryRequest(BaseModel):
    query: str = Field(..., description="Semantic search query")
    top_k: int = Field(4, ge=1, le=10, description="Number of results to retrieve")


@router.post("/query")
async def query_knowledge_base(req: RagQueryRequest):
    """
    Perform hybrid vector + BM25 search across curated knowledge base articles.
    """
    results = rag_engine.query(req.query, top_k=req.top_k)
    return {
        "query": req.query,
        "results_count": len(results),
        "chunks": results,
    }


@router.post("/sync")
async def trigger_kb_sync(force: bool = False):
    """
    Re-indexes markdown documents from the kb/ directory into ChromaDB.
    """
    try:
        count = sync_knowledge_base(force=force)
        return {
            "status": "success",
            "message": f"Successfully synced knowledge base. Total indexed chunks: {count}",
            "indexed_chunks": count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge base sync failed: {str(e)}",
        )


@router.get("/stats")
async def get_rag_stats():
    """
    Returns index size and document counts in ChromaDB.
    """
    return {
        "total_chunks": rag_engine.count(),
        "collection_name": rag_engine.collection_name,
    }
