"""Chaîne RAG : récupération + génération + citations."""

from dataclasses import dataclass
from typing import Any, Generator

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.config import Settings

# Prompt RAG strict — réponses ancrées dans les documents uniquement
_SYSTEM_PROMPT = """You are a precise and professional knowledge assistant for a business.
Your role is to answer questions using ONLY the provided document context.

Rules:
- Answer based exclusively on the context below.
- If the information is not in the context, say: "I couldn't find this information in the available documents."
- Be concise and structured. Use bullet points when listing multiple items.
- Do not invent facts or reference external knowledge.

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


def build_retriever(vector_store: FAISS, k: int):
    """Construit un retriever FAISS avec similarité cosinus."""
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )


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
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.1,  # Faible créativité pour maximiser la précision factuelle
    )


def ask_stream(
    question: str,
    retriever,
    llm: BaseChatModel,
    fallback_to_llm: bool = False,
) -> tuple[Any, list[Document], bool]:
    """
    Répond en streaming avec citations. Retourne un tuple (stream, source_docs, is_fallback).

    Si fallback_to_llm=True et qu'aucun document pertinent n'est trouvé,
    le LLM répond depuis ses connaissances générales avec un avertissement clair dans l'UI.

    Args:
        question: Question de l'utilisateur.
        retriever: Retriever FAISS configuré.
        llm: Modèle de génération.
        fallback_to_llm: Autoriser le fallback sur les connaissances générales du LLM.

    Returns:
        (stream_iterator, source_documents, is_fallback)
    """
    source_documents: list[Document] = retriever.invoke(question)

    # Aucun document pertinent trouvé
    if not source_documents:
        if fallback_to_llm:
            # Fallback : réponse depuis les connaissances générales du LLM
            fallback_prompt = ChatPromptTemplate.from_messages([
                ("system", _FALLBACK_PROMPT),
                ("human", "{question}"),
            ])
            chain = fallback_prompt | llm | StrOutputParser()
            return chain.stream({"question": question}), [], True

        # Mode strict : refus sans fallback
        def _no_docs_stream() -> Generator[str, None, None]:
            yield "No relevant information found in the knowledge base for this question."

        return _no_docs_stream(), [], False

    # Flux RAG normal — réponse ancrée dans les documents
    context = _format_context(source_documents)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    chain = prompt | llm | StrOutputParser()
    stream = chain.stream({"context": context, "question": question})

    return stream, source_documents, False
