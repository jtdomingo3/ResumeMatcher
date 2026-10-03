"""
Model Registry for Free OpenRouter Models.
Discovers, filters, caches, and benchmarks free models dynamically.
Provides per-task routing, fallback cascades, and health metrics.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.secrets import SecretManager

logger = logging.getLogger(__name__)

DEFAULT_FALLBACK_FREE_MODELS: List[Dict[str, Any]] = [
    {
        "id": "openrouter/free",
        "name": "OpenRouter Free Auto-Router (Auto-fails to best available free model)",
        "context_length": 32768,
        "is_free": True,
        "supported_parameters": ["tools", "structured_outputs"],
        "recommended_for": ["extraction", "scoring", "career_report", "chat"],
    },
    {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "name": "Meta Llama 3.3 70B Instruct (Free)",
        "context_length": 131072,
        "is_free": True,
        "supported_parameters": ["structured_outputs"],
        "recommended_for": ["career_report", "chat"],
    },
    {
        "id": "google/gemini-2.0-flash-exp:free",
        "name": "Google Gemini 2.0 Flash Exp (Free)",
        "context_length": 1048576,
        "is_free": True,
        "supported_parameters": ["tools", "structured_outputs"],
        "recommended_for": ["extraction", "scoring", "career_report"],
    },
    {
        "id": "qwen/qwen-2.5-72b-instruct:free",
        "name": "Qwen 2.5 72B Instruct (Free)",
        "context_length": 32768,
        "is_free": True,
        "supported_parameters": ["structured_outputs"],
        "recommended_for": ["scoring", "extraction"],
    },
    {
        "id": "deepseek/deepseek-r1:free",
        "name": "DeepSeek R1 (Free Reasoning)",
        "context_length": 65536,
        "is_free": True,
        "supported_parameters": ["reasoning"],
        "recommended_for": ["scoring", "career_report"],
    },
]


class FreeModelInfo(BaseModel):
    id: str
    name: str
    context_length: int = 32768
    is_free: bool = True
    supported_parameters: List[str] = Field(default_factory=list)
    recommended_for: List[str] = Field(default_factory=list)
    enabled: bool = True
    success_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None
    last_tested_at: Optional[float] = None


class ModelRegistry:
    """
    Manages live model discovery from OpenRouter API and maintains healthy free fallbacks.
    """

    def __init__(self):
        self._models: Dict[str, FreeModelInfo] = {}
        self._last_fetch_time: float = 0.0
        self._cache_ttl_seconds: float = 1800.0  # 30 minutes (from LIS-Prototype)
        self._task_assignments: Dict[str, List[str]] = {
            "extraction": ["openrouter/free", "google/gemini-2.0-flash-exp:free", "qwen/qwen-2.5-72b-instruct:free"],
            "scoring": ["openrouter/free", "deepseek/deepseek-r1:free", "meta-llama/llama-3.3-70b-instruct:free"],
            "career_report": ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free", "google/gemini-2.0-flash-exp:free"],
            "chat": ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free", "google/gemini-2.0-flash-exp:free"],
        }
        self._load_fallback_defaults()

    def _load_fallback_defaults(self):
        for raw in DEFAULT_FALLBACK_FREE_MODELS:
            self._models[raw["id"]] = FreeModelInfo(**raw)

    async def fetch_free_models(self, force_refresh: bool = False) -> List[FreeModelInfo]:
        """
        Fetches live models from OpenRouter and filters for active free endpoints.
        """
        now = time.time()
        if not force_refresh and (now - self._last_fetch_time) < self._cache_ttl_seconds and self._models:
            return list(self._models.values())

        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
            "X-Title": settings.OPENROUTER_APP_TITLE,
        }

        # Include key if available for higher rate limits on discovery
        secret = SecretManager.get_openrouter_key()
        if secret:
            headers["Authorization"] = f"Bearer {secret.get_secret_value()}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"OpenRouter /models returned HTTP {resp.status_code}. Using cached/fallback models.")
                    return list(self._models.values())

                data = resp.json().get("data", [])
                discovered: Dict[str, FreeModelInfo] = {}

                # Always keep openrouter/free router at the top
                discovered["openrouter/free"] = FreeModelInfo(
                    id="openrouter/free",
                    name="OpenRouter Free Auto-Router",
                    context_length=65536,
                    is_free=True,
                    supported_parameters=["tools", "structured_outputs"],
                    recommended_for=["extraction", "scoring", "career_report", "chat"],
                )

                for item in data:
                    model_id = item.get("id", "")
                    pricing = item.get("pricing", {})

                    # Zero-cost pricing or :free tag
                    is_zero_prompt = str(pricing.get("prompt", "1")).strip() in {"0", "0.0"}
                    is_zero_completion = str(pricing.get("completion", "1")).strip() in {"0", "0.0"}
                    is_free_price = is_zero_prompt and is_zero_completion
                    has_free_tag = model_id.endswith(":free")

                    # Exclude image / audio / video diffusion models
                    is_excluded = any(ex in model_id.lower() for ex in ["flux", "diffusion", "lyria", "whisper", "tts", "image"])

                    if (is_free_price or has_free_tag) and not is_excluded:
                        ctx = item.get("context_length") or 32768
                        name = item.get("name") or model_id
                        if not name.lower().endswith("(free)") and not model_id == "openrouter/free":
                            name = f"{name} (Free)"

                        params = item.get("supported_parameters", [])

                        # Preserve existing health statistics if already known
                        existing = self._models.get(model_id)
                        successes = existing.success_count if existing else 0
                        failures = existing.failure_count if existing else 0
                        enabled = existing.enabled if existing else True

                        rec_tasks = []
                        if "structured_outputs" in params:
                            rec_tasks.extend(["extraction", "scoring"])
                        if ctx >= 65536:
                            rec_tasks.append("career_report")
                        rec_tasks.append("chat")

                        discovered[model_id] = FreeModelInfo(
                            id=model_id,
                            name=name,
                            context_length=int(ctx),
                            is_free=True,
                            supported_parameters=params,
                            recommended_for=list(set(rec_tasks)),
                            enabled=enabled,
                            success_count=successes,
                            failure_count=failures,
                        )

                if discovered:
                    self._models = discovered
                    self._last_fetch_time = now
                    logger.info(f"Discovered {len(discovered)} active free models from OpenRouter.")

        except Exception as e:
            logger.warning(f"Error fetching live OpenRouter models: {e}. Preserving fallback list.")

        return list(self._models.values())

    def get_models(self) -> List[FreeModelInfo]:
        return list(self._models.values())

    def get_enabled_models(self) -> List[FreeModelInfo]:
        return [m for m in self._models.values() if m.enabled]

    def get_enabled_free_models(self) -> List[FreeModelInfo]:
        return self.get_enabled_models()


    def set_model_enabled(self, model_id: str, enabled: bool) -> bool:
        if model_id in self._models:
            self._models[model_id].enabled = enabled
            return True
        return False

    def get_fallback_chain_for_task(self, task: str) -> List[str]:
        """
        Returns the ordered list of model IDs configured for a specific task.
        Filters out any models currently disabled.
        """
        preferred = self._task_assignments.get(task, ["openrouter/free"])
        enabled_ids = {m.id for m in self._models.values() if m.enabled}

        chain = [m_id for m_id in preferred if m_id in enabled_ids]

        # Add remaining enabled models as safety net
        for m_id in enabled_ids:
            if m_id not in chain:
                chain.append(m_id)

        # Always ensure openrouter/free is present
        if "openrouter/free" not in chain and "openrouter/free" in enabled_ids:
            chain.insert(0, "openrouter/free")

        return chain or ["openrouter/free"]

    def record_result(self, model_id: str, success: bool, error_msg: Optional[str] = None):
        if model_id in self._models:
            model = self._models[model_id]
            if success:
                model.success_count += 1
                model.last_error = None
            else:
                model.failure_count += 1
                model.last_error = error_msg
            model.last_tested_at = time.time()


# Singleton Registry instance
model_registry = ModelRegistry()
