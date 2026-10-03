"""
Multi-format Document Parsers (PDF, DOCX, TXT/MD).
Extracts readable text from resumes and job descriptions with multi-column support
and scanned-document detection.
"""

import io
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
import pypdf
import pdfplumber
import docx

from backend.app.ingestion.normalizer import normalize_text

logger = logging.getLogger(__name__)


def parse_pdf(file_input: Union[bytes, Path, str]) -> Dict[str, Any]:
    """
    Extracts text from PDF files.
    Tries pypdf first; falls back to pdfplumber for complex multi-column resumes.
    """
    if isinstance(file_input, (str, Path)):
        pdf_bytes = Path(file_input).read_bytes()
    else:
        pdf_bytes = file_input

    text_parts = []
    page_count = 0
    warning: Optional[str] = None

    # 1. Primary extractor: pypdf (fastest)
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        page_count = len(reader.pages)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    except Exception as e:
        logger.warning(f"pypdf extraction error: {e}. Trying pdfplumber fallback.")

    extracted_text = "\n\n".join(text_parts).strip()

    # 2. Fallback to pdfplumber if text is empty or sparse (multi-column layouts)
    if len(extracted_text) < 150 and page_count > 0:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                plumber_parts = []
                for p in pdf.pages:
                    txt = p.extract_text(layout=True)
                    if txt:
                        plumber_parts.append(txt)
                if plumber_parts:
                    extracted_text = "\n\n".join(plumber_parts).strip()
        except Exception as pe:
            logger.warning(f"pdfplumber fallback error: {pe}")

    # Check for scanned / image-only PDFs
    if len(extracted_text) < 100 and page_count > 0:
        warning = (
            f"The uploaded PDF has {page_count} page(s) but very little text ({len(extracted_text)} characters). "
            "It may be a scanned image. OCR is recommended for scanned PDFs."
        )

    return {
        "text": normalize_text(extracted_text),
        "page_count": page_count,
        "format": "pdf",
        "warning": warning,
    }


def parse_docx(file_input: Union[bytes, Path, str]) -> Dict[str, Any]:
    """
    Extracts text from Microsoft Word (.docx) files, parsing both paragraphs and table cells.
    """
    if isinstance(file_input, (str, Path)):
        doc = docx.Document(file_input)
    else:
        doc = docx.Document(io.BytesIO(file_input))

    text_parts = []

    # 1. Paragraph text
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    # 2. Table text (many resumes use tables for skills/dates)
    for table in doc.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                text_parts.append(" | ".join(row_cells))

    raw_text = "\n".join(text_parts)
    return {
        "text": normalize_text(raw_text),
        "format": "docx",
        "warning": None,
    }


def parse_txt(file_input: Union[bytes, Path, str]) -> Dict[str, Any]:
    """
    Reads plain text or markdown files with encoding detection.
    """
    if isinstance(file_input, (str, Path)):
        raw_bytes = Path(file_input).read_bytes()
    else:
        raw_bytes = file_input

    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            text = raw_bytes.decode(encoding)
            return {
                "text": normalize_text(text),
                "format": "txt",
                "warning": None,
            }
        except UnicodeDecodeError:
            continue

    return {
        "text": normalize_text(raw_bytes.decode("utf-8", errors="replace")),
        "format": "txt",
        "warning": "Character encoding was lossy.",
    }


def parse_document(file_input: Union[bytes, Path, str], filename: str) -> Dict[str, Any]:
    """
    Generic dispatcher based on file extension.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(file_input)
    elif ext in {".docx", ".doc"}:
        return parse_docx(file_input)
    elif ext in {".txt", ".md", ".markdown"}:
        return parse_txt(file_input)
    else:
        raise ValueError(f"Unsupported document format: '{ext}'. Supported: .pdf, .docx, .txt, .md")


class DocumentParser:
    """Convenience class wrapper for parsing document bytes."""

    @staticmethod
    def parse_bytes(content: bytes, filename: str) -> str:
        result = parse_document(content, filename)
        return result.get("text", "")

