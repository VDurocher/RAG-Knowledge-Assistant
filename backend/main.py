"""FastAPI — main entry point with lifespan and CORS."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.deps import init_pipeline
from backend.routes.chat import router as chat_router
from backend.routes.documents import router as documents_router
from core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads the RAG pipeline on startup, releases resources on shutdown."""
    settings.validate()
    init_pipeline()
    yield


app = FastAPI(
    title="RAG Knowledge Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allows the Next.js frontend in dev and prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Healthcheck — verifies the API is responding."""
    return {"status": "ok"}
