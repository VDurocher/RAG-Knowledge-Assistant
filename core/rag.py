"""RAG chain: retrieval + generation + citations + confidence scores."""

from dataclasses import dataclass
from typing import Any, Generator

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever

from core.config import Settings

# RAG prompt — intelligent synthesis, refuses only if truly nothing relevant
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

# Fallback prompt — used when no relevant document is found
_FALLBACK_PROMPT = """You are a helpful and professional business assistant.
The user's question could not be answered from the company's internal documents.

Provide a clear, helpful answer based on your general knowledge.
Be concise and structured. If relevant, suggest what type of internal document
could help answer this question more precisely in the future."""


@dataclass(frozen=True)
class RAGResponse:
    """Complete RAG system response with citations."""

    answer: str
    source_documents: list[Document]
    is_fallback: bool = False

    @property
    def unique_sources(self) -> list[str]:
        """Deduplicated list of cited source files."""
        seen: set[str] = set()
        sources: list[str] = []
        for doc in self.source_documents:
            source = doc.metadata.get("source", "Unknown")
            if source not in seen:
                seen.add(source)
                sources.append(source)
        return sources


def _format_context(documents: list[Document]) -> str:
    """Formats retrieved documents into a structured context for the prompt."""
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
    """Converts a confidence score (0–1) into a human-readable label."""
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
    Retrieves documents via similarity_search_with_score and filters by threshold.

    Adds _confidence (0–1) and _confidence_label to each document's metadata.
    With normalised embeddings, FAISS L2 distance converts to:
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
    Builds a FAISS or hybrid BM25 + FAISS retriever.

    - hybrid=False (default): pure semantic search via FAISS
    - hybrid=True: EnsembleRetriever (BM25 lexical + FAISS semantic)
      Requires rank-bm25 installed and documents provided.
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
        # rank-bm25 not available — silent fallback to FAISS only
        return faiss_retriever


def build_llm(settings: Settings) -> BaseChatModel:
    """
    Instantiates the generation model according to LLM_TYPE.

    - "openai" → ChatOpenAI (cloud, API key required)
    - "ollama" → ChatOllama (local, fully free, requires Ollama installed)
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
        temperature=0.1,  # Low creativity to maximise factual accuracy
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
    Answers with streaming and citations. Returns (stream, source_docs, is_fallback).

    Parameters:
        question: User's question.
        retriever: Configured retriever (FAISS or hybrid).
        llm: Generation model.
        fallback_to_llm: Answer from general knowledge if no document found.
        score_threshold: Minimum confidence threshold (0.0 = disabled).
            Requires vector_store for score computation.
        chat_history: History [(question, answer), ...] for multi-turn context.
        vector_store: Raw FAISS index for scored retrieval (optional).
        k: Number of documents to retrieve (used with vector_store).

    Returns:
        (stream_iterator, source_documents, is_fallback)
    """
    # Retrieval: scored if vector_store available, otherwise via retriever
    if vector_store is not None and score_threshold > 0.0:
        source_documents = _retrieve_with_scores(question, vector_store, k, score_threshold)
    else:
        source_documents = retriever.invoke(question)

    # No relevant documents found
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

    # Build conversational history block
    history_block = ""
    if chat_history:
        lines = "\n".join(
            f"Human: {q}\nAssistant: {a}"
            for q, a in chat_history[-3:]  # Window of last 3 exchanges
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
