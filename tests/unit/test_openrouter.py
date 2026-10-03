"""
Unit Tests for OpenRouter Client, Model Registry, and Structured JSON Extractor.
Uses respx for deterministic mock HTTP testing without consuming API quota.
"""

import json
import pytest
import respx
import httpx
from pydantic import BaseModel, Field

from backend.app.core.secrets import SecretManager
from backend.app.llm.structured import extract_json_object, parse_and_validate
from backend.app.llm.model_registry import ModelRegistry
from backend.app.llm.openrouter_client import OpenRouterClient, OPENROUTER_CHAT_URL, OPENROUTER_KEY_URL


class SampleScoreSchema(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    summary: str
    key_strengths: list[str]


def test_extract_json_object_with_markdown_fence():
    llm_output = """
    Here is your requested evaluation:
    ```json
    {
        "overall_score": 88,
        "summary": "Candidate matches strong Python experience.",
        "key_strengths": ["FastAPI", "Docker", "Machine Learning"]
    }
    ```
    I hope this helps!
    """
    extracted = extract_json_object(llm_output)
    assert extracted is not None
    assert extracted["overall_score"] == 88
    assert len(extracted["key_strengths"]) == 3


def test_extract_json_object_with_raw_newlines():
    # Free models frequently output raw unescaped newlines inside strings
    raw_output = '{"overall_score": 90, "summary": "Line 1\nLine 2", "key_strengths": ["Python"]}'
    extracted = extract_json_object(raw_output)
    assert extracted is not None
    assert extracted["overall_score"] == 90
    assert "Line 1" in extracted["summary"]


def test_parse_and_validate_success():
    text = '{"overall_score": 95, "summary": "Outstanding match", "key_strengths": ["RAG", "Vector DB"]}'
    model, err = parse_and_validate(text, SampleScoreSchema)
    assert err is None
    assert model is not None
    assert model.overall_score == 95


@pytest.mark.asyncio
async def test_model_registry_free_filtering():
    registry = ModelRegistry()

    # Synthetic /models response containing free, paid, and image models
    mock_models_response = {
        "data": [
            {
                "id": "vendor/paid-expensive-model",
                "name": "Super Paid",
                "pricing": {"prompt": "0.01", "completion": "0.03"},
                "context_length": 8192,
            },
            {
                "id": "vendor/good-free-model:free",
                "name": "Good Free Model",
                "pricing": {"prompt": "0", "completion": "0"},
                "context_length": 32768,
                "supported_parameters": ["structured_outputs"],
            },
            {
                "id": "black-forest-labs/flux-1-schnell",
                "name": "Flux Image Gen",
                "pricing": {"prompt": "0", "completion": "0"},
                "context_length": 1024,
            },
            {
                "id": "meta-llama/llama-3.3-70b-instruct:free",
                "name": "Llama 3.3 Free",
                "pricing": {"prompt": "0.0", "completion": "0.0"},
                "context_length": 131072,
            },
        ]
    }

    with respx.mock:
        respx.get("https://openrouter.ai/api/v1/models").mock(
            return_value=httpx.Response(200, json=mock_models_response)
        )

        models = await registry.fetch_free_models(force_refresh=True)
        model_ids = [m.id for m in models]

        assert "openrouter/free" in model_ids
        assert "vendor/good-free-model:free" in model_ids
        assert "meta-llama/llama-3.3-70b-instruct:free" in model_ids
        # Paid and image models must be excluded
        assert "vendor/paid-expensive-model" not in model_ids
        assert "black-forest-labs/flux-1-schnell" not in model_ids


@pytest.mark.asyncio
async def test_openrouter_client_chat_success(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-" + "b" * 32)
    client = OpenRouterClient()

    mock_chat_response = {
        "id": "gen-123",
        "model": "openrouter/free",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello! I am ready to analyze resumes.",
                }
            }
        ],
        "usage": {"total_tokens": 42},
    }

    with respx.mock:
        respx.post(OPENROUTER_CHAT_URL).mock(return_value=httpx.Response(200, json=mock_chat_response))
        result = await client.chat(
            messages=[{"role": "user", "content": "Ping"}],
            model="openrouter/free",
        )

        assert result["content"] == "Hello! I am ready to analyze resumes."
        assert result["model"] == "openrouter/free"
        assert result["usage"]["total_tokens"] == 42


@pytest.mark.asyncio
async def test_openrouter_key_info(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-" + "c" * 32)
    client = OpenRouterClient()

    mock_key_response = {
        "data": {
            "label": "My Dev Key",
            "usage": 0.05,
            "limit": 0.0,
            "rate_limit": {"requests": 20, "interval": "1m"},
        }
    }

    with respx.mock:
        respx.get(OPENROUTER_KEY_URL).mock(return_value=httpx.Response(200, json=mock_key_response))
        info = await client.get_key_info()

        assert info["label"] == "My Dev Key"
        assert info["usage"] == 0.05
        assert info["rate_limit"]["requests"] == 20
