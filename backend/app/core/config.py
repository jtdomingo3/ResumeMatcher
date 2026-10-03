"""
Application Configuration using Pydantic Settings.
Non-secret application parameters with environment overrides.
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Service
    APP_NAME: str = "AI-Powered Resume Matcher & Career Analyzer"
    VERSION: str = "1.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    FRONTEND_PORT: int = 8080
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # OpenRouter metadata
    OPENROUTER_DEFAULT_MODEL: str = "openai/gpt-4o-mini:free"
    OPENROUTER_HTTP_REFERER: str = "https://resume-matcher.local"
    OPENROUTER_APP_TITLE: str = "AI Resume Matcher & Career Analyzer"
    OPENROUTER_MAX_RETRIES: int = 3
    OPENROUTER_TIMEOUT_SECONDS: float = 60.0
    OPENROUTER_REQUESTS_PER_MINUTE_LIMIT: int = 20
    OPENROUTER_DAILY_BUDGET_LIMIT: int = 50  # free tier default ceiling

    # RAG & Persistence
    RAG_DATA_DIR: str = "data/chroma"
    SQLITE_DB_PATH: str = "data/app.db"
    COLLECTION_KNOWLEDGE: str = "career_knowledge_base"
    COLLECTION_RESUMES: str = "user_resumes"
    COLLECTION_JOBS: str = "job_descriptions"

    # Web Search (DuckDuckGo)
    DDG_REGION: str = "wt-wt"
    DDG_TIMEOUT_SECONDS: int = 6
    DDG_MAX_RESULTS: int = 5
    DDG_CACHE_TTL_HOURS: int = 24

    # Security & Tokens
    JWT_SECRET: str = "change-this-in-production-using-cli-or-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: List[str] = ["http://127.0.0.1:8080", "http://localhost:8080"]

    # Candidate Privacy
    MASK_PII_DEFAULT: bool = True

    # Scoring Rubric Defaults (sum = 1.0)
    WEIGHT_SKILLS: float = 0.40
    WEIGHT_SEMANTIC: float = 0.20
    WEIGHT_EXPERIENCE: float = 0.15
    WEIGHT_EDUCATION: float = 0.10
    WEIGHT_LLM: float = 0.15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def db_url(self) -> str:
        Path(self.SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.SQLITE_DB_PATH}"


settings = Settings()
