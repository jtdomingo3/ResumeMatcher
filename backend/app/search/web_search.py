"""
DuckDuckGo Web Search Module with SQLite TTL Caching.
Ports and enhances the web search functionality from LIS-Prototype:
- Structured snippet extraction (Title, URL, Snippet, Source)
- SQLite caching to conserve rate limits and guarantee low latency
- Formatted prompt context builder with [WEB-n] citations
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from duckduckgo_search import DDGS

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class WebSearchEngine:
    """
    Lightweight web search client powered by DuckDuckGo with persistent TTL caching.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.SQLITE_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_cache_table()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_cache_table(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS web_search_cache (
                    query_key TEXT PRIMARY KEY,
                    results_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def _get_from_cache(self, query: str) -> Optional[List[Dict[str, Any]]]:
        clean_key = query.strip().lower()
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT results_json, expires_at FROM web_search_cache WHERE query_key = ?",
                (clean_key,),
            )
            row = cursor.fetchone()
            if row:
                if row["expires_at"] > now:
                    try:
                        return json.loads(row["results_json"])
                    except Exception:
                        pass
                else:
                    # Expired entry
                    cursor.execute("DELETE FROM web_search_cache WHERE query_key = ?", (clean_key,))
                    conn.commit()
        return None

    def _save_to_cache(self, query: str, results: List[Dict[str, Any]], ttl_seconds: float):
        clean_key = query.strip().lower()
        now = time.time()
        expires_at = now + ttl_seconds
        payload = json.dumps(results)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO web_search_cache (query_key, results_json, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (clean_key, payload, now, expires_at),
            )
            conn.commit()

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: Optional[str] = None,
        timelimit: Optional[str] = None,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Executes web search returning structured snippet items.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        # Check cache
        if not force_refresh:
            cached = self._get_from_cache(clean_query)
            if cached is not None:
                return cached[:max_results]

        search_region = region or settings.DDG_REGION
        results: List[Dict[str, Any]] = []

        try:
            ddgs = DDGS(timeout=settings.DDG_TIMEOUT_SECONDS)
            raw = list(ddgs.text(
                clean_query,
                region=search_region,
                safesearch="moderate",
                timelimit=timelimit,
                max_results=max_results,
            ))

            for item in raw:
                title = item.get("title", "").strip()
                href = item.get("href", "").strip()
                body = item.get("body", "").strip()
                if title and href:
                    results.append({
                        "title": title,
                        "url": href,
                        "snippet": body,
                        "source": "DuckDuckGo Web",
                    })

            # Cache results for 24 hours
            if results:
                self._save_to_cache(clean_query, results, ttl_seconds=settings.DDG_CACHE_TTL_HOURS * 3600)

        except Exception as e:
            logger.warning(f"DuckDuckGo search error for '{clean_query}': {e}")

        return results[:max_results]


def format_web_context(web_results: List[Dict[str, Any]]) -> str:
    """
    Formats web search snippets for injection into LLM prompts with citations.
    """
    if not web_results:
        return ""

    lines = [
        "### LIVE WEB SEARCH REFERENCES (EXTERNAL RECENT MARKET CONTEXT):",
        "*Note: External web search results are provided for live industry calibration and verification.*",
        "",
    ]

    for idx, r in enumerate(web_results, start=1):
        lines.append(f"[WEB-{idx}] {r.get('title', 'Web Citation')}")
        lines.append(f"URL: {r.get('url', '')}")
        lines.append(f"Snippet: {r.get('snippet', '')}")
        lines.append("")

    return "\n".join(lines).strip()


# Global Web Search Engine instance
web_search_engine = WebSearchEngine()
