"""Point d'entrée Streamlit — interface chat entreprise avec citations."""

import sys
from pathlib import Path

import streamlit as st

# Permettre les imports depuis la racine du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from core.indexer import load_or_build_index
from core.loader import list_source_files, load_documents
from core.rag import RAGResponse, ask_stream, build_llm, build_retriever

# ─── Configuration Streamlit ─────────────────────────────────────────────────

st.set_page_config(
    page_title="RAG Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS personnalisé — aspect enterprise ────────────────────────────────────

st.markdown("""
<style>
/* Conteneur du logo */
.logo-placeholder {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
    border: 1px solid #0f3460;
}
.logo-text {
    color: #e94560;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
    margin: 0;
}
.logo-subtitle {
    color: #a0a0b0;
    font-size: 11px;
    letter-spacing: 1px;
    margin-top: 4px;
}

/* Badge de statut */
.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.status-ready { background: #1a3a2e; color: #4caf50; border: 1px solid #4caf50; }
.status-empty { background: #3a1a1a; color: #f44336; border: 1px solid #f44336; }

/* Bloc citation */
.citation-block {
    background: #1e1e2e;
    border-left: 3px solid #0f3460;
    border-radius: 0 8px 8px 0;
    padding: 8px 12px;
    margin: 4px 0;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# ─── Cache des ressources lourdes ────────────────────────────────────────────

@st.cache_resource(show_spinner="Chargement de la base de connaissances...")
def initialize_rag_pipeline(force_rebuild: bool = False):
    """
    Initialise le pipeline RAG au démarrage.
    Mis en cache pour éviter le rechargement entre les interactions.
    """
    documents = load_documents(settings.knowledge_base_path)
    vector_store = load_or_build_index(documents, settings, force_rebuild=force_rebuild)
    retriever = build_retriever(vector_store, k=settings.retrieval_k)
    llm = build_llm(settings)
    return retriever, llm, len(documents)


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    # Logo placeholder enterprise
    st.markdown("""
    <div class="logo-placeholder">
        <p class="logo-text">⬡ ACME CORP</p>
        <p class="logo-subtitle">KNOWLEDGE ASSISTANT</p>
    </div>
    """, unsafe_allow_html=True)

    # Statut de la base de connaissances
    source_files = list_source_files(settings.knowledge_base_path)

    if source_files:
        st.markdown(
            f'<span class="status-badge status-ready">● {len(source_files)} documents indexed</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-badge status-empty">● No documents found</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ─── Paramètres ───────────────────────────────────────────────────────────
    st.subheader("⚙️ Settings")

    retrieval_k = st.slider(
        "Results per query",
        min_value=1,
        max_value=10,
        value=settings.retrieval_k,
        help="Number of document passages retrieved for each question.",
    )

    fallback_enabled = st.toggle(
        "LLM fallback",
        value=True,
        help="When no relevant documents are found, the AI answers from general knowledge and clearly labels it.",
    )

    embedder_display = "OpenAI (cloud)" if settings.embedder_type == "openai" else "Local (HuggingFace)"
    if settings.llm_type == "ollama":
        llm_display = f"Ollama / {settings.ollama_model} (local)"
    else:
        llm_display = f"OpenAI / {settings.openai_chat_model}"
    st.caption(f"**Embedder:** {embedder_display}")
    st.caption(f"**LLM:** {llm_display}")

    st.divider()

    # ─── Base de connaissances ────────────────────────────────────────────────
    st.subheader("📚 Knowledge Base")

    if source_files:
        for filename in source_files:
            icon = "📄" if filename.endswith(".pdf") else "📝"
            st.caption(f"{icon} {filename}")
    else:
        st.info("Add PDF or TXT files to the `knowledge_base/` folder.")

    st.divider()

    # ─── Actions ──────────────────────────────────────────────────────────────
    if st.button("🔄 Rebuild Index", use_container_width=True, type="secondary"):
        st.cache_resource.clear()
        st.success("Index cleared. It will be rebuilt on next query.")
        st.rerun()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ─── Zone principale ─────────────────────────────────────────────────────────

st.title("🧠 RAG Knowledge Assistant")
st.caption("Ask questions about your company documents. All answers are grounded in your knowledge base.")

# Vérification de la configuration avant affichage du chat
try:
    settings.validate()
    config_error = None
except ValueError as error:
    config_error = str(error)

if config_error:
    st.error(f"**Configuration error:** {config_error}")
    st.code("cp .env.example .env\n# Then fill in your OPENAI_API_KEY", language="bash")
    st.stop()

if not source_files:
    st.warning(
        "**No documents found.** Add PDF or TXT files to the `knowledge_base/` folder, then restart the app."
    )
    st.code("cp your_document.pdf knowledge_base/", language="bash")
    st.stop()

# Chargement du pipeline (depuis le cache si disponible)
try:
    retriever, llm, doc_count = initialize_rag_pipeline()
except Exception as pipeline_error:
    st.error(f"**Pipeline initialization failed:** {pipeline_error}")
    st.stop()

# ─── Historique des messages ─────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage de l'historique de la conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Ré-affichage du badge fallback pour les messages de l'historique
        if message["role"] == "assistant" and message.get("is_fallback"):
            st.warning("⚠️ **Not found in your documents.** Answer from general knowledge.")

        # Ré-affichage des citations pour les messages de l'assistant
        if message["role"] == "assistant" and message.get("citations"):
            with st.expander(f"📎 Citations ({len(message['citations'])} sources)", expanded=False):
                for citation in message["citations"]:
                    st.markdown(
                        f'<div class="citation-block">📄 <strong>{citation["source"]}</strong>'
                        + (f' — page {citation["page"]}' if citation.get("page") is not None else "")
                        + f'<br><em>{citation["excerpt"]}</em></div>',
                        unsafe_allow_html=True,
                    )

# ─── Saisie utilisateur ───────────────────────────────────────────────────────

if prompt := st.chat_input("Ask a question about your documents..."):
    # Affichage du message utilisateur
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    # Génération de la réponse avec streaming
    with st.chat_message("assistant"):
        response_placeholder = st.empty()

        is_fallback = False

        try:
            stream, source_docs, is_fallback = ask_stream(
                prompt, retriever, llm, fallback_to_llm=fallback_enabled
            )

            # Avertissement visible AVANT la réponse si fallback activé
            if is_fallback:
                st.warning(
                    "⚠️ **Not found in your documents.** "
                    "This answer is based on the AI's general knowledge — verify before acting on it.",
                    icon=None,
                )

            # Streaming de la réponse token par token
            full_response = st.write_stream(stream)

        except Exception as generation_error:
            full_response = f"An error occurred: {generation_error}"
            st.error(full_response)
            source_docs = []

        # Construction des citations (uniquement si réponse documentaire)
        citations: list[dict] = []
        seen_excerpts: set[str] = set()

        for doc in source_docs:
            excerpt = doc.page_content[:200].strip().replace("\n", " ")
            if excerpt not in seen_excerpts:
                seen_excerpts.add(excerpt)
                page = doc.metadata.get("page")
                citations.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": page + 1 if page is not None else None,
                    "excerpt": excerpt + ("..." if len(doc.page_content) > 200 else ""),
                })

        if citations:
            with st.expander(f"📎 Citations ({len(citations)} sources)", expanded=True):
                for citation in citations:
                    st.markdown(
                        f'<div class="citation-block">📄 <strong>{citation["source"]}</strong>'
                        + (f' — page {citation["page"]}' if citation.get("page") is not None else "")
                        + f'<br><em>{citation["excerpt"]}</em></div>',
                        unsafe_allow_html=True,
                    )

    # Sauvegarde dans l'historique
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "citations": citations,
        "is_fallback": is_fallback,
    })
