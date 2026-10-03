"""
Unit Tests for DuckDuckGo Web Search Engine and Caching.
"""

from unittest.mock import MagicMock, patch
import pytest
from backend.app.search.web_search import WebSearchEngine, format_web_context


def test_format_web_context():
    sample_results = [
        {
            "title": "Python Developer In-Demand Skills 2026",
            "url": "https://example.com/python-skills",
            "snippet": "FastAPI, Docker, and AI RAG pipelines top the list.",
        },
        {
            "title": "Salary Benchmark Report",
            "url": "https://example.com/salary",
            "snippet": "Senior Python engineers average $140k-$180k.",
        },
    ]

    formatted = format_web_context(sample_results)
    assert "[WEB-1] Python Developer In-Demand Skills 2026" in formatted
    assert "https://example.com/python-skills" in formatted
    assert "[WEB-2] Salary Benchmark Report" in formatted


def test_web_search_engine_caching(tmp_path):
    test_db = str(tmp_path / "test_cache.db")
    engine = WebSearchEngine(db_path=test_db)

    mock_ddg_results = [
        {"title": "Result A", "href": "https://a.com", "body": "Snippet A"},
        {"title": "Result B", "href": "https://b.com", "body": "Snippet B"},
    ]

    with patch("backend.app.search.web_search.DDGS") as mock_ddgs_cls:
        instance = mock_ddgs_cls.return_value
        instance.text.return_value = mock_ddg_results

        # 1. First call: hits DDGS
        first_call = engine.search("python developer salary 2026")
        assert len(first_call) == 2
        assert instance.text.call_count == 1

        # 2. Second call: should hit SQLite cache without calling DDGS
        second_call = engine.search("python developer salary 2026")
        assert len(second_call) == 2
        assert second_call[0]["title"] == "Result A"
        assert instance.text.call_count == 1  # Still 1 because cached!
