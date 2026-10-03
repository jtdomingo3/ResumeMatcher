"""
Career Copilot chat streaming endpoints with interactive RAG and Web Search context injection.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.repository import DBRepository
from backend.app.rag.engine import rag_engine
from backend.app.rag.context import format_rag_context
from backend.app.search.web_search import web_search_engine, format_web_context
from backend.app.llm.openrouter_client import openrouter_client

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User prompt or inquiry")
    session_id: Optional[str] = Field(None, description="Existing chat session ID")
    enable_rag: bool = Field(False, description="Whether to augment prompt with RAG knowledge base")
    enable_web: bool = Field(False, description="Whether to augment prompt with DuckDuckGo web search")
    resume_id: Optional[str] = Field(None, description="Optional attached candidate resume")
    job_id: Optional[str] = Field(None, description="Optional attached target job")
    model: Optional[str] = Field(None, description="Specific free model to use")


@router.post("/sessions")
async def create_session(title: Optional[str] = "Career Advisory Session", db: Session = Depends(get_db)):
    """
    Start a new Copilot chat session.
    """
    session = DBRepository.create_chat_session(db=db, title=title or "Career Advisory Session")
    return {"session_id": session.id, "title": session.title}


@router.get("/sessions")
async def list_sessions(db: Session = Depends(get_db)):
    """
    List previous Copilot chat sessions.
    """
    sessions = DBRepository.list_chat_sessions(db=db)
    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """
    Get full message transcript and citation history for a session.
    """
    session = DBRepository.get_chat_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")

    return {
        "id": session.id,
        "title": session.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": json.loads(m.citations_json) if m.citations_json else [],
                "model_used": m.model_used,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in session.messages
        ],
    }


@router.post("")
async def stream_chat(req: ChatMessageRequest, db: Session = Depends(get_db)):
    """
    Real-time SSE streaming chat with Career Copilot.
    Supports dynamic RAG vector retrieval, DuckDuckGo web search, and resume context.
    """
    # 1. Resolve or create chat session
    session_id = req.session_id
    if not session_id:
        session = DBRepository.create_chat_session(db=db, title=req.message[:40] + "...")
        session_id = session.id
    else:
        session = DBRepository.get_chat_session(db=db, session_id=session_id)
        if not session:
            session = DBRepository.create_chat_session(db=db, title=req.message[:40] + "...")
            session_id = session.id

    # 2. Record user message
    DBRepository.add_chat_message(db=db, session_id=session_id, role="user", content=req.message)

    # 3. Assemble context
    citations: List[Dict[str, Any]] = []
    context_blocks: List[str] = []

    # Optional Resume context
    if req.resume_id:
        res_rec = DBRepository.get_resume(db=db, resume_id=req.resume_id)
        if res_rec:
            context_blocks.append(f"ATTACHED CANDIDATE RESUME:\nName: {res_rec.full_name}\nExperience: {res_rec.total_experience_years} years\n{res_rec.raw_text[:1200]}")

    # Optional Job context
    if req.job_id:
        job_rec = DBRepository.get_job(db=db, job_id=req.job_id)
        if job_rec:
            context_blocks.append(f"ATTACHED JOB POSTING:\nTitle: {job_rec.title}\nCompany: {job_rec.company}\n{job_rec.raw_text[:1200]}")

    # Optional RAG context
    if req.enable_rag:
        rag_chunks = rag_engine.query(req.message, top_k=2)
        if rag_chunks:
            context_blocks.append(format_rag_context(rag_chunks))
            for c in rag_chunks:
                citations.append({
                    "type": "kb",
                    "title": c.get("metadata", {}).get("source", "Knowledge Base"),
                    "snippet": c.get("text", "")[:120],
                })

    # Optional Web Search context
    if req.enable_web:
        web_results = web_search_engine.search(req.message, max_results=2)
        if web_results:
            context_blocks.append(format_web_context(web_results))
            for w in web_results:
                citations.append({
                    "type": "web",
                    "title": w.get("title", "Web Result"),
                    "url": w.get("url", ""),
                    "snippet": w.get("snippet", "")[:120],
                })

    # 4. Prepare system prompt and history
    system_prompt = (
        "You are an empathetic, world-class Career Copilot and Senior Technical Advisor.\n"
        "Provide direct, actionable, practical career and resume guidance.\n"
        "Cite sources using [KB-n] or [WEB-n] when drawing from injected context blocks.\n"
        "Never invent credentials or false market claims.\n"
    )

    combined_context = "\n\n".join(context_blocks)
    if combined_context:
        system_prompt += f"\n\nADDITIONAL REFERENCE CONTEXT:\n{combined_context}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.message},
    ]

    async def sse_event_generator():
        # First send metadata event with session_id and citations
        meta_event = {
            "session_id": session_id,
            "citations": citations,
        }
        yield f"event: meta\ndata: {json.dumps(meta_event)}\n\n"

        full_content = []
        try:
            async for token in openrouter_client.chat_stream(
                messages=messages,
                model=req.model,
                task="chat",
                max_tokens=1500,
                temperature=0.4,
            ):
                full_content.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            fallback_text = (
                f"\n\n*(Notice: LLM response fallback triggered: {str(e)}. "
                "Please verify your API key in Settings or ensure free models are available.)*"
            )
            full_content.append(fallback_text)
            yield f"data: {json.dumps({'token': fallback_text})}\n\n"

        complete_response = "".join(full_content)
        # Save assistant message to DB
        from backend.app.db.session import SessionLocal
        save_db = SessionLocal()
        try:
            DBRepository.add_chat_message(
                db=save_db,
                session_id=session_id,
                role="assistant",
                content=complete_response,
                citations=citations,
                model_used=req.model or "free-cascade",
            )
        finally:
            save_db.close()

        yield f"event: done\ndata: [DONE]\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")
