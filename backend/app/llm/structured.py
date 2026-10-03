"""
Structured LLM Output Parser and Validator.
Ports and enhances the robust JSON extraction logic from Project_Inspire,
specifically handling free LLM output anomalies (unescaped newlines, markdown code blocks,
conversational preambles/trailers).
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Robust JSON object extractor for noisy LLM outputs.
    Scans for the outermost balanced curly braces while respecting string literals and escapes.
    Includes a fallback that sanitizes unescaped newlines within strings.
    """
    if not text:
        return None

    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Fast path: direct JSON parse
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # Balanced bracket scanning
    start: Optional[int] = None
    stack = 0
    in_string = False
    escape = False

    for index, char in enumerate(cleaned):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            if start is None:
                start = index
            stack += 1
        elif char == "}":
            if start is not None:
                stack -= 1
                if stack == 0:
                    candidate = cleaned[start : index + 1]
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, dict):
                            return result
                    except Exception:
                        # Failsafe for free LLMs: escape literal newlines inside strings
                        try:
                            # Replace raw unescaped newlines in JSON candidate
                            sanitized = re.sub(r"(?<!\\)\n", r"\\n", candidate)
                            result = json.loads(sanitized)
                            if isinstance(result, dict):
                                return result
                        except Exception:
                            start = None
                            stack = 0

    return None


def parse_and_validate(raw_text: str, schema_cls: Type[T]) -> tuple[Optional[T], Optional[str]]:
    """
    Extracts JSON from text and validates it against a Pydantic schema model.
    Returns (validated_model_or_none, error_message_or_none).
    """
    extracted = extract_json_object(raw_text)
    if not extracted:
        return None, "Failed to extract valid JSON object from LLM response."

    try:
        model = schema_cls.model_validate(extracted)
        return model, None
    except ValidationError as ve:
        logger.warning(f"Schema validation error on extracted JSON: {ve}")
        return None, f"Schema validation error: {ve}"
