"""Chaîne RAG : récupération + génération + citations + scores de confiance."""

from dataclasses import dataclass
from typing import Any, Generator

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever

from core.config import Settings

# Prompt RAG — synthèse intelligente, refuse uniquement si vraiment rien de pertinent
_SYSTEM_PROMPT = """You are a professional knowledge assistant for a business.
Answer the user's question using the provided document context.

Guidelines:
- Extract and synthesize all relevant information from the context, even if partial.
- If the context covers the topic partially, provide what is available and specify what is missing.
- Use bullet points for lists, bold for key figures (prices, totals, names).
- When citing prices or numbers, always mention which document or supplier they come from.
- Only say you could not find something if the context contains absolutely no relevant information.
- Never invent figures, prices, or facts not present in the context.
- Format prices as clean integers when they have no cents (write 1 849 EUR, not 1 849,00 EUR).
{history_block}
Context:
{context}"""

# Prompt fallback — utilisé quand aucun document pertinent n'est trouvé
_FALLBACK_PROMPT = """You are a helpful and professional business assistant.
The user's question could not be answered from the company's internal documents.

Provide a clear, helpful answer based on your general knowledge.
Be concise and structured. If relevant, suggest what type of internal document
could help answer this question more precisely in the future."""


@dataclass(frozen=True)
class RAGResponse:
    """Réponse complète du système RAG avec citations."""

    answer: str
    source_documents: list[Document]
    is_fallback: bool = False

    @property
    def unique_sources(self) -> list[str]:
        """Liste dédupliquée des fichiers sources cités."""
        seen: set[str] = set()
        sources: list[str] = []
        for doc in self.source_documents:
            source = doc.metadata.get("source", "Unknown")
            if source not in seen:
                seen.add(source)
                sources.append(source)
        return sources


def _format_context(documents: list[Document]) -> str:
    """Formate les documents récupérés en contexte structuré pour le prompt."""
    sections: list[str] = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page")
        page_info = f", page {page + 1}" if page is not None else ""
        sections.append(
            f"[Document {i} — {source}{page_info}]\n{doc.page_content.strip()}"
        )
    return "\n\n---\n\n".join(sections)


def _confidence_label(score: float) -> str:
    """Convertit un score de confiance (0–1) en label lisible."""
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _retrieve_with_scores(
    question: str,
    vector_store: FAISS,
    k: int,
    score_threshold: float,
) -> list[Document]:
    """
    Récupère les documents via similarity_search_with_score et filtre par seuil.

    Ajoute _confidence (0–1) et _confidence_label dans metadata de chaque document.
    Avec embeddings normalisés, la distance L2 FAISS se convertit en :
        confidence = max(0, 1 - distance / 2)
    """
    results: list[tuple[Document, float]] = vector_store.similarity_search_with_score(
        question, k=k
    )
    filtered: list[Document] = []
    for doc, distance in results:
        confidence = max(0.0, 1.0 - distance / 2.0)
        if confidence >= score_threshold:
            doc.metadata["_confidence"] = round(confidence, 3)
            doc.metadata["_confidence_label"] = _confidence_label(confidence)
            filtered.append(doc)
    return filtered


def build_retriever(
    vector_store: FAISS,
    k: int,
    documents: list[Document] | None = None,
    hybrid: bool = False,
    bm25_weight: float = 0.4,
    settings: Settings | None = None,
) -> BaseRetriever:
    """
    Construit un retriever FAISS ou hybride BM25 + FAISS.

    - hybrid=False (défaut) : recherche sémantique pure via FAISS
    - hybrid=True : EnsembleRetriever (BM25 lexical + FAISS sémantique)
      Requiert rank-bm25 installé et documents fournis.
    """
    faiss_retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

    if not hybrid or documents is None:
        return faiss_retriever

    try:
        from langchain.retrievers import EnsembleRetriever
        from langchain_community.retrievers import BM25Retriever

        from core.indexer import split_documents

        chunk_size = settings.chunk_size if settings else 1000
        chunk_overlap = settings.chunk_overlap if settings else 200
        chunks = split_documents(documents, chunk_size, chunk_overlap)
        bm25_retriever = BM25Retriever.from_documents(chunks, k=k)

        return EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever],
            weights=[bm25_weight, 1.0 - bm25_weight],
        )
    except ImportError:
        # rank-bm25 absent — fallback silencieux sur FAISS seul
        return faiss_retriever


def build_llm(settings: Settings) -> BaseChatModel:
    """
    Instancie le modèle de génération selon LLM_TYPE.

    - "openai" → ChatOpenAI (cloud, API key requise)
    - "ollama" → ChatOllama (local, entièrement gratuit, nécessite Ollama installé)
    """
    if settings.llm_type == "ollama":
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
            timeout=60,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.1,  # Faible créativité pour maximiser la précision factuelle
        timeout=60,
        max_retries=2,
    )


def ask_stream(
    question: str,
    retriever: BaseRetriever,
    llm: BaseChatModel,
    fallback_to_llm: bool = False,
    score_threshold: float = 0.0,
    chat_history: list[tuple[str, str]] | None = None,
    vector_store: FAISS | None = None,
    k: int = 4,
) -> tuple[Any, list[Document], bool]:
    """
    Répond en streaming avec citations. Retourne (stream, source_docs, is_fallback).

    Paramètres:
        question: Question de l'utilisateur.
        retriever: Retriever configuré (FAISS ou hybride).
        llm: Modèle de génération.
        fallback_to_llm: Répondre depuis les connaissances générales si aucun doc trouvé.
        score_threshold: Seuil de confiance minimum (0.0 = désactivé).
            Nécessite vector_store pour le calcul des scores.
        chat_history: Historique [(question, réponse), ...] pour le contexte multi-tour.
        vector_store: Index FAISS brut pour la recherche scorée (optionnel).
        k: Nombre de documents à récupérer (utilisé avec vector_store).

    Returns:
        (stream_iterator, source_documents, is_fallback)
    """
    # Récupération : scorée si vector_store disponible, sinon via retriever
    if vector_store is not None and score_threshold > 0.0:
        source_documents = _retrieve_with_scores(question, vector_store, k, score_threshold)
    else:
        source_documents = retriever.invoke(question)

    # Aucun document pertinent trouvé
    if not source_documents:
        if fallback_to_llm:
            fallback_prompt = ChatPromptTemplate.from_messages([
                ("system", _FALLBACK_PROMPT),
                ("human", "{question}"),
            ])
            chain = fallback_prompt | llm | StrOutputParser()
            return chain.stream({"question": question}), [], True

        def _no_docs_stream() -> Generator[str, None, None]:
            yield "No relevant information found in the knowledge base for this question."

        return _no_docs_stream(), [], False

    # Construction du bloc historique conversationnel
    history_block = ""
    if chat_history:
        lines = "\n".join(
            f"Human: {q}\nAssistant: {a}"
            for q, a in chat_history[-3:]  # Fenêtre des 3 derniers échanges
        )
        history_block = f"\nPrevious conversation:\n{lines}\n"

    context = _format_context(source_documents)
    system_content = _SYSTEM_PROMPT.format(
        history_block=history_block,
        context=context,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_content),
        ("human", "{question}"),
    ])

    chain = prompt | llm | StrOutputParser()
    stream = chain.stream({"question": question})

    return stream, source_documents, False
