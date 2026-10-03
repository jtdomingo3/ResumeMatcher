"""
Document Text Normalization Pipeline.
Sanitizes raw extracted text from PDFs, DOCX files, and web pages:
- Normalizes Unicode characters (NFKC)
- Standardizes diverse bullet symbols to standard dashes
- Reconnects hyphenated word breaks across newlines
- Cleans trailing whitespaces and excessive line gaps
"""

import re
import unicodedata


BULLET_SYMBOLS = [
    "\u2022",  # •
    "\u2023",  # ‣
    "\u25b6",  # ▶
    "\u25c0",  # ◀
    "\u25ba",  # ►
    "\u25b8",  # ▸
    "\u25aa",  # ▪
    "\u25ab",  # ▫
    "\u2013",  # – (en dash)
    "\u2014",  # — (em dash)
    "\u2713",  # ✓
    "\u2714",  # ✔
    "\u25cf",  # ●
    "\u25cb",  # ○
    "\u25c6",  # ◆
    "\u25c7",  # ◇
]

BULLET_REGEX = re.compile(r"^[\s\t]*[" + "".join(BULLET_SYMBOLS) + r"][\s\t]*", re.MULTILINE)
HYPHEN_BREAK_REGEX = re.compile(r"(\b[a-zA-Z]{3,})-\s*\n\s*([a-zA-Z]{3,}\b)")
MULTI_NEWLINES_REGEX = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """
    Cleans raw document text into clean, searchable, readable format.
    """
    if not text:
        return ""

    # 1. Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Fix carriage returns
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Un-break hyphenated words split across lines
    normalized = HYPHEN_BREAK_REGEX.sub(r"\1\2", normalized)

    # 4. Standardize bullet characters to "- "
    normalized = BULLET_REGEX.sub("- ", normalized)

    # 5. Remove excessive trailing space per line
    lines = [line.strip() for line in normalized.split("\n")]
    cleaned = "\n".join(lines)

    # 6. Collapse 3+ consecutive newlines to 2
    cleaned = MULTI_NEWLINES_REGEX.sub("\n\n", cleaned)

    return cleaned.strip()


# Convenience alias
clean_and_normalize_text = normalize_text
