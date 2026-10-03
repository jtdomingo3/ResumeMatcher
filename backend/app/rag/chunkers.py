"""
Context-Preserving Document Chunkers for RAG.
Ports and extends the SmartMarkdownChunker from LIS-Prototype:
- Section-aware markdown chunker preserving heading breadcrumbs and tables intact
- Resume-specific chunker splitting experience items into cohesive accomplishment chunks
"""

import hashlib
from typing import Any, Dict, List


class SmartMarkdownChunker:
    """
    Parses Markdown technical manuals and guides into self-contained chunks
    grouped by headings, ensuring context breadcrumbs are prefixed to each chunk.
    """

    @staticmethod
    def chunk_document(content: str, source_name: str = "document.md") -> List[Dict[str, Any]]:
        lines = content.replace("\r\n", "\n").split("\n")
        chunks: List[Dict[str, Any]] = []

        current_h1 = "Knowledge Document"
        current_h2 = ""
        current_h3 = ""
        current_lines: List[str] = []

        def flush_chunk():
            nonlocal current_lines
            text = "\n".join(current_lines).strip()
            if not text:
                return

            # Build contextual breadcrumb header
            breadcrumbs = [b for b in [current_h1, current_h2, current_h3] if b]
            context_title = " > ".join(breadcrumbs)

            chunk_content = f"### Section: {context_title}\n\n{text}"
            chunk_id = hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()[:16]

            chunks.append({
                "id": f"chunk_{len(chunks) + 1}_{chunk_id}",
                "text": chunk_content,
                "metadata": {
                    "source": source_name,
                    "title": context_title,
                    "h1": current_h1,
                    "h2": current_h2,
                    "h3": current_h3,
                    "length": len(chunk_content),
                },
            })
            current_lines = []

        for line in lines:
            trimmed = line.strip()

            if trimmed.startswith("# "):
                flush_chunk()
                current_h1 = trimmed[2:].strip()
                current_h2 = ""
                current_h3 = ""
                current_lines.append(line)
            elif trimmed.startswith("## "):
                flush_chunk()
                current_h2 = trimmed[3:].strip()
                current_h3 = ""
                current_lines.append(line)
            elif trimmed.startswith("### "):
                flush_chunk()
                current_h3 = trimmed[4:].strip()
                current_lines.append(line)
            else:
                current_lines.append(line)

        flush_chunk()
        return chunks


class ResumeSectionChunker:
    """
    Splits resume content into searchable semantic units (Summary, Individual Job Roles, Skills, Projects).
    """

    @staticmethod
    def chunk_resume(profile_dict: Dict[str, Any], resume_id: str) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []

        # 1. Summary Chunk
        summary = profile_dict.get("summary") or profile_dict.get("headline")
        if summary:
            c_text = f"Candidate Profile & Summary:\n{summary}"
            chunks.append({
                "id": f"res_{resume_id}_summary",
                "text": c_text,
                "metadata": {"type": "summary", "resume_id": resume_id, "title": "Summary"},
            })

        # 2. Experience Role Chunks
        experiences = profile_dict.get("experience", [])
        for idx, exp in enumerate(experiences, start=1):
            title = exp.get("title", "Experience")
            company = exp.get("company", "Company")
            bullets = "\n".join(f"- {b}" for b in exp.get("bullets", []))
            c_text = f"Experience Role {idx}: {title} at {company}\n{bullets}"
            c_id = f"res_{resume_id}_exp_{idx}"
            chunks.append({
                "id": c_id,
                "text": c_text,
                "metadata": {"type": "experience", "resume_id": resume_id, "title": f"{title} @ {company}"},
            })

        # 3. Skills Chunk
        skills = profile_dict.get("skills", [])
        if skills:
            skill_names = [s.get("name") if isinstance(s, dict) else str(s) for s in skills]
            c_text = f"Candidate Verified Skills:\n{', '.join(skill_names)}"
            chunks.append({
                "id": f"res_{resume_id}_skills",
                "text": c_text,
                "metadata": {"type": "skills", "resume_id": resume_id, "title": "Skills Overview"},
            })

        return chunks
