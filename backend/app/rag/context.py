"""
RAG Context Builder with Token Budgeting and Citations.
Prepares retrieved knowledge snippets for LLM prompts with clear citation headers.
"""

from typing import Any, Dict, List


def format_rag_context(
    retrieved_chunks: List[Dict[str, Any]],
    max_tokens: int = 1500,
) -> str:
    """
    Formats vector search snippets into labeled citation context.
    Approximates tokens at ~4 characters per token.
    """
    if not retrieved_chunks:
        return ""

    lines = [
        "### RETRIEVED KNOWLEDGE BASE EXCERPTS (VERIFIED DOMAIN CONTEXT):",
        "*Use the following authoritative excerpts to inform the analysis and recommendations.*",
        "",
    ]

    current_chars = len("\n".join(lines))
    max_chars = max_tokens * 4

    for idx, chunk in enumerate(retrieved_chunks, start=1):
        meta = chunk.get("metadata", {})
        title = meta.get("title") or meta.get("source") or f"Excerpt {idx}"
        text = chunk.get("text", "").strip()

        chunk_block = f"[{idx}] {title}\n{text}\n"

        if current_chars + len(chunk_block) > max_chars:
            break

        lines.append(chunk_block)
        current_chars += len(chunk_block)

    return "\n".join(lines)
