"""
FastAPI Application Entry Point for AI-Powered Resume Matcher & Career Analyzer.
Initializes database tables, syncs curated RAG knowledge base, and configures security middleware.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.core.redaction import mask_secret
from backend.app.db.session import init_db
from backend.app.rag.sync import sync_knowledge_base
from backend.app.llm.model_registry import model_registry

# Import all route submodules
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.resumes import router as resumes_router
from backend.app.api.routes.jobs import router as jobs_router
from backend.app.api.routes.match import router as match_router
from backend.app.api.routes.career import router as career_router
from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.models import router as models_router
from backend.app.api.routes.settings import router as settings_router
from backend.app.api.routes.rag import router as rag_router
from backend.app.api.routes.search import router as search_router

setup_logging()
logger = logging.getLogger("backend.app.main")



# Ensure database tables exist
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle management.
    """
    logger.info("Initializing database schemas...")
    init_db()

    logger.info("Synchronizing curated knowledge base markdown files...")
    try:
        count = sync_knowledge_base()
        logger.info(f"RAG Knowledge Base ready with {count} indexed chunks.")
    except Exception as e:
        logger.warning(f"Initial RAG sync encountered an issue: {e}")

    logger.info("Application startup complete. Ready to serve requests.")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="AI-Powered Resume Matcher & Career Analyzer",
    description="Explainable Resume-to-Job Matching, ATS Compliance, 90-Day Roadmaps, and Career Advisory.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware (allowed origins for local NiceGUI frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def secret_redaction_middleware(request: Request, call_next):
    """
    Ensures no raw secrets ever leak through unhandled error responses or response headers.
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        redacted_err = mask_secret(str(exc))
        logger.error(f"Unhandled server error: {redacted_err}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred.", "error": redacted_err},
        )


# Mount API V1 Routers
API_V1_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_V1_PREFIX)
app.include_router(resumes_router, prefix=API_V1_PREFIX)
app.include_router(jobs_router, prefix=API_V1_PREFIX)
app.include_router(match_router, prefix=API_V1_PREFIX)
app.include_router(career_router, prefix=API_V1_PREFIX)
app.include_router(chat_router, prefix=API_V1_PREFIX)
app.include_router(models_router, prefix=API_V1_PREFIX)
app.include_router(settings_router, prefix=API_V1_PREFIX)
app.include_router(rag_router, prefix=API_V1_PREFIX)
app.include_router(search_router, prefix=API_V1_PREFIX)


@app.get("/")
async def root():
    return {
        "app": "AI-Powered Resume Matcher & Career Analyzer API",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
        "version": "1.0.0",
    }
