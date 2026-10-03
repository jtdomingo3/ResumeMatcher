"""
Unit Tests for RAG Engine: Chunkers, ChromaDB Vector Sync, BM25 Indexing, and Hybrid Query.
"""

from pathlib import Path
import pytest
from backend.app.rag.chunkers import SmartMarkdownChunker, ResumeSectionChunker
from backend.app.rag.engine import RagEngine
from backend.app.rag.context import format_rag_context


def test_smart_markdown_chunker():
    doc_content = """# Main Header
Introductory text here.

## Subsection A
Details about Subsection A with a table.
| Col1 | Col2 |
|---|---|
| A | B |

## Subsection B
Details about Subsection B.
"""
    chunks = SmartMarkdownChunker.chunk_document(doc_content, source_name="sample.md")
    assert len(chunks) >= 3
    assert chunks[0]["metadata"]["title"] == "Main Header"
    assert "Main Header > Subsection A" in chunks[1]["metadata"]["title"]
    assert "Col1" in chunks[1]["text"]


def test_resume_section_chunker():
    profile = {
        "summary": "Full Stack Python Dev with 5 years experience.",
        "experience": [
            {"title": "Backend Lead", "company": "Tech Inc", "bullets": ["Built RAG pipeline", "Led 4 engineers"]}
        ],
        "skills": [{"name": "Python"}, {"name": "FastAPI"}, {"name": "ChromaDB"}],
    }
    chunks = ResumeSectionChunker.chunk_resume(profile, resume_id="123")
    assert len(chunks) == 3
    types = {c["metadata"]["type"] for c in chunks}
    assert "summary" in types
    assert "experience" in types
    assert "skills" in types


def test_rag_engine_sync_and_hybrid_query(tmp_path):
    # Use temporary directory for Chroma storage in test
    test_rag = RagEngine(data_dir=str(tmp_path / "chroma_test"))

    # Sync kb directory
    res = test_rag.sync_knowledge_directory(kb_dir_path=Path("kb"), force=True)
    assert res["success"] is True
    assert res["indexed_chunks"] > 0

    # Query for ATS table formatting risks
    query_res = test_rag.query("table formatting risks in ATS", top_k=2)
    assert len(query_res) > 0
    assert "rrf_score" in query_res[0]
    assert "text" in query_res[0]

    # Context formatting
    formatted = format_rag_context(query_res, max_tokens=500)
    assert "[1]" in formatted
    assert "RETRIEVED KNOWLEDGE BASE EXCERPTS" in formatted
