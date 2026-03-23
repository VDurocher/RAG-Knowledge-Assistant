"""Route POST /api/chat — streaming SSE token par token."""

import asyncio
import json
import threading
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.deps import get_state
from core.rag import ask_stream

router = APIRouter()


class ChatRequest(BaseModel):
    """Corps de la requête chat."""

    question: str
    chat_history: list[tuple[str, str]] = []
    score_threshold: float = 0.3
    fallback_enabled: bool = True
    k: int = 4


async def _generate_sse(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Génère les événements SSE depuis le pipeline RAG.

    Protocole :
        event: token   → {"token": "..."} — un token du stream LLM
        event: sources → [{source, page, confidence, excerpt}, ...]
        event: done    → {"is_fallback": bool}
        event: error   → {"message": "..."}
    """
    state = get_state()
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def run_rag() -> None:
        """Exécute le pipeline RAG dans un thread dédié."""
        try:
            stream, source_docs, is_fallback = ask_stream(
                question=request.question,
                retriever=state.retriever,
                llm=state.llm,
                fallback_to_llm=request.fallback_enabled,
                score_threshold=request.score_threshold,
                chat_history=request.chat_history or None,
                vector_store=state.vector_store,
                k=request.k,
            )

            for token in stream:
                loop.call_soon_threadsafe(queue.put_nowait, ("token", token))

            # Construction des citations dédupliquées
            citations: list[dict] = []
            seen: set[str] = set()
            for doc in source_docs:
                excerpt = doc.page_content[:180].strip().replace("\n", " ")
                if excerpt in seen:
                    continue
                seen.add(excerpt)
                page = doc.metadata.get("page")
                citations.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": page + 1 if page is not None else None,
                    "excerpt": excerpt + ("…" if len(doc.page_content) > 180 else ""),
                    "confidence": doc.metadata.get("_confidence"),
                    "confidence_label": doc.metadata.get("_confidence_label"),
                })

            loop.call_soon_threadsafe(queue.put_nowait, ("sources", citations))
            loop.call_soon_threadsafe(queue.put_nowait, ("done", is_fallback))

        except Exception as error:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(error)))

    thread = threading.Thread(target=run_rag, daemon=True)
    thread.start()

    while True:
        event_type, data = await queue.get()

        if event_type == "token":
            yield f"event: token\ndata: {json.dumps({'token': data})}\n\n"

        elif event_type == "sources":
            yield f"event: sources\ndata: {json.dumps(data)}\n\n"

        elif event_type == "done":
            yield f"event: done\ndata: {json.dumps({'is_fallback': data})}\n\n"
            break

        elif event_type == "error":
            yield f"event: error\ndata: {json.dumps({'message': data})}\n\n"
            break


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Répond en streaming SSE à une question sur la knowledge base."""
    return StreamingResponse(
        _generate_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
