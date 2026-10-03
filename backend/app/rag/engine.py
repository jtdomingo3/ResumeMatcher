"""
RAG Engine with ChromaDB & BM25 Hybrid Retrieval.
Combines ONNX local semantic vector search with BM25 keyword search via Reciprocal Rank Fusion (RRF).
Includes automatic directory synchronization for knowledge files.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

from backend.app.core.config import settings
from backend.app.rag.chunkers import SmartMarkdownChunker, ResumeSectionChunker

logger = logging.getLogger(__name__)


class RagEngine:
    """
    Hybrid semantic + lexical vector retrieval engine.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or settings.RAG_DATA_DIR
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.data_dir)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        # Knowledge Base Collection
        self.kb_collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_KNOWLEDGE,
            embedding_function=self.embedding_fn,
            metadata={"description": "Career and Resume Optimization Knowledge Base"},
        )

        # User Resumes Collection
        self.resumes_collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_RESUMES,
            embedding_function=self.embedding_fn,
            metadata={"description": "Parsed User Resumes"},
        )

        self._bm25_indices: Dict[str, Dict[str, Any]] = {}
        self._rebuild_bm25(settings.COLLECTION_KNOWLEDGE)

    def count(self) -> int:
        """Returns the total number of chunks indexed in the knowledge base."""
        try:
            return self.kb_collection.count()
        except Exception:
            return 0


    def _rebuild_bm25(self, collection_name: str):
        collection = self.client.get_collection(collection_name)
        data = collection.get()
        docs = data.get("documents", [])
        ids = data.get("ids", [])
        metadatas = data.get("metadatas", [])

        if not docs:
            self._bm25_indices[collection_name] = {"index": None, "corpus": []}
            return

        tokenized_corpus = [doc.lower().split() for doc in docs]
        bm25 = BM25Okapi(tokenized_corpus)

        self._bm25_indices[collection_name] = {
            "index": bm25,
            "docs": docs,
            "ids": ids,
            "metadatas": metadatas,
        }

    def sync_knowledge_directory(self, kb_dir_path: Optional[Path] = None, force: bool = False) -> Dict[str, Any]:
        """
        Synchronizes all markdown files from kb/ into the Chroma knowledge collection.
        """
        kb_dir = kb_dir_path or Path("kb")
        if not kb_dir.exists():
            return {"success": False, "indexed_chunks": 0, "error": f"Directory {kb_dir} not found."}

        md_files = list(kb_dir.glob("*.md"))
        if not md_files:
            return {"success": True, "indexed_chunks": 0, "message": "No markdown files found to sync."}

        all_chunks: List[Dict[str, Any]] = []
        for file_path in md_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                chunks = SmartMarkdownChunker.chunk_document(content, source_name=file_path.name)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Error chunking {file_path.name}: {e}")

        if not all_chunks:
            return {"success": True, "indexed_chunks": 0}

        # Clear existing or update
        existing = self.kb_collection.get()
        if existing and existing.get("ids") and force:
            self.kb_collection.delete(ids=existing["ids"])

        ids = [c["id"] for c in all_chunks]
        documents = [c["text"] for c in all_chunks]
        metadatas = [c["metadata"] for c in all_chunks]

        self.kb_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        self._rebuild_bm25(settings.COLLECTION_KNOWLEDGE)

        logger.info(f"Indexed {len(all_chunks)} chunks from {len(md_files)} knowledge files into ChromaDB.")
        return {
            "success": True,
            "indexed_chunks": len(all_chunks),
            "total_collection_chunks": self.kb_collection.count(),
        }

    def index_resume(self, resume_id: str, profile_dict: Dict[str, Any]) -> int:
        """
        Indexes segmented chunks of a candidate's resume for targeted semantic matching.
        """
        chunks = ResumeSectionChunker.chunk_resume(profile_dict, resume_id)
        if not chunks:
            return 0

        ids = [c["id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        self.resumes_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        self._rebuild_bm25(settings.COLLECTION_RESUMES)
        return len(chunks)

    def query(
        self,
        query_text: str,
        collection_name: str = settings.COLLECTION_KNOWLEDGE,
        top_k: int = 4,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search (Vector + BM25) with Reciprocal Rank Fusion.
        """
        clean_query = query_text.strip()
        if not clean_query:
            return []

        collection = self.kb_collection if collection_name == settings.COLLECTION_KNOWLEDGE else self.resumes_collection
        count = collection.count()
        if count == 0:
            return []

        # 1. Vector Search
        n_results = min(top_k * 2, count)
        query_kwargs: Dict[str, Any] = {
            "query_texts": [clean_query],
            "n_results": n_results,
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        vec_res = collection.query(**query_kwargs)
        vec_docs = vec_res.get("documents", [[]])[0]
        vec_ids = vec_res.get("ids", [[]])[0]
        vec_metas = vec_res.get("metadatas", [[]])[0]
        vec_dists = vec_res.get("distances", [[]])[0]

        # 2. BM25 Search
        bm25_data = self._bm25_indices.get(collection_name)
        bm25_ranks: Dict[str, int] = {}

        if bm25_data and bm25_data["index"]:
            tokens = clean_query.lower().split()
            scores = bm25_data["index"].get_scores(tokens)
            # Rank indices by score descending
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_results]
            for rank, idx in enumerate(ranked_indices, start=1):
                if scores[idx] > 0:
                    doc_id = bm25_data["ids"][idx]
                    bm25_ranks[doc_id] = rank

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF_Score = 1/(k + vector_rank) + 1/(k + bm25_rank)
        K = 60
        fused_scores: Dict[str, float] = {}
        doc_details: Dict[str, Dict[str, Any]] = {}

        for rank, doc_id in enumerate(vec_ids, start=1):
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (K + rank))
            meta = vec_metas[rank - 1] if rank - 1 < len(vec_metas) else {}
            dist = vec_dists[rank - 1] if rank - 1 < len(vec_dists) else 1.0
            relevance = round(1.0 / (1.0 + float(dist)), 4)
            doc_details[doc_id] = {
                "id": doc_id,
                "text": vec_docs[rank - 1],
                "metadata": meta,
                "relevance": relevance,
            }

        for doc_id, rank in bm25_ranks.items():
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (K + rank))
            if doc_id not in doc_details and bm25_data:
                idx = bm25_data["ids"].index(doc_id)
                doc_details[doc_id] = {
                    "id": doc_id,
                    "text": bm25_data["docs"][idx],
                    "metadata": bm25_data["metadatas"][idx],
                    "relevance": 0.65,
                }

        # Sort by fused score
        sorted_ids = sorted(fused_scores.keys(), key=lambda i: fused_scores[i], reverse=True)[:top_k]

        results = []
        for d_id in sorted_ids:
            if d_id in doc_details:
                item = doc_details[d_id]
                item["rrf_score"] = round(fused_scores[d_id], 4)
                results.append(item)

        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "knowledge_chunks": self.kb_collection.count(),
            "resume_chunks": self.resumes_collection.count(),
            "storage_path": self.data_dir,
            "embedding_model": "all-MiniLM-L6-v2 (ONNX)",
        }


# Singleton RAG Engine instance
rag_engine = RagEngine()
