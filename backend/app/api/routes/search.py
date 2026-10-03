"""
DuckDuckGo live web search endpoint with SQLite caching.
"""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.search.web_search import web_search_engine

router = APIRouter(prefix="/search", tags=["Search"])


class WebSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, ge=1, le=10, description="Maximum search results to return")


@router.post("/web")
async def execute_web_search(req: WebSearchRequest):
    """
    Search DuckDuckGo with local 24-hr SQLite caching and rate-limit backoff.
    """
    results = web_search_engine.search(req.query, max_results=req.max_results)
    return {
        "query": req.query,
        "count": len(results),
        "results": results,
    }
