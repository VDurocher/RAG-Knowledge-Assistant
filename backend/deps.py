"""Singleton du pipeline RAG — chargé une seule fois au démarrage FastAPI."""

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_community.vectorstores import FAISS
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever

from core.config import settings
from core.indexer import load_or_build_index
from core.loader import load_documents
from core.rag import build_llm, build_retriever


@dataclass
class PipelineState:
    """État du pipeline RAG partagé entre toutes les requêtes."""

    retriever: BaseRetriever
    vector_store: FAISS
    llm: BaseChatModel
    doc_count: int
    llm_label: str
    embedder_label: str


# Instance globale initialisée au démarrage
_state: PipelineState | None = None


def load_pipeline(force_rebuild: bool = False) -> PipelineState:
    """Charge ou recharge le pipeline RAG complet."""
    documents = load_documents(settings.knowledge_base_path)
    vector_store = load_or_build_index(documents, settings, force_rebuild=force_rebuild)
    retriever = build_retriever(
        vector_store,
        k=settings.retrieval_k,
        documents=documents,
        hybrid=settings.hybrid_search,
        bm25_weight=settings.bm25_weight,
        settings=settings,
    )
    llm = build_llm(settings)

    llm_label = (
        f"Ollama / {settings.ollama_model}"
        if settings.llm_type == "ollama"
        else f"OpenAI / {settings.openai_chat_model}"
    )
    embedder_label = "OpenAI" if settings.embedder_type == "openai" else "Local (HuggingFace)"

    return PipelineState(
        retriever=retriever,
        vector_store=vector_store,
        llm=llm,
        doc_count=len(set(d.metadata.get("source", "") for d in documents)),
        llm_label=llm_label,
        embedder_label=embedder_label,
    )


def get_state() -> PipelineState:
    """Retourne l'état courant du pipeline (erreur si non initialisé)."""
    if _state is None:
        raise RuntimeError("Pipeline non initialisé. Appelez init_pipeline() d'abord.")
    return _state


def init_pipeline(force_rebuild: bool = False) -> None:
    """Initialise ou réinitialise le pipeline global."""
    global _state
    _state = load_pipeline(force_rebuild=force_rebuild)


def reload_pipeline(force_rebuild: bool = False) -> None:
    """Recharge le pipeline (après ajout/suppression de documents)."""
    init_pipeline(force_rebuild=force_rebuild)
