"""Point d'entrée Streamlit — interface chat entreprise avec citations."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from core.indexer import load_or_build_index
from core.loader import list_source_files, load_documents
from core.rag import ask_stream, build_llm, build_retriever

# ─── Configuration Streamlit ─────────────────────────────────────────────────

st.set_page_config(
    page_title="RAG Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Import police */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* Logo entreprise */
.logo-wrap {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
    margin-bottom: 16px;
    border: 1px solid #1e40af33;
}
.logo-name  { color: #60a5fa; font-size: 20px; font-weight: 700; letter-spacing: 3px; margin: 0; }
.logo-sub   { color: #64748b; font-size: 10px; letter-spacing: 2px; margin-top: 3px; }

/* Badges statut */
.badge      { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge-ok   { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.badge-err  { background: #450a0a; color: #f87171; border: 1px solid #991b1b; }

/* Chips de source — compactes, inline */
.sources-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.source-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #0f1e35;
    border: 1px solid #1e3a5f;
    border-radius: 20px;
    padding: 3px 10px 3px 8px;
    font-size: 12px;
    color: #7eb3e8;
    white-space: nowrap;
}
.source-chip .page { color: #4a6a8a; margin-left: 2px; }
.conf-high { color: #4ade80; font-size: 10px; margin-left: 4px; }
.conf-medium { color: #fbbf24; font-size: 10px; margin-left: 4px; }
.conf-low { color: #f87171; font-size: 10px; margin-left: 4px; }

/* Ligne séparatrice légère sous les chips */
.sources-label { font-size: 11px; color: #4a6a8a; margin-bottom: 4px; letter-spacing: 0.5px; }

/* Bannière fallback */
.fallback-banner {
    background: #1c1505;
    border: 1px solid #854d0e;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    color: #fbbf24;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ─── Cache pipeline ───────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading knowledge base…")
def initialize_rag_pipeline(
    retrieval_k: int,
    hybrid_search: bool,
    force_rebuild: bool = False,
):
    documents = load_documents(settings.knowledge_base_path)
    vector_store = load_or_build_index(documents, settings, force_rebuild=force_rebuild)
    retriever = build_retriever(
        vector_store,
        k=retrieval_k,
        documents=documents,
        hybrid=hybrid_search,
        bm25_weight=settings.bm25_weight,
        settings=settings,
    )
    llm = build_llm(settings)
    return retriever, vector_store, llm


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="logo-wrap">
        <p class="logo-name">⬡ ACME CORP</p>
        <p class="logo-sub">KNOWLEDGE ASSISTANT</p>
    </div>
    """, unsafe_allow_html=True)

    source_files = list_source_files(settings.knowledge_base_path)

    if source_files:
        st.markdown(
            f'<span class="badge badge-ok">● {len(source_files)} documents indexed</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="badge badge-err">● No documents found</span>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("⚙️ Settings")

    retrieval_k = st.slider("Results per query", 1, 10, settings.retrieval_k)

    score_threshold = st.slider(
        "Confidence threshold",
        0.0, 1.0,
        settings.retrieval_score_threshold,
        step=0.05,
        help="Documents below this score are filtered out. 0 = disabled.",
    )

    hybrid_search = st.toggle(
        "Hybrid search (BM25 + semantic)",
        value=settings.hybrid_search,
        help="Combines keyword and semantic search. Better for product codes and proper nouns.",
    )

    fallback_enabled = st.toggle(
        "LLM fallback",
        value=True,
        help="When no relevant documents are found, the AI answers from general knowledge.",
    )

    if settings.llm_type == "ollama":
        llm_label = f"Ollama / {settings.ollama_model}"
    else:
        llm_label = f"OpenAI / {settings.openai_chat_model}"

    embed_label = "OpenAI" if settings.embedder_type == "openai" else "Local (HuggingFace)"
    st.caption(f"**LLM:** {llm_label}")
    st.caption(f"**Embedder:** {embed_label}")

    st.divider()
    st.subheader("📚 Knowledge Base")

    # Liste des fichiers avec bouton de suppression
    for filename in source_files:
        icon = "📄" if filename.endswith(".pdf") else "📊" if filename.endswith(".csv") else "📝"
        col1, col2 = st.columns([5, 1])
        with col1:
            st.caption(f"{icon} {filename}")
        with col2:
            if st.button("×", key=f"del_{filename}", help=f"Delete {filename}"):
                (settings.knowledge_base_path / filename).unlink(missing_ok=True)
                st.cache_resource.clear()
                st.rerun()

    if not source_files:
        st.info("Add PDF or TXT files to `knowledge_base/`.")

    st.divider()
    st.subheader("📤 Add Documents")

    uploaded_files = st.file_uploader(
        "PDF, TXT, MD, CSV, DOCX or JSON",
        type=["pdf", "txt", "md", "csv", "docx", "json"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        saved = []
        for uploaded_file in uploaded_files:
            dest = settings.knowledge_base_path / uploaded_file.name
            dest.write_bytes(uploaded_file.read())
            saved.append(uploaded_file.name)
        st.success(f"Added: {', '.join(saved)}")
        st.cache_resource.clear()
        st.rerun()

    st.divider()

    if st.button("🔄 Rebuild Index", use_container_width=True, type="secondary"):
        st.cache_resource.clear()
        st.rerun()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # Export de la conversation en Markdown
    if st.session_state.get("messages"):
        lines: list[str] = ["# Knowledge Assistant — Conversation Export\n"]
        for msg in st.session_state.messages:
            role = "**You**" if msg["role"] == "user" else "**Assistant**"
            lines.append(f"{role}\n\n{msg['content']}\n")
            if msg.get("citations"):
                sources = ", ".join(c["source"] for c in msg["citations"])
                lines.append(f"*Sources: {sources}*\n")
            lines.append("---\n")
        st.download_button(
            "📥 Export Conversation",
            "\n".join(lines),
            file_name="conversation.md",
            mime="text/markdown",
            use_container_width=True,
        )


# ─── Main ─────────────────────────────────────────────────────────────────────

st.title("🧠 Knowledge Assistant")
st.caption("Ask questions about your company documents. Answers are grounded in your knowledge base.")

# Validation config
try:
    settings.validate()
except ValueError as error:
    st.error(f"**Configuration error:** {error}")
    st.code("cp .env.example .env  # then fill OPENAI_API_KEY", language="bash")
    st.stop()

if not source_files:
    st.warning("**No documents found.** Add PDF or TXT files to `knowledge_base/`, then rebuild.")
    st.stop()

try:
    retriever, vector_store, llm = initialize_rag_pipeline(retrieval_k, hybrid_search)
except Exception as error:
    st.error(f"**Pipeline error:** {error}")
    st.stop()

# ─── Historique ───────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_sources(citations: list[dict]) -> None:
    """Affiche les sources sous forme de chips avec badge de confiance + excerpts."""
    if not citations:
        return

    chips_html = '<div class="sources-label">SOURCES</div><div class="sources-row">'
    for c in citations:
        page_part = f'<span class="page">· p.{c["page"]}</span>' if c.get("page") else ""

        # Badge de confiance si disponible
        conf = c.get("confidence")
        conf_html = ""
        if conf is not None:
            label = c.get("confidence_label", "")
            conf_html = f'<span class="conf-{label}" title="{conf:.0%}">●</span>'

        chips_html += (
            f'<span class="source-chip">📄 {c["source"]}{page_part}{conf_html}</span>'
        )
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)

    with st.expander("View excerpts", expanded=False):
        for c in citations:
            label = f"**{c['source']}**" + (f" — page {c['page']}" if c.get("page") else "")
            if c.get("confidence") is not None:
                label += f" — confidence {c['confidence']:.0%}"
            st.markdown(label)
            st.caption(c["excerpt"])


# Message d'accueil — affiché uniquement si l'historique est vide
if not st.session_state.messages:
    st.markdown("""
    <div style="
        text-align: center;
        padding: 48px 24px;
        color: #64748b;
    ">
        <div style="font-size: 48px; margin-bottom: 16px;">💬</div>
        <p style="font-size: 16px; margin: 0 0 8px;">
            Ask any question about your company documents.
        </p>
        <p style="font-size: 13px; color: #475569; margin: 0;">
            Answers are cited from the indexed knowledge base.
        </p>
    </div>
    """, unsafe_allow_html=True)

# Rendu de l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("is_fallback"):
            st.markdown(
                '<div class="fallback-banner">⚠️ Not in your documents — answer from general knowledge</div>',
                unsafe_allow_html=True,
            )
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and not msg.get("is_fallback"):
            render_sources(msg.get("citations", []))

# ─── Input ────────────────────────────────────────────────────────────────────

if prompt := st.chat_input("Ask a question about your documents…"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Construction de l'historique multi-tour (3 derniers échanges)
    chat_history: list[tuple[str, str]] = []
    msgs = st.session_state.messages[:-1]  # Exclure la question courante
    for i in range(0, len(msgs) - 1, 2):
        if msgs[i]["role"] == "user" and msgs[i + 1]["role"] == "assistant":
            chat_history.append((msgs[i]["content"], msgs[i + 1]["content"]))
    chat_history = chat_history[-3:]

    with st.chat_message("assistant"):
        is_fallback = False
        source_docs = []
        full_response: str = ""

        try:
            stream, source_docs, is_fallback = ask_stream(
                prompt,
                retriever,
                llm,
                fallback_to_llm=fallback_enabled,
                score_threshold=score_threshold if not hybrid_search else 0.0,
                chat_history=chat_history or None,
                vector_store=vector_store if not hybrid_search else None,
                k=retrieval_k,
            )

            if is_fallback:
                st.markdown(
                    '<div class="fallback-banner">⚠️ Not in your documents — answer from general knowledge</div>',
                    unsafe_allow_html=True,
                )

            full_response = st.write_stream(stream)

        except Exception as error:
            full_response = f"An error occurred: {error}"
            st.error(full_response)

        # Citations — uniquement si l'IA a trouvé des docs (pas en fallback)
        citations: list[dict] = []
        if source_docs:
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
            render_sources(citations)

    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "citations": citations,
        "is_fallback": is_fallback,
    })
