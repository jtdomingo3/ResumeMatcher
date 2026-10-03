"""
Asynchronous OpenRouter API Client for Free Tier Models.
Features:
- Native multi-model fallback cascade ('models' array)
- Client-side automatic failover across enabled free models
- Backoff and retry on HTTP 429 (rate limits) and 5xx errors
- SSE streaming response generator for real-time frontend typing
- Zero raw key logging (integrates with SecretManager and SecretStr)
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.app.core.config import settings
from backend.app.core.secrets import SecretManager
from backend.app.llm.model_registry import model_registry

logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"


class OpenRouterRateLimitError(Exception):
    """Raised when upstream returns HTTP 429 Too Many Requests."""
    pass


class OpenRouterServiceError(Exception):
    """Raised when upstream returns 5xx server error."""
    pass


class OpenRouterClient:
    """
    High-performance async client for OpenRouter chat completions.
    """

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
            "X-Title": settings.OPENROUTER_APP_TITLE,
        }
        secret = SecretManager.get_openrouter_key()
        if secret:
            headers["Authorization"] = f"Bearer {secret.get_secret_value()}"
        return headers

    async def get_key_info(self) -> Dict[str, Any]:
        """
        Queries OpenRouter /key endpoint for credit balance, usage, and daily limits.
        """
        headers = self._get_headers()
        if "Authorization" not in headers:
            return {"error": "No API key configured."}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPENROUTER_KEY_URL, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("data", {})
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}

    async def test_connection(self, model: str = "openrouter/free") -> Dict[str, Any]:
        """
        Lightweight probe to test API key validity and model responsiveness.
        """
        try:
            res = await self.chat(
                messages=[{"role": "user", "content": "Respond with OK"}],
                model=model,
                max_tokens=10,
                temperature=0.0,
            )
            return {"success": True, "model": res.get("model", model), "message": res.get("content", "").strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @retry(
        retry=retry_if_exception_type((OpenRouterRateLimitError, OpenRouterServiceError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        reraise=True,
    )
    async def _send_chat_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = self._get_headers()
        if "Authorization" not in headers:
            raise RuntimeError("Cannot call OpenRouter: No API key configured in Keyring or environment.")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "5")
                logger.warning(f"[OpenRouter 429] Rate limit reached. Backing off for {retry_after}s...")
                raise OpenRouterRateLimitError(f"Rate limited (429). Retry after {retry_after}s.")

            if resp.status_code in {502, 503, 504}:
                logger.warning(f"[OpenRouter {resp.status_code}] Upstream provider busy/down. Retrying...")
                raise OpenRouterServiceError(f"OpenRouter upstream service error {resp.status_code}")

            if resp.status_code != 200:
                err_text = resp.text
                try:
                    err_json = resp.json()
                    if "error" in err_json:
                        err_text = json.dumps(err_json["error"])
                except Exception:
                    pass
                raise RuntimeError(f"OpenRouter API error (HTTP {resp.status_code}): {err_text}")

            return resp.json()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        task: str = "chat",
        max_tokens: int = 1500,
        temperature: float = 0.3,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes chat completion with server-side and client-side fallback across free models.
        """
        # Resolve fallback models chain
        model_chain = model_registry.get_fallback_chain_for_task(task)
        primary_model = model or (model_chain[0] if model_chain else settings.OPENROUTER_DEFAULT_MODEL)

        # Prepare server-side fallback list (OpenRouter allows max 3 items in 'models')
        fallback_models = [m for m in model_chain if m != primary_model][:2]

        payload: Dict[str, Any] = {
            "model": primary_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if fallback_models:
            payload["models"] = [primary_model, *fallback_models][:3]

        if response_format:
            payload["response_format"] = response_format

        # Execute with client-side failover if all server-side fallbacks fail
        last_error = None
        candidates = [primary_model, *fallback_models]
        for idx, candidate_model in enumerate(candidates):
            payload["model"] = candidate_model
            if idx > 0 and "models" in payload:
                # Remove server-side 'models' cascade on client retry to target model directly
                del payload["models"]
            try:
                data = await self._send_chat_request(payload)
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    content = choices[0]["message"].get("content", "")
                    actual_model = data.get("model", candidate_model)
                    model_registry.record_result(actual_model, success=True)
                    return {
                        "content": content,
                        "model": actual_model,
                        "usage": data.get("usage", {}),
                    }
            except Exception as e:
                last_error = e
                model_registry.record_result(candidate_model, success=False, error_msg=str(e))
                logger.warning(f"Model {candidate_model} failed: {e}. Trying next fallback...")

        raise RuntimeError(f"All configured OpenRouter models failed. Last error: {last_error}")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        task: str = "chat",
        max_tokens: int = 2000,
        temperature: float = 0.4,
    ) -> AsyncGenerator[str, None]:
        """
        Streams completions token-by-token using Server-Sent Events (SSE).
        """
        model_chain = model_registry.get_fallback_chain_for_task(task)
        target_model = model or (model_chain[0] if model_chain else settings.OPENROUTER_DEFAULT_MODEL)

        headers = self._get_headers()
        payload = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", OPENROUTER_CHAT_URL, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    raise RuntimeError(f"OpenRouter streaming error HTTP {response.status_code}: {err_body.decode('utf-8', errors='ignore')}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue


# Global client instance
openrouter_client = OpenRouterClient()
