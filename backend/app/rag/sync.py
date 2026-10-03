"""
Knowledge Base Synchronization Helper.
Reads curated markdown guidelines from kb/ and indexes them into ChromaDB.
"""

from pathlib import Path
import logging
from backend.app.rag.engine import rag_engine

logger = logging.getLogger(__name__)


def sync_knowledge_base(kb_dir: str = "kb", force: bool = False) -> int:
    """
    Syncs markdown files from the kb/ directory into ChromaDB.
    Returns the count of indexed chunks.
    """
    res = rag_engine.sync_knowledge_directory(kb_dir_path=Path(kb_dir), force=force)
    return res.get("indexed_chunks", 0)
