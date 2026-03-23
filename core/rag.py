"""Chaîne RAG : récupération + génération + citations."""

from dataclasses import dataclass

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from core.config import Settings

# Prompt système — instructions strictes pour éviter les hallucinations
_SYSTEM_PROMPT = """You are a precise and professional knowledge assistant for a business.
Your role is to answer questions using ONLY the provided document context.

Rules:
- Answer based exclusively on the context below.
- If the information is not in the context, say: "I couldn't find this information in the available documents."
- Be concise and structured. Use bullet points when listing multiple items.
- Do not invent facts or reference external knowledge.

Context:
{context}"""


@dataclass(frozen=True)
class RAGResponse:
    """Réponse complète du système RAG avec citations."""

    answer: str
    source_documents: list[Document]

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


def build_llm(settings: Settings) -> ChatOpenAI:
    """Instancie le modèle de génération OpenAI."""
    return ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.1,  # Faible créativité pour maximiser la précision factuelle
    )


def ask(question: str, retriever, llm: ChatOpenAI) -> RAGResponse:
    """
    Répond à une question en récupérant les passages pertinents et en générant une réponse.

    Args:
        question: Question de l'utilisateur en langage naturel.
        retriever: Retriever FAISS configuré.
        llm: Modèle de génération OpenAI.

    Returns:
        RAGResponse avec la réponse et les documents sources (citations).
    """
    # 1. Récupération des passages pertinents
    source_documents: list[Document] = retriever.invoke(question)

    if not source_documents:
        return RAGResponse(
            answer="No relevant information found in the knowledge base for this question.",
            source_documents=[],
        )

    # 2. Construction du contexte et de la chaîne de génération
    context = _format_context(source_documents)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    chain = prompt | llm | StrOutputParser()

    # 3. Génération de la réponse
    answer = chain.invoke({"context": context, "question": question})

    return RAGResponse(answer=answer, source_documents=source_documents)


def ask_stream(question: str, retriever, llm: ChatOpenAI) -> tuple:
    """
    Variante streaming de ask() pour une meilleure UX dans Streamlit.

    Returns:
        Tuple (stream_iterator, source_documents) — le stream est consommé par st.write_stream.
    """
    source_documents: list[Document] = retriever.invoke(question)

    if not source_documents:
        def empty_stream():
            yield "No relevant information found in the knowledge base for this question."

        return empty_stream(), []

    context = _format_context(source_documents)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    chain = prompt | llm | StrOutputParser()
    stream = chain.stream({"context": context, "question": question})

    return stream, source_documents
