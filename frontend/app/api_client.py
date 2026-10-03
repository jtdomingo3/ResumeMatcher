"""
Frontend HTTP API Client.
Communicates with the FastAPI backend (:8000).
Never handles or stores raw API keys - all sensitive operations are encapsulated in the backend.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
import json

BACKEND_BASE_URL = "http://127.0.0.1:8000/api/v1"


class BackendApiClient:
    """
    Asynchronous client for NiceGUI frontend to communicate with the FastAPI backend.
    """

    def __init__(self, base_url: str = BACKEND_BASE_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # --- Health ---
    async def get_health(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    # --- Resumes ---
    async def list_resumes(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/resumes")
            resp.raise_for_status()
            return resp.json()

    async def get_resume(self, resume_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/resumes/{resume_id}")
            resp.raise_for_status()
            return resp.json()

    async def upload_resume(self, filename: str, content_bytes: bytes, mask_pii: bool = False) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            files = {"file": (filename, content_bytes, "application/octet-stream")}
            data = {"mask_pii_enabled": "true" if mask_pii else "false"}
            resp = await client.post(f"{self.base_url}/resumes/upload", files=files, data=data)
            resp.raise_for_status()
            return resp.json()

    async def delete_resume(self, resume_id: str) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(f"{self.base_url}/resumes/{resume_id}")
            return resp.status_code == 200

    # --- Jobs ---
    async def list_jobs(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/jobs")
            resp.raise_for_status()
            return resp.json()

    async def get_job(self, job_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/jobs/{job_id}")
            resp.raise_for_status()
            return resp.json()

    async def create_job(self, title: Optional[str] = None, raw_text: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {"title": title, "raw_text": raw_text, "url": url}
            resp = await client.post(f"{self.base_url}/jobs", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def delete_job(self, job_id: str) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(f"{self.base_url}/jobs/{job_id}")
            return resp.status_code == 200

    # --- Matching ---
    async def match(self, resume_id: str, job_id: str, use_llm: bool = True) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {"resume_id": resume_id, "job_id": job_id, "use_llm": use_llm}
            resp = await client.post(f"{self.base_url}/match", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def list_matches(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/match")
            resp.raise_for_status()
            return resp.json()

    async def get_match(self, match_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/match/{match_id}")
            resp.raise_for_status()
            return resp.json()

    # --- Career ---
    async def analyze_career(self, resume_id: str, target_career: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {"resume_id": resume_id, "target_career": target_career}
            resp = await client.post(f"{self.base_url}/career/analyze", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def rewrite_bullet(self, bullet_text: str, target_role: Optional[str] = None, target_skill: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {"bullet_text": bullet_text, "target_role": target_role, "target_skill": target_skill}
            resp = await client.post(f"{self.base_url}/career/rewrite-bullet", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def generate_cover_letter(self, resume_id: str, job_id: Optional[str] = None, job_description: Optional[str] = None, company_name: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=45.0) as client:
            payload = {
                "resume_id": resume_id,
                "job_id": job_id,
                "job_description": job_description,
                "company_name": company_name,
            }
            resp = await client.post(f"{self.base_url}/career/cover-letter", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def generate_interview_prep(self, resume_id: str, job_id: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=45.0) as client:
            payload = {"resume_id": resume_id, "job_id": job_id}
            resp = await client.post(f"{self.base_url}/career/interview-prep", json=payload)
            resp.raise_for_status()
            return resp.json()

    # --- Models ---
    async def get_free_models(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/models/free")
            resp.raise_for_status()
            return resp.json()

    async def refresh_models(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/models/refresh")
            resp.raise_for_status()
            return resp.json()

    async def test_model(self, model_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/models/{model_id}/test")
            resp.raise_for_status()
            return resp.json()

    async def get_quota(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/models/quota")
            resp.raise_for_status()
            return resp.json()

    # --- Settings ---
    async def get_settings(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/settings")
            resp.raise_for_status()
            return resp.json()

    async def update_api_key(self, api_key: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {"api_key": api_key}
            resp = await client.post(f"{self.base_url}/settings/key", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def delete_api_key(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.delete(f"{self.base_url}/settings/key")
            resp.raise_for_status()
            return resp.json()

    # --- Chat Streaming ---
    async def stream_chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        enable_rag: bool = False,
        enable_web: bool = False,
        resume_id: Optional[str] = None,
        job_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "message": message,
            "session_id": session_id,
            "enable_rag": enable_rag,
            "enable_web": enable_web,
            "resume_id": resume_id,
            "job_id": job_id,
            "model": model,
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream("POST", f"{self.base_url}/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data_str)
                            if "token" in parsed:
                                yield parsed["token"]
                        except Exception:
                            pass


# Singleton frontend client instance
api_client = BackendApiClient()
